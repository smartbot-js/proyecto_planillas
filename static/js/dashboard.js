// ============================================
// DASHBOARD JS
// ============================================

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard JS loaded successfully');
    
    // Verificar que los modales existen
    const modales = document.querySelectorAll('.modal');
    console.log(`Found ${modales.length} modals`);
});

// ============================================
// MODAL FUNCTIONS
// ============================================

window.showModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        console.log(`Modal ${modalId} opened`);
    } else {
        console.error(`Modal ${modalId} not found`);
    }
}

window.hideModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        console.log(`Modal ${modalId} closed`);
    }
}

// Cerrar modal al hacer clic en overlay
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        const modal = e.target.closest('.modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
});

// Cerrar modal con ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal.active');
        if (activeModal) {
            activeModal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
});

// ============================================
// OTRAS FUNCIONES GLOBALES
// ============================================

// Ejemplo de función para mostrar notificaciones
window.showNotification = function(message, type = 'info') {
    // TODO: Implementar sistema de notificaciones
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// ============================================
// AUTO-DISMISS MESSAGES
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        // Auto-cerrar después de 5 segundos
        setTimeout(() => {
            alert.style.animation = 'fadeOut 0.5s ease-out forwards';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);
    });
});