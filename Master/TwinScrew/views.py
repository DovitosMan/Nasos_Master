from django.shortcuts import render
import math
import numpy as np
from scipy.optimize import bisect, fsolve
from functools import partial
from tqdm import tqdm
import itertools
import pandas as pd
import logging
import cadquery as cq
from cadquery import exporters, Compound
from functools import reduce

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def twin_screw(request):
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Подача, м³/ч', 'name': 'flow_rate', 'value': ''},
            {'type': 'float', 'placeholder': 'Напор, м', 'name': 'pressure', 'value': ''},
            {'type': 'float', 'placeholder': 'Частота вращения, об/мин', 'name': 'rotation_speed', 'value': ''},
            {'type': 'float', 'placeholder': 'Плотность, кг/м³:', 'name': 'density', 'value': ''},
            {'type': 'float', 'placeholder': 'Вязкость, мПа*с', 'name': 'viscosity', 'value': ''},
            {'type': 'float', 'placeholder': 'Температура, С:', 'name': 'temperature', 'value': ''},
            {'type': 'float', 'placeholder': 'Теплоемкость, Дж/(кг*К):', 'name': 'heat_capacity', 'value': ''},
        ],
    }

    if request.method == "POST":

        input_data = {}

        for select in context['calc']:
            name = select['name']
            raw_value = request.POST.get(name, '')
            select['value'] = raw_value
            try:
                input_data[name] = float(raw_value)
            except ValueError:
                input_data[name] = None

        result = calculate(**input_data)

        print("Лучшие параметры и вычисленные значения:")

        if result is None:
            raise ValueError("Не удалось получить результат из twin_screw, параметры не валидны")
        else:
            for key, value in result.items():
                print(f"{key}: {value}")

        create_assembly(result)

    return render(request, 'twinscrew.html', context)


