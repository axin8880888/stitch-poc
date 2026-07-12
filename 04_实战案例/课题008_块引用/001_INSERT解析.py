#!/usr/bin/env python3
"""
课题008 — INSERT 块引用解析
"""

import os, sys, json
from collections import Counter, defaultdict

OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题008_块引用'


def parse_inserts(filepath):
    """从原始 DXF 提取 INSERT 和 BLOCK 定义"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')
    S = [l.strip() for l in lines]
    N = len(S)
    
    # 提取 BLOCK 定义
    blocks = {}
    in_blocks_sec = False
    in_block = False
    block_name = None
    block_entities = 0
    for i in range(N):
        if S[i] == 'BLOCKS' and i > 0 and S[i-1] == '2':
            in_blocks_sec = True
        if in_blocks_sec and S[i] == 'ENDSEC':
            break
        if in_blocks_sec and S[i] == 'BLOCK' and i > 0 and S[i-1] == '0':
            in_block = True; block_name = None; block_entities = 0
        if in_block and S[i] == 'ENDBLK':
            if block_name:
                blocks[block_name] = block_entities
            in_block = False; block_entities = 0
        if in_block and S[i] == '2' and block_name is None:
            if i+1 < N: block_name = S[i+1]
        if in_block and S[i] == '0' and i+1 < N and S[i+1] not in ('BLOCK', 'ENDBLK', 'ENDSEC'):
            block_entities += 1
    
    # 提取 INSERT 实体
    start = -1; end = -1
    for i in range(N):
        if S[i] == 'ENTITIES' and i > 0 and S[i-1] == '2':
            for j in range(i+1, min(i+10, N)):
                if S[j] == '0': start = j; break
        if start >= 0 and S[i] == 'ENDSEC': end = i; break
    
    if start < 0: return [], blocks
    
    inserts = []
    i = start
    while i < end:
        if S[i] == '0' and i+1 < end and S[i+1] == 'INSERT':
            ins = {}
            i += 2
            while i < end:
                s = S[i]; i += 1
                if s == '0': break
                val = S[i] if i < end else ''
                if s == '2': ins['block'] = val
                elif s == '8': ins['layer'] = val
                elif s == '10': ins['x'] = float(val)
                elif s == '20': ins['y'] = float(val)
                elif s == '30': ins['z'] = float(val)
                elif s == '41': ins['scale_x'] = float(val)
                elif s == '42': ins['scale_y'] = float(val)
                elif s == '43': ins['scale_z'] = float(val)
                elif s == '50': ins['rotation'] = float(val)
                elif s == '62': ins['color'] = int(val)
                elif s == '70': ins['col_count'] = int(val)
                elif s == '71': ins['row_count'] = int(val)
                elif s == '44': ins['col_spacing'] = float(val)
                elif s == '45': ins['row_spacing'] = float(val)
                i += 1
            inserts.append(ins)
        else:
            i += 1
    
    return inserts, blocks


def classify_block(name):
    """块名分类"""
    if name.startswith('*'):
        return '匿名块'
    if name.startswith('A$C') or name.startswith('A$B'):
        return '代理匿名块'
    if 'YLD' in name.upper() or 'STUDIO' in name.upper():
        return '标准库(YLD)'
    if 'ZHOUXIAN' in name.upper():
        return '轴线符号'
    if len(name) <= 5:
        return '短名块'
    if name.isupper() and len(name) > 5 and not any(c.isdigit() for c in name):
        return '大写块'
    if any(c.islower() for c in name):
        return '小写块'
    return '其他'


def generate_report(inserts, blocks, filename=''):
    report = []
    sep = '=' * 65
    
    report.append(sep)
    report.append("  课题008 — INSERT 块引用解析报告")
    report.append("  文件: %s" % filename)
    report.append(sep)
    report.append("")
    
    report.append("  1. 概况")
    report.append("  " + '-' * 50)
    report.append("    INSERT 引用: %d" % len(inserts))
    report.append("    BLOCK 定义: %d" % len(blocks))
    report.append("")
    
    # 块引用分布
    blk_counts = Counter(ins['block'] for ins in inserts)
    report.append("  2. 块引用 TOP20")
    report.append("  " + '-' * 50)
    for b, c in blk_counts.most_common(20):
        defined = '✓' if b in blocks else '✗未定义'
        ents = blocks.get(b, 0) if b in blocks else '?'
        report.append("    %-30s: %d次 [%s][%d实体]" % (b, c, defined, ents if isinstance(ents, int) else 0))
    report.append("")
    
    # 图层分布
    layers = Counter(ins['layer'] for ins in inserts)
    report.append("  3. 图层分布")
    report.append("  " + '-' * 50)
    for l, c in layers.most_common():
        report.append("    %-30s: %d" % (l, c))
    report.append("")
    
    # 块名分类
    report.append("  4. 块名质量分析")
    report.append("  " + '-' * 50)
    categories = Counter()
    for ins in inserts:
        categories[classify_block(ins['block'])] += 1
    for cat, cnt in categories.most_common():
        report.append("    %-15s: %d" % (cat, cnt))
    report.append("")
    
    # 所有 INSERT 明细
    report.append("  5. INSERT 明细")
    report.append("  " + '-' * 50)
    for i, ins in enumerate(inserts, 1):
        r = ins.get('rotation', 0)
        s = ins.get('scale_x', 1)
        report.append("    #%d: %-30s @(%.0f, %.0f) rot=%.0f scale=%.2f layer=%s" % (
            i, ins.get('block','?'), ins.get('x',0), ins.get('y',0), r, s, ins.get('layer','?')))
    
    report.append("")
    report.append(sep)
    report.append("  报告结束")
    report.append(sep)
    return '\n'.join(report)


def render_insert_svg(inserts, output_path, title='INSERT 可视化'):
    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="0 0 1000 800">')
    lines.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    lines.append('<text x="500" y="25" text-anchor="middle" fill="#e0e0e0" font-size="14" font-family="monospace">%s</text>' % title)
    
    all_x = [i.get('x', 0) for i in inserts]
    all_y = [i.get('y', 0) for i in inserts]
    if not all_x:
        lines.append('<text x="500" y="400" fill="#888" text-anchor="middle">无数据</text>')
        lines.append('</svg>')
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        return
    
    mnx, mxx = min(all_x), max(all_x)
    mny, mxy = min(all_y), max(all_y)
    marg = max((mxx-mnx)*0.1, 100)
    sw, sh = 960, 760
    
    def tx(x): return 20 + (x - mnx + marg) / (mxx - mnx + 2*marg) * sw
    def ty(y): return 20 + (mxy + marg - y) / (mxy - mny + 2*marg) * sh
    
    cat_colors = {
        '标准库(YLD)': '#4fc3f7', '轴线符号': '#ff7043', '代理匿名块': '#81c784',
        '匿名块': '#888', '短名块': '#ffb74d', '大写块': '#ce93d8', '小写块': '#4dd0e1', '其他': '#a1887f'
    }
    
    for ins in inserts:
        cat = classify_block(ins.get('block', ''))
        c = cat_colors.get(cat, '#888')
        x, y = tx(ins.get('x', 0)), ty(ins.get('y', 0))
        name = ins.get('block', '?')[:12]
        # dot for insert position
        lines.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s" opacity="0.7"/>' % (x, y, c))
        # label
        lines.append('<text x="%.1f" y="%.1f" fill="%s" font-size="8" font-family="monospace">%s</text>' % (x+5, y+3, c, name))
    
    lines.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', '-o', default=OUT_DIR)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    files = ['/storage/emulated/0/设计/DXF学习/晴碧园晶园26栋.dxf']
    
    for fpath in files:
        if not os.path.isfile(fpath):
            continue
        inserts, blocks = parse_inserts(fpath)
        print("INSERT: %d 个, BLOCK: %d 个" % (len(inserts), len(blocks)))
        
        report = generate_report(inserts, blocks, filename=fpath)
        print(report)
        
        bname = os.path.splitext(os.path.basename(fpath))[0]
        rpath = os.path.join(args.output_dir, bname + '_块报告.txt')
        with open(rpath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        svg_path = os.path.join(args.output_dir, bname + '_块引用.svg')
        render_insert_svg(inserts, svg_path, title='%s — INSERT' % bname)
        print("SVG: %s" % svg_path)
    
    print("\n课题008 完成!")


if __name__ == '__main__':
    main()
