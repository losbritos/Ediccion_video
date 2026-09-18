"""
Suite de pruebas unitarias para la Fase 4:
- Gestor de Plantillas (gestor_plantillas.py)
- Director de Montaje (director_montaje.py)
"""

from pathlib import Path
import sys
import tempfile

RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from modulos.gestor_plantillas import GestorPlantillas  # noqa: E402
from modulos.director_montaje import DirectorMontaje  # noqa: E402
from tests.test_motor_edicion import crear_video_sintetico_prueba  # noqa: E402


def test_gestor_plantillas_obtencion():
    """
    Verifica que el gestor cargue las plantillas y responda con los perfiles correctos.
    """
    gestor = GestorPlantillas()
    todas = gestor.listar_todas()
    assert len(todas) >= 3

    plantilla_shooters = gestor.obtener_plantilla("shooters_highlights")
    assert plantilla_shooters["id"] == "shooters_highlights"
    assert "ajustes_audio" in plantilla_shooters

    # Si se pide una inexistente, debe dar fallback seguro sin romperse
    plantilla_inexistente = gestor.obtener_plantilla("juego_desconocido_xyz")
    assert plantilla_inexistente is not None
    assert "ajustes_audio" in plantilla_inexistente


def test_director_montaje_generacion_guion():
    """
    Verifica que el Director de Montaje calcule métricas coherentes en el guion de edición.
    """
    director = DirectorMontaje()
    plantilla = director.gestor_plantillas.obtener_plantilla("shooters_highlights")

    duracion_total = 10.0
    silencios = [(3.0, 5.0)] # 2 segundos de pausa
    picos_audio = [{"inicio": 1.0, "fin": 2.0, "puntuacion_energia": 85.0}]
    muestras_movimiento = [{"tiempo": 1.5, "puntuacion_movimiento": 80.0}]

    guion = director.generar_guion_montaje(
        duracion_total=duracion_total,
        silencios=silencios,
        picos_audio=picos_audio,
        muestras_movimiento=muestras_movimiento,
        plantilla=plantilla
    )

    assert guion["duracion_original"] == 10.0
    assert guion["duracion_final_estimada"] < 10.0
    assert guion["ahorro_tiempo_porcentaje"] > 0
    assert len(guion["segmentos_conservar"]) == 2
    assert len(guion["momentos_cumbre"]) >= 1


def test_director_montaje_procesar_video_completo():
    """
    Verifica la ejecución del pipeline completo de montaje con reporte de progreso.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_p = Path(temp_dir)
        ruta_entrada = str(dir_p / "video_entrada.mp4")
        ruta_salida = str(dir_p / "video_editado_final.mp4")

        crear_video_sintetico_prueba(ruta_entrada, duracion_segundos=3)

        director = DirectorMontaje()
        hitos_reportados = []

        def callback_prueba(pct, etapa, msg):
            hitos_reportados.append((pct, etapa))

        resultado = director.procesar_video_completo(
            ruta_video_entrada=ruta_entrada,
            ruta_video_salida=ruta_salida,
            id_plantilla="shooters_highlights",
            callback_progreso=callback_prueba
        )

        assert Path(ruta_salida).exists()
        assert Path(ruta_salida).stat().st_size > 1000
        assert resultado["duracion_original"] == 3.0
        # Validar que el callback haya reportado el 100%
        assert any(pct == 100 for pct, _ in hitos_reportados)
