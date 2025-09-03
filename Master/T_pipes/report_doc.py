from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_BREAK
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import RGBColor
import math2docx
from docx.enum.section import WD_SECTION
from copy import deepcopy
import os
from django.conf import settings


def set_heading_style(style, font_name="Times New Roman", size=14, bold=True, align=None,
                      f_l_indent=0.0, space_after=6, space_before=12, color=(0, 0, 0)):
    font = style.font
    font.name = font_name
    font.size = Pt(size)
    font.bold = bold
    font.color.rgb = RGBColor(*color)

    rFonts = OxmlElement('w:rFonts')
    for tag in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
        rFonts.set(qn(f'w:{tag}'), font_name)
    style.element.rPr.append(rFonts)

    fmt = style.paragraph_format
    if align:
        fmt.alignment = align
    fmt.first_line_indent = Cm(f_l_indent)
    fmt.space_after = Pt(space_after)
    fmt.space_before = Pt(space_before)


def add_paragraph_with_indent(doc, text="", left=2.75, first_line=-2.75, tab=2.75,
                              italic=None, sub_text="", subscript=False, value=None, desc=None):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.left_indent = Cm(left)
    fmt.first_line_indent = Cm(first_line)
    fmt.tab_stops.add_tab_stop(Cm(tab))
    if text:
        run = p.add_run(text)
        run.italic = italic
        sub = p.add_run(sub_text)
        sub.font.subscript = subscript
        if value is not None:
            p.add_run(f" = {value}  – ")
        else:
            p.add_run("  – ")
        if desc:
            p.add_run("\t")
            p.add_run(desc)
    return p


def add_equation(doc, latex: str, number=None, f_l_indent=0.0, font_size_pt=14, min_line_pts=30):
    section = doc.sections[0]
    content_width_emu = section.page_width - section.left_margin - section.right_margin
    right_tab_pos_pt = content_width_emu / 12700.0  # EMU -> pt

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt = p.paragraph_format
    fmt.first_line_indent = Cm(f_l_indent)  # без красной строки
    fmt.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
    fmt.line_spacing = Pt(min_line_pts)  # ключ к отсутствию обрезания
    fmt.space_after = fmt.space_before = Pt(2)

    math2docx.add_math(p, latex)

    if number is not None:
        fmt.tab_stops.add_tab_stop(Pt(right_tab_pos_pt), alignment=WD_TAB_ALIGNMENT.RIGHT)
        p.add_run("\t")
        p.add_run(f"({number})").font.size = Pt(font_size_pt)

    return p


def add_equation_calc(doc, formula_latex: str, variables: dict, units: str, number=None, eval_expr=None, roundness=0):
    formula_with_values = formula_latex
    for var, val in variables.items():
        formula_with_values = formula_with_values.replace(var, str(val))

    expr = eval_expr or formula_latex.split("=")[-1]
    for var, val in variables.items():
        expr = expr.replace(var, str(val))

    try:
        result = round(eval(expr), roundness)
        full_formula = f"{formula_with_values} = {result:.{roundness}f} {units}"
    except Exception:
        result = None
        full_formula = formula_with_values

    add_equation(doc, full_formula, number=number)
    return result


def add_frame(main_doc, template_name, section_index=0):
    template_path = os.path.join(settings.BASE_DIR, 'templates', 'frames', template_name)
    template_doc = Document(template_path)
    section = main_doc.sections[section_index]
    section.header.is_linked_to_previous = False

    for p in section.header.paragraphs:
        p.clear()

    template_header = template_doc.sections[0].header
    for element in template_header._element:
        section.header._element.append(deepcopy(element))


