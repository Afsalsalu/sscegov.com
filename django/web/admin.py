from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode

from .models import (AboutBlog, AboutPage, AddState, Career, CareerForm,
                     CentreUserAccount, Contact, Department, DownloadForm,
                     CentreReactivationAuditLog,
                     Employee, HeadOffice, HomeCompleteSolutions,
                     HomeLogoBrand, HomeService, LatestNewsCentre, Media,
                     OnlineClass, Software, StateService, User,Table_Accountsmaster,Table_Companydetailsmaster,
		     Table_Acntchild,Table_companyDetailschild,VoucherConfiguration,Table_DrCrNote,Table_Contra_Entry,Table_Journal_Entry,Table_Voucher)

# Register your models here.


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Custom fields to be displayed in the list view
    list_display = (
        "username",
        "email",
        "usertype",
        "is_staff",
        "is_active",
        "last_login",
        "is_superuser",
        "formatted_usertype",
    )

    # Filter options
    list_filter = ("is_staff", "is_superuser", "is_active", "usertype", "last_login")

    # Search functionality
    search_fields = ("username", "email", "usertype")

    # Ordering of records
    ordering = ("-id",)

    # Readonly fields (you can include fields like 'last_login' here)
    readonly_fields = ("last_login", "date_joined", "password")

    # Fieldsets to organize fields in the detail view
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("User Type", {"fields": ("usertype",)}),
    )

    # Add fieldsets for the create user view
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "usertype",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    # Custom admin actions
    actions = ["make_active", "make_inactive", "make_staff", "remove_staff"]

    # Inline for related models (if any)
    # Example (uncomment if needed):
    # inlines = [RelatedModelInline]

    # Custom method for displaying usertype with formatting
    def formatted_usertype(self, obj):
        if obj.usertype == "HeadOffice":
            color = "blue"
        elif obj.usertype == "State":
            color = "green"
        elif obj.usertype == "Employee":
            color = "purple"
        elif obj.usertype == "centre":
            color = "orange"
        elif obj.usertype == "subcentre":
            color = "red"
        else:
            color = "black"
        return format_html(
            '<span style="color: {};">{}</span>', color, obj.get_usertype_display()
        )

    formatted_usertype.short_description = "User Type"

    # Custom actions
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    make_active.short_description = "Mark selected users as Active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected users as Inactive"

    def make_staff(self, request, queryset):
        queryset.update(is_staff=True)

    make_staff.short_description = "Grant staff status to selected users"

    def remove_staff(self, request, queryset):
        queryset.update(is_staff=False)

    remove_staff.short_description = "Revoke staff status from selected users"


@admin.register(HomeService)
class HomeServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "image_tag")
    search_fields = ("name",)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"

    image_tag.short_description = "Image"


@admin.register(HomeCompleteSolutions)
class HomeCompleteSolutionsAdmin(admin.ModelAdmin):
    list_display = ("title", "short_description", "image_tag")
    search_fields = ("title",)

    def short_description(self, obj):
        return (
            obj.description[:75] + "..."
            if len(obj.description) > 75
            else obj.description
        )

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"

    image_tag.short_description = "Image"


