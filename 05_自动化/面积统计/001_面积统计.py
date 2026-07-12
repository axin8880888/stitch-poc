#!/usr/bin/env python3
"""
面积统计工具 V1 — 从轴网对齐后的墙体计算房间面积

原理：
1. 从墙体LINE段构建无向图
2. 识别闭合多边形（房间轮廓）
3. 对每个多边形计算面积（Shoelace公式）
4. 匹配房间名称文本
5. 输出面积表 + SVG热力图

施工图标准面积精度：
- 房间面积: 保留2位小数 (m²)
- 总面积: 保留2位小数
- 误差容限: 墙中线~墙边线 = 半墙厚偏移
"""
import json, os, math
from collections import defaultdict, deque
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union, polygonize

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
WALL_DXF = f'{BASE}/04_实战案例/课题013_墙轴对齐/墙体_轴网对齐.dxf'
JSON_PATH = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT_DIR   = f'{BASE}/05_自动化/面积统计'
os.makedirs(OUT_DIR, exist_ok=True)

# ========== 1. 加载墙段 ==========
def parse_dxf_walls(filepath):
    segs = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == 'LINE':
            x1=y1=x2=y2=0
            layer = 'A-WALL'
            i += 1
            while i < len(lines):
                l = lines[i].strip()
                if l == '0':
                    break
                elif l == '8':
                    i += 1
                    layer = lines[i].strip()
                elif l == '10':
                    i += 1
                    x1 = float(lines[i].strip())
                elif l == '20':
                    i += 1
                    y1 = float(lines[i].strip())
                elif l == '11':
                    i += 1
                    x2 = float(lines[i].strip())
                elif l == '21':
                    i += 1
                    y2 = float(lines[i].strip())
                i += 1
            segs.append((x1, y1, x2, y2))
        else:
            i += 1
    return segs

# 替代方案：直接从解析JSON提取
def load_walls_from_json():
    data = json.load(open(JSON_PATH))
    ents = data.get('entities', [])
    wall_layers = ['A-WALL', 'A-土建墙', 'A-新隔墙', 'W-墙体']
    segs = []
    for e in ents:
        if e.get('type') == 'LINE':
            l = e.get('layer', '')
            if l in wall_layers or '墙' in l or 'WALL' in l:
                def fv(c): 
                    try: return float(e.get(f'code_{c}', 0))
                    except: return 0.0
                segs.append((fv(10), fv(20), fv(11), fv(21)))
    return segs

print('加载墙段...')
# 先尝试从JSON加载（更完整的墙段）
segs = load_walls_from_json()
print(f'  从JSON加载: {len(segs)} 段')

# ========== 2. 构建空间索引 + 闭合多边形 ==========
print('\n构建闭合多边形...')

# 使用shapely的polygonize功能
lines = []
for x1, y1, x2, y2 in segs:
    if (x1, y1) != (x2, y2):  # 排除零长度线段
        lines.append(LineString([(x1, y1), (x2, y2)]))

print(f'  有效线段: {len(lines)}')

# 多边形化
merged = unary_union(lines)
polygons = list(polygonize(merged))
print(f'  识别到闭合多边形: {len(polygons)}')

# ========== 3. 过滤有意义的房间 ==========
# 过滤过小的碎片
MIN_AREA = 0.5  # 最小房间面积 (m²)
rooms = []
for poly in polygons:
    area = poly.area  # DXF单位是mm，面积是mm²
    area_m2 = area / 1_000_000
    if area_m2 >= MIN_AREA and poly.is_valid:
        centroid = poly.centroid
        bounds = poly.bounds
        rooms.append({
            'polygon': poly,
            'area_mm2': area,
            'area_m2': round(area_m2, 2),
            'centroid': (centroid.x, centroid.y),
            'bounds': bounds
        })

rooms.sort(key=lambda r: r['area_m2'], reverse=True)
print(f'  有意义房间: {len(rooms)}')
print(f'  最大房间: {rooms[0]["area_m2"]:.2f}m²' if rooms else '')

# ========== 4. 匹配房间名称 ==========
data = json.load(open(JSON_PATH))
ents = data.get('entities', [])
mtexts = [e for e in ents if e.get('type') == 'MTEXT']

