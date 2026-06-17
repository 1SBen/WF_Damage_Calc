# numba_kernels.py
import numba as nb
import numpy as np

@nb.njit
def enervate_cc_nb(c_base: float) -> float:
    """Exact wiki AFCC formula, returns the flat CC added by Enervate (as fraction)."""
    x = c_base * 100.0
    if x < 110.0:
        avg = 102.45 + 0.5 * x
    elif x < 140.0:
        avg = 128.8 - 0.0075 * x + 0.00244 * x * x
    elif x < 150.0:
        avg = 77.5 + 0.70 * x
    elif x < 160.0:
        avg = 70.0 + 0.75 * x
    elif x < 170.0:
        avg = 62.0 + 0.80 * x
    elif x < 180.0:
        avg = 53.5 + 0.85 * x
    elif x < 190.0:
        avg = 44.5 + 0.90 * x
    elif x < 200.0:
        avg = 35.0 + 0.95 * x
    else:
        avg = 25.0 + x
    return (avg - x) / 100.0


@nb.njit
def calc_component_nb(comp, dist, strength_mult, sum_stats, fixed_stats, enervate_active):
    """
    comp  : [total_base, crit_chance, crit_mult, fire_rate, status_chance, multishot, magazine, reload]
    dist  : [imp, pun, sla, heat, cold, elec, toxin, blast, corr, gas, mag, rad, viral]
    sum_stats: length 14 (mod totals)
    fixed_stats: [fx_base, flat_cc, final_dmg, final_cd_add, faction, fire_rate, ext_base, enervate_flag]
    Returns (burst_dps, dot_dps) for this component.
    """
    total_base = comp[0]
    if total_base == 0.0:
        return 0.0, 0.0

    crit_chance = comp[1]
    crit_mult = comp[2]
    fire_rate = comp[3]
    status_chance = comp[4]
    multishot = comp[5]

    # unpack mod sums
    ms_base = sum_stats[0]
    ms_ms = sum_stats[1]
    ms_fr = sum_stats[2]
    ms_ele = sum_stats[3]
    ms_cc = sum_stats[4]
    ms_cd = sum_stats[5]
    ms_imp = sum_stats[6]
    ms_pun = sum_stats[7]
    ms_sla = sum_stats[8]
    ms_heat = sum_stats[9]
    ms_cold = sum_stats[10]
    ms_elec = sum_stats[11]
    ms_tox = sum_stats[12]
    ms_sc = sum_stats[13]

    # unpack fixed stats (arcanes, buffs)
    fx_base = fixed_stats[0]
    fx_flat_cc = fixed_stats[1]
    fx_final_dmg = fixed_stats[2]
    fx_final_cd = fixed_stats[3]
    fx_faction = fixed_stats[4]
    fx_fr = fixed_stats[5]
    fx_ext_base = fixed_stats[6]

    # Damage multipliers
    phys_mult = dist[0] * ms_imp + dist[1] * ms_pun + dist[2] * ms_sla
    # combined element bonuses are not tracked → 0
    damage_mult = 1.0 + ms_ele + phys_mult
    damage_mult *= (1.0 + ms_base + fx_ext_base)
    damage_mult *= strength_mult
    damage_mult *= multishot * (1.0 + ms_ms)

    total_damage = total_base * damage_mult

    # Criticals
    final_cc = crit_chance * (1.0 + ms_cc) + fx_flat_cc
    if enervate_active:
        final_cc += enervate_cc_nb(crit_chance * (1.0 + ms_cc) + fx_flat_cc)
    final_cd = crit_mult * (1.0 + ms_cd) + fx_final_cd
    avg_crit = 1.0 + final_cc * (final_cd - 1.0)

    avg_hit = total_damage * avg_crit

    # Burst
    eff_fr = fire_rate * (1.0 + ms_fr + fx_fr)
    burst = avg_hit * eff_fr * (1.0 + fx_faction) * (1.0 + fx_final_dmg)

    # ----- DoT (only if status chance > 0) -----
    dot_burst = 0.0
    # We'll compute it lazily; if status chance is zero, skip entirely
    if status_chance > 0.0:
        # Use the same base damage without fire rate/multishot (since DoT is per hit)
        modded_damage = total_base * (1.0 + ms_base + fx_ext_base) * strength_mult
        modded_damage *= multishot * (1.0 + ms_ms)
        modded_damage *= (1.0 + fx_faction)

        # tick count (matches original logic: delayed first tick)
        # We'll pass dot_duration from the caller, but since we're inside a component,
        # we need it as a parameter. We'll extend the signature.
        # To keep it simple, I'll move dot_duration to calc_component_nb.
        # Actually, we'll pass dot_duration and include_dot flags.
        # I'll refactor slightly.
        pass

    return burst, dot_burst


