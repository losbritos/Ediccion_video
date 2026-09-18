"""
Módulo del Director de Montaje.
Orquesta y toma decisiones de edición contextuales combinando análisis de audio,
análisis de video, transcripción por IA y la plantilla de juego seleccionada.
"""

from pathlib import Path
import tempfile
from typing import Any, Callable, Dict, List, Optional
from scipy.io import wavfile

from modulos.analizador_audio import (
    extraer_pista_audio,
    detectar_intervalos_silencio,
    calcular_segmentos_activos,
    detectar_picos_energia
)
from modulos.analizador_video import (
    analizar_movimiento_video,
    calcular_puntuacion_atencion,
    agrupar_momentos_cumbre
)
from modulos.motor_edicion import (
    cortar_y_unir_segmentos,
    renderizar_short_con_subtitulos
)
from modulos.generador_subtitulos import generar_subtitulos_ass_animados
from modulos.transcriptor_ia import TranscriptorLocal
from modulos.gestor_plantillas import GestorPlantillas


class DirectorMontaje:
    """
    Motor inteligente de toma de decisiones para la edición y renderizado automático.
    """

    def __init__(self, gestor_plantillas: Optional[GestorPlantillas] = None) -> None:
        """
        Inicializa el Director de Montaje.
        """
        self.gestor_plantillas = gestor_plantillas or GestorPlantillas()

    def generar_guion_montaje(
        self,
        duracion_total: float,
        silencios: List[tuple],
        picos_audio: List[Dict[str, float]],
        muestras_movimiento: List[Dict[str, float]],
        plantilla: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcula la línea de tiempo de edición (guion de montaje) aplicando las reglas de la plantilla.

        Args:
            duracion_total: Duración completa del video original en segundos.
            silencios: Intervalos detectados de pausas.
            picos_audio: Momentos de alto volumen o emoción detectados.
            muestras_movimiento: Puntuaciones de acción visual de OpenCV.
            plantilla: Diccionario con la configuración del perfil seleccionado.

        Returns:
            Diccionario estructurado con el plan de montaje completo:
            - segmentos_conservar: [(inicio, fin), ...]
            - duracion_estimada: segundos
            - ahorro_tiempo_porcentaje: %
            - momentos_destacados: [...]
        """
        ajustes_audio = plantilla.get("ajustes_audio", {})
        margen = ajustes_audio.get("margen_conservacion_corte_segundos", 0.1)

        # 1. Calcular segmentos a conservar
        segmentos_activos = calcular_segmentos_activos(
            duracion_total=duracion_total,
            silencios=silencios,
            margen_segundos=margen
        )

        duracion_final = sum(fin - inicio for inicio, fin in segmentos_activos)
        ahorro = ((duracion_total - duracion_final) / duracion_total) * 100 if duracion_total > 0 else 0.0

        # 2. Evaluar Puntuación de Atención para detectar highlights
        bloques_atencion = calcular_puntuacion_atencion(
            muestras_movimiento=muestras_movimiento,
            picos_audio=picos_audio,
            duracion_total=duracion_total
        )
        momentos_cumbre = [b for b in bloques_atencion if b.get("es_momento_cumbre", False)]

        return {
            "id_plantilla": plantilla.get("id", "desconocida"),
            "nombre_plantilla": plantilla.get("nombre", "Plantilla"),
            "duracion_original": round(duracion_total, 2),
            "duracion_final_estimada": round(duracion_final, 2),
            "ahorro_tiempo_porcentaje": round(ahorro, 1),
            "cantidad_cortes": max(0, len(segmentos_activos) - 1),
            "segmentos_conservar": segmentos_activos,
            "momentos_cumbre": momentos_cumbre
        }

    def procesar_video_completo(
        self,
        ruta_video_entrada: str,
        ruta_video_salida: str,
        id_plantilla: str = "shooters_highlights",
        ajustes_personalizados: Optional[Dict[str, Any]] = None,
        callback_progreso: Optional[Callable[[int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Orquesta el ciclo completo de edición automática:
        1. Extracción y análisis de audio.
        2. Detección de silencios y picos.
        3. Análisis visual con OpenCV.
        4. Montaje y renderizado con FFmpeg.

        Args:
            ruta_video_entrada: Video a procesar.
            ruta_video_salida: Video final generado.
            id_plantilla: Perfil de juego ('shooters_highlights', 'gameplay_narrado', etc.).
            ajustes_personalizados: Sobrescritura opcional de umbrales.
            callback_progreso: Función (porcentaje, etapa, mensaje) para reportar avance en tiempo real.

        Returns:
            Diccionario con las métricas finales del video producido.
        """
        def reportar(pct: int, etapa: str, msg: str) -> None:
            if callback_progreso:
                callback_progreso(pct, etapa, msg)

        plantilla = self.gestor_plantillas.obtener_plantilla(id_plantilla)
        if ajustes_personalizados:
            # Mezclar ajustes personalizados
            plantilla = {**plantilla, **ajustes_personalizados}

        reportar(5, "inicio", f"Iniciando procesamiento con plantilla: {plantilla.get('nombre')}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            ruta_audio_temp = temp_wav.name

        try:
            # Paso 1: Extracción de audio
            reportar(15, "audio", "Extrayendo audio en alta fidelidad (16kHz mono)...")
            extraer_pista_audio(ruta_video_entrada, ruta_audio_temp)

            tasa, datos = wavfile.read(ruta_audio_temp)
            duracion_total = len(datos) / tasa

            # Paso 2: Análisis de Silencios y Picos
            reportar(30, "audio", "Analizando decibelios y detectando pausas...")
            cfg_audio = plantilla.get("ajustes_audio", {})
            umbral_db = cfg_audio.get("umbral_silencio_db", -28.0)
            dur_min = cfg_audio.get("duracion_minima_silencio_segundos", 0.35)

            silencios = detectar_intervalos_silencio(
                ruta_audio_temp,
                umbral_db=umbral_db,
                duracion_minima_segundos=dur_min
            )
            picos_audio = detectar_picos_energia(ruta_audio_temp)

            # Paso 3: Análisis Visual
            reportar(50, "vision", "Muestreando fotogramas con OpenCV para medir acción...")
            muestras_movimiento = analizar_movimiento_video(ruta_video_entrada, fps_muestreo=3.0)

            # Paso 4: Generación de Guion de Montaje
            reportar(70, "montaje", "Calculando 'Puntuación de Atención' y generando lista de cortes...")
            guion = self.generar_guion_montaje(
                duracion_total=duracion_total,
                silencios=silencios,
                picos_audio=picos_audio,
                muestras_movimiento=muestras_movimiento,
                plantilla=plantilla
            )

            # Paso 5: Renderizado con FFmpeg
            reportar(85, "render", "Renderizando video ensamblado con FFmpeg...")
            cortar_y_unir_segmentos(
                ruta_video_origen=ruta_video_entrada,
                segmentos_activos=guion["segmentos_conservar"],
                ruta_video_destino=ruta_video_salida
            )

            reportar(100, "completado", "¡Video editado y renderizado con éxito!")
            return guion

        finally:
            if Path(ruta_audio_temp).exists():
                Path(ruta_audio_temp).unlink()

    def procesar_generacion_shorts(
        self,
        ruta_video_entrada: str,
        directorio_salida: str,
        id_plantilla: str = "shooters_highlights",
        cantidad_shorts: int = 3,
        duracion_short_segundos: float = 35.0,
        formato_vertical: bool = True,
        incluir_subtitulos: bool = True,
        ajustes_personalizados: Optional[Dict[str, Any]] = None,
        callback_progreso: Optional[Callable[[int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Analiza el video completo de partida larga, localiza los momentos cumbre con mayor impacto
        (gritos/emoción + acción visual), y genera múltiples Shorts independientes con subtítulos
        incrustados por Whisper y opción de encuadre vertical 9:16.

        Args:
            ruta_video_entrada: Video fuente largo (ej. partida de 20-40 min).
            directorio_salida: Carpeta donde se guardarán los archivos MP4 de cada Short.
            id_plantilla: Perfil de juego ('shooters_highlights', etc.).
            cantidad_shorts: Cantidad de clips independientes a producir (ej. 3 a 5).
            duracion_short_segundos: Duración aproximada de cada short (ej. 30 a 50s).
            formato_vertical: True para exportar en lienzo 9:16 con fondo blur para TikTok/Shorts.
            incluir_subtitulos: Si es True, transcribe con Faster-Whisper e incrusta subtítulos.
            ajustes_personalizados: Parámetros opcionales para afinar umbrales.
            callback_progreso: Función (porcentaje, etapa, mensaje) para actualizar estado en vivo.

        Returns:
            Diccionario estructurado con la lista de shorts producidos y sus metadatos.
        """
        def reportar(pct: int, etapa: str, msg: str) -> None:
            if callback_progreso:
                callback_progreso(pct, etapa, msg)

        dir_salida = Path(directorio_salida)
        dir_salida.mkdir(parents=True, exist_ok=True)

        plantilla = self.gestor_plantillas.obtener_plantilla(id_plantilla)
        if ajustes_personalizados:
            plantilla = {**plantilla, **ajustes_personalizados}

        reportar(5, "inicio", f"Iniciando escaneo del metraje completo para extraer {cantidad_shorts} Shorts destacados...")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            ruta_audio_temp = temp_wav.name

        archivos_temporales: List[Path] = [Path(ruta_audio_temp)]

        try:
            # 1. Extracción y análisis de audio del metraje completo
            reportar(12, "audio", "Extrayendo audio para detección de jugadas y picos de voz...")
            extraer_pista_audio(ruta_video_entrada, ruta_audio_temp)

            tasa_muestreo, datos_audio = wavfile.read(ruta_audio_temp)
            duracion_total = len(datos_audio) / tasa_muestreo

            reportar(22, "audio", "Calculando decibelios y detectando momentos de gritos/reacción...")
            picos_audio = detectar_picos_energia(ruta_audio_temp)

            # 2. Análisis visual de movimiento con OpenCV
            reportar(35, "vision", "Muestreando fotogramas con OpenCV para medir intensidad visual...")
            muestras_movimiento = analizar_movimiento_video(ruta_video_entrada, fps_muestreo=2.5)

            # 3. Puntuación de Atención y selección de los mejores momentos no solapados
            reportar(48, "montaje", "Calculando 'Puntuación de Atención' y seleccionando los momentos cumbre...")
            bloques_atencion = calcular_puntuacion_atencion(
                muestras_movimiento=muestras_movimiento,
                picos_audio=picos_audio,
                duracion_total=duracion_total
            )

            momentos_cumbre = agrupar_momentos_cumbre(
                bloques_atencion=bloques_atencion,
                duracion_total=duracion_total,
                cantidad_shorts=cantidad_shorts,
                duracion_short_segundos=duracion_short_segundos,
                distancia_minima_segundos=max(30.0, duracion_short_segundos * 1.2)
            )

            if not momentos_cumbre:
                raise RuntimeError("No se detectaron momentos suficientes en el metraje analizado.")

            reportar(55, "montaje", f"Se seleccionaron {len(momentos_cumbre)} momentos cumbre para generar Shorts.")

            # 4. Transcripción con Faster-Whisper e incrustación de subtítulos por cada Short
            transcriptor = None
            if incluir_subtitulos:
                try:
                    reportar(58, "whisper", "Inicializando motor de Inteligencia Artificial Faster-Whisper...")
                    transcriptor = TranscriptorLocal(tamano_modelo="base")
                except Exception as error_ia:
                    reportar(59, "whisper", f"Aviso: Transcripción IA no disponible ({error_ia}). Renderizando sin subtítulos.")
                    transcriptor = None

            shorts_generados: List[Dict[str, Any]] = []
            total_momentos = len(momentos_cumbre)

            for idx, momento in enumerate(momentos_cumbre, start=1):
                inicio_corte = momento["inicio"]
                duracion_corte = momento["duracion"]
                fin_corte = momento["fin"]

                porcentaje_base = 60 + int((idx - 1) / total_momentos * 35)
                reportar(
                    porcentaje_base,
                    "render",
                    f"Procesando Short #{idx} de {total_momentos} (Minuto {int(inicio_corte // 60):02d}:{int(inicio_corte % 60):02d})..."
                )

                ruta_ass_short = None

                # Si los subtítulos están habilitados, transcribir el audio específico de este clip
                if transcriptor is not None:
                    reportar(
                        porcentaje_base + 2,
                        "whisper",
                        f"Transcribiendo diálogo y generando subtítulos animados para Short #{idx}..."
                    )
                    # Cortar el audio en memoria directamente
                    indice_muestra_inicio = int(inicio_corte * tasa_muestreo)
                    indice_muestra_fin = int(fin_corte * tasa_muestreo)
                    trozo_audio = datos_audio[indice_muestra_inicio:indice_muestra_fin]

                    ruta_audio_trozo = dir_salida / f"temp_audio_short_{idx}.wav"
                    archivos_temporales.append(ruta_audio_trozo)
                    wavfile.write(str(ruta_audio_trozo), tasa_muestreo, trozo_audio)

                    try:
                        segmentos_texto = transcriptor.transcribir_audio(
                            str(ruta_audio_trozo),
                            idioma="es",
                            con_marcas_palabra=True
                        )
                        ruta_ass = dir_salida / f"subtitulos_short_{idx}.ass"
                        archivos_temporales.append(ruta_ass)

                        generar_subtitulos_ass_animados(
                            segmentos_transcripcion=segmentos_texto,
                            ruta_salida_ass=str(ruta_ass),
                            color_primario_hex="#FFEA00",
                            color_borde_hex="#000000",
                            formato_vertical=formato_vertical
                        )
                        ruta_ass_short = str(ruta_ass)
                    except Exception as error_sub:
                        reportar(porcentaje_base + 3, "whisper", f"Aviso al transcribir Short #{idx}: {error_sub}")
                        ruta_ass_short = None

                # Renderizar el archivo final de este short
                nombre_archivo_short = f"short_{idx}_min_{int(inicio_corte // 60):02d}_{int(inicio_corte % 60):02d}.mp4"
                ruta_mp4_short = dir_salida / nombre_archivo_short

                renderizar_short_con_subtitulos(
                    ruta_video_origen=ruta_video_entrada,
                    tiempo_inicio=inicio_corte,
                    duracion=duracion_corte,
                    ruta_salida=str(ruta_mp4_short),
                    ruta_subtitulos_ass=ruta_ass_short,
                    formato_vertical=formato_vertical
                )

                minutos = int(inicio_corte // 60)
                segs = int(inicio_corte % 60)

                shorts_generados.append({
                    "indice": idx,
                    "nombre_archivo": nombre_archivo_short,
                    "ruta_archivo": str(ruta_mp4_short.resolve()),
                    "inicio": inicio_corte,
                    "fin": fin_corte,
                    "duracion": duracion_corte,
                    "puntuacion_atencion": momento["puntuacion_atencion"],
                    "tiempo_formateado": f"{minutos:02d}:{segs:02d}",
                    "descripcion": momento["descripcion"],
                    "formato": "9:16 Vertical" if formato_vertical else "16:9 Panorámico"
                })

            reportar(100, "completado", f"¡Completado! Se generaron {len(shorts_generados)} Shorts destacados con subtítulos.")

            return {
                "modo": "shorts",
                "duracion_original": round(duracion_total, 2),
                "cantidad_shorts": len(shorts_generados),
                "formato_vertical": formato_vertical,
                "shorts": shorts_generados
            }

        finally:
            # Limpieza exhaustiva de archivos temporales
            for temp_f in archivos_temporales:
                if temp_f.exists():
                    try:
                        temp_f.unlink()
                    except Exception:
                        pass
