"""
Módulo para generación y gestión de recursos multimedia locales (assets).
Sintetiza efectos de sonido gamer y pistas de música rítmica libres de copyright
para dinamizar los videos de jugadas y Shorts sin depender de descargas externas.
"""

from pathlib import Path
from typing import Optional
import numpy as np
from scipy.io import wavfile

RUTA_BASE_BACKEND = Path(__file__).resolve().parent.parent
RUTA_CARPETA_ASSETS = RUTA_BASE_BACKEND / "assets"
RUTA_SONIDOS = RUTA_CARPETA_ASSETS / "sonidos"
RUTA_MUSICA = RUTA_CARPETA_ASSETS / "musica"


def asegurar_directorios_assets() -> None:
    """Crea los directorios necesarios para los assets del editor."""
    RUTA_SONIDOS.mkdir(parents=True, exist_ok=True)
    RUTA_MUSICA.mkdir(parents=True, exist_ok=True)


def sintetizar_impacto_boom(ruta_archivo: str, duracion_segundos: float = 1.8, tasa: int = 44100) -> str:
    """
    Sintetiza un efecto de sonido de impacto cinematográfico / sub-bass boom (estilo Vine Boom / golpe épico).
    Combina un impacto inicial percusivo con una caída exponencial de sub-graves (85 Hz -> 30 Hz).
    """
    total_muestras = int(tasa * duracion_segundos)
    t = np.linspace(0, duracion_segundos, total_muestras, endpoint=False)

    # 1. Transitorio inicial percusivo (ruido blanco filtrado de 40ms)
    ruido_inicial = np.random.uniform(-1.0, 1.0, total_muestras)
    envolvente_ruido = np.exp(-t * 65.0)
    golpe_transitorio = ruido_inicial * envolvente_ruido * 0.55

    # 2. Frecuencia descendente de sub-graves (85 Hz a 28 Hz)
    frecuencia_instantanea = 85.0 * np.exp(-t * 1.8) + 28.0
    fase = 2.0 * np.pi * np.cumsum(frecuencia_instantanea) / tasa
    tono_bajo = np.sin(fase)

    # Envolvente suave y contundente
    envolvente_bajo = np.exp(-t * 2.2)
    cuerpo_bajo = tono_bajo * envolvente_bajo

    # 3. Saturación sutil analógica (tanh)
    audio_combinado = np.tanh((golpe_transitorio + cuerpo_bajo * 0.9) * 1.6)

    # Normalizar a 16-bit PCM
    audio_normalizado = np.int16(audio_combinado / np.max(np.abs(audio_combinado) + 1e-9) * 31000)
    wavfile.write(ruta_archivo, tasa, audio_normalizado)
    return ruta_archivo


def sintetizar_whoosh(ruta_archivo: str, duracion_segundos: float = 0.9, tasa: int = 44100) -> str:
    """
    Sintetiza un efecto de barrido / whoosh dinámico para anticipar la jugada.
    """
    total_muestras = int(tasa * duracion_segundos)
    t = np.linspace(0, duracion_segundos, total_muestras, endpoint=False)

    ruido = np.random.uniform(-1.0, 1.0, total_muestras)
    # Envolvente parabólica (sube y luego baja rápidamente)
    envolvente = np.sin(np.pi * (t / duracion_segundos)) ** 2.5

    # Frecuencia modulada de filtro
    modulacion = np.sin(2.0 * np.pi * 3.0 * t) * 0.2 + 0.8
    senal = ruido * envolvente * modulacion

    audio_normalizado = np.int16(senal / (np.max(np.abs(senal)) + 1e-9) * 28000)
    wavfile.write(ruta_archivo, tasa, audio_normalizado)
    return ruta_archivo