def fv(e, c):
    try: return float(e.get(f'code_{c}', 0))
    except: return 0.0

room_labels = []
for m in mtexts:
    txt = m.get('code_1', '').strip()
    h = fv(m, 40)
    if txt and abs(h - 140) < 10:  # 房间名高度≈140
        room_labels.append({
            'text': txt,
            'x': fv(m, 10),
            'y': fv(m, 20)
        })

print(f'  房间名标注: {len(room_labels)}')

# 匹配房间名到多边形
for room in rooms:
    pt = Point(room['centroid'])
    matched = []
    for label in room_labels:
        label_pt = Point(label['x'], label['y'])
        # 如果标注点在多边形内部，或者离多边形很近
        if room['polygon'].contains(label_pt) or room['polygon'].distance(label_pt) < 500:
            matched.append(label['text'])
    room['labels'] = matched if matched else ['(未命名)']

# ========== 5. 按楼层分组 ==========
def floor_key(y):
    """根据Y坐标判断楼层"""
    if y < -324000: return 5  # F5
    if y < -322000: return 4  # F4
    if y < -320000: return 3  # F3
    if y < -318000: return 2  # F2
    if y < -316000: return 1  # F1
    if y < -314000: return 'B1'  # B1
    return 'B2'

floors = defaultdict(list)
for room in rooms:
    y_center = room['centroid'][1]
    fk = floor_key(y_center)
    floors[fk].append(room)

# ========== 6. 输出CSV面积表 ==========
import csv
csv_path = os.path.join(OUT_DIR, '房间面积统计.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['楼层', '房间名称', '面积(m²)', '中心X', '中心Y', '边界Xmin', 'Ymin', 'Xmax', 'Ymax'])
    
    for fk in sorted(floors.keys(), key=lambda k: (isinstance(k, str), k)):
        floor_rooms = sorted(floors[fk], key=lambda r: r['area_m2'], reverse=True)
        floor_total = sum(r['area_m2'] for r in floor_rooms)
        for room in floor_rooms:
            labels_str = '/'.join(room['labels'])
            b = room['bounds']
            writer.writerow([fk, labels_str, f'{room["area_m2"]:.2f}', 
                           f'{room["centroid"][0]:.0f}', f'{room["centroid"][1]:.0f}',
                           f'{b[0]:.0f}', f'{b[1]:.0f}', f'{b[2]:.0f}', f'{b[3]:.0f}'])
        writer.writerow([fk, '--- 小计 ---', f'{floor_total:.2f}', '', '', '', '', '', ''])

print(f'\n✅ CSV面积表: {csv_path}')

# ========== 7. SVG可视化 ==========
def write_area_svg(rooms, floors, filepath):
    all_rooms = [r for fl in floors.values() for r in fl]
    if not all_rooms:
        return
    x_min = min(r['bounds'][0] for r in all_rooms)
    x_max = max(r['bounds'][2] for r in all_rooms)
    y_min = min(r['bounds'][1] for r in all_rooms)
    y_max = max(r['bounds'][3] for r in all_rooms)
    
    x_range = x_max - x_min or 1
    y_range = y_max - y_min or 1
    
    def sx(x): return 50 + (x - x_min) / x_range * 750
    def sy(y): return 650 - (y - y_min) / y_range * 600
    
    # 颜色渐变函数
    def area_color(area_m2, max_area):
        ratio = area_m2 / max_area if max_area > 0 else 0
        # 深绿色(小) → 黄色(中) → 红色(大)
        if ratio < 0.33:
            g = int(200 + 55 * ratio/0.33)
            return f'rgb({int(180*ratio/0.33)}, {g}, {int(100*(1-ratio/0.33))})'
        elif ratio < 0.66:
            r2 = (ratio - 0.33) / 0.33
            return f'rgb({int(180+75*r2)}, {int(255-55*r2)}, {int(50*(1-r2))})'
        else:
            r3 = (ratio - 0.66) / 0.34
            return f'rgb({int(255)}, {int(200-200*r3)}, 50)'
    
    max_area = max(r['area_m2'] for r in all_rooms)
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 700">')
    svg.append(f'<rect width="100%" height="100%" fill="#f8f9fa"/>')
    svg.append(f'<text x="30" y="25" font-size="16" font-weight="bold">晴碧园晶园26栋 — 房间面积统计</text>')
    svg.append(f'<text x="30" y="45" font-size="11" fill="#666">颜色: 深绿(小) → 黄(中) → 红(大) | 总面积: {sum(r["area_m2"] for r in all_rooms):.2f}m²</text>')
    
    # 房间多边形 + 标注
    y_offset = 60
    for room in all_rooms:
        poly = room['polygon']
        color = area_color(room['area_m2'], max_area)
        pts = list(poly.exterior.coords)
        pt_str = ' '.join([f'{sx(p[0]):.1f},{sy(p[1]):.1f}' for p in pts])
        svg.append(f'<polygon points="{pt_str}" fill="{color}" fill-opacity="0.4" stroke="#333" stroke-width="1.5"/>')
        
        # 房间名 + 面积
        cx, cy = room['centroid']
        label = '/'.join(room['labels'][:2])
        svg.append(f'<text x="{sx(cx):.0f}" y="{sy(cy)+3:.0f}" text-anchor="middle" font-size="9" fill="#333" font-weight="bold">{label}</text>')
        svg.append(f'<text x="{sx(cx):.0f}" y="{sy(cy)+15:.0f}" text-anchor="middle" font-size="8" fill="#666">{room["area_m2"]:.1f}m²</text>')
    
    # 侧边面积图例
    svg.append(f'<rect x="820" y="60" width="30" height="200" fill="url(#grad)" stroke="#999" stroke-width="0.5"/>')
    svg.append(f'<defs><linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">')
    svg.append(f'<stop offset="0%" stop-color="rgb(255,50,50)"/>')
    svg.append(f'<stop offset="50%" stop-color="rgb(255,200,50)"/>')
    svg.append(f'<stop offset="100%" stop-color="rgb(50,200,50)"/>')
    svg.append(f'</linearGradient></defs>')
    svg.append(f'<text x="820" y="275" font-size="8" fill="#666">{max_area:.0f}m²</text>')
    svg.append(f'<text x="820" y="310" font-size="8" fill="#666">0m²</text>')
    
    svg.append('</svg>')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))

