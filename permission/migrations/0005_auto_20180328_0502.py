# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-03-28 05:02
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('permission', '0004_auto_20180328_0459'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='permissionuser', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
    ]