# We need dot_duration in the component function, so let's redefine it.
@nb.njit
def calc_component_full_nb(comp, dist, strength_mult, sum_stats, fixed_stats,
                           enervate_active, include_dot, dot_duration):
    total_base = comp[0]
    if total_base == 0.0:
        return 0.0, 0.0

    crit_chance = comp[1]
    crit_mult = comp[2]
    fire_rate = comp[3]
    status_chance = comp[4]
    multishot = comp[5]

    ms_base = sum_stats[0]
    ms_ms = sum_stats[1]
    ms_fr = sum_stats[2]
    ms_ele = sum_stats[3]
    ms_cc = sum_stats[4]
    ms_cd = sum_stats[5]
    ms_imp = sum_stats[6]
    ms_pun = sum_stats[7]
    ms_sla = sum_stats[8]
    ms_heat = sum_stats[9]
    ms_cold = sum_stats[10]
    ms_elec = sum_stats[11]
    ms_tox = sum_stats[12]
    ms_sc = sum_stats[13]

    fx_base = fixed_stats[0]
    fx_flat_cc = fixed_stats[1]
    fx_final_dmg = fixed_stats[2]
    fx_final_cd = fixed_stats[3]
    fx_faction = fixed_stats[4]
    fx_fr = fixed_stats[5]
    fx_ext_base = fixed_stats[6]

    phys_mult = dist[0] * ms_imp + dist[1] * ms_pun + dist[2] * ms_sla
    damage_mult = 1.0 + ms_ele + phys_mult
    damage_mult *= (1.0 + ms_base + fx_ext_base)
    damage_mult *= strength_mult
    damage_mult *= multishot * (1.0 + ms_ms)

    total_damage = total_base * damage_mult

    final_cc = crit_chance * (1.0 + ms_cc) + fx_flat_cc
    if enervate_active:
        final_cc += enervate_cc_nb(crit_chance * (1.0 + ms_cc) + fx_flat_cc)
    final_cd = crit_mult * (1.0 + ms_cd) + fx_final_cd
    avg_crit = 1.0 + final_cc * (final_cd - 1.0)

    avg_hit = total_damage * avg_crit

    eff_fr = fire_rate * (1.0 + ms_fr + fx_fr)
    burst = avg_hit * eff_fr * (1.0 + fx_faction) * (1.0 + fx_final_dmg)

    dot_burst = 0.0
    if include_dot and status_chance > 0.0 and dot_duration > 0:
        # Base damage for DoT (same as modded_damage without faction? original does faction twice)
        modded_damage = total_base * (1.0 + ms_base + fx_ext_base) * strength_mult
        modded_damage *= multishot * (1.0 + ms_ms)
        modded_damage *= (1.0 + fx_faction)  # first faction multiplier

        # Ticks
        if dot_duration < 1.0:
            ticks = 0
        else:
            ticks = int(dot_duration)
            if ticks > 6:
                ticks = 6

        if ticks > 0:
            status_modded = status_chance * (1.0 + ms_sc)
            base_avg_dot = modded_damage * (1.0 + fx_faction) * ticks  # second faction multiplier
            slash_dot = 0.35 * base_avg_dot * dist[2]
            heat_dot = 0.50 * (1.0 + ms_heat) * base_avg_dot * dist[3]
            toxin_dot = 0.50 * (1.0 + ms_tox) * base_avg_dot * dist[6]
            electricity_dot = 0.50 * (1.0 + ms_elec) * base_avg_dot * dist[5]
            gas_dot = 0.50 * base_avg_dot * dist[9]   # no gas bonus tracked
            dot_total = slash_dot + heat_dot + toxin_dot + electricity_dot + gas_dot
            dot_burst = dot_total * status_modded * avg_crit

    return burst, dot_burst


@nb.njit
def calculate_dps_nb(mod_stats, combo_indices, strength_mult, fixed_stats,
                     comp_direct, comp_radial, dist_direct, dist_radial,
                     sustained, include_dot, dot_duration):
    """
    Main entry point for Numba.
    """
    sum_stats = np.zeros(14, dtype=np.float64)

    # Sum the 8 mod stats
    for idx in combo_indices:
        sum_stats[0] += mod_stats[idx, 0]
        sum_stats[1] += mod_stats[idx, 1]
        sum_stats[2] += mod_stats[idx, 2]
        sum_stats[3] += mod_stats[idx, 3]
        sum_stats[4] += mod_stats[idx, 4]
        sum_stats[5] += mod_stats[idx, 5]
        sum_stats[6] += mod_stats[idx, 6]
        sum_stats[7] += mod_stats[idx, 7]
        sum_stats[8] += mod_stats[idx, 8]
        sum_stats[9] += mod_stats[idx, 9]
        sum_stats[10] += mod_stats[idx, 10]
        sum_stats[11] += mod_stats[idx, 11]
        sum_stats[12] += mod_stats[idx, 12]
        sum_stats[13] += mod_stats[idx, 13]

    enervate_active = fixed_stats[7] > 0.5

    total_burst = 0.0
    total_dot = 0.0
    mag = -1.0
    rel = 0.0
    eff_fr = 0.0

    # Direct component
    if comp_direct[0] > 0:
        burst, dot = calc_component_full_nb(
            comp_direct, dist_direct, strength_mult, sum_stats, fixed_stats,
            enervate_active, include_dot, dot_duration
        )
        total_burst += burst
        total_dot += dot
        if comp_direct[6] > 0:
            mag = comp_direct[6]
            rel = comp_direct[7]
            eff_fr = comp_direct[3] * (1.0 + sum_stats[2] + fixed_stats[5])

    # Radial component
    if comp_radial[0] > 0:
        burst, dot = calc_component_full_nb(
            comp_radial, dist_radial, strength_mult, sum_stats, fixed_stats,
            enervate_active, include_dot, dot_duration
        )
        total_burst += burst
        total_dot += dot
        if comp_radial[6] > 0 and mag < 0:
            mag = comp_radial[6]
            rel = comp_radial[7]
            eff_fr = comp_radial[3] * (1.0 + sum_stats[2] + fixed_stats[5])

    total = total_burst + total_dot

    if sustained and mag > 0 and eff_fr > 0:
        shots_per_mag = mag
        sustained_factor = (shots_per_mag / eff_fr) / (rel + shots_per_mag / eff_fr)
        return total * sustained_factor

    return total