from django.urls import path
from . import views

urlpatterns = [
    path('', views.t_pipes, name='t_pipes'),
]
