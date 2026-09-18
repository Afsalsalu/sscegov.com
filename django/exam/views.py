# Django imports for views, request handling, and authentication
import json
import random
import string
import uuid
from datetime import date

import pdfkit
# Third-party imports for payment integration and email handling
import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout
# from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
# from easy_pdf.views import PDFView
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from sib_api_v3_sdk import ApiClient, Configuration
from sib_api_v3_sdk.api import transactional_emails_api
from sib_api_v3_sdk.models import SendSmtpEmail
from sib_api_v3_sdk.rest import ApiException


from .models.user_registration import MainExamRegistration

# Custom imports for user forms and email utilities
from web.forms import CentreUserForm
from web.models import CentreUserAccount

from .constants import PaymentStatus
# Django imports for models, forms, and utility functions
from .forms import UserRegistrationForm
from .models import (ExamCategory, MainExamOption, MainExamProgress,
                     MainExamQuestion, Option, Payment, Question,
                     TecExamProgress, UserRegistration,RegistrationState,RegistrationDistrict,RegistrationPanchayat)





class UserRegistrationMixin:
    """
    A mixin to handle user registration-specific data in class-based views.

    This mixin provides utility methods to retrieve the `UserRegistration`
    instance associated with the currently logged-in user and to filter querysets
    based on the user's registration details.
    """

    def get_user_registration(self):
        """
        Retrieve the `UserRegistration` instance for the currently logged-in user.

        Returns:
            UserRegistration: The `UserRegistration` instance associated with the current user.

        Raises:
            Http404: If the `UserRegistration` instance does not exist for the current user.
        """
        return get_object_or_404(TemporaryUser, user=self.request.user)

    def get_queryset(self):
        """
        Filter the queryset to include only objects related to the current user's registration.

        This method overrides the base `get_queryset` method to filter the queryset
        based on the current user's registration details. It ensures that only data
        pertinent to the user's registration is included in the queryset.

        Returns:
            QuerySet: A filtered queryset containing only objects related to the current user's registration.
        """
        qs = super().get_queryset()  # Call the parent class's get_queryset method.
        return qs.filter(
            user_registration=self.get_user_registration()
        )  # Filter the queryset.


# View to handle user registration
from django.shortcuts import render
from django.views import View
from .forms import UserRegistrationForm

from django.shortcuts import render
from .models import RegistrationState

from django.http import JsonResponse

import random
import string
from datetime import date
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from razorpay import Client as RazorpayClient
from django.conf import settings


from .models.user_registration import TemporaryUser


from .models import UserRegistration, Payment, RegistrationState, RegistrationDistrict
from .forms import UserRegistrationForm
# from .utils import PaymentStatus  # Assuming PaymentStatus is defined elsewhere
# from sib_api_v3_sdk import ApiClient, Configuration, transactional_emails_api
from sib_api_v3_sdk.models import SendSmtpEmail
from sib_api_v3_sdk.rest import ApiException


from django.shortcuts import render
from django.views import View
from .models import RegistrationState, RegistrationDistrict
from .forms import UserRegistrationForm

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from .models import RegistrationState, RegistrationDistrict
from .forms import UserRegistrationForm
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from datetime import date
from razorpay import Client
from django.conf import settings

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from .models import RegistrationState, RegistrationDistrict
from .forms import UserRegistrationForm
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from datetime import date
from razorpay import Client
from django.conf import settings
from datetime import datetime


class UserRegistrationView(View):
    def get(self, request):
        states = RegistrationState.objects.all()
        districts = RegistrationDistrict.objects.all()
        panchayats = RegistrationPanchayat.objects.all()
        form = UserRegistrationForm()
        selected_state = None  # Initially, no state is selected

        return render(
            request,
            "web/exam/register.html",
            {"form": form, "states": states, "districts": districts, 'panchayats': panchayats, "selected_state": selected_state},
        )

    def post(self, request):
        states = RegistrationState.objects.all()
        selected_state = request.POST.get('state')
        districts = RegistrationDistrict.objects.filter(state=selected_state) if selected_state else []
        form = UserRegistrationForm(request.POST, request.FILES)





        # new commmented.....///////

        # if form.is_valid():
        #     form_data = form.cleaned_data
        #     mobile = form_data.get("mobile")
        #     photo = request.FILES.get("photo")
        #     if photo:
        #         photo_path = default_storage.save(
        #             f"photos/{photo.name}", ContentFile(photo.read())
        #         )
        #         form_data["photo"] = photo_path

        #     for key, value in form_data.items():
        #         if isinstance(value, (datetime, date)):
        #             form_data[key] = value.strftime('%Y-%m-%d')

        #     request.session['user_data'] = form_data





            # never commented //////

            # client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            # amount = 100

            # try:
            #     # Create the Razorpay order
            #     order = client.order.create({
            #         'amount': amount,
            #         'currency': 'INR',
            #         'payment_capture': 1  # 1 means automatic capture
            #     })

            #     # Extract the Razorpay order ID
            #     razorpay_order_id = order['id']

            #     # Save the order ID to session for later verification
            #     request.session['razorpay_order_id'] = razorpay_order_id


            # here.............//////









            # new commented.../////


        #     return render(
        #     request,
        #     "web/exam/cnfm_pymt-btn.html",  # Render confirmation page with payment details
        #     {
        #         "mobile": mobile,
        #         "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        #         "amount": 100,  # Amount can be dynamic if needed
        #     }
        # )
        # else:
        return render(request, "web/exam/register.html",{"form": form, 
                                                             "states": states,
                                                               "districts": districts, 
                                                               "selected_state": selected_state})



        # here ......///////////


