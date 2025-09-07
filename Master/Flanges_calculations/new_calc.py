from types import SimpleNamespace
import math
import bisect
import pandas as pd
from .gasket_data import (table_15180, table_34655, table_iso_7483, table_28759_8,
                          GASKET_SIZES_15180, GASKET_SIZES_34655, GASKET_SIZES_28759_8,
                          GASKET_SIZES_ISO_7483, gasket_params, gasket_type_map)
from .bolt_data import bolt_areas, bolts_data, nuts_data, washer_data
from .steel_prop_data import E_modulus_data_1, alpha_data_1, strength_data_1, yield_data_1, allowed_flange_data
from .graphs_data import (x_values_B_F, x_values_B_V, x_values_f,
                          B_F_values, B_V_values, f_values)


def new_calc_pre(input_data, input_select):
    all_data = {**input_data, **input_select}
    d = SimpleNamespace(**all_data)

    if d.flange_type == 'one_one':
        if d.D_m_flange > d.D_n_flange:
            s0 = (d.D_n_flange - d.D_int_flange) / 2
            s1 = (d.D_m_flange - d.D_int_flange) / 2
        elif d.D_m_flange == d.D_n_flange:
            s0 = s1 = ((d.D_m_flange or d.D_n_flange) - d.D_int_flange) / 2
        else:
            raise ValueError("Ошибка: D_m_flange < D_n_flange, что недопустимо")
    elif d.flange_type == 'zero_one':
        s0 = s1 = d.T_b
    else:
        raise ValueError("Ошибка: Такой фланец считать не умею.")

    continue_calc = (
            ((d.D_ext_flange / d.D_int_flange) <= 5.0) and
            ((2 * d.h_flange / (d.D_ext_flange - d.D_int_flange)) >= 0.25) and
            (((s1 - s0) / (d.H_flange - d.h_flange)) <= 0.4)
    )
    if ((s1 - s0) / (d.H_flange - d.h_flange)) >= 0.33:
        if d.D_m_flange != d.D_n_flange:
            continue_calc = False
            print('Ошибка: Втулка должна быть цилиндрической!')
        if d.H_flange - d.h_flange < 1.5 * s0:
            continue_calc = False
            print(f"Ошибка: Длина втулки должна быть не менее 1.5 * {s0} = {1.5 * s0}")
    print('Условие применимости расчета 1: ', (d.D_ext_flange / d.D_int_flange), ' <= ', 5.0)
    print('Условие применимости расчета 2: ', (2 * d.h_flange / (d.D_ext_flange - d.D_int_flange)), ' >= ', 0.25)
    print('Условие применимости расчета 3: ', ((s1 - s0) / (d.H_flange - d.h_flange)), ' <= ', 0.4)
    print()
    return continue_calc, s0, s1


