from django.shortcuts import render
from django.http import HttpResponse
import cadquery as cq
from cadquery import exporters
import logging
import os
import math
import zipfile
import numpy as np
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def screw(request):
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Подача, м³/ч', 'name': 'flow_rate', 'value': ''},
            {'type': 'float', 'placeholder': 'Напор, м', 'name': 'pressure', 'value': ''},
            {'type': 'float', 'placeholder': 'Вязкость · 10⁻⁶, м²/с', 'name': 'viscosity', 'value': ''},
            {'type': 'float', 'placeholder': 'Диаметр винта, мм', 'name': 'diam', 'value': ''},
            {'type': 'float', 'placeholder': 'Число витков, шт.', 'name': 'turns', 'value': ''},
            {'type': 'float', 'placeholder': 'Частота вращения, об/мин', 'name': 'rotation_speed', 'value': ''},
        ],
        'error': "",
        'message': "",
        'logs': [],
        'input_data': {},
        'recommendations': [],
        'debug_test': False,
        'pause_calculations': False

    }

    if request.method == "POST":
        if 'calculate_params' in request.POST:
            context['pause_calculations'] = True
        else:
            context['pause_calculations'] = False
        print(context['pause_calculations'])
        for select in context['calc']:
            if select['type'] == 'float':
                name = select['name']
                select['value'] = request.POST.get(name, "")

        # print(context['calc'])
        flow_rate = float(request.POST.get("flow_rate").replace(',', '.'))
        pressure = float(request.POST.get("pressure").replace(',', '.'))
        viscosity = float(request.POST.get("viscosity").replace(',', '.'))
        if flow_rate and pressure:
            try:
                context['input_viscosity'] = viscosity
                rotation_speed = request.POST.get("rotation_speed")
                if rotation_speed:
                    rotation_speed = float(rotation_speed.replace(',', '.'))
                else:
                    rotation_speed = None

                context['input_feed'] = flow_rate
                context['input_pressure'] = pressure
                context['input_rotation_speed'] = rotation_speed

                if context['pause_calculations']:
                    turns = calculate_turns(pressure)
                    context['turns'] = turns
                    if flow_rate <= 0 or pressure <= 0:
                        raise ValueError("Все входные значения должны быть положительными числами.")
                    n_rec, d_rec, feed_rec, powers = calculate_data(flow_rate, pressure, rotation_speed)

                    if d_rec:
                        context['calculated_diam'] = (d_rec[0] if isinstance(d_rec, list) else d_rec) * 1000  # Переводим в мм
                    if n_rec:
                        context['calculated_rotation_speed'] = n_rec[0] if isinstance(n_rec, list) else n_rec
                    qh_plot = calculate_qh_characteristic(d_rec, feed_rec, pressure)

                    kpd_plot, is_low_pressure = calculate_kpd_characteristic(d_rec, feed_rec, pressure, viscosity,
                                                                             rotation_speed)
                    power_plot, is_power_error = calculate_power_characteristic(d_rec, feed_rec, pressure, viscosity, turns,
                                                                                rotation_speed)

                    feed_p, kpd_volumetric_p, kpd_mechanical_p, kpd_total_p, power_t_p, power_eff_p, power_nominal_p = (
                        print_data(d_rec, pressure, rotation_speed, viscosity, turns))

                    force_plot = 'force_plot' in request.POST

                    if (is_low_pressure or is_power_error) and not force_plot:
                        context['error'] = "Внимание: давление слишком низкое, что может привести к некорректной работе насоса."
                        context['is_low_pressure'] = True
                        plots = []
                    else:
                        plots = [
                            qh_plot,
                            kpd_plot,
                            power_plot,
                        ]
                        context['is_low_pressure'] = False
                    context['plots'] = plots

                    # Передаем значения в контекст
                    context['feed_real'] = float(feed_p)  # Фактический расход
                    context['user_pressure'] = float(pressure)
                    context['kpd_volumetric'] = float(kpd_volumetric_p)  # Объемный КПД
                    context['kpd_mechanical'] = float(kpd_mechanical_p)  # Механический КПД
                    context['kpd_total'] = float(kpd_total_p)  # Полный КПД
                    context['power_t'] = float(power_t_p)  # Теоретическая мощность
                    context['power_eff'] = float(power_eff_p)  # Эффективная мощность
                    context['power_nominal'] = float(power_nominal_p)  # Номинальная мощность

                if 'download_model' in request.POST:
                    response = handle_download_model(request, context)
                    if response:
                        return response

            except ValueError as e:
                context['error'] = f"Ошибка ввода: {str(e)}"
                logger.warning(f"Некорректный ввод: {str(e)}")
            except Exception as e:
                context['message'] = f"Нажмите кнопку Построить график"
                logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)

    return render(request, 'screw.html', context)


