from datetime import timedelta
from django.core.exceptions import ValidationError
from datetime import datetime
import pytz
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict

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

    def save(self, *args, **kwargs):
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
        return model_to_dict(self)

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
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=100, null=True, blank=True)
    uid = models.CharField(default=f"{uuid.uuid4}", max_length=200)
