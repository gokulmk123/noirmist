from pyexpat.errors import messages
import random
from django.conf import settings
from django.shortcuts import get_object_or_404, render,redirect
from django.views.decorators.cache import never_cache
from django.contrib.auth import login,logout,get_backends
from django.http import JsonResponse
from django.core.mail import send_mail
from myapp.models import CustomUser,Product,banner,ProductImage,Category,Brand,Address,ProductVariant,Cart,CartItem,WishlistItem
from myapp.models import Order,OrderItem
from myapp.forms import UserSignupForm,UserLoginForm ,ShippingAddressForm
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.utils.timezone import now
from django.db.models import Prefetch,Q,Min,Max
from decimal import Decimal
from django.contrib.auth.decorators import login_required
import json
from django.core.paginator import Paginator
import os
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from .utils import get_or_create_cart
from django.views.decorators.http import require_POST


 


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
    purpose = request.session.get('otp_purpose')

    # Prevent redirecting if user is logged in but came for 'edit_email'
    if request.user.is_authenticated and purpose != 'edit_email':
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
            elif purpose == 'edit_email':
                new_email = request.session.get('new_email')
                if not new_email:
                    messages.error(request, "Something went wrong. Please try again.")
                    return redirect('profile')

                user.email = new_email
                user.save()

                messages.success(request, "Your email has been updated successfully.")
                return redirect('profile')


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
            min_price = float(min_price) / 0.9  # Adjust for 10% discount
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

    # Annotate with minimum variant price for sorting
    products = products.annotate(min_price=Min('variants__price'))

    if sort == 'price_asc':
        products = products.order_by('min_price')
    elif sort == 'price_desc':
        products = products.order_by('-min_price')

    products = products.distinct()

    # Prefetch variants (ordered by size) and main images
    products = products.prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.order_by('size')),
        Prefetch('productimage_set', queryset=ProductImage.objects.filter(is_main=True), to_attr='main_images')
    )

    # Set display attributes based on smallest size variant
    for product in products:
        discount = 10
        product.discount_percent = discount
        smallest_variant = product.variants.first()  # First variant after ordering by size
        if smallest_variant:
            product.default_variant_id = smallest_variant.id
            product.display_size = smallest_variant.size
            product.display_price = smallest_variant.price  # Use display_price instead of default_price
            product.discounted_price = round(smallest_variant.price * Decimal((100 - discount) / 100), 2)
        else:
            product.default_variant_id = None
            product.display_size = None
            product.display_price = None
            product.discounted_price = None

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

    variant_data = {
        str(variant.id): {
            'size': str(variant.size),
            'price': float(variant.price),
            'stock': int(variant.stock),
            'discounted_price': round(float(variant.price) * 0.9, 2)
        }
        for variant in variants
    }

   
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
        'variant_data_json': json.dumps(variant_data),  # Important
    }
    return render(request, 'product_detail.html', context)







def profile(request):
    user = request.user
    default_address = user.addresses.filter(is_default=True).first()

    addresses=user.addresses.all()
    
    return render(request, 'profile.html', {
        'default_address': default_address,
        'addresses':addresses
    })


def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username')
        user.mobile = request.POST.get('phone')
        user.save()

        selected_address_id = request.POST.get('default_address')
        if selected_address_id:
            Address.objects.filter(user=user).update(is_default=False)
            Address.objects.filter(id=selected_address_id, user=user).update(is_default=True)

        messages.success(request, "Profile updated successfully.")
        return redirect('profile')

def update_profile_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        user = request.user
        new_image = request.FILES['image']

        # ✅ Delete old image file if it exists
        if user.image and user.image.name and user.image.name != new_image.name:
            old_image_path = os.path.join(settings.MEDIA_ROOT, user.image.name)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

        # ✅ Save the new image
        user.image = new_image
        user.save()

    return redirect('profile')

