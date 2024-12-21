from django.shortcuts import render
import math
from .models import Pumps, PumpFamily
import matplotlib.pyplot as plt
import io
import urllib, base64


def pump_selection(request):
    selects1 = ['Назначение системы', 'Семейство насосов']
    selects2 = ['ХВС', 'СВ', 'СО', 'Подпитка', 'ГВС']
    selects3 = ['Любой', 'Астрахань', 'Барнаул', 'Белгород', 'Бийск',
                'Владивосток', 'Волгоград', 'Вологда', 'Воронеж',
                'Екатеринбург', 'Ижевск', 'Казань', 'Калуга', 'Кемерово',
                'Киров', 'Краснодар', 'Красноярск', 'Курган', 'Курск',
                'Москва', 'Набережные Челны', 'Нижний Новгород', 'Новосибирск',
                'Омск', 'Оренбург', 'Ростов-на-Дону', 'Самара', 'Санкт-Петербург',
                'Саратов', 'Тамбов', 'Тверь', 'Томск', 'Уфа', 'Хабаровск', 'Челябинск',
                'Чебоксары', 'Ярославль']
    selects4 = ['Вода', 'Этиленгликоль', 'Пропиленгликоль']
    selects5 = ['Насосы консольные "К"', 'Насосы консольные моноблочные "КМ"', 'Насосы линейные циркуляционные',
                'Насосы двухстороннего входа', 'Насосы секционные', 'Насосы "КГВ" специальные',
                'Насосы "НКУ" специальные']
    inputs1 = [
        {
            'placeholder': 'Расход, м3/ч',
            'type': 'float',
            'name': 'flow_rate',
            'value': '',
        },
        {
            'placeholder': 'Напор, м',
            'type': 'float',
            'name': 'pressure',
            'value': '',
        },
        {
            'placeholder': 'Температура, C',
            'type': 'float',
            'name': 'temperature',
            'value': '',
        },
        {
            'placeholder': 'Давление, бар',
            'type': 'float',
            'name': 'max_pressure',
            'value': ''
        },
    ]
    buttons = ['Вернуться домой', 'Подобрать насос']
    context = {
        'select1': selects1,
        'select2': selects2,
        'select5': selects5,
        'select3': selects3,
        'select4': selects4,
        'input1': inputs1,
        'button1': buttons[0],
        'button2': buttons[1],
        'user_pressure': None,
        'user_flow_rate': None,
        'user_max_pressure': None,
        'user_temperature': None,
        'user_data': None,
        'pumps': Pumps.objects.all(),
        'families': PumpFamily.objects.all(),
        'total_a0': None,
        'total_b0': None,
        'total_c0': None,
        'calc_q2': None,
        'calc_h2': None,
        'calc_a': None,
        'calc_q2_all': None,
        'calc_h2_all': None,
        'calc_a_all': None,
        'not_filter_pumps': None,
        'graph_url': None,
    }

    graph_url = ''
    if request.method == "POST":
        user_pressure = request.POST.get("pressure")
        user_flow_rate = request.POST.get("flow_rate")
        user_max_pressure = request.POST.get("max_pressure")
        user_temperature = request.POST.get("temperature")

        not_filter_pumps = Pumps.objects.all()
        a_0 = Pumps.objects.values_list('a0', flat=True)#.filter(pressure__gt=float(user_pressure))#
        a_0_list = list(a_0)
        b_0 = Pumps.objects.values_list('b0', flat=True)#.filter(pressure__gt=float(user_pressure))#
        b_0_list = list(b_0)
        c_0 = Pumps.objects.values_list('c0', flat=True)#.filter(pressure__gt=float(user_pressure))#
        c_0_list = list(c_0)

        def calc_q2(a_1, b_1, c_1, d_1, e_1):
            return round((-b_1 * math.pow(d_1, 2) - d_1 * math.sqrt(math.pow(d_1, 2) * (math.pow(b_1, 2) - (4 * a_1 * c_1)) + 4 * c_1 * e_1)) / (2 * (a_1 * math.pow(d_1, 2) - e_1)), 2)

        def calc_h2(a_2, b_2, c_2, d_2):
            return round(a_2 * math.pow(d_2, 2) + b_2 * d_2 + c_2, 2)

        def calc_a(d_3, e_3):
            return round(d_3 / pow(e_3, 2), 5)

        def return_data(a, b, c, d):
            return a, b, c, d

        context['user_data'] = return_data(user_flow_rate, user_pressure, user_temperature, user_max_pressure)
        context['total_a0'] = a_0_list
        context['total_b0'] = b_0_list
        context['total_c0'] = c_0_list

        calcs_q2_all = []
        calcs_h2_all = []
        calc_a_all = []
        for i_i in range(len(a_0_list)):
            i_a = a_0_list[i_i]
            i_b = b_0_list[i_i]
            i_c = c_0_list[i_i]
            calcs_q2_all.append(calc_q2(float(i_a), float(i_b), float(i_c), float(user_flow_rate), float(user_pressure)))
            calcs_h2_all.append(calc_h2(float(i_a), float(i_b), float(i_c), calcs_q2_all[i_i]))
            calc_a_all.append(calc_a(calcs_h2_all[i_i], calcs_q2_all[i_i]))

        context['calc_q2_all'] = calcs_q2_all
        context['calc_h2_all'] = calcs_h2_all
        context['calc_a_all'] = calc_a_all
        context['not_filter_pumps'] = not_filter_pumps

        context['calc_q2'] = calc_q2(float(a_0_list[0]), float(b_0_list[0]), float(c_0_list[0]), float(user_flow_rate), float(user_pressure))
        context['calc_h2'] = calc_h2(float(a_0_list[0]), float(b_0_list[0]), float(c_0_list[0]), context['calc_q2'])
        context['calc_a'] = calc_a(context['calc_h2'], context['calc_q2'])

        x = []
        for num in range(math.ceil(float(context['calc_q2']))+1):
            x.append(num)
        x.insert(-1, float(context['calc_q2']))
        print(x)

        y1 = []
        for num_1 in range(len(x)):
            y1.append(float(a_0_list[0] * math.pow(x[num_1], 2) + b_0_list[0] * x[num_1] + c_0_list[0]))
        print(y1)

        y2 = []
        for num_2 in range(len(x)):
            y2.append(float(context['calc_a'] * math.pow(x[num_2], 2)))
        print(y2)

        plt.figure()
        plt.plot(x, y1)
        plt.plot(x, y2)
        plt.title('Для 1-го насоса')
        plt.xlabel('Q, м3/ч')
        plt.ylabel('H, м')

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        graph_url = base64.b64encode(buffer.getvalue()).decode('utf-8')
        context['graph_url'] = graph_url

    return render(request, 'pump_selection.html', context)

