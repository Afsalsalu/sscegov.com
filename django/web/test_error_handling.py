from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CentreUserAccount


User = get_user_model()


@override_settings(DEBUG=False)
class FranchiseDashboardErrorTests(TestCase):
    def setUp(self):
        self.franchise_user = User.objects.create_user(
            username="error-franchise",
            password="test-password",
            usertype="centre",
        )
        self.centre = CentreUserAccount.objects.create(
            user=self.franchise_user,
            name="Error Centre Manager",
            username="error-franchise",
            owner_centre="Error Owner Centre",
            mobile=9876543210,
            aadhaar_number=123456789012,
            email="error-centre@example.test",
            centre_name="Error Centre",
            centre_phone_number=9123456780,
            state="kerala",
            taluk="Kochi",
            location="Kochi",
        )

    def assert_safe_franchise_error(self, response, message):
        self.assertContains(response, message, status_code=response.status_code)
        self.assertContains(response, "Go to Dashboard", status_code=response.status_code)
        self.assertContains(response, "Try Again", status_code=response.status_code)
        self.assertContains(response, 'id="navbar-nav"', status_code=response.status_code)
        self.assertNotContains(response, "Traceback", status_code=response.status_code)
        self.assertNotContains(response, "database details", status_code=response.status_code)

    def test_franchise_404_uses_dashboard_layout_and_safe_message(self):
        self.client.force_login(self.franchise_user)

        response = self.client.get(
            reverse("web:franchise_latest_news_detail", kwargs={"pk": 999999})
        )

        self.assert_safe_franchise_error(
            response,
            "The requested item is not available or may have been removed.",
        )

    def test_franchise_403_uses_dashboard_layout_and_safe_message(self):
        head_office = User.objects.create_user(
            username="error-head-office",
            password="test-password",
            usertype="HeadOffice",
        )
        self.client.force_login(head_office)

        response = self.client.get(reverse("web:centre_dashboard"))

        self.assert_safe_franchise_error(
            response,
            "You do not have permission to access this page.",
        )

    def test_franchise_500_uses_dashboard_layout_and_safe_message(self):
        self.client.force_login(self.franchise_user)
        self.client.raise_request_exception = False

        with patch(
            "web.views.DistrictDashboardView.get_context_data",
            side_effect=RuntimeError("secret database details"),
        ):
            response = self.client.get(reverse("web:centre_dashboard"))

        self.assert_safe_franchise_error(
            response,
            "Unable to complete this request right now. Please try again later.",
        )

    def test_head_office_404_does_not_expose_franchise_sidebar(self):
        head_office = User.objects.create_user(
            username="error-head-office-404",
            password="test-password",
            usertype="HeadOffice",
        )
        self.client.force_login(head_office)

        response = self.client.get("/head-office/page-that-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Go to Home", status_code=404)
        self.assertNotContains(response, 'id="navbar-nav"', status_code=404)
        self.assertNotContains(response, "Go to Dashboard", status_code=404)
    def test_public_404_does_not_expose_franchise_sidebar(self):
        response = self.client.get("/a-public-page-that-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            "The requested item is not available or may have been removed.",
            status_code=404,
        )
        self.assertContains(response, "Go to Home", status_code=404)
        self.assertNotContains(response, 'id="navbar-nav"', status_code=404)
        self.assertNotContains(response, "Go to Dashboard", status_code=404)