def calculate_mid_point(p1, p2, center, radius, is_lower=False):
    mid_x = (p1[0] + p2[0]) / 2
    y_offset = math.sqrt(radius ** 2 - (mid_x - center[0]) ** 2)
    mid_y = center[1] - y_offset if is_lower else center[1] + y_offset
    return (mid_x, mid_y)


def create_section_lead(d):
    try:
        R = d * 5 / 6  # Главный радиус
        r = d * 9 / 16  # Боковой радиус
        r_small = d * 19 / 80  # Малый радиус
        r_low = d * 1 / 2  # Нижний радиус

        centers = [
            (0.0, 0.0),  # Центр нижней дуги
            (0.1394955476 * d, 0.4801468810 * d),  # Центр малой дуги
            (-0.1793279524 * d, 0.4170867143 * d),  # Центр боковой дуги
            (0.0, 0.0),  # Центр главной дуги
            (-0.0, 0.0),  # Центр главной дуги отраженный
            (0.1793279524 * d, 0.4170867143 * d),  # Центр боковой дуги отраженный
            (-0.1394955476 * d, 0.4801468810 * d),  # Центр малой дуги отраженный
            (-0.0, 0.0),  # Центр нижней дуги отраженный
            (-0.0, -0.0),  # Центр нижней дуги отраженный 2
            (-0.1394955476 * d, -0.4801468810 * d),  # Центр малой дуги отраженный 2
            (0.1793279524 * d, -0.4170867143 * d),  # Центр боковой дуги отраженный 2
            (-0.0, -0.0),  # Центр главной дуги отраженный 2
            (0.0, -0.0),  # Центр главной дуги отраженный 3
            (-0.1793279524 * d, -0.4170867143 * d),  # Центр боковой дуги отраженный 3
            (0.1394955476 * d, -0.4801468810 * d),  # Центр малой дуги отраженный 3
            (0.0, -0.0),  # Центр нижней дуги отраженный 3
        ]

        points = [
            (r_low, 0),  # Точка a
            (0.34530280952381 * d, 0.361615785714286 * d),  # Точка b
            (0.372481928571429 * d, 0.52622930952381 * d),  # Точка c
            (0.232492571428571 * d, 0.800244785714286 * d),  # Точка d
            (0.0, R),  # Точка e
            (-0.232492571428571 * d, 0.800244785714286 * d),  # Точка d отраженная
            (-0.372481928571429 * d, 0.52622930952381 * d),  # Точка c отраженная
            (-0.34530280952381 * d, 0.361615785714286 * d),  # Точка b отраженная
            (-r_low, 0),  # Точка a отраженная
            (-0.34530280952381 * d, -0.361615785714286 * d),  # Точка b отраженная 2
            (-0.372481928571429 * d, -0.52622930952381 * d),  # Точка c отраженная 2
            (-0.232492571428571 * d, -0.800244785714286 * d),  # Точка d отраженная 2
            (-0.0, -R),  # Точка e отраженная 2
            (0.232492571428571 * d, -0.800244785714286 * d),  # Точка d отраженная 3
            (0.372481928571429 * d, -0.52622930952381 * d),  # Точка c отраженная 3
            (0.34530280952381 * d, -0.361615785714286 * d),  # Точка b отраженная 3
            (r_low, -0),  # Точка a отраженная 3
        ]

        mid_points = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            center = centers[i]
            radius = r_low if i in [0, 7, 8, 15] else r_small if i in [1, 6, 9, 14] else r if i in [2, 5, 10, 13] else R
            is_lower = True if i in [1, 6, 8, 10, 11, 12, 13, 15] else False
            mid_points.append(calculate_mid_point(p1, p2, center, radius, is_lower))

        section = cq.Workplane("XY").moveTo(points[0][0], points[0][1])  # Начало в точке a

        for i in range(len(mid_points)):
            section = section.threePointArc(
                (mid_points[i][0], mid_points[i][1]),  # Средняя точка
                (points[i + 1][0], points[i + 1][1])  # Конечная точка
            )

        section = section.close()

        exporters.export(section, 'debug_section_lead.step')
        logger.info("Сечение успешно создано и экспортировано в debug_section_lead.step")

        return section

    except Exception as e:
        logger.error(f"Ошибка создания сечения: {str(e)}", exc_info=True)
        raise


