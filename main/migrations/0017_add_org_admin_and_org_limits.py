from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_alter_profile_phone_number_alter_profile_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='max_categories',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum number of categories allowed for this organization. Null means unlimited.', null=True),
        ),
        migrations.AddField(
            model_name='organization',
            name='max_config_users',
            field=models.PositiveIntegerField(blank=True, help_text='Maximum number of config/admin users allowed for this organization. Null means unlimited.', null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_org_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='org_access',
            field=models.ManyToManyField(blank=True, related_name='access_profiles', to='main.Organization'),
        ),
    ]
