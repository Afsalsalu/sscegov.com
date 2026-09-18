// Function to generate and download the PDF
function generatePDF() {
    // Import jsPDF library
    importScripts('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.4.0/jspdf.umd.min.js');

    // Create a new jsPDF instance
    const doc = new jsPDF();

    // Add content to the PDF
    doc.text("Certificate of Achievement", 10, 10);
    doc.text("This is to certify that John Doe has completed the course.", 10, 20);

    // Save the PDF
    doc.save("certificate.pdf");
}

// Event listener for button click
document.getElementById("downloadCertificate").addEventListener("click", function() {
    // Call the generatePDF function when the button is clicked
    generatePDF();
});