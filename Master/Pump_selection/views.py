from django.shortcuts import render
import math
from .models import Pumps, PumpFamily
### Нужно для фильтрации и вывода графика старого ###
# import matplotlib.pyplot as plt
# import io
# import base64
### Нужно для фильтрации и вывода графика старого ###

### Нужно для фильтрации и вывода графика старого ###
# def getting_base_a_0(flow_rate, pressure):
#     a_0 = Pumps.objects.values_list('a0', flat=True).filter(pressure__gt=pressure).filter(
#         feed__gt=flow_rate).order_by("power")
#
#     a_0_list = list(a_0)
#
#     return a_0_list
#
#
# def getting_base_b_0(flow_rate, pressure):
#     b_0 = Pumps.objects.values_list('b0', flat=True).filter(pressure__gt=pressure).filter(
#         feed__gt=flow_rate).order_by("power")
#
#     b_0_list = list(b_0)
#
#     return b_0_list
#
#
# def getting_base_c_0(flow_rate, pressure):
#     c_0 = Pumps.objects.values_list('c0', flat=True).filter(pressure__gt=pressure).filter(
#         feed__gt=flow_rate).order_by("power")
#
#     c_0_list = list(c_0)
#
#     return c_0_list


# def plot(x_, y1_, y2_):
#     plt.figure()
#     plt.plot(x_, y1_)
#     plt.plot(x_, y2_)
#     plt.title('Для 1-го насоса с наименьшей мощностью')
#     plt.xlabel('Q, м3/ч')
#     plt.ylabel('H, м')
#
#     buffer = io.BytesIO()
#     plt.savefig(buffer, format='png')
#     plt.close()
#     buffer.seek(0)
#     graph_url = base64.b64encode(buffer.getvalue()).decode('utf-8')
#
#     return graph_url
### Нужно для фильтрации и вывода графика старого ###

