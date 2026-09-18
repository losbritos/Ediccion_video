# AutoCut Studio - App Local de Edición Automática de Video para YouTube

Aplicación **100% local** en Python diseñada para creadores de contenido y gaming en YouTube. Automatiza el recorte de silencios, detecta acción visual con visión artificial, genera subtítulos palabra por palabra con IA y ensambla un video final optimizado para la retención de audiencia.

---

## 📁 Estructura del Repositorio

```text
Ediccion_video/
│
├── .agents/                        # Personalizaciones del entorno Antigravity
│   └── skills/
│       └── normas-codigo/
│           └── SKILL.md            # Skill: Variables en español, comentarios, cero código muerto y tests
│
├── docs/                           # Documentación de referencia del proyecto
│   ├── plan_maestro.md             # Plan completo, visión y 6 fases originales
│   ├── subtareas_fases.md          # Desglose en micro-tareas incrementales comprobables
│   └── arquitectura.md             # Flujo de datos y contratos de la API
│
├── frontend/                       # Interfaz Web Local (Vanilla HTML5 / CSS3 / JS)
│   ├── AGENTS.md                   # Instrucciones especializadas para el Agente Frontend
│   ├── index.html                  # Panel visual de control y carga de video
│   ├── css/
│   │   └── styles.css              # Estilos modernos oscuros, glassmorphism y acentos neón
│   └── js/
│       ├── api.js                  # Cliente de conexión REST con FastAPI
│       └── app.js                  # Lógica interactiva de usuario y flujo de render
│
├── backend/                        # Motor de Procesamiento y API Local (Python)
│   ├── AGENTS.md                   # Instrucciones especializadas para el Agente Backend
│   ├── main.py                     # Servidor FastAPI y CLI
│   ├── config/
│   │   └── plantillas.json         # Perfiles de edición (Shooters, Let's Play, Tutoriales)
│   ├── modulos/                    # Módulos de audio, visión y montaje
│   ├── tests/                      # Suite de pruebas automatizadas con pytest
│   └── requirements.txt            # Dependencias Python
│
├── AGENTS.md                       # Reglas generales del espacio de trabajo
└── README.md                       # Este documento
```

---

## ⚡ Estándares de Codificación Obligatorios (`normas-codigo`)
1. **Variables y Funciones en Español**: Nombres claros y descriptivos (`detectar_silencios()`, `umbral_decibelios`, `calcular_segmentos_activos()`).
2. **Código Documentado**: Docstrings explicativos con `Args` y `Returns` en cada función.
3. **Tolerancia Cero al Código Muerto**: Sin imports ociosos, variables huérfanas o bloques comentados antiguos.
4. **Testing Riguroso**: Ninguna subtarea se cierra sin su correspondiente test unitario funcional.

---

## 🚀 Inicio Rápido

### 1. Previsualizar la Interfaz de Usuario (Frontend)
Puedes abrir directamente el archivo [frontend/index.html](file:///c:/Users/canha/Desktop/app_edicion_video/Ediccion_video/frontend/index.html) en cualquier navegador web moderno para explorar el diseño interactivo, seleccionar plantillas y probar el simulador del pipeline de edición.

### 2. Puesta en Marcha del Backend (Fase 1 en adelante)
1. Instalar dependencias:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Iniciar el servidor local:
   ```bash
   python main.py
   ```
   La API estará disponible en `http://127.0.0.1:8000` con documentación interactiva en `http://127.0.0.1:8000/docs`.

3. Ejecutar las pruebas unitarias:
   ```bash
   pytest
   ```

---

## 🗺️ Hoja de Ruta (Roadmap)
Consulta el documento [docs/subtareas_fases.md](file:///c:/Users/canha/Desktop/app_edicion_video/Ediccion_video/docs/subtareas_fases.md) para ver el progreso detallado de las 6 fases de desarrollo.
