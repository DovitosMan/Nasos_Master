from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name="home"),
    path('pump_selection/', include('Pump_selection.urls')),
    path('calculations/', include('calculations.urls')),
    path('characteristics/', include('characteristics.urls')),
    path('screw/', include('Screw.urls')),
    path('multiphase/', include('Multiphase.urls')),
    path('twinscrew/', include('TwinScrew.urls')),
    path('flanges_calculations/', include('Flanges_calculations.urls')),
    path('t_pipes/', include('T_pipes.urls')),
]
