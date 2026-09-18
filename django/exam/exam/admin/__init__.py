# Importing admin classes to ensure they are registered with the Django admin site

from .exam_category_admin import *  # Importing ExamCategory related admin classes
from .exam_progress_admin import *  # Importing ExamProgress related admin classes
from .option_admin import *  # Importing Option related admin classes
from .payment_admin import *  # Importing Payment related admin classes
from .question_admin import *  # Importing Question related admin classes
from .question_admin import MainExamQuestionAdmin
from .user_registration_admin import *  # Importing UserRegistration related admin classes
