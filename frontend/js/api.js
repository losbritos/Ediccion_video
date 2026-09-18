/**
 * Módulo de comunicación con el Backend local (FastAPI).
 * Provee funciones asíncronas para consultar estado, obtener plantillas y orquestar tareas.
 */

const URL_BASE_API = (typeof window !== 'undefined' && window.location.protocol.startsWith('http'))
  ? `${window.location.origin}/api`
  : 'http://127.0.0.1:8000/api';

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
 * Envía un archivo de video al backend para su análisis local con seguimiento de subida.
 * @param {File} archivoVideo - Objeto File seleccionado por el usuario.
 * @param {Function} [callbackProgresoSubida] - Función opcional que recibe el porcentaje (0-100).
 * @returns {Promise<object>}
 */
export function subirVideoLocal(archivoVideo, callbackProgresoSubida) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formulario = new FormData();
    formulario.append('archivo', archivoVideo);

    if (xhr.upload && callbackProgresoSubida) {
      xhr.upload.onprogress = (evento) => {
        if (evento.lengthComputable) {
          const porcentaje = Math.round((evento.loaded / evento.total) * 100);
          callbackProgresoSubida(porcentaje);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const respuesta = JSON.parse(xhr.responseText);
          resolve(respuesta);
        } catch (e) {
          reject(new Error('Respuesta no válida del servidor'));
        }
      } else {
        reject(new Error(`El servidor respondió con código ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Fallo de red al enviar el archivo al servidor local'));
    xhr.open('POST', `${URL_BASE_API}/subir`);
    xhr.send(formulario);
  });
}

/**
 * Inicia la tarea de edición automática con los parámetros configurados.
 * @param {object} opciones - Parámetros de procesamiento (id_video, modo_edicion, plantilla, etc.).
 * @returns {Promise<object>}
 */
export async function iniciarProcesamiento(opciones) {
  const cuerpoPeticion = {
    id_video: opciones.idVideo || opciones.id_video,
    modo_edicion: opciones.modoEdicion || opciones.modo_edicion || 'shorts',
    plantilla: opciones.plantilla || 'shooters_highlights',
    cantidad_shorts: opciones.cantidadShorts || 3,
    duracion_short_seg: opciones.duracionShortSeg || 35.0,
    formato_vertical: opciones.formatoVertical !== undefined ? opciones.formatoVertical : true,
    incluir_subtitulos: opciones.incluirSubtitulos !== undefined ? opciones.incluirSubtitulos : true,
    ajustes: opciones.ajustes || null
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
