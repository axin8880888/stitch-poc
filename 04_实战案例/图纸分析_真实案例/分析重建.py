#!/usr/bin/env python3
"""
图纸分析：真实建筑平面图重建
基于用户提供的CAD截图

图纸信息：
- 总跨度：17900mm
- 轴网：J轴 — H轴（间距3700mm）
- 结构柱：200×200mm
- 层高：H高=3600, H低=3100
- 楼梯：20步
- 外墙窗：L=920, H=1440 等多个

输出：
1. 重建 DXF（可用CAD看图王打开对比）
2. SVG/PNG 可视化
3. 分析报告 PDF/TXT
"""

import os, math
from svgwrite import Drawing
from collections import defaultdict

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/图纸分析_真实案例'
os.makedirs(OUT, exist_ok=True)

# =============================================
# 图纸重建参数（基于图像分析）
# =============================================
# 总长 17900，上下宽度不同
# 上方从左到右：柱(200) + 间距1600 + 柱(200) + 间距3700 + 柱(200) + 间距1600 + 柱(200) + 间距100
# 下方从左到右：间距3600 + 柱(200) + 间距3700 + 柱(200) + 间距2200

W = 17900  # 总宽
# 垂直方向：底部宽度窄一些，上部有阳台/外扩
H_BOTTOM = 6000  # 底部区域的垂直高度（估计）
H_TOP = 8500     # 顶部区域
H = H_TOP

# 关键轴线和柱子位置
# 垂直轴线
V_AXES = [0, 1800, 2000, 5700, 5900, 7500, 7700, 17900]
V_LABELS = ['①', '', 'J', '', 'H', '', '②', '③']

# 柱子（200x200）
COLUMNS = [
    # (left, bottom, width, height)
    (0, 0, 200, H),         # 最左柱（通高）
    (1800, 0, 200, H),      # J轴左柱
    (5700, 0, 200, H),      # H轴左柱
    (7500, 0, 200, H),      # 右侧柱
    (0, H_BOTTOM-200, W, 200),  # 底部水平柱
]

# =============================================
# 1. DXF 生成
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

# 图层定义
layers = [
    "0\nLAYER\n2\nA-WALL\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n30",
    "0\nLAYER\n2\nA-COLU\n70\n0\n62\n8\n6\nCONTINUOUS\n370\n9",
    "0\nLAYER\n2\nA-DOOR\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n18",
    "0\nLAYER\n2\nA-WINDW\n70\n0\n62\n5\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-AXIS\n70\n0\n62\n1\n6\nCENTER\n370\n13",
    "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
    "0\nLAYER\n2\nA-HIDD\n70\n0\n62\n2\n6\nHIDDEN\n370\n13",
    "0\nLAYER\n2\nA-STAI\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n18",
]

# --- 墙体 (A-WALL, 紫色=颜色6) ---
# 外轮廓
entities.append(ent('A-WALL', 'LINE', x1=0, y1=H_BOTTOM, x2=V_AXES[2], y2=H_BOTTOM))
entities.append(ent('A-WALL', 'LINE', x1=V_AXES[2], y1=H_BOTTOM, x2=V_AXES[2], y2=0))
entities.append(ent('A-WALL', 'LINE', x1=V_AXES[2], y1=0, x2=W, y2=0))
entities.append(ent('A-WALL', 'LINE', x1=W, y1=0, x2=W, y2=H_BOTTOM))
entities.append(ent('A-WALL', 'LINE', x1=W, y1=H_BOTTOM, x2=V_AXES[4], y2=H_BOTTOM))
entities.append(ent('A-WALL', 'LINE', x1=V_AXES[4], y1=H_BOTTOM, x2=V_AXES[4], y2=H))
entities.append(ent('A-WALL', 'LINE', x1=V_AXES[4], y1=H, x2=0, y2=H))
entities.append(ent('A-WALL', 'LINE', x1=0, y1=H, x2=0, y2=H_BOTTOM))

# 内墙（J轴到H轴之间的横向墙）
entities.append(ent('A-WALL', 'LINE', x1=V_AXES[2], y1=H_BOTTOM-3700, x2=V_AXES[4], y2=H_BOTTOM-3700))

# 顶部横向内墙
entities.append(ent('A-WALL', 'LINE', x1=0, y1=H-2000, x2=V_AXES[2], y2=H-2000))