def address_list_view(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')

        if address_id:
            # UPDATE existing address
            address = get_object_or_404(Address, id=address_id, user=request.user)
            address.full_name = request.POST.get('full_name')
            address.mobile = request.POST.get('mobile')
            address.city = request.POST.get('city')
            address.state = request.POST.get('state')
            address.zip_code = request.POST.get('zip_code')
            address.country = request.POST.get('country')
            address.the_address = request.POST.get('Address')
            address.save()
        else:
            # CREATE new address
            if request.POST.get('is_default'):
                Address.objects.filter(user=request.user).update(is_default=False)
            Address.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name'),
                mobile=request.POST.get('mobile'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                zip_code=request.POST.get('zip_code'),
                country=request.POST.get('country'),
                the_address=request.POST.get('Address'),
                is_default=bool(request.POST.get('is_default')),
            )

        return redirect('address')

    addresses = Address.objects.filter(user=request.user).order_by('-is_default')
    return render(request, 'address.html', {'addresses': addresses})


def set_default_address(request, address_id):
    if request.method == "POST":
        # Unset all current default addresses
        Address.objects.filter(user=request.user).update(is_default=False)

        # Set selected address as default
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.is_default = True
        address.save()

        messages.success(request, "Default address updated.")
    
    return redirect('address')

def delete_address( request,address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.delete()
    return redirect('address')



def edit_email(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')
        
        if CustomUser.objects.filter(email__iexact=new_email).exclude(id=request.user.id).exists():
            messages.error(request, 'Email already in use by another user.')
            return render(request, 'edit_email.html', {'email': new_email})

        otp = str(random.randint(100000, 999999))
        request.session['otp'] = otp
        request.session['user_id'] = request.user.id
        request.session['otp_purpose'] = 'edit_email'
        request.session['new_email'] = new_email

        send_mail(
            subject='Noirmist - OTP for Email Change',
            message=f'Your OTP for email change is {otp}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[new_email],
            fail_silently=False,
        )
        return redirect('otp_verify')

    return render(request, 'edit_email.html')


def set_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        if not user.check_password(old_password):
            messages.error(request, "Old password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # prevent logout
            messages.success(request, "Password updated successfully.")
            return redirect('profile')  # or wherever you want to go

    return render(request, 'set_password.html')
def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user, defaults={'user': request.user})
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, defaults={'session_key': session_key})
    return cart

@login_required
@require_POST
def add_to_cart(request):
    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))

    try:
        variant = ProductVariant.objects.get(id=variant_id)
        if quantity < 1:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Quantity must be at least 1.'})
            else:
                messages.error(request, 'Quantity must be at least 1.')
                return redirect('product_detail', variant.product_id.id)
        if quantity > variant.stock:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': f'Only {variant.stock} items available.'})
            else:
                messages.error(request, f'Only {variant.stock} items available.')
                return redirect('product_detail', variant.product_id.id)

        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'Only {variant.stock} items available.'})
                else:
                    messages.error(request, f'Only {variant.stock} items available.')
                    return redirect('product_detail', variant.product_id.id)
            cart_item.quantity = new_quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        
        wishlist_item = WishlistItem.objects.filter(user=request.user, product=variant.product_id).first()
        if wishlist_item:
            wishlist_item.delete()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Item added to cart'})
        else:
            messages.success(request, 'Item added to cart.')
            return redirect('cart')
    except ProductVariant.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Invalid product variant.'})
        else:
            messages.error(request, 'Invalid product variant.')
            return redirect('product_list')
    except ValueError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Invalid quantity.'})
        else:
            messages.error(request, 'Invalid quantity.')
            return redirect('product_list')
    if not request.user.is_authenticated and not request.session.session_key:
        return JsonResponse({'status': 'error', 'message': 'Please log in or start a session.'})

    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))

    try:
        variant = ProductVariant.objects.get(id=variant_id)
        if quantity < 1:
            return JsonResponse({'status': 'error', 'message': 'Quantity must be at least 1.'})
        if quantity > variant.stock:
            return JsonResponse({'status': 'error', 'message': f'Only {variant.stock} items available.'})

        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                return JsonResponse({'status': 'error', 'message': f'Only {variant.stock} items available.'})
            cart_item.quantity = new_quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({'status': 'success', 'message': 'Item added to cart'})
    except ProductVariant.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid product variant.'})
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid quantity.'})

def cart(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('variant__product_id').prefetch_related('variant__images', 'variant__product_id__productimage_set')
    
    for item in cart_items:
        
        item.discounted_price = Decimal(str(item.variant.price)) * Decimal('0.9')
        
        item.main_image = item.variant.images.filter(is_main=True).first()
        if not item.main_image:
            
            item.main_image = item.variant.product_id.productimage_set.filter(is_main=True).first()
    
    context = {'cart_items': cart_items}
    try:
        subtotal = sum(item.discounted_price * item.quantity for item in cart_items if item.variant.product_id)
        
        total = round(subtotal , 2)
        context.update({'subtotal': subtotal,  'total': total})
    except Exception as e:
        print(f"Error calculating totals: {e}")

    return render(request, 'cart.html', context)

@require_POST
def update_cart_item(request):
    if not request.user.is_authenticated and not request.session.session_key:
        return JsonResponse({'status': 'error', 'message': 'Please log in or start a session.'})

    try:
       
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity'))

        if not item_id or quantity < 1:
            return JsonResponse({'status': 'error', 'message': 'Invalid item ID or quantity.'})

        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        variant = cart_item.variant

        if quantity > variant.stock:
            return JsonResponse({'status': 'error', 'message': f'Only {variant.stock} items available.'})

        cart_item.quantity = quantity
        cart_item.save()

        
        cart_items = cart.items.select_related('variant__product_id')
        subtotal = sum((Decimal(str(item.variant.price)) * Decimal('0.9')) * item.quantity for item in cart_items if item.variant.product_id)
        
       
        total = round(subtotal , 2)

        return JsonResponse({
            'status': 'success',
            'message': 'Cart updated',
            'subtotal': float(subtotal),
            
            'total': float(total)
        })
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found.'})
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid quantity.'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'})
    except Exception as e:
        print(f"Error updating cart item: {e}")
        return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'})

