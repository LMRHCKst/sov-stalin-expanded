import io, os, shutil

GAME = r"D:\Hearts of Iron IV (2016)\Hearts of Iron IV"
MOD = os.path.join(os.path.expanduser("~"), "Documents", "Paradox Interactive",
                   "Hearts of Iron IV", "mod", "sov_stalin_expanded")

TEMPLATE = '''

##### Универсальная дивизия (мод) #####
division_template = {
\tname = "Universalnaya Diviziya"
\tdivision_names_group = SOV_INF_01

\tregiments = {
\t\tinfantry = { x = 0 y = 0 }
\t\tinfantry = { x = 0 y = 1 }
\t\tinfantry = { x = 0 y = 2 }
\t\tinfantry = { x = 1 y = 0 }
\t\tinfantry = { x = 1 y = 1 }
\t\tinfantry = { x = 1 y = 2 }
\t\tinfantry = { x = 2 y = 0 }
\t\tinfantry = { x = 2 y = 1 }
\t\tinfantry = { x = 2 y = 2 }
\t\tartillery = { x = 3 y = 0 }
\t\tartillery = { x = 3 y = 1 }
\t\tartillery = { x = 3 y = 2 }
\t}
\tsupport = {
\t\tengineer = { x = 0 y = 0 }
\t\tartillery = { x = 0 y = 1 }
\t\tanti_air = { x = 0 y = 2 }
\t}
}
'''

for name in ("SOV_1936.txt", "SOV_1939.txt"):
    src = os.path.join(GAME, "history", "units", name)
    if not os.path.exists(src):
        print("skip", name)
        continue
    dst_dir = os.path.join(MOD, "history", "units")
    os.makedirs(dst_dir, exist_ok=True)
    text = io.open(src, encoding="utf-8-sig").read()
    import re as _re
    m = _re.search(r'division_template = \{\s*name = "Strelkovaya Diviziya".*?\n\}', text, _re.S)
    if m:
        body = """division_template = {
	name = "Strelkovaya Diviziya"
	division_names_group = SOV_INF_01

	regiments = {
		infantry = { x = 0 y = 0 }
		infantry = { x = 0 y = 1 }
		infantry = { x = 0 y = 2 }
		infantry = { x = 1 y = 0 }
		infantry = { x = 1 y = 1 }
		infantry = { x = 1 y = 2 }
		infantry = { x = 2 y = 0 }
		infantry = { x = 2 y = 1 }
		infantry = { x = 2 y = 2 }
		artillery = { x = 3 y = 0 }
		artillery = { x = 3 y = 1 }
		artillery = { x = 3 y = 2 }
	}
	support = {
		engineer = { x = 0 y = 0 }
		artillery = { x = 0 y = 1 }
		anti_air = { x = 0 y = 2 }
	}
}"""
        text = text[:m.start()] + body + text[m.end():]
    if "Universalnaya Diviziya" not in text:
        text = text.rstrip() + "\n" + TEMPLATE
    io.open(os.path.join(dst_dir, name), "w", encoding="utf-8-sig", newline="\n").write(text)
    print("patched", name)
