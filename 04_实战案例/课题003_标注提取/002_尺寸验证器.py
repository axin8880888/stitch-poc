#!/usr/bin/env python3
"""
课题003 Step2 — 尺寸验证器
======================
验证提取的标注值是否与实际几何尺寸匹配

思路：
1. 找到每个标注附近的 LINE/LWPOLYLINE
2. 比较标注值 vs 实际几何距离
3. 报告偏差和异常
"""

import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../05_自动化'))
from collections import defaultdict

# ============================================================
# 1. 几何工具
# ============================================================

def point_dist(p1, p2):
    """两点距离"""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return math.sqrt(dx*dx + dy*dy)

def axis_dist(p1, p2):
    """x/y方向距离"""
    return abs(p1[0] - p2[0]), abs(p1[1] - p2[1])

def line_midpoint(line):
    """LINE中点"""
    return ((line[0][0] + line[1][0]) / 2, (line[0][1] + line[1][1]) / 2)

def line_length(line):
    """线段长度"""
    return point_dist(line[0], line[1])

def line_direction(line):
    """线段方向（度）"""
    dx = line[1][0] - line[0][0]
    dy = line[1][1] - line[0][1]
    return math.degrees(math.atan2(dy, dx)) % 360

def lines_are_parallel(angle1, angle2, tolerance=5):
    """两条线是否平行"""
    diff = abs((angle1 - angle2) % 360)
    return diff < tolerance or abs(diff - 180) < tolerance


# ============================================================
# 2. 标注与几何对比
# ============================================================

