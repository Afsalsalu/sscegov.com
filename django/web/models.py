import uuid

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from .storages import FranchiseEnquiryStorage

from .constants import PaymentStatus
from .whatsapp_utils import normalize_whatsapp_number

# Create your models here.


class UserSession(Session):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-expire_date"]


class CustomUserManager(BaseUserManager):
    def normalize_username(self, username):
        return username.lower().strip()

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The username field must be set")
        username = self.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = "username"
    preferred_language = models.CharField(max_length=10, blank=True, default="")
    usertype = models.CharField(
        max_length=128,
        choices=[
            ("HeadOffice", "HeadOffice"),
            ("State", "State"),
            ("Employee", "Employee"),
            ("centre", "centre"),
            ("subcentre", "subcentre"),
        ],
        default="Administrator",
    )
    objects = CustomUserManager()

    def change_password(self, new_password):
        self.password = make_password(new_password)
        self.save()


class FailedLoginAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.ip_address} at {self.timestamp}"
# /////////////////////////////////////////// HOME PAGE MODELS  //////////////////////////////////////////// #


class AboutPage(models.Model):
    main_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="Samatwa Service Centre E-Governance LTD",
    )
    main_text = models.TextField(blank=True, null=True)
    main_image1 = models.ImageField(upload_to="media/", blank=True, null=True)
    main_image2 = models.ImageField(upload_to="media/", blank=True, null=True)
    main_image3 = models.ImageField(upload_to="media/", blank=True, null=True)
    main_image4 = models.ImageField(upload_to="media/", blank=True, null=True)
    mission_title = models.CharField(
        max_length=100, blank=True, null=True, default="Mission"
    )
    mission_text = models.TextField(blank=True, null=True)
    vision_title = models.CharField(
        max_length=100, blank=True, null=True, default="Vision"
    )
    vision_text = models.TextField(blank=True, null=True)
    topic_image1 = models.ImageField(upload_to="media/", blank=True, null=True)
    topic_title1 = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="Partner with SSC: Unlock Opportunities with Our Franchise",
    )
    topic_text1 = models.TextField(blank=True, null=True)
    topic_image2 = models.ImageField(upload_to="media/", blank=True, null=True)
    topic_title2 = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="Empowering Government Services Across India",
    )
    topic_text2 = models.TextField(blank=True, null=True)
    blog_title = models.CharField(
        max_length=100, blank=True, null=True, default="Transformation"
    )
    blog_text = models.TextField(blank=True, null=True)

    def __str__(self):
        return "About Page Content"


class AboutBlog(models.Model):
    image = models.ImageField(upload_to="media/", blank=True, null=True)
    mini_title = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    text = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title


class HomeService(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="media/servicelogo")

    def __str__(self):
        return self.name


class HomeCompleteSolutions(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to="media")

    def __str__(self):
        return self.title


class HomeLogoBrand(models.Model):
    image = models.ImageField(upload_to="media")


