"""
Módulo de montaje y edición de video.
Orquesta los cortes, concatenaciones y ensamblado final de clips utilizando FFmpeg nativo.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from modulos.analizador_audio import obtener_ruta_ejecutable_ffmpeg


def generar_archivo_demuxer_concat(
    ruta_video_origen: str,
    segmentos: List[Tuple[float, float]],
    ruta_archivo_lista: str
) -> None:
    """
    Genera un archivo de texto con el formato requerido por el concatenador de FFmpeg (concat demuxer).

    Args:
        ruta_video_origen: Ruta absoluta al video fuente.
        segmentos: Lista de tuplas (inicio, fin) en segundos.
        ruta_archivo_lista: Ruta donde se guardará el archivo temporal de lista de segmentos.
    """
    ruta_normalizada = Path(ruta_video_origen).resolve().as_posix()

    lineas = ["ffconcat version 1.0"]
    for inicio, fin in segmentos:
        duracion = fin - inicio
        if duracion <= 0:
            continue
        lineas.append(f"file '{ruta_normalizada}'")
        lineas.append(f"inpoint {inicio:.3f}")
        lineas.append(f"outpoint {fin:.3f}")

    with open(ruta_archivo_lista, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")


def detectar_codificador_optimo() -> Tuple[str, List[str]]:
    """
    Determina si se puede utilizar aceleración por hardware NVIDIA NVENC o si se debe usar CPU (libx264).

    Returns:
        Tupla con (nombre_codec, lista_argumentos_optimizacion).
    """
    ejecutable = obtener_ruta_ejecutable_ffmpeg()
    try:
        # Prueba de soporte NVENC
        prueba = subprocess.run(
            [ejecutable, "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if prueba.returncode == 0:
            return "h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
    except Exception:
        pass

    # Fallback seguro por CPU con preset ultrafast
    return "libx264", ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"]


def cortar_y_unir_segmentos(
    ruta_video_origen: str,
    segmentos_activos: List[Tuple[float, float]],
    ruta_video_destino: str,
    usar_recodificacion_rapida: bool = True
) -> str:
    """
    Corta los fragmentos activos de un video y los concatena para generar un video continuo sin pausas.

    Args:
        ruta_video_origen: Ruta al video original que se desea editar.
        segmentos_activos: Lista de tuplas (tiempo_inicio, tiempo_fin) que se deben conservar.
        ruta_video_destino: Ruta donde se generará el video procesado.
        usar_recodificacion_rapida: Si es True, utiliza 'ultrafast' con h264 para garantizar
                                   cortes limpios en keyframes sin pérdida de sincronía de audio.

    Returns:
        Ruta absoluta al video final exportado.

    Raises:
        FileNotFoundError: Si el video origen no existe o la lista de segmentos está vacía.
        RuntimeError: Si la ejecución de FFmpeg falla.
    """
    archivo_origen = Path(ruta_video_origen)
    if not archivo_origen.exists():
        raise FileNotFoundError(f"El archivo de video origen no existe: {ruta_video_origen}")

    if not segmentos_activos:
        raise ValueError("La lista de segmentos activos no puede estar vacía.")

    archivo_destino = Path(ruta_video_destino)
    archivo_destino.parent.mkdir(parents=True, exist_ok=True)

    ejecutable_ffmpeg = obtener_ruta_ejecutable_ffmpeg()

    # Si solo hay un segmento que abarca todo el video, copiar directamente
    if len(segmentos_activos) == 1 and segmentos_activos[0][0] <= 0.05:
        # Segmento único sin cortes
        inicio, fin = segmentos_activos[0]
        comando_unico = [
            ejecutable_ffmpeg, "-y",
            "-ss", str(inicio),
            "-to", str(fin),
            "-i", str(archivo_origen),
            "-c", "copy",
            str(archivo_destino)
        ]
        proceso = subprocess.run(comando_unico, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proceso.returncode != 0:
            raise RuntimeError(f"Error al exportar video: {proceso.stderr}")
        return str(archivo_destino.resolve())

    # Para múltiples segmentos, usar concat demuxer con archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as archivo_lista_temp:
        ruta_lista = archivo_lista_temp.name

    try:
        generar_archivo_demuxer_concat(str(archivo_origen), segmentos_activos, ruta_lista)

        # Configuración de comando FFmpeg
        comando_concat = [
            ejecutable_ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", ruta_lista
        ]

        if usar_recodificacion_rapida:
            _, args_codec = detectar_codificador_optimo()
            comando_concat.extend(args_codec)
            comando_concat.extend([
                "-c:a", "aac",
                "-b:a", "192k"
            ])
        else:
            # Copia directa de streams (más rápido pero sensible a keyframes)
            comando_concat.extend(["-c", "copy"])

        comando_concat.append(str(archivo_destino))

        proceso = subprocess.run(
            comando_concat,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if proceso.returncode != 0:
            raise RuntimeError(
                f"Error durante el ensamblado y corte con FFmpeg: {proceso.stderr.strip()}"
            )

        return str(archivo_destino.resolve())

    finally:
        # Limpieza rigurosa del archivo de lista temporal
        if Path(ruta_lista).exists():
            Path(ruta_lista).unlink()


def aplicar_audio_ducking(
    ruta_video_o_audio_voz: str,
    ruta_musica_fondo: str,
    ruta_salida: str,
    volumen_musica_base: float = 0.25,
    atenuacion_db: float = 14.0
) -> str:
    """
    Mezcla una pista de música de fondo con la voz principal, aplicando Audio Ducking automático:
    el volumen de la música baja cuando el creador habla y sube en las pausas.

    Args:
        ruta_video_o_audio_voz: Video o archivo de audio principal que contiene la voz.
        ruta_musica_fondo: Pista de audio con música de fondo (se repite en bucle si es más corta).
        ruta_salida: Archivo destino generado con la mezcla equilibrada.
        volumen_musica_base: Nivel de volumen de la música cuando no hay voz (ej. 0.25 = 25%).
        atenuacion_db: Cantidad de decibelios a atenuar cuando la voz está activa.

    Returns:
        Ruta absoluta al archivo final con audio ducking aplicado.

    Raises:
        FileNotFoundError: Si los archivos de entrada no existen.
        RuntimeError: Si FFmpeg falla en la mezcla.
    """
    archivo_voz = Path(ruta_video_o_audio_voz)
    archivo_musica = Path(ruta_musica_fondo)

    if not archivo_voz.exists():
        raise FileNotFoundError(f"Archivo de voz o video no encontrado: {ruta_video_o_audio_voz}")
    if not archivo_musica.exists():
        raise FileNotFoundError(f"Archivo de música de fondo no encontrado: {ruta_musica_fondo}")

    salida = Path(ruta_salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    ejecutable_ffmpeg = obtener_ruta_ejecutable_ffmpeg()

    # Filtro complejo de FFmpeg:
    # 1. La música se ajusta a su volumen base y se repite en bucle infinito si es necesario.
    # 2. La voz actúa como señal de control (sidechain) para comprimir la música cuando se detecta voz.
    # 3. Se mezclan ambas pistas preservando la duración exacta del video principal.
    ratio_compresion = 4.0
    filtro_ducking = (
        f"[1:a]volume={volumen_musica_base:.2f},aloop=loop=-1:size=2e+09[musica_base];"
        f"[musica_base][0:a]sidechaincompress=threshold=0.03:ratio={ratio_compresion}:"
        f"attack=120:release=450[musica_atenuada];"
        f"[0:a][musica_atenuada]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    es_video = archivo_voz.suffix.lower() in [".mp4", ".mkv", ".mov", ".webm", ".avi"]

    comando = [
        ejecutable_ffmpeg, "-y",
        "-i", str(archivo_voz),
        "-stream_loop", "-1",
        "-i", str(archivo_musica),
        "-filter_complex", filtro_ducking
    ]

    if es_video:
        # Mantener el flujo de video intacto sin re-codificar (máxima velocidad)
        comando.extend([
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest"
        ])
    else:
        # Salida puramente de audio
        comando.extend([
            "-map", "[aout]",
            "-c:a", "pcm_s16le"
        ])

    comando.append(str(salida))

    proceso = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if proceso.returncode != 0:
        raise RuntimeError(f"Error al aplicar audio ducking con FFmpeg: {proceso.stderr.strip()}")

    return str(salida.resolve())


def escapar_ruta_filtro_ffmpeg(ruta: str) -> str:
    """
    Escapa una ruta de archivo en Windows para que FFmpeg la interprete correctamente
    dentro de la sintaxis de filtros como 'subtitles'.
    Convierte barras invertidas a slash posix y escapa los dos puntos ':' de las unidades de disco.

    Args:
        ruta: Ruta local al archivo.

    Returns:
        Cadena con la ruta escapada (ej. 'C\\:/carpeta/archivo.ass').
    """
    ruta_posix = Path(ruta).resolve().as_posix()
    return ruta_posix.replace(":", "\\:")


def renderizar_short_con_subtitulos(
    ruta_video_origen: str,
    tiempo_inicio: float,
    duracion: float,
    ruta_salida: str,
    ruta_subtitulos_ass: Optional[str] = None,
    formato_vertical: bool = False,
    tiempo_climax_relativo: Optional[float] = None,
    incluir_zoom_impacto: bool = False,
    ruta_audio_mezclado: Optional[str] = None
) -> str:
    """
    Renderiza un clip independiente (Short) a partir de una marca de tiempo del video original,
    con opción de subtítulos dinámicos incrustados, formato vertical 9:16 (fondo desenfocado + acción centrada),
    efecto de zoom de impacto (punch-in zoom) en el clímax y pista de audio mezclada con música gamer y SFX.

    Args:
        ruta_video_origen: Archivo de video fuente.
        tiempo_inicio: Segundo de inicio del clip.
        duracion: Duración del clip en segundos.
        ruta_salida: Archivo destino MP4 generado.
        ruta_subtitulos_ass: Ruta opcional a los subtítulos .ass que se quemarán (hardsub).
        formato_vertical: Si es True, renderiza en lienzo 9:16 (1080x1920) ideal para TikTok y Shorts.
        tiempo_climax_relativo: Segundo dentro del clip donde ocurre la jugada clave para centrar el zoom.
        incluir_zoom_impacto: Si es True, realiza un punch-in zoom dramático de 1.25x en el clímax.
        ruta_audio_mezclado: Ruta a pista WAV personalizada (juego + música gamer + SFX de impacto).

    Returns:
        Ruta absoluta al Short generado.

    Raises:
        FileNotFoundError: Si el video de entrada no existe.
        RuntimeError: Si la renderización con FFmpeg falla.
    """
    archivo_origen = Path(ruta_video_origen)
    if not archivo_origen.exists():
        raise FileNotFoundError(f"Video de entrada no encontrado: {ruta_video_origen}")

    salida = Path(ruta_salida)
    salida.parent.mkdir(parents=True, exist_ok=True)

    ejecutable = obtener_ruta_ejecutable_ffmpeg()
    _, args_codec = detectar_codificador_optimo()

    tiempo_inicio_seg = max(0.0, float(tiempo_inicio))
    duracion_seg = max(0.5, float(duracion))

    tiene_subtitulos = bool(ruta_subtitulos_ass and Path(ruta_subtitulos_ass).exists())
    sub_escapada = escapar_ruta_filtro_ffmpeg(ruta_subtitulos_ass) if tiene_subtitulos else ""

    tiene_audio_mezclado = bool(ruta_audio_mezclado and Path(ruta_audio_mezclado).exists())

    comando_base = [
        ejecutable, "-y",
        "-ss", f"{tiempo_inicio_seg:.3f}",
        "-t", f"{duracion_seg:.3f}",
        "-i", str(archivo_origen)
    ]

    if tiene_audio_mezclado:
        comando_base.extend(["-i", str(Path(ruta_audio_mezclado).resolve())])

    # Configurar expresión de punch-in zoom dramático (1.25x por ~2 segundos)
    aplicar_zoom = incluir_zoom_impacto and (tiempo_climax_relativo is not None)
    if aplicar_zoom:
        t_zoom_ini = max(0.0, float(tiempo_climax_relativo) - 0.2)
        t_zoom_fin = float(tiempo_climax_relativo) + 1.8
        filtro_crop_zoom = (
            f"crop=w='if(between(t,{t_zoom_ini:.2f},{t_zoom_fin:.2f}),in_w*0.80,in_w)':"
            f"h='if(between(t,{t_zoom_ini:.2f},{t_zoom_fin:.2f}),in_h*0.80,in_h)'"
        )
    else:
        filtro_crop_zoom = ""

    mapa_audio = ["-map", "1:a"] if tiene_audio_mezclado else ["-map", "0:a?"]

    if formato_vertical:
        # Lienzo vertical 9:16 (1080x1920)
        # Capa fondo: reescalado a 1080x1920 recortado con desenfoque de fondo
        # Capa frente: 1080 de ancho con zoom de impacto opcional y centrada verticalmente
        if aplicar_zoom:
            transformacion_fg = f"[fg_in]{filtro_crop_zoom},scale=1080:-1[fg];"
        else:
            transformacion_fg = "[fg_in]scale=1080:-1[fg];"

        filtro_vertical = (
            "[0:v]split=2[bg_in][fg_in];"
            "[bg_in]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:20[bg];"
            f"{transformacion_fg}"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        if tiene_subtitulos:
            filtro_completo = f"{filtro_vertical}[comp];[comp]subtitles='{sub_escapada}'[vout]"
        else:
            filtro_completo = f"{filtro_vertical}[vout]"

        comando = list(comando_base)
        comando.extend([
            "-filter_complex", filtro_completo,
            "-map", "[vout]"
        ])
        comando.extend(mapa_audio)
        comando.extend(args_codec)
        comando.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            str(salida)
        ])
    else:
        # Formato estándar panorámico (16:9)
        comando = list(comando_base)
        filtros_vf = []
        if aplicar_zoom:
            filtros_vf.append(f"{filtro_crop_zoom},scale=1920:1080")
        if tiene_subtitulos:
            filtros_vf.append(f"subtitles='{sub_escapada}'")

        if filtros_vf:
            comando.extend(["-vf", ",".join(filtros_vf)])

        if tiene_audio_mezclado:
            comando.extend(["-map", "0:v", "-map", "1:a"])
        else:
            comando.extend(["-map", "0:v?", "-map", "0:a?"])

        comando.extend(args_codec)
        comando.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            str(salida)
        ])

    proceso = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Si hubo error (ej. codec NVENC incompatibilidad temporal de resolución), reintentar con CPU ultrafast
    if proceso.returncode != 0:
        comando_fallback = list(comando)
        # Sustituir argumentos de codec por libx264 ultrafast
        indices_eliminar = []
        for idx, arg in enumerate(comando_fallback):
            if arg in ["-c:v", "-preset", "-cq", "-crf"]:
                indices_eliminar.extend([idx, idx + 1])

        comando_limpio = [arg for idx, arg in enumerate(comando_fallback) if idx not in indices_eliminar]
        # Insertar codec cpu antes de la ruta final de salida
        posicion_insercion = len(comando_limpio) - 1
        comando_limpio[posicion_insercion:posicion_insercion] = [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22"
        ]

        proceso_cpu = subprocess.run(comando_limpio, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proceso_cpu.returncode != 0:
            raise RuntimeError(f"Error al renderizar Short con FFmpeg: {proceso_cpu.stderr.strip()}")

    return str(salida.resolve())


