# 手机 → Mac 接力操作指南

> 在手机端用 OpenClaw 完成 DXF 解析/分析/修复后，
> 如何在 Mac 上用 AutoCAD 接力完成制图工作

---

## 一、文件传输

### 方法1：微信/QQ（最简单）
```
手机: 打开文件 → 发送给"文件传输助手" / "我的电脑"
Mac:  从微信/QQ下载保存
```

### 方法2：AirDrop（最快）
```
手机: 文件管理器 → 长按文件 → 共享 → AirDrop → 选Mac
Mac:  自动接收，出现在"下载"文件夹
```

### 方法3：网盘
```
推荐: 百度网盘 / iCloud / 阿里云盘
手机: 上传 → Mac: 下载
```

### 需要拷贝的文件

```
CAD_Master/
├── 04_实战案例/
│   ├── 课题011_图纸重构/重构标准版.dxf     ← 墙体骨架
│   ├── 课题012_轴网重建/主结构轴网.dxf      ← 推荐：先打开这个
│   ├── 课题012_轴网重建/轴网系统.dxf        ← 全轴线版（62条）
│   └── 课题013_墙轴对齐/墙体_轴网对齐.dxf   ← 对齐后的墙体
├── 05_自动化/
│   ├── scripts/cad_master.lsp               ← LISP工具集
│   └── scripts/*.scr                        ← SCR脚本
└── 03_规范/
    └── 检查器与修复器脚本                    ← 可选
```

---

## 二、AutoCAD 接力流程

### Step 1：加载 LISP 工具
```
AutoCAD 命令行:
  APPLOAD → 浏览到 cad_master.lsp → 加载
```

### Step 2：打开结构轴网
```
File → Open → 主结构轴网.dxf
（绿色粗线 = 主结构，紫色细虚线 = 次轴线）
```

### Step 3：标准化图层
```
命令行输入:
  LB-LAYER
→ 自动建立18个标准图层
```

### Step 4：插入墙体
```
File → Open → 墙体_轴网对齐.dxf
或者: INSERT → 墙体_轴网对齐.dxf
→ 查看墙体是否与轴线对齐
```

### Step 5：叠加验证
```
将 墙体DXF 和 轴网DXF 放在同一个文件中:
  1. 打开主结构轴网.dxf
  2. INSERT → 墙体_轴网对齐.dxf → 指定插入点
  3. 检查墙体是否在轴线位置上
  4. 手动微调偏移的墙体
```

### Step 6：补全图纸
```
1. 标注尺寸  → 用 LB-DIMSTYLE 设标注样式
2. 添加门窗 → 在轴线之间插入门/窗
3. 标注房间名 → A-TEXT 图层
4. 加填充  → HATCH 区分功能区
5. 加图框  → 参考 10_标题栏图框.md
```

### Step 7：清洁输出
```
命令行:
  LB-CLEAN   → 清理零长度线+空文本
  PURGE      → 清除未使用图块/图层
  AUDIT      → 修复图纸错误

然后:
  LB-PLOT → 批量打印PDF
  或 File → Export → PDF
```

---

## 三、各DXF文件用途对照

| DXF文件 | 用途 | 建议操作 |
|---------|------|---------|
| **主结构轴网.dxf** | 设计基准 | 以此为底图开始画 |
| 轴网系统.dxf | 全轴线（含次轴） | 复杂节点参考 |
| 墙体_轴网对齐.dxf | 墙体定位 | 叠加到轴网上校核 |
| 重构标准版.dxf | 房间名称+门弧 | 标注参考 |
| 晴碧园晶园26栋_规范修复.dxf | 完整原始图修复版 | 最终参考 |

---

## 四、Mac AutoCAD 环境配置

### 4.1 建议安装
```
1. AutoCAD for Mac 2024+ （正版或试用）
   - 完全兼容LISP
   - 完全兼容DXF/DWG
   
2. 替代方案：LibreCAD（免费）
   - 打开/编辑 DXF
   - 不支持LISP
   - 轻量级
```

### 4.2 字体设置
```
为了显示中文标注和文字:

1. 拷贝中文字体到:
   /Applications/Autodesk/AutoCAD 2024/Contents/Resources/Fonts/

2. 推荐字体:
   - 仿宋_GB2312.shx
   - 宋体.shx
   - Romans.shx（英文用）

3. 或用 TTF字体:
   - simfang.ttf（仿宋）
   - simsun.ttc（宋体）
```

### 4.3 CTB打印样式
```
monochrome.ctb 路径:
Mac: /Users/[用户名]/Library/Application Support/Autodesk/AutoCAD 2024/R24x/cht/Plot Styles/

如果没有，从Windows版拷贝或新建:
  1. Page Setup → Plot Style Table → New
  2. 选择 "monochrome" 模板
  3. 确保 Color 7 线宽=0.35mm
```

---

## 五、常见问题

### Q: DXF在Mac上中文乱码？
```
原因: 字体缺失
解决: 安装仿宋SHX字体，或改文字样式为TTF字体
```

### Q: LISP加载报错？
```
原因: Mac AutoCAD某些LISP函数差异
解决: cad_master.lsp 已兼容Mac/Win
      如果还有问题，注释掉出问题的行
```

### Q: 轴线太密看不清？
```
方法1: 关掉 A-AXIS-SUB 图层（只留主轴线）
方法2: 用主结构轴网.dxf（非全轴线版）
方法3: ZOOM到局部区域
```

---

## 六、推荐工作顺序

```
                    ┌─────────────────┐
                    │ 手机端OpenClaw   │
                    │ DXF解析+轴网重建 │
                    │ 墙体对齐+材料估算│
                    └────────┬────────┘
                             │ 拷贝到Mac
                             ▼
                    ┌─────────────────┐
                    │ Mac AutoCAD     │
                    │ 1. 开主结构轴网  │
                    │ 2. 加载LISP     │
                    │ 3. LB-LAYER图层 │
                    │ 4. INSERT墙体   │
                    │ 5. 手动补全图纸  │
                    │ 6. 标注+填充+图框│
                    │ 7. LB-CLEAN清理 │
                    │ 8. 打印PDF      │
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ 成品: 施工图PDF  │
                    └─────────────────┘
```

> ——— 手机分析 + Mac绘图 = 最高效的工作流 ———
