from django.db import models


class PumpFamily(models.Model):
    objects = None
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class Pumps(models.Model):
    objects = None
    image = models.ImageField(upload_to='pumps images')
    name = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    family = models.ForeignKey(PumpFamily, on_delete=models.PROTECT)
    feed = models.FloatField()
    feed_min = models.FloatField(default=10)
    pressure = models.FloatField()
    pressure_min = models.FloatField(default=16)
    pump_lift = models.FloatField(default=7)
    pump_lift_min = models.FloatField(default=0)
    cavitation = models.FloatField()
    cavitation_min = models.FloatField(default=0.5)
    rotation_speed = models.PositiveIntegerField()
    rotation_speed_min = models.FloatField(default=0)
    power = models.FloatField()
    power_min = models.FloatField(default=1)
    gas_content = models.FloatField(default=5)
    gas_content_min = models.FloatField(default=0)
    solid_content = models.FloatField(default=0.1)
    solid_content_min = models.FloatField(default=0)
    solid_size = models.FloatField(default=0.2)
    solid_size_min = models.FloatField(default=0)
    density = models.FloatField(default=1030)
    density_min = models.FloatField(default=0)
    viscosity = models.FloatField(default=1.4)
    viscosity_min = models.FloatField(default=0)
    mass = models.FloatField()
    mass_all = models.FloatField()
    a0 = models.FloatField()
    b0 = models.FloatField()
    c0 = models.FloatField()

    def __str__(self):
        return f'Насос: {self.name} | Семейство: {self.family.name}'


