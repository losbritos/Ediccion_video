"""
Punto de entrada principal para el Backend del Editor Automático de Video.
Provee la API REST local con FastAPI, orquestador de tareas en segundo plano
y soporte para ejecución por línea de comandos (CLI).
"""

import argparse
import asyncio
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Dict, Optional
import uuid

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from scipy.io import wavfile

from modulos.analizador_audio import (
    extraer_pista_audio,
    detectar_intervalos_silencio,
    calcular_segmentos_activos
)
from modulos.director_montaje import DirectorMontaje
from modulos.gestor_plantillas import GestorPlantillas
from modulos.motor_edicion import cortar_y_unir_segmentos
from modulos.transcriptor_ia import detectar_dispositivo_optimo

# Rutas base del proyecto
RUTA_BASE_BACKEND = Path(__file__).resolve().parent
RUTA_ARCHIVOS_SUBIDOS = RUTA_BASE_BACKEND / "temp" / "subidas"
RUTA_ARCHIVOS_RENDER = RUTA_BASE_BACKEND / "temp" / "renders"

RUTA_ARCHIVOS_SUBIDOS.mkdir(parents=True, exist_ok=True)
RUTA_ARCHIVOS_RENDER.mkdir(parents=True, exist_ok=True)

# Registro en memoria de tareas en segundo plano y videos cargados
registro_videos: Dict[str, Dict[str, Any]] = {}
registro_tareas: Dict[str, Dict[str, Any]] = {}

# Inicialización de dependencias
gestor_plantillas = GestorPlantillas()
director_montaje = DirectorMontaje(gestor_plantillas)

# Inicialización de la aplicación FastAPI
aplicacion = FastAPI(
    title="AutoCut Studio API",
    description="Servidor local para análisis multimedia y renderizado automático de video.",
    version="0.2.0",
)

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SolicitudProcesamiento(BaseModel):
    """Modelo de solicitud para iniciar edición automática."""
    id_video: str
    plantilla: str = "shooters_highlights"
    ajustes: Optional[Dict[str, Any]] = None


@aplicacion.get("/api/estado")
def consultar_estado_servidor() -> Dict[str, Any]:
    """
    Verifica el estado del servidor y el hardware de aceleración disponible.
    """
    dispositivo = detectar_dispositivo_optimo()
    return {
        "estado": "operativo",
        "version": "0.2.0",
        "modo": "local",
        "aceleracion_disponible": dispositivo == "cuda",
        "dispositivo_computo": dispositivo,
        "mensaje": "Servidor de edición listo para procesar."
    }


@aplicacion.get("/api/plantillas")
def listar_plantillas_disponibles() -> Dict[str, Any]:
    """
    Obtiene las plantillas de edición configuradas para videojuegos.
    """
    return {"plantillas": gestor_plantillas.listar_todas()}


