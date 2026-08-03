# -*- coding: utf-8 -*-
"""姫路市南部のエリア地図を実データから生成する。

データ源（いずれも OpenStreetMap／ODbL）
  rel.json    : 姫路市の行政境界（relation 900269 の member way 群）
  coast.json  : natural=coastline の way 群
  schools.json: 姫路市内の学校（amenity=school）

手順
  1. 行政境界の way を端点でつないで閉じたリングにする
  2. 海岸線をグリッド上に壁として描き、南端から塗りつぶして「海」を決める
     （日本の市町村境界は港湾区域・島しょを含めて海上に延びるため、
       行政境界だけでは陸地の形にならない）
  3. 陸地 = 海でない かつ 行政境界の内側
  4. 陸地の各セルを最近傍の小学校に割り当て、6エリア＋その他に集約
  5. エリアごとの輪郭を抽出して SVG のパスにする
出力
  map_geo.json : エリアごとの SVG パスと重心（バルーン位置）
"""
import json
import math
from collections import deque

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath

# ---------------------------------------------------------------- 設定
BBOX = dict(lon0=134.5550, lon1=134.7500, lat0=34.7480, lat1=34.8850)
NX = 900                      # 東西の分割数（1セル ≈ 20m）
BLUR = 2                      # 輪郭を滑らかにする箱ぼかしの半径（セル）
SIMPLIFY_M = 22               # パス簡略化の許容誤差（m）

GROUPS = {
    "himejinishi": ["八幡", "広畑", "広畑第二", "大津", "南大津", "大津茂",
                    "網干", "網干西", "勝原", "旭陽", "余部"],
    "takaoka":     ["高岡西", "高岡", "安室", "安室東", "青山"],
    "ekikita":     ["白鷺", "城西", "船場", "城東", "東", "城乾", "野里"],
    "ekiminami":   ["手柄", "城陽", "荒川"],
    "shikama":     ["飾磨", "英賀保", "津田", "高浜"],
    "shirahama":   ["糸引", "白浜", "妻鹿"],
}
ORDER = ["himejinishi", "takaoka", "ekikita", "ekiminami", "shikama", "shirahama"]

# OSMに小学校として登録がないものの代替座標（出所を明記する）
PROXY = {
    "白鷺":   (34.8349162, 134.6892797),   # 市立白鷺中学校（白鷺小中学校と同一敷地）
    "高岡西": (34.8487810, 134.6559320),   # 高岡西幼稚園（高岡西小学校に隣接）
}


# ------------------------------------------------------- 行政境界のリング化
def stitch(ways, tol=1e-6):
    """way の端点をつないで閉じたリングを作る。"""
    segs = [[(p["lon"], p["lat"]) for p in w["geometry"]] for w in ways]
    used = [False] * len(segs)
    rings = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        cur = list(segs[i])
        changed = True
        while changed:
            changed = False
            for j in range(len(segs)):
                if used[j]:
                    continue
                s = segs[j]
                if math.dist(cur[-1], s[0]) < tol:
                    cur += s[1:]; used[j] = True; changed = True
                elif math.dist(cur[-1], s[-1]) < tol:
                    cur += s[::-1][1:]; used[j] = True; changed = True
                elif math.dist(cur[0], s[-1]) < tol:
                    cur = s[:-1] + cur; used[j] = True; changed = True
                elif math.dist(cur[0], s[0]) < tol:
                    cur = s[::-1][:-1] + cur; used[j] = True; changed = True
        rings.append(cur)
    rings.sort(key=len, reverse=True)
    return rings


# --------------------------------------------------------------- 投影
LAT_MID = (BBOX["lat0"] + BBOX["lat1"]) / 2
KX = math.cos(math.radians(LAT_MID))          # 経度を緯度スケールに合わせる係数
M_PER_DEG = 111_320.0


def to_plane(lon, lat):
    """経度緯度 → 平面（度単位、東西を cos(lat) で縮める）"""
    return (lon - BBOX["lon0"]) * KX, (BBOX["lat1"] - lat)


PW = (BBOX["lon1"] - BBOX["lon0"]) * KX       # 平面での幅（度）
PH = (BBOX["lat1"] - BBOX["lat0"])            # 平面での高さ（度）
NY = int(round(NX * PH / PW))


