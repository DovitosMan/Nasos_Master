from django.urls import path
from . import views
from .views import index

urlpatterns = [
    path('', index),
    path('wheel_calc/', views.wheel_calc, name='wheel_calc'),
]