#!/usr/bin/env python3
"""
课题010 — 综合图纸解析 FINAL
从 DXF 解析JSON 中提取并关联所有关键图元
输出：空间关系报告 + SVG可视化 + 结构化JSON
"""
import json, os, math
from collections import defaultdict, Counter

JSON_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录'
OUT_DIR  = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题010_综合图纸解析'

def load_json(bn):
    with open(os.path.join(JSON_DIR, bn), 'r', encoding='utf-8') as f:
        return json.load(f)

def fval(ent, code):
    """获取数值"""
    v = ent.get('code_%d' % code)
    if v is None:
        return 0.0
    try: return float(v)
    except: return 0.0

def sv(ent, code):
    """获取字符串"""
    return ent.get('code_%d' % code, '')

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = load_json('晴碧园晶园26栋_解析.json')
    ents = data.get('entities', [])
    
    # === 分类 ===
    by_type = Counter(e.get('type', '') for e in ents)
    by_layer = Counter(e.get('layer', '0') for e in ents)
    
    # MTEXT / 文本
    mtexts = [e for e in ents if e.get('type') == 'MTEXT']
    room_texts = []
    for m in mtexts:
        txt = sv(m, 1)
        if not txt: continue
        h = fval(m, 40)
        room_texts.append({'text': txt.strip(), 'height': h, 'layer': m.get('layer',''), 'x': fval(m,10), 'y': fval(m,20)})
    
    # 门弧
    door_arcs = [e for e in ents if e.get('type') == 'ARC' and '门' in e.get('layer','')]
    
    # 墙体图元（LWPOLYLINE 在 A-土建墙 / A-新隔墙）
    wall_layers = {l for l in by_layer if '墙' in l or 'WALL' in l.upper()}
    wall_entities = defaultdict(list)
    for l in wall_layers:
        wall_entities[l] = [e for e in ents if e.get('layer') == l]
    
    # 家具
    furn_layers = {l for l in by_layer if '家具' in l or 'FURN' in l.upper() or '洁具' in l}
    furn_entities = defaultdict(list)
    for l in furn_layers:
        furn_entities[l] = [e for e in ents if e.get('layer') == l]
    
    # 填充
    hatches = [e for e in ents if e.get('type') == 'HATCH']
    
    # 尺寸
    dims = [e for e in ents if e.get('type') == 'DIMENSION']
    
    # 块引用
    inserts = [e for e in ents if e.get('type') == 'INSERT']
    
    # === 分析 ===
    total_room_texts = len(room_texts)
    visible_texts = [t for t in room_texts if t['height'] == 140.0]
    furniture_texts = [t for t in room_texts if t['height'] == 100.0]
    
    room_names = [t['text'] for t in visible_texts]
    
    door_radii = [fval(d, 40) for d in door_arcs if fval(d, 40) > 0]
    door_widths = [int(r * math.pi / 2) for r in door_radii]
    
    # 墙体图元数统计
    total_wall_ents = sum(len(ents) for ents in wall_entities.values())
    total_furn_ents = sum(len(ents) for ents in furn_entities.values())
    
    # === 生成报告 ===
    report = []
    sep = '=' * 65
    report.append(sep)
    report.append('  课题010 — 综合图纸解析 FINAL')
    report.append(sep)
    report.append('')
    report.append('【概况】')
    report.append('  总图元: %d' % len(ents))
    report.append('')
    report.append('【类型分布 Top 10】')
    for t, c in by_type.most_common(10):
        report.append('  %-15s: %d' % (t, c))
    report.append('')
    report.append('【墙体系统】')
    report.append('  墙体图层: %d个' % len(wall_layers))
    for wl in sorted(wall_layers):
        c = sum(len(e) for l, ents in wall_entities.items() if l == wl for e in ents)
        report.append('    %-35s: %d' % (wl, c))
    report.append('  合计: %d entities' % total_wall_ents)
    report.append('')
    report.append('【房间标注（H=140）】')
    for r in room_names:
        report.append('  - %s' % r)
    report.append('')
    report.append('【家具/设备标注（H=100）】')
    for t in furniture_texts:
        report.append('  - %s' % t['text'])
    report.append('')
    report.append('【门窗系统】')
    report.append('  门弧: %d个' % len(door_arcs))
    if door_radii:
        report.append('  半径范围: %.0f~%.0f' % (min(door_radii), max(door_radii)))
        dw = Counter(door_widths)
        report.append('  估算门宽分布:')
        for w, c in dw.most_common(5):
            report.append('    %dmm: %d扇' % (w, c))
    report.append('')
    report.append('【填充系统】')
    report.append('  HATCH: %d个' % len(hatches))
    hatch_layers = Counter(h.get('layer','0') for h in hatches)
    for l, c in hatch_layers.most_common(5):
        report.append('    %-35s: %d' % (l, c))
    report.append('')
    report.append('【尺寸系统】')
    report.append('  DIMENSION: %d个' % len(dims))
    dim_layers = Counter(d.get('layer','0') for d in dims)
    for l, c in dim_layers.most_common(5):
        report.append('    %-35s: %d' % (l, c))
    report.append('')
    report.append('【家具系统】')
    report.append('  家具图层: %d个' % len(furn_layers))
    for fl in sorted(furn_layers):
        c = sum(len(ents) for l, ents in furn_entities.items() if l == fl for ents in ents)
        report.append('    %-35s: %d' % (fl, c))
    report.append('  合计: %d entities' % total_furn_ents)
    report.append('')
    report.append('【块引用】')
    report.append('  INSERT: %d个' % len(inserts))
    insert_layers = Counter(i.get('layer','0') for i in inserts)
    for l, c in insert_layers.most_common(5):
        report.append('    %-35s: %d' % (l, c))
    report.append('')
    report.append(sep)
    report.append('  报告结束')
    report.append(sep)
    
    report_text = '\n'.join(report)
    print(report_text)
    
    # === 保存 ===
    with open(os.path.join(OUT_DIR, '综合图纸解析报告.txt'), 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    # 结构化 JSON
    struct = {
        '概况': {'总图元': len(ents)},
        '类型分布': dict(by_type.most_common(20)),
        '墙体': {
            '图层': sorted(wall_layers),
            '图元合计': total_wall_ents
        },
        '房间': room_names,
        '家具标注': [t['text'] for t in furniture_texts],
        '门窗': {
            '门弧': len(door_arcs),
            '半径范围': [min(door_radii), max(door_radii)] if door_radii else [],
            '估算门宽': dict(Counter(door_widths).most_common(5)) if door_widths else {}
        },
        '填充': {'HATCH': len(hatches)},
        '尺寸': {'DIMENSION': len(dims)},
        '家具': {'图元合计': total_furn_ents, '图层': sorted(furn_layers)},
        '块引用': {'INSERT': len(inserts)}
    }
    with open(os.path.join(OUT_DIR, '综合图纸结构.json'), 'w', encoding='utf-8') as f:
        json.dump(struct, f, indent=2, ensure_ascii=False)
    
    # === SVG ===
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="700" viewBox="0 0 800 700">')
    svg.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    svg.append('<text x="400" y="25" text-anchor="middle" fill="#e0e0e0" font-size="14" font-family="monospace">课题010 — 晴碧园晶园26栋 综合图纸解析</text>')
    
    # 收集坐标
    all_pts = []
    for t in room_texts:
        all_pts.append((t['x'], t['y']))
    for d in door_arcs:
        all_pts.append((fval(d,10), fval(d,20)))
    
    if all_pts:
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        mnx, mxx = min(xs), max(xs)
        mny, mxy = min(ys), max(ys)
        wdt = max(mxx - mnx, 1)
        hgt = max(mxy - mny, 1)
        marg = max(wdt * 0.25, 2000)
        
        def tx(v): return 20 + (v - mnx + marg) / (wdt + 2*marg) * 760
        def ty(v): return 20 + (mxy + marg - v) / (hgt + 2*marg) * 560
        
        # 房间名
        colors = ['#4fc3f7','#ff7043','#81c784','#ffb74d','#ce93d8','#4dd0e1','#f06292','#a1887f']
        y_used = []
        for i, t in enumerate(room_texts):
            sx, sy = tx(t['x']), ty(t['y'])
            y_used.append(sy)
            c = colors[i % len(colors)]
            sz = 12 if t['height'] == 140 else 10
            svg.append('<text x="%.1f" y="%.1f" fill="%s" font-size="%d" font-family="monospace" text-anchor="middle">%s</text>' % (sx, sy, c, sz, t['text']))
        
        # 门弧
        for d in door_arcs:
            dx, dy = tx(fval(d,10)), ty(fval(d,20))
            r = fval(d,40)
            svg_r = max(r / (wdt + 2*marg) * 760, 2)
            svg.append('<path d="M %.1f %.1f A %.1f %.1f 0 0 1 %.1f %.1f" fill="none" stroke="#e57373" stroke-width="1.5"/>' % (
                dx, dy, svg_r, svg_r, 
                dx + svg_r, dy
            ))
        
        # 图例
        ly = 580
        svg.append('<text x="20" y="%d" fill="#4fc3f7" font-size="12" font-family="monospace">■ 房间名 (H=140)</text>' % ly)
        svg.append('<text x="20" y="%d" fill="#81c784" font-size="10" font-family="monospace">● 家具名 (H=100)</text>' % (ly+18))
        svg.append('<text x="20" y="%d" fill="#e57373" font-size="12" font-family="monospace">⌒ 门弧</text>' % (ly+36))
        svg.append('<text x="20" y="%d" fill="#888" font-size="10" font-family="monospace">晴碧园晶园26栋 | 4701 entities | 房间%s </text>' % (ly+54, ' / '.join(room_names[:6])))
    
    svg.append('</svg>')
    
    with open(os.path.join(OUT_DIR, '综合图纸可视化.svg'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))
    
    print('SVG: 综合图纸可视化.svg')
    print('JSON: 综合图纸结构.json')
    print('TXT: 综合图纸解析报告.txt')
    print('课题010 FINAL 完成')

if __name__ == '__main__':
    main()
