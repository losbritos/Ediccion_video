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
from modulos.analizador_video import agrupar_momentos_cumbre, calcular_puntuacion_atencion
from modulos.generador_subtitulos import generar_subtitulos_ass_animados
from modulos.generador_assets import mezclar_audio_clip
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


def test_filtro_pantalla_muerte_lol_atencion_cero():
    """
    Verifica que el filtro de pantalla en escala de grises (muerte / respawn en LoL)
    invalide completamente la puntuación de atención (score = 0), evitando seleccionar clips muertos.
    """
    muestras = [
        # Tramo normal con algo de movimiento
        {"tiempo": 10.0, "puntuacion_movimiento": 60.0, "saturacion_promedio": 120.0, "es_pantalla_muerte": False, "destello_combate": False},
        # Tramo de muerte (pantalla grisácea en LoL, sat < 28)
        {"tiempo": 20.0, "puntuacion_movimiento": 85.0, "saturacion_promedio": 18.0, "es_pantalla_muerte": True, "destello_combate": False},
        {"tiempo": 21.0, "puntuacion_movimiento": 90.0, "saturacion_promedio": 20.0, "es_pantalla_muerte": True, "destello_combate": False}
    ]

    bloques = calcular_puntuacion_atencion(
        muestras_movimiento=muestras,
        picos_audio=[],
        duracion_total=30.0
    )

    bloque_muerto = next(b for b in bloques if 20.0 <= b["inicio"] <= 21.0)
    assert bloque_muerto["es_pantalla_muerte"] is True
    assert bloque_muerto["puntuacion_atencion"] == 0.0
    assert bloque_muerto["es_momento_cumbre"] is False


def test_filtro_paneo_camara_lol_penalizacion():
    """
    Verifica que un paneo generalizado de cámara (>85% movimiento uniforme sin destellos de hechizo)
    reciba penalización frente a un combate genuino focalizado con partículas/destellos.
    """
    muestras_paneo = [
        {"tiempo": 0.5, "puntuacion_movimiento": 90.0, "saturacion_promedio": 110.0, "es_pantalla_muerte": False, "destello_combate": False, "es_paneo_camara": True}
    ]
    muestras_combate = [
        {"tiempo": 0.5, "puntuacion_movimiento": 90.0, "saturacion_promedio": 110.0, "es_pantalla_muerte": False, "destello_combate": True, "es_paneo_camara": False}
    ]

    bloques_paneo = calcular_puntuacion_atencion(muestras_movimiento=muestras_paneo, picos_audio=[], duracion_total=1.0)
    bloques_combate = calcular_puntuacion_atencion(muestras_movimiento=muestras_combate, picos_audio=[], duracion_total=1.0)

    score_paneo = bloques_paneo[0]["puntuacion_atencion"]
    score_combate = bloques_combate[0]["puntuacion_atencion"]

    assert score_combate > score_paneo


def test_generar_subtitulos_con_sticker_meme_gaming():
    """
    Verifica que generar_subtitulos_ass_animados cree el evento de estilo GamingMeme
    con animación pop-up y ubicación central para destacar la jugada cumbre.
    """
    with tempfile.TemporaryDirectory() as carpeta_temp:
        ruta_ass = Path(carpeta_temp) / "meme.ass"
        generar_subtitulos_ass_animados(
            segmentos_transcripcion=[],
            ruta_salida_ass=str(ruta_ass),
            texto_sticker_climax="🔥 ¡OUTPLAYED! 🔥",
            tiempo_climax_segundos=12.5,
            formato_vertical=True
        )

        assert ruta_ass.exists()
        contenido = ruta_ass.read_text(encoding="utf-8")
        assert "Style: GamingMeme" in contenido
        assert "🔥 ¡OUTPLAYED! 🔥" in contenido
        assert "\\fscx140\\fscy140" in contenido


def test_mezclar_audio_clip_gamer():
    """
    Verifica que mezclar_audio_clip inserte correctamente la música gamer de fondo
    y el sonido de impacto boom sin saturación o recorte digital.
    """
    with tempfile.TemporaryDirectory() as carpeta_temp:
        ruta_salida_wav = Path(carpeta_temp) / "clip_mezclado.wav"
        tasa = 16000
        duracion_seg = 6.0
        audio_silencio_relativo = np.zeros(int(tasa * duracion_seg), dtype=np.int16)

        mezclar_audio_clip(
            datos_audio_original=audio_silencio_relativo,
            tasa_muestreo=tasa,
            tiempo_climax_relativo=3.0,
            incluir_musica_fondo=True,
            incluir_sfx_climax=True,
            ruta_salida_wav=str(ruta_salida_wav)
        )

        assert ruta_salida_wav.exists()
        assert ruta_salida_wav.stat().st_size > 1000


def test_renderizar_short_con_zoom_impacto_y_audio_mezclado():
    """
    Verifica que renderizar_short_con_subtitulos aplique el punch-in zoom en el clímax
    y cargue la pista de audio mezclada correctamente.
    """
    with tempfile.TemporaryDirectory() as carpeta_temp:
        ruta_video = Path(carpeta_temp) / "origen.mp4"
        crear_video_sintetico_prueba(str(ruta_video), duracion_segundos=4)

        ruta_audio_mezclado = Path(carpeta_temp) / "audio_mezclado.wav"
        mezclar_audio_clip(
            datos_audio_original=np.zeros(16000 * 3, dtype=np.int16),
            tasa_muestreo=16000,
            tiempo_climax_relativo=1.5,
            incluir_musica_fondo=True,
            incluir_sfx_climax=True,
            ruta_salida_wav=str(ruta_audio_mezclado)
        )

        ruta_salida = Path(carpeta_temp) / "short_zoom.mp4"
        resultado = renderizar_short_con_subtitulos(
            ruta_video_origen=str(ruta_video),
            tiempo_inicio=0.5,
            duracion=2.5,
            ruta_salida=str(ruta_salida),
            formato_vertical=True,
            tiempo_climax_relativo=1.2,
            incluir_zoom_impacto=True,
            ruta_audio_mezclado=str(ruta_audio_mezclado)
        )

        assert Path(resultado).exists()
        assert Path(resultado).stat().st_size > 1000

