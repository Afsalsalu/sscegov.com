import json
import logging
import random

import requests
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.core import serializers
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

logger = logging.getLogger(__name__)
User = get_user_model()
import logging
from decimal import Decimal

import sib_api_v3_sdk
from django.contrib.auth import login as django_login
from django.contrib.auth import logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (PasswordResetCompleteView,
                                       PasswordResetConfirmView,
                                       PasswordResetDoneView,
                                       PasswordResetView)
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.utils.translation import gettext
# CRUD operations
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from django_ratelimit.decorators import ratelimit
from .banner_forms import BannerForm
from .service_forms import StateServiceForm, validate_detail_image
from .models import Banner
from sib_api_v3_sdk.rest import ApiException

# forms
from .forms import (CentreUserForm, DownloadFormForm, OnlineClassForm,
                    CustomPasswordChangeForm,
                    CustomPasswordResetForm, DepartmentForm, EmployeeForm,
                    HeadOfficeForm, KeralaSubCentreForm, LoginForm,
                    ServiceFilterForm, StateForm)
# models
from .models import (AboutBlog, AboutPage, AddState, Career, CareerForm,
                     CentreReactivationAuditLog, CentreReactivationSettings,
                     CentreUserAccount, CertificatePayment, Contact,
                     Department, DownloadForm, Employee, FailedLoginAttempt,
                     FranchiseEnquiry,
                     HeadOffice, HomeLogoBrand,
                     HomeService, KeralaSubCentre, LatestNewsCentre, Media,
                     OnlineClass, Software, State, StateService,
                     StateServiceDetailImage,
                     
                     Wallet,Table_Accountsmaster,Table_Acntchild,Table_Companydetailsmaster,Table_companyDetailschild,Table_DrCrNote,
		     Table_Journal_Entry,Table_Contra_Entry,Ledger,
		     Table_Voucher)
from .reactivation_services import calculate_reactivation_amount, mark_centre_inactive_if_due

from datetime import datetime




def index(request):
    return render(request,"web/accounts/receipt/receipt.html")




def safe_redirect(request):
    # Use a trusted list of redirect targets
    redirect_target = request.GET.get("next", "/")
    allowed_hosts = ["test.sscegov.com", "sscegov.com"]

    if redirect_target not in allowed_hosts:
        return redirect("/")

    return redirect(redirect_target)

from django.shortcuts import render

def custom_csrf_failure(request, reason=""):
    return redirect("web:login_view")
    
@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def sensitive_view(request):
    # Your sensitive view logic here
    pass



def logout_view(request):
    try:
        logout(request)
    except Exception as e:
        print("Logout error:", e)
    response = redirect("/")

    return response


def my_view(request):
    response = HttpResponse("Hello, world!")
    # response["Content-Security-Policy"] = (
    #     "default-src 'self'; "
    #     "script-src 'self' https://trusted.cdn.com; "
    #     "style-src 'self' https://trusted.cdn.com; "
    #     "img-src 'self' data:; "
    #     "connect-src 'self'; "
    #     "font-src 'self'; "
    #     "frame-ancestors 'none'; "
    #     "base-uri 'self';"
    # )
    return response


# Helper function to get client's IP address
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@ratelimit(key="ip", rate="5/m", method="ALL", block=True)
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            captcha_response = form.cleaned_data.get("captcha")

            # Authenticate the user
            user = authenticate(request, username=username, password=password)

            if user and captcha_response:  # Check if user is authenticated and CAPTCHA is valid
                if user.is_active:
                    centre = None
                    if user.usertype == "centre":
                        try:
                            centre = user.centre
                        except CentreUserAccount.DoesNotExist:
                            centre = None
                        if centre:
                            mark_centre_inactive_if_due(centre.pk)
                            centre.refresh_from_db()
                            if (
                                not centre.is_active
                                and not centre.inactive_due_to_inactivity
                                and not centre.manual_disabled
                            ):
                                form.add_error(
                                    None,
                                    "Your centre account is manually disabled. Please contact Head Office.",
                                )
                                return render(
                                    request,
                                    "web/registration/login.html",
                                    {"form": form},
                                )
                    login(request, user)
                    # Clear previous failed login attempts for this user
                    FailedLoginAttempt.objects.filter(user=user).delete()

                    # Redirect based on user type
                    if user.is_superuser:
                        return redirect("web:admin_dashboard")
                    elif user.usertype == "centre":
                        if centre and (
                            centre.inactive_due_to_inactivity or centre.manual_disabled
                        ):
                            return redirect("web:centre_reactivation")
                        return redirect("web:centre_dashboard")
                    elif user.usertype == "Employee":
                        return redirect("web:employee_dashboard")
                    elif user.usertype == "HeadOffice":
                        return redirect("web:headoffice_dashboard")
                    elif user.usertype == "State":
                        return redirect("web:state_dashboard")
                    elif user.usertype == "Subcentre":
                        return redirect("web:subcentre_dashboard")
                    else:
                        return redirect("web:not_found")
                else:
                    return HttpResponseBadRequest("Your account is inactive.")
            else:
                # Track failed login attempt
                ip_address = get_client_ip(request)  # Get the client's IP address

                if ip_address:  # Ensure we have a valid IP address
                    form.add_error(None, "Invalid username or password.")
                    return render(request, "web/registration/login.html", {"form": form, "error": "Invalid username or password."})
                else:
                    messages.error(request, "Could not record login attempt due to missing IP address.")
                    return render(
                        request,
                        "web/registration/login.html",
                        {"form": form, "error": "Invalid credentials or CAPTCHA."}, 
                    )
        else:
            return render(
                request,
                "web/registration/login.html",
                {"form": form, "error": "Invalid form submission."},
            )
    else:
        form = LoginForm()  
        response = render(request, "web/registration/login.html", {"form": form})
        for cookies in request.COOKIES:
            response.delete_cookie(cookies)
        return response

# class CustomLoginView(LoginView):
#     def form_valid(self, form):
#         user = form.get_user()

#         if not user.is_active:
#             messages.error(
#                 self.request, "Your account is inactive. Please contact support."
#             )
#             return redirect("login")

#         django_login(self.request, user)

#         # Update last_login for CentreUser
#         if hasattr(user, "centre"):
#             user.centre.last_login = timezone.now()
#             user.centre.save()

#         if user.is_superuser:
#             return redirect("web:admin_dashboard")
#         elif user.usertype == "centre":
#             return redirect("web:centre_dashboard")
#         elif user.usertype == "Employee":
#             return redirect("web:employee_dashboard")
#         elif user.usertype == "HeadOffice":
#             return redirect("web:headoffice_dashboard")
#         elif user.usertype == "State":
#             return redirect("web:state_dashboard")
#         elif user.usertype == "Subcentre":
#             return redirect("web:subcentre_dashboard")
#         else:
#             return redirect("web:not_found")


from django.db.utils import OperationalError
class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = "web/change_password.html"
    success_url = reverse_lazy("web:login_view")

    def form_valid(self, form):
        try:
            # ?? Try saving password normally
            response = super().form_valid(form)
        except OperationalError as e:
            # ?? Log error but don't show it to user
            print("Password save error:", e)
            response = redirect(self.success_url)

        # ?? Force logout (even if DB error happened)
        try:
            logout(self.request)
        except Exception as e:
            print("Logout error:", e)

        # ?? Always go to login page
        return redirect(f"{self.success_url}?password_changed=1")






class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = "web/registration/password_reset_form.html"
    email_template_name = "web/registration/password_reset_email.html"
    subject_template_name = "web/registration/password_reset_subject.txt"
    success_url = reverse_lazy("web:password_reset_done")

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "web/registration/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "web/registration/password_reset_confirm.html"
    success_url = reverse_lazy("web:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "web/registration/password_reset_complete.html"


# Home Page
def notfound(request, exception=None):
    return render(request, "web/404.html", status=404)


def index(request):
    home_services = HomeService.objects.all()
    blogs = AboutBlog.objects.all()
    logos = HomeLogoBrand.objects.all()
    context = {
        "blogs": blogs,
        "home_services": home_services,
        "logos": logos,
    }
    return render(request, "web/home/index.html", context)


def whatwedo(request):
    return render(request, "web/home/whatwedo.html")


def contact(request):
    if request.method == "POST":
        # Get form data
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        centre_name = request.POST.get("centre_name")
        state = request.POST.get("state")
        district = request.POST.get("district")
        taluk = request.POST.get("taluk")
        subject = request.POST.get("subject")
        comments = request.POST.get("comments")

        # reCAPTCHA validation
        recaptcha_response = request.POST.get("g-recaptcha-response")
        data = {
            "secret": "6LfhACgqAAAAAFqwP-iG32CZyREH66J6u43F-I8D",
            "response": recaptcha_response,
        }
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        result = r.json()

        if result["success"]:
            # Save contact form data to the database
            contact = Contact(
                full_name=full_name,
                phone=phone,
                email=email,
                centre_name=centre_name,
                state=state,
                district=district,
                taluk=taluk,
                subject=subject,
                comments=comments,
            )
            contact.save()
            return redirect("web:contact")
        else:
            # reCAPTCHA validation failed, return an error message
            context = {
                "error_message": "Invalid reCAPTCHA. Please try again.",
                "full_name": full_name,
                "phone": phone,
                "email": email,
                "centre_name": centre_name,
                "state": state,
                "district": district,
                "taluk": taluk,
                "subject": subject,
                "comments": comments,
            }
            return render(request, "web/home/contact.html", context)

    # Handle GET request or when form submission is not successful
    return render(request, "web/home/contact.html")


class MediaListView(ListView):
    model = Media
    template_name = "web/home/media.html"
    context_object_name = "media"


def about(request):
    about_content = AboutPage.objects.all()  # Query the AboutPage content
    blogs = AboutBlog.objects.all()  # Query all the blogs
    about_logos = HomeLogoBrand.objects.all()  # Query all the About Logos

    context = {
        "about_content": about_content,
        "blogs": blogs,
        "about_logos": about_logos,
    }
    return render(request, "web/home/about.html", context)


class Admin(ListView):
    model = Career
    template_name = "web/home/career.html"
    context_object_name = "career"


class CareerListView(ListView):
    model = Career
    template_name = "web/home/career.html"
    context_object_name = "career"


def privacy_policy(request):
    return render(request, "web/home/privacy_policy.html")

def Cancellation_Refund_Policy(request):
    return render(request, "web/home/Cancellation_Refund_Policy.html")




def terms_and_conditions(request):
    return render(request, "web/home/terms_and_conditions.html")


def exam(request):
    return render(request, "web/home/exam.html")


def maintenance(request):
    return render(request, "web/maintenance.html")


def main(request):
    return render(request, "web/home/main.html")


def offline(request):
    return render(request, "web/offline.html")


def career_role(request):
    return render(request, "web/career_role.html")


def centre_contact(request):
    return render(request, "web/centre/centre_contact.html")


# ----------------------------------------------------------------------------------------------- #
# -------------------------------| ADMIN & HEADOFFICE DASHBOARD START |-------------------------- #
# ----------------------------------------------------------------------------------------------- #


class AdminOrHeadOfficeRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.usertype not in ["Administrator", "HeadOffice"]:
            messages.error(request, gettext("You do not have permission to access this page."))
            return redirect("web:not_found")
        return super().dispatch(request, *args, **kwargs)


class AdminListPaginationMixin:
    """Apply consistent, query-string preserving pagination to admin lists."""

    paginate_by = 10

    def paginate_queryset(self, queryset, page_size):
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(self.request.GET.get("page", 1))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["pagination_query"] = query_params.urlencode()
        return context


class AdminDashboardView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/admin_panel/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        total_kerala = CentreUserAccount.objects.count()
        departments = Department.objects.all()
        headoffice = HeadOffice.objects.count()
        total_employees = Employee.objects.count()
        total_state = State.objects.count()
        total_service = StateService.objects.count()

        context.update(
            {
                "total_kerala": total_kerala,
                "departments": departments,
                "headoffice": headoffice,
                "total_employees": total_employees,
                "total_state": total_state,
                "total_service": total_service,
                "open_enquiry_count": FranchiseEnquiry.objects.filter(
                    status=FranchiseEnquiry.Status.OPEN
                ).count(),
            }
        )

        user_details = []

        # Limiting the contacts to only 6
        contacts = Contact.objects.all()[:6]
        context["contacts"] = contacts

        request = self.request
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")

        context["ip"] = ip

        return context


# Admin - Headoffice


class AddHeadOfficeView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = HeadOffice
    form_class = HeadOfficeForm
    template_name = "web/admin_panel/headoffice/add_headoffice.html"
    success_url = reverse_lazy("web:headoffice_list")

    def form_valid(self, form):
        # Generate username as HO followed by 8 random numbers
        username = f"HO{random.randint(10000000, 99999999)}"

        # Set the password as the phone number
        password = form.cleaned_data["phone_number"]

        # Create the user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=form.cleaned_data["email"],
            usertype="HeadOffice",
        )

        # Assign the newly created user to the HeadOffice object
        form.instance.user = user

        # Save the HeadOffice object
        self.object = form.save()

        # Prepare the email content
        subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
        html_content = (
            f"<p>Thank you for registering. Your account has been created successfully.</p>"
            f"<p><strong>Centre ID:</strong> {self.object.id}</p>"
            f"<p><strong>Username:</strong> {username}</p>"
            f"<p><strong>Password:</strong> {password}</p>"
            f"<p>We recommend you change your password after logging in.</p>"
            f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
            f"<p>Best regards,<br>The SSC Team</p>"
        )

        # Send email using Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        email_data = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": form.cleaned_data["email"]}],
            subject=subject,
            html_content=html_content,
            sender={
                "name": "Samatwa Service Centre",
                "email": "samatwaservicecenter.gov.in@gmail.com",
            },
        )

        try:
            api_response = api_instance.send_transac_email(email_data)
            print("Email sent successfully:", api_response)
        except ApiException as e:
            print("Exception when sending email: %s\n" % e)

        return super().form_valid(form)


