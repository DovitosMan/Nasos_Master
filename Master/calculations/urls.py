from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('wheel_calc/', views.wheel_calc, name='wheel_calc'),
]