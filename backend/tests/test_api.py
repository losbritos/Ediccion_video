"""
Pruebas unitarias para la configuración y endpoints básicos de la API.
"""

from pathlib import Path
import sys

# Agregar ruta backend al path para ejecución directa de pytest
RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from main import cargar_plantillas_configuradas  # noqa: E402


def test_carga_plantillas_retorna_lista_valida():
    """
    Verifica que la función de carga de plantillas retorne la lista configurada
    con los identificadores requeridos.
    """
    datos = cargar_plantillas_configuradas()
    assert "plantillas" in datos
    assert isinstance(datos["plantillas"], list)
    assert len(datos["plantillas"]) >= 3

    identificadores = [p["id"] for p in datos["plantillas"]]
    assert "shooters_highlights" in identificadores
    assert "gameplay_narrado" in identificadores
    assert "tutorial_educativo" in identificadores


def test_estructura_ajustes_plantilla_shooters():
    """
    Verifica que la plantilla de Shooters contenga los ajustes obligatorios de audio y video.
    """
    datos = cargar_plantillas_configuradas()
    plantilla_shooter = next(
        p for p in datos["plantillas"] if p["id"] == "shooters_highlights"
    )

    assert "ajustes_audio" in plantilla_shooter
    assert "umbral_silencio_db" in plantilla_shooter["ajustes_audio"]
    assert "ajustes_video" in plantilla_shooter
    assert "activar_zooms_dinamicos" in plantilla_shooter["ajustes_video"]
    assert plantilla_shooter["ajustes_video"]["activar_zooms_dinamicos"] is True
