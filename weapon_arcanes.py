# weapon_arcanes.py – Max‑rank fully‑stacked secondary arcanes
# Fully stacked values assume conditions are met (headshots, overshields, max stacks).
# Secondary Enervate is modelled dynamically.

weapon_arcanes = [
    # --- Base damage (additive with Hornet Strike etc.) ---
    {"name": "Secondary Deadhead",      "base_dmg": 1.20, "final_dmg_bonus": 0.30, "weapon_type": "secondary", "requires_headshot": True},
    {"name": "Secondary Dexterity",     "base_dmg": 0.60, "weapon_type": "secondary"},
    {"name": "Secondary Merciless",     "base_dmg": 3.60, "weapon_type": "secondary"},
    {"name": "Cascadia Flare",          "base_dmg": 4.80, "weapon_type": "secondary"},

    # --- Critical chance (additive with Primed Pistol Gambit etc.) ---
    {"name": "Cascadia Overcharge",     "cc": 3.00, "weapon_type": "secondary"},
    {"name": "Cascadia Accuracy",       "cc": 3.00, "weapon_type": "secondary", "requires_headshot": True},

    # --- Special dynamic: Secondary Enervate ---
    {"name": "Secondary Enervate",      "dynamic_flat_cc": True, "weapon_type": "secondary"},
]