def calculate(flow_rate, pressure, rotation_speed, density, viscosity, temperature, heat_capacity, double_inlet=True,
              num_threads=2):
    def pre_calc(r_ratio, t_ratio, alpha, kpd_vol, flow_rate_add):
        phi = 2 * math.acos((1 + r_ratio) / 2)

        pi = math.pi
        lambda_val = (
                2 * pi
                - phi
                + math.sin(phi)
                - pi * (1 + r_ratio ** 2)
                + (2 * pi * math.tan(math.radians(alpha)) * (1 - r_ratio) ** 3) / (3 * t_ratio)
        )

        val = 200 * (
                (
                        flow_rate_add / (lambda_val * kpd_vol * t_ratio * rotation_speed * 60)
                ) ** (1 / 3)) * 10

        # Проверяем, что val вещественное число, а не комплексное
        if isinstance(val, complex):
            logger.debug(
                f"pre_calc: комплексное значение val={val} для r_ratio={r_ratio}, t_ratio={t_ratio}, alpha={alpha}")
            return None

        ext_diam_mm = round(val, 1)
        ext_radius_mm = round(ext_diam_mm / 2, 2)
        int_radius_mm = round(ext_radius_mm * r_ratio, 2)
        t_mm = round(ext_radius_mm * t_ratio, 1)
        logger.debug(
            f"pre_calc: r_ratio={r_ratio}, t_ratio={t_ratio}, alpha={alpha} => ext_r={ext_radius_mm}, int_r={int_radius_mm}, t={t_mm}, phi={phi:.3f}, lambda_val={lambda_val:.3f}")
        return ext_radius_mm, int_radius_mm, t_mm, phi, lambda_val

    def dtheta1_ddelta(theta1, r_ratio, ext_r, t, alpha_deg):
        alpha_rad = math.radians(alpha_deg)
        pi = math.pi

        cos_theta = math.cos(theta1)
        sin_theta = math.sin(theta1)

        num1 = (
                3 * cos_theta
                + 3 * r_ratio * cos_theta
                - 3
                - 2 * r_ratio
                - r_ratio ** 2
        )
        den1 = (1 + r_ratio - cos_theta) ** 2 + sin_theta ** 2

        first_term = - (t / (2 * pi)) * (num1 / den1)

        numerator2 = (1 + r_ratio) * sin_theta
        denominator2 = math.sqrt(
            2 * (1 - cos_theta) * (1 + r_ratio) + r_ratio ** 2
        )

        second_term = ext_r * math.tan(alpha_rad) * (numerator2 / denominator2)

        return first_term + second_term

    def delta_t(theta1_max, r_ratio, R, t, alpha_deg):
        alpha_rad = math.radians(alpha_deg)
        pi = math.pi

        arctan_part = math.atan(
            math.sin(theta1_max) / (1 + r_ratio - math.cos(theta1_max))
        )
        first_term = (t / (2 * pi)) * (arctan_part - theta1_max)

        root_argument = 2 * (1 - math.cos(theta1_max)) * (1 + r_ratio) + r_ratio ** 2
        second_term = R * math.tan(alpha_rad) * (math.sqrt(root_argument) - r_ratio)

        return first_term - second_term

    def gap_calc(delt_t, t, ext_r, int_r, alpha, num):
        b_ext_top = round(t / 2 - (delt_t + 2 * (ext_r - int_r) * math.tan(math.radians(alpha))), 1) / num
        b_ext_low = round(t - num * b_ext_top, 1) / num
        b_int_low = round(b_ext_low - 2 * math.tan(math.radians(alpha)) * (ext_r - int_r), 1)

        stator_gap = round(round(delt_t / 0.05) * 0.05, 2)
        screw_gap = round(round(0.7 * delt_t / 0.05) * 0.05, 2)
        side_gap = round((b_int_low - b_ext_top) / 2, 2)

        axis_dist = round(round((ext_r + int_r + screw_gap) / 0.1) * 0.1, 1)
        # Если зазор отрицательный, уменьшать число заходов num
        return stator_gap, screw_gap, side_gap, b_ext_top, b_int_low, b_ext_low, axis_dist

    flow_rate_adj = flow_rate / 2 if double_inlet else flow_rate

    kpd_vol_pre_fixed = 0.8
    best_params = None
    min_effective_koef = float('inf')

    logger.info(
        f"Запуск перебора параметров для flow_rate={flow_rate}, pressure={pressure}, rotation_speed={rotation_speed}, "
        f"temperature={temperature}")

    r_ratio_values = sorted(set(
        [round(x, 3) for x in np.arange(0.400, 0.500 + 0.001, 0.025)] +
        [round(x, 3) for x in np.arange(0.525, 0.701 + 0.001, 0.025)]
    ))
    t_ratio_values = sorted(set(
        [round(x, 3) for x in np.arange(0.500, 0.700 + 0.001, 0.025)] +
        [round(x, 3) for x in np.arange(0.725, 1.250 + 0.001, 0.025)]
    ))
    alpha_values = [round(x * 0.1, 2) for x in range(0, 100 + 1)]  # 0..10 step 0.1

    combinations = list(itertools.product(r_ratio_values, t_ratio_values, alpha_values))

    for r_ratio, t_ratio, alpha in tqdm(combinations, desc="Перебор параметров", total=len(combinations)):
        try:
            pre_calc_result = pre_calc(r_ratio, t_ratio, alpha, kpd_vol_pre_fixed, flow_rate_adj)
            if pre_calc_result is None:
                continue  # Пропускаем комплексные значения

            ext_r, int_r, t, phi, lambda_val = pre_calc(r_ratio, t_ratio, alpha, kpd_vol_pre_fixed,
                                                        flow_rate_adj)
            f = partial(dtheta1_ddelta, r_ratio=r_ratio, ext_r=ext_r, t=t, alpha_deg=alpha)
            theta1_root = bisect(f, 0.01, math.pi - 0.01, xtol=1e-6)
            delta_t_val = delta_t(theta1_root, r_ratio, ext_r, t, alpha)
            stator_gap, screw_gap, side_gap, b_ext_top, b_int_low, b_ext_low, axis_dist = gap_calc(delta_t_val, t,
                                                                                                   ext_r, int_r,
                                                                                                   alpha,
                                                                                                   num_threads)
            viscosity_kin = viscosity / density * 1000

            pressure_mpa = 0.009806649643957326 * pressure
            k = 0.94
            dp_per_turn = 0.71 * (viscosity_kin / 1) ** k
            dp_per_turn = max(0.5, min(dp_per_turn, 5))
            pressure_kgs_sm = 10.197162 * pressure_mpa
            turns_est = round(round(pressure_kgs_sm / dp_per_turn, 1) / 10, 2)
            thread_length_mm = round(turns_est * t, 1)

            stator_gap_koef = 0.7
            feed_loss_stator = 60 * 60 * 2 * ((stator_gap * stator_gap_koef / 1000 / 2) ** 3) * (
                    (2 * math.pi - phi) * ext_r / 1000) * (pressure_mpa * 1_000_000) / (
                                       12 * (viscosity / 1000) * (thread_length_mm / 1000))

            screw_gap_koef = 1
            feed_loss_screw = 60 * 60 * ((screw_gap * screw_gap_koef / 1000 / 2) ** 3) * (
                    phi * ext_r / 1000) * (pressure_mpa * 1_000_000) / (
                                      12 * (viscosity / 1000) * (thread_length_mm / 1000))

            side_gap_koef = 1
            feed_loss_side = 60 * 60 * ((side_gap * side_gap_koef / 1000 / 2) ** 3) * (
                    side_gap * side_gap_koef * (math.sin(phi / 2) * ext_r / 1000)) * (
                                     pressure_mpa * 1_000_000) / (
                                     12 * (viscosity / 1000) * (thread_length_mm / 1000))

            feed_loss = feed_loss_stator + feed_loss_screw + feed_loss_side

            multiplier = 2 if double_inlet else 1
            flow_rate_theory = round(
                multiplier * lambda_val * ext_r ** 2 * t * rotation_speed * 60 / 1_000_000_000, 1)

            kpd_vol_2 = round(1 - feed_loss / flow_rate_theory, 3)
            flow_rate_real = kpd_vol_2 * flow_rate_theory

            w = math.pi * rotation_speed / 30
            k_t = density * heat_capacity * temperature / ((viscosity / 1000) * w)
            g = pressure_mpa * 1_000_000 / (viscosity / 1000) / w
            f_m = (thread_length_mm / t) * math.pow(k_t, 0.55) * math.pow(g, -1)
            k_m = 15 * math.pow(ext_r / int_r, -2.7)

            kpd_mech = round(1 / (1 + f_m * k_m), 3)

            power_gap = round(pressure_mpa * (feed_loss / 60 / 60) * 1000, 3)
            power_theory = round(pressure_mpa * (flow_rate_theory / 60 / 60) * 1000, 3)
            power_required = round(power_theory / kpd_mech, 3)
            power_full = round(power_required + power_gap, 3)

            kpd_total = round(kpd_mech * kpd_vol_2, 3)

            effective_koef = power_full / flow_rate_real
            if effective_koef <= 0:
                continue

            if effective_koef < min_effective_koef:
                min_effective_koef = effective_koef
                best_params = (r_ratio, t_ratio, alpha, kpd_vol_2, ext_r, int_r, t, phi, lambda_val,
                               stator_gap, screw_gap, side_gap, b_ext_top, b_int_low, b_ext_low, axis_dist,
                               density, viscosity, viscosity_kin, heat_capacity,
                               feed_loss, flow_rate_theory, flow_rate_real,
                               kpd_mech, power_gap, power_theory, power_required, power_full, kpd_total)
                logger.debug(
                    f"Новая лучшая комбинация: r_ratio={r_ratio}, t_ratio={t_ratio}, alpha={alpha}, effective_koef={effective_koef:.6f}")
        except Exception as e:
            logger.debug(
                f"Ошибка в переборе параметров r_ratio={r_ratio}, t_ratio={t_ratio}, alpha={alpha}: {e}")
            continue

    if best_params is None:
        logger.warning("Не удалось найти подходящую комбинацию параметров.")
        return None
    logger.info(
        f"Лучшие параметры: r_ratio={best_params[0]}, t_ratio={best_params[1]}, alpha={best_params[2]}, "
        f"effective_koef={min_effective_koef:.6f}")
    r_ratio_b, t_ratio_b, alpha_b, kpd_vol_2_b, ext_r_b, int_r_b, t_b, phi_b, lambda_val_b = best_params[:9]

    pre_calc_result = pre_calc(r_ratio_b, t_ratio_b, alpha_b, kpd_vol_2_b, flow_rate_adj)
    if pre_calc_result is None:
        return None  # или выбросить исключение
    ext_r, int_r, t, phi, lambda_val = pre_calc_result
    f = partial(dtheta1_ddelta, r_ratio=r_ratio_b, ext_r=ext_r, t=t, alpha_deg=alpha_b)
    theta1_root = bisect(f, 0.01, math.pi - 0.01, xtol=1e-6)
    delta_t_val = delta_t(theta1_root, r_ratio_b, ext_r, t, alpha_b)
    stator_gap, screw_gap, side_gap, b_ext_top, b_int_low, b_ext_low, axis_dist = gap_calc(delta_t_val, t, ext_r, int_r,
                                                                                           alpha_b, num_threads)
    viscosity_kin = viscosity / density * 1000

    pressure_mpa = 0.009806649643957326 * pressure
    k = 0.94
    dp_per_turn = 0.71 * (viscosity_kin / 1) ** k
    dp_per_turn = max(0.5, min(dp_per_turn, 5))

    pressure_kgs_sm = 10.197162 * pressure_mpa
    turns_est = round(round(pressure_kgs_sm / dp_per_turn, 1) / 10, 2)
    thread_length_mm = round(turns_est * t, 1)

    stator_gap_koef = 0.7
    feed_loss_stator = 60 * 60 * 2 * ((stator_gap * stator_gap_koef / 1000 / 2) ** 3) * (
            (2 * math.pi - phi) * ext_r / 1000) * (pressure_mpa * 1_000_000) / (
                               12 * (viscosity / 1000) * (thread_length_mm / 1000))

    screw_gap_koef = 1
    feed_loss_screw = 60 * 60 * ((screw_gap * screw_gap_koef / 1000 / 2) ** 3) * (phi * ext_r / 1000) * (
            pressure_mpa * 1_000_000) / (12 * (viscosity / 1000) * (thread_length_mm / 1000))

    side_gap_koef = 1
    feed_loss_side = 60 * 60 * ((side_gap * side_gap_koef / 1000 / 2) ** 3) * (
            side_gap * side_gap_koef * (math.sin(phi / 2) * ext_r / 1000)) * (pressure_mpa * 1_000_000) / (
                             12 * (viscosity / 1000) * (thread_length_mm / 1000))

    feed_loss = feed_loss_stator + feed_loss_screw + feed_loss_side

    multiplier = 2 if double_inlet else 1
    flow_rate_theory = multiplier * lambda_val * ext_r ** 2 * t * rotation_speed * 60 / 1_000_000_000

    kpd_vol_2 = 1 - feed_loss / flow_rate_theory
    flow_rate_real = kpd_vol_2 * flow_rate_theory

    w = math.pi * rotation_speed / 30
    k_t = density * heat_capacity * temperature / ((viscosity / 1000) * w)
    g = pressure_mpa * 1_000_000 / (viscosity / 1000) / w
    f_m = (thread_length_mm / t) * math.pow(k_t, 0.55) * math.pow(g, -1)
    k_m = 15 * math.pow(ext_r / int_r, -2.7)

    kpd_mech = 1 / (1 + f_m * k_m)

    power_gap = pressure * (feed_loss / 60 / 60) * density * 9.81 / 1000
    power_theory = pressure * (flow_rate_theory / 60 / 60) * density * 9.81 / 1000
    power_required = power_theory / kpd_mech
    power_full = power_required + power_gap

    kpd_total = kpd_mech * kpd_vol_2

    # Возвращаем результаты
    results_dict = {
        "flow_rate": float(flow_rate),
        "pressure": float(pressure),
        "rotation_speed": float(rotation_speed),
        "temperature": float(temperature),
        "flow_rate_real": float(flow_rate_real),
        "kpd_vol": float(kpd_vol_2),
        "kpd_mech": float(kpd_mech),
        "kpd_total": float(kpd_total),
        "delta_t_val": float(delta_t_val),
        "stator_gap": float(stator_gap),
        "screw_gap": float(screw_gap),
        "side_gap": float(side_gap),
        "power_full": float(power_full),
        "effective_koef": float(power_full / flow_rate_real),
        "r_ratio": float(r_ratio_b),
        "t_ratio": float(t_ratio_b),
        "alpha": float(alpha_b),
        "ext_radius_mm": float(ext_r),
        "int_radius_mm": float(int_r),
        "t_mm": float(t),
        "axis_dist": float(axis_dist),
        "thread_length_mm": float(thread_length_mm),
        "phi": float(phi),
        "lambda_val": float(lambda_val),
        "b_ext_top": float(b_ext_top),
        "b_int_low": float(b_int_low),
        "b_ext_low": float(b_ext_low),
        "density": float(density),
        "viscosity_dyn": float(viscosity),
        "viscosity_kin": float(viscosity_kin),
        "heat_capacity": float(heat_capacity),
        "feed_loss": float(feed_loss),
        "flow_rate_theory": float(flow_rate_theory),
        "power_gap": float(power_gap),
        "power_theory": float(power_theory),
        "power_required": float(power_required),
    }

    df = pd.DataFrame([results_dict])  # одна строка таблицы

    # Имя файла по наружному диаметру
    ext_diam = round(ext_r * 2, 1)
    filename = f"twin_screw_D{ext_diam}mm.xlsx"

    # Сохранение
    df.to_excel(filename, index=False)
    print(f"Результаты сохранены в файл: {filename}")

    return results_dict


