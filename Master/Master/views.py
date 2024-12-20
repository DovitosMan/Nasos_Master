from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'button3': 'К расчету!',
    }
    return render(request, 'home.html', context)