def create_trapezoid_lead(d, num_turns):
    try:
        r_low = d * 1 / 2  # Нижний радиус
        width = d / 4
        height = d / 2
        angle = 30
        slant_height = height / math.tan(math.radians(angle))

        trapezoid = cq.Workplane("ZY").polyline([
            ((10 * d / 3) * num_turns + width, height + r_low - 1),
            ((10 * d / 3) * num_turns - slant_height, height + r_low - 1),
            ((10 * d / 3) * num_turns, r_low - 1),
            ((10 * d / 3) * num_turns + width, r_low - 1)
        ]).close()

        exporters.export(trapezoid, 'debug_trapezoid_lead.step')
        logger.info("Трапеция успешно создана и экспортирована в debug_trapezoid_lead.step")

        return trapezoid
    except Exception as e:
        logger.error(f"Ошибка создания трапеции: {str(e)}", exc_info=True)
        raise


def create_body_lead(d, num_turns):
    try:
        section = create_section_lead(d)

        screw_body = section.twistExtrude(distance=(10 * d / 3) * num_turns, angleDegrees=360 * num_turns)

        trapezoid = create_trapezoid_lead(d=d, num_turns=num_turns)

        trapezoid_revolved = trapezoid.revolve(axisStart=(0, 0, 0), axisEnd=(1, 0, 0), angleDegrees=360)

        result_cut = screw_body.cut(trapezoid_revolved)

        top_face = cq.Workplane('XY').workplane(offset=(10 * d / 3) * num_turns)
        circle = top_face.circle(d / 2 - 1)
        circle_extruded = circle.extrude(math.ceil(d / 3 + 2) * 5)
        result_union = result_cut.union(circle_extruded)

        if result_union.val().isValid():
            exporters.export(result_union, 'screw_lead.step')
            logger.info("Модель успешно создана и экспортирована в screw_lead.step")
            return True
        else:
            raise RuntimeError("Некорректная геометрия после выдавливания")

    except Exception as e:
        logger.error(f"Ошибка при выдавливании: {str(e)}", exc_info=True)
        raise


def create_section_driven(d):
    try:
        r_5 = d * 1 / 2
        r_6 = d * 19 / 80
        r_7 = d * 3 / 10
        r_8 = d * 1 / 6
        r_9 = d * 31 / 160

        centers = [
            (0.0, 0.0),  # Центр дуги r5
            (0.1394955476 * d, 0.4801468810 * d),  # Центр дуги r6 = r3
            (0.0430406905 * d, 0.4354444762 * d),  # Центр дуги r7
            (0.1005530476 * d, 0.3461058571 * d),  # Центр дуги r9
            (0.0, 0.0),  # Центр дуги r8
            (-0.0, 0.0),  # Центр дуги r8 отраженный
            (-0.1005530476 * d, 0.3461058571 * d),  # Центр дуги r9 отраженный
            (-0.0430406905 * d, 0.4354444762 * d),  # Центр дуги r7 отраженный
            (-0.1394955476 * d, 0.4801468810 * d),  # Центр дуги r6 = r3 отраженный
            (-0.0, 0.0),  # Центр дуги r5 отраженный
            (-0.0, -0.0),  # Центр дуги r5 отраженный 2
            (-0.1394955476 * d, -0.4801468810 * d),  # Центр дуги r6 = r3 отраженный 2
            (-0.0430406905 * d, -0.4354444762 * d),  # Центр дуги r7 отраженный 2
            (-0.1005530476 * d, -0.3461058571 * d),  # Центр дуги r9 отраженный 2
            (-0.0, -0.0),  # Центр дуги r8 отраженный 2
            (0.0, -0.0),  # Центр дуги r8 отраженный 3
            (0.1005530476 * d, -0.3461058571 * d),  # Центр дуги r9 отраженный 3
            (0.0430406905 * d, -0.4354444762 * d),  # Центр дуги r7 отраженный 3
            (0.1394955476 * d, -0.4801468810 * d),  # Центр дуги r6 = r3 отраженный 3
            (0.0, -0.0),  # Центр дуги r5 отраженный 3
        ]

        points = [
            (r_5, 0),  # Точка f
            (0.34530280952381 * d, 0.361615785714286 * d),  # Точка g = b
            (0.32422885714286 * d, 0.330882452380952 * d),  # Точка i
            (0.20542857142857 * d, 0.183194261904762 * d),  # Точка j
            (0.04649852380952 * d, 0.160048952380952 * d),  # Точка k
            (0.0, r_8),  # Точка l
            (-0.04649852380952 * d, 0.160048952380952 * d),  # Точка k отраженная
            (-0.20542857142857 * d, 0.183194261904762 * d),  # Точка j отраженная
            (-0.32422885714286 * d, 0.330882452380952 * d),  # Точка i отраженная
            (-0.34530280952381 * d, 0.361615785714286 * d),  # Точка g = b отраженная
            (-r_5, 0),  # Точка f отраженная
            (-0.34530280952381 * d, -0.361615785714286 * d),  # Точка g = b отраженная 2
            (-0.32422885714286 * d, -0.330882452380952 * d),  # Точка i отраженная 2
            (-0.20542857142857 * d, -0.183194261904762 * d),  # Точка j отраженная 2
            (-0.04649852380952 * d, -0.160048952380952 * d),  # Точка k отраженная 2
            (-0.0, -r_8),  # Точка l отраженная 2
            (0.04649852380952 * d, -0.160048952380952 * d),  # Точка k отраженная 3
            (0.20542857142857 * d, -0.183194261904762 * d),  # Точка j отраженная 3
            (0.32422885714286 * d, -0.330882452380952 * d),  # Точка i отраженная 3
            (0.34530280952381 * d, -0.361615785714286 * d),  # Точка g = b отраженная 3
            (r_5, -0),  # Точка f отраженная 3
        ]

        mid_points = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            center = centers[i]
            radius = r_5 if i in [0, 9, 10, 19] else r_6 if i in [1, 8, 11, 18] \
                else r_7 if i in [2, 7, 12, 17] else r_9 if i in [3, 6, 13, 16] else r_8
            is_lower = True if i in [1, 2, 3, 6, 7, 8, 10, 14, 15, 19] else False
            mid_points.append(calculate_mid_point(p1, p2, center, radius, is_lower))

        section = cq.Workplane("XY").moveTo(points[0][0], points[0][1])  # Начало в точке a

        for i in range(len(mid_points)):
            section = section.threePointArc(
                (mid_points[i][0], mid_points[i][1]),  # Средняя точка
                (points[i + 1][0], points[i + 1][1])  # Конечная точка
            )

        section = section.close()

        exporters.export(section, 'debug_section_driven.step')
        logger.info("Сечение успешно создано и экспортировано в debug_section_driven.step")

        return section

    except Exception as e:
        logger.error(f"Ошибка создания сечения: {str(e)}", exc_info=True)
        raise


