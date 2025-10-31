document.addEventListener('DOMContentLoaded', () => {
    // Para cerrar alertas
    document.querySelectorAll('.alert-close').forEach(button => {
        button.addEventListener('click', () => {
            button.closest('.alert').remove();
        });
    });

    // Manejo del sidebar en móvil (colapsar/expandir)
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const body = document.body;

    // Puedes añadir un botón para togglear el sidebar si lo necesitas,
    // o simplemente hacerlo responsivo vía CSS.
    // Por ahora, el CSS se encarga del colapsado en pantallas pequeñas.

    // Si quieres un botón de toggle (opcional):
    // const toggleButton = document.querySelector('.sidebar-toggle-btn');
    // if (toggleButton) {
    //     toggleButton.addEventListener('click', () => {
    //         sidebar.classList.toggle('collapsed');
    //         mainContent.classList.toggle('sidebar-collapsed');
    //         body.classList.toggle('sidebar-collapsed');
    //     });
    // }
});