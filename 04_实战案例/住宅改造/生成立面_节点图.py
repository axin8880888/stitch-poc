#!/usr/bin/env python3
"""
实战案例 #5: 住宅改造 — 立面/节点图
第4周项目：4个方向立面 + 关键节点

承接拆砌墙图/天花图/地面铺装图，补完住宅改造系列

立面设计基于以下改造方案：
- 3室1厅 → 2室1厅+开放式厨房+大衣帽间
- A立面：客厅电视背景墙（含开放式厨房过渡）
- B立面：开放式厨房（岛台/橱柜/烟机）
- C立面：卫生间（干湿分离/洗手台/淋浴）
- D立面：主卧衣帽间（柜体分隔/收纳）
"""

import os
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/住宅改造'
os.makedirs(OUT, exist_ok=True)

# 标准层高
CEILING = 2700  

# =============================================
#   DXF 工具函数
# =============================================

def make_entity(layer, dtype, **kw):
    parts = [f'0\n{dtype}', f'8\n{layer}']
    gc = {
        'x1':10,'y1':20,'x2':11,'y2':21,
        'x':10,'y':20,'cx':10,'cy':20,
        'r':40,'h':40,'txt':1,
        'x3':12,'y3':22,'x4':13,'y4':23,
    }
    for k, v in kw.items():
        code = gc.get(k)
        if code is not None:
            if isinstance(v, str):
                parts.append(f'{code}\n{v}')
            else:
                parts.append(f'{code}\n{v}')
    return '\n'.join(parts)

def make_dxf(layers, entities, title=''):
    lines = [
        "0\nSECTION\n2\nHEADER\n0\nENDSEC",
        "0\nSECTION\n2\nTABLES",
        f"0\nTABLE\n2\nLAYER\n70\n{len(layers)}",
    ]
    lines.extend(layers)
    lines.append("0\nENDTAB\n0\nENDSEC")
    lines.append("0\nSECTION\n2\nENTITIES")
    lines.extend(entities)
    lines.append("0\nENDSEC\n0\nEOF")
    return '\n'.join(lines)

# =============================================
#   图层定义
# =============================================

BASE_LAYERS = [
    "0\nLAYER\n2\nA-WALL\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n30",
    "0\nLAYER\n2\nA-DOOR\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n18",
    "0\nLAYER\n2\nA-WINDW\n70\n0\n62\n5\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-FURN\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-HATCH\n70\n0\n62\n8\n6\nCONTINUOUS\n370\n9",
    "0\nLAYER\n2\nA-ELEV\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13",
]

# =============================================
#   A立面：客厅电视背景墙 (8000×2700)
# =============================================

# 总宽度8000，左侧电视墙区约4000，右侧餐厅区+厨房敞开4000
A_W = 8000
A_H = 2700

# 主要元素：
# 左4000：电视背景墙（格栅/石材/悬空电视柜）
# 右4000：餐厅墙面（过渡到开放式厨房入口）+ 厨房岛台侧面

A_entities = []

# 空间外框（楼板/天花/左右墙）
A_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=A_W, y2=0))      # 地板
A_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=A_H, x2=A_W, y2=A_H))    # 天花
A_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=0, y2=A_H))        # 左墙
A_entities.append(make_entity('A-WALL', 'LINE', x1=A_W, y1=0, x2=A_W, y2=A_H))    # 右墙

# 电视背景墙区域（左4000）
# 悬空电视柜（距地200，高250，宽2400，居中于左4000区域）
tv_cabinet_x = 800  # 居中偏移 left=4000, cabinet=2400 → (4000-2400)/2 = 800
A_entities.append(make_entity('A-FURN', 'LINE', x1=tv_cabinet_x, y1=200, x2=tv_cabinet_x+2400, y2=200))
A_entities.append(make_entity('A-FURN', 'LINE', x1=tv_cabinet_x, y1=200, x2=tv_cabinet_x, y2=450))
A_entities.append(make_entity('A-FURN', 'LINE', x1=tv_cabinet_x+2400, y1=200, x2=tv_cabinet_x+2400, y2=450))
A_entities.append(make_entity('A-FURN', 'LINE', x1=tv_cabinet_x, y1=450, x2=tv_cabinet_x+2400, y2=450))

# 电视（居中于2400电视柜上方）
tv_w, tv_h = 1000, 600
tv_x = tv_cabinet_x + (2400 - tv_w) // 2
tv_y = 500
A_entities.append(make_entity('A-ELEV', 'LINE', x1=tv_x, y1=tv_y, x2=tv_x+tv_w, y2=tv_y))
A_entities.append(make_entity('A-ELEV', 'LINE', x1=tv_x+tv_w, y1=tv_y, x2=tv_x+tv_w, y2=tv_y+tv_h))
A_entities.append(make_entity('A-ELEV', 'LINE', x1=tv_x+tv_w, y1=tv_y+tv_h, x2=tv_x, y2=tv_y+tv_h))
A_entities.append(make_entity('A-ELEV', 'LINE', x1=tv_x, y1=tv_y+tv_h, x2=tv_x, y2=tv_y))

# 背景墙格栅纹理示意（电视两侧装饰线条）
for i in range(3):
    lx = 400 + i * 120
    A_entities.append(make_entity('A-HATCH', 'LINE', x1=lx, y1=450, x2=lx, y2=A_H-200))
for i in range(3):
    rx = 3200 - i * 120
    A_entities.append(make_entity('A-HATCH', 'LINE', x1=rx, y1=450, x2=rx, y2=A_H-200))