def get_districts(request):
        state_id = request.GET.get('state_id') 
        print(state_id)
        if state_id:
            # Ensure the state_id exists in the database and fetch related districts
            districts = RegistrationDistrict.objects.filter(state=state_id)
            district_list = [
                {"id": district.district_id, "district_name": district.district_name}  # Use correct field names
                for district in districts
            ]
            return JsonResponse(district_list, safe=False)
        return JsonResponse([], safe=False)



def get_panchayats(request):
    district_id = request.GET.get('district_id')  
    local_body = request.GET.get('local_body')

    if district_id and district_id != "undefined":
        try:
            district_id = int(district_id)
            # Update the filter to also consider local_body if it exists
            panchayats = RegistrationPanchayat.objects.filter(district=district_id)

            if local_body:  # Filter based on local_body if it is provided
                panchayats = panchayats.filter(local_body=local_body)

            # Prepare the response data
            panchayat_data = [{
                'id': panchayat.panchayat_id,
                'name': panchayat.name
            } for panchayat in panchayats]

            return JsonResponse(panchayat_data, safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid district ID'}, status=400)
    return JsonResponse({'error': 'District ID not provided'}, status=400)
        
    


# class PaymentCallbackView(View):
@csrf_exempt
def payment_callback(request, user_id):
    if request.method == "POST":
        data = json.loads(request.body)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
        
        try:
            # Verify Razorpay payment signature
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })
            
            # Payment is verified successfully
            razorpay_order_id = data['razorpay_order_id']
            payment_id = data['razorpay_payment_id']
            signature = data['razorpay_signature']

            # Get form data from session
            form_data = request.session.get("form_data")
            if not form_data:
                print("Session data not found.")
                return JsonResponse({"success": False, "message": "Session expired. Please try again."})

            # Prepare user registration data
            user_registration = get_object_or_404(TemporaryUser, id=user_id)
            username = generate_unique_username(user_registration.id)
            password = user_registration.mobile

            try:
                # Create user and save registration details
                User = get_user_model()
                user = User.objects.create_user(username=username, password=password, email=user_registration.email)

                # Record successful payment
                # Payment.objects.create(
                #     user_registration=user_registration,
                #     amount=100,
                #     provider_order_id=razorpay_order_id,
                #     status=PaymentStatus.SUCCESS,
                #     payment_id=payment_id,
                #     signature_id=signature,
                # )

                # Clear session data
                request.session.pop("form_data", None)
                request.session.pop("razorpay_order_id", None)

                # Send welcome email
                send_welcome_email(user_registration)
                return JsonResponse({"success": True})

            except IntegrityError as e:
                print("Integrity error:", e)
                return JsonResponse({"success": False, "message": "Registration failed. Please try again."})

        except razorpay.errors.SignatureVerificationError as e:
            print("Signature verification failed:", e)
            return JsonResponse({"success": False, "message": "Payment verification failed."})
        
        except Exception as e:
            print("Unexpected error:", e)
            # try:
            #     # Update payment status to failure
            #     payment = Payment.objects.get(provider_order_id=data['razorpay_order_id'])
            #     payment.status = PaymentStatus.FAILURE
            #     payment.save()
            # except Payment.DoesNotExist:
            #     print("Payment record not found.")
            # return JsonResponse({"success": False, "message": "Payment processing failed."})
    else:
        return JsonResponse({"success": False, "message": "Invalid request method."})


def generate_unique_username(base_username):
    prefix = "000000500"
    base_username = f"{prefix}{base_username}"
    # User = get_user_model()
    username = base_username
    while User.objects.filter(username=username).exists():
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        username = f"{base_username}{suffix}"
    return username


def send_welcome_email(user_registration):
    subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
    html_content = (
        f"<p>Thank you for registering. Your account has been created successfully.</p>"
        f"<p><strong>Centre ID:</strong> {user_registration.id}</p>"
        f"<p><strong>Username:</strong> {user_registration.user.username}</p>"
        f"<p><strong>Password:</strong> {user_registration.mobile}</p>"
        f"<p>We recommend you change your password after logging in.</p>"
        f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
        f"<p>Best regards,<br>The SSC Team</p>"
    )

    configuration = Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_client = ApiClient(configuration)
    api_instance = transactional_emails_api.TransactionalEmailsApi(api_client)

    email_data = SendSmtpEmail(
        to=[{"email": user_registration.email}],
        subject=subject,
        html_content=html_content,
        sender={
            "name": "Samatwa Service Centre",
            "email": "samatwaservicecenter.gov.in@gmail.com",
        },
    )

    try:
        api_instance.send_transac_email(email_data)
    except ApiException as e:
        print("Exception when sending email:", e)

# def login_view(request):
#     if request.method == "POST":
#         username = request.POST.get("username")
#         password = request.POST.get("password")

#         print(f"Trying to authenticate: {username}, {password}")

#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             print(f"Authenticated successfully: {user.username}")
#             login(request, user)
#             return redirect("exam:dashboard")
#         else:
#             print("Authentication failed!")
#             messages.error(request, "Invalid username or password")

#     return render(request, "web/exam/userlogin.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        print(f"Trying to authenticate: {username}, {password}")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            print(f"Authenticated successfully: {user.username}")
            login(request, user)
            return redirect("exam:dashboard")
        else:
            print("Authentication failed!")
            messages.error(request, "Invalid username or password")
    else:
        response = render(request, "web/exam/userlogin.html")
        for cookies in request.COOKIES:
            response.delete_cookie(cookies)
        return response

    return render(request, "web/exam/userlogin.html")


def logout_view(request):
        response = render(request, "web/exam/userlogin.html")
        for cookies in request.COOKIES:
            response.delete_cookie(cookies)
        return response 

