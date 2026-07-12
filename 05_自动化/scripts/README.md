# CAD Master — 自动化脚本集

## 文件说明

### LISP 脚本（推荐，功能更强大）
| 文件 | 命令 | 功能 |
|------|------|------|
| `cad_master.lsp` | `LB-LAYER` | 创建/更新标准图层体系（18个标准图层） |
| | `LB-DIMSTYLE` | 设置HG-50/HG-100两个标注样式 |
| | `LB-CLEAN` | 一键清理：零长度LINE、空文本、PURGE、AUDIT |
| | `LB-PLOT` | 批量打印所有布局到PDF（A3横版） |
| | `LB-EXPORT` | 当前布局导出PDF |
| | `LB-AREA` | 选择多个对象，累加总面积 |

**用法:** `APPLOAD` → 选择 `cad_master.lsp` → 在命令行输入对应命令

### SCR 脚本（无需加载，适合简单操作）
| 文件 | 功能 |
|------|------|
| `图层标准化.scr` | 一键创建18个标准图层 |
| `批量打印A3.scr` | 布局1~3批量打印为PDF |
| `图纸清理.scr` | 删除零长度线 + PURGE + AUDIT |
| `批量导出DXF.scr` | 另存为DXF R2000格式 |

**用法:** 在CAD中 `SCRIPT` → 选择.scr文件

## 建议使用流程

```
1. 打开原始DWG
2. SCRIPT → 图纸清理.scr          # 先清理
3. APPLOAD → cad_master.lsp       # 加载LISP
4. LB-LAYER                       # 标准化图层
5. LB-DIMSTYLE                    # 设置标注样式
6. 手动调整有问题的元素
7. LB-PLOT → 批量打印             # 出图
```

## Mac 版 AutoCAD 注意
- LISP: 完全兼容
- SCR: 完全兼容
- 打印驱动: Mac 可能用 "AutoCAD PDF (General Documentation).pc3"
- 路径分隔符: Mac 用 `/`
