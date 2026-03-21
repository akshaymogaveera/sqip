from phonenumber_field.modelfields import PhoneNumberField
from datetime import timedelta
from django.core.exceptions import ValidationError
from datetime import datetime
import pytz
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import Group
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
import phonenumbers

# Create your models here.

User = get_user_model()


class Organization(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        # Add other choices as needed
    ]

    TYPE = [
        ("restaurant", "Restaurant"),
        ("clinic", "Clinic"),
        ("doctor", "Doctor"),
        ("company", "Company"),
        ("store", "Store"),
        ("home", "Home"),
        ("bank", "Bank"),
        ("ATM", "ATM"),
        ("school", "School"),
        ("factory", "Factory"),
        ("others", "Others"),
        # Add other choices as needed
    ]
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    portfolio_site = models.URLField(blank=True)
    display_picture = models.ImageField(upload_to="display_picture", blank=True)
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20)
    type = models.CharField(max_length=20, choices=TYPE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    groups = models.ManyToManyField(Group, related_name="organizations")
    # Optional limits enforced for org-admins (null/blank => unlimited)
    max_categories = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of categories allowed for this organization. Null means unlimited."
    )
    max_config_users = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of config/admin users allowed for this organization. Null means unlimited."
    )


class Category(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        # Add other choices as needed
    ]
    CHOICES = [
        ("general", "General"),
        ("inperson", "In Person"),
        ("drive-thru", "Drive-thru"),
        ("online", "Online")
        # Add other choices as needed
    ]
    group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        related_name="categories",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    type = models.CharField(max_length=20, choices=CHOICES, blank=True)
    estimated_time = models.DateTimeField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, default=timezone.now)
    is_scheduled = models.BooleanField(default=False)
    time_zone = models.CharField(
        max_length=50, 
        choices=[(tz, tz) for tz in pytz.all_timezones], 
        default="UTC"
    )
    opening_hours = models.JSONField(
        blank=True,
        default=dict  # Empty dictionary as default (you can modify to something more specific if needed)
    )   # e.g., {"Monday": [["09:00", "17:00"]]}
    break_hours = models.JSONField(
        default=dict, blank=True  # Empty dictionary as default (modify as needed)
    )    # e.g., {"Monday": [["12:00", "13:00"]]}
    time_interval_per_appointment = models.DurationField(
        default=timedelta(minutes=30)  # Default to 30 minutes for each appointment
    )
    max_advance_days = models.PositiveIntegerField(
        default=7,  # Default to one week ahead
        help_text="Maximum number of days in the future an appointment can be scheduled.",
        blank=True
    )
    # Maximum number of scheduled appointments a single user may have per calendar day
    # Null/blank means unlimited
    max_scheduled_per_user_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of scheduled appointments a single user may create per calendar day. Null means unlimited."
    )

    def save(self, *args, **kwargs):
        # Enforce organization-level max_categories if set
        if self.organization and hasattr(self.organization, 'max_categories') and self.organization.max_categories is not None:
            # When creating (no id yet) count existing categories
            existing_count = Category.objects.filter(organization=self.organization).count()
            creating = self._state.adding
            if creating and existing_count >= self.organization.max_categories:
                raise ValidationError(f"Organization has reached its max_categories limit ({self.organization.max_categories}).")

        # Ensure a Group exists for this Category following the 1:1 convention.
        if not self.group:
            # Derive a unique group name using org id and slugified category name
            base = f"org-{self.organization.id}-{slugify(self.name or 'category')}"
            # Ensure uniqueness by appending suffix if needed
            group_name = base
            suffix = 0
            while Group.objects.filter(name=group_name).exists():
                suffix += 1
                group_name = f"{base}-{suffix}"
            grp = Group.objects.create(name=group_name)
            self.group = grp
            # Ensure the newly created Group is associated with the Organization's groups
            try:
                if self.organization:
                    # organization.groups is a ManyToManyField
                    self.organization.groups.add(grp)
            except Exception:
                # If anything goes wrong here, don't prevent saving the Category;
                # the association is best-effort and can be fixed later.
                pass

        self.full_clean()  # Validates the data before saving
        super().save(*args, **kwargs)
            

    def _validate_opening_and_break_hours(self):
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Ensure all days are present in opening_hours
        for day in days_of_week:
            if day not in self.opening_hours:
                raise ValidationError(f"Missing opening hours for {day}.")

        # Validate opening_hours and break_hours structure
        for day, opening_ranges in self.opening_hours.items():

            if isinstance(opening_ranges, list) and len(opening_ranges) == 0:
                continue

            if not isinstance(opening_ranges, list) or len(opening_ranges) != 1:
                raise ValidationError(f"Opening hours for {day} must consist of exactly one time range.")

            try:
                start, end = opening_ranges[0]
                if not isinstance(start, str) or not isinstance(end, str):
                    raise ValidationError(f"Opening hours for {day} must be strings in 'HH:MM' format.")
                start_time = datetime.strptime(start, "%H:%M").time()
                end_time = datetime.strptime(end, "%H:%M").time()
            except ValueError:
                raise ValidationError(f"Invalid time format in opening hours for {day}")

            if start_time >= end_time:
                raise ValidationError(f"Opening hours for {day} must have a start time earlier than the end time.")

            # Validate break_hours (if provided)
            break_ranges = self.break_hours.get(day, [])
            for break_start, break_end in break_ranges:
                if not isinstance(break_start, str) or not isinstance(break_end, str):
                    raise ValidationError(f"Break hours for {day} must be strings in 'HH:MM' format.")

                try:
                    break_start_time = datetime.strptime(break_start, "%H:%M").time()
                    break_end_time = datetime.strptime(break_end, "%H:%M").time()
                except ValueError:
                    raise ValidationError(f"Invalid time format in break hours for {day}: {break_start} - {break_end}")

                if break_start_time >= break_end_time:
                    raise ValidationError(f"Break hours for {day} must have a start time earlier than the end time.")

                if not (start_time <= break_start_time < end_time and start_time < break_end_time <= end_time):
                    raise ValidationError(
                        f"Break hours ({break_start} - {break_end}) for {day} must be within opening hours ({start} - {end})."
                    )

                if break_start_time == start_time and break_end_time == end_time:
                    raise ValidationError(
                        f"Break hours ({break_start} - {break_end}) for {day} cannot fully overlap with opening hours."
                    )



    def clean(self):

        if self.is_scheduled:
            # Validate time zone
            if self.time_zone not in pytz.all_timezones:
                raise ValidationError(f"Invalid time zone: {self.time_zone}")

            # Validate opening and break hours
            self._validate_opening_and_break_hours()

            # Ensure the interval is a valid positive duration
            if self.time_interval_per_appointment <= timedelta(0):
                raise ValidationError("Appointment interval must be a positive duration.")

        super().clean()  # Call parent clean() to apply any other necessary validation.

        


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("checkin", "CheckIn"),
        ("checkout", "CheckOut"),
        ("cancel", "Cancelled"),
        # Add other choices as needed
    ]
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    type = models.CharField(max_length=20, blank=True)
    counter = models.IntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0]
    )
    date_created = models.DateTimeField(auto_now_add=True)
    is_scheduled = models.BooleanField(default=False)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    scheduled_end_time = models.DateTimeField(null=True, blank=True)
    estimated_time = models.DateTimeField(null=True, blank=True)
    checkout_time = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_appointments",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_appointments",
    )

    def as_dict(self) -> dict:
        """
        Converts the Appointment instance to a dictionary representation, 
        including all fields in the model.
        
        Returns:
            dict: Dictionary representation of the Appointment instance.
        """
        data = model_to_dict(self)

        # recursively convert any phonenumbers.PhoneNumber objects to strings
        def _convert(obj):
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(v) for v in obj]
            try:
                if isinstance(obj, phonenumbers.phonenumber.PhoneNumber):
                    return str(obj)
            except Exception:
                pass
            return obj

        return _convert(data)

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    item = models.CharField(max_length=20)
    status = models.CharField(max_length=20, blank=True)


class AppointmentMapToSubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    # Phone is the primary identifier for regular users; must be unique across all profiles.
    # Admins / staff may leave it blank.
    phone_number = PhoneNumberField(blank=True, null=True, unique=True)
    otp = models.CharField(max_length=100, null=True, blank=True)
    uid = models.CharField(default=f"{uuid.uuid4}", max_length=200)
    # Whether this user is an organization-level admin (can manage categories/users for organizations in org_access)
    is_org_admin = models.BooleanField(default=False)
    # Organizations this profile has admin access to (empty => none)
    org_access = models.ManyToManyField('Organization', blank=True, related_name='access_profiles')

    def clean(self):
        super().clean()
        # Regular users (not staff, not superuser, no groups) must have a phone number.
        if not self.user.is_staff and not self.user.is_superuser and self.user.groups.count() == 0:
            if not self.phone_number:
                raise ValidationError("Phone number is required for regular users.")
