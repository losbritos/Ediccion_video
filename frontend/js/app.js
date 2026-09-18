/**
 * Controlador principal de la interfaz de usuario de AutoCut Studio.
 * Gestiona eventos de interfaz, selector de modos (YouTube Shorts vs Video Completo),
 * configuración de plantillas, carga de archivos, seguimiento del pipeline y galería interactiva.
 */

import {
  verificarEstadoServidor,
  obtenerPlantillasDisponibles,
  subirVideoLocal,
  iniciarProcesamiento,
  consultarProgresoTarea
} from './api.js';

// Estado global de la aplicación cliente
const estadoApp = {
  servidorConectado: false,
  archivoSeleccionado: null,
  modoEdicion: 'shorts', // 'shorts' o 'video_completo'
  cantidadShorts: 3,
  duracionShortSeg: 40,
  formatoVertical: true,
  idPlantillaSeleccionada: 'shooters_highlights',
  enProceso: false,
  ajustes: {
    umbralSilencioDb: -28,
    duracionSilencioSeg: 0.35,
    zoomsDinamicos: true,
    subtitulosIa: true,
    audioDucking: true,
    aceleracionGpu: true
  }
};

// Referencias a los elementos del DOM
const elementos = {
  insigniaServidor: document.getElementById('insignia-servidor'),
  puntoEstado: document.querySelector('.punto-estado'),
  textoEstadoServidor: document.getElementById('texto-estado-servidor'),
  zonaSoltar: document.getElementById('zona-soltar-archivo'),
  inputArchivo: document.getElementById('entrada-archivo-video'),
  botonSeleccionarVideo: document.getElementById('boton-seleccionar-video'),
  tarjetaArchivoCargado: document.getElementById('tarjeta-archivo-cargado'),
  nombreArchivo: document.getElementById('nombre-archivo-seleccionado'),
  tamanoArchivo: document.getElementById('tamano-archivo-seleccionado'),
  botonQuitarVideo: document.getElementById('boton-quitar-video'),

  // Modos de Edición
  tarjetasModo: document.querySelectorAll('.tarjeta-modo'),
  panelAjustesShorts: document.getElementById('panel-ajustes-shorts'),
  btnsCantidadShorts: document.querySelectorAll('#selector-cantidad-shorts .btn-opcion'),
  btnsDuracionShorts: document.querySelectorAll('#selector-duracion-shorts .btn-opcion'),
  tarjetasFormato: document.querySelectorAll('.tarjeta-formato'),

  // Plantillas
  tarjetasPlantilla: document.querySelectorAll('.tarjeta-plantilla'),
  resumenModo: document.getElementById('resumen-modo'),

  // Ajustes de Silencio y Efectos
  sliderUmbral: document.getElementById('slider-umbral-silencio'),
  valorUmbral: document.getElementById('valor-umbral-silencio'),
  sliderDuracion: document.getElementById('slider-duracion-silencio'),
  valorDuracion: document.getElementById('valor-duracion-silencio'),
  checkZooms: document.getElementById('check-zooms-dinamicos'),
  checkSubtitulos: document.getElementById('check-subtitulos-ia'),
  checkDucking: document.getElementById('check-audio-ducking'),
  checkGpu: document.getElementById('check-aceleracion-gpu'),
  botonRestablecer: document.getElementById('boton-restablecer-ajustes'),

  // Ejecución y Progreso
  botonIniciarEdicion: document.getElementById('boton-iniciar-edicion'),
  textoBotonIniciar: document.getElementById('texto-boton-iniciar'),
  etiquetaPorcentaje: document.getElementById('etiqueta-porcentaje'),
  barraProgresoRelleno: document.getElementById('barra-progreso-relleno'),
  cuerpoConsolaLogs: document.getElementById('cuerpo-consola-logs'),
  botonLimpiarLogs: document.getElementById('boton-limpiar-logs'),

  // Reproductor y Resultados
  placeholderReproductor: document.getElementById('placeholder-reproductor'),
  textoPlaceholderReproductor: document.getElementById('texto-placeholder-reproductor'),
  reproductorVideoFinal: document.getElementById('reproductor-video-final'),
  seccionShortsGenerados: document.getElementById('seccion-shorts-generados'),
  contenedorTarjetasShorts: document.getElementById('contenedor-tarjetas-shorts'),
  conteoShortsGenerados: document.getElementById('conteo-shorts-generados'),
  gridMetricas: document.getElementById('grid-metricas-resultado'),
  metricaOriginal: document.getElementById('metrica-duracion-original'),
  metricaEditado: document.getElementById('metrica-duracion-editado'),
  metricaAhorro: document.getElementById('metrica-ahorro-tiempo'),
  metricaCortes: document.getElementById('metrica-cortes'),
  badgeListo: document.getElementById('badge-video-listo'),
  accionesExportacion: document.getElementById('acciones-exportacion'),
  enlaceDescargaVideo: document.getElementById('enlace-descarga-video'),

  etapas: {
    audio: document.getElementById('etapa-audio'),
    vision: document.getElementById('etapa-vision'),
    whisper: document.getElementById('etapa-whisper'),
    montaje: document.getElementById('etapa-montaje'),
    render: document.getElementById('etapa-render')
  }
};

