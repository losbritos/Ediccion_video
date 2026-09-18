"""
Módulo gestor de plantillas de edición contextuales.
Permite cargar, validar, modificar y registrar perfiles de edición para distintos tipos de juego.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

RUTA_PREDETERMINADA_PLANTILLAS = Path(__file__).resolve().parent.parent / "config" / "plantillas.json"


class GestorPlantillas:
    """
    Administrador central de perfiles de estilo y configuración de montaje.
    """

    def __init__(self, ruta_configuracion: Optional[Path] = None) -> None:
        """
        Inicializa el gestor con la ruta al archivo JSON de plantillas.
        """
        self.ruta_archivo = ruta_configuracion or RUTA_PREDETERMINADA_PLANTILLAS
        self._catalogo: Dict[str, Dict[str, Any]] = {}
        self.recargar_plantillas()

    def recargar_plantillas(self) -> None:
        """
        Lee el archivo de configuración y almacena las plantillas en memoria.
        """
        if not self.ruta_archivo.exists():
            self._catalogo = {}
            return

        with open(self.ruta_archivo, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            lista_plantillas = datos.get("plantillas", [])
            self._catalogo = {p["id"]: p for p in lista_plantillas if "id" in p}

    def listar_todas(self) -> List[Dict[str, Any]]:
        """
        Retorna la lista completa de plantillas disponibles.
        """
        return list(self._catalogo.values())

    def obtener_plantilla(self, id_plantilla: str) -> Dict[str, Any]:
        """
        Obtiene los parámetros de una plantilla específica por su ID.
        Si no se encuentra, retorna la plantilla por defecto ('shooters_highlights').

        Args:
            id_plantilla: Identificador único de la plantilla.

        Returns:
            Diccionario con la configuración completa del perfil.
        """
        if id_plantilla in self._catalogo:
            return self._catalogo[id_plantilla]

        # Fallback predeterminado seguro
        if "shooters_highlights" in self._catalogo:
            return self._catalogo["shooters_highlights"]

        if self._catalogo:
            return next(iter(self._catalogo.values()))

        # Fallback sintético en caso de archivo ausente
        return {
            "id": "predeterminado",
            "nombre": "Edición Básica",
            "ajustes_audio": {
                "umbral_silencio_db": -28.0,
                "duracion_minima_silencio_segundos": 0.4,
                "margen_conservacion_corte_segundos": 0.1
            },
            "ajustes_video": {
                "activar_zooms_dinamicos": True,
                "factor_zoom": 1.15
            }
        }
