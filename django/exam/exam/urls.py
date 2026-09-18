from django.urls import path

from .import views
from .views import CertificateView, UserRegistrationView,csp_report_endpoint,csp_violation_report,csp_report_view

app_name = "exam"

urlpatterns = [
    # User registration - ensure that registration is secure and validates input thoroughly
    path("register/", UserRegistrationView.as_view(), name="entrepreneur_register"),
    path("register/payment_callback/", views.payment_callback, name="payment_callback"),
    path(
        "download/certificate/", CertificateView.as_view(), name="certificate_download"
    ),
    path("certificate/", CertificateView.as_view(), name="certificate_view"),
    # User login - Ensure login view is secure, consider using Django's built-in auth system
    path("userlogin/", views.login_view, name="entrepreneur_userlogin"),
    # User logout - Requires authentication, ensures user is logged out securely
    path("logout_view/", views.logout_view, name="logout_view"),
    # Dashboard - Ensure only authorized users can access
    path("dashboard/", views.admin_dashboard, name="dashboard"),
    # Learning and assessment pages - Consider using permissions or restrictions if needed
    path("learning/", views.learning, name="learning"),
    path("assessments/", views.assessments, name="assessments"),
    # Exam-related views - Ensure these are protected for authenticated users
    path("take-exam/<int:exam_id>/", views.take_exam, name="take_exam"),
    path("main-exam/", views.main_exam, name="main_exam"),
    path("submit_exam/", views.submit_exam, name="submit_exam"),
    # Certificate-related views - Protect these routes as they involve financial transactions
    path("certificate-payment/", views.certificate_payment, name="certificate_payment"),
    path(
        "download-certificate/", views.download_certificate, name="download_certificate"
    ),
    # Details entry - Ensure only authenticated users can access and submit
    path("details-entry/", views.details_entry, name="details_entry"),
    path("test/", views.test, name="test"),
    path("exam/save_video/", views.save_video, name="save_video"),
    path('register/get_districts/', views.get_districts, name='get_districts'),  
    path('register/get_panchayats/', views.get_panchayats, name='get_panchayats'),  

    path("gotopayment/", views.gotopayment, name="gotopayment"),


    path('csp-report-endpoint', csp_report_endpoint, name='csp_report_endpoint'),



    path('csp-violation-report/', csp_violation_report, name='csp_violation_report'),
    path("csp-report-endpoint", csp_report_view, name="csp_report"),

    path('csp-violation-report/', csp_violation_report, name='csp_violation_report'),
    path('csp-report-endpoint', csp_report_endpoint, name='csp_report_endpoint'),
    path('csp-report-endpoint', views.csp_report_view),

    path("csp-report-endpoint", csp_report_view, name="csp_report"),

    path("register/sbi/", views.sbi, name="sbi"),
    path("temporary_user/", views.temporary_user, name="temporary_user"),

]
