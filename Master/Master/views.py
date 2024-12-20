from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'button3': 'К расчету!',
    }
    return render(request, 'home.html', context)


def pump_selection(request):
    return HttpResponse('This is pump_selection page')

