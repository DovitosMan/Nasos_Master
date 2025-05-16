from django.contrib import admin

from Pump_selection.models import PumpFamily, Pumps


class PumpFamilyAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


class PumpAdmin(admin.ModelAdmin):
    list_display = ('image', 'name', 'description', 'price',
                    'quantity', 'family', 'feed', 'feed_min', 'pressure', 'pressure_min', 'pump_lift',
                    'pump_lift_min', 'cavitation', 'cavitation_min', 'rotation_speed', 'rotation_speed_min',
                    'power', 'power_min', 'gas_content', 'gas_content_min', 'solid_content',
                    'solid_content_min', 'solid_size', 'solid_size_min', 'density', 'density_min',
                    'viscosity', 'viscosity_min', 'mass', 'mass_all', 'a0', 'b0', 'c0')


admin.site.register(Pumps, PumpAdmin)
admin.site.register(PumpFamily, PumpFamilyAdmin)
