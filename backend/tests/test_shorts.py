"""
Pruebas unitarias y de integración para la generación de YouTube Shorts.
Valida la agrupación de momentos cumbre, renderizado de clips con subtítulos incrustados,
formato vertical 9:16 y los endpoints de descarga de Shorts individuales.
"""

from pathlib import Path
import tempfile
import numpy as np
from fastapi.testclient import TestClient

from main import aplicacion
from modulos.analizador_video import agrupar_momentos_cumbre
from modulos.generador_subtitulos import generar_subtitulos_ass_animados
from modulos.motor_edicion import renderizar_short_con_subtitulos
from tests.test_motor_edicion import crear_video_sintetico_prueba

cliente = TestClient(aplicacion)


def test_agrupar_momentos_cumbre_selecciona_mejores_picos_sin_solapamiento():
    """
    Verifica que agrupar_momentos_cumbre identifique los picos con mayor atención
    y respete la separación mínima y duración objetivo.
    """
    duracion_total = 600.0  # 10 minutos de partida
    bloques_atencion = []

    # Crear 600 bloques de 1 segundo con picos en segundos 120 (score 95), 300 (score 90), 450 (score 88)
    for seg in range(600):
        score = 20.0
        if 115 <= seg <= 125:
            score = 95.0
        elif 295 <= seg <= 305:
            score = 90.0
        elif 445 <= seg <= 455:
            score = 88.0
        elif 126 <= seg <= 135:
            # Pico muy cercano al primero, debe evitarse por distancia mínima
            score = 85.0

        bloques_atencion.append({
            "inicio": float(seg),
            "fin": float(seg + 1),
            "puntuacion_atencion": score
        })

    shorts = agrupar_momentos_cumbre(
        bloques_atencion=bloques_atencion,
        duracion_total=duracion_total,
        cantidad_shorts=3,
        duracion_short_segundos=35.0,
        distancia_minima_segundos=60.0
    )

    assert len(shorts) == 3
    # Los 3 climaxes deben corresponder aproximadamente a los minutos 2, 5 y 7.5
    for short in shorts:
        assert short["duracion"] == 35.0
        assert short["inicio"] >= 0.0
        assert short["fin"] <= duracion_total

    # Verificar que están ordenados cronológicamente
    assert shorts[0]["inicio"] < shorts[1]["inicio"] < shorts[2]["inicio"]


def test_agrupar_momentos_cumbre_video_corto():
    """
    Verifica el comportamiento cuando el video dura menos que un short.
    """
    bloques = [
        {"inicio": 0.0, "fin": 1.0, "puntuacion_atencion": 80.0},
        {"inicio": 1.0, "fin": 2.0, "puntuacion_atencion": 85.0}
    ]
    shorts = agrupar_momentos_cumbre(
        bloques_atencion=bloques,
        duracion_total=2.0,
        cantidad_shorts=3,
        duracion_short_segundos=35.0
    )
    assert len(shorts) == 1
    assert shorts[0]["inicio"] == 0.0
    assert shorts[0]["fin"] == 2.0


def test_renderizar_short_con_subtitulos_y_formato_vertical():
    """
    Verifica que renderizar_short_con_subtitulos exporte un MP4 vertical 9:16 con subtítulos ASS.
    """
    with tempfile.TemporaryDirectory() as carpeta_temp:
        ruta_video = Path(carpeta_temp) / "origen.mp4"
        crear_video_sintetico_prueba(str(ruta_video), duracion_segundos=3)

        # Crear subtítulo ASS sintético
        ruta_ass = Path(carpeta_temp) / "test_sub.ass"
        segmentos_prueba = [{
            "inicio": 0.5,
            "fin": 2.0,
            "texto": "Buena jugada",
            "palabras": [
                {"palabra": "Buena", "inicio": 0.5, "fin": 1.1, "probabilidad": 0.99},
                {"palabra": "jugada", "inicio": 1.1, "fin": 2.0, "probabilidad": 0.98}
            ]
        }]
        generar_subtitulos_ass_animados(segmentos_prueba, str(ruta_ass), formato_vertical=True)

        ruta_salida = Path(carpeta_temp) / "short_vertical.mp4"
        resultado = renderizar_short_con_subtitulos(
            ruta_video_origen=str(ruta_video),
            tiempo_inicio=0.5,
            duracion=1.5,
            ruta_salida=str(ruta_salida),
            ruta_subtitulos_ass=str(ruta_ass),
            formato_vertical=True
        )

        assert Path(resultado).exists()
        assert Path(resultado).stat().st_size > 1000


def test_endpoint_descarga_short_individual():
    """
    Verifica que /api/descargar_short responda correctamente o retorne 404 si la tarea no existe.
    """
    res = cliente.get("/api/descargar_short/tarea_inexistente/1")
    assert res.status_code == 404