def create_stator(results_dict):
    ext_radius_mm = float(results_dict['ext_radius_mm'])
    axis_dist = round(float(results_dict['axis_dist']), 1)
    thread_length_mm = float(results_dict['thread_length_mm'])
    stator_gap = float(results_dict['stator_gap'])

    logger.info('Вычисляем размеры статора')
    radius_1 = radius_round(ext_radius_mm, factor=0.407)
    radius_2 = radius_round(ext_radius_mm, round_base=1, factor=0.418)
    radius_3 = radius_round(ext_radius_mm, round_base=1, factor=0.46)
    radius_4 = radius_round(ext_radius_mm, round_base=1, factor=0.75)
    radius_5 = radius_1 + 2.5
    radius_6 = radius_1 + 5.0
    radius_7 = radius_1 + 7.5
    radius_8 = radius_round(ext_radius_mm, round_base=1, factor=0.831)
    radius_9 = radius_round(ext_radius_mm, round_base=1, factor=0.926)
    radius_10 = radius_round(ext_radius_mm, round_base=1, factor=0.713)
    radius_11 = ext_radius_mm + stator_gap
    radius_12 = radius_round(ext_radius_mm, round_base=1, factor=0.82)

    dist_1 = int(thread_length_mm / 7.8)
    dist_2 = int(thread_length_mm / 13.0)
    dist_3 = int(thread_length_mm / 17.73)
    dist_4 = int(thread_length_mm / 3.19)
    dist_5 = int(thread_length_mm / 8.86)
    dist_6 = int(thread_length_mm / 5.42)
    dist_7 = int(thread_length_mm / 2.78)
    dist_8 = int(dist_7/2)
    dist_9 = int(thread_length_mm / 3.0)
    dist_10 = int(thread_length_mm / 3.197)
    dist_11 = int(thread_length_mm / 3.979)
    dist_12 = int(thread_length_mm / 2.0)

    base_offset = dist_1 + dist_2 + radius_1 - radius_2 + dist_3
    final_offset = base_offset + dist_4 - dist_5 + int(axis_dist)

    logger.info('Создаем контуры')
    contour_1 = cq.Workplane('ZY').moveTo(dist_1, radius_1).polyline([
        (dist_1 + dist_2, radius_1),
        (dist_1 + dist_2 + radius_1 - radius_2, radius_2),
        (dist_1 + dist_2 + radius_1 - radius_2 + dist_3, radius_2),
        (dist_1 + dist_2 + radius_1 - radius_2 + dist_3, radius_3),
        (dist_1, radius_3),
        (dist_1, radius_1)
    ]).close()

    def create_arc_contour(r1, r2, offset, sign=1):
        return (cq.Workplane('XY').workplane(offset=offset).
                moveTo(-r1 * math.cos(math.radians(45)), sign * r1 * math.sin(math.radians(45))).
                radiusArc((r1 * math.cos(math.radians(45)), sign * r1 * math.sin(math.radians(45))), r1 * sign).
                lineTo(r2 * math.cos(math.radians(45)), sign * r2 * math.sin(math.radians(45))).
                radiusArc((-r2 * math.cos(math.radians(45)), sign * r2 * math.sin(math.radians(45))), -r2 * sign).
                close()
                )

    contour_2 = create_arc_contour(radius_2, radius_3, base_offset, 1)
    contour_3 = create_arc_contour(radius_2, radius_3, base_offset, -1)

    def create_cap_contour(r1, offset, sign=1):
        return (cq.Workplane('XY').workplane(offset=offset).
                moveTo(-r1 * math.cos(math.radians(45)), sign * r1 * math.sin(math.radians(45))).
                radiusArc((r1 * math.cos(math.radians(45)), sign * r1 * math.sin(math.radians(45))), sign * r1).
                lineTo(0, 0).close()
                )

    contour_4 = create_cap_contour(radius_2, base_offset + dist_4 - dist_5, 1)
    contour_5 = create_cap_contour(radius_2, base_offset + dist_4 - dist_5, -1)

    contour_6 = create_cap_contour(radius_2, final_offset - dist_5 + 2 * dist_6 + dist_7 + int(axis_dist), 1)
    contour_7 = create_cap_contour(radius_2, final_offset - dist_5 + 2 * dist_6 + dist_7 + int(axis_dist), -1)

    contour_8 = create_arc_contour(radius_2, radius_3, final_offset - dist_5 + 2 * dist_6 + dist_7 + int(axis_dist), 1)
    contour_9 = create_arc_contour(radius_2, radius_3, final_offset - dist_5 + 2 * dist_6 + dist_7 + int(axis_dist), -1)

    contour_10_offset = final_offset - dist_5 + 2 * dist_6 + dist_7 + int(axis_dist) + dist_4

    contour_10 = (
        cq.Workplane('ZY').moveTo(contour_10_offset, radius_2).
        polyline([
            (contour_10_offset, radius_2),
            (contour_10_offset + dist_3/2, radius_2),
            (contour_10_offset + dist_3/2 + radius_7 - radius_2, radius_7),
            (contour_10_offset + dist_3/2 + radius_7 - radius_2 + dist_2, radius_7),
            (contour_10_offset + dist_3 / 2 + radius_7 - radius_2 + dist_2, radius_3),
            (contour_10_offset, radius_3)
        ]).close()
    )

    middle_contour_1 = (
        cq.Workplane('XY').workplane(offset=final_offset + dist_6).
        moveTo(-dist_8/2, radius_3 * math.sin(math.acos(dist_8/(2*radius_3)))).
        radiusArc((dist_8/2, radius_3 * math.sin(math.acos(dist_8/(2*radius_3)))), radius_3).
        lineTo(dist_8/2, radius_8 * math.sin(math.acos(dist_8/(2*radius_8)))).
        radiusArc((-dist_8 / 2, radius_8 * math.sin(math.acos(dist_8 / (2 * radius_8)))), -radius_8).
        close()
    )

    middle_contour_2 = (
        cq.Workplane('XY').workplane(offset=final_offset + dist_6).
        moveTo(-dist_8 / 2, -radius_3 * math.sin(math.acos(dist_8 / (2 * radius_3)))).
        radiusArc((dist_8 / 2, -radius_3 * math.sin(math.acos(dist_8 / (2 * radius_3)))), -radius_3).
        lineTo(dist_8 / 2, -radius_8 * math.sin(math.acos(dist_8 / (2 * radius_8)))).
        radiusArc((-dist_8 / 2, -radius_8 * math.sin(math.acos(dist_8 / (2 * radius_8)))), radius_8).
        close()
    )

    def calc_some_points(r, a, d, x0, y0=0.0, upper=1):
        c = (upper * a * math.sqrt(2) - d/2)
        if y0 == 0 or 0.0 or None:
            D = 2 * r**2 - (c + x0)**2
            if D < 0.0:
                x = 0.0
                y = 0.0
            else:
                x = (-(c - x0) + math.sqrt(D)) / 2
                y = x + c
        else:
            D = (c - x0 - y0)**2 - 2 * (x0**2 - r**2 + (y0 - c)**2)
            if D < 0.0:
                x = 0.0
                y = 0.0
            else:
                x = (-(c - x0 - y0) + math.sqrt(D)) / 2
                y = x + c
        return x, y

    x1, y1 = calc_some_points(radius_9, dist_10, axis_dist, axis_dist/2, 0, 1)
    x2, y2 = calc_some_points(radius_9, dist_11, axis_dist, axis_dist / 2, 0, -1)
    x3, y3 = calc_some_points(radius_10, dist_11, axis_dist, dist_9, dist_9*math.tan(math.radians(11.5)), -1)
    x4, y4 = calc_some_points(radius_10, dist_10, axis_dist, dist_9, dist_9*math.tan(math.radians(11.5)), 1)

    middle_contour_3 = (
        cq.Workplane('XY').workplane(offset=final_offset + dist_6).
        moveTo(x1, y1).
        radiusArc((x2, y2), radius_9).
        lineTo(x3, y3).
        radiusArc((x4, y4), -radius_10).
        close()
    )

    middle_contour_4 = (
        cq.Workplane('XY').workplane(offset=final_offset + dist_6).
        moveTo(-x1, y1).
        radiusArc((-x2, y2), -radius_9).
        lineTo(-x3, y3).
        radiusArc((-x4, y4), radius_10).
        close()
    )

    middle_contour_5 = (
        cq.Workplane('XY').workplane(offset=final_offset + dist_6).
        moveTo(x1, -y1).
        radiusArc((x2, -y2), -radius_9).
        lineTo(x3, -y3).
        radiusArc((x4, -y4), radius_10).
        close()
    )

    middle_contour_6 = (
        cq.Workplane('XY').workplane(offset=final_offset + dist_6).
        moveTo(-x1, -y1).
        radiusArc((-x2, -y2), radius_9).
        lineTo(-x3, -y3).
        radiusArc((-x4, -y4), -radius_10).
        close()
    )
    logger.info('Создаем тела статора')
    parts = [
        create_cylinder(radius_1, dist_1, 0, 0, 0),
        contour_1.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(1, 0, 0)),
        contour_2.extrude(dist_4),
        contour_3.extrude(dist_4),
        contour_4.extrude(dist_5),
        contour_5.extrude(dist_5),
        create_cylinder(radius_4, int(axis_dist), base_offset + dist_4 - dist_5, 0, axis_dist / 2),
        create_cylinder(radius_4, int(axis_dist), base_offset + dist_4 - dist_5, 0, -axis_dist / 2),
        create_cylinder(radius_5, dist_6, final_offset, 0, 0),
        middle_contour_1.extrude(dist_7).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90),
        middle_contour_2.extrude(dist_7).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90),
        middle_contour_3.extrude(dist_7).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90),
        middle_contour_4.extrude(dist_7).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90),
        middle_contour_5.extrude(dist_7).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90),
        middle_contour_6.extrude(dist_7).rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(0, 0, 1), angleDegrees=90),
        create_cylinder(radius_6, dist_6, final_offset + dist_6 + dist_7, 0, 0),
        create_cylinder(radius_4, int(axis_dist), final_offset + 2 * dist_6 + dist_7, 0, axis_dist / 2),
        create_cylinder(radius_4, int(axis_dist), final_offset + 2 * dist_6 + dist_7, 0, -axis_dist / 2),
        contour_6.extrude(dist_5),
        contour_7.extrude(dist_5),
        contour_8.extrude(dist_4),
        contour_9.extrude(dist_4),
        contour_10.revolve(angleDegrees=360, axisStart=(0, 0, 0), axisEnd=(1, 0, 0)),
        create_cylinder(radius_7, dist_1, contour_10_offset + dist_3 / 2 + radius_7 - radius_2 + dist_2, 0, 0),
    ]

    stator_len = 2 * final_offset + dist_7 + 2 * dist_6
    logger.info('Создаем тела для вырезания в статоре')
    parts_1 = [
        create_cylinder(radius_11, stator_len + 10, 0, 0, axis_dist / 2),
        create_cylinder(radius_11, stator_len + 10, 0, 0, -axis_dist / 2),
        create_cylinder(radius_12, dist_12 / 2, 0, 0, axis_dist / 2),
        create_cylinder(radius_12, dist_12 / 2, 0, 0, -axis_dist / 2),
        create_cylinder(radius_12, -dist_12 / 2, stator_len, 0, axis_dist / 2),
        create_cylinder(radius_12, -dist_12 / 2, stator_len, 0, -axis_dist / 2),
    ]
    logger.info('Объединяем тела в статоре')
    stator_1 = combine_parts(parts)
    stator_2 = combine_parts(parts_1)
    logger.info('Создаем статор')
    stator = stator_1.cut(stator_2)
    logger.info('Статор создан')

    return stator, stator_len


