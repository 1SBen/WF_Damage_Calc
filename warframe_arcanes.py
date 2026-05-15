# warframe_arcanes.py – All max‑rank weapon‑related Arcanes
# Each arcane is a dict with effect keys.
# weapon_type: "primary", "secondary", "melee", "shotgun", "sniper", "universal"
# final_dmg_bonus is additive with itself, final_cd_add is a flat addition to the final crit multiplier.

warframe_arcanes = [
    # --- Fire Rate ---
    {"name": "Arcane Acceleration",     "fire_rate": 0.90, "weapon_type": "primary"},   # on crit
    {"name": "Arcane Velocity",         "fire_rate": 1.20, "weapon_type": "secondary"},  # on crit
    {"name": "Arcane Tempo",            "fire_rate": 0.90, "weapon_type": "shotgun"},    # on crit

    # --- Flat Critical Chance ---
    {"name": "Arcane Avenger",          "flat_crit_chance": 0.45},                       # on damaged (universal)
    {"name": "Arcane Hot Shot",         "flat_crit_chance": 3.00},  # fully stacked 50 stacks × 6%, universal

    # --- Base Damage (additive with Serration/Hornet Strike) ---
    {"name": "Arcane Awakening",        "base_dmg": 1.50, "weapon_type": "secondary"},   # on reload
    {"name": "Arcane Precision",        "base_dmg": 3.00, "weapon_type": "secondary", "requires_headshot": True},
    {"name": "Arcane Rage",             "base_dmg": 1.80, "weapon_type": "primary",   "requires_headshot": True},
    {"name": "Arcane Rise",             "base_dmg": 1.50, "weapon_type": "primary"},     # on reload
    {"name": "Arcane Primary Charger",  "base_dmg": 3.00, "weapon_type": "primary"},     # on melee kill

    # --- Final Damage Multiplier (multiplicative after everything, like Roar) ---
    {"name": "Arcane Arachne",          "final_dmg_bonus": 1.50},                        # on wall latch
    {"name": "Theorem Demulcent",       "final_dmg_bonus": 1.80},  # fully stacked (15×12%), needs zone

    # --- Final Critical Multiplier addition ---
    {"name": "Arcane Crepuscular",      "strength": 0.30, "final_cd_add": 3.0},  # while invisible, also +30% strength

    # --- Melee (placeholders for future use) ---
    {"name": "Arcane Fury",             "base_dmg": 1.80, "weapon_type": "melee"},
    {"name": "Arcane Blade Charger",    "base_dmg": 3.00, "weapon_type": "melee"},
]