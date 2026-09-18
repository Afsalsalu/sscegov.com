from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.db import transaction
import random
import string
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from django.contrib.auth import logout
import uuid
from django.contrib.auth.forms import SetPasswordForm
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .forms import (
    # StateCreateForm,
    # DistrictCreateForm,
    # RetailerCreateForm,
    EditContactForm,
    WalletRequestForm,
    CommissionWithdrawForm
)

from .models import (
    UserProfile,
    State,
    District,
    Wallet,
    WalletTransaction,
    WalletRequest,
    CommissionWallet,
    RoleRegistrationCharge,
    CommissionTransaction,
    CommissionWithdrawRequest,
    PSAMaster
)
from django.core.paginator import Paginator
from django.db.models import Q
import random

from .services import create_wallet_transaction


def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')
def privacy_policy(request):
    return render(request, 'privacy_policy.html')
def terms_condition_view(request):
    return render(request, 'terms_condition.html')

User = get_user_model()


@transaction.atomic
def register_view(request): 

    states = State.objects.all()
    districts = District.objects.all() 
    charges = RoleRegistrationCharge.objects.all()
    role_fees = {c.role: float(c.amount) for c in charges}

    if request.method == 'POST':

        # OTP Verification Check
        otp_verified = request.session.get('otp_verified')
        otp_email = request.session.get('otp_email')

        if not otp_verified:
            messages.error(request, 'Please verify your email with OTP first')
            return render(request, 'register.html', {
                'states': states,
                'role_fees': role_fees
            })

        username = request.POST.get('username')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        role = request.POST.get('role')
        address = request.POST.get('address')
        pin_code = request.POST.get('pin_code')
        dob = request.POST.get('dob')
        state_id = request.POST.get("state")
        district_id = request.POST.get("district")
        pan = request.POST.get('pan')
        aadhaar = request.POST.get('aadhaar')
        upi_id = request.POST.get('upi_id')

        # Ensure verified email matches
        if email != otp_email:
            messages.error(request, 'Verified email does not match.')
            return render(request, 'register.html', {
                'states': states,
                'role_fees': role_fees
            })

        # Duplicate Checks
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'register.html', {
                'states': states,
                'role_fees': role_fees
            })

        if User.objects.filter(mobile=mobile).exists():
            messages.error(request, 'Mobile number already exists')
            return render(request, 'register.html', {
                'states': states,
                'role_fees': role_fees
            })

        if UserProfile.objects.filter(pan=pan).exists():
            messages.error(request, 'PAN already exists')
            return render(request, 'register.html', {
                'states': states,
                'role_fees': role_fees
            })

        if UserProfile.objects.filter(aadhaar=aadhaar).exists():
            messages.error(request, 'Aadhaar already exists')
            return render(request, 'register.html', {
                'states': states,
                'role_fees': role_fees
            })


        role_price = RoleCouponPrice.objects.filter(role=role).first()
        uti_price = role_price.price if role_price else Decimal(0)

        # Create User (Inactive + No Password)
        user = User.objects.create(
            username=username,
            email=email,
            role=role,
            mobile=mobile,
            is_email_verified=True,
            is_active=False
        )

        user.set_unusable_password()
        user.save()

        state = State.objects.filter(id=state_id).first()
        district = District.objects.filter(id=district_id).first()

        # Create Profile
        UserProfile.objects.create(
            user=user,
            address=address,
            pin_code=pin_code,
            dob=dob if dob else None,
            state=state,
            district = district,
            upi_id = upi_id,
            pan=pan,
            aadhaar=aadhaar,
            uti_price=uti_price,
            is_approved=False
        )

        # Create Wallet
        Wallet.objects.get_or_create(user=user)
        

        # Clear OTP session
        for key in ["email_otp", "otp_verified", "otp_email"]:
            request.session.pop(key, None)

        # registration amount
        amount = user.registration_fee

        # Your UPI ID
        upi_id = "8304991136@cnrb"

        # UPI Payment String
        upi_link = f"upi://pay?pa={upi_id}&pn=SSC%20Pan%20Service&am={amount}&cu=INR"

        # Generate QR
        qr = qrcode.make(upi_link)

        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return render(request, "registration_qr.html", {
            "amount": amount,
            "username": user.username,
            "qr_code": qr_base64
        })

    return render(request, "register.html", {
        "states": states,
        'districts':districts,
        "role_fees": role_fees
    })