def pump_selection(request):
    context = {
        'button': ['Вернуться домой', 'Подобрать насос'],
        'selects': [
            {
                'type': 'option',
                'placeholder': 'Режим расчёта:',
                'keys': [
                    {'name': 'Назначение системы', 'value': None}
                ],
            },
            {
                'type': 'option',
                'placeholder': 'Назначение:',
                'keys': [
                    {'name': 'ХВС', 'value': 'HVS'},
                    {'name': 'СВ', 'value': 'SV'},
                    {'name': 'СО', 'value': 'SO'},
                    {'name': 'Подпитка', 'value': 'Recharge'},
                    {'name': 'ГВС', 'value': 'GVS'},

                ],
            },
            {
                'type': 'option',
                'placeholder': 'Регион:',
                'keys': [
                    {'name': 'Любой', 'value': 'Any'},
                    {'name': 'Астрахань', 'value': 'Astrakhan'},
                    {'name': 'Барнаул', 'value': 'Barnaul'},
                    {'name': 'Белгород', 'value': 'Belgorod'},
                    {'name': 'Бийск', 'value': 'Biysk'},
                    {'name': 'Владивосток', 'value': 'Vladivostok'},
                    {'name': 'Волгоград', 'value': 'Volgograd'},
                    {'name': 'Вологда', 'value': 'Vologda'},
                    {'name': 'Воронеж', 'value': 'Voronezh'},
                    {'name': 'Екатеринбург', 'value': 'Yekaterinburg'},
                    {'name': 'Ижевск', 'value': 'Izhevsk'},
                    {'name': 'Казань', 'value': 'Kazan'},
                    {'name': 'Калуга', 'value': 'Kaluga'},
                    {'name': 'Кемерово', 'value': 'Kemerovo'},
                    {'name': 'Киров', 'value': 'Kirov'},
                    {'name': 'Краснодар', 'value': 'Krasnodar'},
                    {'name': 'Красноярск', 'value': 'Krasnoyarsk'},
                    {'name': 'Курган', 'value': 'Kurgan'},
                    {'name': 'Курск', 'value': 'Kursk'},
                    {'name': 'Москва', 'value': 'Moscow'},
                    {'name': 'Набережные Челны', 'value': 'Naberezhnye Chelny'},
                    {'name': 'Нижний Новгород', 'value': 'Nizhny Novgorod'},
                    {'name': 'Новосибирск', 'value': 'Novosibirsk'},
                    {'name': 'Омск', 'value': 'Omsk'},
                    {'name': 'Оренбург', 'value': 'Orenburg'},
                    {'name': 'Ростов-на-Дону', 'value': 'Rostov-on-Don'},
                    {'name': 'Самара', 'value': 'Samara'},
                    {'name': 'Санкт-Петербург', 'value': 'Saint Petersburg'},
                    {'name': 'Саратов', 'value': 'Saratov'},
                    {'name': 'Тамбов', 'value': 'Tambov'},
                    {'name': 'Тверь', 'value': 'Tver'},
                    {'name': 'Томск', 'value': 'Tomsk'},
                    {'name': 'Уфа', 'value': 'Ufa'},
                    {'name': 'Хабаровск', 'value': 'Khabarovsk'},
                    {'name': 'Челябинск', 'value': 'Chelyabinsk'},
                    {'name': 'Чебоксары', 'value': 'Cheboksary'},
                    {'name': 'Ярославль', 'value': 'Yaroslavl'},

                ],
            },
            {
                'type': 'input',
                'placeholder': 'Подача, м³,ч:',
                'name': 'flow_rate',
            },
            {
                'type': 'input',
                'placeholder': 'Напор, м:',
                'name': 'pressure',
            },
            {
                'type': 'input',
                'placeholder': 'Высота всасывания, м:',
                'name': 'pump_lift',
            },
            {
                'type': 'input',
                'placeholder': 'Доп. кав. запас, м:',
                'name': 'cav_reserve',
            },
            {
                'type': 'option',
                'placeholder': 'Тип режима перекачки',
                'keys': [
                    {'name': 'Постоянный', 'value': 'Constant'},
                    {'name': 'Переменный', 'value': 'Variable'},
                ],
            },
            {
                'type': 'option',
                'placeholder': 'Материал',
                'keys': [
                    {'name': 'Сталь', 'value': 'Steel'},
                    {'name': 'Чугун', 'value': 'Cast_iron'},
                    {'name': 'Нержавеющая сталь', 'value': 'Stainless_steel'},
                    {'name': 'Композит', 'value': 'Composite'},
                ],
            },
            {
                'type': 'input',
                'placeholder': 'Частота вращения, об/мин:',
                'name': 'rotation_speed',
            },
            {
                'type': 'input',
                'placeholder': 'Потребляемая мощность, кВт:',
                'name': 'power',
            },
            {
                'type': 'option',
                'placeholder': 'Среда:',
                'keys': [
                    {'name': 'Вода', 'value': 'Water'},
                    {'name': 'Этиленгликоль', 'value': 'Ethylene_Glycol'},
                    {'name': 'Пропиленгликоль', 'value': 'Propylene_Glycol'}
                ],
            },
            {
                'type': 'input',
                'placeholder': 'Содержание газа, %:',
                'name': 'gas_content',
            },
            {
                'type': 'option',
                'placeholder': 'Наличие твердых включений, (да/нет)',
                'keys': [
                    {'name': 'Да', 'value': 'Yes'},
                    {'name': 'Нет', 'value': 'No'},
                ],
            },
            {
                'type': 'input',
                'placeholder': 'Об. конц. тв. включ., %:',
                'name': 'solid_content',
            },
            {
                'type': 'input',
                'placeholder': 'Макс. лин. р-р тв. включ.,мм:',
                'name': 'solid_size',
            },
            {
                'type': 'input',
                'placeholder': 'Плотность среды,℃:',
                'name': 'density',
            },
            {
                'type': 'input',
                'placeholder': 'Вязкость среды, мПа*с:',
                'name': 'viscosity',
            },
            {
                'type': 'input',
                'placeholder': 'Температура эксп., ℃:',
                'name': 'temperature',
            },
            {
                'type': 'input',
                'placeholder': 'Тmax среды, ℃:',
                'name': 'max_temperature',
                'class': 'Select_a_value_4'
            },
            {
                'type': 'input',
                'placeholder': 'Pmax на входе, МПа:',
                'name': 'max_pressure',
                'class': 'Select_a_value_5'
            },
            {
                'type': 'hz',
                'placeholder1': 'Список насосов',
                'keys': ['Насосы консольные "К"', 'Насосы консольные моноблочные "КМ"',
                         'Насосы линейные циркуляционные',
                         'Насосы двухстороннего входа', 'Насосы секционные', 'Насосы "КГВ" специальные',
                         'Насосы "НКУ" специальные'],
            },

        ],
        'calculations': {
            'user_pressure': None,
            'user_flow_rate': None,
            'user_max_pressure': None,
            'user_temperature': None,
            'user_pump_lift': None,
            'user_cav_reserve': None,
            'user_rotation_speed': None,
            'user_power': None,
            'user_gas_content': None,
            'user_solid_content': None,
            'user_solid_size': None,
            'user_density': None,
            'user_viscosity': None,
            'user_data': None,
            'pumps': Pumps.objects.all(),
            'families': PumpFamily.objects.all(),
            'total_a0': None,
            'total_b0': None,
            'total_c0': None,
            'calc_q2_all': None,
            'calc_h2_all': None,
            'calc_a_all': None,
            'calc_q2': None,
            'calc_h2': None,
            'calc_a': None,
            'not_filter_pumps': None,
            'graph_url': None,
        },
        'columns': None,
        'debug_test': True
    }

    if request.method == "POST":
        user_pressure = request.POST.get("pressure")
        user_flow_rate = request.POST.get("flow_rate")
        user_max_pressure = request.POST.get("max_pressure")
        user_temperature = request.POST.get("temperature")
        user_pump_lift = request.POST.get('pump_lift')
        user_cav_reserve = request.POST.get('cav_reserve')
        user_rotation_speed = request.POST.get('rotation_speed')
        user_power = request.POST.get('power')
        user_gas_content = request.POST.get('gas_content')
        user_solid_content = request.POST.get('solid_content')
        user_solid_size = request.POST.get('solid_size')
        user_density = request.POST.get('density')
        user_viscosity = request.POST.get('viscosity')

        ### Нужно для фильтрации и вывода графика старого ###
        # filter_pumps = Pumps.objects.all().filter(pressure__gt=user_pressure).filter(feed__gt=user_flow_rate).order_by(
        #     "power")
        ### Нужно для фильтрации и вывода графика старого ###

        context['calculations']['user_data'] = (user_flow_rate, user_pressure, user_pump_lift, user_cav_reserve,
                                                user_rotation_speed, user_power, user_gas_content, user_solid_content,
                                                user_solid_size, user_density, user_viscosity, user_temperature,
                                                user_max_pressure)
        ### Нужно для фильтрации и вывода графика старого ###
        # context['calculations']['total_a0'] = getting_base_a_0(user_flow_rate, user_pressure)
        # context['calculations']['total_b0'] = getting_base_b_0(user_flow_rate, user_pressure)
        # context['calculations']['total_c0'] = getting_base_c_0(user_flow_rate, user_pressure)

        # calcs_q2_all = []
        # calcs_h2_all = []
        # calc_a_all = []
        # for i_i in range(len(getting_base_a_0(user_flow_rate, user_pressure))):
        #     i_a = getting_base_a_0(user_flow_rate, user_pressure)[i_i]
        #     i_b = getting_base_b_0(user_flow_rate, user_pressure)[i_i]
        #     i_c = getting_base_c_0(user_flow_rate, user_pressure)[i_i]
        #     calcs_q2_all.append(
        #         calc_q2(float(i_a), float(i_b), float(i_c), float(user_flow_rate), float(user_pressure)))
        #     calcs_h2_all.append(calc_h2(float(i_a), float(i_b), float(i_c), calcs_q2_all[i_i]))
        #     calc_a_all.append(calc_a(calcs_h2_all[i_i], calcs_q2_all[i_i]))
        #
        # context['calculations']['calc_q2_all'] = calcs_q2_all
        # context['calculations']['calc_h2_all'] = calcs_h2_all
        # context['calculations']['calc_a_all'] = calc_a_all
        # context['calculations']['filter_pumps'] = filter_pumps
        #
        # context['calculations']['calc_q2'] = calc_q2(float(getting_base_a_0(user_flow_rate, user_pressure)[0]),
        #                                              float(getting_base_b_0(user_flow_rate, user_pressure)[0]),
        #                                              float(getting_base_c_0(user_flow_rate, user_pressure)[0]),
        #                                              float(user_flow_rate), float(user_pressure))
        # context['calculations']['calc_h2'] = calc_h2(float(getting_base_a_0(user_flow_rate, user_pressure)[0]),
        #                                              float(getting_base_b_0(user_flow_rate, user_pressure)[0]),
        #                                              float(getting_base_c_0(user_flow_rate, user_pressure)[0]),
        #                                              context['calculations']['calc_q2'])
        # context['calculations']['calc_a'] = calc_a(context['calculations']['calc_h2'],
        #                                            context['calculations']['calc_q2'])
        #
        # x = []
        # for num in range(math.ceil(float(context['calculations']['calc_q2'])) + 1):
        #     x.append(num)
        # x.insert(-1, float(context['calculations']['calc_q2']))
        #
        # y1 = []
        # for num_1 in range(len(x)):
        #     y1.append(float(getting_base_a_0(user_flow_rate, user_pressure)[0] * math.pow(x[num_1], 2) +
        #                     getting_base_b_0(user_flow_rate, user_pressure)[0] * x[num_1] +
        #                     getting_base_c_0(user_flow_rate, user_pressure)[0]))
        #
        # y2 = []
        # for num_2 in range(len(x)):
        #     y2.append(float(context['calculations']['calc_a'] * math.pow(x[num_2], 2)))
        #
        # context['calculations']['graph_url'] = plot(x, y1, y2)
        ### Нужно для фильтрации и вывода графика старого ###

        ### Новая логика выбора и фильтрации ###
        # Фильтрация насосов по диапазонам
        filtered_pumps = Pumps.objects.filter(
            # feed_min__lte=user_flow_rate, feed__gte=user_flow_rate,
            # pressure_min__lte=user_pressure, pressure__gte=user_pressure,
            pump_lift_min__lte=user_pump_lift, pump_lift__gte=user_pump_lift,
            cavitation_min__lte=user_cav_reserve, cavitation__gte=user_cav_reserve,
            # rotation_speed_min__lte=user_rotation_speed, rotation_speed__gte=user_rotation_speed,
            # power_min__lte=user_power, power__gte=user_power,
            gas_content_min__lte=user_gas_content, gas_content__gte=user_gas_content,
            solid_content_min__lte=user_solid_content, solid_content__gte=user_solid_content,
            solid_size_min__lte=user_solid_size, solid_size__gte=user_solid_size,
            density_min__lte=user_density, density__gte=user_density,
            viscosity_min__lte=user_viscosity, viscosity__gte=user_viscosity
        )
        context['calculations']['filter_pumps'] = filtered_pumps
        ### Новая логика выбора и фильтрации ###

        context['columns'] = column_renaming()

    return render(request, 'pump_selection.html', context)


