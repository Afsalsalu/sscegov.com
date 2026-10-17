(function () {
    "use strict";

    const refreshMessage = "Could not refresh the CAPTCHA. Please try again.";

    function showError(errorElement) {
        errorElement.textContent = refreshMessage;
        errorElement.hidden = false;
    }

    function clearError(errorElement) {
        errorElement.textContent = "";
        errorElement.hidden = true;
    }

    function refreshCaptcha(button) {
        const widget = button.closest(".captcha-widget");
        if (!widget || button.disabled) {
            return;
        }

        const image = widget.querySelector(".js-captcha-image");
        const keyInput = widget.querySelector('input[name$="_0"]');
        const answerInput = widget.querySelector('input[name$="_1"]');
        const errorElement = widget.querySelector(".captcha-refresh-error");
        const refreshUrl = widget.dataset.refreshUrl;

        if (!image || !keyInput || !answerInput || !errorElement || !refreshUrl) {
            return;
        }

        button.disabled = true;
        button.setAttribute("aria-busy", "true");
        clearError(errorElement);

        fetch(refreshUrl, {
            method: "GET",
            headers: {
                Accept: "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            credentials: "same-origin",
            cache: "no-store",
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("CAPTCHA refresh failed");
                }
                return response.json();
            })
            .then(function (payload) {
                if (!payload.key || !payload.image_url) {
                    throw new Error("Invalid CAPTCHA refresh response");
                }

                image.src = payload.image_url;
                keyInput.value = payload.key;
                answerInput.value = "";
                answerInput.focus();
            })
            .catch(function () {
                showError(errorElement);
            })
            .finally(function () {
                button.disabled = false;
                button.removeAttribute("aria-busy");
            });
    }

    function initCaptchaRefresh() {
        document.querySelectorAll(".js-captcha-refresh").forEach(function (button) {
            button.addEventListener("click", function () {
                refreshCaptcha(button);
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initCaptchaRefresh);
    } else {
        initCaptchaRefresh();
    }
})();