def send_email_otp(request):

    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return JsonResponse({
                "status": "error",
                "message": "Email is required"
            })

        otp = str(random.randint(100000, 999999))

        request.session['email_otp'] = otp
        request.session['otp_email'] = email

        send_mail(
            "Your OTP Code",
            f"Your OTP is {otp}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return JsonResponse({"status": "success"})

def verify_email_otp(request):

    if request.method == "POST":

        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("email_otp")

        if not session_otp:
            return JsonResponse({
                "status": "error",
                "message": "Please send OTP first."
            })

        if entered_otp == session_otp:
            request.session['otp_verified'] = True

            return JsonResponse({
                "status": "success",
                "message": "Email verified successfully."
            })

        return JsonResponse({
            "status": "error",
            "message": "Invalid OTP"
        })



def activate_user(user):

    new_userid = f"SSC{user.mobile}"
    new_password = f"SSC{user.mobile}"

    # user.username = new_userid
    user.set_password(new_password)
    user.is_active = True
    user.save()

    send_mail(
        "Account Approved - Login Details",
        f"""
            Congratulations!

            Your account has been approved.

            User ID: {new_userid}
            Password: {new_password}

            Please login and change your password after first login.
        """,
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

    return new_userid
   
@login_required
def role_redirect(request):

    role = request.user.role

    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'state':
        return redirect('state_dashboard')
    elif role == 'district':
        return redirect('district_dashboard')
    else:
        return redirect('retailer_dashboard')


def user_login(request):

    if request.method == 'POST':
        entered_userid = request.POST.get('username')
        password = request.POST.get('password')

        # Check if entered ID starts with SSC
        if entered_userid.startswith("SSC"):
            mobile_number = entered_userid.replace("SSC", "")
            try:
                user = User.objects.get(mobile=mobile_number)
            except User.DoesNotExist:
                user = None
        else:
            # fallback normal username login
            try:
                user = User.objects.get(username=entered_userid)
            except User.DoesNotExist:
                user = None

        if user is not None:
            user = authenticate(request, username=user.username, password=password)

        if user is None:
            messages.error(request, "Invalid UserID or Password.")
            return redirect('login')

        if not user.is_active:
            messages.error(request, "Your account is not approved yet.")
            return redirect('login')

        login(request, user)

        # if user.must_change_password:
        #     return redirect('change_password')

        return redirect('role_redirect')

    return render(request, 'login.html')


def get_districts(request):
    state_id = request.GET.get('state_id')

    if not state_id:
        return JsonResponse({'districts': []})

    districts = District.objects.filter(state_id=state_id).values('id', 'name')

    return JsonResponse({'districts': list(districts)}, safe=False)


@login_required
def user_logout(request):
    logout(request)
    return redirect('login')
    


class ChangePasswordView(PasswordChangeView):
    template_name = 'change_password.html'
    success_url = reverse_lazy('password_change_done')
    form_class = SetPasswordForm   # ✅ Important

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()

        user = self.request.user
        user.must_change_password = False   # if you are using this field
        user.save()

        return super().form_valid(form)

@login_required
def password_change_done(request):
    messages.success(request, 'Password Changed Successfully! Please login again.')
    logout(request)
    return redirect('login')

@login_required
def create_user(request):

    if request.user.role != "admin":
        return redirect("login")

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        mobile = request.POST.get("mobile")
        role = request.POST.get("role")

        state_id = request.POST.get("state")
        district_id = request.POST.get("district")

        gender = request.POST.get("gender")
        address = request.POST.get("address")
        pin_code = request.POST.get("pin_code")
        dob = request.POST.get("dob")
        company = request.POST.get("company")

        upi_id = request.POST.get("upi_id")
        pan = request.POST.get("pan")
        aadhaar = request.POST.get("aadhaar")

        margin_slab = request.POST.get("margin_slab")
        uti_price = Decimal(request.POST.get("uti_price") or 0)
        nsdl_price = Decimal(request.POST.get("nsdl_price") or 0)

        state = State.objects.filter(id=state_id).first()
        district = District.objects.filter(id=district_id).first()

        login_id = f"SSC{mobile}"
        password = login_id

        user = User.objects.create(
            username=username,
            email=email,
            mobile=mobile,
            role=role,
            status="active",
            created_by=request.user,
            is_email_verified=True,
        )

        user.set_password(password)
        user.is_active = True
        user.save()

        UserProfile.objects.create(
            user=user,
            gender=gender,
            address=address,
            pin_code=pin_code,
            dob=dob if dob else None,
            company=company,
            state=state,
            district=district,
            upi_id=upi_id,
            pan=pan,
            aadhaar=aadhaar,
            margin_slab=margin_slab,
            uti_price=uti_price,
            nsdl_price=nsdl_price,
            is_approved=True
        )

        send_mail(
            "Your Login Credentials",
            f"""
Welcome!

Your account has been created.

UserID : {login_id}
Password : {password}

Please login and change password.
""",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        messages.success(request, "User created successfully")
        return redirect("all_users")

    states = State.objects.all()
    districts = District.objects.all()

    roles = [
        role for role in User._meta.get_field('role').choices
        if role[0] != 'admin'
    ]

    return render(request, "create_user.html", {
        "states": states,
        "districts": districts,
        "roles": roles,
        "gender": UserProfile._meta.get_field('gender').choices,
        "margin_slab": UserProfile._meta.get_field('margin_slab').choices
    })


@login_required
def all_users(request):

    if request.user.role != 'admin':
        return redirect('login')

    search_query = request.GET.get('search','')

    users = User.objects.select_related('profile', 'wallet', 'created_by')

    if search_query:

    # support SSC search
        if search_query.upper().startswith("SSC"):
            search_query = search_query.replace("SSC", "")

        filters = (
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(mobile__icontains=search_query) |
            Q(profile__state__name__icontains=search_query) |
            Q(profile__address__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )

        if search_query.isdigit():
            filters |= Q(id=int(search_query))

        users = users.filter(filters)

    users = users.order_by('date_joined')

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'all_users.html',{
        'users': page_obj,
        'search_query': search_query
    })

@login_required
def approve_user(request, user_id):

    if request.user.role != 'admin':
        return redirect('login')


    user = get_object_or_404(User, id = user_id)

    user.profile.is_approved = True
    user.profile.save()

    activate_user(user)
    
    return redirect('all_users')

@login_required
def reject_user(request,user_id):

    user = get_object_or_404(User, id = user_id)

    user.profile.is_approved = False
    user.profile.save()

    return redirect('all_users')


@login_required
def delete_user(request, user_id):

    if request.user.role != 'admin':
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    user.delete()

    messages.success(request, "User deleted successfully")

    return redirect('all_users')

@login_required
def admin_change_user_password(request, user_id):

    if request.user.role != 'admin':
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        password = request.POST.get("password")

        user.set_password(password)
        user.save()

        messages.success(request, "Password updated successfully")

        return redirect("all_users")

    return render(request, "admin_change_password.html", {
        "target_user": user
    })


@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.error(request, "You are not allowed to access this page!")
        return redirect('login')

    try:
        system_wallet = request.user.wallet.balance
    except Wallet.DoesNotExist:
        system_wallet = 0

    try:
        commission_amount = request.user.commission_wallet.balance
    except CommissionWallet.DoesNotExist:
        commission_amount = 0

    return render(request, 'admin_dashboard.html', {
        'system_wallet': system_wallet,
        'commission_amount': commission_amount,
    })

@login_required
def state_dashboard(request):

    if request.user.role != 'state':
        messages.error(request, "You are not allowed to access this page!")
        return redirect('login')

    # State main wallet (system wallet)
    try:
        state_wallet = request.user.wallet.balance
    except Wallet.DoesNotExist:
        state_wallet = 0

    # Commission wallet
    try:
        commission_amount = request.user.commission_wallet.balance
    except CommissionWallet.DoesNotExist:
        commission_amount = 0

    # Districts created under this state
    districts = User.objects.filter(
        role='district',
        created_by=request.user
    )

    total_districts = districts.count()

    # Retailers under those districts
    total_retailers = User.objects.filter(
        role='retailer',
        created_by__in=districts
    ).count()

    return render(request, 'state_dashboard.html', {
        "state_wallet": state_wallet,
        "wallet_balance": commission_amount,
        "total_districts": total_districts,
        "total_retailers": total_retailers
    })

@login_required
def district_dashboard(request):

    if request.user.role != 'district':
        messages.error(request, "You are not allowed to access this page!")
        return redirect('login')

    # District main wallet
    try:
        district_wallet = request.user.wallet.balance
    except Wallet.DoesNotExist:
        district_wallet = 0

    # Commission wallet
    try:
        commission_amount = request.user.commission_wallet.balance
    except CommissionWallet.DoesNotExist:
        commission_amount = 0

    # Retailers created by this district
    total_retailers = User.objects.filter(
        role='retailer',
        created_by=request.user
    ).count()

    return render(request, 'district_dashboard.html', {
        "district_wallet": district_wallet,
        "wallet_balance": commission_amount,
        "total_retailers": total_retailers
    })

    
@login_required
def retailer_dashboard(request):

    if request.user.role != 'retailer':
        messages.error(request, "You are not allowed to access this page!")
        return redirect('login')

    # Main wallet
    try:
        system_wallet = request.user.wallet.balance
    except Wallet.DoesNotExist:
        system_wallet = 0

    # Commission wallet
    try:
        commission_amount = request.user.commission_wallet.balance
    except CommissionWallet.DoesNotExist:
        commission_amount = 0

    context = {
        "wallet_balance": system_wallet,
        "commission_wallet": commission_amount,
    }

    return render(request, 'retailer_dashboard.html', context)

@login_required
def district_list(request):
    # If Admin → show all district distributors
    if request.user.role == 'admin':
        districts = User.objects.filter(role='district')

    # If State Distributor → show only their districts
    elif request.user.role == 'state':
        districts = User.objects.filter(
            role='district',
            profile__state=request.user.profile.state
        )
    
    # District or Retailer → not allowed
    else:
        messages.error(request, "You are not allowed to view this page!")
        return redirect('login')

    return render(request, 'district_list.html', {'districts': districts})


## ------------------ State ------------------------



@login_required
def state_create_user(request):
    if request.user.role != 'state':
        return redirect('login')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        role = request.POST.get('role')
        mobile = request.POST.get('mobile')
        state_id = request.POST.get('state')
        district_id = request.POST.get('district')
        gender = request.POST.get('gender')
        address = request.POST.get('address')
        pin_code = request.POST.get('pin_code')
        dob = request.POST.get('dob')
        company = request.POST.get('company')
        upi_id = request.POST.get('upi_id')
        pan = request.POST.get('pan')
        aadhaar = request.POST.get('aadhaar')
        uti_price = Decimal(request.POST.get('uti_price') or 0)
        nsdl_price = Decimal(request.POST.get('nsdl_price') or 0)

        state = State.objects.filter(id = state_id).first()
        district = District.objects.filter(id = district_id).first()

        login_id = f"SSC{mobile}"
        password = login_id

        user = User.objects.create(
            username = username,
            email = email,
            mobile = mobile,
            role = role,
            status = 'active',
            created_by = request.user,
            is_email_verified = True
        )

        user.set_password(password)
        user.is_active = True
        user.save()

        UserProfile.objects.create(
            user = user,
            gender = gender,
            address = address,
            pin_code = pin_code,
            dob = dob if dob else None,
            company = company,
            district = district,
            state = state,
            upi_id = upi_id,
            pan = pan,
            aadhaar = aadhaar,
            uti_price = uti_price,
            nsdl_price = nsdl_price,
            is_approved = True
        )

        send_mail(
            "Your Login Credentials",
            f"""
Welcome!

Your account has been created.

UserID : {login_id}
Password : {password}

Please login and change password.
""",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        messages.success(request, "User created successfully")
        return redirect("state_created_users")

    states = State.objects.all()
    districts = District.objects.all()

    roles = [
        role for role in User._meta.get_field('role').choices
        if role[0] not in ['admin', 'state']
    ]

    return render(request, "state_create_users.html", {
        "states": states,
        "districts": districts,
        "roles": roles,
        "gender": UserProfile._meta.get_field('gender').choices,
        "margin_slab": UserProfile._meta.get_field('margin_slab').choices
    })

@login_required
def state_created_users(request):

    if request.user.role != 'state':
        return redirect('login')

    search_query = request.GET.get('search', '')

    # districts created by state
    districts = User.objects.filter(
        role='district',
        created_by=request.user
    )

    # retailers created by those districts
    retailers = User.objects.filter(
        role='retailer',
        created_by__in=districts
    )

    # combine both
    users = User.objects.select_related(
        'profile', 'created_by'
    ).filter(
        Q(id__in=districts.values_list('id', flat=True)) |
        Q(id__in=retailers.values_list('id', flat=True))
    )

    if search_query:

        # support SSC search
        if search_query.upper().startswith("SSC"):
            search_query = search_query.replace("SSC", "")

        filters = (
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(mobile__icontains=search_query) |
            Q(profile__state__name__icontains=search_query) |
            Q(profile__district__name__icontains=search_query) |
            Q(profile__address__icontains=search_query)
        )

        if search_query.isdigit():
            filters |= Q(id=int(search_query))

        users = users.filter(filters)

    users = users.order_by('-profile__created_at')

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'state_created_users.html', {
        'users': page_obj,
        'search_query': search_query
    })

@login_required
def state_details(request, state_name):

    state_distributors = User.objects.filter(
        role='state',
        profile__state=state_name
    )

    district_count = 0
    retailer_count = 0
    distributor_details = []

    for sd in state_distributors:
        districts = User.objects.filter(created_by=sd, role='district')
        d_count = districts.count()

        retailers = User.objects.filter(created_by__in=districts, role='retailer')
        r_count = retailers.count()

        distributor_details.append({
            'sd': sd,
            'district_count': d_count,
            'retailer_count': r_count
        })

        district_count += d_count
        retailer_count += r_count

    state_count = state_distributors.count()

    return render(request, 'state_details.html', {
        'state_name': state_name,
        'distributor_details': distributor_details,
        'state_count': state_count,
        'district_count': district_count,
        'retailer_count': retailer_count,
    })


@login_required
def state_districts_list(request, user_id):
    state_distributor = User.objects.get(id=user_id)

    districts = User.objects.filter(
        created_by=state_distributor,
        role='district',
        profile__state=state_distributor.profile.state  # 👈 FIXED
    )

    return render(request, 'state_districts_list.html', {
        'state_distributor': state_distributor,
        'districts': districts
    })


@login_required
def state_retailers_list(request, user_id):
    state_distributor = User.objects.get(id=user_id)

    # Show only retailers created by THIS State Distributor
    retailers = User.objects.filter(
        role='retailer',
        created_by=state_distributor
    )

    return render(request, 'state_retailers_list.html', {
        'state_distributor': state_distributor,
        'retailers': retailers
    })



@login_required
def state_distributor_profile(request, user_id):
    distributor = User.objects.get(id=user_id)
    
    return render(request, 'state_distributor_profile.html', {
        'distributor': distributor
    })

@login_required
def admin_created_districts(request):
    if request.user.role != 'admin':
        return redirect('login')

    districts = User.objects.filter(
        role='district',
        created_by=request.user  # 👈 ONLY admin created users
    )

    return render(request, 'admin_created_districts.html', {
        'districts': districts
    })


@login_required
def retailer_profile(request, user_id):
    user = User.objects.get(id=user_id)
    profile = user.profile

    return render(request, 'retailer_profile.html', {
        'user': user,
        'profile': profile
    })


@login_required
def state_district_retailers(request, district_id):
    district_user = User.objects.get(id=district_id)

    # Safety check – Same state retailers only
    retailers = User.objects.filter(
        role='retailer',
        profile__district=district_user.profile.district,
        profile__state=district_user.profile.state
    )

    return render(request, 'state_district_retailers.html', {
        'district_user': district_user,
        'retailers': retailers
    })

@login_required
def list_retailers(request):
    user = request.user

    if user.role == 'admin':
        retailers = User.objects.filter(role='retailer').select_related('profile')
    elif user.role in ['state', 'district']:
        retailers = User.objects.filter(
            role='retailer',
            created_by=user
        ).select_related('profile')
    else:
        return redirect('login')

    return render(request, 'retailers_list.html', {
        'retailers': retailers
    })


@login_required
def admin_created_retailers(request):
    if request.user.role != 'admin':
        return redirect('login')

    retailers = User.objects.filter(
        role='retailer',
        created_by=request.user
    )

    return render(request, 'admin_created_retailers.html', {
        'retailers': retailers
    })


@login_required
def state_profile(request):
    if request.user.role != 'state':
        return redirect('login')

    return render(request, 'state_profile.html', {
        'user': request.user,
        'profile': request.user.profile
    })

@login_required
def district_create_user(request):

    if request.user.role != 'district':
        return redirect('login')

    if request.method == 'POST':

        username = request.POST.get('username')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        role = request.POST.get('role')

        state_id = request.POST.get('state')
        district_id = request.POST.get('district')

        gender = request.POST.get('gender')
        address = request.POST.get('address')
        pin_code = request.POST.get('pin_code')
        dob = request.POST.get('dob')
        company = request.POST.get('company')

        upi_id = request.POST.get('upi_id')
        pan = request.POST.get('pan')
        aadhaar = request.POST.get('aadhaar')

        uti_price = Decimal(request.POST.get('uti_price') or 0)
        nsdl_price = Decimal(request.POST.get('nsdl_price') or 0)

        # duplicate checks
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('district_create_user')

        if User.objects.filter(mobile=mobile).exists():
            messages.error(request, "Mobile already exists")
            return redirect('district_create_user')

        if UserProfile.objects.filter(pan=pan).exists():
            messages.error(request, "PAN already exists")
            return redirect('district_create_user')

        if UserProfile.objects.filter(aadhaar=aadhaar).exists():
            messages.error(request, "Aadhaar already exists")
            return redirect('district_create_user')

        # price validation
        district_price = request.user.profile.uti_price

        if uti_price < district_price:
            messages.error(request, "Retailer price cannot be less than your price")
            return redirect('district_create_user')

        state = State.objects.filter(id=state_id).first()
        district = District.objects.filter(id=district_id).first()

        login_id = f"SSC{mobile}"
        password = login_id

        user = User.objects.create(
            username=username,
            email=email,
            mobile=mobile,
            role=role,
            status='active',
            created_by=request.user,
            is_email_verified=True
        )

        user.set_password(password)
        user.is_active = True
        user.save()

        UserProfile.objects.create(
            user=user,
            gender=gender,
            address=address,
            pin_code=pin_code,
            dob=dob if dob else None,
            company=company,
            district=district,
            state=state,
            upi_id=upi_id,
            pan=pan,
            aadhaar=aadhaar,
            uti_price=uti_price,
            nsdl_price=nsdl_price,
            is_approved=True
        )

        # create wallets
        Wallet.objects.get_or_create(user=user)
        CommissionWallet.objects.get_or_create(user=user)

        send_mail(
            "Your Login Credentials",
            f"""
Welcome!

Your account has been created.

UserID : {login_id}
Password : {password}

Please login and change password.
""",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        messages.success(request, "Retailer created successfully")
        return redirect("district_created_users")

    states = State.objects.all()
    districts = District.objects.all()

    roles = [
        role for role in User._meta.get_field('role').choices
        if role[0] == 'retailer'
    ]

    return render(request, "district_create_users.html", {
        "states": states,
        "districts": districts,
        "roles": roles,
        "gender": UserProfile._meta.get_field('gender').choices,
    })


@login_required
def district_created_users(request):

    if request.user.role != 'district':
        return redirect('login')

    search_query = request.GET.get('search', '')

    users = User.objects.select_related(
        'profile', 'created_by'
    ).filter(created_by=request.user)

    if search_query:

        # support SSC search
        if search_query.upper().startswith("SSC"):
            search_query = search_query.replace("SSC", "")

        filters = (
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(mobile__icontains=search_query) |
            Q(profile__state__name__icontains=search_query) |
            Q(profile__district__name__icontains=search_query) |
            Q(profile__address__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )

        if search_query.isdigit():
            filters |= Q(id=int(search_query))

        users = users.filter(filters)

    users = users.order_by('-profile__created_at')

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'district_created_users.html', {
        'users': page_obj,
        'search_query': search_query
    })

@login_required
def district_profile(request):
    if request.user.role != 'district':
        return redirect('login')

    return render(request, 'district_profile.html', {
        'user': request.user,
        'profile': request.user.profile
    })


@login_required
def edit_contact(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        form = EditContactForm(request.POST)
        if form.is_valid():
            user.email = form.cleaned_data['email']
            profile.mobile = form.cleaned_data['mobile']

            user.save()
            profile.save()

            messages.success(request, "Contact updated successfully!")
            return redirect('login')  # Or redirect back to dashboard
    else:
        form = EditContactForm(initial={
            'email': user.email,
            'mobile': profile.mobile,
        })

    return render(request, 'edit_contact.html', {'form': form})

# ================================================================================================
# ================================================================================================
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import base64


@login_required
def add_money(request):
    form = WalletRequestForm()
    return render(request, 'wallet_add_step1.html', {
        'form': form,
        'user': request.user
    })


@login_required
def add_money_proceed(request):
    
    if request.method == "POST":
        form = WalletRequestForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount'] * Decimal("107")

            wallet_req = WalletRequest.objects.create(
                user=request.user,
                amount=amount,
                status='pending'
            )

            upi_id = "8304991136@cnrb"
            name = 'JANASAHAYA KENDRAM CHARITABLE SOCIETY'
            upi_link = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"

            qr = qrcode.make(upi_link)
            buffer = BytesIO()
            qr.save(buffer, format = 'PNG')
            qr_image = buffer.getvalue()

            qr_base64 = base64.b64encode(buffer.getvalue()).decode()

            return render(request, 'wallet_add_step2.html', {
                'request_obj': wallet_req,
                'qr_code': qr_base64
            })
    else:
        form = WalletRequest()
    return redirect('add_money')

@login_required
def wallet_status(request, req_id):
    wallet_req = WalletRequest.objects.get(id=req_id, user = request.user)
    return render(request, 'wallet_status.html', {
        'wallet_req': wallet_req
    })

@login_required
def wallet_requests_admin(request):
    if request.user.role != 'admin':
        return redirect('login')

    pending = WalletRequest.objects.filter(status='pending').order_by('-created_at')

    return render(request, 'wallet_requests_admin.html', {
        'pending': pending
    })
from django.db import transaction
from django.contrib import messages

@login_required
@transaction.atomic
def approve_wallet(request, req_id):

    if request.user.role != 'admin':
        return redirect('login')

    req = WalletRequest.objects.select_for_update().get(id=req_id)

    if req.status != 'pending':
        messages.error(request, "Already processed")
        return redirect('wallet_requests_admin')

    txn = create_wallet_transaction(
        user=req.user,
        amount=req.amount,
        txn_type='credit',
        description='Admin Approved Wallet Add'
    )

    txn.wallet_request = req
    txn.save(update_fields=['wallet_request'])

    req.status = 'approved'
    req.save(update_fields=['status'])

    messages.success(request, "Wallet approved successfully")

    return redirect('wallet_requests_admin')


@login_required
def reject_wallet(request, req_id):
    if request.user.role != 'admin':
        return redirect('login')

    req = WalletRequest.objects.get(id=req_id)
    req.status = 'rejected'
    req.save()  

    return redirect('wallet_requests_admin')

@login_required
def my_wallet_requests(request):
    # Ensure wallet exists
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    requests = WalletRequest.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'my_wallet_requests.html', {
        'requests': requests,
        'wallet': wallet
    })

from django.db.models import Q
from django.utils import timezone

@login_required
def wallet_approved_history(request):
    if request.user.role != 'admin':
        return redirect('login')

    search = request.GET.get('search', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    approved = WalletRequest.objects.filter(status='approved').order_by('-created_at')

    # Search filter
    if search:
        approved = approved.filter(
            Q(user__username__icontains=search) |
            Q(user__mobile__icontains=search)
        )

    # Date range filter
    if from_date and to_date:
        approved = approved.filter(
            created_at__date__range=[from_date, to_date]
        )

    return render(request, 'wallet_approved_history.html', {
        'approved': approved,
        'search': search,
        'from_date': from_date,
        'to_date': to_date,
    })


@login_required
def my_transactions(request):
    transactions = WalletTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'my_transactions.html', {
        'transactions': transactions,
        'wallet': request.user.wallet
    })

@login_required
def all_transactions(request):
    if request.user.role != 'admin':
        return redirect('login')

    transactions = WalletTransaction.objects.all().order_by('-created_at')

    search = request.GET.get('search')
    txn_type = request.GET.get('txn_type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if search:
        transactions = transactions.filter(
            Q(user__id__icontains=search) |
            Q(user__username__icontains=search)
        )

    if txn_type:
        transactions = transactions.filter(txn_type = txn_type)
    
    if start_date:
        transactions = transactions.filter(created_at__date__gte = start_date)

    if end_date:
        transactions = transactions.filter(created_at__date__lte = end_date)

    

    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_credit = transactions.filter(txn_type='credit').aggregate(total=Sum('amount'))['total'] or 0
    total_debit = transactions.filter(txn_type='debit').aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'all_transactions.html', {
        'transactions': page_obj,
        'total_credit': total_credit,
        'total_debit': total_debit,
    })

def admin_wallet():
    total = Wallet.objects.aggregate(Sum('balance'))['balance__sum'] or 0
    return total


@login_required
def admin_withdraw(request):
    if request.user.role != 'admin':
        return redirect('login')

    if request.method == "POST":
        amount = Decimal(request.POST.get("amount"))

        # Calculate system total
        total_balance = Wallet.objects.aggregate(balance=Sum('balance'))['balance'] or 0

        if total_balance < amount:
            messages.error(request, "Not enough money in system wallet!")
            return redirect("admin_dashboard")

        # Proportionally deduct from all users
        wallets = Wallet.objects.all()

        for w in wallets:
            if total_balance > 0:
                user_share = (w.balance / total_balance) * amount
                w.balance -= user_share
                w.save()

        # Log transaction
        WalletTransaction.objects.create(
            user=request.user,
            amount=amount,
            txn_type="debit",
            description="Admin Withdraw from System Wallet"
        )

        messages.success(request, f"₹{amount} withdrawn from System Wallet!")

        return redirect("admin_dashboard")

    return render(request, "admin_withdraw.html")



from decimal import Decimal
from django.contrib import messages

@login_required
def admin_add_money(request):
    if request.user.role != 'admin':
        return redirect('login')

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        wallet = request.user.wallet

        wallet.balance += amount
        wallet.save()

        WalletTransaction.objects.create(
            user=request.user,
            amount=amount,
            txn_type="credit",
            description="Admin Added to Wallet"
        )

        messages.success(request, f"₹{amount} added!")
        return redirect('admin_dashboard')

    return render(request, 'admin_add_money.html')

from .forms import CouponPurchaseForm
from .models import CouponPurchase, Wallet, RoleCouponPrice
from decimal import Decimal
@login_required
def buy_coupons(request):

    user = request.user
    form = CouponPurchaseForm()

    # ✅ Get price from user profile
    try:
        unit_price = user.profile.uti_price
    except:
        messages.error(request, "User profile not found.")
        return redirect("role_redirect")

    if not unit_price:
        messages.error(request, "Coupon price not configured.")
        return redirect("role_redirect")

    # Wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)

    if request.method == "POST":

        form = CouponPurchaseForm(request.POST)

        if form.is_valid():

            qty = form.cleaned_data['quantity']
            total = qty * unit_price

            if wallet.balance < total:
                messages.error(request, "Not enough balance.")
                return redirect("buy_coupons")

            CouponPurchase.objects.create(
                user=user,
                quantity=qty,
                unit_price=unit_price,
                total_amount=total,
                status='pending'
            )

            messages.success(request, "Request submitted.")
            return redirect("my_coupon_requests")

    return render(request, 'buy_coupons.html', {
        'form': form,
        'user_price': unit_price,
        'wallet_balance': wallet.balance
    })


@login_required
def coupon_requests_admin(request):

    if request.user.role != 'admin':
        return redirect('login')

    coupon_requests = CouponPurchase.objects.all().order_by('-created_at')

    search = request.GET.get('search')
    action = request.GET.get('action')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if search:
        coupon_requests = coupon_requests.filter(
            Q(user__id__icontains=search) |
            Q(user__username__icontains=search)
        )

    if action:
        coupon_requests = coupon_requests.filter(status=action)

    if start_date:
        coupon_requests = coupon_requests.filter(created_at__date__gte=start_date)

    if end_date:
        coupon_requests = coupon_requests.filter(created_at__date__lte=end_date)

    paginator = Paginator(coupon_requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'coupon_requests_admin.html', {
        'requests': page_obj
    })

@login_required
def my_coupon_requests(request):
    requests = CouponPurchase.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_coupon_requests.html', {'requests': requests})


def _sync_psa_master_status(req):
    if req.psa_username:
        PSAMaster.objects.filter(psa_login_id=req.psa_username).update(status=req.psa_status)


def _deduct_psa_processing_amount(req):
    if req.amount_deducted:
        return

    admin = User.objects.filter(role='admin').first()
    if not admin:
        raise ValueError("Admin user not found.")

    retailer_amount = Decimal("107")
    admin_amount = Decimal("93")
    retailer_wallet, _ = Wallet.objects.select_for_update().get_or_create(user=req.user)
    admin_wallet, _ = Wallet.objects.select_for_update().get_or_create(user=admin)

    if retailer_wallet.balance < retailer_amount:
        raise ValueError("Insufficient retailer wallet balance.")
    if admin_wallet.balance < admin_amount:
        raise ValueError("Insufficient admin wallet balance.")

    retailer_opening = retailer_wallet.balance
    admin_opening = admin_wallet.balance
    retailer_wallet.balance = retailer_opening - retailer_amount
    admin_wallet.balance = admin_opening - admin_amount
    retailer_wallet.save(update_fields=['balance'])
    admin_wallet.save(update_fields=['balance'])

    WalletTransaction.objects.create(
        user=req.user,
        amount=retailer_amount,
        txn_type='debit',
        opening_balance=retailer_opening,
        closing_balance=retailer_wallet.balance,
        description=f"PSA processing deduction for request #{req.id}"
    )
    WalletTransaction.objects.create(
        user=admin,
        amount=admin_amount,
        txn_type='debit',
        opening_balance=admin_opening,
        closing_balance=admin_wallet.balance,
        description=f"PSA admin deduction for request #{req.id}"
    )
    req.amount_deducted = True


def _issued_psa_expired(req):
    return (
        req.psa_status == 'issued'
        and req.approved_at
        and timezone.now() > req.approved_at + timedelta(minutes=30)
    )


def _busy_psa_login_ids():
    busy_ids = set()
    active_assignments = CouponPurchase.objects.filter(
        status='approved',
        psa_status__in=['issued', 'started', 'partially_completed']
    ).exclude(psa_username__isnull=True).exclude(psa_username='')

    for assignment in active_assignments:
        if assignment.psa_status == 'issued' and _issued_psa_expired(assignment):
            continue
        busy_ids.add(assignment.psa_username)

    return busy_ids


def _free_psa_queryset():
    return PSAMaster.objects.exclude(
        psa_login_id__in=_busy_psa_login_ids()
    ).order_by('-created_at')


def _psa_login_is_busy(psa_login_id):
    return psa_login_id in _busy_psa_login_ids()


@login_required
@transaction.atomic
def update_psa_lifecycle(request, req_id):
    if request.method != "POST":
        return redirect('my_coupon_requests')

    req = get_object_or_404(
        CouponPurchase.objects.select_for_update(),
        id=req_id,
        user=request.user,
        status='approved'
    )

    action = request.POST.get("action")
    submission_id = (request.POST.get("submission_id") or "").strip()

    try:
        if action == "start":
            if req.psa_status != "issued":
                messages.error(request, "PSA can be started only from issued status.")
                return redirect('my_coupon_requests')
            if _issued_psa_expired(req):
                req.done = True
                req.save(update_fields=['done'])
                messages.error(request, "PSA expired. Request again.")
                return redirect('my_coupon_requests')

            req.psa_status = "started"
            req.started_at = timezone.now()
            req.done = False
            req.save(update_fields=['psa_status', 'started_at', 'done'])
            _sync_psa_master_status(req)
            messages.success(request, "PSA marked as started.")

        elif action == "partial":
            if req.psa_status != "started":
                messages.error(request, "PSA can be partially completed only after start.")
                return redirect('my_coupon_requests')
            if not submission_id:
                messages.error(request, "Submission ID is required.")
                return redirect('my_coupon_requests')

            _deduct_psa_processing_amount(req)
            req.psa_status = "partially_completed"
            req.submission_id = submission_id
            req.save(update_fields=[
                'psa_status',
                'submission_id',
                'amount_deducted'
            ])
            _sync_psa_master_status(req)
            messages.success(request, "PSA marked as partially completed.")

        elif action == "rerequest":
            if req.psa_status != "partially_completed":
                messages.error(request, "Re-Request can be submitted only after partial completion.")
                return redirect('my_coupon_requests')
            if req.rerequest_status == "requested":
                messages.error(request, "Re-Request already submitted. Please wait for admin approval.")
                return redirect('my_coupon_requests')

            req.rerequest_status = "requested"
            req.rerequest_requested_at = timezone.now()
            req.save(update_fields=['rerequest_status', 'rerequest_requested_at'])
            messages.success(request, "Re-Request submitted successfully.")

        elif action == "full":
            if req.psa_status not in ["started", "partially_completed"]:
                messages.error(request, "PSA can be fully completed only after start.")
                return redirect('my_coupon_requests')
            if req.psa_status == "partially_completed" and req.rerequest_status == "requested":
                messages.error(request, "Please wait for admin approval before fully completing this PSA.")
                return redirect('my_coupon_requests')
            if req.psa_status == "partially_completed" and req.rerequest_status != "approved":
                messages.error(request, "Please submit a Re-Request and wait for admin approval before fully completing this PSA.")
                return redirect('my_coupon_requests')

            _deduct_psa_processing_amount(req)
            req.psa_status = "fully_completed"
            req.completed_at = timezone.now()
            req.done = True
            req.save(update_fields=['psa_status', 'amount_deducted', 'completed_at', 'done'])
            _sync_psa_master_status(req)
            messages.success(request, "PSA marked as fully completed.")

        else:
            messages.error(request, "Invalid PSA action.")

    except ValueError as e:
        messages.error(request, str(e))

    return redirect('my_coupon_requests')


@login_required
@transaction.atomic
def approve_coupon_psa(request, req_id):

    if request.user.role not in ['admin', 'state', 'district']:
        messages.error(request, "You are not allowed.")
        return redirect('login')

    req = get_object_or_404(
        CouponPurchase.objects.select_for_update(),
        id=req_id
    )

    if req.status != 'pending':
        messages.error(request, "Already processed.")
        return redirect('coupon_requests_admin')

    if request.method == "POST":

        psa_id = request.POST.get("psa_id")
        psa_balance = request.POST.get("psa_balance")
        topup_balance = request.POST.get("topup_balance")

        if not psa_id:
            messages.error(request, "PSA selection required.")
            return redirect('coupon_requests_admin')

        try:
            psa_master = PSAMaster.objects.get(id=psa_id)

            if _psa_login_is_busy(psa_master.psa_login_id):
                messages.error(request, "Selected PSA is currently in use. Please choose a free PSA.")
                return redirect('coupon_requests_admin')

            if psa_balance and psa_master.balance is None:
                initial_balance = Decimal(psa_balance)
                if initial_balance < 0:
                    raise ValueError("PSA balance cannot be negative.")
                psa_master.balance = initial_balance

            if topup_balance:
                topup_amount = Decimal(topup_balance)
                if topup_amount < 0:
                    raise ValueError("Top up balance cannot be negative.")
                psa_master.balance = (psa_master.balance or Decimal("0.00")) + topup_amount
            
            psa_master.status = 'issued'
            psa_master.save(update_fields=['balance', 'status'])

            psa_user = psa_master.psa_login_id
            psa_pass = psa_master.psa_password

            # SAVE PSA
            req.psa_username = psa_user
            req.psa_password = psa_pass
            req.psa_status = 'issued'
            req.submission_id = ''
            req.amount_deducted = False
            req.started_at = None
            req.completed_at = None
            req.rerequest_status = 'none'
            req.rerequest_requested_at = None

            # CHANGE STATUS → triggers model save()
            req.status = 'approved'

            req.save()

            distribute_commission(req)

        except PSAMaster.DoesNotExist:
            messages.error(request, "Invalid PSA selected.")
            return redirect('coupon_requests_admin')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('coupon_requests_admin')
        except InvalidOperation:
            messages.error(request, "Invalid PSA balance amount.")
            return redirect('coupon_requests_admin')

        messages.success(request, "Coupon Approved Successfully!")
        return redirect('coupon_requests_admin')

    available_psas = _free_psa_queryset()
    return render(request, 'approve_coupon_psa.html', {'req': req, 'available_psas': available_psas})


@login_required
def view_psa_details(request, req_id):
    req = get_object_or_404(CouponPurchase, id=req_id)

    if req.user != request.user:
        return redirect('login')

    if req.psa_status == 'partially_completed' and req.rerequest_status == 'requested':
        messages.error(request, "Please wait for admin approval.")
        return redirect('my_coupon_requests')

    if req.psa_status == 'partially_completed' and req.rerequest_status != 'approved':
        messages.error(request, "Please submit a Re-Request and wait for admin approval.")
        return redirect('my_coupon_requests')

    if req.psa_status not in ['started', 'partially_completed']:
        messages.error(request, "PSA Login ID can be viewed only after PSA is started.")
        return redirect('my_coupon_requests')

    if req.psa_status == 'issued' and req.approved_at:
        valid_until = req.approved_at + timedelta(minutes=30)
        now = timezone.now()

        # 🔥 STRICT BLOCK
        if now > valid_until:
            req.done = True
            req.save(update_fields=['done'])

            messages.error(request, "PSA expired. Request again.")
            return redirect('my_coupon_requests')

    return render(request, 'view_psa_details.html', {'req': req})


@login_required
def psa_assigned_list_admin(request):

    if request.user.role != 'admin':
        return redirect('login')

    query = request.GET.get('q')

    requests = CouponPurchase.objects.filter(status='approved')

    if query:
        requests = requests.filter(user__username__icontains=query)

    if request.method == "POST":
        req_id = request.POST.get("req_id")
        req = get_object_or_404(CouponPurchase, id=req_id)

        if not req.request_again:
            messages.error(request, "No request pending.")
            return redirect('psa_assigned_list_admin')

        req.request_again = False
        req.done = False
        req.approved_at = timezone.now()
        req.psa_status = 'issued'
        req.submission_id = ''
        req.amount_deducted = False
        req.started_at = None
        req.completed_at = None
        req.rerequest_status = 'none'
        req.rerequest_requested_at = None

        req.save(update_fields=[
            'request_again',
            'done',
            'approved_at',
            'psa_status',
            'submission_id',
            'amount_deducted',
            'started_at',
            'completed_at',
            'rerequest_status',
            'rerequest_requested_at'
        ])
        _sync_psa_master_status(req)

        messages.success(request, "PSA Reactivated Successfully")
        return redirect('psa_assigned_list_admin')

    requests = requests.order_by('-approved_at')

    now = timezone.now()

    for req in requests:
        psa = PSAMaster.objects.filter(psa_login_id=req.psa_username).first()
        req.psa_balance = psa.balance if psa else None
        req.psa_master_status = psa.get_status_display() if psa else '-'
        req.psa_is_expired = (
            req.psa_status == 'issued'
            and req.approved_at
            and now > req.approved_at + timedelta(minutes=30)
        )

    return render(request, 'psa_assigned_list_admin.html', {
        'requests': requests,
        'query': query
    })

@login_required
def request_psa_again(request, req_id):
    req = get_object_or_404(CouponPurchase, id=req_id)

    if req.user != request.user:
        return redirect('login')

    if req.psa_status == 'partially_completed':
        if req.rerequest_status == 'requested':
            messages.error(request, 'Already requested. Wait for admin.')
            return redirect('my_coupon_requests')

        req.rerequest_status = 'requested'
        req.rerequest_requested_at = timezone.now()
        req.save(update_fields=['rerequest_status', 'rerequest_requested_at'])

        messages.success(request, "Re-Request submitted successfully.")
        return redirect('my_coupon_requests')

    if req.request_again:
        messages.error(request, 'Already requested. Wait for admin.')
        return redirect('my_coupon_requests')

    if req.psa_status == 'issued' and req.approved_at:
        valid_until = req.approved_at + timedelta(minutes=30)
        if timezone.now() < valid_until:
            messages.error(request, "You can request only after expiry.")
            return redirect('my_coupon_requests')

    req.request_again = True
    req.done = False
    req.save(update_fields=['request_again', 'done'])

    messages.success(request, 'PSA requested successfully')
    return redirect('my_coupon_requests')


def _find_busy_psa_assignment(req):
    active_statuses = ['issued', 'started', 'partially_completed']
    others = CouponPurchase.objects.filter(
        status='approved',
        psa_username=req.psa_username,
        psa_status__in=active_statuses
    ).exclude(id=req.id).exclude(user_id=req.user_id).select_related('user')

    for other in others:
        if other.psa_status == 'issued' and _issued_psa_expired(other):
            continue
        return other

    return None


@login_required
def psa_rerequests_admin(request):
    if request.user.role != 'admin':
        return redirect('login')

    rerequests = CouponPurchase.objects.filter(
        status='approved',
        rerequest_status='requested'
    ).select_related('user').order_by('-rerequest_requested_at', '-created_at')

    for req in rerequests:
        busy_assignment = _find_busy_psa_assignment(req)
        req.busy_assignment = busy_assignment
        req.can_approve_rerequest = busy_assignment is None

    return render(request, 'psa_rerequests_admin.html', {
        'rerequests': rerequests
    })


@login_required
@transaction.atomic
def approve_psa_rerequest(request, req_id):
    if request.user.role != 'admin':
        return redirect('login')

    if request.method != "POST":
        return redirect('psa_rerequests_admin')

    req = get_object_or_404(
        CouponPurchase.objects.select_for_update(),
        id=req_id,
        status='approved',
        psa_status='partially_completed',
        rerequest_status='requested'
    )

    busy_assignment = _find_busy_psa_assignment(req)
    if busy_assignment:
        messages.error(request, f"PSA is currently in use by {busy_assignment.user.username}.")
        return redirect('psa_rerequests_admin')

    req.rerequest_status = 'approved'
    req.save(update_fields=['rerequest_status'])

    messages.success(request, "PSA re-request approved.")
    return redirect('psa_rerequests_admin')


def _update_psa_master_password(psa_login_id, new_password):
    psa_master = get_object_or_404(
        PSAMaster.objects.select_for_update(),
        psa_login_id=psa_login_id
    )

    psa_master.psa_password = new_password
    psa_master.save(update_fields=['psa_password'])

    return CouponPurchase.objects.filter(
        psa_username=psa_login_id
    ).update(psa_password=new_password)


@login_required
@transaction.atomic
def update_psa_rerequest_password(request):
    if request.user.role != 'admin':
        return redirect('login')

    if request.method != "POST":
        return redirect('psa_rerequests_admin')

    psa_login_id = (request.POST.get("psa_login_id") or "").strip()
    new_password = (request.POST.get("new_password") or "").strip()

    if not psa_login_id:
        messages.error(request, "PSA Login ID is required.")
        return redirect('psa_rerequests_admin')

    if not new_password:
        messages.error(request, "New password is required.")
        return redirect('psa_rerequests_admin')

    if len(new_password) < 4:
        messages.error(request, "New password must be at least 4 characters.")
        return redirect('psa_rerequests_admin')

    updated_assignments = _update_psa_master_password(psa_login_id, new_password)

    messages.success(
        request,
        f"Password updated for {psa_login_id}. Synced {updated_assignments} assignment(s)."
    )
    return redirect('psa_rerequests_admin')


@login_required
@transaction.atomic
def update_psa_assigned_password(request):
    if request.user.role != 'admin':
        return redirect('login')

    if request.method != "POST":
        return redirect('psa_assigned_list_admin')

    psa_login_id = (request.POST.get("psa_login_id") or "").strip()
    new_password = (request.POST.get("new_password") or "").strip()

    if not psa_login_id:
        messages.error(request, "PSA Login ID is required.")
        return redirect('psa_assigned_list_admin')

    if not new_password:
        messages.error(request, "New password is required.")
        return redirect('psa_assigned_list_admin')

    if len(new_password) < 4:
        messages.error(request, "New password must be at least 4 characters.")
        return redirect('psa_assigned_list_admin')

    updated_assignments = _update_psa_master_password(psa_login_id, new_password)

    messages.success(
        request,
        f"Password updated for {psa_login_id}. Synced {updated_assignments} assignment(s)."
    )
    return redirect('psa_assigned_list_admin')


@login_required
def my_commissions(request):
    commissions = CommissionTransaction.objects.filter(user=request.user).order_by('-created_at')

    total_commission = commissions.aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'my_commissions.html', {
        'commissions': commissions,
        'total_commission': total_commission
    })

@login_required
def admin_commission_dashboard(request):
    if request.user.role != 'admin':
        return redirect('login')

    total_admin = CommissionTransaction.objects.filter(level="Admin").aggregate(Sum('amount'))['amount__sum'] or 0
    total_state = CommissionTransaction.objects.filter(level="State").aggregate(Sum('amount'))['amount__sum'] or 0
    total_district = CommissionTransaction.objects.filter(level="District").aggregate(Sum('amount'))['amount__sum'] or 0

    recent_commissions = CommissionTransaction.objects.all().order_by('-created_at')[:20]

    return render(request, 'admin_commission_dashboard.html', {
        'total_admin': total_admin,
        'total_state': total_state,
        'total_district': total_district,
        'recent_commissions': recent_commissions
    })


@login_required
def distributor_commission_dashboard(request):
    if request.user.role not in ['state', 'district']:
        return redirect('login')

    user = request.user

    commissions = CommissionTransaction.objects.filter(user=user).order_by('-created_at')

    total_commission = commissions.aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'distributor_commission_dashboard.html', {
        'commissions': commissions,
        'total_commission': total_commission,
        'user': user
    })


@login_required
def request_commission_withdraw(request):
    if request.user.role not in ['state', 'district']:
        return redirect('login')

    form = CommissionWithdrawForm()

    if request.method == 'POST':
        form = CommissionWithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']

            # 🔹 check COMMISSION WALLET, not main wallet
            comm_wallet = request.user.commission_wallet

            if comm_wallet.balance < amount:
                messages.error(request, "Not enough commission balance")
                return redirect('request_commission_withdraw')

            CommissionWithdrawRequest.objects.create(
                user=request.user,
                amount=amount,
                status='pending'
            )

            messages.success(request, "Withdraw request submitted!")
            return redirect('distributor_commission_dashboard')

    return render(request, 'request_commission_withdraw.html', {'form': form})

@login_required
def admin_withdraw_requests(request):
    if request.user.role != 'admin':
        return redirect('login')

    pending = CommissionWithdrawRequest.objects.filter(status='pending').order_by('-created_at')

    return render(request, 'admin_withdraw_requests.html', {
        'pending': pending
    })


@login_required
def approve_commission_withdraw(request, req_id):
    if request.user.role != 'admin':
        return redirect('login')

    req = CommissionWithdrawRequest.objects.get(id=req_id)
    user = req.user
    comm_wallet = user.commission_wallet

    if comm_wallet.balance >= req.amount:
        # 🔹 debit from commission wallet
        comm_wallet.balance -= req.amount
        comm_wallet.save()

        req.status = "approved"
        req.save()

        # optional: log as commission transaction (debit)
        CommissionTransaction.objects.create(
            user=user,
            from_user=None,
            coupon_request=None,
            amount=req.amount,
            level="Withdraw",
            txn_type="debit",
        )

        messages.success(request, f"₹{req.amount} Commission Withdrawal Approved!")
    else:
        messages.error(request, "Not enough commission wallet balance!")

    return redirect('admin_withdraw_requests')

@login_required
def reject_commission_withdraw(request, req_id):
    if request.user.role != 'admin':
        return redirect('login')

    req = CommissionWithdrawRequest.objects.get(id=req_id)
    req.status = "rejected"
    req.save()

    messages.success(request, "Withdraw Rejected!")
    return redirect('admin_withdraw_requests')



from decimal import Decimal
from .models import CommissionWallet, CommissionTransaction, User

from decimal import Decimal
from .models import CommissionTransaction, User


def distribute_commission(purchase):

    buyer = purchase.user
    creator = buyer.created_by
    quantity = purchase.quantity

    admin = User.objects.filter(role='admin').first()

    admin_comm = Decimal(0)
    state_comm = Decimal(0)
    district_comm = Decimal(0)

    buyer_price = buyer.profile.uti_price

    # BUYER IS STATE
    if buyer.role == "state":

        admin_price = Decimal("93")   # base system price
        admin_comm = buyer_price - admin_price

    # BUYER IS DISTRICT
    elif buyer.role == "district":

        if creator and creator.role == "state":

            state_price = creator.profile.uti_price
            state_comm = buyer_price - state_price
            admin_comm = state_price - Decimal("93")

        elif creator and creator.role == "admin":

            admin_comm = buyer_price - Decimal("93")

    # BUYER IS RETAILER
    elif buyer.role == "retailer":

        if creator and creator.role == "district":

            district_price = creator.profile.uti_price

            district_comm = buyer_price - district_price

            parent_state = creator.created_by

            if parent_state and parent_state.role == "state":

                state_price = parent_state.profile.uti_price
                state_comm = district_price - state_price
                admin_comm = state_price - Decimal("93")

        elif creator and creator.role == "state":

            state_price = creator.profile.uti_price
            state_comm = buyer_price - state_price
            admin_comm = state_price - Decimal("93")

        elif creator and creator.role == "admin":

            admin_comm = buyer_price - Decimal("93")

    # multiply by quantity
    admin_comm *= quantity
    state_comm *= quantity
    district_comm *= quantity

    def credit(user, amount, level):

        if user and amount > 0:

            wallet = user.commission_wallet
            wallet.balance += amount
            wallet.save()

            CommissionTransaction.objects.create(
                user=user,
                from_user=buyer,
                coupon_request=purchase,
                amount=amount,
                level=level,
                txn_type="credit"
            )

    credit(admin, admin_comm, "Admin")

    if creator and creator.role == "state":
        credit(creator, state_comm, "State")

    if creator and creator.role == "district":
        credit(creator, district_comm, "District")

@login_required
def my_commission_wallet(request):
    wallet = request.user.commission_wallet

    transactions = CommissionTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    return render(request, 'commission_wallet.html', {
        "wallet": wallet,
        "transactions": transactions
    })


@login_required
def commission_history(request):
    txns = request.user.commissions_received.order_by('-created_at')

    search = request.GET.get('search')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if search:
        txns = txns.filter(from_user__username__icontains = search)
    
    if start_date:
        txns = txns.filter(created_at__date__gte = start_date)

    if end_date:
        txns = txns.filter(created_at__date__lte = end_date)


    return render(request, 'commission_history.html', {"txns": txns})



@login_required
def admin_commission_withdraw(request):
    if request.user.role != 'admin':
        return redirect('login')

    commission_wallet, _ = CommissionWallet.objects.get_or_create(user=request.user)

    if request.method == "POST":
        amount = Decimal(request.POST.get("amount"))

        if amount <= 0:
            messages.error(request, "Invalid amount!")
            return redirect('admin_commission_withdraw')

        if commission_wallet.balance < amount:
            messages.error(request, "Not enough commission balance!")
            return redirect('admin_commission_withdraw')

        commission_wallet.balance -= amount
        commission_wallet.save()

        CommissionTransaction.objects.create(
        user=request.user,
        from_user=request.user,
        amount=amount,
        level="Admin"
)

        messages.success(request, f"₹{amount} withdrawn from Admin Commission Wallet!")
        return redirect('admin_commission_withdraw')

    return render(request, 'admin_commission_withdraw.html', {
        "wallet": commission_wallet
    })


@login_required
def admin_all_commissions(request):
    if request.user.role != 'admin':
        return redirect('login')

    users = User.objects.filter(role__in=['admin', 'state', 'district'])

    data = []
    for u in users:
        wallet, _ = CommissionWallet.objects.get_or_create(user=u)
        total_commission = CommissionTransaction.objects.filter(user=u).aggregate(
            total=Sum('amount')
        )['total'] or 0

        data.append({
            'user': u,
            'wallet_balance': wallet.balance,
            'total_commission': total_commission
        })

    return render(request, 'admin_all_commissions.html', {
        'data': data
    })

# change  PSA master
@login_required
def psa_master_list(request):
    if request.user.role != 'admin':
        return redirect('login')
    psas = PSAMaster.objects.all().order_by('-created_at')
    return render(request, 'psa_master/psa_master_list.html', {'psas': psas})

@login_required
def psa_master_add(request):
    if request.user.role != 'admin':
        return redirect('login')
    
    if request.method == 'POST':
        psa_login_id = request.POST.get('psa_login_id')
        psa_password = request.POST.get('psa_password')
        
        if PSAMaster.objects.filter(psa_login_id=psa_login_id).exists():
            messages.error(request, 'PSA Login ID already exists.')
        else:
            PSAMaster.objects.create(psa_login_id=psa_login_id, psa_password=psa_password)
            messages.success(request, 'PSA Master added successfully.')
            return redirect('psa_master_list')
            
    return render(request, 'psa_master/psa_master_form.html', {'action': 'Add'})

@login_required
def psa_master_edit(request, pk):
    if request.user.role != 'admin':
        return redirect('login')
        
    psa = get_object_or_404(PSAMaster, pk=pk)
    
    if request.method == 'POST':
        psa_login_id = request.POST.get('psa_login_id')
        psa_password = request.POST.get('psa_password')
        
        if PSAMaster.objects.filter(psa_login_id=psa_login_id).exclude(pk=pk).exists():
            messages.error(request, 'PSA Login ID already exists.')
        else:
            psa.psa_login_id = psa_login_id
            psa.psa_password = psa_password
            psa.save()
            messages.success(request, 'PSA Master updated successfully.')
            return redirect('psa_master_list')
            
    return render(request, 'psa_master/psa_master_form.html', {'action': 'Edit', 'psa': psa})

@login_required
def psa_master_delete(request, pk):
    if request.user.role != 'admin':
        return redirect('login')
        
    psa = get_object_or_404(PSAMaster, pk=pk)
    if request.method == 'POST':
        psa.delete()
        messages.success(request, 'PSA Master deleted successfully.')
        return redirect('psa_master_list')
    
    return render(request, 'psa_master/psa_master_form.html', {'action': 'Delete', 'psa': psa})

@login_required
def all_psa_history(request):
    if request.user.role != 'admin':
        return redirect('login')

    search_query = request.GET.get('psa_id', '').strip()
    psas = PSAMaster.objects.all().order_by('-created_at')
    
    data = []
    now = timezone.now()
    
    for psa in psas:
        history = CouponPurchase.objects.filter(psa_username=psa.psa_login_id).order_by('-approved_at')
        
        active_count = 0
        for h in history:
            h.is_active = False
            h.is_expired = False
            h.lifecycle_label = h.get_psa_status_display()
            h.lifecycle_class = 'status-active'
            
            if h.approved_at and not h.done:
                valid_until = h.approved_at + timedelta(minutes=30)
                if now <= valid_until:
                    h.is_active = True
                    active_count += 1
                else:
                    h.is_expired = True
                    if h.psa_status == 'issued':
                        h.lifecycle_label = 'Expired'
                        h.lifecycle_class = 'status-expired'
            elif h.done:
                h.is_expired = True
                h.lifecycle_class = 'status-complete'

            if h.request_again:
                h.lifecycle_label = 'Requested Reactivation'
                h.lifecycle_class = 'status-pending'
            elif h.psa_status == 'fully_completed':
                h.lifecycle_class = 'status-complete'
            elif h.psa_status == 'partially_completed':
                h.lifecycle_class = 'status-partial'
            elif h.psa_status == 'started':
                h.lifecycle_class = 'status-started'

        data.append({
            'psa': psa,
            'history': history,
            'active_count': active_count
        })

    return render(request, 'psa_master/all_psa_history.html', {
        'data': data,
        'search_query': search_query
    })



