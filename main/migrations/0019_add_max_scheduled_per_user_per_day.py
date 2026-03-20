from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0018_alter_profile_uid"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="max_scheduled_per_user_per_day",
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text="Maximum number of scheduled appointments a single user may create per calendar day. Null means unlimited.",
            ),
        ),
    ]
