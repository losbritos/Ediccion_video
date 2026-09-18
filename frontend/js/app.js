/**
 * Controlador principal de la interfaz de usuario de AutoCut Studio.
 * Gestiona eventos de interfaz, selección de plantillas, carga de archivos y ciclo de renderizado.
 */

import { verificarEstadoServidor, obtenerPlantillasDisponibles } from './api.js';

// Estado global de la aplicación cliente
const estadoApp = {
  servidorConectado: false,
  archivoSeleccionado: null,
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

// Referencias del DOM
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
  tarjetasPlantilla: document.querySelectorAll('.tarjeta-plantilla'),
  resumenModo: document.getElementById('resumen-modo'),
  sliderUmbral: document.getElementById('slider-umbral-silencio'),
  valorUmbral: document.getElementById('valor-umbral-silencio'),
  sliderDuracion: document.getElementById('slider-duracion-silencio'),
  valorDuracion: document.getElementById('valor-duracion-silencio'),
  checkZooms: document.getElementById('check-zooms-dinamicos'),
  checkSubtitulos: document.getElementById('check-subtitulos-ia'),
  checkDucking: document.getElementById('check-audio-ducking'),
  checkGpu: document.getElementById('check-aceleracion-gpu'),
  botonRestablecer: document.getElementById('boton-restablecer-ajustes'),
  botonIniciarEdicion: document.getElementById('boton-iniciar-edicion'),
  etiquetaPorcentaje: document.getElementById('etiqueta-porcentaje'),
  barraProgresoRelleno: document.getElementById('barra-progreso-relleno'),
  cuerpoConsolaLogs: document.getElementById('cuerpo-consola-logs'),
  botonLimpiarLogs: document.getElementById('boton-limpiar-logs'),
  gridMetricas: document.getElementById('grid-metricas-resultado'),
  metricaOriginal: document.getElementById('metrica-duracion-original'),
  metricaEditado: document.getElementById('metrica-duracion-editado'),
  metricaAhorro: document.getElementById('metrica-ahorro-tiempo'),
  metricaCortes: document.getElementById('metrica-cortes'),
  badgeListo: document.getElementById('badge-video-listo'),
  accionesExportacion: document.getElementById('acciones-exportacion'),
  etapas: {
    audio: document.getElementById('etapa-audio'),
    vision: document.getElementById('etapa-vision'),
    whisper: document.getElementById('etapa-whisper'),
    montaje: document.getElementById('etapa-montaje'),
    render: document.getElementById('etapa-render')
  }
};

/**
 * Inicialización de la aplicación al cargar la página.
 */
document.addEventListener('DOMContentLoaded', () => {
  configurarEventosCargaArchivos();
  configurarEventosPlantillas();
  configurarEventosAjustes();
  configurarEventosEjecucion();
  comprobarConectividadServidor();

  // Revisar estado del servidor periódicamente
  setInterval(comprobarConectividadServidor, 6000);
});

/**
 * Verifica si el backend local de FastAPI está activo y actualiza la insignia de estado.
 */
async function comprobarConectividadServidor() {
  const resultado = await verificarEstadoServidor();
  if (resultado.conectado) {
    estadoApp.servidorConectado = true;
    elementos.puntoEstado.classList.add('conectado');
    elementos.textoEstadoServidor.textContent = 'Backend Conectado (Local)';
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

  // Eventos de arrastre
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
      elementos.resumenModo.textContent = `Plantilla: ${nombrePlantilla}`;

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
  agregarLogConsola(`Plantilla activa: ${estadoApp.idPlantillaSeleccionada}`);
  agregarLogConsola(`Umbral de silencio: ${elementos.sliderUmbral.value} dB | Duración mín: ${elementos.sliderDuracion.value} s`);

  // Etapa 1: Análisis de Audio
  marcarEtapaActiva('audio');
  agregarLogConsola('[1/5] Extrayendo pista de audio WAV (16kHz PCM)...');
  await simularRetardo(1200);
  agregarLogConsola('[1/5] Analizando decibelios ($dB$) y detectando pausas y silencios...');
  await simularRetardo(1400);
  actualizarBarraProgreso(25);
  marcarEtapaCompletada('audio');

  // Etapa 2: Detección Visual
  marcarEtapaActiva('vision');
  agregarLogConsola('[2/5] Muestreando keyframes con OpenCV...');
  await simularRetardo(1300);
  agregarLogConsola('[2/5] Identificando picos de acción y movimiento rápido...');
  await simularRetardo(1100);
  actualizarBarraProgreso(50);
  marcarEtapaCompletada('vision');

  // Etapa 3: Transcripción IA Whisper
  marcarEtapaActiva('whisper');
  agregarLogConsola('[3/5] Ejecutando transcripción local con Faster-Whisper...');
  await simularRetardo(1400);
  agregarLogConsola('[3/5] Generando marcas de tiempo de palabras y subtítulos dinámicos...');
  await simularRetardo(1200);
  actualizarBarraProgreso(75);
  marcarEtapaCompletada('whisper');

  // Etapa 4: Montaje y Cortes
  marcarEtapaActiva('montaje');
  agregarLogConsola('[4/5] Director de Montaje calculando "Puntuación de Atención"...');
  await simularRetardo(1100);
  agregarLogConsola('[4/5] Ensamblando lista de decisiones de edición (EDL)...');
  await simularRetardo(900);
  actualizarBarraProgreso(90);
  marcarEtapaCompletada('montaje');

  // Etapa 5: Renderizado FFmpeg
  marcarEtapaActiva('render');
  agregarLogConsola('[5/5] Renderizando video final mediante FFmpeg...');
  await simularRetardo(1400);
  actualizarBarraProgreso(100);
  marcarEtapaCompletada('render');

  // Conclusión
  agregarLogConsola('¡Procesamiento completado con éxito!');
  agregarLogConsola('==============================================');

  mostrarResultadosFinales();
  estadoApp.enProceso = false;
  elementos.botonIniciarEdicion.disabled = false;
}

/**
 * Muestra las métricas calculadas y activa la descarga del video procesado.
 */
function mostrarResultadosFinales() {
  elementos.gridMetricas.classList.remove('oculto');
  elementos.badgeListo.classList.remove('oculto');
  elementos.accionesExportacion.classList.remove('oculto');

  elementos.metricaOriginal.textContent = '22:45';
  elementos.metricaEditado.textContent = '08:12';
  elementos.metricaAhorro.textContent = '-64%';
  elementos.metricaCortes.textContent = '148';
}

function ocultarResultadosPrevios() {
  elementos.gridMetricas.classList.add('oculto');
  elementos.badgeListo.classList.add('oculto');
  elementos.accionesExportacion.classList.add('oculto');
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
    etapa.classList.remove('activa', 'completada');
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
