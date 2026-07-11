#!/usr/bin/env python3
"""
课题001 — 二层平面图DXF精准重绘
源文件：晴碧园晶园26栋拆砌墙.dxf (28.4MB, AC1027)
方法：
  1. 直接解析ENTITIES段中的所有实体
  2. 按2F模型空间范围(Y:-328538~-311966, X:103K~250K)过滤
  3. 图层映射为标准命名
  4. 导出纯净AC1015 DXF
  5. DXFValidator 质量检查
"""

import re, sys, os, json, math
from collections import defaultdict, Counter

# 路径
DXF_PATH = '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf'
OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/课题001'
os.makedirs(OUT_DIR, exist_ok=True)

# ==================== 二层层平面图边界 ====================
# (通过前期分析确认)
F2F_Y_MIN = -328538.0
F2F_Y_MAX = -311965.8
F2F_X_MIN = 102962.3
F2F_X_MAX = 249744.8

# ==================== 图层映射 ====================
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
    '0': '0',
    'Defpoints': 'Defpoints',
}

LAYER_COLORS = {
    'A-WALL': 7,
    'A-COLUMN': 7,
    'A-DOOR': 4,
    'A-WINDOW': 5,
    'A-STAIR': 6,
    'A-AXIS': 1,
    'A-DIMS': 3,
    'A-TEXT': 7,
    'A-SYMBOL': 2,
    'A-FURN': 6,
    'A-HATCH': 8,
    '0': 7,
    'Defpoints': 250,
}

LAYER_LW = {
    'A-WALL': 30, 'A-COLUMN': 30, 'A-DOOR': 18, 'A-WINDOW': 13,
    'A-STAIR': 18, 'A-AXIS': 13, 'A-DIMS': 13, 'A-TEXT': 13,
    'A-SYMBOL': 13, 'A-FURN': 13, 'A-HATCH': 9, '0': 13, 'Defpoints': 13,
}

# 保留需原封输出的图层（非建筑主要结构但需要保留的图纸内容）
PRESERVE_LAYERS = {
    'W-尺寸', 'W-文字', 'W-Word(文字及尺寸标注)', 'W-基础引线',
    'C-顶部标高',
    'P-固定家具（落地、到顶）', 'P-固定家具（悬空）', 'P-固定家具（落地、不到顶）',
    'P-固定家具（不落地、到顶）', 'P-活动家具', 'P-家具尺寸',
    'P-完成面', 'P-完成面（不到顶）',
    'P-洁具及配件（地坪图不显示）', 'P-完成面尺寸',
    'F-地坪造型线', 'F-地坪尺寸 @ 30',
    'C-顶面造型线', 'C-顶面造型尺寸',
    'C-顶面灯具、灯带', 'C-顶面设备（风口、换气扇、投影仪）',
    'C-顶面灯具及其他点位尺寸', 'C-顶面设备（喷淋、烟感、报警）',
    'M-开关点位', 'M-插座连线', 'BJ-X25 插座', 'BJ-X22 天花尺寸', 'F-X19 开关',
    'TEXT', 'T-text', '0', 'Defpoints',
    # 保留尺寸相关
    # A-WALL等已经在映射表中
}

# ==================== 主逻辑 ====================

def load_dxf_text():
    """加载DXF为文本"""
    with open(DXF_PATH, 'rb') as f:
        data = f.read()
    print(f"📖 读取: {DXF_PATH}")
    print(f"   大小: {len(data)/1024/1024:.1f} MB")
    text = data.decode('utf-8', errors='replace')
    return text


def in_2f_area(block, etype=''):
    """判断实体是否在2F范围内"""
    all_ys = set()
    
    for m in re.finditer(r'\n 2[01]\n', block):
        pos = m.start()
        end_line = block.find('\n', pos + len(m.group(0)))
        if end_line > 0:
            try:
                y = float(block[pos + len(m.group(0)):end_line])
                if abs(y) > 1000:  # 模型空间
                    all_ys.add(y)
            except ValueError:
                pass
    
    if not all_ys:
        return False
    
    # 判断：是否有任何Y坐标在2F范围内
    y_in = any(F2F_Y_MIN <= y <= F2F_Y_MAX for y in all_ys)
    
    if not y_in:
        # 对于LINE/LWPOLYLINE等跨越边界的实体，允许跨越检测
        # 但对于HATCH/CIRCLE/ARC等闭合边界实体，要求必须至少一个点在范围内
        if etype in ('LINE', 'LWPOLYLINE', 'DIMENSION', 'LEADER', 'MLEADER'):
            if len(all_ys) >= 2:
                y_min, y_max = min(all_ys), max(all_ys)
                if y_min <= F2F_Y_MAX and y_max >= F2F_Y_MIN:
                    # 进一步检查：跨越的Y范围必须大部分在2F范围内
                    overlap = min(y_max, F2F_Y_MAX) - max(y_min, F2F_Y_MIN)
                    span = y_max - y_min
                    if span > 0 and overlap / span > 0.1:
                        y_in = True
    
    return y_in


