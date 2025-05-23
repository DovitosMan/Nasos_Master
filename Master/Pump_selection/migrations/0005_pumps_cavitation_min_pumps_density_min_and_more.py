# Generated by Django 5.1.4 on 2025-05-14 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Pump_selection', '0004_pumps_density_pumps_gas_content_pumps_pump_lift_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pumps',
            name='cavitation_min',
            field=models.FloatField(default=0.5),
        ),
        migrations.AddField(
            model_name='pumps',
            name='density_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='pumps',
            name='feed_min',
            field=models.FloatField(default=10),
        ),
        migrations.AddField(
            model_name='pumps',
            name='gas_content_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='pumps',
            name='power_min',
            field=models.FloatField(default=1),
        ),
        migrations.AddField(
            model_name='pumps',
            name='pressure_min',
            field=models.FloatField(default=16),
        ),
        migrations.AddField(
            model_name='pumps',
            name='pump_lift_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='pumps',
            name='rotation_speed_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='pumps',
            name='solid_content_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='pumps',
            name='solid_size_min',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='pumps',
            name='viscosity_min',
            field=models.FloatField(default=0),
        ),
    ]
