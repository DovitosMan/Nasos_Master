from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import redirect
import math
import cadquery as cq
from cadquery import exporters
import numpy as np


def wheel_calc(request):
    context = {
        'selects': [
            {'type': 'option', 'placeholder': 'Расчет рабочего колеса:',
             'keys': ['Центробежный насос', 'Струйный насос']},
            {'type': 'input', 'placeholder': 'Расход, м3/ч', 'name': 'flow_rate', 'value': ''},
            {'type': 'input', 'placeholder': 'Напор, м', 'name': 'pressure', 'value': ''},
            {'type': 'input', 'placeholder': 'Плотность, кг/м3', 'name': 'density', 'value': ''},
            {'type': 'input', 'placeholder': 'Частота вр., об/мин', 'name': 'rotation_speed', 'value': ''},
        ],
        'calculations': [
            {'name': 'Коэффициент быстроходности насоса: ', 'value': None, 'round': 0, 'unit': '', },
            {'name': 'Наружный диаметр рабочего колеса: ', 'value': None, 'round': 4, 'unit': ' мм', },
            {'name': 'Ширина лопастного канала рабочего колеса на входе: ', 'value': None, 'round': 4,
             'unit': ' мм', },
            {'name': 'Приведенный диаметр входа в рабочее колесо 1: ', 'value': None, 'round': 4,
             'unit': ' мм', },
            {'name': 'Приведенный диаметр входа в рабочее колесо 2: ', 'value': None, 'round': 4,
             'unit': ' мм', },
            {'name': 'Объемный КПД: ', 'value': None, 'round': 3, 'unit': ' %', },
            {'name': 'Гидравлический КПД: ', 'value': None, 'round': 3, 'unit': ' %', },
            {'name': 'Внутр. мех. КПД: ', 'value': None, 'round': 3, 'unit': ' %', },
            {'name': 'Полный ожидаемый КПД: ', 'value': None, 'round': 3, 'unit': ' %', },
            {'name': 'Мощность: ', 'value': None, 'round': 0, 'unit': ' кВт', },
            {'name': 'Мощность максимальная: ', 'value': None, 'round': 0, 'unit': ' кВт', },
            {'name': 'Диаметр вала: ', 'value': None, 'round': 0, 'unit': ' мм', },
            {'name': 'Диаметр входа в рабочее колесо: ', 'value': None, 'round': 4, 'unit': ' мм', },
        ],
        'error': None,
        'plots': [],
        'input_data': {},

    }

    if request.method == "POST":
        # Получаем данные из формы
        try:
            flow_rate = float(request.POST.get("flow_rate"))
            pressure = float(request.POST.get("pressure"))
            density = float(request.POST.get("density"))
            rotation_speed = float(request.POST.get("rotation_speed"))
            for select in context['selects']:
                if select['type'] == 'input':
                    name = select['name']
                    select['value'] = request.POST.get(name, "")
            calculated_values = calculations(flow_rate, pressure, density, rotation_speed)  # Получаем расчёты
            update_context(context, calculated_values)  # Обновляем context
            format_context_list(context)  # форматирование текста

            r_list, angle_total_list, number_of_blades, thickness, b_list_updated = calculations_2(flow_rate, pressure,
                                                                                                   density,
                                                                                                   rotation_speed)
            contour_1, contour_2, contour_3, heihgt_blades = create_section_meridional(flow_rate, pressure, density,
                                                                                       rotation_speed,
                                                                                       r_list,
                                                                                       b_list_updated)
            create_wheel(contour_1, contour_2, contour_3, heihgt_blades, r_list, angle_total_list, number_of_blades,
                         thickness)

        except ZeroDivisionError:
            context['error'] = 'Ошибка: деление на ноль. Были выбраны неправильные данные.'
        except ValueError:
            context['error'] = 'Ошибка: введены некорректные числовые данные.'
        except TypeError as e:
            if "complex" in str(e):
                context['error'] = 'Ошибка: расчёты привели к комплексному числу, а ожидалось вещественное.'
            else:
                context['error'] = f'Ошибка типа данных: {str(e)}'
    else:
        # Для GET-запроса ошибка всегда None — это сбрасывает старые ошибки
        context['error'] = None
    print("Request method:", request.method)
    print("Error in context:", context.get('error'))
    return render(request, 'calculations.html', context)


