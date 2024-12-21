from django.urls import path
from . import views

urlpatterns = [
    path('', views.pump_selection, name='pump_selection'),
    path('index/', views.pump_selection_index, name='pump_selection_index'),
]