def extract_2f_entities(text):
    """从DXF中提取2F平面图的所有实体"""
    eidx = text.find('\n  0\nSECTION\n  2\nENTITIES\n')
    eend = text.find('\n  0\nENDSEC\n', eidx)
    ent_text = text[eidx:eend]
    
    entities = []  # [(raw_block, etype, original_layer)]
    
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
        
        # 跳过SEQEND, ENDBLK
        if etype in ('SEQEND', 'ENDBLK'):
            pos = start + len(m.group(0))
            continue
        
        # 提取图层
        lm = re.search(r'\n  8\n([^\n]+)', block)
        layer = lm.group(1).strip() if lm else '0'
        
        # 检查是否在2F模型空间
        if in_2f_area(block, etype):
            entities.append((block, etype, layer))
        
        pos = start + len(m.group(0))
    
    return entities


def map_layer(original):
    """将原始图层映射到标准图层"""
    if original in LAYER_MAP:
        return LAYER_MAP[original]
    
    # 搜索包含关系
    for key, val in LAYER_MAP.items():
        if key and (key in original or original in key):
            return val
    
    # 根据关键词推测
    if '墙' in original or '柱' in original or '梁' in original:
        return 'A-WALL'
    if '门' in original:
        return 'A-DOOR'
    if '窗' in original:
        return 'A-WINDOW'
    if '楼梯' in original:
        return 'A-STAIR'
    if '轴' in original:
        return 'A-AXIS'
    if '尺寸' in original or 'DIM' in original:
        return 'A-DIMS'
    if '文字' in original or 'TEXT' in original or 'Word' in original:
        return 'A-TEXT'
    if '标高' in original:
        return 'A-SYMBOL'
    if '家具' in original or '完成面' in original or '地坪' in original or 'FINISH' in original:
        return 'A-FURN'
    if '顶面' in original or '开关' in original or '插座' in original or '灯具' in original:
        return 'A-HATCH'
    
    return '0'