# @login_required
def admin_dashboard(request):
    user = request.user
    profile = TemporaryUser.objects.filter(user=user).first()

    if not profile:
        return redirect("exam:details_entry")

    progress = MainExamProgress.objects.filter(user=user).order_by("-attempt_number")
    last_attempt = progress.first() if progress.exists() else None

    tec_certificate_status = False

    try:
        passed_exams_list = TecExamProgress.objects.filter(user=profile, status='Passed').count()
        if passed_exams_list >= 5:
            tec_certificate_status = True
    except Exception as e:
        messages.error(request, f'Error: {e}')

    # Default value for payment_button
    payment_button = None  

    # Determine the certificate status
    if not progress.exists():
        certificate_status = "Exam not attempted. Please complete the assessment and take the exam."
    elif last_attempt.status == "Passed":
        if profile.certificate_paid:
            certificate_status = "Certificate payment successful. Download your certificate anytime."
        else:
            certificate_status = "Congratulations! You have passed the exam. Please complete your details to pay for the certificate."
            payment_button = True  # Set payment button here
    elif last_attempt.status == "Failed Attempt 1":
        if last_attempt.attempt_number == 1:
            certificate_status = "Your 1st attempt failed. You have only 1 chance remaining. Better luck on the 2nd attempt!"
        else:
            certificate_status = "You have failed on the 1st attempt. Please review the material and try again."
    elif last_attempt.status == "Failed Attempt 2":
        certificate_status = "You have failed the exam twice. The exam is frozen. No more chances available. Sorry!"
    else:
        certificate_status = "Exam not attempted. Please complete the assessment to take the exam."

    if not profile.certificate_paid:  
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_data = {
            "amount": 100,  # Amount in paise (?500)
            "currency": "INR",
            "receipt": f"order_rcpt_{user.id}",
            "payment_capture": "1"
        }
        order = client.order.create(data=payment_data)
        order_id = order["id"]
    else:
        order_id = None

    context = {
        "profile": profile,
        "progress": progress,
        "certificate_status": certificate_status,
        "tec_certificate_status": tec_certificate_status,
        "payment_button": payment_button,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": order_id,
        "amount": 100,
    }

    return render(request, "web/exam/dashboard.html", context)

# @login_required
def learning(request):
    # Retrieve all exam categories
    questions = ExamCategory.objects.all()
    user = request.user
    profile = TemporaryUser.objects.get(user=user)

    # Render the learning page with the exam categories
    return render(request, "web/exam/learning.html", {"questions": questions, 'profile': profile})


# @login_required
def assessments(request):
    user = request.user
    user_registration = get_object_or_404(TemporaryUser, user=user)
    profile = TemporaryUser.objects.get(user=user)

    # Retrieve all exam categories
    exams = ExamCategory.objects.all()

    # Fetch progress data for the current user
    progress_data = TecExamProgress.objects.filter(
        user=user_registration
    ).select_related("exam_category")

    # Convert progress data into a dictionary for easy access
    progress_dict = {p.exam_category.id: p for p in progress_data}

    # Prepare a list to store progress information
    progress_list = []

    all_exams_passed = True  

    for index, exam in enumerate(exams):
        exam_progress = progress_dict.get(exam.id)
        total_questions = Question.objects.filter(exam_category=exam).count()
        correct_answers = exam_progress.correct_answers if exam_progress else None

        # Determine the status of the current exam
        if index == 0:
            # First exam's status is determined based on its progress
            if exam_progress:
                status = (
                    exam_progress.status.capitalize()
                    if exam_progress.status
                    else "Open"
                )
            else:
                status = (
                    "Open"  # Assuming we want the first exam open if no progress exists
                )
        else:
            # Check the status of the previous exam
            previous_exam = exams[index - 1]
            previous_progress = progress_dict.get(previous_exam.id)

            if previous_progress and previous_progress.status == "Passed":  
                status = (
                    "Open" if not exam_progress else exam_progress.status.capitalize()
                )
            elif previous_progress and previous_progress.status == "Failed":  
                status = (
                    "Open" if not exam_progress else exam_progress.status.capitalize()
                )
            else:
                status = "Locked"
                all_exams_passed = (
                    False  # Mark as False if any exam is locked or not passed
                )


        progress_list.append(
            {
                "exam_name": exam.name,
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "status": status,
                "exam_id": exam.id,
            }
        )


    current_user = TemporaryUser.objects.get(user=request.user)
    lists = TecExamProgress.objects.filter(user=current_user, status='Passed')
    length = len(lists)
    if length >= 5:
        all_exams_passed =True
        auth_email = request.user.email
        auth_username = request.user.username
        auth_user = User.objects.get(email=auth_email, username=auth_username)
        try:
            new_username = generate_tec_username(current_user.user.username)
            try:
                existing_user = MainExamRegistration.objects.filter(username=new_username)
                messages.warning(request, 'user is already existing.......')
            except MainExamRegistration.DoesNotExist:
                existing_user = None
            if not existing_user:
                new_user = MainExamRegistration.objects.create(user=auth_user, 
                                            username = new_username, 
                                            password = current_user.mobile, 
                                            mobile = current_user.mobile)
                new_user.save()
                tec_passed_email_send(new_user)
                return redirect('exam:dashboard')
        except Exception as e:
            messages.error(request, f'error{e}')
    return render(
        request,
        "web/exam/assessments.html",
        {
            "progress_data": progress_list,
            "all_exams_passed": all_exams_passed,
            'profile': profile
        },
    )


