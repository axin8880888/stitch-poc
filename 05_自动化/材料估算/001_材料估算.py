#!/usr/bin/env python3
"""
材料估算工具 V1 — 基于轴网对齐墙段

功能：
1. 从轴网对齐墙体DXF计算墙长度
2. 按房间分组：墙面积、地面积、踢脚线、油漆/墙纸
3. 扣除门窗洞口
4. 输出材料清单CSV + 报告

标准参数：
  层高: 2800mm (住宅默认)
  门洞: 900×2100mm (标准单开门)
  窗洞: 1500×1500mm (标准推拉窗)
  踢脚线高: 100mm
  损耗率: 5%
"""
import json, os, math, csv
from collections import defaultdict

BASE = '/storage/emulated/0/Download/篮筐整改/CAD_Master'
WALL_DXF = f'{BASE}/04_实战案例/课题013_墙轴对齐/墙体_轴网对齐.dxf'
JSON_PATH = f'{BASE}/05_自动化/训练记录/晴碧园晶园26栋_解析.json'
OUT_DIR   = f'{BASE}/05_自动化/材料估算'
os.makedirs(OUT_DIR, exist_ok=True)

# ===== 标准参数 =====
STD_HEIGHT = 2800       # 层高mm
DOOR_W, DOOR_H = 900, 2100   # 标准门
WINDOW_W, WINDOW_H = 1500, 1500  # 标准窗
BASEBOARD_H = 100       # 踢脚线高
LOSS_RATE = 0.05        # 损耗率

# ===== 材料单价参考（¥/m²或¥/m）=====
PRICES = {
    '内墙乳胶漆': 25,      # 元/m²
    '墙纸(国产)': 60,
    '墙纸(进口)': 150,
    '地砖(800×800)': 80,
    '地砖(600×600)': 60,
    '木地板(复合)': 120,
    '木地板(实木)': 300,
    '瓷砖(墙砖300×600)': 90,
    '踢脚线(实木)': 25,    # 元/m
    '踢脚线(瓷砖)': 15,
    '防水(卫生间)': 40,    # 元/m²
}

def fv(e,c):
    try: return float(e.get(f'code_{c}',0))
    except: return 0.0

# ===== 1. 加载墙段 =====
print('加载墙段...')
data = json.load(open(JSON_PATH))
ents = data.get('entities', [])

wl = ['A-WALL','A-土建墙','A-新隔墙','W-墙体']
segments = []
for e in ents:
    if e.get('type') != 'LINE': continue
    l = e.get('layer','')
    if l in wl or '墙' in l or 'WALL' in l:
        x1,y1 = fv(e,10), fv(e,20)
        x2,y2 = fv(e,11), fv(e,21)
        seg = math.hypot(x2-x1, y2-y1)
        is_h = abs(y2-y1) < abs(x2-x1)
        segments.append({
            'len': seg, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'is_h': is_h, 'layer': l,
            'y_center': (y1+y2)/2, 'x_center': (x1+x2)/2
        })

# 高度统计
lengths = [s['len'] for s in segments]
print(f'  墙段: {len(segments)}')
print(f'  墙总长: {sum(lengths)/1000:.1f}m')
print(f'  平均墙长: {sum(lengths)/len(lengths)/1000:.1f}m' if lengths else '')

# ===== 2. 按楼层分组 =====
def floor_key(y):
    if y < -324000: return 'F5'
    if y < -322000: return 'F4'
    if y < -320000: return 'F3'
    if y < -318000: return 'F2'
    if y < -316000: return 'F1'
    if y < -314000: return 'B1'
    return 'B2'

floors = defaultdict(list)
for s in segments:
    fk = floor_key(s['y_center'])
    floors[fk].append(s)

# ===== 3. 房间识别（用闭包面面积 = 地面积）=====
# 复用面积统计V4的闭合面结果
# 但我们先算整层数据

def estimate_openings(perimeter_m, wall_area):
    """按房间类型估算门窗洞口"""
    # 假设每4m墙长一个标准门洞
    door_count = max(1, round(perimeter_m / 8))
    window_count = max(1, round(perimeter_m / 12))
    door_area = door_count * DOOR_W * DOOR_H / 1e6  # m²
    window_area = window_count * WINDOW_W * WINDOW_H / 1e6
    return door_count, window_count, door_area, window_area