@aplicacion.post("/api/subir")
async def subir_video_para_procesar(archivo: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Recibe un archivo de video mediante subida multipart y lo registra localmente.
    """
    id_video = str(uuid.uuid4())
    nombre_limpio = Path(archivo.filename).name
    ruta_guardado = RUTA_ARCHIVOS_SUBIDOS / f"{id_video}_{nombre_limpio}"

    with open(ruta_guardado, "wb") as buffer_destino:
        shutil.copyfileobj(archivo.file, buffer_destino)

    tamano_mb = round(ruta_guardado.stat().st_size / (1024 * 1024), 2)

    # Registrar información del video
    registro_videos[id_video] = {
        "id": id_video,
        "nombre": nombre_limpio,
        "ruta": str(ruta_guardado.resolve()),
        "tamano_mb": tamano_mb
    }

    return {
        "id_video": id_video,
        "nombre": nombre_limpio,
        "tamano_mb": tamano_mb,
        "mensaje": "Video cargado exitosamente."
    }


def tarea_segundo_plano_procesar(id_tarea: str, id_video: str, id_plantilla: str, ajustes: Optional[Dict[str, Any]]) -> None:
    """
    Worker que ejecuta el ciclo de análisis y renderizado en segundo plano sin bloquear el servidor.
    """
    registro_tareas[id_tarea]["estado"] = "en_proceso"
    info_video = registro_videos.get(id_video)
    if not info_video:
        registro_tareas[id_tarea]["estado"] = "error"
        registro_tareas[id_tarea]["error"] = "Video no encontrado en el servidor."
        return

    ruta_origen = info_video["ruta"]
    nombre_base = Path(ruta_origen).stem
    ruta_salida = str(RUTA_ARCHIVOS_RENDER / f"render_{id_tarea}_{nombre_base}.mp4")

    def notificar_progreso(porcentaje: int, etapa: str, mensaje: str) -> None:
        registro_tareas[id_tarea]["progreso"] = porcentaje
        registro_tareas[id_tarea]["etapa"] = etapa
        registro_tareas[id_tarea]["logs"].append(f"[{time.strftime('%H:%M:%S')}] {mensaje}")

    try:
        resultado = director_montaje.procesar_video_completo(
            ruta_video_entrada=ruta_origen,
            ruta_video_salida=ruta_salida,
            id_plantilla=id_plantilla,
            ajustes_personalizados=ajustes,
            callback_progreso=notificar_progreso
        )

        registro_tareas[id_tarea]["estado"] = "completado"
        registro_tareas[id_tarea]["completado"] = True
        registro_tareas[id_tarea]["ruta_video_final"] = ruta_salida
        registro_tareas[id_tarea]["resultado"] = resultado

    except Exception as excepcion:
        registro_tareas[id_tarea]["estado"] = "error"
        registro_tareas[id_tarea]["error"] = str(excepcion)
        registro_tareas[id_tarea]["logs"].append(f"[ERROR] {str(excepcion)}")


@aplicacion.post("/api/procesar")
def iniciar_procesamiento_automatico(
    solicitud: SolicitudProcesamiento,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Encola una tarea de edición en segundo plano y retorna su identificador único.
    """
    if solicitud.id_video not in registro_videos:
        raise HTTPException(status_code=404, detail="El video especificado no existe.")

    id_tarea = str(uuid.uuid4())
    registro_tareas[id_tarea] = {
        "id_tarea": id_tarea,
        "id_video": solicitud.id_video,
        "estado": "en_cola",
        "progreso": 0,
        "etapa": "iniciando",
        "completado": False,
        "error": None,
        "resultado": None,
        "logs": [f"[{time.strftime('%H:%M:%S')}] Tarea encolada. Iniciando análisis..."]
    }

    background_tasks.add_task(
        tarea_segundo_plano_procesar,
        id_tarea,
        solicitud.id_video,
        solicitud.plantilla,
        solicitud.ajustes
    )

    return {
        "id_tarea": id_tarea,
        "estado": "en_cola",
        "mensaje": "Tarea iniciada en segundo plano."
    }


@aplicacion.get("/api/progreso/{id_tarea}")
def consultar_progreso_edicion(id_tarea: str) -> Dict[str, Any]:
    """
    Consulta el estado, porcentaje y registros de una tarea en curso.
    """
    tarea = registro_tareas.get(id_tarea)
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")

    return tarea


@aplicacion.get("/api/descargar/{id_tarea}")
def descargar_video_procesado(id_tarea: str):
    """
    Descarga o sirve el video final renderizado en formato MP4.
    """
    tarea = registro_tareas.get(id_tarea)
    if not tarea or not tarea.get("completado"):
        raise HTTPException(status_code=404, detail="El video aún no está disponible.")

    ruta_archivo = tarea.get("ruta_video_final")
    if not ruta_archivo or not Path(ruta_archivo).exists():
        raise HTTPException(status_code=404, detail="Archivo renderizado no encontrado.")

    return FileResponse(
        path=ruta_archivo,
        media_type="video/mp4",
        filename=Path(ruta_archivo).name
    )


# Servir la interfaz web local directamente en http://127.0.0.1:8000/
RUTA_FRONTEND = RUTA_BASE_BACKEND.parent / "frontend"
if RUTA_FRONTEND.exists():
    aplicacion.mount("/", StaticFiles(directory=str(RUTA_FRONTEND), html=True), name="frontend")



def procesar_video_cli(
    ruta_entrada: str,
    ruta_salida: str,
    umbral_db: float = -28.0,
    duracion_minima_segundos: float = 0.35,
    margen_segundos: float = 0.1
) -> None:
    """
    Ejecuta el pipeline de edición rápida por terminal.
    """
    tiempo_inicio = time.time()
    print("==========================================================")
    print("  AutoCut Studio CLI - Procesamiento de Cortes y Silencios")
    print("==========================================================")
    print(f"Entrada: {ruta_entrada} -> Salida: {ruta_salida}\n")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        ruta_audio_temp = temp_audio.name

    try:
        print("[1/4] Extrayendo pista de audio...")
        extraer_pista_audio(ruta_entrada, ruta_audio_temp)

        tasa, datos = wavfile.read(ruta_audio_temp)
        duracion_total = len(datos) / tasa

        print(f"[2/4] Detectando silencios por debajo de {umbral_db} dB...")
        silencios = detectar_intervalos_silencio(
            ruta_audio_temp,
            umbral_db=umbral_db,
            duracion_minima_segundos=duracion_minima_segundos
        )

        print("[3/4] Generando lista de segmentos activos...")
        segmentos_activos = calcular_segmentos_activos(
            duracion_total,
            silencios,
            margen_segundos=margen_segundos
        )

        print("[4/4] Renderizando video con FFmpeg...")
        cortar_y_unir_segmentos(ruta_entrada, segmentos_activos, ruta_salida)

        print(f"\n¡Éxito! Video guardado en: {ruta_salida}")
        print(f"Tiempo total: {time.time() - tiempo_inicio:.2f} segundos")
        print("==========================================================")

    finally:
        if Path(ruta_audio_temp).exists():
            Path(ruta_audio_temp).unlink()


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description="AutoCut Studio")
    analizador.add_argument("--entrada", "--input", "-i", type=str, default=None)
    analizador.add_argument("--salida", "--output", "-o", type=str, default=None)
    analizador.add_argument("--umbral-db", type=float, default=-28.0)
    analizador.add_argument("--duracion-silencio", type=float, default=0.35)
    analizador.add_argument("--margen", type=float, default=0.1)

    args = analizador.parse_args()

    if args.entrada and args.salida:
        procesar_video_cli(args.entrada, args.salida, args.umbral_db, args.duracion_silencio, args.margen)
    else:
        import uvicorn
        print("Iniciando servidor local de Edición de Video en http://127.0.0.1:8000")
        uvicorn.run("main:aplicacion", host="127.0.0.1", port=8000, reload=True)
