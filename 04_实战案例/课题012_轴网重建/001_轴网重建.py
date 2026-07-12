#!/usr/bin/env python3
"""
课题012 — 轴网重建

从晴碧园晶园26栋的 DIMENSION 标注链提取并重建轴网系统。

步骤：
1. 从解析JSON读取尺寸标注
2. 按角度分组：水平(0°) → 垂直轴线X，垂直(90°) → 水平轴线Y
3. 聚类去重 — 识别每个结构区段的"干净"轴线位置
4. 构建轴网 — 垂直和水平轴线交点
5. 输出 DXF + SVG + 报告
"""
import json, os, math
from collections import defaultdict, OrderedDict

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
JSON_PATH = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT_DIR   = f'{BASE}/04_实战案例/课题012_轴网重建'

os.makedirs(OUT_DIR, exist_ok=True)

def f(v):
    try: return float(v)
    except: return 0.0

def fmt(v): return f'{v:.2f}'

# ========== 1. 加载数据 ==========
data = json.load(open(JSON_PATH))
ents = data.get('entities', [])
dims = [e for e in ents if e.get('type') == 'DIMENSION']

h_dims = [d for d in dims if abs(f(d.get('code_50',0))) < 1]   # 水平 (0°)
v_dims = [d for d in dims if abs(f(d.get('code_50',0))) > 89]  # 垂直 (90°)

print(f'DIMENSION 总数: {len(dims)}')
print(f'  水平尺寸 (0°): {len(h_dims)}')
print(f'  垂直尺寸 (90°): {len(v_dims)}')
print()

# ========== 2. 提取轴线候选位置 ==========

# 水平尺寸延伸线端点 → 垂直轴线X坐标
v_axis_x_raw = set()
for d in h_dims:
    v_axis_x_raw.add(round(f(d.get('code_13',0)), 1))
    v_axis_x_raw.add(round(f(d.get('code_14',0)), 1))

# 垂直尺寸延伸线端点 → 水平轴线Y坐标
h_axis_y_raw = set()
for d in v_dims:
    h_axis_y_raw.add(round(f(d.get('code_23',0)), 1))
    h_axis_y_raw.add(round(f(d.get('code_24',0)), 1))

print(f'垂直轴线候选 (X): {len(v_axis_x_raw)}')
print(f'水平轴线候选 (Y): {len(h_axis_y_raw)}')

# ========== 3. 聚类去重（tolerance = 50mm）==========
def cluster(values, tol=50):
    """将相近的值聚为一类，返回代表性值（均值）"""
    sorted_vals = sorted(values)
    clusters = []
    current = [sorted_vals[0]]
    for v in sorted_vals[1:]:
        if v - current[-1] <= tol:
            current.append(v)
        else:
            clusters.append(round(sum(current)/len(current), 0))
            current = [v]
    clusters.append(round(sum(current)/len(current), 0))
    return clusters

v_axis_x = cluster(list(v_axis_x_raw), tol=50)
h_axis_y = cluster(list(h_axis_y_raw), tol=50)

print(f'\n聚类后垂直轴线 (X): {len(v_axis_x)} 条')
print(f'  X = {v_axis_x}')
print(f'聚类后水平轴线 (Y): {len(h_axis_y)} 条')
print(f'  Y = {h_axis_y}')

# ========== 4. 按结构区段分组 ==========
# 根据X轴线的间距，识别三个结构区段
v_axis_x_sorted = sorted(v_axis_x)
gaps = [v_axis_x_sorted[i+1] - v_axis_x_sorted[i] for i in range(len(v_axis_x_sorted)-1)]
print(f'\nX轴线间距:')
for i, g in enumerate(gaps):
    print(f'  X{v_axis_x_sorted[i]:.0f} → X{v_axis_x_sorted[i+1]:.0f} = {g:.0f}mm')

# 大 gap (>5000) 表示区段边界
segment_boundaries = [0]
for i, g in enumerate(gaps):
    if abs(g) > 5000:
        segment_boundaries.append(i+1)
segment_boundaries.append(len(v_axis_x_sorted))

