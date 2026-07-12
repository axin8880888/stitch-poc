#!/usr/bin/env python3
"""
面积统计工具 V3 — 墙端桥接版

针对纯LINE墙段不含门窗闭合线的问题：
1. 连接相近墙端（≤1200mm = 典型门宽）来填补门洞
2. 构建完整闭合多边形
3. Shoelace计算面积 + 房间名匹配
"""
import json, os, math
from collections import defaultdict

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
JSP = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT = f'{BASE}/05_自动化/面积统计'
os.makedirs(OUT, exist_ok=True)

def fv(e,c):
    try: return float(e.get(f'code_{c}',0))
    except: return 0.0

print('加载墙段...')
data = json.load(open(JSP))
ents = data.get('entities', [])

wl = ['A-WALL', 'A-土建墙', 'A-新隔墙', 'W-墙体']
wall_pts = defaultdict(set)
raw_edges = set()

for e in ents:
    if e.get('type') != 'LINE': continue
    l = e.get('layer','')
    if l not in wl and '墙' not in l and 'WALL' not in l: continue
    x1,y1 = round(fv(e,10),-1), round(fv(e,20),-1)  # 10mm精度
    x2,y2 = round(fv(e,11),-1), round(fv(e,21),-1)
    if (x1,y1) != (x2,y2):
        wall_pts[(x1,y1)].add((x2,y2))
        wall_pts[(x2,y2)].add((x1,y1))
        raw_edges.add(((x1,y1),(x2,y2)))

# 找游离端点（degree=1的节点）
endpoints = [p for p in wall_pts if len(wall_pts[p]) == 1]
print(f'  墙端点数: {len(endpoints)}')

# 桥接：连接相近的游离端点
DOOR_GAP = 1500  # 最大门洞宽度
bridges = []
used_eps = set()

for ep in endpoints:
    if ep in used_eps: continue
    if len(wall_pts[ep]) > 1: continue  # 已经不是游离点
    
    # 找最近的另一个游离点
    best_d, best_p = DOOR_GAP, None
    for ep2 in endpoints:
        if ep2 == ep or ep2 in used_eps: continue
        if len(wall_pts[ep2]) > 1: continue
        d = math.hypot(ep[0]-ep2[0], ep[1]-ep2[1])
        if 200 < d < best_d:  # 至少200mm
            best_d, best_p = d, ep2
    
    if best_p:
        bridges.append((ep, best_p))
        used_eps.add(ep)
        used_eps.add(best_p)

print(f'  桥接线: {len(bridges)}')

# 桥接线也加入图
for p1, p2 in bridges:
    wall_pts[p1].add(p2)
    wall_pts[p2].add(p1)
    raw_edges.add((p1, p2))

print(f'  总边数（含桥接）: {len(raw_edges)}')

# ========== 排序邻接 ==========
sorted_nbrs = {}
for node in wall_pts:
    nbrs = list(wall_pts[node])
    nbrs.sort(key=lambda n: math.atan2(n[1]-node[1], n[0]-node[0]))
    sorted_nbrs[node] = nbrs

# ========== 半边结构 ==========
next_edge = {}
for (a, b) in raw_edges:
    if a not in sorted_nbrs or b not in sorted_nbrs: continue
    bn = sorted_nbrs[b]
    if a in bn:
        ai = bn.index(a)
        ni = (ai + 1) % len(bn)
        next_edge[(a, b)] = (b, bn[ni])
    an = sorted_nbrs[a]
    if b in an:
        bi = an.index(b)
        ni = (bi + 1) % len(an)
        next_edge[(b, a)] = (a, an[ni])

print(f'  半边: {len(next_edge)}')

# ========== 追踪面 ==========
visited = set()
faces = []

for start in next_edge:
    if start in visited: continue
    face = []; cur = start
    for _ in range(len(next_edge)+1):
        if cur in visited: break
        visited.add(cur); face.append(cur[0])
        if cur not in next_edge: break
        cur = next_edge[cur]
        if cur == start:
            face.append(cur[0])
            if len(face) >= 3:
                n = len(face); a = 0
                for i in range(n):
                    j = (i+1)%n; a += face[i][0]*face[j][1] - face[j][0]*face[i][1]
                a = abs(a)/2
                if a > 500000:
                    cx = sum(p[0] for p in face)/n
                    cy = sum(p[1] for p in face)/n
                    faces.append({'pts':face,'area':a,'area_m2':round(a/1e6,2),
                                  'centroid':(cx,cy)})
            break

# 去重
seen={}; cleaned=[]
for f in faces:
    k = (round(f['centroid'][0],-2), round(f['centroid'][1],-2))
    if k not in seen:
        seen[k]=True; cleaned.append(f)

print(f'  闭合面 (>0.5m²): {len(cleaned)}')

# ========== 房间标签 ==========
mts = [e for e in ents if e.get('type')=='MTEXT']
lbls = []
for m in mts:
    t = m.get('code_1','').strip()
    h = fv(m,40)
    if t and 120 < h < 160:
        lbls.append({'text':t, 'x':fv(m,10), 'y':fv(m,20)})

def pip(pt, poly):
    x,y=pt; n=len(poly); j=n-1; inside=False
    for i in range(n):
        xi,yi=poly[i]; xj,yj=poly[j]
        if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/(yj-yi)+xi: inside=not inside
        j=i
    return inside

for f in cleaned:
    match=[]
    for l in lbls:
        if pip((l['x'],l['y']), f['pts']): match.append(l['text'])
    if not match:
        bd=None; bv=1e9
        for l in lbls:
            d=math.hypot(l['x']-f['centroid'][0], l['y']-f['centroid'][1])
            if d<bv: bv,bd=d,l['text']+'?'
        match=[bd] if bd else ['?']
    f['labels']=match

# ========== 楼层 ==========
def fk(y):
    return 'F5' if y<-324000 else 'F4' if y<-322000 else 'F3' if y<-320000 else 'F2' if y<-318000 else 'F1' if y<-316000 else 'B1' if y<-314000 else 'B2'

floors=defaultdict(list)
for f in cleaned: floors[fk(f['centroid'][1])].append(f)

# ========== CSV ==========
import csv
csvp=f'{OUT}/房间面积统计.csv'
with open(csvp,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['楼层','房间','面积(m²)'])
    ta=0
    for fk2 in sorted(floors, key=lambda k:(isinstance(k,str),k)):
        fr=sorted(floors[fk2],key=lambda r:r['area_m2'],reverse=True)
        ft=sum(r['area_m2'] for r in fr); ta+=ft
        for r in fr: w.writerow([fk2,'/'.join(r['labels']),f'{r["area_m2"]:.2f}'])
        w.writerow([fk2,'--- 小计 ---',f'{ft:.2f}'])
    w.writerow(['','=== 总计 ===',f'{ta:.2f}'])

# ========== 报告 ==========
print('\n' + '='*60)
print('  面积统计 — 晴碧园晶园26栋（桥接版）')
print('='*60 + '\n')
ta=0
for fk2 in sorted(floors, key=lambda k:(isinstance(k,str),k)):
    fr=sorted(floors[fk2],key=lambda r:r['area_m2'],reverse=True)
    ft=sum(r['area_m2'] for r in fr); ta+=ft
    print(f'  {fk2}层 ({len(fr)}间, {ft:.2f}m²):')
    for r in fr: print(f'    {"/".join(r["labels"]):20s}  {r["area_m2"]:>7.2f} m²')
print(f'\n  {"总计":>20s}  {ta:>7.2f} m²')
print(f'\n✅ CSV: {csvp}')
print('注意: 墙端桥接只补门洞不补窗洞，结果偏低')
