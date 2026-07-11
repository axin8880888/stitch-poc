#!/usr/bin/env python3
"""
图纸分析 #2: 晴碧园晶园26栋拆砌图
全面重建 + 深度分析

图纸关键特征：
- 电梯井 1.6m×1.58m
- U型楼梯（上21步 / 下17步）
- 早餐区+岛台
- 玻璃砖隔墙
- 挑空区域
- 钢琴、留声机等细部
"""

import os
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/图纸分析_拆砌图'
os.makedirs(OUT, exist_ok=True)

# =============================================
# 图纸参数
# =============================================
# 尺寸数据重建
# 左侧跨度: 3900 + 200墙 + 1700卫生间 = 5800?
# 更准确：总宽约 6500-7000

W = 7000  # 总宽估计
H = 8000  # 总高估计

# 关键位置
CENTER_X = 3500  # 中心

# 电梯井尺寸 (mm)
ELV_W = 1600  # 净宽
ELV_D = 1580  # 净深
ELV_X = CENTER_X - ELV_W//2 - 100  # 偏移让位置合理
ELV_Y = 3000  # 电梯底部Y

# 早餐区
BRK_X = 500
BRK_Y = 5000
BRK_W = 2500
BRK_H = 2000

# 岛台
ISL_X = BRK_X + 800
ISL_Y = BRK_Y + 600
ISL_W = 900
ISL_H = 700

# 挑空区
VOID_X = 4000
VOID_Y = 5000
VOID_W = 2000
VOID_H = 2500

# 卫生间
WC_X = 2000
WC_Y = 1000
WC_W = 4000
WC_H = 2000

# 衣帽间
CLO_X = 4000
CLO_Y = 7000
CLO_W = 2500
CLO_H = 1000

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
    "0\nLAYER\n2\nA-WALL\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n30",
    "0\nLAYER\n2\nA-EXST\n70\n0\n62\n2\n6\nHIDDEN\n370\n13",
    "0\nLAYER\n2\nA-DEMO\n70\n0\n62\n1\n6\nDASHED\n370\n13",
    "0\nLAYER\n2\nA-GLAS\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-ELVT\n70\n0\n62\n8\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-STAI\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n18",
    "0\nLAYER\n2\nA-FURN\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-VOID\n70\n0\n62\n2\n6\nHIDDEN\n370\n9",
]

# --- 外墙 ---
entities.append(ent('A-EXST', 'LINE', x1=0, y1=0, x2=W, y2=0))
entities.append(ent('A-EXST', 'LINE', x1=W, y1=0, x2=W, y2=H))
entities.append(ent('A-EXST', 'LINE', x1=W, y1=H, x2=0, y2=H))
entities.append(ent('A-EXST', 'LINE', x1=0, y1=H, x2=0, y2=0))

# --- 内部隔墙 ---
# 卫生间上方横墙
entities.append(ent('A-WALL', 'LINE', x1=0, y1=3000, x2=ELV_X+ELV_W+200, y2=3000))
# 卫生间右墙
entities.append(ent('A-WALL', 'LINE', x1=WC_X+WC_W, y1=0, x2=WC_X+WC_W, y2=3000))
# 卫生间纵墙
entities.append(ent('A-WALL', 'LINE', x1=WC_X+2000, y1=0, x2=WC_X+2000, y2=3000))

# 早餐区隔墙（玻璃砖）
entities.append(ent('A-GLAS', 'LINE', x1=BRK_X+BRK_W, y1=BRK_Y, x2=BRK_X+BRK_W, y2=BRK_Y+BRK_H))
entities.append(ent('A-GLAS', 'LINE', x1=BRK_X, y1=BRK_Y+BRK_H, x2=BRK_X+BRK_W, y2=BRK_Y+BRK_H))

# 另一道玻璃砖墙（左侧边界）
entities.append(ent('A-GLAS', 'LINE', x1=500, y1=0, x2=500, y2=H))

# 衣帽间隔墙
entities.append(ent('A-WALL', 'LINE', x1=CLO_X, y1=CLO_Y, x2=CLO_X+CLO_W, y2=CLO_Y))
entities.append(ent('A-WALL', 'LINE', x1=CLO_X+CLO_W, y1=CLO_Y, x2=CLO_X+CLO_W, y2=CLO_Y+CLO_H))