svg_path = os.path.join(OUT_DIR, '房间面积统计.svg')
write_area_svg(rooms, floors, svg_path)
print(f'✅ SVG热力图: {svg_path}')

# ========== 8. 报告 ==========
report = []
sep = '=' * 65
report.append(sep)
report.append('  面积统计工具 V1 — 晴碧园晶园26栋')
report.append(sep)
report.append('')
report.append(f'  墙线段总数: {len(segs)}')
report.append(f'  闭合多边形: {len(polygons)}')
report.append(f'  有效房间: {len(rooms)}')
report.append('')
total_all = 0
for fk in sorted(floors.keys(), key=lambda k: (isinstance(k, str), k)):
    floor_total = sum(r['area_m2'] for r in floors[fk])
    total_all += floor_total
    report.append(f'  === {fk}层 ({len(floors[fk])}间, {floor_total:.2f}m²) ===')
    for room in sorted(floors[fk], key=lambda r: r['area_m2'], reverse=True):
        labels = '/'.join(room['labels'])
        report.append(f'    {labels:15s}  {room["area_m2"]:>7.2f} m²')
    report.append('')
report.append(f'  {"总计":15s}  {total_all:>7.2f} m²')
report.append('')
report.append('  输出文件:')
report.append(f'    房间面积统计.csv — 面积表')
report.append(f'    房间面积统计.svg — 热力图')
report.append('')
report.append('【精度说明】')
report.append('  面积基于墙中线计算，实际使用面积需扣除半墙厚')
report.append('  装修面积 = 本面积 - 墙厚修正')
report.append('  一般住宅: 净面积 ≈ 本面积 × 0.92~0.95')
report.append(sep)

with open(os.path.join(OUT_DIR, '面积统计报告.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n' + '\n'.join(report))
print('\n✅ 面积统计工具完成!')
