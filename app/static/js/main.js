document.addEventListener('DOMContentLoaded', function() {
    const swapBtn = document.getElementById('swapCurrencies');
    if (swapBtn) {
        swapBtn.addEventListener('click', function() {
            const fromSelect = document.getElementById('from_currency');
            const toSelect = document.getElementById('to_currency');
            const temp = fromSelect.value;
            fromSelect.value = toSelect.value;
            toSelect.value = temp;
        });
    }
    
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    const fromCurrency = document.getElementById('from_currency');
    const toCurrency = document.getElementById('to_currency');
    
    if (fromCurrency && toCurrency) {
        const savedFrom = localStorage.getItem('lastFromCurrency');
        const savedTo = localStorage.getItem('lastToCurrency');
        
        if (savedFrom) fromCurrency.value = savedFrom;
        if (savedTo) toCurrency.value = savedTo;
        
        fromCurrency.addEventListener('change', function() {
            localStorage.setItem('lastFromCurrency', this.value);
        });
        
        toCurrency.addEventListener('change', function() {
            localStorage.setItem('lastToCurrency', this.value);
        });
    }
    
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(function(link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});