def main():
    # ---- データ読み込み
    rel = json.load(open("rel.json", encoding="utf-8"))["elements"][0]
    ways = [m for m in rel["members"]
            if m["type"] == "way" and m.get("geometry") and m.get("role") != "label"]
    rings = stitch(ways)
    print(f"行政境界: way {len(ways)} → リング {len(rings)}（最大 {len(rings[0])} 点）")

    coast = json.load(open("coast.json", encoding="utf-8"))
    coast_ways = [[(p["lon"], p["lat"]) for p in w["geometry"]]
                  for w in coast["elements"] if w.get("geometry")]
    print(f"海岸線: way {len(coast_ways)} / 点 {sum(len(w) for w in coast_ways)}")

    sd = json.load(open("schools.json", encoding="utf-8"))
    schools = {}
    for e in sd["elements"]:
        t = e.get("tags", {}) or {}
        n = t.get("name") or ""
        if "小学校" not in n:
            continue
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if not c.get("lat"):
            continue
        base = n.replace("姫路市立", "").replace("市立", "").replace("小学校", "").strip()
        schools.setdefault(base, (c["lat"], c["lon"]))
    for k, v in PROXY.items():
        schools[k] = v
    name2group = {nm: g for g, names in GROUPS.items() for nm in names}
    missing = [nm for nm in name2group if nm not in schools]
    assert not missing, f"座標が無い学校: {missing}"
    print(f"学校: {len(schools)} 校（うち対象 {len(name2group)} 校）")

    # ---- グリッド
    xs = (np.arange(NX) + 0.5) / NX * PW
    ys = (np.arange(NY) + 0.5) / NY * PH
    GX, GY = np.meshgrid(xs, ys)
    print(f"グリッド {NX}×{NY}（1セル ≈ {PW / NX * M_PER_DEG:.0f}m）")

    # ---- 海岸線を壁として描く
    wall = np.zeros((NY, NX), bool)
    def draw_line(p, q):
        x0, y0 = p; x1, y1 = q
        c0, r0 = x0 / PW * NX, y0 / PH * NY
        c1, r1 = x1 / PW * NX, y1 / PH * NY
        n = int(max(abs(c1 - c0), abs(r1 - r0))) + 1
        cc = np.linspace(c0, c1, n * 2 + 2).astype(int)
        rr = np.linspace(r0, r1, n * 2 + 2).astype(int)
        ok = (cc >= 0) & (cc < NX) & (rr >= 0) & (rr < NY)
        wall[rr[ok], cc[ok]] = True
    for w in coast_ways:
        pl = [to_plane(lo, la) for lo, la in w]
        for a, b in zip(pl, pl[1:]):
            draw_line(a, b)
    # 壁を1セル太らせて隙間を防ぐ
    wall |= np.roll(wall, 1, 0) | np.roll(wall, -1, 0) | np.roll(wall, 1, 1) | np.roll(wall, -1, 1)
    print(f"海岸線の壁セル: {wall.sum():,}")

    # ---- 南端から塗りつぶして海を決める
    sea = np.zeros((NY, NX), bool)
    dq = deque()
    for c in range(NX):
        if not wall[NY - 1, c]:
            sea[NY - 1, c] = True; dq.append((NY - 1, c))
    while dq:
        r, c = dq.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            r2, c2 = r + dr, c + dc
            if 0 <= r2 < NY and 0 <= c2 < NX and not sea[r2, c2] and not wall[r2, c2]:
                sea[r2, c2] = True; dq.append((r2, c2))
    print(f"海セル: {sea.sum():,} / {NY * NX:,}")

    # ---- 行政境界の内側
    pts = np.column_stack([GX.ravel(), GY.ravel()])
    inside = np.zeros(NY * NX, bool)
    for ring in rings:
        pl = np.array([to_plane(lo, la) for lo, la in ring])
        inside |= MplPath(pl).contains_points(pts)
    inside = inside.reshape(NY, NX)
    land = inside & ~sea
    print(f"姫路市の陸地セル: {land.sum():,}")

    # ---- 最近傍の学校に割り当て
    keys = list(schools.keys())
    sx = np.array([to_plane(schools[k][1], schools[k][0])[0] for k in keys])
    sy = np.array([to_plane(schools[k][1], schools[k][0])[1] for k in keys])
    best = np.full((NY, NX), -1, np.int16)
    bestd = np.full((NY, NX), np.inf)
    for i in range(len(keys)):
        d = (GX - sx[i]) ** 2 + (GY - sy[i]) ** 2
        m = d < bestd
        bestd[m] = d[m]; best[m] = i
    gidx = {g: i for i, g in enumerate(ORDER)}
    grp = np.full((NY, NX), -1, np.int16)          # -1: その他
    for i, k in enumerate(keys):
        g = name2group.get(k)
        if g is not None:
            grp[best == i] = gidx[g]
    for g in ORDER:
        print(f"  {g:<12} {int(((grp == gidx[g]) & land).sum()):>8,} セル")

    # ---- 輪郭を抽出
    def box_blur(a, r):
        out = a.astype(float)
        for _ in range(2):
            k = np.ones(2 * r + 1) / (2 * r + 1)
            out = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, out)
            out = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, out)
        return out

    def rdp(pl, eps):
        """Ramer–Douglas–Peucker で点を間引く"""
        if len(pl) < 3:
            return pl
        a, b = np.array(pl[0]), np.array(pl[-1])
        ab = b - a
        L = np.hypot(*ab)
        P = np.array(pl)
        if L < 1e-12:
            d = np.hypot(*(P - a).T)
        else:
            d = np.abs(np.cross(np.tile(ab, (len(P), 1)), P - a)) / L
        i = int(np.argmax(d))
        if d[i] <= eps:
            return [pl[0], pl[-1]]
        return rdp(pl[:i + 1], eps)[:-1] + rdp(pl[i:], eps)

    eps = SIMPLIFY_M / M_PER_DEG
    out = {"viewBox": [0, 0, 1000, round(1000 * PH / PW, 1)], "areas": {}, "other": [],
           "sea": [], "meta": {}}
    SCALE = 1000.0 / PW

    def polys_of(mask):
        f = box_blur(mask & land, BLUR)
        cs = plt.contour(GX, GY, f, levels=[0.5])
        res = []
        for p in cs.get_paths():
            for poly in p.to_polygons():
                if len(poly) < 8:
                    continue
                area = 0.5 * abs(np.dot(poly[:, 0], np.roll(poly[:, 1], 1))
                                 - np.dot(poly[:, 1], np.roll(poly[:, 0], 1)))
                if area * (M_PER_DEG ** 2) < 40_000:       # 4万m²未満は捨てる
                    continue
                simp = rdp([tuple(q) for q in poly], eps)
                res.append([(round(x * SCALE, 1), round(y * SCALE, 1)) for x, y in simp])
        plt.close("all")
        return res

    def centroid_pct(polys):
        bigA, bx, by = 0, 0, 0
        for poly in polys:
            P = np.array(poly)
            a = 0.5 * (np.dot(P[:, 0], np.roll(P[:, 1], 1)) - np.dot(P[:, 1], np.roll(P[:, 0], 1)))
            if abs(a) > abs(bigA):
                bigA = a
                cx = np.sum((P[:, 0] + np.roll(P[:, 0], 1)) *
                            (P[:, 0] * np.roll(P[:, 1], 1) - np.roll(P[:, 0], 1) * P[:, 1])) / (6 * a)
                cy = np.sum((P[:, 1] + np.roll(P[:, 1], 1)) *
                            (P[:, 0] * np.roll(P[:, 1], 1) - np.roll(P[:, 0], 1) * P[:, 1])) / (6 * a)
                bx, by = cx, cy
        vbh = 1000 * PH / PW
        return round(bx / 1000 * 100, 1), round(by / vbh * 100, 1)

    for g in ORDER:
        polys = polys_of(grp == gidx[g])
        out["areas"][g] = {"paths": polys, "balloon": centroid_pct(polys)}
        print(f"  {g:<12} 図形 {len(polys)} / 点 {sum(len(p) for p in polys)} / "
              f"balloon {out['areas'][g]['balloon']}")

    out["other"] = polys_of(grp == -1)
    print(f"  other        図形 {len(out['other'])} / 点 {sum(len(p) for p in out['other'])}")

    # 海（描画用）
    f = box_blur(sea, BLUR)
    cs = plt.contour(GX, GY, f, levels=[0.5])
    seap = []
    for p in cs.get_paths():
        for poly in p.to_polygons():
            if len(poly) < 8:
                continue
            simp = rdp([tuple(q) for q in poly], eps * 2)
            seap.append([(round(x * SCALE, 1), round(y * SCALE, 1)) for x, y in simp])
    plt.close("all")
    out["sea"] = sorted(seap, key=len, reverse=True)[:3]
    print(f"  sea          図形 {len(out['sea'])}")

    out["meta"] = {
        "source": "OpenStreetMap (ODbL) — 行政境界 relation 900269 / natural=coastline / amenity=school",
        "bbox": BBOX, "grid": [NX, NY],
        "cell_m": round(PW / NX * M_PER_DEG, 1),
        "proxy": {k: "市立白鷺中学校（同一敷地）" if k == "白鷺" else "高岡西幼稚園（隣接）"
                  for k in PROXY},
    }
    json.dump(out, open("map_geo.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("\nmap_geo.json を書き出しました  viewBox =", out["viewBox"])


if __name__ == "__main__":
    main()
