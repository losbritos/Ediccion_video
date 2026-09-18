# Guía de Trabajo y Normas para Agentes en el Workspace

Bienvenido al proyecto **Editor Automático de Video para YouTube (Local)**.
Este repositorio sigue una arquitectura desacoplada en dos áreas principales: `frontend/` y `backend/`.

---

## 📌 Roles de Agentes Especializados

1. **Agente de Frontend (`frontend/AGENTS.md`)**:
   - Encargado de la interfaz web local (`index.html`, `styles.css`, `app.js`, `api.js`).
   - Especializado en diseño visual moderno (Dark mode, glassmorphism, micro-animaciones, estética gaming/creadores), accesibilidad y experiencia de usuario.
   - Cero frameworks externos invasivos; pureza en Vanilla HTML/CSS/JS.

2. **Agente de Backend (`backend/AGENTS.md`)**:
   - Encargado del motor de análisis de audio/video, inteligencia artificial local (Faster-Whisper), visión por computadora (OpenCV), montaje con FFmpeg y API REST con FastAPI.
   - Especializado en rendimiento, algoritmos de detección de atención y procesamiento seguro en segundo plano.

---

## ⚡ Skill Obligatoria: `normas-codigo`
Todos los agentes deben consultar y aplicar estrictamente las directrices de la skill [.agents/skills/normas-codigo/SKILL.md](file:///c:/Users/canha/Desktop/app_edicion_video/Ediccion_video/.agents/skills/normas-codigo/SKILL.md):
- Nombres de variables, funciones y comentarios en **español**.
- Documentación exhaustiva mediante **docstrings** y comentarios claros.
- **Tolerancia cero a código muerto** (imports ociosos, código comentado o variables huérfanas).
- **Testing riguroso**: cada cambio debe ir respaldado por pruebas unitarias o funcionales antes de darse por completado.

---

## 📋 Flujo de Trabajo Basado en Subtareas
Toda implementación debe guiarse por el documento [docs/subtareas_fases.md](file:///c:/Users/canha/Desktop/app_edicion_video/Ediccion_video/docs/subtareas_fases.md):
1. Seleccionar la subtarea activa.
2. Implementar los cambios necesarios respetando la skill `normas-codigo`.
3. Ejecutar las pruebas unitarias y verificar el correcto funcionamiento.
4. Actualizar el estado de la tarea en la documentación.
