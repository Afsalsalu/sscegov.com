# exam/admin/user_registration_admin.py
from django.contrib import admin
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html

from exam.models import TemporaryUser, UserRegistration, DocumentValidation


@admin.register(UserRegistration)
class UserRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "mobile",
        "email",
        "state",
        "district",
        "certificate_paid_status",
        "certificate_downloaded_status",
        "view_user_link",
        "registration_date",
    )

    readonly_fields = (
        "name",
        "mobile",
        "email",
        "state",
        "district",
        "certificate_paid",
        "certificate_downloaded",
        "registration_date",  # Ensure this is in readonly_fields
        "view_user_link",
    )

    # List filter
    list_filter = (
        "state",
        "district",
        "gender",
        "certificate_paid",
        "certificate_downloaded",
        )

    # Search fields
    search_fields = ("name", "mobile", "email", "state", "district")

    # Ordering
    ordering = ("-registration_date",)

    # Fieldsets for organizing fields	
    fieldsets = (
        (
            "Personal Information",
            {
                "fields": (
                    "user",
                    "name",
                    "mobile",
                    "email",
                    "another_name",
                    "state",
                    "district",
                    "gender",
                    "date_of_birth",
                    "address",
                    "photo",
                )
            },
        ),
        (
            "Registration Details",
            {
                "fields": (
                    "registration_date",
                    "certificate_paid",
                    "certificate_downloaded",
                ),
            },
        ),
    )

    # Custom actions
    actions = [
        "mark_certificate_paid",
        "mark_certificate_unpaid",
         ]

    def mark_certificate_paid(self, request, queryset):
        queryset.update(certificate_paid=True)

    mark_certificate_paid.short_description = "Mark selected registrations as Paid"

    def mark_certificate_unpaid(self, request, queryset):
        queryset.update(certificate_paid=False)

    mark_certificate_unpaid.short_description = "Mark selected registrations as Unpaid"

    
    # Custom display for certificate paid status
    def certificate_paid_status(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if obj.certificate_paid else "red",
            "Paid" if obj.certificate_paid else "Not Paid",
        )

    certificate_paid_status.short_description = "Certificate Paid Status"

    # Custom display for certificate downloaded status
    def certificate_downloaded_status(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if obj.certificate_downloaded else "red",
            "Downloaded" if obj.certificate_downloaded else "Not Downloaded",
        )

    certificate_downloaded_status.short_description = "Certificate Downloaded Status"


    # Link to related user model
    def view_user_link(self, obj):
        if obj.user:
            try:
                url = reverse("admin:auth_user_change", args=[obj.user.id])
                return format_html('<a href="{}">{}</a>', url, obj.user.username)
            except NoReverseMatch:
                return format_html('<span style="color: red;">Link not found</span>')
        return "-"

    view_user_link.short_description = "User"

    # Customizing the admin form
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["user"].disabled = True
        return form


from django.contrib import admin
from exam.models import RegistrationState, RegistrationDistrict, RegistrationPanchayat

# Registering RegistrationState model
@admin.register(RegistrationState)
class RegistrationStateAdmin(admin.ModelAdmin):
    list_display = ('name','state_id')  # Display the 'name' field in the list view
    search_fields = ('name','state_id')  # Allow searching by 'name'
    ordering = ('name',)  # Order entries by 'name'

from django.contrib import admin

# Registering RegistrationDistrict model
@admin.register(RegistrationDistrict)
class RegistrationDistrictAdmin(admin.ModelAdmin):
    list_display = ( 'state', 'state_id', 'district_name', 'district_id')  # Include state_id
    search_fields = ('district_name',)  # Allow searching by 'district_name'
    list_filter = ('state',)  # Add filtering by state
    ordering = ('state', 'district_name')  # Order entries by 'state' and 'district_name'

    # Define a custom method to display the state_id
    def state_id(self, obj):
        return obj.state.state_id  # Accessing state_id from the related RegistrationState model
    state_id.admin_order_field = 'state__state_id'  # Allow sorting by state_id
    state_id.short_description = 'State ID'  # Display name for the column


from django.contrib import admin






from django import forms
from django.utils.safestring import mark_safe



class DynamicDistrictFilter(admin.SimpleListFilter):
    title = 'District'  # Title displayed in the admin filter sidebar
    parameter_name = 'district'  # URL parameter for filtering

    def lookups(self, request, model_admin):
        # Get the selected state from the query parameters
        state_id = request.GET.get('state')
        
        # Filter districts based on the selected state, only if state is selected
        if state_id:
            districts = RegistrationDistrict.objects.filter(state=state_id)
        else:
            districts = RegistrationDistrict.objects.none()  # No districts unless state is selected

        # Return the district choices for the filter
        return [(district.district_id, district.district_name) for district in districts]

    def queryset(self, request, queryset):
        # Filter the queryset by the selected district only if a district is selected
        if self.value():
            return queryset.filter(district_id=self.value())
        return queryset



