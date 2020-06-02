# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-10-16 09:12
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('permission', '0028_auto_20191009_1337'),
    ]

    operations = [
        migrations.CreateModel(
            name='InternalReport',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('type', models.SmallIntegerField(choices=[
                    (0, 'Active users'),
                    (1, 'User risk scores'),
                    (2, 'Quarter validation'),
                    (3, 'Goals')
                ])),
                ('status', models.SmallIntegerField(choices=[
                    (0, 'Generating'),
                    (1, 'Ready'),
                    (2, 'Failed')
                ])),
                ('generated', models.DateTimeField(
                    default=datetime.datetime.now
                )),
                ('input_data', models.TextField()),
                ('data', models.TextField(blank=True, null=True)),
                ('context', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='permission.AppContext',
                    verbose_name='Context'
                )),
            ],
        ),
    ]
