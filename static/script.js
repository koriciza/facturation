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