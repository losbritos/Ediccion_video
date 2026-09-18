"""
Pruebas unitarias para el módulo analizador_audio.py.
Valida la detección de FFmpeg, el cálculo de decibelios (dBFS),
la detección de silencios y el cálculo de segmentos activos.
"""

from pathlib import Path
import sys
import tempfile
import numpy as np
import pytest
from scipy.io import wavfile

# Agregar la ruta del backend al path de ejecución
RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from modulos.analizador_audio import (  # noqa: E402
    obtener_ruta_ejecutable_ffmpeg,
    calcular_energia_dbfs,
    detectar_intervalos_silencio,
    calcular_segmentos_activos,
    extraer_pista_audio
)


def test_obtener_ruta_ejecutable_ffmpeg_valido():
    """
    Verifica que el ejecutable de FFmpeg sea localizado en el sistema.
    """
    ruta_ffmpeg = obtener_ruta_ejecutable_ffmpeg()
    assert ruta_ffmpeg is not None
    assert Path(ruta_ffmpeg).exists()


def test_calcular_energia_dbfs_silencio_absoluto():
    """
    Un arreglo de muestras en cero debe arrojar el nivel mínimo de energía (-100 dBFS).
    """
    muestras_cero = np.zeros(1600, dtype=np.int16)
    db = calcular_energia_dbfs(muestras_cero)
    assert db == -100.0


def test_calcular_energia_dbfs_seno_fuerte():
    """
    Una onda senoidal de amplitud máxima debe tener una energía alta (cercana a -3 dBFS).
    """
    tiempo = np.linspace(0, 1, 16000, endpoint=False)
    # Tono de 440 Hz a amplitud completa
    onda_seno = (np.sin(2 * np.pi * 440 * tiempo) * 32767).astype(np.int16)
    db = calcular_energia_dbfs(onda_seno)
    assert -6.0 < db < 0.0


def test_deteccion_silencios_con_audio_sintetico():
    """
    Crea un audio sintético de 3 segundos (1s sonido, 1s silencio, 1s sonido)
    y verifica que el intervalo de silencio entre 1.0 y 2.0 segundos sea detectado.
    """
    tasa_muestreo = 16000
    duracion_segmento = 1.0  # 1 segundo cada bloque
    num_muestras = int(tasa_muestreo * duracion_segmento)

    tiempo = np.linspace(0, duracion_segmento, num_muestras, endpoint=False)
    tono = (np.sin(2 * np.pi * 440 * tiempo) * 20000).astype(np.int16)
    silencio = np.zeros(num_muestras, dtype=np.int16)

    # Concatenar: Sonido (0-1s) + Silencio (1-2s) + Sonido (2-3s)
    audio_completo = np.concatenate([tono, silencio, tono])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        ruta_temporal = temp_wav.name
        wavfile.write(ruta_temporal, tasa_muestreo, audio_completo)

    try:
        silencios = detectar_intervalos_silencio(
            ruta_temporal,
            umbral_db=-30.0,
            duracion_minima_segundos=0.5
        )

        assert len(silencios) == 1
        inicio_silencio, fin_silencio = silencios[0]

        # Tolerancia de +- 0.1s en la detección por tamaño de ventana
        assert abs(inicio_silencio - 1.0) < 0.1
        assert abs(fin_silencio - 2.0) < 0.1
    finally:
        # Limpieza rigurosa de archivos temporales (Skill normas-codigo)
        if Path(ruta_temporal).exists():
            Path(ruta_temporal).unlink()


def test_calcular_segmentos_activos_invierte_correctamente():
    """
    Verifica que calcular_segmentos_activos genere los fragmentos con voz/acción
    dejando fuera el intervalo de pausa.
    """
    duracion_total = 10.0
    silencios = [(4.0, 6.0)]  # Silencio de 2 segundos a mitad del video

    segmentos = calcular_segmentos_activos(
        duracion_total,
        silencios,
        margen_segundos=0.1
    )

    assert len(segmentos) == 2
    # Primer segmento: desde 0 hasta el inicio del silencio + margen (4.1s)
    assert segmentos[0][0] == 0.0
    assert abs(segmentos[0][1] - 4.1) < 0.05

    # Segundo segmento: desde el fin del silencio - margen (5.9s) hasta el final (10.0s)
    assert abs(segmentos[1][0] - 5.9) < 0.05
    assert segmentos[1][1] == 10.0


def test_extraer_pista_audio_archivo_inexistente_lanza_error():
    """
    Verifica que extraer_pista_audio lance FileNotFoundError si el archivo origen no existe.
    """
    with pytest.raises(FileNotFoundError):
        extraer_pista_audio("video_que_no_existe_12345.mp4", "salida.wav")
