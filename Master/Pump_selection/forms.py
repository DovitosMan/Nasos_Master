from django import forms


class CalculationForm(forms.Form):
    flow_rate = forms.FloatField(label='Первое число')
    pressure = forms.FloatField(label='Второе число')
    speed_rotation = forms.FloatField(label='Третье число')
    ns = forms.ChoiceField(choices=[
        ('+', 'Сложение'),
        ('-', 'Вычитание'),
        ('*', 'Умножение'),
        ('/', 'Деление'),
        ('**', 'Возведение в степень'),
        ('sqrt', 'Извлечение квадратного корня'),
        ('sin', 'Синус (в радианах)'),
        ('cos', 'Косинус (в радианах)'),
        ('tan', 'Тангенс (в радианах)'),
        ('log', 'Логарифм ()'),
        ('exp', 'Экспонента'),
    ], label='ns')