class HeadofficeListView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = HeadOffice
    template_name = "web/admin_panel/headoffice/headoffice_list.html"
    context_object_name = "headoffices"

    def get_queryset(self):
        return super().get_queryset().order_by("-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_headoffice = HeadOffice.objects.count()
        context.update(
            {
                "total_headoffice": total_headoffice,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Handle file upload
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            with open("uploaded_file.txt", "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            messages.success(request, "File uploaded successfully!")
        else:
            messages.error(request, "No file uploaded!")

        return response


class EditHeadOfficeView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = HeadOffice
    form_class = HeadOfficeForm
    template_name = "web/admin_panel/headoffice/add_headoffice.html"
    success_url = reverse_lazy("web:headoffice_list")


class DeleteHeadOfficeView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = HeadOffice
    success_url = reverse_lazy("web:headoffice_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class HeadofficeDashboardView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/headoffice/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        total_kerala = CentreUserAccount.objects.count()
        departments = Department.objects.all()
        total_employees = Employee.objects.count()
        total_state = State.objects.count()
        total_service = StateService.objects.count()

        context.update(
            {
                "total_kerala": total_kerala,
                "departments": departments,
                "total_employees": total_employees,
                "total_state": total_state,
                "total_service": total_service,
                "open_enquiry_count": FranchiseEnquiry.objects.filter(
                    status=FranchiseEnquiry.Status.OPEN
                ).count(),
            }
        )

        request = self.request
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")

        context["ip"] = ip  # Add IP address to the context

        return context


# Admin - State dashboard
class AddStateAdminView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = State
    form_class = StateForm
    template_name = "web/admin_panel/state/add_state_admin.html"
    success_url = reverse_lazy("web:admin_state_list")

    def form_valid(self, form):
        try:
            # Save the state object without committing to the database
            state = form.save(commit=False)
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            email = form.cleaned_data.get("email")

            # Check for missing data
            if not username or not password or not email:
                messages.error(
                    self.request, "Username, password, and email are required."
                )
                return self.form_invalid(form)

            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                usertype="state",
                is_active=True,
            )

            # Link the new user to the state object
            state.user = user
            state.save()  # Save the state object with the user linked

            # Optionally, authenticate and log in the user
            user = authenticate(username=username, password=password)
            if user is not None:
                login(self.request, user)

            # Success message using unpkg1
            messages.success(
                self.request,
                "State user added successfully.",
            )

            return super().form_valid(form)

        except IntegrityError:
            # Handle the case where the username already exists
            messages.error(self.request, "Username already exists.")
            return self.form_invalid(form)

        except Exception as e:
            # General exception handling
            messages.error(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)


class AdminStateListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = State
    template_name = "web/admin_panel/state/state_list.html"
    context_object_name = "states"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Handle file upload
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            with open("uploaded_file.txt", "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            messages.success(request, "File uploaded successfully!")
        else:
            messages.error(request, "No file uploaded!")

        return response


class EditStateView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = State
    form_class = StateForm
    template_name = "web/admin_panel/state/add_state_admin.html"
    success_url = reverse_lazy("web:admin_state_list")


class DeleteStateView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = State
    success_url = reverse_lazy("web:admin_state_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


# Admin - centre


def generate_unique_username():
    while True:
        username = "".join([str(random.randint(0, 9)) for _ in range(12)])
        if not User.objects.filter(username=username).exists():
            return username


# A decorator to check if the user is either an Administrator or HeadOffice
def admin_or_headoffice_required(user):
    return user.usertype in ["Administrator", "HeadOffice"]

@method_decorator(user_passes_test(admin_or_headoffice_required), name="dispatch")
class AddCentreUserAdminView(CreateView):
    model = CentreUserAccount
    form_class = CentreUserForm
    template_name = "web/admin_panel/franchise/add_centre_admin.html"
    success_url = reverse_lazy("web:franchise_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        print("Form is valid")  # Debugging statement
        self.object = form.save(commit=False)

        # Generate unique username and set user credentials
        username = generate_unique_username()
        password = str(form.cleaned_data["mobile"])
        email = form.cleaned_data["email"]

        # Create the related user
        user = User.objects.create_user(
            username=username, password=password, email=email
        )
        user.usertype = "centre"
        user.is_active = form.cleaned_data.get("is_active", True)
        user.save()

        # Assign the user to the CentreUserAccount instance
        self.object.user = user
        self.object.username = username
        self.object.is_active = form.cleaned_data.get("is_active", True)
        self.object.manual_disabled = not self.object.is_active
        self.object.created_at = timezone.now()
        self.object.created_by = self.request.user
        self.object.save()

        # Prepare and log email content
        subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
        html_content = (
            f"<p>Thank you for registering. Your account has been created successfully.</p>"
            f"<p><strong>Centre ID:</strong> {self.object.formatted_id}</p>"
            f"<p><strong>Username:</strong> {username}</p>"
            f"<p><strong>Password:</strong> {password}</p>"
            f"<p>We recommend you change your password after logging in.</p>"
            f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
            f"<p>Best regards,<br>The SSC Team</p>"
        )

        print("Email content:", html_content)

        # Send the email via Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        email_data = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email}],
            subject=subject,
            html_content=html_content,
            sender={
                "name": "Samatwa Service Centre",
                "email": "samatwaservicecenter.gov.in@gmail.com",
            },
        )

        try:
            api_response = api_instance.send_transac_email(email_data)
            print("Email sent successfully:", api_response)
        except ApiException as e:
            print("Exception when sending email: %s\n" % e)

        return super().form_valid(form)

    def form_invalid(self, form):
        print("Form is invalid")  # Debugging statement
        print(form.errors)  # Print form errors to the console
        return super().form_invalid(form)



class EditCentreUserView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = CentreUserAccount
    form_class = CentreUserForm
    template_name = "web/admin_panel/franchise/add_centre_admin.html"
    success_url = reverse_lazy("web:franchise_list")

    def form_valid(self, form):
        try:
            user = self.object.user
            user.email = form.cleaned_data["email"]

            password = form.cleaned_data.get("password")
            if password:
                user.set_password(password)

            requested_active = form.cleaned_data.get("is_active", True)
            was_manual_disabled = self.object.manual_disabled
            user.is_active = requested_active
            if was_manual_disabled and not requested_active:
                # Manual restrictions keep the authentication account active so
                # the user can reach the restricted/reactivation workflow.
                user.is_active = True
            user.save()
            form.instance.user = user
            form.instance.is_active = requested_active
            if "is_active" in form.changed_data:
                form.instance.manual_disabled = not form.instance.is_active
            if (
                "is_active" in form.changed_data
                and form.instance.is_active
                and form.instance.inactive_due_to_inactivity
            ):
                now = timezone.now()
                form.instance.inactive_due_to_inactivity = False
                form.instance.inactivity_reason = ""
                form.instance.reactivated_at = now
                form.instance.last_successful_login = now
                form.instance.last_login = now
                CentreReactivationAuditLog.objects.create(
                    centre=form.instance,
                    actor=self.request.user,
                    event=CentreReactivationAuditLog.Event.REACTIVATED,
                    details={"source": "head_office_manual_reactivation"},
                )
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Error: {e}")
            return self.form_invalid(form)


class AdminCentreUserListView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = CentreUserAccount
    template_name = "web/admin_panel/franchise/franchise_list.html"
    context_object_name = "centreusers"

    def get_queryset(self):
        return CentreUserAccount.objects.order_by("-pk")


class AdminCenterUserDetailView(AdminOrHeadOfficeRequiredMixin, DetailView):
    model = CentreUserAccount
    template_name = "web/admin_panel/franchise/centre_profile.html"
    context_object_name = "centreusers"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        created_by = self.object.created_by
        context["created_by_username"] = (
            created_by.username if created_by else "Unknown"
        )
        settings_obj = CentreReactivationSettings.get_solo()
        context["reactivation_amount"] = calculate_reactivation_amount(
            self.object, settings_obj
        )
        context["reactivation_payments"] = self.object.reactivation_payments.all()
        context["reactivation_audit_logs"] = self.object.reactivation_audit_logs.select_related(
            "actor"
        ).all()
        return context


class AdminCentreUserDeleteView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = CentreUserAccount
    success_url = reverse_lazy("web:franchise_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class CentreWalletTransListView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/admin_panel/franchise/wallet_transactions.html"


class CentreNonActiveListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = CentreUserAccount
    template_name = "web/admin_panel/franchise/non_active_centre.html"
    context_object_name = "non_active_centres"

    def get_queryset(self):
        # Include both legacy/manual disables and inactivity-restricted centres.
        return CentreUserAccount.objects.filter(
            Q(user__is_active=False) | Q(inactive_due_to_inactivity=True)
        ).distinct()


class AddSoftwareView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = Software
    fields = ["title", "logo", "site_link"]
    template_name = "web/admin_panel/franchise/add_software.html"
    success_url = reverse_lazy("web:software_list")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class CentreSoftwareListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = Software
    template_name = "web/admin_panel/franchise/software_list.html"
    context_object_name = "softwares"


class EditSoftwareView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = Software
    fields = ["title", "logo", "site_link"]
    template_name = "web/admin_panel/franchise/add_software.html"
    success_url = reverse_lazy("web:software_list")


# Admin - Employee Department
class DepartmentListView(AdminOrHeadOfficeRequiredMixin, View):
    model = Department
    template_name = "web/admin_panel/employee/department.html"

    def get(self, request):
        form = DepartmentForm()
        departments = self.model.objects.all()
        return render(
            request, self.template_name, {"departments": departments, "form": form}
        )

    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("web:department_list")
        departments = self.model.objects.all()
        return render(
            request, self.template_name, {"departments": departments, "form": form}
        )


# Admin - Employee
class AddEmployeeView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = "web/admin_panel/employee/add_employee.html"
    success_url = reverse_lazy("web:employee_list")

    def form_valid(self, form):
        employee = form.save(commit=False)
        password = form.cleaned_data.get("password")
        user = User.objects.create_user(
            username=employee.email,
            email=employee.email,
            password=password,
            is_staff=True,
            usertype="Employee",
        )
        employee.user = user
        employee.save()
        messages.success(
            self.request, f"Employee '{employee.name}' added successfully."
        )
        return super().form_valid(form)


class AddOnlineClassView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = OnlineClass
    form_class = OnlineClassForm
    template_name = "web/admin_panel/franchise_dashboard/add_online_class.html"
    success_url = reverse_lazy("web:onlineclass_list")


class OnlineClassListView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = OnlineClass
    template_name = "web/admin_panel/franchise_dashboard/onlineclass_list.html"
    context_object_name = "onlineclass"

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-created_at", "-pk")
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for online_class in context["onlineclass"]:
            thumbnail = online_class.thumbnail
            online_class.admin_thumbnail_url = ""
            if thumbnail and thumbnail.name and thumbnail.storage.exists(thumbnail.name):
                online_class.admin_thumbnail_url = thumbnail.url
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context


class EmployeeDetailView(AdminOrHeadOfficeRequiredMixin, DetailView):
    model = Employee
    template_name = "web/admin_panel/employee/admin_employee_profile.html"
    context_object_name = "employees"


class EmployeeListView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = Employee
    template_name = "web/admin_panel/employee/employee_list.html"
    context_object_name = "employees"

    def get_queryset(self):
        return super().get_queryset().order_by("-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_employees"] = self.model.objects.count()
        return context


class EditEmployeeView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = "web/admin_panel/employee/add_employee.html"
    success_url = reverse_lazy("web:employee_list")


class DeleteEmployeeView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = Employee
    success_url = reverse_lazy("web:employee_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


# Admin - Online Class
class EditOnlineClassView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = OnlineClass
    form_class = OnlineClassForm
    template_name = "web/admin_panel/franchise_dashboard/add_online_class.html"
    success_url = reverse_lazy("web:onlineclass_list")


class DeleteOnlineClassView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = OnlineClass
    success_url = reverse_lazy("web:onlineclass_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


# admin contact details
class ContactListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = Contact
    template_name = "web/admin_panel/home/contact_list.html"
    context_object_name = "contacts"


class DeleteContactView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = Contact
    success_url = reverse_lazy("web:contact_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


# Admin  media
class MediaAdminListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = Media
    template_name = "web/admin_panel/home/media_list.html"
    context_object_name = "media"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titles"] = Media.objects.values_list("title", flat=True).distinct()
        selected_title = self.request.GET.get("title", "")
        if selected_title:
            context["media"] = Media.objects.filter(title=selected_title)
        else:
            context["media"] = Media.objects.all()
        return context


class MediaAdminCreateView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = Media
    template_name = "web/admin_panel/home/add_media.html"
    fields = ["image", "sub_title", "title", "content", "place"]
    success_url = reverse_lazy("web:media_list")


class EditMediaView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = Media
    fields = ["image", "sub_title", "title", "content", "place"]
    template_name = "web/admin_panel/home/add_media.html"
    success_url = reverse_lazy("web:media_list")


class DeleteMediaView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = Media
    success_url = reverse_lazy("web:media_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


# Exam Registration
# class ExamRegisterListView(AdminOrHeadOfficeRequiredMixin, ListView):
#     model = UserRegistration
#     template_name = "web/admin_panel/franchise_dashboard/exam_register_list.html"
#     context_object_name = "examregister"

#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)
#         # Handle file upload
#         uploaded_file = request.FILES.get("file")
#         if uploaded_file:
#             with open("uploaded_file.txt", "wb+") as destination:
#                 for chunk in uploaded_file.chunks():
#                     destination.write(chunk)
#             messages.success(request, "File uploaded successfully!")
#         else:
#             messages.error(request, "No file uploaded!")

#         return response


class ErrorView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/admin_panel/error.html"


class FaqView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/centre/faq.html"


class AddDownloadFormView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = DownloadForm
    form_class = DownloadFormForm
    template_name = "web/admin_panel/franchise_dashboard/add_downloadform.html"
    success_url = reverse_lazy("web:downloadform_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["states"] = AddState.objects.order_by("state_name")
        context["services"] = StateService.objects.select_related("state").order_by(
            "service_name"
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Download form saved successfully.")
        return response


class DownloadFormAdminListView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = DownloadForm
    template_name = "web/admin_panel/franchise_dashboard/downloadform_list.html"
    context_object_name = "download_forms"

    def get_queryset(self):
        return super().get_queryset().order_by("-created_at", "-pk")


class EditDownloadFormView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = DownloadForm
    form_class = DownloadFormForm
    template_name = "web/admin_panel/franchise_dashboard/add_downloadform.html"
    success_url = reverse_lazy("web:downloadform_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["states"] = AddState.objects.order_by("state_name")
        context["services"] = StateService.objects.select_related("state").order_by(
            "service_name"
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Download form updated successfully.")
        return response


class DeleteDownloadFormView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = DownloadForm
    success_url = reverse_lazy("web:downloadform_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class CareerAddAdminView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = Career
    template_name = "web/admin_panel/home/add_career.html"
    fields = ["name_of_host", "experience", "qualification", "salary"]
    success_url = reverse_lazy("web:career_list")


class CareerAdminListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = Career
    template_name = "web/admin_panel/home/career_list.html"
    context_object_name = "career"


class DeleteCareerView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = Career
    success_url = reverse_lazy("web:career_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class CareerCreateView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = CareerForm
    fields = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "job_title",
        "experience_years",
        "qualification",
        "age",
        "current_role",
        "resume",
        "experience_level",
        "work_preference",
        "comments",
    ]
    template_name = "web/home/career_form.html"
    success_url = reverse_lazy("web:career_form")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"message": "Career form submitted successfully!"})
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["careers"] = Career.objects.all()
        return context


class CareerApplicationsList(AdminOrHeadOfficeRequiredMixin, ListView):
    model = CareerForm
    template_name = "web/admin_panel/home/career_applications.html"
    context_object_name = "applications"


class DeleteCareerApplicationsView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = CareerForm
    success_url = reverse_lazy("web:career_applications")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            self.object.delete()
            return JsonResponse({"success": True})
        else:
            self.object.delete()
            return redirect(self.success_url)


class AdminKeralaSubCentreView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/admin_panel/franchise/admin_kerala_subcentre.html"


class AddStateCreateView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = AddState
    fields = ["state_name", "logo"]
    template_name = "web/admin_panel/services/addstate_form.html"
    success_url = reverse_lazy("web:all_sections")


class AddStateListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = AddState
    template_name = "web/admin_panel/services/addstate_list.html"
    context_object_name = "states"


class AddStateUpdateView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = AddState
    fields = ["state_name", "logo"]
    template_name = "web/admin_panel/services/addstate_form.html"
    success_url = reverse_lazy("web:addstate_list")


class AddStateDeleteView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = AddState
    success_url = reverse_lazy("web:addstate_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class StateServiceListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = StateService
    template_name = "web/admin_panel/services/stateservice_list.html"
    context_object_name = "services"

class StateServiceDetailImageUploadMixin:
    def validate_detail_uploads(self, form):
        self.detail_uploads = self.request.FILES.getlist("detail_images")
        for uploaded_file in self.detail_uploads:
            try:
                validate_detail_image(uploaded_file)
            except ValidationError as error:
                form.add_error(None, error)
        return not form.errors

    def save_detail_uploads(self):
        for uploaded_file in self.detail_uploads:
            StateServiceDetailImage.objects.create(
                service=self.object,
                image=uploaded_file,
            )


class StateServiceCreateView(
    StateServiceDetailImageUploadMixin, AdminOrHeadOfficeRequiredMixin, CreateView
):
    model = StateService
    form_class = StateServiceForm
    template_name = "web/admin_panel/services/stateservice_form.html"

    def form_valid(self, form):
        if not self.validate_detail_uploads(form):
            return self.form_invalid(form)
        state = get_object_or_404(AddState, slug=self.kwargs["state_slug"])
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.state = state
            self.object.save()
            self.save_detail_uploads()
        messages.success(self.request, "Service saved successfully.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(
            "web:stateservice_by_state",
            kwargs={"state_slug": self.kwargs["state_slug"]},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["state"] = AddState.objects.get(slug=self.kwargs["state_slug"])
        return context


class StateServiceUpdateView(
    StateServiceDetailImageUploadMixin, AdminOrHeadOfficeRequiredMixin, UpdateView
):
    model = StateService
    form_class = StateServiceForm
    template_name = "web/admin_panel/services/stateservice_form.html"

    def form_valid(self, form):
        if not self.validate_detail_uploads(form):
            return self.form_invalid(form)
        with transaction.atomic():
            self.object = form.save()
            self.save_detail_uploads()
        messages.success(self.request, "Service updated successfully.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        print(form.errors)  # Print form errors for debugging
        return super().form_invalid(form)

    def get_success_url(self):
        state_slug = self.object.state.slug
        return reverse_lazy(
            "web:stateservice_by_state", kwargs={"state_slug": state_slug}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detail_images"] = self.object.detail_images.all()
        context["state"] = self.object.state
        return context


class StateServiceDetailImageDeleteView(AdminOrHeadOfficeRequiredMixin, View):
    def post(self, request, pk):
        detail_image = get_object_or_404(StateServiceDetailImage, pk=pk)
        service_pk = detail_image.service_id
        if detail_image.image:
            detail_image.image.delete(save=False)
        detail_image.delete()
        return redirect("web:stateservice_update", pk=service_pk)


from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView
from django.shortcuts import redirect
from .models import StateService

class StateServiceDeleteView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = StateService

    def get_success_url(self):
        # Assuming your StateService model has a ForeignKey to AddState model named 'state'
        state_slug = self.object.state.slug
        return reverse_lazy("web:stateservice_by_state", kwargs={"state_slug": state_slug})

    def post(self, request, *args, **kwargs):
        # Get the object to delete
        self.object = self.get_object()
        self.object.delete()

        # Redirect to the success URL after deletion
        return redirect(self.get_success_url())



class AllSectionView(AdminOrHeadOfficeRequiredMixin, TemplateView):
    template_name = "web/admin_panel/services/all_section.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["states"] = AddState.objects.all()
        return context


class StateServiceByStateView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = StateService
    template_name = "web/admin_panel/services/state_services_by_state.html"
    context_object_name = "services"

    def get_queryset(self):
        state_slug = self.kwargs["state_slug"]
        return StateService.objects.filter(state__slug=state_slug).order_by(
            "-created_at", "-pk"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["state"] = AddState.objects.get(slug=self.kwargs["state_slug"])
        return context


class LatestNewsCentreAddView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = LatestNewsCentre
    template_name = "web/admin_panel/franchise/add_news_centre.html"
    fields = ["image", "title", "content"]
    success_url = reverse_lazy("web:latest_news_list")


class LatestNewsCentreListView(AdminOrHeadOfficeRequiredMixin, ListView):
    model = LatestNewsCentre
    template_name = "web/admin_panel/franchise/news_centre_list.html"
    context_object_name = "latest_news"


class EditLatestNewsCentreView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = LatestNewsCentre
    fields = ["image", "title", "content"]  # Use fields instead of form_class list
    template_name = "web/admin_panel/franchise/add_news_centre.html"
    success_url = reverse_lazy("web:latest_news_list")


class DeleteLatestNewsCentreView(AdminOrHeadOfficeRequiredMixin, DeleteView):
    model = LatestNewsCentre
    success_url = reverse_lazy("web:latest_news_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


class BannerListView(AdminListPaginationMixin, AdminOrHeadOfficeRequiredMixin, ListView):
    model = Banner
    template_name = "web/admin_panel/banners/list.html"
    context_object_name = "banners"

    def get_queryset(self):
        return super().get_queryset().order_by("display_order", "-created_at", "-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_banners"] = Banner.objects.count()
        context["active_banners"] = Banner.objects.filter(is_enabled=True).count()
        context["disabled_banners"] = Banner.objects.filter(is_enabled=False).count()
        return context


class BannerCreateView(AdminOrHeadOfficeRequiredMixin, CreateView):
    model = Banner
    form_class = BannerForm
    template_name = "web/admin_panel/banners/form.html"
    success_url = reverse_lazy("web:banner_list")


class BannerUpdateView(AdminOrHeadOfficeRequiredMixin, UpdateView):
    model = Banner
    form_class = BannerForm
    template_name = "web/admin_panel/banners/form.html"
    success_url = reverse_lazy("web:banner_list")


class BannerActionView(AdminOrHeadOfficeRequiredMixin, View):
    def post(self, request, action, pk):
        banner = get_object_or_404(Banner, pk=pk)
        if action == "delete":
            banner.delete()
        elif action == "enable":
            banner.is_enabled = True
            banner.save(update_fields=["is_enabled", "updated_at"])
        elif action == "disable":
            banner.is_enabled = False
            banner.save(update_fields=["is_enabled", "updated_at"])
        else:
            return HttpResponseBadRequest("Unknown banner action")
        return redirect("web:banner_list")


@login_required
def service_list(request):
    form = ServiceFilterForm(request.GET or None)
    services = StateService.objects.all()

    if form.is_valid():
        show_popular = form.cleaned_data.get("show_popular")
        if show_popular:
            services = services.filter(is_popular=True)

    return render(
        request,
        "web/admin_panel/services/popular_service.html",
        {"form": form, "services": services},
    )


# ----------------------------------------X---------------------X-------------------------------- #
# ---------------------------------| ADMIN & HEADOFFICE DASHBOARD END |-------------------------- #
# ----------------------------------------X---------------------X---------------------------------#


# ----------------------------------------------------------------------------------------------- #
# ------------------------------------| KERALA CENTRE DASHBOARD START |-------------------------- #
# ----------------------------------------------------------------------------------------------- #


class FranchiseAuthenticatedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.usertype != "centre":
            messages.error(request, gettext("You do not have permission to access this page."))
            return redirect("web:not_found")
        return super().dispatch(request, *args, **kwargs)


class FranchiseAccessMixin(FranchiseAuthenticatedMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.usertype != "centre":
            return super().dispatch(request, *args, **kwargs)
        try:
            centre = request.user.centre
        except CentreUserAccount.DoesNotExist:
            # Preserve the existing behaviour for legacy centre logins that
            # have no linked profile; inactivity enforcement only applies to
            # real CentreUserAccount records.
            return super().dispatch(request, *args, **kwargs)
        if centre.inactive_due_to_inactivity or centre.manual_disabled:
            return redirect("web:centre_reactivation")
        if not centre.is_active:
            messages.error(
                request,
                gettext("Your centre account is disabled. Please contact Head Office."),
            )
            return redirect("web:not_found")
        return super().dispatch(request, *args, **kwargs)


class KeralaRequiredMixin(FranchiseAccessMixin):
    pass


class DistrictDashboardView(KeralaRequiredMixin, TemplateView):
    template_name = "web/franchise/centre_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        from .enquiry_utils import get_support_whatsapp_url

        context["support_whatsapp_url"] = get_support_whatsapp_url(user)

        try:
            # Try to get the related centre
            district_detail = user.centre  # Assuming user has a related 'centre'
        except ObjectDoesNotExist:
            raise Http404("User has no associated centre.")

        latest_news_queryset = LatestNewsCentre.objects.order_by("-created_at")
        latest_news_count = latest_news_queryset.count()
        latest_news = latest_news_queryset[:3]
        popular_services = StateService.objects.filter(
            is_popular=True, is_active=True
        ).select_related("state").order_by("-updated_at", "-created_at", "pk")
        state_value = (district_detail.state or "").strip()
        franchise_state = None
        if state_value:
            franchise_state = AddState.objects.filter(
                Q(slug__iexact=state_value) | Q(state_name__iexact=state_value)
            ).first()

        priority_services = list(popular_services.none())
        other_services = list(popular_services)
        if franchise_state:
            priority_services = list(popular_services.filter(state_id=franchise_state.pk))
            other_services = list(popular_services.exclude(state_id=franchise_state.pk))

        ordered_services = priority_services + other_services
        dashboard_services = ordered_services[:8]
        popular_programs = ordered_services[:2]
        if franchise_state:
            service_page_url = reverse(
                "web:state_detail", kwargs={"slug": franchise_state.slug}
            )
        else:
            service_page_url = reverse("web:state_list")

        banners = Banner.objects.filter(is_enabled=True)
        total_service = StateService.objects.count()
        ac_master = Table_Accountsmaster.objects.filter(user=self.request.user).first()
        wallet_total = ac_master.currentbalance if ac_master else None
        wallet_transaction_count = (
            Table_Voucher.objects.filter(user=user).count()
            + Table_DrCrNote.objects.filter(user=user).count()
            + Table_Journal_Entry.objects.filter(auth_user=user).count()
            + Table_Contra_Entry.objects.filter(auth_user=user).count()
        )
        centre_display_name = (
            district_detail.centre_name
            or district_detail.owner_centre
            or user.get_username()
        )
        agency_identifier = district_detail.username or user.get_username()
        context.update(
            {
                "latest_news": latest_news,
                "latest_news_count": latest_news_count,
                "district_detail": district_detail,
                "popular_services": popular_services,
                "priority_services": priority_services,
                "other_services": other_services,
                "dashboard_services": dashboard_services,
                "popular_programs": popular_programs,
                "franchise_state": franchise_state,
                "service_page_url": service_page_url,
                "centre_display_name": centre_display_name,
                "agency_identifier": agency_identifier,
                "last_login": user.last_login if user.centre else None,
                "total_service": total_service,
                "wallet_total": wallet_total,
                "wallet_transaction_count": wallet_transaction_count,
                "banners": banners,
            }
        )

        request = self.request
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        context["ip"] = ip

        return context


class CenterWalletHistoryView(KeralaRequiredMixin, TemplateView):
    def get(self, request):
        user = request.user

        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()

        # Fetch all user accounts
        accounts = Table_Accountsmaster.objects.filter(user=user).order_by('group', 'head')

        # Fetch all entries
        voucher_entries = Table_Voucher.objects.filter(user=user)
        drcr_entries = Table_DrCrNote.objects.filter(user=user)
        journal_entries = Table_Journal_Entry.objects.filter(auth_user=user)
        contra_entries = Table_Contra_Entry.objects.filter(auth_user=user)

        # Combine entries into one list and sort by date
        combined_entries = (
            list(voucher_entries) + 
            list(drcr_entries) + 
            list(journal_entries) + 
            list(contra_entries)
        )

        def get_entry_date(entry):
            return getattr(entry, 'Vdate', getattr(entry, 'ndate', getattr(entry, 'vdate', datetime.min.date())))

        combined_entries.sort(key=get_entry_date)

        entry_list = []
        group_totals = {}
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        # Process account-level summaries
        for account in accounts:
            current_balance = Decimal(account.currentbalance or "0.00")
            acc_debit = Decimal("0.00")
            acc_credit = Decimal("0.00")

            for entry in combined_entries:
                code = account.account_code
                if hasattr(entry, "Accountcode") and entry.Accountcode == code:
                    amount = Decimal(entry.VAmount or "0.00")
                    if entry.CStatus == "P":
                        acc_debit += amount
                    elif entry.CStatus == "R":
                        acc_credit += amount
                elif hasattr(entry, "accountcode") and entry.accountcode == code:
                    acc_debit += Decimal(entry.dramount or "0.00")
                    acc_credit += Decimal(entry.cramount or "0.00")

            # Track per-group totals
            group = account.group
            group_totals.setdefault(group, {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
            if current_balance > 0:
                group_totals[group]["debit"] += current_balance
            elif current_balance < 0:
                group_totals[group]["credit"] += abs(current_balance)

            # Append to entry list
            # entry_list.append({
            #     "group": group,
            #     # "head": account.head,
            #     "current_balance": current_balance,
            #     "debit": acc_debit,
            #     "credit": acc_credit
            # })

            total_debit += acc_debit
            total_credit += acc_credit

        # Append group totals into entries
        for entry in entry_list:
            group = entry["group"]
            if group in group_totals:
                entry["debit"] += group_totals[group]["debit"]
                entry["credit"] += group_totals[group]["credit"]

        # Now process transaction-level entries
        for entry in combined_entries:
            entry_dict = {}
            if hasattr(entry, "Vdate"):  # Table_Voucher
                date = entry.Vdate
                amount = Decimal(entry.VAmount or "0.00")
                cstatus = entry.CStatus
                debit = amount if cstatus == "P" else Decimal("0.00")
                credit = amount if cstatus == "R" else Decimal("0.00")
                head = Table_Accountsmaster.objects.filter(account_code=entry.Accountcode, user=user).first()
                head_name = head.head if head else "Unknown"
                entry_dict = {
                    "date": date,
                    "head": head_name,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "debit": debit,
                    "credit": credit,
                    "type": cstatus,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

                # Add Book Head entry
                if entry.Headcode:
                    try:
                        head_acc = Table_Accountsmaster.objects.get(account_code=entry.Headcode, user=user)
                        head_entry = {
                            "date": date,
                            "head": head_acc.head,
                            "voucher_number": entry.VoucherNo or entry.Series,
                            "narration": "",
                            "debit": credit if cstatus == "R" else Decimal("0.00"),
                            "credit": debit if cstatus == "P" else Decimal("0.00"),
                            "type": cstatus,
                            "is_journal_entry": False,
                            "is_contra_entry": False,
                        }
                        total_debit += head_entry["debit"]
                        total_credit += head_entry["credit"]
                        entry_list.append(head_entry)
                    except Table_Accountsmaster.DoesNotExist:
                        pass

            elif hasattr(entry, "ndate"):  # Table_DrCrNote
                amount_debit = Decimal(entry.dramount or "0.00")
                amount_credit = Decimal(entry.cramount or "0.00")
                if entry.ntype == "C":  # Credit Note
                    amount_debit, amount_credit = amount_credit, amount_debit
                acc = Table_Accountsmaster.objects.filter(account_code=entry.accountcode, user=user).first()
                entry_dict = {
                    "date": entry.ndate,
                    "head": acc.head if acc else "Unknown",
                    "voucher_number": entry.noteno or entry.series,
                    "narration": entry.narration,
                    "debit": amount_debit,
                    "credit": amount_credit,
                    "type": entry.ntype,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Journal_Entry):
                amount_debit = Decimal(entry.dramount or "0.00")
                amount_credit = Decimal(entry.cramount or "0.00")
                acc = Table_Accountsmaster.objects.filter(account_code=entry.accountcode, user=user).first()
                entry_dict = {
                    "date": entry.vdate,
                    "head": acc.head if acc else "Unknown",
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": amount_debit,
                    "credit": amount_credit,
                    "type": "Journal",
                    "is_journal_entry": True,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Contra_Entry):
                amount_debit = Decimal(entry.dramount or "0.00")
                amount_credit = Decimal(entry.cramount or "0.00")
                acc = Table_Accountsmaster.objects.filter(account_code=entry.accountcode, user=user).first()
                entry_dict = {
                    "date": entry.vdate,
                    "head": acc.head if acc else "Unknown",
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": amount_debit,
                    "credit": amount_credit,
                    "type": "Contra",
                    "is_journal_entry": False,
                    "is_contra_entry": True,
                }

            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))
            entry_list.append(entry_dict)

        context = {
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "total_group_debit": sum(e["debit"] for e in entry_list if "debit" in e),
            "total_group_credit": sum(e["credit"] for e in entry_list if "credit" in e),
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
        }

        return render(request, "web/franchise/wallet/history.html", context)

class CenterAddWalletView(KeralaRequiredMixin, TemplateView):
    template_name = "web/franchise/wallet/add_wallet.html"


class DownloadFormListView(KeralaRequiredMixin, ListView):
    model = DownloadForm
    template_name = "web/franchise/download_form_list.html"
    context_object_name = "download_forms"

    def get_queryset(self):
        queryset = DownloadForm.objects.select_related("state", "service")
        state_id = self.request.GET.get("state")
        service_id = self.request.GET.get("service")
        if state_id and state_id.isdigit():
            queryset = queryset.filter(state_id=state_id)
        if service_id and service_id.isdigit():
            queryset = queryset.filter(service_id=service_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_state = self.request.GET.get("state", "")
        selected_service = self.request.GET.get("service", "")
        context["states"] = AddState.objects.order_by("state_name")
        services = StateService.objects.select_related("state").order_by(
            "service_name"
        )
        if selected_state.isdigit():
            services = services.filter(state_id=selected_state)
        context["services"] = services
        context["selected_state"] = selected_state
        context["selected_service"] = selected_service
        context["has_filters"] = bool(selected_state or selected_service)
        return context

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        uploaded_file = request.FILES.get("pdf")
        if uploaded_file:
            DownloadForm.objects.create(title="Uploaded File", pdf=uploaded_file)
            messages.success(request, "File uploaded successfully!")
        else:
            messages.error(request, "No file uploaded!")

        return response


class DownloadFileView(View):
    def get(self, request, *args, **kwargs):
        try:
            download_form = DownloadForm.objects.get(pk=kwargs["pk"])
            file_path = download_form.pdf.path
            return FileResponse(open(file_path, "rb"), as_attachment=True)
        except DownloadForm.DoesNotExist:
            pass


class SoftwareView(KeralaRequiredMixin, TemplateView):
    template_name = "web/franchise/tool.html"


class OnlineClassView(KeralaRequiredMixin, TemplateView):
    template_name = "web/franchise/online_class.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Retrieve necessary data
        onlineclass = OnlineClass.objects.all().order_by("-created_at", "-pk")

        context = {
            "onlineclass": onlineclass,
        }
        return context


class OnlineClassDetailView(KeralaRequiredMixin, DetailView):
    model = OnlineClass
    template_name = "web/franchise/online_class_detail.html"
    context_object_name = "online_class"
    slug_field = "slug"
    slug_url_kwarg = "slug"


class SoftwaresView(KeralaRequiredMixin, ListView):
    model = Software
    template_name = "web/franchise/softwares.html"
    context_object_name = "softwares"


class AddKeralaSubCentreView(KeralaRequiredMixin, CreateView):
    model = KeralaSubCentre
    form_class = KeralaSubCentreForm
    template_name = "web/franchise/add_subcentre.html"
    success_url = reverse_lazy("web:kerala_subcentre")

    def form_valid(self, form):
        try:
            state = form.save(commit=False)
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            name = form.cleaned_data.get("name")
            user = User.objects.create_user(
                username=username,
                email=username,
                password=password,
                usertype="subcentre",
                is_active=True,
            )
            state.user = user
            state.name = name
            state.save()
            messages.success(
                self.request,
                f"State added successfully. Username: {username}, Password: {password}",
            )
            user = authenticate(username=username, password=password)
            if user is not None:
                login(self.request, user)
            return super().form_valid(form)
        except IntegrityError:
            messages.error(self.request, "Username already exists.")
            return HttpResponseRedirect(reverse_lazy("web:error"))


class KeralaSubCentreView(LoginRequiredMixin, TemplateView):
    model = KeralaSubCentre
    template_name = "web/franchise/sub_centre.html"
    context_object_name = "keralasubcentre"

    def post(self, request, *args, **kwargs):

        response = super().post(request, *args, **kwargs)

        # Handle file upload
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            with open("uploaded_file.txt", "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            messages.success(request, "File uploaded successfully!")
        else:
            messages.error(request, "No file uploaded!")

        return response


from django.views.generic import TemplateView
from web.models import Table_Accountsmaster  # Update the import based on your project structure

class CenterWalletView(KeralaRequiredMixin, TemplateView):
    template_name = 'web/franchise/wallet/wallet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        account = Table_Accountsmaster.objects.filter(user=self.request.user).first() 
        context['wallet_total'] = account.currentbalance if account else '0'
        return context


class StateListView(ListView):
    model = AddState
    template_name = "web/franchise/services/state_list.html"
    context_object_name = "states"


class StateDetailView(DetailView):
    model = AddState
    template_name = "web/franchise/services/state_detail.html"
    context_object_name = "state"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["services"] = self.object.services.filter(is_active=True)
        return context


class StateServiceDetailView(KeralaRequiredMixin, DetailView):
    model = StateService
    template_name = "web/franchise/services/service_detail.html"
    context_object_name = "service"

    def get_queryset(self):
        return StateService.objects.filter(
            state__slug=self.kwargs["state_slug"], is_active=True
        ).select_related("state").prefetch_related("detail_images")


import pdfkit
from django.conf import settings
from django.http import HttpResponse
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt

from .constants import PaymentStatus


class DistrictProfileView(KeralaRequiredMixin, TemplateView):
    template_name = "web/franchise/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            centreusers = CentreUserAccount.objects.get(user=user)
            context["centreusers"] = centreusers
        except CentreUserAccount.DoesNotExist:
            context["centreusers"] = None

        # Add Razorpay Key ID to context
        context["razorpay_key_id"] = settings.RAZORPAY_KEY_ID
        return context


@login_required
@csrf_exempt
def centre_certificate_payment(request):
    # Process only POST requests
    if request.method == "POST":
        # Parse JSON data from the request body
        data = json.loads(request.body)
        payment_id = data.get("razorpay_payment_id")
        provider_order_id = data.get("provider_order_id")
        signature_id = data.get("signature_id")

        # Optional: Verify payment with Razorpay or other verification services
        # (Implementation depends on specific verification needs)

        # Retrieve the user registration profile
        profile = CentreUserAccount.objects.get(user=request.user)
        # Mark the certificate as paid
        profile.certificate_paid = True
        profile.save()

        # Record the payment details in the Payment model
        CertificatePayment.objects.create(
            user_registration=profile,
            amount=2.0,  # Amount in INR
            status=PaymentStatus.COMPLETED,
            provider_order_id=provider_order_id,
            payment_id=payment_id,
            signature_id=signature_id,
            is_certificate_payment=True,
        )

        # Return a JSON response indicating success
        return JsonResponse({"success": True})

    # Return a JSON response indicating failure for non-POST requests
    return JsonResponse({"success": False})


class CentreCertificateView(View):
    def get(self, request, *args, **kwargs):
        user_registration = get_object_or_404(CentreUserAccount, user=request.user)

        # Use Django's static file handling to get the image URL
        image_url = request.build_absolute_uri(static("web/images/ssc-certificate.jpg"))

        # Render the HTML template with context data
        html_string = render_to_string(
            "web/franchise/certificate.html",
            {
                "content": user_registration.owner_centre,
                "district": user_registration.district,
                "state": user_registration.state,
                "formatted_id": user_registration.formatted_id,
                "photo": request.build_absolute_uri(
                    user_registration.photo.url
                ),  # Ensure the photo URL is absolute
                "image_url": image_url,
            },
        )

        # Specify the full path to wkhtmltopdf
        path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

        # Define options for pdfkit
        options = {
            "page-width": "900px",
            "page-height": "650px",
            "margin-top": "0px",
            "margin-right": "0px",
            "margin-bottom": "0px",
            "margin-left": "0px",
            "no-outline": None,
            "enable-local-file-access": None,
            "no-stop-slow-scripts": None,
        }

        # Generate PDF from the HTML string with custom options
        pdf = pdfkit.from_string(
            html_string, False, configuration=config, options=options
        )

        # Determine if the user wants to view or download the PDF
        response = HttpResponse(pdf, content_type="application/pdf")
        if "download" in request.GET:
            response["Content-Disposition"] = (
                f'attachment; filename="certificate_{user_registration.id}.pdf"'
            )
            user_registration.certificate_downloaded = True
            user_registration.save()
        else:
            response["Content-Disposition"] = "inline"

        return response


# --------------------------------------X-----------------------------X-------------------------- #
# --------------------------------------| KERALA CENTRE DASHBOARD END |-------------------------- #
# --------------------------------------X-----------------------------X-------------------------- #

# ----------------------------------------------------------------------------------------------- #
# ---------------------------------------| STATE DASHBOARD START |------------------------------- #
# ----------------------------------------------------------------------------------------------- #


class StateRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.usertype != "State":
            messages.error(request, gettext("You do not have permission to access this page."))
            return redirect("web:not_found")
        return super().dispatch(request, *args, **kwargs)


class StateDashboardView(StateRequiredMixin, TemplateView):
    template_name = "web/state/state_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            state = State.objects.get(user=user)
            if state.state.lower() == "kerala":
                kerala_centres = CentreUserAccount.objects.filter(state=state.state)
                context["kerala_centres"] = kerala_centres
                context["user_state"] = state
            else:
                context["kerala_centres"] = None
        except State.DoesNotExist:
            context["kerala_centres"] = None
        return context


class KeralaStateEdistrictServiceView(StateRequiredMixin, TemplateView):
    template_name = "web/state/edistrict.html"


class KeralaStateWalletView(StateRequiredMixin, TemplateView):
    template_name = "web/state/state_wallet.html"


class AllKeralaService(StateRequiredMixin, TemplateView):
    template_name = "web/state/all_service.html"


# ----------------------------------------X---------------------X-------------------------------- #
# ----------------------------------------| STATE DASHBOARD END |-------------------------------- #
# ----------------------------------------X---------------------X---------------------------------#




import json
from django.http import JsonResponse

def csp_report_view(request):
    if request.method == 'POST':
        try:
            # Decode the JSON payload
            report = json.loads(request.body.decode('utf-8'))
            print("CSP Violation Report:", report)  # Log the report
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


def render_button(request):
    return render(request, 'web/js-test.html') 





from django.http import JsonResponse

def csp_violation_report(request):
    # Log or analyze CSP violation reports
    if request.method == "POST":
        print("CSP Violation Report:", request.body.decode())
    return JsonResponse({'status': 'ok'})




from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def csp_report_endpoint(request):
    if request.method == "POST":
        # Handle CSP violation report
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid request method"}, status=400)



# views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def csp_report_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Log the CSP report (or save it to your database)
            print("CSP Violation Report:", data)
            return JsonResponse({"status": "received"}, status=200)
        except json.JSONDecodeError:    
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    return JsonResponse({"error": "GET method not allowed"}, status=405)


from exam.models.user_registration import Complaints

def admin_complaints(request):
    pending_complaints = Complaints.objects.filter(status=False).order_by('-timestamp')
    resolved_complaints = Complaints.objects.filter(status=True).order_by('-timestamp')

    if request.method == 'POST':
        complaint_id = request.POST.get('complaint_id')
        reply = request.POST.get('reply')
        complaint = get_object_or_404(Complaints, id=complaint_id)
        complaint.reply = reply
        complaint.status = True
        complaint.save()
        messages.success(request, 'Reply sent successfully!')
        return redirect('web:admin_complaints')

    context = {
        'pending_complaints': pending_complaints,
        'resolved_complaints': resolved_complaints,
    }
    return render(request, 'web/admin_panel/home/admin_complaints.html', context)


def centre_certificate(request):
    centreusers = get_object_or_404(CentreUserAccount, user=request.user)
    return render(request, 'web/franchise/centre_certificate.html', {'centreusers': centreusers})

def tec_certificate(request):
    user = request.user
    current_user = CentreUserAccount.objects.get(user=user)
    return render(request, 'web/franchise/tec_certificate.html', {'current_user': current_user})



import razorpay
from razorpay import Client

def certificate_payment_order(request):
    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    if request.method == 'POST':
        amount = 100  
        currency = 'INR'
        order_data = {
            'amount': amount,
            'currency': currency,
            'payment_capture': 1,
        }
        
        # Create Razorpay order
        order = razorpay_client.order.create(data=order_data)
        razorpay_order_id = order['id']
        print("order id is: ", razorpay_order_id)
        
        # Send the Razorpay order ID to the frontend
        return JsonResponse({
            'razorpay_order_id': razorpay_order_id,
            'amount': amount
        })
    

import json
from exam.models.user_registration import TemporaryUser
def payment_success(request):
    if request.method == "POST":
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        razorpay_order_id = data.get('razorpay_order_id')

        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Verify the payment
        try:
            payment = razorpay_client.payment.fetch(payment_id)
            if payment['status'] == 'captured':
                user = request.user
                temp_user = TemporaryUser.objects.filter(user=user).first()
                temp_user.certificate_paid = True
                temp_user.save()

                try:
                    centre_user = CentreUserAccount.objects.filter(user=user).first()
                    centre_user.certificate_paid = True
                    centre_user.save()
                except Exception as e:
                    messages.error(request, f"error: {e}")
                return JsonResponse({"success": True, "message": "Payment Successful", "redirect_url": "/franchise-dashboard/profile/"})
            else:
                return JsonResponse({"success": False, "message": "Payment Failed"})
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"success": False, "message": "Signature Verification Failed"})
    return JsonResponse({"success": False, "message": "Invalid request"})


def main_certificate(request):
    user = request.user
    current_user = CentreUserAccount.objects.get(user=user)
    return render(request, 'web/franchise/main_certificate.html', {'current_user': current_user})




class wallet_history(LoginRequiredMixin, View):
    def get(self, request):
        company_details = Table_Companydetailsmaster.objects.first()
        voucher_entries = Table_Voucher.objects.all().order_by("Vdate")
        drcr_entries = Table_DrCrNote.objects.all().order_by("ndate")
        journal_entries = Table_Journal_Entry.objects.all().order_by("vdate")
        contra_entries = Table_Contra_Entry.objects.all().order_by("vdate")

        combined_entries = (
            list(voucher_entries) + list(drcr_entries) +
            list(journal_entries) + list(contra_entries)
        )
        combined_entries.sort(key=lambda x: getattr(x, 'Vdate', getattr(x, 'ndate', getattr(x, 'vdate', date.min))))

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        entry_list = []

        # Your existing processing logic...

        context = {
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "company_details": company_details,
        }

        return render(request, "web/franchise/wallet-history.html", context)






# ----------------------------------------------------------------------------------------------- #
# ---------------------------------------| ACCOUNTING START |------------------------------------ #
# ----------------------------------------------------------------------------------------------- #



# - ACCOUNT MASTER

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.contrib import messages
from .models import Table_Accountsmaster
from .forms import AccountMasterForm
import json

class AccountMasterView(LoginRequiredMixin, CreateView):
    model = Table_Accountsmaster
    form_class = AccountMasterForm
    template_name = 'web/accounts/account-master/acc-master.html'
    success_url = reverse_lazy("web:acc_master")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        
        opbalance = form.cleaned_data.get('opbalance', 0)  # Get the opening balance
        debitcredit = form.cleaned_data.get('debitcredit')  # Get the debit/credit choice
        
        # Set opbalance and currentbalance based on debitcredit selection
        if debitcredit == 'Debit':
            form.instance.opbalance = abs(opbalance)  # Ensure positive
            form.instance.currentbalance = abs(opbalance)  # Ensure positive
        elif debitcredit == 'Credit':
            form.instance.opbalance = -abs(opbalance)  # Ensure negative
            form.instance.currentbalance = -abs(opbalance)  # Ensure negative
        
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Account created successfully!')
            return response
        except IntegrityError:
            form.add_error('head', 'This head already exists for this user. Please choose a different one.')
            return self.form_invalid(form)



from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Table_Accountsmaster  # Adjust the import according to your structure

from django.http import JsonResponse

class AccountmMasterUserView(LoginRequiredMixin, ListView):
    model = Table_Accountsmaster
    template_name = "web/accounts/account-master/acc_master_list.html"
    context_object_name = "userlists"

    def get_queryset(self):
        # Get all records for the logged-in user
        queryset = self.model.objects.filter(user=self.request.user)
        search_query = self.request.GET.get('search')
        
        # Filter queryset if search_query exists
        if search_query:
            queryset = queryset.filter(head__icontains=search_query)
        
        return queryset

    def get(self, request, *args, **kwargs):
        # Check if the request is AJAX by inspecting the HTTP headers
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            queryset = self.get_queryset()
            results = [{
                'account_code': userlist.account_code,
                'head': userlist.head,
                'group': userlist.group,
                'category': userlist.category,
                'mobile': userlist.mobile,
                'slug': userlist.slug,
                'get_absolute_url': userlist.get_absolute_url()
            } for userlist in queryset]
            return JsonResponse({'results': results})  # Return JSON response

        return super().get(request, *args, **kwargs)  # Default behavior for non-AJAX requests



class AccountMasterDetailView(DetailView):
    model = Table_Accountsmaster
    template_name = 'web/accounts/account-master/acc_master_detail.html'  # Ensure this template exists

    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        user = self.request.user
        
        # Fetch the account associated with the current user using get_object_or_404
        return get_object_or_404(Table_Accountsmaster, slug=slug, user=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["userlist"] = self.get_object()
        return context


class EditAccountmMasterUserView(LoginRequiredMixin, UpdateView):
    model = Table_Accountsmaster
    form_class = AccountMasterForm
    template_name = 'web/accounts/account-master/acc-master.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        user = self.request.user
        return get_object_or_404(Table_Accountsmaster, slug=slug, user=user)

    def form_valid(self, form):
        form.instance.user = self.request.user
        
        opbalance = form.cleaned_data.get('opbalance', 0)  # Get the opening balance
        debitcredit = form.cleaned_data.get('debitcredit')  # Get the debit/credit choice
        
        # Set opbalance and currentbalance based on debitcredit selection
        if debitcredit == 'Debit':
            form.instance.opbalance = abs(opbalance)  # Ensure positive
            form.instance.currentbalance = abs(opbalance)  # Ensure positive
        elif debitcredit == 'Credit':
            form.instance.opbalance = -abs(opbalance)  # Ensure negative
            form.instance.currentbalance = -abs(opbalance)  # Ensure negative

        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Account updated successfully!')
            return response
        except IntegrityError:
            form.add_error('head', 'This head already exists for this user. Please choose a different one.')
            return self.form_invalid(form)

    def get_success_url(self):
        if self.object and self.object.slug:
            return reverse_lazy('web:account_master_detail', kwargs={'slug': self.object.slug})
        else:
            return reverse_lazy('web:account_master_list')  # Redirect to a list or other page



class DeleteAccountmMasterUserView(DeleteView):
    model = Table_Accountsmaster
    template_name = 'web/accounts/account-master/acc-master.html'
    success_url = reverse_lazy('web:acc_master')

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        return JsonResponse({'message': 'Deleted successfully'})

    def get(self, request, *args, **kwargs):
        # Ensure that the view only handles DELETE requests
        return JsonResponse({'error': 'GET method not allowed'}, status=405)  
  





# - COMPANY MASTER


from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Table_Companydetailsmaster
from .forms import ComapnyDetailsMasterForm
from django.core.exceptions import ValidationError


class CompanyDetailsMasterView(LoginRequiredMixin, CreateView):
    model = Table_Companydetailsmaster
    form_class = ComapnyDetailsMasterForm
    template_name = "web/accounts/company-master/companydetailsmaster.html"
    success_url = reverse_lazy("web:company_details_master")
    success_message = "Company Details Created Successfully"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, self.success_message, extra_tags="form_submit")
            return response
        except ValidationError as e:
            messages.error(self.request, str(e), extra_tags="form_error")
            return self.form_invalid(form)





class CompanyMasterUserView(LoginRequiredMixin, ListView):
    model = Table_Companydetailsmaster
    template_name = "web/accounts/company-master/companymaster_list.html"
    context_object_name = "companylists"

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(head__icontains=search_query)
        return queryset

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            qs_json = serializers.serialize("json", self.get_queryset())
            return JsonResponse({"results": json.loads(qs_json)}, safe=False)
        else:
            return super(CompanyMasterUserView, self).render_to_response(
                context, **response_kwargs
            )


class CompanyMasterDetailView(LoginRequiredMixin, DetailView):
    model = Table_Companydetailsmaster
    template_name = "web/accounts/company-master/companymaster_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        companylists = get_object_or_404(Table_Companydetailsmaster, slug=slug)
        context["companylist"] = companylists
        return context


class DeletecompanymMasterUserView(LoginRequiredMixin, DeleteView):
    model = Table_Companydetailsmaster
    success_url = reverse_lazy("web:company_details_master")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(
            request, "Account Deleted Successfully", extra_tags="form_delete"
        )
        return HttpResponseRedirect(success_url)


from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView
from django.contrib import messages
from django.db import IntegrityError
from .models import Table_Companydetailsmaster
from .forms import ComapnyDetailsMasterForm

class EditCompanyMasterUserView(LoginRequiredMixin, UpdateView):
    model = Table_Companydetailsmaster
    form_class = ComapnyDetailsMasterForm
    template_name = "web/accounts/company-master/companydetailsmaster.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Account edited successfully!")
            return response
        except IntegrityError:
            form.add_error(
                "company_id", "This Company ID already exists. Please choose a different one."
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            "web:companymaster_detail", kwargs={"slug": self.object.slug}
        )



# - DEBIT NOTES

from django.contrib.auth.mixins import LoginRequiredMixin

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Table_DrCrNote, VoucherConfiguration, Table_Accountsmaster

class AccountDebitNoteView(TemplateView):
    template_name = 'web/accounts/debit-note/debit-note.html'
    success_url = reverse_lazy('web:account_debit_note')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = self.kwargs.get('series')
        serial_no = self.kwargs.get('serial_no')
        
        logger.debug(f'Getting context data for series: {series}, serial_no: {serial_no}')

        context['series_options'] = VoucherConfiguration.objects.filter(category='Debit Note', user=self.request.user).values('series', 'serial_no')
        excluded_categories = ['Bank', 'Cashbook']
        head_options = Table_Accountsmaster.objects.exclude(category__in=excluded_categories).values('head', 'account_code').filter(user=self.request.user)
        context['head_options'] = head_options
        context['drcrnotes'] = Table_DrCrNote.objects.filter(ntype='D', user=self.request.user)
        context['series'] = series
        context['serial_no'] = serial_no
    
        if series and serial_no:
            matched_notes = Table_DrCrNote.objects.filter(series=series, noteno=serial_no, ntype='D', user=self.request.user)
            logger.debug(f'Matched notes: {matched_notes}')

            if matched_notes.exists():
                matched_note_dr = matched_notes.filter(dramount__gt=0).first()
                matched_note_cr = matched_notes.filter(cramount__gt=0).first()
    
                if matched_note_dr:
                    matched_note_dr_head = Table_Accountsmaster.objects.filter(user=self.request.user, account_code=matched_note_dr.accountcode).first()
                    if matched_note_dr_head:
                        matched_note_dr.head = matched_note_dr_head.head
                    matched_note_dr.ndate = matched_note_dr.ndate.strftime('%Y-%m-%d')
                    context['matched_note_dr'] = matched_note_dr
    
                if matched_note_cr:
                    matched_note_cr_head = Table_Accountsmaster.objects.filter(account_code=matched_note_cr.accountcode, user=self.request.user).first()
                    if matched_note_cr_head:
                        matched_note_cr.head = matched_note_cr_head.head
                    context['matched_note_cr'] = matched_note_cr
    
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context['company_name'] = company_details.companyname
            context['address1'] = company_details.address1
            context['address2'] = company_details.address2
            context['phoneno'] = company_details.phoneno
    
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        series = request.POST.get('series')
        serial_no = request.POST.get('serial_no')
        date = request.POST.get('date')
        head1 = request.POST.get('head1')
        narration1 = request.POST.get('narration1')
        debit1_str = request.POST.get('debit1', '0')
        debit1 = float(debit1_str) if debit1_str else 0.0  # Convert to float with default value
        head2 = request.POST.get('head2')
        narration2 = request.POST.get('narration2')
        credit2_str = request.POST.get('credit2', '0')
        credit2 = float(credit2_str) if credit2_str else 0.0  # Convert to float with default value
    
        try:
            if series and serial_no:
                matched_notes = Table_DrCrNote.objects.filter(series=series, noteno=serial_no, user=self.request.user, ntype='D')
                if matched_notes.exists():
                    # Update existing debit and credit notes
                    dr_note = matched_notes.filter(dramount__gt=0).first()
                    cr_note = matched_notes.filter(cramount__gt=0).first()
    
                    # Update the current balance before updating the note
                    if dr_note:
                        self.update_account_balance(dr_note.accountcode, -float(dr_note.dramount))
                    if cr_note:
                        self.update_account_balance(cr_note.accountcode, float(cr_note.cramount))
    
                    # Update the note details
                    if dr_note:
                        dr_note.ndate = date
                        dr_note.accountcode = head1  # Debit account
                        dr_note.narration = narration1
                        dr_note.dramount = debit1
                        dr_note.save()
                        # Update the Account_Master table for debit
                        self.update_account_balance(head1, debit1)
                    if cr_note:
                        cr_note.ndate = date
                        cr_note.accountcode = head2  # Credit account
                        cr_note.narration = narration2
                        cr_note.cramount = credit2
                        cr_note.save()
                        # Update the Account_Master table for credit
                        self.update_account_balance(head2, -credit2)
    
                    messages.success(request, 'Debit note updated successfully.')
                else:
                    # Create new entries if no existing notes are matched
                    self.create_new_entries(request, series, date, head1, narration1, debit1, head2, narration2, credit2)
    
            else:
                # Create new entries if series and serial_no are not provided
                self.create_new_entries(request, series, date, head1, narration1, debit1, head2, narration2, credit2)
    
            return redirect(self.success_url)
    
        except Exception as e:
            messages.error(request, f'Failed to save debit note: {str(e)}')
            return redirect(self.success_url)
    

    def create_new_entries(self, request, series, date, head1, narration1, debit1, head2, narration2, credit2):
        voucher_config = VoucherConfiguration.objects.select_for_update().filter(series=series, category='Debit Note', user=request.user).first()
    
        if not voucher_config:
            messages.error(request, 'Invalid series for Debit Note.')
            return redirect(self.success_url)
        
        while Table_DrCrNote.objects.filter(user=self.request.user, series=series, noteno=voucher_config.serial_no, ntype='D').exists():
            voucher_config.serial_no += 1

    
        current_serial_no = voucher_config.serial_no
        voucher_config.serial_no += 1
        voucher_config.save()
    
        coid_entry = Table_companyDetailschild.objects.first()
        fycode_entry = Table_companyDetailschild.objects.first()
        coid = coid_entry.company_id if coid_entry else 'C'
        fycode = fycode_entry.fycode if fycode_entry else 'NON'
        user = request.user
        
        Table_DrCrNote.objects.create(
            user=user,
            series=series,
            ndate=date,
            noteno=current_serial_no,
            accountcode=head1,
            narration=narration1,
            dramount=debit1,
            cramount='0',
            ntype='D',
            userid=user.username,  # Correct field name
            coid=coid,
            fycode=fycode,
            brid='1'
        )
    
        Table_DrCrNote.objects.create(
            user=user,
            series=series,
            ndate=date,
            noteno=current_serial_no,
            accountcode=head2,
            narration=narration2,
            dramount='0',
            cramount=credit2,
            ntype='D',
            userid=user.username,  # Correct field name
            coid=coid,
            fycode=fycode,
            brid='1'
        )
    
        self.update_account_balance(head1, debit1)
        self.update_account_balance(head2, -credit2)
    
        messages.success(request, 'Debit note created successfully.')
    

    def update_account_balance(self, account_code, amount):
        accounts = Table_Accountsmaster.objects.filter(account_code=account_code, user=self.request.user)
    
        if accounts.exists():
            for account in accounts:
                current_balance = float(account.currentbalance or 0)
                account.currentbalance = current_balance + amount
                account.save()
        else:
            raise ValueError(f"No accounts found with account code: {account_code}")

class DeleteDebitNoteView(DeleteView):
    model = Table_DrCrNote
    success_url = reverse_lazy("web:account_debit_note")

    def get_object(self, queryset=None):
        pk1 = self.kwargs.get('pk1')
        pk2 = self.kwargs.get('pk2')

        # Fetch the object
        obj = Table_DrCrNote.objects.filter(id=pk1, noteno=pk2, user=self.request.user, ntype='D').first()
        if not obj:
            raise Http404("No Table_DrCrNote matches the given query.")
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # Convert dramount and cramount to float before comparison
        dramount = float(self.object.dramount) if self.object.dramount else 0
        cramount = float(self.object.cramount) if self.object.cramount else 0

        # Update the account balance before deleting
        if dramount > 0:
            self.update_account_balance(self.object.accountcode, -dramount)
        elif cramount > 0:
            self.update_account_balance(self.object.accountcode, cramount)

        # Delete the object
        self.object.delete()

        # Optionally, handle the second object if needed
        obj2 = Table_DrCrNote.objects.filter(noteno=self.object.noteno, user=self.request.user, ntype='D').exclude(id=self.object.id).first()
        if obj2:
            dramount2 = float(obj2.dramount) if obj2.dramount else 0
            cramount2 = float(obj2.cramount) if obj2.cramount else 0
            
            if dramount2 > 0:
                self.update_account_balance(obj2.accountcode, -dramount2)
            elif cramount2 > 0:
                self.update_account_balance(obj2.accountcode, cramount2)
            obj2.delete()

        messages.success(request, "Debit note entry deleted successfully.")
        return redirect(success_url)

    def update_account_balance(self, account_code, amount):
        """Updates the current balance of the account(s) in Table_Accountsmaster."""
        accounts = Table_Accountsmaster.objects.filter(account_code=account_code, user=self.request.user)
    
        if accounts.exists():
            for account in accounts:
                current_balance = float(account.currentbalance or 0)
                account.currentbalance = current_balance + amount
                account.save()
        else:
            raise ValueError(f"No accounts found with account code: {account_code}")










from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.list import ListView
from .models import Table_DrCrNote

class AccountDebitTableView(LoginRequiredMixin, ListView):
    model = Table_DrCrNote
    template_name = 'web/accounts/debit-note/debit-table.html'
    context_object_name = 'drcrnotes'

    def get_queryset(self):
        return Table_DrCrNote.objects.filter(ntype='D', userid=self.request.user.username)

          


class SearchDebitTableView(TemplateView):
    template_name = 'web/accounts/debit-note/debit-search-box.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['series_options'] = VoucherConfiguration.objects.filter(category='Debit Note', user=self.request.user).values('series')
        return context

    def post(self, request, *args, **kwargs):
        series = request.POST.get('series')
        serial_no = request.POST.get('serial_no')

        if series and serial_no:
            # Check if the serial number exists
            if Table_DrCrNote.objects.filter(series=series, noteno=serial_no, ntype='D', user=self.request.user).exists():
                return redirect(reverse('web:account_debit_note', kwargs={'series': series, 'serial_no': serial_no}))
            else:
                context = self.get_context_data(**kwargs)
                context['error'] = 'This serial number does not exist.'
                return render(request, self.template_name, context)
        
        context = self.get_context_data(**kwargs)
        context['error'] = 'Please enter both series and serial number.'
        return render(request, self.template_name, context)
    

class EditDebitTableView(LoginRequiredMixin, View):
    template_name = 'web/accounts/debit-note/edit-debit-note.html'





# - CREDIT NOTES

from django.shortcuts import redirect
from django.db import transaction
from django.contrib import messages
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from .models import Table_DrCrNote, Table_Accountsmaster, VoucherConfiguration, Table_companyDetailschild

import logging
from django.utils import timezone
from django.db import transaction


class AccountCreditNoteView(TemplateView):
    template_name = 'web/accounts/credit-note/credit-note.html'
    success_url = reverse_lazy('web:account_credit_note')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = self.kwargs.get('series')
        serial_no = self.kwargs.get('serial_no')
        
        logger.debug(f'Getting context data for series: {series}, serial_no: {serial_no}')

        context['series_options'] = VoucherConfiguration.objects.filter(category='Credit Note', user=self.request.user).values('series', 'serial_no')
        excluded_categories = ['Bank', 'Cashbook']
        head_options = Table_Accountsmaster.objects.exclude(category__in=excluded_categories).values('head', 'account_code').filter(user=self.request.user)
        context['head_options'] = head_options
        context['drcrnotes'] = Table_DrCrNote.objects.filter(ntype='C', user=self.request.user)
        context['series'] = series
        context['serial_no'] = serial_no
    
        if series and serial_no:
            matched_notes = Table_DrCrNote.objects.filter(series=series, noteno=serial_no, ntype='C', user=self.request.user)
            logger.debug(f'Matched notes: {matched_notes}')

            if matched_notes.exists():
                matched_note_dr = matched_notes.filter(dramount__gt=0).first()
                matched_note_cr = matched_notes.filter(cramount__gt=0).first()
    
                if matched_note_dr:
                    matched_note_dr_head = Table_Accountsmaster.objects.filter(account_code=matched_note_dr.accountcode, user=self.request.user).first()
                    if matched_note_dr_head:
                        matched_note_dr.head = matched_note_dr_head.head
                    matched_note_dr.ndate = matched_note_dr.ndate.strftime('%Y-%m-%d')
                    context['matched_note_dr'] = matched_note_dr
    
                if matched_note_cr:
                    matched_note_cr_head = Table_Accountsmaster.objects.filter(user=self.request.user, account_code=matched_note_cr.accountcode).first()
                    if matched_note_cr_head:
                        matched_note_cr.head = matched_note_cr_head.head
                    context['matched_note_cr'] = matched_note_cr
    
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context['company_name'] = company_details.companyname
            context['address1'] = company_details.address1
            context['address2'] = company_details.address2
            context['phoneno'] = company_details.phoneno
    
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        series = request.POST.get('series')
        serial_no = request.POST.get('serial_no')
        date = request.POST.get('date')
        head1 = request.POST.get('head1')
        narration1 = request.POST.get('narration1')
        credit1_str = request.POST.get('credit1', '0')
        credit1 = float(credit1_str) if credit1_str else 0.0  # Convert to float with default value
        head2 = request.POST.get('head2')
        narration2 = request.POST.get('narration2')
        debit2_str = request.POST.get('debit2', '0')
        debit2 = float(debit2_str) if debit2_str else 0.0  # Convert to float with default value
    
        try:
            if series and serial_no:
                matched_notes = Table_DrCrNote.objects.filter(user=self.request.user, series=series, noteno=serial_no, ntype='C')
                if matched_notes.exists():
                    # Update existing debit and credit notes
                    dr_note = matched_notes.filter(dramount__gt=0).first()
                    cr_note = matched_notes.filter(cramount__gt=0).first()
    
                    # Update the current balance before updating the note
                    if dr_note:
                        self.update_account_balance(dr_note.accountcode, float(dr_note.dramount))
                    if cr_note:
                        self.update_account_balance(cr_note.accountcode, -float(cr_note.cramount))
    
                    # Update the note details
                    if dr_note:
                        dr_note.ndate = date
                        dr_note.accountcode = head1  # Updated to head2 for debit2
                        dr_note.narration = narration1
                        dr_note.dramount = credit1
                        dr_note.save()
                        # Update the Account_Master table for debit
                        self.update_account_balance(head1, -credit1)
                    if cr_note:
                        cr_note.ndate = date
                        cr_note.accountcode = head2  # Updated to head1 for credit1
                        cr_note.narration = narration2
                        cr_note.cramount = debit2
                        cr_note.save()
                        # Update the Account_Master table for credit
                        self.update_account_balance(head2, debit2)
    
                    messages.success(request, 'Credit note updated successfully.')
                else:
                    # Create new entries if no existing notes are matched
                    self.create_new_entries(request, series, date, head1, narration1, credit1, head2, narration2, debit2)
    
            else:
                # Create new entries if series and serial_no are not provided
                self.create_new_entries(request, series, date, head1, narration1, credit1, head2, narration2, debit2)
    
            return redirect(self.success_url)
    
        except Exception as e:
            messages.error(request, f'Failed to save credit note: {str(e)}')
            return redirect(self.success_url)
    

    def create_new_entries(self, request, series, date, head1, narration1, credit1, head2, narration2, debit2):
        voucher_config = VoucherConfiguration.objects.filter(series=series, category='Credit Note', user=self.request.user).first()
    
        if not voucher_config:
            messages.error(request, 'Invalid series for Credit Note.')
            return redirect(self.success_url)
    
        current_serial_no = voucher_config.serial_no
        next_serial_no = current_serial_no + 1
    
        voucher_config.serial_no = next_serial_no
        voucher_config.save()
    
        coid_entry = Table_companyDetailschild.objects.first()
        fycode_entry = Table_companyDetailschild.objects.first()
        coid = coid_entry.company_id if coid_entry else 'C'
        fycode = fycode_entry.fycode if fycode_entry else 'NON'
        user = request.user

        if Table_DrCrNote.objects.filter(
            user=user,
            series=series,
            noteno=current_serial_no,
            ntype='C'
        ).exists():
            messages.error(request, f"A Credit Note with Series '{series}' and Serial No '{current_serial_no}' already exists.")
            return redirect(self.success_url)
    
        Table_DrCrNote.objects.create(
            user=user,
            series=series,
            ndate=date,
            noteno=current_serial_no,
            accountcode=head1,
            narration=narration1,
            dramount=debit2,
            cramount='0',
            ntype='C',
            userid=user.username,  # Correct field name
            coid=coid,
            fycode=fycode,
            brid='1'
        )
    
        Table_DrCrNote.objects.create(
            user=user,
            series=series,
            ndate=date,
            noteno=current_serial_no,
            accountcode=head2,
            narration=narration2,
            dramount='0',
            cramount=credit1,
            ntype='C',
            userid=user.username,  # Correct field name
            coid=coid,
            fycode=fycode,
            brid='1'
        )
    
        self.update_account_balance(head1, -credit1)
        self.update_account_balance(head2, debit2)
    
        messages.success(request, 'Credit note created successfully.')
    

    def update_account_balance(self, account_code, amount):
        accounts = Table_Accountsmaster.objects.filter(account_code=account_code, user=self.request.user)
    
        if accounts.exists():
            for account in accounts:
                current_balance = float(account.currentbalance or 0)
                account.currentbalance = current_balance + amount
                account.save()
        else:
            raise ValueError(f"No accounts found with account code: {account_code}")












class AccountCreditTableView(ListView):
    model = Table_DrCrNote
    template_name = 'web/accounts/credit-note/credit-table.html'
    context_object_name = "drcrnotesss"

    def get_queryset(self):
        return super().get_queryset().filter(ntype='C', user=self.request.user)    

class SearchCreditTableView(LoginRequiredMixin, TemplateView):
    template_name = 'web/accounts/credit-note/credit-search-box.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['series_options'] = VoucherConfiguration.objects.filter(category='Credit Note', user=self.request.user).values('series')
        return context

    def post(self, request, *args, **kwargs):
        series = request.POST.get('series')
        serial_no = request.POST.get('serial_no')

        if series and serial_no:
            # Check if the serial number exists
            if Table_DrCrNote.objects.filter(series=series, noteno=serial_no, ntype='C', user=self.request.user).exists():
                return redirect(reverse('web:account_credit_note', kwargs={'series': series, 'serial_no': serial_no}))
            else:
                context = self.get_context_data(**kwargs)
                context['error'] = 'This serial number does not exist.'
                return render(request, self.template_name, context)
        
        context = self.get_context_data(**kwargs)
        context['error'] = 'Please enter both series and serial number.'
        return render(request, self.template_name, context)


class DeleteCreditNoteView(LoginRequiredMixin, DeleteView):
    model = Table_DrCrNote
    success_url = reverse_lazy("web:account_credit_note")

    def get_object(self, queryset=None):
        pk1 = self.kwargs.get('pk1')
        pk2 = self.kwargs.get('pk2')

        # Fetch the object
        obj = Table_DrCrNote.objects.filter(id=pk1, noteno=pk2, user=self.request.user, ntype='C').first()
        if not obj:
            raise Http404("No Table_DrCrNote matches the given query.")
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # Convert dramount and cramount to float before comparison
        dramount = float(self.object.dramount) if self.object.dramount else 0
        cramount = float(self.object.cramount) if self.object.cramount else 0

        # Update the account balance before deleting
        if dramount > 0:
            self.update_account_balance(self.object.accountcode, dramount)
        elif cramount > 0:
            self.update_account_balance(self.object.accountcode, -cramount)

        # Delete the object
        self.object.delete()

        # Optionally, handle the second object if needed
        obj2 = Table_DrCrNote.objects.filter(noteno=self.object.noteno, user=self.request.user, ntype='C').exclude(id=self.object.id).first()
        if obj2:
            dramount2 = float(obj2.dramount) if obj2.dramount else 0
            cramount1 = float(obj2.cramount) if obj2.cramount else 0
            
            if dramount2 > 0:
                self.update_account_balance(obj2.accountcode, dramount2)
            elif cramount1 > 0:
                self.update_account_balance(obj2.accountcode, -cramount1)
            obj2.delete()

        messages.success(request, "credit note entry deleted successfully.")
        return redirect(success_url)

    def update_account_balance(self, account_code, amount):
        """Updates the current balance of the account(s) in Table_Accountsmaster."""
        accounts = Table_Accountsmaster.objects.filter(account_code=account_code, user=self.request.user)
    
        if accounts.exists():
            for account in accounts:
                current_balance = float(account.currentbalance or 0)
                account.currentbalance = current_balance + amount
                account.save()
        else:
            raise ValueError(f"No accounts found with account code: {account_code}")
 


# - Voucher Configuration
class VoucherConfigurationListView(LoginRequiredMixin, ListView, View):
    model = VoucherConfiguration
    template_name = 'web/accounts/voucher-configuration/voucher_configuration.html'
    success_url = reverse_lazy('web:voucher_configuration')

    def get(self, request, *args, **kwargs):
        configurations = VoucherConfiguration.objects.all()
        next_serial_numbers = {}

        for config in configurations:
            category_series = (config.category, config.series)
            last_serial = VoucherConfiguration.objects.filter(
                category=config.category,
                series=config.series
            ).order_by('-serial_no').first()
            if last_serial:
                next_serial_numbers[category_series] = last_serial.serial_no + 1
            else:
                next_serial_numbers[category_series] = 1

        context = {
            'object_list': configurations,
            'next_serial_numbers': next_serial_numbers
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        category = request.POST.get('category')
        series = request.POST.get('series')
        serial_no = request.POST.get('serial_no')

        if category and series and serial_no:
            try:
                VoucherConfiguration.objects.create(
                    user = self.request.user,
                    category=category,
                    series=series,
                    serial_no=serial_no
                )
                return JsonResponse({'success': True, 'redirect_url': self.success_url})
            except IntegrityError:
                context = {
                    'object_list': VoucherConfiguration.objects.all(),
                    'error': 'This combination of category and series already exists.'
                }
                return render(request, self.template_name, context)
        else:
            context = {
                'object_list': VoucherConfiguration.objects.all(),
                'error': 'All fields are required.'
            }
            return render(request, self.template_name, context)


class ValidateVoucherConfiguration(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        series = request.GET.get('series')
        next_serial_no = 1  # Default to 1 if no existing serial number

        if series:
            last_serial = Table_Voucher.objects.filter(Series=series).order_by('-VoucherNo').first()
            if last_serial:
                next_serial_no = last_serial.VoucherNo + 1

        return JsonResponse({'next_serial_no': next_serial_no})
    

class VoucherConfigurationTable(LoginRequiredMixin, ListView):
    model = VoucherConfiguration
    template_name = 'web/accounts/voucher-configuration/voucher_search.html'
    context_object_name = "voucherconfiguration"

    def get_queryset(self):
        return VoucherConfiguration.objects.filter(user=self.request.user)



# - RECEIPT 


class EnterAmountView(LoginRequiredMixin, View):
    template_name = 'web/accounts/receipt/receipt.html'

    def get(self, request, *args, **kwargs):
        vouchers = VoucherConfiguration.objects.filter(category='receipt', user=request.user)
        next_serial_numbers = {voucher.series: voucher.serial_no for voucher in vouchers}

        account_masters = Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'])
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user)

        table_acntchildren = Table_Acntchild.objects.select_related('account_master').filter(
            account_master__category__in=['Bank', 'Cashbook'], account_master__user=request.user
        )

        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': account_masters,
            'wallet': Wallet.objects.first(),
            'head_accounts': head_accounts,
            'next_serial_numbers': next_serial_numbers,
            'selected_series': None,
            'next_voucher_no': None,
            'table_acntchildren': table_acntchildren,
            'user_id': request.user.id,
        })

    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('Series')
            vdate = request.POST.get('Vdate')
            headcode = request.POST.get('Headcode')
            user_id = request.user.id
            fy_code = '2024-2025'
            coid = 'C'
            branch_id = '1'
    
            accountcodes = request.POST.getlist('Accountcode[]')
            narrations = request.POST.getlist('Narration[]')
            vtypes = request.POST.getlist('VType[]')
            payments = request.POST.getlist('payment[]')
    
            if not (len(accountcodes) == len(narrations) == len(vtypes) == len(payments)):
                raise ValueError("Mismatched input lengths in form data.")
    
            total_amount = sum(float(payment) for payment in payments)
    
            voucher_config = VoucherConfiguration.objects.get(series=series, category='receipt', user=self.request.user)
            current_serial_no = int(voucher_config.serial_no)
            voucher_no = current_serial_no
    
            with transaction.atomic():
                for accountcode, narration, vtype, payment in zip(accountcodes, narrations, vtypes, payments):
                    # Create voucher entry
                    Table_Voucher.objects.create(
                        user=request.user,
                        Series=series,
                        VoucherNo=voucher_no,
                        Vdate=vdate,
                        Accountcode=accountcode,
                        Headcode=headcode,
                        payment=payment,
                        VAmount=total_amount,
                        VType=vtype,
                        Narration=narration,
                        CStatus='R',
                        UserID=user_id,
                        FYCode=fy_code,
                        Coid=coid,
                        Branch_ID=branch_id
                    )
    
                    # Update the current balance for Table_Acntchild
                    try:
                        account_master = Table_Accountsmaster.objects.filter(account_code=accountcode, user=self.request.user).first()
                        acnt_child = Table_Acntchild.objects.get(account_code=accountcode, account_master=account_master)
                        if acnt_child:
                            current_balance = float(acnt_child.current_balance or 0)
                            payment_amount = float(payment)
                            new_balance = current_balance - payment_amount
                            acnt_child.current_balance = str(new_balance)
                            acnt_child.save()
                        else:
                            print('no acnt child 1')
                    except Table_Acntchild.DoesNotExist:
                        print(f"Account code {accountcode} not found in Table_Acntchild.")
                    except Exception as e:
                        print(f"Error updating balance for account code {accountcode}: {e} 1")
    
                    # Update the current balance for Table_Accountsmaster
                    try:
                        account_master = Table_Accountsmaster.objects.filter(account_code=accountcode, user=self.request.user).first()
                        if account_master:
                            current_balance_master = float(account_master.currentbalance or 0)
                            new_balance_master = current_balance_master - float(payment)
                            account_master.currentbalance = str(new_balance_master)
                            account_master.save()
                        else:
                            print('no account_master 1')
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account code {accountcode} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error updating balance for account code {accountcode} in Table_Accountsmaster: {e} 2")
    
                # Only update the selected account
                selected_account_code = request.POST.get('Headcode')
                # In the EnterAmountView post method

                # Update the current balance for Table_Accountsmaster (Head accounts)
                if selected_account_code:
                    try:
                        selected_account_master = Table_Accountsmaster.objects.filter(account_code=selected_account_code, user=self.request.user).first()
                        current_balance_master = float(selected_account_master.currentbalance or 0)
                        new_balance_master = current_balance_master + total_amount
                        selected_account_master.currentbalance = str(new_balance_master)
                        selected_account_master.save()
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Selected account code {selected_account_code} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error updating balance for selected account code {selected_account_code}: {e} 2")

    
                voucher_config.serial_no = voucher_no + 1
                voucher_config.save()
    
            next_serial_numbers = {
                voucher.series: str(voucher_config.serial_no)
                for voucher in VoucherConfiguration.objects.filter(category='receipt')
            }
    
            return render(request, self.template_name, {
                'success': "Voucher saved successfully!",
                'vouchers': VoucherConfiguration.objects.filter(category='receipt', user=self.request.user),
                'accountmas': Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user),
                'wallet': Wallet.objects.first(),
                'head_accounts': Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user),
                'next_serial_numbers': next_serial_numbers,
                'selected_series': series,
                'next_voucher_no': next_serial_numbers.get(series),
                'table_acntchildren': Table_Acntchild.objects.select_related('account_master').filter(
                    account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
                ),
                'user_id': request.user.id,
            })
        except Exception as e:
            print(f"Error: {e}")
            # If there's an error, still provide the necessary context
            next_serial_numbers = {
                voucher.series: str(voucher_config.serial_no)
                for voucher in VoucherConfiguration.objects.filter(category='receipt')
            }
            
            return render(request, self.template_name, {
                'error': str(e),
                'vouchers': VoucherConfiguration.objects.filter(category='receipt', user=self.request.user),
                'accountmas': Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user),
                'wallet': Wallet.objects.first(),
                'head_accounts': Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user),
                'next_serial_numbers': next_serial_numbers,
                'selected_series': series,
                'next_voucher_no': next_serial_numbers.get(series),
                'table_acntchildren': Table_Acntchild.objects.select_related('account_master').filter(
                    account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
                ),
                'user_id': request.user.id,
            })
        
        
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse

class EditReceiptView(LoginRequiredMixin, View):
    template_name = 'web/accounts/receipt/edit_receipt.html'

    def get(self, request, *args, **kwargs):
        series = request.GET.get('Series')
        voucher_no = request.GET.get('VoucherNo')

        # Fetch necessary data
        vouchers = VoucherConfiguration.objects.filter(category='receipt', user=self.request.user)
        accountmas = Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user)
        wallet = Wallet.objects.first()
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank'], user=self.request.user)
        table_acntchildren = Table_Acntchild.objects.select_related('account_master').filter(
            account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
        )

        # Fetch voucher entries for the given series and voucher number
        voucher_entries = Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='R', user=self.request.user)

        if not voucher_entries:
            return render(request, 'web/accounts/receipt/receipt_modify.html', {
                'vouchers': vouchers,
                'accountmas': accountmas,
                'wallet': wallet,
                'head_accounts': head_accounts,
                'table_acntchildren': table_acntchildren,
                'voucher_entries': [],
                'user_id': request.user.id,
                'error_message': 'This combination of Series and Voucher No does not exist.',
                'redirect_url': reverse('web:receipt_modify')  # Replace with the correct URL name
            })

        # Assuming you want to fetch the first entry for the book head
        first_voucher = voucher_entries.first()
        headcode = first_voucher.Headcode

        try:
            # Retrieve the account master entry for the selected head code
            head_account = Table_Accountsmaster.objects.filter(account_code=headcode, user=self.request.user).first()
            head_name = head_account.head  # Assuming 'head' is the field name for the head name
            current_balance = head_account.currentbalance  # Retrieve the current balance
        except Table_Accountsmaster.DoesNotExist:
            head_name = None  # Handle this as appropriate
            current_balance = None

        # Pass the head name and current balance to the template
        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': accountmas,
            'wallet': wallet,
            'head_accounts': head_accounts,
            'table_acntchildren': table_acntchildren,
            'voucher_entries': voucher_entries,
            'user_id': request.user.id,
            'headcode': headcode,  # Pass the head code to the template
            'head_name': head_name,  # Pass the head name to the template
            'current_balance': current_balance  # Pass current balance to the template
        })

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')  # Hidden input to determine the action
        series = request.POST.get('Series')
        voucher_no = request.POST.get('VoucherNo')

        try:
            if action == 'delete':
                # Fetch voucher entries for deletion
                voucher_entries = Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='R', user=self.request.user)

                if not voucher_entries:
                    return render(request, self.template_name, {
                        'error': 'No voucher entries found for deletion.',
                        'user_id': request.user.id,
                        'redirect_url': reverse('web:receipt_modify')
                    })

                # Get the Headcode and old total amount for adjustment
                headcode = voucher_entries.first().Headcode
                old_total_amount = sum(float(entry.payment) for entry in voucher_entries)

                # Update the current balance of the head account
                try:
                    head_account = Table_Accountsmaster.objects.get(account_code=headcode, user=self.request.user)
                    current_balance = float(head_account.currentbalance or 0)
                    new_balance = current_balance - old_total_amount  # Add back the old amount
                    head_account.currentbalance = str(new_balance)
                    head_account.save()
                except Table_Accountsmaster.DoesNotExist:
                    print(f"Head account code {headcode} not found in Table_Accountsmaster.")

                # Delete the voucher entries
                voucher_entries.delete()

                return render(request, self.template_name, {
                    'success': "Receipt deleted successfully!",
                    'user_id': request.user.id,
                    'redirect_url': reverse('web:receipt_modify')
                })

            # Update logic for editing the receipt (if not delete)
            accountcodes = request.POST.getlist('Accountcode[]')
            narrations = request.POST.getlist('Narration[]')
            vtypes = request.POST.getlist('VType[]')
            payments = request.POST.getlist('payment[]')

            if not (len(accountcodes) == len(narrations) == len(vtypes) == len(payments)):
                raise ValueError("Mismatched input lengths in form data.")

            total_amount = sum(float(payment) for payment in payments)

            # Use a transaction to ensure atomic operations
            with transaction.atomic():
                # Fetch and revert existing voucher entries
                voucher_entries = Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='R', user=self.request.user)
                old_total_amount = 0
                for entry in voucher_entries:
                    account_code = entry.Accountcode
                    payment_amount = float(entry.payment)
                    old_total_amount += payment_amount

                    # Revert the old payment amount from Table_Acntchild
                    try:
                        acnt_child = Table_Acntchild.objects.get(account_code=account_code, account_master__user=self.request.user)
                        current_balance = float(acnt_child.current_balance or 0)
                        new_balance = current_balance + payment_amount  # Add back the old amount
                        acnt_child.current_balance = str(new_balance)
                        acnt_child.save()
                    except Table_Acntchild.DoesNotExist:
                        print(f"Account code {account_code} not found in Table_Acntchild.")
                    except Exception as e:
                        print(f"Error reverting balance for account code {account_code}: {e}")

                    # Revert the old payment amount from Table_Accountsmaster
                    try:
                        account_master = Table_Accountsmaster.objects.get(account_code=account_code, user=self.request.user)
                        current_balance_master = float(account_master.currentbalance or 0)
                        new_balance_master = current_balance_master + payment_amount  # Add back the old amount
                        account_master.currentbalance = str(new_balance_master)
                        account_master.save()
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account code {account_code} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error reverting balance for account code {account_code} in Table_Accountsmaster: {e}")

                # Delete old voucher entries after reverting balances
                voucher_entries.delete()

                # Create new voucher entries with updated balances
                for accountcode, narration, vtype, payment in zip(accountcodes, narrations, vtypes, payments):
                    Table_Voucher.objects.create(
                        user=request.user,
                        Series=series,
                        VoucherNo=voucher_no,
                        Vdate=request.POST.get('Vdate'),
                        Accountcode=accountcode,
                        Headcode=request.POST.get('Headcode'),
                        payment=payment,
                        VAmount=total_amount,
                        VType=vtype,
                        Narration=narration,
                        CStatus='R',
                        UserID=request.user.id,
                        FYCode='2024-2025',
                        Coid='C',
                        Branch_ID='1'
                    )

                    # Update the current balance for Table_Acntchild
                    try:
                        acnt_child = Table_Acntchild.objects.get(account_code=accountcode, account_master__user=self.request.user)
                        if acnt_child:
                            current_balance = float(acnt_child.current_balance or 0)
                            new_balance = current_balance - float(payment)  # Subtract the new amount
                            acnt_child.current_balance = str(new_balance)
                            acnt_child.save()
                        else:
                            print('no acnt child 2')
                    except Table_Acntchild.DoesNotExist:
                        print(f"Account code {accountcode} not found in Table_Acntchild.")
                    except Exception as e:
                        print(f"Error updating balance for account code {accountcode}: {e} 3")

                    # Update the current balance for Table_Accountsmaster
                    try:
                        account_master = Table_Accountsmaster.objects.get(account_code=accountcode, user=self.request.user)
                        if account_master:
                            current_balance_master = float(account_master.currentbalance or 0)
                            new_balance_master = current_balance_master - float(payment)  # Subtract the new amount
                            account_master.currentbalance = str(new_balance_master)
                            account_master.save()
                        else:
                            print('no account master 2')
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account code {accountcode} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error updating balance for account code {accountcode} in Table_Accountsmaster: {e} 4")

                # Update the balance of the selected head account
                headcode = request.POST.get('Headcode')
                if headcode:
                    try:
                        selected_account_master = Table_Accountsmaster.objects.get(account_code=headcode, user=self.request.user)
                        current_balance_master = float(selected_account_master.currentbalance or 0)
                        new_balance_master = current_balance_master + total_amount - old_total_amount

                        selected_account_master.currentbalance = str(new_balance_master)
                        selected_account_master.save()
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Selected head account code {headcode} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error updating balance for selected head account code {headcode}: {e}")

                return render(request, self.template_name, {
                    'success': "Receipt updated successfully!",
                    'user_id': request.user.id,
                    'redirect_url': reverse('web:receipt_modify')
                })

        except Exception as e:
            print(f"Error: {e}")
            return render(request, self.template_name, {
                'error': str(e),
                'user_id': request.user.id,
                'redirect_url': reverse('web:receipt_modify')
            })



   

class SearchReceiptView(LoginRequiredMixin, View):
    template_name = 'web/accounts/receipt/receipt_modify.html'

    def get(self, request, *args, **kwargs):
        vouchers = VoucherConfiguration.objects.filter(category='receipt', user=self.request.user)
        return render(request, self.template_name, {'vouchers': vouchers})
    
    
class ReceiptDetailView(View):
    template_name = 'web/accounts/receipt/table-details.html'

    def get(self, request, voucher_id, *args, **kwargs):
        voucher = get_object_or_404(Table_Voucher, id=voucher_id)
        return render(request, self.template_name, {
            'voucher': voucher,
        })


class ReceiptListTable(LoginRequiredMixin, ListView):
    model = Table_Voucher
    template_name = 'web/accounts/receipt/receipt_list.html'
    context_object_name = "vouchers"

    def get_queryset(self):
        receipt_series = VoucherConfiguration.objects.filter(category='receipt', user=self.request.user).values_list('series', flat=True)
        
        # Filter Table_Voucher based on the series related to the receipt category and CStatus being 'R'
        return Table_Voucher.objects.filter(Series__in=receipt_series, CStatus='R', user=self.request.user)
        



# - PAYMENT

from django.db import transaction
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import VoucherConfiguration, Table_Acntchild, Table_Accountsmaster, Table_Voucher

class PaymentEnterAmountView(LoginRequiredMixin, View):
    template_name = 'web/accounts/payment/payment.html'

    def get(self, request, *args, **kwargs):
        # Get relevant data
        vouchers = VoucherConfiguration.objects.filter(category='payment', user=self.request.user)
        next_serial_numbers = {voucher.series: voucher.serial_no for voucher in vouchers}

        account_masters = Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user)
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user)

        table_acntchildren = Table_Acntchild.objects.select_related('account_master').filter(
            account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
        )

        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': account_masters,
            'head_accounts': head_accounts,
            'next_serial_numbers': next_serial_numbers,
            'table_acntchildren': table_acntchildren,
            'user_id': request.user.id,
        })

    def update_current_balance(self, account_code, payment, increase=True):
        try:
            acnt_child = Table_Acntchild.objects.filter(account_code=account_code,  account_master__user=self.request.user).first()
            current_balance = float(acnt_child.current_balance or 0)
            payment_amount = float(payment)
            new_balance = current_balance + payment_amount if increase else current_balance - payment_amount
            acnt_child.current_balance = str(new_balance)
            acnt_child.save()
        except Table_Acntchild.DoesNotExist:
            print(f"Account code {account_code} not found in Table_Acntchild.")
        except Exception as e:
            print(f"Error updating balance for account code {account_code}: {e} 5")

        try:
            account_master = Table_Accountsmaster.objects.filter(account_code=account_code, user=self.request.user).first()
            current_balance_master = float(account_master.currentbalance or 0)
            # Update balance with appropriate adjustment for head accounts
            if account_master.category in ['Cashbook', 'Bank']:
                new_balance_master = current_balance_master - payment_amount if increase else current_balance_master - payment_amount
            else:
                new_balance_master = current_balance_master - payment_amount if not increase else current_balance_master + payment_amount
            account_master.currentbalance = str(new_balance_master)
            account_master.save()
        except Table_Accountsmaster.DoesNotExist:
            print(f"Account code {account_code} not found in Table_Accountsmaster.")
        except Exception as e:
            print(f"Error updating balance for account code {account_code} in Table_Accountsmaster: {e} 6")


    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('Series')
            vdate = request.POST.get('Vdate')
            headcode = request.POST.get('Headcode')
            user_id = request.user.id
            fy_code = '2024-2025'
            coid = 'C'
            branch_id = '1'

            accountcodes = request.POST.getlist('Accountcode[]')
            narrations = request.POST.getlist('Narration[]')
            vtypes = request.POST.getlist('VType[]')
            payments = request.POST.getlist('payment[]')

            if not (len(accountcodes) == len(narrations) == len(vtypes) == len(payments)):
                raise ValueError("Mismatched input lengths in form data.")

            total_amount = sum(float(payment) for payment in payments)

            voucher_config = VoucherConfiguration.objects.get(series=series, category='payment', user=self.request.user)
            current_serial_no = int(voucher_config.serial_no)
            voucher_no = current_serial_no

            with transaction.atomic():
                for accountcode, narration, vtype, payment in zip(accountcodes, narrations, vtypes, payments):
                    # Create voucher entry
                    Table_Voucher.objects.create(
                        user=request.user,
                        Series=series,
                        VoucherNo=voucher_no,
                        Vdate=vdate,
                        Accountcode=accountcode,
                        Headcode=headcode,
                        payment=payment,
                        VAmount=total_amount,
                        VType=vtype,
                        Narration=narration,
                        CStatus='P',
                        UserID=user_id,
                        FYCode=fy_code,
                        Coid=coid,
                        Branch_ID=branch_id
                    )

                    # Update the current balance for each account
                    self.update_current_balance(accountcode, payment)

                # Only update the selected account
                selected_account_code = request.POST.get('Headcode')
                if selected_account_code:
                    self.update_current_balance(selected_account_code, total_amount)

                voucher_config.serial_no = voucher_no + 1
                voucher_config.save()

            next_serial_numbers = {
                voucher.series: str(voucher_config.serial_no)
                for voucher in VoucherConfiguration.objects.filter(category='payment')
            }

            return render(request, self.template_name, {
                'success': "Payment voucher saved successfully!",
                'vouchers': VoucherConfiguration.objects.filter(category='payment', user=self.request.user),
                'accountmas': Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user),
                'head_accounts': Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user),
                'next_serial_numbers': next_serial_numbers,
                'table_acntchildren': Table_Acntchild.objects.select_related('account_master').filter(
                    account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
                ),
                'user_id': request.user.id,
            })
        except Exception as e:
            print(f"Error: {e}")
            next_serial_numbers = {
                voucher.series: str(voucher_config.serial_no)
                for voucher in VoucherConfiguration.objects.filter(category='payment', user=self.request.user)
            }
            return render(request, self.template_name, {
                'error': str(e),
                'vouchers': VoucherConfiguration.objects.filter(category='payment', user=self.request.user),
                'accountmas': Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user),
                'head_accounts': Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user),
                'next_serial_numbers': next_serial_numbers,
                'table_acntchildren': Table_Acntchild.objects.select_related('account_master').filter(
                    account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
                ),
                'user_id': request.user.id,
            })








from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .models import VoucherConfiguration, Table_Voucher, Table_Accountsmaster, Table_Acntchild, Wallet
from django.urls import reverse

class EditPaymentView(LoginRequiredMixin, View):
    template_name = 'web/accounts/payment/edit_payment.html'

    def get(self, request, *args, **kwargs):
        series = request.GET.get('Series')
        voucher_no = request.GET.get('VoucherNo')
    
        # Fetch necessary data
        vouchers = VoucherConfiguration.objects.filter(category='payment', user=self.request.user)
        accountmas = Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user)
        wallet = Wallet.objects.first()
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank'], user=self.request.user)
        table_acntchildren = Table_Acntchild.objects.select_related('account_master').filter(
            account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user,
        )
    
        # Fetch voucher entries for the given series and voucher number
        voucher_entries = Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='P', user=self.request.user)
    
        if not voucher_entries:
            # If voucher entries do not exist, display SweetAlert error message
            return render(request, 'web/accounts/payment/payment_modify.html', {
                'vouchers': vouchers,
                'accountmas': accountmas,
                'wallet': wallet,
                'head_accounts': head_accounts,
                'table_acntchildren': table_acntchildren,
                'voucher_entries': [],
                'user_id': request.user.id,
                'error_message': 'This combination of Series and Voucher No does not exist.',
                'redirect_url': reverse('web:payment_modify')  # Replace with the correct URL name
            })
    
        # Get the head code from the first voucher entry
        head_code = voucher_entries[0].Headcode
    
        # Fetch the current balance of the head account
        try:
            head_account = Table_Accountsmaster.objects.get(account_code=head_code, user=self.request.user)
            current_balance_head = head_account.currentbalance or 0
            head_account_name = head_account.head  # Get the account name
        except Table_Accountsmaster.DoesNotExist:
            current_balance_head = None  # Handle case where head account does not exist
            head_account_name = None
    
        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': accountmas,
            'wallet': wallet,
            'head_accounts': head_accounts,
            'table_acntchildren': table_acntchildren,
            'voucher_entries': voucher_entries,
            'user_id': request.user.id,
            'current_balance_head': current_balance_head,  # Pass current balance to the template
            'head_account_name': head_account_name,  # Pass the head account name
        })
    

    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('Series')
            vdate = request.POST.get('Vdate')
            headcode = request.POST.get('Headcode')
            user_id = request.user.id
            fy_code = '2024-2025'
            coid = 'C'
            branch_id = '1'
    
            accountcodes = request.POST.getlist('Accountcode[]')
            narrations = request.POST.getlist('Narration[]')
            vtypes = request.POST.getlist('VType[]')
            payments = request.POST.getlist('payment[]')
            voucher_no = request.POST.get('VoucherNo')
    
            # Ensure all lists are of the same length
            if not (len(accountcodes) == len(narrations) == len(vtypes) == len(payments)):
                raise ValueError("Mismatched input lengths in form data.")
    
            # Validate that all payments except those related to head_accounts are positive
            for payment, accountcode in zip(payments, accountcodes):
                if Table_Accountsmaster.objects.filter(account_code=accountcode, user=self.request.user).exclude(category__in=['Cashbook', 'Bank']).exists():
                    if float(payment) < 0:
                        raise ValueError(f"Payment for account code {accountcode} must be positive.")
    
            # Calculate the new total amount
            new_total_amount = sum(float(payment) for payment in payments)
    
            with transaction.atomic():
                # Fetch existing entries to get old amounts and account codes
                old_entries = Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='P')
    
                # Calculate the old total amount
                old_total_amount = sum(float(entry.payment) for entry in old_entries)
    
                # Revert previous balances before updating
                for old_entry in old_entries:
                    accountcode = old_entry.Accountcode
                    old_payment = old_entry.payment
                    try:
                        account_master = Table_Accountsmaster.objects.get(account_code=accountcode, user=self.request.user)
                        if account_master:
                            current_balance_master = float(account_master.currentbalance or 0)
                            updated_balance_master = current_balance_master - float(old_payment)  # Revert balance
                            account_master.currentbalance = str(updated_balance_master)
                            account_master.save()
                        else:
                            print('no account master 3')
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account code {accountcode} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error updating balance for account code {accountcode} in Table_Accountsmaster: {e} 7")
    
                # Delete old entries
                old_entries.delete()
    
                # Update or create new entries and adjust balances
                for accountcode, narration, vtype, payment in zip(accountcodes, narrations, vtypes, payments):
                    Table_Voucher.objects.create(
                        user=request.user,
                        Series=series,
                        VoucherNo=voucher_no,
                        Vdate=vdate,
                        Accountcode=accountcode,
                        Headcode=headcode,
                        payment=payment,
                        VAmount=new_total_amount,  # Save the total amount
                        VType=vtype,
                        Narration=narration,
                        CStatus='P',
                        UserID=user_id,
                        FYCode=fy_code,
                        Coid=coid,
                        Branch_ID=branch_id
                    )
        
                    # Update the balance in Table_Accountsmaster
                    try:
                        account_master = Table_Accountsmaster.objects.get(account_code=accountcode, user=self.request.user)
                        if account_master:
                            current_balance_master = float(account_master.currentbalance or 0)
                            updated_balance_master = current_balance_master + float(payment)  # Add new payment
                            account_master.currentbalance = str(updated_balance_master)
                            account_master.save()
                        else:
                            print('no account master 4')
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account code {accountcode} not found in Table_Accountsmaster.")
                    except Exception as e:
                        print(f"Error updating balance for account code {accountcode} in Table_Accountsmaster: {e} 8")
    
                # Update the balance for head_accounts by adding the difference between the new and old total amount
                try:
                    head_account = Table_Accountsmaster.objects.filter(account_code=headcode, user=self.request.user).first()
                    current_balance_head = float(head_account.currentbalance or 0)
                    difference = new_total_amount - old_total_amount
                    updated_balance_head = current_balance_head - difference
                    head_account.currentbalance = str(updated_balance_head)
                    head_account.save()
    
                except Table_Accountsmaster.DoesNotExist:
                    print(f"Head account code {headcode} not found in Table_Accountsmaster.")
                except Exception as e:
                    print(f"Error updating balance for head account code {headcode} in Table_Accountsmaster: {e}")
    
                # Update the serial number in VoucherConfiguration for the next use if not editing
                if not voucher_no:
                    voucher_config = VoucherConfiguration.objects.get(series=series, category='payment', user=self.request.user)
                    voucher_config.serial_no += 1
                    voucher_config.save()
    
            print("Payment saved successfully!")
            return redirect('web:payment')  # Redirect to payment modify page after saving
    
        except Exception as e:
            print("Error saving payment: ", e)
    
            # Fetch necessary data to repopulate the form
            vouchers = VoucherConfiguration.objects.filter(category='payment', user=self.request.user)
            accountmas = Table_Accountsmaster.objects.filter(category__in=['Cashbook', 'Bank'], user=self.request.user)
            wallet = Wallet.objects.first()
            head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Cashbook', 'Bank']).filter(user=self.request.user)
            table_acntchildren = Table_Acntchild.objects.select_related('account_master').filter(
                account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
            )
    
            return render(request, self.template_name, {
                'error_message': str(e),
                'vouchers': vouchers,
                'accountmas': accountmas,
                'wallet': wallet,
                'head_accounts': head_accounts,
                'table_acntchildren': table_acntchildren,
                'voucher_entries': Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='P', user=self.request.user),
                'user_id': request.user.id,
            })




    








        
    
