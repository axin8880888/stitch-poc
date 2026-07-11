#!/usr/bin/env python3
"""
规范检查器 V1.0 — CAD Master 第三阶段核心工具
对 DXF 图纸自动检查是否符合制图规范

检查项目：
1. 图层命名规范
2. 图层颜色规范
3. 线宽规范
4. 文字高度规范
5. 图层使用检查
"""

import os, re
from collections import defaultdict

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/03_规范'


# =============================================
# 规范标准定义
# =============================================

LAYER_STANDARD = {
    'A-WALL':   {'color': 7,  'lineweight': 30, 'linetype': 'Continuous', 'desc': '墙体轮廓'},
    'A-WALL-H': {'color': 8,  'lineweight': 9,  'linetype': 'Continuous', 'desc': '墙体填充'},
    'A-DOOR':   {'color': 4,  'lineweight': 18, 'linetype': 'Continuous', 'desc': '门'},
    'A-WINDW':  {'color': 5,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '窗'},
    'A-FURN':   {'color': 6,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '家具'},
    'A-DIM':    {'color': 3,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '尺寸标注'},
    'A-TEXT':   {'color': 7,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '文字说明'},
    'A-AXIS':   {'color': 1,  'lineweight': 13, 'linetype': 'CENTER',     'desc': '轴线'},
    'A-HIDD':   {'color': 2,  'lineweight': 13, 'linetype': 'HIDDEN',     'desc': '隐藏线'},
    'A-CNTR':   {'color': 2,  'lineweight': 13, 'linetype': 'CENTER',     'desc': '中心线'},
    'A-DOTE':   {'color': 9,  'lineweight': 9,  'linetype': 'DASHED',     'desc': '辅助线'},
    'A-EXST':   {'color': 2,  'lineweight': 13, 'linetype': 'HIDDEN',     'desc': '保留现有'},
    'A-DEMO':   {'color': 1,  'lineweight': 13, 'linetype': 'DASHED',     'desc': '拆除部分'},
    'A-NEWW':   {'color': 4,  'lineweight': 18, 'linetype': 'Continuous', 'desc': '新建墙体'},
    'A-HATCH':  {'color': 8,  'lineweight': 9,  'linetype': 'Continuous', 'desc': '图案填充'},
    'A-NOTE':   {'color': 7,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '注释'},
    'A-HEAD':   {'color': 3,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '索引/标高'},
    'A-SECT':   {'color': 3,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '剖切符号'},
    'A-PLOT':   {'color': 252,'lineweight': 9,  'linetype': 'Continuous', 'desc': '打印层'},
    'A-REF':    {'color': 9,  'lineweight': 9,  'linetype': 'Continuous', 'desc': '参考底图'},
}

# 图层前缀规范
PREFIX_RULES = {
    'A-': '建筑',
    'S-': '结构',
    'M-': '机械',
    'E-': '电气',
    'P-': '给排水',
}

# 线宽整数对应的毫米值
LINEWEIGHT_MAP = {
    9: 0.09, 13: 0.13, 15: 0.15, 18: 0.18,
    20: 0.20, 25: 0.25, 30: 0.30, 35: 0.35,
    40: 0.40, 50: 0.50, 53: 0.53, 60: 0.60,
    70: 0.70, 80: 0.80, 100: 1.00,
}

# 推荐文字高度（1:100比例）
TEXT_HEIGHT_STANDARD = {
    '大标题': (7, 10),
    '中标题': 5,
    '说明文字': 3.5,
    '尺寸文字': 2.5,
    '图注': 2.5,
    '小标注': 2.0,
}


# =============================================
# DXF 解析器（复用）
# =============================================

