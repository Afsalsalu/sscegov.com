from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from .models import AddState, CentreUserAccount


User = get_user_model()


class WhatsAppSupportTests(TestCase):
    def make_franchise(self, username, state):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            email=f"{username}@example.test",
            usertype="centre",
        )
        centre = CentreUserAccount.objects.create(
            user=user,
            name=username,
            username=username,
            owner_centre=username,
            centre_name=username,
            mobile=9876543210,
            aadhaar_number=123456789012,
            email=f"{username}@registered.example.test",
            centre_phone_number=9123456780,
            state=state,
            taluk="Kochi",
            location="Kochi",
        )
        return user, centre

    def add_state(self, name, number="", enabled=True, slug=None):
        return AddState.objects.create(
            state_name=name,
            slug=slug or name.lower().replace(" ", "-"),
            whatsapp_number=number,
            whatsapp_enabled=enabled,
        )

    def test_kerala_user_uses_kerala_number(self):
        self.add_state("Kerala", "919876543210")
        user, _centre = self.make_franchise("kerala-user", "kerala")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertContains(response, "https://wa.me/919876543210?text=")

    def test_configured_other_state_uses_its_own_number(self):
        self.add_state("Kerala", "919876543210")
        self.add_state("Karnataka", "919812345678")
        user, _centre = self.make_franchise("karnataka-user", "karnataka")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertContains(response, "https://wa.me/919812345678?text=")
        self.assertNotContains(response, "https://wa.me/919876543210?text=")

    def test_missing_state_number_falls_back_to_kerala(self):
        self.add_state("Kerala", "919876543210")
        self.add_state("Assam")
        user, _centre = self.make_franchise("assam-user", "assam")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertContains(response, "https://wa.me/919876543210?text=")

    def test_disabled_state_number_falls_back_to_kerala(self):
        self.add_state("Kerala", "919876543210")
        self.add_state("Tamil Nadu", "919812345678", enabled=False)
        user, _centre = self.make_franchise("tamil-user", "tamilnadu")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertContains(response, "https://wa.me/919876543210?text=")
        self.assertNotContains(response, "https://wa.me/919812345678?text=")

    def test_missing_kerala_fallback_shows_safe_unavailable_message(self):
        self.add_state("Assam")
        user, _centre = self.make_franchise("assam-user", "assam")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard"))

        self.assertNotContains(response, "https://wa.me/")
        self.assertContains(response, "WhatsApp support is currently unavailable")

    def test_state_is_not_overridable_by_query_string(self):
        self.add_state("Kerala", "919876543210")
        self.add_state("Karnataka", "919812345678")
        user, _centre = self.make_franchise("karnataka-user", "karnataka")

        self.client.force_login(user)
        response = self.client.get(reverse("web:centre_dashboard") + "?state=kerala")

        self.assertContains(response, "https://wa.me/919812345678?text=")
        self.assertNotContains(response, "https://wa.me/919876543210?text=")

    def test_admin_can_save_normalized_number_and_clear_it(self):
        state = self.add_state("Kerala")
        admin = User.objects.create_user(
            username="whatsapp-admin",
            password="test-password",
            usertype="HeadOffice",
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("web:whatsapp_management"),
            {"state_id": state.pk, "whatsapp_number": "+91 (98765) 43210", "whatsapp_enabled": "on"},
        )

        self.assertRedirects(response, reverse("web:whatsapp_management"))
        state.refresh_from_db()
        self.assertEqual(state.whatsapp_number, "919876543210")
        self.assertTrue(state.whatsapp_enabled)

        self.client.post(
            reverse("web:whatsapp_management"),
            {"state_id": state.pk, "whatsapp_number": "", "whatsapp_enabled": "on"},
        )
        state.refresh_from_db()
        self.assertEqual(state.whatsapp_number, "")

    def test_admin_rejects_urls_text_and_missing_country_code(self):
        state = self.add_state("Kerala")
        admin = User.objects.create_user(
            username="validation-admin",
            password="test-password",
            usertype="Administrator",
        )
        self.client.force_login(admin)

        for value in ("https://wa.me/919876543210", "support-number", "9876543210"):
            response = self.client.post(
                reverse("web:whatsapp_management"),
                {"state_id": state.pk, "whatsapp_number": value, "whatsapp_enabled": "on"},
            )
            self.assertEqual(response.status_code, 200)
            state.refresh_from_db()
            self.assertEqual(state.whatsapp_number, "")

    def test_franchise_cannot_access_management_or_change_number(self):
        state = self.add_state("Kerala", "919876543210")
        user, _centre = self.make_franchise("franchise-user", "kerala")
        self.client.force_login(user)

        get_response = self.client.get(reverse("web:whatsapp_management"))
        self.assertEqual(get_response.status_code, 302)

        post_response = self.client.post(
            reverse("web:whatsapp_management"),
            {"state_id": state.pk, "whatsapp_number": "919812345678", "whatsapp_enabled": "on"},
        )
        self.assertEqual(post_response.status_code, 302)
        state.refresh_from_db()
        self.assertEqual(state.whatsapp_number, "919876543210")
