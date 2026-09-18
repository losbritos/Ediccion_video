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
) -> List[Dict[str, Any]]:
    """
    Analiza la intensidad de movimiento inter-fotograma, destellos de habilidades/combate
    y saturación cromática a lo largo del video utilizando OpenCV.
    Incluye filtros para descartar pantallas de muerte (escala de grises) y atenuar paneos de cámara.

    Args:
        ruta_video: Ruta al archivo de video de entrada.
        fps_muestreo: Cantidad de fotogramas por segundo a analizar.
        resolucion_analisis: (ancho, alto) para redimensionar durante el análisis.

    Returns:
        Lista de diccionarios con marcas de tiempo, puntuación de movimiento, estado de muerte y destellos:
        [
            {
                "tiempo": 12.33,
                "puntuacion_movimiento": 84.1,
                "es_pantalla_muerte": False,
                "destello_combate": 18.5
            },
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
    resultados_movimiento: List[Dict[str, Any]] = []
    numero_fotograma = 0

    while True:
        exito, fotograma = captura.read()
        if not exito:
            break

        if numero_fotograma % salto_fotogramas == 0:
            tiempo_actual = round(numero_fotograma / fps_original, 3)

            # Redimensionar para análisis rápido y eficiente
            fotograma_pequeno = cv2.resize(fotograma, (ancho_analisis, alto_analisis), interpolation=cv2.INTER_AREA)
            fotograma_gris = cv2.cvtColor(fotograma_pequeno, cv2.COLOR_BGR2GRAY)
            fotograma_gris = cv2.GaussianBlur(fotograma_gris, (9, 9), 0)

            # Analizar saturación cromática y brillo en espacio HSV
            fotograma_hsv = cv2.cvtColor(fotograma_pequeno, cv2.COLOR_BGR2HSV)
            canal_saturacion = fotograma_hsv[:, :, 1]
            canal_brillo = fotograma_hsv[:, :, 2]

            saturacion_media = float(np.mean(canal_saturacion))
            brillo_medio = float(np.mean(canal_brillo))

            # Filtro Anti-Muerte y Carga: en LoL y shooters, al morir la pantalla pasa a escala de grises
            es_pantalla_muerte = bool(saturacion_media < 28.0 and brillo_medio > 22.0)
            es_pantalla_negra_o_carga = bool(brillo_medio < 16.0)
            es_inactivo = es_pantalla_muerte or es_pantalla_negra_o_carga

            # Destellos de habilidades (ultimates, destello/flash, explosiones mágicas)
            pixeles_destello = int(np.count_nonzero(canal_brillo > 225))
            fraccion_destello = pixeles_destello / (ancho_analisis * alto_analisis)
            puntuacion_destello = min(100.0, fraccion_destello * 450.0)

            if fotograma_previo_gris is not None:
                # Diferencia absoluta entre fotogramas consecutivos
                diferencia = cv2.absdiff(fotograma_gris, fotograma_previo_gris)
                _, mascara_movimiento = cv2.threshold(diferencia, 20, 255, cv2.THRESH_BINARY)

                pixeles_movimiento = np.count_nonzero(mascara_movimiento)
                total_pixeles = ancho_analisis * alto_analisis
                fraccion_movimiento = pixeles_movimiento / total_pixeles

                puntuacion_base = min(100.0, fraccion_movimiento * 250.0)

                # Filtro Anti-Paneo: si toda la pantalla se mueve uniformemente (>85%) sin destello,
                # es solo el jugador moviendo el ratón por el mapa, no un combate real
                if fraccion_movimiento > 0.85 and puntuacion_destello < 6.0:
                    puntuacion_base *= 0.40

                puntuacion_total = puntuacion_base + (puntuacion_destello * 0.35)

                if es_inactivo:
                    puntuacion_total = 0.0

                puntuacion_total = min(100.0, max(0.0, puntuacion_total))

                resultados_movimiento.append({
                    "tiempo": tiempo_actual,
                    "puntuacion_movimiento": round(float(puntuacion_total), 1),
                    "es_pantalla_muerte": es_inactivo,
                    "destello_combate": round(float(puntuacion_destello), 1)
                })

            fotograma_previo_gris = fotograma_gris

        numero_fotograma += 1

    captura.release()
    return resultados_movimiento


def calcular_puntuacion_atencion(
    muestras_movimiento: List[Dict[str, Any]],
    picos_audio: List[Dict[str, float]],
    duracion_total: float,
    tamano_bloque_segundos: float = 1.0,
    peso_audio: float = 0.55,
    peso_movimiento: float = 0.45
) -> List[Dict[str, Any]]:
    """
    Cruza los datos de movimiento visual y picos de audio para calcular una "Puntuación de Atención"
    unificada por cada intervalo temporal del video.
    Detecta automáticamente si el video cuenta con voz o si es un gameplay sin locución,
    adaptando los pesos dinámicamente y descartando de inmediato las pantallas de muerte.

    Args:
        muestras_movimiento: Salida de analizar_movimiento_video().
        picos_audio: Salida de detectar_picos_energia().
        duracion_total: Duración total del video en segundos.
        tamano_bloque_segundos: Tamaño de cada ventana de evaluación.
        peso_audio: Ponderación predeterminada de la pista sonora.
        peso_movimiento: Ponderación predeterminada de la acción visual.

    Returns:
        Lista de bloques temporales ordenados con su puntuación de atención.
    """
    if duracion_total <= 0:
        return []

    # Autodetección de locución: ¿el video tiene voz por micrófono o es solo audio de juego/mudo?
    picos_relevantes = [p for p in picos_audio if p.get("puntuacion_energia", 0.0) >= 60.0]
    tiene_locucion = len(picos_relevantes) >= 2

    # Si no hay voz de micrófono, la acción visual y destellos toman el 90% del peso para destacar peleas
    peso_audio_efectivo = peso_audio if tiene_locucion else 0.10
    peso_movimiento_efectivo = peso_movimiento if tiene_locucion else 0.90

    bloques: List[Dict[str, Any]] = []
    tiempo_actual = 0.0

    while tiempo_actual < duracion_total:
        tiempo_fin = min(duracion_total, tiempo_actual + tamano_bloque_segundos)

        # 1. Puntuación promedio de movimiento en este intervalo
        muestras_en_intervalo = [
            m for m in muestras_movimiento
            if tiempo_actual <= m["tiempo"] < tiempo_fin
        ]

        # Verificar si hay fotogramas de muerte en este bloque
        esta_muerto_o_inactivo = any(m.get("es_pantalla_muerte", False) for m in muestras_en_intervalo)

        movimientos_en_intervalo = []
        for m in muestras_en_intervalo:
            p_mov = m["puntuacion_movimiento"]
            if m.get("es_paneo_camara", False):
                p_mov *= 0.40
            movimientos_en_intervalo.append(p_mov)

        score_movimiento = float(np.mean(movimientos_en_intervalo)) if movimientos_en_intervalo else 10.0

        # 2. Puntuación de audio en este intervalo
        score_audio = 10.0
        for pico in picos_audio:
            if not (pico["fin"] < tiempo_actual or pico["inicio"] > tiempo_fin):
                score_audio = max(score_audio, pico.get("puntuacion_energia", 50.0))

        if esta_muerto_o_inactivo:
            score_atencion = 0.0
            es_cumbre = False
        else:
            score_atencion = (score_audio * peso_audio_efectivo) + (score_movimiento * peso_movimiento_efectivo)
            score_atencion = round(min(100.0, max(0.0, score_atencion)), 1)
            umbral_cumbre = 65.0 if tiene_locucion else 48.0
            es_cumbre = score_atencion >= umbral_cumbre

        bloques.append({
            "inicio": round(tiempo_actual, 3),
            "fin": round(tiempo_fin, 3),
            "puntuacion_atencion": score_atencion,
            "puntuacion_audio": round(score_audio, 1),
            "puntuacion_movimiento": round(score_movimiento, 1),
            "es_pantalla_muerte": esta_muerto_o_inactivo,
            "es_momento_cumbre": es_cumbre
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
    distribuyendo los clips a lo largo de las distintas fases de la partida (inicio, mitad y final),
    descartando pantallas de muerte y asegurando ventanas de tiempo con contexto natural
    (antes, durante y después del clímax).

    Args:
        bloques_atencion: Lista de bloques temporales con 'puntuacion_atencion'.
        duracion_total: Duración total del video original en segundos.
        cantidad_shorts: Número de momentos/shorts deseados.
        duracion_short_segundos: Duración objetivo de cada short.
        distancia_minima_segundos: Separación mínima entre clímax de diferentes shorts.

    Returns:
        Lista de especificaciones de shorts ordenados cronológicamente.
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

    # Filtrar bloques con atención mayor a 0 (descartar pantallas de muerte y estáticas)
    bloques_validos = [b for b in bloques_atencion if b.get("puntuacion_atencion", 0.0) > 0.0]
    if not bloques_validos:
        bloques_validos = bloques_atencion

    momentos_seleccionados: List[Dict[str, Any]] = []

    def intervalo_solapa(t_ini: float, t_fin: float, lista_existentes: List[Dict[str, Any]]) -> bool:
        for ex in lista_existentes:
            if not (t_fin <= ex["inicio"] or t_ini >= ex["fin"]):
                return True
        return False

    def distancia_suficiente(t_climax: float, lista_existentes: List[Dict[str, Any]]) -> bool:
        for ex in lista_existentes:
            if abs(t_climax - ex["tiempo_climax"]) < distancia_minima_segundos:
                return False
        return True

    # 1. Partición por Fases de la Partida:
    # Divide el metraje en N fases para garantizar que los Shorts cubran toda la partida
    duracion_fase = duracion_total / cantidad_shorts

    for fase_idx in range(cantidad_shorts):
        fase_inicio = fase_idx * duracion_fase
        fase_fin = (fase_idx + 1) * duracion_fase

        bloques_fase = [
            b for b in bloques_validos
            if fase_inicio <= b["inicio"] < fase_fin
        ]

        if not bloques_fase:
            continue

        # Ordenar candidatos dentro de esta fase de mayor a menor atención
        candidatos_fase = sorted(bloques_fase, key=lambda b: b.get("puntuacion_atencion", 0.0), reverse=True)

        for mejor_bloque in candidatos_fase:
            tiempo_climax = (mejor_bloque["inicio"] + mejor_bloque["fin"]) / 2.0

            if not distancia_suficiente(tiempo_climax, momentos_seleccionados):
                continue

            tiempo_previo = duracion_short_segundos * 0.40
            inicio_ventana = max(0.0, tiempo_climax - tiempo_previo)
            fin_ventana = min(duracion_total, inicio_ventana + duracion_short_segundos)

            if fin_ventana >= duracion_total:
                inicio_ventana = max(0.0, duracion_total - duracion_short_segundos)
                fin_ventana = duracion_total

            if not intervalo_solapa(inicio_ventana, fin_ventana, momentos_seleccionados):
                momentos_seleccionados.append({
                    "inicio": round(inicio_ventana, 2),
                    "fin": round(fin_ventana, 2),
                    "duracion": round(fin_ventana - inicio_ventana, 2),
                    "puntuacion_atencion": mejor_bloque.get("puntuacion_atencion", 50.0),
                    "tiempo_climax": round(tiempo_climax, 2)
                })
                break  # Encontrado el mejor momento para esta fase

    # 2. Si alguna fase no tuvo momentos válidos, rellenar con los mejores bloques globales
    if len(momentos_seleccionados) < cantidad_shorts:
        candidatos_globales = sorted(bloques_validos, key=lambda b: b.get("puntuacion_atencion", 0.0), reverse=True)

        for bloque in candidatos_globales:
            if len(momentos_seleccionados) >= cantidad_shorts:
                break

            tiempo_climax = (bloque["inicio"] + bloque["fin"]) / 2.0

            if not distancia_suficiente(tiempo_climax, momentos_seleccionados):
                continue

            tiempo_previo = duracion_short_segundos * 0.40
            inicio_ventana = max(0.0, tiempo_climax - tiempo_previo)
            fin_ventana = min(duracion_total, inicio_ventana + duracion_short_segundos)

            if fin_ventana >= duracion_total:
                inicio_ventana = max(0.0, duracion_total - duracion_short_segundos)
                fin_ventana = duracion_total

            if not intervalo_solapa(inicio_ventana, fin_ventana, momentos_seleccionados):
                momentos_seleccionados.append({
                    "inicio": round(inicio_ventana, 2),
                    "fin": round(fin_ventana, 2),
                    "duracion": round(fin_ventana - inicio_ventana, 2),
                    "puntuacion_atencion": bloque.get("puntuacion_atencion", 50.0),
                    "tiempo_climax": round(tiempo_climax, 2)
                })

    # 3. Fallback equitativo si el video fue extremadamente estático
    if len(momentos_seleccionados) < cantidad_shorts:
        intervalo_paso = duracion_total / (cantidad_shorts + 1)
        for i in range(1, cantidad_shorts + 1):
            if len(momentos_seleccionados) >= cantidad_shorts:
                break
            t_centro = i * intervalo_paso
            t_ini = max(0.0, t_centro - (duracion_short_segundos / 2.0))
            t_fin = min(duracion_total, t_ini + duracion_short_segundos)

            if not intervalo_solapa(t_ini, t_fin, momentos_seleccionados):
                momentos_seleccionados.append({
                    "inicio": round(t_ini, 2),
                    "fin": round(t_fin, 2),
                    "duracion": round(t_fin - t_ini, 2),
                    "puntuacion_atencion": 55.0,
                    "tiempo_climax": round(t_centro, 2)
                })

    # Ordenar cronológicamente
    momentos_seleccionados.sort(key=lambda m: m["inicio"])

    nombres_fases = ["Fase Inicial / Líneas", "Mid Game / Objetivos", "Late Game / Pelea Final", "Combate Épico", "Victoria / Cierre"]

    for idx, item in enumerate(momentos_seleccionados, start=1):
        item["indice"] = idx
        minutos = int(item["inicio"] // 60)
        segundos = int(item["inicio"] % 60)
        fase_desc = nombres_fases[min(idx - 1, len(nombres_fases) - 1)]
        item["descripcion"] = f"Short {idx}: Minuto {minutos:02d}:{segundos:02d} ({fase_desc} - Score: {item['puntuacion_atencion']})"

    return momentos_seleccionados


