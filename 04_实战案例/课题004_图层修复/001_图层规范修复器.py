#!/usr/bin/env python3
"""
课题004 — 图层规范修复器
修正 DXF 文件：图层迁移 + 颜色移除 + 图层表修正
"""

import os, sys
from collections import Counter


LAYER_MAP = {
    'W-尺寸':    'A-DIM',
    'W-文字':    'A-TEXT',
    'A-土建墙（含管井、立管）': 'A-WALL',
    'A-土建墙填充': 'A-HATCH',
    'A-新隔墙':   'A-NEWW',
    'A-新隔墙填充': 'A-HATCH',
    'A-轴线':    'A-AXIS',
    'P-活动家具':  'A-FURN',
    'P-门':      'A-DOOR',
    'P-门套':    'A-DOOR',
    'P-固定家具（落地、到顶）': 'A-FURN',
    'P-固定家具（悬空）': 'A-FURN',
    'P-固定家具（不落地、到顶）': 'A-FURN',
    'P-完成面':   'A-FURN-H',
    'P-完成面（不到顶）': 'A-FURN-H',
    'P-楼梯（包括扶手）': 'A-STAIR',
    'P-洁具及配件（地坪图不显示）': 'P-PLUMB',
    'BJ-X15 活动家具': 'A-FURN',
    '活动家私':  'A-FURN',
}

LAYER_STANDARD = {
    'A-WALL':   {'color': 7,  'lw': 30, 'lt': 'Continuous'},
    'A-WALL-H': {'color': 8,  'lw': 9,  'lt': 'Continuous'},
    'A-NEWW':   {'color': 4,  'lw': 18, 'lt': 'Continuous'},
    'A-DOOR':   {'color': 4,  'lw': 18, 'lt': 'Continuous'},
    'A-WINDW':  {'color': 5,  'lw': 13, 'lt': 'Continuous'},
    'A-FURN':   {'color': 6,  'lw': 13, 'lt': 'Continuous'},
    'A-FURN-H': {'color': 8,  'lw': 9,  'lt': 'Continuous'},
    'A-DIM':    {'color': 3,  'lw': 13, 'lt': 'Continuous'},
    'A-TEXT':   {'color': 7,  'lw': 13, 'lt': 'Continuous'},
    'A-AXIS':   {'color': 1,  'lw': 13, 'lt': 'CENTER'},
    'A-STAIR':  {'color': 6,  'lw': 13, 'lt': 'Continuous'},
    'A-HATCH':  {'color': 8,  'lw': 9,  'lt': 'Continuous'},
    'A-NOTE':   {'color': 7,  'lw': 13, 'lt': 'Continuous'},
    'P-PLUMB':  {'color': 5,  'lw': 13, 'lt': 'Continuous'},
}


