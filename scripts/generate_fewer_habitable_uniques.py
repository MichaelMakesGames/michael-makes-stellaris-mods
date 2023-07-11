import argparse
import shutil
import os
from pathlib import Path
import pprint
import re

sources = {
    "vanilla": "~/.steam/root/steamapps/common/Stellaris",
    "realspace": "~/.local/share/Steam/steamapps/workshop/content/281990/937289339"
}

parser = argparse.ArgumentParser(prog="generate_fewer_habitable_uniques")
parser.add_argument("--scale", type=int, default=25)
parser.add_argument("--source", choices=sources.keys(), default="vanilla")
parser.add_argument("--debug", action='store_true', default=False)
args = parser.parse_args()

pp = pprint.PrettyPrinter(indent=4)
copy_data_from = os.path.expanduser(sources[args.source])
spawn_chance_mult = float(args.scale) / 100.0
spawn_chance_mult_extra_scale = spawn_chance_mult**1.5

DEBUG = args.debug
MIN = 1

# assume proper indentation
initializer_open_re = re.compile("^(\w+) ?= ?\{")
initializer_close_re = re.compile("^\}")
open_re = re.compile("^\s*(\w+) ?= ?\{\s*(#.*)?$")
close_re = re.compile("^\s*\}\s*(#.*)?$")
variable_re = re.compile("^(@\w+) ?= ?([0-9\.]+)\s*(#.*)?$")
# make sure only white space is before content, so we don't match commented out lines
prop_re = re.compile('^\s*(\w+) ?= ?"?(@?\w+)"?\s*(#.*)?$')

# these are important systems that should never be overwritten
overwrite_deny_list = {
    "overlord_system_init",  # spawns the overlord empire for Imperial Fiefdom origin
    "lost_colony_1",  # spawns parent civ for Lost Colony origin
    "special_init_04",  # don't mess with Sol!
    "msi_home_system",  # MSI for Payback and Broken Shackles origins
    "broken_shackles_parent_system",  # used for Broken Shackles origin
    "com_sol_system",  # don't mess with Sol!
    "lost_colony_sol_system",  # don't mess with Sol!
    "une_deneb_system",  # don't mess with Deneb!
}
# these are confirmed safe-to-scale
overwrite_allow_list = {
    "relic_system_4",  # omnirelic archaeology site
    "wenkwort_initializer",  # Wenkwort Artem
    "hostile_init_06",  # red crystal system
    "lone_defender",  # Lone Defender, low usage odds
    "ghost_ship_system_initializer_01",  # Ghost Ship, not particularly high usage odds
    "distar_phaseshift_system",  # this has a guaranteed gaia world that isn't in the system_initializer
    "locust_system_initializer_01",  # Locust Swarm system
    "legendary_leader_start_site",  # Exakeides system, spawns a bunch of neighbor systems with habitables
}
# these come with lots of planets, so scale them even more
extra_scale_list = {
    "legendary_leader_start_site",  # spawns 3 neighbor systems with habitables
    "unique_system_initializer_07",  # triple planet system
    "unique_system_initializer_08",  # triple planet system
    "unique_system_initializer_09",  # triple planet system
    "ratling_1_1",  # lots of tomb worlds
}

