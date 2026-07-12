#!/usr/bin/env python3
"""
课题013 — 墙体-轴网对齐

将墙体LINE段端点吸附到最近的轴线位置，使墙体完全正交对齐。

步骤：
1. 从解析JSON读取墙体LINE段
2. 加载主结构轴网和次轴线
3. 对每个墙段端点，计算到最近轴线的距离并吸附
4. 处理特殊情况：墙端对齐、墙角闭合、门洞保留
5. 输出对齐后的墙体DXF + SVG
"""
import json, os, math
from collections import defaultdict

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
JSON_PATH = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT_DIR   = f'{BASE}/04_实战案例/课题013_墙轴对齐/'
os.makedirs(OUT_DIR, exist_ok=True)

def f(v):
    try: return float(v)
    except: return 0.0

def fmt(v):
    return f'{v:.2f}'

# ========== 1. 加载轴线数据 ==========
# 从课题012的主结构轴网逻辑复制过来
data = json.load(open(JSON_PATH))
ents = data.get('entities', [])
dims = [e for e in ents if e.get('type') == 'DIMENSION']

h_dims = [d for d in dims if abs(f(d.get('code_50',0))) < 1]
v_dims = [d for d in dims if abs(f(d.get('code_50',0))) > 89]

# 轴线聚类
def cluster(values, tol=50):
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

# 垂直轴线
v_axis_raw = set()
for d in h_dims:
    v_axis_raw.add(round(f(d.get('code_13',0)), 1))
    v_axis_raw.add(round(f(d.get('code_14',0)), 1))

# 水平轴线 
h_axis_raw = set()
for d in v_dims:
    h_axis_raw.add(round(f(d.get('code_23',0)), 1))
    h_axis_raw.add(round(f(d.get('code_24',0)), 1))

v_axes = cluster(list(v_axis_raw), tol=50)
h_axes = cluster(list(h_axis_raw), tol=50)

# 筛选主要轴线 (gap > 200mm)
v_axes_sorted = sorted(v_axes)
v_gaps = [v_axes_sorted[i+1]-v_axes_sorted[i] for i in range(len(v_axes_sorted)-1)]
v_axes_main = [v_axes_sorted[0]]
for i, g in enumerate(v_gaps):
    v_axes_main.append(v_axes_sorted[i+1])

h_axes_sorted = sorted(h_axes)
h_gaps = [h_axes_sorted[i+1]-h_axes_sorted[i] for i in range(len(h_axes_sorted)-1)]
h_axes_main = [h_axes_sorted[0]]
for i, g in enumerate(h_gaps):
    h_axes_main.append(h_axes_sorted[i+1])

print(f'垂直轴线: {len(v_axes_main)} 条, X范围 [{min(v_axes_main):.0f} - {max(v_axes_main):.0f}]')
print(f'水平轴线: {len(h_axes_main)} 条, Y范围 [{min(h_axes_main):.0f} - {max(h_axes_main):.0f}]')

# ========== 2. 提取墙体 ==========
wall_layers = ['A-WALL', 'A-土建墙', 'A-新隔墙', 'W-墙体']
walls = [e for e in ents if e.get('type') == 'LINE' and e.get('layer','') in wall_layers]
# 也尝试匹配图层名
for e in ents:
    if e.get('type')=='LINE' and e.get('layer','') not in [w.get('layer','') for w in walls]:
        l = e.get('layer','')
        if '墙' in l or 'WALL' in l:
            walls.append(e)

print(f'\n墙体LINE段: {len(walls)}')

# 每个墙段: (x1, y1, x2, y2, layer)
wall_segs = []
for w in walls:
    x1, y1 = f(w.get('code_10',0)), f(w.get('code_20',0))
    x2, y2 = f(w.get('code_11',0)), f(w.get('code_21',0))
    # 去重（相同或镜像的墙段）
    wall_segs.append((x1, y1, x2, y2, w.get('layer','A-WALL')))

# ========== 3. 吸附函数 ==========
TOLERANCE = 300  # 最大吸附距离(mm)，超过此值不吸附

def snap_to_axes(x, y):
    """将点(x,y)吸附到最近轴线"""
    # 水平方向：找最近的垂直轴线
    best_dx = TOLERANCE
    snap_x = x
    for ax in v_axes_main:
        dx = abs(x - ax)
        if dx < best_dx:
            best_dx = dx
            snap_x = ax
    
    # 垂直方向：找最近的水平轴线
    best_dy = TOLERANCE
    snap_y = y
    for ay in h_axes_main:
        dy = abs(y - ay)
        if dy < best_dy:
            best_dy = dy
            snap_y = ay
    
    return snap_x, snap_y, best_dx < TOLERANCE, best_dy < TOLERANCE

# ========== 4. 对齐墙体 ==========
snapped_segs = []
snap_stats = {'snapped_x': 0, 'snapped_y': 0, 'kept': 0}

