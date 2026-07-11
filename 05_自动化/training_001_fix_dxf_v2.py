#!/usr/bin/env python3
"""
课题001 DXF修复 V2
核心修复：正确定义格式识别 LINE 端点坐标
"""
import re, os, sys
from collections import Counter

DXF_PATH = '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf'
OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题001_二层重绘'
TRAIN_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/课题001'

F2F_Y_MIN = -328538.0
F2F_Y_MAX = -311965.8

LAYER_MAP = {
    'A-土建墙（含管井、立管）': 'A-WALL',
    'A-新隔墙': 'A-WALL',
    'A-土建墙填充': 'A-WALL',
    'A-新隔墙填充': 'A-WALL',
    'A-土建拆除尺寸图': 'A-WALL',
    'A-新隔墙尺寸': 'A-WALL',
    'A-土建柱': 'A-COLUMN',
    'A-窗': 'A-WINDOW',
    'P-门': 'A-DOOR',
    'P-门套': 'A-DOOR',
    'P-楼梯（包括扶手）': 'A-STAIR',
    'A-轴线': 'A-AXIS',
    'W-尺寸': 'A-DIMS',
    'W-Word(文字及尺寸标注)': 'A-TEXT',
    'W-文字': 'A-TEXT',
    'C-顶部标高': 'A-SYMBOL',
    'W-基础引线': 'A-DIMS',
    'P-固定家具（落地、到顶）': 'A-FURN',
    'P-固定家具（悬空）': 'A-FURN',
    'P-固定家具（落地、不到顶）': 'A-FURN',
    'P-固定家具（不落地、到顶）': 'A-FURN',
    'P-活动家具': 'A-FURN',
    'P-家具尺寸': 'A-FURN',
    'P-完成面': 'A-FURN',
    'P-完成面（不到顶）': 'A-FURN',
    'P-洁具及配件（地坪图不显示）': 'A-FURN',
    'P-完成面尺寸': 'A-FURN',
    'F-地坪造型线': 'A-FURN',
    'F-地坪尺寸 @ 30': 'A-FURN',
    'C-顶面造型线': 'A-HATCH',
    'C-顶面造型尺寸': 'A-HATCH',
    'C-顶面灯具、灯带': 'A-HATCH',
    'C-顶面设备（风口、换气扇、投影仪）': 'A-HATCH',
    'C-顶面灯具及其他点位尺寸': 'A-HATCH',
    'C-顶面设备（喷淋、烟感、报警）': 'A-HATCH',
    'M-开关点位': 'A-HATCH',
    'M-插座连线': 'A-HATCH',
    'BJ-X25 插座': 'A-HATCH',
    'BJ-X22 天花尺寸': 'A-HATCH',
    'F-X19 开关': 'A-HATCH',
    'TEXT': 'A-TEXT',
    'T-text': 'A-TEXT',
    '活动家私': 'A-FURN',
    '0': '0',
    'Defpoints': 'Defpoints',
}

LAYER_COLORS = {
    'A-WALL': 7, 'A-COLUMN': 7, 'A-DOOR': 4, 'A-WINDOW': 5, 'A-STAIR': 6,
    'A-AXIS': 1, 'A-DIMS': 3, 'A-TEXT': 7, 'A-SYMBOL': 2, 'A-FURN': 6,
    'A-HATCH': 8, '0': 7, 'Defpoints': 250,
}

LAYER_LW = {
    'A-WALL': 30, 'A-COLUMN': 30, 'A-DOOR': 18, 'A-WINDOW': 13,
    'A-STAIR': 18, 'A-AXIS': 13, 'A-DIMS': 13, 'A-TEXT': 13,
    'A-SYMBOL': 13, 'A-FURN': 13, 'A-HATCH': 9, '0': 13, 'Defpoints': 13,
}


def map_layer(orig):
    if orig in LAYER_MAP:
        return LAYER_MAP[orig]
    for k, v in LAYER_MAP.items():
        if k and (k in orig or orig in k):
            return v
    if '墙' in orig or '柱' in orig: return 'A-WALL'
    if '门' in orig: return 'A-DOOR'
    if '窗' in orig: return 'A-WINDOW'
    if '楼梯' in orig: return 'A-STAIR'
    if '轴' in orig: return 'A-AXIS'
    if '尺寸' in orig or 'DIM' in orig: return 'A-DIMS'
    if '文字' in orig or 'TEXT' in orig or 'Word' in orig: return 'A-TEXT'
    if '标高' in orig: return 'A-SYMBOL'
    if '家具' in orig or '完成面' in orig or '地坪' in orig: return 'A-FURN'
    if '顶面' in orig or '开关' in orig or '插座' in orig or '灯具' in orig: return 'A-HATCH'
    return '0'


