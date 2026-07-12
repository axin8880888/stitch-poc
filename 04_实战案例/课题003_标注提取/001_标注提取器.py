#!/usr/bin/env python3
"""
课题003 — 尺寸标注提取与整理
=======================
DIMENSION 提取 + 分类 + 计算 + 验证 + 报告

DXF DIMENSION 关键组码:
  2   = 匿名块名 (*DXXXX)
  3   = 标注样式名
  10/20/30 = 定义点（标注线位置）
  11/21/31 = 文字中点
  13/23/33 = 第一条延伸线端点
  14/24/34 = 第二条延伸线端点
  50   = 旋转角度（度）
  52   = 角度标注的弧角度
  70   = 类型标志（位运算）
  71   = 文字附着点 (1=上左 ... 5=中)
  72   = 文字流向 (0=水平对齐, 1=随标注)
  1    = 用户自定义文字（空=使用实测值）
  42   = 实测值（不总是存在）
  41   = 全局比例
  53   = 文字旋转
"""

import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../05_自动化'))
from collections import Counter, defaultdict

# ============================================================
# 1. 标注解释器
# ============================================================

def decode_rotated_dim(dim, infer_from_geometry=True):
    """
    解析 RotatedDimension（旋转标注）
    
    返回结构化字典
    """
    result = {
        'handle': dim.get('code_5', ''),
        'block': dim.get('code_2', ''),
        'style': dim.get('code_3', ''),
        'layer': dim.get('layer', '0'),
        'color': int(dim.get('code_62', 256)),
        'linetype': dim.get('code_6', 'BYLAYER'),
    }
    
    # 定义点 (10,20,30) - 标注线位置
    result['def_x'] = float(dim.get('code_10', 0))
    result['def_y'] = float(dim.get('code_20', 0))
    
    # 文字中点 (11,21,31)
    result['text_x'] = float(dim.get('code_11', 0))
    result['text_y'] = float(dim.get('code_21', 0))
    
    # 延伸线端点 (13,23) 和 (14,24)
    result['ext1_x'] = float(dim.get('code_13', 0))
    result['ext1_y'] = float(dim.get('code_23', 0))
    result['ext2_x'] = float(dim.get('code_14', 0))
    result['ext2_y'] = float(dim.get('code_24', 0))
    
    # 旋转角度
    result['rotation'] = float(dim.get('code_50', 0))
    
    # 标注类型
    type_code = int(dim.get('code_70', 0))
    result['type_code'] = type_code
    result['is_rotated'] = bool(type_code & 32)
    result['is_aligned'] = bool(type_code & 64)
    result['is_angular'] = bool(type_code & 1)
    result['is_ordinate'] = bool(type_code & 8)
    
    # 文字设置
    result['user_text'] = dim.get('code_1', '')
    result['text_attachment'] = int(dim.get('code_71', 0))
    result['text_flow'] = int(dim.get('code_72', 0))
    result['text_rotation'] = float(dim.get('code_53', 0))
    
    # 用户文本
    result['user_text'] = dim.get('code_1', '').strip()
    
    # 计算实际测量值
    if 'code_42' in dim:
        result['actual_measurement'] = float(dim['code_42'])
    elif infer_from_geometry:
        result['actual_measurement'] = compute_measurement(result)
    else:
        result['actual_measurement'] = None
    
    # 判定方向
    angle = result['rotation']
    # 旋转标注: 测量方向垂直于标注线方向
    # 标注线沿角度方向，测量沿 angle-90°（或+90°）
    meas_angle = (angle + 90) % 360
    
    # 判定为纵向标注还是横向标注
    if abs(meas_angle - 0) < 45 or abs(meas_angle - 360) < 45 or abs(meas_angle - 180) < 45:
        result['orientation'] = '横向 (水平距离)'
    elif abs(meas_angle - 90) < 45 or abs(meas_angle - 270) < 45:
        result['orientation'] = '纵向 (垂直距离)'
    else:
        result['orientation'] = f'斜向 ({meas_angle:.1f}°)'
    
    # 测量方向描述
    if abs(angle - 0) < 1:
        result['dim_line_dir'] = '水平'
    elif abs(angle - 90) < 1:
        result['dim_line_dir'] = '垂直'
    else:
        result['dim_line_dir'] = f'{angle:.1f}°'
    
    return result


def compute_measurement(dim_info):
    """
    计算 RotatedDimension 的实际距离
    
    延伸线端点 (13,23) → (14,24)
    投影到旋转角度方向
    """
    dx = dim_info['ext2_x'] - dim_info['ext1_x']
    dy = dim_info['ext2_y'] - dim_info['ext1_y']
    angle_rad = math.radians(dim_info['rotation'])
    
    # 投影到标注线方向 (角度方向)
    direction = (math.cos(angle_rad), math.sin(angle_rad))
    projection = dx * direction[0] + dy * direction[1]
    
    return abs(round(projection, 2))