def write_dxf(entities, output_path, remap_layers=True):
    """
    将实体列表写出为DXF
    remap_layers=True: 图层重映射为重绘版
    remap_layers=False: 保留原图层为原始提取版
    """
    # 收集使用的图层
    used_layers = set()
    layer_orig_map = {}  # orig -> target
    
    for _, _, orig_layer in entities:
        if remap_layers:
            target = map_layer(orig_layer)
        else:
            target = orig_layer
        layer_orig_map[orig_layer] = target
        used_layers.add(target)
    
    # 确保标准图层都在
    for l in LAYER_COLORS:
        used_layers.add(l)
    
    lines = []
    
    # === HEADER ===
    lines.extend([
        "  0", "SECTION", "  2", "HEADER",
        "  9", "$ACADVER", "  1", "AC1015",
        "  9", "$INSUNITS", " 70", "4",
        "  0", "ENDSEC"
    ])
    
    # === TABLES ===
    lines.extend(["  0", "SECTION", "  2", "TABLES"])
    
    # LTYPE
    lines.extend([
        "  0", "TABLE", "  2", "LTYPE", " 70", "2",
        "  0", "LTYPE", "  2", "Continuous",
        " 70", "0", "  3", "Solid line",
        " 72", "65", " 73", "0", " 40", "0.0",
        "  0", "LTYPE", "  2", "ByLayer",
        " 70", "0", "  3", "", " 72", "65", " 73", "0", " 40", "0.0",
        "  0", "ENDTAB"
    ])
    
    # LAYER
    lines.extend(["  0", "TABLE", "  2", "LAYER", " 70", str(len(used_layers))])
    for name in sorted(used_layers):
        color = LAYER_COLORS.get(name, 7)
        lw = LAYER_LW.get(name, 13)
        lines.extend([
            "  0", "LAYER",
            "  2", name,
            " 70", "0",
            " 62", str(color),
            "  6", "Continuous",
            "370", str(lw)
        ])
    lines.extend(["  0", "ENDTAB"])
    
    # STYLE
    lines.extend([
        "  0", "TABLE", "  2", "STYLE", " 70", "1",
        "  0", "STYLE", "  2", "Standard",
        " 70", "0", " 40", "0.0", " 41", "1.0",
        " 50", "0.0", " 71", "0", " 42", "2.5",
        "  3", "txt", "  4", "",
        "  0", "ENDTAB"
    ])
    
    lines.extend(["  0", "ENDSEC"])
    
    # === BLOCKS ===
    lines.extend(["  0", "SECTION", "  2", "BLOCKS", "  0", "ENDSEC"])
    
    # === ENTITIES ===
    lines.extend(["  0", "SECTION", "  2", "ENTITIES"])
    
    for raw_block, etype, orig_layer in entities:
        target_layer = layer_orig_map[orig_layer]
        
        # 解析属性
        props = {}
        for cm in re.finditer(r'\n(\d+)\n([^\n]+)', raw_block):
            code = int(cm.group(1))
            val = cm.group(2).strip()
            props[code] = val
        
        # 获取颜色
        color = props.get(62, '256')
        if color == '256':
            color = str(LAYER_COLORS.get(target_layer, 7))
        
        lines.append("  0")
        lines.append(etype)
        lines.append("  8")
        lines.append(target_layer)
        lines.append(" 62")
        lines.append(color)
        
        if etype == 'LINE':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 11", props.get(11, '0'),
                " 21", props.get(21, '0'),
                " 31", props.get(31, '0.0'),
            ])
        
        elif etype == 'LWPOLYLINE':
            # 提取顶点
            n_verts = int(props.get(90, 0))
            lines.extend([" 90", str(n_verts), " 70", props.get(70, '1')])
            
            # LWPOLYLINE 顶点是连续存储的 10/20/10/20...
            # 需要用正则表达式从原始块提取
            verts = re.findall(r'\n 10\n([^\n]+)\n 20\n([^\n]+)', raw_block)
            for vx, vy in verts:
                lines.extend([" 10", vx.strip(), " 20", vy.strip()])
            
            if 43 in props:
                lines.extend([" 43", props[43]])
        
        elif etype == 'CIRCLE':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 40", props.get(40, '0'),
            ])
        
        elif etype == 'ARC':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 40", props.get(40, '0'),
                " 50", props.get(50, '0'),
                " 51", props.get(51, '0'),
            ])
        
        elif etype == 'TEXT':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 40", props.get(40, '2.5'),
                "  1", props.get(1, '').replace('\n', '\\P'),
            ])
            if 50 in props:
                lines.extend([" 50", props[50]])
        
        elif etype == 'MTEXT':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 40", props.get(40, '2.5'),
                " 41", props.get(41, '100'),
                " 71", props.get(71, '1'),
                " 72", props.get(72, '5'),
                "  1", props.get(1, '').replace('\n', '\\P'),
            ])
        
        elif etype == 'DIMENSION':
            lines.extend([
                "  2", props.get(2, '*D0'),
                "  3", props.get(3, 'Standard'),
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 11", props.get(11, '0'),
                " 21", props.get(21, '0'),
                " 31", props.get(31, '0.0'),
                " 12", props.get(12, '0'),
                " 22", props.get(22, '0'),
                " 13", props.get(13, '0'),
                " 23", props.get(23, '0'),
                " 14", props.get(14, '0'),
                " 24", props.get(24, '0'),
                " 70", props.get(70, '0'),
                " 71", props.get(71, '0'),
                " 42", props.get(42, '0.0'),
            ])
        
        elif etype == 'POINT':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
            ])
        
        elif etype == 'INSERT':
            lines.extend([
                "  2", props.get(2, '0'),
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 41", props.get(41, '1.0'),
                " 42", props.get(42, '1.0'),
                " 43", props.get(43, '1.0'),
                " 50", props.get(50, '0.0'),
            ])
        
        elif etype == 'ATTRIB':
            lines.extend([
                " 10", props.get(10, '0'),
                " 20", props.get(20, '0'),
                " 30", props.get(30, '0.0'),
                " 40", props.get(40, '2.5'),
                "  1", props.get(1, ''),
                "  2", props.get(2, ''),
                " 70", props.get(70, '0'),
                " 72", props.get(72, '0'),
                " 74", props.get(74, '0'),
            ])
        
        elif etype == 'HATCH':
            # Hatch - use raw block to preserve boundary data
            # Extract all group codes from raw block
            hatch_codes = []
            for cm in re.finditer(r'\n(\d+)\n([^\n]+)', raw_block):
                code = int(cm.group(1))
                val = cm.group(2).strip()
                hatch_codes.append((code, val))
            
            # Only write basic structure if no 91 boundary count
            if '91' not in dict(hatch_codes) or int(dict(hatch_codes).get('91', '0')) == 0:
                lines.extend([
                    " 10", "0",
                    " 20", "0",
                    " 30", "0.0",
                    "  2", "SOLID",
                    " 70", "0",
                    " 71", "0",
                    " 91", "0",
                ])
            else:
                # Write full hatch with all boundary data from raw block
                for code, val in hatch_codes:
                    if code in (8, 62):
                        continue  # already written
                    lines.append(f"{code:3d}")
                    lines.append(val)
    
    lines.extend(["  0", "ENDSEC"])
    
    # === OBJECTS ===
    lines.extend(["  0", "SECTION", "  2", "OBJECTS", "  0", "ENDSEC"])
    
    # === EOF ===
    lines.append("  0")
    lines.append("EOF")
    
    out_text = '\n' + '\n'.join(lines) + '\n'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(out_text)
    
    return output_path