class SearchPaymentView(LoginRequiredMixin, View):
    template_name = 'web/accounts/payment/payment_modify.html'

    def get(self, request, *args, **kwargs):
        vouchers = VoucherConfiguration.objects.filter(category='payment', user=self.request.user)
        return render(request, self.template_name, {'vouchers': vouchers})
    

# class ModifyPaymentTableView(TemplateView):
#     template_name = 'web/accounts/payment/payment_modify.html'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['series_options'] = VoucherConfiguration.objects.filter(category='payment').values('series')
#         return context

#     def post(self, request, *args, **kwargs):
#         series = request.POST.get('series')
#         voucher_no = request.POST.get('voucher_no')  # Change from serial_no to VoucherNo

#         if series and voucher_no:
#             # Check if the voucher number exists
#             if Table_Voucher.objects.filter(Series=series, VoucherNo=voucher_no, CStatus='P').exists():
#                 return redirect(reverse('web:account_debit_note', kwargs={'series': series, 'voucher_no': voucher_no}))
#             else:
#                 context = self.get_context_data(**kwargs)
#                 context['error'] = 'This voucher number does not exist or does not match the criteria.'
#                 return render(request, self.template_name, context)
        
#         context = self.get_context_data(**kwargs)
#         context['error'] = 'Please enter both series and voucher number.'
#         return render(request, self.template_name, context)


