from django.urls import path
from . import views

urlpatterns = [
    path('', views.characteristics, name='characteristics'),
]