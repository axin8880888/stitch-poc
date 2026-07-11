#!/usr/bin/env python3
"""
CAD Master - 命令训练器 V1.0
手机端运行，每日随机抽取命令进行练习
"""

import random
import os
from svgwrite import Drawing

OUT = '/storage/emulated/0/Download/篮筐整改/CAD_Master/02_命令'
COURSE_FILE = f'{OUT}/每日训练_课程表.txt'

# =============================================
# 27个核心命令数据库
# =============================================

COMMANDS = [
    {
        'name': 'LINE',
        'alias': 'L',
        'category': '绘图',
        'description': '绘制直线段',
        'difficulty': 1,
        'example': 'L → 点A → 点B → Enter',
        'param_desc': '连续点击指定起点和终点',
        'common_error': '应使用 PL 多段线画连续轮廓',
        'exercise': '画一个L形路径: 起点(0,0)→(500,0)→(500,300)→(200,300)',
        'fun_fact': 'LINE是最基础也最容易被替代的命令，大多数时候PLINE更好用'
    },
    {
        'name': 'PLINE',
        'alias': 'PL',
        'category': '绘图',
        'description': '绘制连续多段线（直线/圆弧）',
        'difficulty': 2,
        'example': 'PL → 点A → W → 50 → 50 → 画墙厚',
        'param_desc': 'W(宽度) A(圆弧) L(直线) C(闭合)',
        'common_error': '画完忘记C闭合，导致区域不是封闭的',
        'exercise': '画一个带宽度的矩形轮廓: 宽度50, 长500x300',
        'fun_fact': 'PLINE可以设置起点和端点不同宽度，画出锥形线'
    },
    {
        'name': 'RECTANG',
        'alias': 'REC',
        'category': '绘图',
        'description': '绘制矩形多段线',
        'difficulty': 1,
        'example': 'REC → 点A → D → 500 → 300 → 点',
        'param_desc': 'D(尺寸) R(圆角) W(线宽)',
        'common_error': '不用REC而用LINE画四条线拼矩形',
        'exercise': '画一个600x400的矩形，带R=50的圆角',
        'fun_fact': 'REC画出来的是PLINE，可以直接整体编辑'
    },
    {
        'name': 'CIRCLE',
        'alias': 'C',
        'category': '绘图',
        'description': '绘制圆形',
        'difficulty': 1,
        'example': 'C → 圆心 → 半径500',
        'param_desc': '半径R / 直径D / 2P / 3P / TTR',
        'common_error': '半径和直径搞混（看看参数提示栏）',
        'exercise': '画一个半径300的圆, 再画一个直径500的圆',
        'fun_fact': 'TTR方式可以直接画出与两条线相切的圆'
    },
    {
        'name': 'ARC',
        'alias': 'A',
        'category': '绘图',
        'description': '绘制圆弧',
        'difficulty': 2,
        'example': 'A → 起点 → C(圆心) → 端点',
        'param_desc': '三点(默认) / 起点-圆心-端点 / 起点-圆心-角度',
        'common_error': '逆时针与顺时针方向搞混',
        'exercise': '画一条180度的半圆弧，半径200',
        'fun_fact': 'ARC有11种画法，但常用的就两三种'
    },
    {
        'name': 'COPY',
        'alias': 'CO',
        'category': '修改',
        'description': '复制选中的对象',
        'difficulty': 1,
        'example': 'CO → 选对象 → 基点 → M → 多重复制',
        'param_desc': 'M(多重复制) D(阵列)',
        'common_error': '基点选偏导致复制后位置偏移',
        'exercise': '复制同一个家具图块到4个不同位置',
        'fun_fact': 'CO结合M可以一次性复制多个阵列'
    },
    {
        'name': 'MOVE',
        'alias': 'M',
        'category': '修改',
        'description': '移动对象到新位置',
        'difficulty': 1,
        'example': 'M → 选对象 → 基点 → 目标点',
        'param_desc': '选择对象 → 指定位移',
        'common_error': '距离远时用M不如用STRETCH',
        'exercise': '将一组家具从(0,0)移动到(500,300)',
        'fun_fact': 'MOVE配合正交F8可以完美水平/垂直移动'
    },
    {
        'name': 'ROTATE',
        'alias': 'RO',
        'category': '修改',
        'description': '绕基点旋转对象',
        'difficulty': 2,
        'example': 'RO → 选对象 → 基点 → 45',
        'param_desc': 'R(参照旋转) C(复制并旋转)',
        'common_error': '正负角度搞混（逆时针为正）',
        'exercise': '把一个矩形旋转45度（用参照方式旋转到与已有线对齐）',
        'fun_fact': 'R(参照)模式可以旋转到与已有对象对齐，不用算角度'
    },
    {
        'name': 'SCALE',
        'alias': 'SC',
        'category': '修改',
        'description': '缩放对象比例',
        'difficulty': 2,
        'example': 'SC → 选对象 → 基点 → 2.0',
        'param_desc': 'R(参照缩放) C(复制并缩放)',
        'common_error': '用SC改视口比例（应该用属性面板）',
        'exercise': '把一个图块放大1.5倍（参照方式: 已知长度→目标长度）',
        'fun_fact': 'R(参照)缩放是最实用的：告诉你"左边这个长度要变成和右边一样"'
    },
    {
        'name': 'MIRROR',
        'alias': 'MI',
        'category': '修改',
        'description': '镜像复制对象',
        'difficulty': 2,
        'example': 'MI → 选对象 → 镜像线第一点 → 第二点 → N',
        'param_desc': '是否删除源对象(Y/N)',
        'common_error': '文字被镜像变反字（MIRRTEXT=0可解决）',
        'exercise': '把卫生间布局镜像到另一侧（保留源）',
        'fun_fact': '对称户型用MI至少省一半时间'
    },
    {
        'name': 'TRIM',
        'alias': 'TR',
        'category': '修改',
        'description': '修剪多余线段',
        'difficulty': 2,
        'example': 'TR → 空格(全选剪切边) → 点要剪的部分',
        'param_desc': '选剪切边 → 选要修剪的部分',
        'common_error': '不习惯按两下空格进入快速修剪',
        'exercise': '把交叉的墙体线修剪干净（开窗洞）',
        'fun_fact': '按两下空格 = 所有对象都作为剪切边，最快模式'
    },
    {
        'name': 'EXTEND',
        'alias': 'EX',
        'category': '修改',
        'description': '延伸对象到边界',
        'difficulty': 2,
        'example': 'EX → 空格(全选边界) → 点要延伸的部分',
        'param_desc': '选边界 → 选延伸对象',
        'common_error': '延伸方向不对或边界不可见',
        'exercise': '把墙体线延伸到外墙边界',
        'fun_fact': 'EX和TR可以互相按住Shift键切换'
    },
    {
        'name': 'OFFSET',
        'alias': 'O',
        'category': '修改',
        'description': '按距离创建平行副本',
        'difficulty': 2,
        'example': 'O → 100 → 选线 → 点方向',
        'param_desc': 'T(通过点偏移)',
        'common_error': '偏移后忘记改图层',
        'exercise': '外墙偏移100mm作为内墙线',
        'fun_fact': 'OFFSET是画墙体最快的方法：外墙→偏移→内墙'
    },
    {
        'name': 'FILLET',
        'alias': 'F',
        'category': '修改',
        'description': '两条线间创建圆角',
        'difficulty': 2,
        'example': 'F → R → 50 → 选线1 → 选线2',
        'param_desc': 'R(半径) P(多段线整体圆角) T(修剪模式)',
        'common_error': '半径太大导致图形变形',
        'exercise': '对一个矩形做4个角R=30的圆角',
        'fun_fact': '半径设为0时，FILLET可以修剪延伸两条线（相当于修剪+延伸）'
    },
    {
        'name': 'CHAMFER',
        'alias': 'CHA',
        'category': '修改',
        'description': '两条线间创建倒角',
        'difficulty': 2,
        'example': 'CHA → D → 100 → 100 → 选线1 → 选线2',
        'param_desc': 'D(距离) A(角度) T(修剪模式)',
        'common_error': '两个距离搞反了',
        'exercise': '对矩形做4个倒角 D=50',
        'fun_fact': 'D设0时CHA也能修剪延伸，和FILLET的R=0效果一样'
    },
    {
        'name': 'EXPLODE',
        'alias': 'X',
        'category': '修改',
        'description': '将块/多段线分解为单个对象',
        'difficulty': 1,
        'example': 'X → 选对象 → Enter',
        'param_desc': '选择要分解的对象',
        'common_error': '分解后块的属性丢失变为普通文字',
        'exercise': '分解一个PLINE为单独线段',
        'fun_fact': '能不用X就不用——块是结构化的，X掉就没了'
    },
    {
        'name': 'BLOCK',
        'alias': 'B',
        'category': '块',
        'description': '创建块（组合对象）',
        'difficulty': 3,
        'example': 'B → 名称 "DOOR-900" → 基点 → 选对象 → OK',
        'param_desc': '名称、基点、选择对象、保留/转换/删除',
        'common_error': '基点选在远处，插入时位置偏差大',
        'exercise': '创建一个900宽的门图块（门扇+弧线+门套）',
        'fun_fact': '块修改一个定义，所有引用自动更新——CAD最重要的复用机制'
    },
    {
        'name': 'INSERT',
        'alias': 'I',
        'category': '块',
        'description': '插入已定义的块',
        'difficulty': 1,
        'example': 'I → 选块名 → 插入点 → 比例1 → 角度0',
        'param_desc': '块名、插入点、比例、旋转',
        'common_error': '忘记调整比例和角度',
        'exercise': '插入门块到墙体中（调整旋转角度）',
        'fun_fact': 'I插入时可以在对话框中预览块'
    },
    {
        'name': 'HATCH',
        'alias': 'H',
        'category': '填充',
        'description': '封闭区域填充图案',
        'difficulty': 2,
        'example': 'H → 选图案(ANSI31) → 比例50 → 拾取内部点',
        'param_desc': '图案类型、比例、角度、边界',
        'common_error': '边界不封闭导致无法填充',
        'exercise': '对墙体剖面填充（比例合适，不要过密或过疏）',
        'fun_fact': 'HATCH还可以填充渐变色和纯色块'
    },
    {
        'name': 'LAYER',
        'alias': 'LA',
        'category': '管理',
        'description': '图层管理器',
        'difficulty': 1,
        'example': 'LA → 新建 "A-WALL" → 颜色7 → 线宽0.30',
        'param_desc': '新建/删除/冻结/锁定/颜色/线型/线宽',
        'common_error': '所有对象画在一个图层上',
        'exercise': '在当前图纸中建立完整的图层体系（至少6个图层）',
        'fun_fact': '图层的冻结/锁定/打印开关是最常用的组织方式'
    },
    {
        'name': 'DIMENSION',
        'alias': 'D / DLI / DAL',
        'category': '标注',
        'description': '创建尺寸标注',
        'difficulty': 3,
        'example': 'DLI → 点第一条延伸线原点 → 第二条 → 标注位置',
        'param_desc': 'DLI(线性) DAL(对齐) DRA(半径) DDI(直径) DAN(角度)',
        'common_error': '标注样式没设好，箭头文字大小不一致',
        'exercise': '标注一个房间的完整尺寸（长宽+内部门窗位置）',
        'fun_fact': 'DIMSTYLE(D)可以创建多种标注样式，不同比例用不同样式'
    },
    {
        'name': 'MTEXT',
        'alias': 'MT',
        'category': '文字',
        'description': '多行文字输入',
        'difficulty': 1,
        'example': 'MT → 拖框 → 输入说明文字 → 设字体/高度',
        'param_desc': '字体、高度、对齐、行距、符号',
        'common_error': '字体用系统自带，换机子后乱码',
        'exercise': '写一段施工说明：包含标题、正文、材料说明',
        'fun_fact': 'MT里面可以插入度数°、直径Ø、正负±等符号'
    },
    {
        'name': 'MATCHPROP',
        'alias': 'MA',
        'category': '工具',
        'description': '属性匹配（格式刷）',
        'difficulty': 1,
        'example': 'MA → 选源对象 → 选目标对象',
        'param_desc': 'S(选择匹配的属性，如图层/颜色/线型等)',
        'common_error': '复制了不需要的属性（用S参数筛选）',
        'exercise': '把多个不同图层的对象统一到同一个图层',
        'fun_fact': 'MA是最省力的标准化工具——点一下源再点目标'
    },
    {
        'name': 'PURGE',
        'alias': 'PU',
        'category': '管理',
        'description': '清理未使用的项目',
        'difficulty': 1,
        'example': 'PU → 全部清理 → 反复清理直到无可清理项',
        'param_desc': '图层/块/线型/标注样式/文字样式等',
        'common_error': '没有勾选"清理嵌套项"导致清理不彻底',
        'exercise': '对一张从网上下载的图纸做彻底清理',
        'fun_fact': 'PU要按好几次直到灰了才算清理干净'
    },
    {
        'name': 'AUDIT',
        'alias': 'AUDIT',
        'category': '管理',
        'description': '核查并修复图形错误',
        'difficulty': 1,
        'example': 'AUDIT → Y(修复错误)',
        'param_desc': 'Y(修复) N(仅报告)',
        'common_error': '收到损坏图纸不先AUDIT就操作',
        'exercise': '打开一个有问题的DWG，先用AUDIT检查',
        'fun_fact': '每次打开别人发来的图，先AUDIT是职业习惯'
    },
    {
        'name': 'PLOT',
        'alias': 'PLOT / Ctrl+P',
        'category': '输出',
        'description': '打印/输出图纸',
        'difficulty': 3,
        'example': 'Ctrl+P → 打印机(DWG to PDF) → 图纸A3 → 比例1:1',
        'param_desc': '纸张、打印机、范围、比例、打印样式',
        'common_error': '比例不对导致打印出来尺寸不对',
        'exercise': '在布局空间设置A3图框并输出PDF',
        'fun_fact': '打印出问题90%是因为页面设置不对'
    },
    {
        'name': 'LAYOUT',
        'alias': 'LO',
        'category': '输出',
        'description': '创建和管理布局',
        'difficulty': 3,
        'example': '右键布局标签 → 新建布局 → 页面设置管理器',
        'param_desc': '新建/删除/重命名/移动/复制',
        'common_error': '在模型空间排图（应该在布局空间）',
        'exercise': '创建3个布局（A1平面/A2立面/A3节点）分别设置出图比例',
        'fun_fact': '一张图可以有很多布局，每个布局对应一张图纸'
    },
    {
        'name': 'PUBLISH',
        'alias': 'PUBLISH',
        'category': '输出',
        'description': '批量发布多张图纸',
        'difficulty': 3,
        'example': 'PUBLISH → 勾选布局 → 发布为PDF → 保存',
        'param_desc': '选择布局、输出格式、保存路径',
        'common_error': '不同图幅混排需要分别设置',
        'exercise': '把一套图纸（4张）一次批量输出PDF',
        'fun_fact': 'PUBLISH可以一键输出整套图纸，每个布局一页'
    },
]

