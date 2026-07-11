#!/usr/bin/env python3
"""
课题001 训练脚本 — 解析晴碧园DXF，提取二层平面图区域
"""
import re, json, os
from collections import defaultdict

DXF_PATH = '/storage/emulated/0/设计/晴碧园晶园26栋拆砌墙.dxf'
OUT_DIR = '/storage/emulated/0/Download/篮筐整改/CAD_Master/05_自动化/训练记录/课题001'

os.makedirs(OUT_DIR, exist_ok=True)

print(f"📖 读取 DXF: {DXF_PATH}")
with open(DXF_PATH, 'rb') as f:
    data = f.read()
text = data.decode('utf-8', errors='replace')

# ============ 1. 提取所有 LAYER ============
print("🔍 提取图层信息...")
layers = {}
for m in re.finditer(r'\n  0\nLAYER\n  5\n([^\n]+)\n.*?\n  2\n([^\n]+)\n 70\n([^\n]+)\n 62\n([^\n]+)\n  6\n([^\n]+)\n290\n([^\n]+)\n370\n([^\n]+)\n', text, re.DOTALL):
    handle = m.group(1).strip()
    name = m.group(2).strip()
    flag70 = m.group(3).strip()
    color62 = m.group(4).strip()
    linetype = m.group(5).strip()
    plot = m.group(6).strip()
    lw = m.group(7).strip()
    layers[name] = {
        'color': int(color62) if color62.lstrip('-').isdigit() else 7,
        'lineweight': int(lw) if lw.lstrip('-').isdigit() else -3,
        'linetype': linetype,
        'frozen': bool(int(flag70) & 1),
    }

print(f"   共 {len(layers)} 个图层")
for name, info in sorted(layers.items()):
    print(f"   {name:20s}  color={info['color']:3d}  lw={info['lineweight']:3d}  {info['linetype']:15s}  {'❄' if info['frozen'] else '  '}")

# ============ 2. 提取 ENTITIES 段 ============
print("\n🔍 提取 ENTITIES 段...")
eidx = text.find('\n  0\nSECTION\n  2\nENTITIES\n')
eend = text.find('\n  0\nENDSEC\n', eidx)
ent_text = text[eidx:eend]

# 统计各图层的实体数量
layer_entities = defaultdict(int)
entity_types = defaultdict(lambda: defaultdict(int))

# 遍历所有实体
pos = 0
while True:
    # 找下一个实体开始
    m = re.search(r'\n  0\n([^\n]+)\n', ent_text[pos:])
    if not m:
        break
    etype = m.group(1).strip()
    estart = pos + m.start()
    
    # 找到下一个 0\n 作为实体结束
    next_m = re.search(r'\n  0\n', ent_text[estart+len(m.group(0)):])
    if next_m:
        eend_pos = estart + len(m.group(0)) + next_m.start()
    else:
        eend_pos = len(ent_text)
    
    entity_block = ent_text[estart:eend_pos]
    
    # 找 8\nLAYER_NAME
    lm = re.search(r'\n  8\n([^\n]+)\n', entity_block)
    layer_name = lm.group(1).strip() if lm else '0'
    
    layer_entities[layer_name] += 1
    entity_types[etype][layer_name] += 1
    
    pos = estart + len(m.group(0))

print(f"\n📊 实体统计:")
print(f"   总实体数: {sum(layer_entities.values())}")
print(f"   实体类型数: {len(entity_types)}")

# 各图层实体数 TOP 20
print("\n📊 图层实体数 TOP 30:")
for name, count in sorted(layer_entities.items(), key=lambda x: -x[1])[:30]:
    print(f"   {name:20s}  {count:6d} entities")

# 实体类型分布
print("\n📊 实体类型分布:")
for etype, layers_dict in sorted(entity_types.items(), key=lambda x: -sum(x[1].values()))[:15]:
    total = sum(layers_dict.values())
    print(f"   {etype:20s}  {total:6d} total")
    for lname, cnt in sorted(layers_dict.items(), key=lambda x: -x[1])[:5]:
        print(f"      {lname:20s}  {cnt}")

# ============ 3. 识别楼层区域 ============
print("\n🔍 尝试识别楼层...")

# 找TEXT/MTEXT中含"二层"的
text_entities = []
pos = 0
for m in re.finditer(r'\n  0\nTEXT\n', ent_text):
    start = m.start()
    next_m = re.search(r'\n  0\n', ent_text[start+10:])
    end = start + 10 + next_m.start() if next_m else len(ent_text)
    block = ent_text[start:end]
    
    # 提取内容 (group code 1)
    cm = re.search(r'\n  1\n([^\n]+)', block)
    content = cm.group(1).strip() if cm else ''
    
    # 提取位置 (10, 20)
    xm = re.search(r'\n 10\n([^\n]+)', block)
    ym = re.search(r'\n 20\n([^\n]+)', block)
    x = float(xm.group(1)) if xm else 0
    y = float(ym.group(1)) if ym else 0
    
    # 提取图层
    lm = re.search(r'\n  8\n([^\n]+)', block)
    layer = lm.group(1).strip() if lm else ''
    
    text_entities.append((content, layer, x, y))

# 找含"二层"、"2F"、"二楼"的文字
floor_texts = [t for t in text_entities if any(kw in t[0] for kw in ['二层', '2F', '二楼', '2层'])]
print(f"\n📝 含楼层标识的文字 ({len(floor_texts)}):")
for content, layer, x, y in floor_texts:
    print(f"   [{layer}] \"{content}\"  @ ({x:.0f}, {y:.0f})")

# 如果没有找到，找"二层平面"、"二层拆墙"等
if not floor_texts:
    floor_texts = [t for t in text_entities if any(kw in t[0] for kw in ['二', '2F'])]
    print(f"\n📝 含\"二\"的文字 ({len(floor_texts)}):")
    for content, layer, x, y in floor_texts:
        print(f"   [{layer}] \"{content}\"  @ ({x:.0f}, {y:.0f})")

# 输出找到的所有文字用于参考
print(f"\n📝 所有文字实体 ({len(text_entities)}):")
for content, layer, x, y in sorted(text_entities, key=lambda t: -t[2]):
    if len(content) < 30:
        print(f"   [{layer}] \"{content}\"  @ ({x:.0f}, {y:.0f})")

print("\n✅ 解析完成")
print(f"   结果输出到: {OUT_DIR}/")