def create_assembly(results_dict):
    alpha = float(results_dict['alpha'])
    ext_radius_mm = float(results_dict['ext_radius_mm'])
    int_radius_mm = float(results_dict['int_radius_mm'])
    t_mm = float(results_dict['t_mm'])
    axis_dist = round(float(results_dict['axis_dist']), 1)
    b_int_low = float(results_dict['b_int_low'])
    thread_length_mm = float(results_dict['thread_length_mm'])

    add = (ext_radius_mm - int_radius_mm) * math.tan(math.radians(alpha))
    dist_0 = int(thread_length_mm / 0.87)
    logger.info('Создаем ведомый винт')
    driven = create_driven_screw(results_dict, 0, False, True)[0]
    logger.info('Создаем ведущий винт')
    lead = create_lead_screw(results_dict).rotate((0, 0, 0), (0, 0, 1), angleDegrees=360 * (b_int_low + add) / t_mm)
    logger.info('Создаем статор')
    stator = create_stator(results_dict)[0]
    stator_len = create_stator(results_dict)[1]
    mid_position = create_driven_screw(results_dict, 0, False, True)[1]
    stator_position = mid_position - stator_len/2

    logger.info('Экспортируем модели')
    exporters.export(driven, 'driven_screw.step')
    exporters.export(lead, 'lead_screw.step')
    exporters.export(stator, 'stator.step')
    logger.info('Валы и статор успешно созданы и экспортированы')

    logger.info('Создаем сборку')
    asm = cq.Assembly()
    asm.add(cq.importers.importStep('driven_screw.step'), name='driven',
            loc=cq.Location(cq.Vector(0, axis_dist / 2, 0)))
    asm.add(cq.importers.importStep('lead_screw.step'), name='lead',
            loc=cq.Location(cq.Vector(0, -axis_dist / 2, -dist_0)))
    asm.add(cq.importers.importStep('stator.step'), name='stator',
            loc=cq.Location(cq.Vector(0, 0, stator_position)))
    exporters.export(asm.toCompound(), 'twin_assembly.step')
    logger.info('Сборка успешно создана и экспортирована')


