import json
from pathlib import Path

from captcha.models import CaptchaStore
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import clear_url_caches, get_script_prefix, reverse, set_script_prefix


class CaptchaRefreshTests(TestCase):
    def setUp(self):
        self.original_script_prefix = get_script_prefix()

    def tearDown(self):
        set_script_prefix(self.original_script_prefix)
        clear_url_caches()

    def test_refresh_button_is_rendered_on_login_form(self):
        response = self.client.get(reverse("web:login_view"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="captcha-refresh js-captcha-refresh"')
        self.assertContains(response, 'data-refresh-url="/captcha/refresh/"')
        self.assertContains(response, 'name="captcha_0"')
        self.assertContains(response, 'class="captcha js-captcha-image"')

    def test_refresh_endpoint_returns_a_new_captcha_key_and_image_url(self):
        initial_key = CaptchaStore.generate_key()

        response = self.client.get(
            reverse("captcha-refresh"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertIn("key", payload)
        self.assertIn("image_url", payload)
        self.assertTrue(payload["key"])
        self.assertTrue(payload["image_url"])
        self.assertNotEqual(payload["key"], initial_key)
        self.assertEqual(
            payload["image_url"],
            reverse("captcha-image", kwargs={"key": payload["key"]}),
        )

    def test_javascript_clears_answer_and_updates_image_and_key(self):
        script_path = Path(settings.BASE_DIR) / "static" / "web" / "js" / "captcha-refresh.js"
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("image.src = payload.image_url;", script)
        self.assertIn("keyInput.value = payload.key;", script)
        self.assertIn('answerInput.value = "";', script)
        self.assertIn("answerInput.focus();", script)
        self.assertIn('"X-Requested-With": "XMLHttpRequest"', script)

    @override_settings(FORCE_SCRIPT_NAME="/test")
    def test_refresh_urls_include_test_subpath(self):
        set_script_prefix("/test/")
        clear_url_caches()

        response = Client().get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-refresh-url="/test/captcha/refresh/"')
        self.assertContains(response, "/test/captcha/image/")
