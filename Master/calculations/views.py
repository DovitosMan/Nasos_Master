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
        'outer_diam_of_work_wheel': None,
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

        def pump_speed_coef(flow_rate, pressure, speed):
            return round((3.65 * speed * math.sqrt(flow_rate/60/60)) / (pressure ** (3 / 4)))

        def outer_diam_of_work_wheel(flow_rate, speed):
            Kww = 9.35 * math.sqrt(100 / context['pump_speed_coef'])
            return round(( Kww * (flow_rate /60/60/ speed) ** (1 / 3)),4)

        # Результат вычисления
        context['pump_speed_coef'] = pump_speed_coef(flow_rate, pressure, speed)
        context['outer_diam_of_work_wheel'] = outer_diam_of_work_wheel(flow_rate, speed)
    return render(request, 'calculations.html', context)