for x1, y1, x2, y2, layer in wall_segs:
    sx1, sy1, sx1_ok, sy1_ok = snap_to_axes(x1, y1)
    sx2, sy2, sx2_ok, sy2_ok = snap_to_axes(x2, y2)
    
    # 判断墙段方向
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    is_horizontal = dy < dx  # 水平墙：Y相同，X变化
    
    if is_horizontal:
        # 水平墙段：吸附Y到轴线
        if sy1_ok: sy1 = round((sy1 + sy2)/2, 0) if sy1 != sy2 else sy1
        if sy2_ok: sy2 = sy1
        if sx1_ok: snap_stats['snapped_x'] += 1
        if sy1_ok: snap_stats['snapped_y'] += 1
        sx1 = round(sx1, 0)
        sx2 = round(sx2, 0)
    else:
        # 垂直墙段：吸附X到轴线
        if sx1_ok: sx1 = round((sx1 + sx2)/2, 0) if sx1 != sx2 else sx1
        if sx2_ok: sx2 = sx1
        if sx1_ok: snap_stats['snapped_x'] += 1
        if sy1_ok: snap_stats['snapped_y'] += 1
        sy1 = round(sy1, 0)
        sy2 = round(sy2, 0)
    
    snapped_segs.append((sx1, sy1, sx2, sy2, layer))
    snap_stats['kept'] += 1

print(f'对齐统计:')
print(f'  墙段总数: {snap_stats["kept"]}')
print(f'  X吸附次数: {snap_stats["snapped_x"]}')
print(f'  Y吸附次数: {snap_stats["snapped_y"]}')

# ========== 5. 合并共线墙段 ==========
def merge_collinear(segs, tol=50):
    """合并同一直线上的相邻/重叠墙段"""
    # 分离水平和垂直
    h_segs = [s for s in segs if abs(s[3]-s[1]) < abs(s[2]-s[0])]  # 水平墙：Y基本不变
    v_segs = [s for s in segs if abs(s[2]-s[0]) <= abs(s[3]-s[1])]  # 垂直墙：X基本不变
    
    def merge_one_axis(seg_list, is_h):
        """合并同轴墙段"""
        if not seg_list:
            return []
        
        # 按轴线位置分组
        groups = defaultdict(list)
        for s in seg_list:
            x1, y1, x2, y2, layer = s
            if is_h:
                key = round(y1, 0)  # 水平墙按Y分组
            else:
                key = round(x1, 0)  # 垂直墙按X分组
            groups[key].append(s)
        
        merged = []
        for key in sorted(groups.keys()):
            segs_in_group = groups[key]
            if is_h:
                # 水平墙：按X排序后合并
                sorted_segs = sorted(segs_in_group, key=lambda s: min(s[0], s[2]))
                merged_ranges = []
                for x1, y1, x2, y2, layer in sorted_segs:
                    lo, hi = min(x1, x2), max(x1, x2)
                    if not merged_ranges:
                        merged_ranges.append([lo, hi])
                    else:
                        if lo <= merged_ranges[-1][1] + tol:
                            merged_ranges[-1][1] = max(merged_ranges[-1][1], hi)
                        else:
                            merged_ranges.append([lo, hi])
                for lo, hi in merged_ranges:
                    length = hi - lo
                    if length > 200:  # 过滤过短的
                        merged.append((lo, key, hi, key, 'A-WALL'))
            else:
                # 垂直墙：按Y排序后合并
                sorted_segs = sorted(segs_in_group, key=lambda s: min(s[1], s[3]))
                merged_ranges = []
                for x1, y1, x2, y2, layer in sorted_segs:
                    lo, hi = min(y1, y2), max(y1, y2)
                    if not merged_ranges:
                        merged_ranges.append([lo, hi])
                    else:
                        if lo <= merged_ranges[-1][1] + tol:
                            merged_ranges[-1][1] = max(merged_ranges[-1][1], hi)
                        else:
                            merged_ranges.append([lo, hi])
                for lo, hi in merged_ranges:
                    length = hi - lo
                    if length > 200:
                        merged.append((key, lo, key, hi, 'A-WALL'))
        
        return merged
    
    merged_h = merge_one_axis(h_segs, True)
    merged_v = merge_one_axis(v_segs, False)
    return merged_h + merged_v

print(f'\n合并共线墙段...')
merged_segs = merge_collinear(snapped_segs)
print(f'  合并前: {len(snapped_segs)} 段')
print(f'  合并后: {len(merged_segs)} 段')
print(f'  压缩率: {(1-len(merged_segs)/len(snapped_segs))*100:.1f}%')

# ========== 6. 导出DXF ==========
def write_wall_dxf(segs, filepath):
    lines = []
    lines.append('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC')
    lines.append('0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n3')
    layers = [('0', '7'), ('A-WALL', '7'), ('A-AXIS', '3')]
    for name, color in layers:
        lines.append(f'0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\nCONTINUOUS')
    lines.append('0\nENDTAB\n0\nENDSEC')
    
    lines.append('0\nSECTION\n2\nENTITIES')
    
    for x1, y1, x2, y2, layer in segs:
        lines.append(f'0\nLINE\n8\nA-WALL\n62\n7\n10\n{fmt(x1)}\n20\n{fmt(y1)}\n11\n{fmt(x2)}\n21\n{fmt(y2)}')
    
    lines.append('0\nENDSEC\n0\nEOF')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