class Contact(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    centre_name = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    taluk = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Media(models.Model):
    image = models.ImageField(upload_to="media/")
    sub_title = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    content = models.CharField(max_length=255)
    place = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def update_service(self, **kwargs):
        """
        Update the service attributes with the provided kwargs.
        """
        for field, value in kwargs.items():
            setattr(self, field, value)
        self.save()

    def __str__(self):
        return self.title


class Career(models.Model):
    name_of_host = models.CharField(max_length=255)
    experience = models.CharField(max_length=255)
    qualification = models.CharField(max_length=255)
    salary = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def update_service(self, **kwargs):
        """
        Update the service attributes with the provided kwargs.
        """
        for field, value in kwargs.items():
            setattr(self, field, value)
        self.save()


class CareerForm(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    job_title = models.CharField(max_length=100)
    experience_years = models.IntegerField()
    qualification = models.CharField(max_length=100)
    age = models.IntegerField()
    current_role = models.CharField(max_length=50)
    resume = models.FileField(upload_to="resumes/")
    experience_level = models.CharField(max_length=255)
    work_preference = models.CharField(max_length=50)
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Ensure this line is present

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["-created_at"]  # Ensure this matches the field name


# /////////////////////////////////////////// HOME PAGE MODELS END //////////////////////////////////////////// #


class State(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="state", null=True
    )
    name = models.CharField(max_length=255)
    mobile = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )
    photo = models.ImageField(upload_to="media/", blank=True, null=True)
    aadhaar_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    aadhaar_number = models.BigIntegerField(
        validators=[MaxValueValidator(999999999999), MinValueValidator(100000000000)]
    )
    pan_card_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    pan_card_number = models.CharField(max_length=10)
    sign_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    email = models.EmailField()
    STATE_CHOICES = [
        ("andhrapradesh", "Andhra Pradesh"),
        ("arunachalpradesh", "Arunachal Pradesh"),
        ("assam", "Assam"),
        ("bihar", "Bihar"),
        ("chhattisgarh", "Chhattisgarh"),
        ("goa", "Goa"),
        ("gujarat", "Gujarat"),
        ("haryana", "Haryana"),
        ("himachalpradesh", "Himachal Pradesh"),
        ("jharkhand", "Jharkhand"),
        ("karnataka", "Karnataka"),
        ("kerala", "Kerala"),
        ("madhyapradesh", "Madhya Pradesh"),
        ("maharashtra", "Maharashtra"),
        ("manipur", "Manipur"),
        ("meghalaya", "Meghalaya"),
        ("mizoram", "Mizoram"),
        ("nagaland", "Nagaland"),
        ("odisha", "Odisha"),
        ("punjab", "Punjab"),
        ("rajasthan", "Rajasthan"),
        ("sikkim", "Sikkim"),
        ("tamilnadu", "Tamil Nadu"),
        ("telangana", "Telangana"),
        ("tripura", "Tripura"),
        ("uttarpradesh", "Uttar Pradesh"),
        ("uttarakhand", "Uttarakhand"),
        ("westbengal", "West Bengal"),
        ("andamanandnicobarislands", "Andaman and Nicobar Islands"),
        ("chandigarh", "Chandigarh"),
        ("dadra&Nagarhavelianddaman&diu", "Dadra & Nagar Haveli and Daman & Diu"),
        ("delhi", "Delhi"),
        ("jammuandkashmir", "Jammu and Kashmir"),
        ("ladakh", "Ladakh"),
        ("lakshadweep", "Lakshadweep"),
        ("puducherry", "Puducherry"),
    ]
    state = models.CharField(max_length=100, choices=STATE_CHOICES)
    District = models.CharField(max_length=355)
    taluk = models.CharField(max_length=50, blank=True)
    pin_code = models.IntegerField()
    address = models.CharField(max_length=550, blank=True)


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class HeadOffice(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="HeadOffice", null=True
    )
    name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to="media", blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=255)


