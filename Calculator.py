"""
Warframe DPS Calculator
=======================
Structure
---------
BuildStats       – flat numeric bonuses aggregated from all sources
OptimizeConfig   – what to search (weapon, pool of mods/arcanes, filters)
DPSResult        – the best build found by the optimizer
DPSCalculator    – pure DPS math (no I/O, no side-effects)
BuildOptimizer   – iterates combinations, delegates to DPSCalculator
ResultPrinter    – all console output lives here
run_calculation  – thin public entry point (glues the above together)
"""

from __future__ import annotations

import itertools
import multiprocessing
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Local imports (keep your existing data files unchanged)
# ---------------------------------------------------------------------------
from pistol_mods import pistol_mods_base, pistol_mods_stacked
from primary_mods import primary_mods
from weapons import weapons
from warframe_mods import warframe_mods
from warframe_arcanes import warframe_arcanes
from weapon_arcanes import weapon_arcanes
from external_buffs import external_buffs as all_external_buffs
from exclusive_mods import EXCLUSIVE_GROUPS
from arcane_calcs import compute_enervate_cc

# ===========================================================================
# Data model
# ===========================================================================

@dataclass
class BuildStats:
    """Flat numeric bonuses aggregated from ALL sources."""
    damage_bonuses: float = 0.0
    external_damage_bonuses: float = 0.0

    impact_bonuses: float = 0.0
    puncture_bonuses: float = 0.0
    slash_bonuses: float = 0.0

    elemental_bonuses: float = 0.0
    heat_bonuses: float = 0.0
    cold_bonuses: float = 0.0
    electricity_bonuses: float = 0.0
    toxin_bonuses: float = 0.0
    gas_bonuses: float = 0.0

    crit_chance_bonuses: float = 0.0
    crit_damage_bonuses: float = 0.0
    flat_crit_chance: float = 0.0
    final_crit_multiplier_add: float = 0.0

    fire_rate_bonuses: float = 0.0
    external_fire_rate_bonuses: float = 0.0
    multishot_bonuses: float = 0.0
    status_chance_bonuses: float = 0.0

    faction_damage_bonuses: float = 0.0
    final_damage_bonuses: float = 0.0
    ability_strength_bonuses: float = 0.0

    enervate_active: bool = False


@dataclass
class OptimizeConfig:
    """Everything that controls what the optimizer searches over."""
    weapon_name:             str
    weapon_type:             str
    damage_mode:             str            = "all"
    faction:                 Optional[str]  = None
    sustained:               bool           = True
    allow_headshot:          bool           = True
    use_arcanes:             bool           = True
    use_weapon_arcanes:      bool           = True
    use_conditional_stacks:  bool           = True
    include_dot:             bool           = True
    dot_duration:            float          = 1.0   # 6 is the full duration
    strength_mods:           list           = field(default_factory=list)
    include_buffs:           list           = field(default_factory=list)
    exclude_mods:            list           = field(default_factory=list)
    exclude_wf_arcanes:      list           = field(default_factory=list)
    exclude_weapon_arcanes:  list           = field(default_factory=list)


@dataclass
class DPSResult:
    dps:            float
    mods:           tuple
    wf_arcanes:     tuple
    weapon_arcane:  dict
    build_stats:    BuildStats   # combined stats that produced this DPS

# ===========================================================================
# Pure DPS math
# ===========================================================================

