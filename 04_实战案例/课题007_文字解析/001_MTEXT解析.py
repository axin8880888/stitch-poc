#!/usr/bin/env python3
"""
课题007 — MTEXT 多行文字解析
"""

import os, sys, json, re
from collections import Counter, defaultdict

OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题007_文字解析'


def extract_mtexts(filepath):
    """从原始 DXF 提取 MTEXT 实体"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    lines = content.split('\n')
    stripped = [l.strip() for l in lines]
    N = len(stripped)
    
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
    
    mtexts = []
    i = start
    while i < end:
        if stripped[i] == '0' and i+1 < end and stripped[i+1] == 'MTEXT':
            m = {}
            i += 2
            while i < end:
                s = stripped[i]
                i += 1
                if s == '0':
                    break
                val = stripped[i] if i < end else ''
                if s == '1': m['text'] = val
                elif s == '8': m['layer'] = val
                elif s == '7': m['style'] = val
                elif s == '40': m['height'] = float(val)
                elif s == '41': m['width'] = float(val)
                elif s == '10': m['x'] = float(val)
                elif s == '20': m['y'] = float(val)
                elif s == '30': m['z'] = float(val)
                elif s == '71': m['attachment'] = int(val)
                elif s == '72': m['direction'] = int(val)
                elif s == '73': m['ref'] = int(val)
                elif s == '62': m['color'] = int(val)
                i += 1
            mtexts.append(m)
        else:
            i += 1
    
    return mtexts


def classify_text(text):
    """按内容分类文字"""
    if not text:
        return '空'
    t = text.strip()
    # 房间名
    rooms = {'卧室','客厅','餐厅','厨房','卫生间','阳台','书房','茶室','休闲区',
             '储藏间','衣帽间','玄关','门厅','过道','走廊','主卧','次卧','儿童房','保姆房'}
    if t in rooms:
        return '房间名'
    # 尺寸标注文字
    if any(c.isdigit() for c in t) and any(c in '×xX*' for c in t):
        return '尺寸'
    if t.startswith('图名') or t.startswith('平面') or t.startswith('立面') or t.startswith('剖面'):
        return '图名'
    if any(c in '标高' for c in t) or 'H=' in t or 'h=' in t.lower():
        return '标高'
    if '说明' in t or '注:' in t or '注：' in t:
        return '说明'
    if '材料' in t or '木饰面' in t or '石材' in t or '瓷砖' in t or '乳胶漆' in t or '壁纸' in t:
        return '材料标注'
    if '拆除' in t or '新建' in t or '保留' in t:
        return '施工标注'
    if len(t) <= 4:
        return '短文本'
    return '说明文字'


def generate_report(mtexts, filename=''):
    report = []
    sep = '=' * 65
    
    report.append(sep)
    report.append("  课题007 — MTEXT 文字解析报告")
    report.append("  文件: %s" % filename)
    report.append(sep)
    report.append("")
    report.append("  1. 概况")
    report.append("  " + '-' * 50)
    report.append("    MTEXT 总数: %d" % len(mtexts))
    
    # 图层
    layers = Counter(m.get('layer', '0') for m in mtexts)
    report.append("    图层分布:")
    for l, c in layers.most_common():
        report.append("      %-25s: %d" % (l, c))
    
    # 样式
    styles = Counter(m.get('style', '(无)') for m in mtexts)
    report.append("    样式: %s" % ', '.join('%s(%d)' % (s, c) for s, c in styles.most_common()))
    report.append("")
    
    # 2. 内容分类
    report.append("  2. 内容分类")
    report.append("  " + '-' * 50)
    categories = Counter()
    for m in mtexts:
        categories[classify_text(m.get('text', ''))] += 1
    for cat, cnt in categories.most_common():
        report.append("    %-12s: %d" % (cat, cnt))
    report.append("")
    
    # 3. 明细
    report.append("  3. 全部文字明细")
    report.append("  " + '-' * 50)
    for i, m in enumerate(mtexts, 1):
        txt = m.get('text', '(?)')
        h = m.get('height', 0)
        layer = m.get('layer', '0')
        style = m.get('style', '?')
        report.append("    #%d: %-36s | h=%.0f | style=%-6s | layer=%s" % (
            i, txt[:36], h, style, layer))
    
    report.append("")
    report.append(sep)
    report.append("  报告结束")
    report.append(sep)
    return '\n'.join(report)


def render_mtext_svg(mtexts, output_path, title='MTEXT 可视化'):
    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="0 0 1000 800">')
    lines.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    lines.append('<text x="500" y="25" text-anchor="middle" fill="#e0e0e0" font-size="14" font-family="monospace">%s</text>' % title)
    
    # 分类颜色
    cat_colors = {
        '房间名': '#4fc3f7', '短文本': '#81c784', '尺寸': '#ffb74d',
        '说明文字': '#ce93d8', '图名': '#f06292', '材料标注': '#4dd0e1',
        '施工标注': '#fff176', '说明': '#a1887f', '标高': '#ff7043',
        '空': '#888',
    }
    
    all_x = [m.get('x', 0) for m in mtexts]
    all_y = [m.get('y', 0) for m in mtexts]
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
    
    for i, m in enumerate(mtexts):
        cat = classify_text(m.get('text', ''))
        c = cat_colors.get(cat, '#888')
        x, y = tx(m.get('x', 0)), ty(m.get('y', 0))
        txt = m.get('text', '')[:20]
        h = max(m.get('height', 100) / 10, 10)
        lines.append('<text x="%.1f" y="%.1f" fill="%s" font-size="%.0f" font-family="monospace">%s</text>' % (
            x, y, c, min(h, 30), txt))
    
    # 图例
    cats_used = Counter(classify_text(m.get('text', '')) for m in mtexts)
    ly = 30
    for cat, c in cat_colors.items():
        if cat in cats_used:
            lines.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/>' % (ly, sh+20, c))
            lines.append('<text x="%d" y="%d" fill="#ccc" font-size="10">%s</text>' % (ly+16, sh+30, cat))
            ly += 80
    
    lines.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', '-o', default=OUT_DIR)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    files = [
        '/storage/emulated/0/设计/DXF学习/晴碧园晶园26栋.dxf',
    ]
    
    for fpath in files:
        if not os.path.isfile(fpath):
            continue
        mtexts = extract_mtexts(fpath)
        print("MTEXT: %d 个" % len(mtexts))
        
        report = generate_report(mtexts, filename=fpath)
        print(report)
        
        bname = os.path.splitext(os.path.basename(fpath))[0]
        rpath = os.path.join(args.output_dir, bname + '_文字报告.txt')
        with open(rpath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        svg_path = os.path.join(args.output_dir, bname + '_文字.svg')
        render_mtext_svg(mtexts, svg_path, title='%s — MTEXT' % bname)
        print("SVG: %s" % svg_path)
    
    print("\n课题007 完成!")


if __name__ == '__main__':
    main()
