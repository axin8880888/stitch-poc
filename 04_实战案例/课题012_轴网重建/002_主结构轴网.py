#!/usr/bin/env python3
"""
课题012 — V2 主结构轴网（剔除次轴线）
只保留间距 > 800mm 的主要结构轴线，过滤墙厚分隔线。
"""
import json, os
from collections import defaultdict

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
JSON_PATH = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT_DIR   = f'{BASE}/04_实战案例/课题012_轴网重建'

def f(v):
    try: return float(v)
    except: return 0.0

def fmt(v): return f'{v:.2f}'

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

data = json.load(open(JSON_PATH))
dims = [e for e in data.get('entities',[]) if e.get('type')=='DIMENSION']

h_dims = [d for d in dims if abs(f(d.get('code_50',0))) < 1]
v_dims = [d for d in dims if abs(f(d.get('code_50',0))) > 89]

# ---- 提取原始轴线 ----
v_axis_x = set()
for d in h_dims:
    v_axis_x.add(round(f(d.get('code_13',0)), 1))
    v_axis_x.add(round(f(d.get('code_14',0)), 1))
v_clustered = cluster(list(v_axis_x), tol=50)

h_axis_y = set()
for d in v_dims:
    h_axis_y.add(round(f(d.get('code_23',0)), 1))
    h_axis_y.add(round(f(d.get('code_24',0)), 1))
h_clustered = cluster(list(h_axis_y), tol=50)

# ---- 按大间距分组（区段边界 > 5000mm）----
v_sorted = sorted(v_clustered)
gaps = [v_sorted[i+1]-v_sorted[i] for i in range(len(v_sorted)-1)]

segments = []
seg_start = 0
for i, g in enumerate(gaps):
    if abs(g) > 5000:
        segments.append(v_sorted[seg_start:i+1])
        seg_start = i+1
segments.append(v_sorted[seg_start:])

# ---- 每个区段筛选主轴线 (gap > 800mm 的结构跨度) ----
# 结构轴线 = 间距 > 800mm 的轴线（过滤墙厚/偏移的次轴线）
main_segments = []
sub_segments = []
for seg in segments:
    main_x = [seg[0]]  # 第一条总是主轴线
    sub_x = []
    for i in range(1, len(seg)):
        gap = seg[i] - seg[i-1]
        if gap > 800:
            main_x.append(seg[i])
        else:
            sub_x.append(seg[i])
    main_segments.append(main_x)
    sub_segments.append(sub_x)

# ---- 水平轴线筛选 ----
h_sorted = sorted(h_clustered)
h_gaps = [h_sorted[i+1]-h_sorted[i] for i in range(len(h_sorted)-1)]
main_h = [h_sorted[0]]
sub_h = []
for i in range(1, len(h_sorted)):
    gap = h_sorted[i] - h_sorted[i-1]
    if gap > 800:
        main_h.append(h_sorted[i])
    else:
        sub_h.append(h_sorted[i])

print('=== 主结构轴网（间距>800mm）===')
print(f'\n垂直主轴线:')
for si, seg in enumerate(main_segments):
    spans = [f'{seg[i+1]-seg[i]:.0f}mm' for i in range(len(seg)-1)]
    print(f'  区段{chr(65+si)}: {len(seg)}条, X[{seg[0]:.0f} - {seg[-1]:.0f}], 跨度: {", ".join(spans)}')
    print(f'    X={seg}')

print(f'\n水平主轴线: {len(main_h)}条')
h_spans = [f'{main_h[i+1]-main_h[i]:.0f}mm' for i in range(len(main_h)-1)]
print(f'  Y={main_h}, 跨度: {", ".join(h_spans)}')

print(f'\n过滤掉的次轴线:')
for si, seg in enumerate(sub_segments):
    if seg:
        print(f'  区段{chr(65+si)}: {seg}')
print(f'  水平次轴线: {sub_h}')

