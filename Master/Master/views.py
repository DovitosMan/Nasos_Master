from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    context = {
        'title': 'Расчет рабочего колеса',
        # 'buttons': [
        #     {
        #         'value': 'Главное меню',
        #         'url_name': "{% url 'home' %}",
        #     },
        #     {
        #         'value': 'Расчет колеса',
        #         'url_name': "{% url 'wheel_calc' %}",
        #     },
        #     {
        #         'value': 'Расчет подвода',
        #         'url_name': "{% url 'home' %}",
        #     },
        #     {
        #         'value': 'Расчет отвода',
        #         'url_name': "{% url 'home' %}",
        #     },
        #     {
        #         'value': 'Построение характеристики',
        #         'url_name': "{% url 'characteristics' %}",
        #     },
        #     {
        #         'value': 'Подбор насоса',
        #         'url_name': "{% url 'pump_selection' %}",
        #     },
        #     {
        #         'value': 'Расчет энергозатрат',
        #         'url_name': "{% url 'home' %}",
        #     },
        #     {
        #         'value': 'Расчет трудозатрат',
        #         'url_name': "{% url 'home' %}",
        #     },
        # ],
        'button1': '',
        'button2': 'Расчет колеса',
        'button3': 'Построение характеристики рассчитанного насоса',
        'button4': 'Подбор насоса',
    }
    return render(request, 'home.html', context)