def calc_q2(a_1, b_1, c_1, d_1, e_1):
    return round((-b_1 * math.pow(d_1, 2) - d_1 * math.sqrt(
        math.pow(d_1, 2) * (math.pow(b_1, 2) - (4 * a_1 * c_1)) + 4 * c_1 * e_1)) / (
                         2 * (a_1 * math.pow(d_1, 2) - e_1)), 2)


def calc_h2(a_2, b_2, c_2, d_2):
    return round(a_2 * math.pow(d_2, 2) + b_2 * d_2 + c_2, 2)


def calc_a(d_3, e_3):
    return round(d_3 / pow(e_3, 2), 5)


def column_renaming():
    column_mapping = {
        'name': 'Марка насоса',
        'price': 'Цена',
        'quantity': 'Количество',
        'family': 'Семейство',
        'feed': 'Подача',
        'pressure': 'Напор',
        'cavitation': 'Кав. запас',
        'rotation_speed': 'Частота вращения',
        'power': 'Мощность',
        'mass': 'Масса насоса',
        'mass_all': 'Масса агрегата',
    }
    column_names = ['name', 'price', 'quantity', 'family', 'feed', 'pressure', 'cavitation', 'rotation_speed',
                    'power',
                    'mass', 'mass_all']
    # Переименование
    renamed_columns = [column_mapping.get(col, col) for col in column_names]
    return renamed_columns
