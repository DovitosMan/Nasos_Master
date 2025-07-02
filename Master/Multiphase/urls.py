from django.urls import path
from . import views

urlpatterns = [
    path('', views.multiphase, name='multiphase'),
]
