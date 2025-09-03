import math

from django.shortcuts import render
import bisect
from Flanges_calculations.steel_prop_data import strength_data, yield_data
from .data import class_data, k_n_values
from .report_doc import generate_report


def t_pipes(request):
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Условный диаметр трубопровода DN, мм', 'name': 'D_N_pipe', 'value': '',
             'max': 1400, 'min': 10},
            {'type': 'float', 'placeholder': 'Условный диаметр ответвления тройника DN, мм', 'name': 'D_N_b', 'value': '', 'max': 1400,
             'min': 10},
            {'type': 'float', 'placeholder': 'Рабочее давление, P, МПа', 'name': 'pressure', 'value': '', 'max': 32.0,
             'min': 0.1},
            {'type': 'float', 'placeholder': 'Температура эксплуатации C', 'name': 'temperature', 'value': '',
             'max': 380, 'min': 21},
            {'type': 'float', 'placeholder': 'Наружный диаметр трубопровода Dn, мм', 'name': 'D_n', 'value': '', 'max': 1400,
             'min': 10},
            {'type': 'float', 'placeholder': 'Внутренний диаметр ответвления Db, мм', 'name': 'D_vn', 'value': '',
             'max': 1400, 'min': 10},
            {'type': 'float', 'placeholder': 'Полудлина тройника L, мм', 'name': 'L', 'value': '',
             'max': 1400, 'min': 10},
        ],
        'selects': [
            {'type': 'option', 'placeholder': 'Марка стали тройника', 'name': 'steel_grade', 'value': '',
             'keys': [
                 {'name': "10", 'value': "10"},
                 {'name': "20", 'value': "20"},
                 {'name': "25", 'value': "25"},
                 {'name': "30", 'value': "30"},
                 {'name': "35", 'value': "35"},
                 {'name': "40", 'value': "40"},
                 {'name': "35Х", 'value': "35Х"},
                 {'name': "40Х", 'value': "40Х"},
                 {'name': "30ХМА", 'value': "30ХМА"},
                 {'name': "25Х1МФ", 'value': "25Х1МФ"},
                 {'name': "25Х2М1Ф", 'value': "25Х2М1Ф"},
                 {'name': "20Х13", 'value': "20Х13"},
                 {'name': "18Х12ВМБФР", 'value': "18Х12ВМБФР"},
                 {'name': "12Х18Н10Т", 'value': "ХН35ВТ"},
                 {'name': "ХН35ВТ", 'value': "ХН35ВТ"},
                 {'name': "Д16", 'value': "Д16"},
             ],
             },
        ]
    }

    if request.method == "POST":
        input_data = {}
        input_select = {}

        for select in context['calc']:
            name = select['name']
            raw_value = request.POST.get(name, '')
            select['value'] = raw_value
            try:
                input_data[name] = float(raw_value)
            except ValueError:
                input_data[name] = None

        for select in context['selects']:
            name = select['name']
            raw = request.POST.get(name, '')
            select['value'] = raw
            input_select[name] = raw

        result = calc(input_data, input_select)
        print_result(result)
        generate_report(result)
        print("отчет создан")

    return render(request, 't_pipes.html', context)


def get_steel_class(steel_grade, temperature):

    sigma_b_T, sigma_y_T = get_steel_prop(steel_grade, temperature)
    div = sigma_y_T / sigma_b_T

    best_class = None
    best_sigma_y_min = -1

    for steel_class, (sigma_b_range, sigma_y_min, max_ratio) in class_data.items():
        sigma_b_min, sigma_b_max = sigma_b_range
        if (sigma_b_min <= sigma_b_T <= sigma_b_max and
                sigma_y_T >= sigma_y_min and
                div <= max_ratio):
            if sigma_y_min > best_sigma_y_min:
                best_sigma_y_min = sigma_y_min
                best_class = steel_class

    return best_class


