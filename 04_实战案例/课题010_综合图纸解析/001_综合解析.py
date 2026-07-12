#!/usr/bin/env python3
"""
课题010 — 综合图纸解析
从解析JSON加载全量数据，建立空间关系
"""
import json, os, math, sys
from collections import defaultdict

JSON_DIR  = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录'
OUT_DIR   = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题010_综合图纸解析'

def load_json(basename):
    fp = os.path.join(JSON_DIR, basename)
    with open(fp, 'r', encoding='utf-8') as f:
        return json.load(f)

def classify_entities(data):
    """按类型+图层初步分类所有图元"""
    classes = defaultdict(list)
    for ent in data.get('entities', []):
        etype = ent.get('type', '')
        layer = ent.get('layer', '0')
        classes[(etype, layer)].append(ent)
    return classes

def detect_walls(classes):
    """聚合墙体相关图元"""
    wall_types = [
        'LWPOLYLINE', 'LINE', 'POLYLINE', 'ARC'
    ]
    wall_layers = [
        'A-WALL', 'A-土建墙', 'A-新隔墙', 'A-NEWW',
        'A-土建墙（含管井、立管）', 'A-WALL-H'
    ]
    walls = []
    for etype in wall_types:
        for layer in wall_layers:
            walls.extend(classes.get((etype, layer), []))
    # 也包含所有 LWPOLYLINE（墙体通常用多段线）
    for (etype, layer), ents in classes.items():
        if etype == 'LWPOLYLINE':
            walls.extend(ents)
    return walls

def detect_doors(classes):
    """检测门（ARC 在 P-门 图层）"""
    doors = []
    for (etype, layer), ents in classes.items():
        if etype == 'ARC' and '门' in layer:
            doors.extend(ents)
    return doors

def detect_furniture(classes):
    """检测家具（INSERT + CIRCLE 在家具层）"""
    furn = []
    for (etype, layer), ents in classes.items():
        if '家具' in layer or 'FURN' in layer:
            furn.extend(ents)
    return furn

def detect_text(classes):
    """提取所有 MTEXT"""
    texts = []
    for (etype, layer), ents in classes.items():
        if etype == 'MTEXT':
            texts.append({
                'text': ents[0].get('text', '') if ents else '',
                'layer': layer,
                'entities': len(ents)
            })
    return texts

def generate_report(data):
    lines = []
    lines.append('=' * 65)
    lines.append('  课题010 — 综合图纸解析报告')
    lines.append('=' * 65)
    lines.append('')
    
    total = len(data.get('entities', []))
    lines.append('总图元数: %d' % total)
    lines.append('')
    
    # 按类型统计
    lines.append('【图元类型分布】')
    by_type = defaultdict(int)
    by_layer = defaultdict(int)
    for ent in data.get('entities', []):
        by_type[ent.get('type', '')] += 1
        by_layer[ent.get('layer', '0')] += 1
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append('  %-15s: %d' % (t, c))
    lines.append('')
    
    lines.append('【关键图层统计】')
    for l, c in sorted(by_layer.items(), key=lambda x: -x[1]):
        lines.append('  %-35s: %d' % (l, c))
    lines.append('')
    
    # 空间关系
    classes = classify_entities(data)
    walls = detect_walls(classes)
    doors = detect_doors(classes)
    furn = detect_furniture(classes)
    texts = detect_text(classes)
    
    lines.append('【空间关系提取】')
    lines.append('  墙体相关图元: %d' % len(walls))
    lines.append('  门弧: %d' % len(doors))
    lines.append('  家具/设备: %d' % len(furn))
    lines.append('  MTEXT文字: %d条' % len(texts))
    if texts:
        lines.append('  文字样例:')
        for t in texts[:8]:
            lines.append('    [%s] %s' % (t['layer'], t['text'][:40]))
    lines.append('')
    
    lines.append('=' * 65)
    lines.append('  报告结束')
    lines.append('=' * 65)
    return '\n'.join(lines)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # 加载 晴碧园 解析JSON
    data = load_json('晴碧园晶园26栋_解析.json')
    print('已加载: %d entities' % len(data.get('entities', [])))
    
    report = generate_report(data)
    print(report)
    
    # 保存报告
    rpath = os.path.join(OUT_DIR, '综合解析报告.txt')
    with open(rpath, 'w', encoding='utf-8') as f:
        f.write(report)
    print('报告: %s' % rpath)
    
    # 保存结构化数据
    classes = classify_entities(data)
    struct = {
        'total_entities': len(data.get('entities', [])),
        'by_type': dict(sorted(
            [(t, len(entities)) for (t, _), entities in classes.items()],
            key=lambda x: -x[1]
        )),
        'walls': len(detect_walls(classes)),
        'doors': len(detect_doors(classes)),
        'furniture': len(detect_furniture(classes)),
    }
    jpath = os.path.join(OUT_DIR, '综合结构数据.json')
    with open(jpath, 'w', encoding='utf-8') as f:
        json.dump(struct, f, indent=2, ensure_ascii=False)
    print('结构化数据: %s' % jpath)
    print('课题010 完成')

if __name__ == '__main__':
    main()
