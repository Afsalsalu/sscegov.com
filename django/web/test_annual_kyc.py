import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings
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

    def set_due_date(self, due_date):
        self.status.next_kyc_due_at = timezone.make_aware(
            datetime.combine(due_date, datetime.min.time())
        )
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))

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
        self.assertContains(renewal, "Annual KYC renewal expired")
        self.assertNotEqual(renewal.url if hasattr(renewal, "url") else "", reverse("web:annual_kyc"))

    def test_not_due_centre_can_open_kyc_page_and_sidebar_link_is_reversed(self):
        self.status.next_kyc_due_at = self.at(2027, 1, 1, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        client = Client()
        client.force_login(self.user)

        response = client.get(reverse("web:annual_kyc"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Annual KYC Renewal")
        self.assertEqual(
            response.context["annual_kyc"]["due_date"],
            timezone.localtime(self.status.next_kyc_due_at).date(),
        )
        self.assertContains(response, "Review your centre verification status and renewal details.")
        self.assertContains(response, "Not due yet")
        self.assertContains(response, "Your annual KYC renewal is not due yet.")
        self.assertContains(response, "Last verified")
        self.assertContains(response, "days remaining")
        self.assertContains(response, "Renewal fee")
        self.assertContains(response, "Annual KYC Renewal")
        self.assertContains(response, f'href="{reverse("web:annual_kyc")}"')
        self.assertNotContains(response, "Not_due")
        self.assertNotContains(response, "Pay &amp; Get OTP")

        dashboard = client.get(reverse("web:centre_dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, f'href="{reverse("web:annual_kyc")}"')
        self.assertNotContains(dashboard, "Pay &amp; Get OTP")

    def test_warning_banner_on_dashboard_shows_remaining_days_and_payment_action(self):
        self.set_due_date(timezone.localdate() + timedelta(days=30))
        client = Client()
        client.force_login(self.user)

        response = client.get(reverse("web:centre_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your annual KYC renewal is due in 30 days.")
        self.assertContains(response, f'href="{reverse("web:annual_kyc")}"')
        self.assertContains(response, "Pay &amp; Get OTP")

    @patch("web.annual_kyc_services._razorpay_client")
    def test_order_creation_uses_configured_annual_fee(self, mock_razorpay_client):
        self.set_due_date(timezone.localdate() + timedelta(days=10))
        self.settings.default_amount = Decimal("175.50")
        self.settings.save(update_fields=("default_amount", "updated_at"))
        mock_razorpay_client.return_value.order.create.return_value = {
            "id": "order_annual_fee"
        }
        client = Client()
        client.force_login(self.user)

        response = client.post(reverse("web:annual_kyc_order"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["amount"], 17550)
        order_data = mock_razorpay_client.return_value.order.create.call_args.kwargs[
            "data"
        ]
        self.assertEqual(order_data["amount"], 17550)
        payment = CentreAnnualKYCPayment.objects.get(
            razorpay_order_id="order_annual_fee"
        )
        self.assertEqual(payment.amount, Decimal("175.50"))

    def test_due_page_uses_friendly_status_label_and_keeps_payment_action(self):
        self.status.next_kyc_due_at = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("web:annual_kyc"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Renewal due")
        self.assertContains(response, "Pay &amp; Get OTP")
        self.assertContains(response, "Online renewal is available only for the next 30 days.")
        self.assertContains(response, 'class="annual-kyc-overlay"')
        self.assertContains(response, 'id="annual-pay-button-overlay"')
        self.assertNotContains(response, "Not_due")

    def test_expired_page_is_whatsapp_only_and_contains_centre_identity(self):
        client = Client()
        self.settings.whatsapp_support_number = "919876543210"
        self.settings.whatsapp_message_template = "Configured annual KYC message for {centre_name} ({centre_id})"
        self.settings.expired_message = "Configured expired annual KYC message."
        self.settings.save(
            update_fields=(
                "whatsapp_support_number",
                "whatsapp_message_template",
                "expired_message",
                "updated_at",
            )
        )
        self.status.next_kyc_due_at = self.at(2025, 1, 1, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        client.force_login(self.user)
        response = client.get(reverse("web:annual_kyc"))
        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Annual KYC renewal expired", body)
        self.assertIn("Configured expired annual KYC message.", body)
        self.assertIn("Online renewal is no longer available. Please contact Head Office for assistance.", body)
        self.assertIn('id="annual-kyc-expired-whatsapp"', body)
        self.assertIn("Contact on WhatsApp", body)
        self.assertIn("Contact us on WhatsApp", body)
        self.assertIn("Online renewal expired", body)
        self.assertNotIn("Pay &amp; Get OTP", body)
        self.assertNotIn('id="annual-pay-button-overlay"', body)
        self.assertNotIn('id="annual-pay-button"', body)
        self.assertNotIn('id="annual-kyc-otp-panel"', body)
        self.assertNotIn('id="annual-verify-otp"', body)
        self.assertNotIn('id="annual-resend-otp"', body)
        self.assertNotIn("checkout.razorpay.com", body)
        whatsapp_url = response.context["annual_kyc_whatsapp_url"]
        self.assertEqual(urlparse(whatsapp_url).netloc, "wa.me")
        self.assertEqual(urlparse(whatsapp_url).path, "/919876543210")
        self.assertEqual(
            parse_qs(urlparse(whatsapp_url).query)["text"][0],
            f"Configured annual KYC message for {self.centre.centre_name} ({self.centre.formatted_id})",
        )
        self.assertIn("Annual+Centre", body)
        self.assertIn(self.centre.formatted_id, body)

    def test_expired_popup_without_whatsapp_number_shows_support_message(self):
        self.settings.whatsapp_support_number = ""
        self.settings.save(update_fields=("whatsapp_support_number", "updated_at"))
        self.status.next_kyc_due_at = self.at(2025, 1, 1, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        client = Client()
        client.force_login(self.user)

        with override_settings(SUPPORT_WHATSAPP_NUMBER=""):
            response = client.get(reverse("web:annual_kyc"))

        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Annual KYC renewal expired")
        self.assertContains(response, "Please contact Head Office for assistance.")
        self.assertNotIn('id="annual-kyc-expired-whatsapp"', body)

    def test_expired_cycle_disables_payment_and_otp_endpoints(self):
        self.settings.whatsapp_support_number = "919876543210"
        self.settings.save(update_fields=("whatsapp_support_number", "updated_at"))
        self.status.next_kyc_due_at = self.at(2025, 1, 1, 0)
        self.status.save(update_fields=("next_kyc_due_at", "updated_at"))
        payment = self.make_payment(status=CentreAnnualKYCPayment.Status.SUCCESS)
        otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=self.centre,
            payment=payment,
            otp_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=10),
            resend_available_at=timezone.now(),
        )
        client = Client()
        client.force_login(self.user)
        session = client.session
        session["annual_kyc_payment_id"] = payment.pk
        session.save()

        page = client.get(reverse("web:annual_kyc"))
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("annual-kyc-otp is-visible", page.content.decode())
        dashboard = client.get(reverse("web:centre_dashboard"))
        self.assertEqual(dashboard.status_code, 302)
        self.assertEqual(dashboard.url, reverse("web:annual_kyc"))

        resend = client.post(reverse("web:annual_kyc_resend_otp"))
        verify = client.post(
            reverse("web:annual_kyc_verify_otp"), {"otp": "123456"}
        )

        self.assertEqual(resend.status_code, 403)
        self.assertEqual(verify.status_code, 403)
        self.status.refresh_from_db()
        otp.refresh_from_db()
        self.assertIsNone(self.status.last_kyc_verified_at)
        self.assertEqual(otp.status, CentreAnnualKYCOTPVerification.Status.SENT)

    @patch("web.annual_kyc_services._razorpay_client")
    def test_grace_period_keeps_payment_available(self, mock_razorpay_client):
        self.set_due_date(timezone.localdate() - timedelta(days=1))
        mock_razorpay_client.return_value.order.create.return_value = {
            "id": "order_grace"
        }
        client = Client()
        client.force_login(self.user)

        page = client.get(reverse("web:annual_kyc"))
        order = client.post(reverse("web:annual_kyc_order"))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Grace period active")
        self.assertContains(page, "Pay &amp; Get OTP")
        self.assertContains(page, "Online renewal is available for 29 more days.")
        self.assertContains(page, 'class="annual-kyc-overlay"')
        self.assertContains(page, 'id="annual-pay-button-overlay"')
        self.assertEqual(order.status_code, 200)
        self.assertEqual(order.json()["razorpay_order_id"], "order_grace")

    def test_completed_cycle_does_not_offer_payment_again(self):
        payment = self.make_payment()
        otp = CentreAnnualKYCOTPVerification.objects.create(
            centre=self.centre,
            payment=payment,
            otp_hash=make_password("123456"),
            expires_at=timezone.now() + timedelta(minutes=10),
            resend_available_at=timezone.now(),
        )
        verify_annual_kyc_otp(payment, "123456")
        client = Client()
        client.force_login(self.user)

        response = client.get(reverse("web:annual_kyc"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not due yet")
        self.status.refresh_from_db()
        self.assertEqual(
            response.context["annual_kyc"]["due_date"],
            timezone.localtime(self.status.next_kyc_due_at).date(),
        )
        self.assertNotContains(response, "Pay &amp; Get OTP")
        otp.refresh_from_db()
        self.assertEqual(otp.status, CentreAnnualKYCOTPVerification.Status.VERIFIED)

    def test_verified_payment_uses_configured_sms_backend(self):
        payment = self.make_payment(status=CentreAnnualKYCPayment.Status.CREATED)
        sms_backend = Mock(return_value=True)
        with override_settings(ANNUAL_KYC_SMS_BACKEND="tests.sms_backend"):
            with patch(
                "web.annual_kyc_services.import_string", return_value=sms_backend
            ):
                completed, otp, _ = complete_annual_kyc_payment(
                    payment.pk,
                    payment_id_value="pay_sms_backend",
                    signature="verified_signature",
                )

        self.assertEqual(completed.status, CentreAnnualKYCPayment.Status.SUCCESS)
        self.assertEqual(otp.status, CentreAnnualKYCOTPVerification.Status.SENT)
        sms_backend.assert_called_once()
        recipient, message = sms_backend.call_args.args[:2]
        self.assertEqual(recipient, str(self.centre.mobile))
        self.assertRegex(message, r"\b\d{6}\b")
        self.assertEqual(sms_backend.call_args.kwargs["centre"], self.centre)

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
        self.assertContains(response, "Annual Centre KYC Settings")
        self.assertContains(response, "group-data-[sidebar-size=lg]:ltr:md:ml-vertical-menu")
        self.assertContains(response, "pt-[calc(theme('spacing.header')_*_1)]")
        self.assertContains(response, "Renewal &amp; Payment")
        self.assertContains(response, "OTP Verification")
        self.assertContains(response, "Messages &amp; WhatsApp Support")
        self.assertContains(response, 'class="annual-admin-button')
        self.assertContains(response, "Save Settings")
        self.assertContains(response, "Annual Centre")
        detail = client.get(reverse("web:annual_kyc_centre", kwargs={"pk": self.centre.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "group-data-[sidebar-size=lg]:ltr:md:ml-vertical-menu")
        self.assertContains(detail, "pt-[calc(theme('spacing.header')_*_1)]")
        self.assertContains(detail, "Centre Controls")
        self.assertContains(detail, "Last verified")
        self.assertContains(detail, "Next due")
        self.assertContains(detail, "Current fee")
        self.assertContains(detail, "Payment History")
        self.assertContains(detail, "Audit History")
        self.assertContains(detail, 'name="fee_override"')
        self.assertContains(detail, 'name="manual_due_date"')
        self.assertContains(detail, "Mark as Verified")

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
        self.set_due_date(timezone.localdate() + timedelta(days=10))
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

    def test_verified_webhook_marks_payment_success_but_waits_for_otp(self):
        self.set_due_date(timezone.localdate() + timedelta(days=10))
        payment = self.make_payment(status=CentreAnnualKYCPayment.Status.CREATED)
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook",
                        "order_id": payment.razorpay_order_id,
                        "amount": int(payment.amount * Decimal("100")),
                        "status": "captured",
                    }
                }
            },
        }
        razorpay_client = Mock()
        with override_settings(RAZORPAY_WEBHOOK_SECRET="webhook_secret"), patch(
            "web.annual_kyc_views.razorpay.Client", return_value=razorpay_client
        ) as client_factory, patch(
            "web.annual_kyc_services._send_annual_kyc_sms", return_value=True
        ):
            client = Client()
            response = client.post(
                reverse("web:annual_kyc_webhook"),
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_RAZORPAY_SIGNATURE="webhook_signature",
            )

        self.assertEqual(response.status_code, 200)
        client_factory.assert_called_once()
        razorpay_client.utility.verify_webhook_signature.assert_called_once_with(
            json.dumps(payload), "webhook_signature", "webhook_secret"
        )
        payment.refresh_from_db()
        self.status.refresh_from_db()
        self.assertEqual(payment.status, CentreAnnualKYCPayment.Status.SUCCESS)
        self.assertIsNone(self.status.last_kyc_verified_at)
        self.assertEqual(
            payment.otp_verifications.latest("sent_at").status,
            CentreAnnualKYCOTPVerification.Status.SENT,
        )