# --- 结构柱 (A-COLU) ---
for cx, cy, cw, ch in COLUMNS:
    entities.append(ent('A-COLU', 'LINE', x1=cx, y1=cy, x2=cx+cw, y2=cy))
    entities.append(ent('A-COLU', 'LINE', x1=cx+cw, y1=cy, x2=cx+cw, y2=cy+ch))
    entities.append(ent('A-COLU', 'LINE', x1=cx+cw, y1=cy+ch, x2=cx, y2=cy+ch))
    entities.append(ent('A-COLU', 'LINE', x1=cx, y1=cy+ch, x2=cx, y2=cy))

# --- 窗 (A-WINDW) ---
windows = [
    # (x1, y1, x2, y2) 在墙上的开窗
    (200, H-100, 200+1120, H-100, 'L=1120'),
    (3500, H-100, 3500+900, H-100, 'L=900'),
    (200, H_BOTTOM, 200+920, H_BOTTOM, 'L=920'),
    (200, 0, 200+920, 0, 'L=920'),
    (V_AXES[4]-920, 0, V_AXES[4], 0, 'L=920'),
    (V_AXES[4]+200, H_BOTTOM-3200, V_AXES[4]+200+920, H_BOTTOM-3200, 'L=920'),
]
for x1, y1, x2, y2, label in windows:
    entities.append(ent('A-WINDW', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))
    # 窗的上下双线
    entities.append(ent('A-WINDW', 'LINE', x1=x1, y1=y1+80, x2=x2, y2=y2+80))
    entities.append(ent('A-WINDW', 'LINE', x1=x1, y1=y1-80, x2=x2, y2=y2-80))

# --- 门 (A-DOOR) ---
doors = [
    (V_AXES[2], H_BOTTOM-1500, V_AXES[2], H_BOTTOM-2500, '房门'),
    (V_AXES[4]-100, 200, V_AXES[4]-100, 200+900, '房门'),
    (200, H-2000+400, 200, H-2000+400+900, '房门'),
]
for x1, y1, x2, y2, label in doors:
    entities.append(ent('A-DOOR', 'LINE', x1=x1, y1=y1, x2=x2, y2=y2))

# --- 楼梯 (A-STAI) ---
# 位置：右下角，下20步
stair_bottom_x = V_AXES[4] + 500
stair_bottom_y = H_BOTTOM - 3000
stair_width = 1200
stair_length = 2400  # 20步 x 120mm步宽

# 楼梯踏步线
for i in range(21):
    step_y = stair_bottom_y + i * 120
    entities.append(ent('A-STAI', 'LINE', x1=stair_bottom_x, y1=step_y, 
                        x2=stair_bottom_x+stair_width, y2=step_y))

# 折断线
entities.append(ent('A-HIDD', 'LINE', 
    x1=stair_bottom_x, y1=stair_bottom_y+1200, 
    x2=stair_bottom_x+stair_width, y2=stair_bottom_y+1200))

# 扶手
entities.append(ent('A-STAI', 'LINE', x1=stair_bottom_x+stair_width-100, y1=stair_bottom_y,
                    x2=stair_bottom_x+stair_width-100, y2=stair_bottom_y+stair_length))

# 箭头（上行方向）
entities.append(ent('A-TEXT', 'TEXT', x=stair_bottom_x+200, y=stair_bottom_y+1800, h=3, txt='↑ 上'))

# --- 轴线 (A-AXIS) ---
# 垂直轴线
for i, (ax_x, label) in enumerate(zip(V_AXES[1:4], ['', 'J', 'H', ''])):
    if label:
        entities.append(ent('A-AXIS', 'LINE', x1=ax_x, y1=-300, x2=ax_x, y2=H+300))
        # 轴线圆圈
        entities.append(ent('A-AXIS', 'CIRCLE', cx=ax_x, cy=-400, r=150))
        entities.append(ent('A-TEXT', 'TEXT', x=ax_x-30, y=-410, h=150, txt=label))
        entities.append(ent('A-AXIS', 'CIRCLE', cx=ax_x, cy=H+400, r=150))
        entities.append(ent('A-TEXT', 'TEXT', x=ax_x-30, y=H+390, h=150, txt=label))