def create_body_driven(d, num_turns):
    try:
        section = create_section_driven(d)
        screw_length = (100 * d / 27) * num_turns

        screw_body = section.twistExtrude(screw_length, angleDegrees=-400 * num_turns)

        top_face = cq.Workplane('XY').workplane(offset=screw_length)
        circle = top_face.circle(d / 2)
        circle_extruded = circle.extrude(math.ceil(d / 6) * 5)
        result_union = screw_body.union(circle_extruded)

        filleted_body = result_union

        if filleted_body.val().isValid():
            exporters.export(filleted_body, 'screw_driven.step')
            logger.info("Модель успешно создана и экспортирована в screw_driven.step")
            return True
        else:
            raise RuntimeError("Некорректная геометрия после выдавливания")

    except Exception as e:
        logger.error(f"Ошибка при выдавливании: {str(e)}", exc_info=True)
        raise


def create_section_stator(d, num_turns, rotation_speed):
    try:
        r_stator = math.ceil(2 * d / 2.5) * 2.5
        r_lead = 5 * d / 6
        r_driven = d / 2
        r_extrude = math.ceil(1.7 * d / 2.5) * 2.5

        square_mm = 1.240623 * math.pow(d, 2)
        step = 10 * d / 3
        feed_mm_s = square_mm * step * rotation_speed / 60
        feed_m_h = feed_mm_s * 60 * 60 / 1000000000
        velocity_m_s = feed_mm_s / square_mm / 1000

        r_exit = math.ceil(math.sqrt(feed_m_h / 2500 / velocity_m_s / math.pi) * 1000)

        # Создаем сечения
        section1 = cq.Workplane("XY").circle(r_stator)
        section2 = cq.Workplane("XY").circle(r_lead)
        section3 = cq.Workplane("XY").transformed(offset=(0, d, 0)).circle(r_driven)
        section4 = cq.Workplane("XY").transformed(offset=(0, -d, 0)).circle(r_driven)
        section5 = cq.Workplane("XY").transformed(offset=(0, 0, 10 * d / 3 * num_turns - d + 10)).circle(r_extrude)
        section6 = cq.Workplane("XZ").transformed(offset=(0, 10 * d / 3 * num_turns - d + 20 + r_exit, 0)).circle(r_exit)

        exporters.export(section1, 'debug_section1_stator.step')
        exporters.export(section2, 'debug_section2_stator.step')
        exporters.export(section3, 'debug_section3_stator.step')
        exporters.export(section4, 'debug_section4_stator.step')
        exporters.export(section5, 'debug_section5_stator.step')
        exporters.export(section6, 'debug_section6_stator.step')

        return section1, section2, section3, section4, section5, section6

    except Exception as e:
        logger.error(f"Ошибка создания сечения: {str(e)}", exc_info=True)
        raise