@admin.register(HomeLogoBrand)
class HomeLogoBrandAdmin(admin.ModelAdmin):
    list_display = ("image_tag",)

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"

    image_tag.short_description = "Image"


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "centre_name",
        "state",
        "district",
        "created_at",
    )
    search_fields = ("full_name", "email", "phone", "centre_name", "subject")
    list_filter = ("state", "district", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        (
            "Contact Information",
            {"fields": ("full_name", "email", "phone", "centre_name")},
        ),
        ("Location Details", {"fields": ("state", "district", "taluk")}),
        ("Message Details", {"fields": ("subject", "comments")}),
        ("Metadata", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = (
        "image_tag",
        "title",
        "sub_title",
        "content",
        "place",
        "created_at",
        "is_active",
    )
    search_fields = ("title", "sub_title", "content", "place")
    list_filter = ("is_active", "created_at")
    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Media Details",
            {"fields": ("image", "title", "sub_title", "content", "place")},
        ),
        ("Status", {"fields": ("is_active",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.image.url
            )
        return "-"

    image_tag.short_description = "Image"


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = (
        "name_of_host",
        "experience",
        "qualification",
        "salary",
        "created_at",
        "is_active",
    )
    search_fields = ("name_of_host", "experience", "qualification")
    list_filter = ("is_active", "created_at")
    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Career Information",
            {"fields": ("name_of_host", "experience", "qualification", "salary")},
        ),
        ("Status", {"fields": ("is_active",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(CareerForm)
class CareerFormAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "job_title",
        "experience_years",
        "qualification",
        "age",
        "current_role",
        "resume_tag",
        "created_at",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "job_title",
        "current_role",
    )
    list_filter = (
        "experience_years",
        "qualification",
        "age",
        "current_role",
        "created_at",
    )
    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

    fieldsets = (
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            "Job Details",
            {
                "fields": (
                    "job_title",
                    "experience_years",
                    "qualification",
                    "age",
                    "current_role",
                    "resume",
                    "experience_level",
                    "work_preference",
                )
            },
        ),
        ("Additional Information", {"fields": ("comments",)}),
        ("Metadata", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def resume_tag(self, obj):
        if obj.resume:
            return format_html(
                '<a href="{}" target="_blank">View Resume</a>', obj.resume.url
            )
        return "-"

    resume_tag.short_description = "Resume"


@admin.register(AddState)
class AddStateAdmin(admin.ModelAdmin):
    list_display = ("state_name", "slug", "logo_tag")
    search_fields = ("state_name",)
    prepopulated_fields = {"slug": ("state_name",)}

    def logo_tag(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" />', obj.logo.url)
        return "-"

    logo_tag.short_description = "Logo"


@admin.register(StateService)
class StateServiceAdmin(admin.ModelAdmin):
    list_display = (
        "service_name",
        "state",
        "service_logo_tag",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("state", "is_active", "created_at")
    search_fields = ("service_name", "state__state_name")
    list_editable = ("is_active",)

    def service_logo_tag(self, obj):
        if obj.service_logo:
            return format_html(
                '<img src="{}" width="50" height="50" />', obj.service_logo.url
            )
        return "-"

    service_logo_tag.short_description = "Service Logo"

    # Actions to activate/deactivate services
    actions = ["make_active", "make_inactive"]

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    make_active.short_description = "Mark selected services as Active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark selected services as Inactive"



# Custom Filter Example (Optional)
class ActiveStatusFilter(SimpleListFilter):
    title = "Active Status"
    parameter_name = "is_active"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("inactive", "Inactive"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_active=True)
        elif self.value() == "inactive":
            return queryset.filter(is_active=False)


@admin.register(CentreUserAccount)
class CentreUserAccountAdmin(admin.ModelAdmin):
    # List display
    list_display = (
        "photo_tag",
        "formatted_id",
        "username",
        "owner_centre",
	"another_name",
        "mobile",
        "email",
        "state",
        "district",
        "is_active",
        "last_login",
        "certificate_paid_link",
        "certificate_downloaded",
    )

    # List filter
    list_filter = (
        "state",
        "district",
        "is_active",
        "last_login",
        "created_by",
        "certificate_paid",
        "certificate_downloaded",
    )

    # Search fields
    search_fields = ("username", "email", "mobile", "aadhaar_number", "pan_card_number", "another_name", "owner_centre")

    # Ordering
    ordering = ("-id",)

    # Readonly fields
    readonly_fields = ("formatted_id", "last_login")

    # Fieldsets for organizing fields
    fieldsets = (
        (
            "User Details",
            {
                "fields": (
                    "user",
                    "username",
                    "another_name",
                    "email",
                    "mobile",
                    "alternative_mobile",
                    "is_active",
                    "last_login",
                )
            },
        ),
        (
            "Centre Info",
            {
                "fields": (
                    "owner_centre",
                    "centre_name",
                    "centre_phone_number",
                    "centre_email",
                    "centre_owner_address",
                )
            },
        ),
        (
            "Location Info",
            {
                "fields": (
                    "state",
                    "district",
                    "taluk",
                    "rural_areas",
                    "ward_number",
                    "pin_code",
                    "address",
                )
            },
        ),
        (
            "Documents",
            {
                "fields": (
                    "photo",
                    "aadhaar_number",
                    "aadhaar_front_side_uploading",
                    "aadhaar_back_side_uploading",
                    "pan_card_number",
                    "pan_card_uploading",
                    "sign_uploading",
                    "another_document",
                )
            },
        ),
        (
            "Certificate Info",
            {"fields": ("certificate_paid", "certificate_downloaded")},
        ),
    )

    # Custom actions
    actions = ["mark_active", "mark_inactive"]

    # Action to mark selected users as active
    def mark_active(self, request, queryset):
        now = timezone.now()
        for centre in queryset:
            if centre.user_id:
                centre.user.is_active = True
                centre.user.save(update_fields=["is_active"])
            centre.is_active = True
            centre.manual_disabled = False
            centre.inactive_due_to_inactivity = False
            centre.inactivity_reason = ""
            centre.reactivated_at = now
            centre.last_successful_login = now
            centre.last_login = now
            centre.save(update_fields=[
                "is_active", "manual_disabled", "inactive_due_to_inactivity",
                "inactivity_reason", "reactivated_at", "last_successful_login",
                "last_login"
            ])
            CentreReactivationAuditLog.objects.create(
                centre=centre,
                actor=request.user,
                event=CentreReactivationAuditLog.Event.REACTIVATED,
                details={"source": "django_admin_action"},
            )

    mark_active.short_description = "Mark selected users as Active"

    # Action to mark selected users as inactive
    def mark_inactive(self, request, queryset):
        for centre in queryset:
            if centre.user_id:
                centre.user.is_active = False
                centre.user.save(update_fields=["is_active"])
            centre.is_active = False
            centre.manual_disabled = True
            centre.inactive_due_to_inactivity = False
            centre.inactivity_reason = ""
            centre.save(update_fields=[
                "is_active", "manual_disabled", "inactive_due_to_inactivity",
                "inactivity_reason"
            ])

    mark_inactive.short_description = "Mark selected users as Inactive"

    def save_model(self, request, obj, form, change):
        if change and "is_active" in form.changed_data:
            obj.manual_disabled = not obj.is_active
            if obj.is_active and obj.inactive_due_to_inactivity:
                obj.inactive_due_to_inactivity = False
                obj.inactivity_reason = ""
                obj.reactivated_at = timezone.now()
                obj.last_successful_login = obj.reactivated_at
                obj.last_login = obj.reactivated_at
                CentreReactivationAuditLog.objects.create(
                    centre=obj,
                    actor=request.user,
                    event=CentreReactivationAuditLog.Event.REACTIVATED,
                    details={"source": "django_admin"},
                )
        super().save_model(request, obj, form, change)


    def certificate_paid_link(self, obj):
        if hasattr(obj, "certificate_paid") and obj.certificate_paid:
            return format_html('<span style="color: green;">Paid</span>')
        return format_html('<span style="color: red;">Not Paid</span>')

    certificate_paid_link.short_description = "Certificate Status"

    def photo_tag(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" />', obj.photo.url)
        return "-"

    photo_tag.short_description = "Photo"

    # Customizing the admin form
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["created_by"].disabled = True
        return form


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("name", "username", "email", "position", "date_of_birth", "mobile")
    search_fields = ("name", "username", "email", "position__name")
    list_filter = ("position",)
    ordering = ("-date_of_birth",)

    fieldsets = (
        (
            "Employee Details",
            {
                "fields": (
                    "user",
                    "name",
                    "username",
                    "email",
                    "position",
                    "date_of_birth",
                    "mobile",
                )
            },
        ),
    )


@admin.register(HeadOffice)
class HeadOfficeAdmin(admin.ModelAdmin):
    list_display = ("name", "photo_tag", "phone_number", "email")
    search_fields = ("name", "phone_number", "email")
    readonly_fields = ("photo_tag",)
    ordering = ("name",)

    fieldsets = (
        (
            "Head Office Details",
            {"fields": ("user", "name", "photo", "phone_number", "email")},
        ),
        ("Photo Preview", {"fields": ("photo_tag",), "classes": ("collapse",)}),
    )

    def photo_tag(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.photo.url
            )
        return "-"

    photo_tag.short_description = "Photo"


@admin.register(OnlineClass)
class OnlineClassAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "class_video_link",
        "thumbnail_tag",
        "description",
        "is_active",
        "created_at",
    )
    search_fields = ("title", "description")
    list_filter = ("is_active", "created_at")
    readonly_fields = ("thumbnail_tag",)
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Class Details",
            {
                "fields": (
                    "title",
                    "class_video_link",
                    "thumbnail",
                    "description",
                    "is_active",
                )
            },
        ),
        ("Thumbnail Preview", {"fields": ("thumbnail_tag",), "classes": ("collapse",)}),
    )

    def thumbnail_tag(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.thumbnail.url
            )
        return "-"

    thumbnail_tag.short_description = "Thumbnail"


@admin.register(DownloadForm)
class DownloadFormAdmin(admin.ModelAdmin):
    list_display = ("title", "pdf_link", "is_active", "created_at")
    search_fields = ("title",)
    list_filter = ("is_active", "created_at")
    readonly_fields = ("pdf_link",)
    ordering = ("-created_at",)

    fieldsets = (
        ("Form Details", {"fields": ("title", "pdf", "is_active")}),
        ("PDF Preview", {"fields": ("pdf_link",), "classes": ("collapse",)}),
    )

    def pdf_link(self, obj):
        if obj.pdf:
            return format_html(
                '<a href="{}" target="_blank">Download PDF</a>', obj.pdf.url
            )
        return "-"

    pdf_link.short_description = "PDF"


@admin.register(Software)
class SoftwareAdmin(admin.ModelAdmin):
    list_display = ("title", "logo_tag", "site_link")
    search_fields = ("title", "site_link")
    readonly_fields = ("logo_tag",)
    ordering = ("-title",)

    fieldsets = (
        ("Software Details", {"fields": ("title", "logo", "site_link")}),
        ("Logo Preview", {"fields": ("logo_tag",), "classes": ("collapse",)}),
    )

    def logo_tag(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.logo.url
            )
        return "-"

    logo_tag.short_description = "Logo"


@admin.register(LatestNewsCentre)
class LatestNewsCentreAdmin(admin.ModelAdmin):
    list_display = ("title", "image_tag", "content", "created_at")
    search_fields = ("title", "content")
    readonly_fields = ("image_tag",)
    ordering = ("-created_at",)

    fieldsets = (
        ("News Details", {"fields": ("title", "image", "content")}),
        ("Image Preview", {"fields": ("image_tag",), "classes": ("collapse",)}),
    )

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.image.url
            )
        return "-"

    image_tag.short_description = "Image"


admin.site.register(AboutPage)
admin.site.register(AboutBlog)





# //////////////////////////////////////////// ACCOUNTS ADMIN START //////////////////////////////////////////// #



admin.site.register(Table_Accountsmaster)

admin.site.register(Table_Acntchild)

class CompanydetailsmasterAdmin(admin.ModelAdmin):
    list_display = ('company_id', 'companyname', 'email', 'gst', 'pan')
    search_fields = ('company_id', 'companyname')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

class CompanyDetailschildAdmin(admin.ModelAdmin):
    list_display = ('company_id', 'fycode', 'finyearfrom', 'finyearto', 'databasename1')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company_id__user=request.user)

admin.site.register(Table_Companydetailsmaster, CompanydetailsmasterAdmin)
admin.site.register(Table_companyDetailschild, CompanyDetailschildAdmin)


@admin.register(VoucherConfiguration)
class VoucherConfigurationAdmin(admin.ModelAdmin):
    list_display = ('category', 'series', 'serial_no')
    search_fields = ('category', 'series')
    list_filter = ('category',)

@admin.register(Table_DrCrNote)
class Table_DrCrNoteAdmin(admin.ModelAdmin):
    list_display = ("series", "noteno", "ndate", "accountcode", "narration", "dramount", "cramount", "ntype", "userid", "coid", "fycode", "brid")


class ContraEntryNoteAdmin(admin.ModelAdmin):
    list_display = ('series', 'voucher_no', 'vdate', 'accountcode', 'narration', 'dramount', 'cramount', 'user_id', 'coid', 'fycode', 'brid')

admin.site.register(Table_Contra_Entry, ContraEntryNoteAdmin)


class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('series', 'voucher_no', 'vdate', 'accountcode', 'narration', 'dramount', 'cramount', 'user_id', 'coid', 'fycode', 'brid')

admin.site.register(Table_Journal_Entry, JournalEntryAdmin)




class TableVoucherAdmin(admin.ModelAdmin):
    list_display = ('Series', 'VoucherNo', 'Vdate', 'Accountcode', 'Headcode', 'payment', 'VAmount', 'VType', 'Narration', 'CStatus', 'UserID', 'FYCode', 'Coid', 'Branch_ID')
    search_fields = ('Series', 'VoucherNo', 'Accountcode', 'Headcode', 'Narration')
    list_filter = ('Series', 'Vdate', 'VType', 'CStatus')

admin.site.register(Table_Voucher, TableVoucherAdmin)

# //////////////////////////////////////////// ACCOUNTS ADMIN END //////////////////////////////////////////// #




