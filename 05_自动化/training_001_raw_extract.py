#!/usr/bin/env python3
"""
课题001 DXF 最终修复版
从原始 DXF 直接提取并保持原始文本格式
"""
import re, os, sys, shutil
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


def main():
    print("🏗  CAD Master 课题001 — 原始文本提取 V4\n")
    
    with open(DXF_PATH, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    
    print(f"📖 源DXF: {len(data)/1024/1024:.1f} MB, {len(text)/1024:.0f} K 字符")
    
    # 1. 找到 ENTITIES 段在全文中的起止位置
    e_marker = 'SECTION\n  2\nENTITIES'
    eidx = text.find(e_marker)
    if eidx < 0:
        print("❌ 找不到 ENTITIES 段!")
        return
    
    # 从头开始找，跳过 HEADER/TABLES
    # 找 ENTITIES 开头的 0\nSECTION\n2\nENTITIES
    eidx = text.find('\n  0\nSECTION\n  2\nENTITIES\n')
    eend = text.find('\n  0\nENDSEC\n', eidx)
    if eend < 0:
        eend = len(text)
    
    ent_text = text[eidx:eend]
    print(f"📍 ENTITIES 段: {eidx} ~ {eend} ({len(ent_text)} 字节)")
    
    # 2. 按 \n  0\n 切分实体（标准DXF格式）
    raw_blocks = ent_text.split('\n  0\n')
    print(f"📦 原始块数: {len(raw_blocks)}")
    
    # 3. 过滤2F区域
    extracted = []  # [(完整块字符串, etype, orig_layer)]
    
    for block in raw_blocks:
        if not block.strip():
            continue
        
        # 取实体类型 - split('\n  0\n') 后第一行就是实体类型名
        lines = block.split('\n')
        etype = lines[0].strip() if lines else ''
        
        # 读取原始行列表
        all_lines = block.split('\n')
        
        # 找图层 (组码8)
        orig_layer = '0'
        for i in range(len(all_lines)):
            if all_lines[i].strip() == '8' and i + 1 < len(all_lines):
                orig_layer = all_lines[i+1].strip()
                break
        
        # 找Y坐标 (组码20, 21) 判断是否在2F区域
        in_2f = False
        for i in range(len(all_lines)):
            stripped = all_lines[i].strip()
            if stripped in ('20', '21') and i + 1 < len(all_lines):
                try:
                    y_val = float(all_lines[i+1].strip())
                    if abs(y_val) > 1000:  # 模型空间
                        if F2F_Y_MIN <= y_val <= F2F_Y_MAX:
                            in_2f = True
                            break
                except:
                    pass
        
        if in_2f and etype not in ('SEQEND', 'ENDBLK'):
            extracted.append((block, etype, orig_layer))
    
    print(f"🔍 2F区域实体: {len(extracted)}")
    
    # 4. 统计
    layer_src = Counter()
    etype_src = Counter()
    for blk, etype, layer in extracted:
        layer_src[layer] += 1
        etype_src[etype] += 1
    
    print(f"\n📊 源图层:")
    for l, c in layer_src.most_common(25):
        print(f"   {l:35s}: {c:4d}")
    
    print(f"\n📊 实体类型:")
    for e, c in etype_src.most_common(15):
        print(f"   {e:15s}: {c:4d}")
    
    # 验证第一个 LINE 的坐标
    for blk, etype, layer in extracted[:20]:
        if etype == 'LINE':
            lines = blk.split('\n')
            x1, y1, x2, y2 = None, None, None, None
            for i in range(len(lines)):
                s = lines[i].strip()
                if s == '10' and i+1 < len(lines): x1 = lines[i+1].strip()
                if s == '20' and i+1 < len(lines): y1 = lines[i+1].strip()
                if s == '11' and i+1 < len(lines): x2 = lines[i+1].strip()
                if s == '21' and i+1 < len(lines): y2 = lines[i+1].strip()
            print(f"\n✅ 验证 LINE: layer={layer}, 端点({x1},{y1})→({x2},{y2})")
            break
    
    # 5. 写 DXF 纯文本方式
    def write_dxf(ents, path, remap=True):
        used_layers = set()
        for _, _, orig in ents:
            t = map_layer(orig) if remap else orig
            used_layers.add(t)
        if remap:
            for l in LAYER_COLORS:
                used_layers.add(l)
        
        out = []
        
        # HEADER
        out.extend([
            '  0', 'SECTION', '  2', 'HEADER',
            '  9', '$ACADVER', '  1', 'AC1015',
            '  9', '$INSUNITS', ' 70', '4',
            '  0', 'ENDSEC',
        ])
        
        # TABLES
        out.extend(['  0', 'SECTION', '  2', 'TABLES'])
        out.extend([
            '  0', 'TABLE', '  2', 'LTYPE', ' 70', '2',
            '  0', 'LTYPE', '  2', 'Continuous', ' 70', '0',
            '  3', 'Solid line', ' 72', '65', ' 73', '0', ' 40', '0.0',
            '  0', 'LTYPE', '  2', 'ByLayer', ' 70', '0',
            '  3', '', ' 72', '65', ' 73', '0', ' 40', '0.0',
            '  0', 'ENDTAB',
        ])
        out.extend(['  0', 'TABLE', '  2', 'LAYER', ' 70', str(len(used_layers))])
        for name in sorted(used_layers):
            color = LAYER_COLORS.get(name, 7)
            lw = LAYER_LW.get(name, 13)
            out.extend([
                '  0', 'LAYER', '  2', name, ' 70', '0',
                ' 62', str(color), '  6', 'Continuous', '370', str(lw),
            ])
        out.extend(['  0', 'ENDTAB'])
        out.extend([
            '  0', 'TABLE', '  2', 'STYLE', ' 70', '1',
            '  0', 'STYLE', '  2', 'Standard',
            ' 70', '0', ' 40', '0.0', ' 41', '1.0',
            ' 50', '0.0', ' 71', '0', ' 42', '2.5',
            '  3', 'txt', '  4', '',
            '  0', 'ENDTAB',
        ])
        out.extend(['  0', 'ENDSEC'])
        
        # BLOCKS
        out.extend(['  0', 'SECTION', '  2', 'BLOCKS', '  0', 'ENDSEC'])
        
        # ENTITIES
        out.extend(['  0', 'SECTION', '  2', 'ENTITIES'])
        
        for blk, etype, orig in ents:
            target = map_layer(orig) if remap else orig
            
            # 每个实体前加 '  0' 做分隔
            out.append('  0')
            
            lines = blk.split('\n')
            i = 0
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped == '8' and i + 1 < len(lines):
                    out.append(lines[i])  # keep '  8' spacing
                    out.append(f'  {target}')
                    i += 2
                elif stripped == '62' and i + 1 < len(lines):
                    color = str(LAYER_COLORS.get(target, 7))
                    out.append(lines[i])
                    out.append(f'  {color}')
                    i += 2
                else:
                    out.append(lines[i])
                    i += 1
        
        out.extend([
            '  0', 'ENDSEC',
            '  0', 'SECTION', '  2', 'OBJECTS', '  0', 'ENDSEC',
            '  0', 'EOF',
        ])
        
        # write
        output = '\n'.join(out) + '\n'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        return os.path.getsize(path)
    
    # 6. 导出
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TRAIN_DIR, exist_ok=True)
    
    raw_path = os.path.join(OUT_DIR, '二层层平面布置图_原始提取.dxf')
    redrawn_path = os.path.join(OUT_DIR, '二层层平面布置图_重绘.dxf')
    
    s1 = write_dxf(extracted, raw_path, remap=False)
    s2 = write_dxf(extracted, redrawn_path, remap=True)
    
    print(f"\n📄 原始提取: {raw_path}")
    print(f"   大小: {s1/1024:.1f} KB")
    print(f"📄 重绘版:   {redrawn_path}")
    print(f"   大小: {s2/1024:.1f} KB")
    
    # 同步到训练记录
    shutil.copy2(raw_path, TRAIN_DIR)
    shutil.copy2(redrawn_path, TRAIN_DIR)
    
    # 7. 快速验证：检查输出的实体数量
    def count_ents(path):
        with open(path, 'r', encoding='utf-8') as f:
            txt = f.read()
        return len([m for m in re.finditer(r'\n  0\n(?!SECTION)(?!ENDSEC)(?!TABLE)(?!EOF)', txt)])
    
    c1 = count_ents(raw_path)
    c2 = count_ents(redrawn_path)
    print(f"\n🔍 实体计数: 原始={c1}, 重绘={c2}")
    
    # 检查 DXF 段平衡
    def check_dxf(path):
        with open(path, 'r', encoding='utf-8') as f:
            txt = f.read()
        sections = len(re.findall(r'\n  0\nSECTION\n', txt))
        ends = len(re.findall(r'\n  0\nENDSEC\n', txt))
        has_eof = txt.rstrip().endswith('EOF')
        has_ent = 'ENTITIES' in txt
        return sections, ends, has_eof, has_ent
    
    for p in [raw_path, redrawn_path]:
        s, end, eof, ent = check_dxf(p)
        print(f"   {os.path.basename(p)}: SECTION={s}, ENDSEC={end}, EOF={eof}, ENTITIES={ent}")
        if s == end and eof and ent:
            print(f"   ✅ 结构正确")
        else:
            print(f"   ❌ 结构异常")
    
    print(f"\n✅ 完成!")

if __name__ == '__main__':
    main()