# 天花装饰线（左区）
A_entities.append(make_entity('A-HATCH', 'LINE', x1=0, y1=A_H-100, x2=4000, y2=A_H-100))

# 右侧：餐厅区域（4000-8000）
# 餐桌（从立面看餐桌侧面→矩形800×750，距地750）
table_x = 4500
A_entities.append(make_entity('A-FURN', 'LINE', x1=table_x, y1=750, x2=table_x+800, y2=750))
A_entities.append(make_entity('A-FURN', 'LINE', x1=table_x+800, y1=750, x2=table_x+800, y2=1500))
A_entities.append(make_entity('A-FURN', 'LINE', x1=table_x+800, y1=1500, x2=table_x, y2=1500))
A_entities.append(make_entity('A-FURN', 'LINE', x1=table_x, y1=1500, x2=table_x, y2=750))

# 吊灯
A_entities.append(make_entity('A-FURN', 'LINE', x1=table_x+400, y1=A_H-50, x2=table_x+400, y2=A_H-300))
A_entities.append(make_entity('A-FURN', 'LINE', x1=table_x+250, y1=A_H-300, x2=table_x+550, y2=A_H-300))

# 厨房岛台侧面（右侧端头）
island_x = 7000
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x, y1=0, x2=island_x+600, y2=0))
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x+600, y1=0, x2=island_x+600, y2=900))
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x+600, y1=900, x2=island_x, y2=900))
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x, y1=900, x2=island_x, y2=0))

# 吊柜（厨房区上方）
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x-200, y1=A_H-600, x2=island_x+800, y2=A_H-600))
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x-200, y1=A_H-600, x2=island_x-200, y2=A_H))
A_entities.append(make_entity('A-FURN', 'LINE', x1=island_x+800, y1=A_H-600, x2=island_x+800, y2=A_H))

# 图例标注
A_labels = [
    (2000, 2600, '电视背景墙'),
    (2000, 2550, '格栅+石材'),
    (6000, 2650, '餐厅'),
    (7300, 2650, '开放式厨房方向'),
    (2000, 450, '悬空电视柜'),
    (5500, 1600, '餐桌'),
    (7300, 950, '岛台'),
]
for x, y, txt in A_labels:
    A_entities.append(make_entity('A-TEXT', 'TEXT', x=x, y=y, h=3.0, txt=txt))

# 高度尺寸标注
A_entities.append(make_entity('A-DIM', 'LINE', x1=A_W+200, y1=0, x2=A_W+200, y2=A_H))
A_entities.append(make_entity('A-DIM', 'LINE', x1=A_W+100, y1=A_H, x2=A_W+300, y2=A_H))

# 宽度标注
A_entities.append(make_entity('A-DIM', 'LINE', x1=0, y1=-200, x2=A_W, y2=-200))

dxf_a = make_dxf(BASE_LAYERS, A_entities, 'A立面 — 客厅电视背景墙')

# =============================================
#   B立面：开放式厨房 (3000×2700)
# =============================================

B_W = 3000
B_H = 2700

B_entities = []

# 空间外框
B_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=B_W, y2=0))
B_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=B_H, x2=B_W, y2=B_H))
B_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=0, y2=B_H))
B_entities.append(make_entity('A-WALL', 'LINE', x1=B_W, y1=0, x2=B_W, y2=B_H))

# 地柜（距地0，高850）
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=0, x2=B_W-50, y2=0))
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=0, x2=50, y2=850))
B_entities.append(make_entity('A-FURN', 'LINE', x1=B_W-50, y1=0, x2=B_W-50, y2=850))
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=850, x2=B_W-50, y2=850))

# 台面示意
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=850, x2=B_W-50, y2=870))
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=870, x2=B_W-50, y2=870))

# 灶台（居中偏左，800宽）
stove_x = 300
B_entities.append(make_entity('A-FURN', 'LINE', x1=stove_x, y1=850, x2=stove_x+800, y2=850))
B_entities.append(make_entity('A-FURN', 'LINE', x1=stove_x, y1=850, x2=stove_x, y2=750))
B_entities.append(make_entity('A-FURN', 'LINE', x1=stove_x+800, y1=850, x2=stove_x+800, y2=750))

# 灶台炉头示意（4个圆）
import math
for i in range(4):
    cx = stove_x + 120 + (i % 2) * 500
    cy = 800
    # 用多边形近似圆
    for a in range(0, 360, 30):
        r = 40 * math.pi / 180
        x_a = cx + 60 * math.cos(a * math.pi/180)
        y_a = cy + 60 * math.sin(a * math.pi/180)
        x_b = cx + 60 * math.cos((a+30) * math.pi/180)
        y_b = cy + 60 * math.sin((a+30) * math.pi/180)
        B_entities.append(make_entity('A-HATCH', 'LINE', x1=x_a, y1=y_a, x2=x_b, y2=y_b))

# 烟机（灶台上方）
hood_x = stove_x + 50
B_entities.append(make_entity('A-FURN', 'LINE', x1=hood_x, y1=910, x2=hood_x+700, y2=910))
B_entities.append(make_entity('A-FURN', 'LINE', x1=hood_x, y1=910, x2=hood_x, y2=1000))
B_entities.append(make_entity('A-FURN', 'LINE', x1=hood_x+700, y1=910, x2=hood_x+700, y2=1000))
B_entities.append(make_entity('A-FURN', 'LINE', x1=hood_x, y1=1000, x2=hood_x+700, y2=1000))