def new_calc(input_data, input_select):
    all_data = {**input_data, **input_select}
    d = SimpleNamespace(**all_data)
    results_dict = {}

    continue_calc, s0, s1 = new_calc_pre(input_data, input_select)

    if continue_calc:
        try:
            gasket_parameters = get_gasket(d.pressure, d.D_N_flange, d.face_type)
            g = SimpleNamespace(**gasket_parameters)

            shape = gasket_type_map.get((g.document, g.type)) or gasket_type_map.get(g.document)
            if shape is None:
                raise ValueError("Пока что нет данных по прокладкам для продолжения расчета в таких условиях")

            gasket_width = (g.D_outer - g.d_inner) / 2
            calc_funcs = {
                'ring': lambda gw, Dg: (gw if gw <= 15.0 else round(3.8 * math.sqrt(gw), 1),
                                        Dg - (gw if gw <= 15.0 else round(3.8 * math.sqrt(gw), 1))),
                'octagon': lambda gw, Dg: (round(gw / 4, 1), Dg - gw),
                'oval': lambda gw, Dg: (round(gw / 4, 1), Dg - gw),
            }
            gasket_eff_width, gasket_cal_diam = calc_funcs[shape](gasket_width, g.D_outer)

            P_obj = round(0.5 * math.pi * gasket_cal_diam * gasket_eff_width * g.q_obj / 1000, 3)
            R_p = round(math.pi * gasket_cal_diam * gasket_eff_width * g.m * d.pressure / 1000, 3)

            (bolt_area, bolts_area, stud_length,
             bolt_type, fasteners_data) = get_bolt_area_and_size(d.pin_diam, d.pins_quantity, d.pressure, d.h_flange)

            Q_d = round(0.785 * gasket_cal_diam ** 2 * d.pressure / 1000, 3)

            Q_F_M = round(max(d.ext_force + 4 * abs(d.ext_moment) * 1000 / gasket_cal_diam,
                              d.ext_force - 4 * abs(d.ext_moment) * 1000 / gasket_cal_diam), 3)

            flange_steel_prop_data = get_steel_prop(d.flange_steel, d.temperature, 'flange')
            fs = SimpleNamespace(**flange_steel_prop_data)

            bolt_steel_prop_data = get_steel_prop(d.bolt_steel, d.temperature, 'bolt')
            bs = SimpleNamespace(**bolt_steel_prop_data)

            ductility_data = {
                "gasket_width": gasket_width,
                "gasket_cal_diam": gasket_cal_diam,
                "stud_length": stud_length,
                "bolts_area": bolts_area,
                "s0": s0,
                "s1": s1
            }

            hardness_data = get_hardness_flanges(all_data, gasket_parameters, flange_steel_prop_data,
                                                 bolt_steel_prop_data, ductility_data)
            h = SimpleNamespace(**hardness_data)

            Q_t = h.gamma * (fs.alpha_flange_T * d.h_flange * (0.96 * d.temperature - 20) +
                             fs.alpha_flange_T * d.h_flange * (0.96 * d.temperature - 20) -
                             bs.alpha_bolt_T * 2 * d.h_flange * (0.95 * d.temperature - 20)) / 1000

            P_b_1 = max(
                h.alpha * (Q_d + d.ext_force) + R_p + 4 * h.alpha_m * abs(d.ext_moment) * 1000 / gasket_cal_diam,
                h.alpha * (Q_d + d.ext_force) + R_p + 4 * h.alpha_m * abs(d.ext_moment) * 1000 / gasket_cal_diam - Q_t
            )

            allowed_stress_b_m, allowed_stress_b_r, n_T_b = get_allowed_stress_bolt(bolt_steel_prop_data)
            allowed_stress_flange_m, allowed_stress_flange_r, allowed_stress_flange_T = (
                get_allowed_stress_flange(d.flange_steel, d.temperature))

            P_b_2 = max(
                P_obj,
                0.4 * bolts_area * max(allowed_stress_b_m, allowed_stress_b_r) / 1000
            )

            P_b_m = round(max(P_b_1, P_b_2), 3)
            P_b_r = round(
                P_b_m + (1 - h.alpha) * (Q_d + d.ext_force) + Q_t + 4 * (1 - h.alpha_m) *
                abs(d.ext_moment) * 1000 / gasket_cal_diam, 3)

            c_flange, c_bolt = get_corrosion_thickness(d.operating_time, d.flange_steel, d.bolt_steel)
            bolt_corrosion_diam = math.sqrt(4 * bolt_area / math.pi) - 2 * c_bolt
            bolt_corrosion_area = math.pi * bolt_corrosion_diam ** 2 / 4
            bolts_corrosion_area = d.pins_quantity * bolt_corrosion_area

            stress_b_1 = P_b_m * 1000 / bolts_corrosion_area
            stress_b_2 = P_b_r * 1000 / bolts_corrosion_area

            q = max(P_b_m, P_b_r) * 1000 / (math.pi * gasket_cal_diam * gasket_width)

            is_bolt_true = False
            is_gasket_true = False

            if stress_b_1 <= allowed_stress_b_m and stress_b_2 <= allowed_stress_b_r:
                is_bolt_true = True
                print(f"Шпильки при затяжке: {stress_b_1:.2f} <= {allowed_stress_b_m:.2f}")
                print(f"Шпильки при рабочей нагрузке: {stress_b_2:.2f} <= {allowed_stress_b_r:.2f}")
                print(f"Шпильки типа {bolt_type} удовлетворяют условиям прочности\n")
            else:
                print(f"Шпильки при затяжке: {stress_b_1:.2f}, рабочие: {stress_b_2:.2f}")
                print(f"Шпильки типа {bolt_type} НЕ удовлетворяют условиям прочности!!!\n")

            if g.document == 'ГОСТ 15180-86':
                if q <= g.q_obj_dop:
                    is_gasket_true = True
                    print(f"Прокладка: {q:.2f} <= {g.q_obj_dop:.2f}")
                    print(f"Прокладка типа {g.type} по {g.document} удовлетворяет условию прочности\n")
                else:
                    print(f"Прокладка: {q:.2f} <= {g.q_obj_dop:.2f}")
                    print(f"Прокладка типа {g.type} по {g.document} НЕ удовлетворяет условию прочности!!!\n")
            else:
                is_gasket_true = True
                print("Для стальных прокладок условие прочности не проверяется.")

            if is_bolt_true and is_gasket_true:
                M_M = h.C_F * P_b_m * h.b / 1000
                M_R = h.C_F * max(
                    P_b_r * h.b / 1000 + (Q_d + Q_F_M) * h.e / 1000,
                    abs(Q_d + Q_F_M) * h.e / 1000
                )

                if d.flange_type == 'one_one':
                    stress_M_1 = M_M * 1e6 / (h.lambda_ * (s1 - c_flange) ** 2 * h.D_pr_flange)
                    stress_M_0 = h.f * stress_M_1
                    stress_R_1 = M_R * 1e6 / (h.lambda_ * (s1 - c_flange) ** 2 * h.D_pr_flange)
                    stress_R_0 = h.f * stress_R_1
                elif d.flange_type == 'zero_one':
                    stress_M_0 = stress_M_1 = M_M * 1e6 / (h.lambda_ * (s0 - c_flange) ** 2 * h.D_pr_flange)
                    stress_R_0 = stress_R_1 = M_R * 1e6 / (h.lambda_ * (s0 - c_flange) ** 2 * h.D_pr_flange)
                else:
                    raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")

                stress_M_R = ((1.33 * h.B_F * d.h_flange + h.l_0) * M_M * 1e6 /
                              (h.lambda_ * d.h_flange ** 2 * h.l_0 * d.D_int_flange))
                stress_M_T = h.B_Y * M_M * 1e6 / (d.h_flange ** 2 * d.D_int_flange) - h.B_Z * stress_M_R

                stress_1MM_R = max(
                    (Q_d + d.ext_force + 4 * abs(d.ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (d.D_int_flange + s1) * (s1 - c_flange)),
                    (Q_d + d.ext_force - 4 * abs(d.ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (d.D_int_flange + s1) * (s1 - c_flange)))

                stress_0MM_R = max(
                    (Q_d + d.ext_force + 4 * abs(d.ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (d.D_int_flange + s0) * (s0 - c_flange)),
                    (Q_d + d.ext_force - 4 * abs(d.ext_moment) / gasket_cal_diam / 1000) * 1000 / (
                            math.pi * (d.D_int_flange + s0) * (s0 - c_flange)))

                stress_0MO_R = d.pressure * d.D_int_flange / (2 * (s0 - c_flange))
                stress_R_R = ((1.33 * h.B_F * d.h_flange + h.l_0) * M_R * 1e6 /
                              (h.lambda_ * d.h_flange ** 2 * h.l_0 * d.D_int_flange))
                stress_R_T = h.B_Y * M_R * 1e6 / (d.h_flange ** 2 * d.D_int_flange) - h.B_Z * stress_R_R

                condition_43 = max(abs(stress_M_1 + stress_M_R), abs(stress_M_1 + stress_M_T))
                condition_44 = max(abs(stress_R_1 - stress_1MM_R + stress_R_R),
                                   abs(stress_R_1 - stress_1MM_R + stress_R_T),
                                   abs(stress_R_1 + stress_1MM_R))
                condition_45 = stress_M_0
                condition_46 = max(
                    abs(max(stress_R_0 + stress_0MM_R, stress_R_0 - stress_0MM_R)),
                    abs(max(0.3 * stress_R_0 + stress_0MO_R, 0.3 * stress_R_0 - stress_0MO_R)),
                    abs(max(0.7 * stress_R_0 + (stress_0MM_R - stress_0MO_R),
                            0.7 * stress_R_0 - (stress_0MM_R - stress_0MO_R)))
                )
                condition_47 = max(abs(stress_M_0 + stress_M_R), abs(stress_M_0 + stress_M_T))
                condition_48 = max(abs(stress_R_0 - stress_0MM_R + stress_R_T),
                                   abs(stress_R_0 - stress_0MM_R + stress_R_R),
                                   abs(stress_R_0 + stress_0MM_R))
                condition_53 = max(stress_0MO_R, stress_0MM_R)
                condition_54 = max(stress_M_R, stress_M_T)
                condition_55 = max(stress_R_R, stress_R_T)

                if d.flange_type == 'one_one':
                    if d.D_m_flange > d.D_n_flange:
                        is_flange_true = False
                        print(f"Условие (43): {condition_43} <= {1.3 * allowed_stress_flange_m}")
                        print(f"Условие (44): {condition_44} <= {1.3 * allowed_stress_flange_m}")
                        print(f"Условие (45): {condition_45} <= {1.3 * allowed_stress_flange_r}")
                        print(f"Условие (46): {condition_46} <= {1.3 * allowed_stress_flange_r}")
                        print(f"Условие (53): {condition_53} <= {allowed_stress_flange_T}")
                        print(f"Условие (54): {condition_54} <= {1.3 * allowed_stress_flange_T}")
                        print(f"Условие (55): {condition_55} <= {1.3 * allowed_stress_flange_T}\n")
                        if all([condition_43 <= 1.3 * allowed_stress_flange_m,
                                condition_44 <= 1.3 * allowed_stress_flange_m,
                                condition_45 <= 1.3 * allowed_stress_flange_r,
                                condition_46 <= 1.3 * allowed_stress_flange_r,
                                condition_53 <= allowed_stress_flange_T,
                                condition_54 <= 1.3 * allowed_stress_flange_T,
                                condition_55 <= 1.3 * allowed_stress_flange_T]):
                            print(f"Фланец типа {d.flange_type} проверку статической прочности прошел\n")
                            print(f"Условие (43): {condition_43} <= {1.3 * allowed_stress_flange_m}")
                            print(f"Условие (44): {condition_44} <= {1.3 * allowed_stress_flange_m}")
                            print(f"Условие (45): {condition_45} <= {1.3 * allowed_stress_flange_r}")
                            print(f"Условие (46): {condition_46} <= {1.3 * allowed_stress_flange_r}")
                            print(f"Условие (53): {condition_53} <= {allowed_stress_flange_T}")
                            print(f"Условие (54): {condition_54} <= {1.3 * allowed_stress_flange_T}")
                            print(f"Условие (55): {condition_55} <= {1.3 * allowed_stress_flange_T}\n")
                            is_flange_true = True
                        else:
                            print(f"Фланец типа {d.flange_type} проверку статической прочности НЕ прошел!!!\n")
                    elif d.D_m_flange == d.D_n_flange:
                        print(stress_M_0, stress_M_T)
                        print(stress_R_0, stress_0MM_R, stress_R_T),
                        print(f"Условие (47): {condition_47} <= {1.3 * allowed_stress_flange_m}")
                        print(f"Условие (48): {condition_48} <= {1.3 * allowed_stress_flange_m}")
                        print(f"Условие (53): {condition_53} <= {allowed_stress_flange_T}")
                        print(f"Условие (54): {condition_54} <= {1.3 * allowed_stress_flange_T}")
                        print(f"Условие (55): {condition_55} <= {1.3 * allowed_stress_flange_T}\n")
                        is_flange_true = False
                        if all([condition_47 <= 1.3 * allowed_stress_flange_m,
                                condition_48 <= 1.3 * allowed_stress_flange_m,
                                condition_53 <= allowed_stress_flange_T,
                                condition_54 <= 1.3 * allowed_stress_flange_T,
                                condition_55 <= 1.3 * allowed_stress_flange_T]):
                            print(f"Условие (47): {condition_47} <= {1.3 * allowed_stress_flange_m}")
                            print(f"Условие (48): {condition_48} <= {1.3 * allowed_stress_flange_m}")
                            print(f"Условие (53): {condition_53} <= {allowed_stress_flange_T}")
                            print(f"Условие (54): {condition_54} <= {1.3 * allowed_stress_flange_T}")
                            print(f"Условие (55): {condition_55} <= {1.3 * allowed_stress_flange_T}\n")
                            print(f"Фланец типа {d.flange_type} проверку статической прочности прошел\n")
                            is_flange_true = True
                    else:
                        raise ValueError("Ошибка: Такой фланец считать не умею.")
                elif d.flange_type == 'zero_one':
                    is_flange_true = False
                    print(f"Условие (47): {condition_47} <= {1.3 * allowed_stress_flange_m}")
                    print(f"Условие (48): {condition_48} <= {1.3 * allowed_stress_flange_m}")
                    print(f"Условие (53): {condition_53} <= {allowed_stress_flange_T}")
                    print(f"Условие (54): {condition_54} <= {1.3 * allowed_stress_flange_T}")
                    print(f"Условие (55): {condition_55} <= {1.3 * allowed_stress_flange_T}\n")
                    print(f"Фланец типа {d.flange_type} проверку статической прочности прошел\n")
                    if all([condition_47 <= 1.3 * allowed_stress_flange_m,
                            condition_48 <= 1.3 * allowed_stress_flange_m,
                            condition_53 <= allowed_stress_flange_T,
                            condition_54 <= 1.3 * allowed_stress_flange_T,
                            condition_55 <= 1.3 * allowed_stress_flange_T]):
                        print(f"Условие (47): {condition_47} <= {1.3 * allowed_stress_flange_m}")
                        print(f"Условие (48): {condition_48} <= {1.3 * allowed_stress_flange_m}")
                        print(f"Условие (53): {condition_53} <= {allowed_stress_flange_T}")
                        print(f"Условие (54): {condition_54} <= {1.3 * allowed_stress_flange_T}")
                        print(f"Условие (55): {condition_55} <= {1.3 * allowed_stress_flange_T}\n")
                        print(f"Фланец типа {d.flange_type} проверку статической прочности прошел\n")
                        is_flange_true = True
                else:
                    raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")

                if is_flange_true:
                    theta = M_R * 1e6 * h.y_flange * fs.E_flange_20 / fs.E_flange_T
                    if d.flange_type == 'one_one':
                        if d.D_int_flange <= 400:
                            allowed_theta = 0.006
                        elif d.D_int_flange >= 2000:
                            allowed_theta = 0.013
                        else:
                            D_i_f_1 = 400
                            D_i_f_2 = 2000
                            allowed_theta_1 = 0.006
                            allowed_theta_2 = 0.013
                            allowed_theta = round((allowed_theta_1 + (allowed_theta_2 - allowed_theta_1) *
                                                  (d.D_int_flange - D_i_f_1) / (D_i_f_2 - D_i_f_1)), 4)
                    elif d.flange_type == 'zero_one':
                        allowed_theta = 0.013
                    else:
                        raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")

                    if theta <= allowed_theta:
                        is_theta_true = True
                        print(f'Фланец типа {d.flange_type} проверку углов поворота при затяжке и раб. усл. прошел\n')
                        if is_theta_true:
                            delta_sigma_data = {
                                "Q_t": Q_t,
                                "Q_F_M": Q_F_M,
                                "gasket_width": gasket_width,
                                "gasket_eff_width": gasket_eff_width,
                                "gasket_cal_diam": gasket_cal_diam,
                                "P_b_2": P_b_2,
                                "bolts_corrosion_area": bolts_corrosion_area,
                                "allowed_stress_b_r": allowed_stress_b_r,
                                "s0": s0,
                                "s1": s1,
                                "c_flange": c_flange,
                            }
                            if d.flange_type == 'one_one':
                                if d.D_m_flange > d.D_n_flange:
                                    stress_M_1_1 = stress_M_1
                                    stress_M_1_2 = -stress_M_1
                                    stress_M_1_4 = stress_M_T
                                    stress_M_1_6 = stress_M_R
                                    stress_M_0_1 = stress_M_0

                                    alpha_sigma = get_alpha_sigma(d.r, s1)
                                    stress_a = max(
                                        alpha_sigma * abs(stress_M_1_1),
                                        abs(stress_M_1_2 - stress_M_1_4),
                                        abs(stress_M_1_2 - stress_M_1_6),
                                        abs(stress_M_0_1)) / 2

                                elif d.D_m_flange == d.D_n_flange:
                                    stress_M_0_1 = stress_M_0
                                    stress_M_0_2 = -stress_M_0
                                    stress_M_0_4 = stress_M_T
                                    stress_M_0_6 = stress_M_R

                                    alpha_sigma = get_alpha_sigma(d.r, s0)
                                    stress_a = max(
                                        alpha_sigma * abs(stress_M_0_1),
                                        abs(stress_M_0_2 - stress_M_0_4),
                                        abs(stress_M_0_2 - stress_M_0_6)) / 2

                                else:
                                    raise ValueError("Ошибка: Такой фланец считать не умею.")
                            elif d.flange_type == 'zero_one':
                                alpha_sigma = None
                                stress_M_0_1 = stress_M_0
                                stress_M_0_2 = -stress_M_0
                                stress_M_0_4 = stress_M_T
                                stress_M_0_6 = stress_M_R

                                stress_a = 1.5 * max(
                                    abs(stress_M_0_1),
                                    abs(stress_M_0_2 - stress_M_0_4),
                                    abs(stress_M_0_2 - stress_M_0_6)) / 2

                            else:
                                raise ValueError("Ошибка: Такой фланец считать не умею.")

                            stress_R_a, stress_delta_data = get_delta_sigma(all_data, gasket_parameters,
                                                                            hardness_data, delta_sigma_data)
                            print(stress_R_a, stress_delta_data)

                            stress_a_bolt = 1.8 * stress_b_1 / 2
                            stress_R_a_bolt = 2.0 * stress_b_2 / 2

                            allowed_amplitude_flange_m, allowed_N_c_flange = (
                                get_allowed_amplitude(d.num_cycles_c, d.flange_steel, fs.sigma_y_flange_T,
                                                      d.temperature, abs(stress_a)))
                            allowed_amplitude_flange_r, allowed_N_r_flange = (
                                get_allowed_amplitude(d.num_cycles_r, d.flange_steel, fs.sigma_y_flange_T,
                                                      d.temperature, abs(stress_R_a)))
                            allowed_amplitude_bolt_m, allowed_N_c_bolt = (
                                get_allowed_amplitude(d.num_cycles_c, d.bolt_steel, bs.sigma_y_bolt_T,
                                                      d.temperature, abs(stress_a_bolt)))
                            allowed_amplitude_bolt_r, allowed_N_r_bolt = (
                                get_allowed_amplitude(d.num_cycles_r, d.bolt_steel, bs.sigma_y_bolt_T,
                                                      d.temperature, abs(stress_R_a_bolt)))

                            condition_cycles = (d.num_cycles_c / (allowed_N_c_flange + allowed_N_c_bolt) +
                                                d.num_cycles_r / (allowed_N_r_flange + allowed_N_r_bolt))

                            if all([stress_a_bolt <= allowed_amplitude_bolt_m,
                                    stress_R_a_bolt <= allowed_amplitude_bolt_r,
                                    stress_a <= allowed_amplitude_flange_m,
                                    stress_R_a <= allowed_amplitude_flange_r,
                                    condition_cycles <= 1.0]):
                                is_cycles = True
                                print(f"Шпильки типа {bolt_type} удовлетворяют расчету на малоцикловую усталость\n")
                                print(f"Фланец типа {d.flange_type} удовлетворяет расчету на малоцикловую усталость\n")
                            else:
                                is_cycles = False
                                print(f'Шпильки типа {bolt_type} НЕ удовлетворяет расчету на малоцикловую усталость!\n')
                                print(f'Фланец типа {d.flange_type} НЕ удовлетворяет расчету на малоцикловую '
                                      f'усталость!\n')

                            if is_cycles:
                                if d.flange_type == 'one_one':
                                    if d.D_m_flange > d.D_n_flange:
                                        results_dict = {
                                            "gasket_params": gasket_parameters,
                                            "fasteners_data": fasteners_data,
                                            "stud_length": stud_length,
                                            "sigma_b_flange_T": fs.sigma_b_flange_T,
                                            "sigma_y_flange_T": fs.sigma_y_flange_T,
                                            "sigma_b_bolt_T": bs.sigma_b_bolt_T,
                                            "sigma_y_bolt_T": bs.sigma_y_bolt_T,
                                            "E_bolt_20": bs.E_bolt_20,
                                            "E_bolt_T": bs.E_bolt_T,
                                            "E_flange_20": fs.E_flange_20,
                                            "E_flange_T": fs.E_flange_T,
                                            "alpha_bolt_20": bs.alpha_bolt_20,
                                            "alpha_bolt_T": bs.alpha_bolt_T,
                                            "alpha_flange_20": fs.alpha_flange_20,
                                            "alpha_flange_T": fs.alpha_flange_T,
                                            "flange_type": d.flange_type,
                                            "face_type": d.face_type,
                                            "flange_steel": d.flange_steel,
                                            "bolt_steel": d.bolt_steel,
                                            "D_N_flange": d.D_N_flange,
                                            "pressure": d.pressure,
                                            "temperature": d.temperature,
                                            "D_ext_flange": d.D_ext_flange,
                                            "D_int_flange": d.D_int_flange,
                                            "r": d.r,
                                            "d_pins_flange": d.d_pins_flange,
                                            "pins_quantity": d.pins_quantity,
                                            "pin_diam": d.pin_diam,
                                            "bolt_area": bolt_area,
                                            "ext_force": d.ext_force,
                                            "ext_moment": d.ext_moment,
                                            "operating_time": d.operating_time,
                                            "h_flange": d.h_flange,
                                            "H_flange": d.H_flange,
                                            "D_n_flange": d.D_n_flange,
                                            "D_m_flange": d.D_m_flange,
                                            "c_flange": c_flange,
                                            "c_bolt": c_bolt,
                                            "Шпильки при затяжке: ": (
                                                'Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m),
                                            "Шпильки при раб. усл.: ": (
                                                'Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r),
                                            "Прокладка: ": ('Прокладка: ', q, ' <= ', g.q_obj_dop),
                                            "Условие (43): ": (
                                                'Условие (43): ', condition_43, ' <= ', 1.3 * allowed_stress_flange_m),
                                            "Условие (44): ": (
                                                'Условие (44): ', condition_44, ' <= ', 1.3 * allowed_stress_flange_m),
                                            "Условие (45): ": (
                                                'Условие (45): ', condition_45, ' <= ', 1.3 * allowed_stress_flange_r),
                                            "Условие (46): ": (
                                                'Условие (46): ', condition_46, ' <= ', 1.3 * allowed_stress_flange_r),
                                            "Условие (53): ":
                                                ('Условие (53): ', condition_53, ' <= ', allowed_stress_flange_T),
                                            "Условие (54): ":
                                                ('Условие (54): ', condition_54, ' <= ', 1.3 * allowed_stress_flange_T),
                                            "Условие (55): ":
                                                ('Условие (55): ', condition_55, ' <= ', 1.3 * allowed_stress_flange_T),
                                            "stress_a_bolt": (stress_a_bolt, ' <= ', allowed_amplitude_bolt_m),
                                            "stress_R_a_bolt": (stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r),
                                            "stress_a": (stress_a, ' <= ', allowed_amplitude_flange_m),
                                            "stress_R_a": (stress_R_a, ' <= ', allowed_amplitude_flange_r),
                                            "allowed_amplitude_bolt_m": allowed_amplitude_bolt_m,
                                            "allowed_amplitude_bolt_r": allowed_amplitude_bolt_r,
                                            "allowed_amplitude_flange_m": allowed_amplitude_flange_m,
                                            "allowed_amplitude_flange_r": allowed_amplitude_flange_r,
                                            "c_cycles": (allowed_N_c_flange + allowed_N_c_bolt),
                                            "r_cycles": (allowed_N_r_flange + allowed_N_r_bolt),
                                            "condition_cycles": condition_cycles,
                                            "num_cycles_c": d.num_cycles_c,
                                            "num_cycles_r": d.num_cycles_r,
                                            "B_V": h.B_V,
                                            "lambda_": h.lambda_,
                                            "ko_ef_B_x": h.ko_ef_B_x,
                                            "D_pr_flange": h.D_pr_flange,
                                            "f": h.f,
                                            "B_F": h.B_F,
                                            "B_Y": h.B_Y,
                                            "B_Z": h.B_Z,
                                            "allowed_stress_flange_T": allowed_stress_flange_T,
                                            "allowed_stress_flange_m": allowed_stress_flange_m,
                                            "allowed_stress_flange_r": allowed_stress_flange_r,
                                            "allowed_theta": allowed_theta,
                                            "stress_delta_data": stress_delta_data,
                                            "T_b": d.T_b,
                                            "n_T_b": n_T_b,
                                            "alpha_sigma": alpha_sigma,
                                        }
                                    elif d.D_m_flange == d.D_n_flange:
                                        results_dict = {
                                            "gasket_params": gasket_parameters,
                                            "fasteners_data": fasteners_data,
                                            "stud_length": stud_length,
                                            "sigma_b_flange_T": fs.sigma_b_flange_T,
                                            "sigma_y_flange_T": fs.sigma_y_flange_T,
                                            "sigma_b_bolt_T": bs.sigma_b_bolt_T,
                                            "sigma_y_bolt_T": bs.sigma_y_bolt_T,
                                            "E_bolt_20": bs.E_bolt_20,
                                            "E_bolt_T": bs.E_bolt_T,
                                            "E_flange_20": fs.E_flange_20,
                                            "E_flange_T": fs.E_flange_T,
                                            "alpha_bolt_20": bs.alpha_bolt_20,
                                            "alpha_bolt_T": bs.alpha_bolt_T,
                                            "alpha_flange_20": fs.alpha_flange_20,
                                            "alpha_flange_T": fs.alpha_flange_T,
                                            "flange_type": d.flange_type,
                                            "face_type": d.face_type,
                                            "flange_steel": d.flange_steel,
                                            "bolt_steel": d.bolt_steel,
                                            "D_N_flange": d.D_N_flange,
                                            "pressure": d.pressure,
                                            "temperature": d.temperature,
                                            "D_ext_flange": d.D_ext_flange,
                                            "D_int_flange": d.D_int_flange,
                                            "r": d.r,
                                            "d_pins_flange": d.d_pins_flange,
                                            "pins_quantity": d.pins_quantity,
                                            "pin_diam": d.pin_diam,
                                            "bolt_area": bolt_area,
                                            "ext_force": d.ext_force,
                                            "ext_moment": d.ext_moment,
                                            "operating_time": d.operating_time,
                                            "h_flange": d.h_flange,
                                            "H_flange": d.H_flange,
                                            "D_n_flange": d.D_n_flange,
                                            "D_m_flange": d.D_m_flange,
                                            "c_flange": c_flange,
                                            "c_bolt": c_bolt,
                                            "Шпильки при затяжке: ": (
                                                'Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m),
                                            "Шпильки при раб. усл.: ": (
                                                'Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r),
                                            "Прокладка: ": ('Прокладка: ', q, ' <= ', g.q_obj_dop),
                                            "Условие (47): ": (
                                                'Условие (47): ', condition_47, ' <= ', 1.3 * allowed_stress_flange_m),
                                            "Условие (48): ": (
                                                'Условие (48): ', condition_48, ' <= ', 1.3 * allowed_stress_flange_m),
                                            "Условие (53): ":
                                                ('Условие (53): ', condition_53, ' <= ', allowed_stress_flange_T),
                                            "Условие (54): ":
                                                ('Условие (54): ', condition_54, ' <= ', 1.3 * allowed_stress_flange_T),
                                            "Условие (55): ":
                                                ('Условие (55): ', condition_55, ' <= ', 1.3 * allowed_stress_flange_T),
                                            "stress_a_bolt": (stress_a_bolt, ' <= ', allowed_amplitude_bolt_m),
                                            "stress_R_a_bolt": (stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r),
                                            "stress_a": (stress_a, ' <= ', allowed_amplitude_flange_m),
                                            "stress_R_a": (stress_R_a, ' <= ', allowed_amplitude_flange_r),
                                            "allowed_amplitude_bolt_m": allowed_amplitude_bolt_m,
                                            "allowed_amplitude_bolt_r": allowed_amplitude_bolt_r,
                                            "allowed_amplitude_flange_m": allowed_amplitude_flange_m,
                                            "allowed_amplitude_flange_r": allowed_amplitude_flange_r,
                                            "c_cycles": (allowed_N_c_flange + allowed_N_c_bolt),
                                            "r_cycles": (allowed_N_r_flange + allowed_N_r_bolt),
                                            "condition_cycles": condition_cycles,
                                            "num_cycles_c": d.num_cycles_c,
                                            "num_cycles_r": d.num_cycles_r,
                                            "B_V": h.B_V,
                                            "lambda_": h.lambda_,
                                            "ko_ef_B_x": h.ko_ef_B_x,
                                            "D_pr_flange": h.D_pr_flange,
                                            "f": h.f,
                                            "B_F": h.B_F,
                                            "B_Y": h.B_Y,
                                            "B_Z": h.B_Z,
                                            "allowed_stress_flange_T": allowed_stress_flange_T,
                                            "allowed_stress_flange_m": allowed_stress_flange_m,
                                            "allowed_stress_flange_r": allowed_stress_flange_r,
                                            "allowed_theta": allowed_theta,
                                            "stress_delta_data": stress_delta_data,
                                            "T_b": d.T_b,
                                            "n_T_b": n_T_b,
                                            "alpha_sigma": alpha_sigma,
                                        }
                                    else:
                                        raise ValueError("Ошибка: Такой фланец считать не умею.")
                                elif d.flange_type == 'zero_one':
                                    results_dict = {
                                        "gasket_params": gasket_parameters,
                                        "fasteners_data": fasteners_data,
                                        "stud_length": stud_length,
                                        "sigma_b_flange_T": fs.sigma_b_flange_T,
                                        "sigma_y_flange_T": fs.sigma_y_flange_T,
                                        "sigma_b_bolt_T": bs.sigma_b_bolt_T,
                                        "sigma_y_bolt_T": bs.sigma_y_bolt_T,
                                        "E_bolt_20": bs.E_bolt_20,
                                        "E_bolt_T": bs.E_bolt_T,
                                        "E_flange_20": fs.E_flange_20,
                                        "E_flange_T": fs.E_flange_T,
                                        "alpha_bolt_20": bs.alpha_bolt_20,
                                        "alpha_bolt_T": bs.alpha_bolt_T,
                                        "alpha_flange_20": fs.alpha_flange_20,
                                        "alpha_flange_T": fs.alpha_flange_T,
                                        "flange_type": d.flange_type,
                                        "face_type": d.face_type,
                                        "flange_steel": d.flange_steel,
                                        "bolt_steel": d.bolt_steel,
                                        "D_N_flange": d.D_N_flange,
                                        "pressure": d.pressure,
                                        "temperature": d.temperature,
                                        "D_ext_flange": d.D_ext_flange,
                                        "D_int_flange": d.D_int_flange,
                                        "r": d.r,
                                        "d_pins_flange": d.d_pins_flange,
                                        "pins_quantity": d.pins_quantity,
                                        "pin_diam": d.pin_diam,
                                        "bolt_area": bolt_area,
                                        "ext_force": d.ext_force,
                                        "ext_moment": d.ext_moment,
                                        "operating_time": d.operating_time,
                                        "h_flange": d.h_flange,
                                        "H_flange": d.H_flange,
                                        "D_n_flange": d.D_n_flange,
                                        "D_m_flange": d.D_m_flange,
                                        "c_flange": c_flange,
                                        "c_bolt": c_bolt,
                                        "Шпильки при затяжке: ": (
                                            'Шпильки при затяжке: ', stress_b_1, ' <= ', allowed_stress_b_m),
                                        "Шпильки при раб. усл.: ": (
                                            'Шпильки при раб. усл.: ', stress_b_2, ' <= ', allowed_stress_b_r),
                                        "Прокладка: ": ('Прокладка: ', q, ' <= ', g.q_obj_dop),
                                        "Условие (47): ": (
                                            'Условие (47): ', condition_47, ' <= ', 1.3 * allowed_stress_flange_m),
                                        "Условие (48): ": (
                                            'Условие (48): ', condition_48, ' <= ', 1.3 * allowed_stress_flange_m),
                                        "Условие (53): ":
                                            ('Условие (53): ', condition_53, ' <= ', allowed_stress_flange_T),
                                        "Условие (54): ":
                                            ('Условие (54): ', condition_54, ' <= ', 1.3 * allowed_stress_flange_T),
                                        "Условие (55): ":
                                            ('Условие (55): ', condition_55, ' <= ', 1.3 * allowed_stress_flange_T),
                                        "stress_a_bolt": (stress_a_bolt, ' <= ', allowed_amplitude_bolt_m),
                                        "stress_R_a_bolt": (stress_R_a_bolt, ' <= ', allowed_amplitude_bolt_r),
                                        "stress_a": (stress_a, ' <= ', allowed_amplitude_flange_m),
                                        "stress_R_a": (stress_R_a, ' <= ', allowed_amplitude_flange_r),
                                        "allowed_amplitude_bolt_m": allowed_amplitude_bolt_m,
                                        "allowed_amplitude_bolt_r": allowed_amplitude_bolt_r,
                                        "allowed_amplitude_flange_m": allowed_amplitude_flange_m,
                                        "allowed_amplitude_flange_r": allowed_amplitude_flange_r,
                                        "c_cycles": (allowed_N_c_flange + allowed_N_c_bolt),
                                        "r_cycles": (allowed_N_r_flange + allowed_N_r_bolt),
                                        "condition_cycles": condition_cycles,
                                        "num_cycles_c": d.num_cycles_c,
                                        "num_cycles_r": d.num_cycles_r,
                                        "B_V": h.B_V,
                                        "lambda_": h.lambda_,
                                        "ko_ef_B_x": h.ko_ef_B_x,
                                        "D_pr_flange": h.D_pr_flange,
                                        "f": h.f,
                                        "B_F": h.B_F,
                                        "B_Y": h.B_Y,
                                        "B_Z": h.B_Z,
                                        "allowed_stress_flange_T": allowed_stress_flange_T,
                                        "allowed_stress_flange_m": allowed_stress_flange_m,
                                        "allowed_stress_flange_r": allowed_stress_flange_r,
                                        "allowed_theta": allowed_theta,
                                        "stress_delta_data": stress_delta_data,
                                        "T_b": d.T_b,
                                        "n_T_b": n_T_b,
                                        "alpha_sigma": alpha_sigma,
                                    }
                                else:
                                    raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")
                                df = pd.DataFrame([results_dict])
                                filename = (f'Фланец DN_{d.D_N_flange} PN_{int(d.pressure * 10)}_{d.flange_steel}'
                                            f'_{d.bolt_steel} Dн_{d.D_ext_flange} Dвн_{d.D_int_flange}.xlsx')
                                df.to_excel(filename, index=False)
                                print(
                                    f"Добавлена комбинация c D_N: {d.D_n_flange}, D_m: {d.D_m_flange},"
                                    f" h: {d.h_flange}, H: {d.H_flange}")
                                return results_dict
                            else:
                                raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")
                        else:
                            raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")
                    else:
                        print(f'Фланец типа {d.flange_type} проверку углов поворота при затяжке и раб. усл. НЕ '
                              f'прошел!!!\n')
                else:
                    print("Условие статической прочности фланцев не выполняется")
            else:
                print(f"Условие прочности болтов: {is_bolt_true}, прокладки: {is_gasket_true}")
        except Exception as e:
            raise ValueError(f"Ошибка: {e}")
    return results_dict


def get_gasket(pressure, D_N_flange, face_type):
    gasket_sizes = {}

    def add_gasket_params(gasket_sizes_dict, material, gasket_parameters):
        for i, mat in enumerate(gasket_parameters['material']):
            if mat == material:
                gasket_sizes_dict.update({
                    'm': gasket_parameters['m'][i],
                    'q_obj': gasket_parameters['q_obj'][i],
                    'q_obj_dop': gasket_parameters['q_obj_dop'][i],
                    'K_obj': gasket_parameters['K_obj'][i],
                    'E_p': gasket_parameters['E_p'][i]
                })
                break

    standards = [
        ("ГОСТ 15180-86", table_15180, GASKET_SIZES_15180, gasket_params,
         ["D_outer", "d_inner", "thickness", "material"]),
        ("ГОСТ 34655-2020", table_34655, GASKET_SIZES_34655, gasket_params,
         ["D_outer", "d_inner", "thickness", "radius_or_height_1", "material"]),
        ("ISO 7483-2011", table_iso_7483, GASKET_SIZES_ISO_7483, gasket_params,
         ["D_outer", "d_inner", "thickness", "radius_or_width_c", "material"]),
        ("ГОСТ 28759.8-2022", table_28759_8, GASKET_SIZES_28759_8, gasket_params,
         ["D_outer", "d_inner", "thickness", "radius_or_height_1", "material"]),
    ]
    for doc_name, table, sizes_dict, g_params, keys in standards:
        gasket_type = None
        for row in table:
            if (row["p_min"] < float(pressure) <= row["p_max"]
                    and row["dn_min"] <= int(D_N_flange) <= row["dn_max"]
                    and (row["face_type"] is None or face_type in row["face_type"])):
                gasket_type = row["type"]
                break

        if gasket_type in sizes_dict:
            for size_data in sizes_dict[gasket_type]:
                dy, p_range, *rest = size_data
                low, high = p_range
                if int(dy) == int(D_N_flange) and low <= float(pressure) <= high:
                    gasket_sizes = {
                        "document": doc_name,
                        "type": gasket_type,
                        "dy": dy,
                        **dict(zip(keys, rest))
                    }
                    add_gasket_params(gasket_sizes, rest[-1], g_params)

    return gasket_sizes


def get_bolt_area_and_size(pin_diam, pins_quantity, pressure, h_flange):
    if pin_diam not in bolt_areas:
        raise ValueError(f"Неизвестный диаметр: {pin_diam} мм")
    if pressure <= 4.0:
        bolt_type, key = "1", "без_проточки"
    elif pressure <= 16.0:
        bolt_type, key = "2", "с_проточкой"
    else:
        raise ValueError("Давление выше 16 МПа не поддерживается.")

    bolt_area = bolt_areas[pin_diam][key]
    bolts_area = pins_quantity * bolt_area

    nut_height = nuts_data[pin_diam][1]
    washer_thickness = washer_data[pin_diam][2]

    required_length = 2 * (nut_height + washer_thickness + h_flange)

    bolt_entry = next((b for b in bolts_data[bolt_type] if b[0] == pin_diam), None)
    if not bolt_entry:
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


def get_steel_prop(steel_grade: str, temperature: float, part: str):
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
            raise ValueError(f"Марка стали '{steel_grade}' не найдена в {name}.")
        data = table[steel_grade]

        val20 = round(data[20] * scale, round_digits)

        if temperature in data:
            valT = data[temperature] * scale
        else:
            temps = sorted(k for k in data.keys() if isinstance(k, (int, float)))
            if temperature < temps[0] or temperature > temps[-1]:
                raise ValueError(f"Температура {temperature}°C вне диапазона данных для {steel_grade} ({name})")
            pos = bisect.bisect_left(temps, temperature)
            t1, t2 = temps[pos - 1], temps[pos]
            v1, v2 = data[t1], data[t2]
            valT = round((v1 + (v2 - v1) * (temperature - t1) / (t2 - t1)) * scale, round_digits)

        results[f"{name}_{part}_20"] = val20
        results[f"{name}_{part}_T"] = valT

    return results


def get_ductility(all_data, gasket_parameters, flange_steel_prop_data, bolt_steel_prop_data, ductility_data):
    def interpolate(value, points):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if x1 <= value <= x2:
                return y1 + (y2 - y1) * (value - x1) / (x2 - x1)
        return None

    d = SimpleNamespace(**all_data)
    g = SimpleNamespace(**gasket_parameters)
    fs = SimpleNamespace(**flange_steel_prop_data)
    bs = SimpleNamespace(**bolt_steel_prop_data)
    dt_l = SimpleNamespace(**ductility_data)
    if g.material in ('Паронит по ГОСТ 481-80', 'Фторопласт-4 или лента ПН по ГОСТ 24222-80',
                      'Уплотнительный материал ФУМ-В', 'Листовая резина тип 1 по ГОСТ 7338-77'):
        if g.material == 'Листовая резина тип 1 по ГОСТ 7338-77':
            E_p = 0.3e-5 * (1 + dt_l.gasket_width / (2 * g.thickness))
            y_p = g.thickness * g.K_obj / (E_p * math.pi * dt_l.gasket_cal_diam * dt_l.gasket_width)
        else:
            y_p = g.thickness * g.K_obj / (g.E_p * math.pi * dt_l.gasket_cal_diam * dt_l.gasket_width)
    else:
        y_p = 0.0

    L_b = dt_l.stud_length + 0.56 * d.pin_diam
    y_b = L_b / (bs.E_bolt_20 * dt_l.bolts_area)

    l_0 = math.sqrt(d.D_int_flange * dt_l.s0)
    K = d.D_ext_flange / d.D_int_flange
    B = dt_l.s1 / dt_l.s0
    x = d.H_flange / l_0

    B_T = (K ** 2 * (1 + 8.55 * math.log10(K)) - 1) / ((1.05 + 1.945 * K ** 2) * (K - 1))
    B_U = (K ** 2 * (1 + 8.55 * math.log10(K)) - 1) / (1.36 * (K ** 2 - 1) * (K - 1))
    B_Y = (1 / (K - 1)) * (0.69 + 5.72 * (K ** 2 * math.log10(K) / (K ** 2 - 1)))
    B_Z = (K ** 2 + 1) / (K ** 2 - 1)

    f = 1.0
    if B == 1.0:
        B_F, B_V = 0.91, 0.55
    else:
        x_B_F = min(x_values_B_F, key=lambda v: abs(v - x))
        x_B_V = min(x_values_B_V, key=lambda v: abs(v - x))
        x_f = min(x_values_f, key=lambda v: abs(v - x))

        B_F = interpolate(B, B_F_values[x_B_F])
        B_V = interpolate(B, B_V_values[x_B_V])
        f_val = interpolate(B, f_values[x_f])
        if f_val is not None:
            f = f_val

    lambda_ = (B_F * d.h_flange + l_0) / (B_T * l_0) + B_V * d.h_flange ** 3 / (B_U * l_0 * dt_l.s0 ** 2)

    y_flange = 0.91 * B_V / (fs.E_flange_20 * lambda_ * dt_l.s0 ** 2 * l_0)
    y_flange_n = (math.pi / 4) ** 3 * d.d_pins_flange / (fs.E_flange_20 * d.D_n_flange * d.h_flange ** 3)

    C_F = max(
        1.0,
        math.sqrt((math.pi * d.d_pins_flange / d.pins_quantity) / (2 * d.pin_diam + 6 * d.h_flange / (g.m + 0.5)))
    )

    if d.flange_type == 'one_one':
        if d.D_int_flange >= 20 * dt_l.s1:
            D_pr_flange = d.D_int_flange
        elif d.D_int_flange < 20 * dt_l.s1 and f > 1.0:
            D_pr_flange = d.D_int_flange + dt_l.s0
        elif d.D_int_flange < 20 * dt_l.s1 and f == 1.0:
            D_pr_flange = d.D_int_flange + dt_l.s1
        else:
            raise ValueError(f"Невозможно вычислить приведенный диаметр для фланца типа: {d.flange_type}")
    elif d.flange_type == 'zero_one':
        D_pr_flange = d.D_int_flange
    else:
        raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")

    result_dict = {
        "f": f, "x": x, "B": B, "y_p": y_p, "y_b": y_b,
        "y_flange": y_flange, "y_flange_n": y_flange_n,
        "C_F": C_F, "D_pr_flange": D_pr_flange,
        "lambda_": lambda_, "l_0": l_0,
        "B_F": B_F, "B_Y": B_Y, "B_Z": B_Z, "B_V": B_V
    }
    return result_dict


def get_hardness_flanges(all_data, gasket_parameters, flange_steel_prop_data, bolt_steel_prop_data, ductility_data):
    ductility_result = get_ductility(all_data, gasket_parameters, flange_steel_prop_data,
                                     bolt_steel_prop_data, ductility_data)
    d = SimpleNamespace(**all_data)
    fs = SimpleNamespace(**flange_steel_prop_data)
    bs = SimpleNamespace(**bolt_steel_prop_data)
    dt_l = SimpleNamespace(**ductility_data)
    dt_lr = SimpleNamespace(**ductility_result)

    b = 0.5 * (d.d_pins_flange - dt_l.gasket_cal_diam)
    ko_ef_B_x = 1 + (dt_lr.B - 1) * (dt_lr.x / (dt_lr.x + ((1 + dt_lr.B) / 4)))

    s_e = dt_l.s0 if d.flange_type == 'zero_one' else ko_ef_B_x * dt_l.s0

    e = 0.5 * (dt_l.gasket_cal_diam - d.D_int_flange - s_e)

    gamma = 1 / (dt_lr.y_p + dt_lr.y_b * bs.E_bolt_20 / bs.E_bolt_T +
                 2 * dt_lr.y_flange * fs.E_flange_20 / fs.E_flange_T * b ** 2)
    alpha = 1 - (dt_lr.y_p - 2 * dt_lr.y_flange * e * b) / (dt_lr.y_p + dt_lr.y_b + 2 * dt_lr.y_flange * (b ** 2))
    alpha_m = ((dt_lr.y_b + 2 * dt_lr.y_flange_n * b * (b + e - e ** 2 / dt_l.gasket_cal_diam)) /
               (dt_lr.y_b + dt_lr.y_p * (d.d_pins_flange / dt_l.gasket_cal_diam) ** 2 + 2 * dt_lr.y_flange_n * b ** 2))

    result_data = {"b": b, "e": e, "gamma": gamma, "alpha": alpha, "alpha_m": alpha_m,
                   "ko_ef_B_x": ko_ef_B_x, "s_e": s_e}
    hardness_data = {**ductility_result, **result_data}

    return hardness_data


def get_allowed_stress_bolt(bolt_steel_prop_data):
    bs = SimpleNamespace(**bolt_steel_prop_data)

    n_T = 2.7 if bs.sigma_y_bolt_20 / bs.sigma_b_bolt_20 >= 0.7 else 2.3

    allowed_stress_b_n = bs.sigma_y_bolt_T / n_T
    allowed_stress_b_m = 1.2 * 1.0 * 1.1 * 1.3 * allowed_stress_b_n
    allowed_stress_b_r = 1.35 * 1.1 * 1.3 * allowed_stress_b_n

    return allowed_stress_b_m, allowed_stress_b_r, n_T


def get_allowed_stress_flange(steel_grade, temperature):
    key = None
    for grades in allowed_flange_data:
        if any(g.strip() == steel_grade for g in grades.split(",")):
            key = grades
            break

    if key is None:
        raise ValueError(f"Марка стали '{steel_grade}' не найдена в таблице.")

    temp_data = allowed_flange_data[key]
    allowed_stress_flange_20 = temp_data.get(20)
    if allowed_stress_flange_20 is None:
        raise ValueError(f"Для стали '{steel_grade}' нет данных при 20°C.")

    if temperature in temp_data:
        return (
            1.5 * temp_data[temperature],
            3.0 * temp_data[temperature],
            temp_data[temperature],
        )

    temps = sorted(temp_data.keys())
    if temperature < temps[0] or temperature > temps[-1]:
        raise ValueError(f"Температура {temperature}°C вне диапазона данных для этой стали.")

    pos = bisect.bisect_left(temps, temperature)
    t_1, t_2 = temps[pos - 1], temps[pos]
    allowed_stress_flange_1, allowed_stress_flange_2 = temp_data[t_1], temp_data[t_2]
    allowed_stress_flange_T = round((allowed_stress_flange_1 + (allowed_stress_flange_2 - allowed_stress_flange_1) *
                                     (temperature - t_1) / (t_2 - t_1)), 3)

    allowed_stress_flange_m = round(1.5 * allowed_stress_flange_T, 3)
    allowed_stress_flange_r = round(3.0 * allowed_stress_flange_T, 3)

    return allowed_stress_flange_m, allowed_stress_flange_r, allowed_stress_flange_T


def get_corrosion_thickness(operating_time: float, flange_steel: str, bolt_steel: str):
    corrosion_rates = {
        0.2: ["10", "20", "25", "30", "35", "40", "09Г2С"],
        0.18: ["35Х", "40Х", "30ХМА"],
        0.15: ["25Х1МФ", "25Х2М1Ф"],
        0.1: ["20Х13", "18Х12ВМБФР"],
        0.02: ["12Х18Н10Т", "ХН35ВТ"]
    }

    def get_rate(steel: str) -> float:
        for rate, steels in corrosion_rates.items():
            if steel in steels:
                return rate
        raise ValueError(f"Нет данных по коррозии для: {steel}")

    velocity_of_corrosion_flange = get_rate(flange_steel)
    velocity_of_corrosion_bolt = get_rate(bolt_steel)

    c_flange = round(velocity_of_corrosion_flange * operating_time, 3)
    c_bolt = round(velocity_of_corrosion_bolt * operating_time, 3)

    return c_flange, c_bolt


def get_alpha_sigma(r, s):
    x = r / s
    if x <= 0.75:
        a_s = (
                114.63 * x ** 6 - 342.10 * x ** 5 + 418.49 * x ** 4 -
                276.59 * x ** 3 + 111.30 * x ** 2 - 28.286 * x + 5.0888)
    else:
        a_s = 1.5
    return a_s


def get_delta_sigma(all_data, gasket_parameters, hardness_data, delta_sigma_data):
    d = SimpleNamespace(**all_data)
    g = SimpleNamespace(**gasket_parameters)
    h = SimpleNamespace(**hardness_data)
    dsd = SimpleNamespace(**delta_sigma_data)

    pressure_min, pressure_max = 0.6 * d.pressure, 1.25 * d.pressure

    def R_p(p):
        return round(math.pi * dsd.gasket_cal_diam * dsd.gasket_eff_width * g.m * p / 1000, 3)

    def Q_d(p):
        return round(0.785 * dsd.gasket_cal_diam ** 2 * p / 1000, 3)

    R_p_min, R_p_max = R_p(pressure_min), R_p(pressure_max)
    Q_d_min, Q_d_max = Q_d(pressure_min), Q_d(pressure_max)

    def P_b_1(Q_d_val, R_p_val):
        return max(
            h.alpha * (Q_d_val + d.ext_force) + R_p_val +
            4 * h.alpha_m * abs(d.ext_moment) * 1000 / dsd.gasket_cal_diam,
            h.alpha * (Q_d_val + d.ext_force) + R_p_val +
            4 * h.alpha_m * abs(d.ext_moment) * 1000 / dsd.gasket_cal_diam - dsd.Q_t)

    P_b_1_min, P_b_1_max = P_b_1(Q_d_min, R_p_min), P_b_1(Q_d_max, R_p_max)

    P_b_m_min = round(max(P_b_1_min, dsd.P_b_2), 3)
    P_b_m_max = round(max(P_b_1_max, dsd.P_b_2), 3)

    def P_b_r(P_b_m_val, Q_d_val):
        return round(P_b_m_val + (1 - h.alpha) * (Q_d_val + d.ext_force) + dsd.Q_t +
                     4 * (1 - h.alpha_m) * abs(d.ext_moment) * 1000 / dsd.gasket_cal_diam, 3)

    P_b_r_min, P_b_r_max = P_b_r(P_b_m_min, Q_d_min), P_b_r(P_b_m_max, Q_d_max)

    stress_b_2_min = P_b_r_min * 1000 / dsd.bolts_corrosion_area
    stress_b_2_max = P_b_r_max * 1000 / dsd.bolts_corrosion_area
    print(stress_b_2_max, stress_b_2_min, dsd.allowed_stress_b_r)

    if max(stress_b_2_min, stress_b_2_max) > dsd.allowed_stress_b_r:
        return None, {}

    def M(P_b_m, Q_d_val):
        M_M = h.C_F * P_b_m * h.b / 1000
        M_R = h.C_F * max(P_b_r_min * h.b / 1000 + (Q_d_val + dsd.Q_F_M) * h.e / 1000,
                          abs(Q_d_val + dsd.Q_F_M) * h.e / 1000)
        return M_M, M_R

    M_M_min, M_R_min = M(P_b_m_min, Q_d_min)
    M_M_max, M_R_max = M(P_b_m_max, Q_d_max)

    def stress_R_01_cone(M_R_val):
        stress_R_1_val = M_R_val * 1e6 / (h.lambda_ * (dsd.s1 - dsd.c_flange) ** 2 * h.D_pr_flange)
        stress_R_0_val = h.f * stress_R_1_val
        return stress_R_1_val, stress_R_0_val

    def stress_R_01_cyl(M_R_val):
        stress_R_1_val = stress_R_0_val = M_R_val * 1e6 / (h.lambda_ * (dsd.s0 - dsd.c_flange) ** 2 * h.D_pr_flange)
        return stress_R_1_val, stress_R_0_val

    def stress_1MM_R(Q_d_val, s):
        return max((Q_d_val + d.ext_force + 4 * abs(d.ext_moment) / dsd.gasket_cal_diam / 1000) * 1000 / (
                math.pi * (d.D_int_flange + s) * (s - dsd.c_flange)),
                   (Q_d_val + d.ext_force - 4 * abs(d.ext_moment) / dsd.gasket_cal_diam / 1000) * 1000 / (
                           math.pi * (d.D_int_flange + s) * (s - dsd.c_flange)))

    def stress_MR_R(M_M_val):
        return ((1.33 * h.B_F * d.h_flange + h.l_0) * M_M_val * 1e6 /
                (h.lambda_ * d.h_flange ** 2 * h.l_0 * d.D_int_flange))

    def stress_R_T(M_R_val, stress_R_R):
        return h.B_Y * M_R_val * 1e6 / (d.h_flange ** 2 * d.D_int_flange) - h.B_Z * stress_R_R

    if d.flange_type == 'one_one':
        if d.D_m_flange > d.D_n_flange:
            stress_R_1_min, stress_R_0_min = stress_R_01_cone(M_R_min)
            stress_R_1_max, stress_R_0_max = stress_R_01_cone(M_R_max)
            stress_1MM_R_min = stress_1MM_R(Q_d_min, dsd.s1)
            stress_1MM_R_max = stress_1MM_R(Q_d_max, dsd.s1)
            stress_R_R_min = stress_MR_R(M_R_min)
            stress_R_R_max = stress_MR_R(M_R_max)
            stress_R_T_min = stress_R_T(M_R_min, stress_R_R_min)
            stress_R_T_max = stress_R_T(M_R_max, stress_R_R_max)

            stress_R_1_1_min = stress_R_1_min + stress_1MM_R_min
            stress_R_1_2_min = -stress_R_1_min + stress_1MM_R_min
            stress_R_1_4_min = stress_R_T_min
            stress_R_1_6_min = stress_R_R_min
            stress_R_1_1_max = stress_R_1_max + stress_1MM_R_max
            stress_R_1_2_max = -stress_R_1_max + stress_1MM_R_max
            stress_R_1_4_max = stress_R_T_max
            stress_R_1_6_max = stress_R_R_max

            stress_delta_R_1_1 = max(abs(stress_R_1_1_max - stress_R_1_1_min), abs(stress_R_1_1_min - stress_R_1_1_max))
            stress_delta_R_1_2 = max(abs(stress_R_1_2_max - stress_R_1_2_min), abs(stress_R_1_2_min - stress_R_1_2_max))
            stress_delta_R_1_4 = max(abs(stress_R_1_4_max - stress_R_1_4_min), abs(stress_R_1_4_min - stress_R_1_4_max))
            stress_delta_R_1_6 = max(abs(stress_R_1_6_max - stress_R_1_6_min), abs(stress_R_1_6_min - stress_R_1_6_max))

            alpha_sigma = get_alpha_sigma(d.r, dsd.s1)
            stress_delta_a = max(
                alpha_sigma * abs(stress_delta_R_1_1),
                abs(stress_delta_R_1_2 - stress_delta_R_1_4),
                abs(stress_delta_R_1_2 - stress_delta_R_1_6)) / 2

            stress_delta_data = {
                "stress_delta_R_1_1": stress_delta_R_1_1,
                "stress_delta_R_1_2": stress_delta_R_1_2,
                "stress_delta_R_1_4": stress_delta_R_1_4,
                "stress_delta_R_1_6": stress_delta_R_1_6,
            }

        elif d.D_m_flange == d.D_n_flange:
            stress_R_1_min, stress_R_0_min = stress_R_01_cyl(M_R_min)
            stress_R_1_max, stress_R_0_max = stress_R_01_cyl(M_R_max)
            stress_0MM_R_min = stress_1MM_R(Q_d_min, dsd.s0)
            stress_0MM_R_max = stress_1MM_R(Q_d_max, dsd.s0)
            stress_M_R_min = stress_MR_R(M_M_min)
            stress_M_R_max = stress_MR_R(M_M_max)
            stress_R_R_min = stress_MR_R(M_R_min)
            stress_R_R_max = stress_MR_R(M_R_max)
            stress_R_T_min = stress_R_T(M_R_min, stress_R_R_min)
            stress_R_T_max = stress_R_T(M_R_max, stress_R_R_max)

            stress_R_0_1_min = stress_R_0_min + stress_0MM_R_min
            stress_R_0_2_min = -stress_R_0_min + stress_0MM_R_min
            stress_R_0_3_min = stress_R_0_4_min = stress_R_T_min
            stress_R_0_5_min = stress_R_0_6_min = stress_M_R_min
            stress_R_0_1_max = stress_R_0_max + stress_0MM_R_max
            stress_R_0_2_max = -stress_R_0_max + stress_0MM_R_max
            stress_R_0_3_max = stress_R_0_4_max = stress_R_T_max
            stress_R_0_5_max = stress_R_0_6_max = stress_M_R_max

            stress_delta_R_0_1 = max(abs(stress_R_0_1_max - stress_R_0_1_min), abs(stress_R_0_1_min - stress_R_0_1_max))
            stress_delta_R_0_2 = max(abs(stress_R_0_2_max - stress_R_0_2_min), abs(stress_R_0_2_min - stress_R_0_2_max))
            stress_delta_R_0_3 = max(abs(stress_R_0_3_max - stress_R_0_3_min), abs(stress_R_0_3_min - stress_R_0_3_max))
            stress_delta_R_0_4 = max(abs(stress_R_0_4_max - stress_R_0_4_min), abs(stress_R_0_4_min - stress_R_0_4_max))
            stress_delta_R_0_5 = max(abs(stress_R_0_5_max - stress_R_0_5_min), abs(stress_R_0_5_min - stress_R_0_5_max))
            stress_delta_R_0_6 = max(abs(stress_R_0_6_max - stress_R_0_6_min), abs(stress_R_0_6_min - stress_R_0_6_max))

            alpha_sigma = get_alpha_sigma(d.r, dsd.s0)

            stress_delta_a = max(
                alpha_sigma * abs(stress_delta_R_0_1),
                abs(stress_delta_R_0_1 - stress_delta_R_0_3),
                abs(stress_delta_R_0_1 - stress_delta_R_0_5),
                abs(stress_delta_R_0_2),
                abs(stress_delta_R_0_2 - stress_delta_R_0_4),
                abs(stress_delta_R_0_2 - stress_delta_R_0_6)) / 2

            stress_delta_data = {
                "stress_delta_R_0_1": stress_delta_R_0_1,
                "stress_delta_R_0_3": stress_delta_R_0_3,
                "stress_delta_R_0_5": stress_delta_R_0_5,
                "stress_delta_R_0_2": stress_delta_R_0_2,
                "stress_delta_R_0_4": stress_delta_R_0_4,
                "stress_delta_R_0_6": stress_delta_R_0_6
            }

        else:
            raise ValueError("Ошибка: Такой фланец считать не умею.")
    elif d.flange_type == 'zero_one':
        stress_R_1_min, stress_R_0_min = stress_R_01_cyl(M_R_min)
        stress_R_1_max, stress_R_0_max = stress_R_01_cyl(M_R_max)
        stress_0MM_R_min = stress_1MM_R(Q_d_min, dsd.s0)
        stress_0MM_R_max = stress_1MM_R(Q_d_max, dsd.s0)
        stress_M_R_min = stress_MR_R(M_M_min)
        stress_M_R_max = stress_MR_R(M_M_max)
        stress_R_R_min = stress_MR_R(M_R_min)
        stress_R_R_max = stress_MR_R(M_R_max)
        stress_R_T_min = stress_R_T(M_R_min, stress_R_R_min)
        stress_R_T_max = stress_R_T(M_R_max, stress_R_R_max)

        stress_R_0_1_min = stress_R_0_min + stress_0MM_R_min
        stress_R_0_2_min = -stress_R_0_min + stress_0MM_R_min
        stress_R_0_3_min = stress_R_0_4_min = stress_R_T_min
        stress_R_0_5_min = stress_R_0_6_min = stress_M_R_min
        stress_R_0_1_max = stress_R_0_max + stress_0MM_R_max
        stress_R_0_2_max = -stress_R_0_max + stress_0MM_R_max
        stress_R_0_3_max = stress_R_0_4_max = stress_R_T_max
        stress_R_0_5_max = stress_R_0_6_max = stress_M_R_max

        stress_delta_R_0_1 = max(abs(stress_R_0_1_max - stress_R_0_1_min), abs(stress_R_0_1_min - stress_R_0_1_max))
        stress_delta_R_0_2 = max(abs(stress_R_0_2_max - stress_R_0_2_min), abs(stress_R_0_2_min - stress_R_0_2_max))
        stress_delta_R_0_3 = max(abs(stress_R_0_3_max - stress_R_0_3_min), abs(stress_R_0_3_min - stress_R_0_3_max))
        stress_delta_R_0_4 = max(abs(stress_R_0_4_max - stress_R_0_4_min), abs(stress_R_0_4_min - stress_R_0_4_max))
        stress_delta_R_0_5 = max(abs(stress_R_0_5_max - stress_R_0_5_min), abs(stress_R_0_5_min - stress_R_0_5_max))
        stress_delta_R_0_6 = max(abs(stress_R_0_6_max - stress_R_0_6_min), abs(stress_R_0_6_min - stress_R_0_6_max))

        stress_delta_a = 1.5 * max(
            abs(stress_delta_R_0_1),
            abs(stress_delta_R_0_1 - stress_delta_R_0_3),
            abs(stress_delta_R_0_1 - stress_delta_R_0_5),
            abs(stress_delta_R_0_2),
            abs(stress_delta_R_0_2 - stress_delta_R_0_4),
            abs(stress_delta_R_0_2 - stress_delta_R_0_6)) / 2

        stress_delta_data = {
            "stress_delta_R_0_1": stress_delta_R_0_1,
            "stress_delta_R_0_3": stress_delta_R_0_3,
            "stress_delta_R_0_5": stress_delta_R_0_5,
            "stress_delta_R_0_2": stress_delta_R_0_2,
            "stress_delta_R_0_4": stress_delta_R_0_4,
            "stress_delta_R_0_6": stress_delta_R_0_6
        }

    else:
        raise ValueError(f"Нет методики расчета фланцев типа: {d.flange_type}")

    return stress_delta_a, stress_delta_data


def get_allowed_amplitude(num_cycles, steel_grade, sigma_y_T, temperature, stress_a):
    data = {  # A, B, Ct, nN, n_sigma
        "10,20,25,30,35,40":
            [0.6 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0],
        "35Х,40Х,30ХМА,25Х1МФ,25Х2М1Ф,20Х13,18Х12ВМБФР":
            [0.45 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0],
        "12Х18Н10Т,ХН35ВТ":
            [0.6 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0],
        "09Г2С":
            [0.45 * 1e5, 0.4 * sigma_y_T, (2300 - temperature) / 2300, 10.0, 2.0]
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
