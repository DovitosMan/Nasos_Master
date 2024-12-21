from django.db import models


class PumpFamily(models.Model):
    objects = None
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'Семейство: {self.name}'


class Pumps(models.Model):
    objects = None
    image = models.ImageField(upload_to='pumps images')
    name = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    family = models.ForeignKey(PumpFamily, on_delete=models.PROTECT)
    feed = models.FloatField()
    pressure = models.FloatField()
    cavitation = models.FloatField()
    rotation_speed = models.PositiveIntegerField()
    power = models.FloatField()
    mass = models.FloatField()
    mass_all = models.FloatField()
    a0 = models.FloatField()
    b0 = models.FloatField()
    c0 = models.FloatField()

    def __str__(self):
        return f'Насос: {self.name} | Семейство: {self.family.name}'


