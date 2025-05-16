from django.shortcuts import render
from django.http import HttpResponse
import math
import cadquery as cq


def calculations_2(flow_rate, pressure, density, speed, num_items=10):
    data = calculations(flow_rate, pressure, density, speed)

    k = 1.3115
    n_vol = round(data[5] / 100, 3)
    n_hydro = round(data[6] / 100, 3)
    d_hub = data[11] * k
    number_of_blade = 6
    thickness_of_blade_inlet = 8
    thickness_of_blade_outlet = 14
    thickness_of_blade_max = 20
    angle_b_l_2 = 35

    r_outer = data[1] / 2
    r_inner = data[12] / 2

    velocity_inlet = (4 * flow_rate / 3600) / (n_vol * math.pi * (math.pow(2 * r_inner / 1000, 2) -
                                                                  math.pow(d_hub / 1000, 2)))
    width_in_inlet_of_work_field = (flow_rate / 3600) / (n_vol * math.pi * (2 * r_inner / 1000) * velocity_inlet)
    u_1 = math.pi * (2 * r_inner / 1000) * speed / 60
    angle_b_1 = round(math.atan(velocity_inlet / u_1) * 180 / math.pi)
    attack_angle_b = 4
    angle_b_l_1 = angle_b_1 + attack_angle_b

    flow_resistance_koef_1 = 1 - (number_of_blade * thickness_of_blade_inlet /
                                  (math.pi * 2 * r_inner * math.sin(angle_b_l_1 * math.pi / 180)))
    velocity_on_blades = velocity_inlet / flow_resistance_koef_1

    flow_resistance_koef_2 = 1 - (number_of_blade * thickness_of_blade_outlet /
                                  (math.pi * 2 * r_outer * math.sin(angle_b_l_2 * math.pi / 180)))

    velocity_on_outlet = (flow_rate / 3600) / (flow_resistance_koef_2 * math.pi * 2 * r_outer / 1000 * data[2])
    u_2 = math.pi * (2 * r_outer / 1000) * speed / 60

    velocity_after_outlet = velocity_on_outlet * flow_resistance_koef_2

    angle_b_2 = angle_b_l_2 - attack_angle_b

    if data[0] < 150:
        fi = 0.6 + 0.6 * math.sin(angle_b_2 * math.pi / 180)
    elif 150 <= data[0] <= 200:
        fi = (1.6 * math.sin(angle_b_2 * math.pi / 180) + math.sin(angle_b_1 * math.pi / 180) *
              math.pow(r_inner / r_outer, 2))
    else:
        fi = (math.sin(angle_b_1 * math.pi / 180) *
              (1.7 + 13.3 * math.pow((velocity_on_outlet / (u_2 * math.tan(angle_b_2 * math.pi / 180))), 2)))

    mu = math.pow((1 + ((2 * fi * (2 * r_outer / 1000)) / (
                number_of_blade * (math.pow(2 * r_outer / 1000, 2) - math.pow(2 * r_inner / 1000, 2))))), -1)

    velocity_u_2_inf = 9.81 * pressure / (mu * n_hydro * u_2)
    pressure_inf = velocity_u_2_inf * u_2 / 9.81
    pressure_check = pressure_inf * mu * n_hydro

    cot_b_l_1 = (u_2 - velocity_u_2_inf) / velocity_on_outlet
    m = round(r_outer / r_inner)
    number_of_blade_checked = round(6.5 * ((m + 1) / (m - 1)) *
                                    math.sin((angle_b_l_1 + angle_b_l_2) * math.pi / 2 / 180))

    r_step = (r_outer - r_inner) / num_items

    r_list = [r_inner]
    for i in range(num_items):
        r_list.append(r_list[i] + r_step)

    v_dependence_k = (velocity_after_outlet - velocity_inlet) / (r_outer / 1000 - r_inner / 1000)
    v_dependence_b = velocity_after_outlet - v_dependence_k * r_outer / 1000

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
        thickness_list.append(round((thickness_dependence_a * ((i / 1000) - thickness_dependence_b) ** 2 + thickness_dependence_c), 1))

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
                                                         num_integrate_list[i+1]) / 2) * 180 / math.pi), 1))
    angle_total_list = []
    cumulative = 0
    for i in angle_step_list:
        cumulative += i
        angle_total_list.append(round(cumulative, 1))

    return r_list, angle_total_list, number_of_blade_checked, thickness_list
    # print(r_list, len(r_list))
    # print(v_list, len(v_list))
    # print(b_list, len(b_list))
    # print(b_list_updated, len(b_list_updated))
    # print(thickness_list, len(thickness_list))
    # print(w_list, len(w_list))
    # print(b_l_list, len(b_l_list))
    # print(num_integrate_list, len(num_integrate_list))
    # print(angle_step_list, len(angle_step_list))
    # print(angle_total_list, len(angle_total_list))