def room_type_from_name(name):
    """从房间名判断装修类型"""
    name_lower = name.lower()
    if any(k in name_lower for k in ['厨','kitchen']): return '厨房'
    if any(k in name_lower for k in ['卫','toilet','bath','wc','淋']): return '卫生间'
    if any(k in name_lower for k in ['阳台','露台','院子','庭']): return '阳台'
    if any(k in name_lower for k in ['储','杂','设备','管道']): return '储藏'
    if any(k in name_lower for k in ['车库','车位']): return '车库'
    return '卧室/客厅'

# ===== 4. 计算材料 =====
print('\n计算材料用量...')
report = []
sep = '='*65
report.append(sep)
report.append('  晴碧园晶园26栋 — 材料估算')
report.append(sep)
report.append('')
report.append(f'  层高: {STD_HEIGHT/1000:.1f}m | 标准门: {DOOR_W/1000:.1f}×{DOOR_H/1000:.1f}m')
report.append(f'  标准窗: {WINDOW_W/1000:.1f}×{WINDOW_H/1000:.1f}m | 损耗率: {LOSS_RATE*100:.0f}%')
report.append('')

total_wall_area = 0
total_floor_area = 0
total_baseboard = 0

csv_path = os.path.join(OUT_DIR, '材料估算表.csv')
with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['楼层', '房间类型', '墙周长(m)', '墙面积(m²)', '门洞(m²)', '窗洞(m²)',
                '净墙面积(m²)', '地面积(m²)', '踢脚线(m)', '推荐材料', '估算费用(¥)'])

    for fk in sorted(floors.keys(), key=lambda k: (isinstance(k,str), k)):
        segs = floors[fk]
        # 这层的墙总长（可做统计基准）
        floor_wall_len = sum(s['len'] for s in segs) / 1000  # m
        
        # 整层粗略估算
        perimeter = floor_wall_len * 2  # 双面墙
        gross_wall = floor_wall_len * (STD_HEIGHT/1000)  # m²
        
        # 楼层尺寸
        xs = [s['x_center'] for s in segs]
        ys = [s['y_center'] for s in segs]
        floor_x = max(xs)-min(xs) if xs else 0
        floor_y = max(ys)-min(ys) if ys else 0
        floor_area = floor_x * floor_y / 1e6  # m²
        
        # 估算洞口
        doors = max(1, round(perimeter/12))
        windows = max(1, round(perimeter/18))
        door_area = doors * DOOR_W * DOOR_H / 1e6
        window_area = windows * WINDOW_W * WINDOW_H / 1e6
        net_wall = gross_wall - door_area - window_area
        
        baseboard = perimeter * 0.8  # 扣除门洞位
        
        # 推荐材料 + 费用
        rtype = '卧室/客厅' if fk.startswith('F') else '储藏'
        if rtype == '卧室/客厅':
            wall_mat = '内墙乳胶漆'
            floor_mat = '木地板(复合)'
            base_mat = '踢脚线(实木)'
        else:
            wall_mat = '内墙乳胶漆'
            floor_mat = '地砖(800×800)'
            base_mat = '踢脚线(瓷砖)'
        
        wall_cost = net_wall * PRICES[wall_mat] * (1+LOSS_RATE)
        floor_cost = floor_area * PRICES[floor_mat] * (1+LOSS_RATE)
        base_cost = baseboard * PRICES[base_mat] * (1+LOSS_RATE)
        total_cost = wall_cost + floor_cost + base_cost
        
        total_wall_area += net_wall
        total_floor_area += floor_area
        total_baseboard += baseboard
        
        w.writerow([fk, rtype, f'{perimeter:.1f}', f'{gross_wall:.1f}',
                    f'{door_area:.1f}', f'{window_area:.1f}', f'{net_wall:.1f}',
                    f'{floor_area:.1f}', f'{baseboard:.1f}',
                    f'{wall_mat}+{floor_mat}', f'{total_cost:.0f}'])
        
        report.append(f'  {fk}层:')
        report.append(f'    墙总长: {floor_wall_len:.1f}m')
        report.append(f'    毛墙面积: {gross_wall:.1f}m²')
        report.append(f'    洞口扣除: -门{doors}扇({door_area:.1f}m²) -窗{windows}个({window_area:.1f}m²)')
        report.append(f'    净墙面积: {net_wall:.1f}m² → {wall_mat} ¥{wall_cost:.0f}')
        report.append(f'    地板面积: {floor_area:.1f}m² → {floor_mat} ¥{floor_cost:.0f}')
        report.append(f'    踢脚线: {baseboard:.1f}m → {base_mat} ¥{base_cost:.0f}')
        report.append(f'    小计: ¥{total_cost:.0f}')
        report.append('')
    
    # 总计
    total_cost_all = 0
    w.writerow(['', '=== 总计 ===', '', '', '', '', f'{total_wall_area:.1f}',
                f'{total_floor_area:.1f}', f'{total_baseboard:.1f}', '', ''])
    
    report.append(f'  {"总计":>30s}')
    report.append(f'    净墙面积: {total_wall_area:.1f}m²')
    report.append(f'    地板面积: {total_floor_area:.1f}m²')
    report.append(f'    踢脚线长: {total_baseboard:.1f}m')

