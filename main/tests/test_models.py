from django.test import TestCase
from django.core.exceptions import ValidationError
import pytest
from main.models import Category
from django.contrib.auth import get_user_model
from main.models import Organization

User = get_user_model()


def create_test_user():
    return User.objects.create_user(username="testuser", password="password")


def create_test_organization(user):
    return Organization.objects.create(name="Test Organization", created_by=user)


class CategoryModelTest(TestCase):
    def setUp(self):
        self.created_by = create_test_user()
        self.organization = create_test_organization(self.created_by)

    def test_valid_opening_hours(self):
        """Test valid opening hours where all days have one time range or are empty."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "17:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],  # Ensure non-empty range
            },
            break_hours={},
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        try:
            category.clean()
        except ValidationError as e:
            self.fail(f"Validation failed unexpectedly: {e}")
            

    def test_valid_opening_hours_and_break_hours(self):
        """Test valid opening hours and break hours."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "17:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["12:00", "13:00"]],
                "Tuesday": [["15:00", "15:30"]],
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        try:
            category.clean()
        except ValidationError as e:
            self.fail(f"Validation failed unexpectedly: {e}")

    def test_invalid_break_hours(self):
        """Test valid opening hours and break hours."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "17:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["18:00", "20:00"]]
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Break hours (18:00 - 20:00) for Monday must be within opening hours (09:00 - 17:00).', str(cm.exception))

    def test_valid_opening_hours_and_break_hours_invalid_time(self):
        """Test invalid opening hours and break hours."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "25:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["10:00", "11:00"]]
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Invalid time format in opening hours for Monday', str(cm.exception))

    def test_valid_opening_hours_and_break_hours_invalid_opening_hours(self):
        """Test invalid opening hours and break hours."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["22:00", "09:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["10:00", "11:00"]]
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Opening hours for Monday must have a start time earlier than the end time.', str(cm.exception))

    def test_valid_opening_hours_and_break_hours_invalid_opening_hours_1(self):
        """Test invalid opening hours and break hours."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "ab:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["10:00", "11:00"]]
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Invalid time format in opening hours for Monday', str(cm.exception))

        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["10:00", "11:00"]]
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Invalid time format in opening hours for Monday', str(cm.exception))

        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": {1:["09:00"]},
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["10:00", "11:00"]]
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Opening hours for Monday must consist of exactly one time range.', str(cm.exception))

    def test_valid_opening_hours_and_break_hours_holiday(self):
        """Test if sunday was empty list (holoday)"""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "16:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [],
            },
            break_hours={},
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        category.clean()
        

    def test_missing_day_in_opening_hours(self):
        """Test that missing days in opening hours do not raise errors."""
        opening_hours = {
            "Monday": [["09:00", "17:00"]],
            "Tuesday": [["09:00", "17:00"]],
            # Missing Wednesday
            "Thursday": [["09:00", "17:00"]],
            "Friday": [["09:00", "17:00"]],
            "Saturday": [["10:00", "14:00"]],
            "Sunday": [["10:00", "14:00"]],
        }
        category = Category(
            name="Test Category",
            opening_hours=opening_hours,
            break_hours={},
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn("Missing opening hours for Wednesday.", str(cm.exception))

    def test_break_hours_equal_to_opening_hours(self):
        """Test that break hours equal to opening hours raise a validation error."""
        category = Category(
            name="Test Category",
            opening_hours={
                "Monday": [["09:00", "17:00"]],
                "Tuesday": [["09:00", "17:00"]],
                "Wednesday": [["09:00", "17:00"]],
                "Thursday": [["09:00", "17:00"]],
                "Friday": [["09:00", "17:00"]],
                "Saturday": [["10:00", "14:00"]],
                "Sunday": [["10:00", "14:00"]],
            },
            break_hours={
                "Monday": [["09:00", "17:00"]],  # Exactly matches opening hours
            },
            organization=self.organization,
            created_by=self.created_by,
            is_scheduled=True
        )
        with self.assertRaises(ValidationError) as cm:
            category.clean()
        self.assertIn('Break hours (09:00 - 17:00) for Monday cannot fully overlap with opening hours.', str(cm.exception))

