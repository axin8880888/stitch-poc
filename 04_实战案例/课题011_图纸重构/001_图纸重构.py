#!/usr/bin/env python3
"""
课题011 — 图纸重构（从读懂到能画）
选取一个标准层，从零重构平面图

步骤：
1. 从解析JSON提取标准层的墙体骨架
2. 根据mtext定位房间名称
3. 按房间-墙体-门窗-标注顺序重建
4. 输出重构后的SVG + 过程记录
"""
import json, os
from collections import defaultdict

JSON_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录'
OUT_DIR  = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题011_图纸重构'

def load_json(bn):
    with open(os.path.join(JSON_DIR, bn), 'r', encoding='utf-8') as f:
        return json.load(f)

def fval(ent, code):
    v = ent.get('code_%d' % code)
    try: return float(v) if v is not None else 0.0
    except: return 0.0

def sv(ent, code):
    return ent.get('code_%d' % code, '')

def write_dxf_skeleton(wall_segments, door_arcs, text_labels, filepath):
    """生成一个基础 DXF 结构"""
    lines = []
    lines.append('0')
    lines.append('SECTION')
    lines.append('2')
    lines.append('ENTITIES')
    lines.append('0')
    
    # 墙体（LINE 简化）
    for seg in wall_segments[:100]:
        lines.append('LINE')
        lines.append('8')
        lines.append('A-WALL')
        lines.append('10')
        lines.append(str(seg[0]))
        lines.append('20')
        lines.append(str(seg[1]))
        lines.append('11')
        lines.append(str(seg[2]))
        lines.append('21')
        lines.append(str(seg[3]))
        lines.append('0')
    
    # 门弧
    for d in door_arcs[:10]:
        lines.append('ARC')
        lines.append('8')
        lines.append('A-DOOR')
        lines.append('10')
        lines.append(str(fval(d, 10)))
        lines.append('20')
        lines.append(str(fval(d, 20)))
        lines.append('40')
        lines.append(str(fval(d, 40)))
        lines.append('0')
    
    lines.append('ENDSEC')
    lines.append('0')
    lines.append('EOF')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = load_json('晴碧园晶园26栋_解析.json')
    ents = data.get('entities', [])
    
    # 分类
    by_type = defaultdict(list)
    for e in ents:
        by_type[e.get('type', '')].append(e)
    
    walls = by_type.get('LINE', []) + by_type.get('LWPOLYLINE', [])
    doors = [e for e in ents if e.get('type') == 'ARC' and '门' in e.get('layer','')]
    mtexts = by_type.get('MTEXT', [])
    hatches = by_type.get('HATCH', [])
    dims = by_type.get('DIMENSION', [])
    inserts = by_type.get('INSERT', [])
    
    # 墙面LINE段提取（每个LINE的两个端点）
    wall_segments = []
    for w_line in walls[:200]:
        if w_line.get('type') == 'LINE':
            x1, y1 = fval(w_line, 10), fval(w_line, 20)
            x2, y2 = fval(w_line, 11), fval(w_line, 21)
            if x1 != x2 or y1 != y2:
                wall_segments.append((x1, y1, x2, y2))
        elif w_line.get('type') == 'LWPOLYLINE':
            pass  # 复杂多边形，暂略
    
    # 房间名文本
    room_labels = []
    furn_labels = []
    for m in mtexts:
        txt = sv(m, 1)
        if not txt: continue
        h = fval(m, 40)
        label = {'text': txt.strip(), 'x': fval(m,10), 'y': fval(m,20), 'h': h}
        if h == 140:
            room_labels.append(label)
        else:
            furn_labels.append(label)
    
    # 报告
    report = []
    sep = '=' * 65
    report.append(sep)
    report.append('  课题011 — 图纸重构 V1')
    report.append('  重构基础数据提取')
    report.append(sep)
    report.append('')
    report.append('从晴碧园全图纸提取重构所需数据：')
    report.append('')
    report.append('  LINE墙体段: %d条' % len(wall_segments))
    report.append('  LWPOLYLINE: %d条（墙体轮廓）' % len(walls) - len(wall_segments))
    report.append('  门弧: %d个' % len(doors))
    report.append('  房间标注: %d个' % len(room_labels))
    report.append('  家具标注: %d个' % len(furn_labels))
    report.append('  HATCH: %d个（填充区域）' % len(hatches))
    report.append('  DIMENSION: %d个（尺寸控制）' % len(dims))
    report.append('  INSERT: %d个（图块引用）' % len(inserts))
    report.append('')
    report.append('【房间列表】')
    for r in sorted(room_labels, key=lambda x: x['text']):
        report.append('  %-15s (%.0f, %.0f)' % (r['text'], r['x'], r['y']))
    report.append('')
    report.append('【重构思路】')
    report.append('  1. 从LINE段提取墙体中线/边线')
    report.append('  2. 用墙体交点确定房间边界')
    report.append('  3. 在房间内布置标注文字')
    report.append('  4. 标注门弧位置')
    report.append('  5. 校核尺寸标注与墙体距离')
    report.append('')
    report.append('【下一步】')
    report.append('  选取一个标准层（如二层：含卧室、主卧、衣帽间、卫生间）')
    report.append('  从零绘制墙体，逐步完善')
    report.append(sep)
    
    report_text = '\n'.join(report)
    print(report_text)
    
    with open(os.path.join(OUT_DIR, '重构基础数据报告.txt'), 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    # 输出简化的DXF骨架
    dxf_path = os.path.join(OUT_DIR, '重构骨架.dxf')
    write_dxf_skeleton(wall_segments, doors, room_labels, dxf_path)
    print('DXF骨架: %s' % dxf_path)
    print('课题011 V1 完成')

if __name__ == '__main__':
    main()
