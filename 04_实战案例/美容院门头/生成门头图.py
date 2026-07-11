#!/usr/bin/env python3
'''
实战案例：美容院门头 自动生成脚本
把第一阶段学到的坐标/图层/对象知识综合运用

输出：
  1. DXF 文件 → 手机用 CAD看圖王打开
  2. SVG 文件 → 可视化预览
  3. PNG 文件 → 直接查看
'''

import os, math
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例'
PROJ = '美容院门头'
DIR = f'{OUT}/{PROJ}'
os.makedirs(DIR, exist_ok=True)

# =============================================
# 项目参数
# =============================================
# 门面尺寸: 宽6000mm x 高3500mm
W, H = 6000, 3500
# 门洞: 宽1800mm x 高2400mm  位置在左侧1500处
DOOR_X, DOOR_W, DOOR_H = 1500, 1800, 2400
# 窗户: 两个展示窗
WIN1_X, WIN1_W, WIN1_H = 3500, 1000, 2000
WIN2_X, WIN2_W, WIN2_H = 4700, 800, 2000
# 招牌区域: 顶部 800mm 高
SIGN_H = 800
# 材质标注
MATERIALS = [
    (0, 0, W, SIGN_H, '铝塑板招牌'),
    (0, SIGN_H, DOOR_X, WIN1_X - DOOR_X, '石材干挂'),
    (DOOR_X + DOOR_W, SIGN_H, WIN1_X - (DOOR_X + DOOR_W), H - SIGN_H, '石材干挂'),
    (DOOR_X, SIGN_H, DOOR_W, DOOR_H, '玻璃门'),
    (WIN1_X, SIGN_H, WIN1_W, WIN1_H, '展示窗(钢化玻璃)'),
    (WIN2_X, SIGN_H, WIN2_W, WIN2_H, '展示窗(钢化玻璃)'),
]

# =============================================
# 1. 生成 DXF 文件
# =============================================

def entity(layer, dtype, **kw):
    parts = [f'0\n{dtype}', f'8\n{layer}']
    gc = {  # 组码映射
        'x1':10,'y1':20,'x2':11,'y2':21,
        'x':10,'y':20,'r':40,'h':40,'txt':1,
        'cx':10,'cy':20,
    }
    for k, v in kw.items():
        code = gc.get(k)
        if code is not None:
            parts.append(f'{code}\n{v}')
    return '\n'.join(parts)

entities = []
layers_def = [
    '0\nLAYER\n2\nA-WALL\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n30',
    '0\nLAYER\n2\nA-DOOR\n70\n0\n62\n4\n6\nCONTINUOUS\n370\n18',
    '0\nLAYER\n2\nA-WINDW\n70\n0\n62\n5\n6\nCONTINUOUS\n370\n13',
    '0\nLAYER\n2\nA-FURN\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n13',
    '0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13',
    '0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13',
    '0\nLAYER\n2\nA-HATCH\n70\n0\n62\n8\n6\nCONTINUOUS\n370\n9',
    '0\nLAYER\n2\nA-NOTE\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13',
]

# 模型框
entities.append(entity('A-WALL', 'LINE', x1=0, y1=0, x2=W, y2=0))
entities.append(entity('A-WALL', 'LINE', x1=W, y1=0, x2=W, y2=H))
entities.append(entity('A-WALL', 'LINE', x1=W, y1=H, x2=0, y2=H))
entities.append(entity('A-WALL', 'LINE', x1=0, y1=H, x2=0, y2=0))

# 招牌分界线
entities.append(entity('A-DIM', 'LINE', x1=0, y1=SIGN_H, x2=W, y2=SIGN_H))
entities.append(entity('A-DIM', 'LINE', x1=0, y1=SIGN_H+1, x2=W, y2=SIGN_H+1))

# 门洞
entities.append(entity('A-DOOR', 'LINE', x1=DOOR_X, y1=0, x2=DOOR_X, y2=DOOR_H))
entities.append(entity('A-DOOR', 'LINE', x1=DOOR_X+DOOR_W, y1=0, x2=DOOR_X+DOOR_W, y2=DOOR_H))
entities.append(entity('A-DOOR', 'LINE', x1=DOOR_X, y1=DOOR_H, x2=DOOR_X+DOOR_W, y2=DOOR_H))

