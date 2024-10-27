# Generated by Django 5.0.1 on 2024-01-29 12:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0011_organization_group_alter_category_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="estimated_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="profile",
            name="uid",
            field=models.CharField(
                default="<function uuid4 at 0x102ef6200>", max_length=200
            ),
        ),
    ]
