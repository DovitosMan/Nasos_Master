def menu_items_context(request):
    menu_items = {
        'title': 'Расчет рабочего колеса',
        'menu_buttons': [
            {
                'value': 'Подбор насоса',
                'url_name': "pump_selection",
                'key': True,
            },
            {
                'value': 'Расчет колеса',
                'url_name': "wheel_calc",
                'key': True,
            },
            {
                'value': 'Расчет подвода',
                'url_name': "home",
                'key': False,
            },
            {
                'value': 'Расчет отвода',
                'url_name': "home",
                'key': False,
            },
            {
                'value': 'Построение характеристики',
                'url_name': "characteristics",
                'key': False,
            },
            {
                'value': 'Расчет энергозатрат',
                'url_name': "home",
                'key': False,
            },
            {
                'value': 'Расчет трудозатрат',
                'url_name': "home",
                'key': False,
            },
            {
                'value': 'Личный кабинет',
                'url_name': "home",
                'key': False,
            },
            {
                'value': 'Трехвинтовой насос',
                'url_name': "screw",
                'key': True,
            },
        ],
    }
    return menu_items