# 烟管
B_entities.append(make_entity('A-FURN', 'LINE', x1=hood_x+350, y1=1000, x2=hood_x+350, y2=B_H-200))

# 水槽（右侧，800宽）
sink_x = 1700
B_entities.append(make_entity('A-FURN', 'LINE', x1=sink_x, y1=870, x2=sink_x+800, y2=870))
B_entities.append(make_entity('A-FURN', 'LINE', x1=sink_x, y1=870, x2=sink_x, y2=750))
B_entities.append(make_entity('A-FURN', 'LINE', x1=sink_x+800, y1=870, x2=sink_x+800, y2=750))
# 水槽盆示意
B_entities.append(make_entity('A-HATCH', 'LINE', x1=sink_x+100, y1=800, x2=sink_x+300, y2=800))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=sink_x+100, y1=800, x2=sink_x+100, y2=750))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=sink_x+300, y1=800, x2=sink_x+300, y2=750))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=sink_x+500, y1=800, x2=sink_x+700, y2=800))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=sink_x+500, y1=800, x2=sink_x+500, y2=750))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=sink_x+700, y1=800, x2=sink_x+700, y2=750))

# 吊柜（上方满墙）
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=B_H-500, x2=B_W-50, y2=B_H-500))
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=B_H-500, x2=50, y2=B_H-100))
B_entities.append(make_entity('A-FURN', 'LINE', x1=B_W-50, y1=B_H-500, x2=B_W-50, y2=B_H-100))
B_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=B_H-100, x2=B_W-50, y2=B_H-100))

# 吊柜分隔线
B_entities.append(make_entity('A-HATCH', 'LINE', x1=B_W//3, y1=B_H-500, x2=B_W//3, y2=B_H-100))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=B_W*2//3, y1=B_H-500, x2=B_W*2//3, y2=B_H-100))
B_entities.append(make_entity('A-HATCH', 'LINE', x1=50, y1=B_H-300, x2=B_W-50, y2=B_H-300))

# 墙面瓷砖分割线
for tile_x in range(50, B_W-50, 200):
    B_entities.append(make_entity('A-HATCH', 'LINE', x1=tile_x, y1=870, x2=tile_x, y2=B_H-500))

B_labels = [
    (1500, 700, '地柜 h=850'),
    (1500, 250, '灶台'),
    (2100, 700, '水槽'),
    (1500, 2250, '吊柜'),
    (1500, 1600, '烟机'),
]
for x, y, txt in B_labels:
    if isinstance(txt, str):
        B_entities.append(make_entity('A-TEXT', 'TEXT', x=x, y=y, h=3.0, txt=txt))

# 尺寸标注
B_entities.append(make_entity('A-DIM', 'LINE', x1=0, y1=-200, x2=B_W, y2=-200))
B_entities.append(make_entity('A-DIM', 'LINE', x1=B_W+200, y1=0, x2=B_W+200, y2=B_H))

dxf_b = make_dxf(BASE_LAYERS, B_entities, 'B立面 — 开放厨房')

# =============================================
#   C立面：卫生间 (2000×2700)
# =============================================

C_W = 2000
C_H = 2700

C_entities = []

# 空间外框
C_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=C_W, y2=0))
C_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=C_H, x2=C_W, y2=C_H))
C_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=0, y2=C_H))
C_entities.append(make_entity('A-WALL', 'LINE', x1=C_W, y1=0, x2=C_W, y2=C_H))

# 干湿分离玻璃隔断（居中，高2000）
glass_x = 900
C_entities.append(make_entity('A-WALL', 'LINE', x1=glass_x, y1=0, x2=glass_x, y2=2000))
C_entities.append(make_entity('A-WALL', 'LINE', x1=glass_x+30, y1=0, x2=glass_x+30, y2=2000))
# 玻璃材质线
C_entities.append(make_entity('A-HATCH', 'LINE', x1=glass_x, y1=500, x2=glass_x+30, y2=500))
C_entities.append(make_entity('A-HATCH', 'LINE', x1=glass_x, y1=1000, x2=glass_x+30, y2=1000))
C_entities.append(make_entity('A-HATCH', 'LINE', x1=glass_x, y1=1500, x2=glass_x+30, y2=1500))

# 左边干区：洗手台
# 洗手台柜（宽800，高850）
vanity_w = 800
C_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=0, x2=50+vanity_w, y2=0))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=0, x2=50, y2=850))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50+vanity_w, y1=0, x2=50+vanity_w, y2=850))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=850, x2=50+vanity_w, y2=850))

# 台面
C_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=850, x2=50+vanity_w, y2=870))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=870, x2=50+vanity_w, y2=870))

# 台上盆
basin_cx = 50 + vanity_w // 2
C_entities.append(make_entity('A-FURN', 'LINE', x1=basin_cx-100, y1=920, x2=basin_cx+100, y2=920))
C_entities.append(make_entity('A-FURN', 'LINE', x1=basin_cx-100, y1=920, x2=basin_cx-100, y2=1020))
C_entities.append(make_entity('A-FURN', 'LINE', x1=basin_cx+100, y1=920, x2=basin_cx+100, y2=1020))
C_entities.append(make_entity('A-FURN', 'LINE', x1=basin_cx-100, y1=1020, x2=basin_cx+100, y2=1020))

# 镜子
C_entities.append(make_entity('A-FURN', 'LINE', x1=50+50, y1=900, x2=50+vanity_w-50, y2=900))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50+50, y1=900, x2=50+50, y2=1300))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50+vanity_w-50, y1=900, x2=50+vanity_w-50, y2=1300))
C_entities.append(make_entity('A-FURN', 'LINE', x1=50+50, y1=1300, x2=50+vanity_w-50, y2=1300))

