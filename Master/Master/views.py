from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'button3': 'К расчету!',
    }
    return render(request, 'home.html', context)


def wheel_calc(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'button1': 'Получить размеры',
        'button2': 'Вернуться домой',
        'inputs': [
            {
                'placeholder': 'Расход, м3/ч',
                'type': 'number',
                'name': 'flow rate',
                'value': '',
            },
            {
                'placeholder': 'Напор, м',
                'type': 'number',
                'name': 'pressure',
                'value': '',
            },
            {
                'placeholder': 'Частота вр., об/мин',
                'type': 'number',
                'name': 'speed',
                'value': '',
            },
        ]
    }
    return render(request, 'wheel_calc.html', context)


def pump_selection(request):
    return HttpResponse('This is pump_selection page')
