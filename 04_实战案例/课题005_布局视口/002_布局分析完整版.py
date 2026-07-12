#!/usr/bin/env python3
"""
课题005 — 布局空间分析(完整版)
含 ENTITIES 段 VIEWPORT 提取
"""

import os, sys, json, re
from collections import defaultdict

OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题005_布局视口'


def parse_raw_sections(filepath):
    """将 DXF 按段切分"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')
    sections = {}
    cur = None
    start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s == 'SECTION':
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip() == '2' and j+1 < len(lines):
                    cur = lines[j+1].strip()
                    start = i
                    break
        elif s == 'ENDSEC' and cur:
            sections[cur] = lines[start:i+1]
            cur = None
    return sections, lines


def collect_viewports(lines_section):
    """从一段文本中提取所有 VIEWPORT 实体"""
    vps = []
    tokens = []
    for line in lines_section:
        tokens.append(line.strip())
    
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == '0' and i+1 < n and tokens[i+1] == 'VIEWPORT':
            vp = {}
            i += 2
            while i < n:
                code = tokens[i]
                i += 1
                if code == '0':
                    break  
                val = tokens[i] if i < n else ''
                if code == '8':
                    vp['layer'] = val
                elif code == '10': vp['cx'] = float(val)
                elif code == '20': vp['cy'] = float(val)
                elif code == '30': vp['cz'] = float(val)
                elif code == '40': vp['width'] = float(val)
                elif code == '41': vp['height'] = float(val)
                elif code == '69': vp['status'] = int(val)
                elif code == '42': vp['scale'] = float(val)
                elif code == '62': vp['color'] = int(val)
                elif code == '12': vp['twist_x'] = float(val)
                elif code == '22': vp['twist_y'] = float(val)
                elif code == '5':  vp['handle'] = val
                i += 1
            vps.append(vp)
        else:
            i += 1
    return vps


def collect_layouts(lines_section):
    """从 OBJECTS 段提取 LAYOUT 对象"""
    layouts = []
    tokens = []
    for line in lines_section:
        tokens.append(line.strip())
    
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == '0' and i+1 < n and tokens[i+1] == 'LAYOUT':
            layout = {}
            i += 2
            while i < n:
                code = tokens[i]
                i += 1
                if code == '0':
                    break
                val = tokens[i] if i < n else ''
                if code == '1': layout['name'] = val
                elif code == '2': layout['printer'] = val
                elif code == '4': layout['paper'] = val
                elif code == '7': layout['ctb'] = val
                elif code == '5': layout['handle'] = val
                elif code == '44': layout['pw'] = float(val)
                elif code == '45': layout['ph'] = float(val)
                elif code == '46': layout['vcx'] = float(val)
                elif code == '47': layout['vcy'] = float(val)
                elif code == '48': layout['vw'] = float(val)
                elif code == '49': layout['vh'] = float(val)
                elif code == '142': layout['scale'] = float(val)
                i += 1
            layouts.append(layout)
        else:
            i += 1
    return layouts


def analyze(filepath):
    """完整布局分析"""
    sections, _ = parse_raw_sections(filepath)
    basename = os.path.basename(filepath)
    
    # LAYOUTs from OBJECTS
    obj_lines = sections.get('OBJECTS', [])
    layouts = collect_layouts(obj_lines)
    
    # VIEWPORTs in BLOCKS (paper space)
    blk_lines = sections.get('BLOCKS', [])
    blk_vps = collect_viewports(blk_lines)
    
    # VIEWPORTs in ENTITIES (model space paper space viewports)
    ent_lines = sections.get('ENTITIES', [])
    ent_vps = collect_viewports(ent_lines)
    
    # Report
    report = []
    report.append('=' * 65)
    report.append("  课题005 — 布局与视口分析")
    report.append("  文件: %s" % basename)
    report.append('=' * 65)
    report.append("")
    
    # Layouts
    report.append("  1. 布局定义 (OBJECTS段)")
    report.append("  " + '-' * 50)
    if layouts:
        for lay in layouts:
            report.append("    布局名: %s (handle:%s)" % (lay.get('name','?'), lay.get('handle','?')))
            report.append("      纸张: %s (%s)" % (lay.get('paper','?'), lay.get('printer','?')))
            report.append("      打印样式: %s" % lay.get('ctb','?'))
            pw = lay.get('pw', 0)
            ph = lay.get('ph', 0)
            vw = lay.get('vw', 0)
            vh = lay.get('vh', 0)
            report.append("      纸张尺寸: %.0f x %.0f mm" % (pw, ph))
            report.append("      视口中心: (%.1f, %.1f)" % (lay.get('vcx',0), lay.get('vcy',0)))
            report.append("      模型空间视野: %.0f x %.0f" % (vw, vh))
            if pw and vw:
                s = abs(vw) / pw if pw else 0
                report.append("      大致出图比例: 1:%.0f" % s if s > 0 else "      大致出图比例: ?")
            report.append("")
    else:
        report.append("    未找到 LAYOUT\n")
    
    # Viewports in BLOCKS
    report.append("  2. 视口实体 (BLOCKS段 = 布局空间)")
    report.append("  " + '-' * 50)
    if blk_vps:
        report.append("    共 %d 个" % len(blk_vps))
        for i, vp in enumerate(blk_vps, 1):
            scale = vp.get('scale', 0)
            sstr = "1:%.0f" % scale if scale > 0 else "?"
            report.append("    #%d: layer=%-12s center=(%.0f, %.0f)  size=%.0fx%.0f  scale=%s  status=%d" % (
                i, vp.get('layer','?'), vp.get('cx',0), vp.get('cy',0),
                vp.get('width',0), vp.get('height',0), sstr, vp.get('status',0)))
    else:
        report.append("    未找到\n")
    
    # Viewports in ENTITIES
    report.append("")
    report.append("  3. 视口实体 (ENTITIES段 = 图纸空间)")
    report.append("  " + '-' * 50)
    if ent_vps:
        report.append("    共 %d 个" % len(ent_vps))
        layers = defaultdict(int)
        for vp in ent_vps:
            layers[vp.get('layer','?')] += 1
        report.append("    图层分布:")
        for l, c in sorted(layers.items()):
            report.append("      %-12s: %d个" % (l, c))
        report.append("")
        # 显示前几个
        for i, vp in enumerate(ent_vps[:5], 1):
            scale = vp.get('scale', 0)
            sstr = "1:%.0f" % scale if scale > 0 else "?"
            report.append("    #%d: layer=%-12s center=(%.1f, %.1f)  size=%.1fx%.1f  scale=%s" % (
                i, vp.get('layer','?'), vp.get('cx',0), vp.get('cy',0),
                vp.get('width',0), vp.get('height',0), sstr))
        if len(ent_vps) > 5:
            report.append("    ... 还有 %d 个" % (len(ent_vps)-5))
    else:
        report.append("    未找到\n")
    
    # Summary
    report.append("")
    report.append("  4. 分析总结")
    report.append("  " + '-' * 50)
    report.append("    布局数: %d" % len(layouts))
    report.append("    BLOCKS段视口: %d" % len(blk_vps))
    report.append("    ENTITIES段视口: %d" % len(ent_vps))
    report.append("    合计 VIEWPORT: %d" % (len(blk_vps) + len(ent_vps)))
    
    report.append("")
    report.append('=' * 65)
    report.append("  报告结束")
    report.append('=' * 65)
    
    return '\n'.join(report)


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
        print("\n%s" % ('='*65))
        print("分析: %s" % os.path.basename(fpath))
        report = analyze(fpath)
        print(report)
        
        basename = os.path.splitext(os.path.basename(fpath))[0]
        rpath = os.path.join(args.output_dir, basename + '_布局分析.txt')
        with open(rpath, 'w', encoding='utf-8') as f:
            f.write(report)
        print("报告: %s" % rpath)
    
    print("\n课题005 完成!")


if __name__ == '__main__':
    main()