# ==================== Validator ====================

def validate_dxf(filepath):
    """验证DXF质量"""
    from lb_dxf_engine import DXFValidator
    validator = DXFValidator()
    ok = validator.validate(filepath)
    print(f"\n📋 DXFValidator 报告:")
    print(validator.report())
    return ok


# ==================== 主函数 ====================

def main():
    print("=" * 64)
    print("🏗  CAD Master 课题001 — 二层平面图DXF精准重绘")
    print("=" * 64)
    print()
    
    # 1. 加载
    text = load_dxf_text()
    
    # 2. 提取2F实体
    print(f"\n🔍 提取二层平面图 (Y:{F2F_Y_MIN:.0f}~{F2F_Y_MAX:.0f}, X:{F2F_X_MIN:.0f}~{F2F_X_MAX:.0f})...")
    entities = extract_2f_entities(text)
    print(f"   提取到 {len(entities)} 个实体")
    
    if not entities:
        print("❌ 未提取到任何实体! 中止。")
        return
    
    # 3. 统计
    layer_stats = Counter(orig for _, _, orig in entities)
    etype_stats = Counter(etype for _, etype, _ in entities)
    
    print(f"\n📊 图层分布 (来源):")
    for layer, cnt in layer_stats.most_common(30):
        target = map_layer(layer)
        print(f"   {layer:35s} → {target:10s}  ({cnt:4d}个)")
    
    print(f"\n📊 实体类型分布:")
    for etype, cnt in etype_stats.most_common(15):
        print(f"   {etype:20s}: {cnt:4d}")
    
    # 4. 导出原始提取版
    print(f"\n📄 导出原始提取版...")
    raw_path = os.path.join(OUT_DIR, '二层层平面布置图_原始提取.dxf')
    write_dxf(entities, raw_path, remap_layers=False)
    raw_size = os.path.getsize(raw_path)
    print(f"   已保存: {raw_path}")
    print(f"   大小: {raw_size/1024:.1f} KB")
    validate_dxf(raw_path)
    
    # 5. 导出重绘版
    print(f"\n📄 导出重绘版 (图层映射)...")
    redrawn_path = os.path.join(OUT_DIR, '二层层平面布置图_重绘.dxf')
    write_dxf(entities, redrawn_path, remap_layers=True)
    redrawn_size = os.path.getsize(redrawn_path)
    print(f"   已保存: {redrawn_path}")
    print(f"   大小: {redrawn_size/1024:.1f} KB")
    validate_dxf(redrawn_path)
    
    # 6. 写分析日志
    log = {
        'source_file': DXF_PATH,
        'task': '课题001 — 二层平面图DXF精准重绘',
        '2f_bounds': {
            'y_min': F2F_Y_MIN, 'y_max': F2F_Y_MAX,
            'x_min': F2F_X_MIN, 'x_max': F2F_X_MAX,
        },
        'entity_count': len(entities),
        'layer_stats': {l: c for l, c in layer_stats.most_common()},
        'etype_stats': {e: c for e, c in etype_stats.most_common()},
        'output_files': {
            '原始提取': raw_path,
            '重绘版': redrawn_path,
        }
    }
    
    log_path = os.path.join(OUT_DIR, '课题001_分析日志.json')
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\n📄 分析日志: {log_path}")
    
    print(f"\n✅ 课题001 完成!")
    print(f"   提取实体: {len(entities)}")
    print(f"   输出目录: {OUT_DIR}/")

if __name__ == '__main__':
    main()
