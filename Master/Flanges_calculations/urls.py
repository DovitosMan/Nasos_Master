from django.urls import path
from . import views

urlpatterns = [
    path('', views.flanges_calculations, name='flanges'),
]
