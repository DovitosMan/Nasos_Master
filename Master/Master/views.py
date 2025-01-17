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
        'button0': 'Pump Master',
        'button1': 'Главное меню',
        'button2': 'Расчет колеса',
        'button3': 'Расчет подвода',
        'button4': 'Расчет отвода',
        'button5': 'Построение характеристики',
        'button6': 'Подбор насоса',
        'button7': 'Расчет энергозатрат',
        'button8': 'Расчет трудозатрат',
        'button9': 'Личный кабинет',
    }
    return render(request, 'home.html', context)


