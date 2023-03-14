def generate_wiki_rows():
  f = open("/home/mscottmoore/.steam/steam/steamapps/common/Stellaris/common/on_actions/00_on_actions.txt")
  desc = []
  rows = []
  for line in f:
    if not line.strip():
      # reset desc on empty lines
      # this stops commented out events from ending up in next on_action's desc
      desc = []
    if line.startswith("#"):
      desc.append(line.lstrip("#").strip())
    if line.startswith("on_"):
      name = line.strip().rstrip("{= ")
      desc = "<br>".join(desc)
      rows.append(f"| {name} || {desc} ||")
      rows.append("|-")
      desc = []
  for row in rows:
    print(row)

generate_wiki_rows()