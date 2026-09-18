"""
Módulo de análisis visual y visión por computadora con OpenCV.
Permite muestrear fotogramas clave, medir la intensidad de movimiento en pantalla,
calcular la "Puntuación de Atención" cruzando audio y video, y aplicar zooms dinámicos.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple
import cv2
import numpy as np

from modulos.analizador_audio import obtener_ruta_ejecutable_ffmpeg


def analizar_movimiento_video(
    ruta_video: str,
    fps_muestreo: float = 3.0,
    resolucion_analisis: Tuple[int, int] = (320, 180)
) -> List[Dict[str, float]]:
    """
    Analiza la intensidad de movimiento inter-fotograma a lo largo del video utilizando OpenCV.
    Aplica una resolución reducida y una tasa de muestreo baja (ej. 3 fps) para máxima velocidad.

    Args:
        ruta_video: Ruta al archivo de video de entrada.
        fps_muestreo: Cantidad de fotogramas por segundo a analizar.
        resolucion_analisis: (ancho, alto) para redimensionar durante el análisis.

    Returns:
        Lista de diccionarios con la marca de tiempo y la puntuación de movimiento (0 a 100):
        [
            {"tiempo": 0.33, "puntuacion_movimiento": 12.4},
            {"tiempo": 0.66, "puntuacion_movimiento": 84.1},
            ...
        ]
    """
    archivo_video = Path(ruta_video)
    if not archivo_video.exists():
        raise FileNotFoundError(f"Video no encontrado: {ruta_video}")

    captura = cv2.VideoCapture(str(archivo_video))
    if not captura.isOpened():
        raise RuntimeError(f"No se pudo abrir el video con OpenCV: {ruta_video}")

    fps_original = captura.get(cv2.CAP_PROP_FPS)
    if fps_original <= 0:
        fps_original = 30.0

    salto_fotogramas = max(1, int(round(fps_original / fps_muestreo)))
    ancho_analisis, alto_analisis = resolucion_analisis

    fotograma_previo_gris = None
    resultados_movimiento: List[Dict[str, float]] = []
    numero_fotograma = 0

    while True:
        exito, fotograma = captura.read()
        if not exito:
            break

        if numero_fotograma % salto_fotogramas == 0:
            tiempo_actual = round(numero_fotograma / fps_original, 3)

            # Redimensionar y convertir a escala de grises
            fotograma_pequeno = cv2.resize(fotograma, (ancho_analisis, alto_analisis), interpolation=cv2.INTER_AREA)
            fotograma_gris = cv2.cvtColor(fotograma_pequeno, cv2.COLOR_BGR2GRAY)
            fotograma_gris = cv2.GaussianBlur(fotograma_gris, (9, 9), 0)

            if fotograma_previo_gris is not None:
                # Diferencia absoluta entre fotogramas consecutivos
                diferencia = cv2.absdiff(fotograma_gris, fotograma_previo_gris)
                _, mascara_movimiento = cv2.threshold(diferencia, 20, 255, cv2.THRESH_BINARY)

                # Porcentaje de píxeles en movimiento sobre el total de la pantalla
                pixeles_movimiento = np.count_nonzero(mascara_movimiento)
                total_pixeles = ancho_analisis * alto_analisis
                fraccion_movimiento = pixeles_movimiento / total_pixeles

                # Normalizar a escala de 0 a 100
                puntuacion = min(100.0, fraccion_movimiento * 250.0)

                resultados_movimiento.append({
                    "tiempo": tiempo_actual,
                    "puntuacion_movimiento": round(float(puntuacion), 1)
                })

            fotograma_previo_gris = fotograma_gris

        numero_fotograma += 1

    captura.release()
    return resultados_movimiento


def calcular_puntuacion_atencion(
    muestras_movimiento: List[Dict[str, float]],
    picos_audio: List[Dict[str, float]],
    duracion_total: float,
    tamano_bloque_segundos: float = 1.0,
    peso_audio: float = 0.55,
    peso_movimiento: float = 0.45
) -> List[Dict[str, Any]]:
    """
    Cruza los datos de movimiento visual y picos de audio para calcular una "Puntuación de Atención"
    unificada por cada intervalo temporal del video.

    Args:
        muestras_movimiento: Salida de analizar_movimiento_video().
        picos_audio: Salida de detectar_picos_energia().
        duracion_total: Duración total del video en segundos.
        tamano_bloque_segundos: Tamaño de cada ventana de evaluación.
        peso_audio: Ponderación de la pista sonora (0.0 a 1.0).
        peso_movimiento: Ponderación de la acción en pantalla (0.0 a 1.0).

    Returns:
        Lista de bloques temporales ordenados con su puntuación de atención:
        [
            {
                "inicio": 14.0,
                "fin": 15.0,
                "puntuacion_atencion": 91.2,
                "es_momento_cumbre": True
            }
        ]
    """
    if duracion_total <= 0:
        return []

    bloques: List[Dict[str, Any]] = []
    tiempo_actual = 0.0

    while tiempo_actual < duracion_total:
        tiempo_fin = min(duracion_total, tiempo_actual + tamano_bloque_segundos)

        # 1. Puntuación promedio de movimiento en este intervalo
        movimientos_en_intervalo = [
            m["puntuacion_movimiento"] for m in muestras_movimiento
            if tiempo_actual <= m["tiempo"] < tiempo_fin
        ]
        score_movimiento = float(np.mean(movimientos_en_intervalo)) if movimientos_en_intervalo else 10.0

        # 2. Puntuación de audio en este intervalo
        score_audio = 10.0
        for pico in picos_audio:
            # Si el pico de audio se solapa con el bloque
            if not (pico["fin"] < tiempo_actual or pico["inicio"] > tiempo_fin):
                score_audio = max(score_audio, pico.get("puntuacion_energia", 50.0))

        # Puntuación ponderada combinada
        score_atencion = (score_audio * peso_audio) + (score_movimiento * peso_movimiento)
        score_atencion = round(min(100.0, max(0.0, score_atencion)), 1)

        bloques.append({
            "inicio": round(tiempo_actual, 3),
            "fin": round(tiempo_fin, 3),
            "puntuacion_atencion": score_atencion,
            "puntuacion_audio": round(score_audio, 1),
            "puntuacion_movimiento": round(score_movimiento, 1),
            "es_momento_cumbre": score_atencion >= 70.0
        })

        tiempo_actual += tamano_bloque_segundos

    return bloques


def aplicar_zoom_dinamico_a_clip(
    ruta_video_origen: str,
    tiempo_inicio: float,
    duracion: float,
    ruta_salida: str,
    factor_zoom: float = 1.15
) -> str:
    """
    Aplica un zoom suave hacia el centro en un fragmento de video específico mediante FFmpeg.

    Args:
        ruta_video_origen: Video origen.
        tiempo_inicio: Segundo de inicio del corte a procesar.
        duracion: Duración en segundos del fragmento.
        ruta_salida: Ruta donde guardar el clip con zoom.
        factor_zoom: Factor de acercamiento (ej. 1.15 = 115%).

    Returns:
        Ruta absoluta al clip procesado con zoom.
    """
    import subprocess

    salida = Path(ruta_salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    ejecutable = obtener_ruta_ejecutable_ffmpeg()

    # Filtro pan & zoom suave hacia el centro usando crop y scale
    filtro_zoom = (
        f"scale=iw*{factor_zoom}:ih*{factor_zoom},"
        f"crop=iw/{factor_zoom}:ih/{factor_zoom}:(in_w-out_w)/2:(in_h-out_h)/2"
    )

    comando = [
        ejecutable, "-y",
        "-ss", f"{tiempo_inicio:.3f}",
        "-t", f"{duracion:.3f}",
        "-i", str(ruta_video_origen),
        "-vf", filtro_zoom,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        str(salida)
    ]

    proceso = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proceso.returncode != 0:
        raise RuntimeError(f"Error al aplicar zoom con FFmpeg: {proceso.stderr.strip()}")

    return str(salida.resolve())