def calculate_min_diam(results_dict):
    alpha = float(results_dict['alpha'])
    ext_radius_mm = float(results_dict['ext_radius_mm'])
    int_radius_mm = float(results_dict['int_radius_mm'])
    t_mm = float(results_dict['t_mm'])
    b_ext_top = float(results_dict['b_ext_top'])
    power_full = float(results_dict['power_full'])
    rotation_speed = float(results_dict['rotation_speed'])
    pressure = float(results_dict['pressure'])
    thread_length_mm = float(results_dict['thread_length_mm'])

    pressure_mpa = 0.00980665 * pressure

    add = (ext_radius_mm - int_radius_mm) * math.tan(math.radians(alpha))

    trapezoid_contour = [
        (0, int_radius_mm),
        (add, ext_radius_mm),
        (add + b_ext_top, ext_radius_mm),
        (2 * add + b_ext_top, int_radius_mm)
    ]

    def interpolate_2d_segment(p1, p2, n_points):
        x1, y1 = p1
        x2, y2 = p2
        return [
            (
                x1 + (x2 - x1) * i / (n_points - 1),
                y1 + (y2 - y1) * i / (n_points - 1)
            )
            for i in range(n_points)
        ]

    points_per_segment = 100
    all_points = []

    for i in range(len(trapezoid_contour) - 1):
        p1 = trapezoid_contour[i]
        p2 = trapezoid_contour[i + 1]

        segment_points = interpolate_2d_segment(p1, p2, points_per_segment)

        if i != 0:
            segment_points = segment_points[1:]

        all_points.extend(segment_points)

    angle_i = [2 * math.pi * (t_mm - x[0]) / t_mm for x in all_points]

    new_points = []
    for i, j in zip(all_points, angle_i):
        x_proj = i[1] * math.cos(j)
        y_proj = i[1] * math.sin(j)
        new_points.append((x_proj, y_proj))

    new_contour = cq.Workplane('XY').polyline(new_points).close().wire()
    face = cq.Face.makeFromWires(new_contour.val())
    area = face.Area()

    distance = math.sqrt((new_points[0][0] - new_points[-1][0]) ** 2 + (new_points[0][1] - new_points[-1][1]) ** 2)
    angle = math.acos(1 - distance ** 2 / (2 * int_radius_mm ** 2))
    sector = int_radius_mm ** 2 / 2 * (angle - math.sin(angle))
    middle = math.pi * int_radius_mm ** 2 - 2 * sector

    total_area_screw = 2 * area + middle

    total_moment = 30 * power_full / math.pi / rotation_speed  # в кН * м

    axial_force_screw = power_full * 60000 / rotation_speed / t_mm  # в кН
    axial_force_normal = total_area_screw * pressure_mpa / 1000

    axial_force = axial_force_screw + axial_force_normal

    border_angle_i = [2 * math.pi * (t_mm - x[0]) / t_mm for x in trapezoid_contour]
    border_points = []
    for i, j in zip(trapezoid_contour, border_angle_i):
        x_proj = i[1] * math.cos(j)
        y_proj = i[1] * math.sin(j)
        border_points.append((x_proj, y_proj))

    distance_c = math.sqrt(
        (border_points[1][0] - border_points[2][0]) ** 2 + (border_points[1][1] - border_points[2][1]) ** 2)
    distance_cd = distance_c / 2 + ext_radius_mm

    radial_force_cyl = b_ext_top * distance_cd * pressure_mpa / 1000  # в кН

    distance_l = math.sqrt(
        (border_points[1][0] + border_points[2][0]) ** 2 + (border_points[1][1] + border_points[2][1]) ** 2)
    radial_force_vpad = distance_l * t_mm * pressure_mpa / math.pi / 1000  # в кН

    radial_force = radial_force_vpad + radial_force_cyl

    b = 3 * thread_length_mm / 1000
    max_reaction = radial_force / 2 + total_moment / b
    min_reaction = radial_force / 2 - total_moment / b
    max_moment = radial_force * b / 4 + total_moment / 2

    temp_strength = 300
    diam_force = math.sqrt(4 * radial_force / math.pi / temp_strength / 1000) * 1000
    diam_moment = (32 * max_moment / temp_strength / 1000 / math.pi) ** (1 / 3) * 1000

    return max(diam_force / 2, diam_moment / 2)


