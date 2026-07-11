#!/bin/bash
# 在 PC 上安装 numpy+ezdxf 运行解析
pip install numpy ezdxf && python3 << 'PYSCRIPT'
import ezdxf

dxf_path = '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf'
out_dir = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/课题001_二层重绘'

import os
os.makedirs(out_dir, exist_ok=True)

doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

# 找到2F平面布置图的边界
# 从图纸目录知 PL-2F-01 = 2F平面布置图
f2f_y_min, f2f_y_max = -328538, -311966

layer_map = {
    'A-土建墙（含管井、立管）': 'A-WALL',
    'A-新隔墙': 'A-WALL',
    'P-门': 'A-DOOR',
    'A-窗': 'A-WINDOW',
    'P-楼梯（包括扶手）': 'A-STAIR',
    'A-轴线': 'A-AXIS',
    'W-尺寸': 'A-DIMS',
    'W-文字': 'A-TEXT',
    'W-Word(文字及尺寸标注)': 'A-TEXT',
    'C-顶部标高': 'A-SYMBOL',
    'P-固定家具（落地、到顶）': 'A-FURN',
    'P-活动家具': 'A-FURN',
    'P-完成面': 'A-FURN',
    'TEXT': 'A-TEXT',
    'T-text': 'A-TEXT',
    'A-土建柱': 'A-COLUMN',
    'A-土建墙填充': 'A-WALL',
    'A-新隔墙填充': 'A-WALL',
    'P-门套': 'A-DOOR',
    'P-楼梯（包括扶手）': 'A-STAIR',
    'W-基础引线': 'A-DIMS',
    'P-固定家具（悬空）': 'A-FURN',
    'P-固定家具（落地、不到顶）': 'A-FURN',
    'P-固定家具（不落地、到顶）': 'A-FURN',
    'P-家具尺寸': 'A-FURN',
    'P-完成面（不到顶）': 'A-FURN',
    'P-洁具及配件（地坪图不显示）': 'A-FURN',
    'P-完成面尺寸': 'A-FURN',
    'F-地坪造型线': 'A-FURN',
    'C-顶面造型线': 'A-HATCH',
    'C-顶面灯具、灯带': 'A-HATCH',
    'C-顶面设备': 'A-HATCH',
    'M-开关点位': 'A-HATCH',
    'M-插座连线': 'A-HATCH',
    'BJ-X25 插座': 'A-HATCH',
    'BJ-X22 天花尺寸': 'A-HATCH',
    '0': '0',
    'Defpoints': 'Defpoints',
    '活动家私': 'A-FURN',
}

count = 0
for e in msp:
    # 检查 Y 范围
    try:
        y = None
        if hasattr(e.dxf, 'insert'):
            y = e.dxf.insert.y
        elif hasattr(e.dxf, 'start'):
            y = e.dxf.start.y
        
        if y is None:
            continue
        if abs(y) < 1000:  # 图纸空间
            continue
        if not (f2f_y_min <= y <= f2f_y_max):
            continue
    except:
        continue
    
    count += 1

print(f'2F 区域实体: {count}')
PYSCRIPT
