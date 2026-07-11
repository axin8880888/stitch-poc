#!/usr/bin/env python3
"""
实战案例 #3: 天花图（吊顶图）

什么是天花图？
- 也叫"天棚图"、"吊顶布置图"
- 从天花板往下看的投影图（镜像）
- 包含：吊顶造型、标高、灯具、空调口、检修口
- 在装修中与平面图同等重要

关键命令：
- PLINE — 画吊顶轮廓
- OFFSET — 吊顶跌级（多层落差）
- HATCH — 不同吊顶区域用不同填充区分
- DIM — 标注标高
- TEXT — 标注材质

图层：
- A-CEIL 吊顶造型
- A-LITE 灯具
- A-AC 空调口
- A-HATC 填充
"""

import os
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/天花图'
os.makedirs(OUT, exist_ok=True)

# =============================================
# 户型（沿用住宅改造的8000x8500）
# 修改：现在布置的是从上面看的"天花板"
# =============================================
W, H = 8000, 8500

# 区域定义（天花图视角）
# ┌─────────────────────────────┐
# │  主卧吊顶         │  储物   │  CL=2800mm
# │  平顶+石膏线      │  平顶    │
# ├────────┬──────────┤         │
# │  过道  │  卫生间   │         │
# │ 跌级顶 │ 防水石膏板│         │
# ├────────┴──────────┴─────────┤
# │  客厅+餐厅 跌级吊顶         │  CL=2700mm
# │  ⭐ 主灯位置   筒灯○        │
# │               ┌───────────┤
# │               │  厨房       │  防水石膏板
# │               │  ⭐ 吸顶灯  │  CL=2600mm
# └───────────────┴───────────┘

# =============================================
# DXF 生成
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
    "0\nLAYER\n2\nA-CEIL\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-CEIL-D\n70\n0\n62\n2\n6\nDASHED\n370\n9",
    "0\nLAYER\n2\nA-LITE\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-AC\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-HATC\n70\n0\n62\n8\n6\nCONTINUOUS\n370\n9",
    "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
]

# --- 吊顶轮廓 (A-CEIL) ---
# 客厅+餐厅 跌级吊顶外框 (3000x4000 的区域，四周吊顶)
# 吊顶从四周向内300mm开始
living_top = 5000  # 客厅区域顶边
living_bottom = 0
living_left = 500
living_right = 7500

# 客厅跌级吊顶 - 外轮廓
entities.append(ent('A-CEIL', 'LINE', x1=living_left, y1=living_bottom+300, x2=living_right, y2=living_bottom+300))
entities.append(ent('A-CEIL', 'LINE', x1=living_right, y1=living_bottom+300, x2=living_right, y2=living_top-300))
entities.append(ent('A-CEIL', 'LINE', x1=living_right, y1=living_top-300, x2=living_left, y2=living_top-300))
entities.append(ent('A-CEIL', 'LINE', x1=living_left, y1=living_top-300, x2=living_left, y2=living_bottom+300))

# 吊顶内轮廓（跌级落差线）
entities.append(ent('A-CEIL-D', 'LINE', x1=living_left+100, y1=living_bottom+400, x2=living_right-100, y2=living_bottom+400))
entities.append(ent('A-CEIL-D', 'LINE', x1=living_right-100, y1=living_bottom+400, x2=living_right-100, y2=living_top-400))
entities.append(ent('A-CEIL-D', 'LINE', x1=living_right-100, y1=living_top-400, x2=living_left+100, y2=living_top-400))
entities.append(ent('A-CEIL-D', 'LINE', x1=living_left+100, y1=living_top-400, x2=living_left+100, y2=living_bottom+400))

# 卫生间防水石膏板
entities.append(ent('A-CEIL', 'LINE', x1=4500, y1=5000, x2=6500, y2=5000))
entities.append(ent('A-CEIL', 'LINE', x1=6500, y1=5000, x2=6500, y2=8500))
entities.append(ent('A-CEIL', 'LINE', x1=6500, y1=8500, x2=4500, y2=8500))
entities.append(ent('A-CEIL', 'LINE', x1=4500, y1=8500, x2=4500, y2=5000))

# 主卧平顶
entities.append(ent('A-CEIL', 'LINE', x1=3000, y1=5000, x2=3000, y2=8500))
entities.append(ent('A-CEIL', 'LINE', x1=3000, y1=8500, x2=4500, y2=8500))

