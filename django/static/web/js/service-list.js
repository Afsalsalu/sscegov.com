document.addEventListener("DOMContentLoaded", function () {
    const searchBar = document.getElementById("searchBar");
    const serviceCards = document.querySelectorAll(".card");

    searchBar.addEventListener("input", function () {
      const query = searchBar.value.toLowerCase().trim();
      serviceCards.forEach(card => {
        const serviceName = card.querySelector("h5").textContent.toLowerCase();
        if (serviceName.includes(query)) {
          card.style.display = ""; // Show matching service
        } else {
          card.style.display = "none"; // Hide non-matching service
        }
      });
    });
  });

