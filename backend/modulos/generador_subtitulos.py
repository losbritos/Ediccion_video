"""
Módulo para generación y formateo de subtítulos automáticos.
Soporta exportación a formato estándar SubRip (.srt) y formato animado estilo Gaming (.ass).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional


def formatear_tiempo_srt(segundos: float) -> str:
    """
    Convierte una marca de tiempo en segundos al formato estándar de SubRip (HH:MM:SS,mmm).

    Args:
        segundos: Tiempo en segundos (ej. 75.42).

    Returns:
        Cadena con formato '00:01:15,420'.
    """
    segundos = max(0.0, segundos)
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    milisegundos = int(round((segundos - int(segundos)) * 1000))

    if milisegundos >= 1000:
        segs += 1
        milisegundos = 0

    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegundos:03d}"


def formatear_tiempo_ass(segundos: float) -> str:
    """
    Convierte una marca de tiempo en segundos al formato SubStation Alpha (H:MM:SS.cc).

    Args:
        segundos: Tiempo en segundos.

    Returns:
        Cadena con formato '0:01:15.42'.
    """
    segundos = max(0.0, segundos)
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = int(segundos % 60)
    centesimas = int(round((segundos - int(segundos)) * 100))

    if centesimas >= 100:
        segs += 1
        centesimas = 0

    return f"{horas:01d}:{minutos:02d}:{segs:02d}.{centesimas:02d}"


def convertir_hex_a_color_ass(color_hex: str) -> str:
    """
    Convierte un color en formato hexadecimal (#RRGGBB) al formato BGR de ASS (&H00BBGGRR&).

    Args:
        color_hex: Código hexadecimal con o sin almohadilla (ej. '#FF0055').

    Returns:
        Cadena de color en formato ASS (ej. '&H005500FF&').
    """
    hex_limpio = color_hex.lstrip("#")
    if len(hex_limpio) != 6:
        # Fallback a blanco en caso de formato erróneo
        return "&H00FFFFFF&"

    rojo = hex_limpio[0:2]
    verde = hex_limpio[2:4]
    azul = hex_limpio[4:6]

    return f"&H00{azul}{verde}{rojo}&"


def generar_subtitulos_srt(
    segmentos_transcripcion: List[Dict[str, Any]],
    ruta_salida_srt: str
) -> str:
    """
    Genera un archivo de subtítulos estándar en formato .srt a partir de los segmentos de Whisper.

    Args:
        segmentos_transcripcion: Lista de diccionarios con 'inicio', 'fin' y 'texto'.
        ruta_salida_srt: Ruta donde se guardará el archivo .srt.

    Returns:
        Ruta absoluta al archivo .srt generado.
    """
    archivo_salida = Path(ruta_salida_srt)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    bloques_srt: List[str] = []

    for indice, segmento in enumerate(segmentos_transcripcion, start=1):
        inicio_str = formatear_tiempo_srt(segmento["inicio"])
        fin_str = formatear_tiempo_srt(segmento["fin"])
        texto = segmento.get("texto", "").strip()

        if not texto:
            continue

        bloque = f"{indice}\n{inicio_str} --> {fin_str}\n{texto}\n"
        bloques_srt.append(bloque)

    with open(archivo_salida, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(bloques_srt))

    return str(archivo_salida.resolve())


def generar_subtitulos_ass_animados(
    segmentos_transcripcion: List[Dict[str, Any]],
    ruta_salida_ass: str,
    color_primario_hex: str = "#FFEA00",
    color_borde_hex: str = "#000000",
    tamano_fuente: int = 42,
    formato_vertical: bool = False,
    texto_sticker_climax: Optional[str] = None,
    tiempo_climax_segundos: Optional[float] = None,
    duracion_sticker_segundos: float = 2.4
) -> str:
    """
    Genera un archivo de subtítulos animados (.ass) con tipografía llamativa,
    borde grueso, efecto de resaltado palabra por palabra para YouTube / Shorts / Gaming,
    y soporte para stickers / memes animados emergentes en el clímax de la jugada.

    Args:
        segmentos_transcripcion: Lista de segmentos con marcas de palabras.
        ruta_salida_ass: Ruta destino del archivo .ass.
        color_primario_hex: Color de relleno del texto en hexadecimal.
        color_borde_hex: Color del contorno del texto en hexadecimal.
        tamano_fuente: Tamaño de fuente en puntos.
        formato_vertical: True para adaptar la resolución y márgenes a 9:16 (1080x1920).
        texto_sticker_climax: Texto meme / cartel a mostrar en el momento cumbre (ej. '🔥 ¡OUTPLAYED! 🔥').
        tiempo_climax_segundos: Segundo exacto del Short donde ocurre la kill o jugada clave.
        duracion_sticker_segundos: Duración en pantalla del cartel animado.

    Returns:
        Ruta absoluta al archivo .ass generado.
    """
    archivo_salida = Path(ruta_salida_ass)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    color_primario_ass = convertir_hex_a_color_ass(color_primario_hex)
    color_borde_ass = convertir_hex_a_color_ass(color_borde_hex)

    res_x = 1080 if formato_vertical else 1920
    res_y = 1920 if formato_vertical else 1080
    tamano = 56 if formato_vertical and tamano_fuente == 42 else tamano_fuente
    margen_v = 480 if formato_vertical else 90

    # Tamaño y estilo del sticker meme
    tamano_meme = 72 if formato_vertical else 60

    # Cabecera estándar de archivo ASS con estilo moderno (fuente gruesa, sombra, alineación central)
    cabecera_ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: GamingSub,Arial Black,{tamano},{color_primario_ass},&H0000FFFF&,{color_borde_ass},&H80000000&,-1,0,0,0,100,100,0,0,1,4.5,2,2,40,40,{margen_v},1
Style: GamingMeme,Arial Black,{tamano_meme},&H0000FFFF&,&H00FFFFFF&,&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,6.0,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lineas_eventos: List[str] = []

    # 1. Añadir subtítulos de locución
    for segmento in segmentos_transcripcion:
        palabras = segmento.get("palabras", [])

        if palabras:
            tamano_grupo = 4
            for i in range(0, len(palabras), tamano_grupo):
                grupo_palabras = palabras[i : i + tamano_grupo]
                t_inicio = grupo_palabras[0]["inicio"]
                t_fin = grupo_palabras[-1]["fin"]

                inicio_ass = formatear_tiempo_ass(t_inicio)
                fin_ass = formatear_tiempo_ass(t_fin)

                texto_grupo = " ".join(p["palabra"] for p in grupo_palabras)
                linea = f"Dialogue: 0,{inicio_ass},{fin_ass},GamingSub,,0,0,0,,{{\\t(0,80,\\fscx112\\fscy112)\\t(80,160,\\fscx100\\fscy100)}}{texto_grupo}"
                lineas_eventos.append(linea)
        else:
            inicio_ass = formatear_tiempo_ass(segmento["inicio"])
            fin_ass = formatear_tiempo_ass(segmento["fin"])
            texto = segmento.get("texto", "").strip()
            if texto:
                linea = f"Dialogue: 0,{inicio_ass},{fin_ass},GamingSub,,0,0,0,,{texto}"
                lineas_eventos.append(linea)

    # 2. Añadir sticker / meme animado emergente en el clímax
    if texto_sticker_climax and tiempo_climax_segundos is not None:
        t_ini_stk = max(0.0, tiempo_climax_segundos - 0.2)
        t_fin_stk = t_ini_stk + duracion_sticker_segundos
        stk_ini_str = formatear_tiempo_ass(t_ini_stk)
        stk_fin_str = formatear_tiempo_ass(t_fin_stk)

        # Ubicación central con pop-up explosivo
        pos_y = 960 if formato_vertical else 540
        pos_x = 540 if formato_vertical else 960

        linea_stk = (
            f"Dialogue: 1,{stk_ini_str},{stk_fin_str},GamingMeme,,0,0,0,,"
            f"{{\\an5\\pos({pos_x},{pos_y})\\t(0,100,\\fscx140\\fscy140)\\t(100,240,\\fscx100\\fscy100)}}{texto_sticker_climax}"
        )
        lineas_eventos.append(linea_stk)

    with open(archivo_salida, "w", encoding="utf-8") as archivo:
        archivo.write(cabecera_ass + "\n".join(lineas_eventos) + "\n")

    return str(archivo_salida.resolve())
