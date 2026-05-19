# weapons.py
#
# Structure
# ---------
# Each weapon is a dict with:
#   "direct"       : dict     (mandatory – even if all damage types are 0)
#       "damage"       : dict { "impact":..., "puncture":..., "slash":...,
#                                "heat":..., "electricity":..., ... }
#                        (only non‑zero types need to be listed;
#                         total base damage = sum of values)
#       "crit_chance"      : float
#       "crit_multiplier"  : float
#       "fire_rate"        : float
#       "status_chance"    : float
#       "multishot"        : float
#       "magazine"         : int | None   (None = infinite ammo)
#       "reload"           : float
#   "radial"       : dict | None  (optional – same structure as "direct")
#   "exalted"      : bool
#   "mod_pool"     : str           ("pistol" or "primary")
#
# Ability Strength multiplies *all* components equally when the weapon is exalted.

weapons = {
    "jades_glory": {
        "direct": {
            "damage": {
                "impact":   0,
                "puncture": 0,
                "slash":    0,
                "heat":     0
            },
            "crit_chance":     0.15,
            "crit_multiplier": 2.0,
            "fire_rate":       1.67,
            "status_chance":   0.20,
            "multishot":       1.0,
            "magazine":        None,
            "reload":          0.0,
        },
        "radial": {
            "damage": {
                "heat": 150
            },
            "crit_chance":     0.15,
            "crit_multiplier": 2.0,
            "fire_rate":       1.67,
            "status_chance":   0.20,
            "multishot":       1.0,
            "magazine":        None,
            "reload":          0.0,
        },
        "exalted":  True,
        "mod_pool": "pistol"
    },
    "soma_prime": {
        "direct": {
            "damage": {
                "impact":   1.2,
                "puncture": 4.8,
                "slash":    6.0
            },
            "crit_chance":     0.30,
            "crit_multiplier": 3.0,
            "fire_rate":       15.0,
            "status_chance":   0.10,
            "multishot":       1.0,
            "magazine":        200,
            "reload":          3.0,
        },
        "radial": None,
        "exalted":  False,
        "mod_pool": "primary"
    },
    "soma_prime_incarnon": {
        "direct": {
            "damage": {
                "impact":   1.08,
                "puncture": 5.04,
                "slash":    11.88
            },
            "crit_chance":     0.30,
            "crit_multiplier": 3.0,
            "fire_rate":       15.0,
            "status_chance":   0.10,
            "multishot":       1.0,
            "magazine":        200,
            "reload":          3.0,
        },
        "radial": None,
        "exalted":  False,
        "mod_pool": "primary"
    },
    "hildryns_balefire_prime": {
        "direct": {
            "damage": {
                "impact":   0,
                "puncture": 0,
                "slash":    0,
            },
            "crit_chance":     0.5,
            "crit_multiplier": 1.5,
            "fire_rate":       0.833,
            "status_chance":   0.10,
            "multishot":       1.0,
            "magazine":        None,
            "reload":          0.0,
        },
        "radial": {
            "damage": {
                "electricity": 2000
            },
            "crit_chance":     0.5,
            "crit_multiplier": 1.5,
            "fire_rate":       0.833,
            "status_chance":   0.10,
            "multishot":       1.0,
            "magazine":        None,
            "reload":          0.0,
        },
        "exalted":  True,
        "mod_pool": "pistol"
    },
        "gammacor": {
        "direct": {
            "damage": {
                "impact": 0,
                "puncture": 0,
                "slash": 0,
                "magnetic": 16
            },
            "crit_chance": 0.10,
            "crit_multiplier": 1.5,
            "fire_rate": 8.0,
            "status_chance": 0.15,
            "multishot": 1.0,
            "magazine": 80,
            "reload": 2.0,
        },
        "radial": None,
        "exalted": False,
        "mod_pool": "pistol"
    },
}