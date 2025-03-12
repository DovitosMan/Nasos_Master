from django.shortcuts import render
from django.http import HttpResponse
from stl import mesh
import numpy as np


def create_cube(size):
    # Определяем вершины куба
    vertices = np.array([[0, 0, 0],
                         [size, 0, 0],
                         [size, size, 0],
                         [0, size, 0],
                         [0, 0, size],
                         [size, 0, size],
                         [size, size, size],
                         [0, size, size]])

    # Определяем грани куба
    faces = np.array([[0, 3, 1],
                      [1, 3, 2],
                      [0, 4, 7],
                      [0, 7, 3],
                      [4, 5, 6],
                      [4, 6, 7],
                      [5, 1, 2],
                      [5, 2, 6],
                      [2, 3, 6],
                      [6, 3, 7],
                      [0, 1, 5],
                      [0, 5, 4]])

    # Создаем объект mesh
    cube = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            cube.vectors[i][j] = vertices[f[j], :]

    return cube


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

        # Генерация куба и сохранение в файл
        if user_size:
            size = float(user_size)
            cube = create_cube(size)
            filename = f'cube_{size}.stl'
            cube.save(filename)

            # Отправка файла пользователю
            with open(filename, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.ms-pkistl')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

    return render(request, 'screw.html', context)