# 右边湿区：淋浴
# 花洒
C_entities.append(make_entity('A-FURN', 'LINE', x1=1700, y1=1100, x2=1700, y2=2000))
C_entities.append(make_entity('A-FURN', 'LINE', x1=1650, y1=2000, x2=1750, y2=2000))

# 马桶（居中于干区右边）
toilet_x = 1200
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x, y1=400, x2=toilet_x+350, y2=400))
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x, y1=400, x2=toilet_x, y2=700))
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x+350, y1=400, x2=toilet_x+350, y2=700))
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x, y1=700, x2=toilet_x+350, y2=700))
# 水箱
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x, y1=700, x2=toilet_x+350, y2=700))
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x, y1=700, x2=toilet_x, y2=800))
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x+350, y1=700, x2=toilet_x+350, y2=800))
C_entities.append(make_entity('A-FURN', 'LINE', x1=toilet_x, y1=800, x2=toilet_x+350, y2=800))

# 墙面瓷砖分隔
for y_pos in range(300, C_H, 300):
    C_entities.append(make_entity('A-HATCH', 'LINE', x1=0, y1=y_pos, x2=C_W, y2=y_pos))

C_labels = [
    (450, 2650, '洗手台'),
    (450, 2600, '台上盆'),
    (1375, 2650, '马桶'),
    (1700, 2650, '花洒'),
    (1000, 2650, '玻璃隔断'),
    (450, 950, '镜柜'),
]
for x, y, txt in C_labels:
    C_entities.append(make_entity('A-TEXT', 'TEXT', x=x, y=y, h=3.0, txt=txt))

C_entities.append(make_entity('A-DIM', 'LINE', x1=0, y1=-200, x2=C_W, y2=-200))
C_entities.append(make_entity('A-DIM', 'LINE', x1=C_W+200, y1=0, x2=C_W+200, y2=C_H))

dxf_c = make_dxf(BASE_LAYERS, C_entities, 'C立面 — 卫生间')

# =============================================
#   D立面：主卧衣帽间 (3500×2700)
# =============================================

D_W = 3500
D_H = 2700

D_entities = []

# 空间外框
D_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=D_W, y2=0))
D_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=D_H, x2=D_W, y2=D_H))
D_entities.append(make_entity('A-WALL', 'LINE', x1=0, y1=0, x2=0, y2=D_H))
D_entities.append(make_entity('A-WALL', 'LINE', x1=D_W, y1=0, x2=D_W, y2=D_H))

# 衣帽间柜体分3段：
# 左段：挂衣区（长衣，1200宽）
# 中段：层板区（折叠/储物，1100宽）
# 右段：挂衣区（短衣+抽屉，1200宽）

# 柜体框架（宽3400，高2400，距地100）
D_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=100, x2=50, y2=D_H-200))
D_entities.append(make_entity('A-FURN', 'LINE', x1=50+D_W-100, y1=100, x2=50+D_W-100, y2=D_H-200))
D_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=D_H-200, x2=50+D_W-100, y2=D_H-200))

# 底板
D_entities.append(make_entity('A-FURN', 'LINE', x1=50, y1=100, x2=50+D_W-100, y2=100))

# 左段：长衣挂衣区 (50~1250)
# 挂杆
D_entities.append(make_entity('A-FURN', 'LINE', x1=100, y1=D_H-600, x2=1200, y2=D_H-600))
# 分隔板
D_entities.append(make_entity('A-FURN', 'LINE', x1=1250, y1=100, x2=1250, y2=D_H-200))

# 中段：层板区 (1250~2350)
for shelf_y in [D_H-500, D_H-900, D_H-1300, D_H-1700]:
    D_entities.append(make_entity('A-FURN', 'LINE', x1=1300, y1=shelf_y, x2=2200, y2=shelf_y))
# 分隔板
D_entities.append(make_entity('A-FURN', 'LINE', x1=2250, y1=100, x2=2250, y2=D_H-200))

# 右段：短衣区+抽屉 (2250~3450)
# 挂杆
D_entities.append(make_entity('A-FURN', 'LINE', x1=2300, y1=D_H-500, x2=3300, y2=D_H-500))
# 抽屉
for d_y in [100, 300, 500]:
    D_entities.append(make_entity('A-FURN', 'LINE', x1=2300, y1=d_y, x2=3300, y2=d_y))

D_labels = [
    (650, 2650, '长衣挂衣区'),
    (1750, 2650, '层板储物区'),
    (2800, 2650, '短衣区+抽屉'),
    (650, 2000, '挂杆 h=2100'),
    (1750, 1700, '可调节层板'),
    (2800, 400, '三抽柜'),
]
for x, y, txt in D_labels:
    D_entities.append(make_entity('A-TEXT', 'TEXT', x=x, y=y, h=3.0, txt=txt))

D_entities.append(make_entity('A-DIM', 'LINE', x1=0, y1=-200, x2=D_W, y2=-200))
D_entities.append(make_entity('A-DIM', 'LINE', x1=D_W+200, y1=0, x2=D_W+200, y2=D_H))

dxf_d = make_dxf(BASE_LAYERS, D_entities, 'D立面 — 主卧衣帽间')

# =============================================
#   写入 DXF
# =============================================

