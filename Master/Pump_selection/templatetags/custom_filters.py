from django import template

register = template.Library()


@register.filter
def div(value, arg):
    """Делит value на arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def mul(value, arg):
    """Умножает value на arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0