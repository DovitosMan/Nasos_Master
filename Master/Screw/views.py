from django.shortcuts import render
from django.http import HttpResponse, FileResponse
import cadquery as cq
from cadquery import exporters
import logging
import os
import math
from django.core.files.storage import default_storage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_mid_point(p1, p2, center, radius, is_lower=False):
    """Вычисляет среднюю точку на дуге между двумя точками."""
    mid_x = (p1[0] + p2[0]) / 2
    y_offset = math.sqrt(radius**2 - (mid_x - center[0])**2)
    mid_y = center[1] - y_offset if is_lower else center[1] + y_offset
    return (mid_x, mid_y)


def create_section(d):
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
        exporters.export(section, 'debug_section.step')
        logger.info("Сечение успешно создано и экспортировано в debug_section.step")

        return section

    except Exception as e:
        logger.error(f"Ошибка создания сечения: {str(e)}", exc_info=True)
        raise


def create_spiral_extrusion(d, num_turns):
    """Создает спиральное выдавливание с проверкой геометрии"""
    try:
        # Создание сечения
        section = create_section(d)

        N = 1000

        # Спиральная траектория
        spiral = cq.Workplane("XY").parametricCurve(
            lambda t: (
                d / 2 * math.cos(2 * math.pi * t),
                d / 2 * math.sin(2 * math.pi * t),
                (10 * d / 3) * t
            ),
            start=0,
            stop=num_turns,
            N=int(N * num_turns)
        )

        # Экспортируем спираль для отладки
        exporters.export(spiral, 'debug_spiral.step')
        logger.info("Спираль успешно создана и экспортирована в debug_spiral.step")

        # Выдавливание
        result = section.sweep(
            spiral,
            makeSolid=True,
            isFrenet=True,
            clean=True
        )

        # Валидация результата
        if result.val().isValid():
            exporters.export(result, 'screw.step')
            logger.info("Модель успешно создана и экспортирована в screw.step")
            return True
        else:
            raise RuntimeError("Некорректная геометрия после выдавливания")

    except Exception as e:
        logger.error(f"Ошибка при выдавливании: {str(e)}", exc_info=True)
        raise


def screw(request):
    """Обработчик запроса с улучшенной обработкой ошибок"""
    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Диаметр винта (мм)', 'name': 'diam'},
            {'type': 'float', 'placeholder': 'Число витков', 'name': 'turns'},
        ],
        'error': None,
        'logs': [],
    }

    if request.method == "POST":
        try:
            # Валидация входных данных
            d = float(request.POST.get("diam").replace(',', '.'))
            turns = float(request.POST.get("turns").replace(',', '.'))

            if d <= 0 or turns <= 0:
                raise ValueError("Значения должны быть положительными")

            if d > 1000 or turns > 3.8:
                raise ValueError("Слишком большие значения параметров")

            # Создание модели
            create_spiral_extrusion(d, turns)
            context['logs'].append("Модель успешно создана.")

            # Отправка файла
            if os.path.exists('screw.step'):
                with open('screw.step', 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/step')
                    response['Content-Disposition'] = 'attachment; filename="screw.step"'
                    return response
            raise FileNotFoundError("Файл модели не был создан")

        except ValueError as e:
            context['error'] = f"Ошибка ввода: {str(e)}"
            logger.warning(f"Некорректный ввод: {str(e)}")
            context['logs'].append(f"Ошибка ввода: {str(e)}")
        except Exception as e:
            context['error'] = f"Ошибка генерации: {str(e)}"
            logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
            context['logs'].append(f"Ошибка генерации: {str(e)}")

    return render(request, 'screw.html', context)