def get_steel_prop(steel_grade, temperature: float):
    key_3 = None
    for grades in strength_data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key_3 = grades
            break

    if key_3 is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data_3 = strength_data[key_3]
    sigma_b_20 = temp_data_3[20]

    if temperature in temp_data_3:
        return sigma_b_20, temp_data_3[temperature]

    temps_3 = sorted(temp_data_3.keys())
    if temperature < temps_3[0] or temperature > temps_3[-1]:
        raise ValueError(f"Температура {temperature}°C вне диапазона данных для этой стали.")

    pos_3 = bisect.bisect_left(temps_3, temperature)
    t_1_3, t_2_3 = temps_3[pos_3 - 1], temps_3[pos_3]
    sigma_b_1, sigma_b_2 = temp_data_3[t_1_3], temp_data_3[t_2_3]
    sigma_b_T = round((sigma_b_1 + (sigma_b_2 - sigma_b_1) * (temperature - t_1_3) / (t_2_3 - t_1_3)), 3)

    key_4 = None
    for grades in yield_data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key_4 = grades
            break

    if key_4 is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data_4 = yield_data[key_4]
    sigma_y_20 = temp_data_4[20]

    if temperature in temp_data_4:
        return sigma_y_20, temp_data_4[temperature]

    temps_4 = sorted(temp_data_4.keys())
    if temperature < temps_4[0] or temperature > temps_4[-1]:
        raise ValueError(f"Температура {temperature}°C вне диапазона данных для этой стали.")

    pos_4 = bisect.bisect_left(temps_4, temperature)
    t_1_4, t_2_4 = temps_4[pos_4 - 1], temps_4[pos_4]
    sigma_y_1, sigma_y_2 = temp_data_4[t_1_4], temp_data_4[t_2_4]
    sigma_y_T = round((sigma_y_1 + (sigma_y_2 - sigma_y_1) * (temperature - t_1_4) / (t_2_4 - t_1_4)), 3)

    return sigma_b_T, sigma_y_T


