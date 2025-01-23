from django.shortcuts import render
from django.http import HttpResponse
import math


def wheel_calc(request):
    context = {
        'button': [
            'Pump Master',
            'Получить размеры'
        ],
        'calculations': [
            {
                'name': 'Коэффициент быстроходности насоса: ',
                'value': None,
                'round': 0,
                'unit': '',
            },
            {
                'name': 'Наружный диаметр рабочего колеса: ',
                'value': None,
                'round': 4,
                'unit': ' мм',
            },
            {
                'name': 'Ширина лопастного канала рабочего колеса на входе: ',
                'value': None,
                'round': 4,
                'unit': ' мм',
            },
            {
                'name': 'Приведенный диаметр входа в рабочее колесо 1: ',
                'value': None,
                'round': 4,
                'unit': ' мм',
            },
            {
                'name': 'Приведенный диаметр входа в рабочее колесо 2: ',
                'value': None,
                'round': 4,
                'unit': ' мм',
            },
            {
                'name': 'Объемный КПД: ',
                'value': None,
                'round': 3,
                'unit': ' %',
            },
            {
                'name': 'Гидравлический КПД: ',
                'value': None,
                'round': 3,
                'unit': ' %',
            },
            {
                'name': 'Внутр. мех. КПД: ',
                'value': None,
                'round': 3,
                'unit': ' %',
            },
            {
                'name': 'Полный ожидаемый КПД: ',
                'value': None,
                'round': 3,
                'unit': ' %',
            },
            {
                'name': 'Мощность: ',
                'value': None,
                'round': 0,
                'unit': ' кВт',
            },
            {
                'name': 'Мощность максимальная: ',
                'value': None,
                'round': 0,
                'unit': ' кВт',
            },
            {
                'name': 'Диаметр вала: ',
                'value': None,
                'round': 0,
                'unit': ' мм',
            },
            {
                'name': 'Диаметр входа в рабочее колесо: ',
                'value': None,
                'round': 0,
                'unit': ' мм',
            },
        ],
        'selects': [
            {
                'type': 'option',
                'placeholder': 'Расчет рабочего колеса:',
                'keys': [
                    'Центробежный насос', 'Струйный насос'
                ],
            },
            {
                'placeholder': 'Расход, м3/ч',
                'type': 'input',
                'name': 'flow_rate',
                'value': '',
            },
            {
                'placeholder': 'Напор, м',
                'type': 'input',
                'name': 'pressure',
                'value': '',
            },
            {
                'placeholder': 'Плотность, кг/м3',
                'type': 'input',
                'name': 'density',
                'value': '',
            },
            {
                'placeholder': 'Частота вр., об/мин',
                'type': 'input',
                'name': 'speed',
                'value': '',
            },
        ],
    }
    if request.method == "POST":
        # Получаем данные из формы
        flow_rate = float(request.POST.get("flow_rate", 0))
        pressure = float(request.POST.get("pressure", 0))
        density = float(request.POST.get("density", 0))
        speed = float(request.POST.get("speed", 0))

        calculated_values = calculations(flow_rate, pressure, density, speed)  # Получаем расчёты
        update_context(context, calculated_values)  # Обновляем context
        format_context_list(context)  # форматирование текста

    return render(request, 'calculations.html', context)


def calculations(flow_rate, pressure, density, speed):
    # Коэффициент быстроходности насоса
    pump_speed_coef = round((3.65 * speed * math.sqrt(flow_rate / 60 / 60)) / (pressure ** (3 / 4)))
    # Наружный диаметр рабочего колеса
    k_od = 9.35 * math.sqrt(100 / pump_speed_coef)
    outer_diam_of_work_wheel = round((k_od * (flow_rate / 3600 / speed) ** (1 / 3)), 4)
    # Ширина лопастного канала рабочего колеса на входе
    if pump_speed_coef <= 200:
        k_w = 0.8 * math.sqrt(pump_speed_coef / 100)
    else:
        k_w = 0.635 * (pump_speed_coef / 100) ** (5 / 6)
    width_in_enter_of_work_wheel = round(k_w * (flow_rate / 3600 / speed) ** (1 / 3), 4)
    # Приведенный диаметр входа в рабочее колесо
    k_in = 4.5
    inner_diam_of_work_wheel_1 = round(k_in * (flow_rate / 60 / speed) ** (2 / 3), 4)
    number_of_blade = 7
    alpha = 0.1
    v_0 = alpha * (flow_rate / 3600 * speed ** 2) ** (1 / 3)
    inner_diam_of_work_wheel_2 = round((4 * flow_rate / 3600 / (math.pi * v_0)) ** (1 / 2), 4)
    # Предварительная оценка КПД
    n_0 = (1 + (0.68 / (pump_speed_coef ** (2 / 3)))) ** (-1) * 100
    if inner_diam_of_work_wheel_1 < inner_diam_of_work_wheel_2:
        n_r = (1 - (0.42 / (math.log10(inner_diam_of_work_wheel_1 * 1000) - 0.172) ** 2)) * 100
    else:
        n_r = (1 - (0.42 / (math.log10(inner_diam_of_work_wheel_2 * 1000) - 0.172) ** 2)) * 100
    n_m = (1 + (28.6 / pump_speed_coef) ** 2) ** (-1) * 100
    n_a = n_0 / 100 * n_r / 100 * n_m / 100 * 100
    # Максимальная мощность насоса
    power = density * 9.81 * pressure * flow_rate / 60 / 60 / (n_a / 100) / 1000
    k_n = 1.1
    power_max = power * k_n
    # Определение размеров вала и втулки (ступицы) колеса
    m_max = round(power_max * 30 * 1000 / (math.pi * speed), 3)
    tau = 600 * 10 ** 5
    shaft_diameter = math.ceil(((m_max / (0.2 * tau)) ** (1 / 3) * 1000) / 10) * 10
    # Определение диаметра входной рабочего колеса и диаметра входа в рабочее колесо
    k_inner = 1.3115
    k_inner_0 = 1
    if inner_diam_of_work_wheel_1 < inner_diam_of_work_wheel_2:
        enter_diameter = round(((inner_diam_of_work_wheel_1 * 1000) ** 2 + (shaft_diameter * k_inner) ** 2) ** 0.5, 4)
    else:
        enter_diameter = round(((inner_diam_of_work_wheel_2 * 1000) ** 2 + (shaft_diameter * k_inner) ** 2) ** 0.5, 4)
    enter_diameter_0 = enter_diameter * k_inner_0

    return pump_speed_coef, outer_diam_of_work_wheel, width_in_enter_of_work_wheel, inner_diam_of_work_wheel_1, inner_diam_of_work_wheel_2, n_0, n_r, n_m, n_a, power, power_max, shaft_diameter, enter_diameter


def update_context(context, values):
    for calculation, value in zip(context['calculations'], values):
        calculation['value'] = value


def format_context_list(data_list):
    for item in data_list['calculations']:
        if item['value'] is not None:
            if item['value'] < 1:
                item['value'] = round(item['value'], item['round'])
            else:
                item['value'] = int(item['value'])

    return data_list
