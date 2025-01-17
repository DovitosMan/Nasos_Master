from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'buttons': [
            {
                'value': 'Расчет колеса',
                'url_name': "wheel_calc",
            },
            {
                'value': 'Расчет подвода',
                'url_name': "home",
            },
            {
                'value': 'Расчет отвода',
                'url_name': "home",
            },
            {
                'value': 'Построение характеристики',
                'url_name': "characteristics",
            },
            {
                'value': 'Подбор насоса',
                'url_name': "pump_selection",
            },
            {
                'value': 'Расчет энергозатрат',
                'url_name': "home",
            },
            {
                'value': 'Расчет трудозатрат',
                'url_name': "home",
            },
            {
                'value': 'Личный кабинет',
                'url_name': "home",
            },
        ],
    }
    return render(request, 'home.html', context)


