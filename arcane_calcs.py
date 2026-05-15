# ===========================================================================
# Enervate helper  (exact wiki piecewise formula)
# ===========================================================================
def _afcc(x: float) -> float:
    """
    Exact piecewise AFCC formula from the wiki.
    x       : modded crit chance BEFORE Enervate, as a percentage (e.g. 45.0)
    Returns : average final crit chance, also as a percentage.
    """
    if x < 110:
        return 102.45 + 0.5 * x
    elif x < 140:
        return 128.8 - 0.0075 * x + 0.00244 * x ** 2
    elif x < 150:
        return 77.5  + 0.70 * x
    elif x < 160:
        return 70.0  + 0.75 * x
    elif x < 170:
        return 62.0  + 0.80 * x
    elif x < 180:
        return 53.5  + 0.85 * x
    elif x < 190:
        return 44.5  + 0.90 * x
    elif x < 200:
        return 35.0  + 0.95 * x
    else:
        return 25.0  + x

def compute_enervate_cc(c_base: float) -> float:
    """
    Extra flat CC (as a fraction) contributed by Secondary Enervate.
    c_base : modded CC before Enervate, as a fraction (e.g. 0.45 for 45%)
    """
    x         = c_base * 100   # wiki formula works in percentages
    afcc      = _afcc(x)       # total average final CC  (%)
    extra_pct = afcc - x       # portion added by Enervate (%)
    return extra_pct / 100     # back to fraction