class RegistrationPanchayatForm(forms.ModelForm):
    class Meta:
        model = RegistrationPanchayat
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the state from the initial data or form data (if available)
        state = self.initial.get('state') or self.data.get('state')

        # Debug: print the state value to ensure it's being passed
        print(f"State Value in Form Init: {state}")

        # Initially leave the district field empty if no state is selected
        if state:
            # If state is selected, filter districts accordingly
            self.fields['district'].queryset = RegistrationDistrict.objects.filter(state=state)
        else:
            # If no state is selected, leave the district options empty
            self.fields['district'].queryset = RegistrationDistrict.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get("state")

        # Debug: print the state value after form submission
        print(f"State Value in Clean Method: {state}")

        # Only filter districts if state is selected
        if state:
            self.fields['district'].queryset = RegistrationDistrict.objects.filter(state=state)
        return cleaned_data



    
    
@admin.register(RegistrationPanchayat)
class RegistrationPanchayatAdmin(admin.ModelAdmin):
    form = RegistrationPanchayatForm
    list_display = ('name', 'state_id', 'district', 'district_id', 'local_body', 'state', 'panchayat_id')
    search_fields = ('name',)
    list_filter = ('state',)  # State filter remains; district is handled dynamically
    ordering = ('state', 'district', 'local_body', 'name')

    # Override get_form to filter districts dynamically for editing
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # If editing an existing object, pre-filter districts based on the state
        if obj:
            form.base_fields['district'].queryset = RegistrationDistrict.objects.filter(state=obj.state)
        else:
            # For a new object, districts should be filtered after state selection
            form.base_fields['district'].queryset = RegistrationDistrict.objects.none()

        return form








@admin.register(TemporaryUser)
class TemporaryUserAdmin(admin.ModelAdmin):
    list_display = (
        "name", "mobile", "email", "state", "district", "certificate_paid_status",
        "certificate_downloaded_status", "view_user_link", "registration_date"
    )
    readonly_fields = (
        "name", "mobile", "email", "state", "district", "certificate_paid",
        "certificate_downloaded", "registration_date", "view_user_link"
    )
    list_filter = ("state", "district", "gender", "certificate_paid", "certificate_downloaded")
    search_fields = ("name", "mobile", "email", "state", "district")
    ordering = ("-registration_date",)
    fieldsets = (
        ("Personal Information", {"fields": ("name", "another_name", "mobile", "email", "date_of_birth", "gender", "aadhaar_number", "address", "photo")} ),
        ("Location Details", {"fields": ("state", "district", "panchayat", "ward_number")} ),
        ("Documents", {"fields": ("cheque_passbook",)} ),
        ("Payment & Certificate", {"fields": ("payment", "certificate_paid", "certificate_downloaded")} ),
        ("Other Information", {"fields": ("registration_date", )}),
    )
    actions = ["mark_certificate_paid", "mark_certificate_unpaid"]

    def mark_certificate_paid(self, request, queryset):
        queryset.update(certificate_paid=True)
    mark_certificate_paid.short_description = "Mark selected registrations as Paid"

    def mark_certificate_unpaid(self, request, queryset):
        queryset.update(certificate_paid=False)
    mark_certificate_unpaid.short_description = "Mark selected registrations as Unpaid"

    def certificate_paid_status(self, obj):
        return format_html('<span style="color: {};"><b>{}</b></span>', "green" if obj.certificate_paid else "red", "Paid" if obj.certificate_paid else "Not Paid")
    certificate_paid_status.short_description = "Certificate Paid Status"

    def certificate_downloaded_status(self, obj):
        return format_html('<span style="color: {};"><b>{}</b></span>', "green" if obj.certificate_downloaded else "red", "Downloaded" if obj.certificate_downloaded else "Not Downloaded")
    certificate_downloaded_status.short_description = "Certificate Downloaded Status"

    def view_user_link(self, obj):
        if obj.user:
            try:
                url = reverse("admin:auth_user_change", args=[obj.user.id])
                return format_html('<a href="{}">{}</a>', url, obj.user.username)
            except NoReverseMatch:
                return format_html('<span style="color: red;">Link not found</span>')
        return "-"
    view_user_link.short_description = "User"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["user"].disabled = True
        return form



from exam.models.user_registration import Resources

class ResourcesAdmin(admin.ModelAdmin):
    list_display = ("description", "file_link")  # Show file link in the list view

    def file_link(self, obj):
        if obj.file:  # Check if a file exists
            return format_html('<a href="{}" download><i class="fa fa-download"></i> Download</a>', obj.file.url)
        return "No file"
    
    file_link.short_description = "Download File"

admin.site.register(Resources, ResourcesAdmin)


@admin.register(DocumentValidation)
class DocumentValidationAdmin(admin.ModelAdmin):
    list_display = ('user', 'photo', 'aadhaar')
    search_fields = ('user__email', 'user__username')  # Adjust based on TemporaryUser fields
    list_filter = ('user',)

    def get_queryset(self, request):
        """Ensure admin sees all related user data."""
        return super().get_queryset(request).select_related('user')