def load_geometry(json_path):
    """从解析JSON加载所有几何图元"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    lines = []
    lwpolylines = []
    
    for ent in data['entities']:
        etype = ent['type']
        layer = ent.get('layer', '0')
        
        # 跳过标注本身
        if etype == 'DIMENSION':
            continue
        
        if etype == 'LINE':
            x1 = float(ent.get('code_10', 0))
            y1 = float(ent.get('code_20', 0))
            x2 = float(ent.get('code_11', 0))
            y2 = float(ent.get('code_21', 0))
            lines.append({
                'type': 'LINE',
                'layer': layer,
                'p1': (x1, y1),
                'p2': (x2, y2),
                'length': point_dist((x1, y1), (x2, y2)),
                'angle': line_direction([(x1, y1), (x2, y2)]),
            })
        
        elif etype == 'LWPOLYLINE':
            # 读取顶点
            verts = []
            for i in range(100):
                kx = f'code_10_{i}' if i > 0 else 'code_10'
                ky = f'code_20_{i}' if i > 0 else 'code_20'
                if kx in ent and ky in ent:
                    verts.append((float(ent[kx]), float(ent[ky])))
                else:
                    break
            
            if len(verts) >= 2:
                for i in range(len(verts)):
                    p1 = verts[i]
                    p2 = verts[(i + 1) % len(verts)]
                    closed = int(ent.get('code_70', 0)) & 1
                    if not closed and i == len(verts) - 1:
                        break
                    lwpolylines.append({
                        'type': 'LWPOLYLINE',
                        'layer': layer,
                        'p1': p1,
                        'p2': p2,
                        'length': point_dist(p1, p2),
                        'angle': line_direction([p1, p2]),
                    })
    
    return lines, lwpolylines


def compute_dim_measurement(dim):
    """通过延伸线端点计算标注的实际测量距离"""
    dx = dim['ext2_x'] - dim['ext1_x']
    dy = dim['ext2_y'] - dim['ext1_y']
    angle_rad = math.radians(dim['rotation'])
    # 投影到测量方向（旋转+90°）
    meas_angle_rad = angle_rad + math.pi / 2
    proj = dx * math.cos(meas_angle_rad) + dy * math.sin(meas_angle_rad)
    return abs(round(proj, 2))


def validate_dimension_v2(dim, walls, tolerance=1.0):
    """
    验证标注值是否与墙线一致
    
    改进算法：
    1. 找出标注延伸线端点附近的墙线端点
    2. 在两个延伸线方向找最近的墙线
    3. 比较墙线距离 vs 标注值
    4. 特别关心 200mm(墙厚) 这类常见尺寸
    """
    meas = dim['actual_measurement']
    if not meas:
        return None
    
    ext1 = (dim['ext1_x'], dim['ext1_y'])
    ext2 = (dim['ext2_x'], dim['ext2_y'])
    rot = dim['rotation']
    dim_val = round(meas, 2)
    
    # 测量方向
    meas_angle = (rot + 90) % 360
    meas_rad = math.radians(meas_angle)
    meas_vec = (math.cos(meas_rad), math.sin(meas_rad))
    
    # 寻找在这对延伸线方向上投影长度与标注值接近的墙线
    matches = []
    for wall in walls:
        w_len = wall['length']
        if w_len < 10:
            continue
        
        # 墙线应该大致平行于测量方向
        if not lines_are_parallel(wall['angle'], meas_angle):
            continue
        
        # 检查墙线端点是否在延伸线附近
        for wall_end in [wall['p1'], wall['p2']]:
            for ext_end in [ext1, ext2]:
                d = point_dist(wall_end, ext_end)
                if d < 300:  # 端点距离容差
                    matches.append({
                        'length': w_len,
                        'layer': wall['layer'],
                        'end_dist': d,
                    })
                    break
    
    if matches:
        # 取最近匹配
        matches.sort(key=lambda m: m['end_dist'])
        best = matches[0]
        geo_val = round(best['length'], 2)
        diff = round(abs(dim_val - geo_val), 2)
        return {
            'dim_measurement': dim_val,
            'geo_measurement': geo_val,
            'difference': diff,
            'tolerance_ok': diff <= tolerance,
            'matched_layer': best['layer'],
            'end_dist': round(best['end_dist'], 0),
        }
    
    # 找不到精确匹配,尝试另一种: 在测量方向上找投影
    # 找经过延伸线端点且垂直于测量方向的线
    best_proj = None
    best_diff = float('inf')
    for wall in walls:
        w_len = wall['length']
        if w_len < 10:
            continue
        if not lines_are_parallel(wall['angle'], meas_angle):
            continue
        
        # 检查墙线的延伸覆盖面
        proj1 = (wall['p1'][0] * meas_vec[0] + wall['p1'][1] * meas_vec[1])
        proj2 = (wall['p2'][0] * meas_vec[0] + wall['p2'][1] * meas_vec[1])
        w_proj_len = abs(proj2 - proj1)
        
        diff = abs(w_proj_len - dim_val)
        if diff < best_diff:
            best_diff = diff
            best_proj = {
                'dim_measurement': dim_val,
                'geo_measurement': round(w_proj_len, 2),
                'difference': round(diff, 2),
                'tolerance_ok': diff <= tolerance,
                'matched_layer': wall['layer'],
                'end_dist': -1,
            }
    
    return best_proj


def validate_all_dims(dims, lines, lwpolylines):
    """批量验证所有标注"""
    all_geo = lines + lwpolylines
    
    # 只关注墙体和主要结构线段
    wall_layers = {'A-WALL', 'A-DOOR', 'A-WINDW', 'A-GLASS', 'A-HATCH', 
                   'WALL', 'WALL-1', 'WALL-2', '墙体', '墙线'}
    key_lines = [g for g in all_geo if g['length'] > 50]  # 忽略超短线
    
    results = []
    for dim in dims:
        result = validate_dimension_v2(dim, key_lines)
        
        status = '❓ 未匹配'
        if result:
            if result['tolerance_ok']:
                status = '✅ 精确'
            elif result['difference'] < 50:
                status = '≈ 近似'
            else:
                status = '⚠️ 偏差'
        
        results.append({
            'index': len(results) + 1,
            'handle': dim['handle'],
            'measurement': dim['actual_measurement'],
            'orientation': dim['orientation'],
            'layer': dim['layer'],
            'validation': result,
            'status': status,
        })
    
    return results


# ============================================================
# 3. 验证报告
# ============================================================

def generate_validation_report(results, filename=''):
    """生成尺寸验证报告"""
    report = []
    report.append(f"{'='*70}")
    report.append(f"  课题003 — 尺寸验证报告")
    report.append(f"  文件: {filename}")
    report.append(f"{'='*70}")
    report.append("")
    
    stats = {'✅ 精确': 0, '≈ 近似': 0, '⚠️ 偏差': 0, '❓ 未匹配': 0}
    for r in results:
        stats[r['status']] += 1
    
    report.append(f"  验证统计:")
    report.append(f"    总标注数: {len(results)}")
    report.append(f"    ✅ 精确匹配: {stats.get('✅ 精确', 0)}")
    report.append(f"    ≈ 近似匹配: {stats.get('≈ 近似', 0)}")
    report.append(f"    ⚠️ 有偏差:   {stats.get('⚠️ 偏差', 0)}")
    report.append(f"    ❓ 未匹配:   {stats.get('❓ 未匹配', 0)}")
    report.append("")
    
    # 偏差分析
    diffs = [r['validation']['difference'] 
             for r in results if r['validation'] and not r['validation']['tolerance_ok']]
    if diffs:
        report.append(f"  偏差统计:")
        report.append(f"    最大偏差: {max(diffs)}mm")
        report.append(f"    平均偏差: {sum(diffs)/len(diffs):.1f}mm")
        report.append(f"    偏差数: {len(diffs)}")
        report.append("")
    
    # 层验证统计
    layer_stats = defaultdict(lambda: {'good': 0, 'approx': 0, 'bad': 0, 'no_match': 0})
    for r in results:
        layer = r['layer']
        s = r['status']
        if '精确' in s:
            layer_stats[layer]['good'] += 1
        elif '近似' in s:
            layer_stats[layer]['approx'] += 1
        elif '偏差' in s:
            layer_stats[layer]['bad'] += 1
        else:
            layer_stats[layer]['no_match'] += 1
    
    report.append(f"  各图层验证:")
    for layer in sorted(layer_stats):
        s = layer_stats[layer]
        report.append(f"    {layer:12s}: ✅{s['good']} ≈{s['approx']} ⚠️{s['bad']} ❓{s['no_match']}")
    report.append("")
    
    # 全部结果明细
    report.append(f"  验证明细:")
    report.append(f"  {'#':>4s} │ {'标注值':>8s} │ {'几何值':>8s} │ {'偏差':>6s} │ {'状态':>6s} │ {'图层':12s} │ {'方向':12s}")
    report.append(f"  {'─'*4}┼{'─'*9}┼{'─'*9}┼{'─'*7}┼{'─'*7}┼{'─'*13}┼{'─'*13}")
    
    for r in results:
        v = r['validation']
        dim_val = f"{r['measurement']:.0f}" if r['measurement'] else '?'
        geo_val = f"{v['geo_measurement']:.0f}" if v else '?'
        diff = f"{v['difference']:.1f}" if v else '?'
        report.append(f"  {r['index']:>4d} │ {dim_val:>8s} │ {geo_val:>8s} │ {diff:>6s} │ {r['status']:>6s} │ {r['layer']:12s} │ {r['orientation']:12s}")
    
    report.append("")
    report.append(f"{'='*70}")
    report.append(f"  验证结束")
    report.append(f"{'='*70}")
    
    return '\n'.join(report)


# ============================================================
# 4. 主入口
# ============================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='课题003 Step2 — 尺寸验证器')
    parser.add_argument('json_path', nargs='?',
                        default='/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/晴碧园_一层_重绘V2_解析.json',
                        help='DXF解析JSON路径')
    
    args = parser.parse_args()
    
    print(f"📏 课题003 Step2 — 尺寸验证器")
    print(f"  加载: {args.json_path}")
    
    # 动态加载提取器（文件名含数字前缀）
    import importlib.util, importlib.machinery
    _ext_path = os.path.join(os.path.dirname(__file__), '001_标注提取器.py')
    _loader = importlib.machinery.SourceFileLoader('标注提取器', _ext_path)
    _spec = importlib.util.spec_from_loader('标注提取器', _loader)
    _extractor = importlib.util.module_from_spec(_spec)
    _loader.exec_module(_extractor)
    extract_all_dims_from_json = _extractor.extract_all_dims_from_json
    
    dims = extract_all_dims_from_json(args.json_path)
    print(f"  ✅ {len(dims)} 个标注已加载")
    
    # 加载几何
    lines, lwpolylines = load_geometry(args.json_path)
    print(f"  ✅ {len(lines)} LINE + {len(lwpolylines)} LWPOLYLINE 已加载")
    
    # 验证
    print(f"  正在验证...")
    results = validate_all_dims(dims, lines, lwpolylines)
    
    # 报告
    report = generate_validation_report(results, filename=args.json_path)
    print(f"\n{report}")
