document.addEventListener('DOMContentLoaded', function () {
    var deleteButtons = document.querySelectorAll('.delete-state-btn');

    deleteButtons.forEach(function (button) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            var url = button.getAttribute('href');

            // Use the native confirm dialog
            var isConfirmed = window.confirm("Are you sure you want to delete this state? This action cannot be undone.");

            if (isConfirmed) {
                window.location.href = url;
            }
        });
    });
});
