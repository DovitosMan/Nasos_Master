from django.contrib import admin

from Pump_selection.models import PumpFamily, Pumps


class PumpFamilyAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


class PumpAdmin(admin.ModelAdmin):
    list_display = ('image', 'name', 'description', 'price',
                    'quantity', 'family', 'feed', 'pressure',
                    'cavitation', 'rotation_speed', 'power',
                    'mass', 'mass_all', 'a0', 'b0', 'c0')


admin.site.register(Pumps, PumpAdmin)
admin.site.register(PumpFamily, PumpFamilyAdmin)