# if I start patching for other mods, might be better to parse common/planet_classes
colonizable_planet_classes = {
    "ideal_design_class",
    "ideal_planet_class",
    "pc_alpine",
    "pc_arctic",
    "pc_arid",
    "pc_city",
    "pc_continental",
    "pc_desert",
    "pc_gaia",
    "pc_habitat",
    "pc_nuked",
    "pc_ocean",
    "pc_relic",
    "pc_savannah",
    "pc_shattered_ring_habitable",
    "pc_tropical",
    "pc_tundra",
    "random_colonizable",
    "rl_cool_moist_planets",
    "rl_habitable_normal",
}
# hopefully these use the habitable worlds slider
potentially_colonizable_planet_classes = {
    "random",
    "rl_all_normal_planets",
}
non_colonizable_planet_classes = {
    "pc_a_star",
    "pc_ai",
    "pc_asteroid",
    "pc_b_star",
    "pc_barren_cold",
    "pc_barren",
    "pc_black_hole",
    "pc_broken",
    "pc_crystal_asteroid",
    "pc_cybrex",
    "pc_f_star",
    "pc_frozen",
    "pc_g_star",
    "pc_gas_giant",
    "pc_gray_goo",
    "pc_ice_asteroid",
    "pc_k_star",
    "pc_m_star",
    "pc_machine_broken",
    "pc_molten",
    "pc_rare_crystal_asteroid",
    "pc_ringworld_habitable",
    "pc_ringworld_seam_damaged",
    "pc_ringworld_seam",
    "pc_ringworld_tech_damaged",
    "pc_ringworld_tech",
    "pc_shattered_2",
    "pc_shattered",
    "pc_shielded",
    "pc_shrouded",
    "pc_toxic",
    "random_non_colonizable",
    "rl_no_atmosphere_planets",
    "rl_unhabitable_planets",
    "rl_voidspawn_egg",
    "star",
    # real space
    "pc_o_super_star",
    "pc_k_giant_star",
    "pc_y_star",
    "pc_o_hyper_star",
    "red_giant",
    "blue_supergiant",
    "pc_d_star",
    "yellow_supergiant",
    "yellow_stars",
    "pc_t_star",
    "pc_g_giant_star",
    "pc_m_hyper_star",
    "pc_k_super_star",
    "pc_b_super_star",
    "blue_stars",
    "pc_o_star",
    "pc_f_super_star",
    "none",
}
all_recognized_planet_classes = colonizable_planet_classes.union(
    potentially_colonizable_planet_classes
).union(non_colonizable_planet_classes)


