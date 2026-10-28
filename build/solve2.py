import io, os, json, importlib.util

spec = importlib.util.spec_from_file_location("gm", r"D:\AI_Tools\DSH\hoi4_sov\build\gen.py")
gm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gm)

ALL = gm.ALL
VAN = set(gm.VAN_POS.values())
byid = {f["id"]: f for f in ALL}

def positions():
    memo = {}
    def g(fid, seen=()):
        if fid in memo: return memo[fid]
        if fid in seen: return (0, 0)
        f = byid.get(fid)
        if f is None:
            v = gm.VAN_POS.get(fid, (0, 0))
        else:
            px, py = g(f["parent"], seen + (fid,)) if f["parent"] else (0, 0)
            v = (px + f["dx"], py + f["dy"])
        memo[fid] = v
        return v
    return {f["id"]: g(f["id"]) for f in ALL}

def conflicts():
    pos = positions()
    out = []
    items = sorted((xy[0], xy[1], fid) for fid, xy in pos.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[j][0] - items[i][0] >= 2:
                break
            if items[i][1] == items[j][1]:
                out.append((items[i][2], items[j][2]))
    for fid, xy in pos.items():
        if xy in VAN:
            out.append((fid, None))
    return out

for step in range(600):
    c = conflicts()
    if not c:
        break
    a, b = c[0]
    tgt = byid.get(b) or byid.get(a)
    tgt["dy"] += 1

print("conflicts left:", len(conflicts()))

# база без оверрайдов
ov_path = r"D:\AI_Tools\DSH\hoi4_sov\build\overrides.json"
json.dump({}, io.open(ov_path, "w", encoding="utf-8"))
spec2 = importlib.util.spec_from_file_location("gmb", r"D:\AI_Tools\DSH\hoi4_sov\build\gen.py")
gmb = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(gmb)
base = {f["id"]: (f["dx"], f["dy"]) for f in gmb.ALL}

delta = {}
for f in ALL:
    bx, by = base[f["id"]]
    if (f["dx"], f["dy"]) != (bx, by):
        delta[f["id"]] = [f["dx"] - bx, f["dy"] - by]
json.dump(delta, io.open(ov_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("overrides:", len(delta))