# @login_required
def take_exam(request, exam_id):
    exam_category = get_object_or_404(ExamCategory, id=exam_id)
    user = request.user
    user_registration = get_object_or_404(TemporaryUser, user=user)

    # Get or create a progress record for this user and exam category
    progress, created = TecExamProgress.objects.get_or_create(
        user=user_registration, exam_category=exam_category
    )

    # Prevent retaking the exam if the status is 'Passed' or 'Locked'
    if progress.status in ["Passed", "Locked"]:
        messages.error(request, "You cannot retake this exam.")
        return redirect("exam:assessments")

    questions = Question.objects.filter(exam_category=exam_category).prefetch_related(
        "options"
    ).order_by('?')[:10]
    if not questions.exists():
        messages.error(request, "No questions available for this exam.")
        return redirect("exam:assessments")

    if request.method == "POST":
        user_answers = {}
        correct_count = 0
        for question in questions:
            answer_id = request.POST.get(f"question_{question.id}")
            if answer_id:
                user_answers[question.id] = answer_id
                if Option.objects.filter(
                    id=answer_id, question=question, is_correct=True
                ).exists():
                    correct_count += 1

        total_questions = len(questions)
        score = correct_count  # Score is the number of correct answers

        # Update the progress record with the user's answers, score, and status
        update_user_progress(user, exam_category, score)

        # Redirect to the assessments page after saving the progress
        return redirect("exam:assessments")

    context = {
        "exam_category": exam_category,
        "questions": questions,
        "progress": progress,
    }
    return render(request, "web/exam/exam/take_exam.html", context)


def update_user_progress(user, exam_category, score):
    """
    Update user's progress for the exam category based on score.
    """
    user_registration = get_object_or_404(TemporaryUser, user=user)
    user_progress, created = TecExamProgress.objects.get_or_create(
        user=user_registration, exam_category=exam_category
    )

    # Passing mark is 5 correct answers
    user_progress.score = score
    user_progress.status = "Passed" if score >= 5 else "Failed"
    user_progress.correct_answers = score  
    user_progress.save()

    
    current_user = TemporaryUser.objects.get(user=user)
    lists = TecExamProgress.objects.filter(user=current_user, status='Passed')
    length = len(lists)
    if length >= 5:
        all_exams_passed =True
        auth_email = user.email
        auth_username = user.username
        auth_user = User.objects.get(email=auth_email, username=auth_username)
        try:
            new_username = generate_tec_username(current_user.user.username)
            try:
                existing_user = MainExamRegistration.objects.filter(username=new_username)
                print('user is already existing.......')
            except MainExamRegistration.DoesNotExist:
                existing_user = None
            if not existing_user:
                new_user = MainExamRegistration.objects.create(user=auth_user, 
                                            username = new_username, 
                                            password = current_user.mobile, 
                                            mobile = current_user.mobile)
                new_user.save()
                tec_passed_email_send(new_user)
                return redirect('exam:dashboard')
        except Exception as e:
            print(f'error{e}')

def calculate_score(questions, user_answers):
    """
    Calculate the number of correct answers based on user responses.
    """
    correct_answers = 0
    for question in questions:
        if question.id in user_answers:
            selected_option_id = user_answers[question.id]
            if Option.objects.filter(
                id=selected_option_id, question=question, is_correct=True
            ).exists():
                correct_answers += 1
    return correct_answers  # Return the count of correct answers


