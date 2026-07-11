#!/usr/bin/env python3
"""
课题001 DXF修复 V3
直接用字节查找 ENTITIES 段，按 \n  0\n 分隔实体
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


def parse_ent_block(text):
    """返回 (etype, layer, {code: value})"""
    lines = text.strip('\n').split('\n')
    lines = [l.strip() for l in lines]
    
    etype = lines[1] if len(lines) > 1 else ''
    layer = '0'
    props = {}
    
    for i in range(len(lines)):
        try:
            code = int(lines[i])
            if i + 1 < len(lines):
                val = lines[i+1]
                props[code] = val
                if code == 8:
                    layer = val
        except ValueError:
            continue
    
    return etype, layer, props


def main():
    print("🏗  CAD Master 课题001 — DXF修复 V3\n")
    
    # 按行读取源文件
    with open(DXF_PATH, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    
    print(f"📖 源DXF: {len(data)/1024/1024:.1f} MB")
    
    # 找到 ENTITIES 段
    eidx = text.find('\n  0\nSECTION\n  2\nENTITIES\n')
    print(f"📍 ENTITIES 段偏移: ~{eidx}")
    
    # 从这个位置开始，按 \n  0\n 切分
    segment_text = text[eidx:]
    
    # 找 ENTITIES 段的结束
    eend = segment_text.find('\n  0\nENDSEC\n')
    if eend < 0:
        eend = len(segment_text)
    
    ent_text = segment_text[:eend]
    
    # 按 \n  0\n 切分成实体
    raw_blocks = ent_text.split('\n  0\n')
    print(f"📦 原始块数: {len(raw_blocks)}")
    
    ents = []  # [(raw_block_str, etype, layer, props)]
    for block in raw_blocks:
        b = block.strip('\n')
        if not b:
            continue
        lines = b.split('\n')
        lines = [l.strip() for l in lines]
        if len(lines) < 2:
            continue
        
        etype = lines[1]
        
        # 提取组码值对
        layer = '0'
        y_vals = []
        for i in range(len(lines)):
            try:
                code = int(lines[i])
                if i + 1 < len(lines):
                    val = lines[i+1]
                    if code == 8:
                        layer = val
                    if code in (20, 21):
                        try:
                            y_vals.append(float(val))
                        except:
                            pass
            except ValueError:
                continue
        
        # 检查是否在2F区域
        in_2f = any(F2F_Y_MIN <= y <= F2F_Y_MAX for y in y_vals)
        
        if in_2f and etype not in ('SEQEND', 'ENDBLK', 'ATTRIB'):
            ents.append((block, etype, layer))
    
    print(f"🔍 2F区域实体: {len(ents)}")
    
    # 统计
    layer_src = Counter(l for _, _, l in ents)
    etype_src = Counter(e for _, e, _ in ents)
    
    print(f"\n📊 源图层:")
    for l, c in layer_src.most_common(25):
        print(f"   {l:35s}: {c:4d}")
    
    print(f"\n📊 实体类型:")
    for e, c in etype_src.most_common(15):
        print(f"   {e:20s}: {c:4d}")
    
    # 验证1：找到一个 LINE 看坐标
    for blk, etype, layer in ents[:20]:
        if etype == 'LINE':
            lines = blk.strip('\n').split('\n')
            lines = [l.strip() for l in lines]
            # 找 10,20,11,21
            vals = {}
            for i in range(len(lines)):
                try:
                    code = int(lines[i])
                    if i + 1 < len(lines):
                        vals[code] = lines[i+1]
                except:
                    pass
            print(f"\n✅ 验证LINE: layer={layer}")
            print(f"   10={vals.get(10,'?')}, 20={vals.get(20,'?')}")
            print(f"   11={vals.get(11,'?')}, 21={vals.get(21,'?')}")
            break
    
    # 写 DXF
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TRAIN_DIR, exist_ok=True)
    
    def write_dxf(ents, path, remap=True):
        """写 DXF，保持原始块的格式"""
        used_layers = set()
        for blk, _, orig in ents:
            t = map_layer(orig) if remap else orig
            used_layers.add(t)
        if remap:
            for l in LAYER_COLORS:
                used_layers.add(l)
        
        out_lines = []
        out_lines.extend([
            '  0', 'SECTION', '  2', 'HEADER',
            '  9', '$ACADVER', '  1', 'AC1015',
            '  9', '$INSUNITS', ' 70', '4',
            '  0', 'ENDSEC',
            '  0', 'SECTION', '  2', 'TABLES',
            '  0', 'TABLE', '  2', 'LTYPE', ' 70', '2',
            '  0', 'LTYPE', '  2', 'Continuous', ' 70', '0',
            '  3', 'Solid line', ' 72', '65', ' 73', '0', ' 40', '0.0',
            '  0', 'LTYPE', '  2', 'ByLayer', ' 70', '0',
            '  3', '', ' 72', '65', ' 73', '0', ' 40', '0.0',
            '  0', 'ENDTAB',
            '  0', 'TABLE', '  2', 'LAYER', ' 70', str(len(used_layers)),
        ])
        for name in sorted(used_layers):
            color = LAYER_COLORS.get(name, 7)
            lw = LAYER_LW.get(name, 13)
            out_lines.extend([
                '  0', 'LAYER', '  2', name, ' 70', '0',
                ' 62', str(color), '  6', 'Continuous', '370', str(lw)
            ])
        out_lines.extend([
            '  0', 'ENDTAB',
            '  0', 'TABLE', '  2', 'STYLE', ' 70', '1',
            '  0', 'STYLE', '  2', 'Standard',
            ' 70', '0', ' 40', '0.0', ' 41', '1.0',
            ' 50', '0.0', ' 71', '0', ' 42', '2.5',
            '  3', 'txt', '  4', '',
            '  0', 'ENDTAB',
            '  0', 'ENDSEC',
            '  0', 'SECTION', '  2', 'BLOCKS', '  0', 'ENDSEC',
            '  0', 'SECTION', '  2', 'ENTITIES',
        ])
        
        for blk, etype, orig in ents:
            target = map_layer(orig) if remap else orig
            
            # 替换原始块中的 8 行（图层）和 62 行（颜色）
            lines = blk.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if stripped == '8' and i + 1 < len(lines):
                    new_lines.append(line)
                    new_lines.append(f'  {target}')
                    i += 2
                elif stripped == '62' and i + 1 < len(lines):
                    color = str(LAYER_COLORS.get(target, 7))
                    new_lines.append(line)
                    new_lines.append(f'  {color}')
                    i += 2
                else:
                    new_lines.append(line)
                    i += 1
            
            out_lines.extend(new_lines)
        
        out_lines.extend([
            '  0', 'ENDSEC',
            '  0', 'SECTION', '  2', 'OBJECTS', '  0', 'ENDSEC',
            '  0', 'EOF',
        ])
        
        output = '\n'.join(out_lines) + '\n'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        return os.path.getsize(path)
    
    raw_path = os.path.join(OUT_DIR, '二层层平面布置图_原始提取.dxf')
    redrawn_path = os.path.join(OUT_DIR, '二层层平面布置图_重绘.dxf')
    
    s1 = write_dxf(ents, raw_path, remap=False)
    s2 = write_dxf(ents, redrawn_path, remap=True)
    
    print(f"\n📄 原始提取: {raw_path} ({s1/1024:.1f} KB)")
    print(f"📄 重绘版:   {redrawn_path} ({s2/1024:.1f} KB)")
    
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
        nw = [w for w in v.warnings if not any(w[1].startswith(f'非标准图层: {n}') for n in ('10','6','20'))]
        for ww in nw[:5]:
            print(f"   ⚠️ {ww}")
    
    # 快速验证实体完整性
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    num_ents = len(re.findall(r'\n  0\n(?:LINE|LWPOLYLINE|CIRCLE|ARC|TEXT|MTEXT|DIMENSION|INSERT|HATCH|POINT)\n', raw))
    print(f"\n📊 实体完整性: {num_ents} 个标准实体")
    
    print(f"\n✅ DXF修复 V3 完成!")

if __name__ == '__main__':
    main()
