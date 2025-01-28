import math
import matplotlib.pyplot as plt
import io
import urllib, base64

from django.shortcuts import render
# from Master.calculations import views


def characteristics(request):

    context = {
        'button1': 'Получить характеристику',
        'graph_url': None,
        'inputs': [
            {
                'placeholder': 'Расход, м3/ч',
                'type': 'number',
                'name': 'flow_rate',
                'value': '',
            },
            {
                'placeholder': 'Напор, м',
                'type': 'number',
                'name': 'pressure',
                'value': '',
            },
            {
                'placeholder': 'Частота вр., об/мин',
                'type': 'number',
                'name': 'speed',
                'value': '',
            },
            {
                'placeholder': 'Коэфф. быстр.',
                'type': 'number',
                'name': 'ns',
                'value': '',
            },
            {
                'placeholder': 'Полный ожид. КПД',
                'type': 'number',
                'name': 'kpd',
                'value': '',
            },
        ],
        'calculations': [
            {
                'name': 'w: ',
                'value': None,
                'unit': '',
            },
            {
                'name': 'k1: ',
                'value': None,
                'unit': '',
            },
            {
                'name': 'k_1: ',
                'value': None,
                'unit': '',
            },
            {
                'name': 'k3: ',
                'value': None,
                'unit': '',
            },
            {
                'name': 'k_3: ',
                'value': None,
                'unit': '',
            },
            {
                'name': 'k_2: ',
                'value': None,
                'unit': '',
            },
        ]
    }
    graph_url = ''
    if request.method == "POST":
        flow_rate = float(request.POST.get("flow_rate", 0))
        pressure = float(request.POST.get("pressure", 0))
        speed = float(request.POST.get("speed", 0))
        ns = float(request.POST.get("ns", 0))
        kpd = float(request.POST.get("kpd", 0))

        calculated_values = calculations(flow_rate, pressure, speed, ns, kpd)
        graphs = graph(calculated_values, flow_rate, pressure, graph_url)
        context['graph_url'] = graphs
        update_context(context, calculated_values)

    return render(request, 'characteristics.html', context)


def calculations(flow_rate, pressure, speed, ns, kpd):
    w = round((math.pi * speed / 30), 3)
    if (ns >= 50) and (ns < 80):
        a1 = 0.0015
        a3 = -0.000675
    elif (ns >= 80) and (ns <= 150):
        a1 = 0.0022
        a3 = -0.002
    else:
        a1 = 0
        a3 = 0

    if (ns >= 50) and (ns < 80):
        b1 = 0.686
        b3 = 0.339
    elif (ns >= 80) and (ns <= 150):
        b1 = 0.63
        b3 = 0.125
    else:
        b1 = 0
        b3 = 0

    if (kpd >= 0) and (kpd <= 0.7):
        b_1 = 1.7
        b_3 = 1.3
    elif (kpd > 0.7) and (kpd <= 0.75):
        b_1 = 0
        b_3 = 0
    elif (kpd > 0.75) and (kpd <= 1):
        b_1 = 0.8
        b_3 = 0.3
    else:
        b_1 = 0.000000000001
        b_3 = 0.000000000001

    if (kpd >= 0) and (kpd <= 0.7):
        kpd_1 = 0.7
        kpd_3 = 0.7
    elif (kpd > 0.7) and (kpd <= 0.75):
        kpd_1 = 0
        kpd_3 = 0
    elif (kpd > 0.75) and (kpd <= 1):
        kpd_1 = 0.75
        kpd_3 = 0.75
    else:
        kpd_1 = 0.000000000001
        kpd_3 = 0.000000000001

    k1 = round(a1 * ns + b1 + b_1 * (kpd - kpd_1), 6)
    k_1 = round(pressure * k1 / (kpd * pow(w, 2)), 6)
    k3 = round(a3 * ns + b3 + b_3 * (kpd - kpd_3), 6)
    k_3 = round(pressure * k3 / (kpd * pow((flow_rate / 60), 2)), 6)
    k_2 = round((pressure - k_1 * pow(w, 2) + k_3 * pow((flow_rate / 60), 2)) / (w * (flow_rate / 60)), 6)

    return w, k1, k_1, k3, k_3, k_2


def graph(a, flow_rate, pressure, graph_url):
    plots = list(a)
    plots.append(flow_rate)
    plots.append(pressure)
    x = []
    for i in range(math.ceil((plots[6] / 60) * 1.3)):
        x.append(i)
    print(x)

    y = []
    for i_1 in range(len(x)):
        y.append(float(round(plots[2] * pow(plots[0], 2) + plots[5] * plots[0] * x[i_1] - plots[4] * pow(x[i_1], 2), 1)))
    print(y)

    plt.figure()
    plt.plot(x, y)
    plt.title('Характеристика насоса')
    plt.xlabel('Q, м3/мин')
    plt.ylabel('H, м')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    graph_url = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return graph_url


def update_context(context, values):
    for calculation, value in zip(context['calculations'], values):
        calculation['value'] = value
