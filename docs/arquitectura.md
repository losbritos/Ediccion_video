# Arquitectura del Sistema: Editor Automático de Video Local

Este documento define los principios arquitectónicos, la estructura de carpetas, el flujo de datos y los contratos de comunicación entre el **Frontend** y el **Backend**.

---

## 1. Principios de Diseño
1. **100% Local y Privado**: Ningún archivo de video o audio sale de la máquina del usuario. Los modelos de IA (Faster-Whisper) y la visión artificial (OpenCV) se ejecutan localmente.
2. **Separación Estricta Frontend / Backend**:
   - **Frontend**: Interfaz puramente declarativa y visual en HTML5 / Vanilla CSS / Vanilla JS. Cero dependencias pesadas de npm o frameworks invasivos.
   - **Backend**: Motor de procesamiento en Python estructurado en módulos especializados y expuesto mediante una API REST ligera (FastAPI).
3. **Procesamiento Asíncrono en Segundo Plano**:
   - Las operaciones de análisis de audio, visión artificial y renderizado de video son intensivas en CPU/GPU.
   - La API nunca bloquea el hilo HTTP; utiliza `BackgroundTasks` o colas de trabajo para emitir eventos de progreso continuos hacia la interfaz.
4. **Legibilidad y Mantenibilidad**:
   - Nomenclatura en español para variables, funciones y módulos de dominio.
   - Tipado estático con Python Type Hints (`pydantic` y `typing`).

---

## 2. Diagrama de Flujo de Datos

```
+-------------------------------------------------------------+
|                 Frontend (Navegador Local)                 |
|  - Carga de archivo / Drag & Drop                           |
|  - Selección de Juego y Plantilla de Edición                |
|  - Ajuste de umbrales (dB, zooms, música)                   |
|  - Barra de progreso por etapas y reproductor final         |
+------------------------------+------------------------------+
                               |
               Petición HTTP   |   Eventos de Progreso / SSE
               (JSON / Form)   |   (Estado en tiempo real)
                               v
+-------------------------------------------------------------+
|               Backend: API Local (FastAPI)                  |
|  - Endpoints REST (/api/subir, /api/procesar, etc.)         |
|  - Gestor de Tareas Asíncronas                              |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                     Director de Montaje                     |
|                                                             |
|   +-----------------------+     +-----------------------+   |
|   |   Analizador Audio    |     |   Analizador Video    |   |
|   |   - Silencios (dB)    |     |   - Keyframes OpenCV  |   |
|   |   - Picos de emoción  |     |   - Movimiento/Acción |   |
|   |   - Faster-Whisper    |     |   - Zooms dinámicos   |   |
|   +-----------+-----------+     +-----------+-----------+   |
|               |                             |               |
|               +--------------+--------------+               |
|                              v                              |
|                 Puntuación de Atención                      |
|                              +                              |
|                 Plantilla Elegida (JSON)                    |
|                              |                              |
|                              v                              |
|                 Línea de Tiempo (EDL/Cortes)                |
|                              |                              |
|                              v                              |
|         Motor de Edición y Renderizado (FFmpeg/NVENC)       |
+------------------------------+------------------------------+
                               |
                               v
                       [ Video Final MP4 ]
```

---

## 3. Estructura del Proyecto

```text
Ediccion_video/
│
├── .agents/
│   └── skills/
│       └── normas-codigo/
│           └── SKILL.md            # Skill: Variables en español, comentarios, cero código muerto, tests
│
├── docs/
│   ├── plan_maestro.md             # Plan general y fases del proyecto
│   ├── subtareas_fases.md          # Desglose en micro-tareas incrementales
│   └── arquitectura.md             # Especificación técnica (este archivo)
│
├── frontend/                       # Aplicación Web Local (Cliente)
│   ├── AGENTS.md                   # Instrucciones especializadas para el Agente Frontend
│   ├── index.html                  # Estructura semántica principal
│   ├── css/
│   │   └── styles.css              # Vanilla CSS (Dark mode, neon highlights, glassmorphism)
│   └── js/
│       ├── api.js                  # Conector de peticiones HTTP con FastAPI
│       └── app.js                  # Control de estado de la interfaz y eventos
│
├── backend/                        # Motor de Procesamiento y API (Servidor)
│   ├── AGENTS.md                   # Instrucciones especializadas para el Agente Backend
│   ├── main.py                     # Punto de entrada de la API FastAPI y CLI
│   ├── config/
│   │   └── plantillas.json         # Perfiles de edición por juego/categoría
│   ├── modulos/
│   │   ├── __init__.py
│   │   ├── analizador_audio.py     # Extracción de audio, silencios y picos
│   │   ├── analizador_video.py     # Procesamiento visual con OpenCV
│   │   ├── transcriptor_ia.py      # Transcripción con Faster-Whisper
│   │   ├── director_montaje.py     # Algoritmo de selección de mejores momentos
│   │   ├── gestor_plantillas.py    # Carga y validación de perfiles
│   │   └── motor_edicion.py        # Comandos de corte y renderizado con FFmpeg
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_analizador_audio.py
│   │   ├── test_analizador_video.py
│   │   ├── test_motor_edicion.py
│   │   └── test_api.py
│   └── requirements.txt            # Dependencias Python
│
├── AGENTS.md                       # Reglas generales del espacio de trabajo
└── README.md                       # Guía de inicio rápido y uso
```

---

## 4. Contrato de la API REST (Endpoints Clave)

| Método | Endpoint | Descripción | Parámetros Entrada | Respuesta Salida |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/estado` | Estado del backend y aceleración GPU | Ninguno | `{"estado": "ok", "gpu_disponible": bool, "dispositivo": "cuda"/"cpu"}` |
| `GET` | `/api/plantillas` | Lista de plantillas disponibles | Ninguno | `{"plantillas": [...]}` |
| `POST` | `/api/subir` | Cargar video o registrar ruta local | Archivo multipart o JSON `{"ruta_archivo": str}` | `{"id_video": str, "duracion_segundos": float, "nombre": str}` |
| `POST` | `/api/procesar` | Iniciar edición automática | `{"id_video": str, "plantilla": str, "ajustes": {...}}` | `{"id_tarea": str, "estado": "en_cola"}` |
| `GET` | `/api/progreso/{id_tarea}` | Consultar porcentaje y etapa de avance | `id_tarea` | `{"progreso": int, "etapa": str, "completado": bool, "error": str/null}` |
| `GET` | `/api/descargar/{id_tarea}` | Descargar o visualizar el video exportado | `id_tarea` | Archivo binario de video (`video/mp4`) |
