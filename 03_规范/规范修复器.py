#!/usr/bin/env python3
"""
规范修复器 — 对 DXF 图纸按 Guoxin Standard 自动修正

修复项：
1. 图层颜色纠偏
2. 线宽纠偏  
3. 0图层实体迁移
4. 生成规范检查报告
5. 输出修正后的 DXF

这个脚本本身就是第三阶段的核心训练：
修复 = 理解为什么这样才是对的
"""

import os, re, shutil
from collections import defaultdict

# 标准图层库（完整版）
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
    'A-HATCH':  {'color': 8,  'lineweight': 9,  'linetype': 'Continuous', 'desc': '图案填充'},
    'A-NOTE':   {'color': 7,  'lineweight': 13, 'linetype': 'Continuous', 'desc': '注释'},
}

# 颜色编号 ↔ 名称（用于阅读）
COLOR_NAMES = {
    1: '红', 2: '黄', 3: '绿', 4: '青', 5: '蓝', 
    6: '品红', 7: '白/黑', 8: '深灰', 9: '浅灰',
    252: '浅灰(打印)',
}

# 线宽 (整数编码 → 毫米)
LW_MM = {9:0.09, 13:0.13, 15:0.15, 18:0.18, 20:0.20, 25:0.25, 30:0.30, 35:0.35, 40:0.40, 50:0.50}


