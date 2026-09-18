# exam/models/user_registration.py
from django.conf import settings
from django.db import models


class TemporaryUser(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    another_name = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=100)
    district = models.CharField(db_column='district_id', max_length=100)
    local_body = models.CharField(max_length=30, default='Panchayath',
        choices=[
            ("Panchayath", "Panchayath"),
            ("Muncipality", "Muncipality"),
            ("Corporation", "Corporation"),
        ],)
    panchayat = models.CharField(max_length=255)  # Panchayat/Municipality/Corporations
    ward_number = models.CharField(max_length=20)  # Added field for ward number
    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("transgender", "Transgender"),
        ],
    )
    aadhaar_number = models.CharField(max_length=12, unique=True)  # Aadhaar Number
    cheque_passbook = models.ImageField(upload_to="documents/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=455)
    photo = models.ImageField(upload_to="photos/", null=True, blank=True)
    payment = models.BooleanField(default=False)
    registration_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    certificate_paid = models.BooleanField(default=False)
    certificate_downloaded = models.BooleanField(default=False)
    lattitude = models.FloatField(max_length=500, null=True, blank=True)
    longitude = models.FloatField(max_length=500, null=True, blank=True)
    main_exam_passed = models.BooleanField(default=False)
    def __str__(self):
        return self.name
    




class UserRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    another_name = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=100)
    district = models.CharField(db_column='district_id', max_length=100)
    panchayat = models.CharField(max_length=255)  # Panchayat/Municipality/Corporations
    ward_number = models.CharField(max_length=20)  # Added field for ward number
    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("transgender", "Transgender"),
        ],
    )
    aadhaar_number = models.CharField(max_length=12, unique=True)  # Aadhaar Number
    cheque_passbook = models.ImageField(upload_to="documents/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=455)
    photo = models.ImageField(upload_to="photos/", null=True, blank=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    pan = models.ImageField(upload_to="pan/", null=True, blank=True)
    certificate_paid = models.BooleanField(default=False)
    certificate_downloaded = models.BooleanField(default=False)

    def __str__(self):
        return self.name


    def all_main_exams_passed(self):
        """
        Check if all main exams have been passed by this user.
        """
        from exam.models import \
            MainExamProgress  # Import inside method to avoid circular import

        # Ensure that 'user' in MainExamProgress is an instance of the User model
        progress_records = MainExamProgress.objects.filter(user=self.user)
        return all(progress.status == "Passed" for progress in progress_records)














from django.db import models

class RegistrationState(models.Model):
    state_id = models.AutoField(primary_key=True)  # Explicitly defining an auto-incrementing ID field
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class RegistrationDistrict(models.Model):
    district_id = models.AutoField(primary_key=True)  # Explicitly defining an auto-incrementing ID field
    state = models.ForeignKey(RegistrationState, on_delete=models.CASCADE)
    district_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['state', 'district_name']

    def __str__(self):
        return self.district_name

    @property
    def state_id(self):
        return self.state.state_id  # Explicitly returning the state_id from the related RegistrationState model


class RegistrationPanchayat(models.Model):
    panchayat_id = models.AutoField(primary_key=True)  # Explicitly defining an auto-incrementing ID field
    state = models.ForeignKey(RegistrationState, on_delete=models.CASCADE)
    district = models.ForeignKey(RegistrationDistrict, on_delete=models.CASCADE)
    local_body = models.CharField(max_length=30, default='Panchayath',
        choices=[
            ("Panchayath", "Panchayath"),
            ("Muncipality", "Muncipality"),
            ("Corporation", "Corporation"),
        ],)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['state', 'district', 'name']

    def __str__(self):
        return self.name

    @property
    def state_id(self):
        return self.state.state_id  # Accessing the state_id from the related RegistrationState model

    @property
    def district_id(self):
        return self.district.district_id  # Accessing the district_id from the related RegistrationDistrict model


class Complaints(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    complaint = models.TextField()
    reply = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)



class MainExamRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)
    is_passed = models.BooleanField(default=False)
    is_mail_send = models.BooleanField(default=False)


class Certificate(models.Model):
    user = models.ForeignKey(TemporaryUser, on_delete=models.CASCADE)
    time = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)


class Resources(models.Model):
    description = models.CharField(max_length=255)
    file = models.FileField(upload_to="resources/")



class DocumentValidation(models.Model):
    user = models.OneToOneField(TemporaryUser, on_delete=models.CASCADE, null=True, blank=True, unique=True)
    photo = models.ImageField(upload_to="document_validation/")
    aadhaar = models.ImageField(upload_to="document_validation/")
