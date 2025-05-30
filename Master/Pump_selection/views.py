from django.shortcuts import render
import math
from .models import Pumps, PumpFamily


def pump_selection(request):
    context = {
        'selects': [
            {'type': 'option', 'placeholder': 'Режим расчёта:',
             'keys': [{'name': 'Назначение системы', 'value': None}], },
            {'type': 'option', 'placeholder': 'Назначение:',
             'keys': [{'name': 'ХВС', 'value': 'HVS'},
                      {'name': 'СВ', 'value': 'SV'},
                      {'name': 'СО', 'value': 'SO'},
                      {'name': 'Подпитка', 'value': 'Recharge'},
                      {'name': 'ГВС', 'value': 'GVS'}, ], },
            {'type': 'option', 'placeholder': 'Регион:',
             'keys': [{'name': 'Любой', 'value': 'Any'},
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
                      {'name': 'Ярославль', 'value': 'Yaroslavl'}, ], },
            {'type': 'input', 'placeholder': 'Расход, м³/ч:', 'name': 'flow_rate', 'value': ''},
            {'type': 'input', 'placeholder': 'Напор, м:', 'name': 'pressure', 'value': ''},
            {'type': 'input', 'placeholder': 'Высота всасывания, м:', 'name': 'pump_lift', 'value': ''},
            {'type': 'input', 'placeholder': 'Доп. кав. запас, м:', 'name': 'cav_reserve', 'value': ''},
            {'type': 'option', 'placeholder': 'Тип режима перекачки',
             'keys': [{'name': 'Постоянный', 'value': 'Constant'},
                      {'name': 'Переменный', 'value': 'Variable'}, ], },
            {'type': 'option', 'placeholder': 'Материал',
             'keys': [{'name': 'Сталь', 'value': 'Steel'},
                      {'name': 'Чугун', 'value': 'Cast_iron'},
                      {'name': 'Нержавеющая сталь', 'value': 'Stainless_steel'},
                      {'name': 'Композит', 'value': 'Composite'}, ], },
            {'type': 'input', 'placeholder': 'Частота вращения, об/мин:', 'name': 'rotation_speed', 'value': '', },
            {'type': 'input', 'placeholder': 'Потребляемая мощность, кВт:', 'name': 'power', 'value': ''},
            {'type': 'option', 'placeholder': 'Среда:',
             'keys': [{'name': 'Вода', 'value': 'Water'},
                      {'name': 'Масло турбинное', 'value': 'Ethylene_Glycol'},
                      {'name': 'Нефть+газ', 'value': 'Propylene_Glycol'}], 'value': ''},
            {'type': 'input', 'placeholder': 'Содержание газа, %:', 'name': 'gas_content', },
            {'type': 'option', 'placeholder': 'Наличие твердых включений, (да/нет)',
             'keys': [{'name': 'Да', 'value': 'Yes'},
                      {'name': 'Нет', 'value': 'No'}, ], },
            {'type': 'input', 'placeholder': 'Об. конц. тв. включ., %:', 'name': 'solid_content', 'value': ''},
            {'type': 'input', 'placeholder': 'Макс. лин. р-р тв. включ.,мм:', 'name': 'solid_size','value': ''},
            {'type': 'input', 'placeholder': 'Плотность, кг/м³:', 'name': 'density', 'value': '', },
            {'type': 'input', 'placeholder': 'Вязкость среды, мПа · с:', 'name': 'viscosity', 'value': ''},
            {'type': 'input', 'placeholder': 'Температура эксп., ℃:', 'name': 'temperature', 'value': '' },
            {'type': 'hz', 'placeholder': 'Тmax среды, ℃:', 'name': 'max_temperature', 'class': 'Select_a_value_4', 'value': ''},
            {'type': 'input', 'placeholder': 'Pmax на входе, МПа:', 'name': 'max_pressure', 'class': 'Select_a_value_5', 'value': ''},
            {'type': 'hz', 'placeholder1': 'Список насосов',
             'keys': ['Насосы консольные "К"', 'Насосы консольные моноблочные "КМ"', 'Насосы линейные циркуляционные', 'Насосы двухстороннего входа', 'Насосы секционные',
                      'Насосы "КГВ" специальные', 'Насосы "НКУ" специальные'], },

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
        'debug_test': False
    }
    if request.method == "POST":

        for select in context['selects']:
            if select['type'] == 'input':
                name = select['name']
                select['value'] = request.POST.get(name, "")

        def get_float(value):
            try:
                cleaned_value = str(value).strip().replace(' ', '').replace(',', '.')
                return float(cleaned_value)
            except (ValueError, TypeError, AttributeError):
                return None

        user_data = {
            "pressure": get_float(request.POST.get("pressure")),
            "flow_rate": get_float(request.POST.get("flow_rate")),
            "max_pressure": get_float(request.POST.get("max_pressure")),
            "temperature": get_float(request.POST.get("temperature")),
            "pump_lift": get_float(request.POST.get("pump_lift")),
            "cav_reserve": get_float(request.POST.get("cav_reserve")),
            "rotation_speed": get_float(request.POST.get("rotation_speed")),
            "power": get_float(request.POST.get("power")),
            "gas_content": get_float(request.POST.get("gas_content")),
            "solid_content": get_float(request.POST.get("solid_content")),
            "solid_size": get_float(request.POST.get("solid_size")),
            "density": get_float(request.POST.get("density")),
            "viscosity": get_float(request.POST.get("viscosity")),
        }

        request.session['centrifugal_params'] = {
            'flow_rate': user_data.get('flow_rate'),
            'pressure': user_data.get('pressure'),
            'density': user_data.get('density'),
            'rotation_speed': user_data.get('rotation_speed')
        }
        request.session.modified = True

        required_fields = {
            'pressure': 'Давление',
            'flow_rate': 'Подача',
            'pump_lift': 'Напор',
            'cav_reserve': 'Кав. запас',
            'gas_content': 'Сод. газа',
            'solid_content': 'Конц. тв.',
            'solid_size': 'Р-р тв.',
            'density': 'Плотность',
            'viscosity': 'Вязкость',
        }

        missing_fields = [name for field, name in required_fields.items()
                          if user_data.get(field) is None]

        if missing_fields:
            context['error'] = f"Некорректные значения для: {', '.join(missing_fields)}"
            return render(request, 'pump_selection.html', context)

        for field in required_fields:
            if user_data.get(field) is None:
                context['error'] = f"Некорректное значение для {field}"
                return render(request, 'pump_selection.html', context)

        context['calculations']['user_data'] = (
            user_data["flow_rate"],  # user_flow_rate
            user_data["pressure"],  # user_pressure
            user_data["pump_lift"],  # user_pump_lift
            user_data["cav_reserve"],  # user_cav_reserve
            user_data["rotation_speed"],  # user_rotation_speed
            user_data["power"],  # user_power
            user_data["gas_content"],  # user_gas_content
            user_data["solid_content"],  # user_solid_content
            user_data["solid_size"],  # user_solid_size
            user_data["density"],  # user_density
            user_data["viscosity"],  # user_viscosity
            user_data["temperature"],  # user_temperature
            user_data["max_pressure"]  # user_max_pressure
        )

        pumps = Pumps.objects.only(
            'pump_lift_min', 'pump_lift',
            'cavitation_min', 'cavitation',
            'gas_content_min', 'gas_content',
            'solid_content_min', 'solid_content',
            'solid_size_min', 'solid_size',
            'density_min', 'density',
            'viscosity_min', 'viscosity',
            'pressure_min', 'pressure',
            'feed_min', 'feed',
            'rotation_speed_min', 'rotation_speed',
            'power_min', 'power',
            'name',
            'family'
        )

        pumps_with_score = []
        total_criteria = 11  # Общее количество проверяемых критериев

        for pump in pumps:
            score = 0
            failed_criteria = []

            # Все критерии для проверки
            criteria = [
                ('Давление', pump.pressure_min, pump.pressure, user_data["pressure"]),
                ('Подача', pump.feed_min, pump.feed, user_data["flow_rate"]),
                ('Напор', pump.pump_lift_min, pump.pump_lift, user_data["pump_lift"]),
                ('Кавитационный запас', pump.cavitation_min, pump.cavitation, user_data["cav_reserve"]),
                ('Скорость вращения', pump.rotation_speed_min, pump.rotation_speed, user_data["rotation_speed"]),
                ('Мощность', pump.power_min, pump.power, user_data["power"]),
                ('Газосодержание', pump.gas_content_min, pump.gas_content, user_data["gas_content"]),
                ('Содержание твердых частиц', pump.solid_content_min, pump.solid_content, user_data["solid_content"]),
                ('Размер твердых частиц', pump.solid_size_min, pump.solid_size, user_data["solid_size"]),
                ('Плотность', pump.density_min, pump.density, user_data["density"]),
                ('Вязкость', pump.viscosity_min, pump.viscosity, user_data["viscosity"]),
            ]

            # Проверяем каждый критерий
            for name, min_val, max_val, user_val in criteria:
                if min_val <= user_val <= max_val:
                    score += 1
                else:
                    failed_criteria.append(
                        f"{name}: {user_val} ∉ [{min_val}-{max_val}]"
                    )

            # Фильтр: минимальное количество совпадений
            if score >= total_criteria // 2:  # 50% критериев
                pumps_with_score.append({
                    'pump': pump,
                    'score': score,
                    'total': total_criteria,
                    'failed': failed_criteria
                })

        # Сортировка по приоритету:
        # 1. Количество совпадений (по убыванию)
        pumps_with_score.sort(key=lambda x: (-x['score']))

        # Выбираем топ-3 результата
        context['calculations']['filter_pumps'] = pumps_with_score[:10]

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
        'family': 'Семейство',
        'feed': 'Подача',
        'pressure': 'Напор',
        'cavitation': 'Кав. запас',
        'rotation_speed': 'Частота вращения',
        'power': 'Мощность',
    }
    column_names = ['name', 'family', 'feed', 'pressure', 'cavitation', 'rotation_speed', 'power', ]

    renamed_columns = [column_mapping.get(col, col) for col in column_names]
    return renamed_columns