from web.models import CentreUserAccount
#@login_required
def main_exam(request):
    MAX_ATTEMPTS = 2
    PASSING_SCORE_PERCENTAGE = 50  
    MAX_MALPRACTICE_WARNINGS = 3  

    user = request.user

    if request.method == "POST":
        submitted_answers = request.POST
        malpractice_attempts = request.session.get("malpractice_attempts", 0)

        question_ids = request.session.get("exam_questions", [])
        questions = MainExamQuestion.objects.filter(id__in=question_ids)

        total_questions = len(questions)
        if total_questions == 0:
            messages.error(request, "Error: No questions found for the exam.")
            return redirect("exam:dashboard")

        correct_answers_count = 0
        for question in questions:
            selected_option_id = submitted_answers.get(f"question_{question.id}")
            if selected_option_id:
                try:
                    selected_option = MainExamOption.objects.get(id=selected_option_id)
                    if selected_option.is_correct:
                        correct_answers_count += 1
                except MainExamOption.DoesNotExist:
                    pass

        score_percentage = (correct_answers_count / total_questions) * 100
        passed = score_percentage >= PASSING_SCORE_PERCENTAGE

        previous_attempts = MainExamProgress.objects.filter(user=user).order_by("-attempt_number")
        attempt_number = 1 if not previous_attempts.exists() else previous_attempts.first().attempt_number + 1

        if previous_attempts.exists() and previous_attempts.first().status == "Passed":
            messages.info(request, "You have already passed the exam.")
            return redirect("exam:dashboard")

        if attempt_number > MAX_ATTEMPTS:
            messages.error(request, "You have reached the maximum number of attempts.")
            return redirect("exam:dashboard")

        # **Fail attempt due to malpractice**
        if malpractice_attempts >= MAX_MALPRACTICE_WARNINGS:
            request.session["malpractice_attempts"] = 0  
            MainExamProgress.objects.create(
                user=user,
                attempt_number=attempt_number,
                correct_answers=0,
                total_questions=total_questions,
                status=f"Failed due to Malpractice (Attempt {attempt_number})",
                completed_at=timezone.now(),
            )
            messages.error(request, "Your exam attempt has been failed due to malpractice.")
            return redirect("exam:dashboard")

        # Save exam progress
        MainExamProgress.objects.create(
            user=user,
            attempt_number=attempt_number,
            correct_answers=correct_answers_count,
            total_questions=total_questions,
            status="Passed" if passed else f"Failed Attempt {attempt_number}",
            completed_at=timezone.now(),
        )

        request.session.pop("exam_questions", None)

        if passed:
            user = request.user
            try:
                passed_user = MainExamProgress.objects.filter(user=request.user, status='Passed').exists()
                temp_user = get_object_or_404(TemporaryUser, user=user)
                try:
                    main_reg = MainExamRegistration.objects.get(user=user)
                except Exception as e:
                    messages.error(request, f'erajhjhfasdfjhaf: {e}')
                if passed_user:
                    temp_user.main_exam_passed = True
                    temp_user.save()
                    main_reg.is_mail_send = True
                    main_reg.is_passed = True
                    main_reg.save()
                    new_username = generate_main_username()
                    user.username = new_username
                    user.save()

                    try:
                        import time
                        map_embed_url = f"https://www.google.com/maps/embed?pb=!1m17!1m12!1m3!1d246.6561038260911!2d{temp_user.longitude}!3d{temp_user.lattitude}!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m2!1m1!2s{temp_user.lattitude},{temp_user.longitude}!5e0!3m2!1sen!2sin!4v{int(time.time())}!5m2!1sen!2sin"
                        centre_user = CentreUserAccount.objects.create(user=user, 
                                                         username=new_username, 
                                                         owner_centre=temp_user.name,
                                                         mobile=temp_user.mobile, 
                                                         photo=temp_user.photo, 
                                                         aadhaar_number=temp_user.aadhaar_number,
                                                         email=temp_user.email, 
                                                         state=temp_user.state,
                                                         district=temp_user.district,
                                                         rural_areas=temp_user.local_body, 
                                                         ward_number=temp_user.ward_number, 
                                                         centre_phone_number=temp_user.mobile,
                                                         pan_card_number='-',
                                                         is_olduser=False,
                                                         centre_name = 'None',
                                                         centre_email = 'None@n.com',
                                                         another_name = temp_user.another_name,
                                                         centre_owner_address = temp_user.address,
                                                         is_approved=False                                                         )
                        centre_user.save()
                        main_email_send(centre_user)
                        messages.success(request, 'successsss')
                    except Exception as e:
                        messages.error(request, f'error creating table{e}')
                        print(e)
                    return render(request, "web/exam/mainexam_congratulations.html", {"score": score_percentage})
            except Exception as e:
                messages.error(request, f'error: {e}')
        else:
            remaining_attempts = MAX_ATTEMPTS - attempt_number
            if remaining_attempts > 0:
                messages.warning(request, f"You scored {score_percentage:.2f}%. {remaining_attempts} attempts left.")
            else:
                messages.error(request, f"You scored {score_percentage:.2f}%. No attempts left.")
            return redirect("exam:dashboard")

    else:
        previous_attempts = MainExamProgress.objects.filter(user=user).order_by("-attempt_number")
        if previous_attempts.exists() and previous_attempts.first().status == "Passed":
            messages.info(request, "You have already passed the exam.")
            return redirect("exam:dashboard")

        if previous_attempts.exists() and previous_attempts.first().attempt_number >= MAX_ATTEMPTS:
            messages.error(request, "You have reached the maximum number of attempts.")
            return redirect("exam:dashboard")

        all_questions = list(MainExamQuestion.objects.prefetch_related("options").all())
        questions = random.sample(all_questions, min(50, len(all_questions)))
        request.session["exam_questions"] = [q.id for q in questions]

        return render(request, "web/exam/main_exam.html", {"questions": questions})


@csrf_exempt
def submit_exam(request):
    if request.method == "POST":
        user = request.user
        submitted_answers = request.POST

        # Fetch all questions
        questions = MainExamQuestion.objects.all()
        total_questions = questions.count()
        correct_answers_count = 0

        # Evaluate answers
        for question in questions:
            selected_option_id = submitted_answers.get(f"question_{question.id}")
            if selected_option_id:
                try:
                    selected_option = MainExamOption.objects.get(id=selected_option_id)
                    if selected_option.is_correct:
                        correct_answers_count += 1
                except MainExamOption.DoesNotExist:
                    pass  # Ignore invalid option selections

        # Calculate score percentage
        score_percentage = (correct_answers_count / total_questions) * 100 if total_questions else 0
        passed = score_percentage >= 50  # Adjust passing score if needed

        # Fetch previous attempts
        progress, created = MainExamProgress.objects.get_or_create(user=user, defaults={"attempt_number": 1})
        
        # Determine attempt number
        attempt_number = progress.attempt_number if not created else 1
        if not created:
            attempt_number += 1

        if attempt_number > 3:
            return JsonResponse(
                {"success": False, "message": "You have reached the maximum number of attempts."},
                status=400,
            )

        # Update progress correctly
        progress.correct_answers = correct_answers_count
        progress.total_questions = total_questions
        progress.attempt_number = attempt_number  # Ensure attempt number is saved
        
        # Determine exam status
        if passed:
            progress.status = "Passed"
        else:
            progress.status = f"Failed Attempt {attempt_number}"

        progress.completed_at = timezone.now()
        progress.save()

        return JsonResponse(
            {
                "success": True,
                "score": score_percentage,
                "pass_exam": passed,
                "redirect_url": "/exam/congratulations/",
            },
            status=200,
        )

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)



@csrf_exempt
def save_video(request):
    if request.method == "POST":
        video_file = request.FILES.get("video_file")
        if video_file:
            user = request.user
            user_registration = TemporaryUser.objects.get(user=user)

            # Save the video file
            filename = f"{user.username}_{uuid.uuid4()}.webm"
            video_record = VideoRecord(
                user_registration=user_registration, video_file=video_file
            )
            video_record.save()

            return JsonResponse({"success": True})
        else:
            return JsonResponse(
                {"success": False, "message": "No video file uploaded."}, status=400
            )
    return JsonResponse(
        {"success": False, "message": "Invalid request method."}, status=400
    )


# @login_required
from .models.user_registration import Certificate
from datetime import datetime

