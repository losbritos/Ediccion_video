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


def agrupar_momentos_cumbre(
    bloques_atencion: List[Dict[str, Any]],
    duracion_total: float,
    cantidad_shorts: int = 3,
    duracion_short_segundos: float = 35.0,
    distancia_minima_segundos: float = 45.0
) -> List[Dict[str, Any]]:
    """
    Identifica los momentos cumbre más destacados a partir de los bloques de atención,
    garantizando que no se solapen y extrayendo ventanas de tiempo con contexto natural
    (antes, durante y después de la jugada clave).

    Args:
        bloques_atencion: Lista de bloques temporales con 'puntuacion_atencion'.
        duracion_total: Duración total del video original en segundos.
        cantidad_shorts: Número de momentos/shorts deseados.
        duracion_short_segundos: Duración objetivo de cada short.
        distancia_minima_segundos: Separación mínima entre clímax de diferentes shorts.

    Returns:
        Lista de especificaciones de shorts ordenados cronológicamente:
        [
            {
                "indice": 1,
                "inicio": 120.0,
                "fin": 155.0,
                "duracion": 35.0,
                "puntuacion_atencion": 89.4,
                "tiempo_climax": 134.0,
                "descripcion": "Short 1: Minuto 02:00 (Puntaje: 89.4)"
            }
        ]
    """
    if not bloques_atencion or duracion_total <= 0 or cantidad_shorts <= 0:
        return []

    # Si el video completo es menor o igual a la duración del short, devolver todo el video
    if duracion_total <= duracion_short_segundos:
        return [{
            "indice": 1,
            "inicio": 0.0,
            "fin": round(duracion_total, 2),
            "duracion": round(duracion_total, 2),
            "puntuacion_atencion": round(float(np.mean([b["puntuacion_atencion"] for b in bloques_atencion])), 1),
            "tiempo_climax": round(duracion_total / 2.0, 2),
            "descripcion": "Short 1: Video completo"
        }]

    # Ordenar bloques candidatos por puntuación de atención de mayor a menor
    candidatos_ordenados = sorted(
        bloques_atencion,
        key=lambda b: b.get("puntuacion_atencion", 0.0),
        reverse=True
    )

    momentos_seleccionados: List[Dict[str, Any]] = []

    for bloque in candidatos_ordenados:
        tiempo_climax = (bloque["inicio"] + bloque["fin"]) / 2.0

        # Verificar distancia mínima con los clímax previamente seleccionados
        separacion_suficiente = True
        for sel in momentos_seleccionados:
            if abs(tiempo_climax - sel["tiempo_climax"]) < distancia_minima_segundos:
                separacion_suficiente = False
                break

        if not separacion_suficiente:
            continue

        # Calcular ventana de tiempo alrededor del clímax (40% antes para contexto y 60% jugada/reacción)
        tiempo_previo = duracion_short_segundos * 0.40
        inicio_ventana = max(0.0, tiempo_climax - tiempo_previo)
        fin_ventana = min(duracion_total, inicio_ventana + duracion_short_segundos)

        # Si topa con el final del metraje, reajustar hacia atrás
        if fin_ventana >= duracion_total:
            inicio_ventana = max(0.0, duracion_total - duracion_short_segundos)
            fin_ventana = duracion_total

        # Comprobar si solapa directamente con alguna ventana ya elegida
        solapamiento = False
        for sel in momentos_seleccionados:
            if not (fin_ventana <= sel["inicio"] or inicio_ventana >= sel["fin"]):
                solapamiento = True
                break

        if solapamiento:
            continue

        momentos_seleccionados.append({
            "inicio": round(inicio_ventana, 2),
            "fin": round(fin_ventana, 2),
            "duracion": round(fin_ventana - inicio_ventana, 2),
            "puntuacion_atencion": bloque.get("puntuacion_atencion", 50.0),
            "tiempo_climax": round(tiempo_climax, 2)
        })

        if len(momentos_seleccionados) >= cantidad_shorts:
            break

    # Si por restricciones de distancia no se cubrió la cantidad deseada, rellenar de forma equitativa
    if len(momentos_seleccionados) < cantidad_shorts:
        intervalo_paso = duracion_total / (cantidad_shorts + 1)
        for i in range(1, cantidad_shorts + 1):
            if len(momentos_seleccionados) >= cantidad_shorts:
                break
            t_centro = i * intervalo_paso
            t_ini = max(0.0, t_centro - (duracion_short_segundos / 2.0))
            t_fin = min(duracion_total, t_ini + duracion_short_segundos)

            # Verificar solapamiento
            if not any(not (t_fin <= s["inicio"] or t_ini >= s["fin"]) for s in momentos_seleccionados):
                momentos_seleccionados.append({
                    "inicio": round(t_ini, 2),
                    "fin": round(t_fin, 2),
                    "duracion": round(t_fin - t_ini, 2),
                    "puntuacion_atencion": 60.0,
                    "tiempo_climax": round(t_centro, 2)
                })

    # Ordenar cronológicamente por tiempo de inicio para orden natural en la partida
    momentos_seleccionados.sort(key=lambda m: m["inicio"])

    # Asignar índices y descripciones limpias
    for idx, item in enumerate(momentos_seleccionados, start=1):
        item["indice"] = idx
        minutos = int(item["inicio"] // 60)
        segundos = int(item["inicio"] % 60)
        item["descripcion"] = f"Short {idx}: Minuto {minutos:02d}:{segundos:02d} (Puntaje: {item['puntuacion_atencion']})"

    return momentos_seleccionados