# ========== 生成 DXF ==========
def write_clean_dxf(main_segs, main_h, subs_x, subs_h, filepath):
    lines = []
    lines.append('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC')
    lines.append('0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n5')
    
    layers = [
        ('0', '7', 'CONTINUOUS'),
        ('A-AXIS', '3', 'CENTER2'),        # 主轴线 - 绿, 双点划线
        ('A-AXIS-SUB', '6', 'CENTER'),      # 次轴线 - 紫, 点划线
        ('A-AXIS-LABEL', '7', 'CONTINUOUS'), # 轴号圈
        ('A-AXIS-DIM', '4', 'CONTINUOUS'),   # 尺寸
    ]
    for name, color, ltype in layers:
        lines.append(f'0\nLAYER\n2\n{name}\n70\n0\n62\n{color}\n6\n{ltype}')
    lines.append('0\nENDTAB\n0\nENDSEC')
    
    lines.append('0\nSECTION\n2\nENTITIES')
    
    all_main_x = [x for seg in main_segs for x in seg]
    all_sub_x = [x for seg in subs_x for x in seg]
    all_h = main_h
    
    x_min, x_max = min(all_main_x), max(all_main_x)
    y_min, y_max = min(all_h), max(all_h)
    margin = (x_max - x_min) * 0.05 or 2000
    
    # 主轴线 — 粗线
    for x in all_main_x:
        lines.append(f'0\nLINE\n8\nA-AXIS\n62\n3\n10\n{fmt(x)}\n20\n{fmt(y_min-margin)}\n11\n{fmt(x)}\n21\n{fmt(y_max+margin)}')
    
    # 次轴线 — 细虚线
    for x in all_sub_x:
        lines.append(f'0\nLINE\n8\nA-AXIS-SUB\n62\n6\n10\n{fmt(x)}\n20\n{fmt(y_min-margin)}\n11\n{fmt(x)}\n21\n{fmt(y_max+margin)}')
    
    # 水平主轴线
    for y in all_h:
        lines.append(f'0\nLINE\n8\nA-AXIS\n62\n3\n10\n{fmt(x_min-margin)}\n20\n{fmt(y)}\n11\n{fmt(x_max+margin)}\n21\n{fmt(y)}')
    
    # 水平次轴线
    for y in subs_h:
        lines.append(f'0\nLINE\n8\nA-AXIS-SUB\n62\n6\n10\n{fmt(x_min-margin)}\n20\n{fmt(y)}\n11\n{fmt(x_max+margin)}\n21\n{fmt(y)}')
    
    # 轴号圈 + 尺寸线
    label_r = 300
    dim_offset = label_r * 5
    
    for i, x in enumerate(all_main_x):
        for label_y in [y_min - margin - label_r*2, y_max + margin + label_r*2]:
            lines.append(f'0\nCIRCLE\n8\nA-AXIS-LABEL\n10\n{fmt(x)}\n20\n{fmt(label_y)}\n40\n{fmt(label_r)}')
    
    # 尺寸线
    dim_y = y_min - margin - dim_offset
    for x in all_main_x:
        lines.append(f'0\nLINE\n8\nA-AXIS-DIM\n10\n{fmt(x)}\n20\n{fmt(dim_y)}\n11\n{fmt(x)}\n21\n{fmt(dim_y + label_r)}')
    
    # 跨度标注线
    for seg in main_segs:
        if len(seg) >= 2:
            seg_dim_y = dim_y - label_r
            lines.append(f'0\nLINE\n8\nA-AXIS-DIM\n10\n{fmt(seg[0])}\n20\n{fmt(seg_dim_y)}\n11\n{fmt(seg[-1])}\n21\n{fmt(seg_dim_y)}')
            # 端头45°短斜线
            for x in [seg[0], seg[-1]]:
                lines.append(f'0\nLINE\n8\nA-AXIS-DIM\n10\n{fmt(x-label_r*0.707)}\n20\n{fmt(seg_dim_y-label_r*0.707)}\n11\n{fmt(x+label_r*0.707)}\n21\n{fmt(seg_dim_y+label_r*0.707)}')
    
    lines.append('0\nENDSEC\n0\nEOF')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

# 生成主结构轴网 DXF
dxf_path = os.path.join(OUT_DIR, '主结构轴网.dxf')
write_clean_dxf(main_segments, main_h, sub_segments, sub_h, dxf_path)
print(f'\n✅ 主结构轴网: {dxf_path}')

# 各区段独立主轴线
for si, seg in enumerate(main_segments):
    dxf_seg = os.path.join(OUT_DIR, f'主结构轴网_{chr(65+si)}区.dxf')
    write_clean_dxf([seg], main_h, [sub_segments[si]], sub_h, dxf_seg)
    print(f'✅ {chr(65+si)}区主结构轴网: {dxf_seg}')

print('\n=== 使用说明 ===')
print('主轴线 (A-AXIS, 绿色): 结构柱网/承重墙定位线，间距>800mm')
print('次轴线 (A-AXIS-SUB, 紫色): 墙厚偏移/门洞/细部分隔线')
print('建议: 先加载主结构轴网，再叠加墙体骨架')