# --- 电梯井 (A-ELVT) ---
# 外框
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X, y1=ELV_Y, x2=ELV_X+ELV_W+200, y2=ELV_Y))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+ELV_W+200, y1=ELV_Y, x2=ELV_X+ELV_W+200, y2=ELV_Y+ELV_D+200))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+ELV_W+200, y1=ELV_Y+ELV_D+200, x2=ELV_X, y2=ELV_Y+ELV_D+200))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X, y1=ELV_Y+ELV_D+200, x2=ELV_X, y2=ELV_Y))
# 内框（净尺寸）
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+100, y1=ELV_Y+100, x2=ELV_X+ELV_W+100, y2=ELV_Y+100))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+ELV_W+100, y1=ELV_Y+100, x2=ELV_X+ELV_W+100, y2=ELV_Y+ELV_D+100))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+ELV_W+100, y1=ELV_Y+ELV_D+100, x2=ELV_X+100, y2=ELV_Y+ELV_D+100))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+100, y1=ELV_Y+ELV_D+100, x2=ELV_X+100, y2=ELV_Y+100))
# 电梯对角线符号
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+100, y1=ELV_Y+100, x2=ELV_X+ELV_W+100, y2=ELV_Y+ELV_D+100))
entities.append(ent('A-ELVT', 'LINE', x1=ELV_X+ELV_W+100, y1=ELV_Y+100, x2=ELV_X+100, y2=ELV_Y+ELV_D+100))