class CentreUserAccount(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="centre", null=True
    )
    name = models.CharField(max_length=255, blank=True, null=True, default="None")
    username = models.CharField(max_length=100, null=True, blank=True, unique=True)
    owner_centre = models.CharField(max_length=100)
    mobile = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )
    alternative_mobile = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)],
        blank=True,
        null=True,
    )
    photo = models.ImageField(upload_to="media/", blank=True, null=True)
    aadhaar_front_side_uploading = models.ImageField(
        upload_to="media/", blank=True, null=True
    )
    aadhaar_back_side_uploading = models.ImageField(
        upload_to="media/", blank=True, null=True
    )
    aadhaar_number = models.BigIntegerField(
        validators=[MaxValueValidator(999999999999), MinValueValidator(100000000000)]
    )
    pan_card_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    pan_card_number = models.CharField(max_length=10, blank=True, null=True)
    sign_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    another_document = models.ImageField(upload_to="media/", blank=True, null=True)
    email = models.EmailField()
    centre_owner_address = models.CharField(max_length=255, null=True, blank=True)
    centre_name = models.CharField(max_length=100, null=True, blank=True)
    centre_phone_number = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )
    STATE_CHOICES = [
        ("andhrapradesh", "Andhra Pradesh"),
        ("arunachalpradesh", "Arunachal Pradesh"),
        ("assam", "Assam"),
        ("bihar", "Bihar"),
        ("chhattisgarh", "Chhattisgarh"),
        ("goa", "Goa"),
        ("gujarat", "Gujarat"),
        ("haryana", "Haryana"),
        ("himachalpradesh", "Himachal Pradesh"),
        ("jharkhand", "Jharkhand"),
        ("karnataka", "Karnataka"),
        ("kerala", "Kerala"),
        ("madhyapradesh", "Madhya Pradesh"),
        ("maharashtra", "Maharashtra"),
        ("manipur", "Manipur"),
        ("meghalaya", "Meghalaya"),
        ("mizoram", "Mizoram"),
        ("nagaland", "Nagaland"),
        ("odisha", "Odisha"),
        ("punjab", "Punjab"),
        ("rajasthan", "Rajasthan"),
        ("sikkim", "Sikkim"),
        ("tamilnadu", "Tamil Nadu"),
        ("telangana", "Telangana"),
        ("tripura", "Tripura"),
        ("uttarpradesh", "Uttar Pradesh"),
        ("uttarakhand", "Uttarakhand"),
        ("westbengal", "West Bengal"),
        ("andamanandnicobarislands", "Andaman and Nicobar Islands"),
        ("chandigarh", "Chandigarh"),
        ("dadra&Nagarhavelianddaman&diu", "Dadra & Nagar Haveli and Daman & Diu"),
        ("delhi", "Delhi"),
        ("jammuandkashmir", "Jammu and Kashmir"),
        ("ladakh", "Ladakh"),
        ("lakshadweep", "Lakshadweep"),
        ("puducherry", "Puducherry"),
    ]
    state = models.CharField(max_length=255, choices=STATE_CHOICES)
    district = models.CharField(max_length=255, blank=True, null=True)
    taluk = models.CharField(max_length=50, blank=True)
    RURALAREAS_CHOICES = [
        ("panchayat", "panchayat"),
        ("municipality", "municipality"),
        ("corporation", "corporation"),
    ]
    rural_areas = models.CharField(
        max_length=255, choices=RURALAREAS_CHOICES, blank=True, null=True
    )
    ward_number = models.CharField(max_length=55, null=True, blank=True)
    pin_code = models.IntegerField(blank=True, null=True)
    centre_email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=550, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_centre_users",
    )
    certificate_paid = models.BooleanField(default=False)
    certificate_downloaded = models.BooleanField(default=False)
    location = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_olduser = models.BooleanField(default=False)
    another_name = models.CharField(max_length=1025, default='-', blank=True)

    def __str__(self):
        return self.owner_centre

    @property
    def formatted_id(self):
        # Check if the id is None and return a default string or empty string
        return f"{self.id:06d}" if self.id is not None else "000000"


def franchise_enquiry_attachment_path(instance, filename):
    """Use an opaque name and a server-controlled directory for enquiry uploads."""
    from pathlib import Path
    from uuid import uuid4

    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}:
        extension = ".bin"
    return f"franchise_enquiries/{uuid4().hex}{extension}"


class FranchiseEnquiry(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REPLIED = "replied", "Replied"
        CLOSED = "closed", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="franchise_enquiries",
        null=True,
        blank=True,
    )
    centre = models.ForeignKey(
        CentreUserAccount,
        on_delete=models.SET_NULL,
        related_name="enquiries",
        null=True,
        blank=True,
    )
    franchise_centre_name = models.CharField(max_length=255)
    franchise_user_name = models.CharField(max_length=255)
    franchise_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=10000)
    attachment = models.FileField(
        upload_to=franchise_enquiry_attachment_path,
        storage=FranchiseEnquiryStorage(),
        blank=True,
        null=True,
    )
    original_notification_message_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_reply = models.TextField(blank=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="replied_franchise_enquiries",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Franchise enquiry"
        verbose_name_plural = "Franchise enquiries"

    def __str__(self):
        return f"Enquiry #{self.pk}: {self.subject}"

class CertificatePayment(models.Model):
    user_registration = models.ForeignKey(CentreUserAccount, on_delete=models.CASCADE)
    amount = models.FloatField(default=2.0)  # Set amount to 2 INR
    status = models.CharField(
        max_length=254, choices=PaymentStatus.CHOICES, default=PaymentStatus.PENDING
    )
    provider_order_id = models.CharField(max_length=40)
    payment_id = models.CharField(max_length=36)
    signature_id = models.CharField(max_length=128)
    is_certificate_payment = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user_registration.name} - {self.amount} - {self.status}"