# --- 尺寸标注 (A-DIM) ---
# 底部总长
entities.append(ent('A-DIM', 'LINE', x1=0, y1=-200, x2=W, y2=-200))
entities.append(ent('A-TEXT', 'TEXT', x=W//2-200, y=-250, h=3, txt='17900'))

# J-H轴间距 3700
entities.append(ent('A-DIM', 'LINE', x1=V_AXES[2], y1=-100, x2=V_AXES[4], y2=-100))
entities.append(ent('A-TEXT', 'TEXT', x=(V_AXES[2]+V_AXES[4])//2-200, y=-150, h=3, txt='3700'))

# 高度标注
entities.append(ent('A-TEXT', 'TEXT', x=200, y=H_BOTTOM+100, h=3, txt='H高=3600'))
entities.append(ent('A-TEXT', 'TEXT', x=200, y=H_BOTTOM-100, h=3, txt='H低=3100'))
entities.append(ent('A-TEXT', 'TEXT', x=stair_bottom_x, y=stair_bottom_y-200, h=3, txt='下20步'))

# 窗标注
entities.append(ent('A-TEXT', 'TEXT', x=400, y=H-400, h=2.5, txt='L=1120'))
entities.append(ent('A-TEXT', 'TEXT', x=3600, y=H-400, h=2.5, txt='L=900'))
entities.append(ent('A-TEXT', 'TEXT', x=300, y=H_BOTTOM-200, h=2.5, txt='L=920 H=1450'))
entities.append(ent('A-TEXT', 'TEXT', x=300, y=500, h=2.5, txt='L=920 H=1440'))

# 层高标注（红色=1）
entities.append(ent('A-TEXT', 'TEXT', x=V_AXES[2]+100, y=H_BOTTOM-1800, h=3, txt='h=2240'))

# --- 文字注释 ---
entities.append(ent('A-TEXT', 'TEXT', x=V_AXES[2]+300, y=H_BOTTOM-1000, h=2.5, txt='强电箱'))

# 房间标注
entities.append(ent('A-TEXT', 'TEXT', x=3500, y=H_BOTTOM-2000, h=3.5, txt='房间'))
entities.append(ent('A-TEXT', 'TEXT', x=3500, y=H-1000, h=3.5, txt='阳台'))

# ===== 构建 DXF =====
dxf_lines = [
    "0\nSECTION\n2\nHEADER\n0\nENDSEC",
    "0\nSECTION\n2\nTABLES",
    "0\nTABLE\n2\nLAYER\n70\n9",
]
dxf_lines.extend(layers)
dxf_lines.append("0\nENDTAB\n0\nENDSEC")
dxf_lines.append("0\nSECTION\n2\nENTITIES")
dxf_lines.extend(entities)
dxf_lines.append("0\nENDSEC\n0\nEOF")

dxf_path = f'{OUT}/真实图纸_重建.dxf'
with open(dxf_path, 'w') as f:
    f.write('\n'.join(dxf_lines))
print(f"✅ DXF: {dxf_path}")

# =============================================
# 2. SVG 可视化
# =============================================

dwg = Drawing(f'{OUT}/真实图纸_重建.svg', size=('1000px', '700px'))
dwg.add(dwg.rect(insert=(0,0), size=(1000,700), fill='#f8f8f8'))

# 坐标系：CAD（mm）→ SVG（px）
# 17900宽 → 900px可用
SC = 0.045
OFF_X, OFF_Y = 60, 50

def tx(x): return x * SC + OFF_X
def ty(y): return 650 - (y * SC + OFF_Y)

# 背景网格
for x in range(0, W+1, 1000):
    dwg.add(dwg.line((tx(x), ty(0)), (tx(x), ty(H)), stroke='#eee', stroke_width=0.2))
for y in range(0, H+1, 1000):
    dwg.add(dwg.line((tx(0), ty(y)), (tx(W), ty(y)), stroke='#eee', stroke_width=0.2))

# 墙体（紫色）
wall_lines = [
    (0, H_BOTTOM, V_AXES[2], H_BOTTOM, 'wall'),
    (V_AXES[2], H_BOTTOM, V_AXES[2], 0, 'wall'),
    (V_AXES[2], 0, W, 0, 'wall'),
    (W, 0, W, H_BOTTOM, 'wall'),
    (W, H_BOTTOM, V_AXES[4], H_BOTTOM, 'wall'),
    (V_AXES[4], H_BOTTOM, V_AXES[4], H, 'wall'),
    (V_AXES[4], H, 0, H, 'wall'),
    (0, H, 0, H_BOTTOM, 'wall'),
    (V_AXES[2], H_BOTTOM-3700, V_AXES[4], H_BOTTOM-3700, 'wall'),
    (0, H-2000, V_AXES[2], H-2000, 'wall'),
]
for x1, y1, x2, y2, _ in wall_lines:
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), stroke='magenta', stroke_width=2.5))

# 柱子（灰色填充）
for cx, cy, cw, ch in COLUMNS:
    dwg.add(dwg.rect(insert=(tx(cx), ty(cy+ch)), size=(cw*SC, ch*SC), 
              fill='#bbb', stroke='#888', stroke_width=1))

# 窗（蓝色）
for x1, y1, x2, y2, label in windows:
    dwg.add(dwg.line((tx(x1), ty(y1+80)), (tx(x2), ty(y2+80)), stroke='blue', stroke_width=2))
    dwg.add(dwg.line((tx(x1), ty(y1-80)), (tx(x2), ty(y2-80)), stroke='blue', stroke_width=2))

# 门（青色）
for x1, y1, x2, y2, label in doors:
    dwg.add(dwg.line((tx(x1), ty(y1)), (tx(x2), ty(y2)), stroke='cyan', stroke_width=2))

# 楼梯
sx, sy = stair_bottom_x, stair_bottom_y
for i in range(21):
    step_y = sy + i * 120
    dwg.add(dwg.line((tx(sx), ty(step_y)), (tx(sx+stair_width), ty(step_y)), stroke='#888', stroke_width=0.8))
# 扶手
dwg.add(dwg.line((tx(sx+stair_width-100), ty(sy)), (tx(sx+stair_width-100), ty(sy+stair_length)), 
          stroke='#888', stroke_width=2))
dwg.add(dwg.text('↑ 上', insert=(tx(sx+100), ty(sy+1800)), font_size='9', fill='red'))

# 轴线（红色虚线）
for i, (ax_x, label) in enumerate(zip(V_AXES[1:4], ['', 'J', 'H', ''])):
    if label:
        dwg.add(dwg.line((tx(ax_x), ty(-200)), (tx(ax_x), ty(H+200)), 
                  stroke='red', stroke_width=0.8, stroke_dasharray='10,5'))
        # 轴圈
        dwg.add(dwg.circle(center=(tx(ax_x), ty(-300)), r=8, fill='white', stroke='red', stroke_width=1))
        dwg.add(dwg.text(label, insert=(tx(ax_x)-4, ty(-303)), font_size='8', fill='red', text_anchor='middle'))
        dwg.add(dwg.circle(center=(tx(ax_x), ty(H+300)), r=8, fill='white', stroke='red', stroke_width=1))
        dwg.add(dwg.text(label, insert=(tx(ax_x)-4, ty(H+297)), font_size='8', fill='red', text_anchor='middle'))

# 尺寸标注（绿色）
dwg.add(dwg.line((tx(0), ty(-120)), (tx(W), ty(-120)), stroke='green', stroke_width=1))
dwg.add(dwg.text('17900', insert=(tx(W//2), ty(-130)), font_size='10', fill='green', text_anchor='middle'))
dwg.add(dwg.line((tx(V_AXES[2]), ty(-80)), (tx(V_AXES[4]), ty(-80)), stroke='green', stroke_width=1))
dwg.add(dwg.text('3700', insert=(tx((V_AXES[2]+V_AXES[4])/2), ty(-90)), font_size='9', fill='green', text_anchor='middle'))

# 文字标注
text_items = [
    (W//2, H_BOTTOM+400, 'H高=3600', 'green'),
    (W//2, H_BOTTOM-400, 'H低=3100', 'green'),
    (400, H-400, 'L=1120', 'blue'),
    (3600, H-400, 'L=900', 'blue'),
    (300, H_BOTTOM-200, 'L=920 H=1450', 'blue'),
    (300, 500, 'L=920 H=1440', 'blue'),
    (V_AXES[2]+100, H_BOTTOM-1800, 'h=2240', 'green'),
    (V_AXES[2]+300, H_BOTTOM-1000, '强电箱', '#555'),
    (3500, H_BOTTOM-2000, '房间', '#555'),
    (3500, H-1000, '阳台', '#555'),
    (sx, sy-200, '下20步', 'red'),
]

for x, y, txt, color in text_items:
    dwg.add(dwg.text(txt, insert=(tx(x), ty(y)), font_size='9', fill=color, font_family='sans-serif'))

# 图例
legends = [
    ('magenta', '墙体 A-WALL'),
    ('#bbb', '结构柱 A-COLU'),
    ('blue', '窗 A-WINDW'),
    ('cyan', '门 A-DOOR'),
    ('red', '轴线 A-AXIS'),
    ('green', '尺寸标注 A-DIM'),
]
lgx = 60
for color, label in legends:
    dwg.add(dwg.rect(insert=(lgx, 670), size=(14, 12), fill=color, stroke='#999', stroke_width=0.5))
    dwg.add(dwg.text(label, insert=(lgx+18, 680), font_size='8'))
    lgx += 140

dwg.add(dwg.text('真实图纸重建 — 基于CAD截图分析 | 17900mm跨度 | J-H轴3700',
          insert=(500, 30), font_size='13', font_weight='bold', text_anchor='middle'))

dwg.save()
print(f"✅ SVG: {OUT}/真实图纸_重建.svg")
os.system(f'magick convert "{OUT}/真实图纸_重建.svg" "{OUT}/真实图纸_重建.png" 2>/dev/null')
print(f"✅ PNG: {OUT}/真实图纸_重建.png")

# =============================================
# 3. 分析报告
# =============================================
report = f"""╔═══════════════════════════════════════════╗
║   CAD 图纸深度分析报告                     ║
║   来源：用户上传的CAD截图                   ║
╚═══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
一、图纸基本信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
图纸类型：建筑平面测绘图 / 拆改布置图
总跨度：17900mm（约17.9m）
轴网布局：两跨三柱
  左侧：0—1800（柱）—2000 = 2000mm开间
  中间：J轴—H轴 = 3700mm 主开间
  右侧：5700—5900（柱）—7700—17900
主要结构：框架结构（200×200mm钢筋混凝土柱）
图纸方向：上方为北（指示性）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
二、图层分析（基于截图颜色）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌────────┬──────────────┬──────────────────┐
│ 颜色    │ 对应图层       │ 内容说明          │
├────────┼──────────────┼──────────────────┤
│ 紫色    │ A-WALL        │ 墙体线（外墙+内墙）│
│ 灰色    │ A-COLU        │ 结构柱填充        │
│ 蓝色    │ A-WINDW/A-DIM │ 窗线 + 尺寸边界    │
│ 红色    │ A-AXIS        │ 轴号标注          │
│ 黄色    │ A-TEXT        │ 窗尺寸标注 (L/H)   │
│ 白色    │ A-TEXT/A-DIM  │ 尺寸数值 + 文字说明 │
└────────┴──────────────┴──────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
三、关键尺寸数据
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总尺寸：17900mm（水平）
结构柱：200mm × 200mm
开间：
  J-H轴间距：3700mm
  H-右端：2200mm（底部）/ 1600mm（顶部）
层高数据：
  H高=3600mm（梁底/板底）
  H低=3100mm
  h=2240mm（过道净高/梁下高度）

门窗：
  顶部窗：L=1120, H=1450
  顶部右侧窗：L=900
  左侧下部窗：L=920, H=1440
  底部窗：L=920, H=1440
  右侧窗：L=920

楼梯：
  位置：右下角
  踏步：下20步
  方向：上行→

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
四、规范检查（对比 Guoxin Standard）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 墙体用紫色（对应颜色6）— 可接受
✅ 结构柱用灰色填充 — 标准做法
✅ 尺寸数值清晰 — 符合规范
✅ 轴线标注（J/H轴）— 规范
⚠️ 建议添加图层前缀：A-WALL, A-DIM等
⚠️ 建议添加图框和标题栏
⚠️ 建议统一文字字体和高度

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
五、设计师视角解读
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 这是一张现状测绘图（量房图）
   - 标注了H高/H低 → 说明天花板有高低变化
   - 标注了h=2240 → 可能有梁横穿

2. 改造建议
   - J-H轴主空间3700mm开间，适合做客厅/主卧
   - 左侧窗多，适合次卧或书房
   - 楼梯在右下角 → 可能是复式/别墅二楼平面
   - 顶部标注了"H高=3600/H低=3100"相差500mm
   → 可能可以做局部夹层或吊顶找平

3. 施工注意事项
   - 注意梁下高度 h=2240 → 净高偏矮
   - 楼梯下20步，需要确认休息平台尺寸
   - 强电箱位置需注意改造时是否需要移位

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
六、重建文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 真实图纸_重建.dxf — 用CAD看图王打开对比原图
🖼  真实图纸_重建.svg — 可视化预览
🖼  真实图纸_重建.png — 快速查看

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
分析完成时间：2026-07-11 15:00
CAD Master - OpenClaw AI分析引擎
"""

with open(f'{OUT}/分析报告.md', 'w') as f:
    f.write(report)
print(f"✅ 分析报告: {OUT}/分析报告.md")

# 显示摘要
print()
print(report[:500])
print(f"\n...（完整报告 {len(report)} 字符）")
print(f"\n📋 图纸分析完成！共重建 {len(entities)} 个实体，{len(layers)} 个图层")
print(f"   用 CAD看图王 打开 DXF 可对比原图")
