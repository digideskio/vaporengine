# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-12-05 15:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('visualizer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TermCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('corpus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='visualizer.Corpus')),
                ('terms', models.ManyToManyField(to='visualizer.Term')),
            ],
        ),
    ]