def sintetizar_musica_gaming_loop(ruta_archivo: str, duracion_segundos: float = 30.0, tasa: int = 44100) -> str:
    """
    Sintetiza una pista musical en bucle estilo Synthwave / Gaming Beat (125 BPM):
    contiene bombo percusivo (kick), contratiempo de platillo (hi-hat) y línea de bajo rítmica.
    Diseñada para dar energía y ambientación cuando el video no contiene locución de voz.
    """
    total_muestras = int(tasa * duracion_segundos)
    t = np.linspace(0, duracion_segundos, total_muestras, endpoint=False)

    bpm = 125.0
    segundos_por_negra = 60.0 / bpm
    muestras_por_negra = int(tasa * segundos_por_negra)

    pista_final = np.zeros(total_muestras, dtype=np.float64)

    # 1. Bombo rítmico (Kick drum en cada tiempo de negra: 1, 2, 3, 4)
    duracion_kick = 0.22
    t_kick = np.linspace(0, duracion_kick, int(tasa * duracion_kick), endpoint=False)
    freq_kick = 140.0 * np.exp(-t_kick * 24.0) + 38.0
    fase_kick = 2.0 * np.pi * np.cumsum(freq_kick) / tasa
    onda_kick = np.sin(fase_kick) * np.exp(-t_kick * 14.0)

    for inicio_kick in range(0, total_muestras, muestras_por_negra):
        fin_kick = min(total_muestras, inicio_kick + len(onda_kick))
        longitud = fin_kick - inicio_kick
        pista_final[inicio_kick:fin_kick] += onda_kick[:longitud] * 0.75

    # 2. Platillos en contratiempo (Hi-Hats en las corcheas intermedias)
    muestras_corchea = muestras_por_negra // 2
    duracion_hat = 0.06
    t_hat = np.linspace(0, duracion_hat, int(tasa * duracion_hat), endpoint=False)
    onda_hat = np.random.uniform(-1.0, 1.0, len(t_hat)) * np.exp(-t_hat * 60.0)

    for i in range(muestras_corchea, total_muestras, muestras_por_negra):
        fin_hat = min(total_muestras, i + len(onda_hat))
        longitud = fin_hat - i
        pista_final[i:fin_hat] += onda_hat[:longitud] * 0.25

    # 3. Línea de bajo sintetizado rítmico (Synth Bass en escala menor: La, Do, Re, Fa)
    notas_bajo = [55.0, 65.4, 73.4, 87.3]  # Frecuencias Hz (A1, C2, D2, F2)
    duracion_bajo = segundos_por_negra * 0.85
    muestras_bajo = int(tasa * duracion_bajo)
    t_nota = np.linspace(0, duracion_bajo, muestras_bajo, endpoint=False)

    indice_tiempo = 0
    paso_nota = 0
    while indice_tiempo < total_muestras:
        freq_actual = notas_bajo[paso_nota % len(notas_bajo)]
        # Onda rica con armónicos (onda diente de sierra / square suave)
        onda_bajo = (
            np.sin(2.0 * np.pi * freq_actual * t_nota) +
            0.4 * np.sin(2.0 * np.pi * (freq_actual * 2.0) * t_nota) +
            0.2 * np.sin(2.0 * np.pi * (freq_actual * 3.0) * t_nota)
        )
        envolvente_bajo = np.exp(-t_nota * 3.0)
        segmento_bajo = onda_bajo * envolvente_bajo * 0.35

        fin_bajo = min(total_muestras, indice_tiempo + muestras_bajo)
        longitud = fin_bajo - indice_tiempo
        pista_final[indice_tiempo:fin_bajo] += segmento_bajo[:longitud]

        indice_tiempo += muestras_por_negra
        paso_nota += 1

    # Normalización final
    max_val = np.max(np.abs(pista_final)) + 1e-9
    audio_normalizado = np.int16((pista_final / max_val) * 26000)
    wavfile.write(ruta_archivo, tasa, audio_normalizado)
    return ruta_archivo


def inicializar_assets_predeterminados() -> None:
    """
    Verifica y genera todos los recursos de audio predeterminados si no existen.
    Garantiza que el sistema disponga de sonidos de impacto y música sin dependencias externas.
    """
    asegurar_directorios_assets()

    ruta_boom = RUTA_SONIDOS / "impacto_boom.wav"
    if not ruta_boom.exists():
        sintetizar_impacto_boom(str(ruta_boom))

    ruta_whoosh = RUTA_SONIDOS / "whoosh.wav"
    if not ruta_whoosh.exists():
        sintetizar_whoosh(str(ruta_whoosh))

    ruta_musica = RUTA_MUSICA / "musica_gaming_loop.wav"
    if not ruta_musica.exists():
        sintetizar_musica_gaming_loop(str(ruta_musica), duracion_segundos=45.0)


def remuestrear_audio(audio: np.ndarray, tasa_origen: int, tasa_destino: int) -> np.ndarray:
    """
    Ajusta la tasa de muestreo de una señal de audio unidimensional mediante interpolación lineal.

    Args:
        audio: Arreglo numpy 1D con las muestras.
        tasa_origen: Frecuencia de muestreo inicial en Hz.
        tasa_destino: Frecuencia de muestreo deseada en Hz.

    Returns:
        Arreglo numpy remuestreado con la nueva longitud calculada.
    """
    if tasa_origen == tasa_destino or len(audio) == 0:
        return audio
    num_muestras_destino = int(round(len(audio) * float(tasa_destino) / float(tasa_origen)))
    indices_origen = np.linspace(0, len(audio) - 1, num_muestras_destino)
    return np.interp(indices_origen, np.arange(len(audio)), audio)


