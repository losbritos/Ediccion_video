"""
Pruebas unitarias e integrales para el motor de montaje (motor_edicion.py).
Valida la generación de archivos de concatenación y el renderizado con FFmpeg.
"""

from pathlib import Path
import subprocess
import sys
import tempfile
import pytest

RUTA_ACTUAL = Path(__file__).resolve().parent
RUTA_BACKEND = RUTA_ACTUAL.parent
sys.path.append(str(RUTA_BACKEND))

from modulos.analizador_audio import obtener_ruta_ejecutable_ffmpeg  # noqa: E402
from modulos.motor_edicion import (  # noqa: E402
    generar_archivo_demuxer_concat,
    cortar_y_unir_segmentos
)


def crear_video_sintetico_prueba(ruta_destino: str, duracion_segundos: int = 3) -> None:
    """
    Crea un video MP4 mínimo con audio y video sintético utilizando FFmpeg.
    """
    ejecutable_ffmpeg = obtener_ruta_ejecutable_ffmpeg()
    comando = [
        ejecutable_ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=320x240:d={duracion_segundos}:r=24",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duracion_segundos}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-shortest",
        ruta_destino
    ]
    resultado = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"No se pudo generar video de prueba: {resultado.stderr}")


def test_generar_archivo_demuxer_concat():
    """
    Verifica que el archivo de concatenación contenga las directivas y marcas esperadas.
    """
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as archivo_temp:
        ruta_lista = archivo_temp.name

    try:
        segmentos = [(0.0, 1.5), (2.0, 3.5)]
        generar_archivo_demuxer_concat("video_prueba.mp4", segmentos, ruta_lista)

        contenido = Path(ruta_lista).read_text(encoding="utf-8")
        assert "ffconcat version 1.0" in contenido
        assert "inpoint 0.000" in contenido
        assert "outpoint 1.500" in contenido
        assert "inpoint 2.000" in contenido
        assert "outpoint 3.500" in contenido
    finally:
        if Path(ruta_lista).exists():
            Path(ruta_lista).unlink()


def test_cortar_y_unir_segmentos_video_sintetico():
    """
    Genera un video de prueba de 4 segundos, recorta los segmentos [0.0, 1.0] y [2.0, 3.0],
    y verifica que se exporte correctamente un video resultante.
    """
    with tempfile.TemporaryDirectory() as directorio_temporal:
        dir_path = Path(directorio_temporal)
        ruta_video_entrada = str(dir_path / "video_entrada.mp4")
        ruta_video_salida = str(dir_path / "video_salida_recortado.mp4")

        # 1. Crear video fuente de 4 segundos
        crear_video_sintetico_prueba(ruta_video_entrada, duracion_segundos=4)
        assert Path(ruta_video_entrada).exists()

        # 2. Cortar y unir
        segmentos = [(0.0, 1.0), (2.0, 3.0)]
        resultado_ruta = cortar_y_unir_segmentos(
            ruta_video_entrada,
            segmentos,
            ruta_video_salida
        )

        # 3. Comprobar que el video final fue creado y tiene tamaño mayor a cero
        archivo_resultado = Path(resultado_ruta)
        assert archivo_resultado.exists()
        assert archivo_resultado.stat().st_size > 1000


def test_cortar_video_inexistente_lanza_error():
    """
    Verifica que cortar_y_unir_segmentos lance FileNotFoundError ante una ruta inválida.
    """
    with pytest.raises(FileNotFoundError):
        cortar_y_unir_segmentos(
            "archivo_inexistente_999.mp4",
            [(0.0, 1.0)],
            "salida.mp4"
        )


def test_cortar_con_segmentos_vacios_lanza_error():
    """
    Verifica que pasar una lista vacía de segmentos activos lance ValueError.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        ruta_dummy = temp_video.name

    try:
        with pytest.raises(ValueError):
            cortar_y_unir_segmentos(ruta_dummy, [], "salida.mp4")
    finally:
        if Path(ruta_dummy).exists():
            Path(ruta_dummy).unlink()
