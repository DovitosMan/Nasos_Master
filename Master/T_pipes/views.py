import math
from types import SimpleNamespace
from django.shortcuts import render
import bisect
from Flanges_calculations.steel_prop_data import strength_data_1, yield_data_1, E_modulus_data_1, alpha_data_1
from .data import class_data, k_n_values
from .report_doc import generate_report


def t_pipes(request):
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Условный диаметр трубопровода DN, мм', 'name': 'D_N_pipe', 'value': '',
             'max': 1400, 'min': 10},
            {'type': 'float', 'placeholder': 'Условный диаметр ответвления тройника DN, мм', 'name': 'D_N_b',
             'value': '', 'max': 1400, 'min': 10},
            {'type': 'float', 'placeholder': 'Рабочее давление, P, МПа', 'name': 'pressure', 'value': '', 'max': 32.0,
             'min': 0.1},
            {'type': 'float', 'placeholder': 'Температура эксплуатации C', 'name': 'temperature', 'value': '',
             'max': 380, 'min': 21},
            {'type': 'float', 'placeholder': 'Наружный диаметр трубопровода Dn, мм', 'name': 'D_n', 'value': '',
             'max': 1400, 'min': 10},
            {'type': 'float', 'placeholder': 'Внутренний диаметр ответвления Db, мм', 'name': 'D_vn', 'value': '',
             'max': 1400, 'min': 10},
            {'type': 'float', 'placeholder': 'Полудлина тройника L, мм', 'name': 'L', 'value': '',
             'max': 2000, 'min': 10},
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
                 {'name': "12Х18Н10Т", 'value': "12Х18Н10Т"},
                 {'name': "ХН35ВТ", 'value': "ХН35ВТ"},
                 {'name': "09Г2С", 'value': "09Г2С"},
                 {'name': "17Г1С", 'value': "17Г1С"},
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


def _ensure_float_attr(d: SimpleNamespace, name: str):
    val = getattr(d, name, None)
    try:
        return float(val)
    except (TypeError, ValueError):
        raise ValueError(f"Поле '{name}' должно быть числом (значение: {val!r})")


def get_steel_class(steel_grade: str, temperature: float):

    steel_prop = get_steel_prop(steel_grade, temperature)
    print(steel_prop)
    sp = SimpleNamespace(**steel_prop)

    if sp.sigma_b_T == 0:
        raise ValueError(f"sigma_b_T == 0 для марки {steel_grade} при T={temperature}°C — проверь таблицу свойств")

    div = sp.sigma_y_T / sp.sigma_b_T

    best_class = None
    best_sigma_y_min = -1

    for steel_class, (sigma_b_range, sigma_y_min, max_ratio) in class_data.items():
        sigma_b_min, sigma_b_max = sigma_b_range
        if (sigma_b_min <= sp.sigma_b_T <= sigma_b_max and
                sp.sigma_y_T >= sigma_y_min and
                div <= max_ratio):
            if sigma_y_min > best_sigma_y_min:
                best_sigma_y_min = sigma_y_min
                best_class = steel_class

    return best_class


def get_steel_prop(steel_grade: str, temperature: float):
    steel_grade = str(steel_grade).strip()
    properties = [
        ("E", E_modulus_data_1, 1e5, 0),
        ("alpha", alpha_data_1, 1e-6, 8),
        ("sigma_b", strength_data_1, 1.0, 3),
        ("sigma_y", yield_data_1, 1.0, 3)
    ]
    results = {}
    for name, table, scale, round_digits in properties:
        if steel_grade not in table:
            raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице свойств ({name}).")
        data = table[steel_grade]

        if 20 not in data:
            raise ValueError(f"Для марки '{steel_grade}' в таблице '{name}' отсутствует значение при 20°C.")

        val20 = round(data[20] * scale, round_digits)

        if temperature in data:
            valT = data[temperature] * scale
        else:
            temps = sorted(k for k in data.keys() if isinstance(k, (int, float)))
            if not temps:
                raise ValueError(f"Нет температурных записей для марки {steel_grade} в таблице {name}.")
            if temperature < temps[0] or temperature > temps[-1]:
                raise ValueError(
                    f"Температура {temperature}°C вне диапазона данных для {steel_grade} ({name}). "
                    f"Допустимый диапазон: {temps[0]}..{temps[-1]} °C."
                )
            pos = bisect.bisect_left(temps, temperature)
            t1, t2 = temps[pos - 1], temps[pos]
            v1, v2 = data[t1], data[t2]
            valT = round((v1 + (v2 - v1) * (temperature - t1) / (t2 - t1)) * scale, round_digits)

        results[f"{name}_20"] = val20
        results[f"{name}_T"] = valT

    return results


