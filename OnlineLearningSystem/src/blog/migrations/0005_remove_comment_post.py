# Generated by Django 4.2.5 on 2023-10-04 02:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0004_alter_comment_post'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comment',
            name='post',
        ),
    ]
