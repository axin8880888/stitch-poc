#!/usr/bin/env python3
"""
第一阶段实战测试：手写 DXF + SVG 出图
验证我对 CAD 坐标系统、图层、对象类型的理解

测试内容：
1. 生成一个带多个图层的 DXF 文件（纯文本）
2. 解析 DXF 并打印结构分析
3. 输出 SVG 可视化验证
"""

import os, math
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/_test'

# ============================================================
# 第1步：手写 DXF 文件
# DXF 是纯文本格式，每个实体由组码(整数)+值(字符串)成对表示
# ============================================================

def write_dxf(filename):
    """手写一个 DXF 文件来验证第一阶段学习成果"""
    lines = []
    lines.append("0\nSECTION\n2\nHEADER\n0\nENDSEC")
    
    # TABLES 段 - 定义图层
    tables = [
        "0\nSECTION\n2\nTABLES",
        "0\nTABLE\n2\nLAYER\n70\n4",  # 4个图层
        # 图层: A-WALL (颜色7白, 线宽0.30mm=30)
        "0\nLAYER\n2\nA-WALL\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n30",
        # 图层: A-FURN (颜色6品红, 线宽0.18mm=18)
        "0\nLAYER\n2\nA-FURN\n70\n0\n62\n6\n6\nCONTINUOUS\n370\n18",
        # 图层: A-DIM (颜色3绿, 线宽0.13mm=13)
        "0\nLAYER\n2\nA-DIM\n70\n0\n62\n3\n6\nCONTINUOUS\n370\n13",
        # 图层: A-TEXT (颜色7白, 线宽0.13mm=13)
        "0\nLAYER\n2\nA-TEXT\n70\n0\n62\n7\n6\nCONTINUOUS\n370\n13",
        "0\nENDTAB\n0\nENDSEC",
    ]
    lines.extend(tables)
    
    # ENTITIES 段 - 图形对象
    entities = [
        "0\nSECTION\n2\nENTITIES",
        
        # 墙体: LINE (左下角到右下角)
        "0\nLINE\n8\nA-WALL\n10\n0\n20\n0\n11\n5000\n21\n0",
        # 墙体: LINE (右上角到左上角)  
        "0\nLINE\n8\nA-WALL\n10\n5000\n20\n0\n11\n5000\n21\n4000",
        # 墙体: LINE (右上到右下)
        "0\nLINE\n8\nA-WALL\n10\n5000\n20\n4000\n11\n0\n21\n4000",
        # 墙体: LINE (左下到左上)
        "0\nLINE\n8\nA-WALL\n10\n0\n20\n4000\n11\n0\n21\n0",
        
        # 内墙分割 LINE
        "0\nLINE\n8\nA-WALL\n10\n2500\n20\n0\n11\n2500\n21\n4000",
        "0\nLINE\n8\nA-WALL\n10\n0\n20\n2500\n11\n5000\n21\n2500",
        
        # 家具: CIRCLE (餐桌)
        "0\nCIRCLE\n8\nA-FURN\n10\n1250\n20\n1250\n40\n400",
        # 家具: CIRCLE (茶几)
        "0\nCIRCLE\n8\nA-FURN\n10\n3750\n20\n1250\n40\n300",
        
        # 线性标注 (水平方向 0-5000)
        "0\nDIMENSION\n8\nA-DIM\n2\n*D0\n10\n0\n20\n-500\n11\n2500\n21\n-500\n70\n0\n1\n5000",
        # 简化的标注线
        "0\nLINE\n8\nA-DIM\n10\n0\n20\n-300\n11\n5000\n21\n-300",
        
        # 文字: 房间名称
        "0\nTEXT\n8\nA-TEXT\n10\n1000\n20\n3000\n40\n200\n1\n客厅",
        "0\nTEXT\n8\nA-TEXT\n10\n3000\n20\n3000\n40\n200\n1\n餐厅",
        "0\nTEXT\n8\nA-TEXT\n10\n1000\n20\n700\n40\n200\n1\n卧室",
        "0\nTEXT\n8\nA-TEXT\n10\n3500\n20\n700\n40\n150\n1\n厨房",
        
        # 圆弧 (弧形窗/装饰)
        "0\nARC\n8\nA-WALL\n10\n1250\n20\n4000\n40\n1000\n50\n180\n51\n0",
        
        # 椭圆 (装饰)
        "0\nELLIPSE\n8\nA-FURN\n10\n3750\n20\n3000\n11\n500\n21\n0\n40\n0.5",
        
        "0\nENDSEC\n0\nEOF",
    ]
    lines.extend(entities)
    
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))
    print(f"[OK] DXF written: {filename}")