def create_screw(results_dict, offset, lefthand):
    alpha = float(results_dict['alpha'])
    ext_radius_mm = float(results_dict['ext_radius_mm'])
    int_radius_mm = float(results_dict['int_radius_mm'])
    t_mm = float(results_dict['t_mm'])
    thread_length_mm = float(results_dict['thread_length_mm'])
    b_ext_top = float(results_dict['b_ext_top'])

    shift = 1
    add = (ext_radius_mm - int_radius_mm) * math.tan(math.radians(alpha))
    add_shift = shift / math.tan(math.radians(alpha))
    logger.info('Создаем винтовое тело')
    trapezoid = cq.Workplane('ZY').polyline([
        (-t_mm - shift + offset, int_radius_mm - add_shift),
        (-t_mm + add + shift + offset, ext_radius_mm + add_shift),
        (-t_mm + add + b_ext_top - shift + offset, ext_radius_mm + add_shift),
        (-t_mm + 2 * add + b_ext_top + shift + offset, int_radius_mm - add_shift)
    ]).close()

    spiral = cq.Wire.makeHelix(
        pitch=t_mm,
        height=thread_length_mm + 2 * t_mm,
        radius=ext_radius_mm,
        lefthand=lefthand,
        center=(0, 0, -t_mm + offset),
        dir=(0, 0, 1)
    )

    spiral_body = trapezoid.sweep(spiral, isFrenet=True)
    spiral_body = (spiral_body.union(spiral_body.rotate((0, 0, 0), (0, 0, 1), 180))
                   .union(create_cylinder(int_radius_mm, thread_length_mm + 2 * t_mm, offset - t_mm, 0, 0)))
    logger.info('Винтовое тело готово для вырезания')
    logger.info('Создаем тела для вырезания')
    parts_to_cut = [
        create_cylinder(2 * ext_radius_mm, -thread_length_mm, offset, 0, 0),
        create_cylinder(2 * ext_radius_mm, thread_length_mm, offset + thread_length_mm, 0, 0),
    ]
    body = spiral_body.cut(combine_parts(parts_to_cut)).cut(cq.Workplane('XY').workplane(offset=-2 * t_mm + offset).
                                                            circle(ext_radius_mm).circle(ext_radius_mm * 1.5).
                                                            extrude(thread_length_mm + 4 * t_mm))
    logger.info('Винтовое тело создано')

    return body