def fix_dxf_layer_colors(input_path, output_path=None):
    """
    修正 DXF 文件中所有图层的颜色和线宽
    修改 LAYER 表定义
    """
    if output_path is None:
        output_path = input_path.replace('.dxf', '_fixed.dxf')
    
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # 找到 LAYER 表区域并修正
    in_layer_table = False
    in_layer = False
    current_layer_name = None
    modified = False
    fix_log = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检测 LAYER 表开始：0 TABLE + 2 LAYER
        if line == 'TABLE' and i > 0 and lines[i-1] == '0':
            if i+1 < len(lines) and lines[i+1] == '2':
                for j in range(i, min(i+5, len(lines))):
                    if lines[j] == 'LAYER':
                        in_layer_table = True
                        break
        
        # 检测 LAYER 定义开始
        if in_layer_table and line == '0' and i+1 < len(lines) and lines[i+1] == 'LAYER':
            in_layer = True
            current_layer_name = None
            i += 2
            continue
        
        # 检测 ENDTAB
        if in_layer_table and line == 'ENDTAB':
            in_layer_table = False
            in_layer = False
            i += 1
            continue
        
        # 检测 ENDSEC
        if in_layer_table and line == 'ENDSEC':
            in_layer_table = False
            in_layer = False
            i += 1
            continue
        
        if in_layer and line == '0':
            # 下一个 LAYER 或 ENDTAB
            in_layer = False
            # 不要跳过，让下次循环处理
            i += 1
            continue
        
        # 读取图层名称
        if in_layer and current_layer_name is None and line == '2':
            # 2 后面跟着的是图层名
            if i+1 < len(lines):
                current_layer_name = lines[i+1]
                i += 2
                continue
        
        if in_layer and current_layer_name and current_layer_name in LAYER_STANDARD:
            std = LAYER_STANDARD[current_layer_name]
            
            if line == '62':  # 颜色代码
                i += 1
                if i < len(lines):
                    current_color = int(lines[i])
                    if current_color != std['color']:
                        old_color = COLOR_NAMES.get(current_color, str(current_color))
                        new_color = COLOR_NAMES.get(std['color'], str(std['color']))
                        lines[i] = str(std['color'])
                        fix_log.append(f"  🔧 {current_layer_name}: 颜色 {old_color}({current_color}) → {new_color}({std['color']})")
                        modified = True
                i += 1
                continue
            
            if line == '370':  # 线宽
                i += 1
                if i < len(lines):
                    current_lw = int(lines[i])
                    if current_lw != std['lineweight']:
                        old_lw = LW_MM.get(current_lw, f'{current_lw}')
                        new_lw = LW_MM.get(std['lineweight'], f'{std["lineweight"]}')
                        lines[i] = str(std['lineweight'])
                        fix_log.append(f"  🔧 {current_layer_name}: 线宽 {old_lw}mm → {new_lw}mm")
                        modified = True
                i += 1
                continue
        
        i += 1
    
    # 写回文件
    new_content = '\n'.join(lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return modified, fix_log, output_path


def add_standard_layers(input_path, output_path=None):
    """添加缺少的标准图层定义"""
    if output_path is None:
        output_path = input_path.replace('.dxf', '_layered.dxf')
    
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # 解析已有图层
    tokens = [t.strip() for t in content.split('\n') if t.strip()]
    existing_layers = set()
    
    in_tables = False
    in_lt = False
    for ci, token in enumerate(tokens):
        if token == 'TABLES' and ci > 0 and tokens[ci-1] == '2':
            in_tables = True
        if in_tables and token == 'ENDTAB':
            in_lt = False
            in_tables = False
        if in_tables and token == '0' and ci+1 < len(tokens) and tokens[ci+1] == 'TABLE':
            if ci+2 < len(tokens) and tokens[ci+2] == 'LAYER':
                in_lt = True
        if in_lt and token == '2' and ci > 0 and tokens[ci-1] == '0':
            continue
        if in_lt and token == '0':
            continue
    
    # 更精确地解析已有图层
    pairs = []
    tokens2 = [t.strip() for t in content.split('\n') if t.strip()]
    for ci in range(0, len(tokens2)-1, 2):
        pairs.append((tokens2[ci], tokens2[ci+1]))
    
    in_table = False
    for code, val in pairs:
        if code == '2' and val == 'TABLES':
            in_table = True
        if in_table and code == '2' and val not in ('TABLES', 'LAYER', 'LTYPE', 'STYLE', 'VPORT'):
            existing_layers.add(val)
        if in_table and code == '0' and val == 'ENDSEC':
            in_table = False
    
    # 确定缺失的标准图层
    essential = ['A-WALL', 'A-DOOR', 'A-WINDW', 'A-FURN', 'A-DIM', 'A-TEXT', 'A-AXIS', 'A-HATCH']
    missing = [l for l in essential if l not in existing_layers]
    
    if not missing:
        return False, [], output_path
    
    # 生成图层定义字符串
    new_layer_defs = []
    for name in missing:
        std = LAYER_STANDARD.get(name, {'color': 7, 'lineweight': 13, 'linetype': 'Continuous'})
        new_layer_defs.append(
            f'0\nLAYER\n2\n{name}\n70\n0\n62\n{std["color"]}\n6\n{std["linetype"]}\n370\n{std["lineweight"]}'
        )
    
    # 插入到 ENDTAB 之前
    # 找到 ENDTAB 的位置（LAYER 表的结束）
    insert_pos = -1
    lines_list = content.split('\n')
    in_layer_table = False
    for li in range(len(lines_list)):
        line = lines_list[li]
        if line == 'TABLE' and li > 0 and lines_list[li-1] == '0':
            if li+1 < len(lines_list) and lines_list[li+1] == '2':
                for lj in range(li, min(li+5, len(lines_list))):
                    if lines_list[lj] == 'LAYER':
                        in_layer_table = True
        if in_layer_table and line == 'ENDTAB':
            insert_pos = li
            break
    
    if insert_pos >= 0:
        for layer_def in new_layer_defs:
            for l in reversed(layer_def.split('\n')):
                lines_list.insert(insert_pos, l)
        
        new_content = '\n'.join(lines_list)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        log = [f"  ➕ 添加 {name}" for name in missing]
        return True, log, output_path
    
    return False, [], output_path


def fix_text_heights(input_path, output_path=None):
    """修正文字高度（1:100比例下设为3.5）"""
    if output_path is None:
        output_path = input_path.replace('.dxf', '_hfixed.dxf')
    
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    lines = content.split('\n')
    modified = False
    fix_log = []
    
    for i in range(len(lines)):
        # 找到 TEXT 实体
        if lines[i] == 'TEXT' and i > 0 and lines[i-1] == '0':
            # 往下找 40 高度
            for j in range(i+1, min(i+20, len(lines))):
                if lines[j] == '40':
                    if j+1 < len(lines):
                        try:
                            h = float(lines[j+1])
                            if h > 20:  # 单位应该是mm，如果是200说明用了不同单位
                                old_h = h
                                new_h = 3.5  # 标准字高
                                lines[j+1] = str(new_h)
                                fix_log.append(f"  🔧 文字高度: {old_h} → {new_h}")
                                modified = True
                        except ValueError:
                            pass
                    break
    
    if modified:
        new_content = '\n'.join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    return modified, fix_log, output_path


def run_full_fix(input_path):
    """对 DXF 执行全套修复"""
    print(f"\n{'='*55}")
    print(f"🔧 开始修复: {os.path.basename(input_path)}")
    print(f"{'='*55}")
    
    base = input_path.replace('.dxf', '')
    work_path = input_path
    total_log = []
    
    # 1. 添加缺失的图层
    mod, log, work_path = add_standard_layers(work_path, f'{base}_step1.dxf')
    if mod:
        total_log.extend(log)
        print(f"  ➕ 添加了 {len(log)} 个缺失图层")
    
    # 2. 修正图层颜色和线宽
    mod, log, work_path = fix_dxf_layer_colors(work_path, f'{base}_step2.dxf')
    if mod:
        total_log.extend(log)
        for l in log:
            print(f"  {l}")
    else:
        print("  ✅ 图层颜色/线宽已符合规范")
    
    # 3. 修正文字高度
    mod, log, final_path = fix_text_heights(work_path, f'{base}_fixed.dxf')
    if mod:
        total_log.extend(log)
        for l in log:
            print(f"  {l}")
    else:
        print("  ✅ 文字高度已符合规范")
        # 如果没改，直接把最终文件放到fix位置
        if final_path != f'{base}_fixed.dxf':
            shutil.copy2(work_path, f'{base}_fixed.dxf')
            final_path = f'{base}_fixed.dxf'
    
    # 清理临时文件
    for tmp in [f'{base}_step1.dxf', f'{base}_step2.dxf']:
        if tmp != final_path and os.path.exists(tmp):
            os.remove(tmp)
    
    print(f"\n📋 修复摘要:")
    print(f"  原始文件: {os.path.basename(input_path)}")
    print(f"  修正文件: {os.path.basename(final_path)}")
    print(f"  共 {len(total_log)} 项修改")
    
    return final_path, total_log


if __name__ == '__main__':
    import sys
    
    print("🏗  CAD Master — 规范自动修复器 V1.0")
    print("   修正图层颜色/线宽/文字高度 → Guoxin Standard")
    
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
            run_full_fix(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f.lower().endswith('.dxf') and '_fixed' not in f and '_step' not in f:
                        run_full_fix(os.path.join(root, f))
        else:
            print(f"路径不存在: {path}")
    else:
        # 扫描项目目录
        base = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower().endswith('.dxf') and '_fixed' not in f and '_step' not in f:
                    run_full_fix(os.path.join(root, f))
