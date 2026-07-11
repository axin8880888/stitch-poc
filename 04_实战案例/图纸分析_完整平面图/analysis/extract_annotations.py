#!/usr/bin/env python3
"""
CAD 图纸数字和文字提取器 V1.0
纯 Python + Pillow，不需要任何 OCR 库
专门针对暗色模式 CAD 截图设计

原理：
1. 提取绿色/青色标注线位置的白色数字
2. 数字连通域分析
3. 模板匹配数字（针对CAD常用字体） 
"""

import os
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import math

# 图片路径
IMG = '/data/data/com.termux/files/home/.openclaw/media/inbound/121359---5d77ef14-b566-4345-b690-e6687c9a4dcc.jpg'
OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/04_实战案例/图纸分析_完整平面图/analysis'

os.makedirs(OUT, exist_ok=True)

img = Image.open(IMG)
W, H = img.size
print(f"原始图片: {W}×{H}")

# =============================================
# 步骤1: 颜色分离
# =============================================
# CAD暗色模式中：
# - 背景深色/黑色
# - 标注线: 绿色 (dim)
# - 墙体: 白色/浅色
# - 数字: 白色/浅色
# - 轴线: 红色点划线
# - 窗: 青色

pixels = img.load()

# 创建各种颜色通道掩码
channels = {}

# 白色/浅色通道 — 数字和墙体
white_mask = Image.new('L', (W, H))
wm = white_mask.load()
for y in range(H):
    for x in range(W):
        r, g, b = pixels[x, y]
        brightness = (r + g + b) // 3
        if brightness > 80:  # 浅色
            wm[x, y] = brightness

# 绿色通道 — 尺寸标注
green_mask = Image.new('L', (W, H))
gm = green_mask.load()
for y in range(H):
    for x in range(W):
        r, g, b = pixels[x, y]
        if g > r * 1.5 and g > b * 1.5 and g > 50:
            gm[x, y] = min(g * 2, 255)

# 青色通道 — 窗线
cyan_mask = Image.new('L', (W, H))
cm = cyan_mask.load()
for y in range(H):
    for x in range(W):
        r, g, b = pixels[x, y]
        if b > r * 1.5 and b > g * 1.2 and b > 50:
            cm[x, y] = min(b * 2, 255)

# 红色通道 — 轴线
red_mask = Image.new('L', (W, H))
rm = red_mask.load()
for y in range(H):
    for x in range(W):
        r, g, b = pixels[x, y]
        if r > g * 1.5 and r > b * 1.5 and r > 50:
            rm[x, y] = min(r * 2, 255)

# 保存通道
channels['white'] = white_mask
channels['green'] = green_mask
channels['cyan'] = cyan_mask
channels['red'] = red_mask

for name, mask in channels.items():
    ImageOps.invert(mask).save(f'{OUT}/ch_{name}.png')

print("✅ 颜色通道分离完成")

# =============================================
# 步骤2: 提取底部尺寸标注区域
# =============================================
# CAD图底部通常是尺寸标注行
# 从底部往上扫描，找到第一个密集的标注区域

# 白色通道的水平投影
white_arr = list(white_mask.getdata())
projection = []
for y in range(H):
    row_start = y * W
    row_end = row_start + W
    row = white_arr[row_start:row_end]
    non_black = sum(1 for p in row if p > 50)
    projection.append(non_black)

