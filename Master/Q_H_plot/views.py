from django.shortcuts import render


def q_h_plot(request):
    return render(request, 'characteristics.html')