def mezclar_audio_clip(
    datos_audio_original: np.ndarray,
    tasa_muestreo: int,
    tiempo_climax_relativo: Optional[float] = None,
    incluir_musica_fondo: bool = True,
    incluir_sfx_climax: bool = True,
    ruta_salida_wav: Optional[str] = None
) -> str:
    """
    Mezcla la pista de audio del juego original con música de fondo gamer sutil
    y un efecto sonoro de impacto contundente (sub-bass boom) en el momento del clímax.

    Args:
        datos_audio_original: Arreglo numpy de audio original (1D).
        tasa_muestreo: Tasa de muestreo de la pista original en Hz.
        tiempo_climax_relativo: Segundo dentro del clip donde ocurre el pico de acción.
        incluir_musica_fondo: Si es True, añade la pista musical rítmica a volumen atenuado (-16dB).
        incluir_sfx_climax: Si es True, añade el efecto de impacto boom en el clímax.
        ruta_salida_wav: Ruta donde se guardará el archivo WAV mezclado.

    Returns:
        Ruta absoluta al archivo de audio mezclado.
    """
    inicializar_assets_predeterminados()

    longitud_clip = len(datos_audio_original)
    if longitud_clip == 0:
        raise ValueError("El arreglo de audio original no puede estar vacío.")

    # Convertir a señal flotante normalizada [-1.0, 1.0]
    if np.issubdtype(datos_audio_original.dtype, np.integer):
        max_int = np.iinfo(datos_audio_original.dtype).max
        audio_mezclado = datos_audio_original.astype(np.float64) / max_int
    else:
        audio_mezclado = datos_audio_original.astype(np.float64)

    # 1. Mezcla de música de fondo gamer si está habilitada
    if incluir_musica_fondo:
        ruta_musica = RUTA_MUSICA / "musica_gaming_loop.wav"
        if ruta_musica.exists():
            tasa_musica, datos_musica = wavfile.read(str(ruta_musica))
            musica_flotante = datos_musica.astype(np.float64) / 32768.0
            # Remuestrear a la frecuencia del clip si difiere
            if tasa_musica != tasa_muestreo:
                musica_flotante = remuestrear_audio(musica_flotante, tasa_musica, tasa_muestreo)

            # Repetir bucle musical si el clip es más largo que la pista
            repeticiones = int(np.ceil(longitud_clip / len(musica_flotante)))
            musica_extendida = np.tile(musica_flotante, repeticiones)[:longitud_clip]

            # Aplicar fade in (0.6s) y fade out (1.0s) para entradas y salidas suaves
            muestras_fade_in = min(int(0.6 * tasa_muestreo), longitud_clip // 4)
            muestras_fade_out = min(int(1.0 * tasa_muestreo), longitud_clip // 4)

            envolvente = np.ones(longitud_clip, dtype=np.float64)
            if muestras_fade_in > 0:
                envolvente[:muestras_fade_in] = np.linspace(0.0, 1.0, muestras_fade_in)
            if muestras_fade_out > 0:
                envolvente[-muestras_fade_out:] = np.linspace(1.0, 0.0, muestras_fade_out)

            # Atenuar la música para que no opaque el sonido del juego (volumen al 18%)
            audio_mezclado += musica_extendida * envolvente * 0.18

    # 2. Mezcla de efecto de sonido en el clímax (impacto sub-bass)
    if incluir_sfx_climax and tiempo_climax_relativo is not None:
        ruta_boom = RUTA_SONIDOS / "impacto_boom.wav"
        if ruta_boom.exists():
            tasa_sfx, datos_sfx = wavfile.read(str(ruta_boom))
            sfx_flotante = datos_sfx.astype(np.float64) / 32768.0
            if tasa_sfx != tasa_muestreo:
                sfx_flotante = remuestrear_audio(sfx_flotante, tasa_sfx, tasa_muestreo)

            inicio_sfx = max(0, int(tiempo_climax_relativo * tasa_muestreo))
            if inicio_sfx < longitud_clip:
                fin_sfx = min(longitud_clip, inicio_sfx + len(sfx_flotante))
                longitud_insertar = fin_sfx - inicio_sfx
                audio_mezclado[inicio_sfx:fin_sfx] += sfx_flotante[:longitud_insertar] * 0.70

    # 3. Normalización con saturación suave para prevenir recorte digital (clipping)
    pico_maximo = np.max(np.abs(audio_mezclado)) + 1e-9
    if pico_maximo > 0.95:
        audio_mezclado = np.tanh(audio_mezclado / pico_maximo * 1.05) * 0.95

    audio_final_int16 = np.int16(audio_mezclado * 31000)

    if not ruta_salida_wav:
        ruta_salida_wav = str((RUTA_CARPETA_ASSETS / "temp_mezcla.wav").resolve())

    Path(ruta_salida_wav).parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(ruta_salida_wav, tasa_muestreo, audio_final_int16)
    return ruta_salida_wav


if __name__ == "__main__":
    inicializar_assets_predeterminados()
    print("Assets generados exitosamente en backend/assets/")
