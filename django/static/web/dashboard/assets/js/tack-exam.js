// Wait for the DOM to fully load
document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('startButton');
    const initialDiv = document.getElementById('initialDiv');
    const examForm = document.getElementById('examForm');
    const timerDisplay = document.getElementById('timer');
    const examFormElement = document.getElementById('examFormElement');
    let timeLeft = 600; // 10 minutes in seconds
    let timerInterval;
    const assessmentsUrl = "{% url 'exam:assessments' %}";

    // Function to start the exam
    function startExam(event) {
        event.preventDefault(); // Prevent default behavior
        console.log("Start Exam button clicked!");

        // Hide initial div and show exam form
        if (initialDiv && examForm) {
            initialDiv.style.display = 'none';
            examForm.style.display = 'block';

            // Start timer
            timerInterval = setInterval(updateTimer, 1000);

            // Enter full-screen mode
            requestFullScreen(document.documentElement);
        } else {
            console.error("Initial Div or Exam Form not found.");
        }
    }

    // Function to update the timer
    function updateTimer() {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;

        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds
            .toString()
            .padStart(2, '0')}`;

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            timerDisplay.textContent = '00:00';
            alert('Exam time is over. Redirecting to the home page.');
            window.location.href = assessmentsUrl;
            exitFullScreen();
        } else {
            timeLeft--;
        }
    }

    // Full-screen mode handler
    function requestFullScreen(element) {
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen(); // Safari
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen(); // IE/Edge
        } else {
            console.error("Full-screen not supported.");
        }
    }

    // Exit full-screen mode
    function exitFullScreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen(); // Safari
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen(); // IE/Edge
        }
    }

    // Event listener for form submission
    if (examFormElement) {
        examFormElement.addEventListener('submit', (event) => {
            clearInterval(timerInterval); // Stop the timer
        });
    }

    // Handle visibility changes
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            alert('You left the exam. Redirecting to the home page.');
            exitFullScreen();
            window.location.href = assessmentsUrl;
        }
    });

    // Detect if full-screen is exited
    document.addEventListener('fullscreenchange', () => {
        if (!document.fullscreenElement) {
            alert('You exited full-screen mode. Redirecting to the home page.');
            window.location.href = assessmentsUrl;
        }
    });

    // Add event listener to start button
    if (startButton) {
        console.log("Start button found in DOM.");
        startButton.addEventListener('click', startExam);
    } else {
        console.error("Start button not found in the DOM.");
    }
});