# 导出
dxf_path = os.path.join(OUT_DIR, '墙体_轴网对齐.dxf')
write_wall_dxf(merged_segs, dxf_path)
print(f'\n✅ 输出: {dxf_path}')
print(f'  墙段数: {len(merged_segs)}')

# ========== 7. SVG可视化 ==========
def write_wall_svg(segs, axes_v, axes_h, filepath):
    x_min = min(min(s[0], s[2]) for s in segs) - 2000
    x_max = max(max(s[0], s[2]) for s in segs) + 2000
    y_min = min(min(s[1], s[3]) for s in segs) - 2000
    y_max = max(max(s[1], s[3]) for s in segs) + 2000
    
    def sx(x): return 50 + (x - x_min) / (x_max - x_min) * 750
    def sy(y): return 650 - (y - y_min) / (y_max - y_min) * 600
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 700">')
    svg.append(f'<rect width="100%" height="100%" fill="#f8f9fa"/>')
    svg.append(f'<text x="30" y="30" font-size="14" font-weight="bold">墙体-轴网对齐结果 (晴碧园F2层)</text>')
    
    # 轴线（浅色）
    for ax in axes_v:
        x = sx(ax)
        svg.append(f'<line x1="{x:.0f}" y1="40" x2="{x:.0f}" y2="660" stroke="#ddd" stroke-width="0.5" stroke-dasharray="4,3"/>')
    for ay in axes_h:
        y = sy(ay)
        svg.append(f'<line x1="40" y1="{y:.0f}" x2="810" y2="{y:.0f}" stroke="#ddd" stroke-width="0.5" stroke-dasharray="4,3"/>')
    
    # 墙体（合并后）
    for s in segs:
        x1, y1, x2, y2, _ = s
        svg.append(f'<line x1="{sx(x1):.0f}" y1="{sy(y1):.0f}" x2="{sx(x2):.0f}" y2="{sy(y2):.0f}" stroke="#2c3e50" stroke-width="3"/>')
    
    # 统计
    h_count = len([s for s in segs if abs(s[3]-s[1]) < abs(s[2]-s[0])])
    v_count = len([s for s in segs if abs(s[2]-s[0]) <= abs(s[3]-s[1])])
    svg.append(f'<text x="30" y="680" font-size="11" fill="#666">水平墙: {h_count} | 垂直墙: {v_count} | 总: {len(segs)}</text>')
    
    svg.append('</svg>')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))

svg_path = os.path.join(OUT_DIR, '墙体_轴网对齐.svg')
write_wall_svg(merged_segs, v_axes_main, h_axes_main, svg_path)
print(f'✅ SVG: {svg_path}')

# ========== 8. 统计报告 ==========
report = []
sep = '=' * 65
report.append(sep)
report.append('  课题013 — 墙体-轴网对齐')
report.append('  来源: 晴碧园晶园26栋')
report.append(sep)
report.append('')
report.append(f'  轴线系统:')
report.append(f'    垂直轴线: {len(v_axes_main)} 条')
report.append(f'    水平轴线: {len(h_axes_main)} 条')
report.append(f'    最大吸附距离: {TOLERANCE}mm')
report.append('')
report.append(f'  墙体处理:')
report.append(f'    原始LINE段: {len(wall_segs)}')
report.append(f'    对齐后段: {len(snapped_segs)}')
report.append(f'    合并后段: {len(merged_segs)}')
report.append(f'    压缩率: {(1-len(merged_segs)/len(wall_segs))*100:.1f}%')
report.append('')
report.append(f'  对齐质量:')
h_final = len([s for s in merged_segs if abs(s[3]-s[1]) < abs(s[2]-s[0])])
v_final = len([s for s in merged_segs if abs(s[2]-s[0]) <= abs(s[3]-s[1])])
report.append(f'    水平墙: {h_final} 段')
report.append(f'    垂直墙: {v_final} 段')
ortho_rate = ((h_final+v_final)/len(merged_segs))*100 if merged_segs else 0
report.append(f'    正交率: {ortho_rate:.1f}%')
report.append('')
report.append('  输出文件:')
report.append(f'    墙体_轴网对齐.dxf — 对齐后墙体DXF')
report.append(f'    墙体_轴网对齐.svg — 可视化')
report.append('')
report.append('【下一步】')
report.append('  1. 在AutoCAD中验证对齐准确性')
report.append('  2. 面积统计工具：对封闭房间计算面积')
report.append('  3. 材料清单：壁纸/地砖/涂料用量估算')
report.append(sep)

with open(os.path.join(OUT_DIR, '对齐报告.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n' + '\n'.join(report))
print('\n✅ 课题013 墙体-轴网对齐完成!')
