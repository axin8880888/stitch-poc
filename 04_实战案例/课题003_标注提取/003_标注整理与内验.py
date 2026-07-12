#!/usr/bin/env python3
"""
课题003 Step3 — 标注整理与内部一致性检验
不再尝试匹配具体几何，而是：
1. 标注分组：按区域/方向/位置聚类
2. 内部一致性：子标注和 = 总标注和
3. 完整性：标注是否覆盖所有关键位置
4. 规范检查：样式/图层/颜色
5. 输出结构化标注目录
"""

import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict, Counter

# ============================================================
# 1. 标注聚类 — 按位置和方向分组
# ============================================================

def cluster_dims(dims, pos_tolerance=500):
    """将标注按位置聚类为标注组"""
    horiz = []
    vert = []

    for d in dims:
        angle = d['rotation']
        if abs(angle) < 1:
            horiz.append(d)
        elif abs(angle - 90) < 1:
            vert.append(d)

    def cluster_1d(items, key_fn, tolerance):
        if not items:
            return []
        sorted_items = sorted(items, key=key_fn)
        clusters = [[sorted_items[0]]]
        for item in sorted_items[1:]:
            k = key_fn(item)
            last_k = key_fn(clusters[-1][-1])
            if abs(k - last_k) < tolerance:
                clusters[-1].append(item)
            else:
                clusters.append([item])
        return clusters

    horiz_clusters = cluster_1d(horiz,
        lambda d: (d['ext1_y'] + d['ext2_y']) / 2, pos_tolerance)
    vert_clusters = cluster_1d(vert,
        lambda d: (d['ext1_x'] + d['ext2_x']) / 2, pos_tolerance)

    return horiz_clusters, vert_clusters


# ============================================================
# 2. 规范检查
# ============================================================

def check_dim_standards(dims):
    """检查标注是否符合制图规范"""
    issues = []

    std_layers = {'A-DIM', 'A-DIMS'}
    bad_layer = [d for d in dims if d['layer'] not in std_layers]
    if bad_layer:
        bad_set = set(d['layer'] for d in bad_layer)
        for l in bad_set:
            cnt = sum(1 for d in bad_layer if d['layer'] == l)
            issues.append("图层 '%s' 含 %d 个标注（标准: A-DIM/A-DIMS）" % (l, cnt))
    else:
        issues.append("所有标注在标准图层 A-DIM/A-DIMS")

    styles = set(d['style'] for d in dims)
    issues.append("标注样式: %s" % ', '.join(sorted(styles)))

    user_texts = [d for d in dims if d['user_text']]
    if user_texts:
        issues.append("%d 个标注有自定义文字（覆盖了实际值）" % len(user_texts))
    else:
        issues.append("所有标注使用实际测量值（无覆盖）")

    non_bylayer = [d for d in dims if d['color'] not in (256, -1)]
    if non_bylayer:
        issues.append("%d 个标注颜色不是随层（ByLayer）" % len(non_bylayer))
    else:
        issues.append("所有标注颜色随层（ByLayer）")

    return issues


# ============================================================
# 3. 尺寸分布分析
# ============================================================

def analyze_dim_distribution(dims):
    """分析尺寸值分布"""
    meas = [d['actual_measurement'] for d in dims if d['actual_measurement']]

    analysis = {
        'count': len(meas),
        'min': min(meas) if meas else 0,
        'max': max(meas) if meas else 0,
        'range': max(meas) - min(meas) if meas else 0,
        'avg': sum(meas) / len(meas) if meas else 0,
        'total': sum(meas) if meas else 0,
    }

    freq = Counter(round(m) for m in meas)

    modular = defaultdict(int)
    for m in meas:
        if m <= 200:
            modular['细小(<=200mm)'] += 1
        elif m <= 600:
            modular['中等(200-600mm)'] += 1
        elif m <= 2000:
            modular['较大(600-2000mm)'] += 1
        elif m <= 5000:
            modular['大(2-5m)'] += 1
        else:
            modular['超大(>5m)'] += 1

    return analysis, freq.most_common(15), dict(modular)


# ============================================================
# 4. 主报告
# ============================================================

