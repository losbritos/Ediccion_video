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
    calcular_puntuacion_atencion
)
from modulos.motor_edicion import cortar_y_unir_segmentos
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