class PaymentListTable(LoginRequiredMixin, ListView):
    model = Table_Voucher
    template_name = 'web/accounts/payment/payment_list.html'
    context_object_name = "vouchers"

    def get_queryset(self):
        # Get all series related to the payment category from VoucherConfiguration
        payment_series = VoucherConfiguration.objects.filter(category='payment', user=self.request.user).values_list('series', flat=True)
        
        # Filter Table_Voucher based on the series related to the payment category and CStatus being 'R'
        return Table_Voucher.objects.filter(Series__in=payment_series, CStatus='P', user=self.request.user)


# - Journal Entry

from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Table_Journal_Entry, Table_Accountsmaster, VoucherConfiguration, Table_companyDetailschild
from decimal import Decimal

class JournalEntryView(View):
    template_name = 'web/accounts/journal-entry/journal-entry.html'

    def get(self, request, *args, **kwargs):
        vouchers = VoucherConfiguration.objects.filter(category='Journal Entry', user=self.request.user)
        accountmas = Table_Accountsmaster.objects.filter(category__in=['Bank', 'Cashbook'], user=self.request.user)
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Bank', 'Cashbook']).filter(user=self.request.user)

        next_serial_numbers = {}
        for voucher in vouchers:
            last_serial = Table_Journal_Entry.objects.filter(series=voucher.series, auth_user=self.request.user).order_by('-voucher_no').first()
            next_serial_numbers[voucher.series] = str(int(last_serial.voucher_no) + 1) if last_serial else voucher.serial_no

        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': accountmas,
            'head_accounts': head_accounts,
            'next_serial_numbers': next_serial_numbers,
            'user_id': request.user.id,
        })

    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('series')
            voucher_no = request.POST.get('voucher_no')
            vdate = request.POST.get('vdate')
            user_id = request.user.id
            branch_id = '1'
            heads = request.POST.getlist('head')
            head_codes = request.POST.getlist('head_code')
            narrations = request.POST.getlist('narration[]')
            debit = request.POST.getlist('dramount[]')
            credit = request.POST.getlist('cramount[]')

            if not (len(heads) == len(narrations) == len(debit) == len(credit) == len(head_codes)):
                raise ValueError("Mismatched input lengths in form data.")

            total_amount = sum(float(amount) for amount in debit if amount)

            company_details = Table_companyDetailschild.objects.first()
            coid = company_details.company_id if company_details else ''
            fycode = company_details.fycode if company_details else ''

            with transaction.atomic():
                # Fetch existing entries and compute old debit and credit totals
                existing_entries = Table_Journal_Entry.objects.filter(series=series, voucher_no=voucher_no, auth_user=self.request.user)
                old_account_updates = {}
                for entry in existing_entries:
                    if entry.accountcode not in old_account_updates:
                        old_account_updates[entry.accountcode] = Decimal('0')
                    old_account_updates[entry.accountcode] += (Decimal(entry.dramount) - Decimal(entry.cramount))

                # Delete existing entries
                existing_entries.delete()

                # Create new entries
                for head, head_code, narration, debit_amount, credit_amount in zip(heads, head_codes, narrations, debit, credit):
                    if not head_code or not head_code.isdigit():  # Skip if head_code is empty or not a number
                        continue

                    Table_Journal_Entry.objects.create(
                        auth_user=self.request.user,
                        series=series,
                        voucher_no=voucher_no,
                        vdate=vdate,
                        accountcode=head_code,
                        narration=narration,
                        dramount=float(debit_amount) if debit_amount else 0,
                        cramount=float(credit_amount) if credit_amount else 0,
                        user_id=user_id,
                        fycode=fycode,
                        coid=coid,
                        brid=branch_id
                    )

                # Compute new debit and credit totals
                new_account_updates = {}
                for head, head_code, debit_amount, credit_amount in zip(heads, head_codes, debit, credit):
                    if not head_code or not head_code.isdigit():  # Skip if head_code is empty or not a number
                        continue

                    if debit_amount:
                        if head_code not in new_account_updates:
                            new_account_updates[head_code] = Decimal('0')
                        new_account_updates[head_code] += Decimal(debit_amount)
                    if credit_amount:
                        if head_code not in new_account_updates:
                            new_account_updates[head_code] = Decimal('0')
                        new_account_updates[head_code] -= Decimal(credit_amount)

                # Update account balances
                accounts_to_update = []
                for head_code, new_amount in new_account_updates.items():
                    try:
                        account = Table_Accountsmaster.objects.get(account_code=head_code, user=self.request.user)
                        old_amount = old_account_updates.get(head_code, Decimal('0'))
                        account.currentbalance = (Decimal(account.currentbalance or '0') - old_amount + new_amount)
                        accounts_to_update.append(account)
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account with code {head_code} does not exist. Skipping update.")

                Table_Accountsmaster.objects.bulk_update(accounts_to_update, ['currentbalance'])

                # Update the voucher configuration with the new serial number if needed
                voucher_no_int = int(voucher_no)
                voucher_config = VoucherConfiguration.objects.get(series=series, category='Journal Entry', user=self.request.user)
                if voucher_no_int > voucher_config.serial_no:
                    voucher_config.serial_no = voucher_no_int
                    voucher_config.save()

            messages.success(request, "Journal saved successfully!")
            return redirect('web:account_journal_entry')
        except Exception as e:
            print("Error saving Journal Entry: ", e)
            messages.error(request, f"Error saving Journal Entry: {str(e)}")
            return self.get(request)




