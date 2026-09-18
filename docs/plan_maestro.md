# Plan Maestro: Aplicación Local de Edición Automática de Video para YouTube

## 1. Visión General del Proyecto
Desarrollar una aplicación **100% local** en Python que automatice el proceso de edición de videos largos (principalmente enfocado en *Gaming* y creación de contenido para YouTube). La aplicación analizará archivos de audio y video mediante modelos de Inteligencia Artificial y visión por computadora locales para identificar los momentos más relevantes, recortar silencios, aplicar plantillas dinámicas según el juego/categoría y generar un video final optimizado para maximizar la retención de la audiencia.

---

## 2. Arquitectura y Stack Tecnológico

| Módulo | Tecnología / Librería | Función Principal |
| :--- | :--- | :--- |
| **Interfaz de Usuario (Frontend)** | Vanilla HTML5 / CSS3 / JavaScript (ES6+) | Interfaz web local moderna, ligera y responsiva sin frameworks pesados. |
| **Servidor y API Local (Backend)** | Python 3.10+ / FastAPI | Servidor REST asíncrono, orquestación de tareas en segundo plano. |
| **IA & Transcripción Local** | Faster-Whisper | Transcripción de audio ultra-rápida, marcas de tiempo y subtítulos sincronizados. |
| **Análisis de Audio** | Librosa / Pydub / SciPy | Detección de silencios, análisis de frecuencias y picos de decibelios ($dB$). |
| **Visión por Computadora** | OpenCV | Análisis de movimiento, cambios de escena y detección de acción visual. |
| **Motor de Montaje y Renderizado** | FFmpeg nativo / MoviePy | Ensamblado de clips, zooms dinámicos, audio ducking y codificación por hardware. |

---

## 3. Desglose de Fases de Desarrollo

### **Fase 1: Motor de Edición Básico (Cortes y Silencios)**
*Objetivo:* Crear un script funcional en la terminal que procese un video largo y elimine las pausas/silencios sin necesidad de interfaz gráfica.
* **Tareas:**
  1. Configurar el entorno virtual de Python y dependencias (`moviepy`, `ffmpeg-python`, `scipy`, `pydub`).
  2. Implementar un módulo para extraer y separar la pista de audio del video.
  3. Desarrollar la lógica de detección de silencios basada en umbrales de decibelios ($dB$).
  4. Generar la lista de cortes y exportar el video procesado sin silencios.
* **Resultado / Entregable:** Script CLI ejecutable para procesar cortes iniciales.

---

### **Fase 2: Análisis de Audio Avanzado e IA Local (El "Cerebro")**
*Objetivo:* Analizar la pista de audio para identificar los momentos de mayor impacto emocional y generar subtítulos automáticos.
* **Tareas:**
  1. Integrar **Faster-Whisper** para correr transcripción localmente mediante CPU/GPU (CUDA).
  2. Implementar algoritmo de detección de picos de sonido (risas, gritos, explosiones, reacciones).
  3. Crear generador de subtítulos sincronizados (`.srt` / estilo dinámico palabra por palabra).
  4. Aplicar técnica de *Audio Ducking* (bajar música de fondo automáticamente cuando el creador habla).
* **Resultado / Entregable:** Módulo de análisis de audio que devuelve marcas de tiempo clave y subtítulos integrados.

---

### **Fase 3: Análisis Visual (Computer Vision con OpenCV)**
*Objetivo:* Detectar la intensidad de acción visual en pantalla para complementar los picos de audio.
* **Tareas:**
  1. Procesar fotogramas clave (*keyframes*) con OpenCV.
  2. Medir variaciones inter-fotograma para detectar momentos de movimiento rápido (combates, giros de cámara, explosiones).
  3. Correlacionar picos de acción visual con picos de audio para validar los "mejores momentos" (Puntuación de Atención).
  4. Programar efectos visuales dinámicos (ej. zooms automáticos hacia el centro de la pantalla durante eliminaciones o sorpresas).
* **Resultado / Entregable:** Módulo que asigna una "puntuación de atención" a cada fragmento del video.

---

### **Fase 4: Motor de Plantillas y Contexto (Director de Montaje)**
*Objetivo:* Ajustar el estilo de edición según el juego y la categoría especificados por el usuario.
* **Tareas:**
  1. Definir estructuras de datos (`plantillas.json`) para configurar plantillas:
     * **Gaming - Shooters / Highlights:** Ritmo frenético, 0 silencios, zooms dinámicos en bajas/kills, subtítulos coloridos y grandes, música alta en pausas.
     * **Gaming - Let's Play / Gameplay Narrado:** Cortes suaves (mantiene pausas cortas), música de fondo ambiental relajada, enfoque en comentarios.
     * **Tutoriales / Educativo:** Subtítulos limpios, zooms a zonas específicas, marcadores de capítulos.
  2. Construir el "Director de Montaje": script que recibe las marcas de tiempo, evalúa la plantilla elegida y genera la línea de tiempo final.
* **Resultado / Entregable:** Sistema que modifica la agresividad de los cortes y los efectos de acuerdo al contexto del juego.

---

### **Fase 5: Interfaz de Usuario Local (Frontend & API)**
*Objetivo:* Proporcionar una interfaz gráfica amigable, moderna y accesible desde el navegador web local.
* **Tareas:**
  1. Diseñar interfaz moderna en Vanilla HTML5/CSS3 (Dark Mode, Glassmorphism).
  2. Implementar zona de carga de archivos (*drag and drop*) para videos.
  3. Añadir desplegables y controles:
     * Selección de Juego (ej. Valorant, League of Legends, Minecraft, etc.)
     * Categoría / Estilo (Highlights, Gameplay completo, Shorts/TikTok)
     * Controles deslizantes: Umbral de silencio, agresividad de zooms, nivel de música.
  4. Agregar barra de progreso en tiempo real y reproductor para previsualizar el resultado.
* **Resultado / Entregable:** Aplicación web local funcional comunicada con la API de FastAPI.

---

### **Fase 6: Optimización, Aceleración por Hardware y Renderizado**
*Objetivo:* Maximizar la velocidad de procesamiento y reducir el tiempo de renderizado.
* **Tareas:**
  1. Configurar aceleración por GPU (NVIDIA CUDA / NVENC) para Whisper y FFmpeg.
  2. Optimizar el renderizado convirtiendo la secuencia de edición a un comando nativo de FFmpeg (evitando el cuello de botella de MoviePy en proyectos largos).
  3. Implementar procesamiento en paralelo de clips cuando se suban varios archivos simultáneamente.
* **Resultado / Entregable:** Software pulido de alto rendimiento.

---

## 4. Requisitos de Hardware Recomendados (Modo Local)
* **CPU:** 6 u 8 núcleos (AMD Ryzen 5/7 o Intel Core i5/i7).
* **GPU:** NVIDIA GTX 1660 / RTX 2060 o superior (6GB+ VRAM recomendados para Whisper y NVENC).
* **RAM:** 16 GB mínimo (32 GB recomendado para procesamiento de video 1080p/4K).
* **Almacenamiento:** Disco SSD NVMe con al menos 50 GB libres de espacio de trabajo temporal.
