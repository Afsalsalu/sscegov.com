from django.core.files.storage import FileSystemStorage
from django.templatetags.static import static
from django.test import Client, SimpleTestCase, override_settings
from django.urls import clear_url_caches, get_script_prefix, reverse, set_script_prefix


class URLPrefixConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.original_script_prefix = get_script_prefix()

    def tearDown(self):
        set_script_prefix(self.original_script_prefix)
        clear_url_caches()

    def test_root_configuration_keeps_existing_urls(self):
        with override_settings(
            FORCE_SCRIPT_NAME=None,
            STATIC_URL="/static/",
            MEDIA_URL="/media/",
        ):
            set_script_prefix("/")
            clear_url_caches()

            self.assertEqual(reverse("web:index"), "/")
            self.assertEqual(static("web/css/site.css"), "/static/web/css/site.css")
            self.assertEqual(
                FileSystemStorage().url("uploads/document.pdf"),
                "/media/uploads/document.pdf",
            )

    def test_test_subpath_configuration_prefixes_reversed_and_asset_urls(self):
        with override_settings(
            FORCE_SCRIPT_NAME="/test",
            STATIC_URL="/test/static/",
            MEDIA_URL="/test/media/",
        ):
            set_script_prefix("/test/")
            clear_url_caches()

            self.assertEqual(reverse("web:index"), "/test/")
            self.assertEqual(
                reverse("web:centre_dashboard"),
                "/test/franchise-dashboard/dashboard/",
            )
            self.assertEqual(
                reverse("web:annual_kyc"),
                "/test/franchise-dashboard/annual-kyc/",
            )
            self.assertEqual(
                reverse("web:annual_kyc_order"),
                "/test/franchise-dashboard/annual-kyc/order/",
            )
            self.assertEqual(
                static("web/css/site.css"),
                "/test/static/web/css/site.css",
            )
            self.assertEqual(
                FileSystemStorage().url("uploads/document.pdf"),
                "/test/media/uploads/document.pdf",
            )

    def test_prefixed_client_request_keeps_login_redirect_under_test_prefix(self):
        with override_settings(FORCE_SCRIPT_NAME="/test"):
            set_script_prefix("/test/")
            clear_url_caches()

            response = Client().get("/franchise-dashboard/dashboard/")

            self.assertEqual(response.status_code, 302)
            self.assertIn(
                "next=/test/franchise-dashboard/dashboard/",
                response.url,
            )
