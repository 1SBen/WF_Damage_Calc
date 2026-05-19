import argparse
from Calculator import run_calculation
from weapons import weapons

WEAPON_NAMES = weapons.keys()
WEAPON_TYPES = ["pistol", "primary"]
DAMAGE_MODES = ["all", "direct", "radial"]
FACTIONS = ["grineer", "corpus", "infested", "orokin", "murmur"]   # lowercase

def main():
    parser = argparse.ArgumentParser(
        description="Best 8-mod build calculator with damage-type selection."
    )
    parser.add_argument("--weapon", "-w", choices=WEAPON_NAMES, required=True,
                        help="Weapon to calculate (e.g. jades_glory)")
    parser.add_argument("--type", "-t", choices=WEAPON_TYPES, required=True,
                        help="Weapon category: pistol or primary")
    parser.add_argument("--arcanes", action="store_true",
                        help="Enable Warframe arcanes (e.g. Avenger)")
    parser.add_argument("--include-external-buff", action="append", default=[],
                        help="Include a specific external buff by name (can be repeated)")
    parser.add_argument("--damage-mode", "-dm", choices=DAMAGE_MODES,
                        default="all",
                        help="Which damage component(s) to sum: all, direct, radial (default: all)")
    parser.add_argument("--no-conditional-stacks", action="store_true",
                        help="Disable fully stacked conditional mods (use base stats only)")
    parser.add_argument("--faction", "-f", choices=FACTIONS, default=None,
                        help="Enable faction damage mods for the specified enemy faction")
    parser.add_argument("--weapon-arcanes", action="store_true",
                        help="Enable weapon arcane search (pistol arcanes)")
    parser.add_argument("--no-headshot", action="store_true",
                        help="Exclude any mods/arcanes that require headshots")
    parser.add_argument("--exclude-wf-arcane", action="append", default=[],
                        help="Exclude a warframe arcane by exact name (can repeat)")
    parser.add_argument("--exclude-weapon-arcane", action="append", default=[],
                        help="Exclude a weapon arcane by exact name (can repeat)")
    parser.add_argument("--exclude-mod", action="append", default=[],
                        help="Exclude a mod by exact name (can repeat)")
    parser.add_argument("--burst", action="store_true",
                    help="Calculate burst DPS (ignore reload). Default is sustained DPS.")
    parser.add_argument("--dot", action="store_false",
                    help="exclude Damage over Time (Slash, Heat, etc.) in total DPS")
    parser.add_argument("--dot-duration", type=float, default=1.0,
                    help="Seconds of DoT to count (default 1, full = 6).")

    args = parser.parse_args()

    run_calculation(
        weapon_name=args.weapon,
        weapon_type=args.type,
        use_arcanes=args.arcanes,
        use_weapon_arcanes=args.weapon_arcanes,
        include_buffs=args.include_external_buff,
        damage_mode=args.damage_mode,
        use_conditional_stacks=not args.no_conditional_stacks,
        faction=args.faction,
        allow_headshot=not args.no_headshot,
        exclude_wf_arcanes=args.exclude_wf_arcane,
        exclude_weapon_arcanes=args.exclude_weapon_arcane,
        exclude_mods=args.exclude_mod,
        dot_duration=args.dot_duration
    )

if __name__ == "__main__":
    main()