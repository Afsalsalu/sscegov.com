from email.utils import make_msgid
import logging
import re
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.validators import validate_email
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, ListView

from .enquiry_forms import FranchiseEnquiryForm, FranchiseEnquiryReplyForm
from .models import FranchiseEnquiry
from .views import AdminOrHeadOfficeRequiredMixin, KeralaRequiredMixin


logger = logging.getLogger(__name__)


def _is_valid_message_id(value):
    return bool(re.fullmatch(r"<[^<>\s@\r\n]+@[^<>\s@\r\n]+>", value or ""))


def _safe_reply_to(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        validate_email(value)
    except ValidationError:
        return None
    return value


def _franchise_enquiries_for_user(user):
    return FranchiseEnquiry.objects.filter(user=user).select_related("centre", "user", "replied_by")


def _send_enquiry_notification(enquiry):
    recipient = getattr(settings, "ENQUIRY_ADMIN_EMAIL", "")
    if not recipient:
        logger.error("Franchise enquiry %s was saved, but no notification recipient is configured.", enquiry.pk)
        return False

    created_at = timezone.localtime(enquiry.created_at).strftime("%d %b %Y, %I:%M %p %Z")
    phone = enquiry.contact_phone or "Not provided"
    body = (
        f"Franchise enquiry reference: #{enquiry.pk}\n"
        f"Centre: {enquiry.franchise_centre_name}\n"
        f"Franchise user: {enquiry.franchise_user_name}\n"
        f"Registered email: {enquiry.franchise_email}\n"
        f"Phone: {phone}\n"
        f"Subject: {enquiry.subject}\n"
        f"Created: {created_at}\n\n"
        f"Message:\n{enquiry.message}"
    )

    try:
        message_id = enquiry.original_notification_message_id
        if not _is_valid_message_id(message_id):
            message_id = make_msgid()
        email_kwargs = {
            "subject": f"New franchise enquiry [#{enquiry.pk}]: {enquiry.subject}",
            "body": body,
            "from_email": settings.DEFAULT_FROM_EMAIL,
            "to": [recipient],
            "connection": get_connection(fail_silently=False),
        }
        reply_to = _safe_reply_to(enquiry.franchise_email)
        if reply_to:
            email_kwargs["reply_to"] = [reply_to]
        email = EmailMessage(**email_kwargs)
        email.extra_headers["Message-ID"] = message_id
        if enquiry.attachment:
            extension = Path(enquiry.attachment.name).suffix.lower()
            content_types = {
                ".pdf": "application/pdf",
                ".doc": "application/msword",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
            }
            with enquiry.attachment.open("rb") as attachment:
                email.attach(
                    Path(enquiry.attachment.name).name,
                    attachment.read(),
                    content_types.get(extension, "application/octet-stream"),
                )
        sent = email.send(fail_silently=False) == 1
    except Exception:
        logger.exception("Email delivery failed for franchise enquiry %s.", enquiry.pk)
        return False

    if sent and message_id != enquiry.original_notification_message_id:
        enquiry.original_notification_message_id = message_id
        try:
            enquiry.save(update_fields=("original_notification_message_id", "updated_at"))
        except Exception:
            logger.exception(
                "Notification sent for franchise enquiry %s, but its Message-ID could not be stored.",
                enquiry.pk,
            )
    return sent


def _send_enquiry_reply(enquiry):
    if not enquiry.franchise_email:
        logger.error("Reply for franchise enquiry %s has no registered email address.", enquiry.pk)
        return False

    created_at = timezone.localtime(enquiry.created_at).strftime("%d %b %Y, %I:%M %p %Z")
    body = (
        f"Hello {enquiry.franchise_user_name},\n\n"
        f"Head Office has replied to your franchise enquiry #{enquiry.pk}.\n\n"
        f"Centre: {enquiry.franchise_centre_name}\n"
        f"Original subject: {enquiry.subject}\n"
        f"Submitted: {created_at}\n\n"
        f"Your message:\n{enquiry.message}\n\n"
        f"Head Office reply:\n{enquiry.admin_reply}\n"
    )

    try:
        email_kwargs = {
            "subject": f"Re: New franchise enquiry [#{enquiry.pk}]: {enquiry.subject}",
            "body": body,
            "from_email": settings.DEFAULT_FROM_EMAIL,
            "to": [enquiry.franchise_email],
            "connection": get_connection(fail_silently=False),
        }
        reply_to = _safe_reply_to(getattr(settings, "ENQUIRY_ADMIN_EMAIL", ""))
        if reply_to:
            email_kwargs["reply_to"] = [reply_to]
        email = EmailMessage(**email_kwargs)
        original_message_id = enquiry.original_notification_message_id
        if _is_valid_message_id(original_message_id):
            email.extra_headers["In-Reply-To"] = original_message_id
            email.extra_headers["References"] = original_message_id
        return email.send(fail_silently=False) == 1
    except Exception:
        logger.exception("Email delivery failed for the reply to franchise enquiry %s.", enquiry.pk)
        return False


class FranchiseEnquiryComposeView(KeralaRequiredMixin, FormView):
    template_name = "web/franchise/enquiries/compose.html"
    form_class = FranchiseEnquiryForm

    def form_valid(self, form):
        try:
            centre = self.request.user.centre
        except AttributeError:
            raise Http404("This account is not linked to a franchise centre.")

        centre_name = (centre.centre_name or centre.owner_centre or "Franchise Centre").strip()
        franchise_user_name = (centre.name or "").strip()
        if not franchise_user_name or franchise_user_name.casefold() == "none":
            franchise_user_name = self.request.user.get_full_name().strip() or self.request.user.username
        phone = centre.mobile or centre.centre_phone_number or ""
        enquiry = FranchiseEnquiry.objects.create(
            user=self.request.user,
            centre=centre,
            franchise_centre_name=centre_name,
            franchise_user_name=franchise_user_name,
            franchise_email=centre.email or self.request.user.email,
            contact_phone=str(phone),
            subject=form.cleaned_data["subject"],
            message=form.cleaned_data["message"],
            attachment=form.cleaned_data.get("attachment"),
        )

        if _send_enquiry_notification(enquiry):
            messages.success(self.request, "Your enquiry was submitted successfully.")
        else:
            messages.warning(
                self.request,
                "Your enquiry was saved, but email notification could not be sent.",
            )
        return redirect("web:franchise_enquiry_detail", pk=enquiry.pk)


class FranchiseEnquiryHistoryView(KeralaRequiredMixin, ListView):
    template_name = "web/franchise/enquiries/history.html"
    context_object_name = "enquiries"
    paginate_by = 20

    def get_queryset(self):
        return _franchise_enquiries_for_user(self.request.user)


class FranchiseEnquiryDetailView(KeralaRequiredMixin, View):
    template_name = "web/franchise/enquiries/detail.html"

    def get(self, request, pk):
        enquiry = get_object_or_404(_franchise_enquiries_for_user(request.user), pk=pk)
        return render(request, self.template_name, {"enquiry": enquiry})


class FranchiseEnquiryInboxView(AdminOrHeadOfficeRequiredMixin, ListView):
    template_name = "web/headoffice/enquiries/inbox.html"
    context_object_name = "enquiries"
    paginate_by = 30

    def get_queryset(self):
        queryset = FranchiseEnquiry.objects.select_related("centre", "user", "replied_by")
        status_filter = self.request.GET.get("status", "").strip().lower()
        if status_filter in FranchiseEnquiry.Status.values:
            queryset = queryset.filter(status=status_filter)

        search = self.request.GET.get("q", "").strip()
        if search:
            from django.db.models import Q

            search_filter = (
                Q(franchise_centre_name__icontains=search)
                | Q(franchise_user_name__icontains=search)
                | Q(franchise_email__icontains=search)
                | Q(subject__icontains=search)
            )
            reference_number = search.removeprefix("#").strip()
            if reference_number.isdecimal():
                search_filter |= Q(pk=int(reference_number))
            queryset = queryset.filter(search_filter)
        return queryset.order_by("-created_at", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["open_enquiry_count"] = FranchiseEnquiry.objects.filter(
            status=FranchiseEnquiry.Status.OPEN
        ).count()
        return context


class FranchiseEnquiryAdminDetailView(AdminOrHeadOfficeRequiredMixin, View):
    template_name = "web/headoffice/enquiries/detail.html"

    def get_object(self, pk):
        return get_object_or_404(
            FranchiseEnquiry.objects.select_related("centre", "user", "replied_by"), pk=pk
        )

    def get(self, request, pk):
        enquiry = self.get_object(pk)
        return render(
            request,
            self.template_name,
            {"enquiry": enquiry, "reply_form": FranchiseEnquiryReplyForm()},
        )

    def post(self, request, pk):
        enquiry = self.get_object(pk)
        form = FranchiseEnquiryReplyForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"enquiry": enquiry, "reply_form": form},
            )

        reply_text = form.cleaned_data["reply"]
        status = form.cleaned_data["status"]
        if reply_text:
            enquiry.admin_reply = reply_text
            enquiry.replied_at = timezone.now()
            enquiry.replied_by = request.user
            enquiry.status = FranchiseEnquiry.Status.REPLIED
            enquiry.save(
                update_fields=("admin_reply", "replied_at", "replied_by", "status", "updated_at")
            )
            if _send_enquiry_reply(enquiry):
                messages.success(request, "Reply saved and emailed to the franchise contact.")
            else:
                messages.warning(
                    request,
                    "Reply saved, but email delivery failed. The reply remains available in the franchise enquiry history.",
                )
        else:
            enquiry.status = status
            if status == FranchiseEnquiry.Status.REPLIED:
                enquiry.replied_at = timezone.now()
                enquiry.replied_by = request.user
                enquiry.save(update_fields=("status", "replied_at", "replied_by", "updated_at"))
            else:
                enquiry.save(update_fields=("status", "updated_at"))
            messages.success(request, f"Enquiry status updated to {enquiry.get_status_display()}.")

        return redirect("web:franchise_enquiry_admin_detail", pk=enquiry.pk)


class FranchiseEnquiryAttachmentView(View):
    """Stream an attachment only after role and record ownership checks."""

    def get(self, request, pk):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())

        if request.user.usertype in {"Administrator", "HeadOffice"}:
            queryset = FranchiseEnquiry.objects.all()
        elif request.user.usertype == "centre":
            queryset = FranchiseEnquiry.objects.filter(user=request.user)
        else:
            raise Http404

        enquiry = get_object_or_404(queryset, pk=pk)
        if not enquiry.attachment:
            raise Http404

        try:
            handle = enquiry.attachment.open("rb")
        except (OSError, ValueError, FileNotFoundError):
            logger.exception("Attachment unavailable for franchise enquiry %s.", enquiry.pk)
            raise Http404

        extension = Path(enquiry.attachment.name).suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        return FileResponse(
            handle,
            as_attachment=True,
            filename=Path(enquiry.attachment.name).name,
            content_type=content_types.get(extension, "application/octet-stream"),
        )
