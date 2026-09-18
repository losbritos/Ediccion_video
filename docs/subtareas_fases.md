# Desglose de Fases en Subtareas Pequeñas e Incrementales

Este documento es la guía de trabajo paso a paso del proyecto. Cada subtarea está diseñada para ser pequeña, auto-contenida, documentada y testeable antes de avanzar a la siguiente.

---

## 🎯 Fase 1: Motor de Edición Básico (Cortes y Silencios)

- [x] **Subtarea 1.1: Preparación del Entorno Backend**
  - Instalar y verificar Python 3.10+ y FFmpeg en el sistema.
  - Crear entorno virtual (`backend/venv`).
  - Crear `backend/requirements.txt` con las dependencias base (`pydub`, `scipy`, `numpy`, `pytest`).
  - *Criterio de verificación:* Script de prueba que importe las dependencias y valide la detección de FFmpeg. (Completado: Python 3.12, FFmpeg 9.0.1, venv creado y pytest ejecutado con éxito).

- [x] **Subtarea 1.2: Extracción de Audio de Video**
  - Crear `backend/modulos/analizador_audio.py`.
  - Implementar función `extraer_pista_audio(ruta_video: str, ruta_audio_salida: str) -> str`.
  - Usar FFmpeg directo para extraer WAV PCM a 16kHz mono (optimizado para análisis rápido).
  - *Criterio de verificación:* Test unitario en `backend/tests/test_analizador_audio.py` verificando la extracción de un video de prueba. (Completado y verificado con pytest).

- [x] **Subtarea 1.3: Detección de Silencios por Decibelios ($dB$)**
  - En `backend/modulos/analizador_audio.py`, implementar `detectar_intervalos_silencio(ruta_audio: str, umbral_db: float, duracion_minima_seg: float) -> list[tuple[float, float]]`.
  - Retornar listas de intervalos `(tiempo_inicio, tiempo_fin)` considerados silencio.
  - *Criterio de verificación:* Test unitario con audio sintético con pausas conocidas, validando precisión de los cortes. (Completado y verificado con pytest).

- [x] **Subtarea 1.4: Cálculo de Segmentos Activos (Línea de Tiempo)**
  - Implementar `calcular_segmentos_activos(duracion_total: float, silencios: list[tuple[float, float]], margen_segundos: float = 0.1) -> list[tuple[float, float]]`.
  - Invertir la lista de silencios para obtener los fragmentos hablados/activos, agregando un pequeño margen (*padding*) para que los cortes no suenen abruptos.
  - *Criterio de verificación:* Test unitario validando la continuidad de la línea de tiempo. (Completado y verificado con pytest).

- [x] **Subtarea 1.5: Motor de Corte y Ensamblado Inicial con FFmpeg**
  - Crear `backend/modulos/motor_edicion.py`.
  - Implementar función `cortar_y_unir_segmentos(ruta_video_origen: str, segmentos_activos: list[tuple[float, float]], ruta_video_destino: str) -> str`.
  - Usar lista de filtros o concatenador nativo de FFmpeg sin re-codificación pesada cuando sea posible.
  - *Criterio de verificación:* Ejecutar `backend/main.py --entrada video.mp4 --salida editado.mp4` y comprobar que genera el video recortado sin pausas. (Completado y verificado con pytest y prueba E2E).

---

## 🧠 Fase 2: Análisis de Audio Avanzado e IA Local (El Cerebro)

- [x] **Subtarea 2.1: Integración de Faster-Whisper**
  - Instalar `faster-whisper` (compatible con CPU y GPU CUDA).
  - En `backend/modulos/transcriptor_ia.py`, crear clase `TranscriptorLocal` con soporte para modelos `tiny`, `base` y `small`.
  - Implementar `transcribir_audio(ruta_audio: str, idioma: str = "es") -> list[dict]`.
  - *Criterio de verificación:* Transcribir un archivo corto y validar que devuelve texto y marcas de tiempo por palabra/segmento. (Completado: faster-whisper y ctranslate2 instalados, GPU GTX 1650 Ti detectada con fallback CPU int8).

