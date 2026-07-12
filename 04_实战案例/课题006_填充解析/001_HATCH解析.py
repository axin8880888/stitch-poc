#!/usr/bin/env python3
"""
课题006 — HATCH 填充解析与重构
直接从原始 DXF 提取 HATCH 实体
"""

import os, sys, json, math
from collections import defaultdict, Counter

OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题006_填充解析'


def parse_hatches_raw(filepath):
    """直接从 DXF 文本提取 HATCH 实体"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    lines = content.split('\n')
    stripped = [l.strip() for l in lines]
    N = len(stripped)
    
    # 找到 ENTITIES 段
    ent_start = -1
    ent_end = -1
    i = 0
    while i < N:
        if stripped[i] == '2' and i+1 < N and stripped[i+1] == 'ENTITIES':
            for j in range(i+2, min(i+10, N)):
                if stripped[j] == '0':
                    ent_start = j
                    break
            i += 1
            continue
        if stripped[i] == 'ENDSEC' and ent_start >= 0:
            ent_end = i
            break
        i += 1
    
    if ent_start < 0 or ent_end < 0:
        return []
    
    # 扫描 HATCH 实体
    hatches = []
    i = ent_start
    while i <= ent_end:
        if stripped[i] == '0' and i+1 < N and stripped[i+1] == 'HATCH':
            hatch = {
                'layer': '0',
                'pattern': '?',
                'boundaries': [],
                'vertices': [],
                'solid': False,
            }
            i += 2
            in_boundary = False
            boundary_verts = []
            
            while i <= ent_end:
                code = stripped[i]
                i += 1
                val = stripped[i] if i < N else ''
                
                if code == '0':
                    break  # 下一个实体
                
                if code == '8': hatch['layer'] = val
                elif code == '2': hatch['pattern'] = val
                elif code == '62': hatch['color'] = int(val)
                elif code == '70': hatch['type'] = int(val)
                elif code == '71': hatch['associative'] = int(val)
                elif code == '72': hatch['style'] = int(val)
                elif code == '73': hatch['pattern_type'] = int(val)
                elif code == '75': hatch['fill_style'] = int(val)
                elif code == '76': hatch['pattern_angle'] = float(val) if '.' in val else int(val)
                elif code == '91': hatch['num_boundaries'] = int(val)
                elif code == '92':
                    hatch['boundary_type'] = int(val)
                    in_boundary = True
                    boundary_verts = []
                elif code == '93':
                    hatch['num_vertices'] = int(val)
                elif code == '10' and in_boundary:
                    x = float(val)
                    i += 1
                    y = float(stripped[i]) if i < N else 0
                    # skip 20 and read 20 value
                    if stripped[i] != '20':
                        # read ahead
                        pass
                    boundary_verts.append((x, y))
                elif code == '20':
                    # 这个值已经在10的时候读了，跳过
                    pass
                elif code == '97':  # end of boundary
                    if boundary_verts:
                        hatch['vertices'].append(boundary_verts)
                    in_boundary = False
                i += 1
            
            if boundary_verts:
                hatch['vertices'].append(boundary_verts)
            
            hatch['solid'] = hatch.get('pattern', '') == 'SOLID'
            hatches.append(hatch)
        else:
            i += 1
    
    return hatches


# 简化版 — 直接扫描0/HATCH对并提取顶点
def extract_hatches_simple(filepath):
    """从 DXF 提取所有 HATCH 及其边界顶点"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.read().split('\n')
    
    N = len(lines)
    stripped = [l.strip() for l in lines]
    
    # 找 ENTITIES 段
    start = -1
    end = -1
    for i in range(N):
        if stripped[i] == 'ENTITIES' and i > 0 and stripped[i-1] == '2':
            for j in range(i+1, min(i+10, N)):
                if stripped[j] == '0':
                    start = j
                    break
        if start >= 0 and stripped[i] == 'ENDSEC':
            end = i
            break
    
    if start < 0:
        return []
    
    hatches = []
    i = start
    
    while i < end:
        if stripped[i] == '0' and i+1 < end and stripped[i+1] == 'HATCH':
            h = {'layer': '0', 'pattern': '?', 'vertices_list': [], 'solid': False}
            i += 2
            verts = []
            in_path = False
            
            while i < end:
                s = stripped[i]
                i += 1
                
                if s == '0':
                    if verts:
                        h['vertices_list'].append(verts)
                    break
                
                if s == '8': h['layer'] = stripped[i]; i += 1
                elif s == '2': h['pattern'] = stripped[i]; i += 1
                elif s == '70': h['type'] = int(stripped[i]); i += 1
                elif s == '91': h['boundaries'] = int(stripped[i]); i += 1
                elif s == '92': in_path = True; verts = []
                elif s == '93': h['num_verts'] = int(stripped[i]); i += 1
                elif s == '10' and in_path:
                    x = float(stripped[i]); i += 1
                    if i < end and stripped[i] == '20':
                        i += 1
                        y = float(stripped[i]) if i < end else 0
                        i += 1
                        verts.append((x, y))
                    else:
                        i += 1  # consume next token
                elif s == '20' and in_path:
                    # 已经在10处理了
                    i += 1
                elif s == '97':
                    if verts:
                        h['vertices_list'].append(verts)
                    in_path = False
                    verts = []
                    i += 1
                elif s == '98':
                    # 98, 10, 20 for the hatch loop
                    i += 1
                    if i < end and stripped[i] == '10':
                        i += 1
                        if i < end and stripped[i] == '20':
                            i += 1
                else:
                    i += 1
            
            h['solid'] = (h.get('pattern', '') == 'SOLID')
            hatches.append(h)
        else:
            i += 1
    
    return hatches