class SimpleDXFParser:
    """纯 Python DXF 解析器"""
    def __init__(self, filepath):
        self.filepath = filepath
        self.entities = []
        self.layers = {}  # 图纸中定义的图层
        self.headers = {}
        self._parse()
    
    def _parse(self):
        with open(self.filepath, encoding='utf-8', errors='replace') as f:
            text = f.read()
        
        # 读取所有成对数据
        tokens = [t.strip() for t in text.split('\n') if t.strip()]
        pairs = []
        i = 0
        while i < len(tokens):
            code = tokens[i]
            i += 1
            val = tokens[i] if i < len(tokens) else ''
            pairs.append((code, val))
            i += 1
        
        # 提取 LAYER 表定义
        in_tables = False
        in_layer_table = False
        current_layer = {}
        ci = 0
        while ci < len(pairs):
            code, val = pairs[ci]
            
            if code == '2' and val == 'TABLES':
                in_tables = True
                ci += 1
                continue
            if in_tables and code == '0' and val == 'TABLE':
                ci += 1
                if ci < len(pairs) and pairs[ci][1] == 'LAYER':
                    in_layer_table = True
                ci += 1
                continue
            if in_layer_table and code == '0' and val == 'ENDTAB':
                in_layer_table = False
                in_tables = False
                ci += 1
                continue
            if in_layer_table and code == '0' and val == 'LAYER':
                if current_layer and 'name' in current_layer:
                    self.layers[current_layer['name']] = dict(current_layer)
                current_layer = {'name': None, 'color': 7, 'lineweight': 13, 'linetype': 'Continuous'}
                ci += 1
                continue
            if in_layer_table and code == '2' and current_layer.get('name') is None:
                current_layer['name'] = val
                ci += 1
                continue
            if in_layer_table and code == '62':
                current_layer['color'] = int(val)
                ci += 1
                continue
            if in_layer_table and code == '370':
                current_layer['lineweight'] = int(val)
                ci += 1
                continue
            if in_layer_table and code == '6':
                current_layer['linetype'] = val
                ci += 1
                continue
            
            ci += 1
        
        if current_layer and 'name' in current_layer:
            self.layers[current_layer['name']] = dict(current_layer)
        
        # 提取 ENTITIES
        parts = text.split('ENTITIES')
        if len(parts) < 2:
            return
        
        etext = parts[1].split('ENDSEC')[0]
        tokens = [t.strip() for t in etext.split('\n') if t.strip()]
        
        cur = None
        i = 0
        while i < len(tokens):
            if tokens[i] == '0':
                if cur and cur.get('type'):
                    self.entities.append(cur)
                i += 1
                cur = {'type': tokens[i] if i < len(tokens) else None, 'props': {}}
                i += 1
            elif cur:
                try:
                    code = int(tokens[i])
                    i += 1
                    if i < len(tokens):
                        cur['props'][code] = tokens[i]
                        i += 1
                except ValueError:
                    i += 1
            else:
                i += 1
        
        if cur and cur.get('type') and cur['type'] not in ('ENDSEC', 'EOF', ''):
            self.entities.append(cur)


# =============================================
# 规范检查器
# =============================================