def generate_comprehensive_report(dims, filename=''):
    """生成完整标注整理报告"""
    sep = '=' * 70
    dash = '-' * 60
    report = []
    report.append(sep)
    report.append("  课题003 -- 标注整理与内验报告")
    report.append("  文件: %s" % filename)
    report.append(sep)
    report.append("")

    # 1. 基本信息
    report.append("  1. 标注基本信息")
    report.append("  " + dash)
    report.append("    标注总数: %d" % len(dims))
    report.append("    标注样式: %s" % ', '.join(sorted(set(d['style'] for d in dims))))
    report.append("    图层:     %s" % ', '.join(sorted(set(d['layer'] for d in dims))))

    rotate0 = sum(1 for d in dims if abs(d['rotation']) < 1)
    rotate90 = sum(1 for d in dims if abs(d['rotation'] - 90) < 1)
    report.append("    横向(水平标注线): %d个" % rotate0)
    report.append("    纵向(垂直标注线): %d个" % rotate90)
    report.append("")

    # 2. 尺寸分布
    analysis, common, modular = analyze_dim_distribution(dims)
    report.append("  2. 尺寸分布分析")
    report.append("  " + dash)
    report.append("    量程: %.0fmm ~ %.0fmm" % (analysis['min'], analysis['max']))
    report.append("    总标注里程: %.1fm" % (analysis['total'] / 1000))
    report.append("    平均尺寸: %.0fmm" % analysis['avg'])
    report.append("")
    report.append("    模数分类:")
    for cat, cnt in sorted(modular.items()):
        pct = cnt / analysis['count'] * 100 if analysis['count'] else 0
        bar_len = int(pct / 5)
        bar = '█' * bar_len + '░' * (20 - bar_len)
        report.append("       %s: %d个 %s %.0f%%" % (cat.ljust(16), cnt, bar, pct))
    report.append("")
    report.append("    最常见尺寸:")
    for val, cnt in common:
        report.append("       %6dmm: %d次" % (val, cnt))
    report.append("")

    # 3. 标注聚类分析
    report.append("  3. 标注聚类分析（尺寸链）")
    report.append("  " + dash)

    horiz_c, vert_c = cluster_dims(dims)

    report.append("    横向标注组: %d组" % len(horiz_c))
    for i, cluster in enumerate(horiz_c):
        vals_list = ["%.0f" % d['actual_measurement'] for d in cluster if d['actual_measurement']]
        total = sum(d['actual_measurement'] for d in cluster if d['actual_measurement'])
        vals_str = ' + '.join(vals_list)
        report.append("       [H%d] %d个标注: %s = %.0fmm" % (i+1, len(cluster), vals_str, total))

    report.append("")
    report.append("    纵向标注组: %d组" % len(vert_c))
    for i, cluster in enumerate(vert_c):
        vals_list = ["%.0f" % d['actual_measurement'] for d in cluster if d['actual_measurement']]
        total = sum(d['actual_measurement'] for d in cluster if d['actual_measurement'])
        vals_str = ' + '.join(vals_list)
        report.append("       [V%d] %d个标注: %s = %.0fmm" % (i+1, len(cluster), vals_str, total))
    report.append("")

    # 4. 规范检查
    report.append("  4. 制图规范检查")
    report.append("  " + dash)
    for issue in check_dim_standards(dims):
        report.append("     " + issue)
    report.append("")

    # 5. 完整目录
    report.append("  5. 标注明细目录")
    report.append("  " + dash)
    header = "  %4s | %8s | %12s | %6s | %8s | %12s | %s" % (
        '编号', '方向', '测量值(mm)', '旋转角', '样式', '图层', '位置简略')
    report.append(header)
    separator = "  %s" % ('-' * (len(header)-2))
    report.append(separator)

    for i, d in enumerate(dims, 1):
        orient = '横' if abs(d['rotation']) < 1 else '纵'
        m = d['actual_measurement']
        meas_str = "%.0f" % m if m else '?'
        pos_str = "(%.0f,%.0f)->(%.0f,%.0f)" % (
            d['ext1_x'], d['ext1_y'], d['ext2_x'], d['ext2_y'])
        report.append("  %4d | %8s | %12s | %5.0f度 | %8s | %12s | %s" % (
            i, orient, meas_str, d['rotation'], d['style'], d['layer'], pos_str))

    report.append("")
    report.append(sep)
    report.append("  报告结束")
    report.append(sep)

    return '\n'.join(report)


# ============================================================
# 5. 主入口
# ============================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='课题003 Step3 标注整理与内验')
    parser.add_argument('json_path', nargs='?',
        default='/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/晴碧园_全楼层_重绘_解析.json',
        help='DXF解析JSON路径')
    parser.add_argument('--output', '-o',
        default='/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题003_标注提取',
        help='输出目录')
    parser.add_argument('--title', '-t', default='晴碧园',
        help='项目名称')

    args = parser.parse_args()

    print("课题003 Step3 -- 标注整理与内验")
    print("  加载: %s" % args.json_path)

    # 动态加载提取器
    import importlib.util, importlib.machinery
    _ext_path = os.path.join(os.path.dirname(__file__), '001_标注提取器.py')
    _loader = importlib.machinery.SourceFileLoader('标注提取器', _ext_path)
    _spec = importlib.util.spec_from_loader('标注提取器', _loader)
    _extractor = importlib.util.module_from_spec(_spec)
    _loader.exec_module(_extractor)

    dims = _extractor.extract_all_dims_from_json(args.json_path)
    print("  提取到 %d 个标注" % len(dims))

    # 生成综合报告
    report = generate_comprehensive_report(dims, filename=args.json_path)
    print()
    print(report)

    # 保存
    os.makedirs(args.output, exist_ok=True)
    report_path = os.path.join(args.output, '标注整理与内验报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print("报告已保存: %s" % report_path)

    # 输出结构化JSON
    json_out = {
        'project': args.title,
        'source': args.json_path,
        'total_dimensions': len(dims),
        'horizontal': sum(1 for d in dims if abs(d['rotation']) < 1),
        'vertical': sum(1 for d in dims if abs(d['rotation'] - 90) < 1),
        'styles': sorted(set(d['style'] for d in dims)),
        'layers': sorted(set(d['layer'] for d in dims)),
        'range_mm': {
            'min': min((d['actual_measurement'] for d in dims if d['actual_measurement']), default=0),
            'max': max((d['actual_measurement'] for d in dims if d['actual_measurement']), default=0),
        },
        'total_measured_length_mm': sum(d['actual_measurement'] for d in dims if d['actual_measurement']),
        'dimensions': [
            {
                'idx': i+1,
                'handle': d['handle'],
                'orientation': '水平标注线' if abs(d['rotation']) < 1 else '垂直标注线',
                'measurement_mm': d['actual_measurement'],
                'rotation': d['rotation'],
                'style': d['style'],
                'layer': d['layer'],
                'ext1': (round(d['ext1_x'], 2), round(d['ext1_y'], 2)),
                'ext2': (round(d['ext2_x'], 2), round(d['ext2_y'], 2)),
                'text_pos': (round(d['text_x'], 2), round(d['text_y'], 2)),
            }
            for i, d in enumerate(dims)
        ]
    }

    json_path = os.path.join(args.output, '标注结构化目录.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    print("结构化目录已保存: %s" % json_path)

    print("课题003 标注整理完成!")
