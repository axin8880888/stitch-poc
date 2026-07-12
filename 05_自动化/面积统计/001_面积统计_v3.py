#!/usr/bin/env python3
"""
面积统计工具 V2 — 基于DCEL平面图遍历
纯Python实现，无需shapely

算法：
1. 从墙段构建无向图
2. 对每个节点按角度排序邻接边
3. 构建"半边"（Half-Edge）结构的下一条边映射
4. 从每个未访问半边出发，沿下一条边追踪闭合面
5. Shoelace公式计算面积
6. 匹配房间名标签
7. 输出CSV + SVG + 报告
"""
import json, os, math, csv
from collections import defaultdict

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
JSON_PATH = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT_DIR   = f'{BASE}/05_自动化/面积统计'
os.makedirs(OUT_DIR, exist_ok=True)

def fv(e, c):
    try: return float(e.get(f'code_{c}', 0))
    except: return 0.0

# ========== 1. 加载墙段 ==========
print('加载墙段...')
data = json.load(open(JSON_PATH))
ents = data.get('entities', [])
wall_layers = ['A-WALL', 'A-土建墙', 'A-新隔墙', 'W-墙体']

graph = defaultdict(set)
edges = set()

for e in ents:
    if e.get('type') == 'LINE':
        l = e.get('layer', '')
        if l in wall_layers or '墙' in l or 'WALL' in l:
            x1, y1 = round(fv(e,10)), round(fv(e,20))
            x2, y2 = round(fv(e,11)), round(fv(e,21))
            if (x1, y1) != (x2, y2):
                graph[(x1,y1)].add((x2,y2))
                graph[(x2,y2)].add((x1,y1))
                edges.add(((x1,y1),(x2,y2)))

print(f'  节点: {len(graph)}')
print(f'  边: {len(edges)}')

# ========== 2. 按角度排序邻接 ==========
sorted_nbrs = {}
for node in graph:
    nbrs = list(graph[node])
    nbrs.sort(key=lambda n: math.atan2(n[1]-node[1], n[0]-node[0]))
    sorted_nbrs[node] = nbrs

# ========== 3. 构建半边结构 ==========
next_edge = {}  # (from, to) -> (next_from, next_to)
for (a, b) in edges:
    b_nbrs = sorted_nbrs[b]
    a_idx = b_nbrs.index(a)
    next_idx = (a_idx + 1) % len(b_nbrs)
    next_node = b_nbrs[next_idx]
    next_edge[(a, b)] = (b, next_node)
    
    # 反向边
    a_nbrs = sorted_nbrs[a]
    b_idx = a_nbrs.index(b)
    next_rev = (b_idx + 1) % len(a_nbrs)
    next_edge[(b, a)] = (a, a_nbrs[next_rev])

print(f'  半边: {len(next_edge)}')

# ========== 4. 追踪闭合面 ==========
visited = set()
faces = []

for start in next_edge:
    if start in visited or start[0] == start[1]:
        continue
    
    face = []
    current = start
    max_steps = len(next_edge) + 1
    
    for _ in range(max_steps):
        if current in visited:
            break
        visited.add(current)
        face.append(current[0])
        
        if current not in next_edge:
            break
        
        current = next_edge[current]
        
        if current == start:
            face.append(current[0])
            # Shoelace
            n = len(face)
            if n >= 3:
                area = 0
                for i in range(n):
                    j = (i+1) % n
                    area += face[i][0] * face[j][1]
                    area -= face[j][0] * face[i][1]
                area = abs(area) / 2.0
                if area > 500000:  # >0.5m²
                    cx = sum(p[0] for p in face) / n
                    cy = sum(p[1] for p in face) / n
                    xs = [p[0] for p in face]
                    ys = [p[1] for p in face]
                    faces.append({
                        'pts': face,
                        'area': area,
                        'area_m2': round(area / 1_000_000, 2),
                        'centroid': (cx, cy),
                        'bounds': (min(xs), min(ys), max(xs), max(ys))
                    })
            break

print(f'  闭合面（>0.5m²）: {len(faces)}')

# 去重（按centroid聚类）
def cluster_centroids(polys, tol=500):
    kept = []
    used = set()
    for i, p in enumerate(polys):
        cx, cy = p['centroid']
        key = (round(cx, -2), round(cy, -2))
        if key not in used:
            used.add(key)
            kept.append(p)
    return kept

faces = cluster_centroids(faces)
print(f'  去重后: {len(faces)}')

# ========== 5. 匹配房间名 ==========
mtexts = [e for e in ents if e.get('type') == 'MTEXT']
room_labels = []
for m in mtexts:
    txt = m.get('code_1', '').strip()
    h = fv(m, 40)
    if txt and abs(h - 140) < 15:
        room_labels.append({'text': txt, 'x': fv(m,10), 'y': fv(m,20)})

print(f'  房间名: {len(room_labels)}')

def point_in_poly(pt, poly_pts):
    x, y = pt
    n = len(poly_pts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly_pts[i]
        xj, yj = poly_pts[j]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi) + xi):
            inside = not inside
        j = i
    return inside

for room in faces:
    matched = []
    for lbl in room_labels:
        if point_in_poly((lbl['x'], lbl['y']), room['pts']):
            matched.append(lbl['text'])
    # Fallback: 最近邻
    if not matched:
        min_d = float('inf')
        best = '(未命名)'
        for lbl in room_labels:
            d = math.hypot(lbl['x']-room['centroid'][0], lbl['y']-room['centroid'][1])
            if d < min_d:
                min_d = d
                best = lbl['text'] + '?'
        matched = [best]
    room['labels'] = matched

