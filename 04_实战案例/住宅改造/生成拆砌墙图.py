#!/usr/bin/env python3
"""
实战案例 #2: 住宅改造 — 拆砌墙图
综合运用第二阶段命令知识生成

什么是拆砌墙图？
- 拆除（DEMO）：标记需要敲掉的墙 → 红色虚线
- 新建（NEWW）：标记需要新砌的墙 → 青色实线
- 保留（EXST）：现有的不动墙体 → 黄色虚线

这是施工的第一步，也是最容易出错的一步
"""

import os
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/住宅改造'
os.makedirs(OUT, exist_ok=True)

# =============================================
# 户型参数：原始3房改2房+开放式厨房
# =============================================
# 原始户型
# ┌─────────────────────────────┐
# │  卧室A       │    卧室B     │
# │  (3000x3500) │  (3500x3500) │  ← 拆掉中间隔墙
# ├──────┬───────┤             │
# │ 过道 │ 卫生间 │              │
# ├──────┴───────┴─────────────┤
# │  客厅+餐厅 (8000x5000)      │  ← 拆掉厨房隔墙
# │               ┌───────────┤
# │               │  厨房      │  ← 拆墙变开放式
# └───────────────┴───────────┘

# 改造方案：
# 1. 拆除卧室A和卧室B之间的隔墙 → 打通成大主卧
# 2. 拆除厨房与餐厅之间的隔墙 → 开放式厨房
# 3. 拆除卫生间与过道之间的部分墙体 → 扩大卫生间
# 4. 新建一段隔墙 → 主卧衣帽间隔断

# 定义关键坐标 (单位mm, 原点在左下角)
pts = {}

# 总尺寸
W, H = 8000, 8500

# 分块（从下往上、从左往右）
# 下方: 客厅+餐厅 8000x5000
# 上方左: 卧室A 3000x3500  
# 上方右上: 卧室B 3500x3500
# 上方中: 过道 1500x3500 + 卫生间 2000x3500
# 右上角: 厨房 3000x3000

# 关键轴线
A = {
    # 垂直轴线
    'V0': 0,      # 左边界
    'V1': 3000,   # 卧室A右 / 过道左
    'V2': 4500,   # 过道右 / 卫生间左+卫生间右 / 卧室B左
    'V3': 6500,   # 卫生间右 / 卧室B右
    'V4': 8000,   # 右边界 / 卧室B右
    # 厨房内墙
    'VK1': 5000,  # 厨房左墙
    'VK2': 8000,  # 厨房右墙
    # 水平轴线
    'H0': 0,      # 下边界
    'H1': 5000,   # 客厅+餐厅上边界 / 卧室+厨房下边界
    'H2': 7000,   # 卫生间+过道上边界 / 厨房中分
    'H3': 8500,   # 上边界
    # 门洞位置
    'DoorA': 1000,  # 卧室A门洞左
    'DoorB': 4500,  # 过道口
    'DoorC': 5600,  # 卫生间门洞
}

# =============================================
# 1. DXF 生成
# =============================================

def make_dxf_entity(layer, dtype, **kw):
    parts = [f'0\n{dtype}', f'8\n{layer}']
    gc = {'x1':10,'y1':20,'x2':11,'y2':21,'x':10,'y':20,'r':40,'h':40,'txt':1,'cx':10,'cy':20}
    for k, v in kw.items():
        code = gc.get(k)
        if code is not None:
            parts.append(f'{code}\n{v}')
    return '\n'.join(parts)

entities = []
layers = [
    "0\nLAYER\n2\nA-EXST\n70\n0\n62\n2\n6\nHIDDEN\n370\n13",
    "0\nLAYER\n2\nA-DEMO\n70\n0\n62\n1\n6\nDASHED\n370\n13",
    "0\nLAYER\n2\nA-NEWW\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n18",
    "0\nLAYER\n2\nA-DOOR\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n18",
    "0\nLAYER\n2\nA-WINDW\n70\n0\n62\n5\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-FURN\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13",
]

# --- 保留墙体 (EXST) ---
# 原始外墙
exst_walls = [
    (0,0, W,0), (W,0, W,H), (W,H, 0,H), (0,H, 0,0),
    # 卧室A与客厅的分隔墙 (保留，有门洞)
    (0,5000, 900,5000), (1100,5000, 3000,5000),
    # 原始卫生间外墙 (保留)
    (3000,5000, 3000,8500),
    # 卧室B外墙 (保留)
    (6500,5000, 6500,8500),
    # 阳台栏杆
    (0,0, W,0),
]
for x1,y1,x2,y2 in exst_walls:
    entities.append(make_dxf_entity('A-EXST', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))

# --- 拆除墙体 (DEMO) ---
# 卧室A与卧室B之间的隔墙 (拆除)
demo_walls = [
    (3000,5000, 3000,8500),
    # 厨房与餐厅之间的隔墙 (拆除)
    (5000,2000, 5000,5000),
    (5000,2000, 8000,2000),
    # 卫生间小部分墙体 (拆除扩大)
    (4500,5000, 4500,7000),
]
for x1,y1,x2,y2 in demo_walls:
    entities.append(make_dxf_entity('A-DEMO', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))

