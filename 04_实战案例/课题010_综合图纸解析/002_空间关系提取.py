#!/usr/bin/env python3
"""
课题010 — 空间关系提取（V2）
从解析JSON中提取：
1. 墙体边界（LWPOLYLINE + LINE 聚类）
2. 门窗定位
3. 文字标注 → 房间
4. 家具分布
5. 输出结构化空间SVG
"""
import json, os, math
from collections import defaultdict, Counter

JSON_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录'
OUT_DIR  = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题010_综合图纸解析'

def load_json(basename):
    with open(os.path.join(JSON_DIR, basename), 'r', encoding='utf-8') as f:
        return json.load(f)

def get_code(ent, code):
    """从dict中提取指定group code的值"""
    key = 'code_%s' % code
    return ent.get(key)

def classify_entities(data):
    """以 group code 0 为真实类型重新分类"""
    classes = defaultdict(list)
    real_types = Counter()
    
    for ent in data.get('entities', []):
        etype = get_code(ent, 0) or ent.get('type', '')
        layer = ent.get('layer', '0')
        real_types[etype] += 1
        classes[(etype, layer)].append(ent)
    
    return classes, real_types

def get_wall_candidates(classes):
    """提取墙体相关图元"""
    walls = []
    # 墙体图层
    wall_layers = {l for l in [l for (t,l) in classes if '墙' in l or 'WALL' in l.upper()]}
    for (etype, layer), ents in classes.items():
        if layer in wall_layers and etype in ('LWPOLYLINE', 'LINE', 'ARC'):
            walls.extend(ents)
    return walls, wall_layers

def get_room_candidates(texts, walls):
    """通过文字标注推断房间"""
    rooms = []
    room_keywords = ['卧室','客厅','餐厅','卫','厨','房','阳台','梯','厅','室']
    
    for txt in texts:
        content = txt.get('code_1', '')
        if not content:
            continue
        matched = any(kw in content for kw in room_keywords)
        if matched:
            rooms.append({
                'name': content.strip(),
                'pos': (get_code(txt, 10), get_code(txt, 20)),
                'height': get_code(txt, 40)
            })
    return rooms

def generate_space_report(data, classes, real_types):
    lines = []
    sep = '=' * 65
    lines.append(sep)
    lines.append('  课题010 V2 — 空间关系提取报告')
    lines.append(sep)
    lines.append('')
    
    total = len(data.get('entities', []))
    lines.append('总图元数: %d' % total)
    lines.append('')
    
    lines.append('【真实 DXF 类型分布】')
    for t, c in real_types.most_common(25):
        lines.append('  %-15s: %d' % (repr(t), c))
    lines.append('')
    
    # MTEXT 文本提取
    mtexts = []
    for ent in data.get('entities', []):
        if get_code(ent, 0) == 'MTEXT':
            txt = get_code(ent, 1) or ''
            if txt.strip():
                mtexts.append(ent)
    lines.append('【含文本的 MTEXT: %d条】' % len(mtexts))
    for txt in sorted(mtexts, key=lambda e: (get_code(e, 40) or 0), reverse=True):
        content = (txt.get('code_1', '') or '').strip()
        h = get_code(txt, 40)
        lyr = txt.get('layer', '')
        lines.append('  H=%s  [%s] %s' % (h, lyr, content))
    lines.append('')
    
    # 墙体分析
    walls, wall_layers = get_wall_candidates(classes)
    lines.append('【墙体分析】')
    lines.append('  墙体相关图层: %d个' % len(wall_layers))
    for wl in sorted(wall_layers):
        cnt = sum(1 for (t,l), ents in classes.items() if l == wl for e in ents)
        lines.append('    %-35s: %d entities' % (wl, cnt))
    lines.append('')
    
    # 房间推断
    rooms = get_room_candidates(mtexts, walls)
    lines.append('【房间标注】')
    if rooms:
        for r in sorted(rooms, key=lambda x: x['name']):
            lines.append('  %-12s (%.0f, %.0f)' % (r['name'], r['pos'][0], r['pos'][1]))
    else:
        lines.append('  （未找到含房间关键词的文字）')
    lines.append('')
    
    # 门窗
    doors = []
    for (etype, layer), ents in classes.items():
        if etype == 'ARC' and ('门' in layer or '门' in str(ents[:1])):
            doors.extend(ents)
    lines.append('【门窗】')
    lines.append('  门弧: %d个' % len(doors))
    if doors:
        radii = [get_code(d, 40) for d in doors if get_code(d, 40)]
        if radii:
            lines.append('  半径范围: %.0f~%.0f' % (min(radii), max(radii)))
    lines.append('')
    
    # 家具
    furn_layers = {l for (t,l) in classes if '家具' in l or 'FURN' in l.upper() or '洁具' in l}
    furn_count = sum(len(ents) for (t,l), ents in classes.items() if l in furn_layers)
    lines.append('【家具/设备】')
    lines.append('  家具图层: %d个' % len(furn_layers))
    for fl in sorted(furn_layers):
        cnt = sum(len(ents) for (t,l), ents in classes.items() if l == fl)
        lines.append('    %-35s: %d entities' % (fl, cnt))
    lines.append('  总计: %d entities' % furn_count)
    lines.append('')
    
    lines.append(sep)
    lines.append('  报告结束')
    lines.append(sep)
    return '\n'.join(lines)