# ========== 6. 按楼层分组 ==========
def floor_key(y):
    if y < -324000: return 'F5'
    if y < -322000: return 'F4'
    if y < -320000: return 'F3'
    if y < -318000: return 'F2'
    if y < -316000: return 'F1'
    if y < -314000: return 'B1'
    return 'B2'

floors = defaultdict(list)
for room in faces:
    fk = floor_key(room['centroid'][1])
    floors[fk].append(room)

# ========== 7. CSV ==========
csv_path = os.path.join(OUT_DIR, '房间面积统计.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['楼层', '房间', '面积(m²)', '中心X', '中心Y'])
    total_all = 0
    for fk in sorted(floors.keys(), key=lambda k: (isinstance(k,str), k)):
        fr = sorted(floors[fk], key=lambda r: r['area_m2'], reverse=True)
        ft = sum(r['area_m2'] for r in fr)
        total_all += ft
        for r in fr:
            writer.writerow([fk, '/'.join(r['labels']), f'{r["area_m2"]:.2f}',
                           f'{r["centroid"][0]:.0f}', f'{r["centroid"][1]:.0f}'])
        writer.writerow([fk, '--- 小计 ---', f'{ft:.2f}', '', ''])
    writer.writerow(['', '=== 总计 ===', f'{total_all:.2f}', '', ''])

print(f'✅ CSV: {csv_path}')

# ========== 8. SVG ==========
def write_svg(rooms, floors_dict, filepath):
    all_r = [r for fl in floors_dict.values() for r in fl]
    if not all_r:
        open(filepath, 'w').write('<svg><text>无数据</text></svg>')
        return
    
    xs = [p[0] for r in all_r for p in r['pts']]
    ys = [p[1] for r in all_r for p in r['pts']]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    xr = x_max - x_min or 1
    yr = y_max - y_min or 1
    
    def sx(x): return 60 + (x - x_min) / xr * 720
    def sy(y): return 630 - (y - y_min) / yr * 560
    
    max_area = max(r['area_m2'] for r in all_r)
    
    def area_color(am2):
        r = am2 / max_area if max_area > 0 else 0
        if r < 0.33:
            g = 200 + int(55 * r/0.33)
            return f'rgb({int(180*r/0.33)},{g},{int(100*(1-r/0.33))})'
        elif r < 0.66:
            r2 = (r-0.33)/0.33
            return f'rgb({int(180+75*r2)},{int(255-55*r2)},{int(50*(1-r2))})'
        else:
            r3 = (r-0.66)/0.34
            return f'rgb(255,{int(200-200*r3)},50)'
    
    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 660">')
    lines.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')
    total = sum(r['area_m2'] for r in all_r)
    lines.append(f'<text x="30" y="22" font-size="14" font-weight="bold">晴碧园26栋 — 房间面积统计</text>')
    lines.append(f'<text x="30" y="38" font-size="10" fill="#666">总面积: {total:.2f}m² | 房间: {len(all_r)}间 | 颜色: 绿(小)→黄→红(大)</text>')
    
    for room in all_r:
        color = area_color(room['area_m2'])
        pts_str = ' '.join([f'{sx(p[0]):.1f},{sy(p[1]):.1f}' for p in room['pts']])
        lines.append(f'<polygon points="{pts_str}" fill="{color}" fill-opacity="0.35" stroke="#333" stroke-width="1"/>')
        cx, cy = room['centroid']
        lbl = '/'.join(room['labels'][:2])
        lines.append(f'<text x="{sx(cx):.0f}" y="{sy(cy):.0f}" text-anchor="middle" font-size="8" fill="#333" font-weight="bold">{lbl}</text>')
        lines.append(f'<text x="{sx(cx):.0f}" y="{sy(cy)+10:.0f}" text-anchor="middle" font-size="7" fill="#666">{room["area_m2"]:.1f}m²</text>')
    
    lines.append('<rect x="790" y="50" width="25" height="160" fill="url(#ag)" stroke="#999" stroke-width="0.5"/>')
    lines.append('<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">')
    lines.append('<stop offset="0%" stop-color="rgb(255,50,50)"/>')
    lines.append('<stop offset="50%" stop-color="rgb(255,200,50)"/>')
    lines.append('<stop offset="100%" stop-color="rgb(50,200,50)"/>')
    lines.append('</linearGradient></defs>')
    lines.append(f'<text x="790" y="220" font-size="7" fill="#666">{max_area:.0f}m²</text>')
    lines.append(f'<text x="790" y="240" font-size="7" fill="#666">0</text>')
    lines.append('</svg>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

svg_path = os.path.join(OUT_DIR, '房间面积统计.svg')
write_svg(faces, floors, svg_path)
print(f'✅ SVG: {svg_path}')

# ========== 9. 报告 ==========
sep = '=' * 65
print(f'\n{sep}')
print('  面积统计 — 晴碧园晶园26栋')
print(sep)
total_all = 0
for fk in sorted(floors.keys(), key=lambda k: (isinstance(k,str), k)):
    ft = sum(r['area_m2'] for r in floors[fk])
    total_all += ft
    print(f'\n  === {fk}层 ({len(floors[fk])}间, {ft:.2f}m²) ===')
    for r in sorted(floors[fk], key=lambda x: x['area_m2'], reverse=True):
        lbl = '/'.join(r['labels'])
        print(f'    {lbl:20s}  {r["area_m2"]:>7.2f} m²')
print(f'\n  {"总计":>20s}  {total_all:>7.2f} m²')
print(f'\n✅ 面积统计完成!')
