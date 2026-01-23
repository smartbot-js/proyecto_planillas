/**
 * Manejo de Departamentos y Municipios de Nicaragua
 * Archivo: static/js/nicaragua_ubicacion.js
 * 
 * Uso:
 * 1. Incluir este script en el template
 * 2. Llamar inicializarUbicacionNicaragua('id_departamento', 'id_municipio')
 * 3. Opcionalmente pasar el municipio actual para preseleccionar
 */

// Datos de Nicaragua (se cargan una sola vez)
let nicaraguaData = null;

/**
 * Carga los datos de ubicaciones desde la API
 */
async function cargarDatosNicaragua() {
    if (nicaraguaData) return nicaraguaData;
    
    try {
        const response = await fetch('/api/core/ubicaciones/');
        const data = await response.json();
        nicaraguaData = data.data;
        return nicaraguaData;
    } catch (error) {
        console.error('Error cargando datos de Nicaragua:', error);
        return null;
    }
}

/**
 * Actualiza el select de municipios según el departamento seleccionado
 * 
 * @param {string} departamentoSelectId - ID del select de departamento
 * @param {string} municipioSelectId - ID del select de municipio
 * @param {string} municipioActual - Municipio actual para preseleccionar (opcional)
 */
async function actualizarMunicipios(departamentoSelectId, municipioSelectId, municipioActual = '') {
    const departamentoSelect = document.getElementById(departamentoSelectId);
    const municipioSelect = document.getElementById(municipioSelectId);
    
    if (!departamentoSelect || !municipioSelect) {
        console.error('No se encontraron los selects de departamento o municipio');
        return;
    }
    
    const departamento = departamentoSelect.value;
    
    // Limpiar opciones actuales
    municipioSelect.innerHTML = '<option value="">Seleccione un municipio</option>';
    
    if (!departamento) {
        municipioSelect.disabled = true;
        return;
    }
    
    // Cargar datos si no están disponibles
    const data = await cargarDatosNicaragua();
    
    if (!data || !data[departamento]) {
        municipioSelect.disabled = true;
        return;
    }
    
    // Agregar opciones de municipios
    const municipios = data[departamento].sort();
    municipios.forEach(municipio => {
        const option = document.createElement('option');
        option.value = municipio;
        option.textContent = municipio;
        if (municipio === municipioActual) {
            option.selected = true;
        }
        municipioSelect.appendChild(option);
    });
    
    municipioSelect.disabled = false;
}

/**
 * Inicializa la funcionalidad de departamento-municipio
 * 
 * @param {string} departamentoSelectId - ID del select de departamento
 * @param {string} municipioSelectId - ID del select de municipio
 * @param {string} municipioActual - Municipio actual para preseleccionar (opcional)
 */
async function inicializarUbicacionNicaragua(departamentoSelectId, municipioSelectId, municipioActual = '') {
    const departamentoSelect = document.getElementById(departamentoSelectId);
    const municipioSelect = document.getElementById(municipioSelectId);
    
    if (!departamentoSelect || !municipioSelect) {
        console.error('No se encontraron los selects de departamento o municipio');
        return;
    }
    
    // Cargar datos al inicio
    await cargarDatosNicaragua();
    
    // Si hay departamento seleccionado, cargar sus municipios
    if (departamentoSelect.value) {
        await actualizarMunicipios(departamentoSelectId, municipioSelectId, municipioActual);
    } else {
        municipioSelect.disabled = true;
    }
    
    // Escuchar cambios en el departamento
    departamentoSelect.addEventListener('change', () => {
        actualizarMunicipios(departamentoSelectId, municipioSelectId);
    });
}

/**
 * Versión síncrona usando datos precargados en el HTML
 * Usar cuando los datos se pasan como variable JavaScript en el template
 * 
 * @param {string} departamentoSelectId - ID del select de departamento
 * @param {string} municipioSelectId - ID del select de municipio
 * @param {Object} datosNicaragua - Objeto con datos de departamentos y municipios
 * @param {string} municipioActual - Municipio actual para preseleccionar (opcional)
 */
function inicializarUbicacionNicaraguaSync(departamentoSelectId, municipioSelectId, datosNicaragua, municipioActual = '') {
    const departamentoSelect = document.getElementById(departamentoSelectId);
    const municipioSelect = document.getElementById(municipioSelectId);
    
    if (!departamentoSelect || !municipioSelect) {
        console.error('No se encontraron los selects de departamento o municipio');
        return;
    }
    
    function actualizarMunicipiosSync() {
        const departamento = departamentoSelect.value;
        
        // Limpiar opciones actuales
        municipioSelect.innerHTML = '<option value="">Seleccione un municipio</option>';
        
        if (!departamento || !datosNicaragua[departamento]) {
            municipioSelect.disabled = true;
            return;
        }
        
        // Agregar opciones de municipios
        const municipios = datosNicaragua[departamento].sort();
        municipios.forEach(municipio => {
            const option = document.createElement('option');
            option.value = municipio;
            option.textContent = municipio;
            if (municipio === municipioActual) {
                option.selected = true;
            }
            municipioSelect.appendChild(option);
        });
        
        municipioSelect.disabled = false;
    }
    
    // Si hay departamento seleccionado, cargar sus municipios
    if (departamentoSelect.value) {
        actualizarMunicipiosSync();
    } else {
        municipioSelect.disabled = true;
    }
    
    // Escuchar cambios en el departamento
    departamentoSelect.addEventListener('change', actualizarMunicipiosSync);
}