def main():
    # delete/create folders
    cwd = Path.cwd()
    cwd_common = cwd.joinpath("common")
    cwd_initializers = cwd_common.joinpath("solar_system_initializers")
    if cwd_initializers.exists():
        shutil.rmtree(cwd_initializers)
    if not cwd_common.exists():
        os.mkdir(cwd_common)
    os.mkdir(cwd_initializers)

    # read files and rewrite to cwd
    initializers_dir = Path(copy_data_from, "common/solar_system_initializers")
    initializers = {}
    current_initializer = None
    unrecognized_planet_classes = set()
    scaled_initializers = []
    for child in initializers_dir.iterdir():
        file = open(child, "r")
        file_has_rewrite = False
        write_lines = []
        file_variables = {}
        for index, line in enumerate(file):
            variable_match = variable_re.match(line)
            if variable_match is not None:
                file_variables[variable_match.group(1)] = variable_match.group(2)
            initializer_open_match = initializer_open_re.match(line)
            if initializer_open_match is not None:
                if current_initializer is not None:
                    print(
                        f"WARNING: new initializer '{initializer_open_match.group(1)}' opened by previous initializer '{current_initializer['key']}' is not closed"
                    )
                    print(f"File: ${current_initializer['file']}")
                    print(f"Line: ${index}")
                    print(
                        f"Previous initializer line: {current_initializer['start_line_index']}"
                    )
                current_initializer = {
                    "key": initializer_open_match.group(1),
                    "file": child.name,
                    "start_line_index": index,
                    "lines": [],
                    "usage": None,
                    "usage_odds": None,
                    "has_complex_usage_odds": False,
                    "max_instances": None,
                    "spawn_chance": None,
                    "scaled_spawn_chance": None,
                    "primitive_system": None,
                    "planet_classes": set(),
                    "has_colonizable": False,
                }
                initializers[current_initializer["key"]] = current_initializer
            if current_initializer:
                current_initializer["lines"].append(line)
                open_match = open_re.match(line)
                if open_match is not None and open_match.group(1) == "usage_odds":
                    current_initializer["has_complex_usage_odds"] = True
                prop_match = prop_re.match(line)
                parse_prop(
                    prop="usage",
                    match=prop_match,
                    parse_value=str,
                    index=index,
                    current_initializer=current_initializer,
                    file_variables=file_variables,
                )
                parse_prop(
                    prop="usage_odds",
                    match=prop_match,
                    parse_value=float,
                    index=index,
                    current_initializer=current_initializer,
                    file_variables=file_variables,
                )
                parse_prop(
                    prop="max_instances",
                    match=prop_match,
                    parse_value=int,
                    index=index,
                    current_initializer=current_initializer,
                    file_variables=file_variables,
                )
                parse_prop(
                    prop="primitive_system",
                    match=prop_match,
                    parse_value=str,
                    index=index,
                    current_initializer=current_initializer,
                    file_variables=file_variables,
                )
                # kinda hacky to make sure we're not matching the spawn_chance for a neighbor... kinda getting to the point where I need a full parser
                if (
                    find_most_recent_opener(current_initializer["lines"])
                    != "neighbor_system"
                ):
                    parse_prop(
                        prop="spawn_chance",
                        match=prop_match,
                        parse_value=int,
                        index=index,
                        current_initializer=current_initializer,
                        file_variables=file_variables,
                    )
                    parse_prop(
                        prop="scaled_spawn_chance",
                        match=prop_match,
                        parse_value=int,
                        index=index,
                        current_initializer=current_initializer,
                        file_variables=file_variables,
                    )
                if prop_match is not None and prop_match.group(1) == "class":
                    most_recent_opener = find_most_recent_opener(
                        current_initializer["lines"]
                    )
                    if most_recent_opener == "planet" or most_recent_opener == "moon":
                        planet_class = prop_match.group(2)
                        current_initializer["planet_classes"].add(planet_class)
                        if planet_class in colonizable_planet_classes:
                            current_initializer["has_colonizable"] = True
                        if planet_class not in all_recognized_planet_classes:
                            unrecognized_planet_classes.add(planet_class)
                            print(f"WARNING: unrecognized planet class '{planet_class}")
                            print(f"\tInitializer: {current_initializer['key']}")
                            print(f"\tFile: ${current_initializer['file']}")
                            print(f"\tLine: ${index}")
                initializer_close_match = initializer_close_re.match(line)
                if initializer_close_match is not None:
                    if should_overwrite(current_initializer):
                        scale_by = (
                            spawn_chance_mult_extra_scale
                            if current_initializer["key"] in extra_scale_list
                            else spawn_chance_mult
                        )
                        scaled_initializers.append(current_initializer["key"])
                        file_has_rewrite = True
                        lines_copy = list(current_initializer["lines"])
                        scale_prop(
                            prop="spawn_chance",
                            scale=scale_by,
                            current_initializer=current_initializer,
                            lines_copy=lines_copy,
                            round_value=True,
                        )
                        scale_prop(
                            prop="scaled_spawn_chance",
                            scale=scale_by,
                            current_initializer=current_initializer,
                            lines_copy=lines_copy,
                            round_value=True,
                        )
                        if (
                            current_initializer["spawn_chance"] is None
                            and current_initializer["scaled_spawn_chance"] is None
                        ):
                            lines_copy.insert(
                                current_initializer["usage"]["line_index"],
                                f"\tspawn_chance = {max(MIN, round(100 * scale_by))} # OVERWRITE (added)\n",
                            )
                        for initializer_line in lines_copy:
                            write_lines.append(initializer_line)
                    else:
                        for initializer_line in current_initializer["lines"]:
                            write_lines.append(initializer_line)
                    current_initializer = None
            else:
                write_lines.append(line)
        file.close()
        # write file to cwd
        # don't bother writing if there were no changes
        if file_has_rewrite:
            file = open(cwd_initializers.joinpath(child.name), "w")
            file.writelines(write_lines)
            file.close()
    print("Scaled initializers:")
    for initializer in sorted(scaled_initializers):
        print(f"\t{initializer}")
    print(f"Total: {len(scaled_initializers)}")


