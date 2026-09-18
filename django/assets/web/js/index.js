window.onload = function() {
    const popup = document.getElementById("popup");
    const overlay = document.getElementById("overlay");

    // Show the popup and overlay when the page loads
    overlay.style.display = "block";
    popup.style.display = "block";

    // Close the popup when the "OK" button is clicked
    document.getElementById("closeBtn").addEventListener("click", function() {
        popup.style.display = "none";
        overlay.style.display = "none";
    });
};