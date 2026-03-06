from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='raw_password',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Plain-text password for test environment only. Never use in production.',
                max_length=128,
            ),
        ),
    ]