def create_driven_screw(results_dict, offset, first, second):
    ext_radius_mm = float(results_dict['ext_radius_mm'])
    int_radius_mm = float(results_dict['int_radius_mm'])
    thread_length_mm = float(results_dict['thread_length_mm'])

    r_max = calculate_min_diam(results_dict)

    dist = [int(thread_length_mm / d) for d in [1.5, 2.0, 2.8, 2.9, 0.95]]

    radius = [
        radius_check(ext_radius_mm, r_max, factor=1.1, label=1),
        radius_check(ext_radius_mm, r_max, label=2),
        radius_check(ext_radius_mm, r_max, factor=1.3, label=6)
    ]
    logger.info('Создаем части ведомого винта')
    parts = [
        create_cylinder(radius[0], dist[0], offset, 0, 0),
        create_cylinder(radius[1], dist[1], offset + dist[0], 0, 0),
        create_screw(results_dict, offset + dist[0] + dist[1], first),
        create_cylinder(int_radius_mm, dist[2], offset + dist[0] + dist[1] + thread_length_mm, 0, 0),
        create_screw(results_dict, offset + thread_length_mm + dist[0] + dist[1] + dist[2], second),
        create_cylinder(radius[1], dist[1], offset + 2 * thread_length_mm + sum(dist[:3]), 0, 0),
        create_cylinder(radius[0], dist[3], offset + 2 * thread_length_mm + sum(dist[:3]) + dist[1], 0, 0),
        create_cylinder(radius[2], dist[4], offset + 2 * thread_length_mm + sum(dist[:3]) + dist[1] + dist[3], 0, 0),
    ]

    mid_position = dist[0] + dist[1] + thread_length_mm + dist[2]/2
    logger.info('Создаем ведомый винт'),
    body = combine_parts(parts)
    logger.info('Ведомый винт создан'),

    return body, mid_position


