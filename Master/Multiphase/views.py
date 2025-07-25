from django.shortcuts import render
import math
from scipy.optimize import brentq, minimize_scalar
import cmath
import logging
import numpy as np
import matplotlib.pyplot as plt
import json


logger = logging.getLogger(__name__)


def multiphase(request):
    components = [
        {
            'type': 'float',
            'placeholder': 'Метан (CH₄)',
            'name': 'methane',
            'value': '0',
            'Tc': 190.6,
            'Pc': 45.99,
            'omega': 0.008,
            'M': 16.04,
            'A': 0.01678,
            'B': 99,
            'cp_A': -0.70,
            'cp_B': 108.48,
            'cp_C': -42.52,
            'cp_D': 5.86,
            'cp_E': 0.68,
            'cp_b': None,
            'cp_liquid_25C': 3400,
        },
        {
            'type': 'float',
            'placeholder': 'Этан (C₂H₆)',
            'name': 'ethane',
            'value': '0',
            'Tc': 305.3,
            'Pc': 48.72,
            'omega': 0.099,
            'M': 30.07,
            'A': 0.0713,
            'B': 147.1,
            'cp_A': 5.41,
            'cp_B': 103.22,
            'cp_C': -38.12,
            'cp_D': 4.12,
            'cp_E': 0.56,
            'cp_b': None,
            'cp_liquid_25C': 2400,
        },
        {
            'type': 'float',
            'placeholder': 'Пропан (C₃H₈)',
            'name': 'propane',
            'value': '0',
            'Tc': 369.8,
            'Pc': 42.48,
            'omega': 0.152,
            'M': 44.10,
            'A': 0.1114,
            'B': 177.7,
            'cp_A': 8.39,
            'cp_B': 90.84,
            'cp_C': -26.73,
            'cp_D': 2.52,
            'cp_E': 0.49,
            'cp_b': 2.3,
            'cp_liquid_25C': 2300,
        },
        {
            'type': 'float',
            'placeholder': 'н-Бутан (n-C₄H₁₀)',
            'name': 'n_butane',
            'value': '0',
            'Tc': 425.2,
            'Pc': 37.96,
            'omega': 0.200,
            'M': 58.12,
            'A': 0.1415,
            'B': 203,
            'cp_A': 10.11,
            'cp_B': 84.77,
            'cp_C': -22.45,
            'cp_D': 1.94,
            'cp_E': 0.46,
            'cp_b': 1.9,
            'cp_liquid_25C': 2200,
        },
        {
            'type': 'float',
            'placeholder': 'и-Бутан (i-C₄H₁₀)',
            'name': 'i_butane',
            'value': '0',
            'Tc': 408.1,
            'Pc': 36.48,
            'omega': 0.184,
            'M': 58.12,
            'A': 0.1415,
            'B': 203,
            'cp_A': 10.00,
            'cp_B': 85.30,
            'cp_C': -22.70,
            'cp_D': 2.00,
            'cp_E': 0.46,
            'cp_b': 1.95,
            'cp_liquid_25C': 2100,
        },
        {
            'type': 'float',
            'placeholder': 'н-Пентан (n-C₅H₁₂)',
            'name': 'n_pentane',
            'value': '0',
            'Tc': 469.7,
            'Pc': 33.70,
            'omega': 0.251,
            'M': 72.15,
            'A': 0.1697,
            'B': 222,
            'cp_A': 11.50,
            'cp_B': 76.80,
            'cp_C': -18.45,
            'cp_D': 1.60,
            'cp_E': 0.43,
            'cp_b': 1.8,
            'cp_liquid_25C': 2200,
        },
        {
            'type': 'float',
            'placeholder': 'и-Пентан (i-C₅H₁₂)',
            'name': 'i_pentane',
            'value': '0',
            'Tc': 460.4,
            'Pc': 33.82,
            'omega': 0.227,
            'M': 72.15,
            'A': 0.1697,
            'B': 222,
            'cp_A': 11.30,
            'cp_B': 77.20,
            'cp_C': -18.60,
            'cp_D': 1.58,
            'cp_E': 0.43,
            'cp_b': 1.75,
            'cp_liquid_25C': 2200,
        },
        {
            'type': 'float',
            'placeholder': 'Гексан (C₆H₁₄)',
            'name': 'hexane',
            'value': '0',
            'Tc': 507.4,
            'Pc': 30.25,
            'omega': 0.301,
            'M': 86.18,
            'A': 0.207,
            'B': 244,
            'cp_A': 13.10,
            'cp_B': 68.50,
            'cp_C': -14.00,
            'cp_D': 1.25,
            'cp_E': 0.41,
            'cp_b': 1.6,
            'cp_liquid_25C': 2300,
        },
        {
            'type': 'float',
            'placeholder': 'CO₂ (углекислый газ)',
            'name': 'co2',
            'value': '0',
            'Tc': 304.2,
            'Pc': 73.8,
            'omega': 0.225,
            'M': 44.01,
            'A': 0.028,
            'B': 120,
            'cp_A': 25.00,
            'cp_B': 55.19,
            'cp_C': -33.69,
            'cp_D': 7.95,
            'cp_E': -0.14,
            'cp_b': None,
            'cp_liquid_25C': 2100,
        },
        {
            'type': 'float',
            'placeholder': 'H₂S (сероводород)',
            'name': 'h2s',
            'value': '0',
            'Tc': 373.2,
            'Pc': 89.4,
            'omega': 0.100,
            'M': 34.08,
            'A': 0.05,
            'B': 150,
            'cp_A': 6.43,
            'cp_B': 4.46,
            'cp_C': 0.82,
            'cp_D': -0.81,
            'cp_E': 0.03,
            'cp_b': None,
            'cp_liquid_25C': 1950,
        },
        {
            'type': 'float',
            'placeholder': 'N₂ (азот)',
            'name': 'n2',
            'value': '0',
            'Tc': 126.2,
            'Pc': 33.9,
            'omega': 0.040,
            'M': 28.01,
            'A': 0.015,
            'B': 90,
            'cp_A': 28.90,
            'cp_B': -0.16,
            'cp_C': 0.81,
            'cp_D': -0.20,
            'cp_E': 0.04,
            'cp_b': None,
            'cp_liquid_25C': 2100,
        },
        {
            'type': 'float',
            'placeholder': 'H₂O (вода)',
            'name': 'h2o',
            'value': '0',
            'Tc': 647.1,
            'Pc': 220.6,
            'omega': 0.344,
            'M': 18.02,
            'A': 0.0029,
            'B': 1420,
            'cp_A': -203.60,
            'cp_B': 1523.30,
            'cp_C': -3196.40,
            'cp_D': 2474.50,
            'cp_E': 3.86,
            'cp_b': -0.09,
            'cp_liquid_25C': 4180,
        },
        {
            'type': 'float',
            'placeholder': 'NaCl (раствор)',
            'name': 'nacl',
            'value': '0',
            'Tc': None,
            'Pc': None,
            'omega': None,
            'M': 58.44,
            'A': 0.00035,
            'B': 600,
            'cp_A': None,
            'cp_B': None,
            'cp_C': None,
            'cp_D': None,
            'cp_E': None,
            'cp_b': 0.1,
            'cp_liquid_25C': 3900,
        },
        {
            'type': 'float',
            'placeholder': 'Асфальтены (асф,)',
            'name': 'asphaltenes',
            'value': '0',
            'Tc': 703.8330763,
            'Pc': 10.83585775,
            'omega': 0.9,
            'M': 200.0,
            'A': 0,
            'B': 0,
            'cp_A': None,
            'cp_B': None,
            'cp_C': None,
            'cp_D': None,
            'cp_E': None,
            'cp_b': None,
            'cp_liquid_25C': 2200,
        },
        {
            'type': 'float',
            'placeholder': 'Механические примеси',
            'name': 'solids',
            'value': '0',
            'Tc': None,
            'Pc': None,
            'omega': None,
            'M': None,
            'A': 0,
            'B': 0,
            'cp_A': None,
            'cp_B': None,
            'cp_C': None,
            'cp_D': None,
            'cp_E': None,
            'cp_b': None,
            'cp_liquid_25C': None,
        },
        {
            'type': 'float',
            'placeholder': 'C6+ (тяжёлые фракции)',
            'name': 'c6plus',
            'value': '0',
            'Tc': 562.4225915,
            'Pc': 24.2698538,
            'omega': 0.35,
            'M': 110.0,
            'A': 0.2,
            'B': 600,
            'cp_A': None,
            'cp_B': None,
            'cp_C': None,
            'cp_D': None,
            'cp_E': None,
            'cp_b': None,
            'cp_liquid_25C': 2800,
        },
        {
            'type': 'float',
            'placeholder': 'Псевдокомпонент 1',
            'name': 'pseudo1',
            'value': '0',
            'Tc': None,
            'Pc': None,
            'omega': None,
            'M': None,
            'A': None,
            'B': None,
            'cp_A': None,
            'cp_B': None,
            'cp_C': None,
            'cp_D': None,
            'cp_E': None,
            'cp_b': None,
            'cp_liquid_25C': None,
        },
        {
            'type': 'float',
            'placeholder': 'Псевдокомпонент 2',
            'name': 'pseudo2',
            'value': '0',
            'Tc': None,
            'Pc': None,
            'omega': None,
            'M': None,
            'A': None,
            'B': None,
            'cp_A': None,
            'cp_B': None,
            'cp_C': None,
            'cp_D': None,
            'cp_E': None,
            'cp_b': None,
            'cp_liquid_25C': None,
        }
    ]
    # Пересчёт Tc и Pc для некоторых компонентов
    for comp in components:
        if comp['placeholder'] in ['Асфальтены (асф,)', 'C6+ (тяжёлые фракции)']:
            M = comp.get('M')
            if M and M > 0:
                ln_M = math.log(M)
                comp['Tc'] = round(19.25 * (ln_M ** 2) + 44.06 * ln_M - 70, 1)
                comp['Pc'] = round((7.77 - 9.5e-3 * comp['Tc']) * 10, 2)
                logger.debug(f"Recalculated Tc and Pc for {comp['placeholder']}: Tc={comp['Tc']}, Pc={comp['Pc']}")

    context = {
        'calc': [
            {'type': 'float', 'placeholder': 'Напор, м', 'name': 'pressure', 'value': ''},
            {'type': 'float', 'placeholder': 'Температура, С:', 'name': 'temperature', 'value': ''},
        ],
        'components': components,
        'submitted_data': None,
        'error_message': None,
        'phase_diagram_error': None,  # Добавляем для ошибок фазовой диаграммы
    }

    if request.method == 'POST':
        submitted_data = {}
        logger.info("POST request received, processing input components")
        for comp in components:
            raw_val = request.POST.get(comp['name'], '').replace(',', '.')
            try:
                mol_frac = float(raw_val)
            except ValueError:
                mol_frac = None
                logger.warning(f"Invalid molar fraction for {comp['name']}: '{raw_val}' set as None")
            comp['value'] = raw_val

            submitted_data[comp['name']] = {
                **{k: comp.get(k) for k in
                   ['placeholder', 'Tc', 'Pc', 'omega', 'M', 'A', 'B', 'cp_A', 'cp_B', 'cp_C', 'cp_D', 'cp_E', 'cp_b',
                    'cp_liquid_25C']},
                'name': comp['name'],
                'molar_fraction': mol_frac,
                'label': comp['placeholder'],
            }

        for param in context['calc']:
            val = request.POST.get(param['name'], '').replace(',', '.')
            param['value'] = val
            logger.debug(f"Input parameter '{param['name']}': {val}")

        context['submitted_data'] = submitted_data

        # Отфильтровать компоненты с ненулевой молярной долей
        filtered = {k: [] for k in next(iter(submitted_data.values())).keys()}
        for comp_data in submitted_data.values():
            if comp_data['molar_fraction'] not in (None, 0, 0.0):
                for key, value in comp_data.items():
                    filtered[key].append(value)

        logger.info(f"Filtered components count: {len(filtered['name'])}")

        # Проверка на наличие компонентов
        if not filtered['name']:
            context['error_message'] = "Ошибка: не указаны компоненты с ненулевыми молярными долями."
            logger.error("No components with non-zero molar fractions provided.")
            return render(request, 'multiphase.html', context)

        # Проверка суммы молярных долей
        total_mol_frac = sum([mf for mf in filtered['molar_fraction'] if mf is not None])
        if abs(total_mol_frac - 1.0) > 1e-6:
            context['error_message'] = "Ошибка: сумма молярных долей не равна 1."
            logger.error(f"Sum of molar fractions is {total_mol_frac}, expected 1.0")
            return render(request, 'multiphase.html', context)

        # Преобразуем в кортеж для передачи в calc
        results = zip(
            filtered['name'],
            filtered['molar_fraction'],
            filtered['Tc'],
            filtered['Pc'],
            filtered['omega'],
            filtered['M'],
            filtered['A'],
            filtered['B'],
            filtered['cp_A'],
            filtered['cp_B'],
            filtered['cp_C'],
            filtered['cp_D'],
            filtered['cp_E'],
            filtered['cp_b'],
            filtered['cp_liquid_25C']
        )

        try:
            pressure = float(request.POST.get('pressure', '0').replace(',', '.'))
            temperature = float(request.POST.get('temperature', '0').replace(',', '.'))
            logger.info(f"Pressure input: {pressure}, Temperature input: {temperature}")
        except Exception as e:
            logger.error(f"Error parsing pressure or temperature: {e}")
            context['error_message'] = "Ошибка: некорректные значения давления или температуры."
            return render(request, 'multiphase.html', context)

        try:
            calc_result = calc(pressure, temperature, results)
            logger.info("Calculation successful.")

            calc_result_prepared = []
            names = calc_result.get('name', [])
            density = calc_result.get('density', [])
            viscosity = calc_result.get('viscosity', [])
            heat_capacity = calc_result.get('heat_capasity', [])
            compression = calc_result.get('compression_koef', [])
            P_sat = calc_result.get('P_sat', None)
            mass_fractions = calc_result.get('mass_fraction', [])
            volume_fractions = calc_result.get('volume_fraction', [])

            for i, name in enumerate(names):
                calc_result_prepared.append({
                    'name': name,
                    'density': density[i] if i < len(density) else None,
                    'viscosity': viscosity[i] if i < len(viscosity) else None,
                    'heat_capacity': heat_capacity[i] if i < len(heat_capacity) else None,
                    'mass_fraction': mass_fractions[i] if i < len(mass_fractions) else None,
                    'volume_fraction': volume_fractions[i] if i < len(volume_fractions) else None,
                    'compression_koef': compression[i] if i < len(compression) else None,
                })

            # Расчёт данных для фазовой диаграммы
            phase_data = []
            Tc_values = [c['Tc'] for c in components if c['Tc'] is not None]
            if Tc_values:
                T_min = max(min(Tc_values) - 100, 100)  # Ограничиваем минимальную температуру
                T_max = min(max(Tc_values) + 50, 1000)  # Ограничиваем максимальную температуру
                temp_range = np.linspace(T_min - 273.15, T_max - 273.15, 50)
                valid_points = 0
                for temp in temp_range:
                    try:
                        # Пересоздаём results для каждой температуры
                        results = zip(
                            filtered['name'],
                            filtered['molar_fraction'],
                            filtered['Tc'],
                            filtered['Pc'],
                            filtered['omega'],
                            filtered['M'],
                            filtered['A'],
                            filtered['B'],
                            filtered['cp_A'],
                            filtered['cp_B'],
                            filtered['cp_C'],
                            filtered['cp_D'],
                            filtered['cp_E'],
                            filtered['cp_b'],
                            filtered['cp_liquid_25C']
                        )
                        temp_result = calc(pressure, temp, results)
                        P_sat_value = temp_result.get('P_sat')
                        if P_sat_value is not None and 0 < P_sat_value < 1e6:  # Фильтруем нереалистичные значения
                            phase_data.append({
                                'temperature': temp,
                                'P_sat': P_sat_value
                            })
                            valid_points += 1
                        else:
                            phase_data.append({'temperature': temp, 'P_sat': None})
                            logger.warning(f"Invalid P_sat at T={temp}: {P_sat_value}")
                    except Exception as e:
                        logger.warning(f"Failed to calculate P_sat at T={temp}: {e}")
                        phase_data.append({'temperature': temp, 'P_sat': None})

                if valid_points < 2:
                    logger.error("Not enough valid P_sat points for phase diagram.")
                    context['phase_diagram_error'] = "Недостаточно данных для построения фазовой диаграммы. Проверьте состав смеси."

            context.update({
                'calc_result_prepared': calc_result_prepared,
                'compression_koef_liquid': compression[0] if len(compression) > 0 else None,
                'compression_koef_gas': compression[1] if len(compression) > 1 else None,
                'P_sat': P_sat,
                'phase_data': json.dumps(phase_data),
                'user_point': {'temperature': temperature,
                               'pressure': pressure * 0.098067} if pressure and temperature else None,
                # Добавляем точку пользователя
            })

        except Exception as e:

            logger.error(f"Calculation failed: {e}", exc_info=True)

            context['error_message'] = "Ошибка при выполнении расчётов. Проверьте входные данные."

            return render(request, 'multiphase.html', context)

    return render(request, 'multiphase.html', context)


