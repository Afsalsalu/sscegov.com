# exam/models/user_registration.py
from django.conf import settings
from django.db import models


class TemporaryUser(models.Model):
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

    def __str__(self):
        return self.name
    




class UserRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
    certificate_paid = models.BooleanField(default=False)
    certificate_downloaded = models.BooleanField(default=False)
    details_filled = models.BooleanField(default=False)

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


class VideoRecord(models.Model):
    user_registration = models.ForeignKey(
        UserRegistration, related_name="video_records", on_delete=models.CASCADE
    )
    video_file = models.FileField(upload_to="videos/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"VideoRecord for {self.user_registration.name}"









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
    panchayat_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ['state', 'district', 'panchayat_name']

    def __str__(self):
        return self.panchayat_name

    @property
    def state_id(self):
        return self.state.state_id  # Accessing the state_id from the related RegistrationState model

    @property
    def district_id(self):
        return self.district.district_id  # Accessing the district_id from the related RegistrationDistrict model