def parse_entities(text):
    """返回列表 [(行号, 实体类型, 原始块文本), ...] 从 ENTITIES 段"""
    eidx = text.find('  0\nSECTION\n  2\nENTITIES')
    eend = text.find('  0\nENDSEC\n', eidx)
    
    lines = text[eidx:eend].split('\n')
    
    entities = []  # (block_lines, etype, start_lineno_in_ent_section)
    current = None
    current_type = None
    current_start = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '0' and current is None:
            # 开始新实体
            if i + 1 < len(lines):
                current_type = lines[i+1].strip()
                current = [line]
                current_start = i
        elif stripped == '0' and current is not None:
            # 实体结束（碰到下一个0）
            entities.append((current, current_type, current_start))
            current = [line]
            current_type = lines[i+1].strip() if i+1 < len(lines) else 'EOF'
            current_start = i
        elif current is not None:
            current.append(line)
    
    if current and current_type:
        entities.append((current, current_type, current_start))
    
    return entities


def in_2f(block_lines):
    """检查实体是否在2F范围内"""
    for line in block_lines:
        stripped = line.strip()
        try:
            val = float(stripped)
        except:
            continue
        # 先看前一行是否是 20 或 21
        idx = block_lines.index(line)
        if idx > 0:
            prev = block_lines[idx-1].strip()
            if prev in ('20', '21') and abs(val) > 1000:
                if F2F_Y_MIN <= val <= F2F_Y_MAX:
                    return True
    return False


def get_layer(block_lines):
    """从块中提取图层名"""
    for i, line in enumerate(block_lines):
        if line.strip() == '8' and i + 1 < len(block_lines):
            return block_lines[i+1].strip()
    return '0'


def get_prop(block_lines, code):
    """获取组码对应的值"""
    for i, line in enumerate(block_lines):
        if line.strip() == str(code) and i + 1 < len(block_lines):
            return block_lines[i+1].strip()
    return None


def write_dxf(entities, path, remap=True):
    """按行号写 DXF"""
    used_layers = set()
    layer_target = {}
    for blk, etype, _ in entities:
        orig = get_layer(blk)
        t = map_layer(orig) if remap else orig
        layer_target[orig] = t
        used_layers.add(t)
    
    if remap:
        for l in LAYER_COLORS:
            used_layers.add(l)
    
    out_lines = []
    
    # HEADER
    out_lines.extend([
        '  0', 'SECTION', '  2', 'HEADER',
        '  9', '$ACADVER', '  1', 'AC1015',
        '  9', '$INSUNITS', ' 70', '4',
        '  0', 'ENDSEC'
    ])
    
    # TABLES - LTYPE
    out_lines.extend([
        '  0', 'SECTION', '  2', 'TABLES',
        '  0', 'TABLE', '  2', 'LTYPE', ' 70', '2',
        '  0', 'LTYPE', '  2', 'Continuous', ' 70', '0',
        '  3', 'Solid line', ' 72', '65', ' 73', '0', ' 40', '0.0',
        '  0', 'LTYPE', '  2', 'ByLayer', ' 70', '0',
        '  3', '', ' 72', '65', ' 73', '0', ' 40', '0.0',
        '  0', 'ENDTAB'
    ])
    
    # LAYER
    out_lines.extend(['  0', 'TABLE', '  2', 'LAYER', ' 70', str(len(used_layers))])
    for name in sorted(used_layers):
        color = LAYER_COLORS.get(name, 7)
        lw = LAYER_LW.get(name, 13)
        out_lines.extend([
            '  0', 'LAYER', '  2', name, ' 70', '0',
            ' 62', str(color), '  6', 'Continuous', '370', str(lw)
        ])
    out_lines.extend(['  0', 'ENDTAB'])
    
    # STYLE
    out_lines.extend([
        '  0', 'TABLE', '  2', 'STYLE', ' 70', '1',
        '  0', 'STYLE', '  2', 'Standard',
        ' 70', '0', ' 40', '0.0', ' 41', '1.0',
        ' 50', '0.0', ' 71', '0', ' 42', '2.5',
        '  3', 'txt', '  4', '',
        '  0', 'ENDTAB'
    ])
    out_lines.extend(['  0', 'ENDSEC'])
    
    # BLOCKS
    out_lines.extend(['  0', 'SECTION', '  2', 'BLOCKS', '  0', 'ENDSEC'])
    
    # ENTITIES
    out_lines.extend(['  0', 'SECTION', '  2', 'ENTITIES'])
    
    for blk, etype, _ in entities:
        orig = get_layer(blk)
        target = layer_target.get(orig, '0')
        
        for i, line in enumerate(blk):
            stripped = line.strip()
            if stripped == '8' and i + 1 < len(blk):
                out_lines.append(line)  # keep '  8'
                out_lines.append(f'  {target}')
            elif stripped == '62' and i + 1 < len(blk):
                color = str(LAYER_COLORS.get(target, 7))
                out_lines.append(line)
                out_lines.append(f'  {color}')
            else:
                out_lines.append(line)
    
    out_lines.extend(['  0', 'ENDSEC'])
    
    # OBJECTS
    out_lines.extend(['  0', 'SECTION', '  2', 'OBJECTS', '  0', 'ENDSEC'])
    
    # EOF
    out_lines.append('  0')
    out_lines.append('EOF')
    
    output = '\n'.join(out_lines) + '\n'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    return os.path.getsize(path)


