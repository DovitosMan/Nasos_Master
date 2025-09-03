import itertools
import math
import numpy as np
from tqdm import tqdm
import pandas as pd

from django.shortcuts import render
import bisect
from .gasket_data import (table_15180, table_34655, table_iso_7483,
                          GASKET_SIZES_15180, GASKET_SIZES_34655,
                          GASKET_SIZES_ISO_7483, gasket_params, gasket_type_map)
from .bolt_data import bolt_areas, bolts_data, nuts_data, washer_data
from .steel_prop_data import E_modulus_data, alpha_data, strength_data, yield_data, allowed_flange_data
from .graphs_data import (x_values_B_F, x_values_B_V, x_values_f,
                          B_F_values, B_V_values, f_values)
from .report import generate_report


def flanges_calculations(request):
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Условный диаметр DN, мм', 'name': 'D_N_flange', 'value': '', 'max': 1400,
             'min': 10},
            {'type': 'float', 'placeholder': 'Рабочее давление, P, МПа', 'name': 'pressure', 'value': '', 'max': 32.0,
             'min': 0.1},
            {'type': 'float', 'placeholder': 'Температура эксплуатации C', 'name': 'temperature', 'value': '',
             'max': 380, 'min': -50},
            {'type': 'float', 'placeholder': 'Срок эксплуатации, лет', 'name': 'operating_time', 'value': '',
             'max': 15, 'min': 1},
            {'type': 'float', 'placeholder': 'Наружный диаметр фланца Dн, мм', 'name': 'D_ext_flange', 'value': '',
             'min': 1},
            {'type': 'float', 'placeholder': 'Внутренний диаметр фланца D, мм', 'name': 'D_int_flange', 'value': '',
             'min': 1},
            {'type': 'float', 'placeholder': 'Ширина тарелки фланца h, мм', 'name': 'h_flange', 'value': '', 'min': 1},
            {'type': 'float', 'placeholder': 'Полная высота фланца, H, мм', 'name': 'H_flange', 'value': '', 'min': 1},
            {'type': 'float', 'placeholder': 'Диаметр втулки в месте приварки Dn, мм', 'name': 'D_n_flange',
             'value': '', 'min': 0},
            {'type': 'float', 'placeholder': 'Диаметр втулки в месте присоединения тарелки Dm, мм',
             'name': 'D_m_flange', 'value': '', 'min': 0},
            {'type': 'float', 'placeholder': 'Скругление между втулкой и тарелкой r, мм',
             'name': 'r', 'value': '', 'min': 0},
            {'type': 'float', 'placeholder': 'Диаметр окружности расположения болтов (шпилек), мм',
             'name': 'd_pins_flange', 'value': '', 'min': 1},
            {'type': 'float', 'placeholder': 'Число болтов (шпилек) n, шт.', 'name': 'pins_quantity', 'value': '',
             'max': 50, 'min': 1},
            {'type': 'float', 'placeholder': 'Диаметр болта (шпильки) М', 'name': 'pin_diam', 'value': '', 'max': 68,
             'min': 10},
            {'type': 'float', 'placeholder': 'Внешняя нагрузка F, кН', 'name': 'ext_force', 'value': ''},
            {'type': 'float', 'placeholder': 'Внешний момент M, кН*м', 'name': 'ext_moment', 'value': ''},
            {'type': 'float', 'placeholder': 'Толщина стенки ответвления тройника', 'name': 'T_b', 'value': ''},
        ],
        'selects': [
            {'type': 'option', 'placeholder': 'Тип фланца', 'name': 'flange_type', 'value': '',
             'keys': [
                 {'name': '01 - плоский приварной', 'value': 'zero_one'},
                 # {'name': '02 - плоский свободный на приварном кольце', 'value': 'zero_two'},
                 # {'name': '03 - плоский свободный на отбортовке', 'value': 'zero_three'},
                 # {'name': '04 - плоский свободный на хомуте под приварку', 'value': 'zero_four'},
                 {'name': '11 - приварной встык', 'value': 'one_one'},
                 # {'name': '21 - корпуса арматуры', 'value': 'two_one'},
             ],
             },
            {'type': 'option', 'placeholder': 'Тип уплотнительной поверхности', 'name': 'face_type', 'value': '',
             'keys': [
                 {'name': '1 (B)', 'value': 'B'},
                 {'name': '2 (E)', 'value': 'E'},
                 {'name': '3 (F)', 'value': 'F'},
                 {'name': '4 (C, L)', 'value': 'C_L'},
                 {'name': '5 (D, M)', 'value': 'D_M'},
                 {'name': '6 (J)', 'value': 'J'},
                 {'name': '7 (K)', 'value': 'K'},
             ],
             },
            {'type': 'option', 'placeholder': 'Марка стали фланцев', 'name': 'flange_steel', 'value': '',
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
                 # {'name': "Д16", 'value': "Д16"},
             ],
             },
            {'type': 'option', 'placeholder': 'Марка стали болтов (шпилек)', 'name': 'bolt_steel', 'value': '',
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
                 # {'name': "Д16", 'value': "Д16"},
             ],
             },
        ]
    }
    if request.method == "POST":

        input_data = {}
        input_select = {}
        input_select_names = []

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
            displayed_name = next(
                (item['name'] for item in select['keys'] if item['value'] == raw), raw)
            input_select_names.append(displayed_name)

        # multi_calc(input_data, input_select)

        result, T_b = solo_calc(input_data, input_select)
        generate_report(result, T_b, input_select_names)

    return render(request, 'flanges.html', context)