def calculations(flow_rate, pressure, density, speed):
    # Коэффициент быстроходности насоса
    pump_speed_coef = round((3.65 * speed * math.sqrt(flow_rate / 60 / 60)) / (pressure ** (3 / 4)))
    # Наружный диаметр рабочего колеса
    k_od = 9.35 * math.sqrt(100 / pump_speed_coef)
    outer_diam_of_work_wheel = round((k_od * (flow_rate / 3600 / speed) ** (1 / 3)), 4) * 1000
    # Ширина лопастного канала рабочего колеса на входе
    if pump_speed_coef <= 200:
        k_w = 0.8 * math.sqrt(pump_speed_coef / 100)
    else:
        k_w = 0.635 * (pump_speed_coef / 100) ** (5 / 6)
    width_in_enter_of_work_wheel = round(k_w * (flow_rate / 3600 / speed) ** (1 / 3), 4)
    # Приведенный диаметр входа в рабочее колесо
    k_in = 6
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
    k_inner = 1.3
    hub_diameter = math.ceil(shaft_diameter * k_inner / 5) * 5
    if pump_speed_coef <= 90:
        k_inner_0 = 1.1
    elif 90 < pump_speed_coef <= 300:
        k_inner_0 = 0.8
    else:
        k_inner_0 = 0.7
    if inner_diam_of_work_wheel_1 < inner_diam_of_work_wheel_2:
        enter_diameter_0 = round(((inner_diam_of_work_wheel_1 * 1000) ** 2 + (shaft_diameter * k_inner) ** 2) ** 0.5, 1)
    else:
        enter_diameter_0 = round(((inner_diam_of_work_wheel_2 * 1000) ** 2 + (shaft_diameter * k_inner) ** 2) ** 0.5, 1)
    enter_diameter_1 = enter_diameter_0 * k_inner_0

    return (pump_speed_coef, outer_diam_of_work_wheel, width_in_enter_of_work_wheel, inner_diam_of_work_wheel_1,
            inner_diam_of_work_wheel_2, n_0, n_r, n_m, n_a, power, power_max, shaft_diameter, enter_diameter_0,
            enter_diameter_1, hub_diameter, v_0)