class DPSCalculator:
    """
    Stateless DPS math.  All inputs arrive via BuildStats so the
    signature never needs to change when new sources are added.
    """

    @staticmethod
    def calculate_damage_bonuses_multiplier(stats: BuildStats) -> float:
        return 1 + stats.damage_bonuses

    @staticmethod
    def calculate_external_damage_bonuses_multiplier(stats: BuildStats) -> float:
        return 1 + stats.external_damage_bonuses

    @staticmethod
    def calculate_faction_damage_bonus_multiplier(stats: BuildStats) -> float:
        return 1 + stats.faction_damage_bonuses

    @staticmethod
    def calculate_modded_crit_chance(base_crit_chance: float, stats: BuildStats) -> float:
        final_cc = base_crit_chance * (1 + stats.crit_chance_bonuses) + stats.flat_crit_chance
        if stats.enervate_active:
            final_cc += compute_enervate_cc(final_cc)
        return final_cc

    @staticmethod
    def calculate_modded_crit_multiplier(base_crit_multiplier: float, stats: BuildStats) -> float:
        return (
            base_crit_multiplier
            * (1 + stats.crit_damage_bonuses)
            + stats.final_crit_multiplier_add
        )

    @staticmethod
    def calculate_average_crit_multiplier(
            base_crit_chance: float, base_crit_multiplier: float, stats: BuildStats
    ) -> float:
        modded_crit_chance = DPSCalculator.calculate_modded_crit_chance(
            base_crit_chance, stats
        )
        modded_crit_multiplier = DPSCalculator.calculate_modded_crit_multiplier(
            base_crit_multiplier, stats
        )
        return 1 + modded_crit_chance * (modded_crit_multiplier - 1)

    @staticmethod
    def calculate_modded_multishot(comp: dict, stats: BuildStats) -> float:
        return comp["multishot"] * (1 + stats.multishot_bonuses)

    @staticmethod
    def calculate_modded_fire_rate(comp: dict, stats: BuildStats) -> float:
        return comp["fire_rate"] * (
            1 + stats.fire_rate_bonuses + stats.external_fire_rate_bonuses
        )

    @staticmethod
    def calculate_effective_fire_rate(comp: dict, stats: BuildStats) -> float:
        modded_fire_rate = DPSCalculator.calculate_modded_fire_rate(comp, stats)
        trigger_type = comp.get("trigger_type", "auto").lower()
        if trigger_type == "charge":
            charge_time = comp.get("charge_time", 0.0)
            if charge_time <= 0:
                return modded_fire_rate
            return 1 / (charge_time + 1 / modded_fire_rate)
        if trigger_type == "burst":
            burst_count = comp.get("burst_count", 1)
            burst_delay = comp.get("burst_delay", 0.0)
            return burst_count / (1 / modded_fire_rate + (burst_count - 1) * burst_delay)
        return modded_fire_rate

    @staticmethod
    def calculate_ability_strength_multiplier(
            strength_mult: float, stats: BuildStats, apply_ability_strength: bool
    ) -> float:
        if not apply_ability_strength:
            return strength_mult
        return strength_mult + stats.ability_strength_bonuses

    @staticmethod
    def calculate_arsenal_total_damage(
            comp: dict, strength_mult: float, stats: BuildStats,
            apply_ability_strength: bool
    ) -> float:
        damage = comp["damage"]
        base_damage = sum(damage.values())
        if base_damage == 0:
            return 0.0

        unmodded_impact_distribution = damage.get("impact", 0) / base_damage
        unmodded_puncture_distribution = damage.get("puncture", 0) / base_damage
        unmodded_slash_distribution = damage.get("slash", 0) / base_damage
        impact_bonus_term = unmodded_impact_distribution * stats.impact_bonuses
        puncture_bonus_term = unmodded_puncture_distribution * stats.puncture_bonuses
        slash_bonus_term = unmodded_slash_distribution * stats.slash_bonuses

        elemental_and_physical_bonuses = (
            1
            + stats.elemental_bonuses
            + impact_bonus_term
            + puncture_bonus_term
            + slash_bonus_term
        )

        return (
            base_damage
            * elemental_and_physical_bonuses
            * DPSCalculator.calculate_damage_bonuses_multiplier(stats)
            * DPSCalculator.calculate_ability_strength_multiplier(
                strength_mult, stats, apply_ability_strength
            )
            * DPSCalculator.calculate_modded_multishot(comp, stats)
        )

    @staticmethod
    def calculate_average_shot(
            comp: dict, strength_mult: float, stats: BuildStats,
            apply_ability_strength: bool
    ) -> float:
        arsenal_total_damage = DPSCalculator.calculate_arsenal_total_damage(
            comp, strength_mult, stats, apply_ability_strength
        )
        average_crit_multiplier = DPSCalculator.calculate_average_crit_multiplier(
            comp["crit_chance"], comp["crit_multiplier"], stats
        )
        return arsenal_total_damage * average_crit_multiplier

    @staticmethod
    def calculate_average_burst_dps(
            average_shot: float, effective_fire_rate: float, stats: BuildStats
    ) -> float:
        return (
            average_shot
            * effective_fire_rate
            * DPSCalculator.calculate_external_damage_bonuses_multiplier(stats)
            * DPSCalculator.calculate_faction_damage_bonus_multiplier(stats)
            * (1 + stats.final_damage_bonuses)
        )

    @staticmethod
    def calculate(weapon: dict, direct_comp: dict, radial_comp: dict | None,
                  strength_mult: float, stats: BuildStats,
                  sustained: bool = True, include_dot: bool = False,
                  dot_duration: float = 6.0) -> float:
        total_burst = 0.0
        total_dot_burst = 0.0
        mag = None
        rel = None
        eff_fr = 0.0
        ammo_cost_per_shot = 1.0

        for comp in (direct_comp, radial_comp):
            if comp is None:
                continue
            average_shot = DPSCalculator.calculate_average_shot(
                comp, strength_mult, stats, weapon.get("exalted", False)
            )
            if average_shot == 0:
                continue
            effective_fire_rate = DPSCalculator.calculate_effective_fire_rate(comp, stats)
            average_burst_dps = DPSCalculator.calculate_average_burst_dps(
                average_shot, effective_fire_rate, stats
            )
            total_burst += average_burst_dps

            if include_dot:
                avg_total_avg_dot = DPSCalculator.calculate_dot(
                    comp, strength_mult, stats, dot_duration,
                    weapon.get("exalted", False)
                )
                total_dot_burst += avg_total_avg_dot * effective_fire_rate

            if mag is None and comp.get("magazine") and comp["magazine"] > 0:
                mag = comp["magazine"]
                rel = comp.get("reload", 0.0)
                eff_fr = effective_fire_rate
                ammo_cost_per_shot = comp.get("ammo_cost_per_shot", 1.0)

        sustained_factor = 1.0
        if sustained and mag and mag > 0 and eff_fr > 0:
            shots_per_mag = mag / ammo_cost_per_shot
            sustained_factor = (shots_per_mag / eff_fr) / (rel + shots_per_mag / eff_fr)

        return (total_burst + total_dot_burst) * sustained_factor

    # ── Stats factories ───────────────────────────────────────────────────

    @staticmethod
    def stats_from_mods(mods: tuple) -> BuildStats:
        elemental_bonuses = 0.0
        heat_bonuses = cold_bonuses = electricity_bonuses = toxin_bonuses = gas_bonuses = 0.0

        for m in mods:
            val = m.get("elemental", 0)
            elemental_bonuses += val
            etype = m.get("elemental_type", "")
            if etype == "heat":
                heat_bonuses += val
            elif etype == "cold":
                cold_bonuses += val
            elif etype == "electricity":
                electricity_bonuses += val
            elif etype == "toxin":
                toxin_bonuses += val
            elif etype == "gas":
                gas_bonuses += val

        return BuildStats(
            damage_bonuses=sum(m.get("base_dmg", 0) for m in mods),
            multishot_bonuses=sum(m.get("multishot", 0) for m in mods),
            fire_rate_bonuses=sum(m.get("fire_rate", 0) for m in mods),
            elemental_bonuses=elemental_bonuses,
            crit_chance_bonuses=sum(m.get("cc", 0) for m in mods),
            crit_damage_bonuses=sum(m.get("cd", 0) for m in mods),
            impact_bonuses=sum(m.get("impact_bonus", 0) for m in mods),
            puncture_bonuses=sum(m.get("puncture_bonus", 0) for m in mods),
            slash_bonuses=sum(m.get("slash_bonus", 0) for m in mods),
            heat_bonuses=heat_bonuses,
            cold_bonuses=cold_bonuses,
            electricity_bonuses=electricity_bonuses,
            toxin_bonuses=toxin_bonuses,
            gas_bonuses=gas_bonuses,
            faction_damage_bonuses=sum(m.get("faction", 0) for m in mods),
            status_chance_bonuses=sum(
                m.get("status_chance", m.get("sc", 0)) for m in mods
            ),
        )

    @staticmethod
    def stats_from_wf_arcane(arc: dict) -> BuildStats:
        return BuildStats(
            damage_bonuses=arc.get("base_dmg", 0),
            flat_crit_chance=arc.get("flat_crit_chance", 0),
            fire_rate_bonuses=arc.get("fire_rate", 0),
            final_damage_bonuses=arc.get("final_dmg_bonus", 0),
            final_crit_multiplier_add=arc.get("final_cd_add", 0),
            ability_strength_bonuses=arc.get("strength", 0),
        )

    @staticmethod
    def stats_from_weapon_arcane(arc: dict) -> BuildStats:
        return BuildStats(
            damage_bonuses=arc.get("base_dmg", 0),
            crit_chance_bonuses=arc.get("cc", 0),
            flat_crit_chance=arc.get("flat_crit_chance", 0),
            fire_rate_bonuses=arc.get("fire_rate", 0),
            final_damage_bonuses=arc.get("final_dmg_bonus", 0),
            final_crit_multiplier_add=arc.get("final_cd_add", 0),
            enervate_active=arc.get("dynamic_flat_cc", False),
        )

    @staticmethod
    def stats_from_buffs(buff_list: list) -> BuildStats:
        return BuildStats(
            faction_damage_bonuses=sum(b.get("faction_mult", 0) for b in buff_list),
            external_fire_rate_bonuses=sum(b.get("fire_rate_mult", 0) for b in buff_list),
            external_damage_bonuses=sum(b.get("base_dmg", 0) for b in buff_list),
        )

    @staticmethod
    def merge_stats(*parts: BuildStats) -> BuildStats:
        merged = BuildStats()
        for p in parts:
            merged.damage_bonuses += p.damage_bonuses
            merged.external_damage_bonuses += p.external_damage_bonuses
            merged.impact_bonuses += p.impact_bonuses
            merged.puncture_bonuses += p.puncture_bonuses
            merged.slash_bonuses += p.slash_bonuses
            merged.elemental_bonuses += p.elemental_bonuses
            merged.heat_bonuses += p.heat_bonuses
            merged.cold_bonuses += p.cold_bonuses
            merged.electricity_bonuses += p.electricity_bonuses
            merged.toxin_bonuses += p.toxin_bonuses
            merged.gas_bonuses += p.gas_bonuses
            merged.crit_chance_bonuses += p.crit_chance_bonuses
            merged.crit_damage_bonuses += p.crit_damage_bonuses
            merged.flat_crit_chance += p.flat_crit_chance
            merged.final_crit_multiplier_add += p.final_crit_multiplier_add
            merged.fire_rate_bonuses += p.fire_rate_bonuses
            merged.external_fire_rate_bonuses += p.external_fire_rate_bonuses
            merged.multishot_bonuses += p.multishot_bonuses
            merged.status_chance_bonuses += p.status_chance_bonuses
            merged.faction_damage_bonuses += p.faction_damage_bonuses
            merged.final_damage_bonuses += p.final_damage_bonuses
            merged.ability_strength_bonuses += p.ability_strength_bonuses
            merged.enervate_active = merged.enervate_active or p.enervate_active
        return merged

    @staticmethod
    def _ticks_for_type(dmg_type: str, dot_duration: float) -> int:
        """Return number of ticks to count for a given DoT type within dot_duration seconds."""
        # Electricity and Gas tick at t=0,1,2,... (instant first tick)
        if dmg_type in ("electricity", "gas"):
            return min(6, 1 + int(dot_duration))
        # Slash, Heat, Toxin first tick at t=1
        if dot_duration < 1.0:
            return 0
        return min(6, int(dot_duration))

    @staticmethod
    def calculate_dot(
            comp: dict, strength_mult: float, stats: BuildStats,
            dot_duration: float = 6.0, apply_ability_strength: bool = False
    ) -> float:
        damage = comp["damage"]
        base_damage = sum(damage.values())
        if base_damage == 0:
            return 0.0

        slash_distribution = damage.get("slash", 0) / base_damage
        heat_distribution = damage.get("heat", 0) / base_damage
        electricity_distribution = damage.get("electricity", 0) / base_damage
        toxin_distribution = damage.get("toxin", 0) / base_damage
        gas_distribution = damage.get("gas", 0) / base_damage

        # Damage over Time applies Faction Damage twice.
        modded_base_damage = (
            base_damage
            * DPSCalculator.calculate_damage_bonuses_multiplier(stats)
            * DPSCalculator.calculate_ability_strength_multiplier(
                strength_mult, stats, apply_ability_strength
            )
        )
        modded_multishot = DPSCalculator.calculate_modded_multishot(comp, stats)
        faction_damage_bonus_multiplier = (
            DPSCalculator.calculate_faction_damage_bonus_multiplier(stats)
        )
        modded_damage = (
            modded_base_damage
            * modded_multishot
            * faction_damage_bonus_multiplier
        )

        # ---- determine tick count based on tick_model ----
        tick_model = comp.get("tick_model", "delayed")  # "instant" for Electricity/Gas
        if tick_model == "instant":
            total_ticks = min(6, 1 + int(dot_duration))   # tick at t=0,1,2,...
        else:
            # delayed: first tick at t=1
            if dot_duration < 1.0:
                total_ticks = 0
            else:
                total_ticks = min(6, int(dot_duration))

        if total_ticks == 0:
            return 0.0

        base_avg_dot = (
            modded_damage
            * faction_damage_bonus_multiplier
            * total_ticks
        )

        avg_slash_dot = 0.35 * base_avg_dot
        avg_electricity_dot = 0.50 * (1 + stats.electricity_bonuses) * base_avg_dot
        avg_heat_dot = 0.50 * (1 + stats.heat_bonuses) * base_avg_dot
        avg_toxin_dot = 0.50 * (1 + stats.toxin_bonuses) * base_avg_dot
        avg_gas_dot = 0.50 * (1 + stats.gas_bonuses) * base_avg_dot

        total_avg_dot = (
            avg_slash_dot * slash_distribution
            + avg_electricity_dot * electricity_distribution
            + avg_heat_dot * heat_distribution
            + avg_toxin_dot * toxin_distribution
            + avg_gas_dot * gas_distribution
        )

        average_crit_multiplier = DPSCalculator.calculate_average_crit_multiplier(
            comp["crit_chance"], comp["crit_multiplier"], stats
        )

        modded_status_chance = comp["status_chance"] * (1 + stats.status_chance_bonuses)
        avg_total_avg_dot = (
            modded_status_chance
            * total_avg_dot
            * average_crit_multiplier
        )
        return avg_total_avg_dot