def calc(input_data, input_select, max_iter=100):
    all_data = {**input_data, **input_select}
    d = SimpleNamespace(**all_data)

    req_numeric = ["D_N_pipe", "D_N_b", "pressure", "temperature", "D_n", "D_vn", "L"]
    for name in req_numeric:
        setattr(d, name, _ensure_float_attr(d, name))

    steel_grade = getattr(d, "steel_grade", None)
    if not steel_grade:
        raise ValueError("Не указана марка стали (steel_grade).")

    steel_class = get_steel_class(steel_grade, d.temperature)
    if steel_class is None:
        raise ValueError(
            f"Для стали '{steel_grade}' при температуре {d.temperature}°C не найден подходящий класс прочности."
        )

    if d.L < d.D_vn:
        raise ValueError(f"Полудлина тройника должна быть не менее {d.D_vn} мм!")
    R_1_n = class_data[steel_class][0][0]
    sigma_b = R_1_n
    sigma_y = class_data[steel_class][1]
    m = 0.825 if d.pressure <= 10 else 0.66
    k_1 = 1.47
    n = 1.1

    k_n = None
    for diameter_limit in sorted(k_n_values.keys()):
        if d.D_N_b <= diameter_limit:
            pressures = k_n_values[diameter_limit]
            for pressure_limit in sorted(pressures.keys()):
                if d.pressure <= pressure_limit:
                    k_n = pressures[pressure_limit]
                    break
            if k_n is not None:
                break
    if k_n is None:
        raise ValueError(f"Не удалось определить коэффициент k_n для D_N_b={d.D_N_b}, P={d.pressure}")

    if k_n == 0:
        raise ValueError("k_n = 0 в таблице — проверь данные k_n_values.")

    R_1 = round(R_1_n * m / k_1 / k_n, 1)

    deno = (R_1 + n * d.pressure)
    if deno == 0:
        raise ValueError(f"Некорректная промежуточная величина (R_1 + n*P) == 0 (R_1={R_1}, P={d.pressure})")

    sigma_pipeline = round((n * d.pressure * d.D_n / (2 * deno)), 2)

    if d.D_N_pipe < 1000:
        D_n_ = d.D_n + 4.0
    else:
        D_n_ = d.D_n + 6.0

    D_h = D_n_ + 2 * sigma_pipeline
    D_b = d.D_vn + 2 * sigma_pipeline

    t_h = round((n * d.pressure * D_h / (2 * deno)), 2)
    t_b = round((n * d.pressure * D_b / (2 * deno)), 2)

    T_h, T_b = None, None

    m_b = 1  # При условии, что КП одинаковые у тройника и трубопровода
    ksi = d.L / d.D_vn
    E = 0.45 + 0.55 * D_b / D_h
    counter = 0
    for iteration in range(max_iter):
        counter += 1
        a = (2 + 5 * m_b - 4 * ksi) * E * t_h
        b = (2 * ksi - 1) * D_b + 4 * ksi * E * t_h - 5 * m_b * t_b
        c = -2 * ksi * D_b

        if a == 0:
            raise ValueError(f"Невозможно вычислить ν: коэффициент a == 0 (a={a}). Проверь входные данные.")

        discriminant = b ** 2 - 4 * a * c
        if discriminant < 0:
            raise ValueError(
                f"Невозможно вычислить коэффициент ν: дискриминант < 0 "
                f"(D_h={D_h}, D_b={D_b}, t_h={t_h}, t_b={t_b})"
            )

        nu = (-b + math.sqrt(discriminant)) / (2 * a)
        nu = max(nu, 1.0)

        T_h_new = max(6.0, math.ceil(t_h * nu))
        T_b_new = max(6.0, math.ceil(E * T_h_new))

        if T_h_new == T_h and T_b_new == T_b:
            break

        T_h, T_b = T_h_new, T_b_new
        D_h = D_n_ + 2 * T_h
        D_b = d.D_vn + 2 * T_b

        t_h = math.ceil(n * d.pressure * D_h / (2 * (R_1 + n * d.pressure)))
        t_b = math.ceil(n * d.pressure * D_b / (2 * (R_1 + n * d.pressure)))

        E = 0.45 + 0.55 * D_b / D_h
    print(f"Сошлось за {counter} итераций")
    H_1 = 2.5 * T_h
    H_min = 0.5 * D_h + H_1

    d_h = D_h - 2 * T_h
    d_b = D_b - 2 * T_b

    t_h = round((n * d.pressure * D_h / (2 * deno)), 2)
    t_b = round((n * d.pressure * D_b / (2 * deno)), 2)

    A = d_b * t_h
    A1 = (2 * d.L - d_b) * (T_h - t_h)
    A2 = 2 * H_1 * (T_b - t_b)
    print(A, A1, A2)

    L_min = max(d_b, 0.5 * D_b + 2 * T_h)

    is_area = A1 + m_b * A2 >= A
    is_thickness = (T_b >= 6.0) and (T_h >= 1.5 * sigma_pipeline)
    is_length = (d.L >= d_b) and (d.L >= 0.5 * D_b + 2 * T_h)

    if is_area and is_thickness and is_length:
        result = {
            "steel_class": steel_class,
            "sigma_b": sigma_b,
            "sigma_y": sigma_y,
            "pressure": d.pressure,
            "temperature": d.temperature,
            "D_n": d.D_n,
            "D_h": D_h,
            "D_b": D_b,
            "T_h": T_h,
            "T_b": T_b,
            "d_h": d_h,
            "d_b": d_b,
            "H_min": H_min,
            "L_min": L_min,
            "D_N_b": d.D_N_b,
            "D_vn": d.D_vn,
            "D_N_pipe": d.D_N_pipe,
            "m": m,
            "n": n,
            "k_1": k_1,
            "k_n": k_n,
            "m_b": m_b,
            "L": d.L,
        }
        return result
    else:
        raise ValueError(f"Условия (площадь, толщина, длина) не выполнены: {is_area, is_thickness, is_length}")


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






