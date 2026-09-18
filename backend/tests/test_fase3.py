"""
Suite de pruebas unitarias para la Fase 3:
- Análisis de Movimiento con OpenCV
- Cálculo de la Puntuación de Atención (Attention Score)
- Aplicación de Zoom Dinámico con FFmpeg
"""

from pathlib import Path
import sys
import tempfile

RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from modulos.analizador_video import (  # noqa: E402
    analizar_movimiento_video,
    calcular_puntuacion_atencion,
    aplicar_zoom_dinamico_a_clip
)
from tests.test_motor_edicion import crear_video_sintetico_prueba  # noqa: E402


def test_analizar_movimiento_video_con_clip_sintetico():
    """
    Verifica que OpenCV lea correctamente un video sintético y extraiga puntuaciones de movimiento.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_p = Path(temp_dir)
        ruta_video = str(dir_p / "video_prueba.mp4")

        crear_video_sintetico_prueba(ruta_video, duracion_segundos=2)

        muestras = analizar_movimiento_video(ruta_video, fps_muestreo=4.0)
        assert len(muestras) > 0
        assert "tiempo" in muestras[0]
        assert "puntuacion_movimiento" in muestras[0]
        assert 0.0 <= muestras[0]["puntuacion_movimiento"] <= 100.0


def test_calcular_puntuacion_atencion_detecta_momentos_cumbre():
    """
    Verifica que el algoritmo ponderado asigne puntuación alta y marque 'es_momento_cumbre'
    en los intervalos donde coinciden picos de audio y movimiento.
    """
    muestras_movimiento = [
        {"tiempo": 0.5, "puntuacion_movimiento": 10.0},
        {"tiempo": 1.5, "puntuacion_movimiento": 85.0}, # Momento de alta acción
        {"tiempo": 2.5, "puntuacion_movimiento": 12.0}
    ]

    picos_audio = [
        {
            "inicio": 1.2,
            "fin": 1.8,
            "puntuacion_energia": 90.0 # Grito o disparo simultáneo
        }
    ]

    bloques = calcular_puntuacion_atencion(
        muestras_movimiento,
        picos_audio,
        duracion_total=3.0,
        tamano_bloque_segundos=1.0
    )

    assert len(bloques) == 3
    # El bloque entre 1.0s y 2.0s debe tener la puntuación más alta y ser momento cumbre
    bloque_pico = bloques[1]
    assert bloque_pico["puntuacion_atencion"] >= 75.0
    assert bloque_pico["es_momento_cumbre"] is True

    # Los bloques 0 y 2 no deben ser momentos cumbre
    assert bloques[0]["es_momento_cumbre"] is False
    assert bloques[2]["es_momento_cumbre"] is False


def test_aplicar_zoom_dinamico_a_clip():
    """
    Verifica que aplicar_zoom_dinamico_a_clip genere un clip con el efecto de escala.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_p = Path(temp_dir)
        ruta_origen = str(dir_p / "original.mp4")
        ruta_salida = str(dir_p / "con_zoom.mp4")

        crear_video_sintetico_prueba(ruta_origen, duracion_segundos=2)

        resultado = aplicar_zoom_dinamico_a_clip(
            ruta_video_origen=ruta_origen,
            tiempo_inicio=0.5,
            duracion=1.0,
            ruta_salida=ruta_salida,
            factor_zoom=1.20
        )

        assert Path(resultado).exists()
        assert Path(resultado).stat().st_size > 1000
