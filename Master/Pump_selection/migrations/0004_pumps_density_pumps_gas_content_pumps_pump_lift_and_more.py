# Generated by Django 5.1.4 on 2025-05-14 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Pump_selection', '0003_pumps_a0_pumps_b0_pumps_c0'),
    ]

    operations = [
        migrations.AddField(
            model_name='pumps',
            name='density',
            field=models.FloatField(default=1030),
        ),
        migrations.AddField(
            model_name='pumps',
            name='gas_content',
            field=models.FloatField(default=5),
        ),
        migrations.AddField(
            model_name='pumps',
            name='pump_lift',
            field=models.FloatField(default=7),
        ),
        migrations.AddField(
            model_name='pumps',
            name='solid_content',
            field=models.FloatField(default=0.1),
        ),
        migrations.AddField(
            model_name='pumps',
            name='solid_size',
            field=models.FloatField(default=0.2),
        ),
        migrations.AddField(
            model_name='pumps',
            name='viscosity',
            field=models.FloatField(default=1.4),
        ),
    ]
