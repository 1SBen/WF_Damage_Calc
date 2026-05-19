# pistol_mods.py – Trimmed for maximum raw DPS combinations
# Kept: best-in-slot for each category, all 90% & Primed elementals,
#       special elemental/crit/fire rate hybrids, only Primed faction mods.

# ---------- BASE MOD LIST (no stacked conditional bonuses) ----------

pistol_mods_base = [
    #IPS
    {"name": "Concussion Rounds",   "impact_bonus": 0.90},   # +90% Impact
    {"name": "Pummel",              "impact_bonus": 1.20},   # +120% Impact
    {"name": "No Return",           "puncture_bonus": 0.60}, # +60% Puncture
    {"name": "Bore",                "puncture_bonus": 1.20}, # +120% Puncture
    {"name": "Razor Shot",          "slash_bonus": 0.60},    # +60% Slash
    {"name": "Maim",                "slash_bonus": 1.20},    # +120% Slash

    # Base damage (strongest three)
    {"name": "Hornet Strike",           "base_dmg": 2.20},
    {"name": "Magnum Force",            "base_dmg": 1.65},
    {"name": "Augur Pact",              "base_dmg": 0.90},

    # Multishot (best in slot, Amalgam dropped as inferior)
    {"name": "Barrel Diffusion",        "multishot": 1.20},
    {"name": "Galvanized Diffusion",    "multishot": 1.10},  # base
    {"name": "Lethal Torrent",          "multishot": 0.60, "fire_rate": 0.60},

    # Crit chance (only top options, Creeping Bullseye dropped)
    {"name": "Primed Pistol Gambit",    "cc": 1.87},
    {"name": "Galvanized Crosshairs",   "cc": 1.20},  # base

    # Crit damage (keep Primed, Hollow Point, Merciless, Magnetic Might)
    {"name": "Primed Target Cracker",   "cd": 1.10},
    {"name": "Hollow Point",            "cd": 0.60, "base_dmg": -0.15},
    {"name": "Merciless Gunfight",      "cd": 0.60},
    {"name": "Magnetic Might",          "elemental": 0.60, "cd": 0.40},

    # Elemental – all 90% and Primed (165%) mods, plus special hybrids
    {"name": "Pathogen Rounds",         "elemental": 0.90, "elemental_type": "toxin"},
    {"name": "Convulsion",              "elemental": 0.90, "elemental_type": "electricity"},
    {"name": "Heated Charge",           "elemental": 0.90, "elemental_type": "heat"},
    {"name": "Deep Freeze",             "elemental": 0.90, "elemental_type": "cold"},
    {"name": "Primed Heated Charge",    "elemental": 1.65, "elemental_type": "heat"},
    {"name": "Primed Convulsion",       "elemental": 1.65, "elemental_type": "electricity"},
    {"name": "Accelerated Isotope",     "elemental": 0.60, "fire_rate": 0.60, "elemental_type" : "radiation"},  # radiation + fire rate

    # Fire rate (keep Gunslinger and Anemic Agility)
    {"name": "Gunslinger",              "fire_rate": 0.72},
    {"name": "Anemic Agility",          "fire_rate": 0.90, "base_dmg": -0.15},

    # Faction mods (Primed only – one per faction type)
    {"name": "Primed Expel Grineer",    "faction": 0.55, "faction_type": "grineer"},
    {"name": "Primed Expel Corpus",     "faction": 0.55, "faction_type": "corpus"},
    {"name": "Primed Expel Infested",   "faction": 0.55, "faction_type": "infested"},
    {"name": "Primed Expel Orokin",     "faction": 0.55, "faction_type": "orokin"},
    {"name": "Primed Expel The Murmur","faction": 0.55, "faction_type": "murmur"},
]