- [x] **Subtarea 2.2: Detección de Picos Emocionales y Volumen**
  - Implementar función `detectar_picos_energia(ruta_audio: str, umbral_desviacion: float = 2.0) -> list[dict]`.
  - Calcular la energía RMS (Root Mean Square) a lo largo del tiempo e identificar momentos con explosiones, gritos o risas del creador.
  - *Criterio de verificación:* Test unitario comprobando que detecta picos en archivos de prueba. (Completado y verificado con pytest).

- [x] **Subtarea 2.3: Generador de Subtítulos Sincronizados y Dinámicos**
  - Crear `backend/modulos/generador_subtitulos.py`.
  - Implementar exportación a formato `.srt` estándar y formato `.ass` / `.json` con estilo animado para YouTube Shorts o Gaming (colores, resaltado palabra por palabra).
  - *Criterio de verificación:* Comprobar que el archivo de subtítulos generado es válido y coincide con las marcas de tiempo. (Completado y verificado con pytest).

- [x] **Subtarea 2.4: Módulo de Audio Ducking (Atenuación Automática)**
  - Implementar en `backend/modulos/motor_edicion.py` la mezcla de pista de fondo (música sin copyright) con la voz del creador.
  - La música disminuye a -18dB cuando el creador habla y sube a -8dB durante transiciones o silencios intencionales.
  - *Criterio de verificación:* Test de mezcla de audio verificando la variación de volumen. (Completado y verificado con compresión sidechain nativa en FFmpeg).

---

## 👁️ Fase 3: Análisis Visual (Computer Vision con OpenCV)

- [x] **Subtarea 3.1: Extractor de Fotogramas Clave (*Keyframes*)**
  - Crear `backend/modulos/analizador_video.py`.
  - Implementar lectura optimizada de video con OpenCV saltando fotogramas fijos para no saturar la CPU (muestreo a 3 fps).
  - *Criterio de verificación:* Medir el tiempo de lectura y procesado de un clip de prueba. (Completado y verificado con pytest).

- [x] **Subtarea 3.2: Detección de Intensidad de Movimiento**
  - Implementar cálculo de diferencia de fotogramas (Frame Differencing en escala de grises con desenfoque gaussiano).
  - Generar vector de puntuación de movimiento normalizado de 0 a 100 por cada segundo del video.
  - *Criterio de verificación:* Comparar variaciones inter-fotograma. (Completado y verificado con pytest).

- [x] **Subtarea 3.3: Cálculo de la "Puntuación de Atención" (Atención Score)**
  - Implementar algoritmo ponderado que combine picos de audio y movimiento visual.
  - Marcar los mejores momentos del video como candidatos a *Highlights* o *Shorts*.
  - *Criterio de verificación:* Test que valide la asignación de puntuaciones y marcado de momentos cumbre. (Completado y verificado con pytest).

- [x] **Subtarea 3.4: Generación de Zooms y Efectos Dinámicos**
  - Implementar efectos de cámara en `analizador_video.py` / FFmpeg (Zoom suave al 115%-120% hacia el centro en momentos de impacto).
  - *Criterio de verificación:* Renderizado de un clip con efecto de zoom y validación de archivo. (Completado y verificado con pytest).

---

## 🎬 Fase 4: Motor de Plantillas y Contexto (Director de Montaje)