def format_dim_summary(dim):
    """格式化标注摘要"""
    meas = dim['actual_measurement']
    
    # 圆整到标准值
    if meas:
        rounded = round(meas)
        match = '✓' if abs(meas - rounded) < 0.5 else '≈'
    else:
        rounded = '?'
        match = '?'
    
    return (f"  [{dim['handle']}] {dim['orientation']:12s} | "
            f"线方向:{dim['dim_line_dir']:4s} | "
            f"测量值={meas:>8.0f}mm ({match}) | "
            f"样式={dim['style']} | 图层={dim['layer']}")


# ============================================================
# 2. 批量提取
# ============================================================

def extract_all_dims_from_json(json_path):
    """从解析好的 JSON 提取所有标注"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    raw_dims = [e for e in data['entities'] if e['type'] == 'DIMENSION']
    
    decoded = []
    for d in raw_dims:
        info = decode_rotated_dim(d)
        decoded.append(info)
    
    return decoded


# ============================================================
# 3. 分析报告
# ============================================================

def analyze_dims(dims, filename=''):
    """生成标注分析报告"""
    report = []
    report.append(f"{'='*70}")
    report.append(f"  课题003 — 尺寸标注提取报告")
    report.append(f"  文件: {filename}")
    report.append(f"{'='*70}")
    report.append("")
    
    # 基本信息
    report.append(f"  标注总数: {len(dims)}")
    report.append(f"  标注样式: {sorted(set(d['style'] for d in dims))}")
    report.append(f"  图层: {sorted(set(d['layer'] for d in dims))}")
    report.append("")
    
    # 方向分布
    orientations = Counter(d['orientation'] for d in dims)
    report.append("  📐 方向分布:")
    for orient, cnt in orientations.most_common():
        report.append(f"    {orient}: {cnt}个")
    report.append("")
    
    # 旋转角度分布
    angles = Counter(d['rotation'] for d in dims)
    report.append("  🔄 旋转角度:")
    for angle in sorted(angles):
        report.append(f"    {angle}°: {angles[angle]}个")
    report.append("")
    
    # 量程分析
    measurements = sorted([d['actual_measurement'] for d in dims if d['actual_measurement']])
    if measurements:
        report.append(f"  📏 量程: {min(measurements):.0f}mm ~ {max(measurements):.0f}mm")
        # 常见尺寸
        freq = Counter(round(m) for m in measurements)
        common = freq.most_common(10)
        report.append("  常见尺寸:")
        for size, cnt in common:
            report.append(f"    {size}mm: {cnt}次")
    report.append("")
    
    # 图层合规检查（标准应为 A-DIM 或 A-DIMS）
    report.append("  🏷️ 图层检查:")
    std_layers = {'A-DIM', 'A-DIMS'}
    bad_layers = [d for d in dims if d['layer'] not in std_layers]
    if bad_layers:
        bad_set = set(d['layer'] for d in bad_layers)
        report.append(f"    ❌ {len(bad_layers)}个标注不在标准图层")
        for l in bad_set:
            cnt = sum(1 for d in dims if d['layer'] == l)
            report.append(f"       '{l}': {cnt}个标注")
    else:
        report.append("    ✅ 全部标注在标准图层 A-DIM/A-DIMS")
    report.append("")
    
    # 全部标注明细
    report.append("  📋 所有标注明细:")
    report.append(f"  {'编号':>4s} │ {'方向':12s} │ {'线方向':6s} │ {'测量值(mm)':>12s} │ {'样式':10s} │ {'图层':10s}")
    report.append(f"  {'─'*4}┼{'─'*13}┼{'─'*7}┼{'─'*14}┼{'─'*11}┼{'─'*11}")
    
    for i, d in enumerate(dims, 1):
        m = d['actual_measurement']
        meas_str = f"{m:.0f}" if m else "?"
        report.append(f"  {i:>4d} │ {d['orientation']:12s} │ {d['dim_line_dir']:6s} │ {meas_str:>12s} │ {d['style']:10s} │ {d['layer']:10s}")
    
    report.append("")
    report.append(f"{'='*70}")
    report.append(f"  报告结束")
    report.append(f"{'='*70}")
    
    return '\n'.join(report)


# ============================================================
# 4. SVG 可视化（标注图）
# ============================================================

def render_dim_svg(dims, output_path, title='尺寸标注可视化'):
    """生成标注分布 SVG"""
    
    # 收集所有点
    all_x = []
    all_y = []
    for d in dims:
        all_x.extend([d['ext1_x'], d['ext2_x'], d['text_x'], d['def_x']])
        all_y.extend([d['ext1_y'], d['ext2_y'], d['text_y'], d['def_y']])
    
    if not all_x:
        print("无标注数据")
        return
    
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    
    # 加边距
    margin = (max_x - min_x) * 0.1 or 100
    margin_y = (max_y - min_y) * 0.1 or 100
    
    # SVG 尺寸
    svg_w = 1200
    svg_h = 800
    
    # 坐标映射
    def transform(x, y):
        px = (x - min_x + margin) / (max_x - min_x + 2 * margin) * (svg_w - 40) + 20
        py = (max_y + margin_y - y) / (max_y - min_y + 2 * margin_y) * (svg_h - 40) + 20
        # Flip Y
        sx = px
        sy = svg_h - py
        return sx, sy
    
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">')
    lines.append(f'<rect width="100%" height="100%" fill="#1a1a2e"/>')
    lines.append(f'<text x="{svg_w//2}" y="25" text-anchor="middle" fill="#e0e0e0" font-size="16" font-family="monospace">{title}</text>')
    
    # 绘制每个标注
    for i, d in enumerate(dims):
        # 延伸线1
        x1, y1 = transform(d['ext1_x'], d['ext1_y'])
        xd, yd = transform(d['def_x'], d['def_y'])
        x2, y2 = transform(d['ext2_x'], d['ext2_y'])
        xt, yt = transform(d['text_x'], d['text_y'])
        
        meas = d['actual_measurement']
        label = f"{meas:.0f}" if meas else "?"
        color = '#4fc3f7' if d['layer'] in ('A-DIM','A-DIMS') else '#ff7043'
        
        # 延伸线1
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{xd:.1f}" y2="{yd:.1f}" stroke="{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>')
        # 延伸线2
        lines.append(f'<line x1="{x2:.1f}" y1="{y2:.1f}" x2="{xd:.1f}" y2="{yd:.1f}" stroke="{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>')
        # 标注线
        lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="2" opacity="0.8"/>')
        # 箭头
        lines.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="2.5" fill="{color}"/>')
        lines.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="2.5" fill="{color}"/>')
        # 标注文字
        lines.append(f'<text x="{xt:.1f}" y="{yt:.1f}" text-anchor="middle" fill="white" font-size="11" font-family="monospace">{label}</text>')
    
    # 图例
    lines.append(f'<rect x="20" y="{svg_h-55}" width="20" height="12" fill="#4fc3f7" rx="2"/>')
    lines.append(f'<text x="45" y="{svg_h-45}" fill="#ccc" font-size="11">标准图层 (A-DIM/A-DIMS)</text>')
    lines.append(f'<rect x="20" y="{svg_h-35}" width="20" height="12" fill="#ff7043" rx="2"/>')
    lines.append(f'<text x="45" y="{svg_h-25}" fill="#ccc" font-size="11">非标准图层</text>')
    
    lines.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"  SVG 可视化已保存: {output_path}")


# ============================================================
# 5. 主入口
# ============================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='课题003 — 尺寸标注提取与整理')
    parser.add_argument('json_path', nargs='?',
                        default='/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/晴碧园_全楼层_重绘_解析.json',
                        help='DXF解析JSON路径')
    parser.add_argument('--output', '-o', default='../课题003_标注提取',
                        help='输出目录')
    parser.add_argument('--title', '-t', default='晴碧园全楼层 — 尺寸标注可视化',
                        help='SVG标题')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')
    
    args = parser.parse_args()
    
    print(f"📐 课题003 — 尺寸标注提取与整理")
    print(f"")
    
    # 解析
    dims = extract_all_dims_from_json(args.json_path)
    print(f"✅ 提取到 {len(dims)} 个标注")
    
    # 报告
    report = analyze_dims(dims, filename=args.json_path)
    print(f"\n{report}")
    
    # 保存报告
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), args.output))
    os.makedirs(out_dir, exist_ok=True)
    
    report_path = os.path.join(out_dir, '标注提取报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📄 报告已保存: {report_path}")
    
    # SVG 可视化
    svg_path = os.path.join(out_dir, '标注可视化.svg')
    render_dim_svg(dims, svg_path, title=args.title)
    
    # JSON 结构化输出
    json_out = []
    for d in dims:
        json_out.append({
            'handle': d['handle'],
            'layer': d['layer'],
            'style': d['style'],
            'orientation': d['orientation'],
            'dim_line_dir': d['dim_line_dir'],
            'measurement_mm': d['actual_measurement'],
            'rotation': d['rotation'],
            'type_code': d['type_code'],
            'ext1': (d['ext1_x'], d['ext1_y']),
            'ext2': (d['ext2_x'], d['ext2_y']),
            'text_pos': (d['text_x'], d['text_y']),
            'def_point': (d['def_x'], d['def_y']),
        })
    
    json_path = os.path.join(out_dir, '标注数据.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    print(f"📊 结构数据已保存: {json_path}")
    
    print(f"\n✅ 课题003 标注提取完成!")
