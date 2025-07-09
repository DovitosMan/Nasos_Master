from django.urls import path
from . import views

urlpatterns = [
    path('', views.twin_screw, name='twinscrew'),
]