- [x] **Subtarea 4.1: Estructura y Esquema de Plantillas (`plantillas.json`)**
  - Crear `backend/config/plantillas.json` con perfiles (Shooters/Highlights, Let's Play Narrado y Tutoriales).
  - *Criterio de verificación:* Validación de esquema JSON con dataclass/dict de Python. (Completado).

- [x] **Subtarea 4.2: Gestor de Plantillas**
  - Crear `backend/modulos/gestor_plantillas.py`.
  - Funciones para cargar, validar y obtener plantillas con fallback seguro.
  - *Criterio de verificación:* Tests unitarios de lectura y fallback. (Completado y verificado con pytest).

- [x] **Subtarea 4.3: El "Director de Montaje"**
  - Crear clase `DirectorMontaje` que orqueste:
    1. Lectura de marcas de audio (silencios, picos).
    2. Lectura de marcas de video (acción visual con OpenCV).
    3. Aplicación de la plantilla seleccionada.
    4. Generación del guion de montaje (EDL) y ejecución de pipeline completo.
  - *Criterio de verificación:* Test integral que genere el guion completo y renderice video final. (Completado y verificado con pytest).

---

## 🌐 Fase 5: Interfaz Web Local (Frontend Moderno & API)

- [x] **Subtarea 5.1: Servidor de API Local con FastAPI**
  - En `backend/main.py`, crear endpoints REST:
    - `GET /api/estado`: Salud del servidor y aceleración GPU.
    - `GET /api/plantillas`: Lista de plantillas disponibles.
    - `POST /api/subir`: Subida de archivo de video multipart.
    - `POST /api/procesar`: Iniciar tarea en segundo plano (BackgroundTasks).
    - `GET /api/progreso/{id_tarea}`: Estado del porcentaje de edición y logs en tiempo real.
    - `GET /api/descargar/{id_tarea}`: Servir el video final renderizado en MP4.
  - *Criterio de verificación:* Tests de endpoints con `pytest` y `TestClient` de FastAPI. (Completado y verificado con pytest).

- [x] **Subtarea 5.2: Interfaz de Usuario Vanilla (HTML5 & CSS3)**
  - Crear `frontend/index.html` con estructura moderna, limpia y semántica.
  - Crear `frontend/css/styles.css` con estética premium oscura (*dark mode*, detalles neón/cian para YouTube/Gaming, paneles de cristal *glassmorphism*, responsive).
  - Componentes creados: Zona Drag & Drop, Selector de Juego, Sliders de umbral, Barra de progreso por etapas, Consola de logs y Reproductor final.
  - *Criterio de verificación:* Visualización estética y limpia en navegador. (Completado).

- [x] **Subtarea 5.3: Lógica de Interacción en JavaScript (ES Modules)**
  - Crear `frontend/js/api.js` para peticiones Fetch al backend.
  - Crear `frontend/js/app.js` para control de eventos, animaciones, actualización de estados y polling en vivo.
  - *Criterio de verificación:* Flujo completo implementado y conectado con la API REST. (Completado).

- [x] **Subtarea 5.4: Reproductor de Previsualización Local**
  - Añadir reproductor HTML5 de video con controles de pantalla completa y descarga directa del archivo editado.
  - *Criterio de verificación:* Integración en `app.js` y `index.html`. (Completado).

---

## ⚡ Fase 6: Optimización, Aceleración por Hardware y Renderizado

- [x] **Subtarea 6.1: Detección y Configuración de Hardware (CUDA / NVENC)**
  - Detectar automáticamente GPU NVIDIA GTX 1650 Ti para codificación `h264_nvenc` y `hevc_nvenc` en FFmpeg.
  - Configurar fallback seguro a CPU (`libx264`) con presets ultra-rápidos (`preset ultrafast`).
  - *Criterio de verificación:* Verificado mediante `detectar_codificador_optimo()` y prueba de codificadores en FFmpeg. (Completado).

- [x] **Subtarea 6.2: Pipeline de Renderizado Directo con FFmpeg Nativo**
  - Concat demuxer de FFmpeg implementado en `motor_edicion.py` sin sobrecarga de memoria en Python.
  - *Criterio de verificación:* 27 pruebas unitarias superadas con tiempos de renderizado inferiores a 2 segundos en clips de prueba. (Completado).

- [x] **Subtarea 6.3: Empaquetado y Script de Arranque**
  - Script de arranque con un solo clic creado: `iniciar_app.bat`.
  - Abre automáticamente el navegador y arranca el backend de FastAPI.
  - *Criterio de verificación:* Archivo ejecutable probado y listo para su uso. (Completado).