def multi_calc(input_data, input_select):
    D_N_flange = float(input_data['D_N_flange'])
    pressure = float(input_data['pressure'])
    temperature = float(input_data['temperature'])
    # D_ext_flange = float(input_data['D_ext_flange'])
    D_int_flange = float(input_data['D_int_flange'])
    # h_flange = float(input_data['h_flange'])
    # H_flange = float(input_data['H_flange'])
    #
    # D_n_flange = float(input_data['D_n_flange'])
    # D_m_flange = float(input_data['D_m_flange'])

    r = float(input_data['r'])

    # d_pins_flange = float(input_data['d_pins_flange'])
    # pins_quantity = float(input_data['pins_quantity'])
    # pin_diam = float(input_data['pin_diam'])

    ext_force = float(input_data['ext_force'])
    ext_moment = float(input_data['ext_moment'])
    operating_time = input_data['operating_time']

    num_cycles_c = 200
    num_cycles_r = 40_000

    flange_type = input_select['flange_type']
    face_type = input_select['face_type']
    # flange_steel = input_select['flange_steel']
    # bolt_steel = input_select['bolt_steel']

    filename = "flange_results.xlsx"
    all_results = []

    steel_flange_range = ["40Х", "25Х1МФ", "20Х13", "12Х18Н10Т"]
    steel_bolt_range = ["40Х", "25Х1МФ", "20Х13", "12Х18Н10Т"]
    # steel_flange_range = ["25Х1МФ", "20Х13", "12Х18Н10Т"]
    # steel_bolt_range = ["25Х1МФ", "20Х13", "12Х18Н10Т"]

    D_ext_flange_range = sorted(set(
        [x for x in np.arange(1100, 1301, 50)]
    ))
    D_n_flange_range = sorted(set(
        [x for x in np.arange(800, 951, 25)]
    ))
    D_m_flange_range = sorted(set(
        [x for x in np.arange(800, 951, 25)]
    ))
    h_flange_range = sorted(set(
        [x for x in np.arange(100, 151, 10)]
    ))
    H_flange_range = sorted(set(
        [x for x in np.arange(210, 251, 20)]
    ))
    d_pins_flange_range = sorted(set(
        [x for x in np.arange(870, 971, 20)]
    ))

    pin_diam_range = [52, 56]
    pins_quantity_data = range(24, 28, 2)

    combinations = list(itertools.product(steel_flange_range, steel_bolt_range, D_ext_flange_range, D_n_flange_range, D_m_flange_range, h_flange_range, H_flange_range, pin_diam_range, d_pins_flange_range, pins_quantity_data))
    for flange_steel, bolt_steel, D_ext_flange, D_n_flange, D_m_flange, h_flange, H_flange, pin_diam, d_pins_flange, pins_quantity in tqdm(combinations, desc="Перебор параметров", total=len(combinations)):
        # print(f"Перебираю: {flange_steel}, {bolt_steel}, {D_ext_flange}, {D_n_flange}, {D_m_flange}, {h_flange}, {H_flange}, {pin_diam}, {d_pins_flange}, {pins_quantity}")
        s0 = (D_n_flange - D_int_flange) / 2
        s1 = (D_m_flange - D_int_flange) / 2

        continue_calc = (
                ((D_ext_flange / D_int_flange) <= 5.0) and
                ((2 * h_flange / (D_ext_flange - D_int_flange)) >= 0.25) and
                (((s1 - s0) / (H_flange - h_flange)) <= 0.4)
        )
        if ((s1 - s0) / (H_flange - h_flange)) >= 0.33:
            if D_m_flange != D_n_flange:
                continue_calc = False
                # print('Втулка должна быть цилиндрической!')
            if H_flange - h_flange < 1.5 * s0:
                continue_calc = False
                # print(f"Длина втулки не менее 1.5 * {s0} = {1.5 * s0}")
        # print('Условие применимости расчета 1: ', (D_ext_flange / D_int_flange), ' <= ', 5.0)
        # print('Условие применимости расчета 2: ', (2 * h_flange / (D_ext_flange - D_int_flange)), ' >= ', 0.25)
        # print('Условие применимости расчета 3: ', ((s1 - s0) / (H_flange - h_flange)), ' <= ', 0.4)
        # print()
        if continue_calc:
            try:
                gasket_params = get_gasket(pressure, D_N_flange, face_type)
                # print(gasket_params)
                document = gasket_params.get("document", "")
                gasket_type = str(gasket_params.get("type", ""))
                D_gasket = gasket_params.get("D_outer")
                d_gasket = gasket_params.get("d_inner")
                q_obj = gasket_params.get("q_obj")
                m = gasket_params.get("m")
                K_obj = gasket_params.get("K_obj")
                gasket_thickness = gasket_params.get("thickness")
                gasket_material = gasket_params.get('material')
                E_p = gasket_params.get("E_p")
                q_obj_dop = gasket_params.get("q_obj_dop")

                shape = gasket_type_map.get((document, gasket_type)) or gasket_type_map.get(document)
                if shape is None:
                    raise ValueError("Пока что нет данных по прокладкам для продолжения расчета в таких условиях")

                gasket_width = (D_gasket - d_gasket) / 2
                calc_funcs = {
                    'ring': lambda gw, Dg: (gw if gw <= 15.0 else round(3.8 * math.sqrt(gw), 1),
                                            Dg - (gw if gw <= 15.0 else round(3.8 * math.sqrt(gw), 1))),
                    'octagon': lambda gw, Dg: (round(gw / 4, 1), Dg - gw),
                    'oval': lambda gw, Dg: (round(gw / 4, 1), Dg - gw),
                }

                gasket_eff_width, gasket_cal_diam = calc_funcs[shape](gasket_width, D_gasket)

                P_obj = round(0.5 * math.pi * gasket_cal_diam * gasket_eff_width * q_obj / 1000, 3)
                R_p = round(math.pi * gasket_cal_diam * gasket_eff_width * m * pressure / 1000, 3)

                bolt_area, bolts_area, stud_length, bolt_type, fasteners_data = get_bolt_area_and_size(pin_diam,
                                                                                                       pins_quantity,
                                                                                                       pressure,
                                                                                                       h_flange)  # 6.1

                Q_d = round(0.785 * gasket_cal_diam ** 2 * pressure / 1000, 3)

                Q_F_M = round(max(ext_force + 4 * abs(ext_moment) / gasket_cal_diam,
                                  ext_force - 4 * abs(ext_moment) / gasket_cal_diam), 3)

                (E_bolt_20, E_bolt_T, alpha_bolt_20, alpha_bolt_T,
                 sigma_b_bolt_20, sigma_b_bolt_T, sigma_y_bolt_20, sigma_y_bolt_T) = (
                    get_steel_prop(bolt_steel, temperature))

                (E_flange_20, E_flange_T, alpha_flange_20, alpha_flange_T,
                 sigma_b_flange_20, sigma_b_flange_T, sigma_y_flange_20, sigma_y_flange_T) = (
                    get_steel_prop(flange_steel, temperature))

                f, b, e, gamma, alpha, alpha_m, C_F, D_priv_flange, lambda_, l_0, B_F, B_Y, B_Z, y_flange, B_V, x, B, koef_B_x, s_e = (
                    get_hardness_flanges(flange_type, d_pins_flange, gasket_cal_diam, s0, D_int_flange,
                                         K_obj, gasket_thickness, gasket_material, E_p, gasket_width, pin_diam,
                                         pins_quantity, pressure, h_flange, bolt_steel, temperature, D_ext_flange,
                                         s1, H_flange, flange_steel, D_n_flange, m))

                Q_t = gamma * (alpha_flange_T * h_flange * (0.96 * temperature - 20) +
                               alpha_flange_T * h_flange * (0.96 * temperature - 20) -
                               alpha_bolt_T * (h_flange + h_flange) * (0.95 * temperature - 20)) / 1000
                P_b_1 = max(
                    alpha * (Q_d + ext_force) + R_p + 4 * alpha_m * abs(ext_moment) / gasket_cal_diam,
                    alpha * (Q_d + ext_force) + R_p + 4 * alpha_m * abs(ext_moment) / gasket_cal_diam - Q_t
                )

                allowed_stress_b_m, allowed_stress_b_r, n_T_b = get_allowed_stress_bolt(bolt_steel, temperature)
                allowed_stress_flange_m, allowed_stress_flange_r, allowed_stress_flange_T = (
                    get_allowed_stress_flange(flange_steel, temperature))

                P_b_2 = max(
                    P_obj,
                    0.4 * bolts_area * max(allowed_stress_b_m, allowed_stress_b_r) / 1000
                )

                P_b_m = round(max(P_b_1, P_b_2), 3)
                P_b_r = round(
                    P_b_m + (1 - alpha) * (Q_d + ext_force) + Q_t + 4 * (1 - alpha_m) * abs(ext_moment) / gasket_cal_diam,
                    3)

                c_flange, c_bolt = get_corrosion_thickness(operating_time, flange_steel, bolt_steel)
                bolt_corrosion_diam = math.sqrt(4 * bolt_area / math.pi) - 2 * c_bolt
                bolt_corrosion_area = math.pi * bolt_corrosion_diam ** 2 / 4
                bolts_corrosion_area = pins_quantity * bolt_corrosion_area

                stress_b_1 = P_b_m * 1000 / bolts_corrosion_area
                stress_b_2 = P_b_r * 1000 / bolts_corrosion_area

                q = max(P_b_m, P_b_r) * 1000 / (math.pi * gasket_cal_diam * gasket_width)

                is_bolt_true = False
                is_gasket_true = False

                if stress_b_1 <= allowed_stress_b_m and stress_b_2 <= allowed_stress_b_r:
                    is_bolt_true = True
                    # print('Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m)
                    # print('Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r)
                    # print(f"Шпильки типа {bolt_type} удовлетворяют условиям прочности")
                    # print()
                else:
                    a = 1
                    # print(f"Шпильки типа {bolt_type} НЕ удовлетворяют условиям прочности!!!")
                    # print()
                if document == 'ГОСТ 15180-86':
                    if q <= q_obj_dop:
                        is_gasket_true = True
                        # print('Прокладка: ', q, ' <= ', q_obj_dop)
                        # print(f"Прокладка типа {gasket_type} по {document} удовлетворяет условию прочности")
                        # print()
                    else:
                        a = 1
                        # print('Прокладка: ', q, ' <= ', q_obj_dop)
                        # print(f"Прокладка типа {gasket_type} по {document} НЕ удовлетворяет условию прочности!!!")
                        # print()
                else:
                    is_gasket_true = True
                    a = 1
                    # print("Для стальных прокладок условие прочности не проверяется.")

                if is_bolt_true and is_gasket_true:
                    M_M = C_F * P_b_m * b / 1000
                    M_R = C_F * max(
                        P_b_r * b / 1000 + (Q_d + Q_F_M) * e / 1000,
                        abs(Q_d + Q_F_M) * e / 1000
                    )
                    stress_M_1 = None
                    stress_M_0 = None

                    if flange_type in ('zero_one', 'one_one'):
                        if flange_type == 'one_one':
                            stress_M_1 = M_M * 1e6 / (lambda_ * (s1 - c_flange) ** 2 * D_priv_flange)
                            stress_M_0 = f * stress_M_1
                        elif flange_type == 'zero_one':
                            stress_M_0 = stress_M_1 = M_M / (lambda_ * (s0 - c_flange) ** 2 * D_priv_flange)
                    else:
                        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                    stress_M_R = (1.33 * B_F * h_flange + l_0) * M_M * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
                    stress_M_T = B_Y * M_M * 1e6 / (h_flange ** 2 * D_int_flange) - B_Z * stress_M_R

                    stress_R_1 = None
                    stress_R_0 = None

                    if flange_type in ('zero_one', 'one_one'):
                        if flange_type == 'one_one':
                            stress_R_1 = M_R * 1e6 / (lambda_ * (s1 - c_flange) ** 2 * D_priv_flange)
                            stress_R_0 = f * stress_R_1
                        elif flange_type == 'zero_one':
                            stress_R_0 = stress_R_1 = M_R * 1e6 / (lambda_ * (s0 - c_flange) ** 2 * D_priv_flange)
                    else:
                        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                    stress_1MM_R = max(
                        (Q_d + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                                math.pi * (D_int_flange + s1) * (s1 - c_flange)),
                        (Q_d + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                                math.pi * (D_int_flange + s1) * (s1 - c_flange))
                    )

                    stress_0MM_R = max(
                        (Q_d + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                                math.pi * (D_int_flange + s0) * (s0 - c_flange)),
                        (Q_d + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                                math.pi * (D_int_flange + s0) * (s0 - c_flange))
                    )

                    stress_0MO_R = pressure * D_int_flange / (2 * (s0 - c_flange))

                    stress_R_R = (1.33 * B_F * h_flange + l_0) * M_R * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
                    stress_R_T = B_Y * M_R * 1e6 / (h_flange ** 2 * D_int_flange) - B_Z * stress_R_R

                    condition_43 = (max(
                        abs(stress_M_1 + stress_M_R),
                        abs(stress_M_1 + stress_M_T)
                    ))
                    # print('Условие (43): ', condition_43, ' <= ', 1.3 * allowed_stress_flange_m)

                    condition_44 = (max(
                        abs(stress_R_1 - stress_1MM_R + stress_R_R),
                        abs(stress_R_1 - stress_1MM_R + stress_R_T),
                        abs(stress_R_1 + stress_1MM_R)
                    ))
                    # print('Условие (44): ', condition_44, ' <= ', 1.3 * allowed_stress_flange_m)

                    condition_45 = stress_M_0
                    # print('Условие (45): ', condition_45, ' <= ', 1.3 * allowed_stress_flange_r)

                    condition_46 = (max(
                        abs(max(stress_R_0 + stress_0MM_R, stress_R_0 - stress_0MM_R)),
                        abs(max(0.3 * stress_R_0 + stress_0MO_R, 0.3 * stress_R_0 - stress_0MO_R)),
                        abs(max(0.7 * stress_R_0 + (stress_0MM_R - stress_0MO_R),
                                0.7 * stress_R_0 - (stress_0MM_R - stress_0MO_R)))
                    ))
                    # print('Условие (46): ', condition_46, ' <= ', 1.3 * allowed_stress_flange_r)

                    condition_47 = (max(
                        abs(stress_M_0 + stress_M_R),
                        abs(stress_M_0 + stress_M_T)
                    ))
                    # print('Условие (47): ', condition_47, ' <= ', 1.3 * allowed_stress_flange_m)

                    condition_48 = (max(
                        abs(stress_R_0 - stress_0MM_R + stress_R_T),
                        abs(stress_R_0 - stress_0MM_R + stress_R_R),
                        abs(stress_R_0 + stress_0MM_R)
                    ))
                    # print('Условие (48): ', condition_48, ' <= ', 1.3 * allowed_stress_flange_m)

                    condition_53 = (max(stress_0MO_R, stress_0MM_R))
                    # print('Условие (53): ', condition_53, ' <= ', min(allowed_stress_flange_m, allowed_stress_flange_r))

                    condition_54 = max(stress_M_R, stress_M_T)
                    # print('Условие (54): ', condition_54, ' <= ', min(allowed_stress_flange_m, allowed_stress_flange_r))

                    condition_55 = max(stress_R_R, stress_R_T)
                    # print('Условие (55): ', condition_55, ' <= ', min(allowed_stress_flange_m, allowed_stress_flange_r))
                    # print()

                    is_flange_11_true = False
                    is_flange_01_true = False

                    if flange_type in ('zero_one', 'one_one'):
                        if flange_type == 'one_one':
                            if (
                                    condition_43 <= 1.3 * allowed_stress_flange_m and
                                    condition_44 <= 1.3 * allowed_stress_flange_m and
                                    condition_45 <= 1.3 * allowed_stress_flange_r and
                                    condition_46 <= 1.3 * allowed_stress_flange_r and
                                    condition_53 <= min(allowed_stress_flange_m, allowed_stress_flange_r)
                            ):
                                # print(f'Фланец типа {flange_type} проверку статической прочности прошел')
                                # print()
                                is_flange_11_true = True
                            else:
                                a = 1
                                # print(f'Фланец типа {flange_type} проверку статической прочности НЕ прошел!!!')
                                # print()
                        elif flange_type == 'zero_one':
                            if (
                                    condition_47 <= 1.3 * allowed_stress_flange_m and
                                    condition_48 <= 1.3 * allowed_stress_flange_m and
                                    condition_53 <= min(allowed_stress_flange_m, allowed_stress_flange_r) and
                                    condition_54 <= min(allowed_stress_flange_m, allowed_stress_flange_r) and
                                    condition_55 <= min(allowed_stress_flange_m, allowed_stress_flange_r)
                            ):
                                # print(f'Фланец типа {flange_type} проверку статической прочности прошел')
                                # print()
                                is_flange_01_true = True
                            else:
                                a = 1
                                # print(f'Фланец типа {flange_type} проверку статической прочности НЕ прошел!!!')
                                # print()
                    else:
                        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                    if is_flange_01_true or is_flange_11_true:
                        theta = M_R * y_flange * E_flange_20 / E_flange_T
                        if flange_type in ('zero_one', 'one_one'):
                            if flange_type == 'one_one':
                                if D_int_flange <= 400:
                                    allowed_theta = 0.006
                                elif D_int_flange >= 2000:
                                    allowed_theta = 0.013
                                else:
                                    D_int_flange_1 = 400
                                    D_int_flange_2 = 2000
                                    allowed_theta_1 = 0.006
                                    allowed_theta_2 = 0.013
                                    allowed_theta = (allowed_theta_1 + (allowed_theta_2 - allowed_theta_1) *
                                                     (D_int_flange - D_int_flange_1) / (D_int_flange_2 - D_int_flange_1))
                            elif flange_type == 'zero_one':
                                allowed_theta = 0.013
                            else:
                                raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                            if theta <= allowed_theta:
                                a = 1
                                # print(f'Фланец типа {flange_type} проверку углов поворота при затяжке и раб. усл. прошел')
                                # print()
                            else:
                                a = 1
                                # print(f'Фланец типа {flange_type} проверку углов поворота при затяжке и раб. усл. НЕ '
                                      # f'прошел!!!')
                                # print()

                        #  Приварные с конической втулкой
                        stress_M_1_1 = stress_M_1
                        stress_M_1_2 = -stress_M_1
                        stress_M_1_3 = stress_M_1_4 = stress_M_T
                        stress_M_1_5 = stress_M_1_6 = stress_M_R

                        #  Приварные и плоские
                        stress_M_0_1 = stress_M_0
                        stress_M_0_2 = -stress_M_0

                        #  Плоские и приварные с прямой втулкой
                        stress_M_0_3 = stress_M_0_4 = stress_M_T
                        stress_M_0_5 = stress_M_0_6 = stress_M_R

                        if flange_type == 'one_one':
                            stress_R_0_3 = stress_0MO_R + 0.3 * stress_R_0
                            stress_delta_R_0_3 = stress_0MO_R - 0.3 * stress_R_0
                            stress_R_0_4 = stress_0MO_R - 0.3 * stress_R_0
                            stress_delta_R_0_4 = stress_0MO_R + 0.3 * stress_R_0
                        elif flange_type == 'zero_one':
                            stress_R_0_3 = stress_R_0_4 = stress_R_T
                            stress_delta_R_0_3 = stress_delta_R_0_4 = stress_R_T
                        else:
                            raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                        #  Плоские и приварные с прямой втулкой
                        stress_R_0_5 = stress_R_0_6 = stress_M_R
                        stress_delta_R_0_5 = stress_delta_R_0_6 = stress_M_R

                        if flange_type in ('zero_one', 'one_one'):
                            # print("Провожу расчет на малоцикловую усталость")
                            if flange_type == 'one_one':
                                # print(f"для фланца типа: {flange_type}")
                                if r / s1 <= 0.75:
                                    val_x_1 = r / s1
                                    val_x_2 = r / s0
                                    alpha_sigma_1 = (114.63 * val_x_1 ** 6 - 342.10 * val_x_1 ** 5 +
                                                     418.49 * val_x_1 ** 4 - 276.59 * val_x_1 ** 3 +
                                                     111.30 * val_x_1 ** 2 - 28.286 * val_x_1 + 5.0888)
                                    alpha_sigma_2 = (114.63 * val_x_2 ** 6 - 342.10 * val_x_2 ** 5 +
                                                     418.49 * val_x_2 ** 4 - 276.59 * val_x_2 ** 3 +
                                                     111.30 * val_x_2 ** 2 - 28.286 * val_x_2 + 5.0888)
                                    stress_a = (  # Приварные с конической и прямой втулкой
                                        max(
                                            max(
                                                alpha_sigma_1 * abs(stress_M_1_1),
                                                abs(stress_M_1_2 - stress_M_1_4),
                                                abs(stress_M_1_2 - stress_M_1_6),
                                                abs(stress_M_0_1)
                                            ) / 2,
                                            max(
                                                alpha_sigma_2 * abs(stress_M_0_1),
                                                abs(stress_M_0_2 - stress_M_0_4),
                                                abs(stress_M_0_2 - stress_M_0_6)
                                            ) / 2
                                        ))
                                else:
                                    alpha_sigma_1 = alpha_sigma_2 = 1.5
                                    stress_a = (  # Когда нет альфы
                                        max(
                                            max(
                                                alpha_sigma_1 * abs(stress_M_1_1),
                                                abs(stress_M_1_2 - stress_M_1_4),
                                                abs(stress_M_1_2 - stress_M_1_6),
                                                abs(stress_M_0_1)
                                            ) / 2,
                                            max(
                                                alpha_sigma_2 * abs(stress_M_0_1),
                                                abs(stress_M_0_2 - stress_M_0_4),
                                                abs(stress_M_0_2 - stress_M_0_6)
                                            ) / 2
                                        ))
                            elif flange_type == 'zero_one':
                                # print(f"для фланца типа: {flange_type}")
                                alpha_sigma_1 = alpha_sigma_2 = 1.5
                                stress_a = (  # Плоские
                                    max(
                                        max(
                                            alpha_sigma_1 * abs(stress_M_1_1),
                                            abs(stress_M_1_2 - stress_M_1_4),
                                            abs(stress_M_1_2 - stress_M_1_6),
                                            abs(stress_M_0_1)
                                        ) / 2,
                                        max(
                                            alpha_sigma_2 * abs(stress_M_0_1),
                                            abs(stress_M_0_2 - stress_M_0_4),
                                            abs(stress_M_0_2 - stress_M_0_6)
                                        ) / 2
                                    ))
                            else:
                                stress_a = None
                                # print("Расчет на малоцикловую усталость не произведен")

                            stress_R_a, stress_delta_data = get_delta_sigma(ext_force, ext_moment, pressure, Q_t, alpha, alpha_m,
                                                         gasket_cal_diam, gasket_eff_width,
                                                         m, P_b_2, bolts_corrosion_area, allowed_stress_b_r, C_F, b, e,
                                                         Q_F_M,
                                                         flange_type, lambda_, s1, s0, c_flange, D_priv_flange, f,
                                                         D_int_flange, B_F,
                                                         h_flange, l_0, B_Y, B_Z, alpha_sigma_1, D_m_flange, D_n_flange)

                            stress_a_bolt = 1.8 * stress_b_1 / 2
                            stress_R_a_bolt = 2.0 * stress_b_2 / 2
                            # print("stress_a: ", stress_a)
                            # print("stress_R_a: ", stress_R_a)
                            # print("stress_a_bolt: ", stress_a_bolt)
                            # print("stress_R_a_bolt: ", stress_R_a_bolt)
                            allowed_amplitude_flange_m, allowed_N_c_flange = (
                                get_allowed_amplitude(num_cycles_c, flange_steel, temperature, abs(stress_a)))
                            allowed_amplitude_flange_r, allowed_N_r_flange = (
                                get_allowed_amplitude(num_cycles_r, flange_steel, temperature, abs(stress_R_a)))
                            # print("allowed_amplitude_flange_m: ", allowed_amplitude_flange_m)
                            # print("allowed_N_c_flange: ", allowed_N_c_flange)
                            # print("allowed_amplitude_flange_r: ", allowed_amplitude_flange_r)
                            # print("allowed_N_r_flange: ", allowed_N_r_flange)

                            allowed_amplitude_bolt_m, allowed_N_c_bolt = (
                                get_allowed_amplitude(num_cycles_c, bolt_steel, temperature, abs(stress_a_bolt)))
                            allowed_amplitude_bolt_r, allowed_N_r_bolt = (
                                get_allowed_amplitude(num_cycles_r, bolt_steel, temperature, abs(stress_R_a_bolt)))
                            # print("allowed_amplitude_bolt_m: ", allowed_amplitude_bolt_m)
                            # print("allowed_N_c_bolt: ", allowed_N_c_bolt)
                            # print("allowed_amplitude_bolt_r: ", allowed_amplitude_bolt_m)
                            # print("allowed_N_r_bolt: ", allowed_N_c_bolt)

                            flange_cycles = num_cycles_c / allowed_N_c_flange + num_cycles_r / allowed_N_r_flange
                            bolt_cycles = num_cycles_c / allowed_N_c_bolt + num_cycles_r / allowed_N_r_bolt

                            # print(stress_a, ' <= ', allowed_amplitude_flange_m)
                            # print(stress_R_a, ' <= ', allowed_amplitude_flange_r)
                            # print(flange_cycles, ' <= ', 1)
                            # print(stress_a_bolt, ' <= ', allowed_amplitude_bolt_m)
                            # print(stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r)
                            # print(bolt_cycles, ' <= ', 1)
                            if (
                                    stress_a_bolt <= allowed_amplitude_bolt_m and
                                    stress_R_a_bolt <= allowed_amplitude_bolt_r and
                                    bolt_cycles <= 1.0
                            ):
                                a = 1
                                # print(f"Шпильки типа {bolt_type} удовлетворяют расчету на малоцикловую усталость")
                                # print()
                                is_cycles_bolt = True
                            else:
                                is_cycles_bolt = False
                                a = 1
                                # print(f'Шпильки типа {bolt_type} НЕ удовлетворяет расчету на малоцикловую усталость!!')
                            is_cycles_flange = False
                            if (
                                    stress_a <= allowed_amplitude_flange_m and
                                    stress_R_a <= allowed_amplitude_flange_r and
                                    flange_cycles <= 1.0
                            ):
                                is_cycles_flange = True
                                # print(f"Фланец типа {flange_type} удовлетворяет расчету на малоцикловую усталость")
                                # print()

                            else:
                                is_cycles_bolt = False
                                a = 1
                                # print(f'Фланец типа {flange_type} НЕ удовлетворяет расчету на малоцикловую усталость!!')
                                # print()

                            if is_cycles_bolt and is_cycles_flange:
                                results_dict = {
                                    "gasket_params": gasket_params,
                                    "fasteners_data": fasteners_data,
                                    "stud_length": stud_length,
                                    "sigma_b_flange_T": sigma_b_flange_T,
                                    "sigma_y_flange_T": sigma_y_flange_T,
                                    "sigma_b_bolt_T": sigma_b_bolt_T,
                                    "sigma_y_bolt_T": sigma_y_bolt_T,
                                    "flange_type": flange_type,
                                    "face_type": face_type,
                                    "flange_steel": flange_steel,
                                    "bolt_steel": bolt_steel,
                                    "D_N_flange": D_N_flange,
                                    "pressure": pressure,
                                    "temperature": temperature,
                                    "D_ext_flange": D_ext_flange,
                                    "D_int_flange": D_int_flange,
                                    "r": r,
                                    "d_pins_flange": d_pins_flange,
                                    "pins_quantity": pins_quantity,
                                    "pin_diam": pin_diam,
                                    "ext_force": ext_force,
                                    "ext_moment": ext_moment,
                                    "operating_time": operating_time,
                                    "h_flange": h_flange,
                                    "H_flange": H_flange,
                                    "D_n_flange": D_n_flange,
                                    "D_m_flange": D_m_flange,
                                    "c_flange": c_flange,
                                    "c_bolt": c_bolt,
                                    "Шпильки при затяжке: ": (
                                        'Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m),
                                    "Шпильки при раб. усл.: ": (
                                        'Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r),
                                    "Прокладка: ": ('Прокладка: ', q, ' <= ', q_obj_dop),
                                    "Условие (43): ": (
                                        'Условие (43): ', condition_43, ' <= ', 1.3 * allowed_stress_flange_m),
                                    "Условие (44): ": (
                                        'Условие (44): ', condition_44, ' <= ', 1.3 * allowed_stress_flange_m),
                                    "Условие (45): ": (
                                        'Условие (45): ', condition_45, ' <= ', 1.3 * allowed_stress_flange_r),
                                    "Условие (46): ": (
                                        'Условие (46): ', condition_46, ' <= ', 1.3 * allowed_stress_flange_r),
                                    "Условие (47): ": (
                                        'Условие (47): ', condition_47, ' <= ', 1.3 * allowed_stress_flange_m),
                                    "Условие (48): ": (
                                        'Условие (48): ', condition_48, ' <= ', 1.3 * allowed_stress_flange_m),
                                    "Условие (53): ": ('Условие (53): ', condition_53, ' <= ',
                                                       min(allowed_stress_flange_m, allowed_stress_flange_r)),
                                    "Условие (54): ": ('Условие (54): ', condition_54, ' <= ',
                                                       min(allowed_stress_flange_m, allowed_stress_flange_r)),
                                    "Условие (55): ": ('Условие (55): ', condition_55, ' <= ',
                                                       min(allowed_stress_flange_m, allowed_stress_flange_r)),
                                    "stress_a_bolt": (stress_a_bolt, ' <= ', allowed_amplitude_bolt_m),
                                    "stress_R_a_bolt": (stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r),
                                    "stress_a": (stress_a, ' <= ', allowed_amplitude_flange_m),
                                    "stress_R_a": (stress_R_a, ' <= ', allowed_amplitude_flange_r),
                                    "flange_cycles": (
                                        flange_cycles, allowed_N_c_flange, allowed_N_r_flange),
                                    "bolt_cycles": (bolt_cycles, allowed_N_c_bolt, allowed_N_r_bolt),
                                    "num_cycles_c": num_cycles_c,
                                    "num_cycles_r": num_cycles_r,
                                }
                                all_results.append(results_dict)
                                # df = pd.DataFrame([results_dict])
                                # df.to_excel(filename, index=False)
                                print(
                                    f"Добавлена комбинация c D_N: {D_n_flange}, D_m: {D_m_flange}, h: {h_flange}, H: {H_flange}")
                        else:
                            raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")
                    else:
                        a = 1
                        # print("Условие прочности фланцев не выполняется")
                else:
                    a = 1
                    # print(f"Условие прочности болтов: {is_bolt_true}, прокладки: {is_gasket_true}")

            except Exception as e:
                a = 1
                # print(f"Ошибка: {e}")

    else:
        a = 1
        # print("Данная методика не подходит для такого фланцевого соединения")
    print(len(all_results))
    if len(all_results) < 1048576:

        df = pd.DataFrame(all_results)
        df.to_excel(filename, index=False)
    else:
        all_results = all_results[:1048575]
        df = pd.DataFrame(all_results)
        df.to_excel(filename, index=False)


def get_gasket(pressure, D_N_flange, face_type):
    def add_gasket_params(gasket_sizes, material):
        for i, mat in enumerate(gasket_params['material']):
            if mat == material:
                gasket_sizes.update({
                    'm': gasket_params['m'][i],
                    'q_obj': gasket_params['q_obj'][i],
                    'q_obj_dop': gasket_params['q_obj_dop'][i],
                    'K_obj': gasket_params['K_obj'][i],
                    'E_p': gasket_params['E_p'][i]
                })
                break

    gasket_type_15180 = None
    gasket_type_34655 = None
    gasket_type_iso_7483 = None
    gasket_sizes = {}

    for row in table_15180:
        if (row["p_min"] <= float(pressure) <= row["p_max"]
                and row["dn_min"] <= int(D_N_flange) <= row["dn_max"]
                and (row["face_type"] is None or face_type in row["face_type"])):
            gasket_type_15180 = row["type"]
            break
    if gasket_type_15180 in GASKET_SIZES_15180:
        for dy, p_range, D, d, thickness, material in GASKET_SIZES_15180[gasket_type_15180]:
            low, high = p_range
            if int(dy) == int(D_N_flange) and low <= float(pressure) <= high:
                gasket_sizes = {
                    "document": 'ГОСТ 15180-86',
                    "type": gasket_type_15180,
                    "dy": dy,
                    "D_outer": D,
                    "d_inner": d,
                    "thickness": thickness,
                    "material": material
                }
                add_gasket_params(gasket_sizes, material)
                break

    if not gasket_sizes:  # If no match found in 15180, check 34655
        for row in table_34655:
            if (row["p_min"] <= float(pressure) <= row["p_max"]
                    and row["dn_min"] <= int(D_N_flange) <= row["dn_max"]
                    and (row["face_type"] is None or face_type in row["face_type"])):
                gasket_type_34655 = row["type"]
                break
        if gasket_type_34655 in GASKET_SIZES_34655:
            for dy, p_range, D, d, thickness, radius_or_height_1, material in GASKET_SIZES_34655[gasket_type_34655]:
                low, high = p_range
                if int(dy) == int(D_N_flange) and low <= float(pressure) <= high:
                    gasket_sizes = {
                        "document": 'ГОСТ 34655-2020',
                        "type": gasket_type_34655,
                        "dy": dy,
                        "D_outer": D,
                        "d_inner": d,
                        "thickness": thickness,
                        "radius_or_height_1": radius_or_height_1,
                        "material": material
                    }
                    add_gasket_params(gasket_sizes, material)
                    break

    if not gasket_sizes:  # If no match found in 34655, check ISO 7483
        for row in table_iso_7483:
            if (row["p_min"] <= float(pressure) <= row["p_max"]
                    and row["dn_min"] <= int(D_N_flange) <= row["dn_max"]
                    and (row["face_type"] is None or face_type in row["face_type"])):
                gasket_type_iso_7483 = row["type"]
                break
        if gasket_type_iso_7483 in GASKET_SIZES_ISO_7483:
            for dy, p_range, D, d, thickness, radius_or_width_c, mat in GASKET_SIZES_ISO_7483[gasket_type_iso_7483]:
                low, high = p_range
                if int(dy) == int(D_N_flange) and low <= float(pressure) <= high:
                    gasket_sizes = {
                        "document": 'ISO 7483-2011',
                        "type": gasket_type_iso_7483,
                        "dy": dy,
                        "D_outer": D,
                        "d_inner": d,
                        "thickness": thickness,
                        "radius_or_width_c": radius_or_width_c,
                        "material": mat
                    }
                    add_gasket_params(gasket_sizes, mat)
                    break

    return gasket_sizes


def get_bolt_area_and_size(pin_diam, pins_quantity, pressure, h_flange):
    if pin_diam not in bolt_areas:
        raise ValueError(f"Неизвестный диаметр: {pin_diam} мм")

    if pressure <= 4.0:
        bolt_area = bolt_areas[pin_diam]["без_проточки"]
        bolt_type = "1"
    elif (4.0 < pressure) and (pressure <= 16.0):
        bolt_area = bolt_areas[pin_diam]["с_проточкой"]
        bolt_type = "2"
    else:
        raise ValueError("Давление выше 16 МПа не поддерживается.")

    bolts_area = pins_quantity * bolt_area

    nut_height = nuts_data[pin_diam][1]
    washer_thickness = washer_data[pin_diam][2]

    required_length = 2 * (nut_height + washer_thickness + h_flange)

    bolt_entry = next((b for b in bolts_data[bolt_type] if b[0] == pin_diam), None)
    if bolt_entry is None:
        raise ValueError(f"Нет данных по шпилькам для диаметра {pin_diam}")
    fasteners_data = {
        "bolt": (bolt_type, bolt_entry),
        "nut": nuts_data[pin_diam],
        "washer": washer_data[pin_diam]
    }
    min_len, max_len, step = bolt_entry[4]
    if required_length <= min_len:
        stud_length = min_len
    elif required_length > max_len:
        raise ValueError(f"Требуемая длина {required_length} мм превышает максимальную {max_len} мм")
    else:
        stud_length = ((required_length + step - 1) // step) * step

    return bolt_area, bolts_area, stud_length, bolt_type, fasteners_data


def get_steel_prop(steel_grade, temperature: float):
    key_1 = None
    for grades in E_modulus_data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key_1 = grades
            break

    if key_1 is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data_1 = E_modulus_data[key_1]
    E20 = round(temp_data_1[20] * 1e5, 0)

    if temperature in temp_data_1:
        return E20, temp_data_1[temperature]

    temps_1 = sorted(temp_data_1.keys())
    if temperature < temps_1[0] or temperature > temps_1[-1]:
        raise ValueError(f"Температура {temperature}°C вне диапазона данных для этой стали.")

    pos_1 = bisect.bisect_left(temps_1, temperature)
    t1_1, t2_1 = temps_1[pos_1 - 1], temps_1[pos_1]
    E1, E2 = temp_data_1[t1_1], temp_data_1[t2_1]
    ET = round((E1 + (E2 - E1) * (temperature - t1_1) / (t2_1 - t1_1)) * 1e5, 0)

    key_2 = None
    for grades in alpha_data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key_2 = grades
            break

    if key_2 is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data_2 = alpha_data[key_2]
    alpha20 = temp_data_2[20] * 1e-6

    if temperature in temp_data_2:
        return alpha20, temp_data_2[temperature]

    temps_2 = sorted(temp_data_2.keys())
    if temperature < temps_2[0] or temperature > temps_2[-1]:
        raise ValueError(f"Температура {temperature}°C вне диапазона данных для этой стали.")

    pos_2 = bisect.bisect_left(temps_2, temperature)
    t1_2, t2_2 = temps_2[pos_2 - 1], temps_2[pos_2]
    alpha1, alpha2 = temp_data_2[t1_2], temp_data_2[t2_2]
    alphaT = (alpha1 + (alpha2 - alpha1) * (temperature - t1_2) / (t2_2 - t1_2)) * 1e-6

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

    return E20, ET, alpha20, alphaT, sigma_b_20, sigma_b_T, sigma_y_20, sigma_y_T


def get_hardness_flanges(flange_type, d_pins_flange, gasket_cal_diam, s0, D_int_flange, K_obj, gasket_thickness,
                         gasket_material, E_p, gasket_width, pin_diam, pins_quantity, pressure, h_flange, bolt_steel,
                         temperature, D_ext_flange, s1, H_flange, flange_steel, D_n_flange, m):
    if flange_type in ('zero_one', 'one_one'):
        b = 0.5 * (d_pins_flange - gasket_cal_diam)
        f, x, B, y_p, y_b, y_flange, y_flange_n, C_F, D_priv_flange, lambda_, l_0, B_F, B_Y, B_Z, B_V = (
            get_ductility(K_obj, gasket_thickness, gasket_material, E_p,
                          gasket_cal_diam, gasket_width, pin_diam,
                          pins_quantity, pressure, h_flange, bolt_steel, temperature,
                          D_int_flange, s0, D_ext_flange,
                          s1, H_flange, flange_steel, d_pins_flange, D_n_flange, m,
                          flange_type))
        (E_bolt_20, E_bolt_T, alpha_bolt_20, alpha_bolt_T,
         sigma_b_bolt_20, sigma_b_bolt_T, sigma_y_bolt_20, sigma_y_bolt_T) = (
            get_steel_prop(bolt_steel, temperature))

        (E_flange_20, E_flange_T, alpha_flange_20, alpha_flange_T,
         sigma_b_flange_20, sigma_b_flange_T, sigma_y_flange_20, sigma_y_flange_T) = (
            get_steel_prop(flange_steel, temperature))

        koef_B_x = 1 + (B - 1) * (x / (x + ((1 + B) / 4)))
        s_e = None
        if flange_type == 'one_one':
            s_e = koef_B_x * s0
        elif flange_type == 'zero_one':
            s_e = s0

        e = 0.5 * (gasket_cal_diam - D_int_flange - s_e)

        gamma = 1 / (y_p + y_b * E_bolt_20 / E_bolt_T + (y_flange * E_flange_20 / E_flange_T + y_flange * E_flange_20 /
                                                         E_flange_T) * b ** 2)
        alpha = 1 - (y_p - 2 * y_flange * e * b) / (y_p + y_b + 2 * y_flange * (b ** 2))
        alpha_m = ((y_b + 2 * y_flange_n * b * (b + e - e ** 2 / gasket_cal_diam)) /
                   (y_b + y_p * (d_pins_flange / gasket_cal_diam) ** 2 + 2 * y_flange_n * b ** 2))

    else:
        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

    return f, b, e, gamma, alpha, alpha_m, C_F, D_priv_flange, lambda_, l_0, B_F, B_Y, B_Z, y_flange, B_V, x, B, koef_B_x, s_e


def get_ductility(K_obj, gasket_thickness, gasket_material, E_p, gasket_cal_diam, gasket_width, pin_diam,
                  pins_quantity, pressure, h_flange, bolt_steel, temperature, D_int_flange, s0, D_ext_flange, s1,
                  H_flange, flange_steel, d_pins_flange, D_n_flange, m, flange_type):
    if gasket_material in ('Паронит по ГОСТ 481-80', 'Фторопласт-4 или лента ПН по ГОСТ 24222-80',
                           'Уплотнительный материал ФУМ-В', 'Листовая резина тип 1 по ГОСТ 7338-77'):
        if gasket_material == 'Листовая резина тип 1 по ГОСТ 7338-77':
            E_p = 0.3 * 10 ** (-5) * (1 + gasket_width / (2 * gasket_thickness))
        y_p = gasket_thickness * K_obj / (E_p * math.pi * gasket_cal_diam * gasket_width)
    else:
        y_p = 0
    bolt_area, bolts_area, stud_length, bolt_type, fasteners_data = get_bolt_area_and_size(pin_diam, pins_quantity,
                                                                                           pressure, h_flange)
    (E_bolt_20, E_bolt_T, alpha_bolt_20, alpha_bolt_T,
     sigma_b_bolt_20, sigma_b_bolt_T, sigma_y_bolt_20, sigma_y_bolt_T) = (
        get_steel_prop(bolt_steel, temperature))

    (E_flange_20, E_flange_T, alpha_flange_20, alpha_flange_T,
     sigma_b_flange_20, sigma_b_flange_T, sigma_y_flange_20, sigma_y_flange_T) = (
        get_steel_prop(flange_steel, temperature))

    L_b = stud_length + 0.56 * pin_diam
    y_b = L_b / (E_bolt_20 * bolts_area)

    l_0 = math.sqrt(D_int_flange * s0)
    K = D_ext_flange / D_int_flange

    B_T = (K ** 2 * (1 + 8.55 * math.log10(K)) - 1) / ((1.05 + 1.945 * K ** 2) * (K - 1))
    B_U = (K ** 2 * (1 + 8.55 * math.log10(K)) - 1) / (1.36 * (K ** 2 - 1) * (K - 1))
    B_Y = (1 / (K - 1)) * (0.69 + 5.72 * (K ** 2 * math.log10(K) / (K ** 2 - 1)))
    B_Z = (K ** 2 + 1) / (K ** 2 - 1)

    x = H_flange / l_0

    x_rounded_B_F = min(x_values_B_F, key=lambda v: abs(v - x))
    x_rounded_B_V = min(x_values_B_V, key=lambda v: abs(v - x))
    x_rounded_f = min(x_values_f, key=lambda v: abs(v - x))

    B = s1 / s0

    B_F = None
    B_V = None
    f = 1.0
    if B == 1.0:
        B_F = 0.91
        B_V = 0.55
    else:
        B_F_list = B_F_values[x_rounded_B_F]
        B_V_list = B_V_values[x_rounded_B_V]
        f_list = f_values[x_rounded_f]
        for (B_low, BF_low), (B_high, BF_high) in zip(B_F_list, B_F_list[1:]):
            if B_low <= B <= B_high:
                B_F = BF_low + (BF_high - BF_low) * (B - B_low) / (B_high - B_low)
        for (B_low, BV_low), (B_high, BV_high) in zip(B_V_list, B_V_list[1:]):
            if B_low <= B <= B_high:
                B_V = BV_low + (BV_high - BV_low) * (B - B_low) / (B_high - B_low)
        for (B_low, f_low), (B_high, f_high) in zip(f_list, f_list[1:]):
            if B_low <= B <= B_high:
                f = f_low + (f_high - f_low) * (B - B_low) / (B_high - B_low)

    lambda_ = (B_F * h_flange + l_0) / (B_T * l_0) + B_V * h_flange ** 3 / (B_U * l_0 * s0 ** 2)

    y_flange = 0.91 * B_V / (E_flange_20 * lambda_ * s0 ** 2 * l_0)
    y_flange_n = (math.pi / 4) ** 3 * d_pins_flange / (E_flange_20 * D_n_flange * h_flange ** 3)

    C_F = max(
        1.0,
        math.sqrt((math.pi * d_pins_flange / pins_quantity) / (2 * pin_diam + 6 * h_flange / (m + 0.5)))
    )
    D_priv_flange = None

    if flange_type in ('zero_one', 'one_one'):
        if flange_type == 'one_one':
            if D_int_flange >= 20 * s1:
                D_priv_flange = D_int_flange
            elif D_int_flange < 20 * s1 and f > 1.0:
                D_priv_flange = D_int_flange + s0
            elif D_int_flange < 20 * s1 and f == 1.0:
                D_priv_flange = D_int_flange + s1
            else:
                raise ValueError(f"Невозможно вычислить приведенный диаметр для фланца типа: {flange_type}")
        elif flange_type == 'zero_one':
            D_priv_flange = D_int_flange
    else:
        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

    return f, x, B, y_p, y_b, y_flange, y_flange_n, C_F, D_priv_flange, lambda_, l_0, B_F, B_Y, B_Z, B_V


def get_allowed_stress_bolt(steel, temperature):
    (E_20, E_T, alpha_20, alpha_T,
     sigma_b_20, sigma_b_T, sigma_y_20, sigma_y_T) = (
        get_steel_prop(steel, temperature))

    if sigma_y_20 / sigma_b_20 >= 0.7:
        n_T = 2.7
    else:
        n_T = 2.3
    allowed_stress_b_n = sigma_y_T / n_T

    allowed_stress_b_m = 1.2 * 1.0 * 1.1 * 1.3 * allowed_stress_b_n
    allowed_stress_b_r = 1.35 * 1.1 * 1.3 * allowed_stress_b_n

    return allowed_stress_b_m, allowed_stress_b_r, n_T


def get_allowed_stress_flange(steel_grade, temperature):
    key_3 = None
    for grades in allowed_flange_data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key_3 = grades
            break

    if key_3 is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data_3 = allowed_flange_data[key_3]
    allowed_stress_flange_20 = temp_data_3[20]

    if temperature in temp_data_3:
        return allowed_stress_flange_20, temp_data_3[temperature]

    temps_3 = sorted(temp_data_3.keys())
    if temperature < temps_3[0] or temperature > temps_3[-1]:
        raise ValueError(f"Температура {temperature}°C вне диапазона данных для этой стали.")

    pos_3 = bisect.bisect_left(temps_3, temperature)
    t_1_3, t_2_3 = temps_3[pos_3 - 1], temps_3[pos_3]
    allowed_stress_flange_1, allowed_stress_flange_2 = temp_data_3[t_1_3], temp_data_3[t_2_3]
    allowed_stress_flange_T = round((allowed_stress_flange_1 + (allowed_stress_flange_2 - allowed_stress_flange_1) *
                                     (temperature - t_1_3) / (t_2_3 - t_1_3)), 3)

    allowed_stress_flange_m = 1.5 * allowed_stress_flange_T
    allowed_stress_flange_r = 3.0 * allowed_stress_flange_T

    return allowed_stress_flange_m, allowed_stress_flange_r, allowed_stress_flange_T


def get_corrosion_thickness(operating_time, flange_steel, bolt_steel):
    if flange_steel in ["10", "20", "25", "30", "35", "40"]:
        velocity_of_corrosion_flange = 0.2
    elif flange_steel in ["35Х", "40Х", "30ХМА"]:
        velocity_of_corrosion_flange = 0.18
    elif flange_steel in ["25Х1МФ", "25Х2М1Ф"]:
        velocity_of_corrosion_flange = 0.15
    elif flange_steel in ["20Х13", "18Х12ВМБФР"]:
        velocity_of_corrosion_flange = 0.1
    elif flange_steel in ["12Х18Н10Т", "ХН35ВТ"]:
        velocity_of_corrosion_flange = 0.02
    elif flange_steel in ["Д16"]:
        velocity_of_corrosion_flange = 0.08
    else:
        raise ValueError(f"Нет данных по коррозии для: {flange_steel}")

    if bolt_steel in ["10", "20", "25", "30", "35", "40"]:
        velocity_of_corrosion_bolt = 0.2
    elif bolt_steel in ["35Х", "40Х", "30ХМА"]:
        velocity_of_corrosion_bolt = 0.18
    elif bolt_steel in ["25Х1МФ", "25Х2М1Ф"]:
        velocity_of_corrosion_bolt = 0.15
    elif bolt_steel in ["20Х13", "18Х12ВМБФР"]:
        velocity_of_corrosion_bolt = 0.1
    elif bolt_steel in ["12Х18Н10Т", "ХН35ВТ"]:
        velocity_of_corrosion_bolt = 0.02
    elif bolt_steel in ["Д16"]:
        velocity_of_corrosion_bolt = 0.08
    else:
        raise ValueError(f"Нет данных по коррозии для: {bolt_steel}")

    c_flange = velocity_of_corrosion_flange * operating_time
    c_bolt = velocity_of_corrosion_bolt * operating_time

    return c_flange, c_bolt


def get_allowed_amplitude(num_cycles, steel_grade, temperature, stress_a):
    E20, ET, alpha20, alphaT, sigma_b_20, sigma_b_T, sigma_y_20, sigma_y_T = get_steel_prop(steel_grade, temperature)
    data = {  # A, B, Ct, nN, n_sigma
        "10,20,25,30,35,40":
            [0.6 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0],
        "35Х,40Х,30ХМА,25Х1МФ,25Х2М1Ф,20Х13,18Х12ВМБФР":
            [0.45 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0],
        "12Х18Н10Т,ХН35ВТ":
            [0.6 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0],
        "Д16":
            [0.086 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 20.0, 2.0]
    }

    key = None
    for grades in data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key = grades
            break

    if key is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data = list(data[key])

    allowed_amplitude = temp_data[2] * temp_data[0] / math.sqrt(temp_data[3] * num_cycles) + temp_data[1] / temp_data[4]
    if stress_a <= temp_data[1] / temp_data[4]:
        allowed_N = 1e1000_000_000
    else:
        allowed_N = round(
            (1 / temp_data[3]) * (temp_data[0] * temp_data[2] / (stress_a - (temp_data[1] / temp_data[4]))) ** 2)

    return allowed_amplitude, allowed_N


def get_delta_sigma(ext_force, ext_moment, pressure, Q_t, alpha, alpha_m, gasket_cal_diam, gasket_eff_width,
                    m, P_b_2, bolts_corrosion_area, allowed_stress_b_r, C_F, b, e, Q_F_M,
                    flange_type, lambda_, s1, s0, c_flange, D_priv_flange, f, D_int_flange, B_F,
                    h_flange, l_0, B_Y, B_Z, alpha_sigma_1, D_m_flange, D_n_flange):
    pressure_min = 0.6 * pressure
    pressure_max = 1.25 * pressure

    R_p_min = round(math.pi * gasket_cal_diam * gasket_eff_width * m * pressure_min / 1000, 3)
    R_p_max = round(math.pi * gasket_cal_diam * gasket_eff_width * m * pressure_max / 1000, 3)

    Q_d_min = round(0.785 * gasket_cal_diam ** 2 * pressure_min / 1000, 3)
    Q_d_max = round(0.785 * gasket_cal_diam ** 2 * pressure_max / 1000, 3)

    P_b_1_min = max(
        alpha * (Q_d_min + ext_force) + R_p_min + 4 * alpha_m * abs(ext_moment) / gasket_cal_diam,
        alpha * (Q_d_min + ext_force) + R_p_min + 4 * alpha_m * abs(ext_moment) / gasket_cal_diam - Q_t
    )
    P_b_1_max = max(
        alpha * (Q_d_max + ext_force) + R_p_max + 4 * alpha_m * abs(ext_moment) / gasket_cal_diam,
        alpha * (Q_d_max + ext_force) + R_p_max + 4 * alpha_m * abs(ext_moment) / gasket_cal_diam - Q_t
    )

    P_b_m_min = round(max(P_b_1_min, P_b_2), 3)
    P_b_m_max = round(max(P_b_1_max, P_b_2), 3)

    P_b_r_min = round(
        P_b_m_min + (1 - alpha) * (Q_d_min + ext_force) + Q_t + 4 * (1 - alpha_m) * abs(ext_moment) / gasket_cal_diam,
        3)
    P_b_r_max = round(
        P_b_m_max + (1 - alpha) * (Q_d_max + ext_force) + Q_t + 4 * (1 - alpha_m) * abs(ext_moment) / gasket_cal_diam,
        3)

    stress_b_2_min = P_b_r_min * 1000 / bolts_corrosion_area
    stress_b_2_max = P_b_r_max * 1000 / bolts_corrosion_area

    is_bolt_true = False

    if max(stress_b_2_min, stress_b_2_max) <= allowed_stress_b_r:
        is_bolt_true = True
    if is_bolt_true:
        M_M_min = C_F * P_b_m_min * b / 1000
        M_M_max = C_F * P_b_m_max * b / 1000
        M_R_min = C_F * max(
            P_b_r_min * b / 1000 + (Q_d_min + Q_F_M) * e / 1000,
            abs(Q_d_min + Q_F_M) * e / 1000
        )
        M_R_max = C_F * max(
            P_b_r_max * b / 1000 + (Q_d_max + Q_F_M) * e / 1000,
            abs(Q_d_max + Q_F_M) * e / 1000
        )

        stress_R_1_min = None
        stress_R_1_max = None

        stress_R_0_min = None
        stress_R_0_max = None

        if flange_type == 'one_one':
            stress_R_1_min = M_R_min * 1e6 / (lambda_ * (s1 - c_flange) ** 2 * D_priv_flange)
            stress_R_1_max = M_R_max * 1e6 / (lambda_ * (s1 - c_flange) ** 2 * D_priv_flange)
            stress_R_0_min = f * stress_R_1_min
            stress_R_0_max = f * stress_R_1_max
        elif flange_type == 'zero_one':
            stress_R_0_min = stress_R_1_min = M_R_min * 1e6 / (lambda_ * (s0 - c_flange) ** 2 * D_priv_flange)
            stress_R_0_max = stress_R_1_max = M_R_max * 1e6 / (lambda_ * (s0 - c_flange) ** 2 * D_priv_flange)

        stress_1MM_R_min = max(
            (Q_d_min + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s1) * (s1 - c_flange)),
            (Q_d_min + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s1) * (s1 - c_flange))
        )
        stress_1MM_R_max = max(
            (Q_d_max + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s1) * (s1 - c_flange)),
            (Q_d_max + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s1) * (s1 - c_flange))
        )

        stress_0MM_R_min = max(
            (Q_d_min + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s0) * (s0 - c_flange)),
            (Q_d_min + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s0) * (s0 - c_flange))
        )
        stress_0MM_R_max = max(
            (Q_d_max + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s0) * (s0 - c_flange)),
            (Q_d_max + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                    math.pi * (D_int_flange + s0) * (s0 - c_flange))
        )

        stress_0MO_R_min = pressure_min * D_int_flange / (2 * (s0 - c_flange))
        stress_0MO_R_max = pressure_max * D_int_flange / (2 * (s0 - c_flange))

        stress_M_R_min = (1.33 * B_F * h_flange + l_0) * M_M_min * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
        stress_M_R_max = (1.33 * B_F * h_flange + l_0) * M_M_max * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)

        stress_R_R_min = (1.33 * B_F * h_flange + l_0) * M_R_min * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
        stress_R_R_max = (1.33 * B_F * h_flange + l_0) * M_R_max * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
        stress_R_T_min = B_Y * M_R_min * 1e6 / (h_flange ** 2 * D_int_flange) - B_Z * stress_R_R_min
        stress_R_T_max = B_Y * M_R_max * 1e6 / (h_flange ** 2 * D_int_flange) - B_Z * stress_R_R_max

        stress_R_1_1_min = stress_R_1_min + stress_1MM_R_min
        stress_R_1_1_max = stress_R_1_max + stress_1MM_R_max

        stress_R_1_2_min = -stress_R_1_min + stress_1MM_R_min
        stress_R_1_2_max = -stress_R_1_max + stress_1MM_R_max

        stress_R_1_3_min = stress_R_1_4_min = stress_R_T_min
        stress_R_1_3_max = stress_R_1_4_max = stress_R_T_max

        stress_R_1_5_min = stress_R_1_6_min = stress_R_R_min
        stress_R_1_5_max = stress_R_1_6_max = stress_R_R_max

        #  Приварные и плоские
        stress_R_0_1_min = stress_R_0_min + stress_0MM_R_min
        stress_R_0_1_max = stress_R_0_max + stress_0MM_R_max

        stress_R_0_2_min = -stress_R_0_min + stress_0MM_R_min
        stress_R_0_2_max = -stress_R_0_max + stress_0MM_R_max

        if flange_type == 'one_one':
            stress_R_0_3_min = stress_0MO_R_min + 0.3 * stress_R_0_min
            stress_R_0_3_max = stress_0MO_R_max + 0.3 * stress_R_0_max
            stress_R_0_4_min = stress_0MO_R_min - 0.3 * stress_R_0_min
            stress_R_0_4_max = stress_0MO_R_max - 0.3 * stress_R_0_max
        elif flange_type == 'zero_one':
            stress_R_0_3_min = stress_R_0_4_min = stress_R_T_min
            stress_R_0_3_max = stress_R_0_4_max = stress_R_T_max

        #  Плоские и приварные с прямой втулкой
        stress_R_0_5_min = stress_R_0_6_min = stress_M_R_min
        stress_R_0_5_max = stress_R_0_6_max = stress_M_R_max

        stress_delta_R_0_1 = abs(stress_R_0_1_max - stress_R_0_1_min)
        stress_delta_R_0_2 = abs(stress_R_0_2_max - stress_R_0_2_min)
        stress_delta_R_0_3 = abs(stress_R_0_3_max - stress_R_0_3_min)
        stress_delta_R_0_4 = abs(stress_R_0_4_max - stress_R_0_4_min)
        stress_delta_R_0_5 = abs(stress_R_0_5_max - stress_R_0_5_min)
        stress_delta_R_0_6 = abs(stress_R_0_6_max - stress_R_0_6_min)

        stress_delta_R_1_1 = abs(stress_R_1_1_max - stress_R_1_1_min)
        stress_delta_R_1_2 = abs(stress_R_1_2_max - stress_R_1_2_min)
        stress_delta_R_1_3 = abs(stress_R_1_3_max - stress_R_1_3_min)
        stress_delta_R_1_4 = abs(stress_R_1_4_max - stress_R_1_4_min)
        stress_delta_R_1_5 = abs(stress_R_1_5_max - stress_R_1_5_min)
        stress_delta_R_1_6 = abs(stress_R_1_6_max - stress_R_1_6_min)

        if flange_type == 'one_one':
            if D_m_flange > D_n_flange:
                stress_R_a = (
                        max(
                            alpha_sigma_1 * abs(stress_delta_R_1_1),
                            abs(stress_delta_R_1_2 - stress_delta_R_1_4),
                            abs(stress_delta_R_1_2 - stress_delta_R_1_6)
                        ) / 2
                    )
            if D_m_flange == D_n_flange:
                stress_R_a = (
                        max(
                            alpha_sigma_1 * abs(stress_delta_R_0_1),
                            abs(stress_delta_R_0_1 - stress_delta_R_0_3),
                            abs(stress_delta_R_0_1 - stress_delta_R_1_5),
                            abs(stress_delta_R_0_2),
                            abs(stress_delta_R_0_2 - stress_delta_R_0_4),
                            abs(stress_delta_R_0_2 - stress_delta_R_0_6)
                        ) / 2
                )
        elif flange_type == 'zero_one':
            stress_R_a = (
                    1.5 * max(
                            abs(stress_delta_R_0_1),
                            abs(stress_delta_R_0_3),
                            abs(stress_delta_R_0_1 - stress_delta_R_0_3),
                            abs(stress_delta_R_0_2),
                            abs(stress_delta_R_0_2 - stress_delta_R_0_4),
                            abs(stress_delta_R_0_4),
                        ) / 2
            )
        else:
            stress_R_a = None

    stress_delta_data = {
        "stress_delta_R_1_1": stress_delta_R_1_1,
        "stress_delta_R_1_2": stress_delta_R_1_2,
        "stress_delta_R_1_4": stress_delta_R_1_4,
        "stress_delta_R_1_6": stress_delta_R_1_6,
        "stress_delta_R_0_1": stress_delta_R_0_1,
        "stress_delta_R_0_3": stress_delta_R_0_3,
        "stress_delta_R_0_5": stress_delta_R_0_5,
        "stress_delta_R_0_2": stress_delta_R_0_2,
        "stress_delta_R_0_4": stress_delta_R_0_4,
        "stress_delta_R_0_6": stress_delta_R_0_6
    }

    return stress_R_a, stress_delta_data


