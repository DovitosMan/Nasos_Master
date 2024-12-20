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
        'calculations': [
            {
                'name': 'Коэффициент быстроходности насоса: ',
                'value': None,
            },
            {
                'name': 'Наружный диаметр рабочего колеса: ',
                'value': None,
            },
            {
                'name': 'Ширина лопастного канала рабочего колеса на входе: ',
                'value': None,
            },
            {
                'name': 'Приведенный диаметр входа в рабочее колесо 1: ',
                'value': None,
            },
            {
                'name': 'Приведенный диаметр входа в рабочее колесо 2: ',
                'value': None,
            },
        ],
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

        calculated_values = calculations(flow_rate, pressure, speed)  # Получаем расчёты
        update_context(context, calculated_values)  # Обновляем context

    return render(request, 'calculations.html', context)


def calculations(flow_rate, pressure, speed):
    # Коэффициент быстроходности насоса
    pump_speed_coef = round((3.65 * speed * math.sqrt(flow_rate / 60 / 60)) / (pressure ** (3 / 4)))
    # Наружный диаметр рабочего колеса
    kod = 9.35 * math.sqrt(100 / pump_speed_coef)
    outer_diam_of_work_wheel = round((kod * (flow_rate / 3600 / speed) ** (1 / 3)), 4)
    # Ширина лопастного канала рабочего колеса на входе
    if pump_speed_coef <= 200:
        kw = 0.8 * math.sqrt(pump_speed_coef / 100)
    else:
        kw = 0.635 * (pump_speed_coef / 100) ** (5 / 6)
    width_in_enter_of_work_wheel = round(kw * (flow_rate / 3600 / speed) ** (1 / 3),4)
    # Приведенный диаметр входа в рабочее колесо
    kin = 4.5
    inner_diam_of_work_wheel_1 = round(kin*(flow_rate/60/speed)**(2/3),4)
    z = 7
    alpha = 0.1
    v0 = alpha*(flow_rate/3600*speed**2)**(1/3)
    inner_diam_of_work_wheel_2 = round((4*flow_rate/3600/(math.pi*v0))**(1/2),4)
    #
    return pump_speed_coef, outer_diam_of_work_wheel, width_in_enter_of_work_wheel,inner_diam_of_work_wheel_1, inner_diam_of_work_wheel_2


def update_context(context, values):
    for calculation, value in zip(context['calculations'], values):
        calculation['value'] = value
