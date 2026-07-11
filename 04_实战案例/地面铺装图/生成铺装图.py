#!/usr/bin/env python3
"""
实战案例 #4: 地面铺装图 + 面积统计工具

什么是地面铺装图？
- 显示地砖/地板的铺装方向、起铺点、材料
- 需要标注：材料名称、规格、铺装方向
- 重要：算面积算损耗

关键技术点：
- HATCH — 不同材料不同填充图案
- DIM — 铺装间距
- TEXT — 材料标注
- AREA — 面积计算

图层：
- A-FLOR 地面线
- A-HATC 填充
- A-DIM 标注
- A-TEXT 文字
"""

import os
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/地面铺装图'
os.makedirs(OUT, exist_ok=True)

# =============================================
# 户型数据 (沿用8000x8500)
# =============================================
W, H = 8000, 8500

# 各区域地面材料
# ┌─────────────────────────────┐
# │  主卧                     │
# │  实木地板 450×900"         │
# ├────────┬──────────────────┤
# │  过道  │  卫生间            │
# │ 地砖   │  防滑砖            │
# │ 800×800│  300×300           │
# ├────────┴──────────────────┤
# │  客厅+餐厅                 │
# │  通铺地砖 800×800        │
# │  工字铺 / 对缝           │
# │               ┌───────────┤
# │               │  厨房       │
# │               │  防滑地砖   │
# │               │  600×600   │
# └───────────────┴───────────┘

# 区域坐标 (mm)
ZONES = {
    '客厅餐厅': {'x': 0, 'y': 0, 'w': 8000, 'h': 5000, 'mat': '800×800地砖', 'note': '工字铺'},
    '厨房': {'x': 5000, 'y': 0, 'w': 3000, 'h': 2000, 'mat': '600×600防滑砖', 'note': '十字铺'},
    '过道': {'x': 3000, 'y': 5000, 'w': 1500, 'h': 3500, 'mat': '800×800地砖', 'note': '与客厅对缝'},
    '卫生间': {'x': 4500, 'y': 5000, 'w': 2000, 'h': 3500, 'mat': '300×300防滑砖', 'note': '坡度找坡'},
    '主卧': {'x': 3000, 'y': 5000, 'w': 1500, 'h': 3500, 'mat': '450×900实木地板', 'note': '鱼骨铺'},
    '储物': {'x': 0, 'y': 5000, 'w': 3000, 'h': 3500, 'mat': '800×800地砖', 'note': ''},
}

# =============================================
# 1. 面积统计工具（纯 Python）
# =============================================

def calc_area(zones):
    """计算各区域面积和总材料用量"""
    print("\n====== 面积统计 ======")
    total = 0
    for name, z in sorted(zones.items()):
        area_m2 = (z['w'] * z['h']) / 1_000_000  # mm² → m²
        loss = 1.05 if '地砖' in z['mat'] else 1.03  # 瓷砖5%损耗，木地板3%
        need = area_m2 * loss
        total += area_m2
        print(f"  {name:8s}: {z['w']/1000:.1f}m×{z['h']/1000:.1f}m = {area_m2:.2f}m²")
        print(f"          材料: {z['mat']:20s} 含损耗 {need:.2f}m²")
    
    print(f"  ──────────────────────────")
    print(f"  总面积: {total:.2f}m²")
    print(f"  含损耗总计: {total*1.04:.2f}m²")
    return total

area = calc_area(ZONES)
print(f"\n  📊 建议采购:")
for name, z in sorted(ZONES.items()):
    area_m2 = (z['w'] * z['h']) / 1_000_000
    loss = 1.05 if '地砖' in z['mat'] else 1.03
    need = area_m2 * loss
    # 算砖数
    import re
    if '×' in z['mat']:
        nums = re.findall(r'\d+', z['mat'])
        if len(nums) >= 2:
            sz1, sz2 = int(nums[0]), int(nums[1])
            tiles_per_m2 = 1_000_000 / (sz1 * sz2)
            tiles_needed = area_m2 * loss * tiles_per_m2
            print(f"  {name}: {z['mat']} → 约{int(tiles_needed)}片（{need:.2f}m²）")

# =============================================
# 2. DXF 生成
# =============================================

def ent(layer, dtype, **kw):
    parts = [f'0\n{dtype}', f'8\n{layer}']
    gc = {'x1':10,'y1':20,'x2':11,'y2':21,'x':10,'y':20,'r':40,'h':40,'txt':1,'cx':10,'cy':20}
    for k, v in kw.items():
        code = gc.get(k)
        if code is not None:
            parts.append(f'{code}\n{v}')
    return '\n'.join(parts)