class KeralaSubCentre(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="Subcentre", null=True
    )
    username = models.CharField(max_length=100)
    center_owner_name = models.CharField(max_length=100)
    mobile = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )
    photo = models.ImageField(upload_to="media/", blank=True, null=True)
    aadhaar_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    aadhaar_number = models.BigIntegerField(
        validators=[MaxValueValidator(999999999999), MinValueValidator(100000000000)]
    )
    pan_card_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    pan_card_number = models.CharField(max_length=10)
    sign_uploading = models.ImageField(upload_to="media/", blank=True, null=True)
    email = models.EmailField()
    center_owner_address = models.TextField()
    # Centre Details
    center_name = models.CharField(max_length=100)
    client_name = models.CharField(max_length=100)
    centre_phone_number = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )
    state = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    taluk = models.CharField(max_length=50, blank=True)
    pin_code = models.IntegerField()
    address = models.TextField()

    def __str__(self):
        return self.center_name


class Wallet(models.Model):
    amount = models.FloatField(default=0.0)


class Banner(models.Model):
    image = models.ImageField(upload_to="banners/")
    display_order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]


class Employee(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employee", null=True
    )
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    position = models.ForeignKey(Department, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    mobile = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )

    def __str__(self):
        return self.name


# ////////////////////////////////////////////// CENTRE MODELS  ////////////////////////////////////////////// #


class AddState(models.Model):
    logo = models.ImageField(upload_to="media")
    state_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    whatsapp_number = models.CharField(max_length=15, blank=True, default="")
    whatsapp_enabled = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        try:
            self.whatsapp_number = normalize_whatsapp_number(self.whatsapp_number)
        except ValidationError as exc:
            raise ValidationError({"whatsapp_number": exc.messages}) from exc

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.state_name)
        self.whatsapp_number = normalize_whatsapp_number(self.whatsapp_number)
        super(AddState, self).save(*args, **kwargs)

    def __str__(self):
        return self.state_name


class StateService(models.Model):
    state = models.ForeignKey(
        AddState, on_delete=models.CASCADE, related_name="services"
    )
    service_name = models.CharField(max_length=100)
    service_logo = models.ImageField(upload_to="media/servicelogo")
    service_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    service_details = models.TextField(blank=True, default="")

    def __str__(self):
        return self.service_name


def online_class_video_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp4"
    return f"online_classes/videos/{uuid.uuid4().hex}.{extension}"


class OnlineClass(models.Model):
    title = models.CharField(max_length=255)
    class_video_link = models.URLField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to="media/", blank=True, null=True)
    video_file = models.FileField(
        upload_to=online_class_video_upload_to, blank=True, null=True
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def update_service(self, **kwargs):
        """
        Update the service attributes with the provided kwargs.
        """
        for field, value in kwargs.items():
            setattr(self, field, value)
        self.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "online-class"
            candidate = base_slug
            suffix = 2
            queryset = type(self).objects.all()
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            while queryset.filter(slug=candidate).exists():
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class DownloadForm(models.Model):
    title = models.CharField(max_length=255)
    pdf = models.FileField(upload_to="media/downloadform")
    state = models.ForeignKey(
        AddState,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="download_forms",
    )
    service = models.ForeignKey(
        StateService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="download_forms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def update_service(self, **kwargs):
        """
        Update the service attributes with the provided kwargs.
        """
        for field, value in kwargs.items():
            setattr(self, field, value)
        self.save()


class Software(models.Model):
    title = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="media/logo")
    site_link = models.URLField(blank=True, null=True)


class LatestNewsCentre(models.Model):
    image = models.ImageField(upload_to="media/news")
    title = models.CharField(max_length=55)
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


# ///////////////////////////////////////////// CENTRE MODELS END ////////////////////////////////////////////// #


      








class Wallet(models.Model):
    amount = models.FloatField(default=0.0)


class ExamVideo(models.Model):
    video = models.FileField(upload_to='exam_videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee", null=True
    )
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    position = models.ForeignKey(Department, on_delete=models.CASCADE)
    date_of_birth = models.DateField()
    mobile = models.BigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)]
    )

    def __str__(self):
        return self.name


                           
class HomeService(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='media')

    def __str__(self):
        return self.name
    
    
class HomeCompleteSolutions(models.Model):
    title = models.CharField(max_length=255)
    description  = models.TextField()
    image = models.ImageField(upload_to='media')

    def __str__(self):
        return self.title


class HomeLogoBrand(models.Model):
    image = models.ImageField(upload_to='media')


