from django.urls import path
from . import views

urlpatterns = [
    path('', views.wheel_calc, name='wheel_calc'),
]