def certificate_payment(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get("razorpay_payment_id")
            order_id = request.POST.get("razorpay_order_id")
            signature = request.POST.get("razorpay_signature")

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Verify payment signature
            client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            })

            # Update user profile
            profile = TemporaryUser.objects.get(user=request.user)
            profile.certificate_paid = True
            profile.save()

            # Create certificate entry
            Certificate.objects.create(user=profile, is_paid=True, time=datetime.today().date())

            return JsonResponse({"status": "success", "message": "Payment successful!"})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"status": "error", "message": "Payment verification failed!"})
    return JsonResponse({"status": "error", "message": "Invalid request!"})


# @login_required
def download_certificate(request):
    # Retrieve the user registration profile
    profile = TemporaryUser.objects.get(user=request.user)

    # Check if the certificate payment has been made
    if profile.certificate_paid:
        # Path to the generated certificate file (PDF)
        certificate_file_path = "/path/to/generated/certificate.pdf"

        # Open the certificate file and prepare a response
        with open(certificate_file_path, "rb") as pdf:
            response = HttpResponse(pdf.read(), content_type="application/pdf")
            response["Content-Disposition"] = 'inline; filename="certificate.pdf"'
            return response
    else:
        # If payment has not been made, show an error message and redirect to the dashboard
        messages.error(request, "You must pay for the certificate before downloading.")
        return redirect("exam:dashboard")


# Get the custom user model from the `web` app
User = get_user_model()


def generate_username():
    """
    Generate a unique username that does not exist in the database.
    """
    while True:
        # Generate a 12-digit random username
        username = "".join([str(random.randint(0, 9)) for _ in range(12)])

        # Check if the username already exists in the custom user model
        if not User.objects.filter(username=username).exists():
            return username


