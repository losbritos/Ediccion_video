"""
Suite de pruebas unitarias para la Fase 2:
- IA Local y Transcripción (Faster-Whisper)
- Detección de Picos Emocionales y Energía
- Generación de Subtítulos SRT y ASS animados
- Mezcla y Audio Ducking con FFmpeg
"""

from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
import pytest
from scipy.io import wavfile

RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from modulos.analizador_audio import (  # noqa: E402
    obtener_ruta_ejecutable_ffmpeg,
    detectar_picos_energia
)
from modulos.transcriptor_ia import (  # noqa: E402
    detectar_dispositivo_optimo,
    TranscriptorLocal
)
from modulos.generador_subtitulos import (  # noqa: E402
    formatear_tiempo_srt,
    formatear_tiempo_ass,
    generar_subtitulos_srt,
    generar_subtitulos_ass_animados
)
from modulos.motor_edicion import aplicar_audio_ducking  # noqa: E402


def test_detectar_dispositivo_optimo():
    """
    Verifica que la función retorne 'cuda' o 'cpu' sin lanzar excepciones.
    """
    dispositivo = detectar_dispositivo_optimo()
    assert dispositivo in ["cuda", "cpu"]


def test_formateo_tiempos_subtitulos():
    """
    Verifica los conversores de tiempo para SRT y ASS.
    """
    # 75.456 segundos -> 00:01:15,456 en SRT
    srt_tiempo = formatear_tiempo_srt(75.456)
    assert srt_tiempo == "00:01:15,456"

    # 75.456 segundos -> 0:01:15.46 en ASS
    ass_tiempo = formatear_tiempo_ass(75.456)
    assert ass_tiempo == "0:01:15.46"


def test_generacion_archivo_srt():
    """
    Verifica que el generador SRT cree un archivo válido con la numeración y marcas esperadas.
    """
    segmentos = [
        {"inicio": 1.2, "fin": 3.5, "texto": "Hola a todos"},
        {"inicio": 4.0, "fin": 6.8, "texto": "Bienvenidos al directo"}
    ]

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as temp_srt:
        ruta_srt = temp_srt.name

    try:
        resultado = generar_subtitulos_srt(segmentos, ruta_srt)
        assert Path(resultado).exists()

        contenido = Path(resultado).read_text(encoding="utf-8")
        assert "1\n00:00:01,200 --> 00:00:03,500\nHola a todos" in contenido
        assert "2\n00:00:04,000 --> 00:00:06,800\nBienvenidos al directo" in contenido
    finally:
        if Path(ruta_srt).exists():
            Path(ruta_srt).unlink()


def test_generacion_archivo_ass_animado():
    """
    Verifica la generación del formato ASS con estilos Gaming y efectos de palabras.
    """
    segmentos = [
        {
            "inicio": 0.5,
            "fin": 2.0,
            "texto": "Disparo en la cabeza",
            "palabras": [
                {"palabra": "Disparo", "inicio": 0.5, "fin": 0.9, "probabilidad": 0.95},
                {"palabra": "en", "inicio": 0.9, "fin": 1.1, "probabilidad": 0.98},
                {"palabra": "la", "inicio": 1.1, "fin": 1.3, "probabilidad": 0.99},
                {"palabra": "cabeza", "inicio": 1.3, "fin": 2.0, "probabilidad": 0.97},
            ]
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as temp_ass:
        ruta_ass = temp_ass.name

    try:
        resultado = generar_subtitulos_ass_animados(segmentos, ruta_ass, color_primario_hex="#00E5FF")
        assert Path(resultado).exists()

        contenido = Path(resultado).read_text(encoding="utf-8")
        assert "[Script Info]" in contenido
        assert "Style: GamingSub" in contenido
        assert "Dialogue:" in contenido
        assert "Disparo en la cabeza" in contenido
    finally:
        if Path(ruta_ass).exists():
            Path(ruta_ass).unlink()


def test_deteccion_picos_energia_emocional():
    """
    Genera un audio con voz a volumen normal (-24 dB aprox) y un grito/pico súbito de 1 segundo (-3 dB),
    comprobando que el pico sea detectado con alta puntuación.
    """
    tasa = 16000
    # 2s tono suave (voz normal)
    t1 = np.linspace(0, 2, tasa * 2, endpoint=False)
    voz_normal = (np.sin(2 * np.pi * 300 * t1) * 3500).astype(np.int16)

    # 1s tono fuerte (grito / explosión)
    t2 = np.linspace(0, 1, tasa * 1, endpoint=False)
    grito = (np.sin(2 * np.pi * 700 * t2) * 30000).astype(np.int16)

    # 2s tono suave
    voz_final = (np.sin(2 * np.pi * 300 * t1) * 3500).astype(np.int16)

    audio_prueba = np.concatenate([voz_normal, grito, voz_final])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        ruta_wav = temp_wav.name
        wavfile.write(ruta_wav, tasa, audio_prueba)

    try:
        picos = detectar_picos_energia(ruta_wav, umbral_desviacion=1.5, piso_minimo_db=-18.0)
        assert len(picos) >= 1
        pico_detectado = picos[0]
        # El grito ocurre en el intervalo entre 2.0 y 3.0 segundos
        assert abs(pico_detectado["inicio"] - 2.0) < 0.3
        assert pico_detectado["puntuacion_energia"] > 70.0
    finally:
        if Path(ruta_wav).exists():
            Path(ruta_wav).unlink()


def test_audio_ducking_con_ffmpeg():
    """
    Verifica que aplicar_audio_ducking genere la mezcla con música de fondo atenuada.
    """
    ejecutable = obtener_ruta_ejecutable_ffmpeg()

    with tempfile.TemporaryDirectory() as temp_dir:
        dir_p = Path(temp_dir)
        ruta_voz = str(dir_p / "voz.wav")
        ruta_musica = str(dir_p / "musica.wav")
        ruta_salida = str(dir_p / "mezcla_ducking.wav")

        # Crear 3 segundos de pista de voz
        subprocess.run([
            ejecutable, "-y",
            "-f", "lavfi", "-i", "sine=frequency=300:duration=3",
            "-c:a", "pcm_s16le", ruta_voz
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Crear 3 segundos de pista de música
        subprocess.run([
            ejecutable, "-y",
            "-f", "lavfi", "-i", "sine=frequency=600:duration=3",
            "-c:a", "pcm_s16le", ruta_musica
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        resultado = aplicar_audio_ducking(
            ruta_video_o_audio_voz=ruta_voz,
            ruta_musica_fondo=ruta_musica,
            ruta_salida=ruta_salida,
            volumen_musica_base=0.3
        )

        assert Path(resultado).exists()
        assert Path(resultado).stat().st_size > 1000