class SpecChecker:
    """制图规范检查器"""
    
    def __init__(self, parser):
        self.parser = parser
        self.issues = []  # [(严重程度, 分类, 描述), ...]
    
    def check_all(self):
        """执行所有检查"""
        self.check_layer_names()
        self.check_layer_colors()
        self.check_layer_lineweights()
        self.check_text_heights()
        self.check_0_layer_usage()
        self.check_missing_layers()
        return self.issues
    
    def add_issue(self, severity, category, desc):
        self.issues.append((severity, category, desc))
    
    def check_layer_names(self):
        """检查图层命名是否符合规范"""
        for name in self.parser.layers:
            # 检查是否有标准前缀
            valid_prefix = any(name.startswith(p) for p in PREFIX_RULES)
            if not valid_prefix:
                self.add_issue('WARN', '图层命名', 
                    f'图层 "{name}" 没有标准前缀（应为 A-/S-/M-/E-/P-）')
            else:
                # 检查是否在标准图层列表中
                if name not in LAYER_STANDARD:
                    prefix = name.split('-')[0] + '-' if '-' in name else ''
                    self.add_issue('INFO', '图层命名', 
                        f'图层 "{name}" 不在标准库中（非标准名称），建议统一命名')
        
        # 检查是否有中文图层名
        for name in self.parser.layers:
            if re.search(r'[\u4e00-\u9fff]', name):
                self.add_issue('ERROR', '图层命名', 
                    f'图层 "{name}" 包含中文，应统一使用英文命名')
    
    def check_layer_colors(self):
        """检查图层颜色是否符合规范"""
        for name, props in self.parser.layers.items():
            if name in LAYER_STANDARD:
                std = LAYER_STANDARD[name]
                actual_color = props.get('color', 7)
                if actual_color != std['color']:
                    self.add_issue('WARN', '图层颜色', 
                        f'图层 "{name}" 颜色应为 {std["color"]}({std["desc"]})，当前为 {actual_color}')
    
    def check_layer_lineweights(self):
        """检查线宽"""
        for name, props in self.parser.layers.items():
            if name in LAYER_STANDARD:
                std = LAYER_STANDARD[name]
                actual_lw = props.get('lineweight', 13)
                if actual_lw != std['lineweight']:
                    std_mm = LINEWEIGHT_MAP.get(std['lineweight'], f'{std["lineweight"]/100:.2f}mm')
                    actual_mm = LINEWEIGHT_MAP.get(actual_lw, f'{actual_lw/100:.2f}mm')
                    self.add_issue('WARN', '线宽',
                        f'图层 "{name}" 线宽应为 {std_mm}，当前为 {actual_mm}')
    
    def check_text_heights(self):
        """检查文字高度是否合理"""
        for ent in self.parser.entities:
            if ent['type'] == 'TEXT':
                height = float(ent['props'].get(40, '0'))
                if height > 0:
                    # 检查是否在合理范围（1:100比例下 2-10mm）
                    if height < 1.5:
                        self.add_issue('WARN', '文字高度',
                            f'文字 "{ent["props"].get(1, "")[:20]}" 高度={height}mm，偏小（建议≥2.0）')
                    elif height > 20:
                        self.add_issue('WARN', '文字高度',
                            f'文字 "{ent["props"].get(1, "")[:20]}" 高度={height}mm，偏大（建议≤10）')
    
    def check_0_layer_usage(self):
        """检查是否有对象在 0 图层"""
        count_0 = 0
        for ent in self.parser.entities:
            layer = ent['props'].get(8, '0')
            if layer == '0':
                count_0 += 1
        
        if count_0 > 0:
            self.add_issue('ERROR', '图层使用',
                f'有 {count_0} 个实体在 0 图层上（除块定义外，对象不应在 0 层的）')
    
    def check_missing_layers(self):
        """检查是否缺少常用的标准图层"""
        present = set(self.parser.layers.keys())
        essential = ['A-WALL', 'A-DOOR', 'A-WINDW', 'A-FURN', 'A-DIM', 'A-TEXT']
        missing = [l for l in essential if l not in present]
        if missing:
            self.add_issue('INFO', '图层缺失',
                f'缺少常用图层: {", ".join(missing)}')

    def check_entity_layer_match(self):
        """检查实体是否在正确的图层上"""
        for ent in self.parser.entities:
            layer = ent['props'].get(8, '0')
            etype = ent['type']
            
            # 标注应在 DIM 图层
            if etype == 'DIMENSION' and layer not in ('A-DIM', '0', ''):
                self.add_issue('WARN', '实体图层',
                    f'标注实体应在 A-DIM 图层，当前在 "{layer}"')
            
            # 文字应在 TEXT 图层
            if etype == 'TEXT' and layer not in ('A-TEXT', '0', ''):
                pass  # 文字可能在多个图层，仅做信息提示不够准确
    
    def report(self):
        """生成检查报告"""
        lines = []
        lines.append("=" * 55)
        lines.append("📋 规范检查报告")
        lines.append("=" * 55)
        lines.append(f"文件: {os.path.basename(self.parser.filepath)}")
        lines.append(f"图层数: {len(self.parser.layers)}")
        lines.append(f"实体数: {len(self.parser.entities)}")
        lines.append("")
        
        if not self.issues:
            lines.append("✅ 完美通过！没有发现问题")
            return '\n'.join(lines)
        
        # 按严重程度分组
        by_severity = {}
        for sev, cat, desc in self.issues:
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append((cat, desc))
        
        for severity in ['ERROR', 'WARN', 'INFO']:
            if severity in by_severity:
                sev_label = {'ERROR': '❌ 错误', 'WARN': '⚠️  警告', 'INFO': '💡 建议'}[severity]
                lines.append(f"\n{sev_label} ({len(by_severity[severity])}项):")
                for cat, desc in by_severity[severity]:
                    lines.append(f"  [{cat}] {desc}")
        
        total = len(self.issues)
        errors = len(by_severity.get('ERROR', []))
        warns = len(by_severity.get('WARN', []))
        info = len(by_severity.get('INFO', []))
        lines.append(f"\n📊 摘要: {total}项问题 (错误{errors} / 警告{warns} / 建议{info})")
        
        return '\n'.join(lines)


# =============================================
# 主程序
# =============================================

def check_dxf(filepath):
    """对单个 DXF 执行全部检查"""
    print(f"检查: {filepath}")
    parser = SimpleDXFParser(filepath)
    checker = SpecChecker(parser)
    checker.check_all()
    report = checker.report()
    print(report)
    return checker.issues


if __name__ == '__main__':
    import sys
    
    print("🏗  CAD Master — 制图规范检查器 V1.0")
    print("=" * 55)
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.isfile(filepath) and filepath.lower().endswith('.dxf'):
            check_dxf(filepath)
        else:
            print("❌ 无效文件，请指定 DXF 文件路径")
    else:
        # 默认扫描整个项目目录的所有 DXF
        print("扫描项目目录中的 DXF 文件...\n")
        project_root = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
        dxf_files = []
        for root, dirs, files in os.walk(project_root):
            for f in files:
                if f.lower().endswith('.dxf'):
                    dxf_files.append(os.path.join(root, f))
        
        if not dxf_files:
            print("未找到 DXF 文件")
        else:
            for dxf in sorted(dxf_files):
                check_dxf(dxf)
                print()