# @login_required
def details_entry(request):
    # Attempt to retrieve or create a UserRegistration object for the current user
    user_registration, created = TemporaryUser.objects.get_or_create(
        user=request.user
    )

    # Handle form submission
    if request.method == "POST":
        # Create a form instance with POST data and files
        form = CentreUserForm(request.POST, request.FILES, request=request)

        # Check if the form is valid
        if form.is_valid():
            # Save the form data, but do not commit to the database yet
            centre_user = form.save(commit=False)

            # Generate a unique username
            username = generate_username()
            password = str(
                centre_user.mobile
            )  # Use the user's mobile number as the password

            # Create a new user with the generated username, password, and email
            user = User.objects.create_user(
                username=username,
                password=password,
                email=centre_user.email,  # Assuming the email field is filled in the form
            )

            # Set the user type to 'centre' and save the user
            user.usertype = "centre"
            user.save()

            # Assign the created user to the form instance and save it to the database
            centre_user.user = user
            centre_user.save()

            # Create a CentreUserAccount for the user
            centre_user_account = CentreUserAccount.objects.create(
                user=user,
                username=username,
                owner_centre=centre_user.centre_name,
                mobile=centre_user.mobile,
                # Add other fields as needed
            )

            # Access the formatted ID from the CentreUserAccount instance
            formatted_id = centre_user_account.formatted_id

            # Send a welcome email to the user with the credentials and formatted ID
            subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
            html_content = (
                f"<p>Thank you for registering. Your account has been created successfully.</p>"
                f"<p><strong>Centre ID:</strong> {formatted_id}</p>"
                f"<p><strong>Username:</strong> {username}</p>"
                f"<p><strong>Password:</strong> {password}</p>"
                f"<p>We recommend you change your password after logging in.</p>"
                f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
                f"<p>Best regards,<br>The SSC Team</p>"
            )

            configuration = Configuration()
            configuration.api_key["api-key"] = settings.BREVO_API_KEY

            api_client = ApiClient(configuration)
            api_instance = transactional_emails_api.TransactionalEmailsApi(api_client)

            email_data = SendSmtpEmail(
                to=[{"email": centre_user.email}],
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
                print(f"Exception when sending email: {e}\n")

            # Redirect to the dashboard after successful form submission
            return redirect("exam:dashboard")
    else:
        # Create a form instance for GET request
        form = CentreUserForm(request=request)

    # Render the details entry page with the form instance
    return render(request, "web/exam/details_entry.html", {"form": form})



def test(request):
    return render(request, "web/exam/test.html")




def gotopayment(request):
    return render(request, "web/exam/cnfm_pymt-btn.html")


import json
from django.http import JsonResponse



def render_button(request):
    return render(request, 'web/js-test.html') 


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


def sbi(request):
    data = {"message": "we are currently working on this stay tuned....!!"}
    return JsonResponse(data)

def temporary_user(request):
    states = RegistrationState.objects.all()
    selected_state = request.POST.get('state')
    districts = RegistrationDistrict.objects.filter(state=selected_state) if selected_state else []

    if request.method == 'POST':
            name = request.POST.get('name')
            photo = request.FILES.get('photo')
            email = request.POST.get('email')
            mobile = request.POST.get('mobile')
            another_name = request.POST.get('another_name')
            state = request.POST.get('state')
            state = get_object_or_404(RegistrationState, state_id=state)
            district = request.POST.get('district')
            district = get_object_or_404(RegistrationDistrict, district_id=district)
            local_body = request.POST.get('local_body')
            panchayat = request.POST.get('panchayat')
            panchayat = get_object_or_404(RegistrationPanchayat, panchayat_id=panchayat)
            ward_number = request.POST.get('ward_number')
            gender = request.POST.get('gender')
            aadhaar_number = request.POST.get('aadhaar_number')
            cheque_passbook = request.FILES.get('cheque_passbook')
            date_of_birth = request.POST.get('date_of_birth')
            lattitude = float(request.POST.get('latitude'))
            longitude = float(request.POST.get('longitude'))
            address = request.POST.get('address')

        # Check if another user is within 1 km
            registered_users = TemporaryUser.objects.filter(main_exam_passed=True)

            for user in registered_users:
                if local_body == 'Corporation' and user.local_body == 'Corporation':
                    if user.lattitude and user.longitude:
                        distance = haversine(lattitude, longitude, user.lattitude, user.longitude)
                        if distance <= 0.5:  
                            return render(request, "web/exam/register.html", {
                            "error": "Another user has already registered in this location. Please try again at another location."
                            })
                else:
                    if user.lattitude and user.longitude:
                        distance = haversine(lattitude, longitude, user.lattitude, user.longitude)
                        if distance <= 1:  
                            return render(request, "web/exam/register.html", {
                            "error": f"Another user has already registered in this location. Please try again at another location. {user.id}"
                            })


            try:
                same_ward_user = CentreUserAccount.objects.filter(is_approved=True,
                                                              rural_areas=local_body, 
                                                              state=state.name, 
                                                              district=district.district_name, 
                                                              ward_number=ward_number).first()
                same_email_user = TemporaryUser.objects.filter(payment=True, email=email).first()
                same_aadhaar_user = TemporaryUser.objects.filter(payment=True, aadhaar_number=aadhaar_number).first()
                same_mobile_user = TemporaryUser.objects.filter(payment=True, mobile=mobile).first()
                if same_email_user:
                    return render(request, "web/exam/register.html", {
                                            "states": states,
                                            "districts": districts,
                                            "selected_state": selected_state, 
                                            'error': 'Another user has already registered with this email'
                                        })
                elif same_ward_user:
                    return render(request, "web/exam/register.html", {
                                            "states": states,
                                            "districts": districts,
                                            "selected_state": selected_state, 
                                            'error': 'Another user has already registered in this location....Please Try again at another location'
                                        })
                elif same_aadhaar_user:
                    return render(request, "web/exam/register.html", {
                                            "states": states,
                                            "districts": districts,
                                            "selected_state": selected_state, 
                                            'error': 'Another user has already registered with this aadhaar number'
                                        })
                elif same_mobile_user:
                    return render(request, "web/exam/register.html", {
                                            "states": states,
                                            "districts": districts,
                                            "selected_state": selected_state, 
                                            'error': 'Another user has already registered with this mobile number'
                                        })


            except Exception as e:
                messages.error(request, 'cannot register this user')

            try:
                # Save User Before Payment
                user = TemporaryUser.objects.create(
                    name=name,
                    photo=photo,
                    email=email,
                    mobile=mobile,
                    another_name=another_name,
                    state=state.name,
                    district=district.district_name,
                    local_body=local_body,
                    panchayat=panchayat.name,
                    ward_number=ward_number,
                    gender=gender,
                    aadhaar_number=aadhaar_number,
                    cheque_passbook=cheque_passbook,
                    date_of_birth=date_of_birth,
                    address=address,
                    lattitude=lattitude,
                    longitude=longitude
                )
                return render(request, "web/exam/cnfm_pymt-btn.html", {
                    'user': user,
                    'amount': 100,
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID
                })
            except Exception as e:
                messages.error(request, f'error{e}')
                print(e)

    # Render Registration Form
    return render(request, "web/exam/register.html", {
        "states": states,
        "districts": districts,
        "selected_state": selected_state
    })
    
    


def create_payment_order(request):

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
    

def payment_success(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        razorpay_order_id = data.get('razorpay_order_id')

        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Verify the payment
        try:
            payment = razorpay_client.payment.fetch(payment_id)
            if payment['status'] == 'captured':
                user_email = payment['email']
                temp_user = TemporaryUser.objects.get(email=user_email)
                temp_user.payment = True
                temp_user.save()

                try:
                    user = User.objects.create_user(username=temp_user.name, password=temp_user.mobile, email=temp_user.email, usertype='centre')
                    temp_user.user = user
                    temp_user.save()

                    username = generate_unique_username(temp_user.id)

                    user.username = username
                    user.save()
                    tec_email_send(temp_user)

                    user_reg_district = get_object_or_404(RegistrationDistrict, district_id=temp_user.district)

                    try:
                        form_data = {
                        'name': username,
                        'mobile': temp_user.mobile,
                        'email': temp_user.email,
                        'another_name': temp_user.another_name,
                        'state': temp_user.state,
                        'district': user_reg_district,
                        'panchayat': temp_user.panchayat,
                        'ward_number': temp_user.ward_number,
                        'gender': temp_user.gender,
                        'aadhaar_number': temp_user.aadhaar_number,
                        'cheque_passbook': temp_user.cheque_passbook,
                        'date_of_birth': temp_user.date_of_birth,
                        'address': temp_user.address,
                        'photo': temp_user.photo,
                        }
                        form = UserRegistrationForm(form_data)
                    
                        if form.is_valid():
                            user_registration = form.save(commit=False)
                            user_registration.user = user
                            user_registration.is_paid = True  # Setting is_paid manually
                            user_registration.save()
                            messages.success(request, "User registration successful.")
                        else:
                            messages.error(request, f"Form errors: {form.errors}")
                    
                    except Exception as e:
                        messages.error(request, f"Error creating user: {e}")
                except Exception as e:
                    print(e)
                return JsonResponse({"success": True, "message": "Payment Successful", "redirect_url": "/exam/userlogin/"})
            else:
                return JsonResponse({"success": False, "message": "Payment Failed"})
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({"success": False, "message": "Signature Verification Failed"})
    return JsonResponse({"success": False, "message": "Invalid request"})



def tec_email_send(user_registration):
    subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
    html_content = (
        f"<p>Thank you for registering. Your account has been created successfully.</p>"
        f"<p><strong>Centre ID:</strong> {user_registration.id}</p>"
        f"<p><strong>Username:</strong> {user_registration.user.username}</p>"
        f"<p><strong>Password:</strong> {user_registration.mobile}</p>"
        f"<p>We recommend you change your password after logging in.</p>"
        f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
        f"<p>Best regards,<br>The SSC Team</p>"
    )

    # Sendinblue Configuration
    configuration = Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_client = ApiClient(configuration)
    api_instance = transactional_emails_api.TransactionalEmailsApi(api_client)

    email_data = SendSmtpEmail(
        to=[{"email": user_registration.email}],
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
        print(f"Exception when sending email: {e}\n")





from .models.user_registration import Complaints
def complaints(request):
    current_user = request.user
    messages = Complaints.objects.filter(user=request.user)
    if request.method == 'POST':
        complaint  = request.POST.get('message')
        try:
            if not request.user.is_superuser:
                Complaints.objects.create(user=request.user, complaint=complaint)
                print('message sent successfully')
                return redirect('exam:complaints')
            else:
                print('user is superuser')
        except Exception as e:
            print(e)
    return render(request, 'web/exam/complaints.html', {'messages': messages, 'current_userr': current_user})






def vlc_register_doc(request):
    return render(request,"web/exam/vlc_register_doc.html")


from math import radians, sin, cos, sqrt, atan2
def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in km
    R = 6371.0  

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Calculate differences
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance =  R * c
    return distance



def certificate_view(request):
    current_user = TemporaryUser.objects.get(user=request.user)
    tec_user = MainExamRegistration.objects.get(user=request.user)
    return render(request, 'web/exam/certificate_pdf.html', {'current_user': current_user, 'tec_user': tec_user})

def certificate_download(request):
    pass


def generate_tec_username(base_username):

    prefix = "TEC"
    base_username = base_username.strip() if base_username else "user"
    username = f"{prefix}{base_username}"
    while MainExamRegistration.objects.filter(username=username).exists():
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        username = f"{prefix}{base_username}{suffix}"
    return username

def tec_passed_email_send(user_registration):
    subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
    html_content = (
        f"<p>Congratulations...!! You have passed the TEC Exams, Here is your new ID</p>"
        f"<p><strong>Username:</strong> {user_registration.username}</p>"
        f"<p><strong>Password:</strong> {user_registration.mobile}</p>"
        f"<p>We recommend you change your password after logging in.</p>"
        f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
        f"<p>Best regards,<br>The SSC Team</p>"
    )

    # Sendinblue Configuration
    configuration = Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_client = ApiClient(configuration)
    api_instance = transactional_emails_api.TransactionalEmailsApi(api_client)

    email_data = SendSmtpEmail(
        to=[{"email": user_registration.user.email}],
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
        print(f"Exception when sending email: {e}\n")



def main_exam_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user_now = MainExamRegistration.objects.get(username=username)
        if user_now.password == password:
            return redirect('exam:document_validation')
    return render(request,"web/exam/main_exam_login.html")

def congratulations_view(request):
    return render(request, "web/exam/mainexam_congratulations.html")





def main_email_send(user_registration):
    subject = "Welcome to the Samatwa Service Centre E-Governance LTD"
    html_content = (
        f"<p>Thank you for registering. Your account has been created successfully.</p>"
        f"<p><strong>Centre ID:</strong> {user_registration.id}</p>"
        f"<p><strong>Username:</strong> {user_registration.user.username}</p>"
        f"<p><strong>Password:</strong> {user_registration.mobile}</p>"
        f"<p>We recommend you change your password after logging in.</p>"
        f"<p>For more information, visit our website: <a href='https://sscegov.com'>https://sscegov.com</a></p>"
        f"<p>Best regards,<br>The SSC Team</p>"
    )

    # Sendinblue Configuration
    configuration = Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_client = ApiClient(configuration)
    api_instance = transactional_emails_api.TransactionalEmailsApi(api_client)

    email_data = SendSmtpEmail(
        to=[{"email": user_registration.email}],
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
        print(f"Exception when sending email: {e}\n")


def generate_main_username():
    numeric_suffix = "".join(random.choices(string.digits, k=12))  
    username = numeric_suffix  
    
    while User.objects.filter(username=username).exists():
        numeric_suffix = "".join(random.choices(string.digits, k=12))  
        username = numeric_suffix

    return username

from datetime import datetime
from .models.user_registration import Certificate
def main_certificate(request):
    temp_user = TemporaryUser.objects.get(user=request.user)
    current_user = Certificate.objects.get(user=temp_user)
    date = current_user.time.date()
    return render(request, 'web/exam/main_certificate.html', {'current_user': current_user, 'date': date})


from .models.user_registration import Resources
def resources(request):
    resources = Resources.objects.all()
    return render(request, 'web/home/resources.html', {'resources': resources})



from .models.user_registration import DocumentValidation
import base64
from django.core.files.base import ContentFile
def document_validation(request):
    user = request.user
    user = get_object_or_404(TemporaryUser, user=user)
    existing_data = DocumentValidation.objects.filter(user=user).filter().exists()
    if existing_data:
        return redirect('exam:main_exam')
    return render(request, 'web/exam/document_validation.html')

@csrf_exempt
def upload_images(request):
    if request.method == "POST":
        aadhaar = request.POST.get("aadhaar_image")
        photo = request.POST.get("user_image")

        if aadhaar and photo:
            format, aadhaar_str = aadhaar.split(';base64,')
            format, user_str = photo.split(';base64,')
            
            aadhaar = ContentFile(base64.b64decode(aadhaar_str), name="aadhaar.jpg")
            photo = ContentFile(base64.b64decode(user_str), name="user.jpg")

            user = TemporaryUser.objects.get(user=request.user)

            DocumentValidation.objects.create(user=user, aadhaar=aadhaar, photo=photo)

            return JsonResponse({"message": "Images uploaded successfully!" , 
                                 "redirect_url": "/exam/main-exam/"}, status=201)
    
    return JsonResponse({"error": "Invalid request"}, status=400)