def generate_report(hatches, filename=''):
    report = []
    sep = '=' * 65
    
    report.append(sep)
    report.append("  课题006 — HATCH 填充解析报告")
    report.append("  文件: %s" % filename)
    report.append(sep)
    report.append("")
    
    report.append("  1. 概况")
    report.append("  " + '-' * 50)
    report.append("    总 HATCH 数: %d" % len(hatches))
    
    layers = Counter(h['layer'] for h in hatches)
    report.append("    图层分布:")
    for l, c in layers.most_common():
        report.append("      %-30s: %d" % (l, c))
    
    patterns = Counter(h.get('pattern', '?') for h in hatches)
    report.append("    图案类型:")
    for p, c in patterns.most_common():
        report.append("      %-12s: %d" % (p, c))
    report.append("")
    
    # 按图层/图案分组
    report.append("  2. 明细")
    report.append("  " + '-' * 50)
    for i, h in enumerate(hatches, 1):
        vert_count = sum(len(v) for v in h.get('vertices_list', []))
        report.append("    #%d: %-6s | layer=%-20s | 顶点=%d | 边界数=%d" % (
            i, h.get('pattern','?'), h.get('layer','?'), vert_count,
            h.get('boundaries', 0)))
    
    report.append("")
    report.append(sep)
    report.append("  报告结束")
    report.append(sep)
    
    return '\n'.join(report)


def render_hatch_svg(hatches, output_path, title='HATCH 填充可视化'):
    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="0 0 1000 800">')
    lines.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    lines.append('<text x="500" y="25" text-anchor="middle" fill="#e0e0e0" font-size="14" font-family="monospace">%s</text>' % title)
    
    # 收集所有顶点找边界
    all_x = []
    all_y = []
    for h in hatches:
        for verts in h.get('vertices_list', []):
            for x, y in verts:
                all_x.append(x)
                all_y.append(y)
    
    if not all_x:
        lines.append('<text x="500" y="400" text-anchor="middle" fill="#888">无数据</text>')
        lines.append('</svg>')
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        return
    
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    margin = max((max_x-min_x)*0.1, 100)
    margin_y = max((max_y-min_y)*0.1, 100)
    sw, sh = 960, 760
    
    def tx(x):
        return 20 + (x - min_x + margin) / (max_x - min_x + 2*margin) * sw
    
    def ty(y):
        return 20 + (max_y + margin_y - y) / (max_y - min_y + 2*margin_y) * sh
    
    # 颜色映射
    colors = ['#4fc3f7', '#ff7043', '#81c784', '#ffb74d', '#ce93d8', '#4dd0e1',
              '#f06292', '#a1887f', '#90a4ae', '#fff176']
    
    for idx, h in enumerate(hatches):
        c = colors[idx % len(colors)]
        for verts in h.get('vertices_list', []):
            if len(verts) < 2:
                continue
            pts = ' '.join('%.1f,%.1f' % (tx(x), ty(y)) for x, y in verts)
            # 闭合
            pts += ' %.1f,%.1f' % (tx(verts[0][0]), ty(verts[0][1]))
            lines.append('<polygon points="%s" fill="%s" fill-opacity="0.25" stroke="%s" stroke-width="1.5" stroke-opacity="0.7"/>' % (pts, c, c))
            
            # 图案名标注在重心
            cx = sum(x for x, y in verts) / len(verts)
            cy = sum(y for x, y in verts) / len(verts)
            lines.append('<text x="%.1f" y="%.1f" fill="white" font-size="9" font-family="monospace" text-anchor="middle">%s</text>' % (
                tx(cx), ty(cy), h.get('pattern', '?')))
    
    lines.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', '-o', default=OUT_DIR)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    files = [
        '/storage/emulated/0/设计/DXF学习/晴碧园晶园26栋.dxf',
        '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf',
    ]
    
    for fpath in files:
        if not os.path.isfile(fpath):
            continue
        print("分析: %s" % os.path.basename(fpath))
        hatches = extract_hatches_simple(fpath)
        print("  HATCH 提取: %d 个" % len(hatches))
        
        report = generate_report(hatches, filename=fpath)
        print(report)
        
        bname = os.path.splitext(os.path.basename(fpath))[0]
        rpath = os.path.join(args.output_dir, bname + '_填充报告.txt')
        with open(rpath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        svg_path = os.path.join(args.output_dir, bname + '_填充.svg')
        render_hatch_svg(hatches, svg_path, title='%s — HATCH' % bname)
        print("SVG: %s" % svg_path)
        print()
    
    print("课题006 完成!")


if __name__ == '__main__':
    main()
