import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()

class Organization(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        # Add other choices as needed
    ]

    TYPE = [
        ('restaurant', 'Restaurant'),
        ('clinic', 'Clinic'),
        ('doctor', 'Doctor'),
        ('company', 'Company'),
        ('store', 'Store'),
        ('home', 'Home'),
        ('bank', 'Bank'),
        ('ATM', 'ATM'),
        ('school', 'School'),
        ('factory', 'Factory'),
        ('others', 'Others'),
        # Add other choices as needed
    ]
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    portfolio_site = models.URLField(blank=True)
    display_picture = models.ImageField(upload_to='display_picture', blank=True)
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20)
    type = models.CharField(max_length=20, choices=TYPE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    group = models.ForeignKey(Group, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

class Category(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        # Add other choices as needed
    ]
    CHOICES = [
        ('general', 'General'),
        ('inperson', 'In Person'),
        # Add other choices as needed
    ]
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    type = models.CharField(max_length=20, choices=CHOICES)
    estimated_time = models.DateTimeField(null=True, blank=True)

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('checkin', 'CheckIn'),
        ('cancel', 'Cancelled')
        # Add other choices as needed
    ]
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    type = models.CharField(max_length=20, blank=True)
    counter = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    date_created = models.DateTimeField(auto_now_add=True)
    is_scheduled = models.BooleanField(default=False)
    estimated_time = models.DateTimeField(null=True, blank=True)

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    item = models.CharField(max_length=20)
    status = models.CharField(max_length=20, blank=True)

class AppointmentMapToSubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT)

class Profile(models.Model):
    user=models.OneToOneField(User,   on_delete=models.CASCADE,related_name="profile")
    phone_number=models.CharField(max_length=15)
    otp=models.CharField(max_length=100,null=True,blank=True)
    uid=models.CharField(default=f'{uuid.uuid4}',max_length=200)