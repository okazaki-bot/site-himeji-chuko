# エリア地図の生成ツール

トップページの「姫路市のどこに、何件あるか」（S4-B）のSVGを、実データから生成します。

## データ源

すべて OpenStreetMap（**ODbL**）。生データはこのリポジトリに含めていないので、下記で取得してください。

```bash
# 1. 姫路市の行政境界（relation 900269）
printf '[out:json][timeout:180];\nrel(900269);\nout geom;\n' > qr.txt
curl -s -A "morishita-map/1.0" --data-urlencode "data@qr.txt" \
  https://overpass-api.de/api/interpreter -o rel.json

# 2. 海岸線（natural=coastline）
printf '[out:json][timeout:90];\nway["natural"="coastline"](34.72,134.50,34.86,134.78);\nout geom;\n' > qc.txt
curl -s -A "morishita-map/1.0" --data-urlencode "data@qc.txt" \
  https://overpass-api.de/api/interpreter -o coast.json

# 3. 姫路市内の学校（amenity=school）
printf '[out:json][timeout:60];\narea["name"="姫路市"]["boundary"="administrative"]->.a;\n(node(area.a)["amenity"="school"];way(area.a)["amenity"="school"];);\nout center tags;\n' > qs.txt
curl -s -A "morishita-map/1.0" --data-urlencode "data@qs.txt" \
  https://overpass-api.de/api/interpreter -o schools.json
```

## 生成

```bash
python3 build_map.py    # → map_geo.json（エリアのSVGパスとバルーン位置）
python3 gen_map.py      # → map_block.html（index.html に貼るブロック）
```

必要なもの: Python 3 ＋ numpy ＋ matplotlib（`scipy` / `shapely` は不要）。

## 地図の作り方

1. 行政境界の way を端点でつないで閉じたリングにする
2. 海岸線をグリッド（1セル約20m）に壁として描き、南端から塗りつぶして「海」を決める
   — **日本の市町村境界は港湾区域と島しょを含めて海上に延びるため、行政境界だけでは陸地の形にならない**
3. 陸地 = 海でない かつ 行政境界の内側
4. 陸地の各セルを最近傍の小学校に割り当て、6エリア＋その他に集約
5. エリアごとの輪郭を抽出し、Ramer–Douglas–Peucker（許容誤差22m）で間引いてSVGパスにする

## 精度についての注意

- **市域境界と海岸線は実データ**です（姫路港の埋立地・広畑・網干・妻鹿の形状を含む）
- **エリア区分は小学校33校の位置による最近傍分割（ボロノイ）** です。
  姫路市が定める通学区域の境界とは一致しません。正確な学区境界が必要な場合は、
  姫路市の通学区域データ（GIS）を入手して置き換えてください
- OSMに小学校として登録がない2校は代替座標を使っています（`build_map.py` の `PROXY`）
  - 白鷺 → 市立白鷺中学校（白鷺小中学校と同一敷地）
  - 高岡西 → 高岡西幼稚園（高岡西小学校に隣接）

## エリアや件数を変えるとき

- **件数**: `gen_map.py` の `AREAS[].counts` と `schools`。
  本番では物件管理システムから `data-count="エリアkey:区分"` の要素を書き換える運用にする
- **エリア区分**: `build_map.py` の `GROUPS`（学校名の割り当て）を変えて再生成
- **地図の範囲**: `build_map.py` の `BBOX`
