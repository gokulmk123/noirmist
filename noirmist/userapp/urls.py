from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('',views.user_signup,name='user_signup'),
    path('otp_verify/',views.otp_verify,name='otp_verify'),
    path('user_login/',views.user_login,name='user_login'),
    path('user_logout/', views.user_logout, name='user_logout'),
    path('home/',views.home,name='home'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('product_list/',views.product_list,name='product_list'),
    path('base/',views.base,name='base'),
    
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/',views.cart,name='cart'),
    path('profile/',views.profile,name='profile'),



]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)