segments = []
for s in range(len(segment_boundaries)-1):
    start = segment_boundaries[s]
    end = segment_boundaries[s+1]
    seg_x = v_axis_x_sorted[start:end]
    if seg_x:
        segments.append(seg_x)

print(f'\n结构区段数: {len(segments)}')
for i, seg in enumerate(segments):
    span = seg[-1] - seg[0]
    print(f'  区段{i+1}: X[{seg[0]:.0f} - {seg[-1]:.0f}], {len(seg)}条轴线, 跨度{span:.0f}mm')
    print(f'    轴线: {seg}')

# ========== 5. 水平轴线分组（按楼层）==========
h_axis_y_sorted = sorted(h_axis_y)
h_gaps = [h_axis_y_sorted[i+1] - h_axis_y_sorted[i] for i in range(len(h_axis_y_sorted)-1)]
print(f'\nY轴线间距:')
for i, g in enumerate(h_gaps):
    print(f'  Y{h_axis_y_sorted[i]:.0f} → Y{h_axis_y_sorted[i+1]:.0f} = {g:.0f}mm')

# 大 gap 表示楼层边界
y_boundaries = [0]
for i, g in enumerate(h_gaps):
    if abs(g) > 2000:
        y_boundaries.append(i+1)
y_boundaries.append(len(h_axis_y_sorted))

y_segments = []
for s in range(len(y_boundaries)-1):
    start, end = y_boundaries[s], y_boundaries[s+1]
    seg_y = h_axis_y_sorted[start:end]
    if seg_y:
        y_segments.append(seg_y)

print(f'\n水平轴线组: {len(y_segments)}')
for i, seg in enumerate(y_segments):
    span = seg[-1] - seg[0]
    print(f'  组{i+1}: Y[{seg[0]:.0f} - {seg[-1]:.0f}], {len(seg)}条, 跨度{span:.0f}mm')
    print(f'    轴线: {seg}')

# 取最后一个完整组（F3层最完整）作为主力水平轴网
main_y_axes = y_segments[-1] if y_segments else h_axis_y_sorted