def create_section_meridional(r_list, angle_total_list, number_of_blades, thickness, step_filename="spline_export.step"):
    # Конвертируем полярные координаты в декартовы (X, Y)
    points = [(r_list[0] * math.cos(0), r_list[0] * math.sin(0))]
    for i, angle in enumerate(angle_total_list):
        r = r_list[i + 1]
        rad_angle = math.radians(angle)
        x = r * math.cos(rad_angle)
        y = r * math.sin(rad_angle)
        points.append((x, y))

    # wp = cq.Workplane("XY")

    angle_step = 360.0 / number_of_blades
    all_objects = []
    thickness_temp = thickness
    thickness_all = thickness
    # for i in range(number_of_blades - 1):

    print(thickness_all)
    for i in range(number_of_blades):
        rotated_points = [
            (
                p[0] * math.cos(math.radians(angle_step * i)) - p[1] * math.sin(math.radians(angle_step * i)),
                p[0] * math.sin(math.radians(angle_step * i)) + p[1] * math.cos(math.radians(angle_step * i))
            )
            for p in points
        ]
        # blade_wp = cq.Workplane("XY")
        for p in rotated_points:
            circle = cq.Workplane("XY").moveTo(p[0], p[1]).circle(10)
            all_objects.append(circle.val())

        spline = cq.Workplane("XY").spline(rotated_points)
        all_objects.append(spline.val())

    print(len(rotated_points), rotated_points)

    compound = cq.Compound.makeCompound(all_objects)
    wp = cq.Workplane("XY").newObject([compound])

    # Экспортируем в STEP
    cq.exporters.export(wp, step_filename, "STEP")

    return wp


def wheel_calc(request):
    context = {'button': ['Pump Master', 'Получить размеры'],
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
               'selects': [
                   {'type': 'option', 'placeholder': 'Расчет рабочего колеса:',
                    'keys': ['Центробежный насос', 'Струйный насос'], },
                   {'type': 'input', 'placeholder': 'Расход, м3/ч', 'name': 'flow_rate', 'value': '', },
                   {'type': 'input', 'placeholder': 'Напор, м', 'name': 'pressure', 'value': '', },
                   {'type': 'input', 'placeholder': 'Плотность, кг/м3', 'name': 'density', 'value': '', },
                   {'type': 'input', 'placeholder': 'Частота вр., об/мин', 'name': 'speed', 'value': '', },
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

        r_list, angle_total_list, number_of_blades, thickness = calculations_2(flow_rate, pressure, density, speed)
        create_section_meridional(r_list, angle_total_list, number_of_blades, thickness)

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
        enter_diameter = round(((inner_diam_of_work_wheel_1 * 1000) ** 2 + (shaft_diameter * k_inner) ** 2) ** 0.5, 1)
    else:
        enter_diameter = round(((inner_diam_of_work_wheel_2 * 1000) ** 2 + (shaft_diameter * k_inner) ** 2) ** 0.5, 1)
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