# 厨房吊顶
entities.append(ent('A-CEIL', 'LINE', x1=5000, y1=0, x2=8000, y2=0))
entities.append(ent('A-CEIL', 'LINE', x1=8000, y1=0, x2=8000, y2=2000))
entities.append(ent('A-CEIL', 'LINE', x1=8000, y1=2000, x2=5000, y2=2000))

# --- 灯具 (A-LITE) ---
# 主灯 (客厅中央)
entities.append(ent('A-LITE', 'CIRCLE', cx=4000, cy=2500, r=200))
entities.append(ent('A-LITE', 'CIRCLE', cx=4000, cy=2500, r=100))
# 餐厅吊灯
entities.append(ent('A-LITE', 'CIRCLE', cx=4000, cy=4000, r=150))
entities.append(ent('A-LITE', 'CIRCLE', cx=4000, cy=4000, r=75))
# 🏠 筒灯 (客厅四周)
for lx, ly in [(700, 700), (7300, 700), (7300, 4700), (700, 4700)]:
    entities.append(ent('A-LITE', 'CIRCLE', cx=lx, cy=ly, r=50))
# 卧室吸顶灯
entities.append(ent('A-LITE', 'CIRCLE', cx=3750, cy=6700, r=120))
# 厨房吸顶灯
entities.append(ent('A-LITE', 'CIRCLE', cx=6500, cy=1000, r=100))
# 卫生间浴霸
entities.append(ent('A-LITE', 'CIRCLE', cx=5500, cy=7000, r=150))
entities.append(ent('A-LITE', 'CIRCLE', cx=5500, cy=7000, r=80))

# --- 空调/排风 (A-AC) ---
# 客厅空调出风口
entities.append(ent('A-AC', 'LINE', x1=4000-600, y1=living_top-200, x2=4000+600, y2=living_top-200, x3=0, y3=0))
entities.append(ent('A-AC', 'LINE', x1=4000-600, y1=living_top-200, x2=4000+600, y2=living_top-200))
entities.append(ent('A-AC', 'LINE', x1=4000-600, y1=living_top-200, x2=4000+600, y2=living_top-200))

# 简化为LINE
entities.append(ent('A-AC', 'LINE', x1=3400, y1=4750, x2=4600, y2=4750))

# --- 标高标注 ---
entities.append(ent('A-DIM', 'LINE', x1=300, y1=5000, x2=300, y2=5300))
entities.append(ent('A-DIM', 'LINE', x1=300, y1=5300, x2=250, y2=5300))

# --- 文字 ---
texts = [
    (4000, 2500, 'LED主灯 CL=2850'),
    (4000, 3800, '餐厅吊灯 CL=2500'),
    (4000, 1400, '跌级吊顶 CL=2700'),
    (5500, 7200, '浴霸'),
    (6500, 800, '吸顶灯'),
    (3700, 6800, '吸顶灯 CL=2850'),
    (3000, 5700, '阳角线'),
    (4000, 5200, '石膏板平顶 CL=2850'),
    (5500, 6500, '防水石膏板 CL=2800'),
    (6500, 1200, '铝扣板吊顶 CL=2600'),
]
for x, y, txt in texts:
    entities.append(ent('A-TEXT', 'TEXT', x=x-500, y=y, h=3, txt=txt))

# 简图框
entities.append(ent('A-CEIL', 'LINE', x1=0, y1=0, x2=W, y2=0))
entities.append(ent('A-CEIL', 'LINE', x1=W, y1=0, x2=W, y2=H))
entities.append(ent('A-CEIL', 'LINE', x1=W, y1=H, x2=0, y2=H))
entities.append(ent('A-CEIL', 'LINE', x1=0, y1=H, x2=0, y2=0))

dxf_lines = [
    "0\nSECTION\n2\nHEADER\n0\nENDSEC",
    "0\nSECTION\n2\nTABLES",
    "0\nTABLE\n2\nLAYER\n70\n7",
]
dxf_lines.extend(layers)
dxf_lines.append("0\nENDTAB\n0\nENDSEC")
dxf_lines.append("0\nSECTION\n2\nENTITIES")
dxf_lines.extend(entities)
dxf_lines.append("0\nENDSEC\n0\nEOF")

