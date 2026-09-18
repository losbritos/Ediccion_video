"""
Módulo de transcripción local mediante Inteligencia Artificial (Faster-Whisper).
Permite transcribir audio a texto en CPU o GPU (CUDA) extrayendo marcas de tiempo
por segmento y por palabra para subtitulado dinámico.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
import ctranslate2


def detectar_dispositivo_optimo() -> str:
    """
    Detecta si el sistema cuenta con GPU NVIDIA compatible con CUDA o si se debe utilizar CPU.

    Returns:
        Cadena 'cuda' si hay GPU disponible y ctranslate2 tiene soporte, de lo contrario 'cpu'.
    """
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


class TranscriptorLocal:
    """
    Controlador de transcripción local basado en modelos Faster-Whisper.
    """

    def __init__(
        self,
        tamano_modelo: str = "base",
        dispositivo: Optional[str] = None,
        tipo_computo: Optional[str] = None
    ) -> None:
        """
        Inicializa el modelo de Whisper local.

        Args:
            tamano_modelo: Tamaño del modelo ('tiny', 'base', 'small', 'medium').
            dispositivo: 'cuda' o 'cpu'. Si es None, se autodetecta.
            tipo_computo: Precisión de cómputo ('float16', 'int8_float16', 'int8', 'float32').
        """
        self.tamano_modelo = tamano_modelo
        self.dispositivo = dispositivo or detectar_dispositivo_optimo()

        if tipo_computo:
            self.tipo_computo = tipo_computo
        else:
            # Configuración recomendada según el dispositivo
            if self.dispositivo == "cuda":
                self.tipo_computo = "float16"
            else:
                self.tipo_computo = "int8"

        self._modelo = None

    def _cargar_modelo_si_es_necesario(self) -> None:
        """
        Carga el modelo Whisper en memoria RAM o VRAM de forma perezosa (lazy loading).
        """
        if self._modelo is None:
            from faster_whisper import WhisperModel

            try:
                self._modelo = WhisperModel(
                    self.tamano_modelo,
                    device=self.dispositivo,
                    compute_type=self.tipo_computo
                )
            except Exception as error_cuda:
                # Fallback transparente a CPU si CUDA reporta error de drivers/librerías
                if self.dispositivo == "cuda":
                    print(f"Advertencia: Fallback a CPU por error en GPU ({error_cuda}).")
                    self.dispositivo = "cpu"
                    self.tipo_computo = "int8"
                    self._modelo = WhisperModel(
                        self.tamano_modelo,
                        device="cpu",
                        compute_type="int8"
                    )
                else:
                    raise error_cuda

    def transcribir_audio(
        self,
        ruta_audio: str,
        idioma: str = "es",
        con_marcas_palabra: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Transcribe un archivo de audio a texto, extrayendo tiempos por segmento y por palabra.

        Args:
            ruta_audio: Ruta al archivo WAV mono a transcribir.
            idioma: Código del idioma esperado ('es' para español, 'en' para inglés).
            con_marcas_palabra: Si es True, incluye marcas temporales de cada palabra individual.

        Returns:
            Lista de diccionarios con la estructura:
            [
                {
                    "inicio": 0.5,
                    "fin": 3.2,
                    "texto": "Bienvenidos a este nuevo video",
                    "palabras": [
                        {"palabra": "Bienvenidos", "inicio": 0.5, "fin": 1.1, "probabilidad": 0.98},
                        ...
                    ]
                }
            ]
        """
        archivo = Path(ruta_audio)
        if not archivo.exists():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {ruta_audio}")

        self._cargar_modelo_si_es_necesario()

        segmentos_generador, info = self._modelo.transcribe(
            str(archivo),
            language=idioma,
            word_timestamps=con_marcas_palabra,
            beam_size=5,
            vad_filter=True  # Filtro VAD integrado de Whisper para ignorar silencios
        )

        resultados: List[Dict[str, Any]] = []

        for segmento in segmentos_generador:
            item_segmento = {
                "inicio": round(segmento.start, 3),
                "fin": round(segmento.end, 3),
                "texto": segmento.text.strip(),
                "palabras": []
            }

            if con_marcas_palabra and segmento.words:
                for palabra_info in segmento.words:
                    item_segmento["palabras"].append({
                        "palabra": palabra_info.word.strip(),
                        "inicio": round(palabra_info.start, 3),
                        "fin": round(palabra_info.end, 3),
                        "probabilidad": round(palabra_info.probability, 3)
                    })

            resultados.append(item_segmento)

        return resultados
