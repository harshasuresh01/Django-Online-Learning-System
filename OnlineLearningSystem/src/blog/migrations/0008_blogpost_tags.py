# Generated by Django 4.2.5 on 2024-02-20 05:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0007_remove_choice_question_remove_question_quiz_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='tags',
            field=models.TextField(blank=True, null=True),
        ),
    ]