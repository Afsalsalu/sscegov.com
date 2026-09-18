document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const tableRows = document.querySelectorAll("tbody tr");

    searchInput.addEventListener("input", function () {
      const filterText = searchInput.value.toLowerCase();

      tableRows.forEach(row => {
        const ownerCentre = row.querySelector("h6")?.textContent.toLowerCase();
        if (ownerCentre && ownerCentre.includes(filterText)) {
          row.style.display = ""; // Show the row
        } else {
          row.style.display = "none"; // Hide the row
        }
      });
    });
  });