def fix_dxf(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    lines = content.split('\n')
    log = []
    stats = Counter()
    N = len(lines)

    # ---- 0. 找到 ENTITIES 段范围 ----
    entities_start = -1
    entities_end = -1
    i = 0
    while i < N:
        s = lines[i].strip()
        if s == '2' and i+1 < N and lines[i+1].strip() == 'ENTITIES':
            # 向后找到第一个 0（该段实体起始标记）
            for j in range(i+2, min(i+10, N)):
                if lines[j].strip() == '0':
                    entities_start = j
                    break
            i += 1
            continue
        if s == 'ENDSEC' and entities_start >= 0 and entities_end < 0:
            entities_end = i
            break
        i += 1

    if entities_start < 0:
        print("  [错误] 未找到 ENTITIES 段")
        return None

    # ---- 1. ENTITIES 段：图层迁移 + 颜色移除 ----
    ent_type = None
    color_marks = []  # 要删除的 (行号1, 行号2)

    i = entities_start
    while i <= entities_end:
        s = lines[i].strip()

        # 新实体开始
        if s == '0':
            if i+1 <= entities_end:
                ent_type = lines[i+1].strip()
            i += 1
            continue

        # 图层代码 8 → 检查是否需要迁移
        if s == '8' and ent_type:
            if i+1 < N:
                cur_layer = lines[i+1].strip()
                if cur_layer in LAYER_MAP:
                    target = LAYER_MAP[cur_layer]
                    # 保留缩进
                    indent = lines[i+1][:len(lines[i+1])-len(cur_layer)]
                    lines[i+1] = indent + target
                    log.append("LAYER_MIGRATE  %s: %s -> %s" % (ent_type, cur_layer, target))
                    stats['layer_migrate'] += 1
            i += 2
            continue

        # 颜色 62 → 标记删除（除非在保留图层）
        if s == '62' and ent_type:
            # 往前找当前实体的图层
            layer = '?'
            for j in range(i-1, max(entities_start, i-30), -1):
                if lines[j].strip() == '8' and j+1 < N:
                    layer = lines[j+1].strip()
                    break
            if layer not in ('0', 'Defpoints'):
                if i+1 < N:
                    old_val = lines[i+1].strip()
                    color_marks.append((i, i+1))
                    log.append("COLOR_REMOVE  %s (layer=%s): %s -> ByLayer" % (ent_type, layer, old_val))
                    stats['color_remove'] += 1
            i += 2
            continue

        i += 1

    # 从后往前删除颜色行
    for ci, vi in sorted(color_marks, reverse=True):
        lines[ci] = None
        lines[vi] = None
    lines = [l for l in lines if l is not None]
    N = len(lines)

    # ---- 2. 图层表：修正颜色/线宽/线型 ----
    in_layer_table = False
    in_layer = False
    cur_layername = None

    i = 0
    while i < N:
        s = lines[i].strip()

        # 检测 LAYER 表
        if s == 'TABLE':
            for j in range(i+1, min(i+10, N)):
                if lines[j].strip() == '2' and j+1 < N and lines[j+1].strip() == 'LAYER':
                    in_layer_table = True
                    break

        if in_layer_table and s == 'ENDTAB':
            in_layer_table = False
            in_layer = False
            i += 1
            continue

        if in_layer_table and s == '0' and i+1 < N and lines[i+1].strip() == 'LAYER':
            in_layer = True
            cur_layername = None
            i += 2
            continue

        if in_layer and s == '0':
            in_layer = False
            i += 1
            continue

        if in_layer and cur_layername is None and s == '2':
            if i+1 < N:
                cur_layername = lines[i+1].strip()
            i += 2
            continue

        if in_layer and cur_layername and cur_layername in LAYER_STANDARD:
            std = LAYER_STANDARD[cur_layername]
            if s == '62':
                i += 1
                if i < N:
                    try:
                        cur = int(lines[i].strip())
                        if cur != std['color']:
                            indent = lines[i][:len(lines[i])-len(lines[i].strip())]
                            lines[i] = indent + str(std['color'])
                            log.append("TABLE_COLOR   %s: %d -> %d" % (cur_layername, cur, std['color']))
                            stats['table_color'] += 1
                    except ValueError:
                        pass
                i += 1
                continue
            if s == '370':
                i += 1
                if i < N:
                    try:
                        cur = int(lines[i].strip())
                        if cur != std['lw']:
                            indent = lines[i][:len(lines[i])-len(lines[i].strip())]
                            lines[i] = indent + str(std['lw'])
                            log.append("TABLE_LW      %s: %d -> %d" % (cur_layername, cur, std['lw']))
                            stats['table_lw'] += 1
                    except ValueError:
                        pass
                i += 1
                continue
            if s == '6':
                i += 1
                if i < N:
                    cur_lt = lines[i].strip()
                    if cur_lt != std['lt']:
                        indent = lines[i][:len(lines[i])-len(cur_lt)]
                        lines[i] = indent + std['lt']
                        log.append("TABLE_LT      %s: %s -> %s" % (cur_layername, cur_lt, std['lt']))
                        stats['table_lt'] += 1
                i += 1
                continue

        i += 1

    # ---- 3. 添加缺失标准图层 ----
    existing = set()
    in_table = False
    for i in range(N):
        s = lines[i].strip()
        if s == 'TABLE':
            for j in range(i+1, min(i+10, N)):
                if lines[j].strip() == '2' and j+1 < N and lines[j+1].strip() == 'LAYER':
                    in_table = True
                    break
        if in_table and s == 'ENDTAB':
            in_table = False
        if in_table and s == '2' and i > 0 and lines[i-1].strip() == '0':
            if i+1 < N:
                name = lines[i+1].strip()
                if name not in ('TABLES', 'LAYER', 'LTYPE', 'STYLE', 'VPORT'):
                    existing.add(name)

    for orig, target in LAYER_MAP.items():
        existing.add(target)
    existing.add('Defpoints')

    needed = set(LAYER_STANDARD.keys()) - existing
    if needed:
        for i in range(N):
            if lines[i].strip() == 'ENDTAB':
                blocks = []
                for name in sorted(needed):
                    std = LAYER_STANDARD[name]
                    blocks.append('\n'.join([
                        '0', 'LAYER', '2', name,
                        '70', '0', '62', str(std['color']),
                        '6', std['lt'], '370', str(std['lw']),
                    ]))
                lines.insert(i, '\n'.join(blocks))
                for name in sorted(needed):
                    log.append("LAYER_ADD     %s" % name)
                    stats['layer_add'] += 1
                break

    # 写回
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return log, stats, output_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_path', nargs='?',
        default='/storage/emulated/0/设计/DXF学习/晴碧园晶园26栋.dxf')
    parser.add_argument('--output-dir', '-o',
        default='/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题004_图层修复')

    args = parser.parse_args()

    if not os.path.isfile(args.input_path):
        print("文件不存在: %s" % args.input_path)
        return

    os.makedirs(args.output_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(args.input_path))[0]
    output_path = os.path.join(args.output_dir, basename + '_规范修复.dxf')

    print("课题004 图层规范修复")
    print("  输入: %s" % os.path.basename(args.input_path))
    print("  输出: %s" % os.path.basename(output_path))
    print()

    result = fix_dxf(args.input_path, output_path)
    if result is None:
        return

    log, stats, out_path = result

    # 报告
    print("=" * 55)
    print("  修复统计:")
    for key, label in [('layer_migrate', '图层迁移'),
                       ('color_remove', '颜色移除(恢复ByLayer)'),
                       ('table_color', '表颜色修正'),
                       ('table_lw', '表线宽修正'),
                       ('table_lt', '表线型修正'),
                       ('layer_add', '图层添加')]:
        v = stats.get(key, 0)
        if v:
            print("    %-22s: %d" % (label, v))
    print()
    print("  修复明细:")
    print("  " + "-"*50)
    for entry in log:
        print("    %s" % entry)

    # 验证
    print()
    with open(output_path, 'r', encoding='utf-8', errors='replace') as f:
        fixed_content = f.read()
    parts = fixed_content.split('ENTITIES')
    remaining = []
    if len(parts) >= 2:
        ep = parts[1].split('ENDSEC')[0]
        for orig in sorted(LAYER_MAP, key=len, reverse=True):
            cnt = ep.count('\n' + orig + '\n') + ep.count('\n' + orig)
            if cnt > 0:
                remaining.append((orig, cnt))

    if remaining:
        print("  [注意] 仍有原始图层被引用:")
        for name, cnt in remaining:
            print("    %s: %d处" % (name, cnt))
    else:
        print("  验证: 所有非标准实体图层已迁移完成")

    orig_sz = os.path.getsize(args.input_path)
    fix_sz = os.path.getsize(out_path)
    print("  大小: %.1fKB -> %.1fKB (%.1f%%)" % (
        orig_sz/1024, fix_sz/1024, fix_sz/orig_sz*100))

    print()
    print("课题004 完成!")


if __name__ == '__main__':
    main()