class JournalEntryTable(LoginRequiredMixin, ListView):
    model = Table_Journal_Entry
    template_name = 'web/accounts/journal-entry/journal-entry-table.html'
    context_object_name = "journalentrys"
    
    def get_queryset(self):
        return self.model.objects.filter(auth_user=self.request.user)


class SearchJournalEntryView(LoginRequiredMixin, View):
    template_name = 'web/accounts/journal-entry/search-journal-entry.html'

    def get(self, request, *args, **kwargs):
        series = request.GET.get('Series', '')
        voucher_no = request.GET.get('VoucherNo', '')

        error_message = None
        if not series or not voucher_no:
            error_message = "Please provide both series and voucher number."

        vouchers = VoucherConfiguration.objects.filter(category='Journal Entry', user=self.request.user)
        return render(request, self.template_name, {'vouchers': vouchers, 'error_message': error_message})


class EditJournalEntry(LoginRequiredMixin, View):
    template_name = 'web/accounts/journal-entry/edit-journal-entry.html'

    def get(self, request, *args, **kwargs):
        series = request.GET.get('Series')
        voucher_no = request.GET.get('VoucherNo')

        vouchers = VoucherConfiguration.objects.filter(category='Journal Entry', user=self.request.user)
        accountmas = Table_Accountsmaster.objects.filter(category__in=['Bank', 'Cashbook'], user=self.request.user)
        wallet = Wallet.objects.first()
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Bank', 'Cashbook']).filter(user=self.request.user)
        table_acntchildren = Table_Acntchild.objects.select_related('account_master').filter(
            account_master__category__in=['Bank', 'Cashbook'], account_master__user=self.request.user
        )

        voucher_entries = Table_Journal_Entry.objects.filter(series=series, voucher_no=voucher_no, auth_user=self.request.user)

        if not voucher_entries:
            return redirect('web:search_journal_entry')  # Ensure this matches the name in urls.py

        valid_account_codes = head_accounts.values_list('account_code', flat=True)

        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': accountmas,
            'wallet': wallet,
            'head_accounts': head_accounts,
            'table_acntchildren': table_acntchildren,
            'voucher_entries': voucher_entries,
            'user_id': request.user.id,
            'valid_account_codes': valid_account_codes
        })

    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('series')
            vdate = request.POST.get('vdate')
            voucher_no = request.POST.get('voucher_no')
            if not voucher_no:
                raise ValueError("Voucher number is required.")
            user_id = request.user.id

            company_details = Table_companyDetailschild.objects.first()
            if not company_details:
                raise ValueError("Company details not found.")

            fycode = company_details.fycode
            coid = company_details.company_id  # Assuming `company_id` is the ID for coid
            branch_id = '1'  # Adjust as needed

            heads = request.POST.getlist('head')
            narrations = request.POST.getlist('narration[]')
            debit = request.POST.getlist('dramount[]')
            credit = request.POST.getlist('cramount[]')

            if not (len(heads) == len(narrations) == len(debit) == len(credit)):
                raise ValueError("Mismatched input lengths in form data.")

            # Convert to Decimal for consistency
            debit = [Decimal(d) if d else Decimal('0') for d in debit]
            credit = [Decimal(c) if c else Decimal('0') for c in credit]

            total_amount = sum(debit)

            voucher_config = VoucherConfiguration.objects.get(series=series, category='Journal Entry', user=self.request.user)

            with transaction.atomic():
                # Fetch existing entries and compute old debit and credit totals
                existing_entries = Table_Journal_Entry.objects.filter(series=series, voucher_no=voucher_no, auth_user=self.request.user)
                old_account_updates = {}
                for entry in existing_entries:
                    if entry.accountcode not in old_account_updates:
                        old_account_updates[entry.accountcode] = Decimal('0')
                    old_account_updates[entry.accountcode] += (Decimal(entry.dramount) - Decimal(entry.cramount))

                # Delete existing entries
                existing_entries.delete()

                # Create new entries
                for head, narration, debit_amount, credit_amount in zip(heads, narrations, debit, credit):
                    Table_Journal_Entry.objects.create(
                        auth_user=self.request.user,
                        series=series,
                        voucher_no=voucher_no,
                        vdate=vdate,
                        accountcode=head,
                        narration=narration,
                        dramount=debit_amount,
                        cramount=credit_amount,
                        user_id=user_id,
                        fycode=fycode,
                        coid=coid,
                        brid=branch_id
                    )

                # Compute new debit and credit totals
                new_account_updates = {}
                for head, debit_amount, credit_amount in zip(heads, debit, credit):
                    if debit_amount:
                        if head not in new_account_updates:
                            new_account_updates[head] = Decimal('0')
                        new_account_updates[head] += debit_amount
                    if credit_amount:
                        if head not in new_account_updates:
                            new_account_updates[head] = Decimal('0')
                        new_account_updates[head] -= credit_amount

                # Update account balances
                accounts_to_update = []
                for head_code, new_amount in new_account_updates.items():
                    try:
                        account = Table_Accountsmaster.objects.get(account_code=head_code, user=self.request.user)
                        old_amount = old_account_updates.get(head_code, Decimal('0'))
                        account.currentbalance = (Decimal(account.currentbalance or '0') - old_amount + new_amount)
                        accounts_to_update.append(account)
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account with code {head_code} does not exist. Skipping update.")

                Table_Accountsmaster.objects.bulk_update(accounts_to_update, ['currentbalance'])

                # Update the voucher configuration with the new serial number if needed
                voucher_no_int = int(voucher_no)
                if voucher_no_int > voucher_config.serial_no:
                    voucher_config.serial_no = voucher_no_int
                    voucher_config.save()

            messages.success(request, "Journal entry updated successfully!")
            return redirect('web:account_journal_entry')
        except Exception as e:
            print("Error updating Journal Entry: ", e)
            messages.error(request, f"Error updating Journal Entry: {str(e)}")
            return self.get(request)