def calc(pressure, temperature, results):
    def safe_sum_product(a, b):
        return sum(i * j for i, j in zip(a, b))

    def objective(y, molar_fractions, k_values):
        return sum(
            z * (K - 1) / (1 + y * (K - 1))
            for z, K in zip(molar_fractions, k_values)
            if z is not None and K is not None
        )

    def solve_cubic(C0, C1, C2):
        a, b, c, d = 1, C2, C1, C0

        # Приведение к каноническому виду: x^3 + px + q = 0
        p = (3 * a * c - b ** 2) / (3 * a ** 2)
        q = (2 * b ** 3 - 9 * a * b * c + 27 * a ** 2 * d) / (27 * a ** 3)
        shift = -b / (3 * a)
        D = (q / 2) ** 2 + (p / 3) ** 3  # дискриминант

        if D > 0:
            # Один действительный и два комплексных корня
            sqrt_D = math.sqrt(D)
            u_cubed = -q / 2 + sqrt_D
            v_cubed = -q / 2 - sqrt_D

            u = math.copysign(abs(u_cubed) ** (1 / 3), u_cubed)
            v = math.copysign(abs(v_cubed) ** (1 / 3), v_cubed)

            root1 = u + v + shift
            real_part = -0.5 * (u + v) + shift
            imag_part = (math.sqrt(3) / 2) * (u - v)
            roots = [root1, complex(real_part, imag_part), complex(real_part, -imag_part)]

        elif abs(D) < 1e-12:
            # Все корни вещественные, по крайней мере два совпадают
            u = math.copysign(abs(-q / 2) ** (1 / 3), -q / 2)
            root1 = 2 * u + shift
            root2 = -u + shift
            roots = [root1, root2, root2]

        else:
            # Три различных вещественных корня
            r = math.sqrt(-p / 3)
            phi = math.acos(-q / (2 * r ** 3))
            roots = [
                2 * r * math.cos(phi / 3) + shift,
                2 * r * math.cos((phi + 2 * math.pi) / 3) + shift,
                2 * r * math.cos((phi + 4 * math.pi) / 3) + shift
            ]

        return roots

    def equilibrium_function(P_sat, f_Pc_list, f_omega_list, f_Tc_list, f_molar_fractions, temperature_k,
                             vapor_fraction=0):
        try:
            K_list = []
            for Pc, omega, Tc in zip(f_Pc_list, f_omega_list, f_Tc_list):
                if None in (Pc, omega, Tc):
                    continue
                if Pc <= 0 or Tc <= 0 or temperature_k <= 0:
                    logger.warning(f"Invalid parameters: Pc={Pc}, Tc={Tc}, temperature_k={temperature_k}")
                    return float('inf')
                exponent = max(min(5.37 * (1 + omega) * (1 - Tc / temperature_k), 700), -100)
                if exponent > 700:  # Предотвращаем переполнение exp
                    logger.warning(f"Exponent too large: {exponent} at T={temperature_k}")
                    return float('inf')
                K = (Pc / P_sat) * math.exp(exponent)
                if not (0 < K < 1e10):  # Фильтруем нереалистичные K
                    logger.warning(f"Unrealistic K value: {K} at T={temperature_k}")
                    return float('inf')
                K_list.append(K)
            if vapor_fraction == 0:
                target = sum(z * (K - 1) for z, K in zip(f_molar_fractions, K_list) if z is not None and K is not None)
            else:
                target = sum(z * (K - 1) / (1 + vapor_fraction * (K - 1)) for z, K in zip(f_molar_fractions, K_list) if z is not None and K is not None)
            return abs(target)
        except Exception as e:
            logger.warning(f"Error in equilibrium_function: {e}")
            return float('inf')

    (
        f_comp_names, f_molar_fractions, f_Tc_list, f_Pc_list, f_omega_list,
        f_M_list, f_A_list, f_B_list,
        f_cp_A_list, f_cp_B_list, f_cp_C_list, f_cp_D_list, f_cp_E_list,
        f_cp_b_list, f_cp_liquid_25C_list
    ) = zip(*results)

    pressure_bar = round(pressure * 0.098067, 2)
    pressure_mpa = pressure_bar / 10
    temperature_k = round(temperature + 273.15, 2)

    total_mol_frac = sum(f_molar_fractions)
    if abs(total_mol_frac - 1.0) > 1e-6:
        raise ValueError("Ошибка, молярная доля не равна 1")

    # Расчёт коэффициентов равновесия K_i
    k_i = [
        (Pc / pressure_bar) * math.exp(5.37 * (1 + omega) * (1 - Tc / temperature_k))
        for Tc, Pc, omega in zip(f_Tc_list, f_Pc_list, f_omega_list)
    ]
    is_stable = True if sum([i * (math.log(j) - j + 1) for i, j in zip(f_molar_fractions, k_i)]) > 0.0 else False

    try:
        mol_gas = brentq(objective, 1e-6, 1 - 1e-6, args=(f_molar_fractions, k_i))
    except ValueError:
        result = minimize_scalar(lambda y: abs(objective(y, f_molar_fractions, k_i)), bounds=(1e-6, 1 - 1e-6),
                                 method='bounded')
        mol_gas = result.x
    mol_liquid = 1 - float(mol_gas)

    mol_liquid_i = [z / (1 + mol_gas * (K - 1)) for z, K in zip(f_molar_fractions, k_i)]
    mol_gas_i = [K * x for K, x in zip(k_i, mol_liquid_i)]

    #  Расчет коэффициента сжимаемости
    a_i = [0.45725 * 8.314 ** 2 * i ** 2 / (j * 100000) for i, j in zip(f_Tc_list, f_Pc_list)]
    b_i = [0.0778 * 8.314 * i / (j * 100000) for i, j in zip(f_Tc_list, f_Pc_list)]
    m_i = [0.37464 + 1.54226 * i - 0.26992 * i ** 2 for i in f_omega_list]
    alpha_i = [(1 + i * (1 - math.sqrt(temperature_k / j))) ** 2 for i, j in zip(m_i, f_Tc_list)]
    a_alpha_i = [i * j for i, j in zip(a_i, alpha_i)]

    def a_mix(x_i):
        return sum(x_i[i] * x_i[j] * math.sqrt(a_alpha_i[i] * a_alpha_i[j])
                   for i in range(len(x_i)) for j in range(len(x_i)))

    a_mix_liquid = a_mix(mol_liquid_i)
    a_mix_gas = a_mix(mol_gas_i)
    b_mix_liquid = safe_sum_product(mol_liquid_i, b_i)
    b_mix_gas = safe_sum_product(mol_gas_i, b_i)

    R = 8.314
    A_liquid = a_mix_liquid * pressure_mpa * 1e6 / (R * temperature_k) ** 2
    A_gas = a_mix_gas * pressure_mpa * 1e6 / (R * temperature_k) ** 2
    B_liquid = b_mix_liquid * pressure_mpa * 1e6 / (R * temperature_k)
    B_gas = b_mix_gas * pressure_mpa * 1e6 / (R * temperature_k)

    def cubic_coeffs(A, B):
        return [-(A * B - B**2 - B**3), A - 3 * B**2 - 2 * B, -(1 - B)]

    C0_l, C1_l, C2_l = cubic_coeffs(A_liquid, B_liquid)
    C0_g, C1_g, C2_g = cubic_coeffs(A_gas, B_gas)

    Z_l_roots = [z.real for z in solve_cubic(C0_l, C1_l, C2_l) if z.imag == 0 and z.real > 0]
    Z_g_roots = [z.real for z in solve_cubic(C0_g, C1_g, C2_g) if z.imag == 0 and z.real > 0]

    if not Z_l_roots or not Z_g_roots:
        raise ValueError("Нет допустимых положительных вещественных корней.")

    Z_liquid = min(Z_l_roots)
    Z_gas = max(Z_g_roots)

    mol_mass_liquid = safe_sum_product(f_M_list, mol_liquid_i)
    mol_mass_gas = safe_sum_product(f_M_list, mol_gas_i)

    mol_vol_liquid = Z_liquid * R * temperature_k / pressure_mpa / 1e6
    mol_vol_gas = Z_gas * R * temperature_k / pressure_mpa / 1e6

    vol_gas_i = [g * mol_vol_gas / (g * mol_vol_gas + l * mol_vol_liquid) for g, l in zip(mol_gas_i, mol_liquid_i)]
    vol_liquid_i = [1 - v for v in vol_gas_i]

    vol_gas = mol_gas * mol_vol_gas / (mol_gas * mol_vol_gas + mol_liquid * mol_vol_liquid)
    vol_liquid = 1 - vol_gas

    density_liquid = pressure_mpa * 1e6 * mol_mass_liquid / (Z_liquid * R * temperature_k) / 1000
    density_gas = pressure_mpa * 1e6 * mol_mass_gas / (Z_gas * R * temperature_k) / 1000
    density_mix = vol_liquid * density_liquid + vol_gas * density_gas

    #  Расчет вязкости
    T_red_i = [temperature_k / Tc for Tc in f_Tc_list]
    omega_i = [1.16145 * Tr ** (-0.14874) + 0.52487 * math.exp(-0.7732 * Tr) + 2.16178 * math.exp(-2.43787 * Tr) for Tr
               in T_red_i]
    vol_cr_i = [R * Tc / (Pc * 1e5) for Tc, Pc in zip(f_Tc_list, f_Pc_list)]

    viscosity_gas_i = [40.785 / 100000 * math.sqrt(M * temperature_k) / (Vc ** (2 / 3)) * om for M, Vc, om in
                       zip(f_M_list, vol_cr_i, omega_i)]
    viscosity_liquid_i = [A * math.exp(B / temperature_k) / 0.001 for A, B in zip(f_A_list, f_B_list)]

    viscosity_liquid = safe_sum_product(vol_liquid_i, [v * 0.001 for v in viscosity_liquid_i])
    viscosity_gas = math.exp(safe_sum_product(mol_gas_i, [math.log(v) for v in viscosity_gas_i])) * 0.001

    viscosity_mix = (vol_gas * viscosity_gas + vol_liquid * viscosity_liquid)
    if viscosity_liquid / viscosity_gas > 5:
        viscosity_mix = math.exp(vol_gas * math.log(viscosity_gas) + vol_liquid * math.log(viscosity_liquid))

    t = temperature_k / 1000
    heat_capacity_liquid_i = [(c if c else 0) + (b if b else 0) * temperature for c, b in
                              zip(f_cp_liquid_25C_list, f_cp_b_list)]
    heat_capacity_gas_i = [
        1000 * ((a or 0) + (b or 0) * t + (c or 0) * t ** 2 + (d or 0) * t ** 3 + (e or 0) / t ** 2) / M
        for a, b, c, d, e, M in zip(f_cp_A_list, f_cp_B_list, f_cp_C_list, f_cp_D_list, f_cp_E_list, f_M_list)
    ]

    denom_gas = safe_sum_product(f_M_list, mol_gas_i)
    mass_gas_i = [M * x / denom_gas for M, x in zip(f_M_list, mol_gas_i)]
    denom_liquid = safe_sum_product(f_M_list, mol_liquid_i)
    mass_liquid_i = [M * x / denom_liquid for M, x in zip(f_M_list, mol_liquid_i)]

    heat_capacity_liquid = safe_sum_product(mass_liquid_i, heat_capacity_liquid_i)
    heat_capacity_gas = safe_sum_product(mass_gas_i, heat_capacity_gas_i)

    mass_gas = vol_gas * density_gas / (vol_gas * density_gas + vol_liquid * density_liquid)
    mass_liquid = 1 - mass_gas
    heat_capacity_mix = mass_liquid * heat_capacity_liquid + mass_gas * heat_capacity_gas

    solution = minimize_scalar(
        equilibrium_function,
        bounds=(0.1, 5000),
        method='bounded',
        args=(f_Pc_list, f_omega_list, f_Tc_list, f_molar_fractions, temperature_k, 0)
    )

    P_sat = solution.x  # в бар
    if not (0.1 < P_sat < 5000):
        logger.warning(f"Unrealistic P_sat value: {P_sat}")
        P_sat = None

    result_data = {
        'name': ['Жидкость', 'Газ', 'Смесь'],
        'density': [density_liquid, density_gas, density_mix],
        'viscosity': [viscosity_liquid, viscosity_gas, viscosity_mix],
        'heat_capasity': [heat_capacity_liquid, heat_capacity_gas, heat_capacity_mix],
        'compression_koef': [Z_liquid, Z_gas],
        'P_sat': float(P_sat),
        'mass_fraction': [mass_liquid*100, mass_gas*100, 100],
        'volume_fraction': [vol_liquid*100, vol_gas*100, 100],
    }

    return result_data