/**
 * Inicialización al cargar la página.
 */
document.addEventListener('DOMContentLoaded', () => {
  configurarEventosCargaArchivos();
  configurarEventosModosEdicion();
  configurarEventosPlantillas();
  configurarEventosAjustes();
  configurarEventosEjecucion();
  actualizarTextoResumenModo();
  comprobarConectividadServidor();

  // Comprobar estado del servidor en segundo plano
  setInterval(comprobarConectividadServidor, 6000);
});

/**
 * Verifica si el backend FastAPI está activo y actualiza la insignia visual.
 */
async function comprobarConectividadServidor() {
  const resultado = await verificarEstadoServidor();
  if (resultado.conectado) {
    estadoApp.servidorConectado = true;
    elementos.puntoEstado.classList.add('conectado');
    const gpuInfo = resultado.datos?.aceleracion_disponible ? ' (GPU NVIDIA activa)' : ' (CPU)';
    elementos.textoEstadoServidor.textContent = `Backend Conectado${gpuInfo}`;
  } else {
    estadoApp.servidorConectado = false;
    elementos.puntoEstado.classList.remove('conectado');
    elementos.textoEstadoServidor.textContent = 'Modo Local Autónomo';
  }
}

/**
 * Configuración de la zona de soltar archivos (Drag & Drop) y selección manual.
 */
