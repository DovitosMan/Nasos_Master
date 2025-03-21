from django.shortcuts import render
from django.http import HttpResponse
import cadquery as cq
from cadquery import exporters, Assembly, Workplane
import logging
import os
import math
import zipfile


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_mid_point(p1, p2, center, radius, is_lower=False):
    """Вычисляет среднюю точку на дуге между двумя точками."""
    mid_x = (p1[0] + p2[0]) / 2
    y_offset = math.sqrt(radius**2 - (mid_x - center[0])**2)
    mid_y = center[1] - y_offset if is_lower else center[1] + y_offset
    return (mid_x, mid_y)


def create_section_lead(d):
    """Создает полное сечение винта с точным построением контура"""
    try:
        # Основные параметры
        R = d * 5 / 6  # Главный радиус
        r = d * 9 / 16  # Боковой радиус
        r_small = d * 19 / 80  # Малый радиус
        r_low = d * 1 / 2  # Нижний радиус

        # Центры дуг
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

        # Точки соединения дуг
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

        # Вычисление средних точек
        mid_points = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            center = centers[i]
            radius = r_low if i in [0, 7, 8, 15] else r_small if i in [1, 6, 9, 14] else r if i in [2, 5, 10, 13] else R
            is_lower = True if i in [1, 6, 8, 10, 11, 12, 13, 15] else False
            mid_points.append(calculate_mid_point(p1, p2, center, radius, is_lower))

        # Построение четверти сечения
        section = cq.Workplane("XY").moveTo(points[0][0], points[0][1])  # Начало в точке a

        # Построение дуг в цикле
        for i in range(len(mid_points)):
            section = section.threePointArc(
                (mid_points[i][0], mid_points[i][1]),  # Средняя точка
                (points[i + 1][0], points[i + 1][1])  # Конечная точка
            )

        # Замыкаем контур
        section = section.close()

        # Экспортируем сечение для отладки
        exporters.export(section, 'debug_section_lead.step')
        logger.info("Сечение успешно создано и экспортировано в debug_section_lead.step")

        return section

    except Exception as e:
        logger.error(f"Ошибка создания сечения: {str(e)}", exc_info=True)
        raise


def create_trapezoid_lead(d, num_turns):
    """Создает прямоугольную трапецию для вырезания вращением."""
    try:
        # Вычисляем длину наклонной стороны

        r_low = d * 1 / 2  # Нижний радиус

        width = d / 4
        height = d / 2
        angle = 30
        slant_height = height / math.tan(math.radians(angle))

        # Создаем трапецию
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
    """Создает спиральное выдавливание с проверкой геометрии"""
    try:
        # Создание сечения
        section = create_section_lead(d)

        screw_body = section.twistExtrude(distance=(10 * d / 3) * num_turns, angleDegrees=360 * num_turns)

        # Создание сечения трапеции для вырезания
        trapezoid = create_trapezoid_lead(d=d, num_turns=num_turns)

        # Создание тела вращения трапеции
        trapezoid_revolved = trapezoid.revolve(axisStart=(0, 0, 0), axisEnd=(1, 0, 0), angleDegrees=360)

        # Вырезание тела трапеции из винта
        result_cut = screw_body.cut(trapezoid_revolved)

        top_face = cq.Workplane('XY').workplane(offset=(10 * d / 3) * num_turns)
        circle = top_face.circle(d / 2 - 1)
        circle_extruded = circle.extrude(math.ceil(d / 3 + 2) * 5)
        result_union = result_cut.union(circle_extruded)

        # Валидация результата
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
        # Основные параметры
        r_5 = d * 1 / 2
        r_6 = d * 19 / 80
        r_7 = d * 3 / 10
        r_8 = d * 1 / 6
        r_9 = d * 31 / 160

        # Центры дуг
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

        # Точки соединения дуг
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

        # Вычисление средних точек
        mid_points = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            center = centers[i]
            radius = r_5 if i in [0, 9, 10, 19] else r_6 if i in [1, 8, 11, 18] \
                else r_7 if i in [2, 7, 12, 17] else r_9 if i in [3, 6, 13, 16] else r_8
            is_lower = True if i in [1, 2, 3, 6, 7, 8, 10, 14, 15, 19] else False
            mid_points.append(calculate_mid_point(p1, p2, center, radius, is_lower))

            # Построение четверти сечения
        section = cq.Workplane("XY").moveTo(points[0][0], points[0][1])  # Начало в точке a

        # Построение дуг в цикле
        for i in range(len(mid_points)):
            section = section.threePointArc(
                (mid_points[i][0], mid_points[i][1]),  # Средняя точка
                (points[i + 1][0], points[i + 1][1])  # Конечная точка
            )

        # Замыкаем контур
        section = section.close()

        # Экспортируем сечение для отладки
        exporters.export(section, 'debug_section_driven.step')
        logger.info("Сечение успешно создано и экспортировано в debug_section_driven.step")

        return section

    except Exception as e:
        logger.error(f"Ошибка создания сечения: {str(e)}", exc_info=True)
        raise


