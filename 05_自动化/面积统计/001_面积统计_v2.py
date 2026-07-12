#!/usr/bin/env python3
"""
面积统计工具 V1 — 纯Python实现（无需shapely）

原理：
1. 从墙体LINE段构建无向图（容差去除重复点）
2. 用"最小角转向"算法追踪闭合多边形
3. Shoelace公式计算面积
4. 匹配房间名称
5. 输出CSV面积表 + SVG热力图
"""
import json, os, math
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

def round_pt(x, y, prec=0):
    """将点对齐到整数精度"""
    return (round(x, prec), round(y, prec))

segs = []
for e in ents:
    if e.get('type') == 'LINE':
        l = e.get('layer', '')
        if l in wall_layers or '墙' in l or 'WALL' in l:
            x1, y1 = fv(e,10), fv(e,20)
            x2, y2 = fv(e,11), fv(e,21)
            # 对齐到1mm精度
            p1 = round_pt(x1, y1, 0)
            p2 = round_pt(x2, y2, 0)
            if p1 != p2:
                segs.append((p1, p2))

print(f'  墙段: {len(segs)}')

# ========== 2. 构建邻接图 ==========
graph = defaultdict(set)  # point -> set of connected points
for p1, p2 in segs:
    graph[p1].add(p2)
    graph[p2].add(p1)

print(f'  节点: {len(graph)}')

# ========== 3. 追踪闭合多边形 ==========
def angle_between(p1, p2, p3):
    """向量p1→p2与p1→p3的夹角 """
    v1 = (p2[0]-p1[0], p2[1]-p1[1])
    v2 = (p3[0]-p1[0], p3[1]-p1[1])
    return math.atan2(v2[1], v2[0]) - math.atan2(v1[1], v1[0])

def signed_polygon_area(pts):
    """Shoelace公式计算有符号面积"""
    area = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return area / 2.0

def trace_face(start_node, start_edge, visited_edges):
    """
    从start_node出发，沿着start_edge方向，用最小角转向法追踪面。
    visited_edges: set of ((p1,p2), (p2,p1)) 已访问边
    """
    path = [start_node, start_edge]
    edge_key = (start_node, start_edge)
    if edge_key in visited_edges:
        return None
    visited_edges.add(edge_key)
    
    current = start_edge
    prev = start_node
    
    while True:
        neighbors = list(graph[current])
        if len(neighbors) < 2:
            return None  # 死胡同
        
        # 找到最小转角的下一个节点
        best_angle = float('inf')
        best_next = None
        
        for nxt in neighbors:
            if nxt == prev:
                continue
            # 从prev→current转到current→nxt的角度
            ang = math.atan2(current[1]-prev[1], current[0]-prev[0])
            ang2 = math.atan2(nxt[1]-current[1], nxt[0]-current[0])
            diff = ang2 - ang
            if diff < 0:
                diff += 2 * math.pi
            # 最小正角 = 最左转
            # 我们想要最右转（最小负角），用"最大正角"等效
            # 实际需要：追踪"最小内角" = 最大正转
            if diff < best_angle:
                best_angle = diff
                best_next = nxt
        
        if best_next is None:
            return None
        
        edge_key = (current, best_next)
        if edge_key in visited_edges:
            return None
        
        visited_edges.add(edge_key)
        path.append(best_next)
        
        if best_next == path[0]:
            # 闭合！返回多边形
            return path
        
        prev = current
        current = best_next
        
        if len(path) > 10000:  # 安全保护
            return None

# 平面遍历法：从所有边出发追踪面，收集有效的闭合多边形
print('\n追踪闭合多边形...')
polygons = []
all_edge_keys = set()
for p1, p2 in segs:
    all_edge_keys.add((p1, p2))