def find_most_recent_opener(lines):
    for line in reversed(lines):
        match = open_re.match(line)
        if match is not None:
            return match.group(1)
    return None


def parse_prop(prop, match, parse_value, index, current_initializer, file_variables):
    if match is not None and match.group(1) == prop:
        value = match.group(2)
        if value in file_variables:
            value = file_variables[value]
        try:
            value = parse_value(value)
            current_initializer[prop] = {
                "value": value,
                "line_index": index - current_initializer["start_line_index"],
            }
        except:
            print(f"WARNING: failed to parse {prop}")
            print(f"\tInitializer: {current_initializer['key']}")
            print(f"\tFile: ${current_initializer['file']}")
            print(f"\tLine: ${index}")


def scale_prop(prop, scale, current_initializer, lines_copy, round_value):
    if current_initializer[prop] is not None:
        scaled_value = current_initializer[prop]["value"] * scale
        if round_value:
            scaled_value = max(MIN, round(scaled_value))
        lines_copy[
            current_initializer[prop]["line_index"]
        ] = f"\t{prop} = {scaled_value} # OVERWRITE (from {current_initializer[prop]['value']})\n"


def should_overwrite(initializer):
    if initializer["key"] in overwrite_allow_list:
        return True
    if initializer["key"] in overwrite_deny_list:
        return False
    # only care about misc_system_init with guaranteed habitable
    if (
        initializer["usage"] == None
        or initializer["usage"]["value"] != "misc_system_init"
    ):
        return False
    if not initializer["has_colonizable"]:
        return False
    # skip primitive_system=yes; they are controlled by primitive systems slider
    if (
        initializer["primitive_system"] is not None
        and initializer["primitive_system"]["value"] == "yes"
    ):
        return False
    # if usage odds is 0, then it's being specifically called (and should probably not be misc_system_init in the first place)
    if (
        initializer["usage_odds"] is not None
        and initializer["usage_odds"]["value"] == 0
    ) or (
        initializer["usage_odds"] is None and not initializer["has_complex_usage_odds"]
    ):
        if DEBUG:
            print(
                f"DEBUG: skipping '{initializer['key']}': usage_odds == 0 or is missing"
            )
        return False
    # check if unique
    if (
        initializer["max_instances"] is None
        or initializer["max_instances"]["value"] != 1
    ):
        if DEBUG:
            print(f"DEBUG: skipping '{initializer['key']}': max_instances != 1")
        return False
    # this is already not guaranteed, safe to scale down
    if initializer["scaled_spawn_chance"] is not None or (
        initializer["spawn_chance"] is not None
        and initializer["spawn_chance"]["value"] < 100
    ):
        return True
    # if usage odds >= 100, then it's likely important
    if (
        initializer["usage_odds"] is not None
        and initializer["usage_odds"]["value"] >= 100
    ):
        if DEBUG:
            print(f"DEBUG: skipping '{initializer['key']}': usage_odds >= 100")
        return False
    # complex case...
    if initializer["usage_odds"] is None:
        usage_odds_lines = []
        usage_odds_open = False
        num_opens = 0
        for line in initializer["lines"]:
            close_match = close_re.match(line)
            if close_match is not None and usage_odds_open:
                num_opens -= 1
                if num_opens == 0:
                    usage_odds_open = False
            if usage_odds_open:
                usage_odds_lines.append(line)
            open_match = open_re.match(line)
            if open_match is not None and open_match.group(1) == "usage_odds":
                usage_odds_open = True
                num_opens += 1
            elif open_match and usage_odds_open:
                num_opens += 1
        print(
            f"WARNING: '{initializer['key']}' has complex usage_odds; not skipping; REVIEW THIS!"
        )
        print("".join(usage_odds_lines))
    return True


main()