@require_POST
def remove_cart_item(request):
   
    if not request.user.is_authenticated and not request.session.session_key:
        return JsonResponse({'status': 'error', 'message': 'Please log in or start a session.'})

    try:
        
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        if not item_id:
            return JsonResponse({'status': 'error', 'message': 'No item_id provided.'})

       
        cart = get_or_create_cart(request)
        
        
        print(f"Cart ID: {cart.id}, Item ID: {item_id}")

        
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        cart_item.delete()

        
        cart_items = cart.items.select_related('variant__product_id')
        subtotal = sum((Decimal(str(item.variant.price)) * Decimal('0.9')) * item.quantity for item in cart_items if item.variant.product_id)
        
        total = round(subtotal, 2)

        return JsonResponse({
            'status': 'success',
            'message': 'Item removed from cart',
            'subtotal': float(subtotal),
           
            'total': float(total)
        })
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found.'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'})
    except Exception as e:
        print(f"Error removing cart item: {e}")
        return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'})
    


from django.utils import timezone
from django.http import HttpResponseNotAllowed



@login_required
def add_to_wishlist(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'], 'Method not allowed. Use POST to add to wishlist.')
    
    product_id = request.POST.get('product_id')
    try:
        product = Product.objects.get(id=product_id)
        default_variant = product.variants.filter(stock__gt=0).order_by('size').first()
        if not default_variant:
            messages.error(request, 'No available variants for this product.')
            return redirect('product_list')

        cart = get_or_create_cart(request)
        cart_item = cart.items.filter(variant=default_variant).first()
        if cart_item:
            messages.info(request, 'This item is already in your cart.')
            return redirect('product_list')

        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'created_at': timezone.now()}
        )
        if created:
            messages.success(request, 'Added to wishlist.')
        else:
            messages.info(request, 'Item is already in your wishlist.')
        return redirect('wishlist')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('product_list')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('product_list')
@login_required
def wishlist(request):
    
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('product').prefetch_related('product__productimage_set', 'product__variants__images')
    cart = get_or_create_cart(request)
    cart_variant_ids = cart.items.values_list('variant_id', flat=True)

    filtered_wishlist_items = []
    for item in wishlist_items:
        default_variant = item.product.variants.filter(stock__gt=0).order_by('size').first()
        if default_variant and default_variant.id not in cart_variant_ids:
            
            main_image = default_variant.images.filter(is_main=True).first()
            if not main_image:
                
                main_image = item.product.productimage_set.filter(is_main=True).first()

            
            item_data = {
                'product': item.product,
                'default_variant_id': default_variant.id,
                'discounted_price': default_variant.price * Decimal('0.9'),
                'default_price': default_variant.price,
                'discount_percent': 10,
                'main_image': main_image,  
                'wishlist_item_id': item.id,  
                'created_at': item.created_at,  
            }
            filtered_wishlist_items.append(item_data)

    context = {'wishlist_items': filtered_wishlist_items}
    return render(request, 'wishlist.html', context)

@login_required
def remove_from_wishlist(request, item_id):
    try:
        wishlist_item = WishlistItem.objects.get(id=item_id, user=request.user)
        wishlist_item.delete()
        messages.success(request, 'Removed from wishlist.')
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found.')
    return redirect('wishlist')

