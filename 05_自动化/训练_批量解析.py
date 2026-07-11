#!/usr/bin/env python3
"""
DXF 项目解析器 V3.0 — 自主训练核心
支持完整解析 → JSON → 重建 → 对比验证

训练计划：
1. 遍历所有DXF文件
2. 完整解析每个文件
3. 输出结构化JSON
4. 精确重建
5. 对比差异报告
6. 积累知识库
"""

import os, json, sys, re
from pathlib import Path
from collections import defaultdict, Counter

# 扫描路径
SCAN_DIRS = [
    '/storage/emulated/0/设计/',
    '/storage/emulated/0/Download/篮筐整改/CAD_Master/',
    '/storage/emulated/0/CADViewer/',
]

OUT_BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化'
os.makedirs(OUT_BASE, exist_ok=True)

# =============================================
# V3.0 解析器 — 完整支持所有DXF实体
# =============================================

class DXFReaderV3:
    """通用 DXF 读取器，支持所有标准段"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.sections = {}      # section_name → lines
        self.pairs = []         # 全部组码对
        self.stats = Counter()  # 统计
        self.meta = {}
        self.layers = {}
        self.blocks = {}
        self.entities = []
        self.errors = []
        self._read()
    
    def _read(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"读取失败: {e}")
            return
        
        self.content_size = len(content.encode('utf-8'))
        self.line_count = content.count('\n') + 1
        
        # 分段
        lines = content.split('\n')
        current_sec = None
        sec_start = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == 'SECTION':
                for j in range(i+1, min(i+3, len(lines))):
                    if lines[j].strip() == '2' and j+1 < len(lines):
                        sec_name = lines[j+1].strip()
                        current_sec = sec_name
                        sec_start = i
                        break
            elif stripped == 'ENDSEC' and current_sec:
                self.sections[current_sec] = {
                    'start': sec_start,
                    'end': i,
                    'lines': lines[sec_start:i+1]
                }
                current_sec = None
        
        # 解析HEADER
        self._parse_header()
        
        # 解析TABLES
        self._parse_tables()
        
        # 解析BLOCKS
        self._parse_blocks()
        
        # 解析ENTITIES
        self._parse_entities()
        
        # 统计
        self.stats['file_size'] = self.content_size
        self.stats['line_count'] = self.line_count
        self.stats['section_count'] = len(self.sections)
        self.stats['layer_count'] = len(self.layers)
        self.stats['block_count'] = len(self.blocks)
        self.stats['entity_count'] = len(self.entities)
    
    def _parse_header(self):
        sec = self.sections.get('HEADER')
        if not sec:
            return
        lines = sec['lines']
        for i in range(len(lines)):
            s = lines[i].strip()
            if s == '$ACADVER' and i+1 < len(lines) and lines[i+1].strip() == '1':
                self.meta['version'] = lines[i+2].strip() if i+2 < len(lines) else ''
            elif s == '$DWGCODEPAGE' and i+1 < len(lines) and lines[i+1].strip() == '3':
                self.meta['codepage'] = lines[i+2].strip() if i+2 < len(lines) else ''
            elif s == '$INSUNITS':
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() == '70':
                        unit_code = int(lines[j+1].strip()) if j+1 < len(lines) else 0
                        unit_names = {0:'未定义',1:'英寸',2:'英尺',3:'英里',4:'毫米',5:'厘米',6:'米',7:'公里'}
                        self.meta['units'] = unit_names.get(unit_code, str(unit_code))
                        break
    
    def _parse_tables(self):
        sec = self.sections.get('TABLES')
        if not sec:
            return
        lines = sec['lines']
        
        i = 0
        current_table = None
        
        while i < len(lines):
            s = lines[i].strip()
            
            if s == 'TABLE' and i+1 < len(lines):
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() == '2' and j+1 < len(lines):
                        current_table = lines[j+1].strip()
                        break
            
            if s == 'LAYER' and current_table == 'LAYER':
                layer = {'name': None, 'color': 7, 'lineweight': 13, 'linetype': 'Continuous', 'plot': 1, 'frozen': False, 'locked': False}
                j = i + 1
                while j < len(lines) and lines[j].strip() != '0':
                    code = lines[j].strip()
                    j += 1
                    val = lines[j].strip() if j < len(lines) else ''
                    if code == '2': layer['name'] = val
                    elif code == '62': layer['color'] = int(val)
                    elif code == '70': layer['frozen'] = bool(int(val) & 2); layer['locked'] = bool(int(val) & 4)
                    elif code == '6': layer['linetype'] = val
                    elif code == '370': layer['lineweight'] = int(val)
                    elif code == '290': layer['plot'] = int(val)
                    j += 1
                if layer['name']:
                    self.layers[layer['name']] = layer
            
            i += 1
    
    def _parse_blocks(self):
        sec = self.sections.get('BLOCKS')
        if not sec:
            return
        lines = sec['lines']
        
        i = 0
        in_block = False
        block = None
        
        while i < len(lines):
            s = lines[i].strip()
            
            if s == 'BLOCK' and not in_block:
                block = {'name': None, 'base_x': 0, 'base_y': 0, 'layer': '0', 'entities': []}
                in_block = True
                i += 1
                continue
            
            if in_block:
                if s == 'ENDBLK':
                    if block and block['name']:
                        self.blocks[block['name']] = block
                    in_block = False
                    block = None
                    i += 1
                    continue
                
                code = s
                i += 1
                val = lines[i].strip() if i < len(lines) else ''
                
                if code == '2': block['name'] = val
                elif code == '10': block['base_x'] = float(val)
                elif code == '20': block['base_y'] = float(val)
                elif code == '8': block['layer'] = val
                elif code == '0':
                    # 块中的实体
                    ent = self._read_one_entity(lines, i-1)
                    if ent:
                        block['entities'].append(ent)
            
            i += 1
    
    def _read_one_entity(self, lines, start):
        """读取单个实体"""
        if start >= len(lines) or lines[start].strip() != '0':
            return None
        
        ent = {'type': lines[start+1].strip() if start+1 < len(lines) else 'UNKNOWN'}
        i = start + 2
        
        while i < len(lines):
            s = lines[i].strip()
            if s == '0':  # 下一个实体
                break
            code = s
            i += 1
            val = lines[i].strip() if i < len(lines) else ''
            if code.isdigit() or (code.startswith('-') and code[1:].isdigit()):
                ent[int(code)] = val
            i += 1
        
        self.stats[f'entity_{ent["type"]}'] += 1
        return ent
    
    def _parse_entities(self):
        sec = self.sections.get('ENTITIES')
        if not sec:
            return
        lines = sec['lines']
        
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s == '0' and i+1 < len(lines):
                ent = self._read_one_entity(lines, i)
                if ent and ent['type'] not in ('ENDSEC', 'EOF'):
                    self.entities.append(ent)
                    # 提取常用属性
                    ent['layer'] = ent.get(8, '0')
                    ent['color'] = int(ent.get(62, 256))
                    ent['linetype'] = ent.get(6, 'BYLAYER')
                    
                    # 实体类型统计
                    self.stats['entity_count'] = len(self.entities)
                    
                    # 找到下一个0
                    i += 1
                    while i < len(lines) and lines[i].strip() != '0':
                        i += 1
                    continue
            i += 1
    
    def summary(self):
        """输出摘要"""
        lines_out = []
        lines_out.append(f"\n{'='*60}")
        lines_out.append(f"📋 {self.filename}")
        lines_out.append(f"{'='*60}")
        lines_out.append(f"  文件大小: {self.content_size:,} bytes ({self.line_count:,}行)")
        lines_out.append(f"  DXF版本: {self.meta.get('version','?')}")
        lines_out.append(f"  编码: {self.meta.get('codepage','?')}")
        lines_out.append(f"  单位: {self.meta.get('units','?')}")
        lines_out.append(f"  段数: {len(self.sections)}")
        lines_out.append(f"  图层: {len(self.layers)}")
        lines_out.append(f"  块: {len(self.blocks)}")
        lines_out.append(f"  实体: {len(self.entities)}")
        
        lines_out.append(f"\n  📊 实体类型分布:")
        for t, n in sorted(self.stats.items()):
            if str(t).startswith('entity_'):
                name = t[7:]
                lines_out.append(f"    {name:20s}: {n}")
        
        lines_out.append(f"\n  📑 段结构:")
        for name, info in self.sections.items():
            ln = info['end'] - info['start'] + 1
            lines_out.append(f"    {name:12s} 行{info['start']:5d}-{info['end']:5d} ({ln}行)")
        
        if self.errors:
            lines_out.append(f"\n  ⚠️  错误:")
            for e in self.errors[:5]:
                lines_out.append(f"    {e}")
        
        return '\n'.join(lines_out)
    
    def to_json(self):
        """转JSON (可序列化)"""
        def ent_to_dict(e):
            d = {'type': e['type'], 'layer': e.get('layer','0'), 'color': e.get('color',256)}
            for k, v in e.items():
                if isinstance(k, int):
                    d[f'code_{k}'] = str(v)[:100]
            return d
        
        data = {
            'meta': {
                'filename': self.filename,
                'filepath': self.filepath,
                'size': self.content_size,
                'lines': self.line_count,
                'version': self.meta.get('version',''),
                'codepage': self.meta.get('codepage',''),
                'units': self.meta.get('units',''),
            },
            'layers': self.layers,
            'blocks': {name: {
                'base_x': b['base_x'],
                'base_y': b['base_y'],
                'layer': b['layer'],
                'entity_count': len(b['entities']),
            } for name, b in self.blocks.items()},
            'entities': [ent_to_dict(e) for e in self.entities],
        }
        return data


# =============================================
# 批量扫描
# =============================================

def scan_all_dxf():
    """扫描所有DXF文件"""
    found = []
    for d in SCAN_DIRS:
        if os.path.isdir(d):
            for root, dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith('.dxf'):
                        fp = os.path.join(root, f)
                        sz = os.path.getsize(fp)
                        found.append((fp, sz))
    found.sort(key=lambda x: -x[1])  # 从大到小
    return found

def train_on_dxf(filepath):
    """对单个DXF执行训练"""
    reader = DXFReaderV3(filepath)
    print(reader.summary())
    
    # 保存JSON
    json_dir = f'{OUT_BASE}/训练记录'
    os.makedirs(json_dir, exist_ok=True)
    safe_name = os.path.basename(filepath).replace('.dxf', '')
    
    import json
    json_path = f'{json_dir}/{safe_name}_解析.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(reader.to_json(), f, ensure_ascii=False, indent=2)
    print(f"  💾 JSON: {json_path}")
    
    return reader


# =============================================
# 主程序
# =============================================

print("=" * 60)
print("🏗  DXF 自主训练系统 V3.0")
print("   扫描 + 解析 + JSON + 统计")
print("=" * 60)

# 扫描所有DXF
print("\n🔍 扫描DXF文件...")
all_dxf = scan_all_dxf()

print(f"\n找到 {len(all_dxf)} 个DXF文件:")
for fp, sz in all_dxf:
    human_sz = f"{sz/1024:.1f}KB" if sz < 1_000_000 else f"{sz/1_000_000:.1f}MB"
    print(f"  {human_sz:8s} {fp}")

# 开始训练
print(f"\n{'='*60}")
print("开始训练...")
print("=" * 60)

for i, (fp, sz) in enumerate(all_dxf):
    print(f"\n{'─'*60}")
    print(f"训练 #{i+1}/{len(all_dxf)}: {fp}")
    print(f"{'─'*60}")
    try:
        reader = train_on_dxf(fp)
        print(f"  ✅ 训练完成")
    except Exception as e:
        print(f"  ❌ 训练失败: {e}")

print(f"\n{'='*60}")
print("训练完成！")
print(f"{'='*60}")

# 生成汇总
print(f"\n📊 训练汇总:")
for fp, sz in all_dxf:
    status = '✅' if os.path.exists(OUT_BASE + '/训练记录/' + os.path.basename(fp).replace('.dxf','') + '_解析.json') else '❌'
    print(f"  {status} {os.path.basename(fp)}")
