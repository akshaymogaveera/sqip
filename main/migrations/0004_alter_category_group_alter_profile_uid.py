# Generated by Django 5.1.2 on 2024-10-28 00:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("main", "0003_alter_profile_uid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="group",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categories",
                to="auth.group",
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="uid",
            field=models.CharField(
                default="<function uuid4 at 0x10f792480>", max_length=200
            ),
        ),
    ]