dxf_path = f'{OUT}/天花布置图.dxf'
with open(dxf_path, 'w') as f:
    f.write('\n'.join(dxf_lines))
print(f"✅ DXF: {dxf_path}")

# =============================================
# SVG 可视化
# =============================================

dwg = Drawing(f'{OUT}/天花布置图.svg', size=('900px', '700px'))
dwg.add(dwg.rect(insert=(0,0), size=(900,700), fill='#f8f8f8'))

SC = 0.08
def tx(x): return x * SC + 80
def ty(y): return 620 - (y * SC + 30)

# 网格
for x in range(0, W+1, 1000):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(H)), stroke='#eee', stroke_width=0.3))
for y in range(0, H+1, 1000):
    dwg.add(dwg.line((tx(0), ty(y)), (tx(W), ty(y)), stroke='#eee', stroke_width=0.3))

# 不同吊顶区域填充
ceil_zones = [
    # 客厅跌级吊顶区
    (500, 300, 7500-500, 5000-600, '#f0f0f0', '跌级吊顶 CL=2700'),
    # 客厅中心原顶
    (600, 400, 7500-1000, 5000-800, '#fafafa', ''),
    # 卫生间
    (4500, 5000, 2000, 3500, '#e8f0f8', '防水石膏板 CL=2800'),
    # 主卧
    (3000, 5000, 1500, 2000, '#f8f8f0', ''),
    # 储物 / 过道
    (3000, 5000, 1500, 3500, '#f8f8f0', '平顶 CL=2850'),
    # 厨房
    (5000, 0, 3000, 2000, '#f0f8e8', '铝扣板 CL=2600'),
]

for rx, ry, rw, rh, color, label in ceil_zones:
    dwg.add(dwg.rect(insert=(tx(rx), ty(ry+rh)), size=(rw*SC, rh*SC), 
              fill=color, stroke='#ccc', stroke_width=0.5, fill_opacity=0.7))

# 吊顶轮廓 (实线)
ceil_lines = [
    (500, 300, 7500, 300, '#000', 2),
    (7500, 300, 7500, 4700, '#000', 2),
    (7500, 4700, 500, 4700, '#000', 2),
    (500, 4700, 500, 300, '#000', 2),
    # 跌级内线 (虚线)
    (600, 400, 7400, 400, '#888', 1.5),
    (7400, 400, 7400, 4600, '#888', 1.5),
    (7400, 4600, 600, 4600, '#888', 1.5),
    (600, 4600, 600, 400, '#888', 1.5),
    # 卫生间
    (4500, 5000, 6500, 5000, '#000', 2),
    (6500, 5000, 6500, 8500, '#000', 2),
    (6500, 8500, 4500, 8500, '#000', 2),
    (4500, 8500, 4500, 5000, '#000', 2),
    # 主卧
    (3000, 5000, 3000, 8500, '#000', 2),
    # 厨房
    (5000, 0, 8000, 0, '#000', 2),
    (8000, 0, 8000, 2000, '#000', 2),
    (8000, 2000, 5000, 2000, '#000', 2),
    # 房间框
    (0, 0, 8000, 0, '#ccc', 1),
    (8000, 0, 8000, 8500, '#ccc', 1),
    (8000, 8500, 0, 8500, '#ccc', 1),
    (0, 8500, 0, 0, '#ccc', 1),
]

for x1, y1, x2, y2, color, w in ceil_lines:
    dash = '5,3' if color == '#888' else 'none'
    dash_arr = '5,3' if color == '#888' else ''
    kwargs = {'stroke': color, 'stroke_width': w}
    if dash_arr:
        kwargs['stroke_dasharray'] = dash_arr
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), **kwargs))

