from pyexpat.errors import messages
import random
from django.conf import settings
from django.shortcuts import get_object_or_404, render,redirect
from django.views.decorators.cache import never_cache
from django.contrib.auth import login,logout,get_backends
from django.http import JsonResponse
from django.core.mail import send_mail
from myapp.models import CustomUser,Product,banner,ProductImage,Category,Brand
from myapp.forms import UserSignupForm,UserLoginForm
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.utils.timezone import now
from django.db.models import Prefetch,Q,Min,Max
from decimal import Decimal
from django.contrib.auth.decorators import login_required
import json
from django.core.paginator import Paginator


 


# Create your views here.


@never_cache
def user_signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    
   
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False 
            user.set_password(form.cleaned_data['password'])
            user.save()

           
            otp = random.randint(100000, 999999)
            request.session['otp'] = str(otp)
            request.session['user_id'] = user.id
            request.session['otp_purpose'] = 'signup'



            
            send_mail(
                subject='Noirmist - Your OTP Code',
                message=f'Your OTP is {otp}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return redirect('otp_verify') 
    else:
        form = UserSignupForm()
    
    return render(request, 'usersignup.html', {'form': form})

@never_cache
def otp_verify(request):
    # Redirect if already authenticated
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('home')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        original_otp = request.session.get('otp')
        user_id = request.session.get('user_id')
        purpose = request.session.get('otp_purpose')

        if entered_otp == original_otp:
            user = get_object_or_404(CustomUser, id=user_id)

            # Clear session values safely
            request.session.pop('otp', None)
            request.session.pop('user_id', None)
            request.session.pop('otp_purpose', None)

            if purpose == 'signup':
                user.is_active = True
                user.save()
                messages.success(request, "Your account has been activated. You can now log in.")
                return redirect('user_login')

            elif purpose == 'reset':
                request.session['reset_user_id'] = user.id
                return redirect('reset_password')

        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('otp_verify')

    return render(request, 'otp_page.html', {'otp_title': 'OTP Verification'})

@never_cache
def resend_otp(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Session expired. Please sign up again.'})

    user = get_object_or_404(CustomUser, id=user_id)

    
    otp = random.randint(100000, 999999)
    request.session['otp'] = str(otp)

    
    send_mail(
        subject='Noirmist - Your New OTP Code',
        message=f'Your new OTP is {otp}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return JsonResponse({'success': True, 'message': 'OTP resent successfully.'})

import logging

@never_cache
def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    current_path = request.path

   
    logger = logging.getLogger(__name__)
    logger.warning(f"Redirected here with path: {request.path}")

    if request.path.startswith('/accounts/'):
            return redirect(request.path)

    if request.session.get('user'):
        return redirect('home')

    if request.session.get('adminuser'):
        return redirect('admin_dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.user
            if user.is_superuser:
                form.add_error(None, "Admins cannot log in here.") 
            else:
                backends = get_backends()
                user.backend = f"{backends[0].__module__}.{backends[0].__class__.__name__}"
                login(request, user)
                request.session['user'] = user.username
                return redirect('home')
    else:
        form = UserLoginForm()
    
    return render(request, 'user_login.html', {'form': form})


@never_cache

def home(request):
    if not request.user.is_authenticated:
        return redirect('user_login')
       
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    

    current_date = now().date()

    banners = banner.objects.filter(start_date__lte=current_date, end_date__gte=current_date)

    
    def attach_main_image(products):
        for product in products:
            main_image = product.productimage_set.filter(is_main=True).first()
            product.main_image = main_image
            
            product.discount_percent = 10
            product.discounted_price = product.default_price * Decimal('0.9')
        return products

    fresh_arrivals = Product.objects.select_related('category_id', 'brand_id') \
        .prefetch_related('variants', 'productimage_set') \
        .filter(status='listed', is_deleted=False) \
        .order_by('-created_at')[:4]
    fresh_arrivals = attach_main_image(fresh_arrivals)

    best_selling = Product.objects.select_related('category_id', 'brand_id') \
        .prefetch_related('variants', 'productimage_set') \
        .filter(status='listed', is_deleted=False) \
        .order_by('-default_stock')[:4]
    best_selling = attach_main_image(best_selling)

    recommended = Product.objects.select_related('category_id', 'brand_id') \
        .prefetch_related('variants', 'productimage_set') \
        .filter(status='listed', is_deleted=False)[:4]
    recommended = attach_main_image(recommended)

    return render(request, 'home.html', {
        'banners': banners,
        'fresh_arrivals': fresh_arrivals,
        'best_selling': best_selling,
        'recommended': recommended
    })
@never_cache
def user_logout(request):
    
    if request.method == 'POST':
        logout(request)
        request.session.flush() 
        return redirect('user_login')
    
def forgot_password(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')


    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            otp = random.randint(100000, 999999)

            request.session['user_id'] = user.id
            request.session['otp'] = str(otp)
            request.session['otp_purpose'] = 'reset'


            send_mail(
                'Noirmist - Password Reset OTP',
                f'Your OTP for password reset is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return redirect('otp_verify')

        except CustomUser.DoesNotExist:
            messages.error(request, 'No account found with this email.')
    
    return render(request, 'forgot_password.html')


def reset_password(request):
    

    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')

    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            user.password = make_password(password1)
            user.save()

            
            request.session.pop('reset_user_id', None)
            request.session.pop('reset_otp', None)

            messages.success(request, "Password reset successful. Please log in.")
            return redirect('user_login')

    return render(request, 'reset_password.html')
    

def base(request):
    return render(request,'user_base.html')


def product_list(request):
    category_filter = request.GET.getlist('category')
    brand_filter = request.GET.getlist('brand')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort')
    query = request.GET.get('q') 

    
    products = Product.objects.filter(is_deleted=False, status='listed')

    
    if category_filter:
        products = products.filter(category_id__category_id__in=category_filter)

    if brand_filter:
        products = products.filter(brand_id__brand_id__in=brand_filter)

    if min_price and max_price:
        try:
            min_price = float(min_price) / 0.9  
            max_price = float(max_price) / 0.9  
            products = products.filter(variants__price__range=(min_price, max_price))
        except (ValueError, TypeError):
            
            pass

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(category_id__name__icontains=query) |
            Q(brand_id__name__icontains=query)
        )

   
    products = products.annotate(min_price=Min('variants__price'))

   
    if sort == 'price_asc':
        products = products.order_by('min_price')
    elif sort == 'price_desc':
        products = products.order_by('-min_price')


    products = products.distinct()

   
    products = products.prefetch_related(
        Prefetch('variants'),
        Prefetch('productimage_set', queryset=ProductImage.objects.filter(is_main=True), to_attr='main_images')
    )

    
    for product in products:
        discount = 10
        product.discount_percent = discount
       
        base_price = product.min_price if product.min_price is not None else product.default_price
        product.discounted_price = round(base_price * (100 - discount) / 100)

    categories = Category.objects.filter(is_deleted=False, status='Listed')
    brands = Brand.objects.filter(is_deleted=False, status='Listed')

    paginator = Paginator(products, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'product_list.html', {
        'products': page_obj.object_list,
        'categories': categories,
        'brands': brands,
        'query': query,
        'selected_categories': list(map(int, category_filter)) if category_filter else [],
        'selected_brands': list(map(int, brand_filter)) if brand_filter else [],
        'page_obj': page_obj,
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_deleted=False, status='listed')
    variants = product.variants.all()
    images = ProductImage.objects.filter(product_id=product)

    
    selected_variant = variants.first()

    
    variant_data = [
        {
            'size': str(variant.size),  
            'price': float(variant.price),  
            'stock': int(variant.stock), 
            'discounted_price': float(variant.price) * 0.9  
        }
        for variant in variants
    ]

   
    if selected_variant:
        original_price = float(selected_variant.price)  
        discount_percent = 10
        discounted_price = original_price * 0.9 
    else:
        original_price = discounted_price = discount_percent = None

    context = {
        'product': product,
        'variants': variants,
        'images': images,
        'selected_variant': selected_variant,
        'original_price': original_price,
        'discounted_price': discounted_price,
        'discount_percent': discount_percent,
        'variant_data_json': json.dumps(variant_data), 
    }
    return render(request, 'product_detail.html', context)

def cart(request):
    return render(request,'cart.html')
def profile(request):
    return render(request,'profile.html')