def service_detail_image_upload_to(instance, filename):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"media/service-details/{uuid.uuid4().hex}.{suffix}"


class StateServiceDetailImage(models.Model):
    service = models.ForeignKey(
        StateService, on_delete=models.CASCADE, related_name="detail_images"
    )
    image = models.ImageField(upload_to=service_detail_image_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
    


    



# //////////////////////////////////////////// ACCOUNTS MODELS START //////////////////////////////////////////// #

# ACCOUNT MASTER

# class AccountMaster(models.Model):
#     account_code = models.IntegerField()
#     opbal = models.FloatField()
#     curbal = models.FloatField()
#     drcr = models.CharField(max_length=100)
#     disp = models.CharField(max_length=1)
#     coid = models.CharField(max_length=1)
#     brid = models.CharField(max_length=1)
#     FYCcode = models.CharField(max_length=1)


    def __str__(self):
        return self.account_code


from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.db.models import Max
from django.db import IntegrityError


class Table_Accountsmaster(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accounts', null=True, blank=True)
    account_code = models.IntegerField(blank=True, null=True)
    head = models.CharField(max_length=100)

    GROUP_CHOICES = [
        ('LIABILITIES', 'LIABILITIES'),
        ('INCOME', 'INCOME'),
        ('EXPENSES', 'EXPENSES'),
        ('TRADING EXPENSES', 'TRADING EXPENSES'),
        ('TRADING INCOME', 'TRADING INCOME'),
        ('CURRENT ASSET', 'CURRENT ASSET'),
        ('FIXED ASSETS', 'FIXED ASSETS'),
        ('CURRENT LIABILITIES', 'CURRENT LIABILITIES'),
        ('INDIRECT INCOME', 'INDIRECT INCOME'),
        ('INDIRECT EXPENSES', 'INDIRECT EXPENSES'),
        ('SUNDRY DEBTORS', 'SUNDRY DEBTORS'),
        ('SUNDRY CREDITORS', 'SUNDRY CREDITORS'),
        ('CASH AT BANK', 'CASH AT BANK'),
        ('DUTIES AND TAXES', 'DUTIES AND TAXES'),
        ('LOANS', 'LOANS'),
        ('CAPITAL ACCOUNT', 'CAPITAL ACCOUNT'),
    ]

    group = models.CharField(max_length=249, choices=GROUP_CHOICES)

    CATEGORY_CHOICES = [
        ('Accounts', 'Accounts'),
        ('Cashbook', 'Cashbook'),
        ('Bank', 'Bank'),
        ('Customers', 'Customers'),
        ('Suppliers', 'Suppliers'),
    ]
    category = models.CharField(max_length=249, choices=CATEGORY_CHOICES)

    PRICEGROUP_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
    ]
    pricegroup = models.CharField(max_length=249, null=True, blank=True, choices=PRICEGROUP_CHOICES)

    DEBIT_CREDIT_CHOICES = [
        ('Debit', 'Debit'),
        ('Credit', 'Credit'),
    ]
    debitcredit = models.CharField(max_length=249, choices=DEBIT_CREDIT_CHOICES)

    gstno = models.CharField(max_length=255, null=True, blank=True)
    address1 = models.CharField(max_length=299, null=True, blank=True)
    state = models.CharField(max_length=249, null=True, blank=True)
    address2 = models.CharField(max_length=299, null=True, blank=True)
    statecode = models.CharField(max_length=249, null=True, blank=True)
    address3 = models.CharField(max_length=249, null=True, blank=True)
    panno = models.CharField(max_length=249, null=True, blank=True)
    district = models.CharField(max_length=249, null=True, blank=True)
    creditlimit = models.CharField(max_length=249, null=True, blank=True)
    email = models.CharField(max_length=249, null=True, blank=True)
    creditdays = models.CharField(max_length=249, null=True, blank=True)
    telno = models.CharField(max_length=50, null=True, blank=True)
    mobile = models.CharField(max_length=10, null=True, blank=True)
    opbalance = models.IntegerField(null=True, blank=True, default=0)
    whattsapp = models.CharField(max_length=249, null=True, blank=True)
    currentbalance = models.CharField(max_length=249, null=True, blank=True)  # Ensure this matches your model definition
    slug = models.SlugField(max_length=250, blank=True, null=True)


    def save(self, *args, **kwargs):
        if not self.account_code:
            last_id = Table_Accountsmaster.objects.filter(user=self.user).aggregate(max_id=Max('account_code'))['max_id']
            self.account_code = (last_id or 999) + 1

        if self.head:
            self.head = self.head.upper()

        if not self.slug:
            base_slug = slugify(self.head)
            unique_slug = base_slug
            num = 1
            while Table_Accountsmaster.objects.filter(slug=unique_slug, user=self.user).exists():
                unique_slug = f"{base_slug}-{num}"
                num += 1
            self.slug = unique_slug

        if self.whattsapp is None:
            self.whattsapp = ""

        super(Table_Accountsmaster, self).save(*args, **kwargs)

        # Ensure the corresponding Table_Acntchild instance is created or updated
        Table_Acntchild.objects.update_or_create(
            account_master=self,
            defaults={
                'account_code': self.account_code,
                'openning_balance': self.opbalance,
                'current_balance': self.currentbalance or 0,
                'debit_Credit': self.debitcredit,
                'disp': 'Y',
                'company_id': 'C',
                'branch_id': '1',
                'fyc_code': '2024-2025'
            }
        )

    def __str__(self):
        return f"{self.head} ({self.account_code})"

    def get_absolute_url(self):
        return reverse("web:account_master_detail", kwargs={"slug": self.slug})


class Table_Acntchild(models.Model):
    account_master = models.ForeignKey('Table_Accountsmaster', on_delete=models.CASCADE, related_name='children')
    account_code = models.CharField(max_length=20)
    openning_balance = models.CharField(max_length=19)
    current_balance = models.CharField(max_length=100)
    debit_Credit = models.CharField(max_length=10)
    disp = models.CharField(max_length=10)
    company_id = models.CharField(max_length=10)
    branch_id = models.CharField(max_length=10)
    fyc_code = models.CharField(max_length=10)

    def __str__(self):
        return self.account_code  




from django.contrib.auth.models import User
from django.db import models

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Table_Companydetailsmaster(models.Model):
    company_id = models.CharField(max_length=1, unique=True)
    companyname = models.CharField(max_length=50, unique=True)
    address1 = models.CharField(max_length=50)
    address2 = models.CharField(max_length=50, blank=True, null=True)
    address3 = models.CharField(max_length=50, blank=True, null=True)
    pinCode = models.IntegerField()
    phoneno = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    gst = models.CharField(max_length=30, unique=True)
    pan = models.CharField(max_length=30, blank=True, null=True)
    finyearfrom = models.DateField()
    finyearto = models.DateField(blank=True, null=True)
    slug = models.SlugField(max_length=250, blank=True, null=True)

    def __str__(self):
        return self.company_id

    def save(self, *args, **kwargs):
        # Generate slug from the company name if not set
        if not self.slug:
            self.slug = slugify(self.companyname)
        super().save(*args, **kwargs)

        # Calculate fycode based on finyearfrom and finyearto
        fycode = f"{self.finyearfrom.year}-{self.finyearto.year}"

        Table_companyDetailschild.objects.update_or_create(
            company_id=self,
            defaults={
                "finyearfrom": str(self.finyearfrom),
                "finyearto": str(self.finyearto),
                "fycode": fycode,
                "databasename1": "databasename1",  # This should ideally be dynamic or provided
            },
        )

    def get_absolute_url(self):
        return reverse("web:companymaster_detail", kwargs={"slug": self.slug})


class Table_companyDetailschild(models.Model):
    company_id = models.ForeignKey(Table_Companydetailsmaster, on_delete=models.CASCADE)
    fycode = models.CharField(max_length=20)
    finyearfrom = models.CharField(max_length=19)
    finyearto = models.CharField(max_length=10, blank=True, null=True)
    databasename1 = models.CharField(max_length=50)  # Increased max_length to 50

    def __str__(self):
        return f"{self.company_id.companyname} - {self.fycode}"





from django.conf import settings
class Table_DrCrNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    series = models.CharField(max_length=150, null=True, blank=True)
    noteno = models.CharField(max_length=150, null=True, blank=True)
    ndate = models.DateField(default=timezone.now, null=True, blank=True)
    accountcode = models.CharField(max_length=200, null=True, blank=True)
    narration = models.CharField(max_length=200, null=True, blank=True)
    dramount = models.CharField(max_length=230, null=True, blank=True)
    cramount = models.CharField(max_length=230, null=True, blank=True)
    ntype = models.CharField(max_length=1, null=True, blank=True)
    userid = models.CharField(max_length=25, null=True, blank=True)
    coid = models.CharField(max_length=1, null=True, blank=True)
    fycode = models.CharField(max_length=15, null=True, blank=True)
    brid = models.CharField(max_length=1, null=True, blank=True)
    

    def __str__(self):
        return f"Series: {self.series}, Noteno: {self.noteno}, Date: {self.ndate}"






class VoucherConfiguration(models.Model):
    CATEGORY_CHOICES = [
        ('receipt', 'Receipt'),
        ('payment', 'Payment'), 
        ('Debit Note', 'Debit Note'),
        ('Credit Note', 'Credit Note'),
        ('Contra Entry', 'Contra Entry'),
        ('Journal Entry', 'Journal Entry'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES)
    series = models.CharField(max_length=255)
    serial_no = models.IntegerField()

    class Meta:
        unique_together = ('user', 'category', 'series')

    def __str__(self):
        return f"{self.category} - {self.series} - {self.serial_no}"

class Table_Voucher(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    Series = models.CharField(max_length=255, blank=True, null=True)
    VoucherNo = models.IntegerField(blank=True, null=True)
    Vdate = models.DateField(blank=True, null=True)
    Accountcode = models.CharField(max_length=255, blank=True, null=True)
    Headcode = models.CharField(max_length=255, blank=True, null=True)
    CStatus = models.CharField(max_length=255, blank=True, null=True)
    payment = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    VAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    VType = models.CharField(max_length=255, blank=True, null=True)
    Narration = models.TextField(blank=True, null=True)
    UserID = models.CharField(max_length=255, blank=True, null=True)
    FYCode = models.CharField(max_length=255, blank=True, null=True)
    Coid = models.CharField(max_length=255, blank=True, null=True)
    Branch_ID = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.Series} - {self.VoucherNo}"



class Table_Journal_Entry(models.Model):
    auth_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    series = models.CharField(max_length=100, null=True, blank=True)
    voucher_no = models.IntegerField(null=True, blank=True)
    vdate = models.DateField( null=True, blank=True)
    accountcode = models.CharField(max_length=250, null=True, blank=True)
    narration = models.TextField(null=True, blank=True)
    dramount = models.DecimalField(max_digits=50, decimal_places=2, null=True, blank=True)
    cramount = models.DecimalField(max_digits=50, decimal_places=2, null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    fycode = models.CharField(max_length=100, null=True, blank=True)
    coid = models.CharField(max_length=100, null=True, blank=True)
    brid = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.series}-{self.voucher_no}"



class Table_Contra_Entry(models.Model):
    auth_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    series = models.CharField(max_length=100, null=True, blank=True)
    voucher_no = models.IntegerField(null=True, blank=True)
    vdate = models.DateField( null=True, blank=True)
    accountcode = models.CharField(max_length=200, null=True, blank=True)
    narration = models.TextField(null=True, blank=True)
    dramount = models.DecimalField(max_digits=50, decimal_places=2, null=True, blank=True)
    cramount = models.DecimalField(max_digits=50, decimal_places=2, null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    fycode = models.CharField(max_length=100, null=True, blank=True)
    coid = models.CharField(max_length=100, null=True, blank=True)
    brid = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.series}-{self.voucher_no}"

class Ledger(models.Model):
    AccountCode = models.CharField(max_length=15, null=True, blank=True)
    VoucherType = models.CharField(max_length=15, null=True, blank=True)
    VoucherSeries = models.CharField(max_length=15, null=True, blank=True)
    VoucherNo = models.IntegerField(null=True, blank=True)
    FormType = models.CharField(max_length=15, null=True, blank=True)
    Narration = models.CharField(max_length=255, null=True, blank=True)
    Amount = models.IntegerField(null=True, blank=True)
    Dr_Cr = models.CharField(max_length=15, null=True, blank=True)
    FinancialYear = models.CharField(max_length=15, null=True, blank=True)
    BranchID = models.CharField(max_length=15, null=True, blank=True)
    CompanyID = models.CharField(max_length=15, null=True, blank=True)


# //////////////////////////////////////////// ACCOUNTS MODELS END //////////////////////////////////////////// #
