/**
 * Manejo de Áreas de Trabajo y Puestos Laborales
 * Archivo: static/js/puestos_laborales.js
 * 
 * Uso:
 * 1. Incluir este script en el template
 * 2. Llamar inicializarPuestosLaborales('id_area_cargo', 'id_puesto_laboral')
 * 3. Opcionalmente pasar el puesto actual para preseleccionar
 */

// Datos de puestos (se cargan una sola vez)
let puestosData = null;

/**
 * Carga los datos de puestos desde la API
 */
async function cargarDatosPuestos() {
    if (puestosData) return puestosData;
    
    try {
        const response = await fetch('/api/core/puestos/');
        const data = await response.json();
        puestosData = data.data;
        return puestosData;
    } catch (error) {
        console.error('Error cargando datos de puestos:', error);
        return null;
    }
}

/**
 * Actualiza el select de puestos según el área seleccionada
 * 
 * @param {string} areaSelectId - ID del select de área
 * @param {string} puestoSelectId - ID del select de puesto
 * @param {string} puestoActual - Puesto actual para preseleccionar (opcional)
 */
async function actualizarPuestos(areaSelectId, puestoSelectId, puestoActual = '') {
    const areaSelect = document.getElementById(areaSelectId);
    const puestoSelect = document.getElementById(puestoSelectId);
    
    if (!areaSelect || !puestoSelect) {
        console.error('No se encontraron los selects de área o puesto');
        return;
    }
    
    const area = areaSelect.value;
    
    // Limpiar opciones actuales
    puestoSelect.innerHTML = '<option value="">Seleccione un puesto</option>';
    
    if (!area) {
        puestoSelect.disabled = true;
        return;
    }
    
    // Cargar datos si no están disponibles
    const data = await cargarDatosPuestos();
    
    if (!data || !data[area]) {
        puestoSelect.disabled = true;
        return;
    }
    
    // Agregar opciones de puestos
    const puestos = data[area].sort();
    puestos.forEach(puesto => {
        const option = document.createElement('option');
        option.value = puesto;
        option.textContent = puesto;
        if (puesto === puestoActual) {
            option.selected = true;
        }
        puestoSelect.appendChild(option);
    });
    
    puestoSelect.disabled = false;
}

/**
 * Inicializa la funcionalidad de área-puesto
 * 
 * @param {string} areaSelectId - ID del select de área
 * @param {string} puestoSelectId - ID del select de puesto
 * @param {string} puestoActual - Puesto actual para preseleccionar (opcional)
 */
async function inicializarPuestosLaborales(areaSelectId, puestoSelectId, puestoActual = '') {
    const areaSelect = document.getElementById(areaSelectId);
    const puestoSelect = document.getElementById(puestoSelectId);
    
    if (!areaSelect || !puestoSelect) {
        console.error('No se encontraron los selects de área o puesto');
        return;
    }
    
    // Cargar datos al inicio
    await cargarDatosPuestos();
    
    // Si hay área seleccionada, cargar sus puestos
    if (areaSelect.value) {
        await actualizarPuestos(areaSelectId, puestoSelectId, puestoActual);
    } else {
        puestoSelect.disabled = true;
    }
    
    // Escuchar cambios en el área
    areaSelect.addEventListener('change', () => {
        actualizarPuestos(areaSelectId, puestoSelectId);
    });
}

/**
 * Versión síncrona usando datos precargados en el HTML
 * Usar cuando los datos se pasan como variable JavaScript en el template
 * 
 * @param {string} areaSelectId - ID del select de área
 * @param {string} puestoSelectId - ID del select de puesto
 * @param {Object} datosPuestos - Objeto con datos de áreas y puestos
 * @param {string} puestoActual - Puesto actual para preseleccionar (opcional)
 */
function inicializarPuestosLaboralesSync(areaSelectId, puestoSelectId, datosPuestos, puestoActual = '') {
    const areaSelect = document.getElementById(areaSelectId);
    const puestoSelect = document.getElementById(puestoSelectId);
    
    if (!areaSelect || !puestoSelect) {
        console.error('No se encontraron los selects de área o puesto');
        return;
    }
    
    function actualizarPuestosSync() {
        const area = areaSelect.value;
        
        // Limpiar opciones actuales
        puestoSelect.innerHTML = '<option value="">Seleccione un puesto</option>';
        
        if (!area || !datosPuestos[area]) {
            puestoSelect.disabled = true;
            return;
        }
        
        // Agregar opciones de puestos
        const puestos = datosPuestos[area].sort();
        puestos.forEach(puesto => {
            const option = document.createElement('option');
            option.value = puesto;
            option.textContent = puesto;
            if (puesto === puestoActual) {
                option.selected = true;
            }
            puestoSelect.appendChild(option);
        });
        
        puestoSelect.disabled = false;
    }
    
    // Si hay área seleccionada, cargar sus puestos
    if (areaSelect.value) {
        actualizarPuestosSync();
    } else {
        puestoSelect.disabled = true;
    }
    
    // Escuchar cambios en el área
    areaSelect.addEventListener('change', actualizarPuestosSync);
}
