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
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    path('update_profile_image/',views.update_profile_image,name='update_profile_image'),

    path('address/', views.address_list_view, name='address'),
    path('set-default-address/<int:address_id>/', views.set_default_address, name='set_default_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),

    path('edit_email/',views.edit_email,name='edit_email'),
    path('set-password/', views.set_password, name='set_password'),
    
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('remove-cart-item/', views.remove_cart_item, name='remove_cart_item'),

    
    path('add_to_wishlist/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('remove_from_wishlist/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)