@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('variant__product_id').prefetch_related('variant__images', 'variant__product_id__productimage_set')

    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    valid_items = []
    for item in cart_items:
        if item.quantity > item.variant.stock or item.variant.product_id.status != 'listed' or item.variant.product_id.category_id.status != 'Listed':
            item.delete()
            messages.warning(request, f'{item.variant.product_id.name} ({item.variant.size} ML) is unavailable and removed.')
        else:
            item.discounted_price = Decimal(str(item.variant.price)) * Decimal('0.9') 
            item.item_total = item.discounted_price * item.quantity 
            item.original_total = Decimal(str(item.variant.price)) * item.quantity 
            # Attach main image logic
            item.main_image = item.variant.images.filter(is_main=True).first()
            if not item.main_image:
                item.main_image = item.variant.product_id.productimage_set.filter(is_main=True).first()
            valid_items.append(item)

    if not valid_items:
        messages.error(request, 'Your cart is empty or contains unavailable items.')
        return redirect('cart')

    try:
        subtotal = sum(item.item_total for item in valid_items)
        total = round(subtotal, 2)  
    except Exception as e:
        print(f"Error calculating totals: {e}")
        messages.error(request, 'Error calculating cart totals.')
        return redirect('cart')

    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    context = {
        'cart_items': valid_items,
        'subtotal': subtotal,
        'total': total,
        'addresses': addresses,
        'default_address': default_address,
    }
    return render(request, 'checkout.html', context)
@login_required
def place_order(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('variant__product_id')

    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    valid_items = []
    for item in cart_items:
        if item.quantity <= item.variant.stock and item.variant.product_id.status == 'listed' and item.variant.product_id.category_id.status == 'Listed':
            item.discounted_price = Decimal(str(item.variant.price)) * Decimal('0.9')
            item.item_total = item.discounted_price * item.quantity
            valid_items.append(item)
        else:
            item.delete()
            messages.warning(request, f'{item.variant.product_id.name} ({item.variant.size} ML) is unavailable.')

    if not valid_items:
        messages.error(request, 'Your cart is empty or contains unavailable items.')
        return redirect('cart')

    try:
        subtotal = sum(item.item_total for item in valid_items)
        total = round(subtotal, 2)
        discount_amount = Decimal('0.00')  # Example; calculate based on coupon if applicable
    except Exception as e:
        print(f"Error calculating totals: {e}")
        messages.error(request, 'Error calculating order totals.')
        return redirect('cart')

    address_id = request.POST.get('address_id')
    payment_method = request.POST.get('payment_method', 'cod')
    if not address_id:
        messages.error(request, 'No shipping address selected. Please try again.')
        return redirect('checkout')
    if payment_method != 'cod':
        messages.error(request, 'Only Cash on Delivery is available.')
        return redirect('checkout')

    address = get_object_or_404(Address, id=address_id, user=request.user)
    shipping_address = f"{address.full_name}, {address.the_address}, {address.city}, {address.state}, {address.zip_code}, {address.country}, Phone: {address.mobile}"

    order = Order.objects.create(
        user=request.user,
        total=total,
        status='pending',
        shipping_address=shipping_address,
        discount_amount=discount_amount,
        payment_method=payment_method,
        payment_status='pending',
        delivery_date=None,  # Set dynamically if known
        cancelled_at=None
    )

    for item in valid_items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            price=item.discounted_price,
            total=item.item_total
        )
        item.variant.stock -= item.quantity
        item.variant.save()

    cart.items.all().delete()
    messages.success(request, f'Order {order.id} placed successfully!')
    return redirect('order_confirmation', order_id=order.id)


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('variant__product_id')
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'order_confirmation.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('variant__product_id')
    address = Address.objects.filter(user=request.user, is_default=True).first()
    
    # Attach main_image to each order item
    for item in order_items:
        item.main_image = item.variant.images.filter(is_main=True).first() or item.variant.product_id.productimage_set.filter(is_main=True).first()
    
    context = {
        'order': order,
        'order_items': order_items,
        'address': address,
        'stages': ['Processing', 'Packed', 'Shipped', 'Delivered', 'Return', 'Returned', 'Cancelled'],
        'current_stage': order.status if order.status in ['pending', 'processing', 'shipped', 'delivered'] else 'pending',
    }
    return render(request, 'order_detail.html', context)

@login_required
def orders(request):
    sort_order = request.GET.get('sort', 'newest')
    ordering = '-created_at' if sort_order == 'newest' else 'created_at'

    orders = Order.objects.filter(user=request.user).order_by(ordering).prefetch_related(
        'items__variant__images', 'items__variant__product_id__productimage_set'
    )

    order_list = []
    for order in orders:
        items = list(order.items.all())
        for item in items:
            item.main_image = (
                item.variant.images.filter(is_main=True).first() or 
                item.variant.product_id.productimage_set.filter(is_main=True).first()
            )
        order.first_item = items[0] if items else None
        order.items_with_images = items
        order_list.append(order)

    return render(request, 'orders.html', {
        'orders': order_list,
    })

from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse

@login_required
def generate_invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order).select_related('variant__product_id')
    address = Address.objects.filter(user=request.user, is_default=True).first()
    
    html_string = render_to_string('invoice.html', {
        'order': order,
        'order_items': order_items,
        'address': address,
    })
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
    HTML(string=html_string).write_pdf(response)
    
    return response