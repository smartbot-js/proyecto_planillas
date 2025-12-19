// ============================================
// DASHBOARD JS v3.0 (Sidebar Blanco Responsivo)
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    const body = document.body;
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle');
    
    // --- LÓGICA DE SIDEBAR ---

    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            const isMobile = window.innerWidth <= 1024;
            
            if (isMobile) {
                // En móvil, activa el overlay
                body.classList.toggle('sidebar-mobile-open');
            } else {
                // En desktop, colapsa el menú
                body.classList.toggle('sidebar-collapsed-desktop');
            }
        });
    }

    // --- CERRAR SIDEBAR MÓVIL AL CLICAR FUERA ---
    document.addEventListener('click', function(e) {
        // Si el menú móvil está abierto y se hace clic *fuera* del sidebar
        if (body.classList.contains('sidebar-mobile-open') && !e.target.closest('.sidebar') && !e.target.closest('#sidebar-toggle')) {
            e.preventDefault();
            body.classList.remove('sidebar-mobile-open');
        }
    });


    // --- MANEJO DE MODALES ---
    window.showModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        } else {
            console.error(`Modal ${modalId} not found`);
        }
    }

    window.hideModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    // Cerrar modal al hacer clic en overlay (global)
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-overlay')) {
            e.target.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Cerrar modal con ESC (global)
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal-overlay.active');
            if (activeModal) {
                activeModal.classList.remove('active');
                document.body.style.overflow = '';
            }
        }
    });


    // --- AUTO-DESCARTAR ALERTAS (MENSAJES) ---
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    
    alerts.forEach(alert => {
        // Auto-cerrar después de 5 segundos
        setTimeout(() => {
            alert.style.animation = 'fadeOut 0.5s ease-out forwards';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000);

        // Cierre manual con el botón
        const closeButton = alert.querySelector('.alert-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                alert.style.animation = 'fadeOut 0.3s ease-out forwards';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            });
        }
    });

});

// ===================================
// FUNCIÓN PARA TOGGLE DEL SUBMENÚ
// ===================================

// Al final del archivo dashboard.js

function toggleSubmenu(element) {
    element.classList.toggle('open');
    const submenu = element.nextElementSibling;
    submenu.classList.toggle('open');
    
    // Cerrar otros submenus
    const allParents = document.querySelectorAll('.nav-item-parent');
    allParents.forEach(parent => {
        if (parent !== element && parent.classList.contains('open')) {
            parent.classList.remove('open');
            parent.nextElementSibling.classList.remove('open');
        }
    });
}

// Auto-abrir si hay página activa
document.addEventListener('DOMContentLoaded', function() {
    const activeSubitem = document.querySelector('.nav-subitem.active');
    if (activeSubitem) {
        const submenu = activeSubitem.closest('.nav-submenu');
        const parent = submenu.previousElementSibling;
        parent.classList.add('open');
        submenu.classList.add('open');
    }
});