# 使用"邻接遍历"替代复杂平面追踪
# 对于每个节点，按角度排序相邻点，然后每对相邻邻接构成一个面
for node in graph:
    neighbors = list(graph[node])
    if len(neighbors) < 2:
        continue
    
    # 按相对角度排序
    def sort_key(nbr):
        return math.atan2(nbr[1]-node[1], nbr[0]-node[0])
    neighbors.sort(key=sort_key)
    
    for i in range(len(neighbors)):
        n1 = neighbors[i]
        n2 = neighbors[(i+1) % len(neighbors)]
        
        # 从n1→node→n2追踪
        visited = set()
        # 检查n1-node和node-n2边是否存在
        if (n1, node) not in all_edge_keys:
            # 检查反向
            if (node, n1) not in all_edge_keys:
                continue
        if (node, n2) not in all_edge_keys:
            if (n2, node) not in all_edge_keys:
                continue
        
        # 尝试从node出发往n1方向走，然后右转到n2方向
        path = [n1, node, n2]
        visited.add((n1, node))
        visited.add((node, n2))
        
        current = n2
        prev = node
        found = False
        
        for _ in range(5000):  # 最大步数
            nbrs = list(graph[current])
            if len(nbrs) < 2:
                break
            
            # 最右转 = 最小正角
            vec_in = (prev[0]-current[0], prev[1]-current[1])
            in_ang = math.atan2(vec_in[1], vec_in[0])
            
            best_ang = float('inf')
            best_nxt = None
            
            for nx in nbrs:
                if nx == prev:
                    continue
                vec_out = (nx[0]-current[0], nx[1]-current[1])
                out_ang = math.atan2(vec_out[1], vec_out[0])
                diff = out_ang - in_ang
                if diff <= 0:
                    diff += 2 * math.pi
                if diff < best_ang:
                    best_ang = diff
                    best_nxt = nx
            
            if best_nxt is None:
                break
            
            edge = (current, best_nxt)
            if edge in visited or (best_nxt, current) in visited:
                break
            visited.add(edge)
            
            path.append(best_nxt)
            
            if best_nxt == n1:
                found = True
                break
            
            prev = current
            current = best_nxt
        
        if found:
            # 提取多边形点（去重端点）
            poly_pts = []
            seen_pts = set()
            for p in path:
                if p not in seen_pts:
                    seen_pts.add(p)
                    poly_pts.append(p)
            
            area = signed_polygon_area(poly_pts)
            if area > 500000:  # >0.5m²
                polygons.append({
                    'pts': poly_pts,
                    'area': abs(area),
                    'area_m2': round(abs(area)/1_000_000, 2),
                    'centroid': (sum(p[0] for p in poly_pts)/len(poly_pts), 
                                sum(p[1] for p in poly_pts)/len(poly_pts)),
                    'bounds': (min(p[0] for p in poly_pts), min(p[1] for p in poly_pts),
                              max(p[0] for p in poly_pts), max(p[1] for p in poly_pts))
                })

# 去重（按centroid坐标去重）
seen_centroids = set()
unique_polygons = []
for p in polygons:
    cx = round(p['centroid'][0], -2)  # 100mm精度去重
    cy = round(p['centroid'][1], -2)
    key = (cx, cy)
    if key not in seen_centroids:
        seen_centroids.add(key)
        unique_polygons.append(p)

unique_polygons.sort(key=lambda p: p['area_m2'], reverse=True)
print(f'  追踪到多边形: {len(polygons)}')
print(f'  去重后: {len(unique_polygons)}')

# ========== 4. 匹配房间名 ==========
mtexts = [e for e in ents if e.get('type') == 'MTEXT']
room_labels = []
for m in mtexts:
    txt = m.get('code_1', '').strip()
    h = fv(m, 40)
    if txt and abs(h - 140) < 15:
        room_labels.append({
            'text': txt,
            'x': fv(m, 10),
            'y': fv(m, 20)
        })

print(f'  房间名标注: {len(room_labels)}')

def point_in_polygon(pt, poly_pts):
    """射线法判断点是否在多边形内"""
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

def point_to_polygon_dist(pt, poly_pts):
    """点到多边形的最小距离"""
    x, y = pt
    min_d = float('inf')
    n = len(poly_pts)
    for i in range(n):
        x1, y1 = poly_pts[i]
        x2, y2 = poly_pts[(i+1)%n]
        # 点到线段距离
        dx, dy = x2-x1, y2-y1
        if dx == 0 and dy == 0:
            d = math.hypot(x-x1, y-y1)
        else:
            t = max(0, min(1, ((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)))
            proj_x, proj_y = x1 + t*dx, y1 + t*dy
            d = math.hypot(x-proj_x, y-proj_y)
        min_d = min(min_d, d)
    return min_d

for room in unique_polygons:
    matched = []
    cx, cy = room['centroid']
    for label in room_labels:
        if point_in_polygon((label['x'], label['y']), room['pts']):
            matched.append(label['text'])
        elif point_to_polygon_dist((label['x'], label['y']), room['pts']) < 800:
            matched.append(label['text'] + '?')
    room['labels'] = matched if matched else ['(未命名)']

# ========== 5. 按楼层分组 ==========
def floor_key(y):
    if y < -324000: return 'F5'
    if y < -322000: return 'F4'
    if y < -320000: return 'F3'
    if y < -318000: return 'F2'
    if y < -316000: return 'F1'
    if y < -314000: return 'B1'
    return 'B2'

floors = defaultdict(list)
for room in unique_polygons:
    fk = floor_key(room['centroid'][1])
    floors[fk].append(room)

# ========== 6. CSV ==========
csv_path = os.path.join(OUT_DIR, '房间面积统计.csv')
import csv
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['楼层', '房间名', '面积(m²)', '中心X', '中心Y'])
    for fk in sorted(floors.keys(), key=lambda k: (isinstance(k,str), k)):
        fr = sorted(floors[fk], key=lambda r: r['area_m2'], reverse=True)
        ft = sum(r['area_m2'] for r in fr)
        for r in fr:
            labels = '/'.join(r['labels'])
            writer.writerow([fk, labels, f'{r["area_m2"]:.2f}', f'{r["centroid"][0]:.0f}', f'{r["centroid"][1]:.0f}'])
        writer.writerow([fk, '--- 小计 ---', f'{ft:.2f}', '', ''])

