# Generated by Django 5.1.2 on 2024-10-26 19:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0013_rename_scheduled_appointment_is_scheduled_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="counter",
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                    ("checkin", "CheckIn"),
                    ("cancel", "Cancelled"),
                ],
                default=("active", "Active"),
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="uid",
            field=models.CharField(
                default="<function uuid4 at 0x10b096840>", max_length=200
            ),
        ),
    ]
