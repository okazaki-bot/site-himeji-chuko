# -*- coding: utf-8 -*-
"""姫路市エリア地図ブロックのHTMLを生成する。

参考サイト（himeji.cocoie.co.jp）と同じ情報構造・操作にするが、
SVGの作画・CSS・配色は自作。エリア名・小学校名は公的な地名。
件数はダミー（将来 物件管理システムから出力する）。

境界線（ポリライン）を先に定義し、各エリアをその区間の組み合わせで作る。
こうすると隣接エリアが必ず同じ辺を共有するので、隙間なく1つの市域になる。
"""

import json

GEO = json.load(open("map_geo.json", encoding="utf-8"))
VB = GEO["viewBox"]          # [0, 0, 1000, H]
VBH = VB[3]


AREAS = [
    dict(key="himejinishi", name="姫路西", color="#123a5c", tint="#dde6ee",
         counts=(263, 340, 107),
         schools=[("八幡小学校", 118), ("広畑小学校", 38), ("広畑第二小学校", 68),
                  ("大津小学校", 81), ("南大津小学校", 16), ("大津茂小学校", 35),
                  ("網干小学校", 86), ("網干西小学校", 61), ("勝原小学校", 105),
                  ("旭陽小学校", 68), ("余部小学校", 34)]),
    dict(key="takaoka", name="高岡・安室・青山", color="#96690f", tint="#f5ecd6",
         counts=(105, 170, 64),
         schools=[("高岡西小学校", 37), ("高岡小学校", 63), ("安室小学校", 83),
                  ("安室東小学校", 111), ("青山小学校", 45)]),
    dict(key="ekikita", name="駅北", color="#2f7d4f", tint="#e0efe5",
         counts=(61, 159, 50),
         schools=[("白鷺小学校", 45), ("城西小学校", 59), ("船場小学校", 34),
                  ("城東小学校", 23), ("東小学校", 15), ("城乾小学校", 66),
                  ("野里小学校", 28)]),
    dict(key="ekiminami", name="駅南", color="#b8562a", tint="#f7e6dc",
         counts=(50, 93, 32),
         schools=[("手柄小学校", 36), ("城陽小学校", 37), ("荒川小学校", 102)]),
    dict(key="shikama", name="飾磨", color="#6b4f8f", tint="#ebe4f3",
         counts=(53, 98, 36),
         schools=[("飾磨小学校", 64), ("英賀保小学校", 42), ("津田小学校", 50),
                  ("高浜小学校", 31)]),
    dict(key="shirahama", name="白浜", color="#1f7fb5", tint="#dfedf7",
         counts=(29, 78, 29),
         schools=[("糸引小学校", 70), ("白浜小学校", 53), ("妻鹿小学校", 13)]),
]

ICON = {
    "public": ('<svg class="cnt__ico" viewBox="0 0 24 24" aria-hidden="true">'
               '<path d="M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H10v6H4a1 1 0 0 1-1-1z"/></svg>'),
    "member": ('<svg class="cnt__ico" viewBox="0 0 24 24" aria-hidden="true">'
               '<path d="M7 10V8a5 5 0 0 1 10 0v2h1a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1zm2 0h6V8a3 3 0 0 0-6 0z"/></svg>'),
    "shop":   ('<svg class="cnt__ico" viewBox="0 0 24 24" aria-hidden="true">'
               '<path d="M4 4h16l1 5a3 3 0 0 1-3 3 3 3 0 0 1-3-2 3 3 0 0 1-3 2 3 3 0 0 1-3-2 3 3 0 0 1-3 2 3 3 0 0 1-3-3zm1 10h14v6a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z"/></svg>'),
}
LABEL = {"public": "一般公開", "member": "会員限定", "shop": "店頭のみ"}
KEYS = ["public", "member", "shop"]


def counts_html(a, cls):
    return "".join(
        f'<span class="{cls}__item">{ICON[k]}'
        f'<b data-count="{a["key"]}:{k}">{v}</b>'
        f'<span class="visually-hidden">{LABEL[k]}物件</span></span>'
        for k, v in zip(KEYS, a["counts"]))