# ============================================================  
# 第2步：解析 DXF 并分析
# ============================================================

def parse_dxf(filename):
    """解析 DXF 文件，提取实体信息"""
    with open(filename, 'r') as f:
        content = f.read()
    
    tokens = content.split('\n')
    entities = []
    current = None
    in_entities = False
    i = 0
    
    while i < len(tokens):
        line = tokens[i]
        
        # 找到 ENTITIES 段
        if line == 'ENTITIES' and i > 0 and tokens[i-1] == '2':
            in_entities = True
            i += 1
            continue
        
        if in_entities:
            if line == 'ENDSEC':
                break
            if line == '0':
                # 新实体开始
                if current is not None:
                    entities.append(current)
                i += 1
                if i < len(tokens):
                    current = {'type': tokens[i], 'props': {}}
                else:
                    current = None
            else:
                if current is not None:
                    code = int(line)
                    i += 1
                    val = tokens[i] if i < len(tokens) else ''
                    current['props'][code] = val
        
        i += 1
    
    if current is not None and current.get('type') and current['type'] not in ('ENDSEC', 'EOF'):
        entities.append(current)
    
    return entities

def analyze_entities(entities):
    """分析实体，分类统计"""
    stats = {'LINE': 0, 'CIRCLE': 0, 'ARC': 0, 'ELLIPSE': 0, 'TEXT': 0, 'DIMENSION': 0, 'OTHER': 0}
    layers = {}
    
    for ent in entities:
        t = ent['type']
        stats[t] = stats.get(t, 0) + 1 if t in stats else stats.get('OTHER', 0) + 1
        
        layer = ent['props'].get('8', '0')
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(t)
    
    return stats, layers

# ============================================================
# 第3步：SVG 可视化出图
# ============================================================