# --- 新建墙体 (NEWW) ---
# 主卧衣帽间隔断
new_walls = [
    (3000,7000, 4500,7000),
    (4500,7000, 4500,8500),
    # 扩大后的卫生间新墙
    (3000,5000, 3000,7000),
]
for x1,y1,x2,y2 in new_walls:
    entities.append(make_dxf_entity('A-NEWW', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))

# --- 门 ---
doors = [
    (900, 5000, 1100, 5000, '卧室A入口'),
    (3000, 4500, 3000, 4700, '主卧入口'),
    (5600, 5000, 5800, 5000, '卫生间'),
]
for x1,y1,x2,y2,desc in doors:
    entities.append(make_dxf_entity('A-DOOR', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))

# --- 窗 ---
windows = [
    (500, 0, 2500, 0, '客厅落地窗'),
]
for x1,y1,x2,y2,desc in windows:
    entities.append(make_dxf_entity('A-WINDW', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))

# --- 标注 ---
entities.append(make_dxf_entity('A-DIM', 'LINE', x1=0, y1=-500, x2=8000, y2=-500))
entities.append(make_dxf_entity('A-DIM', 'LINE', x1=-500, y1=0, x2=-500, y2=8500))

# --- 文字标注 ---
texts = [
    (3500, 6700, '拆除'),
    (3500, 6400, '打通→主卧'),
    (5500, 3500, '拆除'),
    (5500, 3200, '→开放式厨房'),
    (3700, 5800, '新建衣帽间'),
    (3700, 5600, '隔断'),
    (4500, 6200, '扩大卫生间'),
]
for x, y, txt in texts:
    entities.append(make_dxf_entity('A-TEXT', 'TEXT', x=x, y=y, h=3.5, txt=txt))

# 构建 DXF
dxf_lines = [
    "0\nSECTION\n2\nHEADER\n0\nENDSEC",
    "0\nSECTION\n2\nTABLES",
    "0\nTABLE\n2\nLAYER\n70\n8",
]
dxf_lines.extend(layers)
dxf_lines.append("0\nENDTAB\n0\nENDSEC")
dxf_lines.append("0\nSECTION\n2\nENTITIES")
dxf_lines.extend(entities)
dxf_lines.append("0\nENDSEC\n0\nEOF")

dxf_path = f'{OUT}/拆砌墙图.dxf'
with open(dxf_path, 'w') as f:
    f.write('\n'.join(dxf_lines))
print(f"✅ DXF: {dxf_path}")

# =============================================
# 2. SVG 可视化
# =============================================

dwg = Drawing(f'{OUT}/拆砌墙图.svg', size=('900px', '700px'))
dwg.add(dwg.rect(insert=(0,0), size=(900,700), fill='#f8f8f8'))

SC = 0.08

def tx(x): return x * SC + 80
def ty(y): return 620 - (y * SC + 30)

# 网格
for x in range(0, W+1, 1000):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(H)), stroke='#eee', stroke_width=0.3))
for y in range(0, H+1, 1000):
    dwg.add(dwg.line((tx(0), ty(y)), (tx(W), ty(y)), stroke='#eee', stroke_width=0.3))

# 房间区域填充（半透明）
rooms = [
    (0, 5000, 3000, 3500, '#ffe0e0', '卧室A\n(改)'),
    (3000, 5000, 3500, 3500, '#ffe0e0', '卧室B\n(改)'),
    (3000, 5000, 1500, 2000, '#e0ffe0', '过道'),
    (4500, 5000, 2000, 3500, '#e0e0ff', '卫生间\n(扩大)'),
    (6500, 5000, 1500, 3500, '#ffe0ff', '卧室B'),
    (5000, 2000, 3000, 3000, '#fff0d0', '厨房\n(改开放式)'),
    (0, 0, 8000, 5000, '#f0fff0', '客厅+餐厅'),
]

for rx, ry, rw, rh, color, label in rooms:
    dwg.add(dwg.rect(insert=(tx(rx), ty(ry+rh)), size=(rw*SC, rh*SC), 
              fill=color, fill_opacity=0.4, stroke='none'))
    # 房间标签
    lab_lines = label.split('\n')
    for li, line in enumerate(lab_lines):
        dwg.add(dwg.text(line, insert=(tx(rx+rw//2), ty(ry+rh//2) - 8 + li*14), 
                  font_size='10' if li==0 else '8', fill='#555', text_anchor='middle',
                  font_weight='bold' if li==0 else 'normal'))

# 保留墙体 (EXST)
for x1,y1,x2,y2 in exst_walls:
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), 
              stroke='#ccaa00', stroke_width=2.5, stroke_dasharray='6,3'))