def build():
    L = []
    w = L.append
    def d_of(polys):
        return " ".join("M " + " L ".join(f"{x},{y}" for x, y in poly) + " Z"
                        for poly in polys)

    geo = {}
    for a in AREAS:
        g = GEO["areas"][a["key"]]
        geo[a["key"]] = (d_of(g["paths"]), g["balloon"][0], g["balloon"][1])

    w('<!-- ========== S4-B 姫路市エリア地図（物件数をひと目で） ========== -->')
    w('<div class="areamap" id="areamap">')
    w('  <h3 class="areamap__title">姫路市のどこに、何件あるか</h3>')
    w('  <p class="areamap__lead measure">エリアをえらぶと、学区ごとの件数が出ます。'
      '会員限定・店頭のみの物件も、件数だけは先にお出しします。</p>')

    w('  <ul class="legend">')
    for k in KEYS:
        w(f'    <li class="legend__item">{ICON[k]}{LABEL[k]}物件</li>')
    w('    <li class="legend__item legend__item--outside">'
      '<span class="legend__swatch"></span>対応エリア外（姫路市北部ほか）</li>')
    w('  </ul>')

    w('  <div class="areamap__stage">')
    w(f'    <svg class="areamap__svg" viewBox="0 0 1000 {VBH:g}" role="img" '
      'aria-label="姫路市南部を6つのエリアに分けた地図。エリアごとの件数は、'
      'この下のエリア一覧でも同じ内容を確認できます。">')
    w('      <title>姫路市南部エリア地図</title>')
    # 海（natural=coastline から生成）
    for poly in GEO["sea"]:
        w('      <path class="areamap__sea" d="'
          + "M " + " L ".join(f"{x},{y}" for x, y in poly) + ' Z"/>')
    # 対応エリア外（姫路市の残りの部分）
    for poly in GEO["other"]:
        w('      <path class="areamap__outside" d="'
          + "M " + " L ".join(f"{x},{y}" for x, y in poly) + ' Z"/>')
    # 6エリア
    for a in AREAS:
        d, _, _ = geo[a["key"]]
        w(f'      <a href="#modal-{a["key"]}" class="areamap__region" '
          f'aria-label="{a["name"]}エリアの学区別件数をひらく">')
        w(f'        <path d="{d}" fill="{a["color"]}" fill-opacity=".82" '
          f'stroke="#ffffff" stroke-width="4" stroke-linejoin="round"/>')
        w('      </a>')
    w('    </svg>')

    for a in AREAS:
        _, cx, cy = geo[a["key"]]
        w(f'    <a class="balloon" href="#modal-{a["key"]}" '
          f'style="--c: {a["color"]}; left: {cx}%; top: {cy}%;">')
        w(f'      <span class="balloon__name">{a["name"]}<small>エリア</small></span>')
        w(f'      <span class="balloon__cnt">{counts_html(a, "balloon__cnt")}</span>')
        w('    </a>')
    w('  </div>')

    w('  <ul class="areacards">')
    for a in AREAS:
        total = sum(a["counts"])
        w(f'    <li class="areacard" style="--c: {a["color"]}">')
        w(f'      <a class="areacard__link" href="#modal-{a["key"]}">')
        w(f'        <span class="areacard__name">{a["name"]}<small>エリア</small></span>')
        w(f'        <span class="areacard__total">{total}<small>件</small></span>')
        w(f'        <span class="areacard__cnt">{counts_html(a, "areacard__cnt")}</span>')
        w(f'        <span class="areacard__more">{len(a["schools"])}校の学区別に見る</span>')
        w('      </a>')
        w('    </li>')
    w('  </ul>')

    w('  <p class="small areamap__note">'
      '件数はダミーです。物件管理システムと接続後、'
      '各数字（<code>data-count="エリア:区分"</code>）を差し替えます。<br>'
      '地図データ: <a href="https://www.openstreetmap.org/copyright" '
      'target="_blank" rel="noopener">&copy; OpenStreetMap contributors</a>（ODbL）。'
      '市域境界・海岸線は実データ、エリア区分は'
      f'小学校{sum(len(a["schools"]) for a in AREAS)}校の位置による最近傍分割で作成しています。'
      '姫路市が定める通学区域の境界とは一致しません。</p>')
    w('</div>')

    for a in AREAS:
        w(f'<div class="modal" id="modal-{a["key"]}" role="dialog" aria-modal="true" '
          f'aria-labelledby="modal-{a["key"]}-h">')
        w('  <a class="modal__bg" href="#areamap" aria-label="閉じる"></a>')
        w('  <div class="modal__panel">')
        w('    <a class="modal__close" href="#areamap" aria-label="閉じる">×</a>')
        w(f'    <p class="modal__h" id="modal-{a["key"]}-h" style="--c: {a["color"]}">'
          f'{a["name"]}エリア</p>')
        w(f'    <p class="modal__cnt">{counts_html(a, "modal__cnt")}</p>')
        w('    <ul class="modal__list">')
        for sname, scount in a["schools"]:
            w(f'      <li><a href="#">{sname}<b>({scount})</b></a></li>')
        w('    </ul>')
        w(f'    <a class="btn btn--primary btn--block" href="#">'
          f'{a["name"]}エリアのすべての物件を見る</a>')
        w('  </div>')
        w('</div>')

    return "\n".join(L), geo


if __name__ == "__main__":
    html, geo = build()
    open("map_block.html", "w", encoding="utf-8").write(html)
    tot = [sum(a["counts"][i] for a in AREAS) for i in range(3)]
    print(f"generated {len(html):,} chars")
    print(f"合計: 一般公開 {tot[0]} / 会員限定 {tot[1]} / 店頭のみ {tot[2]} / 総数 {sum(tot)}")
    for a in AREAS:
        _, cx, cy = geo[a["key"]]
        print(f"  {a['name']:<16} {str(a['counts']):<18} 計{sum(a['counts']):>4}  "
              f"{len(a['schools']):>2}校  balloon {cx}% / {cy}%")