# =============================================
# 训练生成器
# =============================================

def draw_exercise(command, filename):
    """为每个命令生成一个SVG练习示例"""
    name = command['name']
    alias = command['alias']
    category = command['category']
    example = command['example']
    desc = command['description']
    error = command['common_error']
    fact = command.get('fun_fact', '')
    exercise = command.get('exercise', '')
    
    dwg = Drawing(filename, size=('650px', '500px'))
    dwg.add(dwg.rect(insert=(0,0), size=(650,500), fill='#fafafa'))
    
    y = 20
    dwg.add(dwg.text(f'{name} ({alias}) — {category}命令', insert=(30, y), font_size='18', font_weight='bold'))
    y += 30
    dwg.add(dwg.text(f'用途: {desc}', insert=(30, y), font_size='12'))
    y += 20
    dwg.add(dwg.text(f'示例: {example}', insert=(30, y), font_size='11', fill='#444'))
    y += 20
    dwg.add(dwg.text(f'常见错误: {error}', insert=(30, y), font_size='11', fill='#aa3333'))
    y += 20
    if fact:
        dwg.add(dwg.text(f'小知识: {fact}', insert=(30, y), font_size='10', fill='#666'))
        y += 20
    y += 10
    dwg.add(dwg.text('练习题:', insert=(30, y), font_size='12', font_weight='bold'))
    y += 18
    dwg.add(dwg.text(exercise, insert=(30, y), font_size='11', fill='#336699'))
    y += 25
    
    # 根据命令类型画一个示意图形
    # 一个简单的网格
    dwg.add(dwg.line((30, y+50), (600, y+50), stroke='#ddd', stroke_width=0.5))
    dwg.add(dwg.line((300, y+10), (300, y+100), stroke='#ddd', stroke_width=0.5))
    
    # 画个示例图形
    if name == 'LINE':
        dwg.add(dwg.line((100, y+40), (500, y+40), stroke='#222', stroke_width=2.5))
        dwg.add(dwg.text('起点', insert=(95, y+55), font_size='9', fill='#888'))
        dwg.add(dwg.text('终点', insert=(495, y+55), font_size='9', fill='#888'))
    elif name == 'PLINE':
        pts = [(100, y+50), (250, y+30), (400, y+60), (500, y+35)]
        dwg.add(dwg.polyline([(p[0], p[1]) for p in pts], fill='none', stroke='#222', stroke_width=2.5))
        dwg.add(dwg.text('连续多段线', insert=(250, y+85), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'RECTANG':
        dwg.add(dwg.rect(insert=(150, y+20), size=(350, 60), fill='none', stroke='#222', stroke_width=2.5))
        dwg.add(dwg.text('矩形 (一个整体)', insert=(325, y+55), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'CIRCLE':
        dwg.add(dwg.circle(center=(300, y+55), r=40, fill='none', stroke='#222', stroke_width=2.5))
        dwg.add(dwg.text('R=300', insert=(300, y+55), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'ARC':
        dwg.add(dwg.path(d=f'M 150,{y+55} A 150,150 0 0,1 450,{y+55}', fill='none', stroke='#222', stroke_width=2.5))
        dwg.add(dwg.text('180°半圆', insert=(300, y+50), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'COPY':
        dwg.add(dwg.rect(insert=(100, y+30), size=(50, 50), fill='none', stroke='#222', stroke_width=1.5))
        dwg.add(dwg.rect(insert=(200, y+30), size=(50, 50), fill='none', stroke='#888', stroke_width=1))
        dwg.add(dwg.rect(insert=(300, y+30), size=(50, 50), fill='none', stroke='#888', stroke_width=1))
        dwg.add(dwg.text('源 → 复制1 → 复制2', insert=(200, y+95), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'MOVE':
        dwg.add(dwg.rect(insert=(100, y+30), size=(50, 50), fill='#ddd', stroke='#888', stroke_width=1))
        dwg.add(dwg.rect(insert=(250, y+30), size=(50, 50), fill='none', stroke='#222', stroke_width=2))
        dwg.add(dwg.line((120, y+55), (275, y+55), stroke='#aaa', stroke_width=1, stroke_dasharray='5,3'))
        dwg.add(dwg.text('→ 移动', insert=(280, y+60), font_size='10', fill='#888'))
    elif name == 'ROTATE':
        dwg.add(dwg.rect(insert=(200, y+30), size=(100, 50), fill='none', stroke='#888', stroke_width=1))
        dwg.add(dwg.rect(insert=(180, y+25), size=(100, 50), transform="rotate(30, 230, 50)", fill='none', stroke='#222', stroke_width=2))
        dwg.add(dwg.text('旋转30°', insert=(230, y+20), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'SCALE':
        dwg.add(dwg.rect(insert=(100, y+30), size=(80, 50), fill='none', stroke='#888', stroke_width=1))
        dwg.add(dwg.rect(insert=(300, y+15), size=(120, 75), fill='none', stroke='#222', stroke_width=2))
        dwg.add(dwg.text('1.5x', insert=(360, y+58), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'MIRROR':
        pts1 = [(100, y+20), (150, y+20), (130, y+70), (100, y+70)]
        pts2 = [(300, y+20), (250, y+20), (270, y+70), (300, y+70)]
        dwg.add(dwg.polygon(pts1, fill='none', stroke='#222', stroke_width=2))
        dwg.add(dwg.polygon(pts2, fill='none', stroke='#888', stroke_width=1))
        dwg.add(dwg.line((200, y+10), (200, y+80), stroke='#aaa', stroke_width=1, stroke_dasharray='5,3'))
        dwg.add(dwg.text('镜像轴', insert=(203, y+15), font_size='9', fill='#aaa'))
    elif name == 'HATCH':
        dwg.add(dwg.rect(insert=(150, y+15), size=(300, 70), fill='#ddd', stroke='#222', stroke_width=2))
        for i in range(0, 350, 15):
            x = 150 + i
            dwg.add(dwg.line((x, y+15), (x+30, y+85), stroke='#999', stroke_width=0.5))
    elif name == 'OFFSET':
        dwg.add(dwg.line((100, y+55), (500, y+55), stroke='#222', stroke_width=2.5))
        dwg.add(dwg.line((100, y+25), (500, y+25), stroke='#888', stroke_width=1.5))
        dwg.add(dwg.text('偏移30mm', insert=(300, y+45), font_size='10', fill='#888', text_anchor='middle'))
    elif name == 'LAYER':
        layers_colors = [('A-WALL', '#222'), ('A-DIM', '#080'), ('A-TEXT', '#000'), ('A-FURN', '#c0c')]
        for i, (name, color) in enumerate(layers_colors):
            y_offset = y + 15 + i * 17
            dwg.add(dwg.rect(insert=(150, y_offset), size=(20, 12), fill=color))
            dwg.add(dwg.text(name, insert=(175, y_offset+10), font_size='10'))
    elif name in ('DIMENSION',):
        dwg.add(dwg.line((150, y+55), (450, y+55), stroke='#222', stroke_width=2.5))
        dwg.add(dwg.line((150, y+20), (450, y+20), stroke='green', stroke_width=1))
        dwg.add(dwg.line((150, y+18), (150, y+22), stroke='green', stroke_width=1))
        dwg.add(dwg.line((450, y+18), (450, y+22), stroke='green', stroke_width=1))
        dwg.add(dwg.text('3000mm', insert=(300, y+18), font_size='10', fill='green', text_anchor='middle'))
    elif name == 'BLOCK':
        dwg.add(dwg.rect(insert=(150, y+15), size=(80, 30), fill='#e0e0ff', stroke='#222', stroke_width=1.5))
        dwg.add(dwg.circle(center=(190, y+30), r=8, fill='#ccf', stroke='#222', stroke_width=1))
        dwg.add(dwg.text('块定义', insert=(190, y+55), font_size='10', fill='#888', text_anchor='middle'))
        # 插入多个
        for i, (xx, yy) in enumerate([(280, y+20), (380, y+10), (460, y+40)]):
            dwg.add(dwg.rect(insert=(xx, yy), size=(40, 15), fill='#e0e0ff', stroke='#888', stroke_width=0.8))
            if i == 0:
                dwg.add(dwg.text('插入×3', insert=(370, y+65), font_size='10', fill='#888', text_anchor='middle'))
    else:
        dwg.add(dwg.text(f'练习命令: {name}', insert=(300, y+55), font_size='14', fill='#aaa', text_anchor='middle'))
    
    dwg.save()
    return True


# =============================================
# 主程序
# =============================================

def generate_daily_course(day=1):
    """生成每日课程表"""
    os.makedirs(OUT, exist_ok=True)
    
    # 按难度分级（每天5个命令）
    easy = [c for c in COMMANDS if c['difficulty'] == 1]
    medium = [c for c in COMMANDS if c['difficulty'] == 2]
    hard = [c for c in COMMANDS if c['difficulty'] == 3]
    
    # 每天随机组合
    selected = []
    selected.extend(random.sample(easy, min(2, len(easy))))
    selected.extend(random.sample(medium, min(2, len(medium))))
    selected.extend(random.sample(hard, min(1, len(hard))))
    random.shuffle(selected)
    
    # 写入课程表
    with open(COURSE_FILE, 'w') as f:
        f.write(f"=== CAD Master 每日训练 - Day {day} ===\n")
        f.write(f"日期: 训练日 #{day}\n\n")
        for cmd in selected:
            f.write(f"\n── {cmd['name']} ({cmd['alias']}) ──\n")
            f.write(f"  分类: {cmd['category']}\n")
            f.write(f"  难度: {'⭐' * cmd['difficulty']}\n")
            f.write(f"  用途: {cmd['description']}\n")
            f.write(f"  示例: {cmd['example']}\n")
            f.write(f"  常见错误: {cmd['common_error']}\n")
            f.write(f"  练习题: {cmd.get('exercise', '无')}\n")
    
    print(f"📋 课程表已生成: {COURSE_FILE}")
    
    # 为每个命令生成SVG练习图
    svg_files = []
    for cmd in selected:
        svg_file = f'{OUT}/{cmd["name"]}_练习.svg'
        draw_exercise(cmd, svg_file)
        svg_files.append(svg_file)
        print(f"  🖼  {cmd['name']:12s} → {os.path.basename(svg_file)}")
    
    print(f"\n✅ Day {day} 训练就绪! {len(selected)} 个命令")
    return selected


def list_all_commands():
    """列出所有命令"""
    print("\n📋 CAD Master - 27个核心命令")
    print("=" * 50)
    by_cat = {}
    for cmd in COMMANDS:
        cat = cmd['category']
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(cmd)
    
    for cat, cmds in by_cat.items():
        print(f"\n【{cat}】")
        for cmd in cmds:
            diff = '⭐' * cmd['difficulty']
            print(f"  {cmd['alias']:6s} {cmd['name']:12s} {diff}  {cmd['description']}")


if __name__ == '__main__':
    import sys
    print("🏗  CAD Master 命令训练器")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_all_commands()
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        day = int(sys.argv[1])
        generate_daily_course(day)
    else:
        print("用法: 训练_每日命令.py <参数>")
        print("  list           - 列出所有命令")
        print("  <数字>         - 生成第N天训练课")
        print("  (无参数)       - 生成今天的随机训练")
        generate_daily_course(1)
    
    print(f"\n训练文件位置: {OUT}/")
