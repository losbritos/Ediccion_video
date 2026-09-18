"""
Punto de entrada principal para el Backend del Editor Automático de Video.
Provee la API REST local con FastAPI y soporte para ejecución por línea de comandos (CLI).
"""

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Rutas base del proyecto
RUTA_BASE_BACKEND = Path(__file__).resolve().parent
RUTA_CONFIGURACION_PLANTILLAS = RUTA_BASE_BACKEND / "config" / "plantillas.json"

# Inicialización de la aplicación FastAPI
aplicacion = FastAPI(
    title="API de Edición Automática de Video",
    description="Servidor local para análisis de audio/video y renderizado automático.",
    version="0.1.0",
)

# Configuración de CORS para permitir conexiones desde el cliente web local
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def cargar_plantillas_configuradas() -> Dict[str, Any]:
    """
    Carga el catálogo de plantillas de edición desde el archivo JSON de configuración.

    Returns:
        Diccionario con las plantillas disponibles o estructura vacía si no existe.
    """
    if not RUTA_CONFIGURACION_PLANTILLAS.exists():
        return {"plantillas": []}

    with open(RUTA_CONFIGURACION_PLANTILLAS, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


@aplicacion.get("/api/estado")
def consultar_estado_servidor() -> Dict[str, Any]:
    """
    Verifica el estado del servidor backend local.

    Returns:
        Diccionario con el estado de salud, versión y modo operativo.
    """
    return {
        "estado": "operativo",
        "version": "0.1.0",
        "modo": "local",
        "mensaje": "Servidor de edición de video listo para procesar tareas.",
    }


@aplicacion.get("/api/plantillas")
def listar_plantillas_disponibles() -> Dict[str, Any]:
    """
    Obtiene todas las plantillas de edición configuradas para videojuegos y contenidos.

    Returns:
        Diccionario con el listado completo de perfiles y ajustes predeterminados.
    """
    return cargar_plantillas_configuradas()


if __name__ == "__main__":
    import uvicorn

    print("Iniciando servidor local de Edición de Video en http://127.0.0.1:8000")
    uvicorn.run("main:aplicacion", host="127.0.0.1", port=8000, reload=True)
