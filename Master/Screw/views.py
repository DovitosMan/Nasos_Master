from django.shortcuts import render
from django.http import HttpResponse
from stl import mesh
import numpy as np
import os


def create_arc(center, radius, start_angle, end_angle, num_points=10):
    angles = np.linspace(start_angle, end_angle, num_points)
    x = center[0] + radius * np.cos(angles)
    y = center[1] + radius * np.sin(angles)
    return np.array(list(zip(np.round(x, decimals=3), np.round(y, decimals=3))))


def reflect_arcs(all_arcs):
    reflected_arcs = []
    for arc_i in all_arcs:
        # Добавляем оригинальные точки
        reflected_arcs.append(arc_i)
        # Отражение относительно оси Y
        reflected_arcs.append(np.array([[-x, y] for x, y in arc_i]))
        # Отражение относительно оси X
        reflected_arcs.append(np.array([[x, -y] for x, y in arc_i]))
        # Отражение относительно обеих осей
        reflected_arcs.append(np.array([[-x, -y] for x, y in arc_i]))
    return reflected_arcs


def create_stl_from_arcs(curves, filename='model.stl'):
    # Создаем пустой список для треугольников
    vertices = []
    faces = []

    # Для каждой арки создаем треугольники
    for curve in curves:
        # Преобразуем арку в 3D точки (добавляем высоту z)
        for some in range(len(curve) - 1):
            # Добавляем точки на основе арки
            p1 = np.array([curve[some][0], curve[some][1], 0])
            p2 = np.array([curve[some + 1][0], curve[some + 1][1], 0])
            p3 = np.array([curve[some][0], curve[some][1], 1])  # Высота 100 для создания объема
            p4 = np.array([curve[some + 1][0], curve[some + 1][1], 1])  # Высота 100 для создания объема

            # Добавляем вершины
            vertices.extend([p1, p2, p3, p4])

            # Создаем два треугольника для каждого сегмента
            idx = len(vertices) // 3 - 1
            faces.append([idx - 2, idx - 1, idx])
            faces.append([idx - 1, idx + 1, idx])

    # Преобразуем списки в массивы numpy
    vertices = np.array(vertices)
    faces = np.array(faces)

    # Создаем mesh объект
    model = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))

    for i, f in enumerate(faces):
        for j in range(3):
            model.vectors[i][j] = vertices[f[j], :]

    # Сохраняем модель в файл
    model.save(filename)


def screw(request):
    context = {
        'calc': [
            {
                'type': 'number',
                'placeholder': 'Введите размер куба',
                'name': 'size',
            },

        ],
        'calculations': {
            'user_size': None,
        }
    }

    if request.method == "POST":
        user_size = request.POST.get("size")
        context['calculations']['user_size'] = user_size

        d = int(user_size)
        a = 32.4
        arc_centers = [
            (0 * d, 0 * d),
            (-0.179327952 * d, 0.417086714 * d),
            (0.139495548 * d, 0.480146881 * d),
            (0 * d, 0 * d),
        ]
        arc_radii = [d * 5 / 6,
                     d * 9 / 16,
                     d * 19 / 80,
                     d * 1 / 2,
                     ]
        arc_start_angles = [np.pi / 2,
                            np.arctan(0.930399373),
                            np.arctan(0.197789094),
                            np.arctan(1.047242567),
                            ]
        arc_end_angles = [np.pi / 2 - a * np.pi / 360,
                          np.arctan(0.197789094),
                          np.arctan(-0.575932791),
                          0,
                          ]

        arcs = []
        for i in range(len(arc_radii)):
            arc = create_arc(arc_centers[i], arc_radii[i], arc_start_angles[i], arc_end_angles[i])
            arcs.append(arc)

        full_arcs = reflect_arcs(arcs)
        sort_order = [0, 4, 8, 12, 14, 10, 6, 2, 3, 7, 11, 15, 13, 9, 5, 1]
        sorted_full_arcs = [full_arcs[num] for num in sort_order]
        # sorted_full_arcs[4][1] = [sorted_full_arcs[4][1][1], sorted_full_arcs[4][1][0]] #меняет y и x местами

        index_to_process = [4, 5, 6, 7, 12, 13, 14, 15]
        for index in index_to_process:
            sorted_full_arcs[index] = [
                [float(sorted_full_arcs[index][1][0]), float(sorted_full_arcs[index][1][1])],
                [float(sorted_full_arcs[index][0][0]), float(sorted_full_arcs[index][0][1])]
            ]

        for array in sorted_full_arcs:
            print(array)
            print()

        # Используем функцию для создания STL файла
        filename = 'model.stl'
        create_stl_from_arcs(sorted_full_arcs, filename=filename)

        # Отправляем файл пользователю
        with open(filename, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(filename)}"'
            return response

    return render(request, 'screw.html', context)
