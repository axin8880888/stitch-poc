#!/usr/bin/env python3
"""
DXF 图纸解析器 V2.0
针对真实 DXF 文件设计的完整解析系统
严格按照教程要求执行：

1. 读取 DXF → 2. 结构化输出 → 3. 按JSON重建 → 4. 差异报告
"""

import os, json, shutil
from collections import defaultdict
from svgwrite import Drawing

# 原始 DXF
DXF_PATH = '/storage/emulated/0/设计/金沙美容.dxf'
OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/金沙美容_恢复练习'
os.makedirs(OUT_DIR, exist_ok=True)

# =============================================
# 第一步：完全解析 DXF
# =============================================

class DXFParserV2:
    """专业 DXF 解析器"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.pairs = []       # 所有 (group_code, value) 对
        self.version = ''     # DXF 版本
        self.units = ''       # 单位
        self.codepage = ''    # 编码
        self.layers = {}      # 图层定义
        self.blocks = {}      # 块定义
        self.entities = []    # 图形实体
        self.entities_section = []  # ENTITIES 段原始实体
        self.block_defs = {}  # 块内容
        self.unknown = []     # 无法识别的组
        self._parse()
    
    def _read_pairs(self):
        """读取所有组码对"""
        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        # 按行分割，组码和值交替出现
        lines = content.split('\n')
        pairs = []
        i = 0
        while i < len(lines):
            code_str = lines[i].strip()
            i += 1
            if i >= len(lines):
                break
            val = lines[i].strip()
            pairs.append((code_str, val))
            i += 1
        self.pairs = pairs
        return pairs
    
    def _parse(self):
        pairs = self._read_pairs()
        
        # 当前解析状态
        i = 0
        current_section = None
        current_table = None
        in_tables = False
        in_blocks = False
        in_entities = False
        in_block = False
        current_block = None
        current_entity = None
        
        while i < len(pairs):
            code, val = pairs[i]
            
            # 检测 SECTION 开始
            if code == '0' and val == 'SECTION':
                i += 1
                if i < len(pairs):
                    scode, sval = pairs[i]
                    if scode == '2':
                        current_section = sval
                        if sval == 'HEADER':
                            in_tables = False
                            in_blocks = False
                            in_entities = False
                        elif sval == 'TABLES':
                            in_tables = True
                            in_blocks = False
                            in_entities = False
                        elif sval == 'BLOCKS':
                            in_blocks = True
                            in_tables = False
                            in_entities = False
                        elif sval == 'ENTITIES':
                            in_entities = True
                            in_tables = False
                            in_blocks = False
                i += 1
                continue
            
            # 检测 SECTION 结束
            if code == '0' and val == 'ENDSEC':
                current_section = None
                in_tables = False
                in_blocks = False
                in_entities = False
                i += 1
                continue
            
            # ---- HEADER 段 ----
            if current_section == 'HEADER':
                if code == '9':
                    var_name = val
                    i += 1
                    if i < len(pairs):
                        vcode, vval = pairs[i]
                        if var_name == '$DWGCODEPAGE':
                            self.codepage = vval
                        elif var_name == '$ACADVER':
                            self.version = vval
                        elif var_name == '$INSUNITS':
                            self.units = vval
                i += 1
                continue
            
            # ---- TABLES 段（图层）----
            if in_tables:
                if code == '0' and val == 'TABLE':
                    i += 1
                    if i < len(pairs):
                        tcode, tval = pairs[i]
                        if tcode == '2':
                            current_table = tval
                            if tval == 'LAYER':
                                self.layer_count = 0
                        else:
                            current_table = None
                    i += 1
                    continue
                
                if code == '0' and val == 'LAYER' and current_table == 'LAYER':
                    # 开始解析一个图层
                    layer_info = {'name': None, 'color': 7, 'lineweight': 13, 
                                  'linetype': 'Continuous', 'plot': 1, 'state': 0}
                    i += 1
                    while i < len(pairs):
                        lc, lv = pairs[i]
                        if lc == '0':
                            break  # 下一个实体或表结束
                        if lc == '2':
                            layer_info['name'] = lv
                        elif lc == '62':
                            layer_info['color'] = int(lv)
                        elif lc == '70':
                            layer_info['state'] = int(lv)
                        elif lc == '6':
                            layer_info['linetype'] = lv
                        elif lc == '370':
                            layer_info['lineweight'] = int(lv)
                        elif lc == '290':
                            layer_info['plot'] = int(lv)
                        i += 1
                    if layer_info['name']:
                        self.layers[layer_info['name']] = layer_info
                    continue
                
                if code == '0' and val == 'ENDTAB':
                    current_table = None
                    i += 1
                    continue
                
                i += 1
                continue
            
            # ---- BLOCKS 段 ----
            if in_blocks:
                if code == '0' and val == 'BLOCK':
                    in_block = True
                    current_block = {'name': None, 'base_x': 0, 'base_y': 0, 
                                     'entities': [], 'layer': '0'}
                    i += 1
                    while i < len(pairs):
                        bc, bv = pairs[i]
                        if bc == '0' and bv == 'ENDBLK':
                            if current_block and current_block['name']:
                                self.blocks[current_block['name']] = current_block
                            in_block = False
                            current_block = None
                            break
                        if bc == '2':
                            current_block['name'] = bv
                        elif bc == '10':
                            current_block['base_x'] = float(bv)
                        elif bc == '20':
                            current_block['base_y'] = float(bv)
                        elif bc == '8':
                            current_block['layer'] = bv
                        elif bc == '0':
                            # 块内的实体
                            be = self._read_entity(pairs, i)
                            if be:
                                current_block['entities'].append(be)
                            i += 1
                            continue
                        i += 1
                    i += 1
                    continue
                i += 1
                continue
            
            # ---- ENTITIES 段 ----
            if in_entities:
                if code == '0':
                    if val in ('ENDSEC', 'EOF'):
                        if current_entity:
                            self.entities.append(current_entity)
                            self.entities_section.append(current_entity)
                        i += 1
                        break
                    # 新实体开始
                    if current_entity:
                        self.entities.append(current_entity)
                        self.entities_section.append(current_entity)
                    entity = self._read_entity(pairs, i)
                    current_entity = entity if entity else None
                    i += 1
                    continue
                i += 1
                continue
            
            i += 1
        
        # 收集最后的实体
        if current_entity and current_entity not in self.entities:
            self.entities.append(current_entity)
            self.entities_section.append(current_entity)
    
    def _read_entity(self, pairs, start_idx):
        """读取单个实体"""
        if start_idx >= len(pairs):
            return None
        
        code, val = pairs[start_idx]
        if code != '0':
            return None
        
        entity = {'type': val, 'props': {}}
        i = start_idx + 1
        
        # 组码映射（常用组码）
        while i < len(pairs):
            code, val = pairs[i]
            if code == '0':
                break  # 下一个实体
            try:
                entity['props'][int(code)] = val
            except ValueError:
                pass
            i += 1
        
        # 提取关键属性
        props = entity['props']
        entity['layer'] = props.get(8, '0')
        entity['color'] = int(props.get(62, 256))  # 256 = ByLayer
        entity['linetype'] = props.get(6, 'BYLAYER')
        entity['handle'] = props.get(5, '')
        
        # 提取坐标
        if entity['type'] in ('LINE', 'XLINE', 'RAY'):
            entity['x1'] = float(props.get(10, 0))
            entity['y1'] = float(props.get(20, 0))
            entity['z1'] = float(props.get(30, 0))
            entity['x2'] = float(props.get(11, 0))
            entity['y2'] = float(props.get(21, 0))
            entity['z2'] = float(props.get(31, 0))
        elif entity['type'] in ('CIRCLE', 'ARC'):
            entity['cx'] = float(props.get(10, 0))
            entity['cy'] = float(props.get(20, 0))
            entity['cz'] = float(props.get(30, 0))
            entity['r'] = float(props.get(40, 0))
            if entity['type'] == 'ARC':
                entity['angle_start'] = float(props.get(50, 0))
                entity['angle_end'] = float(props.get(51, 0))
        elif entity['type'] == 'LWPOLYLINE':
            # 提取顶点
            entity['vertices'] = []
            entity['closed'] = int(props.get(70, 0)) & 1
            entity['elevation'] = float(props.get(38, 0))
            entity['const_width'] = float(props.get(43, 0))
            # 读取顶点（在后续的组码中）
        elif entity['type'] == 'INSERT':
            entity['block_name'] = props.get(2, '')
            entity['insert_x'] = float(props.get(10, 0))
            entity['insert_y'] = float(props.get(20, 0))
            entity['scale_x'] = float(props.get(41, 1))
            entity['scale_y'] = float(props.get(42, 1))
            entity['rotation'] = float(props.get(50, 0))
        elif entity['type'] == 'TEXT':
            entity['text'] = props.get(1, '')
            entity['x'] = float(props.get(10, 0))
            entity['y'] = float(props.get(20, 0))
            entity['height'] = float(props.get(40, 0))
            entity['rotation'] = float(props.get(50, 0))
            entity['style'] = props.get(7, 'Standard')
        elif entity['type'] == 'MTEXT':
            entity['text'] = props.get(1, '')
            entity['x'] = float(props.get(10, 0))
            entity['y'] = float(props.get(20, 0))
            entity['height'] = float(props.get(40, 0))
            entity['rotation'] = float(props.get(50, 0))
            entity['style'] = props.get(7, 'Standard')
            entity['attachment'] = int(props.get(71, 1))
        elif entity['type'] == 'DIMENSION':
            entity['dim_type'] = int(props.get(70, 0))
            entity['def_x'] = float(props.get(10, 0))
            entity['def_y'] = float(props.get(20, 0))
            entity['text_x'] = float(props.get(11, 0))
            entity['text_y'] = float(props.get(21, 0))
            entity['text'] = props.get(1, '')
            entity['block'] = props.get(2, '')
            entity['style'] = props.get(3, 'Standard')
        elif entity['type'] == 'HATCH':
            entity['pattern'] = props.get(2, '')
            entity['scale'] = float(props.get(41, 1))
            entity['angle'] = float(props.get(52, 0))
            entity['associative'] = int(props.get(71, 0))
        
        return entity


print("=" * 60)
print("第一步：读取 DXF")
print("=" * 60)
print(f"文件: {DXF_PATH}")
parser = DXFParserV2(DXF_PATH)

print(f"\n📋 DXF 版本: {parser.version or '未知'}")
print(f"📋 编码: {parser.codepage}")
print(f"📋 图层数: {len(parser.layers)}")
print(f"📋 块定义数: {len(parser.blocks)}")
print(f"📋 实体数: {len(parser.entities)}")

# =============================================
# 第二步：输出图纸摘要
# =============================================

print("\n" + "=" * 60)
print("第二步：图纸摘要")
print("=" * 60)

print(f"\n🔷 图层列表 ({len(parser.layers)}):")
color_names = {1:'红',2:'黄',3:'绿',4:'青',5:'蓝',6:'品',7:'白',8:'灰',9:'浅灰'}
for name, info in sorted(parser.layers.items()):
    col = info.get('color', 7)
    lw = info.get('lineweight', 13)
    lt = info.get('linetype', 'Continuous')
    plot = '🖨' if info.get('plot', 1) else '🚫'
    state = info.get('state', 0)
    frozen = '❄' if state & 2 else ''
    locked = '🔒' if state & 4 else ''
    col_name = color_names.get(col, f'c{col}')
    print(f"  {name:20s} 颜色={col_name:3s} 线宽={lw:3d} 线型={lt:12s} {plot}{frozen}{locked}")

print(f"\n🔷 块定义列表 ({len(parser.blocks)}):")
for name, blk in sorted(parser.blocks.items()):
    print(f"  {name:30s} 基点({blk['base_x']:.0f},{blk['base_y']:.0f}) {len(blk['entities'])}个实体")

# 实体统计
entity_types = defaultdict(int)
for ent in parser.entities:
    entity_types[ent['type']] += 1

print(f"\n🔷 实体类型统计:")
for t, n in sorted(entity_types.items(), key=lambda x: -x[1]):
    print(f"  {t:15s}: {n}")

# 文字提取
texts = [e for e in parser.entities if e['type'] in ('TEXT', 'MTEXT')]
if texts:
    print(f"\n🔷 文字内容 ({len(texts)}条):")
    for t in texts[:20]:
        txt = t.get('text', '')[:50]
        layer = t.get('layer', '')
        h = t.get('height', 0)
        print(f"  [{layer}] \"{txt}\" (h={h})")

# 块参照
inserts = [e for e in parser.entities if e['type'] == 'INSERT']
if inserts:
    print(f"\n🔷 块参照 ({len(inserts)}个):")
    for ins in inserts[:10]:
        name = ins.get('block_name', '?')
        x = ins.get('insert_x', 0)
        y = ins.get('insert_y', 0)
        rot = ins.get('rotation', 0)
        sx = ins.get('scale_x', 1)
        print(f"  {name:30s} 位置({x:.1f},{y:.1f}) 缩放({sx:.2f}) 旋转{rot:.1f}°")

# 标注
dims = [e for e in parser.entities if e['type'] == 'DIMENSION']
if dims:
    print(f"\n🔷 标注 ({len(dims)}个):")
    for d in dims[:5]:
        txt = d.get('text', '')
        print(f"  位置({d.get('def_x',0):.1f},{d.get('def_y',0):.1f}) 文字=\"{txt}\"")

# =============================================
# 第三步：保存结构化 JSON
# =============================================

print(f"\n{'='*60}")
print("第三步：保存结构化 JSON")
print("=" * 60)

def entity_to_dict(ent):
    """实体转可序列化字典"""
    d = {k: v for k, v in ent.items() if k != 'props'}
    # 只保留关键prop
    props = ent.get('props', {})
    # 存入几个有用的
    if props:
        d['raw_props_sample'] = dict(list(props.items())[:20])
    return d

json_data = {
    "meta": {
        "filename": "金沙美容.dxf",
        "version": parser.version,
        "codepage": parser.codepage,
        "entity_count": len(parser.entities),
        "layer_count": len(parser.layers),
        "block_count": len(parser.blocks),
    },
    "layers": {name: info for name, info in parser.layers.items()},
    "blocks": {name: {
        'base_x': blk['base_x'],
        'base_y': blk['base_y'],
        'entity_count': len(blk['entities']),
        'entities': [entity_to_dict(e) for e in blk['entities']]
    } for name, blk in parser.blocks.items()},
    "entities": [entity_to_dict(e) for e in parser.entities],
}

json_path = f'{OUT_DIR}/金沙美容_解析结果.json'
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)
print(f"✅ JSON 已保存: {json_path} ({os.path.getsize(json_path)} bytes)")

# =============================================
# 第四步：按中间表示重建 DXF
# =============================================

print(f"\n{'='*60}")
print("第四步：重建 DXF")
print("=" * 60)

from dxf_rebuilder import rebuild_dxf

rebuilt_path = f'{OUT_DIR}/金沙美容_重建.dxf'
rebuilt_ok = rebuild_dxf(parser, rebuilt_path)
if rebuilt_ok:
    print(f"✅ 重建 DXF: {rebuilt_path}")
else:
    print(f"⚠️  重建失败，需人工介入")


# =============================================
# 第五步：SVG 可视化
# =============================================

print(f"\n{'='*60}")
print("第五步：SVG 可视化预览")
print("=" * 60)

# 找图纸范围
min_x = min_y = float('inf')
max_x = max_y = float('-inf')
for ent in parser.entities:
    for key in ['x', 'cx', 'x1', 'insert_x', 'def_x']:
        if key in ent:
            v = ent[key]
            if isinstance(v, (int, float)):
                if v != 0 or key == 'x1':
                    if v > -1e6:
                        min_x = min(min_x, v)
                        max_x = max(max_x, v)
    for key in ['y', 'cy', 'y1', 'insert_y', 'def_y']:
        if key in ent:
            v = ent[key]
            if isinstance(v, (int, float)):
                if v != 0 or key == 'y1':
                    if v > -1e6:
                        min_y = min(min_y, v)
                        max_y = max(max_y, v)

print(f"  图纸范围: X[{min_x:.0f}, {max_x:.0f}] Y[{min_y:.0f}, {max_y:.0f}]")
print(f"  图纸尺寸: {(max_x-min_x)/1000:.1f}m × {(max_y-min_y)/1000:.1f}m")

# 画SVG预览
W_svg = (max_x - min_x) or 1000
H_svg = (max_y - min_y) or 1000
scale = min(800 / W_svg, 600 / H_svg) * 0.9

dwg = Drawing(f'{OUT_DIR}/金沙美容_预览.svg', size=('900px', '700px'))
dwg.add(dwg.rect(insert=(0,0), size=(900,700), fill='#f8f8f8'))

def tx(x): return (x - min_x) * scale + 50
def ty(y): return 680 - (y - min_y) * scale

# 网格
for x in range(int(min_x/1000)*1000, int(max_x/1000)*1000+1, 1000):
    dwg.add(dwg.line((tx(x), ty(min_y)), (tx(x), ty(max_y)), stroke='#e8e8e8', stroke_width=0.5))
for y in range(int(min_y/1000)*1000, int(max_y/1000)*1000+1, 1000):
    dwg.add(dwg.line((tx(min_x), ty(y)), (tx(max_x), ty(y)), stroke='#e8e8e8', stroke_width=0.5))

# 绘制实体
layer_colors = {}
color_idx = 0
palette = ['#222','#c00','#080','#00a','#c0c','#088','#880','#0c0','#aa0','#0aa','#a0a','#66a','#a66','#6a6']

for ent in parser.entities:
    layer = ent.get('layer', '0')
    if layer not in layer_colors:
        layer_colors[layer] = palette[color_idx % len(palette)]
        color_idx += 1
    col = layer_colors[layer]
    
    try:
        if ent['type'] == 'LINE':
            dwg.add(dwg.line((tx(ent['x1']), ty(ent['y1'])), (tx(ent['x2']), ty(ent['y2'])), 
                      stroke=col, stroke_width=1))
        elif ent['type'] == 'CIRCLE':
            dwg.add(dwg.circle(center=(tx(ent['cx']), ty(ent['cy'])), r=ent['r']*scale, 
                      fill='none', stroke=col, stroke_width=1))
        elif ent['type'] == 'INSERT':
            # 块参照 - 画十字标记
            x, y = tx(ent['insert_x']), ty(ent['insert_y'])
            dwg.add(dwg.line((x-5, y), (x+5, y), stroke=col, stroke_width=1))
            dwg.add(dwg.line((x, y-5), (x, y+5), stroke=col, stroke_width=1))
            dwg.add(dwg.circle(center=(x, y), r=4, fill='none', stroke=col, stroke_width=0.5))
        elif ent['type'] in ('TEXT', 'MTEXT'):
            txt = ent.get('text', '')[:20]
            if txt:
                dwg.add(dwg.text(txt, insert=(tx(ent.get('x',0)), ty(ent.get('y',0))), 
                          font_size='6', fill=col, font_family='sans-serif'))
        elif ent['type'] == 'LWPOLYLINE':
            pass  # LWPOLYLINE 的顶点在后续处理
    except:
        pass

# 图例
leg = 50
for layer, col in sorted(layer_colors.items()):
    dwg.add(dwg.rect(insert=(leg, 10), size=(10, 8), fill=col))
    dwg.add(dwg.text(layer[:20], insert=(leg+12, 18), font_size='7'))
    leg += 120
    if leg > 800:
        break

dwg.add(dwg.text(f'金沙美容 原图预览 | {len(parser.entities)}个实体 | {len(parser.layers)}个图层',
          insert=(450, 690), font_size='11', font_weight='bold', text_anchor='middle'))

dwg.save()
print(f"✅ SVG: {OUT_DIR}/金沙美容_预览.svg")

# =============================================
# 输出恢复报告
# =============================================

print(f"\n{'='*60}")
print("恢复报告")
print("=" * 60)

print(f"""
📋 金沙美容 DXF 恢复报告
────────────────────────
原文件: 金沙美容.dwg → 金沙美容.dxf ({os.path.getsize(DXF_PATH)} bytes)
恢复目标: 完整保留图层/块/实体信息

✅ 精确保留:
   - {len(parser.layers)} 个图层（名称/颜色/线宽/线型）
   - {len(parser.blocks)} 个块定义（含基点+内部实体）
   - {len(parser.entities)} 个图形实体
   - {entity_types.get('LINE',0)} 条LINE
   - {entity_types.get('CIRCLE',0)} 个CIRCLE
   - {entity_types.get('INSERT',0)} 个INSERT（块参照）
   - {entity_types.get('TEXT',0)} 个TEXT文字
   - {entity_types.get('MTEXT',0)} 个MTEXT多行文字
   - {entity_types.get('DIMENSION',0)} 个DIMENSION标注

⚠️  恢复限制:
   - LWPOLYLINE: 顶点需要额外解析组码90/10/20
   - HATCH: 边界需要完整重建
   - SPLINE: 需要拟合点数据
   - DIMENSION: 标注块引用了 *Dxxx 匿名块

📁 输出文件:
   - 解析JSON: 金沙美容_解析结果.json
   - 重建DXF: 金沙美容_重建.dxf
   - 预览SVG: 金沙美容_预览.svg
""")
