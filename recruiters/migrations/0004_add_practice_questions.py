from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recruiters', '0003_add_interview_questions'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='practice_questions',
            field=models.JSONField(
                default=list,
                blank=True,
                help_text='LLM-generated practice questions for the candidate to prepare with',
            ),
        ),
    ]
