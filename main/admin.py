from django.contrib import admin

# Register your models here.
from .models import Organization, Appointment, Category, SubCategory, AppointmentMapToSubCategory

admin.site.register(Organization)
admin.site.register(Appointment)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(AppointmentMapToSubCategory)