def generate_room_svg(rooms, door_arcs, output_path):
    """生成房间分布SVG"""
    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">')
    lines.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    lines.append('<text x="400" y="25" text-anchor="middle" fill="#e0e0e0" font-size="14" font-family="monospace">课题010 — 房间与空间分布</text>')
    
    # 收集坐标范围
    all_x = [r['pos'][0] for r in rooms] + [d.get('code_10',0) or 0 for d in door_arcs]
    all_y = [r['pos'][1] for r in rooms] + [d.get('code_20',0) or 0 for d in door_arcs]
    
    if all_x and all_y:
        mnx, mxx = min(all_x), max(all_x)
        mny, mxy = min(all_y), max(all_y)
        wdt = max(mxx - mnx, 1)
        hgt = max(mxy - mny, 1)
        marg = max(wdt * 0.2, 1000)
        
        def tx(v): return 20 + (v - mnx + marg) / (wdt + 2*marg) * 760
        def ty(v): return 20 + (mxy + marg - v) / (hgt + 2*marg) * 560
        
        # 房间名
        colors = ['#4fc3f7','#ff7043','#81c784','#ffb74d','#ce93d8','#4dd0e1']
        for i, r in enumerate(rooms):
            sx, sy = tx(r['pos'][0]), ty(r['pos'][1])
            c = colors[i % len(colors)]
            lines.append('<text x="%.1f" y="%.1f" fill="%s" font-size="12" font-family="monospace" text-anchor="middle">%s</text>' % (sx, sy, c, r['name']))
        
        # 门弧
        for d in door_arcs[:15]:
            dx = tx(get_code(d, 10) or 0)
            dy = ty(get_code(d, 20) or 0)
            lines.append('<circle cx="%.1f" cy="%.1f" r="3" fill="none" stroke="#e57373" stroke-width="1"/>' % (dx, dy))
        
        # 图例
        ly = 20
        lines.append('<rect x="680" y="%d" width="10" height="10" fill="#4fc3f7"/>' % ly)
        lines.append('<text x="695" y="%d" fill="#ccc" font-size="10">房间名' % (ly+9))
        lines.append('<circle cx="685" cy="%d" r="3" fill="none" stroke="#e57373" stroke-width="1"/>' % (ly+25))
        lines.append('<text x="695" y="%d" fill="#ccc" font-size="10">门弧' % (ly+30))
    else:
        lines.append('<text x="400" y="300" fill="#888" text-anchor="middle" font-size="14">无空间数据</text>')
    
    lines.append('</svg>')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    data = load_json('晴碧园晶园26栋_解析.json')
    print('加载: %d entities' % len(data.get('entities', [])))
    
    classes, real_types = classify_entities(data)
    report = generate_space_report(data, classes, real_types)
    print(report)
    
    rpath = os.path.join(OUT_DIR, '空间关系报告.txt')
    with open(rpath, 'w', encoding='utf-8') as f:
        f.write(report)
    print('报告: %s' % rpath)
    
    # SVG 房间分布
    mtexts = [e for e in data.get('entities', []) if get_code(e, 0) == 'MTEXT']
    doors = [e for e in data.get('entities', []) if get_code(e, 0) == 'ARC' and '门' in e.get('layer', '')]
    rooms = get_room_candidates(mtexts, [])
    
    svg_path = os.path.join(OUT_DIR, '房间分布.svg')
    generate_room_svg(rooms, doors, svg_path)
    print('SVG: %s' % svg_path)
    
    # 结构化JSON
    struct = {
        '房间': [{'name': r['name'], 'pos': list(r['pos']), 'height': r['height']} for r in rooms],
        '门弧个数': len(doors),
        '墙体图层': sorted(list({l for l in [l for (t,l) in classes if '墙' in l or 'WALL' in l.upper()]})),
    }
    jpath = os.path.join(OUT_DIR, '空间结构.json')
    with open(jpath, 'w', encoding='utf-8') as f:
        json.dump(struct, f, indent=2, ensure_ascii=False)
    print('结构化数据: %s' % jpath)
    print('课题010 V2 完成')

if __name__ == '__main__':
    main()
