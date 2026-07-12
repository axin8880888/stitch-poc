#!/usr/bin/env python3
"""
课题005 — 布局与视口分析
======================
1. 解析 DXF LAYOUT 定义（OBJECTS段）
2. 解析 VIEWPORT 实体（BLOCKS段）
3. 建立: 布局→视口→比例→模型空间可见范围 映射
4. 生成布局结构报告

DXF 布局结构：
  BLOCKS段: *Paper_Space, *Paper_Space0 等块 → 包含 VIEWPORT 实体
  OBJECTS段: LAYOUT 对象 → 打印设置、视口配置、比例
"""

import os, sys, json, re
from collections import defaultdict

OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题005_布局视口'


# ============================================================
# 1. 原始 DXF 解析器（按段提取）
# ============================================================

def parse_sections(filepath):
    """将 DXF 文件按 SECTION 分段"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    lines = content.split('\n')
    sections = {}
    current_sec = None
    sec_start = 0
    
    for i, line in enumerate(lines):
        s = line.strip()
        if s == 'SECTION':
            # 找到段名
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip() == '2' and j+1 < len(lines):
                    sec_name = lines[j+1].strip()
                    current_sec = sec_name
                    sec_start = i
                    break
        elif s == 'ENDSEC' and current_sec:
            sections[current_sec] = lines[sec_start:i+1]
            current_sec = None
    
    return sections, lines


def extract_block_entities(block_lines):
    """从 BLOCK 定义中提取 VIEWPORT 实体"""
    viewports = []
    i = 0
    n = len(block_lines)
    
    while i < n:
        s = block_lines[i].strip()
        if s == '0' and i+1 < n and block_lines[i+1].strip() == 'VIEWPORT':
            # 解析 VIEWPORT 实体
            vp = {'raw_start': i}
            i += 2
            while i < n:
                code = block_lines[i].strip()
                i += 1
                val = block_lines[i].strip() if i < n else ''
                
                if code == '0':  # 下一个实体
                    break
                
                if code.isdigit() or (code.startswith('-') and code[1:].isdigit()):
                    try:
                        c = int(code)
                        if c in (5, 8, 6, 100, 102, 330, 360, 1, 2):
                            vp[c] = val
                        elif c in (10, 20, 30, 40, 41, 12, 22, 13, 23, 14, 24, 15, 25,
                                   16, 26, 36, 17, 27, 37, 42, 43, 48, 62, 69, 70, 71):
                            vp[c] = float(val) if '.' in val else int(val)
                        else:
                            vp[c] = val
                    except (ValueError, IndexError):
                        pass
                i += 1
            
            if vp:
                viewports.append(vp)
        else:
            i += 1
    
    return viewports


def extract_layout_objects(object_lines):
    """从 OBJECTS 段提取 LAYOUT 定义"""
    layouts = []
    i = 0
    n = len(object_lines)
    
    while i < n:
        s = object_lines[i].strip()
        if s == '0' and i+1 < n and object_lines[i+1].strip() == 'LAYOUT':
            layout = {}
            i += 2
            while i < n:
                code = object_lines[i].strip()
                i += 1
                val = object_lines[i].strip() if i < n else ''
                
                if code == '0':
                    break
                
                if code == '1':  # 布局名
                    layout['name'] = val
                
                if code.isdigit():
                    try:
                        c = int(code)
                        layout[c] = val
                        # 数字值转换
                        try:
                            layout[str(c)+'_n'] = float(val) if '.' in val else int(val)
                        except ValueError:
                            pass
                    except ValueError:
                        pass
                
                i += 1
            
            if layout:
                layouts.append(layout)
        else:
            i += 1
    
    return layouts


def extract_block_names(lines):
    """提取 BLOCKS 段中的所有块定义"""
    blocks = {}
    in_blocks = False
    in_block = False
    block_name = None
    block_start = 0
    
    for i, line in enumerate(lines):
        s = line.strip()
        if s == 'BLOCKS' and i > 0 and lines[i-1].strip() == '2':
            in_blocks = True
            continue
        if in_blocks and s == 'ENDSEC':
            in_blocks = False
            continue
        if in_blocks and s == 'BLOCK' and not in_block:
            in_block = True
            block_name = None
            block_start = i
            continue
        if in_block and s == 'ENDBLK':
            if block_name:
                blocks[block_name] = lines[block_start:i+1]
            in_block = False
            continue
        if in_block and s == '2' and block_name is None:
            if i+1 < len(lines):
                block_name = lines[i+1].strip()
    
    return blocks


# ============================================================
# 2. 布局分析器
# ============================================================

def analyze_layouts(filepath):
    """完整分析 DXF 布局结构"""
    sections, all_lines = parse_sections(filepath)
    
    result = {
        'file': os.path.basename(filepath),
        'sections': list(sections.keys()),
        'layouts': [],
        'blocks_with_viewports': [],
    }
    
    # 提取 LAYOUT 对象
    obj_lines = sections.get('OBJECTS', [])
    if obj_lines:
        layouts = extract_layout_objects(obj_lines)
        for layout in layouts:
            entry = {
                'name': layout.get('name', '?'),
                'handle': layout.get(5, '?'),
                'paper_width_mm': layout.get(44, None),
                'paper_height_mm': layout.get(45, None),
                'printer': layout.get(2, '(none)'),
                'plot_style': layout.get(7, '(none)'),
                'paper_size': layout.get(4, '(custom)'),
                'view_center_x': float(layout.get('46_n', 0)),
                'view_center_y': float(layout.get('47_n', 0)),
                'view_width_model': float(layout.get(48, 0)),
                'view_height_model': float(layout.get(49, 0)),
                'scale_numerator': float(layout.get(142, 1)),
            }
            # 计算大致比例
            pw = float(layout.get('44_n', 0))
            vw = float(layout.get(48, 0))
            if pw and vw and pw > 0 and vw > 0:
                entry['approx_scale'] = '1:%.0f' % round(vw / pw)
            else:
                entry['approx_scale'] = '?'
            
            result['layouts'].append(entry)
    
    # 提取 BLOCKS 中的 VIEWPORT
    blk_lines = sections.get('BLOCKS', [])
    if blk_lines:
        blocks = extract_block_names(all_lines)
        for blk_name, blk_content in sorted(blocks.items()):
            vps = extract_block_entities(blk_content)
            if vps:
                vp_list = []
                for vp in vps:
                    vp_info = {
                        'layer': vp.get(8, '0'),
                        'center_x': vp.get(10, 0),
                        'center_y': vp.get(20, 0),
                        'width': vp.get(40, 0),
                        'height': vp.get(41, 0),
                        'status': vp.get(69, 0),
                        'scale': vp.get(42, 1.0),
                        'color': vp.get(62, 256),
                    }
                    if vp_info['scale'] and vp_info['scale'] > 0:
                        vp_info['scale_str'] = '1:%.0f' % vp_info['scale']
                    else:
                        vp_info['scale_str'] = '?'
                    vp_list.append(vp_info)
                
                result['blocks_with_viewports'].append({
                    'block': blk_name,
                    'viewport_count': len(vp_list),
                    'viewports': vp_list,
                })
    
    return result


# ============================================================
# 3. 报告生成
# ============================================================

def generate_layout_report(analysis):
    """生成布局分析报告"""
    report = []
    sep = '=' * 65
    
    report.append(sep)
    report.append("  课题005 — 布局与视口分析报告")
    report.append("  文件: %s" % analysis['file'])
    report.append(sep)
    report.append("")
    report.append("  文件段: %s" % ', '.join(analysis['sections']))
    report.append("")
    
    # LAYOUT 对象
    report.append("  1. 布局定义 (LAYOUT Objects)")
    report.append("  " + '-' * 55)
    if analysis['layouts']:
        for layout in analysis['layouts']:
            report.append("    布局名: %s (handle: %s)" % (layout['name'], layout['handle']))
            report.append("      纸张: %s x %s mm (%s)" % (
                layout['paper_width_mm'], layout['paper_height_mm'], layout['paper_size']))
            report.append("      打印机: %s" % layout['printer'])
            report.append("      打印样式: %s" % layout['plot_style'])
            report.append("      视口中点: (%.1f, %.1f)" % (layout['view_center_x'], layout['view_center_y']))
            report.append("      模型空间视野: %.0f x %.0f" % (layout['view_width_model'], layout['view_height_model']))
            report.append("      标注比例: %s" % layout['approx_scale'])
            report.append("")
    else:
        report.append("    未找到 LAYOUT 定义")
    report.append("")
    
    # VIEWPORT 实体
    report.append("  2. 视口实体 (VIEWPORT in BLOCKS)")
    report.append("  " + '-' * 55)
    if analysis['blocks_with_viewports']:
        for block_entry in analysis['blocks_with_viewports']:
            report.append("    块: %s (%d 个视口)" % (block_entry['block'], block_entry['viewport_count']))
            for vp in block_entry['viewports']:
                report.append("      ├ 图层: %s | 中心: (%.1f, %.1f)" % (vp['layer'], vp['center_x'], vp['center_y']))
                report.append("      ├ 宽高: %.0f x %.0f" % (vp['width'], vp['height']))
                report.append("      ├ 比例: %s | 状态: %d" % (vp['scale_str'], vp['status']))
                report.append("      └ 颜色: %d" % vp['color'])
    else:
        report.append("    未找到 VIEWPORT 实体")
    report.append("")
    
    # 分析总结
    report.append("  3. 分析总结")
    report.append("  " + '-' * 55)
    total_vp = sum(b['viewport_count'] for b in analysis['blocks_with_viewports'])
    report.append("    LAYOUT 定义: %d" % len(analysis['layouts']))
    report.append("    VIEWPORT 总数: %d" % total_vp)
    report.append("    含视口的块数: %d" % len(analysis['blocks_with_viewports']))
    report.append("")
    
    report.append(sep)
    report.append("  报告结束")
    report.append(sep)
    
    return '\n'.join(report)


# ============================================================
# 4. SVG 布局可视化
# ============================================================

def render_layout_svg(analysis, output_path):
    """生成布局 - 视口关系 SVG"""
    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">')
    lines.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    lines.append('<text x="400" y="25" text-anchor="middle" fill="#e0e0e0" font-size="14" font-family="monospace">布局与视口结构 — %s</text>' % analysis['file'])
    
    y = 50
    for block_entry in analysis['blocks_with_viewports']:
        lines.append('<text x="20" y="%d" fill="#4fc3f7" font-size="13" font-family="monospace">块: %s</text>' % (y, block_entry['block']))
        y += 22
        
        for i, vp in enumerate(block_entry['viewports'][:10]):  # 最多显示10个
            color = '#81c784' if vp['status'] == 1 else '#e0e0e0'
            lines.append('<text x="40" y="%d" fill="%s" font-size="11" font-family="monospace">视口 #%d: layer=%s scale=%s center=(%.0f, %.0f) size=%.0fx%.0f</text>' % (
                y, color, i+1, vp['layer'], vp['scale_str'], vp['center_x'], vp['center_y'], vp['width'], vp['height']))
            y += 18
        
        y += 8
    
    # 布局列表
    if analysis['layouts']:
        y = max(y, 250)
        lines.append('<text x="20" y="%d" fill="#ffb74d" font-size="13" font-family="monospace">布局定义:</text>' % y)
        y += 22
        for layout in analysis['layouts']:
            lines.append('<text x="40" y="%d" fill="#e0e0e0" font-size="11" font-family="monospace">%s: %s 纸张=%.0fx%.0fmm 比例=%s</text>' % (
                y, layout['name'], layout['paper_size'], 
                float(layout['paper_width_mm'] or 0), 
                float(layout['paper_height_mm'] or 0),
                layout['approx_scale']))
            y += 18
    
    lines.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path


# ============================================================
# 5. 主入口
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='课题005 布局与视口分析')
    parser.add_argument('input_path', nargs='?',
        default='/storage/emulated/0/设计/DXF学习/晴碧园晶园26栋.dxf')
    parser.add_argument('--output-dir', '-o', default=OUT_DIR)
    parser.add_argument('--compare', '-c', action='store_true',
        help='对比多文件')
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.compare:
        # 对比两个主要文件
        files = [
            '/storage/emulated/0/设计/DXF学习/晴碧园晶园26栋.dxf',
            '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf',
        ]
        for fpath in files:
            if not os.path.isfile(fpath):
                print("跳过: %s" % fpath)
                continue
            print("分析: %s" % os.path.basename(fpath))
            analysis = analyze_layouts(fpath)
            report = generate_layout_report(analysis)
            print(report)
            
            # 保存
            basename = os.path.splitext(os.path.basename(fpath))[0]
            rpath = os.path.join(args.output_dir, basename + '_布局报告.txt')
            with open(rpath, 'w', encoding='utf-8') as f:
                f.write(report)
            print("报告: %s" % rpath)
            
            svg_path = os.path.join(args.output_dir, basename + '_布局.svg')
            render_layout_svg(analysis, svg_path)
            print("SVG: %s" % svg_path)
            
            print()
    else:
        if not os.path.isfile(args.input_path):
            print("文件不存在: %s" % args.input_path)
            return
        
        print("课题005 — 布局与视口分析")
        print("  文件: %s" % os.path.basename(args.input_path))
        print()
        
        analysis = analyze_layouts(args.input_path)
        report = generate_layout_report(analysis)
        print(report)
        
        # 保存
        basename = os.path.splitext(os.path.basename(args.input_path))[0]
        rpath = os.path.join(args.output_dir, basename + '_布局报告.txt')
        with open(rpath, 'w', encoding='utf-8') as f:
            f.write(report)
        print("报告: %s" % rpath)
        
        svg_path = os.path.join(args.output_dir, basename + '_布局.svg')
        render_layout_svg(analysis, svg_path)
        print("SVG: %s" % svg_path)
        
        # 保存 JSON
        jpath = os.path.join(args.output_dir, basename + '_布局数据.json')
        with open(jpath, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print("JSON: %s" % jpath)
        
        print()
        print("课题005 完成!")


if __name__ == '__main__':
    main()