# ---------- STACKED CONDITIONAL MOD LIST ----------
pistol_mods_stacked = [
    # Base damage (same as base)
    {"name": "Hornet Strike",           "base_dmg": 2.20},
    {"name": "Magnum Force",            "base_dmg": 1.65},
    {"name": "Augur Pact",              "base_dmg": 0.90},

    # Multishot – Galvanized Diffusion fully stacked
    {"name": "Barrel Diffusion",        "multishot": 1.20},
    {"name": "Galvanized Diffusion",    "multishot": 2.30},  # stacked
    {"name": "Lethal Torrent",          "multishot": 0.60, "fire_rate": 0.60},

    # Crit chance – Galvanized Crosshairs fully stacked
    {"name": "Primed Pistol Gambit",    "cc": 1.87},
    {"name": "Galvanized Crosshairs",   "cc": 1.20, "requires_headshot": True},

    # Crit damage
    {"name": "Primed Target Cracker",   "cd": 1.10},
    {"name": "Hollow Point",            "cd": 0.60, "base_dmg": -0.15},
    {"name": "Merciless Gunfight",      "cd": 0.60},
    {"name": "Magnetic Might",          "elemental": 0.60, "cd": 0.40},

    # Elemental (same high-damage mods)
    {"name": "Pathogen Rounds",         "elemental": 0.90},
    {"name": "Convulsion",              "elemental": 0.90},
    {"name": "Heated Charge",           "elemental": 0.90},
    {"name": "Deep Freeze",             "elemental": 0.90},
    {"name": "Primed Heated Charge",    "elemental": 1.65},
    {"name": "Primed Convulsion",       "elemental": 1.65},
    {"name": "Accelerated Isotope",     "elemental": 0.60, "fire_rate": 0.60},

    # Fire rate
    {"name": "Gunslinger",              "fire_rate": 0.72},
    {"name": "Anemic Agility",          "fire_rate": 0.90, "base_dmg": -0.15},

    # Faction mods (same Primed set)
    {"name": "Primed Expel Grineer",    "faction": 0.55, "faction_type": "grineer"},
    {"name": "Primed Expel Corpus",     "faction": 0.55, "faction_type": "corpus"},
    {"name": "Primed Expel Infested",   "faction": 0.55, "faction_type": "infested"},
    {"name": "Primed Expel Orokin",     "faction": 0.55, "faction_type": "orokin"},
    {"name": "Primed Expel The Murmur","faction": 0.55, "faction_type": "murmur"},
]





