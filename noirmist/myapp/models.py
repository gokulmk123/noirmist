from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    
    class Meta:
        ordering =['date_joined']



# Category Model
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=10,
        choices=[('Listed', 'Listed'), ('Unlisted', 'Unlisted')],
        default='Listed'
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# Brand Model
class Brand(models.Model):
    brand_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    logo = models.ImageField(upload_to='brand_logos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[('Listed', 'Listed'), ('Unlisted', 'Unlisted')],
        default='Listed')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    default_stock = models.IntegerField()
    image_url = models.CharField(max_length=500)
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand_id = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('listed', 'Listed'), ('unlisted', 'Unlisted')], default='listed')
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering =['created_at']
    @property
    def default_price(self):
        first_variant = self.variants.first()
        return first_variant.price if first_variant else None

    def __str__(self):
        return self.name

# Product Variant Model
class ProductVariant(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.IntegerField()
    stock = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.size}"


# Product Image Model
class ProductImage(models.Model):

    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=255)
    is_main = models.BooleanField(default=False)
    

    def __str__(self):
        return f"{self.product.name} - Image"

class banner(models.Model):

    banner_name =models.CharField(max_length=50)
    banner_img =models.ImageField(upload_to='banners/')
    start_date =models.DateField()
    end_date =models.DateField()
    description =models.TextField(blank=True, null=True)
    def __str__(self):
        return f"Banner ({self.start_date} to {self.end_date})"