entities = []
layers = [
    "0\nLAYER\n2\nA-FLOR\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-HATC\n70\n0\n62\n8\n6\nCONTINUOUS\n370\n9",
    "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-AREA\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13",
]

# 外墙
entities.append(ent('A-FLOR', 'LINE', x1=0, y1=0, x2=W, y2=0))
entities.append(ent('A-FLOR', 'LINE', x1=W, y1=0, x2=W, y2=H))
entities.append(ent('A-FLOR', 'LINE', x1=W, y1=H, x2=0, y2=H))
entities.append(ent('A-FLOR', 'LINE', x1=0, y1=H, x2=0, y2=0))

# 内墙分割
entities.append(ent('A-FLOR', 'LINE', x1=0, y1=5000, x2=8000, y2=5000))
entities.append(ent('A-FLOR', 'LINE', x1=3000, y1=5000, x2=3000, y2=8500))
entities.append(ent('A-FLOR', 'LINE', x1=4500, y1=5000, x2=4500, y2=8500))
entities.append(ent('A-FLOR', 'LINE', x1=5000, y1=0, x2=5000, y2=2000))

# 面积文字
for name, z in ZONES.items():
    area_m2 = (z['w'] * z['h']) / 1_000_000
    txt = f'{name}: {area_m2:.1f}m²'
    cx = z['x'] + z['w']//2
    cy = z['y'] + z['h']//2
    entities.append(ent('A-TEXT', 'TEXT', x=cx-600, y=cy+100, h=3, txt=txt))
    entities.append(ent('A-TEXT', 'TEXT', x=cx-600, y=cy-50, h=2.5, txt=z['mat']))

# 材料标注
mat_texts = [
    (0, 0, '800×800地砖'),
    (0, -200, '通铺 全屋对缝'),
    (5000, 800, '厨房'),
    (5000, 600, '600×600防滑砖'),
    (0, 6500, '过道'),
    (0, 6300, '800×800地砖'),
    (4500, 6500, '卫生间'),
    (4500, 6300, '300×300防滑砖'),
    (3000, 6500, '主卧'),
    (3000, 6300, '450×900实木地板'),
]
for x, y, txt in mat_texts:
    entities.append(ent('A-TEXT', 'TEXT', x=x, y=y, h=3, txt=txt))

dxf_lines = [
    "0\nSECTION\n2\nHEADER\n0\nENDSEC",
    "0\nSECTION\n2\nTABLES",
    "0\nTABLE\n2\nLAYER\n70\n5",
]
dxf_lines.extend(layers)
dxf_lines.append("0\nENDTAB\n0\nENDSEC")
dxf_lines.append("0\nSECTION\n2\nENTITIES")
dxf_lines.extend(entities)
dxf_lines.append("0\nENDSEC\n0\nEOF")

dxf_path = f'{OUT}/地面铺装图.dxf'
with open(dxf_path, 'w') as f:
    f.write('\n'.join(dxf_lines))
print(f"\n✅ DXF: {dxf_path}")

# =============================================
# 3. SVG 可视化
# =============================================

dwg = Drawing(f'{OUT}/地面铺装图.svg', size=('900px', '700px'))
dwg.add(dwg.rect(insert=(0,0), size=(900,700), fill='#f8f8f8'))

SC = 0.08
def tx(x): return x * SC + 80
def ty(y): return 620 - (y * SC + 30)

# 网格
for x in range(0, W+1, 1000):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(H)), stroke='#eee', stroke_width=0.3))
for y in range(0, H+1, 1000):
    dwg.add(dwg.line((tx(0), ty(y)), (tx(W), ty(y)), stroke='#eee', stroke_width=0.3))

# 填充各区域（不同颜色表示不同材料）
zone_colors = {
    '客厅餐厅': '#f5e6d0',
    '厨房': '#e8e0d0',
    '过道': '#f5e6d0',
    '卫生间': '#d0d8e8',
    '主卧': '#d8c8a0',
    '储物': '#f0e8e0',
}
for name, z in ZONES.items():
    color = zone_colors.get(name, '#eee')
    dwg.add(dwg.rect(insert=(tx(z['x']), ty(z['y']+z['h'])), 
              size=(z['w']*SC, z['h']*SC), fill=color, stroke='#999', stroke_width=0.8))

# 铺装纹理示意（画一些网格线模拟砖缝）
# 客厅餐厅 800×800 砖缝
for x in range(0, 8001, 800):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(5000)), stroke='#ddc', stroke_width=0.5))
for y in range(0, 5001, 800):
    dwg.add(dwg.line((tx(0), ty(y)), (tx(8000), ty(y)), stroke='#ddc', stroke_width=0.5))