def create_body_driven(d, num_turns):
    """Создает спиральное выдавливание с проверкой геометрии"""
    try:
        # Создание сечения
        section = create_section_driven(d)
        screw_length = (100 * d / 27) * num_turns

        screw_body = section.twistExtrude(screw_length, angleDegrees=-400 * num_turns)

        top_face = cq.Workplane('XY').workplane(offset=screw_length)
        circle = top_face.circle(d / 2)
        circle_extruded = circle.extrude(math.ceil(d / 6) * 5)
        result_union = screw_body.union(circle_extruded)

        filleted_body = result_union

        # Валидация результата
        if filleted_body.val().isValid():
            exporters.export(filleted_body, 'screw_driven.step')
            logger.info("Модель успешно создана и экспортирована в screw_driven.step")
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

        assembly = cq.Assembly()
        assembly.add(lead_screw, name='lead_screw', loc=cq.Location(cq.Vector(0, 0, 0)))
        assembly.add(driven_screw, name='driven_screw_1', loc=cq.Location(cq.Vector(0, d, 0)))
        assembly.add(driven_screw, name='driven_screw_2', loc=cq.Location(cq.Vector(0, -d, 0)))

        exporters.export(assembly.toCompound(), 'pump_assembly.step')
        logger.info('Сборка успешно создана и экспортирована в pump_assembly.step')

        return assembly

    except Exception as e:
        logger.error(f"Ошибка создания сборки: {str(e)}", exc_info=True)
        raise


def calculate_data(feed, pressure, rotation_speed=None):
    kpd_vol_pre = 0.9
    feed_ls = feed * 5 / 18   # 5 / 18 коэф перевода из м3/ч в л/с
    pressure_kg_sm = pressure * 0.1  # перевод из м в кгс/см2

    rotation_speed_max = math.floor(8175 / math.sqrt(feed_ls / kpd_vol_pre))  # об/мин
    len_iterations = math.floor(rotation_speed_max / 50)

    if len_iterations <= 0:
        raise ValueError("Невозможно выполнить расчет: недостаточное количество итераций.")

    n_rec = []
    d_rec = []
    feed_rec = []
    powers = []

    for i in range(len_iterations):
        n_0 = 50
        n_i = n_0 * i + n_0
        d_i_pre = 10 * math.pow(feed_ls / (0.068924 * n_i * kpd_vol_pre * math.pow(10, 6)), 1/3)
        d_i = math.ceil(d_i_pre * 1000) / 1000
        feed_i_pre = 0.068924 * math.pow(d_i, 3) * n_i * kpd_vol_pre
        feed_i_d = feed_i_pre * 60 * 60
        power_i = pressure_kg_sm * feed_i_pre * 1000

        if feed_i_d >= feed:
            n_rec.append(n_i)
            d_rec.append(d_i)
            feed_rec.append(feed_i_d)
            powers.append(power_i)

    combined = list(zip(n_rec, d_rec, feed_rec, powers))
    combined_sorted = sorted(combined, key=lambda x: x[3])
    combined_filtered = combined_sorted[:7]
    n_rec, d_rec, feed_rec, powers = zip(*combined_filtered)

    n_rec = list(n_rec)
    d_rec = list(d_rec)
    feed_rec = list(feed_rec)
    powers = list(powers)

    print(n_rec)
    print(d_rec)
    print(feed_rec)
    print(powers)
    print(rotation_speed_max)

    if rotation_speed is not None:
        d_i_pre = 10 * math.pow(feed_ls / (0.068924 * rotation_speed * kpd_vol_pre * math.pow(10, 6)), 1 / 3)
        d_i = math.ceil(d_i_pre * 1000) / 1000
        feed_i_pre = 0.068924 * math.pow(d_i, 3) * rotation_speed * kpd_vol_pre
        feed_i_d = feed_i_pre * 60 * 60
        power_i = pressure_kg_sm * feed_i_pre * 1000

        n_rec.append(rotation_speed)
        d_rec.append(d_i)
        feed_rec.append(feed_i_d)
        powers.append(power_i)

        return [n_rec[-1], d_rec[-1], feed_rec[-1], powers[-1]]

    n_rec_filtered = [n for n in n_rec if n > 1450]  # Фильтрация значений с частотой > 1450
    if n_rec_filtered:
        # Фильтруем все параметры по частоте > 1450
        filtered_combined = [(n, d, f, p) for n, d, f, p in zip(n_rec, d_rec, feed_rec, powers) if n > 1450]
        if len(filtered_combined) > 2:  # Если больше 2 значений с частотой > 1450
            # Сортируем по мощности и выбираем элемент с наименьшей мощностью
            filtered_combined_sorted_by_power = sorted(filtered_combined, key=lambda x: x[3])
            selected_item = filtered_combined_sorted_by_power[0]
            return [selected_item[0]], [selected_item[1]], [selected_item[2]], [selected_item[3]]
        else:
            # Если 1 или 2 значения, возвращаем первое
            selected_item = filtered_combined[0]
            return [selected_item[0]], [selected_item[1]], [selected_item[2]], [selected_item[3]]
    else:
        # Если нет значений > 1450, рассчитаем параметры для 1450 оборотов
        n_i = 1450  # Устанавливаем частоту 1450 оборотов
        d_i_pre = 10 * math.pow(feed_ls / (0.068924 * n_i * kpd_vol_pre * math.pow(10, 6)), 1 / 3)
        d_i = math.ceil(d_i_pre * 1000) / 1000  # Округляем до 3 знаков после запятой
        feed_i_pre = 0.068924 * math.pow(d_i, 3) * n_i * kpd_vol_pre
        feed_i_d = feed_i_pre * 60 * 60  # Переводим подачу в м3/ч
        power_i = pressure_kg_sm * feed_i_pre * 1000  # Рассчитываем мощность

        return [n_i], [d_i], [feed_i_d], [power_i]