#копирую функцию вызова страницы расчета, дублирую на файл index.html


def pump_selection_index(request):
    selects1 = ['Назначение системы', 'Семейство насосов']
    selects2 = ['ХВС', 'СВ', 'СО', 'Подпитка', 'ГВС']
    selects3 = ['Любой', 'Астрахань', 'Барнаул', 'Белгород', 'Бийск',
                'Владивосток', 'Волгоград', 'Вологда', 'Воронеж',
                'Екатеринбург', 'Ижевск', 'Казань', 'Калуга', 'Кемерово',
                'Киров', 'Краснодар', 'Красноярск', 'Курган', 'Курск',
                'Москва', 'Набережные Челны', 'Нижний Новгород', 'Новосибирск',
                'Омск', 'Оренбург', 'Ростов-на-Дону', 'Самара', 'Санкт-Петербург',
                'Саратов', 'Тамбов', 'Тверь', 'Томск', 'Уфа', 'Хабаровск', 'Челябинск',
                'Чебоксары', 'Ярославль']
    selects4 = ['Вода', 'Этиленгликоль', 'Пропиленгликоль']
    selects5 = ['Насосы консольные "К"', 'Насосы консольные моноблочные "КМ"', 'Насосы линейные циркуляционные',
                'Насосы двухстороннего входа', 'Насосы секционные', 'Насосы "КГВ" специальные',
                'Насосы "НКУ" специальные']
    inputs1 = [
        {
            'placeholder': 'Расход, м3/ч',
            'type': 'float',
            'name': 'flow_rate',
            'value': '',
        },
        {
            'placeholder': 'Напор, м',
            'type': 'float',
            'name': 'pressure',
            'value': '',
        },
        {
            'placeholder': 'Температура, C',
            'type': 'float',
            'name': 'temperature',
            'value': '',
        },
        {
            'placeholder': 'Давление, бар',
            'type': 'float',
            'name': 'max_pressure',
            'value': ''
        },
    ]
    buttons = ['Вернуться домой', 'Подобрать насос']
    context = {
        'select1': selects1,
        'select2': selects2,
        'select5': selects5,
        'select3': selects3,
        'select4': selects4,
        'input1': inputs1,
        'button1': buttons[0],
        'button2': buttons[1],
        'user_pressure': None,
        'user_flow_rate': None,
        'user_max_pressure': None,
        'user_temperature': None,
        'user_data': None,
        'pumps': Pumps.objects.all(),
        'families': PumpFamily.objects.all(),
        'total_a0': None,
        'total_b0': None,
        'total_c0': None,
        'calc_q2': None,
        'calc_h2': None,
        'calc_a': None,
        'calc_q2_all': None,
        'calc_h2_all': None,
        'calc_a_all': None,
        'not_filter_pumps': None,
        'graph_url': None,
    }

    graph_url = ''
    if request.method == "POST":
        user_pressure = request.POST.get("pressure")
        user_flow_rate = request.POST.get("flow_rate")
        user_max_pressure = request.POST.get("max_pressure")
        user_temperature = request.POST.get("temperature")

        not_filter_pumps = Pumps.objects.all()
        a_0 = Pumps.objects.values_list('a0', flat=True)#.filter(pressure__gt=float(user_pressure))#
        a_0_list = list(a_0)
        b_0 = Pumps.objects.values_list('b0', flat=True)#.filter(pressure__gt=float(user_pressure))#
        b_0_list = list(b_0)
        c_0 = Pumps.objects.values_list('c0', flat=True)#.filter(pressure__gt=float(user_pressure))#
        c_0_list = list(c_0)

        def calc_q2(a_1, b_1, c_1, d_1, e_1):
            return round((-b_1 * math.pow(d_1, 2) - d_1 * math.sqrt(math.pow(d_1, 2) * (math.pow(b_1, 2) - (4 * a_1 * c_1)) + 4 * c_1 * e_1)) / (2 * (a_1 * math.pow(d_1, 2) - e_1)), 2)

        def calc_h2(a_2, b_2, c_2, d_2):
            return round(a_2 * math.pow(d_2, 2) + b_2 * d_2 + c_2, 2)

        def calc_a(d_3, e_3):
            return round(d_3 / pow(e_3, 2), 5)

        def return_data(a, b, c, d):
            return a, b, c, d

        context['user_data'] = return_data(user_flow_rate, user_pressure, user_temperature, user_max_pressure)
        context['total_a0'] = a_0_list
        context['total_b0'] = b_0_list
        context['total_c0'] = c_0_list

        calcs_q2_all = []
        calcs_h2_all = []
        calc_a_all = []
        for i_i in range(len(a_0_list)):
            i_a = a_0_list[i_i]
            i_b = b_0_list[i_i]
            i_c = c_0_list[i_i]
            calcs_q2_all.append(calc_q2(float(i_a), float(i_b), float(i_c), float(user_flow_rate), float(user_pressure)))
            calcs_h2_all.append(calc_h2(float(i_a), float(i_b), float(i_c), calcs_q2_all[i_i]))
            calc_a_all.append(calc_a(calcs_h2_all[i_i], calcs_q2_all[i_i]))

        context['calc_q2_all'] = calcs_q2_all
        context['calc_h2_all'] = calcs_h2_all
        context['calc_a_all'] = calc_a_all
        context['not_filter_pumps'] = not_filter_pumps

        context['calc_q2'] = calc_q2(float(a_0_list[0]), float(b_0_list[0]), float(c_0_list[0]), float(user_flow_rate), float(user_pressure))
        context['calc_h2'] = calc_h2(float(a_0_list[0]), float(b_0_list[0]), float(c_0_list[0]), context['calc_q2'])
        context['calc_a'] = calc_a(context['calc_h2'], context['calc_q2'])

        x = []
        for num in range(math.ceil(float(context['calc_q2']))+1):
            x.append(num)
        x.insert(-1, float(context['calc_q2']))
        print(x)

        y1 = []
        for num_1 in range(len(x)):
            y1.append(float(a_0_list[0] * math.pow(x[num_1], 2) + b_0_list[0] * x[num_1] + c_0_list[0]))
        print(y1)

        y2 = []
        for num_2 in range(len(x)):
            y2.append(float(context['calc_a'] * math.pow(x[num_2], 2)))
        print(y2)

        plt.figure()
        plt.plot(x, y1)
        plt.plot(x, y2)
        plt.title('Для 1-го насоса')
        plt.xlabel('Q, м3/ч')
        plt.ylabel('H, м')

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        graph_url = base64.b64encode(buffer.getvalue()).decode('utf-8')
        context['graph_url'] = graph_url

    return render(request, 'index.html', context)
