from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'button1': '',
        'button2': 'Расчет колеса',
        'button3': 'Построение характеристики рассчитанного насоса',
        'button4': 'Подбор насоса',
    }
    return render(request, 'home.html', context)