# 厨房 600×600
for x in range(5000, 8001, 600):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(2000)), stroke='#ccc', stroke_width=0.4))
for y in range(0, 2001, 600):
    dwg.add(dwg.line((tx(5000), ty(y)), (tx(8000), ty(y)), stroke='#ccc', stroke_width=0.4))

# 卫生间 300×300 
for x in range(4500, 6501, 300):
    dwg.add(dwg.line((tx(x), ty(5000)), (tx(x), ty(8500)), stroke='#bbd', stroke_width=0.3))
for y in range(5000, 8501, 300):
    dwg.add(dwg.line((tx(4500), ty(y)), (tx(6500), ty(y)), stroke='#bbd', stroke_width=0.3))

# 木地板 450×900 鱼骨铺（画斜线示意）
import math
for start_x in range(3000, 4501, 450):
    for start_y in range(5000, 8501, 900):
        off = (start_x - 3000) * 2 % 900
        y_off = off * 200 / 900
        dwg.add(dwg.line((tx(start_x), ty(start_y+500)), (tx(start_x+400), ty(start_y+500-100)), 
                  stroke='#ba9', stroke_width=0.4))
        dwg.add(dwg.line((tx(start_x), ty(start_y+500)), (tx(start_x+400), ty(start_y+500+100)), 
                  stroke='#ba9', stroke_width=0.4))

# 铺装方向箭头（客厅）
dwg.add(dwg.polyline([(tx(1500), ty(100)), (tx(1800), ty(100)), (tx(1650), ty(80)),
                       (tx(1800), ty(100)), (tx(1650), ty(120))],
               fill='none', stroke='#888', stroke_width=1))
dwg.add(dwg.text('铺装方向→', insert=(tx(1300), ty(95)), font_size='8', fill='#888'))

# 区域标签
for name, z in ZONES.items():
    cx = z['x'] + z['w']//2
    cy = z['y'] + z['h']//2
    area_m2 = (z['w'] * z['h']) / 1_000_000
    dwg.add(dwg.text(name, insert=(tx(cx), ty(cy+50)), font_size='12', fill='#444', text_anchor='middle', font_weight='bold'))
    dwg.add(dwg.text(z['mat'], insert=(tx(cx), ty(cy-10)), font_size='9', fill='#888', text_anchor='middle'))
    dwg.add(dwg.text(f'{area_m2:.1f}m²', insert=(tx(cx), ty(cy-25)), font_size='8', fill='#666', text_anchor='middle'))

# 图例
leg = 80
for color, label in [('#f5e6d0', '地砖'), ('#d8c8a0', '木地板'), ('#d0d8e8', '防滑砖')]:
    dwg.add(dwg.rect(insert=(leg, 660), size=(14, 12), fill=color, stroke='#999', stroke_width=0.5))
    dwg.add(dwg.text(label, insert=(leg+18, 670), font_size='9'))
    leg += 120

dwg.add(dwg.text('地面铺装图 | 材料+面积+铺装方向',
          insert=(450, 30), font_size='14', font_weight='bold', text_anchor='middle'))

dwg.save()
print(f"✅ SVG: {OUT}/地面铺装图.svg")
os.system(f'magick convert "{OUT}/地面铺装图.svg" "{OUT}/地面铺装图.png" 2>/dev/null')
print(f"✅ PNG: {OUT}/地面铺装图.png")

# 项目信息
info = f"""# 地面铺装图 — 项目信息

## 各区域材料
| 区域 | 面积 | 材料 | 铺贴方式 | 需砖数 |
|------|------|------|---------|-------|
"""
for name, z in sorted(ZONES.items()):
    area_m2 = (z['w'] * z['h']) / 1_000_000
    loss = 1.05 if '地砖' in z['mat'] else 1.03
    need = area_m2 * loss
    sz = z['mat'].split('×')
    if len(sz) >= 2:
        try:
            s1, s2 = int(sz[0]), int(sz[1].split()[0])
            tiles = int(need / (s1*s2) * 1_000_000)
        except:
            tiles = 0
    info += f"| {name} | {area_m2:.1f}m² | {z['mat']} | {z['note']} | ~{tiles}片 |\n"

info += f"""
## 总面积: {area:.2f}m²
## 损耗率: 瓷砖5%, 木地板3%
## 总面积含损耗: {area*1.04:.2f}m²
"""
with open(f'{OUT}/项目信息.md', 'w') as f:
    f.write(info)
print(f"✅ 项目信息: {OUT}/项目信息.md")
print(f"\n📋 地面铺装图+面积统计 完成！")
