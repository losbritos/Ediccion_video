"""
Módulo de montaje y edición de video.
Orquesta los cortes, concatenaciones y ensamblado final de clips utilizando FFmpeg nativo.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

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

