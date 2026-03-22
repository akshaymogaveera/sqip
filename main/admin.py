from django.contrib import admin
import base64

# Register your models here.
from .models import Organization, Appointment, Category, SubCategory, AppointmentMapToSubCategory, Profile


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Custom admin for Organization: auto-converts uploaded display_picture to a base64 data-URL
    stored in display_picture_base64, so images live in the DB instead of the filesystem."""

    def save_model(self, request, obj, form, change):
        # If a new image file was uploaded, convert it to base64 and clear the file-based field
        if 'display_picture' in form.changed_data and obj.display_picture:
            img_file = obj.display_picture
            try:
                img_file.seek(0)
                raw = img_file.read()
                mime = getattr(img_file, 'content_type', 'image/jpeg') or 'image/jpeg'
                b64 = base64.b64encode(raw).decode('utf-8')
                obj.display_picture_base64 = f"data:{mime};base64,{b64}"
                # Clear the file-based field so nothing is written to disk
                obj.display_picture = None
            except Exception:
                pass  # keep whatever was there if conversion fails
        super().save_model(request, obj, form, change)


admin.site.register(Appointment)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(AppointmentMapToSubCategory)
admin.site.register(Profile)