def solo_calc(input_data, input_select):
    D_N_flange = float(input_data['D_N_flange'])
    pressure = float(input_data['pressure'])
    temperature = float(input_data['temperature'])
    D_ext_flange = float(input_data['D_ext_flange'])
    D_int_flange = float(input_data['D_int_flange'])
    h_flange = float(input_data['h_flange'])
    H_flange = float(input_data['H_flange'])
    T_b = float(input_data['T_b'])

    D_n_flange = float(input_data['D_n_flange'])
    D_m_flange = float(input_data['D_m_flange'])

    r = float(input_data['r'])

    d_pins_flange = float(input_data['d_pins_flange'])
    pins_quantity = float(input_data['pins_quantity'])
    pin_diam = float(input_data['pin_diam'])

    ext_force = float(input_data['ext_force'])
    ext_moment = float(input_data['ext_moment'])
    operating_time = input_data['operating_time']

    num_cycles_c = 200
    num_cycles_r = 40_000

    flange_type = input_select['flange_type']
    face_type = input_select['face_type']
    flange_steel = input_select['flange_steel']
    bolt_steel = input_select['bolt_steel']

    filename = f"{D_N_flange}_{pressure}_{D_n_flange}_{D_m_flange}_{h_flange}_{H_flange}_{pin_diam}_{pins_quantity}.xlsx"
    results_dict = {}
    if flange_type == 'one_one':
        s0 = (D_n_flange - D_int_flange) / 2
        s1 = (D_m_flange - D_int_flange) / 2
    if flange_type == 'zero_one':
        s0 = s1 = T_b

    continue_calc = (
            ((D_ext_flange / D_int_flange) <= 5.0) and
            ((2 * h_flange / (D_ext_flange - D_int_flange)) >= 0.25) and
            (((s1 - s0) / (H_flange - h_flange)) <= 0.4)
    )
    if ((s1 - s0) / (H_flange - h_flange)) >= 0.33:
        if D_m_flange != D_n_flange:
            continue_calc = False
            print('Втулка должна быть цилиндрической!')
        if H_flange - h_flange < 1.5 * s0:
            continue_calc = False
            print(f"Длина втулки не менее 1.5 * {s0} = {1.5 * s0}")

    print('Условие применимости расчета 1: ', (D_ext_flange / D_int_flange), ' <= ', 5.0)
    print('Условие применимости расчета 2: ', (2 * h_flange / (D_ext_flange - D_int_flange)), ' >= ', 0.25)
    print('Условие применимости расчета 3: ', ((s1 - s0) / (H_flange - h_flange)), ' <= ', 0.4)
    print()
    if continue_calc:
        try:
            gasket_params = get_gasket(pressure, D_N_flange, face_type)
            document = gasket_params.get("document", "")
            gasket_type = str(gasket_params.get("type", ""))
            D_gasket = gasket_params.get("D_outer")
            d_gasket = gasket_params.get("d_inner")
            q_obj = gasket_params.get("q_obj")
            m = gasket_params.get("m")
            K_obj = gasket_params.get("K_obj")
            gasket_thickness = gasket_params.get("thickness")
            gasket_material = gasket_params.get('material')
            E_p = gasket_params.get("E_p")
            q_obj_dop = gasket_params.get("q_obj_dop")

            shape = gasket_type_map.get((document, gasket_type)) or gasket_type_map.get(document)
            if shape is None:
                raise ValueError("Пока что нет данных по прокладкам для продолжения расчета в таких условиях")

            gasket_width = (D_gasket - d_gasket) / 2
            calc_funcs = {
                'ring': lambda gw, Dg: (gw if gw <= 15.0 else round(3.8 * math.sqrt(gw), 1),
                                        Dg - (gw if gw <= 15.0 else round(3.8 * math.sqrt(gw), 1))),
                'octagon': lambda gw, Dg: (round(gw / 4, 1), Dg - gw),
                'oval': lambda gw, Dg: (round(gw / 4, 1), Dg - gw),
            }

            gasket_eff_width, gasket_cal_diam = calc_funcs[shape](gasket_width, D_gasket)

            P_obj = round(0.5 * math.pi * gasket_cal_diam * gasket_eff_width * q_obj / 1000, 3)
            R_p = round(math.pi * gasket_cal_diam * gasket_eff_width * m * pressure / 1000, 3)

            bolt_area, bolts_area, stud_length, bolt_type, fasteners_data = get_bolt_area_and_size(pin_diam,
                                                                                                   pins_quantity,
                                                                                                   pressure,
                                                                                                   h_flange)  # 6.1

            Q_d = round(0.785 * gasket_cal_diam ** 2 * pressure / 1000, 3)

            Q_F_M = round(max(ext_force + 4 * abs(ext_moment) * 1000 / gasket_cal_diam,
                              ext_force - 4 * abs(ext_moment) * 1000 / gasket_cal_diam), 3)

            (E_bolt_20, E_bolt_T, alpha_bolt_20, alpha_bolt_T,
             sigma_b_bolt_20, sigma_b_bolt_T, sigma_y_bolt_20, sigma_y_bolt_T) = (
                get_steel_prop(bolt_steel, temperature))

            (E_flange_20, E_flange_T, alpha_flange_20, alpha_flange_T,
             sigma_b_flange_20, sigma_b_flange_T, sigma_y_flange_20, sigma_y_flange_T) = (
                get_steel_prop(flange_steel, temperature))

            f, b, e, gamma, alpha, alpha_m, C_F, D_priv_flange, lambda_, l_0, B_F, B_Y, B_Z, y_flange, B_V, x, B, koef_B_x, s_e = (
                get_hardness_flanges(flange_type, d_pins_flange, gasket_cal_diam, s0, D_int_flange,
                                     K_obj, gasket_thickness, gasket_material, E_p, gasket_width, pin_diam,
                                     pins_quantity, pressure, h_flange, bolt_steel, temperature, D_ext_flange,
                                     s1, H_flange, flange_steel, D_n_flange, m))

            Q_t = gamma * (alpha_flange_T * h_flange * (0.96 * temperature - 20) +
                           alpha_flange_T * h_flange * (0.96 * temperature - 20) -
                           alpha_bolt_T * (h_flange + h_flange) * (0.95 * temperature - 20)) / 1000
            P_b_1 = max(
                alpha * (Q_d + ext_force) + R_p + 4 * alpha_m * abs(ext_moment) * 1000 / gasket_cal_diam,
                alpha * (Q_d + ext_force) + R_p + 4 * alpha_m * abs(ext_moment) * 1000 / gasket_cal_diam - Q_t
            )

            allowed_stress_b_m, allowed_stress_b_r, n_T_b = get_allowed_stress_bolt(bolt_steel, temperature)
            allowed_stress_flange_m, allowed_stress_flange_r, allowed_stress_flange_T = (
                get_allowed_stress_flange(flange_steel, temperature))

            P_b_2 = max(
                P_obj,
                0.4 * bolts_area * max(allowed_stress_b_m, allowed_stress_b_r) / 1000
            )

            P_b_m = round(max(P_b_1, P_b_2), 3)
            P_b_r = round(
                P_b_m + (1 - alpha) * (Q_d + ext_force) + Q_t + 4 * (1 - alpha_m) * abs(ext_moment) * 1000 / gasket_cal_diam,
                3)

            c_flange, c_bolt = get_corrosion_thickness(operating_time, flange_steel, bolt_steel)
            bolt_corrosion_diam = math.sqrt(4 * bolt_area / math.pi) - 2 * c_bolt
            bolt_corrosion_area = math.pi * bolt_corrosion_diam ** 2 / 4
            bolts_corrosion_area = pins_quantity * bolt_corrosion_area

            stress_b_1 = P_b_m * 1000 / bolts_corrosion_area
            stress_b_2 = P_b_r * 1000 / bolts_corrosion_area

            q = max(P_b_m, P_b_r) * 1000 / (math.pi * gasket_cal_diam * gasket_width)

            is_bolt_true = False
            is_gasket_true = False

            if stress_b_1 <= allowed_stress_b_m and stress_b_2 <= allowed_stress_b_r:
                is_bolt_true = True
                print('Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m)
                print('Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r)
                print(f"Шпильки типа {bolt_type} удовлетворяют условиям прочности")
                print()
            else:
                print(f"Шпильки типа {bolt_type} НЕ удовлетворяют условиям прочности!!!")
                print()
            if document == 'ГОСТ 15180-86':
                if q <= q_obj_dop:
                    is_gasket_true = True
                    print('Прокладка: ', q, ' <= ', q_obj_dop)
                    print(f"Прокладка типа {gasket_type} по {document} удовлетворяет условию прочности")
                    print()
                else:
                    print('Прокладка: ', q, ' <= ', q_obj_dop)
                    print(f"Прокладка типа {gasket_type} по {document} НЕ удовлетворяет условию прочности!!!")
                    print()
            else:
                is_gasket_true = True
                print("Для стальных прокладок условие прочности не проверяется.")

            if is_bolt_true and is_gasket_true:
                M_M = C_F * P_b_m * b / 1000
                M_R = C_F * max(
                    P_b_r * b / 1000 + (Q_d + Q_F_M) * e / 1000,
                    abs(Q_d + Q_F_M) * e / 1000
                )
                stress_M_1 = None
                stress_M_0 = None

                if flange_type in ('zero_one', 'one_one'):
                    if flange_type == 'one_one':
                        stress_M_1 = M_M * 1e6 / (lambda_ * (s1 - c_flange) ** 2 * D_priv_flange)
                        stress_M_0 = f * stress_M_1
                    elif flange_type == 'zero_one':
                        stress_M_0 = stress_M_1 = M_M * 1e6 / (lambda_ * (s0 - c_flange) ** 2 * D_priv_flange)
                else:
                    raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                stress_M_R = (1.33 * B_F * h_flange + l_0) * M_M * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
                stress_M_T = B_Y * M_M * 1e6 / (h_flange ** 2 * D_int_flange) - B_Z * stress_M_R

                stress_R_1 = None
                stress_R_0 = None

                if flange_type in ('zero_one', 'one_one'):
                    if flange_type == 'one_one':
                        stress_R_1 = M_R * 1e6 / (lambda_ * (s1 - c_flange) ** 2 * D_priv_flange)
                        stress_R_0 = f * stress_R_1
                    elif flange_type == 'zero_one':
                        stress_R_0 = stress_R_1 = M_R * 1e6 / (lambda_ * (s0 - c_flange) ** 2 * D_priv_flange)
                else:
                    raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                stress_1MM_R = max(
                    (Q_d + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (D_int_flange + s1) * (s1 - c_flange)),
                    (Q_d + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (D_int_flange + s1) * (s1 - c_flange))
                )

                stress_0MM_R = max(
                    (Q_d + ext_force + 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (D_int_flange + s0) * (s0 - c_flange)),
                    (Q_d + ext_force - 4 * abs(ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (D_int_flange + s0) * (s0 - c_flange))
                )

                stress_0MO_R = pressure * D_int_flange / (2 * (s0 - c_flange))

                stress_R_R = (1.33 * B_F * h_flange + l_0) * M_R * 1e6 / (lambda_ * h_flange ** 2 * l_0 * D_int_flange)
                stress_R_T = B_Y * M_R * 1e6 / (h_flange ** 2 * D_int_flange) - B_Z * stress_R_R

                condition_43 = (max(
                    abs(stress_M_1 + stress_M_R),
                    abs(stress_M_1 + stress_M_T)
                ))
                print('Условие (43): ', condition_43, ' <= ', 1.3 * allowed_stress_flange_m)

                condition_44 = (max(
                    abs(stress_R_1 - stress_1MM_R + stress_R_R),
                    abs(stress_R_1 - stress_1MM_R + stress_R_T),
                    abs(stress_R_1 + stress_1MM_R)
                ))
                print('Условие (44): ', condition_44, ' <= ', 1.3 * allowed_stress_flange_m)

                condition_45 = stress_M_0
                print('Условие (45): ', condition_45, ' <= ', 1.3 * allowed_stress_flange_r)

                condition_46 = (max(
                    abs(max(stress_R_0 + stress_0MM_R, stress_R_0 - stress_0MM_R)),
                    abs(max(0.3 * stress_R_0 + stress_0MO_R, 0.3 * stress_R_0 - stress_0MO_R)),
                    abs(max(0.7 * stress_R_0 + (stress_0MM_R - stress_0MO_R),
                            0.7 * stress_R_0 - (stress_0MM_R - stress_0MO_R)))
                ))
                print('Условие (46): ', condition_46, ' <= ', 1.3 * allowed_stress_flange_r)

                condition_47 = (max(
                    abs(stress_M_0 + stress_M_R),
                    abs(stress_M_0 + stress_M_T)
                ))
                print('Условие (47): ', condition_47, ' <= ', 1.3 * allowed_stress_flange_m)

                condition_48 = (max(
                    abs(stress_R_0 - stress_0MM_R + stress_R_T),
                    abs(stress_R_0 - stress_0MM_R + stress_R_R),
                    abs(stress_R_0 + stress_0MM_R)
                ))
                print('Условие (48): ', condition_48, ' <= ', 1.3 * allowed_stress_flange_m)

                condition_53 = (max(stress_0MO_R, stress_0MM_R))
                print('Условие (53): ', condition_53, ' <= ', min(allowed_stress_flange_m, allowed_stress_flange_r))

                condition_54 = max(stress_M_R, stress_M_T)
                print('Условие (54): ', condition_54, ' <= ', min(allowed_stress_flange_m, allowed_stress_flange_r))

                condition_55 = max(stress_R_R, stress_R_T)
                print('Условие (55): ', condition_55, ' <= ', min(allowed_stress_flange_m, allowed_stress_flange_r))
                print()

                is_flange_11_true = False
                is_flange_01_true = False

                if flange_type in ('zero_one', 'one_one'):
                    if flange_type == 'one_one':
                        if (
                                condition_43 <= 1.3 * allowed_stress_flange_m and
                                condition_44 <= 1.3 * allowed_stress_flange_m and
                                condition_45 <= 1.3 * allowed_stress_flange_r and
                                condition_46 <= 1.3 * allowed_stress_flange_r and
                                condition_53 <= min(allowed_stress_flange_m, allowed_stress_flange_r)
                        ):
                            print(f'Фланец типа {flange_type} проверку статической прочности прошел')
                            print()
                            is_flange_11_true = True
                        else:
                            print(f'Фланец типа {flange_type} проверку статической прочности НЕ прошел!!!')
                            print()
                    elif flange_type == 'zero_one':
                        if (
                                condition_47 <= 1.3 * allowed_stress_flange_m and
                                condition_48 <= 1.3 * allowed_stress_flange_m and
                                condition_53 <= min(allowed_stress_flange_m, allowed_stress_flange_r) and
                                condition_54 <= min(allowed_stress_flange_m, allowed_stress_flange_r) and
                                condition_55 <= min(allowed_stress_flange_m, allowed_stress_flange_r)
                        ):
                            print(f'Фланец типа {flange_type} проверку статической прочности прошел')
                            print()
                            is_flange_01_true = True
                        else:
                            print(f'Фланец типа {flange_type} проверку статической прочности НЕ прошел!!!')
                            print()
                else:
                    raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                if is_flange_01_true or is_flange_11_true:
                    theta = M_R * y_flange * E_flange_20 / E_flange_T
                    if flange_type in ('zero_one', 'one_one'):
                        if flange_type == 'one_one':
                            if D_int_flange <= 400:
                                allowed_theta = 0.006
                            elif D_int_flange >= 2000:
                                allowed_theta = 0.013
                            else:
                                D_int_flange_1 = 400
                                D_int_flange_2 = 2000
                                allowed_theta_1 = 0.006
                                allowed_theta_2 = 0.013
                                allowed_theta = (allowed_theta_1 + (allowed_theta_2 - allowed_theta_1) *
                                                 (D_int_flange - D_int_flange_1) / (D_int_flange_2 - D_int_flange_1))
                        elif flange_type == 'zero_one':
                            allowed_theta = 0.013
                        else:
                            raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                        if theta <= allowed_theta:
                            print(f'Фланец типа {flange_type} проверку углов поворота при затяжке и раб. усл. прошел')
                            print()
                        else:
                            print(f'Фланец типа {flange_type} проверку углов поворота при затяжке и раб. усл. НЕ '
                                  f'прошел!!!')
                            print()

                    #  Приварные с конической втулкой
                    stress_M_1_1 = stress_M_1
                    stress_M_1_2 = -stress_M_1
                    stress_M_1_3 = stress_M_1_4 = stress_M_T
                    stress_M_1_5 = stress_M_1_6 = stress_M_R

                    #  Приварные и плоские
                    stress_M_0_1 = stress_M_0
                    stress_M_0_2 = -stress_M_0

                    #  Плоские и приварные с прямой втулкой
                    stress_M_0_3 = stress_M_0_4 = stress_M_T
                    stress_M_0_5 = stress_M_0_6 = stress_M_R

                    if flange_type == 'one_one':
                        stress_R_0_3 = stress_0MO_R + 0.3 * stress_R_0
                        stress_delta_R_0_3 = stress_0MO_R - 0.3 * stress_R_0
                        stress_R_0_4 = stress_0MO_R - 0.3 * stress_R_0
                        stress_delta_R_0_4 = stress_0MO_R + 0.3 * stress_R_0
                    elif flange_type == 'zero_one':
                        stress_R_0_3 = stress_R_0_4 = stress_R_T
                        stress_delta_R_0_3 = stress_delta_R_0_4 = stress_R_T
                    else:
                        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")

                    #  Плоские и приварные с прямой втулкой
                    stress_R_0_5 = stress_R_0_6 = stress_M_R
                    stress_delta_R_0_5 = stress_delta_R_0_6 = stress_M_R

                    if flange_type in ('zero_one', 'one_one'):
                        print("Провожу расчет на малоцикловую усталость")
                        if flange_type == 'one_one':
                            print(f"для фланца типа: {flange_type}")
                            if D_m_flange > D_n_flange:
                                if r / s1 <= 0.75:
                                    val_x_1 = r / s1
                                    alpha_sigma_1 = (114.63 * val_x_1 ** 6 - 342.10 * val_x_1 ** 5 +
                                                     418.49 * val_x_1 ** 4 - 276.59 * val_x_1 ** 3 +
                                                     111.30 * val_x_1 ** 2 - 28.286 * val_x_1 + 5.0888)
                                    stress_a = (  # Приварные с конической и прямой втулкой
                                            max(
                                                alpha_sigma_1 * abs(stress_M_1_1),
                                                abs(stress_M_1_2 - stress_M_1_4),
                                                abs(stress_M_1_2 - stress_M_1_6),
                                                abs(stress_M_0_1)
                                            ) / 2
                                        )
                                else:
                                    alpha_sigma_1 = 1.5
                                    stress_a = (  # Когда нет альфы
                                            max(
                                                alpha_sigma_1 * abs(stress_M_1_1),
                                                abs(stress_M_1_2 - stress_M_1_4),
                                                abs(stress_M_1_2 - stress_M_1_6),
                                                abs(stress_M_0_1)
                                            ) / 2
                                        )
                            if D_m_flange == D_n_flange:
                                if r / s0 <= 0.75:
                                    val_x_1 = r / s0
                                    alpha_sigma_1 = (114.63 * val_x_1 ** 6 - 342.10 * val_x_1 ** 5 +
                                                     418.49 * val_x_1 ** 4 - 276.59 * val_x_1 ** 3 +
                                                     111.30 * val_x_1 ** 2 - 28.286 * val_x_1 + 5.0888)
                                    stress_a = (  # Приварные с конической и прямой втулкой
                                            max(
                                                alpha_sigma_1 * abs(stress_M_0_1),
                                                abs(stress_M_0_2 - stress_M_0_4),
                                                abs(stress_M_0_2 - stress_M_0_6),
                                            ) / 2
                                        )
                                else:
                                    alpha_sigma_1 = 1.5
                                    stress_a = (  # Когда нет альфы
                                            max(
                                                alpha_sigma_1 * abs(stress_M_0_1),
                                                abs(stress_M_0_2 - stress_M_0_4),
                                                abs(stress_M_0_2 - stress_M_0_6),
                                            ) / 2
                                        )
                        elif flange_type == 'zero_one':
                            print(f"для фланца типа: {flange_type}")
                            alpha_sigma_1 = 1.5
                            stress_a = (  # Плоские
                                    alpha_sigma_1 * max(
                                        abs(stress_M_0_1),
                                        abs(stress_M_0_2 - stress_M_0_4),
                                        abs(stress_M_0_2 - stress_M_0_6)
                                    ) / 2
                                )
                        else:
                            stress_a = None
                            print("Расчет на малоцикловую усталость не произведен")

                        stress_R_a, stress_delta_data = get_delta_sigma(ext_force, ext_moment, pressure, Q_t, alpha, alpha_m,
                                                     gasket_cal_diam, gasket_eff_width,
                                                     m, P_b_2, bolts_corrosion_area, allowed_stress_b_r, C_F, b, e,
                                                     Q_F_M,
                                                     flange_type, lambda_, s1, s0, c_flange, D_priv_flange, f,
                                                     D_int_flange, B_F,
                                                     h_flange, l_0, B_Y, B_Z, alpha_sigma_1, D_m_flange, D_n_flange)

                        stress_a_bolt = 1.8 * stress_b_1 / 2
                        stress_R_a_bolt = 2.0 * stress_b_2 / 2

                        allowed_amplitude_flange_m, allowed_N_c_flange = (
                            get_allowed_amplitude(num_cycles_c, flange_steel, temperature, abs(stress_a)))
                        allowed_amplitude_flange_r, allowed_N_r_flange = (
                            get_allowed_amplitude(num_cycles_r, flange_steel, temperature, abs(stress_R_a)))

                        allowed_amplitude_bolt_m, allowed_N_c_bolt = (
                            get_allowed_amplitude(num_cycles_c, bolt_steel, temperature, abs(stress_a_bolt)))
                        allowed_amplitude_bolt_r, allowed_N_r_bolt = (
                            get_allowed_amplitude(num_cycles_r, bolt_steel, temperature, abs(stress_R_a_bolt)))

                        flange_cycles = num_cycles_c / allowed_N_c_flange + num_cycles_r / allowed_N_r_flange
                        bolt_cycles = num_cycles_c / allowed_N_c_bolt + num_cycles_r / allowed_N_r_bolt

                        print(stress_a, ' <= ', allowed_amplitude_flange_m)
                        print(stress_R_a, ' <= ', allowed_amplitude_flange_r)
                        print(flange_cycles, ' <= ', 1)
                        print(stress_a_bolt, ' <= ', allowed_amplitude_bolt_m)
                        print(stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r)
                        print(bolt_cycles, ' <= ', 1)
                        if (
                                stress_a_bolt <= allowed_amplitude_bolt_m and
                                stress_R_a_bolt <= allowed_amplitude_bolt_r and
                                bolt_cycles <= 1.0
                        ):
                            print(f"Шпильки типа {bolt_type} удовлетворяют расчету на малоцикловую усталость")
                            print()
                            is_cycles_bolt = True
                        else:
                            is_cycles_bolt = False
                            print(f'Шпильки типа {bolt_type} НЕ удовлетворяет расчету на малоцикловую усталость!!')
                        is_cycles_flange = False
                        if (
                                stress_a <= allowed_amplitude_flange_m and
                                stress_R_a <= allowed_amplitude_flange_r and
                                flange_cycles <= 1.0
                        ):
                            is_cycles_flange = True
                            print(f"Фланец типа {flange_type} удовлетворяет расчету на малоцикловую усталость")
                            print()

                        else:
                            is_cycles_bolt = False
                            print(f'Фланец типа {flange_type} НЕ удовлетворяет расчету на малоцикловую усталость!!')
                            print()

                        if is_cycles_bolt and is_cycles_flange:
                            results_dict = {
                                "gasket_params": gasket_params,
                                "fasteners_data": fasteners_data,
                                "stud_length": stud_length,
                                "sigma_b_flange_T": sigma_b_flange_T,
                                "sigma_y_flange_T": sigma_y_flange_T,
                                "sigma_b_bolt_T": sigma_b_bolt_T,
                                "sigma_y_bolt_T": sigma_y_bolt_T,
                                "E_bolt_20": E_bolt_20,
                                "E_bolt_T": E_bolt_T,
                                "E_flange_20": E_flange_20,
                                "E_flange_T": E_flange_T,
                                "alpha_bolt_20": alpha_bolt_20,
                                "alpha_bolt_T": alpha_bolt_T,
                                "alpha_flange_20": alpha_flange_20,
                                "alpha_flange_T": alpha_flange_T,
                                "flange_type": flange_type,
                                "face_type": face_type,
                                "flange_steel": flange_steel,
                                "bolt_steel": bolt_steel,
                                "D_N_flange": D_N_flange,
                                "pressure": pressure,
                                "temperature": temperature,
                                "D_ext_flange": D_ext_flange,
                                "D_int_flange": D_int_flange,
                                "r": r,
                                "d_pins_flange": d_pins_flange,
                                "pins_quantity": pins_quantity,
                                "pin_diam": pin_diam,
                                "bolt_area": bolt_area,
                                "ext_force": ext_force,
                                "ext_moment": ext_moment,
                                "operating_time": operating_time,
                                "h_flange": h_flange,
                                "H_flange": H_flange,
                                "D_n_flange": D_n_flange,
                                "D_m_flange": D_m_flange,
                                "c_flange": c_flange,
                                "c_bolt": c_bolt,
                                "Шпильки при затяжке: ": (
                                    'Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m),
                                "Шпильки при раб. усл.: ": (
                                    'Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r),
                                "Прокладка: ": ('Прокладка: ', q, ' <= ', q_obj_dop),
                                "Условие (43): ": (
                                    'Условие (43): ', condition_43, ' <= ', 1.3 * allowed_stress_flange_m),
                                "Условие (44): ": (
                                    'Условие (44): ', condition_44, ' <= ', 1.3 * allowed_stress_flange_m),
                                "Условие (45): ": (
                                    'Условие (45): ', condition_45, ' <= ', 1.3 * allowed_stress_flange_r),
                                "Условие (46): ": (
                                    'Условие (46): ', condition_46, ' <= ', 1.3 * allowed_stress_flange_r),
                                "Условие (47): ": (
                                    'Условие (47): ', condition_47, ' <= ', 1.3 * allowed_stress_flange_m),
                                "Условие (48): ": (
                                    'Условие (48): ', condition_48, ' <= ', 1.3 * allowed_stress_flange_m),
                                "Условие (53): ": ('Условие (53): ', condition_53, ' <= ',
                                                   min(allowed_stress_flange_m, allowed_stress_flange_r)),
                                "Условие (54): ": ('Условие (54): ', condition_54, ' <= ',
                                                   min(allowed_stress_flange_m, allowed_stress_flange_r)),
                                "Условие (55): ": ('Условие (55): ', condition_55, ' <= ',
                                                   min(allowed_stress_flange_m, allowed_stress_flange_r)),
                                "stress_a_bolt": (stress_a_bolt, ' <= ', allowed_amplitude_bolt_m),
                                "stress_R_a_bolt": (stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r),
                                "stress_a": (stress_a, ' <= ', allowed_amplitude_flange_m),
                                "stress_R_a": (stress_R_a, ' <= ', allowed_amplitude_flange_r),
                                "flange_cycles": (
                                    flange_cycles, allowed_N_c_flange, allowed_N_r_flange),
                                "bolt_cycles": (bolt_cycles, allowed_N_c_bolt, allowed_N_r_bolt),
                                "num_cycles_c": num_cycles_c,
                                "num_cycles_r": num_cycles_r,
                                "B_V": B_V,
                                "lambda_": lambda_,
                                "koef_B_x": koef_B_x,
                                "n_T_b": n_T_b,
                                "D_priv_flange": D_priv_flange,
                                "f": f,
                                "B_F": B_F,
                                "B_Y": B_Y,
                                "B_Z": B_Z,
                                "allowed_stress_flange_T": allowed_stress_flange_T,
                                "allowed_theta": allowed_theta,
                                "alpha_sigma_1": alpha_sigma_1,
                                "stress_delta_data": stress_delta_data,
                            }
                            df = pd.DataFrame([results_dict])
                            df.to_excel(filename, index=False)
                            print(
                                f"Добавлена комбинация c D_N: {D_n_flange}, D_m: {D_m_flange}, h: {h_flange}, H: {H_flange}")
                    else:
                        raise ValueError(f"Нет методики расчета фланцев типа: {flange_type}")
                else:
                    print("Условие прочности фланцев не выполняется")
            else:
                print(f"Условие прочности болтов: {is_bolt_true}, прокладки: {is_gasket_true}")

        except Exception as e:
            print(f"Ошибка: {e}")
    else:
        print("Данная методика не подходит для такого фланцевого соединения")

    return results_dict, T_b