def calculations_2(flow_rate, pressure, density, rotation_speed, num_items=10):
    data = calculations(flow_rate, pressure, density, rotation_speed)

    n_vol = round(data[5] / 100, 3)
    n_hydro = round(data[6] / 100, 3)
    d_hub = data[14]  # dвт в мм

    if 50 <= data[0] <= 60:
        number_of_blade = 9 if data[0] < 55 else 8
    elif 60 < data[0] <= 180:
        number_of_blade = 8 if data[0] < 120 else 6
    elif 180 < data[0] <= 350:
        number_of_blade = 6
    elif 350 < data[0] <= 600:
        number_of_blade = 6 if data[0] < 475 else 5
    else:
        raise ValueError("Удельная скорость ns вне диапазона (50…600)")

    flow_rate_m_s = flow_rate / 3600

    r_outer = data[1] / 2  # d2 / 2
    r_inner = data[13] / 2  # d1 / 2
    v_t_1 = (4 * flow_rate_m_s) / (n_vol * math.pi * (math.pow(2 * r_inner / 1000, 2) -
                                                      math.pow(d_hub / 1000, 2)))
    u_2 = math.pi * (2 * r_outer / 1000) * rotation_speed / 60

    m = round(r_outer / r_inner)

    def linear_interpolate_or_extrapolate(x, x_table, y_table):
        return round(float(np.interp(x, x_table, y_table, left=None, right=None)), 1)

    d2 = data[1]  # внешний диаметр колеса, мм

    d2_table = [100, 200, 300, 500, 800]
    delta_1_table = [1.25, 1.25, 2.0, 3.5, 4.5]
    delta_2_table = [3.0, 3.75, 4.5, 5.5, 9.0]
    delta_max_table = [4.0, 4.5, 6.5, 7.5, 12.0]

    thickness_of_blade_inlet = linear_interpolate_or_extrapolate(d2, d2_table, delta_1_table)
    thickness_of_blade_outlet = linear_interpolate_or_extrapolate(d2, d2_table, delta_2_table)
    thickness_of_blade_max = linear_interpolate_or_extrapolate(d2, d2_table, delta_max_table)

    # def calculate_angles():

    if data[0] < 50:
        angle_b_l_2_range = (20, 25)
    elif 50 <= data[0] <= 100:
        angle_b_l_2_range = (25, 35)
    elif 100 < data[0] <= 200:
        angle_b_l_2_range = (23, 27)
    elif 200 < data[0] <= 400:
        angle_b_l_2_range = (18, 22)
    else:
        angle_b_l_2_range = (15, 18)

    angle_b_l_1_range = (15, 30)
    attack_angle_b_range = (3, 8)

    v_t_0 = data[15]
    b_1 = flow_rate_m_s / (n_vol * math.pi * (2 * r_inner / 1000) * v_t_1)
    u_1 = math.pi * (2 * r_inner / 1000) * rotation_speed / 60
    angle_b_1 = round(math.atan(v_t_1 / u_1) * 180 / math.pi)

    found = False  # флаг для выхода из вложенных циклов

    for angle in range(max(angle_b_l_2_range), min(angle_b_l_2_range), -1):
        for attack_angle in range(min(attack_angle_b_range), max(attack_angle_b_range), 1):
            angle_b_l_1 = angle_b_1 + attack_angle
            if min(angle_b_l_1_range) <= angle_b_l_1 <= max(angle_b_l_1_range):
                flow_resistance_koef_1 = 1 - (number_of_blade * thickness_of_blade_inlet /
                                              (math.pi * 2 * r_inner * math.sin(angle_b_l_1 * math.pi / 180)))
                v_t_2 = v_t_1 / flow_resistance_koef_1

                flow_resistance_koef_2 = 1 - (number_of_blade * thickness_of_blade_outlet /
                                              (math.pi * 2 * r_outer * math.sin(angle * math.pi / 180)))

                v_t_3 = flow_rate_m_s / (
                            flow_resistance_koef_2 * math.pi * 2 * r_outer / 1000 * data[2])
                v_t_4 = v_t_3 * flow_resistance_koef_2

                angle_b_2 = angle - attack_angle

                if data[0] < 150:
                    fi = 0.6 + 0.6 * math.sin(angle_b_2 * math.pi / 180)
                elif 150 <= data[0] <= 200:
                    fi = (1.6 * math.sin(angle_b_2 * math.pi / 180) + math.sin(angle_b_1 * math.pi / 180) *
                          math.pow(r_inner / r_outer, 2))
                else:
                    fi = (math.sin(angle_b_1 * math.pi / 180) *
                          (1.7 + 13.3 * math.pow((v_t_4 / (u_2 * math.tan(angle_b_2 * math.pi / 180))), 2)))
                mu = math.pow((1 + ((2 * fi * (2 * r_outer / 1000)) / (
                        number_of_blade * (math.pow(2 * r_outer / 1000, 2) - math.pow(2 * r_inner / 1000, 2))))),
                              -1)
                v_u_2_inf = 9.81 * pressure / (mu * n_hydro * u_2)
                pressure_inf = v_u_2_inf * u_2 / 9.81
                pressure_check = pressure_inf * mu * n_hydro
                cot_b_l_1 = (u_2 - v_u_2_inf) / v_t_4
                number_of_blade_checked = round(6.5 * ((m + 1) / (m - 1)) *
                                                math.sin((angle_b_l_1 + angle) * math.pi / 2 / 180))

                angle_b_l_2_checked = (2 * math.asin((number_of_blade_checked*(m - 1)) / (6.5 * (m + 1))) * 180 / math.pi - angle_b_l_1)
                if abs(angle - angle_b_l_2_checked) < 0.5:  # допустимая погрешность 0.5°
                    angle_b_l_2 = angle_b_l_2_checked
                    found = True
                    print(f"Найдено решение:")
                    print(f"angle_b_l_1 = {round(angle_b_l_1, 1)}")
                    print(f"angle_b_l_2 = {round(angle_b_l_2, 1)}")
                    print(f"attack_angle = {attack_angle}")
                    print(f"number_of_blade_checked = {number_of_blade_checked}")
                    break  # выход из внутреннего цикла

                if found:
                    break

    r_step = (r_outer - r_inner) / num_items

    r_list = [r_inner]
    for i in range(num_items):
        r_list.append(r_list[i] + r_step)

    v_dependence_k = (v_t_4 - v_t_1) / (r_outer / 1000 - r_inner / 1000)
    v_dependence_b = v_t_4 - v_dependence_k * r_outer / 1000

    v_list = []
    for i in range(len(r_list)):
        v_list.append(v_dependence_k * r_list[i] / 1000 + v_dependence_b)

    flow_rate_real = flow_rate / 3600 / n_vol

    b_list = []
    for i in range(len(r_list)):
        b_list.append(round((flow_rate_real / (2 * math.pi * r_list[i] / 1000 * v_list[i])), 4))

    b_list_updated = []
    for i in b_list:
        if i > b_list[-1]:
            b_list_updated.append(i)
        else:
            b_list_updated.append(data[2])

    w = ((thickness_of_blade_inlet - thickness_of_blade_max) * (r_inner / 1000 - r_outer / 1000) /
         (thickness_of_blade_inlet - thickness_of_blade_outlet))
    f = 2 * w - 2 * r_inner / 1000
    t = - r_inner / 1000 * w - r_outer / 1000 * w + (r_inner / 1000) ** 2
    temporary_1 = (- f + math.sqrt(f ** 2 - 4 * t)) / 2
    temporary_2 = (- f - math.sqrt(f ** 2 - 4 * t)) / 2

    thickness_dependence_c = thickness_of_blade_max
    if temporary_1 > r_outer / 1000:
        thickness_dependence_b = temporary_2
    else:
        thickness_dependence_b = temporary_1
    thickness_dependence_a = ((thickness_of_blade_inlet - thickness_of_blade_max) /
                              (2 * (((r_inner / 1000) - (r_outer / 1000)) * (
                                      (r_inner / 1000) + (r_outer / 1000) - 2 * thickness_dependence_b))))

    thickness_list = []
    for i in r_list:
        thickness_list.append(
            round((thickness_dependence_a * ((i / 1000) - thickness_dependence_b) ** 2 + thickness_dependence_c), 1))

    w_inlet = v_list[0] / math.sin(angle_b_l_1 * math.pi / 180)
    w_outlet = v_list[-1] / math.sin(angle_b_l_2 * math.pi / 180)
    w_dependence_k = (w_outlet - w_inlet) / (r_outer / 1000 - r_inner / 1000)
    w_dependence_b = w_outlet - w_dependence_k * r_outer / 1000
    w_list = [w_inlet]
    for i in range(num_items):
        w_list.append(w_dependence_k * r_list[i + 1] / 1000 + w_dependence_b)

    b_l_list = []
    for i in range(len(r_list)):
        b_l_list.append(round((math.asin(v_list[i] / w_list[i] + number_of_blade_checked * thickness_list[i] /
                                         (2 * math.pi * r_list[i])) * 180 / math.pi), 1))

    num_integrate_list = []
    for i in range(len(r_list)):
        num_integrate_list.append(1 / (r_list[i] * math.tan(b_l_list[i] * math.pi / 180) / 1000))

    angle_step_list = []
    for i in range(num_items):
        angle_step_list.append(round((((r_step / 1000) * (num_integrate_list[i] +
                                                          num_integrate_list[i + 1]) / 2) * 180 / math.pi), 1))
    angle_total_list = []
    cumulative = 0
    for i in angle_step_list:
        cumulative += i
        angle_total_list.append(round(cumulative, 1))

    return r_list, angle_total_list, number_of_blade_checked, thickness_list, b_list_updated