def generate_report(result):
    data = dict(result)

    doc = Document()
    section = doc.sections[0]

    section.header_distance = Cm(0)
    section.footer_distance = Cm(0)

    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin, section.right_margin = Cm(3), Cm(1.25)
    section.top_margin, section.bottom_margin = Cm(1.75), Cm(2.5)

    style = doc.styles['Normal']
    font = style.font
    font.name, font.size = 'Times New Roman', Pt(14)
    fmt = style.paragraph_format
    fmt.line_spacing = Pt(21)
    fmt.first_line_indent = Cm(1.25)
    fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt.space_after = fmt.space_before = Pt(0)

    # === Стили заголовков ===
    set_heading_style(doc.styles['Heading 1'], align=WD_ALIGN_PARAGRAPH.CENTER)
    set_heading_style(doc.styles['Heading 2'], align=WD_ALIGN_PARAGRAPH.LEFT, f_l_indent=1.25)

    doc.add_paragraph("РАСЧЕТ ТОЛЩИН СТЕНОК ТРОЙНИКА", style='Heading 1')
    doc.add_section(WD_SECTION.NEW_PAGE)

    doc.add_paragraph("СОДЕРЖАНИЕ", style='Heading 1')
    doc.add_section(WD_SECTION.NEW_PAGE)

    doc.add_paragraph("1. Исходные данные", style='Heading 2')

    p1 = doc.add_paragraph(
        f"Проводится расчёт тройника Ду {int(data['D_N_pipe'])} из стали класса прочности {data['steel_class']}, "
        f"устанавливаемого на трубопровод наружным диаметром {data['D_n']} мм из стали класса прочности "
        f"{data['steel_class']}, ответвление тройника Ду {int(data['D_N_b'])} с внутренним диаметром {data['D_vn']} мм,"
        f" давление среды в трубопроводе {data['pressure']} МПа. Минимальное значение временного сопротивления "
        f"для стали класса прочности {data['steel_class']} – σ")
    p1.add_run("В").font.subscript = True
    p1.add_run(f" = {int(data['sigma_b'])} МПа, а минимальное значение предела текучести σ")
    p1.add_run("Т").font.subscript = True
    p1.add_run(f" = {int(data['sigma_y'])} МПа.")

    doc.add_paragraph("Расчёт проводится согласно методике, приведенной в "
                      "СТО Газпром 2-2.3-116-2016 «Правила производства работ на "
                      "газопроводах врезкой под давлением» [1].")

    doc.add_paragraph("2. Определение толщины стенки трубопровода", style='Heading 2')
    doc.add_paragraph("Толщина стенки трубопровода определяется по СП36.13330.2012 «Магистральные трубопроводы» [2] "
                      "формула (10):")

    delta_formula = r"\delta = \frac{n \cdot p \cdot D_н}{2 \cdot (R_1 + n \cdot p)}"
    add_equation(doc, delta_formula, 1, f_l_indent=7)

    doc.add_paragraph("где: ", style="Normal")
    add_paragraph_with_indent(doc, "n", italic=True, value=data['n'],
                              desc="коэффициент надежности по нагрузке - внутреннему рабочему давлению в "
                                   "трубопроводе ([2] табл. 14);")

    add_paragraph_with_indent(doc, "p", italic=True, value=data['pressure'],
                              desc="рабочее (нормативное) давление в трубопроводе, МПа;")

    add_paragraph_with_indent(doc, "D", italic=True, sub_text="н", subscript=True, value=int(data['D_n']),
                              desc="наружный диаметр трубопровода, мм;")

    add_paragraph_with_indent(doc, "R", italic=True, sub_text="1", subscript=True, tab=0.0,
                              desc="расчетное сопротивление растяжению (сжатию) ([2] формула (2)):")

    R_1_formula = r"R_1 = \frac{R_1^н \cdot m}{k_1 \cdot k_н}"
    add_equation(doc, R_1_formula, 2, f_l_indent=7.25)

    doc.add_paragraph("где:", style="Normal")
    R_1_n = r"R_1^н"
    p2 = add_equation(doc, R_1_n, f_l_indent=1.25, min_line_pts=21)
    fmt2 = p2.paragraph_format
    fmt2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt2.left_indent = Cm(2.75)
    fmt2.first_line_indent = Cm(-2.75)
    fmt2.tab_stops.add_tab_stop(Cm(2.75))
    p2.add_run(f" = {data['sigma_b']} –")
    p2.add_run("\t")
    p2.add_run("нормативное сопротивление растяжению (сжатию) металла"
               "трубопровода, принимается равным минимальному значению временного сопротивления металла, "
               "МПа ([3] табл. 4, СТО Газпром XXX);")

    add_paragraph_with_indent(doc, "m", italic=True, value=data['m'],
                              desc="коэффициент условий работы трубопровода, принимаемый по исходным данным "
                                   "опросного листа Заказчика ([2] табл. 1);")

    add_paragraph_with_indent(doc, "k", italic=True, sub_text="1", subscript=True, value=data['k_1'],
                              desc="коэффициент надежности по материалу ([2] табл. 10);")

    add_paragraph_with_indent(doc, "k", italic=True, sub_text="н", subscript=True, value=data['k_n'],
                              desc="коэффициент надежности по ответственности трубопровода ([2] табл. 12), "
                                   "принимается по условному диаметру и давлению в трубопроводе.")

    doc.add_paragraph()
    doc.add_paragraph("Расчетное сопротивление растяжению (сжатию):")

    variables_R_1 = {"R_1^н": data['sigma_b'], "m": data['m'], "k_1": data['k_1'], "k_н": data['k_n']}
    R_1_py = "(R_1^н * m) / (k_1 * k_н)"
    R_1_units = " МПа"
    R_1_calc = add_equation_calc(doc, R_1_formula, variables_R_1, R_1_units, eval_expr=R_1_py, roundness=1)

    doc.add_paragraph("Расчетная толщина стенки:")

    variables_delta = {"n": data['n'], "p": data['pressure'], "D_н": data['D_n'], "R_1": R_1_calc}
    delta_py = "(n * p * D_н) / (2 * (R_1 + n * p))"
    delta_units = " мм"
    delta_calc = add_equation_calc(doc, delta_formula, variables_delta, delta_units, eval_expr=delta_py, roundness=2)

    doc.add_paragraph("3. Определение толщин стенок тройника", style='Heading 2')

    doc.add_paragraph("Расчетная толщина стенки магистральной части разрезного тройника определяется по формуле [???]:")
    T_h_formula = r"T_h = {\eta \cdot t_h}"
    add_equation(doc, T_h_formula, 3, f_l_indent=7.0)

    doc.add_paragraph("Расчетная толщина стенки ответвления разрезного тройника определяется по формуле [???]:")
    T_b_formula = r"T_b = {\xi \cdot T_h}"
    add_equation(doc, T_b_formula, 4, f_l_indent=7.0)

    doc.add_paragraph("где: ", style="Normal")

    add_paragraph_with_indent(doc, "t", italic=True, sub_text="h", subscript=True, left=1.25, first_line=-1.25,
                              tab=1.25, desc="расчетная толщина стерки условной трубы, имеющей диаметр магистрали и "
                                             "материал разрезного тройника ([2] формула (10)):")

    t_h_formula = r"t_h = \frac{n \cdot p \cdot D_h}{2 \cdot (R_1 + n \cdot p)}"
    add_equation(doc, t_h_formula, f_l_indent=7.0)

    add_paragraph_with_indent(doc, "t", italic=True, sub_text="b", subscript=True, left=1.25, first_line=-1.25,
                              tab=1.25, desc="расчетная толщина стерки условной трубы, имеющей диаметр ответвления и "
                                             "материал разрезного тройника ([2] формула (10)):")

    t_b_formula = r"t_b = \frac{n \cdot p \cdot D_b}{2 \cdot (R_1 + n \cdot p)}"
    add_equation(doc, t_b_formula, f_l_indent=7.0)

    add_paragraph_with_indent(doc, "η", italic=True, left=1.25, first_line=-1.25, tab=1.25,
                              desc="коэффициент несущей способности тройника [???]:")

    eta_formula = r"\eta = \frac{1}{2 \cdot a} \cdot \left(-b + \sqrt{b^2 - 4 \cdot a \cdot c}\right)"
    add_equation(doc, eta_formula, number=5, f_l_indent=5.0)

    add_paragraph_with_indent(doc, "ξ", italic=True, left=1.25, first_line=-1.25, tab=1.25,
                              desc="коэффициент для сварного разрезного тройника [???]:")

    xi_formula = r"\xi = 0.45 + 0.55 \cdot \frac{D_b}{D_h}"
    add_equation(doc, xi_formula, number=6, f_l_indent=6.0)

    p3 = doc.add_paragraph("Предварительно принимается наружный диаметр магистральной "
                           "части тройника и ответвления исходя из расчетной толщины стенки трубопровода ")
    p3.add_run("δ").italic = True
    p3.add_run(" в п.2.")

    if delta_calc <= 6.0:
        delta_calc = 6.0
        doc.add_paragraph("Минимальная толщина стенки из условия прочности тройника в соответствии "
                          "с принципом замещения площадей принимается равной 6 мм ([???]).")
    else:
        delta_calc = delta_calc

    doc.add_paragraph("Наружный диаметр магистральной части тройника:")
    D_h_formula = r"D_h = d_h + 2 \cdot \delta"
    d_h_formula = r"d_h = D_н + 4.0"
    d_h_py = "D_н + 4.0"
    variables_d_h = {"D_н": data['D_n']}
    d_h_units = " мм"
    add_equation(doc, D_h_formula, number=7, f_l_indent=7.0)
    doc.add_paragraph("Внутренний диаметр магистральной части:")
    add_equation(doc, d_h_formula, number=8, f_l_indent=7.0)
    d_h_calc = add_equation_calc(doc, d_h_formula, variables_d_h, d_h_units, eval_expr=d_h_py, roundness=1)

    doc.add_paragraph("Наружный диаметр ответвления тройника:")
    D_b_formula = r"D_b = d_b + 2 \cdot \delta"
    add_equation(doc, D_b_formula, number=9, f_l_indent=7.0)

    variables_D_h = {"d_h": d_h_calc, "delta": delta_calc}
    D_h_py = "d_h + 2 * delta"
    D_h_units = " мм"
    D_h_calc = add_equation_calc(doc, D_h_formula, variables_D_h, D_h_units, eval_expr=D_h_py, roundness=1)

    variables_D_b = {"d_b": data['D_vn'], "delta": delta_calc}
    D_b_py = "d_b + 2 * delta"
    D_b_units = " мм"
    D_b_calc = add_equation_calc(doc, D_b_formula, variables_D_b, D_b_units, eval_expr=D_b_py, roundness=1)

    doc.add_paragraph("Уточняющий расчет толщин стенок тройника (формулы 5, 6):")

    variables_xi = {"D_b": D_b_calc, "D_h": D_h_calc}
    xi_py = "0.45 + 0.55 * D_b / D_h"
    xi_calc = add_equation_calc(doc, xi_formula, variables_xi, units="", eval_expr=xi_py, roundness=3)

    p4 = doc.add_paragraph("Коэффициенты ")
    p4.add_run("a").italic = True
    p4.add_run(", ")
    p4.add_run("b").italic = True
    p4.add_run(", ")
    p4.add_run("c").italic = True
    p4.add_run(" из выражения (5) определяются по формулам ([?] формула 111):")

    eta_equation = r"a \cdot \eta^2 + b \cdot \eta + c = 0"
    a_formula = r"a = (2 + 5 \cdot m_b - 4 \cdot \psi) \cdot \xi \cdot t_h"
    b_formula = r"b = (2 \cdot \psi - 1) \cdot D_b + 4 \cdot \psi \cdot t_h - 5 \cdot m_b \cdot t_b"
    c_formula = r"c = -2 \cdot \psi \cdot D_b"

    add_equation(doc, eta_equation, f_l_indent=4.25)
    add_equation(doc, a_formula, number=10, f_l_indent=4.75)
    add_equation(doc, b_formula, number=11, f_l_indent=3.5)
    add_equation(doc, c_formula, number=12, f_l_indent=6.0)

    doc.add_paragraph("где: ", style="Normal")

    add_paragraph_with_indent(doc, "m", italic=True, sub_text="b", subscript=True, value=data['m_b'],
                              desc=f"коэффициент несущей способности тройника. Принимается равным 1, "
                                   f"если материал магистральной части и ответвления одинаковый – "
                                   f"сталь класса прочности {data['steel_class']}.")

    psi_formula = r"\psi = \frac{L}{d_b}"
    add_equation(doc, psi_formula, f_l_indent=0.0)

    add_paragraph_with_indent(doc, "L", italic=True, desc="полудлина магистрали разрезного тройника")
    variables_psi = {"L": data['L'], "d_b": data['D_vn']}
    psi_py = "L / d_b"
    psi_calc = add_equation_calc(doc, psi_formula, variables_psi, units="", eval_expr=psi_py, roundness=3)

    p4 = doc.add_paragraph("Расчет коэффициентов ")
    p4.add_run("a").italic = True
    p4.add_run(", ")
    p4.add_run("b").italic = True
    p4.add_run(", ")
    p4.add_run("c").italic = True
    p4.add_run(" для определения несущей способности тройника:")

    variables_t_h = {"n": data['n'], "p": data['pressure'], "D_h": D_h_calc, "R_1": R_1_calc}
    t_h_py = "(n * p * D_h) / (2 * (R_1 + n * p))"
    t_h_units = " мм"
    t_h_calc = add_equation_calc(doc, t_h_formula, variables_t_h, t_h_units, eval_expr=t_h_py, roundness=1)

    variables_t_b = {"n": data['n'], "p": data['pressure'], "D_b": D_b_calc, "R_1": R_1_calc}
    t_b_py = "(n * p * D_b) / (2 * (R_1 + n * p))"
    t_b_units = " мм"
    t_b_calc = add_equation_calc(doc, t_b_formula, variables_t_b, t_b_units, eval_expr=t_b_py, roundness=1)

    variables_a = {"m_b": data['m_b'], "psi": psi_calc, "xi": xi_calc, "t_h": t_h_calc}
    a_py = "(2 + 5 * m_b - 4 * psi) * xi * t_h"
    a_calc = add_equation_calc(doc, a_formula, variables_a, units="", eval_expr=a_py, roundness=3)

    variables_b = {"m_b": data['m_b'], "psi": psi_calc, "D_b": D_b_calc, "t_h": t_h_calc, "t_b": t_b_calc}
    b_py = "(2 * psi - 1) * D_b + 4 * psi * t_h - 5 * m_b * t_b"
    b_calc = add_equation_calc(doc, b_formula, variables_b, units="", eval_expr=b_py, roundness=3)

    variables_c = {"psi": psi_calc, "D_b": D_b_calc}
    c_py = "-2 * psi * D_b"
    c_calc = add_equation_calc(doc, c_formula, variables_c, units="", eval_expr=c_py, roundness=3)

    doc.add_paragraph("Решение уравнения для коэффициента несущей способности тройника:")

    eta_calc = round((1 / (2 * a_calc)) * (-b_calc + (b_calc ** 2 - 4 * a_calc * c_calc) ** 0.5), 3)
    eta_formula_with_vals = rf"\eta = 1/(2 \cdot {a_calc}) \cdot (-{b_calc} + \sqrt{{{b_calc}^2 - 4 \cdot {a_calc} \cdot ({c_calc})}}) = {eta_calc}"
    add_equation(doc, eta_formula_with_vals)

    variables_T_h = {"eta": eta_calc, "t_h": t_h_calc}
    T_h_py = "eta * t_h"
    T_h_calc_r = add_equation_calc(doc, T_h_formula, variables_T_h, units=" мм", eval_expr=T_h_py, roundness=1)

    variables_T_b = {"xi": xi_calc, "T_h": T_h_calc_r}
    T_b_py = "xi * T_h"
    T_b_calc_r = add_equation_calc(doc, T_b_formula, variables_T_b, units=" мм", eval_expr=T_b_py, roundness=1)

    if T_h_calc_r <= 6.0 or T_b_calc_r <= 6.0:
        T_h_calc = 6.0
        T_b_calc = xi_calc * T_h_calc
        if T_b_calc <= 6.0:
            T_b_calc = 6.0
            doc.add_paragraph("Минимальная толщина стенки из условия прочности тройника в соответствии "
                              "с принципом замещения площадей принимается равной 6 мм ([???]).")
            add_equation(doc, rf"T_h = {T_h_calc} мм")
            add_equation(doc, rf"T_b = {T_b_calc} мм")

        else:
            T_b_calc = T_b_calc
            add_equation(doc, rf"T_h = {T_h_calc} мм")
            add_equation(doc, rf"T_b = {T_b_calc} мм")
    else:
        T_h_calc = T_h_calc_r
        add_equation(doc, rf"T_h = {T_h_calc} мм")
        add_equation(doc, rf"T_b = {T_b_calc_r} мм")

    doc.add_paragraph("После итерационного расчета принимаем толщины стенок:")
    add_equation(doc, rf"T_h = {data['T_h']} мм")
    add_equation(doc, rf"T_b = {data['T_b']} мм")
    T_h_calc = data['T_h']
    T_b_calc = data['T_b']

    doc.add_paragraph("Уточненный наружный диаметр магистральной части тройника и "
                      "ответвления по принятым толщинам стенок:")

    variables_D_h = {"d_h": d_h_calc, "delta": T_h_calc}
    D_h_py = "d_h + 2 * delta"
    D_h_units = " мм"
    D_h_calc = add_equation_calc(doc, D_h_formula, variables_D_h, D_h_units, eval_expr=D_h_py, roundness=1)

    variables_D_b = {"d_b": data['D_vn'], "delta": T_b_calc}
    D_b_py = "d_b + 2 * delta"
    D_b_units = " мм"
    D_b_calc = add_equation_calc(doc, D_b_formula, variables_D_b, D_b_units, eval_expr=D_b_py, roundness=1)

    doc.add_paragraph("Полудлина тройника L должна удовлетворять неравенству:")

    L_if_1 = r"L >= 0.5 \cdot d_b + 2 \cdot T_h"
    variables_L_if_1 = {"L": data['L'], "d_b": data['D_vn'], "T_h": T_h_calc}
    L_if_1_py = "0.5 * d_b + 2 * T_h"
    add_equation(doc, L_if_1, number=13, f_l_indent=6.0)
    L_if_1 = add_equation_calc(doc, L_if_1, variables_L_if_1, "", eval_expr=L_if_1_py, roundness=1)
    if data['L'] >= L_if_1:
        doc.add_paragraph("Условие полудлины тройника выполняется.")
    else:
        doc.add_paragraph("_____Условие полудлины тройника НЕ выполняется!!!_____")

    doc.add_paragraph("4. Условие прочности тройника в соответствии с принципом замещения "
                      "площадей", style='Heading 2')

    area_condition_formula = r"A_1 + m_b \cdot A_2 >= A"
    add_equation(doc, area_condition_formula, number=14, f_l_indent=6.0)

    doc.add_paragraph("где: ", style="Normal")
    add_equation(doc,
                 rf"A = d_b \cdot t_h = {data['D_vn']} \cdot {t_h_calc} = {round(data['D_vn'] * t_h_calc, 1)} мм^2")

    add_equation(doc, rf"A_1 = (2 \cdot L - d_b) \cdot (T_h - t_h) = "
                      rf"(2 \cdot {data['L']} - {data['D_vn']}) \cdot ({T_h_calc} - {t_h_calc}) = "
                      rf"{round((2 * data['L'] - data['D_vn']) * (T_h_calc - t_h_calc), 1)} мм^2")

    add_equation(doc, rf"H_1 = 2.5 \cdot T_h = 2.5 \cdot {T_h_calc} = {round(2.5 * T_h_calc, 1)} мм")

    add_equation(doc,
                 rf"A_2 = 2 \cdot H_1 \cdot (T_b - t_h) = 2 \cdot {round(2.5 * T_h_calc, 1)} \cdot ({T_b_calc} - {t_h_calc}) = "
                 rf"{round(2 * round(2.5 * T_h_calc, 1) * (T_b_calc - t_h_calc), 1)} мм^2")

    doc.add_paragraph("Подставляем полученные значения в условие прочности:")

    A_1 = round((2 * data['L'] - data['D_vn']) * (T_h_calc - t_h_calc), 1)
    A_2 = round(2 * round(2.5 * T_h_calc, 1) * (T_b_calc - t_h_calc), 1)
    A = round(data['D_vn'] * t_h_calc, 1)

    add_equation(doc, rf"{A_1} + {data['m_b']} \cdot {A_2} = {A_1 + data['m_b'] * A_2} >= {A}")
    if (A_1 + data['m_b'] * A_2) >= A:
        doc.add_paragraph("Условие прочности тройника выполняется.")
    else:
        doc.add_paragraph("_____Условие прочности тройника НЕ выполняется!!!_____")

    doc.add_paragraph("5. Заключение", style='Heading 2')
    doc.add_paragraph("Значение расчетных и принятых толщин стенок тройника:")

    table = doc.add_table(rows=3, cols=5)
    table.style = "Table Grid"

    hdr_cells = table.rows[0].cells
    hdr_cells[1].merge(hdr_cells[2])
    hdr_cells[3].merge(hdr_cells[4])

    hdr_cells[0].text = "Категория трубопровода"
    hdr_cells[1].text = "Th, мм"
    hdr_cells[3].text = "Tb, мм"

    row2 = table.rows[1].cells
    row2[1].text = "Расчетная"
    row2[2].text = "Принятая \n(с учетом технического допуска)"
    row2[3].text = "Расчетная"
    row2[4].text = "Принятая \n(с учетом технического допуска)"

    table.cell(0, 0).merge(table.cell(1, 0))

    row3 = table.rows[2].cells
    row3[0].text = "I"
    row3[1].text = f"{T_h_calc_r}"
    row3[2].text = f"{data['T_h']}"
    row3[3].text = f"{T_b_calc_r}"
    row3[4].text = f"{data['T_b']}"

    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                run = p.runs[0]
                run.font.size = Pt(14)
                run.font.name = "Times New Roman"
                rFonts = run._element.rPr.rFonts
                rFonts.set(qn("w:eastAsia"), "Times New Roman")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.line_spacing = Pt(16)

    p5 = doc.add_paragraph()
    run5 = p5.add_run()
    run5.add_break(WD_BREAK.PAGE)

    doc.add_paragraph("Перечень документов", style='Heading 1')
    doc.add_paragraph("1.	СТО Газпром 2-2.3-116-2016 – Правила производства работ на газопроводах врезкой под "
                      "давлением;")
    doc.add_paragraph("2.	СП36.13330.2012 – Магистральные трубопроводы (актуализированная редакция СНиП 2.05.06-85*);")
    doc.add_paragraph("3.	ГОСТ 31447-2012 – Трубы стальные сварные для магистральных газопроводов, нефтепроводов и "
                      "нефтепродуктопроводов;")


    # Сохраняем файл
    filename = f"Расчет_толщин_стенок_тройника_{int(data['D_N_pipe'])}_{int(data['D_N_b'])}_{int(data['pressure']*10)}"
    doc.save(f'{filename}.docx')

    main_doc = Document(f'{filename}.docx')
    add_frame(main_doc, 'template_1.docx', section_index=0)
    add_frame(main_doc, 'template_2.docx', section_index=1)
    add_frame(main_doc, 'template_3.docx', section_index=2)

    main_doc.save(f'{filename}_w_f.docx')

