from django.shortcuts import render
# from solid import *
# from solid.utils import *


def screw(request):
    context = {
        'calc': [
            {
                'type': 'number',
                'placeholder': 'test1',
                'name': 'test_name1',
            },
            {
                'type': 'text',
                'placeholder': 'test2',
                'name': 'test_name2',
            },
        ],
        'calculations': {
            'user_test1': None,
            'user_test2': None,
        }
    }



    if request.method == "POST":
        user_test1 = request.POST.get("test_name1")
        user_test2 = request.POST.get("test_name2")

        context['calculations']['user_test1'] = user_test1
        context['calculations']['user_test2'] = user_test2

    return render(request, 'screw.html', context)