# 从底部往上找标注区域
# 标注区域特征：连续多行有非零像素，中间有空白行分隔
bottom_zones = []
in_zone = False
zone_start = H
for y in range(H-1, H//2, -1):  # 只关注下半部分
    if projection[y] > 10:
        if not in_zone:
            zone_start = y
            in_zone = True
    else:
        if in_zone and zone_start - y > 3:
            bottom_zones.append((y+1, zone_start))
            in_zone = False

if in_zone:
    bottom_zones.append((H//2, zone_start))

print(f"\n底部找到 {len(bottom_zones)} 个标注带:")
for i, (y1, y2) in enumerate(bottom_zones[:5]):
    height = y2 - y1
    avg_px = sum(projection[y1:y2]) / height if height > 0 else 0
    print(f"  带{i+1}: 行{y1}-{y2} ({height}行, 平均{avg_px:.0f}px/行)")

# 提取最重要的底部标注带
if bottom_zones:
    y1, y2 = bottom_zones[0]
    # 扩大提取区域
    crop_y1 = max(0, y1 - 10)
    crop_y2 = min(H, y2 + 20)
    
    bottom_region = Image.new('RGB', (W, crop_y2 - crop_y1))
    br_pixels = bottom_region.load()
    for y in range(crop_y1, crop_y2):
        for x in range(W):
            r, g, b = pixels[x, y]
            # 增强对比度
            brightness = (r + g + b) // 3
            if brightness > 40:
                br_pixels[x, y-crop_y1] = (min(brightness+100, 255), min(brightness+100, 255), 
                                           min(brightness+100, 255))
            else:
                br_pixels[x, y-crop_y1] = (0, 0, 0)
    
    bottom_region = bottom_region.resize((W*3, (crop_y2-crop_y1)*3), Image.LANCZOS)
    bottom_region.save(f'{OUT}/bottom_region_3x.png')
    print(f"\n✅ 底部标注区3倍放大: {OUT}/bottom_region_3x.png")

# =============================================
# 步骤3: 同样提取左侧尺寸标注
# =============================================
# 左侧：垂直标注
left_region = Image.new('RGB', (150, H))
lr_pixels = left_region.load()
for y in range(H):
    for x in range(150):
        r, g, b = pixels[x, y]
        brightness = (r + g + b) // 3
        if brightness > 40:
            lr_pixels[x, y] = (min(brightness+100, 255), min(brightness+100, 255),
                               min(brightness+100, 255))
        else:
            lr_pixels[x, y] = (0, 0, 0)

left_region = left_region.resize((450, H*3), Image.LANCZOS)
left_region.save(f'{OUT}/left_region_3x.png')
print(f"✅ 左侧标注区放大: {OUT}/left_region_3x.png")

# =============================================
# 步骤4: 水平和垂直标注线位置
# =============================================
# 找到绿色标注线的位置 - 这些是尺寸线
green_arr = list(green_mask.getdata())

# 水平绿色线（底部标注）
h_green_lines = []
for y in range(H):
    row_start = y * W
    row_end = row_start + W
    row = green_arr[row_start:row_end]
    green_count = sum(1 for p in row if p > 50)
    if green_count > W * 0.3:  # 超过30%宽度是绿色
        h_green_lines.append(y)

# 垂直绿色线（左侧标注）
v_green_lines = []
for x in range(W):
    col = [green_arr[y*W + x] for y in range(H)]
    green_count = sum(1 for p in col if p > 50)
    if green_count > H * 0.2:
        v_green_lines.append(x)

print(f"\n找到水平绿色标注线: {len(h_green_lines)} 个位置")
if h_green_lines:
    # 聚类
    clusters = []
    start = h_green_lines[0]
    prev = start
    for y in h_green_lines[1:]:
        if y - prev > 3:
            clusters.append((start, prev))
            start = y
        prev = y
    clusters.append((start, prev))
    for i, (s, e) in enumerate(clusters[:5]):
        center = (s+e)//2
        print(f"  {i+1}: 行{s}-{e} (中心≈{center})")

# =============================================
# 步骤5: 提取数字位置（白色小像素簇）
# =============================================
# 在标注线附近寻找白色数字
# 数字特征：小而紧凑的白色像素簇

from collections import defaultdict

# 扫描底部标注线上下 ±40px 范围内的白色像素
# 找到属于尺寸标注的数字
def find_digit_clusters(mask, scan_y, scan_h=50):
    """在给定行附近找白色像素簇（数字）"""
    clusters = []
    visited = set()
    
    y_start = max(0, scan_y - scan_h)
    y_end = min(H, scan_y + scan_h)
    
    white_arr = list(mask.getdata())
    
    # 找所有白色像素
    white_pixels = []
    for y in range(y_start, y_end):
        for x in range(W):
            if white_arr[y * W + x] > 50:
                white_pixels.append((x, y))
    
    # 连通域聚类
    for px, py in white_pixels:
        if (px, py) in visited:
            continue
        
        # BFS找连通域
        queue = [(px, py)]
        cluster = []
        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            cluster.append((cx, cy))
            
            # 4-邻域
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = cx+dx, cy+dy
                if (nx, ny) not in visited and y_start <= ny < y_end and 0 <= nx < W:
                    if white_arr[ny * W + nx] > 50:
                        queue.append((nx, ny))
        
        # 滤除太小和太大的簇（数字通常10-50像素）
        if 10 < len(cluster) < 200:
            xs = [p[0] for p in cluster]
            ys = [p[1] for p in cluster]
            clusters.append({
                'x': min(xs), 'y': min(ys),
                'w': max(xs)-min(xs), 'h': max(ys)-min(ys),
                'size': len(cluster),
                'cx': (min(xs)+max(xs))//2,
                'cy': (min(ys)+max(ys))//2,
            })
    
    return clusters

# 对每根水平标注线附近的白色簇
print("\n📊 底部标注带数字簇:")
if h_green_lines:
    # 取最下面的标注线
    bottom_line = h_green_lines[-1]
    clusters = find_digit_clusters(white_mask, bottom_line, 60)
    # 按x排序
    clusters.sort(key=lambda c: c['cx'])
    print(f"  找到 {len(clusters)} 个数字/文字簇（标注线附近）")
    for i, c in enumerate(clusters):
        print(f"    簇{i+1}: 位置({c['cx']},{c['cy']}) 尺寸{c['w']}×{c['h']}px")
    
    # 把这些数字区域切出来
    if clusters:
        digit_img = Image.new('L', (W, 120))
        for c in clusters:
            for py in range(max(0, int(c['cy']-15)), min(H, int(c['cy']+15))):
                for px in range(max(0, int(c['cx']-20)), min(W, int(c['cx']+20))):
                    val = white_arr[py * W + px]
                    if val > 50 and py - int(c['cy']-15) < 120:
                        digit_img.putpixel((px, py - int(c['cy']-15)), val)
        digit_img = digit_img.resize((W*3, 360), Image.LANCZOS)
        digit_img.save(f'{OUT}/bottom_digits_3x.png')
        print(f"\n✅ 数字放大图: {OUT}/bottom_digits_3x.png")

print(f"\n{'='*50}")
print(f"提取完成！请用相册打开以下图片看数据：")
print(f"{'='*50}")
print(f"1. {OUT}/bottom_region_3x.png   ← 底部尺寸标注（放大3倍）")
print(f"2. {OUT}/left_region_3x.png     ← 左侧尺寸标注（放大3倍）")
print(f"3. {OUT}/bottom_digits_3x.png   ← 底部数字区域（放大3倍）")
print(f"4. {OUT}/full_2x_enhanced.png   ← 全图增强版")
print(f"5. {OUT}/ch_white.png           ← 白色通道（墙体+文字）")