def calc(input_data, input_select, max_iter=100):
    D_N_pipe = float(input_data['D_N_pipe'])
    D_N_b = float(input_data['D_N_b'])
    D_n = float(input_data['D_n']) + 4.0
    D_vn = float(input_data['D_vn'])
    L = float(input_data['L'])
    steel_grade = input_select.get("steel_grade", None)
    temperature = float(input_data.get("temperature", 20))
    steel_class = get_steel_class(steel_grade, temperature)
    pressure = float(input_data['pressure'])
    if L < D_vn:
        raise ValueError(f"Полудлина тройника должна быть не менее {D_vn} мм!")
    R_1_n = class_data[steel_class][0][0]
    sigma_b = R_1_n
    sigma_y = class_data[steel_class][1]
    m = 0.825 if pressure <= 10 else 0.66
    k_1 = 1.47
    n = 1.1

    k_n_key_d = min((d for d in k_n_values if D_N_b <= d), default=None)
    if k_n_key_d is None:
        raise ValueError(f"Номинальный диаметр '{D_N_b}' не найден в таблице.")
    temp_data = k_n_values[k_n_key_d]
    k_n_key_p = min((p for p in temp_data if pressure <= p), default=None)
    if k_n_key_p is None:
        raise ValueError(f"Нет К1 для давления '{pressure}' МПа.")
    k_n = temp_data[k_n_key_p]

    R_1 = round(R_1_n * m / k_1 / k_n, 1)

    sigma_pipeline = math.ceil(n * pressure * D_n / (2 * (R_1 + n * pressure)))

    D_h = D_n + 2 * sigma_pipeline
    D_b = D_vn + 2 * sigma_pipeline

    t_h = math.ceil(n * pressure * D_h / (2 * (R_1 + n * pressure)))
    t_b = math.ceil(n * pressure * D_b / (2 * (R_1 + n * pressure)))

    m_b = 1  # При условии, что КП одинаковые у тройника и трубопровода
    ksi = L / D_vn
    E = 0.45 + 0.55 * D_b / D_h
    counter = 0
    for i in range(max_iter):
        counter += 1
        a = (2 + 5 * m_b - 4 * ksi) * E * t_h
        b = (2 * ksi - 1) * D_b + 4 * ksi * E * t_h - 5 * m_b * t_b
        c = -2 * ksi * D_b

        nu = (1 / (2 * a)) * (-b + math.sqrt(b**2 - 4 * a * c))
        nu = max(nu, 1.0)

        T_h_new = 6.0
        T_b_new = 6.0

        if math.ceil(t_h * nu) > 6.0:
            T_h_new = math.ceil(t_h * nu)

        if math.ceil(E * T_h_new) > 6.0:
            T_b_new = math.ceil(E * T_h_new)

        if T_h_new == t_h and T_b_new == t_b:
            break

        T_h, T_b = T_h_new, T_b_new

        D_h = D_n + 2 * T_h
        D_b = D_vn + 2 * T_b

        t_h = math.ceil(n * pressure * D_h / (2 * (R_1 + n * pressure)))
        t_b = math.ceil(n * pressure * D_b / (2 * (R_1 + n * pressure)))

        E = 0.45 + 0.55 * D_b / D_h
    print(counter)
    H_1 = 2.5 * T_h
    H_min = 0.5 * D_h + H_1

    d_h = D_h - 2 * T_h
    d_b = D_b - 2 * T_b

    A = d_b * t_h
    A1 = (2 * L - d_b) * (T_h - t_h)
    A2 = 2 * H_1 * (T_b - t_b)

    L_min = max(d_b, 0.5 * D_b + 2 * T_h)

    is_area = True if A1 + m_b * A2 >= A else False
    is_thickness = True if T_b >= 6.0 and T_h >= 1.5 * sigma_pipeline else False
    is_length = True if L >= d_b and L >= 0.5 * D_b + 2 * T_h else False

    if is_area and is_thickness and is_length:
        result = {
            "steel_class": steel_class,
            "sigma_b": sigma_b,
            "sigma_y": sigma_y,
            "pressure": pressure,
            "temperature": temperature,
            "D_n": D_n - 4,
            "D_h": D_h,
            "D_b": D_b,
            "T_h": T_h,
            "T_b": T_b,
            "d_h": d_h,
            "d_b": d_b,
            "H_min": H_min,
            "L_min": L_min,
            "D_N_b": D_N_b,
            "D_vn": D_vn,
            "D_N_pipe": D_N_pipe,
            "m": m,
            "n": n,
            "k_1": k_1,
            "k_n": k_n,
            "m_b": m_b,
            "L": L,
        }
        return result
    else:
        raise ValueError(f"Условия площади, толщины, длины: '{is_area, is_thickness, is_length}'.")


def print_result(result):
    print("=== Результаты расчета ===")
    print(f"Класс прочности стали                      : {result['steel_class']}")
    print(f"Давление                                   : {result['pressure']} МПа")
    print(f"Температура                                : {result['temperature']} С")
    print(f"Наружный диаметр трубопровода              : {result['D_n']}")
    print(f"Наружный диаметр магистральной части   D_h : {result['D_h']:.1f} мм")
    print(f"Наружный диаметр ответвления D_b           : {result['D_b']:.1f} мм")
    print(f"Толщина стенки магистральной части T_h     : {result['T_h']} мм")
    print(f"Толщина стенки ответвления T_b             : {result['T_b']} мм")
    print(f"Внутренний диаметр магистральной части d_h : {result['d_h']:.1f} мм")
    print(f"Внутренний диаметр ответвления d_b         : {result['d_b']:.1f} мм")
    print(f"Минимальная высота H_min                   : {result['H_min']:.1f} мм")
    print(f"Минимальная длина L_min                    : {result['L_min']:.1f} мм")
    print("=============================")