"""
# pistol_mods.py – Base & conditional stats, faction tags

# ---------- BASE MOD LIST (no stacked conditional bonuses) ----------
pistol_mods_base = [
    # Base damage
    {"name": "Hornet Strike",           "base_dmg": 2.20},
    {"name": "Magnum Force",            "base_dmg": 1.65},
    {"name": "Augur Pact",              "base_dmg": 0.90},
    # Multishot
    {"name": "Barrel Diffusion",        "multishot": 1.20},
    {"name": "Amalgam Barrel Diffusion","multishot": 1.10},
    {"name": "Galvanized Diffusion",    "multishot": 1.10},  # base only
    {"name": "Lethal Torrent",          "multishot": 0.60, "fire_rate": 0.60},
    # Crit chance
    {"name": "Pistol Gambit",           "cc": 1.20},
    {"name": "Primed Pistol Gambit",    "cc": 1.87},
    {"name": "Creeping Bullseye",       "cc": 0.48, "fire_rate": -0.20},
    {"name": "Galvanized Crosshairs",   "cc": 1.20, "requires_headshot": True},  # base on headshot
    # Crit damage
    {"name": "Target Cracker",          "cd": 0.60},
    {"name": "Primed Target Cracker",   "cd": 1.10},
    {"name": "Hollow Point",            "cd": 0.60, "base_dmg": -0.15},
    {"name": "Merciless Gunfight",      "cd": 0.60},
    {"name": "Magnetic Might",          "elemental": 0.60, "cd": 0.40},
    # Elemental 90%
    {"name": "Pathogen Rounds",         "elemental": 0.90},
    {"name": "Convulsion",              "elemental": 0.90},
    {"name": "Heated Charge",           "elemental": 0.90},
    {"name": "Deep Freeze",             "elemental": 0.90},
    # Elemental primed
    {"name": "Primed Heated Charge",    "elemental": 1.65},
    {"name": "Primed Convulsion",       "elemental": 1.65},
    # Elemental 60/60
    {"name": "Jolt",                    "elemental": 0.60},
    {"name": "Pistol Pestilence",       "elemental": 0.60},
    {"name": "Frostbite",               "elemental": 0.60},
    {"name": "Scorch",                  "elemental": 0.60},
    # Elemental + utility
    {"name": "Ice Storm",               "elemental": 0.40},
    {"name": "Accelerated Isotope",     "elemental": 0.60, "fire_rate": 0.60},
    # Fire rate
    {"name": "Gunslinger",              "fire_rate": 0.72},
    {"name": "Anemic Agility",          "fire_rate": 0.90, "base_dmg": -0.15},
    # Faction mods (tagged with faction_type)
    {"name": "Primed Expel Grineer",    "faction": 0.55, "faction_type": "grineer"},
    {"name": "Primed Expel Corpus",     "faction": 0.55, "faction_type": "corpus"},
    {"name": "Primed Expel Infested",   "faction": 0.55, "faction_type": "infested"},
    {"name": "Primed Expel Orokin",     "faction": 0.55, "faction_type": "orokin"},
    {"name": "Primed Expel The Murmur","faction": 0.55, "faction_type": "murmur"},
    {"name": "Expel Grineer",           "faction": 0.30, "faction_type": "grineer"},
    {"name": "Expel Corpus",            "faction": 0.30, "faction_type": "corpus"},
    {"name": "Expel Infested",          "faction": 0.30, "faction_type": "infested"},
    {"name": "Expel Orokin",            "faction": 0.30, "faction_type": "orokin"},
    {"name": "Expel The Murmur",       "faction": 0.30, "faction_type": "murmur"},
]

# ---------- STACKED CONDITIONAL MOD LIST (same structure, fully stacked) ----------
pistol_mods_stacked = [
    # (copy all mods from base, but replace the Galvanized entries)
    {"name": "Hornet Strike",           "base_dmg": 2.20},
    {"name": "Magnum Force",            "base_dmg": 1.65},
    {"name": "Augur Pact",              "base_dmg": 0.90},
    {"name": "Barrel Diffusion",        "multishot": 1.20},
    {"name": "Amalgam Barrel Diffusion","multishot": 1.10},
    {"name": "Galvanized Diffusion",    "multishot": 2.30},  # stacked 1.10 + 1.20
    {"name": "Lethal Torrent",          "multishot": 0.60, "fire_rate": 0.60},
    {"name": "Pistol Gambit",           "cc": 1.20},
    {"name": "Primed Pistol Gambit",    "cc": 1.87},
    {"name": "Creeping Bullseye",       "cc": 0.48, "fire_rate": -0.20},
    {"name": "Galvanized Crosshairs",   "cc": 3.20},  # stacked 1.20 + 2.00
    {"name": "Target Cracker",          "cd": 0.60},
    {"name": "Primed Target Cracker",   "cd": 1.10},
    {"name": "Hollow Point",            "cd": 0.60, "base_dmg": -0.15},
    {"name": "Merciless Gunfight",      "cd": 0.60},
    {"name": "Magnetic Might",          "elemental": 0.60, "cd": 0.40},
    {"name": "Pathogen Rounds",         "elemental": 0.90},
    {"name": "Convulsion",              "elemental": 0.90},
    {"name": "Heated Charge",           "elemental": 0.90},
    {"name": "Deep Freeze",             "elemental": 0.90},
    {"name": "Primed Heated Charge",    "elemental": 1.65},
    {"name": "Primed Convulsion",       "elemental": 1.65},
    {"name": "Jolt",                    "elemental": 0.60},
    {"name": "Pistol Pestilence",       "elemental": 0.60},
    {"name": "Frostbite",               "elemental": 0.60},
    {"name": "Scorch",                  "elemental": 0.60},
    {"name": "Ice Storm",               "elemental": 0.40},
    {"name": "Accelerated Isotope",     "elemental": 0.60, "fire_rate": 0.60},
    {"name": "Gunslinger",              "fire_rate": 0.72},
    {"name": "Anemic Agility",          "fire_rate": 0.90, "base_dmg": -0.15},
    # Faction (identical to base)
    {"name": "Primed Expel Grineer",    "faction": 0.55, "faction_type": "grineer"},
    {"name": "Primed Expel Corpus",     "faction": 0.55, "faction_type": "corpus"},
    {"name": "Primed Expel Infested",   "faction": 0.55, "faction_type": "infested"},
    {"name": "Primed Expel Orokin",     "faction": 0.55, "faction_type": "orokin"},
    {"name": "Primed Expel The Murmur","faction": 0.55, "faction_type": "murmur"},
    {"name": "Expel Grineer",           "faction": 0.30, "faction_type": "grineer"},
    {"name": "Expel Corpus",            "faction": 0.30, "faction_type": "corpus"},
    {"name": "Expel Infested",          "faction": 0.30, "faction_type": "infested"},
    {"name": "Expel Orokin",            "faction": 0.30, "faction_type": "orokin"},
    {"name": "Expel The Murmur",       "faction": 0.30, "faction_type": "murmur"},
]
"""