class DeleteJournalEntryView(LoginRequiredMixin, View):
    def delete(self, request, voucher_no, *args, **kwargs):
        try:
            # Fetch the journal entries to be deleted
            entries = Table_Journal_Entry.objects.filter(voucher_no=voucher_no, auth_user=self.request.user)
            
            if entries.exists():
                # Compute the totals to be removed
                debit_totals = {}
                credit_totals = {}
                
                for entry in entries:
                    account_code = entry.accountcode
                    debit_amount = Decimal(entry.dramount)
                    credit_amount = Decimal(entry.cramount)
                    
                    if account_code not in debit_totals:
                        debit_totals[account_code] = Decimal('0')
                        credit_totals[account_code] = Decimal('0')
                    
                    debit_totals[account_code] += debit_amount
                    credit_totals[account_code] += credit_amount

                # Delete the entries
                entries.delete()

                # Update the balances
                accounts_to_update = []
                for account_code in debit_totals.keys():
                    try:
                        account = Table_Accountsmaster.objects.get(account_code=account_code, user=self.request.user)
                        old_balance = Decimal(account.currentbalance or '0')
                        debit_total = debit_totals.get(account_code, Decimal('0'))
                        credit_total = credit_totals.get(account_code, Decimal('0'))
                        new_balance = old_balance - debit_total + credit_total
                        account.currentbalance = new_balance
                        accounts_to_update.append(account)
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account with code {account_code} does not exist. Skipping update.")

                Table_Accountsmaster.objects.bulk_update(accounts_to_update, ['currentbalance'])

                return JsonResponse({'success': True})
            return JsonResponse({'success': False})
        except Exception as e:
            print("Error deleting Journal Entry: ", e)
            return JsonResponse({'success': False, 'error': str(e)})



# CONTRA ENTRY

from decimal import Decimal
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import VoucherConfiguration, Table_Accountsmaster, Wallet, Table_Contra_Entry, Table_Acntchild, Table_companyDetailschild

from decimal import Decimal
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import VoucherConfiguration, Table_Accountsmaster, Wallet, Table_Contra_Entry, Table_Acntchild, Table_companyDetailschild

class ContraEntryView(View):
    template_name = 'web/accounts/contra-entry/contra_entry.html'

    def get(self, request, *args, **kwargs):
        vouchers = VoucherConfiguration.objects.filter(category='Contra Entry', user=self.request.user)
        accountmas = Table_Accountsmaster.objects.filter(category__in=['Accounts', 'Customers', 'Suppliers'], user=self.request.user)
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Accounts', 'Customers', 'Suppliers']).filter(user=self.request.user)
        wallet = Wallet.objects.first()

        next_serial_numbers = {}
        for voucher in vouchers:
            last_serial = Table_Contra_Entry.objects.filter(series=voucher.series, auth_user=self.request.user,).order_by('-voucher_no').first()
            next_serial_numbers[voucher.series] = str(int(last_serial.voucher_no) + 1) if last_serial else voucher.serial_no

        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': accountmas,
            'head_accounts': head_accounts,
            'next_serial_numbers': next_serial_numbers,
            'user_id': request.user.id,
        })

    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('series')
            voucher_no = request.POST.get('voucher_no')
            vdate = request.POST.get('vdate')
            user_id = request.user.id
            branch_id = '1'
            heads = request.POST.getlist('head')
            head_codes = request.POST.getlist('head_code')
            narrations = request.POST.getlist('narration[]')
            debit = request.POST.getlist('dramount[]')
            credit = request.POST.getlist('cramount[]')
    
            if not (len(heads) == len(narrations) == len(debit) == len(credit) == len(head_codes)):
                raise ValueError("Mismatched input lengths in form data.")
    
            total_debit = sum(float(d) for d in debit if d)
            total_credit = sum(float(c) for c in credit if c)
    
            company_details = Table_companyDetailschild.objects.first()
            coid = company_details.company_id if company_details else ''
            fycode = company_details.fycode if company_details else ''
    
            with transaction.atomic():
                entries = []
                for head, head_code, narration, debit_amount, credit_amount in zip(heads, head_codes, narrations, debit, credit):
                    entries.append(
                        Table_Contra_Entry(
                            auth_user=self.request.user,
                            series=series,
                            voucher_no=voucher_no,
                            vdate=vdate,
                            accountcode=head_code,
                            narration=narration,
                            dramount=float(debit_amount) if debit_amount else 0,
                            cramount=float(credit_amount) if credit_amount else 0,
                            user_id=user_id,
                            fycode=fycode,
                            coid=coid,
                            brid=branch_id
                        )
                    )
                Table_Contra_Entry.objects.bulk_create(entries)
    
                account_updates = {}
                for head_code, debit_amount, credit_amount in zip(head_codes, debit, credit):
                    if debit_amount:
                        if head_code not in account_updates:
                            account_updates[head_code] = 0
                        account_updates[head_code] += float(debit_amount)
                    if credit_amount:
                        if head_code not in account_updates:
                            account_updates[head_code] = 0
                        account_updates[head_code] -= float(credit_amount)
                
                accounts_to_update = []
                for head_code, amount in account_updates.items():
                    try:
                        account = Table_Accountsmaster.objects.get(account_code=head_code, user=self.request.user)
                        account.currentbalance = (float(account.currentbalance or 0) + amount)
                        accounts_to_update.append(account)
                    except Table_Accountsmaster.DoesNotExist:
                        pass
                Table_Accountsmaster.objects.bulk_update(accounts_to_update, ['currentbalance'])
    
                voucher_configs = VoucherConfiguration.objects.filter(series=series, category='Contra Entry', user=self.request.user)
                for voucher_config in voucher_configs:
                    voucher_config.serial_no = voucher_no
                    voucher_config.save()
    
            messages.success(request, "Contra saved successfully!")
            return redirect('web:account_contra_entry')
        except Exception as e:
            print("Error saving contra entry: ", e)
            messages.error(request, f"Error saving contra entry: {str(e)}")
            return self.get(request)
    


    




class ContraEntryTable(LoginRequiredMixin, ListView):
    model = Table_Contra_Entry
    template_name = 'web/accounts/contra-entry/contra-entry-table.html'
    context_object_name = "contraentrys"

    def get_queryset(self):
        return self.model.objects.filter(auth_user=self.request.user)


class SearchContraEntryView(LoginRequiredMixin, View):
    template_name = 'web/accounts/contra-entry/search-contra-entry.html'

    def get(self, request, *args, **kwargs):
        series = request.GET.get('Series', '')
        voucher_no = request.GET.get('VoucherNo', '')

        error_message = None
        if not series or not voucher_no:
            error_message = "Please provide both series and voucher number."

        vouchers = VoucherConfiguration.objects.filter(category='Contra Entry', user=self.request.user)
        return render(request, self.template_name, {'vouchers': vouchers, 'error_message': error_message})


from django.shortcuts import redirect, render
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from decimal import Decimal

class EditContraEntry(LoginRequiredMixin, View):
    template_name = 'web/accounts/contra-entry/edit-contra-entry.html'

    def get(self, request, *args, **kwargs):
        series = request.GET.get('Series')
        voucher_no = request.GET.get('VoucherNo')

        vouchers = VoucherConfiguration.objects.filter(category='Contra Entry', user=self.request.user)
        accountmas = Table_Accountsmaster.objects.filter(category__in=['Accounts', 'Customers', 'Suppliers'], user=self.request.user)
        head_accounts = Table_Accountsmaster.objects.exclude(category__in=['Accounts', 'Customers', 'Suppliers']).filter(user=self.request.user)
        table_acntchildren = Table_Acntchild.objects.filter(account_master__category__in=['Accounts', 'Customers', 'Suppliers'], account_master__user=self.request.user)

        voucher_entries = Table_Contra_Entry.objects.filter(series=series, voucher_no=voucher_no,  auth_user=self.request.user)

        if not voucher_entries:
            return redirect('web:search_contra_entry')

        valid_account_codes = head_accounts.values_list('account_code', flat=True)

        return render(request, self.template_name, {
            'vouchers': vouchers,
            'accountmas': accountmas,
            'head_accounts': head_accounts,
            'table_acntchildren': table_acntchildren,
            'voucher_entries': voucher_entries,
            'user_id': request.user.id,
            'valid_account_codes': valid_account_codes
        })


    def post(self, request, *args, **kwargs):
        try:
            series = request.POST.get('series')
            vdate = request.POST.get('vdate')
            voucher_no = request.POST.get('voucher_no')
            if not voucher_no:
                raise ValueError("Voucher number is required.")
            user_id = request.user.id

            company_details = Table_companyDetailschild.objects.first()
            if not company_details:
                raise ValueError("Company details not found.")

            fycode = company_details.fycode
            coid = company_details.company_id
            branch_id = '1'

            heads = request.POST.getlist('head')
            narrations = request.POST.getlist('narration[]')
            debit = request.POST.getlist('dramount[]')
            credit = request.POST.getlist('cramount[]')

            if not (len(heads) == len(narrations) == len(debit) == len(credit)):
                raise ValueError("Mismatched input lengths in form data.")

            # Convert to Decimal for consistency
            debit = [Decimal(d) if d else Decimal('0') for d in debit]
            credit = [Decimal(c) if c else Decimal('0') for c in credit]

            total_debit = sum(debit)
            total_credit = sum(credit)

            voucher_config = VoucherConfiguration.objects.get(series=series, category='Contra Entry', user=self.request.user)

            with transaction.atomic():
                # Fetch existing entries and compute old debit and credit totals
                existing_entries = Table_Contra_Entry.objects.filter(series=series, voucher_no=voucher_no, auth_user=self.request.user,)
                old_account_updates = {}
                for entry in existing_entries:
                    if entry.accountcode not in old_account_updates:
                        old_account_updates[entry.accountcode] = Decimal('0')
                    old_account_updates[entry.accountcode] += (Decimal(entry.dramount) - Decimal(entry.cramount))

                # Delete existing entries
                existing_entries.delete()

                # Create new entries
                for head, narration, debit_amount, credit_amount in zip(heads, narrations, debit, credit):
                    Table_Contra_Entry.objects.create(
                        auth_user=self.request.user,
                        series=series,
                        voucher_no=voucher_no,
                        vdate=vdate,
                        accountcode=head,
                        narration=narration,
                        dramount=debit_amount,
                        cramount=credit_amount,
                        user_id=user_id,
                        fycode=fycode,
                        coid=coid,
                        brid=branch_id
                    )

                # Compute new debit and credit totals
                new_account_updates = {}
                for head, debit_amount, credit_amount in zip(heads, debit, credit):
                    if debit_amount:
                        if head not in new_account_updates:
                            new_account_updates[head] = Decimal('0')
                        new_account_updates[head] += debit_amount
                    if credit_amount:
                        if head not in new_account_updates:
                            new_account_updates[head] = Decimal('0')
                        new_account_updates[head] -= credit_amount

                # Update account balances
                accounts_to_update = []
                for head_code, new_amount in new_account_updates.items():
                    try:
                        account = Table_Accountsmaster.objects.get(account_code=head_code, user=self.request.user)
                        # Adjust the balance by subtracting old amounts and adding new amounts
                        old_amount = old_account_updates.get(head_code, Decimal('0'))
                        account.currentbalance = (Decimal(account.currentbalance or '0') - old_amount + new_amount)
                        accounts_to_update.append(account)
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account with code {head_code} does not exist. Skipping update.")

                Table_Accountsmaster.objects.bulk_update(accounts_to_update, ['currentbalance'])

                # Update the voucher configuration with the new serial number if needed
                voucher_no_int = int(voucher_no)
                if voucher_no_int > voucher_config.serial_no:
                    voucher_config.serial_no = voucher_no_int
                    voucher_config.save()

            messages.success(request, "Contra updated successfully!")
            return redirect('web:account_contra_entry')
        except Exception as e:
            print("Error saving contra entry: ", e)
            messages.error(request, f"Error saving contra entry: {str(e)}")
            return self.get(request, error=str(e))





from django.http import JsonResponse
from django.db import transaction
from decimal import Decimal

class DeleteContraEntryView(LoginRequiredMixin, View):
    def delete(self, request, voucher_no, *args, **kwargs):
        try:
            with transaction.atomic():
                # Retrieve contra entries to delete
                contra_entries = Table_Contra_Entry.objects.filter(voucher_no=voucher_no, auth_user=self.request.user)
                
                if not contra_entries.exists():
                    return JsonResponse({'success': False, 'message': 'No entries found.'})
                
                # Prepare to accumulate amounts to adjust account balances
                account_updates = {}
                for entry in contra_entries:
                    head_code = entry.accountcode
                    dr_amount = Decimal(entry.dramount) if entry.dramount else Decimal('0')
                    cr_amount = Decimal(entry.cramount) if entry.cramount else Decimal('0')
                    
                    if head_code not in account_updates:
                        account_updates[head_code] = Decimal('0')
                    # Subtract the debit amount and add the credit amount
                    account_updates[head_code] -= dr_amount
                    account_updates[head_code] += cr_amount
                
                # Delete the contra entries
                contra_entries.delete()

                # Update the current balance for affected accounts
                accounts_to_update = []
                for head_code, amount_change in account_updates.items():
                    try:
                        account = Table_Accountsmaster.objects.get(account_code=head_code, user=self.request.user)
                        account.currentbalance = Decimal(account.currentbalance or '0') + amount_change
                        accounts_to_update.append(account)
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Account with code {head_code} does not exist. Skipping update.")
                
                if accounts_to_update:
                    Table_Accountsmaster.objects.bulk_update(accounts_to_update, ['currentbalance'])

                return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error deleting contra entry: {e}")
            return JsonResponse({'success': False, 'message': str(e)})