def main():
    print("🏗  CAD Master 课题001 — DXF修复 V2\n")
    
    with open(DXF_PATH, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    
    print(f"📖 源DXF: {len(data)/1024/1024:.1f} MB")
    
    # 解析所有实体
    all_ents = parse_entities(text)
    print(f"📊 总实体数: {len(all_ents)}")
    
    # 过滤2F区域的实体
    f2f_ents = [(blk, etype, ln) for blk, etype, ln in all_ents 
                 if in_2f(blk) and etype not in ('SEQEND', 'ENDBLK')]
    print(f"🔍 2F区域实体: {len(f2f_ents)}")
    
    # 统计
    layer_src = Counter()
    etype_src = Counter()
    for blk, etype, _ in f2f_ents:
        layer_src[get_layer(blk)] += 1
        etype_src[etype] += 1
    
    print(f"\n📊 源图层:")
    for l, c in layer_src.most_common(20):
        print(f"   {l:35s}: {c:4d}")
    
    print(f"\n📊 实体类型:")
    for e, c in etype_src.most_common(15):
        print(f"   {e:20s}: {c:4d}")
    
    # 验证：取第一个LINE的坐标
    for blk, etype, _ in f2f_ents[:5]:
        if etype == 'LINE':
            x1, y1, x2, y2 = get_prop(blk, 10), get_prop(blk, 20), get_prop(blk, 11), get_prop(blk, 21)
            if x1 and y1 and x2 and y2:
                print(f"\n✅ 验证LINE: layer={get_layer(blk)}, ({x1},{y1})→({x2},{y2})")
                break
    
    # 导出
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TRAIN_DIR, exist_ok=True)
    
    raw_path = os.path.join(OUT_DIR, '二层层平面布置图_原始提取.dxf')
    redrawn_path = os.path.join(OUT_DIR, '二层层平面布置图_重绘.dxf')
    
    s1 = write_dxf(f2f_ents, raw_path, remap=False)
    s2 = write_dxf(f2f_ents, redrawn_path, remap=True)
    
    print(f"\n📄 原始提取: {raw_path} ({s1/1024:.1f} KB)")
    print(f"📄 重绘版:   {redrawn_path} ({s2/1024:.1f} KB)")
    
    # 同步到训练记录
    import shutil
    for src in [raw_path, redrawn_path]:
        shutil.copy2(src, TRAIN_DIR)
    
    # 验证
    sys.path.insert(0, '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化')
    from lb_dxf_engine import DXFValidator
    v = DXFValidator()
    for p in [raw_path, redrawn_path]:
        ok = v.validate(p)
        print(f"\n🔍 {os.path.basename(p)}: valid={ok}")
        for err in v.errors[:5]:
            print(f"   ❌ {err}")
        w = [w for w in v.warnings if not any(w[1].startswith(f'非标准图层: {n}') for n in ('10', '6', '20'))]
        for ww in w[:5]:
            print(f"   ⚠️ {ww}")
    
    print(f"\n✅ DXF修复完成!")

if __name__ == '__main__':
    main()
