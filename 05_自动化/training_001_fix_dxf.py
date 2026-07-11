#!/usr/bin/env python3
"""
课题001 DXF修复脚本
问题：LINE实体坐标全为0（props提取失败，未正确读取组码值）
修复策略：直接从源DXF提取实体原始块，只替换图层名
"""
import re, os, sys
from collections import Counter

DXF_PATH = '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf'
OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题001_二层重绘'
TRAIN_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/课题001'

sys.path.insert(0, '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化')

# 二层平面图边界（从之前分析确认）
F2F_Y_MIN = -328538.0
F2F_Y_MAX = -311965.8
F2F_X_MIN = 102962.3
F2F_X_MAX = 249744.8

# 图层映射
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


def has_2f_coord(block):
    """检查实体是否在2F Y范围内（只检查 20/21 组码）"""
    # 提取所有 20/21 组码的值
    coords = re.findall(r'\n(?:20|21)\n(-?\d+\.?\d*)', block)
    if not coords:
        # 有些实体可能用 20 但在不同位置
        coords = re.findall(r'\n(?:20|21)\n(-?\d+)', block)
    for c in coords:
        try:
            y = float(c)
            if abs(y) > 1000:  # 模型空间坐标
                if F2F_Y_MIN <= y <= F2F_Y_MAX:
                    return True
        except:
            pass
    return False


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
    print("🏗  CAD Master 课题001 — DXF修复\n")
    
    # 1. 加载源DXF的ENTITIES段
    with open(DXF_PATH, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8', errors='replace')
    
    eidx = text.find('\n  0\nSECTION\n  2\nENTITIES\n')
    eend = text.find('\n  0\nENDSEC\n', eidx)
    ent_text = text[eidx:eend]
    
    print(f"📖 读取源DXF: {len(data)/1024/1024:.1f} MB")
    print(f"📦 ENTITIES段: {len(ent_text)} 字节")
    
    # 2. 逐实体解析并过滤
    entities_raw = []  # [(orig_block, etype, orig_layer)]
    pos = 0
    
    while True:
        m = re.search(r'\n  0\n([^\n]+)\n', ent_text[pos:])
        if not m:
            break
        start = pos + m.start()
        etype = m.group(1).strip()
        
        end_pos = ent_text.find('\n  0\n', start + len(m.group(0)))
        if end_pos < 0:
            end_pos = len(ent_text)
        
        block = ent_text[start:end_pos]
        
        if etype in ('SEQEND', 'ENDBLK'):
            pos = start + len(m.group(0))
            continue
        
        lm = re.search(r'\n  8\n([^\n]+)', block)
        layer = lm.group(1).strip() if lm else '0'
        
        if has_2f_coord(block):
            entities_raw.append((block, etype, layer))
        
        pos = start + len(m.group(0))
    
    print(f"🔍 约束范围 Y: {F2F_Y_MIN:.0f} ~ {F2F_Y_MAX:.0f}")
    print(f"📊 提取到 {len(entities_raw)} 个2F实体")
    
    # 3. 统计
    layer_src = Counter(l for _, _, l in entities_raw)
    etype_src = Counter(e for _, e, _ in entities_raw)
    
    print(f"\n📊 源图层分布:")
    for l, c in layer_src.most_common(20):
        print(f"   {l:35s}: {c:4d}")
    
    # 4. 输出DXF的方法：保留原始块的文本，只修改 8 和 62 行
    def write_dxf(ents, path, title, remap=True):
        used_layers = set()
        layer_target = {}
        for _, _, orig in ents:
            t = map_layer(orig) if remap else orig
            layer_target[orig] = t
            used_layers.add(t)
        
        if remap:
            for l in LAYER_COLORS:
                used_layers.add(l)
        
        lines = []
        # HEADER
        lines.extend(["  0", "SECTION", "  2", "HEADER",
                       "  9", "$ACADVER", "  1", "AC1015",
                       "  9", "$INSUNITS", " 70", "4",
                       "  0", "ENDSEC"])
        
        # TABLES - LTYPE
        lines.extend(["  0", "SECTION", "  2", "TABLES",
                       "  0", "TABLE", "  2", "LTYPE", " 70", "2",
                       "  0", "LTYPE", "  2", "Continuous", " 70", "0",
                       "  3", "Solid line", " 72", "65", " 73", "0", " 40", "0.0",
                       "  0", "LTYPE", "  2", "ByLayer", " 70", "0",
                       "  3", "", " 72", "65", " 73", "0", " 40", "0.0",
                       "  0", "ENDTAB"])
        
        # TABLES - LAYER
        lines.extend(["  0", "TABLE", "  2", "LAYER", " 70", str(len(used_layers))])
        for name in sorted(used_layers):
            color = LAYER_COLORS.get(name, 7)
            lw = LAYER_LW.get(name, 13)
            lines.extend(["  0", "LAYER", "  2", name, " 70", "0",
                          " 62", str(color), "  6", "Continuous", "370", str(lw)])
        lines.extend(["  0", "ENDTAB"])
        
        # STYLE
        lines.extend(["  0", "TABLE", "  2", "STYLE", " 70", "1",
                       "  0", "STYLE", "  2", "Standard",
                       " 70", "0", " 40", "0.0", " 41", "1.0",
                       " 50", "0.0", " 71", "0", " 42", "2.5",
                       "  3", "txt", "  4", "",
                       "  0", "ENDTAB"])
        lines.extend(["  0", "ENDSEC"])
        
        # BLOCKS
        lines.extend(["  0", "SECTION", "  2", "BLOCKS", "  0", "ENDSEC"])
        
        # ENTITIES
        lines.extend(["  0", "SECTION", "  2", "ENTITIES"])
        
        for raw_block, etype, orig_layer in ents:
            target = layer_target.get(orig_layer, '0')
            color = str(LAYER_COLORS.get(target, 7))
            
            # 从原始块复制所有行，但替换 8 和 62 组码
            # 原始格式： "  0\nLINE\n  8\nA-土建墙\n 62\n7\n..."
            # 我们需要保持原格式不变，只替换 8/ 的值和 62/ 的值
            block = raw_block
            
            # 替换 8\n[层名]
            block = re.sub(r'\n  8\n[^\n]+', f'\n  8\n{target}', block, count=1)
            
            # 替换 62\n[颜色]（如果存在）
            if re.search(r'\n 62\n', block):
                block = re.sub(r'\n 62\n[^\n]+', f'\n 62\n{color}', block, count=1)
            else:
                # 没有颜色组码，插入
                lm_pos = block.find(f'\n  8\n{target}')
                if lm_pos > 0:
                    # 在 8 行后插入 62
                    after_8 = block.find('\n', lm_pos + len(f'\n  8\n{target}'))
                    if after_8 > 0:
                        block = block[:after_8+1] + f' 62\n{color}' + block[after_8+1:]
            
            lines.append(block)
        
        lines.extend(["  0", "ENDSEC"])
        
        # OBJECTS
        lines.extend(["  0", "SECTION", "  2", "OBJECTS", "  0", "ENDSEC"])
        
        # EOF
        lines.append("  0")
        lines.append("EOF")
        
        output = '\n'.join(lines) + '\n'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        size = os.path.getsize(path)
        print(f"✅ {title} → {path}")
        print(f"   大小: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"   层数: {len(used_layers)}, 实体: {len(ents)}")
        
        # 验证完整的实体
        with open(path, 'r', encoding='utf-8') as f:
            out_text = f.read()
        verif = len(re.findall(r'\n  0\n', out_text))
        print(f"   组码行数: {verif}")
        
        return path
    
    # 5. 导出
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TRAIN_DIR, exist_ok=True)
    
    raw_path = os.path.join(OUT_DIR, '二层层平面布置图_原始提取.dxf')
    redrawn_path = os.path.join(OUT_DIR, '二层层平面布置图_重绘.dxf')
    
    write_dxf(entities_raw, raw_path, "原始提取版", remap=False)
    write_dxf(entities_raw, redrawn_path, "重绘版", remap=True)
    
    # 也更新训练记录
    import shutil
    for src in [raw_path, redrawn_path]:
        dst = os.path.join(TRAIN_DIR, os.path.basename(src))
        shutil.copy2(src, dst)
        print(f"   同步到训练记录: {dst}")
    
    # 6. 验证
    print("\n🔍 DXF验证:")
    from lb_dxf_engine import DXFValidator
    v = DXFValidator()
    for p in [raw_path, redrawn_path]:
        ok = v.validate(p)
        print(f"   {os.path.basename(p)}: valid={ok}")
        for e in v.errors[:5]:
            print(f"     ❌ {e}")
        w = [w for w in v.warnings if not w[1].startswith('非标准图层: 1') and not w[1].startswith('非标准图层: 6') and not w[1].startswith('非标准图层: 2')]
        for ww in w[:5]:
            print(f"     ⚠️ {ww}")
    
    print(f"\n✅ 修复完成!")
    print(f"   输出: {OUT_DIR}/")

if __name__ == '__main__':
    main()