def extrude_stator(d, num_turns, rotation_speed):
    try:
        section1, section2, section3, section4, section5, section6 = create_section_stator(d, num_turns, rotation_speed)

        # Выдавливаем первое сечение
        extrusion_length = 10 * d / 3 * num_turns + 2 * d
        solid = section1.extrude(extrusion_length)

        # Вырезаем остальные сечения
        solid = solid.cut(section2.extrude(extrusion_length))
        solid = solid.cut(section3.extrude(extrusion_length))
        solid = solid.cut(section4.extrude(extrusion_length))
        solid = solid.cut(section5.extrude(extrusion_length))
        solid = solid.cut(section6.extrude(extrusion_length))

        if solid.val().isValid():
            exporters.export(solid, 'stator.step')
            logger.info("Модель успешно создана и экспортирована в stator.step")
            return True
        else:
            raise RuntimeError("Некорректная геометрия после выдавливания")

    except Exception as e:
        logger.error(f"Ошибка при выдавливании: {str(e)}", exc_info=True)
        raise


def create_assembly(d):
    try:
        lead_screw = cq.importers.importStep('screw_lead.step')
        driven_screw = cq.importers.importStep('screw_driven.step')
        stator = cq.importers.importStep('stator.step')

        assembly = cq.Assembly()
        assembly.add(lead_screw, name='lead_screw', loc=cq.Location(cq.Vector(0, 0, 0)))
        assembly.add(driven_screw, name='driven_screw_1', loc=cq.Location(cq.Vector(0, d, 0)))
        assembly.add(driven_screw, name='driven_screw_2', loc=cq.Location(cq.Vector(0, -d, 0)))
        assembly.add(stator, name='stator', loc=cq.Location(cq.Vector(0, 0, -10)))

        exporters.export(assembly.toCompound(), 'pump_assembly.step')
        logger.info('Сборка успешно создана и экспортирована в pump_assembly.step')

        return assembly

    except Exception as e:
        logger.error(f"Ошибка создания сборки: {str(e)}", exc_info=True)
        raise


def calculate_data(flow_rate, pressure, rotation_speed=None):
    kpd_vol_pre = 0.85
    feed_ls = flow_rate * 5 / 18  # Перевод из м3/ч в л/с
    pressure_kg_sm = pressure * 0.1  # Перевод из м в кгс/см2

    rotation_speed_max = math.floor(8175 / math.sqrt(feed_ls / kpd_vol_pre))
    len_iterations = math.floor(rotation_speed_max / 50)

    if len_iterations <= 0:
        raise ValueError("Невозможно выполнить расчет: недостаточное количество итераций.")

    def calculate_parameters(n):
        d_i_pre = 10 * math.pow(feed_ls / (0.068924 * n * kpd_vol_pre * math.pow(10, 6)), 1 / 3)
        d_i = math.ceil(d_i_pre * 1000) / 1000
        feed_i_pre = math.ceil(0.068924 * math.pow(d_i, 3) * n * 1000000) / 1000000
        feed_i_d = math.ceil(feed_i_pre * 60 * 60 * 1000000) / 1000000
        power_i = math.ceil(pressure_kg_sm * feed_i_pre * 1000 * 1000) / 1000
        return n, d_i, feed_i_d, power_i

    n_rec, d_rec, feed_rec, powers = [], [], [], []
    for i in range(1, len_iterations + 1):
        n_i = 50 * i
        n, d, f, p = calculate_parameters(n_i)
        if f >= flow_rate:
            n_rec.append(n)
            d_rec.append(d)
            feed_rec.append(f)
            powers.append(p)

    combined = list(zip(n_rec, d_rec, feed_rec, powers))
    combined_sorted = sorted(combined, key=lambda x: x[3])
    combined_filtered = combined_sorted[:7]
    n_rec, d_rec, feed_rec, powers = zip(*combined_filtered)
    n_rec, d_rec, feed_rec, powers = list(n_rec), list(d_rec), list(feed_rec), list(powers)

    if rotation_speed is not None:
        n, d, f, p = calculate_parameters(rotation_speed)
        return [n, d, f, p]

    n_rec_filtered = [n for n in n_rec if n > 1450]
    if n_rec_filtered:
        filtered_combined = [(n, d, f, p) for n, d, f, p in zip(n_rec, d_rec, feed_rec, powers) if n > 1450]
        if len(filtered_combined) > 2:
            filtered_combined_sorted_by_power = sorted(filtered_combined, key=lambda x: x[3])
            selected_item = filtered_combined_sorted_by_power[0]
        else:
            selected_item = filtered_combined[0]
        return [selected_item[0]], [selected_item[1]], [selected_item[2]], [selected_item[3]]
    else:
        if rotation_speed_max < 1450:
            n_i = (rotation_speed_max // 50) * 50
        else:
            n_i = 1450
        n, d, f, p = calculate_parameters(n_i)
        return [n], [d], [f], [p]


def calculate_turns(pressure):
    if pressure < 100:
        return 1.5
    elif 100 <= pressure < 300:
        return 2
    elif 300 <= pressure < 600:
        return 3
    elif 600 <= pressure < 1000:
        return 5
    else:
        raise ValueError("Давление должно быть меньше 1000")


def calculate_common_params(d, pressure, num=50):
    velocity = math.ceil(83.331379 * d * 1000000) / 1000000  # м/с
    pressure_values = np.linspace(0, pressure * 1.1, num=num)
    return velocity, pressure_values


def calculate_feed_loss(d, velocity, pressure_values):
    return 3 * d * velocity * np.sqrt(pressure_values) * 0.001 * 60 * 60 / 11


def create_plotly_figure(plots, title, xaxis_title, yaxis_title):
    fig = go.Figure()
    for plot in plots:
        fig.add_scatter(**plot)
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        hovermode='x',
        showlegend=True
    )
    return fig


