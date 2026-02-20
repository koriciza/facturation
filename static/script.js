// Print invoice function
function imprimerFacture() {
    window.print();
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR', { 
        style: 'currency', 
        currency: 'EUR' 
    }).format(amount);
}

// Confirm delete
function confirmDelete(message) {
    return confirm(message || 'Êtes-vous sûr de vouloir supprimer ?');
}



// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menuToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', function() {
            this.classList.toggle('active');
            navMenu.classList.toggle('show');
            
            // Update aria-expanded attribute for accessibility
            const isExpanded = navMenu.classList.contains('show');
            menuToggle.setAttribute('aria-expanded', isExpanded);
        });

        // Close menu when clicking on a link (for better UX)
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                menuToggle.classList.remove('active');
                navMenu.classList.remove('show');
                menuToggle.setAttribute('aria-expanded', 'false');
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInside = menuToggle.contains(event.target) || navMenu.contains(event.target);
            
            if (!isClickInside && navMenu.classList.contains('show')) {
                menuToggle.classList.remove('active');
                navMenu.classList.remove('show');
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });

        // Handle window resize
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768 && navMenu.classList.contains('show')) {
                menuToggle.classList.remove('active');
                navMenu.classList.remove('show');
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }
});