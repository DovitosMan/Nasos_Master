def menu_items_context(request):
    menu_items = {
        'title': 'Расчет рабочего колеса',
        'menu_buttons': [
            {
                'value': 'Расчет колеса',
                'url_name': "wheel_calc",
            },
            {
                'value': 'Расчет подвода',
                'url_name': "home",
            },
            {
                'value': 'Расчет отвода',
                'url_name': "home",
            },
            {
                'value': 'Построение характеристики',
                'url_name': "characteristics",
            },
            {
                'value': 'Подбор насоса',
                'url_name': "pump_selection",
            },
            {
                'value': 'Расчет энергозатрат',
                'url_name': "home",
            },
            {
                'value': 'Расчет трудозатрат',
                'url_name': "home",
            },
            {
                'value': 'Личный кабинет',
                'url_name': "home",
            },
            {
                'value': 'Трехвинтовой насос',
                'url_name': "screw",
            },
        ],
    }
    return menu_items