# --- U型楼梯 ---
# 楼梯在电梯井周围
STAIR_W = 1000  # 梯段宽度
# 左侧梯段：上21步
left_stair_x = ELV_X - STAIR_W - 100
left_stair_y = ELV_Y
for i in range(22):
    step_y = left_stair_y + i * (ELV_D // 21)
    entities.append(ent('A-STAI', 'LINE', x1=left_stair_x, y1=step_y, 
                        x2=left_stair_x+STAIR_W, y2=step_y))
entities.append(ent('A-STAI', 'LINE', x1=left_stair_x+STAIR_W, y1=left_stair_y, 
                    x2=left_stair_x+STAIR_W, y2=left_stair_y+ELV_D))

# 右侧梯段：下17步
right_stair_x = ELV_X + ELV_W + 300
right_stair_y = ELV_Y
for i in range(18):
    step_y = right_stair_y + i * (ELV_D // 17)
    entities.append(ent('A-STAI', 'LINE', x1=right_stair_x, y1=step_y, 
                        x2=right_stair_x+STAIR_W, y2=step_y))
entities.append(ent('A-STAI', 'LINE', x1=right_stair_x+STAIR_W, y1=right_stair_y, 
                    x2=right_stair_x+STAIR_W, y2=right_stair_y+ELV_D))

# 楼梯箭头
entities.append(ent('A-TEXT', 'TEXT', x=left_stair_x+200, y=left_stair_y+ELV_D//2, h=2.5, txt='↑上21步'))
entities.append(ent('A-TEXT', 'TEXT', x=right_stair_x+200, y=right_stair_y+ELV_D//2, h=2.5, txt='↓下17步'))

# --- 岛台 (A-FURN) ---
entities.append(ent('A-FURN', 'LINE', x1=ISL_X, y1=ISL_Y, x2=ISL_X+ISL_W, y2=ISL_Y))
entities.append(ent('A-FURN', 'LINE', x1=ISL_X+ISL_W, y1=ISL_Y, x2=ISL_X+ISL_W, y2=ISL_Y+ISL_H))
entities.append(ent('A-FURN', 'LINE', x1=ISL_X+ISL_W, y1=ISL_Y+ISL_H, x2=ISL_X, y2=ISL_Y+ISL_H))
entities.append(ent('A-FURN', 'LINE', x1=ISL_X, y1=ISL_Y+ISL_H, x2=ISL_X, y2=ISL_Y))
# 岛台凳子（4个圆）
for i in range(4):
    sx = ISL_X + ISL_W//5 * (i+1)
    sy = ISL_Y - 150
    entities.append(ent('A-FURN', 'CIRCLE', cx=sx, cy=sy, r=80))

# --- 挑空区 (A-VOID) ---
entities.append(ent('A-VOID', 'LINE', x1=VOID_X, y1=VOID_Y, x2=VOID_X+VOID_W, y2=VOID_Y))
entities.append(ent('A-VOID', 'LINE', x1=VOID_X+VOID_W, y1=VOID_Y, x2=VOID_X+VOID_W, y2=VOID_Y+VOID_H))
entities.append(ent('A-VOID', 'LINE', x1=VOID_X+VOID_W, y1=VOID_Y+VOID_H, x2=VOID_X, y2=VOID_Y+VOID_H))
entities.append(ent('A-VOID', 'LINE', x1=VOID_X, y1=VOID_Y+VOID_H, x2=VOID_X, y2=VOID_Y))
# 挑空斜线
entities.append(ent('A-VOID', 'LINE', x1=VOID_X, y1=VOID_Y, x2=VOID_X+VOID_W, y2=VOID_Y+VOID_H))
entities.append(ent('A-VOID', 'LINE', x1=VOID_X+VOID_W, y1=VOID_Y, x2=VOID_X, y2=VOID_Y+VOID_H))

# --- 厨房设备柜 ---
# 在早餐区左侧
cab_x = BRK_X + 100
cab_y = BRK_Y + 200
cab_w = 300
cab_h = BRK_H - 400
entities.append(ent('A-FURN', 'LINE', x1=cab_x, y1=cab_y, x2=cab_x+cab_w, y2=cab_y))
entities.append(ent('A-FURN', 'LINE', x1=cab_x+cab_w, y1=cab_y, x2=cab_x+cab_w, y2=cab_y+cab_h))
entities.append(ent('A-FURN', 'LINE', x1=cab_x+cab_w, y1=cab_y+cab_h, x2=cab_x, y2=cab_y+cab_h))
entities.append(ent('A-FURN', 'LINE', x1=cab_x, y1=cab_y+cab_h, x2=cab_x, y2=cab_y))

# --- 卫生间设施 ---
# 马桶
toilet_x = WC_X + 400
toilet_y = WC_Y + 300
entities.append(ent('A-FURN', 'CIRCLE', cx=toilet_x, cy=toilet_y, r=180))
entities.append(ent('A-FURN', 'LINE', x1=toilet_x-120, y1=toilet_y-180, x2=toilet_x+120, y2=toilet_y-180))

# 洗手台
sink_x = WC_X + 2800
sink_y = WC_Y + 200
sink_w = 600
sink_h = 400
entities.append(ent('A-FURN', 'LINE', x1=sink_x, y1=sink_y, x2=sink_x+sink_w, y2=sink_y))
entities.append(ent('A-FURN', 'LINE', x1=sink_x+sink_w, y1=sink_y, x2=sink_x+sink_w, y2=sink_y+sink_h))
entities.append(ent('A-FURN', 'LINE', x1=sink_x+sink_w, y1=sink_y+sink_h, x2=sink_x, y2=sink_y+sink_h))
entities.append(ent('A-FURN', 'LINE', x1=sink_x, y1=sink_y+sink_h, x2=sink_x, y2=sink_y))
# 水盆圆
entities.append(ent('A-FURN', 'CIRCLE', cx=sink_x+sink_w//2, cy=sink_y+sink_h//2, r=120))

# --- 钢琴 ---
piano_x = 600
piano_y = 3500
piano_w = 500
piano_h = 400
entities.append(ent('A-FURN', 'LINE', x1=piano_x, y1=piano_y, x2=piano_x+piano_w, y2=piano_y))
entities.append(ent('A-FURN', 'LINE', x1=piano_x+piano_w, y1=piano_y, x2=piano_x+piano_w, y2=piano_y+piano_h))
entities.append(ent('A-FURN', 'LINE', x1=piano_x+piano_w, y1=piano_y+piano_h, x2=piano_x, y2=piano_y+piano_h))
entities.append(ent('A-FURN', 'LINE', x1=piano_x, y1=piano_y+piano_h, x2=piano_x, y2=piano_y))

# --- 尺寸标注 ---
entities.append(ent('A-DIM', 'LINE', x1=0, y1=-200, x2=7000, y2=-200))
entities.append(ent('A-DIM', 'LINE', x1=0, y1=-100, x2=3900, y2=-100))
entities.append(ent('A-DIM', 'LINE', x1=3900, y1=-100, x2=4100, y2=-100))

# --- 文字 ---
texts = [
    (W//2, H-200, '晴碧园晶园26栋拆砌图', 5),
    (3500, 4800, '电梯厅', 3.5),
    (BRK_X+BRK_W//2, BRK_Y+BRK_H-200, '早餐区', 3.5),
    (ISL_X+ISL_W//2, ISL_Y-300, '岛台', 2.5),
    (VOID_X+VOID_W//2, VOID_Y+VOID_H//2, '挑空', 3),
    (WC_X+WC_W//2, WC_Y+WC_H-200, '卫生间', 3.5),
    (WC_X+1000, WC_Y+600, '淋浴', 2.5),
    (CLO_X+200, CLO_Y+CLO_H-200, '衣帽间', 2.5),
    (3800, H-600, '院子', 3),
    (2000, H-600, '硬化地面', 2.5),
    (ELV_X+ELV_W//2+100, ELV_Y-200, '井道净宽1.6m', 2.5),
    (ELV_X+ELV_W+400, ELV_Y+ELV_D//2, '净深1.58m', 2.5),
    (cab_x+50, cab_y+100, '高柜', 2),
    (cab_x+50, cab_y+300, '冰箱', 2),
    (cab_x+50, cab_y+500, '净水', 2),
    (cab_x+50, cab_y+700, '破壁机', 2),
    (cab_x+50, cab_y+900, '咖啡机', 2),
    (cab_x+50, cab_y+1100, '扫地机器人', 2),
    (piano_x+50, piano_y+150, '钢琴', 2.5),
    (piano_x+50, piano_y+300, '留声机', 2),
    (500, 200, '玻璃砖隔墙', 2.5),
    (BRK_X+BRK_W, BRK_Y+BRK_H//2, '玻璃砖隔墙', 2.5),
    (ELV_X+ELV_W+900, 1500, '预留水源', 2),
    (ELV_X+ELV_W+900, 1700, '预留充电桩', 2),
    (W-300, H-400, '预留水龙头', 2),
    (WC_X+WC_W//2, 100, '地漏', 2),
]

for x, y, txt, h in texts:
    entities.append(ent('A-TEXT', 'TEXT', x=x-len(txt)*h*0.3, y=y, h=h, txt=txt))

# ===== 构建 DXF =====
dxf_lines = [
    "0\nSECTION\n2\nHEADER\n0\nENDSEC",
    "0\nSECTION\n2\nTABLES",
    "0\nTABLE\n2\nLAYER\n70\n10",
]
dxf_lines.extend(layers)
dxf_lines.append("0\nENDTAB\n0\nENDSEC")
dxf_lines.append("0\nSECTION\n2\nENTITIES")
dxf_lines.extend(entities)
dxf_lines.append("0\nENDSEC\n0\nEOF")

dxf_path = f'{OUT}/晴碧园拆砌图_重建.dxf'
with open(dxf_path, 'w') as f:
    f.write('\n'.join(dxf_lines))
print(f"✅ DXF: {dxf_path}")

# =============================================
# SVG 可视化
# =============================================

dwg = Drawing(f'{OUT}/晴碧园拆砌图_重建.svg', size=('900px', '750px'))
dwg.add(dwg.rect(insert=(0,0), size=(900,750), fill='#1a1a2e'))

SC = 0.08

def tx(x): return x * SC + 150
def ty(y): return 680 - (y * SC + 40)

# 暗色网格
for x in range(0, W+1, 500):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(H)), stroke='#2a2a4e', stroke_width=0.3))
for y in range(0, H+1, 500):
    dwg.add(dwg.line((tx(0), ty(y)), (tx(W), ty(y)), stroke='#2a2a4e', stroke_width=0.3))

# 房间填充
zones = [
    (0, 0, 7000, 3000, '#1a2a1a', '卫生间区域'),
    (0, 3000, 7000, 5000, '#1a1a2a', '交通枢纽'),
    (500, 5000, 2500, 2000, '#2a1a1a', '早餐区'),
    (4000, 5000, 2500, 2000, '#1a2a2a', '挑空区'),
    (4000, 7000, 2500, 1000, '#2a2a1a', '衣帽间'),
]
for rx, ry, rw, rh, color, label in zones:
    dwg.add(dwg.rect(insert=(tx(rx), ty(ry+rh)), size=(rw*SC, rh*SC), 
              fill=color, fill_opacity=0.5, stroke='none'))

# 外墙（黄色虚线 = EXST）
exst_walls = [(0,0,W,0), (W,0,W,H), (W,H,0,H), (0,H,0,0)]
for x1,y1,x2,y2 in exst_walls:
    dwg.add(dwg.line((tx(x1),ty(y1)), (tx(x2),ty(y2)), stroke='#ccaa00', stroke_width=3, stroke_dasharray='8,4'))

# 内墙（青/绿色）
wall_lines = [
    (0,3000,ELV_X+ELV_W+200,3000), (WC_X+WC_W,0,WC_X+WC_W,3000),
    (WC_X+2000,0,WC_X+2000,3000), (CLO_X,CLO_Y,CLO_X+CLO_W,CLO_Y),
    (CLO_X+CLO_W,CLO_Y,CLO_X+CLO_W,CLO_Y+CLO_H),
]
for x1,y1,x2,y2 in wall_lines:
    dwg.add(dwg.line((tx(x1),ty(y1)), (tx(x2),ty(y2)), stroke='cyan', stroke_width=2.5))

# 玻璃砖隔墙（浅蓝/青）
dwg.add(dwg.line((tx(500),ty(0)), (tx(500),ty(H)), stroke='#40e0d0', stroke_width=2, stroke_dasharray='3,2'))
dwg.add(dwg.line((tx(BRK_X+BRK_W),ty(BRK_Y)), (tx(BRK_X+BRK_W),ty(BRK_Y+BRK_H)), stroke='#40e0d0', stroke_width=2, stroke_dasharray='3,2'))
dwg.add(dwg.line((tx(BRK_X),ty(BRK_Y+BRK_H)), (tx(BRK_X+BRK_W),ty(BRK_Y+BRK_H)), stroke='#40e0d0', stroke_width=2, stroke_dasharray='3,2'))

# 电梯井
dwg.add(dwg.rect(insert=(tx(ELV_X), ty(ELV_Y+ELV_D+200)), 
          size=((ELV_W+200)*SC, (ELV_D+200)*SC), fill='#333', stroke='#888', stroke_width=2))
dwg.add(dwg.rect(insert=(tx(ELV_X+100), ty(ELV_Y+ELV_D+100)), 
          size=(ELV_W*SC, ELV_D*SC), fill='#444', stroke='#aaa', stroke_width=1.5))
# 对角线
dwg.add(dwg.line((tx(ELV_X+100), ty(ELV_Y+100)), (tx(ELV_X+ELV_W+100), ty(ELV_Y+ELV_D+100)), stroke='#aaa', stroke_width=1))
dwg.add(dwg.line((tx(ELV_X+ELV_W+100), ty(ELV_Y+100)), (tx(ELV_X+100), ty(ELV_Y+ELV_D+100)), stroke='#aaa', stroke_width=1))
dwg.add(dwg.text('电梯', insert=(tx(ELV_X+ELV_W//2+100), ty(ELV_Y+ELV_D//2-80)), font_size='10', fill='#ddd', text_anchor='middle'))
dwg.add(dwg.text('1.6×1.58m', insert=(tx(ELV_X+ELV_W//2+100), ty(ELV_Y+ELV_D//2+80)), font_size='7', fill='#aaa', text_anchor='middle'))

# 楼梯（白色线）
for i in range(22):
    step_y = left_stair_y + i * (ELV_D // 21)
    dwg.add(dwg.line((tx(left_stair_x), ty(step_y)), (tx(left_stair_x+STAIR_W), ty(step_y)), stroke='white', stroke_width=0.8))
dwg.add(dwg.line((tx(left_stair_x+STAIR_W), ty(left_stair_y)), (tx(left_stair_x+STAIR_W), ty(left_stair_y+ELV_D)), stroke='white', stroke_width=2))
dwg.add(dwg.text('↑上21步', insert=(tx(left_stair_x+100), ty(left_stair_y+ELV_D//2)), font_size='8', fill='#ff6', text_anchor='middle'))

for i in range(18):
    step_y = right_stair_y + i * (ELV_D // 17)
    dwg.add(dwg.line((tx(right_stair_x), ty(step_y)), (tx(right_stair_x+STAIR_W), ty(step_y)), stroke='white', stroke_width=0.8))
dwg.add(dwg.line((tx(right_stair_x+STAIR_W), ty(right_stair_y)), (tx(right_stair_x+STAIR_W), ty(right_stair_y+ELV_D)), stroke='white', stroke_width=2))
dwg.add(dwg.text('↓下17步', insert=(tx(right_stair_x+100), ty(right_stair_y+ELV_D//2)), font_size='8', fill='#ff6', text_anchor='middle'))

# 岛台 + 凳子
dwg.add(dwg.rect(insert=(tx(ISL_X), ty(ISL_Y+ISL_H)), size=(ISL_W*SC, ISL_H*SC), fill='none', stroke='#f6f', stroke_width=1.5))
for i in range(4):
    sx = ISL_X + ISL_W//5 * (i+1)
    sy = ISL_Y - 150
    dwg.add(dwg.circle(center=(tx(sx), ty(sy)), r=6, fill='none', stroke='#f6f', stroke_width=1))

# 挑空区斜线
dwg.add(dwg.line((tx(VOID_X), ty(VOID_Y)), (tx(VOID_X+VOID_W), ty(VOID_Y+VOID_H)), stroke='#888', stroke_width=0.8, stroke_dasharray='5,3'))
dwg.add(dwg.line((tx(VOID_X+VOID_W), ty(VOID_Y)), (tx(VOID_X), ty(VOID_Y+VOID_H)), stroke='#888', stroke_width=0.8, stroke_dasharray='5,3'))

# 卫生间设施
dwg.add(dwg.circle(center=(tx(toilet_x), ty(toilet_y)), r=14, fill='#555', stroke='cyan', stroke_width=1))
dwg.add(dwg.line((tx(toilet_x-10), ty(toilet_y-14)), (tx(toilet_x+10), ty(toilet_y-14)), stroke='cyan', stroke_width=1.5))
dwg.add(dwg.circle(center=(tx(sink_x+sink_w//2), ty(sink_y+sink_h//2)), r=9, fill='#448', stroke='cyan', stroke_width=1))

# 钢琴
dwg.add(dwg.rect(insert=(tx(piano_x), ty(piano_y+piano_h)), size=(piano_w*SC, piano_h*SC), fill='#553', stroke='#f6f', stroke_width=1.5))

# 尺寸标注
dwg.add(dwg.line((tx(0), ty(-80)), (tx(7000), ty(-80)), stroke='green', stroke_width=1))
dwg.add(dwg.text('7000', insert=(tx(3500), ty(-90)), font_size='9', fill='green', text_anchor='middle'))
dwg.add(dwg.text('3900', insert=(tx(1950), ty(-60)), font_size='8', fill='green', text_anchor='middle'))
dwg.add(dwg.text('200', insert=(tx(3900+100), ty(-60)), font_size='8', fill='green', text_anchor='middle'))

# 文字
text_display = [
    (3500, 4800, '电梯厅', '#fff', 11),
    (BRK_X+BRK_W//2, BRK_Y+BRK_H-200, '早餐区', '#faa', 11),
    (ISL_X+ISL_W//2, ISL_Y-400, '岛台', '#f6f', 9),
    (VOID_X+VOID_W//2, VOID_Y+VOID_H//2, '挑空', '#aaa', 10),
    (WC_X+WC_W//2, WC_Y+WC_H-200, '卫生间', '#0ff', 11),
    (CLO_X+200, CLO_Y+CLO_H-200, '衣帽间', '#ff0', 9),
    (3800, H-400, '院子', '#aa0', 10),
    (2000, H-400, '硬化地面', '#aa0', 8),
    (500, 200, '玻璃砖隔墙', '#40e0d0', 8),
    (piano_x+50, piano_y+150, '钢琴', '#f6f', 8),
    (piano_x+50, piano_y+300, '留声机', '#f6f', 7),
    (ELV_X+ELV_W+900, 1500, '预留水源', '#aaa', 7),
    (ELV_X+ELV_W+900, 1700, '预留充电桩', '#aaa', 7),
    (W-300, H-400, '预留水龙头', '#aaa', 7),
]

for x, y, txt, color, size in text_display:
    dwg.add(dwg.text(txt, insert=(tx(x), ty(y)), font_size=str(size), fill=color, font_family='sans-serif', text_anchor='middle'))

# 图例
leg = 150
for color, label in [('#ccaa00', '保留墙'), ('cyan', '内墙'), ('#40e0d0', '玻璃砖'), ('#888', '电梯井'), ('white', '楼梯'), ('#f6f', '家具')]:
    dwg.add(dwg.rect(insert=(leg, 710), size=(14, 12), fill=color, fill_opacity=0.8))
    dwg.add(dwg.text(label, insert=(leg+18, 720), font_size='8', fill='#ddd'))
    leg += 120

dwg.add(dwg.text('晴碧园晶园26栋拆砌图 · 重建版 | 暗色模式',
          insert=(450, 30), font_size='14', font_weight='bold', fill='#ddd', text_anchor='middle'))

dwg.save()
print(f"✅ SVG: {OUT}/晴碧园拆砌图_重建.svg")
os.system(f'magick convert "{OUT}/晴碧园拆砌图_重建.svg" "{OUT}/晴碧园拆砌图_重建.png" 2>/dev/null')
print(f"✅ PNG: {OUT}/晴碧园拆砌图_重建.png")

# =============================================
# 分析报告
# =============================================
report = f"""╔═══════════════════════════════════════════╗
║   CAD 图纸深度分析报告 #2                   ║
║   晴碧园晶园26栋拆砌图                       ║
╚═══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
一、图纸基本信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
图纸名称：晴碧园晶园26栋拆砌图
图纸类型：拆砌布置图 (现状+改造)
整体布局：别墅/大平层 → 以电梯井为交通核心

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二、功能分区
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
核心区（交通枢纽）：
  ├ 电梯井 — 1.6m×1.58m（净尺寸）
  ├ U型楼梯 — 上21步 / 下17步
  └ 电梯厅 — 连接所有区域

生活区（左侧）：
  ├ 早餐区 — 含岛台(4座)
  ├ 设备柜 — 扫地机/高柜/咖啡机/破壁机/净水/冰箱
  └ 钢琴+留声机 — 休闲娱乐

私密区（下部）：
  ├ 卫生间 — 含淋浴、马桶、洗手台
  └ 地漏标注

公用区（右上）：
  ├ 挑空 — 垂直贯通空间
  ├ 衣帽间
  └ 院子/硬化地面 — 室外区域

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
三、图层分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
观测颜色 → 对应 Guoxin 标准
┌────────┬─────────────┬──────────────────┐
│ 原图色  │ 我的映射      │ 说明              │
├────────┼─────────────┼──────────────────┤
│ 紫色    │ A-WALL       │ 内墙（新的）       │
│ 黄色    │ A-EXST       │ 保留外墙（HIDDEN）│
│ 青色    │ A-GLAS       │ 玻璃砖隔墙        │
│ 灰色    │ A-ELVT       │ 电梯井            │
│ 粉色    │ A-FURN       │ 家具/设备          │
│ 绿色    │ A-DIM        │ 尺寸标注           │
│ 白色    │ A-TEXT       │ 文字说明           │
│ 红色    │ A-DEMO       │ (拆除标记)         │
└────────┴─────────────┴──────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
四、关键学到的知识点
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 电梯井画法
   - 外框=井道结构边
   - 内框=净尺寸（1.6m×1.58m）
   - 交叉对角线=电梯井符号
   - 标注净宽净深而非结构尺寸

2. U型楼梯画法
   - 电梯井两侧各一个梯段
   - 一侧上行（21步），一侧下行（17步）
   - 步数不同说明有错层或层高变化
   - 箭头方向指示走向

3. 玻璃砖隔墙
   - 用虚线或特殊线型表示
   - 文字明确标注"玻璃砖隔墙"
   - 常用在采光不足的空间

4. 拆砌图的特点
   - 包含现状和改造后的对比
   - 设备布置非常详细（从扫地机到咖啡机）
   - 家具电器一起标 → 指导水电定位

5. 高端设计的常见特征
   - 电梯入户（私家电梯）
   - 早餐区岛台（开放式厨房起居）
   - 挑空（复式/别墅）
   - 衣帽间（主卧套房）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
五、与原图的差异分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
由于从截图重建，可能存在以下偏差：
□ 总尺寸可能不够精确（缺失整体轴线总长）
□ 楼梯步数可能需复核
□ 某些细部标注可能遗漏
□ 墙体厚度不统一
□ 玻璃砖墙位置需现场复核

请用 CAD看图王 打开 DXF，对比原图告诉我哪里不对
→ 每一次修正都是最好的学习 🐾

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
分析完成时间：2026-07-11 15:10
CAD Master - OpenClaw AI分析引擎 v2.0
"""

with open(f'{OUT}/分析报告.md', 'w') as f:
    f.write(report)
print(f"✅ 分析报告: {OUT}/分析报告.md")
print(f"\n📋 重建完成！{len(entities)}个实体，{len(layers)}个图层")
print(f"   用 CAD看图王 打开 DXF 对比原图")
print(f"   告诉我哪里对哪里不对，就是最好的教学 🐾")