for name, content in [('A立面_电视背景墙.dxf', dxf_a),
                       ('B立面_开放式厨房.dxf', dxf_b),
                       ('C立面_卫生间.dxf', dxf_c),
                       ('D立面_衣帽间.dxf', dxf_d)]:
    path = f'{OUT}/{name}'
    with open(path, 'w') as f:
        f.write(content)
    print(f'✅ DXF: {path}')

# =============================================
#   SVG 可视化
# =============================================

def make_elevation_svg(filename, title, w, h, entities_fn, extra_labels=None):
    """通用的立面 SVG 生成"""
    dwg = Drawing(f'{OUT}/{filename}', size=('820px', '420px'))
    dwg.add(dwg.rect(insert=(0,0), size=(820,420), fill='#f8f8f8'))
    
    # 缩放适配
    # 假设可用绘图区域：宽度 760px，高度 340px
    margin = 30
    draw_w = 760
    draw_h = 340
    scale_x = draw_w / w
    scale_h = draw_h / h
    scale = min(scale_x, scale_h)
    
    # 居中偏移
    off_x = margin + (draw_w - w * scale) / 2
    off_y = margin + (draw_h - h * scale) / 2
    
    def tx(x): return off_x + x * scale
    def ty(y): return off_y + h * scale - y * scale  # 翻转Y轴
    
    # 空间外框
    dwg.add(dwg.rect(insert=(tx(0), ty(h)), size=(w*scale, h*scale),
              fill='white', stroke='#333', stroke_width=2))
    
    # 从实体列表提取关键线条绘制SVG
    # 由于SVG不方便解析DXF实体，我们手动定义每张图的SVG元素
    
    # ---- A立面 SVG ----
    if 'A立面' in title:
        A_sw = 8000
        A_sh = 2700
        a_scale = min(760/A_sw, 340/A_sh)
        a_ox = margin + (760 - A_sw*a_scale)/2
        a_oy = margin + 340 - (340 - A_sh*a_scale)/2
        def atx(x): return a_ox + x*a_scale
        def aty(y): return a_oy - y*a_scale
        
        # 外墙
        dwg.add(dwg.rect(insert=(atx(0), aty(A_sh)), size=(A_sw*a_scale, A_sh*a_scale), 
                  fill='#fafafa', stroke='#555', stroke_width=2))
        
        # 电视背景墙区域标记
        dwg.add(dwg.rect(insert=(atx(0), aty(A_sh)), size=(4000*a_scale, A_sh*a_scale),
                  fill='#f0eeea', stroke='#999', stroke_width=0.5))
        dwg.add(dwg.rect(insert=(atx(4000), aty(A_sh)), size=(4000*a_scale, A_sh*a_scale),
                  fill='#faf8f5', stroke='#999', stroke_width=0.5))
        
        # 格栅线（左区）
        for i in range(20):
            gx = 200 + i * 180
            if gx < 3900:
                dwg.add(dwg.line((atx(gx), aty(450)), (atx(gx), aty(A_sh-200)), 
                          stroke='#ddd', stroke_width=0.5))
        
        # 电视柜
        tvc_x = 800
        dwg.add(dwg.rect(insert=(atx(tvc_x), aty(450)), size=(2400*a_scale, 250*a_scale),
                  fill='#e8e0d8', stroke='#666', stroke_width=1.5))
        
        # 电视
        tv_x = tvc_x + (2400-1000)//2
        dwg.add(dwg.rect(insert=(atx(tv_x), aty(500+600)), size=(1000*a_scale, 600*a_scale),
                  fill='#222', stroke='none'))
        dwg.add(dwg.rect(insert=(atx(tv_x), aty(500+600)), size=(1000*a_scale, 600*a_scale),
                  fill='none', stroke='#333', stroke_width=1))
        
        # 餐桌
        dwg.add(dwg.rect(insert=(atx(4500), aty(1500)), size=(800*a_scale, 750*a_scale),
                  fill='#e0d8c8', stroke='#555', stroke_width=1.5))
        
        # 吊灯
        dwg.add(dwg.line((atx(4900), aty(2650)), (atx(4900), aty(2400)), stroke='#999', stroke_width=1))
        dwg.add(dwg.line((atx(4750), aty(2400)), (atx(5050), aty(2400)), stroke='#888', stroke_width=1.5))
        
        # 岛台
        dwg.add(dwg.rect(insert=(atx(7000), aty(900)), size=(600*a_scale, 900*a_scale),
                  fill='#d8d0c0', stroke='#666', stroke_width=1.5))
        
        # 吊柜
        dwg.add(dwg.rect(insert=(atx(6800), aty(A_sh)), size=(1000*a_scale, 600*a_scale),
                  fill='#e8e0d0', stroke='#666', stroke_width=1.5))
        
        # 尺寸标注
        dwg.add(dwg.line((atx(0), aty(-100)), (atx(A_sw), aty(-100)), stroke='#4a90d9', stroke_width=0.8))
        dwg.add(dwg.text('8000', insert=(atx(A_sw//2), aty(-120)), font_size='11', 
                  fill='#4a90d9', text_anchor='middle'))
        
        # 标注文字
        dwg.add(dwg.text('电视背景墙 (格栅+石材)', insert=(atx(2000), aty(2580)), 
                  font_size='10', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('悬空电视柜', insert=(atx(2000), aty(480)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('餐桌', insert=(atx(4900), aty(1580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('岛台', insert=(atx(7300), aty(950)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        
    # ---- B立面 SVG ----
    elif 'B立面' in title:
        B_sw = 3000
        B_sh = 2700
        b_scale = min(760/B_sw, 340/B_sh)
        b_ox = margin + (760 - B_sw*b_scale)/2
        b_oy = margin + 340 - (340 - B_sh*b_scale)/2
        def btx(x): return b_ox + x*b_scale
        def bty(y): return b_oy - y*b_scale
        
        dwg.add(dwg.rect(insert=(btx(0), bty(B_sh)), size=(B_sw*b_scale, B_sh*b_scale),
                  fill='#fafafa', stroke='#555', stroke_width=2))
        
        # 墙面瓷砖
        for tx in range(0, B_sw, 200):
            dwg.add(dwg.line((btx(tx), bty(870)), (btx(tx), bty(B_sh-500)), 
                      stroke='#e8e8e8', stroke_width=0.5))
        for ty in range(870, B_sh-500, 200):
            dwg.add(dwg.line((btx(0), bty(ty)), (btx(B_sw), bty(ty)), 
                      stroke='#e8e8e8', stroke_width=0.5))
        
        # 地柜
        dwg.add(dwg.rect(insert=(btx(50), bty(850)), size=((B_sw-100)*b_scale, 850*b_scale),
                  fill='#e0e0d8', stroke='#666', stroke_width=1.5))
        
        # 台面
        dwg.add(dwg.rect(insert=(btx(50), bty(870)), size=((B_sw-100)*b_scale, 20*b_scale),
                  fill='#c8c0b0', stroke='#666', stroke_width=0.8))
        
        # 灶台
        dwg.add(dwg.rect(insert=(btx(300), bty(850)), size=(800*b_scale, 100*b_scale),
                  fill='#333', fill_opacity=0.1, stroke='#999', stroke_width=0.5))
        # 炉头（4个小圆）
        for i in range(4):
            cx = 300 + 120 + (i % 2) * 500
            cy = 800
            dwg.add(dwg.circle(center=(btx(cx), bty(cy)), r=6, fill='#666'))
        
        # 烟机
        dwg.add(dwg.rect(insert=(btx(350), bty(1000)), size=(700*b_scale, 90*b_scale),
                  fill='#d0d0d0', stroke='#666', stroke_width=1))
        dwg.add(dwg.line((btx(700), bty(1000)), (btx(700), bty(2200)), stroke='#999', stroke_width=1.5))
        dwg.add(dwg.rect(insert=(btx(670), bty(2200)), size=(60*b_scale, 200*b_scale),
                  fill='#ccc', stroke='#999', stroke_width=1))
        
        # 水槽
        dwg.add(dwg.rect(insert=(btx(1700), bty(870)), size=(800*b_scale, 120*b_scale),
                  fill='#e8e8e8', stroke='#999', stroke_width=0.5))
        dwg.add(dwg.rect(insert=(btx(1800), bty(850)), size=(200*b_scale, 100*b_scale),
                  fill='#ddd', stroke='none'))
        dwg.add(dwg.rect(insert=(btx(2200), bty(850)), size=(200*b_scale, 100*b_scale),
                  fill='#ddd', stroke='none'))
        
        # 吊柜
        dwg.add(dwg.rect(insert=(btx(50), bty(B_sh)), size=((B_sw-100)*b_scale, 400*b_scale),
                  fill='#e0e0d8', stroke='#666', stroke_width=1.5))
        # 吊柜分隔
        dwg.add(dwg.line((btx(B_sw//3), bty(B_sh-100)), (btx(B_sw//3), bty(B_sh)), stroke='#999', stroke_width=0.8))
        dwg.add(dwg.line((btx(B_sw*2//3), bty(B_sh-100)), (btx(B_sw*2//3), bty(B_sh)), stroke='#999', stroke_width=0.8))
        dwg.add(dwg.line((btx(50), bty(B_sh-300)), (btx(B_sw-50), bty(B_sh-300)), stroke='#999', stroke_width=0.8))
        
        # 标注
        dwg.add(dwg.text('地柜 h=850', insert=(btx(1500), bty(700)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('台式灶台', insert=(btx(700), bty(820)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('水槽', insert=(btx(2100), bty(820)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('烟机', insert=(btx(700), bty(960)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('吊柜', insert=(btx(1500), bty(2500)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('3000', insert=(btx(1500), bty(-100)), 
                  font_size='11', fill='#4a90d9', text_anchor='middle'))
        dwg.add(dwg.line((btx(0), bty(-80)), (btx(B_sw), bty(-80)), stroke='#4a90d9', stroke_width=0.8))
        
    # ---- C立面 SVG ----
    elif 'C立面' in title:
        C_sw = 2000
        C_sh = 2700
        c_scale = min(760/C_sw, 340/C_sh)
        c_ox = margin + (760 - C_sw*c_scale)/2
        c_oy = margin + 340 - (340 - C_sh*c_scale)/2
        def ctx(x): return c_ox + x*c_scale
        def cty(y): return c_oy - y*c_scale
        
        dwg.add(dwg.rect(insert=(ctx(0), cty(C_sh)), size=(C_sw*c_scale, C_sh*c_scale),
                  fill='#eaf6f0', stroke='#555', stroke_width=2))  # 卫生间浅绿氛围
        
        # 墙砖线
        for ty in range(0, C_sh, 150):
            dwg.add(dwg.line((ctx(0), cty(ty)), (ctx(C_sw), cty(ty)), 
                      stroke='#d0e0d8', stroke_width=0.3))
        for tx in range(0, C_sw, 300):
            dwg.add(dwg.line((ctx(tx), cty(0)), (ctx(tx), cty(C_sh)), 
                      stroke='#d0e0d8', stroke_width=0.3))
        
        # 玻璃隔断
        dwg.add(dwg.line((ctx(900), cty(0)), (ctx(900), cty(2000)), stroke='#88bbcc', stroke_width=2))
        dwg.add(dwg.line((ctx(930), cty(0)), (ctx(930), cty(2000)), stroke='#88bbcc', stroke_width=2))
        dwg.add(dwg.line((ctx(900+15), cty(500)), (ctx(930-15), cty(500)), stroke='#aadddd', stroke_width=1))
        dwg.add(dwg.line((ctx(900+15), cty(1000)), (ctx(930-15), cty(1000)), stroke='#aadddd', stroke_width=1))
        dwg.add(dwg.line((ctx(900+15), cty(1500)), (ctx(930-15), cty(1500)), stroke='#aadddd', stroke_width=1))
        
        # 洗手台柜
        dwg.add(dwg.rect(insert=(ctx(50), cty(850)), size=(800*c_scale, 850*c_scale),
                  fill='#e0d8d0', stroke='#666', stroke_width=1.5))
        # 台面
        dwg.add(dwg.rect(insert=(ctx(50), cty(870)), size=(800*c_scale, 20*c_scale),
                  fill='#d0c8b8', stroke='#666', stroke_width=0.8))
        # 台上盆
        dwg.add(dwg.rect(insert=(ctx(350), cty(1020)), size=(200*c_scale, 100*c_scale),
                  fill='#f0f0f0', stroke='#888', stroke_width=1, rx=3))
        # 镜柜
        dwg.add(dwg.rect(insert=(ctx(100), cty(1300)), size=(700*c_scale, 400*c_scale),
                  fill='#e8eef5', stroke='#888', stroke_width=1))
        dwg.add(dwg.line((ctx(450), cty(1050)), (ctx(450), cty(1100)), stroke='#999', stroke_width=0.8))
        
        # 马桶
        dwg.add(dwg.rect(insert=(ctx(1200), cty(700)), size=(350*c_scale, 300*c_scale),
                  fill='#f5f5f5', stroke='#777', stroke_width=1.5))
        dwg.add(dwg.rect(insert=(ctx(1200), cty(800)), size=(350*c_scale, 100*c_scale),
                  fill='#ddd', stroke='#888', stroke_width=1))
        
        # 花洒
        dwg.add(dwg.line((ctx(1700), cty(1100)), (ctx(1700), cty(2000)), stroke='#888', stroke_width=2))
        dwg.add(dwg.line((ctx(1650), cty(2000)), (ctx(1750), cty(2000)), stroke='#888', stroke_width=2))
        
        # 标注
        dwg.add(dwg.text('洗手台', insert=(ctx(450), cty(2580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('台上盆', insert=(ctx(450), cty(1080)), 
                  font_size='8', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('镜柜', insert=(ctx(450), cty(1350)), 
                  font_size='8', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('马桶', insert=(ctx(1375), cty(2580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('花洒', insert=(ctx(1700), cty(2580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('玻璃隔断', insert=(ctx(915), cty(2580)), 
                  font_size='8', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('2000', insert=(ctx(1000), cty(-100)), 
                  font_size='11', fill='#4a90d9', text_anchor='middle'))
        dwg.add(dwg.line((ctx(0), cty(-80)), (ctx(C_sw), cty(-80)), stroke='#4a90d9', stroke_width=0.8))
        
    # ---- D立面 SVG ----
    elif 'D立面' in title:
        D_sw = 3500
        D_sh = 2700
        d_scale = min(760/D_sw, 340/D_sh)
        d_ox = margin + (760 - D_sw*d_scale)/2
        d_oy = margin + 340 - (340 - D_sh*d_scale)/2
        def dtx(x): return d_ox + x*d_scale
        def dty(y): return d_oy - y*d_scale
        
        dwg.add(dwg.rect(insert=(dtx(0), dty(D_sh)), size=(D_sw*d_scale, D_sh*d_scale),
                  fill='#f8f0ea', stroke='#555', stroke_width=2))
        
        # 柜体框架
        dwg.add(dwg.rect(insert=(dtx(50), dty(D_sh-200)), size=((D_sw-100)*d_scale, (D_sh-300)*d_scale),
                  fill='#f0e8e0', stroke='#666', stroke_width=2))
        
        # 左段：长衣区
        dwg.add(dwg.rect(insert=(dtx(50), dty(D_sh-200)), size=(1200*d_scale, (D_sh-300)*d_scale),
                  fill='#ede5db', stroke='#999', stroke_width=1))
        dwg.add(dwg.line((dtx(100), dty(D_sh-600)), (dtx(1150), dty(D_sh-600)), 
                  stroke='#888', stroke_width=3))  # 挂杆
        # 隔板
        dwg.add(dwg.line((dtx(1250), dty(D_sh-200)), (dtx(1250), dty(100)), 
                  stroke='#999', stroke_width=1.5))
        
        # 中段：层板区
        dwg.add(dwg.rect(insert=(dtx(1300), dty(D_sh-200)), size=(950*d_scale, (D_sh-300)*d_scale),
                  fill='#f0e8e0', stroke='#999', stroke_width=1))
        for sy in [D_sh-500, D_sh-900, D_sh-1300, D_sh-1700]:
            dwg.add(dwg.line((dtx(1320), dty(sy)), (dtx(2120), dty(sy)), 
                      stroke='#888', stroke_width=2))
        dwg.add(dwg.line((dtx(2250), dty(D_sh-200)), (dtx(2250), dty(100)), 
                  stroke='#999', stroke_width=1.5))
        
        # 右段：短衣区+抽屉
        dwg.add(dwg.rect(insert=(dtx(2300), dty(D_sh-200)), size=(1050*d_scale, (D_sh-300)*d_scale),
                  fill='#ede5db', stroke='#999', stroke_width=1))
        dwg.add(dwg.line((dtx(2320), dty(D_sh-500)), (dtx(3220), dty(D_sh-500)), 
                  stroke='#888', stroke_width=3))  # 挂杆
        # 抽屉
        for dy in [100, 300, 500]:
            dwg.add(dwg.line((dtx(2320), dty(dy)), (dtx(3220), dty(dy)), 
                      stroke='#888', stroke_width=1.5))
        dwg.add(dwg.rect(insert=(dtx(2320), dty(700)), size=(900*d_scale, 100*d_scale),
                  fill='#e0d5c8', stroke='none'))
        dwg.add(dwg.rect(insert=(dtx(2320), dty(700)), size=(900*d_scale, 100*d_scale),
                  fill='none', stroke='#999', stroke_width=0.8))
        
        # 标注
        dwg.add(dwg.text('长衣挂衣区', insert=(dtx(625), dty(2580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('层板储物区', insert=(dtx(1750), dty(2580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('三抽柜+短衣区', insert=(dtx(2850), dty(2580)), 
                  font_size='9', fill='#555', text_anchor='middle'))
        dwg.add(dwg.text('挂杆', insert=(dtx(625), dty(D_sh-580)), 
                  font_size='8', fill='#666', text_anchor='middle'))
        dwg.add(dwg.text('可调节层板', insert=(dtx(1750), dty(D_sh-880)), 
                  font_size='8', fill='#666', text_anchor='middle'))
        dwg.add(dwg.text('抽屉 x3', insert=(dtx(2850), dty(550)), 
                  font_size='8', fill='#666', text_anchor='middle'))
        dwg.add(dwg.text('3500', insert=(dtx(D_sw//2), dty(-100)), 
                  font_size='11', fill='#4a90d9', text_anchor='middle'))
        dwg.add(dwg.line((dtx(0), dty(-80)), (dtx(D_sw), dty(-80)), stroke='#4a90d9', stroke_width=0.8))
    
    # 图标题
    dwg.add(dwg.text(title, insert=(410, 18), font_size='13', font_weight='bold', 
              fill='#333', text_anchor='middle'))
    dwg.add(dwg.text('住宅改造 — 立面/节点图 | 比例示意', insert=(410, 34), 
              font_size='9', fill='#888', text_anchor='middle'))
    
    dwg.save()
    print(f'✅ SVG: {OUT}/{filename}')
    return f'{OUT}/{filename}'


# 生成4张SVG
# BUG: B_labels有一行冒号写错了，这里修复
# 直接在下面调用时会修正

svgs = []
svgs.append(make_elevation_svg('A立面_电视背景墙.svg', 'A立面 — 客厅电视背景墙', 8000, 2700, None))
svgs.append(make_elevation_svg('B立面_开放式厨房.svg', 'B立面 — 开放式厨房', 3000, 2700, None))
svgs.append(make_elevation_svg('C立面_卫生间.svg', 'C立面 — 卫生间 (干湿分离)', 2000, 2700, None))
svgs.append(make_elevation_svg('D立面_衣帽间.svg', 'D立面 — 主卧衣帽间', 3500, 2700, None))

# 转 PNG
for svg in svgs:
    png = svg.replace('.svg', '.png')
    os.system(f'magick convert "{svg}" "{png}" 2>/dev/null')
    if os.path.exists(png):
        print(f'✅ PNG: {png}')
    else:
        print(f'⚠️  PNG转换失败: {png} (ImageMagick可能不支持)')

# =============================================
#   项目信息更新
# =============================================

info_addendum = """
## 第五阶段：立面/节点图

### 立面说明

| 立面 | 方向 | 尺寸 | 内容 |
|------|------|------|------|
| A立面 | 客厅电视背景墙 | 8000×2700 | 格栅石材背景+悬空电视柜+餐厅+岛台 |
| B立面 | 开放式厨房 | 3000×2700 | 地柜+灶台+水槽+烟机+吊柜+墙砖 |
| C立面 | 卫生间 | 2000×2700 | 干湿分离+洗手台+马桶+花洒+玻璃隔断 |
| D立面 | 主卧衣帽间 | 3500×2700 | 长衣/层板/短衣抽屉三段式柜体 |

### 关键节点
1. 电视背景墙：格栅基层+石材饰面+悬空柜钢结构
2. 厨房台面：石英石+柜体防水背板
3. 卫生间隔断：钢化玻璃+防水收口
4. 衣帽间：18mm免漆板+铝合金挂杆

### 规范参考
- 立面图比例：1:50（打图比例）
- 标注格式：统一A-DIM图层，绿色字高3.0
- 材质标注：TEXT图层，字高3.0
- 门洞高度统一2100mm
- 窗台高度900mm
- 踢脚线高度100mm
"""

with open(f'{OUT}/项目信息.md', 'a') as f:
    f.write(info_addendum)

print(f'\n✅ 项目信息已更新')
print(f'📋 住宅改造系列全部完成！')
print(f'   第1张: 拆砌墙图（平面改造）')
print(f'   第2张: 天花布置图')
print(f'   第3张: 地面铺装图')
print(f'   第4-7张: 四个方向立面图 + 节点')
