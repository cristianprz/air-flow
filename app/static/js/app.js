/* AirFlow Lite — Main JavaScript */

// Auto-dismiss flash alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    let alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            let bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Confirm before executing scripts
document.querySelectorAll('form[action*="/execute"]').forEach(function(form) {
    form.addEventListener('submit', function(e) {
        // Only ask for confirmation if not already running
        let btn = form.querySelector('button[type="submit"]');
        if (btn && btn.disabled) {
            e.preventDefault();
            return;
        }
    });
});
