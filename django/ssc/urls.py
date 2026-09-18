"""
URL configuration for ssc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include   
from django.conf import settings
from django.conf.urls.static import static

from django.http import HttpResponse   # 👈 add this import

def validation_file(request):
        return HttpResponse(
         "C57323CB23BD517259FD2C5242DAE41F2B37DA1EC415D1B03138F8766F86C7C7\nsectigo.com\n20250911115349am",
          content_type="text/plain"
       )  



urlpatterns = [
    path("sscegovadmin/", admin.site.urls),
    path("", include("web.urls")),
    path("exam/", include("exam.urls")),
    path("accounts/", include("registration.backends.simple.urls")),
    path("captcha/", include("captcha.urls")),

    path(".well-known/pki-validation/17184DA9C3A1EFE2D8422CDA551CA59E.txt", validation_file),

]+static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
