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
    """
    Flat numeric bonuses aggregated from ALL sources
    (mods + warframe arcanes + weapon arcane + external buffs).
    Passed into DPSCalculator as a single object instead of 10+ loose args.
    """
    base_dmg:        float = 0.0   # additive multiplier on base damage
    multishot:       float = 0.0
    fire_rate:       float = 0.0
    elemental:       float = 0.0
    cc_mod:          float = 0.0   # % CC (multiplied by weapon base CC)
    cd_mod:          float = 0.0   # % CD (multiplied by weapon base CD)
    flat_cc:         float = 0.0   # flat CC added after the % scaling
    final_dmg:       float = 0.0   # multiplies total damage at the end
    final_cd_add:    float = 0.0   # flat addition to the CD multiplier
    ext_faction:     float = 0.0   # faction damage bonus
    ext_fire_rate:   float = 0.0   # external fire-rate buff
    ext_base_dmg:    float = 0.0   # external base-damage buff
    enervate_active: bool  = False


@dataclass
class OptimizeConfig:
    """Everything that controls what the optimizer searches over."""
    weapon_name:             str
    weapon_type:             str
    damage_mode:             str            = "all"
    faction:                 Optional[str]  = None
    allow_headshot:          bool           = True
    use_arcanes:             bool           = True
    use_weapon_arcanes:      bool           = True
    use_conditional_stacks:  bool           = True
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
    def calculate(weapon: dict, base_damage: float,
                  strength_mult: float, stats: BuildStats) -> float:

        # ── Enervate (dynamic flat CC) ────────────────────────────────────
        if stats.enervate_active:
            cc_before_enervate = (weapon["crit_chance"] * (1 + stats.cc_mod)
                                  + stats.flat_cc)
            enervate_extra = compute_enervate_cc(cc_before_enervate)
        else:
            enervate_extra = 0.0

        final_cc = (weapon["crit_chance"] * (1 + stats.cc_mod)
                    + stats.flat_cc + enervate_extra)

        final_cd  = weapon["crit_multiplier"] * (1 + stats.cd_mod) + stats.final_cd_add
        avg_crit  = 1 + final_cc * (final_cd - 1)

        modified_base = (base_damage
                         * (1 + stats.base_dmg + stats.ext_base_dmg)
                         * strength_mult)

        fire_rate = (weapon["fire_rate"]
                     * (1 + stats.fire_rate + stats.ext_fire_rate))

        dps = (modified_base
               * (1 + stats.elemental)
               * avg_crit
               * (1 + stats.multishot)
               * fire_rate
               * (1 + stats.ext_faction)
               * (1 + stats.final_dmg))

        return dps

    # ── Stats factories ───────────────────────────────────────────────────

    @staticmethod
    def stats_from_mods(mods: tuple) -> BuildStats:
        return BuildStats(
            base_dmg  = sum(m.get("base_dmg",  0) for m in mods),
            multishot = sum(m.get("multishot",  0) for m in mods),
            fire_rate = sum(m.get("fire_rate",  0) for m in mods),
            elemental = sum(m.get("elemental",  0) for m in mods),
            cc_mod    = sum(m.get("cc",         0) for m in mods),
            cd_mod    = sum(m.get("cd",         0) for m in mods),
        )

    @staticmethod
    def stats_from_wf_arcane(arc: dict) -> BuildStats:
        return BuildStats(
            base_dmg     = arc.get("base_dmg",        0),
            flat_cc      = arc.get("flat_crit_chance", 0),
            fire_rate    = arc.get("fire_rate",        0),
            final_dmg    = arc.get("final_dmg_bonus",  0),
            final_cd_add = arc.get("final_cd_add",     0),
        )

    @staticmethod
    def stats_from_weapon_arcane(arc: dict) -> BuildStats:
        return BuildStats(
            base_dmg        = arc.get("base_dmg",         0),
            cc_mod          = arc.get("cc",                0),
            flat_cc         = arc.get("flat_crit_chance",  0),
            fire_rate       = arc.get("fire_rate",         0),
            final_dmg       = arc.get("final_dmg_bonus",   0),
            final_cd_add    = arc.get("final_cd_add",      0),
            enervate_active = arc.get("dynamic_flat_cc",   False),
        )

    @staticmethod
    def stats_from_buffs(buff_list: list) -> BuildStats:
        return BuildStats(
            ext_faction   = sum(b.get("faction_mult",  0) for b in buff_list),
            ext_fire_rate = sum(b.get("fire_rate_mult", 0) for b in buff_list),
            ext_base_dmg  = sum(b.get("base_dmg",      0) for b in buff_list),
        )

    @staticmethod
    def merge_stats(*parts: BuildStats) -> BuildStats:
        """Add together an arbitrary number of BuildStats objects."""
        merged = BuildStats()
        for p in parts:
            merged.base_dmg        += p.base_dmg
            merged.multishot       += p.multishot
            merged.fire_rate       += p.fire_rate
            merged.elemental       += p.elemental
            merged.cc_mod          += p.cc_mod
            merged.cd_mod          += p.cd_mod
            merged.flat_cc         += p.flat_cc
            merged.final_dmg       += p.final_dmg
            merged.final_cd_add    += p.final_cd_add
            merged.ext_faction     += p.ext_faction
            merged.ext_fire_rate   += p.ext_fire_rate
            merged.ext_base_dmg    += p.ext_base_dmg
            merged.enervate_active  = merged.enervate_active or p.enervate_active
        return merged


# ===========================================================================
# Multiprocessing worker  (module-level so it can be pickled)
# ===========================================================================

def _eval_chunk(args):
    chunk, weapon, base_damage, strength_mult, fixed_stats = args
    best_dps   = -1.0
    best_combo = None
    for mod_combo in chunk:
        mod_stats    = DPSCalculator.stats_from_mods(mod_combo)
        merged_stats = DPSCalculator.merge_stats(mod_stats, fixed_stats)
        dps = DPSCalculator.calculate(weapon, base_damage, strength_mult, merged_stats)
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
        self.base_dmg   = self._resolve_base_damage()
        self.strength   = self._resolve_strength()
        self.buff_stats = self._resolve_buff_stats()
        self.mod_combos         = self._build_mod_combos()
        self.wf_arcane_combos   = self._build_wf_arcane_combos()
        self.weapon_arcane_pool = self._build_weapon_arcane_pool()

    # ── Setup helpers ─────────────────────────────────────────────────────

    def _resolve_base_damage(self) -> float:
        w      = self.weapon
        direct = w.get("direct_damage", 0)
        radial = w.get("radial_damage",  0)
        m      = self.cfg.damage_mode
        if m == "all":    return direct + radial
        if m == "direct": return direct
        if m == "radial": return radial
        raise ValueError(f"damage_mode must be 'all', 'direct', or 'radial' – got {m!r}")

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
                args       = [
                    (c, self.weapon, self.base_dmg, self.strength, fixed_stats)
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
        return DPSCalculator.calculate(self.weapon, self.base_dmg, self.strength, merged)


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
        allow_headshot         = allow_headshot,
        use_arcanes            = use_arcanes,
        use_weapon_arcanes     = use_weapon_arcanes,
        use_conditional_stacks = use_conditional_stacks,
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