def calculate_qh_characteristic(d, flow_rate, pressure):
    velocity, pressure_values = calculate_common_params(d, pressure)
    feed_loss = calculate_feed_loss(d, velocity, pressure_values)
    feed_real = flow_rate - feed_loss

    plots = [
        {'x': pressure_values, 'y': np.full_like(pressure_values, flow_rate), 'name': 'Теоретическая подача'},
        {'x': pressure_values, 'y': feed_real, 'name': 'Фактическая подача'}
    ]

    fig = create_plotly_figure(plots, 'Характеристика подачи', 'Напор, м', 'Подача, м3/ч')
    return fig.to_html(full_html=False)


def calculate_kpd_characteristic(d, flow_rate, pressure, viscosity, rotation_speed):
    velocity, pressure_values = calculate_common_params(d, pressure)
    feed_loss = calculate_feed_loss(d, velocity, pressure_values)
    feed_real = flow_rate - feed_loss

    power_t = (pressure_values / 10) * (feed_real * 1000 / 60 / 60)

    viscosity_sm = viscosity * math.pow(10, -2)
    viscosity_e = (viscosity_sm + math.sqrt(math.pow(viscosity_sm, 2) + 0.03996)) / (2 * 0.074)
    power_viscosity_loss = 0.4 * math.pow(viscosity_e / 6.4, 1 / 1.8)

    moment_lead = 0.727499 * (pressure_values / 10) * (math.pow(d * 10, 3)) * 1000
    moment_driven = -0.034664 * (pressure_values / 10) * (math.pow(d * 10, 3)) * 1000
    moment = moment_lead + 2 * moment_driven
    power_moment_loss = moment * rotation_speed / 60 / 1019.8

    force_radial = 1.399945 * (pressure_values / 10) * math.pow(d * 10, 2) * 100
    power_friction_loss = (np.pi * rotation_speed * force_radial * d / 60) * 0.009807

    power_loss = power_viscosity_loss + power_moment_loss + power_friction_loss
    kpd_mechanical = np.where(
        power_t != 0,
        np.clip(100 * (1 - power_loss / power_t), 0, 100),
        0
    )

    kpd_volumetric = np.where(
        flow_rate != 0,
        np.clip(100 * (feed_real / flow_rate), 0, 100),
        0
    )

    kpd_total = kpd_volumetric / 100 * kpd_mechanical / 100 * 100

    is_low_pressure = kpd_total[1] == 0

    plots = [
        {'x': pressure_values, 'y': np.full_like(pressure_values, kpd_volumetric), 'name': 'Объемный КПД'},
        {'x': pressure_values, 'y': np.full_like(pressure_values, kpd_mechanical), 'name': 'Механический КПД'},
        {'x': pressure_values, 'y': np.full_like(pressure_values, kpd_total), 'name': 'Полный КПД'}
    ]

    fig = create_plotly_figure(plots, 'Характеристика КПД', 'Напор, м', 'КПД, %')
    return fig.to_html(full_html=False), is_low_pressure