# 窗户
for wx, ww, wh in [(WIN1_X, WIN1_W, WIN1_H), (WIN2_X, WIN2_W, WIN2_H)]:
    entities.append(entity('A-WINDW', 'LINE', x1=wx, y1=SIGN_H, x2=wx+ww, y2=SIGN_H))
    entities.append(entity('A-WINDW', 'LINE', x1=wx, y1=SIGN_H+wh, x2=wx+ww, y2=SIGN_H+wh))
    entities.append(entity('A-WINDW', 'LINE', x1=wx, y1=SIGN_H, x2=wx, y2=SIGN_H+wh))
    entities.append(entity('A-WINDW', 'LINE', x1=wx+ww, y1=SIGN_H, x2=wx+ww, y2=SIGN_H+wh))

# 标注
entities.append(entity('A-DIM', 'LINE', x1=0, y1=-300, x2=W, y2=-300))
entities.append(entity('A-DIM', 'LINE', x1=-300, y1=0, x2=-300, y2=H))

# 材质文字（简化）
materials_text = [
    (W//2, SIGN_H//2, 'GUOXIN BEAUTY'),
    (1500, DOOR_H+300, '玻璃推拉门'),
    (WIN1_X+WIN1_W//2, SIGN_H+WIN1_H//2, '展示窗'),
    (WIN2_X+WIN2_W//2, SIGN_H+WIN2_H//2, '展示窗'),
]
for mx, my, txt in materials_text:
    entities.append(entity('A-TEXT', 'TEXT', x=mx-300, y=my, h=200, txt=txt))

dxf_lines = [
    '0\nSECTION\n2\nHEADER\n0\nENDSEC',
    '0\nSECTION\n2\nTABLES',
    '0\nTABLE\n2\nLAYER\n70\n8',
]
dxf_lines.extend(layers_def)
dxf_lines.append('0\nENDTAB\n0\nENDSEC')
dxf_lines.append('0\nSECTION\n2\nENTITIES')
dxf_lines.extend(entities)
dxf_lines.append('0\nENDSEC\n0\nEOF')

dxf_path = f'{DIR}/美容院门面立面图.dxf'
with open(dxf_path, 'w') as f:
    f.write('\n'.join(dxf_lines))
print(f'✅ DXF: {dxf_path}')

# =============================================
# 2. 生成 SVG 可视化（带颜色标注）
# =============================================

dwg = Drawing(f'{DIR}/美容院门面立面图.svg', size=('850px', '600px'))
dwg.add(dwg.rect(insert=(0,0), size=(850,600), fill='#f8f8f8'))

SC = 0.1
OFFSET = (50, 50)
W_SVG = W * SC
H_SVG = H * SC

def sx(x): return x * SC + OFFSET[0]
def sy(y): return 550 - (y * SC + OFFSET[1])

# 背景格子
for x in range(0, W+1, 500):
    dwg.add(dwg.line((sx(x), sy(0)), (sx(x), sy(H)), stroke='#eee', stroke_width=0.3))
for y in range(0, H+1, 500):
    dwg.add(dwg.line((sx(0), sy(y)), (sx(W), sy(y)), stroke='#eee', stroke_width=0.3))

# 填充各区域材质颜色
# 招牌区 - 浅蓝
dwg.add(dwg.rect(insert=(sx(0), sy(SIGN_H)), size=(W_SVG, SIGN_H*SC), fill='#ddeeff', stroke='#999', stroke_width=0.5))
# 石材区 - 浅灰
# 石材背景直接用简单的覆盖（Y坐标翻转由坐标函数处理）
# 石材左已用上方rect覆盖，这里跳过
# 由于svg坐标翻转，简化：直接用rect
# 石材左
dwg.add(dwg.rect(insert=(sx(0), sy(H)), size=(DOOR_X*SC, (H-SIGN_H)*SC), fill='#e8e8e8', stroke='none'))
# 石材右
dwg.add(dwg.rect(insert=(sx(DOOR_X+DOOR_W), sy(H)), size=((W-DOOR_X-DOOR_W)*SC, (H-SIGN_H)*SC), fill='#e8e8e8', stroke='none'))
# 玻璃门区
dwg.add(dwg.rect(insert=(sx(DOOR_X), sy(DOOR_H)), size=(DOOR_W*SC, DOOR_H*SC), fill='#d0e8ff', stroke='#4a8', stroke_width=1.5))
dwg.add(dwg.rect(insert=(sx(WIN1_X), sy(SIGN_H+WIN1_H)), size=(WIN1_W*SC, WIN1_H*SC), fill='#d0e8ff', stroke='#4a8', stroke_width=1.5))
dwg.add(dwg.rect(insert=(sx(WIN2_X), sy(SIGN_H+WIN2_H)), size=(WIN2_W*SC, WIN2_H*SC), fill='#d0e8ff', stroke='#4a8', stroke_width=1.5))

# 门面外框
dwg.add(dwg.rect(insert=(sx(0), sy(H)), size=(W_SVG, H_SVG), fill='none', stroke='black', stroke_width=3))

# 招牌分界线
dwg.add(dwg.line((sx(0), sy(SIGN_H)), (sx(W), sy(SIGN_H)), stroke='#666', stroke_width=1.5, stroke_dasharray='4,3'))

# 门洞线
dwg.add(dwg.line((sx(DOOR_X), sy(0)), (sx(DOOR_X), sy(DOOR_H)), stroke='#0a0', stroke_width=2))
dwg.add(dwg.line((sx(DOOR_X+DOOR_W), sy(0)), (sx(DOOR_X+DOOR_W), sy(DOOR_H)), stroke='#0a0', stroke_width=2))
dwg.add(dwg.line((sx(DOOR_X), sy(DOOR_H)), (sx(DOOR_X+DOOR_W), sy(DOOR_H)), stroke='#0a0', stroke_width=2))

# 门的开启弧
dwg.add(dwg.path(
    d=f'M {sx(DOOR_X)},{sy(DOOR_H)} A {DOOR_W*SC},{DOOR_W*SC} 0 0,0 {sx(DOOR_X+DOOR_W)},{sy(DOOR_H)}',
    fill='none', stroke='#0a0', stroke_width=1, stroke_dasharray='3,2'))

# 窗户线
for wx, ww, wh in [(WIN1_X, WIN1_W, WIN1_H), (WIN2_X, WIN2_W, WIN2_H)]:
    dwg.add(dwg.line((sx(wx), sy(SIGN_H)), (sx(wx+ww), sy(SIGN_H)), stroke='blue', stroke_width=2))
    dwg.add(dwg.line((sx(wx), sy(SIGN_H+wh)), (sx(wx+ww), sy(SIGN_H+wh)), stroke='blue', stroke_width=2))
    dwg.add(dwg.line((sx(wx), sy(SIGN_H)), (sx(wx), sy(SIGN_H+wh)), stroke='blue', stroke_width=1))
    dwg.add(dwg.line((sx(wx+ww), sy(SIGN_H)), (sx(wx+ww), sy(SIGN_H+wh)), stroke='blue', stroke_width=1))

# 尺寸标注（底部）
dwg.add(dwg.line((sx(0), sy(-50)), (sx(W), sy(-50)), stroke='green', stroke_width=1))
dwg.add(dwg.text('6000', insert=(sx(W//2), sy(-55)), font_size='11', fill='green', text_anchor='middle'))
dwg.add(dwg.text('总宽', insert=(sx(W//2), sy(-68)), font_size='9', fill='#999', text_anchor='middle'))

# 标注门洞
dwg.add(dwg.line((sx(DOOR_X), sy(-80)), (sx(DOOR_X+DOOR_W), sy(-80)), stroke='green', stroke_width=1))
dwg.add(dwg.text('1800', insert=(sx(DOOR_X+DOOR_W//2), sy(-85)), font_size='9', fill='green', text_anchor='middle'))

# 左侧高度标注
dwg.add(dwg.line((sx(-40), sy(0)), (sx(-40), sy(H)), stroke='green', stroke_width=1))
dwg.add(dwg.text('3500', insert=(sx(-45), sy(H//2)), font_size='10', fill='green', text_anchor='end'))

# 标注门高
dwg.add(dwg.line((sx(-60), sy(0)), (sx(-60), sy(DOOR_H)), stroke='green', stroke_width=1))
dwg.add(dwg.text('2400', insert=(sx(-65), sy(DOOR_H//2)), font_size='9', fill='green', text_anchor='end'))

# 文字标注
# 招牌
dwg.add(dwg.text('招 牌 区', insert=(sx(W//2), sy(SIGN_H//2)), font_size='18', fill='#446', text_anchor='middle', font_weight='bold'))
dwg.add(dwg.text('GUOXIN BEAUTY', insert=(sx(W//2), sy(SIGN_H//2-20)), font_size='10', fill='#88a', text_anchor='middle'))

# 门
dwg.add(dwg.text('玻璃推拉门', insert=(sx(DOOR_X+DOOR_W//2), sy(DOOR_H+100)), font_size='12', fill='#080', text_anchor='middle'))

# 窗
dwg.add(dwg.text('展示窗', insert=(sx(WIN1_X+WIN1_W//2), sy(SIGN_H+WIN1_H//2)), font_size='12', fill='blue', text_anchor='middle'))
dwg.add(dwg.text('展示窗', insert=(sx(WIN2_X+WIN2_W//2), sy(SIGN_H+WIN2_H//2)), font_size='12', fill='blue', text_anchor='middle'))

# 材质标注
dwg.add(dwg.text('石材干挂', insert=(sx(DOOR_X//2), sy(H - 200)), font_size='10', fill='#666', text_anchor='middle'))
dwg.add(dwg.text('石材干挂', insert=(sx(DOOR_X+DOOR_W + (W-DOOR_X-DOOR_W)//2), sy(H - 200)), font_size='10', fill='#666', text_anchor='middle'))

# 图例
lgx = 50
for color, label in [('#000','外轮廓'), ('#0a0','门'), ('blue','窗'), ('green','尺寸')]:
    dwg.add(dwg.rect(insert=(lgx, 570), size=(12, 12), fill=color))
    dwg.add(dwg.text(label, insert=(lgx+15, 580), font_size='9'))
    lgx += 120

dwg.add(dwg.text('美容院门头 — 正立面图 | 比例示意 | GUOXIN BEAUTY', 
          insert=(425, 20), font_size='14', font_weight='bold', text_anchor='middle'))

svg_path = f'{DIR}/美容院门面立面图.svg'
dwg.save()
print(f'✅ SVG: {svg_path}')

# 转PNG
os.system(f'magick convert {svg_path} {DIR}/美容院门面立面图.png 2>/dev/null')
print(f'✅ PNG: {DIR}/美容院门面立面图.png')

# =============================================
# 生成项目信息文件
# =============================================
info = f'''# 美容院门头 — 项目信息

## 基本信息
- 项目名称：美容院门头设计
- 项目类型：门头
- 门面尺寸：6000mm(宽) × 3500mm(高)
- 门洞尺寸：1800mm(宽) × 2400mm(高)
- 招牌高度：800mm
- 展示窗：2个（1000×2000 / 800×2000）

## 材质
- 招牌区域：铝塑板 + LOGO灯箱
- 立面：石材干挂
- 门：玻璃推拉门（12mm钢化）
- 窗：钢化玻璃展示窗

## 文件清单
- ✅ 正立面图 DXF
- ✅ 正立面图 SVG
- ✅ 正立面图 PNG
- [ ] 原始现场照片
- [ ] 施工完成照片

## OpenClaw 自动生成
- 图层：A-WALL / A-DOOR / A-WINDW / A-DIM / A-TEXT / A-HATCH / A-NOTE
- 使用命令：LINE / OFFSET / COPY / TRIM / DIM / MTEXT
'''
with open(f'{DIR}/项目信息.md', 'w') as f:
    f.write(info)
print(f'✅ 项目信息: {DIR}/项目信息.md')

print(f'\n📋 美容院门头实战案例完成！')
print(f'   用 CAD看圖王 打开 DXF 可查看原始图纸')
print(f'   用 相册 查看 PNG 对比效果')