# ===========================================================================
# Multiprocessing worker  (module-level so it can be pickled)
# ===========================================================================

def _eval_chunk(args):
    chunk, weapon, direct_comp, radial_comp, strength_mult, fixed_stats, sustained, include_dot, dot_duration = args
    best_dps   = -1.0
    best_combo = None
    for mod_combo in chunk:
        mod_stats    = DPSCalculator.stats_from_mods(mod_combo)
        merged_stats = DPSCalculator.merge_stats(mod_stats, fixed_stats)
        dps = DPSCalculator.calculate(
            weapon, direct_comp, radial_comp, strength_mult, merged_stats,
            sustained=sustained, include_dot=include_dot, dot_duration=dot_duration
        )
        if dps > best_dps:
            best_dps   = dps
            best_combo = mod_combo
    return best_dps, best_combo

# ===========================================================================
# Name normalisation  (makes all exclusion flags case/space insensitive)
# ===========================================================================

def _normalize(name: str) -> str:
    return name.lower().strip()


# ===========================================================================
# Build optimizer
# ===========================================================================

class BuildOptimizer:
    """
    Enumerates every valid (mod combo x wf arcane combo x weapon arcane)
    triple and returns the one with the highest DPS.
    """

    def __init__(self, cfg: OptimizeConfig) -> None:
        self.cfg        = cfg
        self.weapon     = weapons[cfg.weapon_name]
        self.direct_comp, self.radial_comp = self._resolve_components()
        def _total(comp):
            return sum(comp["damage"].values()) if comp else 0.0
        self.direct_base = _total(self.direct_comp)
        self.radial_base = _total(self.radial_comp)
        self.strength   = self._resolve_strength()
        self.buff_stats = self._resolve_buff_stats()
        self.mod_combos         = self._build_mod_combos()
        self.wf_arcane_combos   = self._build_wf_arcane_combos()
        self.weapon_arcane_pool = self._build_weapon_arcane_pool()

   

    # ── Setup helpers ─────────────────────────────────────────────────────
    def _resolve_base_damage(self):
        """Return (direct_base, radial_base) as total damage numbers."""
        w = self.weapon

        def total(comp):
            if comp is None:
                return 0.0
            return sum(comp["damage"].values())

        direct = total(w.get("direct"))
        radial = total(w.get("radial"))

        mode = self.cfg.damage_mode
        if mode == "all":
            return direct, radial
        if mode == "direct":
            return direct, 0.0
        if mode == "radial":
            return 0.0, radial
        raise ValueError(f"Unknown damage_mode: {mode!r}")


    def _resolve_components(self):
        """Return (direct_comp, radial_comp)."""
        w = self.weapon
        mode = self.cfg.damage_mode
        direct = w.get("direct")
        radial = w.get("radial")   # None if absent

        if mode == "all":
            return direct, radial
        elif mode == "direct":
            return direct, None
        elif mode == "radial":
            return None, radial
        raise ValueError(...)

    def _resolve_strength(self) -> float:
        if not self.weapon.get("exalted", False):
            return 1.0
        mods  = self.cfg.strength_mods or warframe_mods
        total = sum(m.get("strength", 0) for m in mods)
        return 1 + total

    def _resolve_buff_stats(self) -> BuildStats:
        if not self.cfg.include_buffs:
            return BuildStats()
        active = [b for b in all_external_buffs
                  if b["name"] in self.cfg.include_buffs]
        return DPSCalculator.stats_from_buffs(active)

    def _build_mod_combos(self) -> list:
        cfg = self.cfg

        if cfg.weapon_type == "pistol":
            pool = pistol_mods_stacked if cfg.use_conditional_stacks else pistol_mods_base
        elif cfg.weapon_type == "primary":
            pool = primary_mods
        else:
            raise ValueError(f"Unknown weapon_type: {cfg.weapon_type!r}")

        if cfg.exclude_mods:
            excluded = {_normalize(n) for n in cfg.exclude_mods}
            pool = [m for m in pool if _normalize(m["name"]) not in excluded]

        if cfg.faction:
            pool = [m for m in pool
                    if m.get("faction_type", cfg.faction) == cfg.faction]
        else:
            pool = [m for m in pool if "faction_type" not in m]

        if not cfg.allow_headshot:
            pool = [m for m in pool if not m.get("requires_headshot", False)]

        valid = []
        for combo in itertools.combinations(pool, 8):
            names = {m["name"] for m in combo}
            if not any(len(g & names) > 1 for g in EXCLUSIVE_GROUPS):
                valid.append(combo)
        return valid

    def _build_wf_arcane_combos(self) -> list:
        cfg = self.cfg
        if not cfg.use_arcanes:
            return [()]

        wtype = {"pistol": "secondary", "primary": "primary"}.get(
            cfg.weapon_type, "universal"
        )
        pool = [a for a in warframe_arcanes
                if a.get("weapon_type", "universal") in (wtype, "universal")]

        if not cfg.allow_headshot:
            pool = [a for a in pool if not a.get("requires_headshot", False)]

        excluded = {_normalize(n) for n in cfg.exclude_wf_arcanes}
        pool = [a for a in pool if _normalize(a["name"]) not in excluded]

        if len(pool) < 2:
            return [tuple(pool)]
        return list(itertools.combinations(pool, 2))

    def _build_weapon_arcane_pool(self) -> list:
        cfg = self.cfg
        if not cfg.use_weapon_arcanes or cfg.weapon_type != "pistol":
            return [{}]

        pool = [a for a in weapon_arcanes if a.get("weapon_type") == "secondary"]

        if not cfg.allow_headshot:
            pool = [a for a in pool if not a.get("requires_headshot", False)]

        excluded = {_normalize(n) for n in cfg.exclude_weapon_arcanes}
        pool = [a for a in pool if _normalize(a.get("name", "")) not in excluded]

        return pool if pool else [{}]

    # ── Optimise ──────────────────────────────────────────────────────────

    def optimize(self) -> DPSResult:
        num_workers  = multiprocessing.cpu_count()
        total_outer  = len(self.weapon_arcane_pool) * len(self.wf_arcane_combos)
        total_combos = total_outer * len(self.mod_combos)
        print(f"Total combinations: {total_combos:,}  ({num_workers} workers)")

        best:       Optional[DPSResult] = None
        start       = time.time()
        last_report = start   # always an absolute timestamp
        outer_done  = 0

        for w_arc in self.weapon_arcane_pool:
            w_arc_stats = (DPSCalculator.stats_from_weapon_arcane(w_arc)
                           if w_arc else BuildStats())

            for wf_combo in self.wf_arcane_combos:
                wf_stats = (
                    DPSCalculator.merge_stats(
                        *(DPSCalculator.stats_from_wf_arcane(a) for a in wf_combo)
                    ) if wf_combo else BuildStats()
                )
                fixed_stats = DPSCalculator.merge_stats(
                    wf_stats, w_arc_stats, self.buff_stats
                )

                chunk_size = max(1, len(self.mod_combos) // num_workers)
                chunks     = [self.mod_combos[i:i + chunk_size]
                              for i in range(0, len(self.mod_combos), chunk_size)]
                args = [
                    (c, self.weapon, self.direct_comp, self.radial_comp, self.strength, fixed_stats,
                     self.cfg.sustained, self.cfg.include_dot, self.cfg.dot_duration)
                    for c in chunks
                ]

                with multiprocessing.Pool(processes=num_workers) as pool:
                    results = pool.map(_eval_chunk, args)

                for dps, combo in results:
                    if best is None or dps > best.dps:
                        mod_stats    = DPSCalculator.stats_from_mods(combo)
                        merged_stats = DPSCalculator.merge_stats(mod_stats, fixed_stats)
                        best = DPSResult(
                            dps           = dps,
                            mods          = combo,
                            wf_arcanes    = wf_combo,
                            weapon_arcane = w_arc,
                            build_stats   = merged_stats,
                        )

                # ── Progress report every 10 s ────────────────────────────
                outer_done += 1
                now = time.time()
                if now - last_report >= 10:
                    done_combos = outer_done * len(self.mod_combos)
                    pct         = done_combos / total_combos * 100
                    elapsed     = now - start
                    rate        = done_combos / elapsed if elapsed > 0 else 1
                    remaining   = (total_combos - done_combos) / rate
                    print(
                        f"Progress: {done_combos:,} / {total_combos:,} "
                        f"({pct:.1f}%)  "
                        f"Elapsed: {elapsed:.0f}s  "
                        f"Remaining: ~{remaining:.0f}s"
                    )
                    last_report = now   # reset to now, not to elapsed

        print(f"Done in {time.time() - start:.1f}s")
        return best

    # ── Marginal impact (used by ResultPrinter) ───────────────────────────

    def marginal_dps_without(self, result: DPSResult,
                             exclude_mod=None,
                             exclude_wf_arcane=None,
                             exclude_weapon_arcane: bool = False) -> float:
        """DPS of the best build with exactly one component removed."""
        mods   = (tuple(m for m in result.mods if m != exclude_mod)
                  if exclude_mod else result.mods)
        wf_arc = (tuple(a for a in result.wf_arcanes if a != exclude_wf_arcane)
                  if exclude_wf_arcane else result.wf_arcanes)
        w_arc  = {} if exclude_weapon_arcane else result.weapon_arcane

        mod_stats   = DPSCalculator.stats_from_mods(mods)
        wf_stats    = (DPSCalculator.merge_stats(
            *(DPSCalculator.stats_from_wf_arcane(a) for a in wf_arc)
        ) if wf_arc else BuildStats())
        w_arc_stats = (DPSCalculator.stats_from_weapon_arcane(w_arc)
                       if w_arc else BuildStats())
        merged      = DPSCalculator.merge_stats(
            mod_stats, wf_stats, w_arc_stats, self.buff_stats
        )
        return DPSCalculator.calculate(
            self.weapon, self.direct_comp, self.radial_comp, self.strength, merged,
            sustained=self.cfg.sustained,
            include_dot=self.cfg.include_dot,
            dot_duration=self.cfg.dot_duration
        )


# ===========================================================================
# Printer  (all console output lives here)
# ===========================================================================

class ResultPrinter:
    NAME_W = 30
    PCT_W  = 6

    @classmethod
    def print(cls, cfg: OptimizeConfig, optimizer: BuildOptimizer,
              result: DPSResult) -> None:
        name = cfg.weapon_name.replace("_", " ").title()
        print(f"\n--- {name} ---")
        print(f"Max DPS: {result.dps:,.2f}")

        print("\nBest Mods (8):")
        for mod in result.mods:
            dps_w  = optimizer.marginal_dps_without(result, exclude_mod=mod)
            impact = (result.dps - dps_w) / result.dps * 100
            print(f"  - {mod['name']:<{cls.NAME_W}} ({impact:>{cls.PCT_W}.1f}%)")

        if result.wf_arcanes:
            print("\nBest Warframe Arcanes:")
            for arc in result.wf_arcanes:
                dps_w  = optimizer.marginal_dps_without(result, exclude_wf_arcane=arc)
                impact = (result.dps - dps_w) / result.dps * 100
                print(f"  - {arc['name']:<{cls.NAME_W}} ({impact:>{cls.PCT_W}.1f}%)")

        if result.weapon_arcane:
            print("\nBest Weapon Arcane:")
            dps_w    = optimizer.marginal_dps_without(result, exclude_weapon_arcane=True)
            impact   = (result.dps - dps_w) / result.dps * 100
            arc_name = result.weapon_arcane.get("name", "?")
            print(f"  - {arc_name:<{cls.NAME_W}} ({impact:>{cls.PCT_W}.1f}%)")


# ===========================================================================
# Public entry point
# ===========================================================================

def run_calculation(
        weapon_name:            str,
        weapon_type:            str,
        strength_mods:          list | None = None,
        use_arcanes:            bool = True,
        use_weapon_arcanes:     bool = True,
        damage_mode:            str  = "all",
        sustained:              bool = True,
        include_dot:            bool = True,
        dot_duration:           float = 1.0,
        use_conditional_stacks: bool = True,
        faction:                str | None = None,
        allow_headshot:         bool = True,
        exclude_wf_arcanes:     list | None = None,
        exclude_weapon_arcanes: list | None = None,
        exclude_mods:           list | None = None,
        include_buffs:          list | None = None,
) -> DPSResult:

    cfg = OptimizeConfig(
        weapon_name            = weapon_name,
        weapon_type            = weapon_type,
        damage_mode            = damage_mode,
        faction                = faction,
        sustained              = sustained,
        allow_headshot         = allow_headshot,
        use_arcanes            = use_arcanes,
        use_weapon_arcanes     = use_weapon_arcanes,
        use_conditional_stacks = use_conditional_stacks,
        include_dot            = include_dot,
        dot_duration           = dot_duration,
        strength_mods          = strength_mods          or [],
        include_buffs          = include_buffs          or [],
        exclude_mods           = exclude_mods           or [],
        exclude_wf_arcanes     = exclude_wf_arcanes     or [],
        exclude_weapon_arcanes = exclude_weapon_arcanes or [],
    )

    optimizer = BuildOptimizer(cfg)
    result    = optimizer.optimize()
    ResultPrinter.print(cfg, optimizer, result)
    return result


# ===========================================================================
# Direct invocation
# ===========================================================================

if __name__ == "__main__":
    run_calculation(
        weapon_name = "jades_glory",
        weapon_type = "pistol",
        use_arcanes = True,
    )