class LedgerSearchView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/ledger/ledger_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the first (or specific) company details record for finyearfrom
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context["finyearfrom"] = company_details.finyearfrom
        context["head_accounts"] = Table_Accountsmaster.objects.filter(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        account_code = request.POST.get("Accountcode")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        
        if not account_code:
            messages.error(request, "No account head selected. Please select an account head.")
            return self.get(request, *args, **kwargs)  # Return to the form page with error message

        # If everything is valid, redirect to the ledger page
        return HttpResponseRedirect(
            reverse(
                "web:ledger",
                kwargs={
                    "account_code": account_code,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )





class LedgerView(LoginRequiredMixin, View):
    def get(self, request, account_code, start_date, end_date):
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        # Fetch account details
        account_master = Table_Accountsmaster.objects.filter(account_code=account_code, user=self.request.user).first()

        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()  # Assuming there's only one record

        # Initialize opening balance variables
        opening_balance = Decimal("0.00")
        
        # Fetch all entries prior to start_date to calculate opening balance
        previous_entries = (
            list(Table_Voucher.objects.filter(Accountcode=account_code, Vdate__lt=start_date)) +
            list(Table_DrCrNote.objects.filter(accountcode=account_code, ndate__lt=start_date)) +
            list(Table_Journal_Entry.objects.filter(accountcode=account_code, vdate__lt=start_date)) +
            list(Table_Contra_Entry.objects.filter(accountcode=account_code, vdate__lt=start_date))
        )

        # Calculate the opening balance based on previous entries
        if previous_entries:
            for entry in previous_entries:
                if hasattr(entry, "Vdate"):
                    if entry.CStatus == "P":
                        opening_balance += Decimal(entry.VAmount or "0.00")
                    elif entry.CStatus == "R":
                        opening_balance -= Decimal(entry.VAmount or "0.00")
                elif hasattr(entry, "ndate"):
                    if entry.ntype == 'C':  # Credit Note
                        opening_balance += Decimal(entry.cramount or "0.00")
                        opening_balance -= Decimal(entry.dramount or "0.00")
                    else:
                        opening_balance += Decimal(entry.dramount or "0.00")
                        opening_balance -= Decimal(entry.cramount or "0.00")
                elif isinstance(entry, Table_Journal_Entry):
                    opening_balance += Decimal(entry.dramount or "0.00")
                    opening_balance -= Decimal(entry.cramount or "0.00")
                elif isinstance(entry, Table_Contra_Entry):
                    opening_balance += Decimal(entry.dramount or "0.00")
                    opening_balance -= Decimal(entry.cramount or "0.00")

        # If no previous entries, use the initial opening balance from the account master
        if opening_balance == Decimal("0.00"):
            opening_balance = Decimal(account_master.opbalance)

        # Initialize opening balance debit and credit
        opening_balance_debit = Decimal("0.00")
        opening_balance_credit = Decimal("0.00")

        # Determine if the opening balance should be in Debit or Credit based on 'debitcredit' in account master
        if account_master.debitcredit == "debit":
            opening_balance_debit = max(opening_balance, Decimal("0.00"))  # Opening balance goes in debit column
        elif account_master.debitcredit == "credit":
            opening_balance_credit = abs(opening_balance)  # Opening balance goes in credit column
        else:
            opening_balance_debit = max(opening_balance, Decimal("0.00"))
            opening_balance_credit = -min(opening_balance, Decimal("0.00"))

        # Fetch entries within date range
        voucher_entries = Table_Voucher.objects.filter(
            Accountcode=account_code, Vdate__range=[start_date, end_date], user=self.request.user
        )

        drcr_entries = Table_DrCrNote.objects.filter(
            accountcode=account_code, ndate__range=[start_date, end_date], user=self.request.user
        )

        journal_entries = Table_Journal_Entry.objects.filter(
            accountcode=account_code, vdate__range=[start_date, end_date], auth_user=self.request.user
        )

        contra_entries = Table_Contra_Entry.objects.filter(
            accountcode=account_code, vdate__range=[start_date, end_date], auth_user=self.request.user
        )

        # Combine and sort entries by date
        combined_entries = sorted(
            list(voucher_entries) +
            list(drcr_entries) +
            list(journal_entries) +
            list(contra_entries),
            key=lambda x: (
                getattr(x, 'Vdate', None) or getattr(x, 'ndate', None) or getattr(x, 'vdate', None)
            )
        )

        total_debit = opening_balance_debit
        total_credit = opening_balance_credit
        closing_balance = opening_balance  # Start with the opening balance

        entry_list = []

        for entry in combined_entries:
            entry_dict = {}

            if hasattr(entry, "Vdate"):  # Table_Voucher entry
                debit_amount = (
                    Decimal(entry.VAmount or "0.00")
                    if entry.CStatus == "P"
                    else Decimal("0.00")
                )
                credit_amount = (
                    Decimal(entry.VAmount or "0.00")
                    if entry.CStatus == "R"
                    else Decimal("0.00")
                )
                entry_dict = {
                    "date": entry.Vdate,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "status": entry.CStatus,
                    "debit": debit_amount,
                    "credit": credit_amount,
                }

            elif hasattr(entry, "ndate"):  # Table_DrCrNote entry
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                if entry.ntype == 'C':  # Credit Note
                    debit_amount, credit_amount = credit_amount, debit_amount
                entry_dict = {
                    "date": entry.ndate,
                    "voucher_number": entry.noteno or entry.series,
                    "narration": entry.narration,
                    "type": entry.ntype,
                    "debit": debit_amount,
                    "credit": credit_amount,
                }

            elif isinstance(entry, Table_Journal_Entry):  # Table_Journal_Entry
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                entry_dict = {
                    "date": entry.vdate,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "is_journal_entry": True,  # Flag for journal entry
                }

            elif isinstance(entry, Table_Contra_Entry):  # Table_Contra_Entry
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                entry_dict = {
                    "date": entry.vdate,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "is_contra_entry": True,  # Flag for contra entry
                }

            # Update the running balance
            closing_balance += entry_dict.get("debit", Decimal("0.00"))
            closing_balance -= entry_dict.get("credit", Decimal("0.00"))

            # Add closing balance to the entry dictionary
            entry_dict["closing_balance"] = closing_balance

            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))

            entry_list.append(entry_dict)

        # Final closing balance at the end of the entries (Balance c/d)
        balance_cd = closing_balance

        context = {
            "account_master": account_master,
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance_cd": balance_cd,  # Final closing balance (carry down)
            "opening_balance": opening_balance,  # Starting opening balance
            "opening_balance_debit": opening_balance_debit,  # For display
            "opening_balance_credit": opening_balance_credit,  # For display
            "start_date": start_date,
            "end_date": end_date,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
        }

        return render(request, "web/accounts/ledger/ledger.html", context)




class CashBookSearchView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/cash-book/cashbook_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the first (or specific) company details record for finyearfrom
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context["finyearfrom"] = company_details.finyearfrom

        # Filter head accounts with category 'Cashbook'
        context["head_accounts"] = Table_Accountsmaster.objects.filter(category='Cashbook', user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        account_code = request.POST.get("Accountcode")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        
        if not account_code:
            messages.error(request, "No account head selected. Please select an account head.")
            return self.get(request, *args, **kwargs)  # Return to the form page with error message

        # If everything is valid, redirect to the ledger page
        return HttpResponseRedirect(
            reverse(
                "web:cashbook",
                kwargs={
                    "account_code": account_code,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )



from django.db.models import Q
class CashBookView(LoginRequiredMixin, View):
    def get(self, request, account_code, start_date, end_date):
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        # Fetch account details
        account_master = Table_Accountsmaster.objects.get(account_code=account_code, user=self.request.user)
        
        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()  # Assuming there's only one record

        # Convert initial balance to Decimal if it is not already
        opbalance = Decimal(account_master.opbalance)

        # Function to get last closing balance
        def get_last_closing_balance():
            entries = (
                list(Table_Voucher.objects.filter(Accountcode=account_code, Vdate__lt=start_date, user=self.request.user)) +
                list(Table_DrCrNote.objects.filter(accountcode=account_code, ndate__lt=start_date, user=self.request.user)) +
                list(Table_Journal_Entry.objects.filter(accountcode=account_code, vdate__lt=start_date, auth_user=self.request.user)) +
                list(Table_Contra_Entry.objects.filter(accountcode=account_code, vdate__lt=start_date, auth_user=self.request.user))
            )
            entries.sort(key=lambda x: (
                getattr(x, 'Vdate', None) or getattr(x, 'ndate', None) or datetime.min.date()
            ))

            last_closing_balance = opbalance
            for entry in entries:
                # Logic for each entry type
                if hasattr(entry, "Vdate"):
                    if entry.CStatus == "P":
                        last_closing_balance += Decimal(entry.payment or "0.00")  # Using payment
                    elif entry.CStatus == "R":
                        last_closing_balance -= Decimal(entry.payment or "0.00")  # Using payment
                elif hasattr(entry, "ndate"):
                    if entry.ntype == 'C':
                        last_closing_balance += Decimal(entry.cramount or "0.00")
                        last_closing_balance -= Decimal(entry.dramount or "0.00")
                    else:
                        last_closing_balance += Decimal(entry.dramount or "0.00")
                        last_closing_balance -= Decimal(entry.cramount or "0.00")
                elif isinstance(entry, Table_Journal_Entry):
                    last_closing_balance += Decimal(entry.dramount or "0.00")
                    last_closing_balance -= Decimal(entry.cramount or "0.00")
                elif isinstance(entry, Table_Contra_Entry):
                    last_closing_balance += Decimal(entry.dramount or "0.00")
                    last_closing_balance -= Decimal(entry.cramount or "0.00")

            return last_closing_balance

        opening_balance = get_last_closing_balance()

        # Updated query to filter by Accountcode or Headcode
        voucher_entries = Table_Voucher.objects.filter(
            Q(Accountcode=account_code) | Q(Headcode=account_code),
            Vdate__range=[start_date, end_date],
            user=self.request.user
        ).order_by("Vdate")

        # Fetch other entries as usual
        drcr_entries = Table_DrCrNote.objects.filter(
            accountcode=account_code, ndate__range=[start_date, end_date], user=self.request.user
        ).order_by("ndate")

        journal_entries = Table_Journal_Entry.objects.filter(
            accountcode=account_code, vdate__range=[start_date, end_date], auth_user=self.request.user
        ).order_by("vdate")

        contra_entries = Table_Contra_Entry.objects.filter(
            accountcode=account_code, vdate__range=[start_date, end_date], auth_user=self.request.user
        ).order_by("vdate")

        # Combine and sort entries as before
        combined_entries = (
            list(voucher_entries) +
            list(drcr_entries) +
            list(journal_entries) +
            list(contra_entries)
        )

        # Sort entries based on date for all types
        combined_entries.sort(
            key=lambda x: (
                getattr(x, 'Vdate', None) or
                getattr(x, 'ndate', None) or
                (getattr(x, 'vdate', None) if hasattr(x, 'vdate') else None) or
                datetime.date.min
            )
        )

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        closing_balance = opening_balance  # Start with the opening balance

        entry_list = []

        for entry in combined_entries:
            entry_dict = {}
            head = ""

            # Process each entry type
            if hasattr(entry, "Vdate"):  # Table_Voucher entry
                head = Table_Accountsmaster.objects.get(account_code=entry.Accountcode, user=self.request.user).head  # Get head using Accountcode instead of Headcode
                debit_amount = Decimal(entry.payment or "0.00") if entry.CStatus == "P" else Decimal("0.00")
                credit_amount = Decimal(entry.payment or "0.00") if entry.CStatus == "R" else Decimal("0.00")
                entry_dict = {
                    "date": entry.Vdate,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "status": entry.CStatus,
                    "debit": credit_amount,
                    "credit": debit_amount,
                    "head": head,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            elif hasattr(entry, "ndate"):  # Table_DrCrNote entry
                head = Table_Accountsmaster.objects.get(account_code=entry.accountcode, user=self.request.user).head
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                if entry.ntype == 'C':  # Assuming 'C' stands for Credit Note
                    debit_amount, credit_amount = credit_amount, debit_amount
                entry_dict = {
                    "date": entry.ndate,
                    "voucher_number": entry.noteno or entry.series,
                    "narration": entry.narration,
                    "type": entry.ntype,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "head": head,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Journal_Entry):  # Table_Journal_Entry
                head = Table_Accountsmaster.objects.get(account_code=entry.accountcode, user=self.request.user).head
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                entry_dict = {
                    "date": entry.vdate,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "head": head,
                    "is_journal_entry": True,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Contra_Entry):  # Table_Contra_Entry
                head = Table_Accountsmaster.objects.get(account_code=entry.accountcode, user=self.request.user).head
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                entry_dict = {
                    "date": entry.vdate,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "head": head,
                    "is_journal_entry": False,
                    "is_contra_entry": True,
                }

            # Update the running balance
            closing_balance += entry_dict.get("debit", Decimal("0.00"))
            closing_balance -= entry_dict.get("credit", Decimal("0.00"))

            # Add closing balance to the entry dictionary
            entry_dict["closing_balance"] = closing_balance

            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))

            entry_list.append(entry_dict)

        balance_cd = closing_balance  # Final closing balance

        # Determine debit and credit values for the opening balance row
        opening_balance_debit = max(opening_balance, Decimal("0.00"))
        opening_balance_credit = max(-opening_balance, Decimal("0.00"))

        context = {
            "account_master": account_master,
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance_cd": balance_cd,
            "opening_balance": opening_balance,
            "opening_balance_debit": opening_balance_debit,
            "opening_balance_credit": opening_balance_credit,
            "start_date": start_date,
            "end_date": end_date,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
        }

        return render(request, "web/accounts/cash-book/cashbook.html", context)








class BankBookSearchView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/bank-book/bankbook_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the first (or specific) company details record for finyearfrom
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context["finyearfrom"] = company_details.finyearfrom

        # Filter head accounts with category 'Cashbook'
        context["head_accounts"] = Table_Accountsmaster.objects.filter(category='Bank', user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        account_code = request.POST.get("Accountcode")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not account_code:
            messages.error(request, "No account head selected. Please select an account head.")
            return self.get(request, *args, **kwargs)  # Return to the form page with error message

        # If everything is valid, redirect to the ledger page
        return HttpResponseRedirect(
            reverse(
                "web:bankbook",
                kwargs={
                    "account_code": account_code,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )


class BankBookView(LoginRequiredMixin, View):
    def get(self, request, account_code, start_date, end_date):
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        # Fetch account details
        account_master = Table_Accountsmaster.objects.get(account_code=account_code, user=self.request.user)
        
        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()  # Assuming there's only one record

        # Convert initial balance to Decimal if it is not already
        opbalance = Decimal(account_master.opbalance)

        # Function to get last closing balance
        def get_last_closing_balance():
            entries = (
                list(Table_Voucher.objects.filter(Accountcode=account_code, Vdate__lt=start_date, user=self.request.user)) +
                list(Table_DrCrNote.objects.filter(accountcode=account_code, ndate__lt=start_date, user=self.request.user)) +
                list(Table_Journal_Entry.objects.filter(accountcode=account_code, vdate__lt=start_date, auth_user=self.request.user)) +
                list(Table_Contra_Entry.objects.filter(accountcode=account_code, vdate__lt=start_date, auth_user=self.request.user))
            )
            entries.sort(key=lambda x: (
                getattr(x, 'Vdate', None) or getattr(x, 'ndate', None) or datetime.min.date()
            ))

            last_closing_balance = opbalance
            for entry in entries:
                # Logic for each entry type
                if hasattr(entry, "Vdate"):
                    if entry.CStatus == "P":
                        last_closing_balance += Decimal(entry.payment or "0.00")  # Using payment
                    elif entry.CStatus == "R":
                        last_closing_balance -= Decimal(entry.payment or "0.00")  # Using payment
                elif hasattr(entry, "ndate"):
                    if entry.ntype == 'C':
                        last_closing_balance += Decimal(entry.cramount or "0.00")
                        last_closing_balance -= Decimal(entry.dramount or "0.00")
                    else:
                        last_closing_balance += Decimal(entry.dramount or "0.00")
                        last_closing_balance -= Decimal(entry.cramount or "0.00")
                elif isinstance(entry, Table_Journal_Entry):
                    last_closing_balance += Decimal(entry.dramount or "0.00")
                    last_closing_balance -= Decimal(entry.cramount or "0.00")
                elif isinstance(entry, Table_Contra_Entry):
                    last_closing_balance += Decimal(entry.dramount or "0.00")
                    last_closing_balance -= Decimal(entry.cramount or "0.00")

            return last_closing_balance

        opening_balance = get_last_closing_balance()

        # Updated query to filter by Accountcode or Headcode
        voucher_entries = Table_Voucher.objects.filter(
            Q(Accountcode=account_code) | Q(Headcode=account_code),
            Vdate__range=[start_date, end_date], user=self.request.user
        ).order_by("Vdate")

        # Fetch other entries as usual
        drcr_entries = Table_DrCrNote.objects.filter(
            accountcode=account_code, ndate__range=[start_date, end_date], user=self.request.user
        ).order_by("ndate")

        journal_entries = Table_Journal_Entry.objects.filter(
            accountcode=account_code, vdate__range=[start_date, end_date], auth_user=self.request.user
        ).order_by("vdate")

        contra_entries = Table_Contra_Entry.objects.filter(
            accountcode=account_code, vdate__range=[start_date, end_date], auth_user=self.request.user
        ).order_by("vdate")

        # Combine and sort entries as before
        combined_entries = (
            list(voucher_entries) +
            list(drcr_entries) +
            list(journal_entries) +
            list(contra_entries)
        )

        # Sort entries based on date for all types
        combined_entries.sort(
            key=lambda x: (
                getattr(x, 'Vdate', None) or
                getattr(x, 'ndate', None) or
                (getattr(x, 'vdate', None) if hasattr(x, 'vdate') else None) or
                datetime.date.min
            )
        )

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        closing_balance = opening_balance  # Start with the opening balance

        entry_list = []

        for entry in combined_entries:
            entry_dict = {}
            head = ""

            # Process each entry type
            if hasattr(entry, "Vdate"):  # Table_Voucher entry
                head = Table_Accountsmaster.objects.get(account_code=entry.Accountcode, user=self.request.user).head  # Get head using Accountcode instead of Headcode
                debit_amount = Decimal(entry.payment or "0.00") if entry.CStatus == "P" else Decimal("0.00")
                credit_amount = Decimal(entry.payment or "0.00") if entry.CStatus == "R" else Decimal("0.00")
                entry_dict = {
                    "date": entry.Vdate,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "status": entry.CStatus,
                    "debit": credit_amount,
                    "credit": debit_amount,
                    "head": head,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            elif hasattr(entry, "ndate"):  # Table_DrCrNote entry
                head = Table_Accountsmaster.objects.get(account_code=entry.accountcode, user=self.request.user).head
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                if entry.ntype == 'C':  # Assuming 'C' stands for Credit Note
                    debit_amount, credit_amount = credit_amount, debit_amount
                entry_dict = {
                    "date": entry.ndate,
                    "voucher_number": entry.noteno or entry.series,
                    "narration": entry.narration,
                    "type": entry.ntype,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "head": head,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Journal_Entry):  # Table_Journal_Entry
                head = Table_Accountsmaster.objects.get(account_code=entry.accountcode, user=self.request.user).head
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                entry_dict = {
                    "date": entry.vdate,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "head": head,
                    "is_journal_entry": True,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Contra_Entry):  # Table_Contra_Entry
                head = Table_Accountsmaster.objects.get(account_code=entry.accountcode, user=self.request.user).head
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                entry_dict = {
                    "date": entry.vdate,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "head": head,
                    "is_journal_entry": False,
                    "is_contra_entry": True,
                }

            # Update the running balance
            closing_balance += entry_dict.get("debit", Decimal("0.00"))
            closing_balance -= entry_dict.get("credit", Decimal("0.00"))

            # Add closing balance to the entry dictionary
            entry_dict["closing_balance"] = closing_balance

            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))

            entry_list.append(entry_dict)

        balance_cd = closing_balance  # Final closing balance

        # Determine debit and credit values for the opening balance row
        opening_balance_debit = max(opening_balance, Decimal("0.00"))
        opening_balance_credit = max(-opening_balance, Decimal("0.00"))

        context = {
            "account_master": account_master,
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance_cd": balance_cd,
            "opening_balance": opening_balance,
            "opening_balance_debit": opening_balance_debit,
            "opening_balance_credit": opening_balance_credit,
            "start_date": start_date,
            "end_date": end_date,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
        }

        return render(request, "web/accounts/bank-book/bankbook.html", context)



class DayBookSearchView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/day-book/daybook_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context["finyearfrom"] = company_details.finyearfrom
        return context

    def post(self, request, *args, **kwargs):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not start_date or not end_date:
            messages.error(request, "Please select both start and end dates.")
            return self.get(request, *args, **kwargs)

        return HttpResponseRedirect(
            reverse(
                "web:daybook",  # Adjust the URL name as per your URL configuration
                kwargs={
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )


from datetime import date
from django.utils.dateparse import parse_date


class DayBookView(LoginRequiredMixin, View):
    def get(self, request, start_date, end_date):
        # Parse start and end dates
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()

        # Fetch entries within the date range
        voucher_entries = Table_Voucher.objects.filter(Vdate__range=[start_date, end_date], user=self.request.user).order_by("Vdate")
        drcr_entries = Table_DrCrNote.objects.filter(ndate__range=[start_date, end_date], user=self.request.user).order_by("ndate")
        journal_entries = Table_Journal_Entry.objects.filter(vdate__range=[start_date, end_date], auth_user=self.request.user).order_by("vdate")
        contra_entries = Table_Contra_Entry.objects.filter(vdate__range=[start_date, end_date], auth_user=self.request.user).order_by("vdate")

        # Combine and sort all entries by date
        combined_entries = (
            list(voucher_entries) + list(drcr_entries) + list(journal_entries) + list(contra_entries)
        )
        combined_entries.sort(key=lambda x: getattr(x, 'Vdate', getattr(x, 'ndate', getattr(x, 'vdate', date.min))))

        # Process and calculate debit, credit, and balances for display
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        entry_list = []

        # Loop through the entries and process each one
        for entry in combined_entries:
            entry_dict = {}

            if hasattr(entry, "Vdate"):  # Table_Voucher entry
                debit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "P" else Decimal("0.00")
                credit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "R" else Decimal("0.00")
                account = Table_Accountsmaster.objects.filter(account_code=entry.Accountcode, user=self.request.user).first()
                head = account.head if account else "Unknown"
                entry_dict = {
                    "date": entry.Vdate,
                    "head": head,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "type": entry.CStatus,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }
                if entry.Headcode:
                    try:
                        head_account = Table_Accountsmaster.objects.get(account_code=entry.Headcode, user=self.request.user)
                
                        # Append 'Book Head' and current balance row only once
                        if entry.CStatus == 'P':
                            # Add 'Book Head' debit and credit to totals
                            total_debit += Decimal("0.00")  # For 'P' entries, we display in the credit column
                            total_credit += debit_amount  # Accumulate the correct amount for payments
                
                            # Show current balance in the credit column for payment entry
                            entry_list.append({
                                "date": entry.Vdate,
                                "head": head_account.head,
                                "voucher_number": entry.VoucherNo or entry.Series,
                                "narration": "",
                                "debit": Decimal("0.00"),  # No debit for payments
                                "credit": debit_amount,  # Show in credit for payments
                                "type": entry.CStatus,
                                "is_journal_entry": False,
                                "is_contra_entry": False,
                            })
                        elif entry.CStatus == 'R':
                            # Add 'Book Head' debit and credit to totals
                            total_debit += credit_amount  # Accumulate the correct amount for receipts
                            total_credit += Decimal("0.00")  # For 'R' entries, we display in the debit column
                
                            # Show current balance in the debit column for receipt entry
                            entry_list.append({
                                "date": entry.Vdate,
                                "head": head_account.head,
                                "voucher_number": entry.VoucherNo or entry.Series,
                                "narration": "",
                                "debit": credit_amount,  # Show in debit for receipts
                                "credit": Decimal("0.00"),  # No credit for receipts
                                "type": entry.CStatus,
                                "is_journal_entry": False,
                                "is_contra_entry": False,
                            })
                    except Table_Accountsmaster.DoesNotExist:
                        print(f"Headcode {entry.Headcode} not found in Table_Accountsmaster.")



            elif hasattr(entry, "ndate"):  # Table_DrCrNote entry
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                if entry.ntype == 'C':  # Credit Note
                    debit_amount, credit_amount = credit_amount, debit_amount
                account = Table_Accountsmaster.objects.filter(account_code=entry.accountcode, user=self.request.user).first()
                head = account.head if account else "Unknown"
                entry_dict = {
                    "date": entry.ndate,
                    "head": head,
                    "voucher_number": entry.noteno or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "type": entry.ntype,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Journal_Entry):
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                account = Table_Accountsmaster.objects.filter(account_code=entry.accountcode, user=self.request.user).first()
                head = account.head if account else "Unknown"
                entry_dict = {
                    "date": entry.vdate,
                    "head": head,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "type": 'Journal',
                    "is_journal_entry": True,
                    "is_contra_entry": False,
                }

            elif isinstance(entry, Table_Contra_Entry):
                debit_amount = Decimal(entry.dramount or "0.00")
                credit_amount = Decimal(entry.cramount or "0.00")
                account = Table_Accountsmaster.objects.filter(account_code=entry.accountcode, user=self.request.user).first()
                head = account.head if account else "Unknown"
                entry_dict = {
                    "date": entry.vdate,
                    "head": head,
                    "voucher_number": entry.voucher_no or entry.series,
                    "narration": entry.narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "type": 'Contra',
                    "is_journal_entry": False,
                    "is_contra_entry": True,
                }

            # Accumulate totals
            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))
            entry_list.append(entry_dict)

        # Context for rendering the template
        context = {
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "start_date": start_date,
            "end_date": end_date,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
        }

        return render(request, "web/accounts/day-book/daybook.html", context)


from datetime import datetime


class TrialBalanceView(LoginRequiredMixin, View):
    def get(self, request):
        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()

        # Fetch all accounts grouped by their group in Table_Accountsmaster
        accounts = Table_Accountsmaster.objects.filter(user=self.request.user).order_by('group', 'head')

        # Fetch all entries without date filtering
        voucher_entries = Table_Voucher.objects.filter(user=self.request.user).order_by("Vdate")
        drcr_entries = Table_DrCrNote.objects.filter(user=self.request.user).order_by("ndate")
        journal_entries = Table_Journal_Entry.objects.filter(auth_user=self.request.user).order_by("vdate")
        contra_entries = Table_Contra_Entry.objects.filter(auth_user=self.request.user).order_by("vdate")

        # Combine and sort all entries by date
        combined_entries = (
            list(voucher_entries) + list(drcr_entries) + list(journal_entries) + list(contra_entries)
        )
        combined_entries.sort(key=lambda x: getattr(x, 'Vdate', getattr(x, 'ndate', getattr(x, 'vdate', datetime.min.date()))))

        # Initialize totals
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        entry_list = []
        group_totals = {}

        # Process and calculate debit, credit, and balances for display
        for account in accounts:
            # Ensure currentbalance is a Decimal
            current_balance = Decimal(account.currentbalance) if account.currentbalance not in [None, ''] else Decimal("0.00")
            
            # Initialize debit and credit for each account
            account_debit = Decimal("0.00")
            account_credit = Decimal("0.00")

            # Filter entries for this account and calculate debit/credit totals
            for entry in combined_entries:
                if hasattr(entry, "Accountcode") and entry.Accountcode == account.account_code:
                    debit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "P" else Decimal("0.00")
                    credit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "R" else Decimal("0.00")
                    account_debit += debit_amount
                    account_credit += credit_amount
                elif hasattr(entry, "accountcode") and entry.accountcode == account.account_code:
                    debit_amount = Decimal(entry.dramount or "0.00")
                    credit_amount = Decimal(entry.cramount or "0.00")
                    account_debit += debit_amount
                    account_credit += credit_amount

            # Update the totals
            total_debit += account_debit
            total_credit += account_credit

            # Add entry for this account with current balance
            entry_list.append({
                "group": account.group,
                "head": account.head,
                "current_balance": current_balance,
                "debit": account_debit,
                "credit": account_credit,
            })

            # Aggregate group totals
            if current_balance > 0:
                group_totals.setdefault(account.group, {'debit': Decimal("0.00"), 'credit': Decimal("0.00")})
                group_totals[account.group]['debit'] += current_balance
            elif current_balance < 0:
                group_totals.setdefault(account.group, {'debit': Decimal("0.00"), 'credit': Decimal("0.00")})
                group_totals[account.group]['credit'] += abs(current_balance)

        # Add group totals to entry list, updating the existing group entries
        for group, totals in group_totals.items():
            for entry in entry_list:
                if entry["group"] == group:
                    entry["debit"] += totals['debit']  # Add group total to debit column
                    entry["credit"] += totals['credit']  # Add group total to credit column
                    break

        # Context for rendering the template
        total_group_debit = sum(entry["debit"] for entry in entry_list)
        total_group_credit = sum(entry["credit"] for entry in entry_list)
        
        # Context for rendering the template
        context = {
            "entries": entry_list,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "total_group_debit": total_group_debit,
            "total_group_credit": total_group_credit,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
        }
        

        return render(request, "web/accounts/trial-balance/trialbalance.html", context)



class ProfitAndLossSearchView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/profit-and-loss/profit_and_loss_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context["finyearfrom"] = company_details.finyearfrom
        return context

    def post(self, request, *args, **kwargs):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not start_date or not end_date:
            messages.error(request, "Please select both start and end dates.")
            return self.get(request, *args, **kwargs)

        return HttpResponseRedirect(
            reverse(
                "web:profit_and_loss",  # Adjust the URL name as per your URL configuration
                kwargs={
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )

from collections import defaultdict

from datetime import date
from django.utils.dateparse import parse_date
from itertools import zip_longest


class ProfitAndLossView(LoginRequiredMixin, View):
    def get(self, request, start_date, end_date):
        
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        
        company_details = Table_Companydetailsmaster.objects.first()

        
        voucher_entries = Table_Voucher.objects.filter(Vdate__range=[start_date, end_date], user=self.request.user).order_by("Vdate")
        drcr_entries = Table_DrCrNote.objects.filter(ndate__range=[start_date, end_date], user=self.request.user).order_by("ndate")
        journal_entries = Table_Journal_Entry.objects.filter(vdate__range=[start_date, end_date], auth_user=self.request.user).order_by("vdate")
        contra_entries = Table_Contra_Entry.objects.filter(vdate__range=[start_date, end_date], auth_user=self.request.user).order_by("vdate")

        
        combined_entries = (
            list(voucher_entries) + list(drcr_entries) + list(journal_entries) + list(contra_entries)
        )
        combined_entries.sort(key=lambda x: getattr(x, 'Vdate', getattr(x, 'ndate', getattr(x, 'vdate', date.min))))

        
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        entry_list = []

        
        for entry in combined_entries:
            entry_dict = {}

            if hasattr(entry, "Vdate"):  
                debit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "P" else Decimal("0.00")
                credit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "R" else Decimal("0.00")
                account = Table_Accountsmaster.objects.filter(account_code=entry.Accountcode, user=self.request.user).first()
                head = account.head if account else "Unknown"
                entry_dict = {
                    "date": entry.Vdate,
                    "head": head,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "type": entry.CStatus,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            
            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))
            entry_list.append(entry_dict)

            
           
            income_totals = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})

            for entry in entry_list:
                head = entry.get("head")
                if head:
                    account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT INCOME').first()
                    if account:
                        income_totals[head]["debit"] += entry.get("debit", Decimal("0.00"))
                        income_totals[head]["credit"] += entry.get("credit", Decimal("0.00"))

            indirect_income_entries = []
            for head, amounts in income_totals.items():
                account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT INCOME').first()
                currentbalance = account.currentbalance if account else "0.00"
                indirect_income_entries.append({
                    "head": head,
                    "debit": Decimal(currentbalance or "0.00"),  
                    "credit": amounts["credit"],  
                })

            # Aggregate INDIRECT EXPENSES
            expense_totals = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
            
            for entry in entry_list:
                head = entry.get("head")
                if head:
                    account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT EXPENSES').first()
                    if account:
                        expense_totals[head]["debit"] += entry.get("debit", Decimal("0.00"))
                        expense_totals[head]["credit"] += entry.get("credit", Decimal("0.00"))
            
            indirect_expense_entries = []
            for head, amounts in expense_totals.items():
                account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT EXPENSES').first()
                currentbalance = account.currentbalance if account else "0.00"
                indirect_expense_entries.append({
                    "head": head,
                    "debit": Decimal(currentbalance or "0.00"),
                    "credit": amounts["credit"],
                })

            


        # Calculate grand totals
        total_indirect_income = sum(entry["debit"] for entry in indirect_income_entries)
        total_indirect_expense = sum(entry["debit"] for entry in indirect_expense_entries)
        max_length = max(len(indirect_income_entries), len(indirect_expense_entries))


        income_expense_rows = list(zip_longest(indirect_income_entries, indirect_expense_entries, fillvalue={}))
        difference_amount = abs(total_indirect_income - total_indirect_expense)
        

        context = {
            "difference_amount": difference_amount,
            "entries": indirect_income_entries,
            "indirect_expense_entries": indirect_expense_entries,
            "total_indirect_income": total_indirect_income,  
            "total_indirect_expense": total_indirect_expense, 
            "total_debit": total_debit,
            "total_credit": total_credit,
            "start_date": start_date,
            "end_date": end_date,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
            "max_length": max_length, 
            "income_expense_rows": income_expense_rows,
            "total_indirect_income": total_indirect_income,
            "total_indirect_expense": total_indirect_expense,


        }
        

        return render(request, "web/accounts/profit-and-loss/profit_and_loss.html", context)


#Balance Sheet
class BalanceSheetSearchView(LoginRequiredMixin, TemplateView):
    template_name = "web/accounts/balance-sheet/balance_sheet_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_details = Table_Companydetailsmaster.objects.first()
        if company_details:
            context["finyearfrom"] = company_details.finyearfrom
        return context

    def post(self, request, *args, **kwargs):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not start_date or not end_date:
            messages.error(request, "Please select both start and end dates.")
            return self.get(request, *args, **kwargs)

        return HttpResponseRedirect(
            reverse(
                "web:balance_sheet",  # Adjust the URL name as per your URL configuration
                kwargs={
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )

from collections import defaultdict

from datetime import date
from django.utils.dateparse import parse_date
from itertools import zip_longest


class BalanceSheetView(LoginRequiredMixin, View):
    def get(self, request, start_date, end_date):
        # Parse start and end dates
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)

        # Fetch company details
        company_details = Table_Companydetailsmaster.objects.first()

        # Fetch entries within the date range
        voucher_entries = Table_Voucher.objects.filter(Vdate__range=[start_date, end_date], user=self.request.user).order_by("Vdate")
        drcr_entries = Table_DrCrNote.objects.filter(ndate__range=[start_date, end_date], user=self.request.user).order_by("ndate")
        journal_entries = Table_Journal_Entry.objects.filter(vdate__range=[start_date, end_date], auth_user=self.request.user).order_by("vdate")
        contra_entries = Table_Contra_Entry.objects.filter(vdate__range=[start_date, end_date], auth_user=self.request.user).order_by("vdate")

        # Combine and sort all entries by date
        combined_entries = (
            list(voucher_entries) + list(drcr_entries) + list(journal_entries) + list(contra_entries)
        )
        combined_entries.sort(key=lambda x: getattr(x, 'Vdate', getattr(x, 'ndate', getattr(x, 'vdate', date.min))))

        # Process and calculate debit, credit, and balances for display
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        entry_list = []

        # Loop through the entries and process each one
        for entry in combined_entries:
            entry_dict = {}

            if hasattr(entry, "Vdate"):  # Table_Voucher entry
                debit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "P" else Decimal("0.00")
                credit_amount = Decimal(entry.VAmount or "0.00") if entry.CStatus == "R" else Decimal("0.00")
                account = Table_Accountsmaster.objects.filter(account_code=entry.Accountcode, user=self.request.user).first()
                head = account.head if account else "Unknown"
                entry_dict = {
                    "date": entry.Vdate,
                    "head": head,
                    "voucher_number": entry.VoucherNo or entry.Series,
                    "narration": entry.Narration,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "type": entry.CStatus,
                    "is_journal_entry": False,
                    "is_contra_entry": False,
                }

            # Accumulate totals
            total_debit += entry_dict.get("debit", Decimal("0.00"))
            total_credit += entry_dict.get("credit", Decimal("0.00"))
            entry_list.append(entry_dict)


            income_totals = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})

            for entry in entry_list:
                head = entry.get("head")
                if head:
                    account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT INCOME').first()
                    if account:
                        income_totals[head]["debit"] += entry.get("debit", Decimal("0.00"))
                        income_totals[head]["credit"] += entry.get("credit", Decimal("0.00"))

            indirect_income_entries = []
            for head, amounts in income_totals.items():
                account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT INCOME').first()
                currentbalance = account.currentbalance if account else "0.00"
                indirect_income_entries.append({
                    "head": head,
                    "debit": Decimal(currentbalance or "0.00"),  
                    "credit": amounts["credit"],  
                })

            # Aggregate INDIRECT EXPENSES
            expense_totals = defaultdict(lambda: {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
            
            for entry in entry_list:
                head = entry.get("head")
                if head:
                    account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT EXPENSES').first()
                    if account:
                        expense_totals[head]["debit"] += entry.get("debit", Decimal("0.00"))
                        expense_totals[head]["credit"] += entry.get("credit", Decimal("0.00"))
            
            indirect_expense_entries = []
            for head, amounts in expense_totals.items():
                account = Table_Accountsmaster.objects.filter(user=request.user, head=head, group='INDIRECT EXPENSES').first()
                currentbalance = account.currentbalance if account else "0.00"
                indirect_expense_entries.append({
                    "head": head,
                    "debit": Decimal(currentbalance or "0.00"),
                    "credit": amounts["credit"],
                })    

    

        # Group mappings
        liability_groups = [
            'LIABILITIES', 'CURRENT LIABILITIES', 'SUNDRY CREDITORS', 'LOANS',
            'CAPITAL ACCOUNT', 'DUTIES AND TAXES', 'INCOME', 'TRADING INCOME',
            'INDIRECT INCOME', 'EXPENSES', 'TRADING EXPENSES', 'INDIRECT EXPENSES',
        ]

        asset_groups = [
            'CURRENT ASSET', 'FIXED ASSETS', 'SUNDRY DEBTORS', 'CASH AT BANK', 'CASH IN HAND',
        ]

        # Liabilities
        liabilities = Table_Accountsmaster.objects.filter(
            user=request.user, group__in=liability_groups
        ).values('head', 'group', 'currentbalance')

        # Assets
        assets = Table_Accountsmaster.objects.filter(
            user=request.user, group__in=asset_groups
        ).values('head', 'group', 'currentbalance')

        liability_entries = []
        asset_entries = []
        total_liability = Decimal("0.00")
        total_asset = Decimal("0.00")

        for item in liabilities:
            balance = Decimal(item["currentbalance"] or "0.00")
            liability_entries.append({
                "head": item["head"],
                "balance": balance
            })
            total_liability += balance

        for item in assets:
            balance = Decimal(item["currentbalance"] or "0.00")
            asset_entries.append({
                "head": item["head"],
                "balance": balance
            })
            total_asset += balance

        # Pad shorter list to match row count for table
        max_balance_rows = max(len(liability_entries), len(asset_entries))
        balance_sheet_rows = list(zip_longest(liability_entries, asset_entries, fillvalue={}))

        # Calculate grand totals
        total_indirect_income = sum(entry["debit"] for entry in indirect_income_entries)
        total_indirect_expense = sum(entry["debit"] for entry in indirect_expense_entries)
        max_length = max(len(indirect_income_entries), len(indirect_expense_entries))


        income_expense_rows = list(zip_longest(indirect_income_entries, indirect_expense_entries, fillvalue={}))
        difference_amount = abs(total_indirect_income - total_indirect_expense)

        context = {
            "difference_amount": difference_amount,
            "balance_sheet_rows": balance_sheet_rows,
            "total_liability": total_liability,
            "total_asset": total_asset,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "start_date": start_date,
            "end_date": end_date,
            "company_name": company_details.companyname,
            "company_phone": company_details.phoneno,
            "company_address": company_details.address1,
            "company_gst": company_details.gst,
            "entries": indirect_income_entries,
            "indirect_expense_entries": indirect_expense_entries,
            "total_indirect_income": total_indirect_income,  
            "total_indirect_expense": total_indirect_expense, 
        }
        

        return render(request, "web/accounts/balance-sheet/balance_sheet.html", context)
    
# ----------------------------------------X---------------------X-------------------------------- #
# ----------------------------------------| ACCOUNTING END |------------------------------------- #
# ----------------------------------------X---------------------X---------------------------------#









# -------------------------------------------- WALLET ------------------------------------------------









from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import json, base64, os, requests
from django.contrib import messages
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import secrets
import string
import hashlib
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.x509 import load_pem_x509_certificate, load_der_x509_certificate

def get_alpha_numeric_string(n):
    sr = secrets.SystemRandom()
    alphanumeric_chars = string.ascii_letters + string.digits
    r = ''.join(sr.choice(alphanumeric_chars) for _ in range(n))
    return r

def encrypt_aess(data, session_key_str):
    """
    AES-128 GCM encryption with SHA-256 digested key (truncated to 16 bytes).
    """
    iv = bytes([0] * 16)
    hashed_key = hashlib.sha256(session_key_str.encode('utf-8')).digest()
    encryptor = Cipher(
        algorithms.AES(hashed_key),
        modes.GCM(iv),
        backend=default_backend()
    ).encryptor()
    ciphertext = encryptor.update(data.encode('utf-8')) + encryptor.finalize()
    ciphertext_with_tag = ciphertext + encryptor.tag
    result = base64.b64encode(ciphertext_with_tag).decode('utf-8')
    return result

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib, base64

def encrypt_aes(data, session_key):
    # Step 1: derive AES key
    key = hashlib.sha256(session_key.encode()).digest()[:16]

    # Step 2: 12-byte zero IV
    iv = b'\x00' * 12

    # Step 3: AES GCM encrypt
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(iv, data.encode(), None)

    # Step 4: base64 encode
    return base64.b64encode(encrypted).decode()

import base64
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes

def encrypt_session_key(session_key_str, sbi_public_key):
    """
    Encrypts the session key string using RSA/OAEP with SHA-1 (same as Java).
    """
    encrypted_key = sbi_public_key.encrypt(
        session_key_str.encode('utf-8'),
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),  
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    result = base64.b64encode(encrypted_key).decode('utf-8')
    return result

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import subprocess, tempfile, os
def load_private_key_auto(path: str, password: bytes = None):
    """
    Load a private key from either OpenSSH or RSA PEM format.
    If it's OpenSSH, convert to RSA PEM automatically using ssh-keygen.
    """
    with open(path, "rb") as f:
        key_data = f.read()

    # Try loading directly first (works for PEM/PKCS#1/PKCS#8)
    try:
        return serialization.load_pem_private_key(key_data, password=password, backend=default_backend())
    except ValueError:
        pass  # Not in PEM format

    # Detect OpenSSH key
    if b"OPENSSH PRIVATE KEY" in key_data:
        # Write temp key
        with tempfile.NamedTemporaryFile(delete=False) as tmp_in:
            tmp_in.write(key_data)
            tmp_in.flush()
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path + "_rsa"

        try:
            # Convert using ssh-keygen
            subprocess.run(
                ["ssh-keygen", "-p", "-m", "PEM", "-f", tmp_in_path, "-N", ""],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            with open(tmp_in_path, "rb") as f2:
                rsa_data = f2.read()

            return serialization.load_pem_private_key(rsa_data, password=password, backend=default_backend())
        finally:
            # Cleanup
            os.remove(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)

    raise ValueError("Unsupported private key format")

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib
import base64

def decrypt_aes256_gcm(encrypted_token_request: str, session_key: str) -> str:
    key_bytes = hashlib.sha256(session_key.encode('utf-8')).digest()
    iv = b'\x00' * 16

    encrypted_bytes = base64.b64decode(encrypted_token_request)
    if len(encrypted_bytes) <= 16:
        raise ValueError("Ciphertext is too short or doesn't include an authentication tag.")

    ciphertext = encrypted_bytes[:-16]
    tag = encrypted_bytes[-16:]

    decryptor = Cipher(
        algorithms.AES(key_bytes),
        modes.GCM(iv, tag),
        backend=default_backend()
    ).decryptor()

    decrypted = decryptor.update(ciphertext) + decryptor.finalize()
    return decrypted.decode('utf-8')

def decrypt_aes_gcm(encrypted_data, session_key):

    key = hashlib.sha256(session_key.encode()).digest()[:16]

    iv = b'\x00' * 12

    encrypted_bytes = base64.b64decode(encrypted_data)

    aesgcm = AESGCM(key)

    decrypted = aesgcm.decrypt(iv, encrypted_bytes, None)

    return decrypted.decode()

@csrf_exempt
def deposit_money(request):
    if request.method == "POST":
        try:
            # 1?? Generate Session Key
            session_key = get_alpha_numeric_string(16)
            print("SESSION KEY:", session_key)
            print("SESSION KEY LENGTH:", len(session_key))
            # 2?? Prepare Auth Data
            auth_data = {
                "password": "4c3658fb275d7d2f89b86dcc3a2b00ecbe08a93d8473318a353d15734e1c7bbabe5456255390160569abe15f1abe8755f64770287649ce8098f8f7caf601cc5d",
                "username": "197_SAMATWA",
                "application": "PaymentsData",
                "client": "283460"
            }
            data = json.dumps(auth_data)
            encrypted_auth = encrypt_aes(data, session_key)
            print("AES INPUT DATA:", data)
            print("AES ENCRYPTED:", encrypted_auth)
            print("AES LENGTH:", len(encrypted_auth))
            messages.success(request, f"? Encrypted AuthTokenRequest:\n{encrypted_auth}")

            # 3?? Load SBI Public Certificate
            try:
                with open("web/certs/SBI_public.cer.txt", "rb") as f:
                    cert_data = f.read()
                    try:
                        cert = load_pem_x509_certificate(cert_data, default_backend())
                    except ValueError:
                        cert = load_der_x509_certificate(cert_data, default_backend())
                    sbi_public_key = cert.public_key()
            except Exception as e:
                messages.error(request, f"? Failed to load public certificate: {str(e)}")
                return render(request, "web/franchise/wallet/payment.html")
            print("CERTIFICATE SUBJECT:", cert.subject)
            print("CERTIFICATE ISSUER:", cert.issuer)
            print("PUBLIC KEY TYPE:", type(sbi_public_key))
            # 4?? Encrypt Session Key
            try:
                encrypted_session_key = encrypt_session_key(session_key, sbi_public_key)
                print("RSA INPUT SESSION KEY:", session_key)
                print("RSA ENCRYPTED SESSION KEY:", encrypted_session_key)
                print("RSA LENGTH:", len(encrypted_session_key))
                messages.success(request, f"? Encrypted SessionKey:\n{encrypted_session_key}")
            except Exception as e:
                messages.error(request, f"? Failed to encrypt session key: {str(e)}")
                return render(request, "web/franchise/wallet/payment.html")

            # 5?? Send AuthTokenRequest
            payload = {
                "AuthTokenRequest": encrypted_auth,
                "SessionKey": encrypted_session_key
            }
            url = 'https://cmp.sbiuat.bank.in:8443/SBITokenServices/token/getToken/'
            headers = {'Content-Type': 'application/JSON'}
            print("FINAL SBI PAYLOAD:")
            print(json.dumps(payload, indent=2))
            response = requests.post(url, json=payload, headers=headers)
            print("===== SBI TOKEN API RESPONSE =====")
            print("STATUS:", response.status_code)
            print("HEADERS:", response.headers)
            print("BODY:", response.text)
            print("==================================")

            if response.status_code != 200:
                messages.error(request, f"? SBI API failed: {response.status_code} {response.text}")
                return render(request, "web/franchise/wallet/payment.html")
            print("RAW RESPONSE:", response.text)
            result = response.json()
            if "SessionKey" not in result:
                print("SBI ERROR RESPONSE:", result)
                messages.error(request, f"SBI error: {result}")
                return render(request, "web/franchise/wallet/payment.html")
            messages.success(request, f'? SBI Token Response:\n -->{result.get("SessionKey", "No SessionKey")} <--, -->{result.get("AuthTokenResponse", "No AuthTokenResponse")}<--')

            # 6?? Check SessionKey and decrypt it
            print("RAW SBI RESPONSE:", result)
            encrypted_session_key_from_response = result.get("SessionKey")
            print("SESSIONKEY STRING:", encrypted_session_key_from_response)
            print("SESSIONKEY LENGTH:", len(encrypted_session_key_from_response) if encrypted_session_key_from_response else 0)
            if not encrypted_session_key_from_response:
                messages.error(request, "? Missing SessionKey in SBI response!")
                return render(request, "web/franchise/wallet/payment.html")

            encrypted_session_key_bytes = base64.b64decode(encrypted_session_key_from_response)
            messages.success(request, f"?? Encrypted SessionKey length: {len(encrypted_session_key_bytes)} bytes")

            # Load private key
            try:
                private_key = load_private_key_auto("web/certs/id_rsa_2048.pem", password=None)
            except Exception as e:
                messages.error(request, f"? Failed to load private key: {str(e)}")
                return render(request, "web/franchise/wallet/payment.html")

            try:
                decrypted_session_key_bytes = private_key.decrypt(
                    encrypted_session_key_bytes,
                    asym_padding.OAEP(
                        mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),
                        algorithm=hashes.SHA1(),
                        label=None
                    )
                )
                decrypted_session_key_hex = decrypted_session_key_bytes.hex()
                messages.success(request, f"?? Decrypted Session Key (hex): {decrypted_session_key_hex}")
            except Exception as e:
                messages.error(request, f"? RSA decryption failed: {str(e)}")
                return render(request, "web/franchise/wallet/payment.html")


            encrypted_auth_response = result.get("AuthTokenResponse")
            if not encrypted_auth_response:
                messages.error(request, "? Missing AuthTokenResponse in SBI response!")
                return render(request, "web/franchise/wallet/payment.html")

            try:
                session_key_str = decrypted_session_key_bytes.decode('latin-1')
                decrypted_auth_response = decrypt_aes_gcm(encrypted_auth_response, session_key_str)
                messages.success(request, f"?? Decrypted AuthTokenResponse:\n{decrypted_auth_response}")
            except Exception as e:
                messages.error(request, f"? Failed to decrypt AuthTokenResponse: {str(e)}")

        except Exception as e:
            messages.error(request, f"? Exception occurred: {str(e)}")

    return render(request, "web/franchise/wallet/payment.html")
