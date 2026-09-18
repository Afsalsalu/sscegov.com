document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById('searchInput');
    const stateCards = document.querySelectorAll('.state-card');

    searchInput.addEventListener('input', function () {
      const searchQuery = searchInput.value.toLowerCase();

      stateCards.forEach(function (card) {
        const stateName = card.getAttribute('data-state-name').toLowerCase();

        if (stateName.includes(searchQuery)) {
          card.style.display = ''; // Show the card
        } else {
          card.style.display = 'none'; // Hide the card
        }
      });
    });
  });