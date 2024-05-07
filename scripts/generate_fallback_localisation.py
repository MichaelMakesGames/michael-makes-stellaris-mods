from pathlib import Path
import re
import subprocess

source_language = "english"
target_languages = [
  "braz_por",
  "french",
  "german",
  "japanese",
  "korean",
  "polish",
  "russian",
  "simp_chinese",
  "spanish",
]
report_languages = [
#   "braz_por",
#   "french",
#   "german",
#   "japanese",
#   "korean",
#   "polish",
#   "russian",
#   "simp_chinese",
#   "spanish",
]

# set this to true when generating fallbacks for updated source string
# set this to false when processing/validating updated target strings
stash = True
# set this to true to do a dry run, printing reports without editing files
dry = False

line_regex = re.compile("^\s*([\w\.]+)\s*:\s*\"(.*)\"\s*(#.*)?$")

def main():
    cwd = Path.cwd()
    source_language_dir = cwd.joinpath("localisation", f"l_{source_language}")

    current_source_files = {}
    current_source_strings = {}
    for child in source_language_dir.iterdir():
        parsed_lines = []
        current_source_files[str(child.relative_to(source_language_dir))] = parsed_lines
        parse_file(child, parsed_lines, current_source_strings)

    if stash:
        subprocess.run(["git", "add", "--all"])
        subprocess.run(["git", "stash", "save", "generating fallback localisation"])

    previous_source_files = {}
    previous_source_strings = {}
    for child in source_language_dir.iterdir():
        parsed_lines = []
        previous_source_files[str(child.relative_to(source_language_dir))] = parsed_lines
        parse_file(child, parsed_lines, previous_source_strings)

    previous_target_strings = {}
    for target_language in target_languages:
        previous_target_strings[target_language] = {}
        target_language_dir = cwd.joinpath("localisation", f"l_{target_language}")
        if not target_language_dir.exists():
            continue
        for child in target_language_dir.iterdir():
            parse_file(child, [], previous_target_strings[target_language])

    if stash:
        subprocess.run(["git" ,"stash", "pop"])

    for target_language in target_languages:
        untranslated_keys = []
        target_language_dir = cwd.joinpath("localisation", f"l_{target_language}")
        if not dry:
            if target_language_dir.exists():
                subprocess.run(["rm", "-r", str(target_language_dir)])
            target_language_dir.mkdir()
        for file in current_source_files:
            target_lines = [f"l_{target_language}:\n"]
            for source_line in current_source_files[file]:
                if type(source_line) == str:
                    if source_line == "":
                        target_lines.append("\n")
                    else:
                        target_lines.append(f" {source_line}\n")
                else:
                    key, current_source_string, comment = source_line
                    is_new = key not in previous_source_strings
                    is_updated = key in previous_source_strings and previous_source_strings[key] != current_source_string
                    do_not_translate = comment == "DO NOT TRANSLATE"
                    translation = previous_target_strings[target_language].get(key)
                    if is_new or is_updated or do_not_translate:
                        translation = None
                    if translation and previous_source_strings.get(key) == translation and not do_not_translate:
                        translation = None
                    if translation is None and not do_not_translate:
                        comment = "UNTRANSLATED"
                        untranslated_keys.append(key)
                    string_to_write = current_source_string if translation is None else translation
                    comment_to_write = f" # {comment}" if comment is not None else ""
                    target_lines.append(f" {key}: \"{string_to_write}\"{comment_to_write}\n")
            if not dry:
                target_file_name = file.replace(source_language, target_language)
                target_file_path = target_language_dir.joinpath(target_file_name)
                target_file = open(target_file_path, "w", encoding="utf-8-sig")
                target_file.writelines(target_lines)
                target_file.close()
        if target_language in report_languages:
            print()
            print(f"{target_language} report:")
            if untranslated_keys:
                print("Untranslated keys:")
                for key in untranslated_keys:
                    print(f"\t{key}")
            else:
                print("Untranslated keys: None")
            unrecognized_keys = [key for key in previous_target_strings[target_language] if key not in previous_source_strings]
            if unrecognized_keys:
                print("Unrecognized keys:")
                for key in unrecognized_keys:
                    print(f"\t{key}")
            else:
                print("Unrecognized keys: None")                


def parse_file(path, lines, strings):
    file = open(path, "r")
    for index, line in enumerate(file):
        if index == 0:
            continue
        m = line_regex.match(line)
        if m is not None:
            key = m.group(1)
            string = m.group(2)
            strings[key] = string
            try:
                comment = m.group(3)
                if comment:
                    comment = comment.strip(" \n#")
            except IndexError:
                comment = None
            lines.append((key, string, comment))
        else:
            stripped = line.strip()
            if stripped.startswith("#") or stripped == "":
                lines.append(stripped)
            else:
                print(f"Failed to parse line in {path.relative_to(Path.cwd())}:")
                print(f"\t{stripped}")
    file.close()


main()
