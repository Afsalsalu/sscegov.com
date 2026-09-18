from django.urls import path

from .import views
from .views import UserRegistrationView,csp_report_endpoint,csp_violation_report,csp_report_view

app_name = "exam"

urlpatterns = [
    # User registration - ensure that registration is secure and validates input thoroughly
    path("register/", UserRegistrationView.as_view(), name="entrepreneur_register"),
    path("register/payment_callback/<int:user_id>", views.payment_callback, name="payment_callback"),
    path(
        "download/certificate/", views.certificate_download, name="certificate_download"
    ),
    path("certificate/", views.certificate_view, name="certificate_view"),    # User login - Ensure login view is secure, consider using Django's built-in auth system
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
    path("certificate_payment/", views.certificate_payment, name="certificate_payment"),
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
    
    path('create_payment_order/', views.create_payment_order, name='create_payment_order'),
    path('payment_success/', views.payment_success, name='payment_success'),

    path('complaints/', views.complaints, name='complaints'),
    path("vlcregistrationdoc/", views.vlc_register_doc, name="vlcregistrationdoc"),
    path("main_exam_login/", views.main_exam_login, name="main_exam_login"),

    path("main_certificate/", views.main_certificate, name="main_certificate"),
    path("resources/", views.resources, name="resources"),

    path("document_validation/", views.document_validation, name="document_validation"),
    path('upload/', views.upload_images, name='upload_images'),

]