# ===== 5. 详细房间级计算（使用面积统计结果）=====
print('加载房间面积数据...')
area_csv = f'{BASE}/05_自动化/面积统计/房间面积统计.csv'
if os.path.exists(area_csv):
    with open(area_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # header
        rooms = []
        for row in reader:
            if row and row[1] and '小计' not in row[1] and '总计' not in row[1]:
                try:
                    rooms.append({
                        'floor': row[0],
                        'name': row[1],
                        'area': float(row[2])
                    })
                except: pass
    
    report.append(f'\n    可用房间数据: {len(rooms)}间')
    
    # 详细房间材料（用房间面积估算周长）
    csv_detail = os.path.join(OUT_DIR, '材料估算_房间明细.csv')
    with open(csv_detail, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['楼层','房间名','面积(m²)','估周长(m)','墙面积(m²)',
                    '洞扣除(m²)','净墙(m²)','墙材','墙费(¥)','地材','地费(¥)',
                    '踢脚线(m)','踢脚费(¥)','合计(¥)'])
        
        for r in rooms:
            area = r['area']
            if area < 0.5: continue
            # 正方形近似周长
            side = math.sqrt(area)
            perimeter = side * 4
            
            rtype = room_type_from_name(r['name'])
            
            gross_wall = perimeter * (STD_HEIGHT/1000)
            _, _, da, wa = estimate_openings(perimeter, gross_wall)
            net_wall = gross_wall - da - wa
            baseboard = perimeter * 0.8
            
            if rtype in ('卫生间', '厨房'):
                wall_mat, floor_mat, base_mat = '瓷砖(墙砖300×600)', '地砖(600×600)', '踢脚线(瓷砖)'
                if rtype == '卫生间':
                    net_wall *= 1.5  # 卫生间墙面全贴砖
            elif rtype == '阳台':
                wall_mat, floor_mat, base_mat = '内墙乳胶漆', '地砖(800×800)', '踢脚线(瓷砖)'
            else:
                wall_mat, floor_mat, base_mat = '内墙乳胶漆', '木地板(复合)', '踢脚线(实木)'
            
            wc = net_wall * PRICES[wall_mat] * (1+LOSS_RATE)
            fc = area * PRICES[floor_mat] * (1+LOSS_RATE)
            bc = baseboard * PRICES[base_mat] * (1+LOSS_RATE)
            total = wc + fc + bc
            
            w.writerow([r['floor'], r['name'][:12], f'{area:.1f}', f'{perimeter:.1f}',
                       f'{gross_wall:.1f}', f'{da+wa:.1f}', f'{net_wall:.1f}',
                       wall_mat, f'{wc:.0f}', floor_mat, f'{fc:.0f}',
                       f'{baseboard:.1f}', f'{bc:.0f}', f'{total:.0f}'])
    
    report.append(f'    房间明细: {csv_detail}')
    report.append('')

report.append(sep)
report.append('  输出文件:')
report.append(f'    材料估算表.csv — 按楼层汇总')
report.append(f'    材料估算_房间明细.csv — 按房间详细')
report.append('')
report.append('【精度说明】')
report.append('  楼层级估算：基于墙总长×层高，洞口按经验比率扣除')
report.append('  房间级估算：基于面积→正方形近似周长，精度±15%')
report.append('  实际施工前需用CAD精确测量每个房间')
report.append(sep)

with open(os.path.join(OUT_DIR, '材料估算报告.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n' + '\n'.join(report))
print(f'\n✅ 材料估算完成!')
