let mediaRecorder;
let recordedChunks = [];
let recordingStarted = false;
let cameraPermissionGranted = false;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            document.getElementById('video-preview-container').style.display = 'block';
            document.getElementById('video-preview').srcObject = stream;

            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const videoURL = URL.createObjectURL(blob);
                document.getElementById('video-preview').src = videoURL;
            };

            mediaRecorder.start();
            recordingStarted = true;
            cameraPermissionGranted = true;
            document.getElementById('recording-status').textContent = 'Recording Started';

            // Hide camera error message if permission granted
            document.getElementById('camera-error-message').style.display = 'none';
        })
        .catch(err => {
            if (!cameraPermissionGranted) {
                // Show error message only if camera was not previously granted
                document.getElementById('camera-error-message').style.display = 'block';
            }
        });
}

document.getElementById('startButton').addEventListener('click', function () {
    document.getElementById('initialDiv').style.display = 'none';
    document.getElementById('examSection').style.display = 'block';
    startRecording();
});

document.getElementById('submit-btn').addEventListener('click', function() {
    if (!recordingStarted) {
        alert('You must start the recording before submitting the exam.');
    } else {
        // Proceed with the submission logic here.
    }
});

// Retry button to attempt camera access again
document.getElementById('retry-camera-btn').addEventListener('click', function() {
    startRecording();
});

document.querySelectorAll('.question-nav-item').forEach(item => {
    item.addEventListener('click', function() {
        const questionId = this.getAttribute('data-id');
        const questionCard = document.querySelector(`#question_${questionId}`);

        document.querySelectorAll('.question-card').forEach(card => card.classList.remove('active'));
        questionCard.classList.add('active');
    });
});

document.querySelectorAll('.form-check-input').forEach(input => {
    input.addEventListener('change', function() {
        const questionNavItem = document.querySelector(`.question-nav-item[data-id="${this.name.split('_')[1]}"]`);
        questionNavItem.classList.add('answered');
        questionNavItem.classList.remove('unanswered');
    });
});

setTimeout(function() {
    document.querySelector('.timer').textContent = 'Time End In - 00:00';
}, 1000 * 60);

// Automatically start recording when the page loads
document.addEventListener('DOMContentLoaded', function () {
    startRecording();
});


