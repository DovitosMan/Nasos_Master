from django.shortcuts import render
import math
import numpy as np
from scipy.optimize import bisect
from functools import partial
from tqdm import tqdm
import itertools
import pandas as pd
import logging
import cadquery as cq
from cadquery import exporters, Compound

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

        result, model = calculate(**input_data)

        print("Лучшие параметры и вычисленные значения:")

        if result is None:
            raise ValueError("Не удалось получить результат из twin_screw, параметры не валидны")
        else:
            for key, value in result.items():
                print(f"{key}: {value}")

        create_bodies(model)

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

        axis_dist = round((ext_r + int_r + screw_gap) / 0.1) * 0.1
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

    power_gap = pressure_mpa * (feed_loss / 60 / 60) * 1000
    power_theory = pressure_mpa * (flow_rate_theory / 60 / 60) * 1000
    power_required = power_theory / kpd_mech
    power_full = power_required + power_gap

    kpd_total = kpd_mech * kpd_vol_2

    # Возвращаем результаты
    results_dict = {
        "flow_rate": flow_rate,
        "pressure": pressure,
        "rotation_speed": rotation_speed,
        "temperature": temperature,
        "flow_rate_real": flow_rate_real,
        "kpd_vol": kpd_vol_2,
        "kpd_mech": kpd_mech,
        "kpd_total": kpd_total,
        "delta_t_val": delta_t_val,
        "stator_gap": stator_gap,
        "screw_gap": screw_gap,
        "side_gap": side_gap,
        "power_full": power_full,
        "effective_koef": power_full / flow_rate_real,
        "r_ratio": r_ratio_b,
        "t_ratio": t_ratio_b,
        "alpha": alpha_b,
        "ext_radius_mm": ext_r,
        "int_radius_mm": int_r,
        "t_mm": t,
        "axis_dist": axis_dist,
        "thread_length_mm": thread_length_mm,
        "phi": phi,
        "lambda_val": lambda_val,
        "b_ext_top": b_ext_top,
        "b_int_low": b_int_low,
        "b_ext_low": b_ext_low,
        "density": density,
        "viscosity_dyn": viscosity,
        "viscosity_kin": viscosity_kin,
        "heat_capacity": heat_capacity,
        "feed_loss": feed_loss,
        "flow_rate_theory": flow_rate_theory,
        "power_gap": power_gap,
        "power_theory": power_theory,
        "power_required": power_required,
    }

    results_model = {
        "alpha": float(alpha_b),
        "ext_radius_mm": float(ext_r),
        "int_radius_mm": float(int_r),
        "t_mm": float(t),
        "axis_dist": float(axis_dist),
        "thread_length_mm": float(thread_length_mm),
        "b_ext_top": float(b_ext_top),
        "b_int_low": float(b_int_low),
    }

    df = pd.DataFrame([results_dict])  # одна строка таблицы

    # Имя файла по наружному диаметру
    ext_diam = round(ext_r * 2, 1)
    filename = f"twin_screw_D{ext_diam}mm.xlsx"

    # Сохранение
    df.to_excel(filename, index=False)
    print(f"Результаты сохранены в файл: {filename}")

    return results_dict, results_model


def create_bodies(results_model):
    alpha = results_model['alpha']
    ext_radius_mm = results_model['ext_radius_mm']
    int_radius_mm = results_model['int_radius_mm']
    t_mm = results_model['t_mm']
    axis_dist = results_model['axis_dist']
    thread_length_mm = results_model['thread_length_mm']
    b_ext_top = results_model['b_ext_top']
    b_int_low = results_model['b_int_low']

    int_circle = cq.Workplane('XY').workplane(offset=-t_mm).circle(int_radius_mm)
    int_circle_extruded = int_circle.extrude(thread_length_mm + 2 * t_mm)

    shift = 1
    add = (ext_radius_mm - int_radius_mm) * math.tan(math.radians(alpha))
    add_shift = shift / math.tan(math.radians(alpha))
    trapezoid = cq.Workplane('ZY').polyline([
        (-t_mm - shift, int_radius_mm - add_shift),
        (-t_mm + add + shift, ext_radius_mm + add_shift),
        (-t_mm + add + b_ext_top - shift, ext_radius_mm + add_shift),
        (-t_mm + 2 * add + b_ext_top + shift, int_radius_mm - add_shift)
    ]).close()

    spiral = cq.Wire.makeHelix(
        pitch=t_mm,
        height=thread_length_mm + 2 * t_mm,
        radius=ext_radius_mm,
        lefthand=False,
        center=(0, 0, -t_mm),
        dir=(0, 0, 1)
    )

    spiral_body_1 = trapezoid.sweep(spiral, isFrenet=True)
    spiral_body_2 = spiral_body_1.rotate((0, 0, 0), (0, 0, 1), 180)

    ext_circle = cq.Workplane('XY').workplane(offset=-2 * t_mm).circle(ext_radius_mm).circle(ext_radius_mm * 1.5)
    ext_circle_extruded = ext_circle.extrude(thread_length_mm + 4 * t_mm)

    circle_cut_1 = cq.Workplane('XY').circle(2 * ext_radius_mm)
    circle_cut_2 = cq.Workplane('XY').workplane(offset=thread_length_mm).circle(2 * ext_radius_mm)
    circle_cut_1_extruded = circle_cut_1.extrude(-thread_length_mm)
    circle_cut_2_extruded = circle_cut_2.extrude(thread_length_mm)

    body_1 = (
        int_circle_extruded.
        union(spiral_body_1).
        union(spiral_body_2).
        cut(ext_circle_extruded).
        cut(circle_cut_1_extruded).
        cut(circle_cut_2_extruded)
    )

    rotate_dist = b_int_low + add
    rotate_angle = 360 * rotate_dist / t_mm

    body_2 = body_1.mirror('YZ').rotate((0, 0, 0), (0, 0, 1), angleDegrees=rotate_angle)

    exporters.export(body_1, 'first_screw.step')
    logger.info('Первый вал успешно создан и экспортирован в first_screw.step')
    exporters.export(body_2, 'second_screw.step')
    logger.info('Второй вал успешно создан и экспортирован в second_screw.step')

    first_screw = cq.importers.importStep('first_screw.step')
    second_screw = cq.importers.importStep('second_screw.step')

    assembly = cq.Assembly()
    assembly.add(first_screw, name='first_screw', loc=cq.Location(cq.Vector(0, axis_dist / 2, 0)))
    assembly.add(second_screw, name='second_screw', loc=cq.Location(cq.Vector(0, -axis_dist / 2, 0)))
    exporters.export(assembly.toCompound(), 'twin_assembly.step')
    logger.info('Сборка успешно создана и экспортирована в twin_assembly.step')