def calculate_turns(pressure):
    """Определяет число витков на основе давления."""
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


def screw(request):
    """Обработчик запроса с улучшенной обработкой ошибок"""
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Диаметр винта, мм', 'name': 'diam'},
            {'type': 'float', 'placeholder': 'Число витков, шт.', 'name': 'turns'},
            {'type': 'float', 'placeholder': 'Подача, м3/ч', 'name': 'feed'},
            {'type': 'float', 'placeholder': 'Напор, м', 'name': 'pressure'},
            {'type': 'float', 'placeholder': 'Частота вращения, об/мин', 'name': 'rotation_speed'},
        ],
        'error': None,
        'logs': [],
    }

    if request.method == "POST":
        try:
            feed = float(request.POST.get("feed").replace(',', '.'))
            pressure = float(request.POST.get("pressure").replace(',', '.'))

            if feed <= 0 or pressure <= 0:
                raise ValueError("Все входные значения должны быть положительными числами.")

            rotation_speed = request.POST.get("rotation_speed")
            if rotation_speed:
                rotation_speed = float(rotation_speed.replace(',', '.'))
            else:
                rotation_speed = None

            n_rec, d_rec, feed_rec, powers = calculate_data(feed, pressure, rotation_speed)

            if d_rec:
                if isinstance(d_rec, list):  # Если d_rec — это список
                    context['calculated_diam'] = d_rec[0] * 1000  # Переводим из метров в миллиметры
                else:  # Если d_rec — это число
                    context['calculated_diam'] = d_rec * 1000

            if n_rec:
                if isinstance(n_rec, list):  # Если n_rec — это список
                    context['calculated_rotation_speed'] = n_rec[0]
                else:  # Если n_rec — это число
                    context['calculated_rotation_speed'] = n_rec

            context['input_feed'] = feed
            context['input_pressure'] = pressure
            context['input_rotation_speed'] = rotation_speed

            turns = calculate_turns(pressure)  # Определяем число витков на основе давления
            context['turns'] = turns  # Добавляем число витков в контекст

            context['logs'].append(f"Рассчитанная подача: {feed_rec}")
            context['logs'].append(f"Рассчитанная мощность: {powers}")
            context['logs'].append(f"Давление: {pressure} м. Определено число витков: {turns}")

            # Если нажата кнопка "Скачать модель", создаем файлы
            if 'download_model' in request.POST:
                d = float(request.POST.get("diam").replace(',', '.'))
                turns = float(request.POST.get("turns").replace(',', '.'))

                if d <= 0 or turns <= 0:
                    raise ValueError("Значения должны быть положительными")

                if d > 500 or turns > 20:
                    raise ValueError("Слишком большие значения параметров")

                # Создание модели ведущего
                context['logs'].append("Начинаем создание модели ведущего...")
                create_body_lead(d, turns)
                context['logs'].append("Модель ведущего успешно создана и экспортирована.")

                # Создание модели ведомого
                context['logs'].append("Начинаем создание модели ведомого...")
                create_body_driven(d, turns)
                context['logs'].append("Модель ведомого успешно создана и экспортирована.")

                # Создание сборки
                context['logs'].append("Начинаем создание сборки...")
                create_assembly(d)
                context['logs'].append("Сборка успешно создана и экспортирована.")

                # Отправка файла
                if not os.path.exists('screw_lead.step') or not os.path.exists('screw_driven.step') \
                        or not os.path.exists('pump_assembly.step'):
                    raise FileNotFoundError("Файлы моделей не были созданы")

                zip_filename = 'screw_models.zip'
                with zipfile.ZipFile(zip_filename, 'w') as zipf:
                    zipf.write('screw_lead.step', arcname='screw_lead.step')
                    zipf.write('screw_driven.step', arcname='screw_driven.step')
                    zipf.write('pump_assembly.step', arcname='pump_assembly.step')

                with open(zip_filename, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/zip')
                    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                    return response

        except ValueError as e:
            context['error'] = f"Ошибка ввода: {str(e)}"
            logger.warning(f"Некорректный ввод: {str(e)}")
            context['logs'].append(f"Ошибка ввода: {str(e)}")
        except Exception as e:
            context['error'] = f"Ошибка генерации: {str(e)}"
            logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
            context['logs'].append(f"Ошибка генерации: {str(e)}")

    return render(request, 'screw.html', context)