print(f'\n✅ CSV: {csv_path}')

# ========== 7. SVG ==========
def write_svg(rooms, floors, filepath):
    all_r = [r for fl in floors.values() for r in fl]
    if not all_r: return
    xs = [p[0] for r in all_r for p in r['pts']]
    ys = [p[1] for r in all_r for p in r['pts']]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    xr = x_max - x_min or 1
    yr = y_max - y_min or 1
    
    def sx(x): return 60 + (x - x_min) / xr * 750
    def sy(y): return 640 - (y - y_min) / yr * 580
    
    max_area = max(r['area_m2'] for r in all_r)
    
    def area_color(am2):
        r = am2 / max_area if max_area > 0 else 0
        if r < 0.33:
            g = 200 + int(55 * r/0.33)
            return f'rgb({int(180*r/0.33)}, {g}, {int(100*(1-r/0.33))})'
        elif r < 0.66:
            r2 = (r-0.33)/0.33
            return f'rgb({int(180+75*r2)}, {int(255-55*r2)}, {int(50*(1-r2))})'
        else:
            r3 = (r-0.66)/0.34
            return f'rgb(255, {int(200-200*r3)}, 50)'
    
    svg_lines = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 680">')
    svg_lines.append(f'<rect width="100%" height="100%" fill="#f8f9fa"/>')
    svg_lines.append(f'<text x="30" y="22" font-size="14" font-weight="bold">晴碧园26栋 — 房间面积</text>')
    svg_lines.append(f'<text x="30" y="38" font-size="10" fill="#666">总面积: {sum(r["area_m2"] for r in all_r):.2f}m² | 房间: {len(all_r)}间</text>')
    
    for room in all_r:
        color = area_color(room['area_m2'])
        pts_str = ' '.join([f'{sx(p[0]):.1f},{sy(p[1]):.1f}' for p in room['pts']])
        svg_lines.append(f'<polygon points="{pts_str}" fill="{color}" fill-opacity="0.35" stroke="#333" stroke-width="1.2"/>')
        cx, cy = room['centroid']
        label = '/'.join(room['labels'][:2])
        svg_lines.append(f'<text x="{sx(cx):.0f}" y="{sy(cy):.0f}" text-anchor="middle" font-size="8" fill="#333" font-weight="bold">{label}</text>')
        svg_lines.append(f'<text x="{sx(cx):.0f}" y="{sy(cy)+11:.0f}" text-anchor="middle" font-size="7" fill="#666">{room["area_m2"]:.1f}m²</text>')
    
    svg_lines.append(f'<rect x="810" y="50" width="30" height="180" fill="url(#ag)" stroke="#999" stroke-width="0.5"/>')
    svg_lines.append(f'<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">')
    svg_lines.append(f'<stop offset="0%" stop-color="rgb(255,50,50)"/>')
    svg_lines.append(f'<stop offset="50%" stop-color="rgb(255,200,50)"/>')
    svg_lines.append(f'<stop offset="100%" stop-color="rgb(50,200,50)"/>')
    svg_lines.append(f'</linearGradient></defs>')
    svg_lines.append(f'<text x="810" y="245" font-size="7" fill="#666">{max_area:.0f}m²</text>')
    svg_lines.append(f'<text x="810" y="275" font-size="7" fill="#666">0</text>')
    svg_lines.append('</svg>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg_lines))

svg_path = os.path.join(OUT_DIR, '房间面积统计.svg')
write_svg(unique_polygons, floors, svg_path)
print(f'✅ SVG: {svg_path}')

# ========== 8. 报告 ==========
print()
print('=' * 65)
print('  面积统计 — 晴碧园晶园26栋')
print('=' * 65)
total = 0
for fk in sorted(floors.keys(), key=lambda k: (isinstance(k,str), k)):
    ft = sum(r['area_m2'] for r in floors[fk])
    total += ft
    print(f'\n  === {fk}层 ({len(floors[fk])}间, {ft:.2f}m²) ===')
    for r in sorted(floors[fk], key=lambda x: x['area_m2'], reverse=True):
        labels = '/'.join(r['labels'])
        print(f'    {labels:20s}  {r["area_m2"]:>7.2f} m²')
print(f'\n  {"总计":20s}  {total:>7.2f} m²')
print(f'\n✅ 面积统计完成!')
