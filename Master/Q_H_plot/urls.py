from django.urls import path
from . import views

urlpatterns = [
    path('', views.q_h_plot, name='characteristics'),
]