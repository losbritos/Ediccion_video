---
name: normas-codigo
description: >-
  Aplica los estándares de codificación obligatorios del proyecto: variables y funciones en español,
  documentación y comentarios claros en cada bloque, tolerancia cero al código muerto, y testing
  automatizado riguroso antes de dar por completado cualquier cambio.
---

# Normas de Calidad y Codificación del Proyecto

Esta skill define las directrices obligatorias de desarrollo para cualquier agente o desarrollador que trabaje en este repositorio. Su objetivo es mantener un código limpio, legible, consistente y libre de errores.

---

## 1. Nomenclatura y Variables en Español

Todo el código de dominio de negocio, lógica y modelos debe nombrarse en **español claro, descriptivo y sin abreviaturas crípticas**.

### Reglas de Nombres por Lenguaje:

#### Python (Backend):
- **Variables y Funciones**: `snake_case` en español.
  - ✅ Bueno: `duracion_segundos`, `detectar_silencios()`, `umbral_decibelios`, `ruta_video_origen`.
  - ❌ Evitar: `audio_len`, `getSilences()`, `thresh_db`, `x`, `tmp`.
- **Clases**: `PascalCase` en español.
  - ✅ Bueno: `AnalizadorAudio`, `DirectorMontaje`, `MotorEdicion`.
  - ❌ Evitar: `AudioAnalyzer`, `VideoProcessor`.
- **Constantes**: `UPPER_SNAKE_CASE` en español.
  - ✅ Bueno: `FRECUENCIA_MUESTREO_HZ = 16000`, `UMBRAL_SILENCIO_PREDETERMINADO_DB = -30.0`.

#### JavaScript / CSS (Frontend):
- **Variables y Funciones**: `camelCase` en español.
  - ✅ Bueno: `cargarVideo()`, `tiempoActual`, `actualizarBarraProgreso()`.
  - ❌ Evitar: `uploadFile()`, `currTime`, `v`.
- **Clases CSS y Selectores**: `kebab-case` en español o términos semánticos claros.
  - ✅ Bueno: `.panel-control`, `.boton-procesar`, `.barra-progreso-llenado`.

---

## 2. Código Documentado y Comentado

Cada módulo, clase y función debe estar apropiadamente documentado.

### Requisitos:
1. **Docstrings en cada función/método**:
   - Describir qué hace la función en 1 o 2 oraciones.
   - Detallar parámetros con sus tipos y propósito.
   - Detallar valor de retorno y excepciones previsibles.
   ```python
   def calcular_segmentos_activos(
       duracion_total: float,
       silencios: list[tuple[float, float]],
       margen_segundos: float = 0.1
   ) -> list[tuple[float, float]]:
       """
       Calcula los intervalos de tiempo donde existe voz o acción relevante,
       invirtiendo los periodos detectados como silencio.

       Args:
           duracion_total: Duración completa del video en segundos.
           silencios: Lista de tuplas (inicio, fin) correspondientes a pausas.
           margen_segundos: Margen de tolerancia antes y después del corte para suavizar.

       Returns:
           Lista de tuplas (inicio, fin) de los segmentos que deben conservarse.
       """
   ```
2. **Comentarios de intención (El "Por qué", no solo el "Qué")**:
   - Explicar decisiones no evidentes o trucos de rendimiento (ej. por qué se usa un muestreo de 16kHz mono, por qué se aplica un umbral específico).
   - Evitar comentarios redundantes (ej. no escribir `# sumar 1 a la variable` encima de `contador += 1`).

---

## 3. Tolerancia Cero al Código Muerto

El repositorio debe mantenerse esbelto y sin basura técnica:
- 🚫 **Imports no utilizados**: Eliminar cualquier `import` que no se use activamente.
- 🚫 **Bloques de código comentados**: Si un bloque de código fue reemplazado o descartado, se borra directamente (Git se encarga del historial).
- 🚫 **Variables huérfanas**: No declarar variables que luego no se consuman.
- 🚫 **Funciones fantasma**: Si una función auxiliar ya no se llama desde ningún punto del proyecto, debe retirarse junto con sus tests asociados.
- 🚫 **Archivos temporales olvidados**: Asegurarse de que los scripts de prueba limpien sus archivos `.tmp`, audios extraídos de prueba o videos intermedios.

---

## 4. Criterio de Verificación y Testing Riguroso

Ninguna tarea o subtarea se considera terminada hasta que haya sido verificada mediante pruebas funcionales o automatizadas.

### Protocolo de Validación:
1. **Pruebas Unitarias**:
   - Cada nuevo módulo en `backend/modulos/` debe tener su correspondiente archivo de pruebas en `backend/tests/test_[nombre_modulo].py`.
   - Utilizar `pytest` para ejecutar la suite de pruebas.
2. **Pruebas de Límites (*Edge Cases*)**:
   - Validar qué ocurre cuando el video no tiene audio.
   - Validar qué ocurre cuando el video no contiene silencios o es todo silencio.
   - Validar archivos inexistentes o formatos corruptos con mensajes de error amigables.
3. **Validación Visual en Frontend**:
   - Comprobar que no haya errores ni advertencias en la consola del navegador.
   - Verificar la adaptabilidad visual a diferentes tamaños de ventana y estados interactivos (hover, active, disabled).