def combine_parts(parts):
    return reduce(lambda a, b: a.union(b), parts)


def create_lead_screw(results_dict):
    ext_radius_mm = float(results_dict['ext_radius_mm'])
    thread_length_mm = float(results_dict['thread_length_mm'])

    r_max = calculate_min_diam(results_dict)

    dist_0 = int(thread_length_mm / 0.87)

    radius_0 = radius_check(ext_radius_mm, r_max, factor=1.15, label=0)
    logger.info('Создаем части ведущего винта')
    parts = [
        create_cylinder(radius_0, dist_0, 0, 0, 0),
        create_driven_screw(results_dict, dist_0, True, False)[0]
    ]
    body = combine_parts(parts)
    logger.info('Тело ведущего винта создано')

    return body


def create_cylinder(radius, height, offset, center_x, center_y):
    logger.info(f'Создаем цилиндр радиусом {radius}')
    return cq.Workplane('XY').workplane(offset=offset).moveTo(center_x, center_y).circle(radius).extrude(height)


def radius_check(radius_base, r_max, round_base=5, factor=1.0, label=None):
    radius = radius_round(radius_base, round_base, factor) / 2
    if radius >= r_max:
        return radius
    else:
        radius = round_base * math.ceil(r_max / round_base)
        if label:
            print(f'⚠️ Радиус {label} меньше допустимого — установлен r_max')
        return radius


def radius_round(radius_base, round_base=5.0, factor=1.0):
    return round_base * math.ceil(radius_base / factor / round_base)