# ========== 6. 生成 DXF 轴网 ==========
def write_axis_dxf(segments_x, main_y, filepath, title='轴网系统'):
    """输出带轴号的 DXF"""
    lines = []
    lines.append('0')
    lines.append('SECTION')
    lines.append('2')
    lines.append('HEADER')
    lines.append('9')
    lines.append('$ACADVER')
    lines.append('1')
    lines.append('AC1009')
    lines.append('0')
    lines.append('ENDSEC')
    
    lines.append('0')
    lines.append('SECTION')
    lines.append('2')
    lines.append('TABLES')
    
    # LAYER table
    lines.append('0')
    lines.append('TABLE')
    lines.append('2')
    lines.append('LAYER')
    lines.append('70')
    lines.append('4')
    
    layers = [
        ('0', '7', 'CONTINUOUS'),
        ('A-AXIS', '3', 'CENTER'),         # 轴线 - 绿色
        ('A-AXIS-LABEL', '7', 'CONTINUOUS'), # 轴号 - 白色
        ('A-AXIS-DIM', '4', 'CONTINUOUS'),   # 尺寸 - 青色
    ]
    for name, color, ltype in layers:
        lines.append('0')
        lines.append('LAYER')
        lines.append('2')
        lines.append(name)
        lines.append('70')
        lines.append('0')
        lines.append('62')
        lines.append(color)
        lines.append('6')
        lines.append(ltype)
    
    lines.append('0')
    lines.append('ENDTAB')
    lines.append('0')
    lines.append('ENDSEC')
    
    # ENTITIES section
    lines.append('0')
    lines.append('SECTION')
    lines.append('2')
    lines.append('ENTITIES')
    
    # 全部轴线合并为一个列表（可能有多区段）
    all_x = []
    for seg in segments_x:
        all_x.extend(seg)
    all_y = main_y
    
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_margin = (x_max - x_min) * 0.05 or 1000
    y_margin = (y_max - y_min) * 0.05 or 1000
    
    # 画垂直轴线（从最低Y到最高Y）
    for x in all_x:
        lines.append('0')
        lines.append('LINE')
        lines.append('8')
        lines.append('A-AXIS')
        lines.append('62')
        lines.append('3')
        lines.append('10')
        lines.append(fmt(x))
        lines.append('20')
        lines.append(fmt(y_min - y_margin))
        lines.append('11')
        lines.append(fmt(x))
        lines.append('21')
        lines.append(fmt(y_max + y_margin))
    
    # 画水平轴线（从左到右贯穿所有区段）
    for y in all_y:
        lines.append('0')
        lines.append('LINE')
        lines.append('8')
        lines.append('A-AXIS')
        lines.append('62')
        lines.append('3')
        lines.append('10')
        lines.append(fmt(x_min - x_margin))
        lines.append('20')
        lines.append(fmt(y))
        lines.append('11')
        lines.append(fmt(x_max + x_margin))
        lines.append('21')
        lines.append(fmt(y))
    
    # 画轴号圈（在每个轴线端点）
    label_r = 300  # 轴号圈半径
    
    # 垂直轴线轴号
    for i, x in enumerate(all_x):
        # 底部轴号
        label_y = y_min - y_margin - label_r * 2
        lines.append('0')
        lines.append('CIRCLE')
        lines.append('8')
        lines.append('A-AXIS-LABEL')
        lines.append('10')
        lines.append(fmt(x))
        lines.append('20')
        lines.append(fmt(label_y))
        lines.append('40')
        lines.append(fmt(label_r))
        
        # 顶部轴号
        label_y_top = y_max + y_margin + label_r * 2
        lines.append('0')
        lines.append('CIRCLE')
        lines.append('8')
        lines.append('A-AXIS-LABEL')
        lines.append('10')
        lines.append(fmt(x))
        lines.append('20')
        lines.append(fmt(label_y_top))
        lines.append('40')
        lines.append(fmt(label_r))
    
    # 水平轴线轴号
    for i, y in enumerate(all_y):
        # 左侧轴号
        label_x = x_min - x_margin - label_r * 2
        lines.append('0')
        lines.append('CIRCLE')
        lines.append('8')
        lines.append('A-AXIS-LABEL')
        lines.append('10')
        lines.append(fmt(label_x))
        lines.append('20')
        lines.append(fmt(y))
        lines.append('40')
        lines.append(fmt(label_r))
        
        # 右侧轴号
        label_x_right = x_max + x_margin + label_r * 2
        lines.append('0')
        lines.append('CIRCLE')
        lines.append('8')
        lines.append('A-AXIS-LABEL')
        lines.append('10')
        lines.append(fmt(label_x_right))
        lines.append('20')
        lines.append(fmt(y))
        lines.append('40')
        lines.append(fmt(label_r))
    
    # 尺寸标注（总尺寸和各区段跨度）
    # 底部总尺寸
    for x in all_x:
        lines.append('0')
        lines.append('LINE')
        lines.append('8')
        lines.append('A-AXIS-DIM')
        lines.append('10')
        lines.append(fmt(x))
        lines.append('20')
        lines.append(fmt(y_min - y_margin - label_r * 5))
        lines.append('11')
        lines.append(fmt(x))
        lines.append('21')
        lines.append(fmt(y_min - y_margin - label_r * 4))
    
    lines.append('0')
    lines.append('ENDSEC')
    lines.append('0')
    lines.append('EOF')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return len(all_x) * len(all_y)