def create_section_meridional(flow_rate, pressure, density, rotation_speed, r_list, b_list_updated, debug_mode=True):
    data = calculations(flow_rate, pressure, density, rotation_speed)

    r_list_mm = [round(i, 2) for i in r_list]
    b_list_updated_mm = [round(i * 1000, 2) for i in b_list_updated]

    hub_radius = round(data[14] / 2, 2)
    shaft_radius = data[11] / 2
    thickness = round(b_list_updated_mm[-1] / 3, 0)

    points = [
        (0, r_list_mm[-1]),  # Точка 1
        (0, hub_radius + data[12] / 2),  # Точка 2
        (-data[12] / 2, hub_radius),  # Точка 3
        (-data[12] / 2, shaft_radius),  # Точка 4
        (thickness, shaft_radius),  # Точка 5
        (thickness, r_list_mm[-1])  # Точка 6
    ]

    b_list_updated_mm_reversed = b_list_updated_mm[::-1]

    r_list_mm_reversed = r_list_mm[::-1]

    point_center = (-data[12] / 2, hub_radius + data[12] / 2)

    points_2 = []
    points_3 = []

    for i, j in zip(r_list_mm_reversed, b_list_updated_mm_reversed):
        if i > point_center[1]:
            points_2.append((-j / 2, i))
            points_3.append((-j, i))
        else:
            points_2.append(
                (
                    point_center[0] + math.sqrt((abs(point_center[0]) - j / 2) ** 2 - (i - point_center[1]) ** 2),
                    i
                )
            )
            points_3.append(
                (
                    j * (-math.sqrt((abs(point_center[0]) - j / 2) ** 2 - (i - point_center[1]) ** 2)) /
                    (2 * (abs(point_center[0]) - j / 2)) + point_center[0] + math.sqrt(
                        (abs(point_center[0]) - j / 2) ** 2 - (i - point_center[1]) ** 2),
                    j * (point_center[1] - i) / (2 * (abs(point_center[0]) - j / 2)) + i
                )
            )

    points_3.append((point_center[0], r_list_mm[0]))

    # Добавляем промежуточные точки между последними двумя с контролем кривизны
    if len(points_3) >= 2:
        # Берем последние две точки
        p_start = points_3[-2]
        p_end = points_3[-1]

        # Параметры для регулировки кривизны
        NUM_POINTS = 5  # Количество промежуточных точек
        CURVATURE = 0.1  # 0.0 - линейно, >0 - выпуклость вверх

        # Вычисляем контрольную точку для кривизны
        control_y = min(p_start[1], p_end[1]) - abs(p_start[1] - p_end[1]) * CURVATURE

        # Квадратичная интерполяция
        x_values = np.linspace(p_start[0], p_end[0], NUM_POINTS + 2)[1:-1]
        y_values = []

        for x in x_values:
            t = (x - p_start[0]) / (p_end[0] - p_start[0])
            y = (1 - t) ** 2 * p_start[1] + 2 * (1 - t) * t * control_y + t ** 2 * p_end[1]
            y_values.append(y)

        # Добавляем новые точки
        new_points = list(zip(x_values, y_values))
        points_3 = points_3[:-1] + new_points + [points_3[-1]]

    # Создаем сплайн с принудительным ограничением
    spline_points = []
    for i in range(len(points_3) - 1):
        # Линейная интерполяция с коррекцией кривизны
        spline_points.extend([
            cq.Vector(points_3[i][0], points_3[i][1], 0),
            cq.Vector(
                (points_3[i][0] + points_3[i + 1][0]) / 2,
                max((points_3[i][1] + points_3[i + 1][1]) / 2, min(points_3[i][1], points_3[i + 1][1]))
            )
        ])
    spline_points.append(cq.Vector(points_3[-1][0], points_3[-1][1], 0))

    mid_point = []  # Используем список вместо кортежа для возможности добавления элементов

    # Перебираем элементы по индексам
    for idx in range(len(b_list_updated_mm_reversed) - 1):  # -1 чтобы не выйти за границы
        current_j = b_list_updated_mm_reversed[idx]
        next_j = b_list_updated_mm_reversed[idx + 1]
        current_i = r_list_mm_reversed[idx]

        if current_j != next_j:
            # Добавляем координаты (x, y)
            mid_point.append((-current_j - thickness, current_i))
            break  # Останавливаем цикл после первого добавления

    # Конвертируем в кортеж при необходимости
    mid_point = tuple(mid_point)

    temp_center = [(
        (-spline_points[-1].x ** 2 + mid_point[0][0] ** 2 - (spline_points[-1].y + thickness - mid_point[0][1]) ** 2) /
        (2 * (-spline_points[-1].x + mid_point[0][0])),
        mid_point[0][1]
    )]
    temp_center = tuple(temp_center)

    r_1 = abs(temp_center[0][0] - mid_point[0][0])
    x_1 = (spline_points[-1].x - mid_point[0][0]) / 2 + mid_point[0][0]
    y_1 = temp_center[0][1] - math.sqrt(r_1 ** 2 - (x_1 - temp_center[0][0]) ** 2)

    height = abs(spline_points[-1].x + 1)

    result = (cq.Workplane("XY")
              .moveTo(points[0][0], points[0][1])
              .lineTo(points[1][0], points[1][1])
              .threePointArc(
        (
            (points[1][0] + points[2][0]) / 2,
            points[1][1] + math.cos(math.pi / 6) * points[2][0]
        ),
        (points[2][0], points[2][1])
    )
              .lineTo(points[3][0], points[3][1])
              .lineTo(points[4][0], points[4][1])
              .lineTo(points[5][0], points[5][1])
              .close()  # Замыкание контура
              )

    result_1 = (cq.Workplane("XY")
                .moveTo(points_3[0][0], points_3[0][1])
                .spline(spline_points)
                .lineTo(spline_points[-1].x, spline_points[-1].y + thickness)
                .threePointArc(
        (x_1, y_1),
        (mid_point[0][0], mid_point[0][1]))
                .lineTo(spline_points[0].x - thickness, spline_points[0].y)
                .close()
                )

    result_2 = (cq.Workplane("XY")
                .moveTo(spline_points[-1].x, spline_points[-1].y + thickness)
                .threePointArc(
        (x_1, y_1),
        (mid_point[0][0], mid_point[0][1]))
                .lineTo(spline_points[0].x - thickness, spline_points[0].y)
                .lineTo(spline_points[-1].x, spline_points[0].y)
                .close()
                )

    if debug_mode:
        # Экспорт основного контура
        main_wp = cq.Workplane("XY").add(result.val())
        cq.exporters.export(main_wp, 'debug_main_contour.step', 'STEP')

        # Экспорт дополнительного контура
        additional_wp = cq.Workplane("XY").add(result_1.val())
        cq.exporters.export(additional_wp, 'debug_additional_contour.step', 'STEP')

    return result, result_1, result_2, height