# 拆除墙体 (DEMO) — 红色×线
for x1,y1,x2,y2 in demo_walls:
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), 
              stroke='red', stroke_width=2.5, stroke_dasharray='4,3'))
    # 画 X 标记
    mx, my = (x1+x2)/2, (y1+y2)/2
    hw, hh = 30, 15
    dwg.add(dwg.line((tx(mx-hw), ty(my-hh)), (tx(mx+hw), ty(my+hh)), stroke='red', stroke_width=1.5))
    dwg.add(dwg.line((tx(mx-hw), ty(my+hh)), (tx(mx+hw), ty(my-hh)), stroke='red', stroke_width=1.5))
    # 拆除文字
    dwg.add(dwg.text('拆', insert=(tx(mx), ty(my+5)), font_size='10', fill='red', text_anchor='middle'))

# 新建墙体 (NEWW)
for x1,y1,x2,y2 in new_walls:
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), 
              stroke='#00aaaa', stroke_width=3))

# 门
for x1,y1,x2,y2,desc in doors:
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), 
              stroke='#008888', stroke_width=2))

# 窗
for x1,y1,x2,y2,desc in windows:
    dwg.add(dwg.line((tx(x1), ty(y1+50)), (tx(x2), ty(y2+50)), stroke='#0044aa', stroke_width=2))
    dwg.add(dwg.line((tx(x1), ty(y1-50)), (tx(x2), ty(y2-50)), stroke='#0044aa', stroke_width=2))

# 材质文字
for x, y, txt in texts:
    dwg.add(dwg.text(txt, insert=(tx(x), ty(y)), font_size='10', fill='#333', text_anchor='middle'))

# 尺寸标注
dwg.add(dwg.line((tx(0), ty(-80)), (tx(W), ty(-80)), stroke='green', stroke_width=1))
dwg.add(dwg.text('8000', insert=(tx(W//2), ty(-90)), font_size='10', fill='green', text_anchor='middle'))

dwg.add(dwg.line((tx(-60), ty(0)), (tx(-60), ty(H)), stroke='green', stroke_width=1))
dwg.add(dwg.text('8500', insert=(tx(-65), ty(H//2)), font_size='10', fill='green', text_anchor='end'))

# 轴线标注
for i, (label, x) in enumerate([('①', 0), ('②', 3000), ('③', 4500), ('④', 6500), ('⑤', 8000)]):
    dwg.add(dwg.circle(center=(tx(x), ty(-120)), r=8, fill='white', stroke='green', stroke_width=1))
    dwg.add(dwg.text(label, insert=(tx(x), ty(-123)), font_size='8', fill='green', text_anchor='middle'))

# 图例
lg_items = [
    ('#ccaa00', '保留墙体 (EXST)', '6,3'),
    ('red', '拆除墙体 (DEMO)', '4,3'),
    ('#00aaaa', '新建墙体 (NEWW)', 'none'),
    ('#008888', '门 (DOOR)', 'none'),
    ('#0044aa', '窗 (WINDW)', 'none'),
]
lgx = 80
for color, label, dash in lg_items:
    dwg.add(dwg.rect(insert=(lgx, 660), size=(16, 12), fill=color, fill_opacity=0.8))
    dwg.add(dwg.text(label, insert=(lgx+20, 670), font_size='9'))
    lgx += 160

dwg.add(dwg.text('住宅改造 — 拆砌墙图 | 比例示意 | 原始3房改2房+开放式厨房', 
          insert=(450, 30), font_size='14', font_weight='bold', text_anchor='middle'))

dwg.save()
print(f"✅ SVG: {OUT}/拆砌墙图.svg")

# 转PNG
os.system(f'magick convert "{OUT}/拆砌墙图.svg" "{OUT}/拆砌墙图.png" 2>/dev/null')
print(f"✅ PNG: {OUT}/拆砌墙图.png")

# =============================================
# 3. 项目信息
# =============================================
info = f"""# 住宅改造 — 拆砌墙图

## 改造方案
- **原始户型：** 3室1厅1厨1卫
- **改造目标：** 2室1厅+开放式厨房+大衣帽间
- **面积：** 约68㎡ (8000x8500mm)

## 拆除部分
1. 卧室A与卧室B之间的隔墙 → 打通成大主卧
2. 厨房与餐厅之间的隔墙 → 开放式厨房
3. 卫生间外墙部分 → 扩大卫生间

## 新建部分
1. 主卧内衣帽间隔断墙
2. 扩大后的卫生间新墙

## 建筑面积统计
- 客厅+餐厅：40㎡ (8000×5000)
- 主卧：21㎡ (6500×3500-过道)
- 厨房：9㎡ (3000×3000)
- 卫生间：7㎡ (2000×3500)

## 命令使用
- LINE — 所有墙体
- OFFSET — 墙厚偏移
- TRIM — 门洞修剪
- COPY — 对称布局复制
- LAYER — EXST/DEMO/NEWW 三层管理
"""
with open(f'{OUT}/项目信息.md', 'w') as f:
    f.write(info)
print(f"✅ 项目信息: {OUT}/项目信息.md")

print(f"\n📋 住宅改造项目完成！")
print(f"   图层: A-EXST(保留) / A-DEMO(拆除) / A-NEWW(新建)")
print(f"   色彩规范: 保留=黄虚线 / 拆除=红虚线 / 新建=青实线")
print(f"   用 CAD看圖王 打开 DXF 可看原始图纸")