# 灯具
lights = [
    (4000, 2500, 16, '#ffdd00', 'LED主灯'), 
    (4000, 4000, 12, '#ffdd00', '吊灯'),
    (700, 700, 5, '#ffcc00', '筒灯'),
    (7300, 700, 5, '#ffcc00', '筒灯'),
    (7300, 4700, 5, '#ffcc00', '筒灯'),
    (700, 4700, 5, '#ffcc00', '筒灯'),
    (3700, 6800, 10, '#ffdd00', '吸顶灯'),
    (6500, 1000, 9, '#ffdd00', '吸顶灯'),
    (5500, 7000, 12, '#ffaa00', '浴霸'),
]
for lx, ly, r, color, label in lights:
    dwg.add(dwg.circle(center=(tx(lx), ty(ly)), r=r, fill=color, stroke='#cc9900', stroke_width=1))
    # 内圈
    dwg.add(dwg.circle(center=(tx(lx), ty(ly)), r=r//2, fill='white', fill_opacity=0.5))

# 空调出风口
dwg.add(dwg.rect(insert=(tx(3400), ty(4750)), size=(1200*SC, 15), fill='#aaddff', stroke='#4488cc', stroke_width=1))
dwg.add(dwg.text('空调出风口', insert=(tx(4000), ty(4770)), font_size='7', fill='#4488cc', text_anchor='middle'))

# 标高标注
dwg.add(dwg.text('CL=2700', insert=(tx(500), ty(2600+1500)), font_size='9', fill='green'))
dwg.add(dwg.text('CL=2850', insert=(tx(3000+750), ty(5000+1700)), font_size='9', fill='green'))
dwg.add(dwg.text('CL=2800', insert=(tx(5500), ty(5000+1700)), font_size='9', fill='green'))
dwg.add(dwg.text('CL=2600', insert=(tx(6500), ty(1000)), font_size='9', fill='green'))
dwg.add(dwg.text('CL=2850', insert=(tx(3700), ty(6800)), font_size='9', fill='green'))

# 区域文字
zone_texts = [
    (4000, 2000, '跌级吊顶区域'),
    (4000, 1800, '四周下降150mm'),
    (5500, 6500, '防水石膏板'),
    (5500, 6300, '防潮处理'),
    (6500, 800, '铝扣板300×300'),
    (3700, 7800, '石膏板平顶'),
    (500, 7800, '过道平顶'),
]
for x, y, txt in zone_texts:
    dwg.add(dwg.text(txt, insert=(tx(x), ty(y)), font_size='9', fill='#555', text_anchor='middle'))

# 图例
legend_x = 80
for color, label in [('#000', '吊顶轮廓'), ('#888', '跌级边线'), 
                      ('#ffcc00', '灯具'), ('#aaddff', '空调口')]:
    dwg.add(dwg.rect(insert=(legend_x, 660), size=(14, 12), fill=color))
    dwg.add(dwg.text(label, insert=(legend_x+18, 670), font_size='9'))
    legend_x += 140

dwg.add(dwg.text('天花布置图 | 从下往上看 | CL=标高(距地高度)',
          insert=(450, 30), font_size='14', font_weight='bold', text_anchor='middle'))

dwg.save()
print(f"✅ SVG: {OUT}/天花布置图.svg")
os.system(f'magick convert "{OUT}/天花布置图.svg" "{OUT}/天花布置图.png" 2>/dev/null')
print(f"✅ PNG: {OUT}/天花布置图.png")

# 项目信息
info = f"""# 天花布置图 — 项目信息

## 基本信息
- 项目：住宅改造天花图
- 户型：8000×8500 两室一厅
- 设计范围：全屋吊顶布置

## 各区域吊顶方案
| 区域 | 吊顶类型 | 标高(CL) | 说明 |
|------|---------|---------|------|
| 客厅 | 跌级吊顶 | 2700mm | 四周下降150mm, 中间原顶 |
| 餐厅 | 跌级吊顶 | 2700mm | 吊灯位CL=2500 |
| 主卧 | 石膏板平顶 | 2850mm | 石膏线收口 |
| 卫生间 | 防水石膏板 | 2800mm | 防潮处理 |
| 厨房 | 铝扣板 | 2600mm | 300×300扣板 |
| 过道 | 石膏板平顶 | 2850mm | |

## 灯具清单
- LED主灯 ×1（客厅）
- 吊灯 ×1（餐厅）
- LED筒灯 ×4（客厅四角）
- 吸顶灯 ×2（主卧/厨房）
- 浴霸 ×1（卫生间）

## 命令使用
- LINE — 吊顶轮廓
- OFFSET — 跌级内线
- CIRCLE — 灯具位置
- HATCH — 区域填充区分
- DIM — 标高标注
"""
with open(f'{OUT}/项目信息.md', 'w') as f:
    f.write(info)
print(f"✅ 项目信息: {OUT}/项目信息.md")
print(f"\n📋 天花图案例完成！")
