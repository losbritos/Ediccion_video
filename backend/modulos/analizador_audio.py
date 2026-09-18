"""
Módulo de análisis de audio para el editor automático de video.
Permite extraer la pista de audio de un video, calcular niveles de decibelios (dB)
y detectar automáticamente pausas y silencios.
"""

import math
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from scipy.io import wavfile


def obtener_ruta_ejecutable_ffmpeg() -> str:
    """
    Localiza el ejecutable de FFmpeg en el sistema o en las rutas conocidas de WinGet.

    Returns:
        Ruta absoluta al binario de FFmpeg.

    Raises:
        FileNotFoundError: Si no se encuentra FFmpeg instalado en el equipo.
    """
    # 1. Buscar en PATH del sistema
    ruta_en_path = shutil.which("ffmpeg")
    if ruta_en_path:
        return ruta_en_path

    # 2. Rutas conocidas de instalación local en Windows
    rutas_candidatas = [
        Path(r"C:\Users\canha\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    ]

    for ruta in rutas_candidatas:
        if ruta.exists():
            return str(ruta)

    raise FileNotFoundError(
        "No se localizó el ejecutable de FFmpeg en el sistema. Asegúrese de que esté instalado."
    )


def extraer_pista_audio(
    ruta_video: str,
    ruta_audio_salida: str,
    frecuencia_muestreo: int = 16000
) -> str:
    """
    Extrae la pista de audio de un archivo de video y la convierte a formato WAV PCM mono.

    Args:
        ruta_video: Ruta al archivo de video de entrada (.mp4, .mkv, .mov).
        ruta_audio_salida: Ruta donde se guardará el archivo de audio extraído (.wav).
        frecuencia_muestreo: Frecuencia de muestreo en Hz (por defecto 16000 Hz, ideal para análisis).

    Returns:
        Ruta absoluta al archivo de audio generado.

    Raises:
        FileNotFoundError: Si el video origen no existe.
        RuntimeError: Si FFmpeg falla al procesar el archivo.
    """
    archivo_video = Path(ruta_video)
    if not archivo_video.exists():
        raise FileNotFoundError(f"El archivo de video no existe: {ruta_video}")

    archivo_salida = Path(ruta_audio_salida)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    ejecutable_ffmpeg = obtener_ruta_ejecutable_ffmpeg()

    # Comando FFmpeg optimizado: extracción rápida mono 16kHz PCM
    comando = [
        ejecutable_ffmpeg,
        "-y",                     # Sobrescribir archivo de salida si ya existe
        "-i", str(archivo_video), # Archivo origen
        "-vn",                    # Desactivar procesamiento de video
        "-ac", "1",               # Convertir a 1 canal (mono)
        "-ar", str(frecuencia_muestreo), # Tasa de muestreo
        "-acodec", "pcm_s16le",   # Códec PCM de 16 bits sin pérdida
        str(archivo_salida)
    ]

    proceso = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if proceso.returncode != 0:
        raise RuntimeError(
            f"Error al extraer audio con FFmpeg: {proceso.stderr.strip()}"
        )

    return str(archivo_salida.resolve())


def calcular_energia_dbfs(muestras_audio: np.ndarray) -> float:
    """
    Calcula la energía de un bloque de audio en decibelios relativos a escala completa (dBFS).

    Args:
        muestras_audio: Arreglo unidimensional de muestras numéricas de audio.

    Returns:
        Valor en dBFS (entre -100.0 y 0.0 dB).
    """
    if len(muestras_audio) == 0:
        return -100.0

    # Valor cuadrático medio (RMS)
    rms = np.sqrt(np.mean(muestras_audio.astype(np.float64) ** 2))
    if rms <= 1e-7:
        return -100.0

    # Normalización para audio de 16 bits (valor pico 32768)
    nivel_db = 20 * math.log10(rms / 32768.0)
    return max(nivel_db, -100.0)


def detectar_intervalos_silencio(
    ruta_audio: str,
    umbral_db: float = -30.0,
    duracion_minima_segundos: float = 0.4,
    tamano_ventana_segundos: float = 0.05
) -> List[Tuple[float, float]]:
    """
    Analiza un archivo de audio WAV e identifica los intervalos temporales considerados silencio.

    Args:
        ruta_audio: Ruta al archivo WAV mono a analizar.
        umbral_db: Umbral en decibelios por debajo del cual se considera silencio (ej. -30 dB).
        duracion_minima_segundos: Duración mínima continua para registrar una pausa como corte.
        tamano_ventana_segundos: Tamaño de la ventana de análisis en segundos.

    Returns:
        Lista de tuplas (tiempo_inicio, tiempo_fin) en segundos con los silencios detectados.
    """
    tasa_muestreo, datos = wavfile.read(ruta_audio)

    # Asegurar que sea arreglo 1D (mono)
    if datos.ndim > 1:
        datos = datos[:, 0]

    muestras_por_ventana = int(tasa_muestreo * tamano_ventana_segundos)
    if muestras_por_ventana <= 0:
        muestras_por_ventana = 1

    total_muestras = len(datos)
    intervalos_silencio: List[Tuple[float, float]] = []

    en_silencio = False
    tiempo_inicio_silencio = 0.0

    for indice in range(0, total_muestras, muestras_por_ventana):
        bloque = datos[indice : indice + muestras_por_ventana]
        tiempo_actual = indice / tasa_muestreo
        volumen_db = calcular_energia_dbfs(bloque)

        es_silencio_actual = volumen_db < umbral_db

        if es_silencio_actual and not en_silencio:
            # Comienza un nuevo intervalo de silencio
            en_silencio = True
            tiempo_inicio_silencio = tiempo_actual
        elif not es_silencio_actual and en_silencio:
            # Termina el intervalo de silencio
            en_silencio = False
            duracion_silencio = tiempo_actual - tiempo_inicio_silencio
            if duracion_silencio >= duracion_minima_segundos:
                intervalos_silencio.append((tiempo_inicio_silencio, tiempo_actual))

    # Verificar si el archivo finaliza en silencio
    if en_silencio:
        tiempo_final = total_muestras / tasa_muestreo
        duracion_silencio = tiempo_final - tiempo_inicio_silencio
        if duracion_silencio >= duracion_minima_segundos:
            intervalos_silencio.append((tiempo_inicio_silencio, tiempo_final))

    return intervalos_silencio


def calcular_segmentos_activos(
    duracion_total: float,
    silencios: List[Tuple[float, float]],
    margen_segundos: float = 0.1
) -> List[Tuple[float, float]]:
    """
    Invierte la lista de silencios para obtener los segmentos activos de contenido
    (donde hay voz o sonido relevante), aplicando un margen de suavizado al inicio y al final.

    Args:
        duracion_total: Duración total del video/audio en segundos.
        silencios: Lista de intervalos (inicio, fin) de pausas o silencios detectados.
        margen_segundos: Margen en segundos para no cortar palabras o respiraciones abruptamente.

    Returns:
        Lista de intervalos (inicio, fin) de los fragmentos que deben conservarse.
    """
    if duracion_total <= 0:
        return []

    if not silencios:
        return [(0.0, duracion_total)]

    segmentos_activos: List[Tuple[float, float]] = []
    cursor_tiempo = 0.0

    for silencio_inicio, silencio_fin in silencios:
        inicio_activo = cursor_tiempo
        # Reducir el corte con el margen de seguridad
        fin_activo = min(duracion_total, silencio_inicio + margen_segundos)

        if fin_activo - inicio_activo > 0.05:
            segmentos_activos.append((round(inicio_activo, 3), round(fin_activo, 3)))

        # Actualizar cursor tras el silencio descontando el margen
        cursor_tiempo = max(0.0, silencio_fin - margen_segundos)

    # Segmento final tras el último silencio
    if cursor_tiempo < duracion_total:
        if duracion_total - cursor_tiempo > 0.05:
            segmentos_activos.append((round(cursor_tiempo, 3), round(duracion_total, 3)))

    return segmentos_activos


def detectar_picos_energia(
    ruta_audio: str,
    umbral_desviacion: float = 1.8,
    duracion_ventana_segundos: float = 0.25,
    piso_minimo_db: float = -22.0
) -> List[Dict[str, float]]:
    """
    Identifica momentos de alto impacto emocional o volumen (gritos, risas, explosiones,
    reacciones intensas) calculando la desviación de energía RMS respecto a la media de la pista.

    Args:
        ruta_audio: Ruta al archivo WAV mono a analizar.
        umbral_desviacion: Factor multiplicador sobre la desviación estándar (ej. 1.8x por encima de la media).
        duracion_ventana_segundos: Duración de cada intervalo de muestreo de energía.
        piso_minimo_db: Umbral absoluto mínimo en decibelios para evitar falsos positivos en videos muy silenciosos.

    Returns:
        Lista de diccionarios con la información de cada pico:
        [
            {
                "inicio": 12.5,
                "fin": 13.75,
                "duracion": 1.25,
                "volumen_pico_db": -8.4,
                "puntuacion_energia": 88.5
            }
        ]
    """
    tasa_muestreo, datos = wavfile.read(ruta_audio)

    if datos.ndim > 1:
        datos = datos[:, 0]

    muestras_por_ventana = int(tasa_muestreo * duracion_ventana_segundos)
    if muestras_por_ventana <= 0:
        muestras_por_ventana = 1

    total_muestras = len(datos)
    if total_muestras == 0:
        return []

    # Calcular energía dBFS de cada ventana
    valores_db: List[float] = []
    tiempos: List[float] = []

    for indice in range(0, total_muestras, muestras_por_ventana):
        bloque = datos[indice : indice + muestras_por_ventana]
        tiempo_actual = indice / tasa_muestreo
        db = calcular_energia_dbfs(bloque)
        valores_db.append(db)
        tiempos.append(tiempo_actual)

    # Filtrar silencios profundos para calcular una media y desviación representativa de la voz
    valores_voz = [v for v in valores_db if v > -45.0]
    if not valores_voz:
        return []

    media_db = float(np.mean(valores_voz))
    desviacion_db = float(np.std(valores_voz))

    # Umbral dinámico combinado con el piso mínimo absoluto
    umbral_corte = max(media_db + (desviacion_db * umbral_desviacion), piso_minimo_db)

    picos_detectados: List[Dict[str, float]] = []
    en_pico = False
    tiempo_inicio_pico = 0.0
    volumen_maximo_pico = -100.0

    for i, (tiempo, db) in enumerate(zip(tiempos, valores_db)):
        es_pico = db >= umbral_corte

        if es_pico and not en_pico:
            en_pico = True
            tiempo_inicio_pico = tiempo
            volumen_maximo_pico = db
        elif es_pico and en_pico:
            if db > volumen_maximo_pico:
                volumen_maximo_pico = db
        elif not es_pico and en_pico:
            en_pico = False
            duracion_pico = tiempo - tiempo_inicio_pico
            # Conservar picos con duración mínima relevante (al menos 0.2s)
            if duracion_pico >= 0.2:
                # Normalizar puntuación de 0 a 100 basada en proximidad a 0 dBFS
                puntuacion = min(100.0, max(10.0, (volumen_maximo_pico + 30.0) * (100.0 / 30.0)))
                picos_detectados.append({
                    "inicio": round(tiempo_inicio_pico, 3),
                    "fin": round(tiempo, 3),
                    "duracion": round(duracion_pico, 3),
                    "volumen_pico_db": round(volumen_maximo_pico, 2),
                    "puntuacion_energia": round(puntuacion, 1)
                })

    return picos_detectados

