from django.shortcuts import render
from django.http import HttpResponse
import math


def index(request):
    return render(request, 'calculations.html')


def wheel_calc(request):
    context = {
        'title': 'Расчет рабочего колеса',
        'button1': 'Получить размеры',
        'button2': 'Вернуться домой',
        'pump_speed_coef': None,
        'inputs': [
            {
                'placeholder': 'Расход, м3/ч',
                'type': 'number',
                'name': 'flow_rate',
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
        ],

    }
    if request.method == "POST":
        # Получаем данные из формы
        flow_rate = float(request.POST.get("flow_rate", 0))
        pressure = float(request.POST.get("pressure", 0))
        speed = float(request.POST.get("speed", 0))

        def two_side(a, b, c):
            return (3.65 * c * math.sqrt(a / 2)) / (b ** (3 / 4))

        def pump_speed_coef(a, b, c):
            return round((3.65 * c * math.sqrt(a)) / (b ** (3 / 4)))

        # Результат вычисления
        context['pump_speed_coef'] = pump_speed_coef(flow_rate, pressure, speed)
    return render(request, 'calculations.html', context)