document.addEventListener("DOMContentLoaded", function() {
    const navItems = document.querySelectorAll('.question-nav-item');
    const questionCards = document.querySelectorAll('.question-card');
    const submitBtn = document.getElementById("submit-btn");
    const resultDiv = document.getElementById("result");

    navItems.forEach(item => {
        item.addEventListener("click", function(event) {
            event.preventDefault();
            const targetId = this.dataset.target;
            questionCards.forEach(card => card.classList.toggle('active', card.id === targetId.substring(1)));
            navItems.forEach(navItem => navItem.classList.toggle('active', navItem.dataset.target === targetId));
        });
    });

    submitBtn.addEventListener("click", function() {
        const selectedAnswers = document.querySelectorAll('.form-check-input:checked');
        if (selectedAnswers.length === 0) {
            alert('Please answer at least one question before submitting.');
            return;
        }

        const formData = new FormData();
        selectedAnswers.forEach(input => formData.append(input.name, input.value));

        fetch("{% url 'exam:submit_exam' %}", {
            method: "POST",
            headers: {
                "X-CSRFToken": document.querySelector('[name=csrf-token]').content,
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultDiv.innerHTML = `<div class="alert alert-success">Your score is: ${data.score}. You ${data.pass_exam ? 'passed' : 'failed'} the exam.</div>`;
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            } else {
                resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message}</div>`;
            }
        })
        .catch(error => {
            console.error("Error:", error);
            resultDiv.innerHTML = `<div class="alert alert-danger">There was an error processing your request. Please try again.</div>`;
        });
    });
});
document.addEventListener("DOMContentLoaded", function() {
    const navItems = document.querySelectorAll('.question-nav-item');
    const questionCards = document.querySelectorAll('.question-card');
    const submitBtn = document.getElementById("submit-btn");
    const resultDiv = document.getElementById("result");

    navItems.forEach(item => {
        item.addEventListener("click", function(event) {
            event.preventDefault();
            const targetId = this.dataset.target;
            questionCards.forEach(card => card.classList.toggle('active', card.id === targetId.substring(1)));
            navItems.forEach(navItem => navItem.classList.toggle('active', navItem.dataset.target === targetId));
        });
    });

    document.querySelectorAll('.form-check-input').forEach(input => {
        input.addEventListener('change', function() {
            const questionId = this.name.split('_')[1]; // Extract question ID from name
            const navItem = document.querySelector(`.question-nav-item[data-id="${questionId}"]`);
            if (navItem) {
                navItem.classList.add('answered');
            }
        });
    });

    submitBtn.addEventListener("click", function() {
        const selectedAnswers = document.querySelectorAll('.form-check-input:checked');
        if (selectedAnswers.length === 0) {
            alert('Please answer at least one question before submitting.');
            return;
        }

        const formData = new FormData();
        selectedAnswers.forEach(input => formData.append(input.name, input.value));

        fetch("{% url 'exam:submit_exam' %}", {
            method: "POST",
            headers: {
                "X-CSRFToken": document.querySelector('[name=csrf-token]').content,
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultDiv.innerHTML = `<div class="alert alert-success">Your score is: ${data.score}. You ${data.pass_exam ? 'passed' : 'failed'} the exam.</div>`;
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
            } else {
                resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.message}</div>`;
            }
        })
        .catch(error => {
            console.error("Error:", error);
            resultDiv.innerHTML = `<div class="alert alert-danger">There was an error processing your request. Please try again.</div>`;
        });
    });
});

    document.addEventListener("DOMContentLoaded", function() {
        let timerElement = document.querySelector('.timer');
        let timeRemaining = 3600; // Example: 1 hour (in seconds)
        
        function updateTimer() {
            if (timeRemaining <= 0) {
                timerElement.textContent = "Time End In - 00:00";
                // Redirect to a timeout page or any other desired URL
                window.location.href = "/exam/dashboard/";
                return;
            }
            
            // Calculate minutes and seconds
            let minutes = Math.floor(timeRemaining / 60);
            let seconds = timeRemaining % 60;

            // Format minutes and seconds
            minutes = minutes < 10 ? '0' + minutes : minutes;
            seconds = seconds < 10 ? '0' + seconds : seconds;

            // Update the timer display
            timerElement.textContent = `Time End In - ${minutes}:${seconds}`;
            timeRemaining--;
        }

        // Call updateTimer every 1 second
        updateTimer(); // Call immediately to avoid delay
        setInterval(updateTimer, 1000);
    });


    document.addEventListener("DOMContentLoaded", function () {
        const startButton = document.getElementById('startButton');
        const initialDiv = document.getElementById('initialDiv');
        const examSection = document.getElementById('examSection');
    
        startButton.addEventListener('click', function () {
            // Attempt to make the page fullscreen
            if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen();
            } else if (document.documentElement.webkitRequestFullscreen) { // For Safari
                document.documentElement.webkitRequestFullscreen();
            } else if (document.documentElement.msRequestFullscreen) { // For IE/Edge
                document.documentElement.msRequestFullscreen();
            }
    
            // Hide the initial content
            initialDiv.style.display = 'none';
    
            // Show the exam section
            examSection.style.display = 'block';
        });
    });
    

    let isTabChanged = false;
    let malpracticeCount = 0;
    const MAX_WARNINGS = 3;
    
    // Detect tab change or window close
    window.addEventListener("beforeunload", function(event) {
        if (!isTabChanged) {
            event.preventDefault();
            event.returnValue = "Are you sure you want to leave? Your attempt may be considered as malpractice.";
            return event.returnValue;
        }
    });
    
    // Detect focus change (i.e., tab change or minimizing the window)
    window.addEventListener("blur", function() {
        if (!isTabChanged) {
            handleMalpracticeAttempt();
        }
    });
    
    // Detect when the user returns to the tab
    window.addEventListener("focus", function() {
        if (isTabChanged) {
            isTabChanged = false;
        }
    });
    
    function handleMalpracticeAttempt() {
        malpracticeCount++;
    
        if (malpracticeCount <= MAX_WARNINGS) {
            showWarningPopup(`?? Warning ${malpracticeCount}: Leaving the exam tab is considered malpractice.`);
        } else {
            showMalpracticePopup();
        }
    }
    
    function createPopup(id, message, buttonText, buttonColor, callback) {
        if (document.getElementById(id)) return;
    
        const popup = document.createElement('div');
        popup.id = id;
        popup.style.position = 'fixed';
        popup.style.top = '0';
        popup.style.left = '0';
        popup.style.width = '100vw';
        popup.style.height = '100vh';
        popup.style.background =  'rgba(0, 0, 0, 0.8)';
        popup.style.display = 'flex';
        popup.style.flexDirection = 'column';
        popup.style.justifyContent = 'center';
        popup.style.alignItems = 'center';
        popup.style.color = 'red';
        popup.style.fontFamily = 'Arial, sans-serif';
        popup.style.fontSize = '24px';
        popup.style.textAlign = 'center';
        popup.style.padding = '20px';
        popup.style.boxShadow = '0 4px 8px rgba(255, 255, 255, 0.3)';
        popup.style.borderRadius = '15px';
        popup.style.zIndex = '9999';
    
        const messageDiv = document.createElement('div');
        messageDiv.textContent = message;
        messageDiv.style.marginBottom = '20px';
    
        const okButton = document.createElement('button');
        okButton.textContent = buttonText;
        okButton.style.padding = '15px 30px';
        okButton.style.backgroundColor = buttonColor;
        okButton.style.color = 'white';
        okButton.style.border = 'none';
        okButton.style.borderRadius = '10px';
        okButton.style.cursor = 'pointer';
        okButton.style.fontSize = '18px';
        okButton.style.transition = 'background 0.3s ease';
    
        okButton.addEventListener('mouseover', () => {
            okButton.style.backgroundColor = '#555';
        });
    
        okButton.addEventListener('mouseout', () => {
            okButton.style.backgroundColor = buttonColor;
        });
    
        okButton.addEventListener('click', callback);
    
        popup.appendChild(messageDiv);
        popup.appendChild(okButton);
        document.body.appendChild(popup);
    }
    
    function showWarningPopup(message) {
        createPopup('warning-popup', message, 'Understood', '#007bff', function () {
            document.getElementById('warning-popup').remove();
        });
    }
    
    function showMalpracticePopup() {
        createPopup('malpractice-popup', "?? Your attempt is considered malpractice. You will be redirected.", 'Proceed', '#dc3545', function () {
            window.location.href = '/exam/dashboard/';
        });
    }
    
    let faceDetectionInterval;
    let warningCount = 0;
    
    async function loadFaceAPI() {
        await faceapi.nets.tinyFaceDetector.loadFromUri('/models'); // Ensure models are available in /models folder
    }
    
    async function detectFaces() {
        const video = document.getElementById('video-preview');
        if (!video || video.readyState !== 4) return;
    
        const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions());
        
        if (detections.length > 1) {
            warningCount++;
            showWarningPopup(`?? Warning ${warningCount}: Multiple faces detected!`);
            
            if (warningCount >= MAX_WARNINGS) {
                showMalpracticePopup();
            }
        }
    }
    
    // Start face detection when recording starts
    document.addEventListener('DOMContentLoaded', async function () {
        await loadFaceAPI();
    
        faceDetectionInterval = setInterval(detectFaces, 3000); // Check every 3 seconds
    });
    


    