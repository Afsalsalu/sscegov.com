import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CentreUserAccount, FranchiseEnquiry
from .enquiry_utils import get_support_whatsapp_url


User = get_user_model()
VALID_PDF = b"%PDF-1.4\n% enquiry attachment\n"


class FranchiseEnquiryTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="notifications@example.test",
            ENQUIRY_ADMIN_EMAIL="head-office@example.test",
            MEDIA_ROOT=str(Path(self.media_directory.name) / "public_media"),
            PRIVATE_MEDIA_ROOT=str(Path(self.media_directory.name) / "private_media"),
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)
        mail.get_connection()
        mail.outbox.clear()

        self.franchise_user, self.centre = self.make_franchise("franchise-one")
        self.other_user, self.other_centre = self.make_franchise("franchise-two")
        self.head_office_user = User.objects.create_user(
            username="head-office",
            password="test-password",
            email="ho-user@example.test",
            usertype="HeadOffice",
        )

    def make_franchise(self, username):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            email=f"{username}@auth.example.test",
            usertype="centre",
            first_name="Browser supplied name should be ignored",
        )
        centre = CentreUserAccount.objects.create(
            user=user,
            name=f"Manager {username}",
            username=username,
            owner_centre=f"Owner centre {username}",
            centre_name=f"Centre {username}",
            mobile=9876543210,
            aadhaar_number=123456789012,
            email=f"{username}@registered.example.test",
            centre_phone_number=9123456780,
            state="kerala",
            taluk="Kochi",
            location="Kochi",
        )
        return user, centre

    def make_enquiry(self, user=None, centre=None, attachment=None, **overrides):
        user = user or self.franchise_user
        centre = centre or self.centre
        values = {
            "user": user,
            "centre": centre,
            "franchise_centre_name": centre.centre_name,
            "franchise_user_name": centre.name,
            "franchise_email": centre.email,
            "contact_phone": str(centre.mobile),
            "subject": "Account support request",
            "message": "Please help with this account question.",
            "attachment": attachment,
        }
        values.update(overrides)
        return FranchiseEnquiry.objects.create(**values)

    def restrict_centre(self):
        self.centre.manual_disabled = True
        self.centre.manual_disable_reason = "Pending document verification"
        self.centre.save(update_fields=("manual_disabled", "manual_disable_reason"))

    def test_reactivation_page_uses_public_home_and_modal_submission_endpoint(self):
        self.restrict_centre()
        self.client.force_login(self.franchise_user)

        response = self.client.get(reverse("web:centre_reactivation"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-home-url="/"')
        self.assertContains(response, "Send Reactivation Enquiry")
        self.assertContains(response, reverse("web:franchise_reactivation_enquiry"))
        self.assertNotContains(response, reverse("web:franchise_enquiry_compose"))

    def test_reactivation_enquiry_uses_server_identity_and_sends_to_head_office(self):
        self.restrict_centre()
        self.client.force_login(self.franchise_user)

        response = self.client.post(
            reverse("web:franchise_reactivation_enquiry"),
            {
                "subject": "Centre Enable Request",
                "message": "Please enable this centre.",
                "centre_id": "forged-centre-id",
                "centre_name": "Forged centre",
                "attachment": SimpleUploadedFile(
                    "reactivation-proof.pdf", VALID_PDF, "application/pdf"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Your enquiry has been sent to Head Office successfully.")
        enquiry = FranchiseEnquiry.objects.get()
        self.assertEqual(enquiry.centre, self.centre)
        self.assertEqual(enquiry.user, self.franchise_user)
        self.assertIn(f"Centre ID: {self.centre.formatted_id}", enquiry.message)
        self.assertIn("Disable reason: Pending document verification", enquiry.message)
        self.assertNotIn("forged-centre-id", enquiry.message)
        self.assertNotIn("Forged centre", enquiry.message)
        self.assertTrue(enquiry.attachment.name.startswith("franchise_enquiries/"))
        self.assertEqual(mail.outbox[0].to, [settings.ENQUIRY_ADMIN_EMAIL])
        self.client.force_login(self.head_office_user)
        inbox = self.client.get(reverse("web:franchise_enquiry_inbox"))
        self.assertContains(inbox, "Centre Enable Request")
        detail = self.client.get(reverse("web:franchise_enquiry_admin_detail", args=[enquiry.pk]))
        self.assertContains(detail, "Disable reason: Pending document verification")

    def test_reactivation_enquiry_validation_errors_stay_in_json_and_do_not_create_record(self):
        self.restrict_centre()
        self.client.force_login(self.franchise_user)

        response = self.client.post(
            reverse("web:franchise_reactivation_enquiry"),
            {"subject": "Centre Enable Request", "message": ""},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.json()["errors"])
        self.assertEqual(FranchiseEnquiry.objects.count(), 0)

    def test_franchise_submission_saves_server_identity_and_uses_configured_recipient(self):
        self.client.force_login(self.franchise_user)
        response = self.client.post(
            reverse("web:franchise_enquiry_compose"),
            {
                "subject": "New service question",
                "message": "Please explain this service.",
                "recipient": "attacker@example.test",
                "email": "attacker@example.test",
                "centre_name": "Forged centre",
                "user_name": "Forged user",
            },
            follow=True,
        )

        self.assertEqual(
            response.redirect_chain,
            [(reverse("web:franchise_enquiry_detail", args=[1]), 302)],
        )
        self.assertContains(response, "Your enquiry was submitted successfully.")
        enquiry = FranchiseEnquiry.objects.get()
        self.assertEqual(enquiry.user, self.franchise_user)
        self.assertEqual(enquiry.centre, self.centre)
        self.assertEqual(enquiry.franchise_centre_name, self.centre.centre_name)
        self.assertEqual(enquiry.franchise_user_name, self.centre.name)
        self.assertEqual(enquiry.franchise_email, self.centre.email)
        self.assertEqual(enquiry.contact_phone, str(self.centre.mobile))
        self.assertEqual(mail.outbox[0].to, [settings.ENQUIRY_ADMIN_EMAIL])
        self.assertEqual(mail.outbox[0].reply_to, [enquiry.franchise_email])
        self.assertNotIn("attacker@example.test", mail.outbox[0].to)
        self.assertIn(f"#{enquiry.pk}", mail.outbox[0].body)
        self.assertTrue(enquiry.original_notification_message_id)
        self.assertEqual(
            mail.outbox[0].extra_headers.get("Message-ID"),
            enquiry.original_notification_message_id,
        )

    def test_valid_attachment_is_stored_with_generated_name_and_attached_to_notification(self):
        self.client.force_login(self.franchise_user)
        response = self.client.post(
            reverse("web:franchise_enquiry_compose"),
            {
                "subject": "Document review",
                "message": "Please review the attached PDF.",
                "attachment": SimpleUploadedFile("my-private-name.pdf", VALID_PDF, "application/pdf"),
            },
        )

        self.assertEqual(response.status_code, 302)
        enquiry = FranchiseEnquiry.objects.get()
        self.assertTrue(enquiry.attachment.name.startswith("franchise_enquiries/"))
        self.assertNotIn("my-private-name", enquiry.attachment.name)
        self.assertTrue(Path(settings.PRIVATE_MEDIA_ROOT, enquiry.attachment.name).is_file())
        self.assertFalse(Path(settings.MEDIA_ROOT, enquiry.attachment.name).exists())
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[0].attachments[0][0].split(".")[-1], "pdf")

    def test_invalid_attachment_extension_content_and_size_are_rejected(self):
        self.client.force_login(self.franchise_user)
        compose_url = reverse("web:franchise_enquiry_compose")
        invalid_uploads = (
            SimpleUploadedFile("payload.exe", VALID_PDF),
            SimpleUploadedFile("disguised.pdf", b"<html>not a PDF</html>"),
            SimpleUploadedFile("oversized.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024)),
        )

        for upload in invalid_uploads:
            with self.subTest(filename=upload.name):
                response = self.client.post(
                    compose_url,
                    {"subject": "File check", "message": "Check this upload.", "attachment": upload},
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "enquiry-errors")
                self.assertEqual(FranchiseEnquiry.objects.count(), 0)

    def test_head_office_sees_all_enquiries_and_franchise_history_is_scoped(self):
        first = self.make_enquiry(subject="First centre request")
        second = self.make_enquiry(
            user=self.other_user,
            centre=self.other_centre,
            subject="Second centre request",
        )

        self.client.force_login(self.head_office_user)
        inbox_response = self.client.get(reverse("web:franchise_enquiry_inbox"))
        self.assertEqual(inbox_response.status_code, 200)
        self.assertContains(inbox_response, "First centre request")
        self.assertContains(inbox_response, "Second centre request")
        reference_search = self.client.get(
            reverse("web:franchise_enquiry_inbox"), {"q": f"#{second.pk}"}
        )
        self.assertContains(reference_search, "Second centre request")
        self.assertNotContains(reference_search, "First centre request")
        head_office_dashboard = self.client.get(reverse("web:headoffice_dashboard"))
        self.assertContains(head_office_dashboard, "Franchise enquiries")
        self.assertContains(head_office_dashboard, "2 open")
        admin_dashboard = self.client.get(reverse("web:admin_dashboard"))
        self.assertContains(admin_dashboard, "Franchise enquiries")
        self.assertContains(admin_dashboard, "2 open")

        self.client.force_login(self.franchise_user)
        history_response = self.client.get(reverse("web:franchise_enquiry_history"))
        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, "First centre request")
        self.assertNotContains(history_response, "Second centre request")
        self.assertEqual(
            self.client.get(reverse("web:franchise_enquiry_detail", args=[second.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("web:franchise_enquiry_detail", args=[first.pk])).status_code,
            200,
        )

    def test_head_office_reply_is_saved_and_sent_to_registered_franchise_email(self):
        original_message_id = "<original-enquiry@example.test>"
        enquiry = self.make_enquiry(original_notification_message_id=original_message_id)
        self.client.force_login(self.head_office_user)
        response = self.client.post(
            reverse("web:franchise_enquiry_admin_detail", args=[enquiry.pk]),
            {
                "reply": "We have updated your account. Please sign in again.",
                "status": "closed",
                "recipient": "attacker@example.test",
            },
        )

        self.assertRedirects(
            response,
            reverse("web:franchise_enquiry_admin_detail", args=[enquiry.pk]),
        )
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.admin_reply, "We have updated your account. Please sign in again.")
        self.assertEqual(enquiry.status, FranchiseEnquiry.Status.REPLIED)
        self.assertEqual(enquiry.replied_by, self.head_office_user)
        self.assertIsNotNone(enquiry.replied_at)
        self.assertEqual(mail.outbox[0].to, [self.centre.email])
        self.assertEqual(mail.outbox[0].reply_to, [settings.ENQUIRY_ADMIN_EMAIL])
        self.assertEqual(
            mail.outbox[0].subject,
            f"Re: New franchise enquiry [#{enquiry.pk}]: {enquiry.subject}",
        )
        self.assertEqual(mail.outbox[0].extra_headers.get("In-Reply-To"), original_message_id)
        self.assertEqual(mail.outbox[0].extra_headers.get("References"), original_message_id)
        self.client.force_login(self.franchise_user)
        history_response = self.client.get(reverse("web:franchise_enquiry_history"))
        self.assertContains(history_response, "We have updated your account.")

    def test_old_enquiry_without_message_id_sends_reply_without_threading_headers(self):
        enquiry = self.make_enquiry(original_notification_message_id="")
        self.client.force_login(self.head_office_user)

        response = self.client.post(
            reverse("web:franchise_enquiry_admin_detail", args=[enquiry.pk]),
            {"reply": "Here is the requested information.", "status": ""},
        )

        self.assertEqual(response.status_code, 302)
        reply = mail.outbox[0]
        self.assertEqual(reply.to, [self.centre.email])
        self.assertEqual(
            reply.subject,
            f"Re: New franchise enquiry [#{enquiry.pk}]: {enquiry.subject}",
        )
        self.assertNotIn("In-Reply-To", reply.extra_headers)
        self.assertNotIn("References", reply.extra_headers)

    def test_invalid_reply_to_addresses_are_omitted(self):
        enquiry = self.make_enquiry(franchise_email="not-an-email")

        with override_settings(ENQUIRY_ADMIN_EMAIL="also-not-an-email"):
            from .enquiry_views import _send_enquiry_notification, _send_enquiry_reply

            self.assertTrue(_send_enquiry_notification(enquiry))
            self.assertNotIn("Reply-To", mail.outbox[0].extra_headers)

            enquiry.admin_reply = "Here is the requested information."
            self.assertTrue(_send_enquiry_reply(enquiry))

        self.assertNotIn("Reply-To", mail.outbox[1].extra_headers)

    def test_mail_delivery_failure_does_not_lose_enquiry_or_reply(self):
        self.client.force_login(self.franchise_user)
        with patch("web.enquiry_views.EmailMessage.send", side_effect=RuntimeError("mail unavailable")):
            response = self.client.post(
                reverse("web:franchise_enquiry_compose"),
                {"subject": "Saved before email", "message": "Keep this request."},
                follow=True,
            )
        self.assertContains(
            response,
            "Your enquiry was saved, but email notification could not be sent.",
        )
        enquiry = FranchiseEnquiry.objects.get(subject="Saved before email")
        self.assertEqual(enquiry.franchise_email, self.centre.email)

        self.client.force_login(self.head_office_user)
        with patch("web.enquiry_views.EmailMessage.send", side_effect=RuntimeError("mail unavailable")):
            response = self.client.post(
                reverse("web:franchise_enquiry_admin_detail", args=[enquiry.pk]),
                {"reply": "This reply must remain saved.", "status": ""},
            )
        self.assertEqual(response.status_code, 302)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.admin_reply, "This reply must remain saved.")
        self.assertEqual(enquiry.status, FranchiseEnquiry.Status.REPLIED)

    def test_only_head_office_can_reply_and_attachment_download_is_scoped(self):
        enquiry = self.make_enquiry(attachment=SimpleUploadedFile("proof.pdf", VALID_PDF))
        self.client.force_login(self.other_user)

        self.assertEqual(
            self.client.get(reverse("web:franchise_enquiry_attachment", args=[enquiry.pk])).status_code,
            404,
        )
        reply_response = self.client.post(
            reverse("web:franchise_enquiry_admin_detail", args=[enquiry.pk]),
            {"reply": "Unauthorized reply", "status": ""},
        )
        self.assertEqual(reply_response.status_code, 302)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.admin_reply, "")

        self.client.force_login(self.franchise_user)
        own_attachment_response = self.client.get(
            reverse("web:franchise_enquiry_attachment", args=[enquiry.pk])
        )
        self.assertEqual(own_attachment_response.status_code, 200)
        self.assertEqual(own_attachment_response["Content-Disposition"].split(";")[0], "attachment")
        own_attachment_response.close()

    def test_dashboard_shows_floating_enquiry_and_unavailable_whatsapp_fallback(self):
        self.client.force_login(self.franchise_user)
        with override_settings(SUPPORT_WHATSAPP_NUMBER=""):
            response = self.client.get(reverse("web:centre_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enquiry")
        self.assertContains(response, "WhatsApp support is currently unavailable")
        self.assertNotContains(response, "https://wa.me/")

    def test_whatsapp_url_requires_a_valid_international_number_and_encodes_message(self):
        with override_settings(SUPPORT_WHATSAPP_NUMBER="+91 (98765) 43210"):
            url = get_support_whatsapp_url()
        self.assertTrue(url.startswith("https://wa.me/919876543210?text="))
        self.assertIn("franchise+account", url)

        with override_settings(SUPPORT_WHATSAPP_NUMBER="support-12345678"):
            self.assertEqual(get_support_whatsapp_url(), "")