def create_wheel(contour1, contour2, contour3, height, r_list, angle_total_list, number_of_blades, thickness):
    """Создает колесо из вращенных контуров и выдавливает лопатки"""
    try:
        # 1. Создаем основное тело из контуров
        main_body = (
            contour1.revolve(360, (0, 0, 0), (1, 0, 0))
            .union(contour2.revolve(360, (0, 0, 0), (1, 0, 0)))
        )

        # 2. Создаем лопатки
        blades_data = create_section_blades(
            r_list,
            angle_total_list,
            number_of_blades,
            thickness,
            debug=False
        )

        if not blades_data or 'faces' not in blades_data:
            raise ValueError("Ошибка создания лопаток")

        # 3. Создаем и выдавливаем лопатки
        extruded_blades = cq.Workplane("ZY")
        for face in blades_data['faces']:
            extruded_blades = extruded_blades.add(face).extrude(height)

        # 4. Объединяем все компоненты
        final_body = main_body.union(extruded_blades).cut(contour3.revolve(360, (0, 0, 0), (1, 0, 0)))

        # 6. Вырезаем кольцо на крайней левой стороне (X-)
        ring_inner_radius = max(r_list)  # внутренний радиус кольца
        ring_outer_radius = ring_inner_radius + 30  # внешний радиус кольца
        # Получаем габариты тела
        bbox = final_body.val().BoundingBox()
        x_min = bbox.xmin - 0.1  # небольшое смещение в -X
        x_max = bbox.xmax

        ring_thickness = (x_max - x_min) + 10  # глубина с запасом
        ring_cut = (
            cq.Workplane("YZ").workplane(offset=x_min)
            .circle(ring_outer_radius)
            .circle(ring_inner_radius)
            .extrude(ring_thickness)
        )

        final_body = final_body.cut(ring_cut)

        # 5. Экспорт
        cq.exporters.export(final_body, 'Wheel.step', 'STEP')

        return final_body

    except Exception as e:
        print(f"Ошибка создания колеса: {str(e)}")
        return None


