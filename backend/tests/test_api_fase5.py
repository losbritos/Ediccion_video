"""
Suite de pruebas de integración para la API REST local (FastAPI).
Valida los endpoints de estado, plantillas, subida de archivos, procesamiento y progreso.
"""

import io
from pathlib import Path
import sys
from fastapi.testclient import TestClient

RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from main import aplicacion  # noqa: E402
from tests.test_motor_edicion import crear_video_sintetico_prueba  # noqa: E402

cliente = TestClient(aplicacion)


def test_endpoint_estado_servidor():
    """
    Verifica que /api/estado responda con código 200 y parámetros de hardware.
    """
    respuesta = cliente.get("/api/estado")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "operativo"
    assert "dispositivo_computo" in datos


def test_endpoint_plantillas_disponibles():
    """
    Verifica que /api/plantillas liste los perfiles de juego configurados.
    """
    respuesta = cliente.get("/api/plantillas")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert "plantillas" in datos
    assert len(datos["plantillas"]) >= 3


def test_flujo_subida_y_procesamiento_api():
    """
    Verifica el flujo completo: subida de video -> inicio de tarea -> consulta de progreso.
    """
    # 1. Crear video mínimo en memoria
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        ruta_temp = temp_video.name

    try:
        crear_video_sintetico_prueba(ruta_temp, duracion_segundos=2)
        with open(ruta_temp, "rb") as f:
            contenido_video = f.read()

        # 2. Subir video
        archivos = {"archivo": ("clip_prueba.mp4", io.BytesIO(contenido_video), "video/mp4")}
        res_subida = cliente.post("/api/subir", files=archivos)
        assert res_subida.status_code == 200
        datos_subida = res_subida.json()
        assert "id_video" in datos_subida
        id_video = datos_subida["id_video"]

        # 3. Iniciar procesamiento
        solicitud = {
            "id_video": id_video,
            "plantilla": "shooters_highlights"
        }
        res_procesar = cliente.post("/api/procesar", json=solicitud)
        assert res_procesar.status_code == 200
        datos_proc = res_procesar.json()
        assert "id_tarea" in datos_proc
        id_tarea = datos_proc["id_tarea"]

        # 4. Consultar progreso
        res_progreso = cliente.get(f"/api/progreso/{id_tarea}")
        assert res_progreso.status_code == 200
        datos_prog = res_progreso.json()
        assert "progreso" in datos_prog
        assert "logs" in datos_prog

    finally:
        if Path(ruta_temp).exists():
            Path(ruta_temp).unlink()