def write_axis_svg(segments_x, main_y, filepath, title='轴网系统'):
    """输出轴网 SVG 可视化"""
    all_x = []
    for seg in segments_x:
        all_x.extend(seg)
    
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(main_y), max(main_y)
    
    # 留出轴号空间
    margin = (x_max - x_min) * 0.08 or 2000
    y_margin = (y_max - y_min) * 0.15 or 2000
    
    # 坐标系取反（SVG Y向下为正）
    def scale(v, lo, hi, target_hi=800):
        return 50 + (v - lo) / (hi - lo) * target_hi
    
    def flip_y(y):
        return scale(y, y_min - y_margin, y_max + y_margin, 600)
    
    def scale_x(x):
        return scale(x, x_min - margin, x_max + margin, 900)
    
    svg_w = 1000
    svg_h = 700
    
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}">')
    lines.append(f'<rect width="100%" height="100%" fill="#f8f9fa"/>')
    lines.append(f'<text x="50" y="30" font-size="16" font-weight="bold">{title}</text>')
    
    # 背景网格
    lines.append(f'<g stroke="#e0e0e0" stroke-width="0.5">')
    for i in range(0, svg_w, 50):
        lines.append(f'<line x1="{i}" y1="0" x2="{i}" y2="{svg_h}"/>')
    for i in range(0, svg_h, 50):
        lines.append(f'<line x1="0" y1="{i}" x2="{svg_w}" y2="{i}"/>')
    lines.append(f'</g>')
    
    # 垂直轴线
    for x in all_x:
        sx = scale_x(x)
        sy1 = flip_y(y_min)
        sy2 = flip_y(y_max)
        lines.append(f'<line x1="{sx:.0f}" y1="{sy1:.0f}" x2="{sx:.0f}" y2="{sy2:.0f}" stroke="#e74c3c" stroke-width="1.5" stroke-dasharray="8,4"/>')
    
    # 水平轴线
    for y in main_y:
        sy = flip_y(y)
        sx1 = scale_x(x_min)
        sx2 = scale_x(x_max)
        lines.append(f'<line x1="{sx1:.0f}" y1="{sy:.0f}" x2="{sx2:.0f}" y2="{sy:.0f}" stroke="#3498db" stroke-width="1.5" stroke-dasharray="8,4"/>')
    
    # 轴号圈
    for i, x in enumerate(all_x):
        sx = scale_x(x)
        # 底部轴号
        label_y = flip_y(y_min) + 30
        lines.append(f'<circle cx="{sx:.0f}" cy="{label_y:.0f}" r="14" fill="white" stroke="#e74c3c" stroke-width="1.5"/>')
        lines.append(f'<text x="{sx:.0f}" y="{label_y+4:.0f}" text-anchor="middle" font-size="10" fill="#333">{i+1}</text>')
        # 顶部轴号
        label_y_top = flip_y(y_max) - 30
        lines.append(f'<circle cx="{sx:.0f}" cy="{label_y_top:.0f}" r="14" fill="white" stroke="#e74c3c" stroke-width="1.5"/>')
        lines.append(f'<text x="{sx:.0f}" y="{label_y_top+4:.0f}" text-anchor="middle" font-size="10" fill="#333">{i+1}</text>')
    
    # 左侧和右侧水平轴号
    for i, y in enumerate(main_y):
        sy = flip_y(y)
        # 左侧
        label_x = scale_x(x_min) - 40
        lines.append(f'<circle cx="{label_x:.0f}" cy="{sy:.0f}" r="14" fill="white" stroke="#3498db" stroke-width="1.5"/>')
        lines.append(f'<text x="{label_x:.0f}" y="{sy+4:.0f}" text-anchor="middle" font-size="10" fill="#333">{chr(65+i)}</text>')
        # 右侧
        label_x_right = scale_x(x_max) + 40
        lines.append(f'<circle cx="{label_x_right:.0f}" cy="{sy:.0f}" r="14" fill="white" stroke="#3498db" stroke-width="1.5"/>')
        lines.append(f'<text x="{label_x_right:.0f}" y="{sy+4:.0f}" text-anchor="middle" font-size="10" fill="#333">{chr(65+i)}</text>')
    
    # 区段标注
    colors = ['#e74c3c', '#9b59b6', '#2ecc71', '#f39c12']
    x_offset = scale_x(x_min)
    for si, seg in enumerate(segments_x):
        seg_center_x = sum(seg) / len(seg)
        sx = scale_x(seg_center_x)
        y_pos = flip_y(y_min) + 60 + si * 25
        span_mm = seg[-1] - seg[0]
        lines.append(f'<text x="{sx:.0f}" y="{y_pos:.0f}" text-anchor="middle" font-size="11" fill="{colors[si%len(colors)]}">{chr(65+si)}区 {span_mm:.0f}mm ({len(seg)}轴)</text>')
    
    # 总跨度标注
    total_x = x_max - x_min
    total_y_val = y_max - y_min
    lines.append(f'<text x="50" y="{svg_h-20}" font-size="11" fill="#666">总跨度: X={total_x:.0f}mm × Y={total_y_val:.0f}mm | 轴线数: {len(all_x)}V × {len(main_y)}H</text>')
    
    lines.append('</svg>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ========== 7. 生成输出 ==========
print('\n========== 生成轴网输出 ==========')

# 所有区段的垂直轴线合并输出
dxf_path = os.path.join(OUT_DIR, '轴网系统.dxf')
n_cells = write_axis_dxf(segments, main_y_axes, dxf_path)
print(f'DXF: {dxf_path}')
print(f'  轴网网格: {sum(len(s) for s in segments)}V × {len(main_y_axes)}H = {n_cells} 个交点')

svg_path = os.path.join(OUT_DIR, '轴网系统.svg')
write_axis_svg(segments, main_y_axes, svg_path)
print(f'SVG: {svg_path}')

# ========== 8. 各区段独立轴网 ==========
for si, seg in enumerate(segments):
    dxf_seg = os.path.join(OUT_DIR, f'轴网_区段{chr(65+si)}.dxf')
    svg_seg = os.path.join(OUT_DIR, f'轴网_区段{chr(65+si)}.svg')
    write_axis_dxf([seg], main_y_axes, dxf_seg, f'{chr(65+si)}区轴网')
    write_axis_svg([seg], main_y_axes, svg_seg, f'{chr(65+si)}区轴网')
    print(f'  区段{chr(65+si)}: DXF+SVG 已输出')

# ========== 9. 生成报告 ==========
report = []
sep = '=' * 65
report.append(sep)
report.append('  课题012 — 尺寸还原与轴网重建')
report.append('  来源: 晴碧园晶园26栋 DXF')
report.append(sep)
report.append('')
report.append(f'  原始 DIMENSION 总数: {len(dims)}')
report.append(f'    水平尺寸 (0°): {len(h_dims)}')
report.append(f'    垂直尺寸 (90°): {len(v_dims)}')
report.append('')
report.append(f'  聚类后垂直轴线: {len(v_axis_x)} 条')
report.append(f'  聚类后水平轴线: {len(h_axis_y)} 条')
report.append('')
report.append(f'  结构区段识别: {len(segments)} 个')
for i, seg in enumerate(segments):
    span = seg[-1] - seg[0]
    report.append(f'    {chr(65+i)}区: X[{seg[0]:.0f} - {seg[-1]:.0f}], {len(seg)}条轴线, 跨度{span:.0f}mm')
    axis_labels = ', '.join([f'{x:.0f}' for x in seg])
    report.append(f'      轴线X: {axis_labels}')
report.append('')
report.append(f'  水平轴线组: {len(y_segments)} 组')
for i, seg in enumerate(y_segments):
    span = seg[-1] - seg[0]
    report.append(f'    组{i+1}: Y[{seg[0]:.0f} - {seg[-1]:.0f}], {len(seg)}条, 跨度{span:.0f}mm')
report.append('')
report.append('  主力水平轴线（组%d）: %d条' % (len(y_segments), len(main_y_axes)))
report.append(f'    Y: {main_y_axes}')
report.append('')
report.append('  输出文件:')
report.append(f'    轴网系统.dxf     — 全楼三维轴网')
report.append(f'    轴网系统.svg     — 全楼轴网可视化')
report.append('')
for i, seg in enumerate(segments):
    report.append(f'    轴网_区段{chr(65+si)}.dxf — {chr(65+si)}区独立轴网')
    report.append(f'    轴网_区段{chr(65+si)}.svg — {chr(65+si)}区轴网可视化')
report.append('')
report.append('【下一步】')
report.append('  1. 在AutoCAD中打开轴网DXF，核对轴线位置准确性')
report.append('  2. 将课题011重建的墙体骨架与轴网叠加')
report.append('  3. 添加轴号标注（垂直: 1,2,3... / 水平: A,B,C...）')
report.append('  4. 课题013: 墙体-轴网对齐（将墙体吸附到最近轴线）')
report.append(sep)

report_text = '\n'.join(report)
print('\n' + report_text)

with open(os.path.join(OUT_DIR, '轴网重建报告.txt'), 'w', encoding='utf-8') as f:
    f.write(report_text)

print('\n✅ 课题012 轴网重建完成!')