def rotate_vector(v, angle_deg, axis='x'):
    """Вращение вектора вокруг выбранной оси"""
    angle = math.radians(angle_deg)
    x, y, z = v.x, v.y, v.z

    if axis.lower() == 'x':
        return cq.Vector(
            x,
            y * math.cos(angle) - z * math.sin(angle),
            y * math.sin(angle) + z * math.cos(angle)
        )
    elif axis.lower() == 'z':
        return cq.Vector(
            x * math.cos(angle) - y * math.sin(angle),
            x * math.sin(angle) + y * math.cos(angle),
            z
        )
    else:
        raise ValueError("Неподдерживаемая ось вращения")


def create_section_blades(r_list, angle_total_list, number_of_blades, thickness, debug=True):
    # Генерация базового профиля в плоскости ZY
    points = [cq.Vector(0, r_list[0], 0)]  # (Z, Y, X)

    for i, angle in enumerate(angle_total_list):
        r = r_list[i + 1]
        rad_angle = math.radians(angle)
        # Преобразование в плоскость ZY: (Z, Y, X)
        points.append(cq.Vector(
            0,
            r * math.cos(rad_angle),
            r * math.sin(rad_angle)
        ))

    all_wire_list = []

    for blade_idx in range(number_of_blades):
        # Поворот вокруг оси X для плоскости ZY
        angle = blade_idx * (360 / number_of_blades)
        rotated_points = [rotate_vector(p, angle, axis='x') for p in points]

        # Генерация контуров с толщиной
        outer_points = []
        inner_points = []

        for i, p in enumerate(rotated_points):
            # Вычисление нормали в плоскости ZY
            if i == 0:
                tangent = rotated_points[i + 1] - p
            elif i == len(rotated_points) - 1:
                tangent = p - rotated_points[i - 1]
            else:
                tangent = rotated_points[i + 1] - rotated_points[i - 1]

            # Нормаль к касательной в плоскости ZY
            normal = tangent.cross(cq.Vector(1, 0, 0)).normalized()  # Ось X перпендикулярна плоскости ZY
            offset = normal * thickness[i] / 2

            outer_points.append(p + offset)
            inner_points.append(p - offset)

        # Создание замкнутого контура
        edges = [
            cq.Edge.makeSpline(outer_points),
            cq.Edge.makeLine(outer_points[-1], inner_points[-1]),
            cq.Edge.makeSpline(list(reversed(inner_points))),
            cq.Edge.makeLine(inner_points[0], outer_points[0])
        ]

        try:
            wire = cq.Wire.assembleEdges(edges)
            all_wire_list.append(wire)

            # Экспорт для дебага
            if debug:
                cq.exporters.export(wire, f'debug_blade_{blade_idx}.step')
        except Exception as e:
            print(f"Ошибка создания проволочного контура для лопасти {blade_idx}: {e}")

    # Создание общего Compound
    compound = cq.Compound.makeCompound(all_wire_list)

    # Экспорт общего файла
    if debug:
        cq.exporters.export(compound, 'all_blades_compound.step')

    # Создание граней
    faces = []
    for wire in all_wire_list:
        try:
            faces.append(cq.Face.makeFromWires(wire))
        except Exception as e:
            print(f"Ошибка создания грани: {e}")

    return {
        'wires': all_wire_list,
        'faces': faces,
        'compound': compound
    }


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
