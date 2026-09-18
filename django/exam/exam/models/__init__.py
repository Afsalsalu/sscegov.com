from .exam_category import ExamCategory
from .exam_progress import MainExamProgress, TecExamProgress
from .option import MainExamOption, Option
from .payment import Payment
from .question import MainExamQuestion, Question
from .user_registration import UserRegistration, VideoRecord
# exam/admin/user_registration_admin.py
from exam.models import RegistrationState, RegistrationDistrict, RegistrationPanchayat



# exam/admin/user_registration_admin.py

from django.apps import apps

RegistrationState = apps.get_model('exam', 'RegistrationState')
RegistrationDistrict = apps.get_model('exam', 'RegistrationDistrict')
RegistrationPanchayat = apps.get_model('exam', 'RegistrationPanchayat')

from .user_registration import RegistrationState, RegistrationDistrict, RegistrationPanchayat