def calculate_power_characteristic(d, flow_rate, pressure, viscosity, num_turns, rotation_speed):
    velocity, pressure_values = calculate_common_params(d, pressure)
    feed_loss = calculate_feed_loss(d, velocity, pressure_values)
    feed_real = flow_rate - feed_loss

    kpd_volumetric = (feed_real / flow_rate) * 100

    power_t = (pressure_values / 10) * (feed_real * 1000 / 60 / 60)

    viscosity_sm = viscosity * math.pow(10, -2)
    viscosity_e = (viscosity_sm + math.sqrt(math.pow(viscosity_sm, 2) + 0.03996)) / (2 * 0.074)
    power_viscosity_loss = 0.4 * math.pow(viscosity_e / 6.4, 1 / 1.8)

    length = 10 * d * num_turns / 3
    power_length_loss = 100 * pressure_values * length * math.pow(d, 2)

    moment_lead = 0.727499 * (pressure_values / 10) * (math.pow(d * 10, 3)) * 1000
    moment_driven = -0.034664 * (pressure_values / 10) * (math.pow(d * 10, 3)) * 1000
    moment = moment_lead + 2 * moment_driven
    power_moment_loss = moment * rotation_speed / 60 / 1019.8

    force_radial = 1.399945 * (pressure_values / 10) * math.pow(d * 10, 2) * 100
    power_friction_loss = (np.pi * rotation_speed * force_radial * d / 60) * 0.009807

    power_loss = power_viscosity_loss + power_moment_loss + power_friction_loss
    kpd_mechanical = np.zeros_like(power_t)
    kpd_mechanical[1:] = np.where(power_t[1:] != 0, (1 - power_loss[1:] / power_t[1:]) * 100, 0)

    kpd = kpd_volumetric / 100 * kpd_mechanical / 100

    feed_loss_user = calculate_feed_loss(d, velocity, np.array([pressure]))[0]
    feed_real_user = flow_rate - feed_loss_user

    power_eff = np.zeros_like(power_t)
    power_eff[1:] = power_t[1:] - power_loss[1:] - power_length_loss[1:]

    power_start = calculate_start_power(d, pressure, rotation_speed, feed_real_user, viscosity)
    power_nominal = np.where(
        np.abs(kpd) > 1e-10,
        power_eff / kpd + power_start,
        power_start
    )

    is_power_increasing = all(power_nominal[i] <= power_nominal[i + 1] for i in range(len(power_nominal) - 1))
    if not is_power_increasing:
        return None, True

    plots = [
        {'x': pressure_values, 'y': power_nominal, 'name': 'Номинальная мощность'},
        {'x': pressure_values, 'y': power_t, 'name': 'Теоретическая мощность'},
        {'x': pressure_values, 'y': power_eff, 'name': 'Эффективная мощность'}
    ]

    fig = create_plotly_figure(plots, 'Характеристика мощности', 'Напор, м', 'Мощность, кВт')
    return fig.to_html(full_html=False), False


def calculate_start_power(d, pressure, rotation_speed, flow_rate, viscosity):
    frictional_koef = 0.05

    force_radial = 1.399945 * (pressure / 10) * math.pow(d * 10, 2) * 100
    moment_frictional = force_radial * frictional_koef * (d * 10 / 2)

    power_t_user = (pressure / 10) * (flow_rate * 1000 / 60 / 60)
    moment_exp = power_t_user * 936.55 / rotation_speed

    moment_start = (moment_frictional + moment_exp) * 10

    viscosity_sm = viscosity * math.pow(10, -2)
    viscosity_e = (viscosity_sm + math.sqrt(math.pow(viscosity_sm, 2) + 0.03996)) / (2 * 0.074)
    power_viscosity_loss = 0.4 * math.pow(viscosity_e / 6.4, 1 / 1.8)

    moment_lead = 0.727499 * (pressure / 10) * (math.pow(d * 10, 3)) * 1000
    moment_driven = -0.034664 * (pressure / 10) * (math.pow(d * 10, 3)) * 1000
    moment = moment_lead + 2 * moment_driven
    power_moment_loss = moment * rotation_speed / 60 / 1019.8

    force_radial = 1.399945 * (pressure / 10) * math.pow(d * 10, 2) * 100
    power_friction_loss = (np.pi * rotation_speed * force_radial * d / 60) * 0.009807

    power_loss_user = power_viscosity_loss + power_moment_loss + power_friction_loss
    kpd_mechanical = (1 - power_loss_user / power_t_user)

    power_start = moment_start * rotation_speed / 60 / 1019.8 / kpd_mechanical

    return power_start


