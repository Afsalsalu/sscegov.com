document.addEventListener('DOMContentLoaded', (event) => {
    // Set default date value
    let dateInput = document.getElementById('date');
    let defaultDate = document.getElementById('defaultDate')?.value || new Date().toISOString().split('T')[0];
    dateInput.value = defaultDate;

    // Show messages from the backend
    const messagesContainer = document.getElementById('messages');
    if (messagesContainer) {
        let messages = JSON.parse(messagesContainer.dataset.messages || '[]');
        messages.forEach(message => {
            Swal.fire({
                title: message.tags.charAt(0).toUpperCase() + message.tags.slice(1),
                text: message.text,
                icon: message.tags,
                confirmButtonText: 'OK'
            });
        });
    }

    // Initialize display for serial number
    let serialNoDisplay = document.getElementById('printSerialNo');
    if (serialNoDisplay) {
        serialNoDisplay.textContent = document.getElementById('serial_no').value;
    }

    // Initialize credit and total calculation
    updateCreditAndTotal();
});

function updateSerialNumber() {
    let seriesSelect = document.getElementById('series');
    let serialNoInput = document.getElementById('serial_no');
    let serialNoDisplay = document.getElementById('printSerialNo');
    let selectedOption = seriesSelect.options[seriesSelect.selectedIndex];

    serialNoInput.value = selectedOption.dataset.serial;
    if (serialNoDisplay) {
        serialNoDisplay.textContent = serialNoInput.value;
    }
}

function updateAccountCode(selectElement) {
    let selectedOption = selectElement.options[selectElement.selectedIndex];
    let narrationInput = selectElement.id.replace('head', 'narration');
    let debitInput = selectElement.id.replace('head', 'debit');
    let creditInput = selectElement.id.replace('head', 'credit');

    document.getElementById(narrationInput).value = selectedOption.dataset.narration || '';
    document.getElementById(debitInput).value = selectedOption.dataset.dramount || '';
    document.getElementById(creditInput).value = selectedOption.dataset.cramount || '';
    updateCreditAndTotal();
}

function numberToWords(num) {
    if (num === 0) return 'zero';
    
    const ones = ['','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen'];
    const tens = ['','', 'twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety'];
    const thousands = ['','thousand','million','billion','trillion'];
    
    function convertToWords(num) {
        let words = '';
        let i = 0;
        
        while (num > 0) {
            if (num % 1000 !== 0) {
                words = convertHundreds(num % 1000) + thousands[i] + ' ' + words;
            }
            num = Math.floor(num / 1000);
            i++;
        }
        
        return words.trim();
    }
    
    function convertHundreds(num) {
        let str = '';
        
        if (num > 99) {
            str += ones[Math.floor(num / 100)] + ' hundred ';
            num %= 100;
        }
        
        if (num > 0) {
            if (num < 20) {
                str += ones[num];
            } else {
                str += tens[Math.floor(num / 10)] + ' ';
                str += ones[num % 10];
            }
        }
        
        return str;
    }
    
    return convertToWords(num);
}

function updateCreditAndTotal() {
    let debit1 = parseFloat(document.getElementById('debit1').value) || 0;
    let debit2 = parseFloat(document.getElementById('debit2').value) || 0;
    let total = debit1 + debit2;
    let totalFixed = total.toFixed(2);

    document.getElementById('total_amount').value = totalFixed;
    document.getElementById('credit2').value = totalFixed;

    // Update the amount displayed dynamically
    document.getElementById('amountDebited').textContent = `${totalFixed} /-  Amount Debited as per details given below / attached.`;
    document.getElementById('dynamicAmount').textContent = `${totalFixed} /-`;
    document.getElementById('amountDebited2').textContent = `${totalFixed} /-`;
    document.getElementById('amountDebitedDisplay').textContent = `(${numberToWords(total)})/- Being Amount Debited`;
}

function confirmDelete(event) {
    event.preventDefault(); // Prevent the default anchor action
    
    // Use SweetAlert for confirmation dialog
    Swal.fire({
        title: 'Are you sure?',
        text: 'You will not be able to recover this item!',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'No, cancel!',
        reverseButtons: true
    }).then((result) => {
        if (result.isConfirmed) {
            // User confirmed deletion, proceed with the deletion
            var deleteLink = document.getElementById('deleteLink');
            if (deleteLink) {
                window.location.href = deleteLink.href; // Navigate to the delete URL
            }
        }
    });
}

// Date input event listener
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    const dateSpan = document.getElementById('dateSpan');
    
    // Update the span when the page loads with the initial value
    dateSpan.textContent = dateInput.value;
    
    // Add event listener to update the span when the date input changes
    dateInput.addEventListener('input', function() {
        dateSpan.textContent = this.value;
    });
});