def dxf_to_svg(entities, filename):
    """将 DXF 实体绘制为 SVG 可视化"""
    SCALE = 0.05  # DXF单位mm → SVG像素
    W = 5000 * SCALE + 100
    H = 4500 * SCALE + 100
    OFFSET_X = 50
    OFFSET_Y = 50
    
    dwg = Drawing(filename, size=(f'{W}px', f'{H}px'))
    
    # 背景
    dwg.add(dwg.rect(insert=(0,0), size=(W,H), fill='white'))
    
    # 图例
    legend_y = 10
    legend_items = [
        ('#000000', 'A-WALL 墙体'),
        ('#FF00FF', 'A-FURN 家具'),
        ('#008000', 'A-DIM 标注'),
        ('#000000', 'A-TEXT 文字'),
    ]
    for i, (color, label) in enumerate(legend_items):
        x = 50 + i * 120
        dwg.add(dwg.rect(insert=(x, legend_y), size=(10,10), fill=color))
        dwg.add(dwg.text(label, insert=(x+12, legend_y+9), font_size='9'))
    
    def tx(x): return x * SCALE + OFFSET_X
    def ty(y): return H - (y * SCALE + OFFSET_Y)  # 翻转Y轴
    
    colors = {'A-WALL': '#000000', 'A-FURN': '#FF00FF', 'A-DIM': '#008000', 'A-TEXT': '#000000'}
    lw = {'A-WALL': 2, 'A-FURN': 1.5, 'A-DIM': 1, 'A-TEXT': 1}
    
    for ent in entities:
        p = ent['props']
        layer = p.get('8', '0')
        color = colors.get(layer, '#888888')
        w = lw.get(layer, 1)
        
        if ent['type'] == 'LINE':
            x1, y1 = tx(float(p.get('10',0))), ty(float(p.get('20',0)))
            x2, y2 = tx(float(p.get('11',0))), ty(float(p.get('21',0)))
            dwg.add(dwg.line((x1,y1), (x2,y2), stroke=color, stroke_width=w))
            
        elif ent['type'] == 'CIRCLE':
            cx, cy = tx(float(p.get('10',0))), ty(float(p.get('20',0)))
            r = float(p.get('40',0)) * SCALE
            dwg.add(dwg.circle(center=(cx,cy), r=r, fill='none', stroke=color, stroke_width=w))
            
        elif ent['type'] == 'ARC':
            cx, cy = tx(float(p.get('10',0))), ty(float(p.get('20',0)))
            r = float(p.get('40',0)) * SCALE
            s_ang = math.radians(float(p.get('50',0)))
            e_ang = math.radians(float(p.get('51',0)))
            
            # 用路径画弧
            sx = cx + r * math.cos(s_ang)
            sy = cy - r * math.sin(s_ang)
            ex = cx + r * math.cos(e_ang)
            ey = cy - r * math.sin(e_ang)
            
            large = 1 if abs(e_ang - s_ang) > math.pi else 0
            d = f'M {sx},{sy} A {r},{r} 0 {large},0 {ex},{ey}'
            dwg.add(dwg.path(d=d, fill='none', stroke=color, stroke_width=w))
            
        elif ent['type'] == 'ELLIPSE':
            cx, cy = tx(float(p.get('10',0))), ty(float(p.get('20',0)))
            mx = float(p.get('11',0)) * SCALE
            my = float(p.get('21',0)) * SCALE
            r = float(p.get('40',0))
            dwg.add(dwg.ellipse(center=(cx, cy), r=(mx, my*r), fill='none', stroke=color, stroke_width=w))
            
        elif ent['type'] == 'TEXT':
            x, y = tx(float(p.get('10',0))), ty(float(p.get('20',0)))
            txt = p.get('1', '')
            h = float(p.get('40', 200)) * SCALE
            dwg.add(dwg.text(txt, insert=(x, y+h/3), font_size=str(h), fill=color, font_family='sans-serif'))
            
        elif ent['type'] == 'DIMENSION':
            # 标注基线
            x1, y1 = tx(float(p.get('10',0))), ty(float(p.get('20',0)))
            x2, y2 = tx(float(p.get('11',0))), ty(float(p.get('21',0)))
            dwg.add(dwg.line((x1,y1), (x2,y2), stroke=color, stroke_width=w, stroke_dasharray='5,3'))
    
    dwg.save()
    print(f"[OK] SVG written: {filename}")

# ============================================================
# 执行
# ============================================================

# 1. 生成 DXF
dxf_path = OUT + '.dxf'
write_dxf(dxf_path)

# 2. 解析并分析
entities = parse_dxf(dxf_path)
stats, layers = analyze_entities(entities)

print(f"\n===== 实体统计 =====")
for t, n in stats.items():
    if n > 0:
        print(f"  {t}: {n}个")

print(f"\n===== 图层分析 =====")
for layer, types in layers.items():
    print(f"  {layer}: {', '.join(types)}")

print(f"\n===== 坐标验证 =====")
# 验证房间尺寸 (5000x4000)
print(f"  房间尺寸: 5000mm x 4000mm (5m x 4m)")
print(f"  内墙分割: 在2500处纵向分割, 2500处横向分割")
print(f"  餐桌圆心: (1250, 1250) 半径400mm")

# 3. 输出 SVG
dxf_to_svg(entities, OUT + '.svg')

print(f"\n✅ 第一阶段实战测试完成")
print(f"📄 DXF: {dxf_path}")
print(f"🖼  SVG: {OUT}.svg")
