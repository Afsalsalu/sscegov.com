from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .language import SUPPORTED_LANGUAGE_CODES, language_for_state
from .models import CentreUserAccount


User = get_user_model()


class DashboardLanguageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="language-admin",
            password="test-password",
            usertype="HeadOffice",
        )
        self.kerala_user = self.make_franchise("language-kerala", "kerala")
        self.unknown_user = self.make_franchise("language-unknown", "")

    def make_franchise(self, username, state):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            usertype="centre",
        )
        CentreUserAccount.objects.create(
            user=user,
            owner_centre=f"{username} centre",
            mobile=9999999999,
            aadhaar_number=999999999999,
            email=f"{username}@example.com",
            centre_phone_number=9999999999,
            state=state,
            location="",
        )
        return user

    def current_language_for(self, user, url_name):
        self.client.force_login(user)
        response = self.client.get(reverse(f"web:{url_name}"))
        self.assertEqual(response.status_code, 200)
        return response.context["current_language"]

    def test_supported_language_catalog_contains_english_and_all_scheduled_languages(self):
        self.assertEqual(len(SUPPORTED_LANGUAGE_CODES), 23)
        self.assertIn("en", SUPPORTED_LANGUAGE_CODES)
        self.assertIn("ml", SUPPORTED_LANGUAGE_CODES)
        self.assertIn("ur", SUPPORTED_LANGUAGE_CODES)

    def test_state_mapping_accepts_slugs_and_display_names(self):
        self.assertEqual(language_for_state("kerala"), "ml")
        self.assertEqual(language_for_state("Kerala"), "ml")
        self.assertEqual(language_for_state("Tamil Nadu"), "ta")
        self.assertEqual(language_for_state("tamil-nadu"), "ta")

    def test_admin_defaults_to_english(self):
        self.assertEqual(self.current_language_for(self.admin, "admin_dashboard"), "en")

    def test_kerala_franchise_defaults_to_malayalam(self):
        self.assertEqual(
            self.current_language_for(self.kerala_user, "centre_dashboard"),
            "ml",
        )

    def test_unknown_or_missing_state_defaults_to_english(self):
        self.assertEqual(
            self.current_language_for(self.unknown_user, "centre_dashboard"),
            "en",
        )

    def test_dashboard_renders_the_language_selector_and_current_static_asset(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("web:admin_dashboard"))

        self.assertContains(response, 'data-language-switcher')
        self.assertContains(response, 'web/css/language-switcher.css')
        self.assertContains(response, reverse("web:set_language"))
        self.assertContains(response, 'value="ur"')

    def test_manual_selection_persists_for_admin_across_login(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("web:set_language"),
            {"language": "ta", "next": reverse("web:admin_dashboard")},
        )
        self.assertRedirects(response, reverse("web:admin_dashboard"))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.preferred_language, "ta")

        self.client.logout()
        self.client.force_login(self.admin)
        self.assertEqual(self.current_language_for(self.admin, "admin_dashboard"), "ta")

    def test_manual_selection_overrides_franchise_state_and_is_user_scoped(self):
        self.client.force_login(self.kerala_user)
        response = self.client.post(
            reverse("web:set_language"),
            {"language": "hi", "next": reverse("web:centre_dashboard")},
        )
        self.assertRedirects(response, reverse("web:centre_dashboard"))
        self.kerala_user.refresh_from_db()
        self.assertEqual(self.kerala_user.preferred_language, "hi")
        self.assertEqual(self.current_language_for(self.kerala_user, "centre_dashboard"), "hi")

        self.assertEqual(self.current_language_for(self.unknown_user, "centre_dashboard"), "en")
        self.unknown_user.refresh_from_db()
        self.assertEqual(self.unknown_user.preferred_language, "")

    def test_language_switch_is_post_only_and_rejects_invalid_values(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("web:set_language")).status_code, 405)

        response = self.client.post(
            reverse("web:set_language"),
            {"language": "xx", "next": reverse("web:admin_dashboard")},
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.preferred_language, "")

    def test_language_switch_rejects_external_redirects(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("web:set_language"),
            {"language": "ml", "next": "https://evil.example/phishing"},
        )
        self.assertRedirects(response, reverse("web:headoffice_dashboard"))