function configurarEventosCargaArchivos() {
  elementos.botonSeleccionarVideo.addEventListener('click', () => {
    elementos.inputArchivo.click();
  });

  elementos.inputArchivo.addEventListener('change', (evento) => {
    const archivos = evento.target.files;
    if (archivos && archivos.length > 0) {
      registrarArchivoSeleccionado(archivos[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(nombreEvento => {
    elementos.zonaSoltar.addEventListener(nombreEvento, (evento) => {
      evento.preventDefault();
      evento.stopPropagation();
      elementos.zonaSoltar.classList.add('arrastrando');
    });
  });

  ['dragleave', 'drop'].forEach(nombreEvento => {
    elementos.zonaSoltar.addEventListener(nombreEvento, (evento) => {
      evento.preventDefault();
      evento.stopPropagation();
      elementos.zonaSoltar.classList.remove('arrastrando');
    });
  });

  elementos.zonaSoltar.addEventListener('drop', (evento) => {
    const archivos = evento.dataTransfer.files;
    if (archivos && archivos.length > 0) {
      registrarArchivoSeleccionado(archivos[0]);
    }
  });

  elementos.botonQuitarVideo.addEventListener('click', () => {
    estadoApp.archivoSeleccionado = null;
    elementos.inputArchivo.value = '';
    elementos.zonaSoltar.classList.remove('oculto');
    elementos.tarjetaArchivoCargado.classList.add('oculto');
    agregarLogConsola('Video retirado. Seleccione otro archivo para continuar.');
  });
}

/**
 * Registra y visualiza el archivo de video en la interfaz.
 * @param {File} archivo - Archivo de video.
 */
function registrarArchivoSeleccionado(archivo) {
  estadoApp.archivoSeleccionado = archivo;
  elementos.nombreArchivo.textContent = archivo.name;
  elementos.tamanoArchivo.textContent = formatearTamanoBytes(archivo.size);

  elementos.zonaSoltar.classList.add('oculto');
  elementos.tarjetaArchivoCargado.classList.remove('oculto');

  agregarLogConsola(`Video cargado: "${archivo.name}" (${formatearTamanoBytes(archivo.size)})`);
  activarPasoVisual(2);
}

/**
 * Configuración del selector de Modos de Edición (Shorts vs Video Completo) y opciones de Shorts.
 */
function configurarEventosModosEdicion() {
  // Selector principal de modo
  elementos.tarjetasModo.forEach(tarjeta => {
    tarjeta.addEventListener('click', () => {
      elementos.tarjetasModo.forEach(t => t.classList.remove('seleccionada'));
      tarjeta.classList.add('seleccionada');

      const modo = tarjeta.dataset.modo;
      estadoApp.modoEdicion = modo;

      if (modo === 'shorts') {
        elementos.panelAjustesShorts.classList.remove('oculto');
        elementos.textoBotonIniciar.textContent = 'Iniciar Generación de Shorts';
        agregarLogConsola('Modo cambiado a: Generador de YouTube Shorts (clips de momentos cumbre).');
      } else {
        elementos.panelAjustesShorts.classList.add('oculto');
        elementos.textoBotonIniciar.textContent = 'Iniciar Edición Automática';
        agregarLogConsola('Modo cambiado a: Video Completo Continuo (corte de pausas).');
      }

      actualizarTextoResumenModo();
    });
  });

  // Selector de cantidad de Shorts
  elementos.btnsCantidadShorts.forEach(btn => {
    btn.addEventListener('click', () => {
      elementos.btnsCantidadShorts.forEach(b => b.classList.remove('activo'));
      btn.classList.add('activo');
      estadoApp.cantidadShorts = parseInt(btn.dataset.cantidad, 10);
      actualizarTextoResumenModo();
      agregarLogConsola(`Cantidad de Shorts configurada en: ${estadoApp.cantidadShorts}`);
    });
  });

  // Selector de duración por Short
  elementos.btnsDuracionShorts.forEach(btn => {
    btn.addEventListener('click', () => {
      elementos.btnsDuracionShorts.forEach(b => b.classList.remove('activo'));
      btn.classList.add('activo');
      estadoApp.duracionShortSeg = parseFloat(btn.dataset.duracion);
      actualizarTextoResumenModo();
      agregarLogConsola(`Duración objetivo por Short: ${estadoApp.duracionShortSeg} segundos`);
    });
  });

  // Selector de formato de pantalla (Vertical 9:16 vs Panorámico 16:9)
  elementos.tarjetasFormato.forEach(tarjeta => {
    tarjeta.addEventListener('click', () => {
      elementos.tarjetasFormato.forEach(t => t.classList.remove('activo'));
      tarjeta.classList.add('activo');

      const esVertical = tarjeta.dataset.formato === 'vertical';
      estadoApp.formatoVertical = esVertical;
      actualizarTextoResumenModo();
      agregarLogConsola(`Formato de video configurado en: ${esVertical ? 'Vertical 9:16 (Shorts/TikTok)' : 'Panorámico 16:9'}`);
    });
  });
}

/**
 * Actualiza el encabezado de resumen en la tarjeta de inicio.
 */
function actualizarTextoResumenModo() {
  if (estadoApp.modoEdicion === 'shorts') {
    const formato = estadoApp.formatoVertical ? 'Vertical 9:16' : '16:9';
    elementos.resumenModo.textContent = `YouTube Shorts: ${estadoApp.cantidadShorts} clips (${formato}, ~${estadoApp.duracionShortSeg}s c/u)`;
  } else {
    elementos.resumenModo.textContent = `Video Completo: ${obtenerNombrePlantillaActual()}`;
  }
}

function obtenerNombrePlantillaActual() {
  const tarjetaSel = document.querySelector('.tarjeta-plantilla.seleccionada');
  return tarjetaSel ? tarjetaSel.querySelector('.nombre-plantilla').textContent : 'Gaming';
}

/**
 * Configuración de las tarjetas de selección de estilo/plantilla.
 */
function configurarEventosPlantillas() {
  elementos.tarjetasPlantilla.forEach(tarjeta => {
    tarjeta.addEventListener('click', () => {
      elementos.tarjetasPlantilla.forEach(t => t.classList.remove('seleccionada'));
      tarjeta.classList.add('seleccionada');

      const idPlantilla = tarjeta.dataset.plantilla;
      estadoApp.idPlantillaSeleccionada = idPlantilla;

      const nombrePlantilla = tarjeta.querySelector('.nombre-plantilla').textContent;
      actualizarTextoResumenModo();
      aplicarValoresPredeterminadosPlantilla(idPlantilla);
      agregarLogConsola(`Plantilla cambiada a: ${nombrePlantilla}`);
    });
  });
}

/**
 * Ajusta los controles deslizantes según el perfil de la plantilla seleccionada.
 * @param {string} idPlantilla - ID de la plantilla.
 */
function aplicarValoresPredeterminadosPlantilla(idPlantilla) {
  if (idPlantilla === 'shooters_highlights') {
    elementos.sliderUmbral.value = -28;
    elementos.valorUmbral.textContent = '-28 dB';
    elementos.sliderDuracion.value = 0.35;
    elementos.valorDuracion.textContent = '0.35 s';
    elementos.checkZooms.checked = true;
  } else if (idPlantilla === 'gameplay_narrado') {
    elementos.sliderUmbral.value = -32;
    elementos.valorUmbral.textContent = '-32 dB';
    elementos.sliderDuracion.value = 0.8;
    elementos.valorDuracion.textContent = '0.80 s';
    elementos.checkZooms.checked = true;
  } else if (idPlantilla === 'tutorial_educativo') {
    elementos.sliderUmbral.value = -34;
    elementos.valorUmbral.textContent = '-34 dB';
    elementos.sliderDuracion.value = 0.7;
    elementos.valorDuracion.textContent = '0.70 s';
    elementos.checkZooms.checked = false;
  }
}

/**
 * Configura los eventos de los sliders y checkboxes de ajustes avanzados.
 */
function configurarEventosAjustes() {
  elementos.sliderUmbral.addEventListener('input', (e) => {
    elementos.valorUmbral.textContent = `${e.target.value} dB`;
    estadoApp.ajustes.umbralSilencioDb = parseFloat(e.target.value);
  });

  elementos.sliderDuracion.addEventListener('input', (e) => {
    const valor = parseFloat(e.target.value).toFixed(2);
    elementos.valorDuracion.textContent = `${valor} s`;
    estadoApp.ajustes.duracionSilencioSeg = parseFloat(valor);
  });

  elementos.checkSubtitulos.addEventListener('change', (e) => {
    estadoApp.ajustes.subtitulosIa = e.target.checked;
    agregarLogConsola(`Subtítulos dinámicos de IA: ${e.target.checked ? 'Activados' : 'Desactivados'}`);
  });

  elementos.botonRestablecer.addEventListener('click', () => {
    aplicarValoresPredeterminadosPlantilla(estadoApp.idPlantillaSeleccionada);
    agregarLogConsola('Ajustes restablecidos a los valores predeterminados del perfil.');
  });
}

/**
 * Configura el botón de arranque del pipeline de edición.
 */
function configurarEventosEjecucion() {
  elementos.botonLimpiarLogs.addEventListener('click', () => {
    elementos.cuerpoConsolaLogs.textContent = '> Consola vacía.\n';
  });

  elementos.botonIniciarEdicion.addEventListener('click', () => {
    if (!estadoApp.archivoSeleccionado) {
      alert('Por favor, selecciona o arrastra primero un archivo de video para comenzar.');
      return;
    }
    iniciarFlujoEdicion();
  });
}

/**
 * Orquesta la ejecución del pipeline (vía backend o simulación demostrativa).
 */
async function iniciarFlujoEdicion() {
  estadoApp.enProceso = true;
  elementos.botonIniciarEdicion.disabled = true;
  activarPasoVisual(4);

  // Reiniciar estado visual de progreso
  actualizarBarraProgreso(0);
  limpiarEstadosEtapas();
  ocultarResultadosPrevios();

  agregarLogConsola('==============================================');
  agregarLogConsola(`Iniciando AutoCut Studio en "${estadoApp.archivoSeleccionado.name}"`);
  agregarLogConsola(`Modo: ${estadoApp.modoEdicion.toUpperCase()} | Plantilla: ${estadoApp.idPlantillaSeleccionada}`);

  if (estadoApp.servidorConectado) {
    try {
      // 1. Subida al backend con reporte visual de progreso
      marcarEtapaActiva('audio');
      agregarLogConsola(`Transfiriendo video al motor local (${formatearTamanoBytes(estadoApp.archivoSeleccionado.size)})...`);

      const datosSubida = await subirVideoLocal(estadoApp.archivoSeleccionado, (porcentajeSubida) => {
        elementos.textoEstadoServidor.textContent = `Subiendo archivo: ${porcentajeSubida}%`;
        if (porcentajeSubida % 25 === 0 && porcentajeSubida > 0 && porcentajeSubida < 100) {
          agregarLogConsola(`Progreso de subida: ${porcentajeSubida}%`);
        }
      });

      elementos.textoEstadoServidor.textContent = 'Backend Conectado (Local)';
      agregarLogConsola(`Video registrado con éxito: "${datosSubida.nombre}" (ID: ${datosSubida.id_video})`);

      // 2. Iniciar tarea con todos los parámetros
      const datosTarea = await iniciarProcesamiento({
        idVideo: datosSubida.id_video,
        modoEdicion: estadoApp.modoEdicion,
        plantilla: estadoApp.idPlantillaSeleccionada,
        cantidadShorts: estadoApp.cantidadShorts,
        duracionShortSeg: estadoApp.duracionShortSeg,
        formatoVertical: estadoApp.formatoVertical,
        incluirSubtitulos: estadoApp.ajustes.subtitulosIa,
        ajustes: {
          ajustes_audio: {
            umbral_silencio_db: estadoApp.ajustes.umbralSilencioDb,
            duracion_minima_silencio_segundos: estadoApp.ajustes.duracionSilencioSeg
          }
        }
      });

      const idTarea = datosTarea.id_tarea;
      agregarLogConsola(`Tarea encolada con ID: ${idTarea}`);

      // 3. Polling de progreso
      let terminado = false;
      let ultimoIndiceLog = 0;

      while (!terminado) {
        await simularRetardo(700);
        const estadoTarea = await consultarProgresoTarea(idTarea);

        actualizarBarraProgreso(estadoTarea.progreso || 0);

        if (estadoTarea.etapa) {
          marcarEtapaActiva(estadoTarea.etapa);
        }

        // Transmitir nuevos logs a la terminal visual
        const nuevosLogs = estadoTarea.logs || [];
        for (let i = ultimoIndiceLog; i < nuevosLogs.length; i++) {
          agregarLogConsola(nuevosLogs[i]);
        }
        ultimoIndiceLog = nuevosLogs.length;

        if (estadoTarea.estado === 'completado') {
          terminado = true;
          marcarEtapaCompletada('render');
          const res = estadoTarea.resultado || {};

          if (estadoTarea.modo_edicion === 'shorts' || res.modo === 'shorts') {
            mostrarResultadosShorts(res.shorts || [], idTarea);
          } else {
            mostrarResultadosFinales({
              duracionOriginal: res.duracion_original ? `${res.duracion_original}s` : '00:00',
              duracionEditado: res.duracion_final_estimada ? `${res.duracion_final_estimada}s` : '00:00',
              ahorro: res.ahorro_tiempo_porcentaje ? `-${res.ahorro_tiempo_porcentaje}%` : '0%',
              cortes: res.cantidad_cortes || 0,
              urlDescarga: `http://127.0.0.1:8000/api/descargar/${idTarea}`
            });
          }
        } else if (estadoTarea.estado === 'error') {
          throw new Error(estadoTarea.error || 'Error desconocido en el procesamiento');
        }
      }
    } catch (err) {
      agregarLogConsola(`[ERROR]: ${err.message}`);
      alert(`Error durante el procesamiento: ${err.message}`);
    }
  } else {
    // Modo demostrativo local (cuando el backend no está iniciado)
    await ejecutarSimulacionDemostrativa();
  }

  estadoApp.enProceso = false;
  elementos.botonIniciarEdicion.disabled = false;
}

/**
 * Simulación visual fluida para exploración sin backend encendido.
 */
async function ejecutarSimulacionDemostrativa() {
  marcarEtapaActiva('audio');
  agregarLogConsola('[1/5] Extrayendo pista de audio WAV y analizando energía...');
  await simularRetardo(1000);
  actualizarBarraProgreso(25);
  marcarEtapaCompletada('audio');

  marcarEtapaActiva('vision');
  agregarLogConsola('[2/5] Muestreando keyframes con OpenCV para medir intensidad visual...');
  await simularRetardo(1000);
  actualizarBarraProgreso(50);
  marcarEtapaCompletada('vision');

  marcarEtapaActiva('whisper');
  agregarLogConsola('[3/5] Transcribiendo diálogos con Faster-Whisper para subtítulos dinámicos...');
  await simularRetardo(1000);
  actualizarBarraProgreso(75);
  marcarEtapaCompletada('whisper');

  marcarEtapaActiva('montaje');
  agregarLogConsola('[4/5] Director de Montaje seleccionando los momentos cumbre...');
  await simularRetardo(800);
  actualizarBarraProgreso(90);
  marcarEtapaCompletada('montaje');

  marcarEtapaActiva('render');
  agregarLogConsola('[5/5] Renderizando clips con FFmpeg y quemando subtítulos...');
  await simularRetardo(1000);
  actualizarBarraProgreso(100);
  marcarEtapaCompletada('render');

  agregarLogConsola('¡Procesamiento demostrativo completado con éxito!');

  if (estadoApp.modoEdicion === 'shorts') {
    const shortsDemo = [
      { indice: 1, tiempo_formateado: '02:40', duracion: 35, puntuacion_atencion: 94.2, formato: '9:16 Vertical', nombre_archivo: 'short_1.mp4', url_descarga: '#' },
      { indice: 2, tiempo_formateado: '07:15', duracion: 40, puntuacion_atencion: 89.6, formato: '9:16 Vertical', nombre_archivo: 'short_2.mp4', url_descarga: '#' },
      { indice: 3, tiempo_formateado: '14:50', duracion: 35, puntuacion_atencion: 86.4, formato: '9:16 Vertical', nombre_archivo: 'short_3.mp4', url_descarga: '#' }
    ];
    mostrarResultadosShorts(shortsDemo, 'demo');
  } else {
    mostrarResultadosFinales({
      duracionOriginal: '22:45',
      duracionEditado: '08:12',
      ahorro: '-64%',
      cortes: '148',
      urlDescarga: '#'
    });
  }
}

/**
 * Renderiza la galería interactiva de Shorts generados con previsualización y descarga.
 * @param {Array<object>} shorts - Lista de shorts generados con metadatos.
 * @param {string} idTarea - Identificador de la tarea para URLs de descarga.
 */
function mostrarResultadosShorts(shorts, idTarea) {
  elementos.badgeListo.classList.remove('oculto');
  elementos.gridMetricas.classList.add('oculto');
  elementos.accionesExportacion.classList.add('oculto');
  elementos.seccionShortsGenerados.classList.remove('oculto');

  elementos.conteoShortsGenerados.textContent = shorts.length;
  elementos.contenedorTarjetasShorts.innerHTML = '';

  if (!shorts || shorts.length === 0) {
    elementos.contenedorTarjetasShorts.innerHTML = '<p class="texto-secundario">No se generaron shorts para este video.</p>';
    return;
  }

  shorts.forEach((short, idx) => {
    const urlDescarga = short.url_descarga
      ? (short.url_descarga.startsWith('http') ? short.url_descarga : `http://127.0.0.1:8000${short.url_descarga}`)
      : `http://127.0.0.1:8000/api/descargar_short/${idTarea}/${short.indice}`;

    const tarjeta = document.createElement('div');
    tarjeta.className = `tarjeta-short-item ${idx === 0 ? 'activo' : ''}`;
    tarjeta.dataset.indice = short.indice;
    tarjeta.dataset.url = urlDescarga;

    tarjeta.innerHTML = `
      <div class="info-short-item">
        <span class="badge-indice-short">#${short.indice}</span>
        <div class="detalles-short-item">
          <span class="titulo-short-item">Short #${short.indice} • Minuto ${short.tiempo_formateado || '00:00'}</span>
          <div class="meta-tags-short">
            <span class="tag-short score">Puntuación: ${short.puntuacion_atencion}</span>
            <span class="tag-short">${short.duracion}s</span>
            <span class="tag-short formato">${short.formato || '9:16'}</span>
          </div>
        </div>
      </div>
      <div class="acciones-short-item">
        <button type="button" class="btn-short-accion btn-short-ver" title="Reproducir en el visor">
          ▶ Ver en Visor
        </button>
        <a href="${urlDescarga}" class="btn-short-accion btn-short-descargar" download="${short.nombre_archivo || `short_${short.indice}.mp4`}" title="Descargar archivo MP4">
          ⬇ Descargar
        </a>
      </div>
    `;

    // Evento de reproducción al hacer clic en la tarjeta o en el botón ver
    const activarEsteShort = () => {
      document.querySelectorAll('.tarjeta-short-item').forEach(t => t.classList.remove('activo'));
      tarjeta.classList.add('activo');
      cargarVideoEnReproductor(urlDescarga);
    };

    tarjeta.addEventListener('click', (e) => {
      // Evitar que el clic en el botón de descarga dispare la selección de tarjeta
      if (!e.target.closest('.btn-short-descargar')) {
        activarEsteShort();
      }
    });

    elementos.contenedorTarjetasShorts.appendChild(tarjeta);
  });

  // Cargar automáticamente el primer Short en el reproductor
  const primeraUrl = shorts[0].url_descarga
    ? (shorts[0].url_descarga.startsWith('http') ? shorts[0].url_descarga : `http://127.0.0.1:8000${shorts[0].url_descarga}`)
    : `http://127.0.0.1:8000/api/descargar_short/${idTarea}/${shorts[0].indice}`;

  cargarVideoEnReproductor(primeraUrl);
}

/**
 * Carga un video en el reproductor HTML5 y lo reproduce.
 * @param {string} urlVideo - URL del video a cargar.
 */
function cargarVideoEnReproductor(urlVideo) {
  if (elementos.placeholderReproductor) {
    elementos.placeholderReproductor.classList.add('oculto');
  }
  if (elementos.reproductorVideoFinal) {
    elementos.reproductorVideoFinal.classList.remove('oculto');
    elementos.reproductorVideoFinal.src = urlVideo;
    elementos.reproductorVideoFinal.load();
    elementos.reproductorVideoFinal.play().catch(() => {
      // Ignorar si el navegador bloquea autoplay sin interacción previa
    });
  }
}

/**
 * Muestra las métricas calculadas para video completo y activa la descarga.
 */
function mostrarResultadosFinales(datosMetricas) {
  elementos.seccionShortsGenerados.classList.add('oculto');
  elementos.gridMetricas.classList.remove('oculto');
  elementos.badgeListo.classList.remove('oculto');
  elementos.accionesExportacion.classList.remove('oculto');

  elementos.metricaOriginal.textContent = datosMetricas.duracionOriginal;
  elementos.metricaEditado.textContent = datosMetricas.duracionEditado;
  elementos.metricaAhorro.textContent = datosMetricas.ahorro;
  elementos.metricaCortes.textContent = datosMetricas.cortes;

  if (datosMetricas.urlDescarga && datosMetricas.urlDescarga !== '#') {
    if (elementos.enlaceDescargaVideo) {
      elementos.enlaceDescargaVideo.href = datosMetricas.urlDescarga;
    }
    cargarVideoEnReproductor(datosMetricas.urlDescarga);
  }
}

function ocultarResultadosPrevios() {
  elementos.gridMetricas.classList.add('oculto');
  elementos.badgeListo.classList.add('oculto');
  elementos.accionesExportacion.classList.add('oculto');
  elementos.seccionShortsGenerados.classList.add('oculto');
}

function actualizarBarraProgreso(porcentaje) {
  elementos.barraProgresoRelleno.style.width = `${porcentaje}%`;
  elementos.etiquetaPorcentaje.textContent = `${porcentaje}%`;
}

function marcarEtapaActiva(nombreEtapa) {
  if (elementos.etapas[nombreEtapa]) {
    elementos.etapas[nombreEtapa].classList.add('activa');
    elementos.etapas[nombreEtapa].classList.remove('completada');
  }
}

function marcarEtapaCompletada(nombreEtapa) {
  if (elementos.etapas[nombreEtapa]) {
    elementos.etapas[nombreEtapa].classList.remove('activa');
    elementos.etapas[nombreEtapa].classList.add('completada');
  }
}

function limpiarEstadosEtapas() {
  Object.values(elementos.etapas).forEach(etapa => {
    if (etapa) etapa.classList.remove('activa', 'completada');
  });
}

function activarPasoVisual(numeroPaso) {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`indicador-paso-${i}`);
    if (el) {
      if (i <= numeroPaso) el.classList.add('activo');
      else el.classList.remove('activo');
    }
  }
}

function agregarLogConsola(mensaje) {
  const marcaTiempo = new Date().toLocaleTimeString();
  elementos.cuerpoConsolaLogs.textContent += `[${marcaTiempo}] ${mensaje}\n`;
  elementos.cuerpoConsolaLogs.scrollTop = elementos.cuerpoConsolaLogs.scrollHeight;
}

function formatearTamanoBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const unidades = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + unidades[i];
}

function simularRetardo(milisegundos) {
  return new Promise(resolver => setTimeout(resolver, milisegundos));
}
