/**
 * Módulo de comunicación con el Backend local (FastAPI).
 * Provee funciones asíncronas para consultar estado, obtener plantillas y orquestar tareas.
 */

const URL_BASE_API = 'http://127.0.0.1:8000/api';

/**
 * Consulta el estado de salud y conectividad del servidor local.
 * @returns {Promise<{conectado: boolean, datos?: object, error?: string}>}
 */
export async function verificarEstadoServidor() {
  try {
    const respuesta = await fetch(`${URL_BASE_API}/estado`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(3000)
    });

    if (!respuesta.ok) {
      throw new Error(`El servidor respondió con código ${respuesta.status}`);
    }

    const datos = await respuesta.json();
    return { conectado: true, datos };
  } catch (error) {
    return { conectado: false, error: error.message };
  }
}

/**
 * Obtiene la lista de plantillas de edición configuradas en el backend.
 * @returns {Promise<Array<object>>}
 */
export async function obtenerPlantillasDisponibles() {
  try {
    const respuesta = await fetch(`${URL_BASE_API}/plantillas`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    if (!respuesta.ok) {
      throw new Error('No se pudieron obtener las plantillas');
    }

    const resultado = await respuesta.json();
    return resultado.plantillas || [];
  } catch (error) {
    console.warn('Usando plantillas en memoria por falta de conexión al servidor:', error);
    return [];
  }
}

/**
 * Envía un archivo de video al backend para su análisis local.
 * @param {File} archivoVideo - Objeto File seleccionado por el usuario.
 * @returns {Promise<object>}
 */
export async function subirVideoLocal(archivoVideo) {
  const formulario = new FormData();
  formulario.append('archivo', archivoVideo);

  const respuesta = await fetch(`${URL_BASE_API}/subir`, {
    method: 'POST',
    body: formulario
  });

  if (!respuesta.ok) {
    throw new Error('Error al enviar el video al motor local');
  }

  return await respuesta.json();
}

/**
 * Inicia la tarea de edición automática con los parámetros configurados.
 * @param {string} idVideo - Identificador del video cargado.
 * @param {string} idPlantilla - Identificador de la plantilla seleccionada.
 * @param {object} opcionesAvanzadas - Ajustes de umbrales y características.
 * @returns {Promise<object>}
 */
export async function iniciarProcesamiento(idVideo, idPlantilla, opcionesAvanzadas) {
  const cuerpoPeticion = {
    id_video: idVideo,
    plantilla: idPlantilla,
    ajustes: opcionesAvanzadas
  };

  const respuesta = await fetch(`${URL_BASE_API}/procesar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpoPeticion)
  });

  if (!respuesta.ok) {
    throw new Error('No se pudo iniciar el procesamiento del video');
  }

  return await respuesta.json();
}

/**
 * Consulta el estado y porcentaje de una tarea en proceso.
 * @param {string} idTarea - Identificador de la tarea en ejecución.
 * @returns {Promise<object>}
 */
export async function consultarProgresoTarea(idTarea) {
  const respuesta = await fetch(`${URL_BASE_API}/progreso/${idTarea}`);
  if (!respuesta.ok) {
    throw new Error('Error al consultar el progreso');
  }
  return await respuesta.json();
}