def handle_download_model(request, context):
    d = float(request.POST.get("diam").replace(',', '.'))
    turns = float(request.POST.get("turns").replace(',', '.'))
    rotation_speed = float(request.POST.get("rotation_speed").replace(',', '.'))

    if d <= 0 or turns <= 0:
        raise ValueError("Значения должны быть положительными")
    if d > 500 or turns > 20:
        raise ValueError("Слишком большие значения параметров")

    # Пути к файлам
    files_to_zip = ['screw_lead.step', 'screw_driven.step', 'stator.step', 'pump_assembly.step']

    # Создание моделей
    context['logs'].append("Начинаем создание модели ведущего...")
    create_body_lead(d, turns)
    context['logs'].append("Модель ведущего успешно создана и экспортирована.")

    context['logs'].append("Начинаем создание модели ведомого...")
    create_body_driven(d, turns)
    context['logs'].append("Модель ведомого успешно создана и экспортирована.")

    context['logs'].append("Начинаем создание статора...")
    extrude_stator(d, turns, rotation_speed)
    context['logs'].append("Статор успешно создан и экспортирован.")

    context['logs'].append("Начинаем создание сборки...")
    create_assembly(d)
    context['logs'].append("Сборка успешно создана и экспортирована.")

    # Проверка существования файлов
    if not all(os.path.exists(file) for file in files_to_zip):
        raise FileNotFoundError("Файлы моделей не были созданы")

    # Создание ZIP-архива
    zip_filename = 'screw_models.zip'
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files_to_zip:
            zipf.write(file, arcname=os.path.basename(file))

    # Чтение ZIP-архива и отправка его в ответе
    with open(zip_filename, 'rb') as f:
        response = HttpResponse(f, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response


def print_data(d, pressure, rotation_speed, viscosity, num_turns):
    square_mm = 1.240623 * math.pow(d * 1000, 2)
    step = 10 * d * 1000 / 3
    feed_mm_s = square_mm * step * rotation_speed / 60
    feed_m_h = feed_mm_s * 60 * 60 / 1000000000
    velocity_m_s = feed_mm_s / square_mm / 1000
    feed_loss = 3 * d * velocity_m_s * np.sqrt(pressure) * 0.001 * 60 * 60 / 11
    feed_real = round(feed_m_h - feed_loss, 3)

    kpd_volumetric = round(feed_real / feed_m_h, 3) * 100

    power_t = round((pressure / 10) * (feed_m_h * 1000 / 60 / 60), 3)

    viscosity_sm = viscosity * math.pow(10, -2)
    viscosity_e = (viscosity_sm + math.sqrt(math.pow(viscosity_sm, 2) + 0.03996)) / (2 * 0.074)
    power_viscosity_loss = 0.4 * math.pow(viscosity_e / 6.4, 1 / 1.8)
    moment_lead = 0.727499 * (pressure / 10) * (math.pow(d * 10, 3)) * 1000
    moment_driven = -0.034664 * (pressure / 10) * (math.pow(d * 10, 3)) * 1000
    moment = moment_lead + 2 * moment_driven
    power_moment_loss = moment * rotation_speed / 60 / 1019.8
    force_radial = 1.399945 * (pressure / 10) * math.pow(d * 10, 2) * 100
    power_friction_loss = (np.pi * rotation_speed * force_radial * d / 60) * 0.009807
    power_loss = power_viscosity_loss + power_moment_loss + power_friction_loss
    kpd_mechanical = round(1 - power_loss / power_t, 3) * 100

    kpd_total = round(kpd_volumetric / 100 * kpd_mechanical / 100, 3) * 100

    length = 10 * d * num_turns / 3
    power_length_loss = 100 * pressure * length * math.pow(d, 2)
    power_eff = round(power_t - power_loss - power_length_loss, 3)

    power_start = calculate_start_power(d, pressure, rotation_speed, feed_real, viscosity)

    power_nominal = round((((pressure / 10) * (feed_m_h * 1000 / 60 / 60)) - power_loss - power_length_loss) /
                          ((feed_real / feed_m_h) * (1 - power_loss / power_t)) + power_start, 3)

    return feed_real, kpd_volumetric, kpd_mechanical, kpd_total, power_t, power_eff, power_nominal
