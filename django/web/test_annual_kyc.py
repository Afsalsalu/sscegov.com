import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .annual_kyc_forms import AnnualKYCSettingsForm
from .annual_kyc_services import (
    annual_kyc_access_restricted,
    annual_kyc_snapshot,
    calculate_annual_kyc_amount,
    complete_annual_kyc_payment,
    ensure_annual_kyc_status,
    get_annual_kyc_settings,
    resend_annual_kyc_otp,
    verify_annual_kyc_otp,
)
from .models import (
    CentreAnnualKYCOTPVerification,
    CentreAnnualKYCPayment,
    CentreUserAccount,
)

User = get_user_model()


class AnnualKYCTestCase(TestCase):
    def setUp(self):
        self.base = timezone.make_aware(datetime(2025, 1, 1, 9, 0, 0))
        self.user = User.objects.create_user(
            username="annual-centre",
            password="password",
            email="centre@example.com",
            usertype="centre",
        )
        self.centre = CentreUserAccount.objects.create(
            user=self.user,
            name="Annual Owner",
            owner_centre="Annual Centre",
            centre_name="Annual Centre",
            mobile=9876543210,
            centre_phone_number=9876543210,
            aadhaar_number=123456789012,
            email="centre@example.com",
            state="kerala",
            location="Test location",
            created_at=self.base,
            is_active=True,
            is_approved=True,
        )
        self.settings = get_annual_kyc_settings()
        self.settings.warning_period_days = 30
        self.settings.grace_period_days = 30
        self.settings.payment_enabled = True
        self.settings.save()
        self.status = ensure_annual_kyc_status(self.centre, settings_obj=self.settings)
        self.status.next_kyc_due_at = timezone.make_aware(datetime(2025, 12, 31, 0, 0, 0))
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))

    def at(self, year, month, day, hour=12):
        return timezone.make_aware(datetime(year, month, day, hour, 0, 0))

    def make_payment(self, *, status=CentreAnnualKYCPayment.Status.SUCCESS):
        return CentreAnnualKYCPayment.objects.create(
            centre=self.centre,
            amount=self.settings.default_amount,
            status=status,
            razorpay_order_id=f"order_{CentreAnnualKYCPayment.objects.count() + 1}",
        )

    def test_warning_starts_at_30_days_and_day_count_decreases_server_side(self):
        first = annual_kyc_snapshot(self.centre, now=self.at(2025, 12, 13))
        second = annual_kyc_snapshot(self.centre, now=self.at(2025, 12, 14))
        self.assertEqual(first["state"], "warning")
        self.assertEqual(first["days_to_due"], 18)
        self.assertEqual(second["days_to_due"], 17)
        self.assertIn("18", first["message"])
        self.assertIn("17", second["message"])

    def test_due_date_and_grace_period_are_blocking_but_online(self):
        due = annual_kyc_snapshot(self.centre, now=self.at(2025, 12, 31))
        grace = annual_kyc_snapshot(self.centre, now=self.at(2026, 1, 1))
        expired = annual_kyc_snapshot(self.centre, now=self.at(2026, 1, 30))
        self.assertEqual(due["state"], "due")
        self.assertTrue(due["restricted"])
        self.assertTrue(due["online_allowed"])
        self.assertEqual(grace["state"], "grace")
        self.assertTrue(grace["online_allowed"])
        self.assertEqual(grace["grace_days"], 29)
        self.assertIn("29", grace["message"])
        self.assertEqual(expired["state"], "expired")
        self.assertFalse(expired["online_allowed"])

    def test_middleware_blocks_direct_dashboard_url_without_redirect_loop(self):
        self.status.next_kyc_due_at = self.at(2025, 12, 31, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("web:centre_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("web:annual_kyc"))
        renewal = client.get(response.url)
        self.assertEqual(renewal.status_code, 200)
        self.assertNotEqual(renewal.url if hasattr(renewal, "url") else "", reverse("web:annual_kyc"))

    def test_expired_page_is_whatsapp_only_and_contains_centre_identity(self):
        client = Client()
        self.settings.whatsapp_support_number = "919876543210"
        self.settings.save(update_fields=("whatsapp_support_number", "updated_at"))
        self.status.next_kyc_due_at = self.at(2025, 1, 1, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        client.force_login(self.user)
        response = client.get(reverse("web:annual_kyc"))
        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Online KYC renewal is no longer available", body)
        self.assertIn("Contact us on WhatsApp", body)
        self.assertNotIn("Pay &amp; Get OTP", body)
        self.assertIn("Annual+Centre", body)
        self.assertIn(self.centre.formatted_id, body)

    def test_payment_stays_unverified_until_server_side_verification_and_otp(self):
        self.status.next_kyc_due_at = self.at(2025, 12, 31, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        payment = self.make_payment(status=CentreAnnualKYCPayment.Status.CREATED)
        self.assertEqual(payment.status, CentreAnnualKYCPayment.Status.CREATED)
        self.assertIsNone(self.status.last_kyc_verified_at)
        with patch("web.annual_kyc_services._send_annual_kyc_sms", return_value=True):
            completed, otp, _ = complete_annual_kyc_payment(
                payment.pk,
                payment_id_value="pay_server_verified",
                signature="verified_signature",
            )
        self.status.refresh_from_db()
        self.assertEqual(completed.status, CentreAnnualKYCPayment.Status.SUCCESS)
        self.assertIsNotNone(otp)
        self.assertIsNone(self.status.last_kyc_verified_at)
        self.assertNotEqual(otp.otp_hash, "123456")

    def test_otp_success_sets_next_cycle_and_expiry_cooldown_and_attempt_limit(self):
        payment = self.make_payment()
        otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=self.centre,
            payment=payment,
            otp_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=10),
            resend_available_at=timezone.now() + timedelta(minutes=10),
        )
        verify_annual_kyc_otp(payment, "123456")
        self.status.refresh_from_db()
        otp.refresh_from_db()
        self.assertEqual(otp.status, CentreAnnualKYCOTPVerification.Status.VERIFIED)
        self.assertIsNotNone(self.status.last_kyc_verified_at)
        self.assertEqual(self.status.next_kyc_due_at.date(), (self.status.last_kyc_verified_at + timedelta(days=365)).date())

        expired_payment = self.make_payment()
        expired_otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=self.centre,
            payment=expired_payment,
            otp_hash=make_password("123456"),
            expires_at=timezone.now() - timedelta(seconds=1),
            resend_available_at=timezone.now(),
        )
        with self.assertRaisesMessage(ValueError, "expired"):
            verify_annual_kyc_otp(expired_payment, "123456")
        expired_otp.refresh_from_db()
        self.assertEqual(expired_otp.status, CentreAnnualKYCOTPVerification.Status.EXPIRED)

        cooldown_payment = self.make_payment()
        cooldown_otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=self.centre,
            payment=cooldown_payment,
            otp_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=10),
            resend_available_at=timezone.now() + timedelta(minutes=2),
        )
        with self.assertRaisesMessage(ValueError, "wait"):
            resend_annual_kyc_otp(cooldown_payment)
        self.assertEqual(cooldown_otp.status, CentreAnnualKYCOTPVerification.Status.SENT)

        attempt_payment = self.make_payment()
        attempt_otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=self.centre,
            payment=attempt_payment,
            otp_hash=make_password("654321"),
            expires_at=timezone.now() + timedelta(minutes=10),
            resend_available_at=timezone.now(),
        )
        self.settings.max_otp_verification_attempts = 2
        self.settings.save(update_fields=("max_otp_verification_attempts", "updated_at"))
        with self.assertRaisesMessage(ValueError, "incorrect"):
            verify_annual_kyc_otp(attempt_payment, "000000")
        with self.assertRaisesMessage(ValueError, "incorrect"):
            verify_annual_kyc_otp(attempt_payment, "000000")
        attempt_otp.refresh_from_db()
        self.assertEqual(attempt_otp.status, CentreAnnualKYCOTPVerification.Status.FAILED)

    def test_admin_settings_and_per_centre_fee_override(self):
        data = {
            field.name: getattr(self.settings, field.name)
            for field in self.settings._meta.fields
            if field.name not in {"id", "updated_at"}
        }
        data.update({"renewal_interval_months": 18, "default_amount": "125.00"})
        form = AnnualKYCSettingsForm(data=data, instance=self.settings)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.renewal_interval_months, 18)
        self.status.fee_override = "222.50"
        self.status.save(update_fields=("fee_override", "updated_at"))
        self.assertEqual(calculate_annual_kyc_amount(self.centre), 222.50)

    def test_head_office_settings_page_renders_and_centre_controls_are_reachable(self):
        admin = User.objects.create_user(
            username="head-office",
            password="password",
            usertype="HeadOffice",
        )
        client = Client()
        client.force_login(admin)
        response = client.get(reverse("web:annual_kyc_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Annual Centre KYC Renewal")
        self.assertContains(response, "Annual Centre")
        detail = client.get(reverse("web:annual_kyc_centre", kwargs={"pk": self.centre.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Audit timeline")

    def test_annual_kyc_and_reactivation_restrictions_remain_independent(self):
        self.centre.is_active = False
        self.centre.inactive_due_to_inactivity = True
        self.centre.save(update_fields=("is_active", "inactive_due_to_inactivity"))
        self.assertFalse(annual_kyc_access_restricted(self.centre))
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("web:centre_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("web:centre_reactivation"))

    def test_server_verified_callback_does_not_complete_kyc_before_otp(self):
        self.status.next_kyc_due_at = self.at(2025, 12, 31, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        payment = self.make_payment(status=CentreAnnualKYCPayment.Status.CREATED)
        client = Client()
        client.force_login(self.user)
        razorpay_client = Mock()
        razorpay_client.payment.fetch.return_value = {
            "order_id": payment.razorpay_order_id,
            "amount": int(payment.amount * 100),
            "status": "captured",
        }
        with patch("web.annual_kyc_views.razorpay.Client", return_value=razorpay_client), patch(
            "web.annual_kyc_services._send_annual_kyc_sms", return_value=True
        ):
            response = client.post(
                reverse("web:annual_kyc_callback"),
                data=json.dumps(
                    {
                        "razorpay_order_id": payment.razorpay_order_id,
                        "razorpay_payment_id": "pay_callback",
                        "razorpay_signature": "signature",
                    }
                ),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.status.refresh_from_db()
        self.assertEqual(payment.status, CentreAnnualKYCPayment.Status.SUCCESS)
        self.assertIsNone(self.status.last_kyc_verified_at)
