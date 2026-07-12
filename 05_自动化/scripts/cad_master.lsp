; ============================================================
; LISP 批处理脚本集 — CAD Master 自动化
; 适用: AutoCAD 2000+
; 用法: APPLOAD → 选择.lsp文件 → 输入对应命令
;
; 脚本清单:
;   LB-LAYER    — 图层标准化（按Guoxin规范）
;   LB-DIMSTYLE — 标注样式设置
;   LB-PLOT     — 批量打印A3
;   LB-CLEAN    — 图纸清理
;   LB-EXPORT   — 一键导出PDF
;   LB-AREA     — 选对象计算总面积
; ============================================================

(defun C:LB-LAYER (/)
  ; 图层标准化 — 创建/修复标准图层体系
  (setq *layers* '(
    ("0"           7 "CONTINUOUS"    0.0)
    ("A-WALL"      7 "CONTINUOUS"    0.35)
    ("A-WALL-H"    3 "HIDDEN"        0.25)
    ("A-COLS"      1 "CONTINUOUS"    0.35)
    ("A-DOOR"      4 "CONTINUOUS"    0.18)
    ("A-WINDW"     4 "CONTINUOUS"    0.18)
    ("A-DIMS"      3 "CONTINUOUS"    0.13)
    ("A-TEXT"      7 "CONTINUOUS"    0.13)
    ("A-NOTE"      6 "CONTINUOUS"    0.13)
    ("A-HATCH"     8 "CONTINUOUS"    0.13)
    ("A-AXIS"      2 "CENTER"        0.13)
    ("A-GRID"      8 "CONTINUOUS"    0.05)
    ("A-ANNO"      6 "CONTINUOUS"    0.13)
    ("A-TTLB"      7 "CONTINUOUS"    0.25)
    ("P-FURN"      6 "CONTINUOUS"    0.13)
    ("P-PLMB"      4 "CONTINUOUS"    0.13)
    ("P-ELEC"      1 "CONTINUOUS"    0.13)
    ("S-DEMO"      1 "PHANTOM"       0.18)
  ))

  (prompt "\n=== LB-LAYER: 建立标准图层 ===\n")
  (foreach layer *layers*
    (setq name   (nth 0 layer)
          color  (nth 1 layer)
          ltype  (nth 2 layer)
          lwidth (nth 3 layer))
    (if (tblsearch "LAYER" name)
      (progn
        (setvar "CLAYER" name)
        (command "_.-layer" "_color" color name "")
        (command "_.-layer" "_ltype" ltype name "")
        (command "_.-layer" "_lw" lwidth name "")
        (prompt (strcat "  ✅ 已更新: " name "\n"))
      )
      (progn
        (command "_.-layer" "_new" name "_color" color name
                 "_ltype" ltype name "_lw" lwidth name "")
        (prompt (strcat "  ✅ 已创建: " name "\n"))
      )
    )
  )
  (setvar "CLAYER" "0")
  (prompt "\n=== 图层标准化完成 ===\n")
  (princ)
)

; ============================================================
(defun C:LB-DIMSTYLE (/)
  ; 标注样式设置 — 1:50/1:100两种常用比例
  (prompt "\n=== LB-DIMSTYLE: 设置标注样式 ===\n")
  
  ; 创建 HG-100 (1:100比例)
  (if (not (tblsearch "DIMSTYLE" "HG-100"))
    (progn
      (command "_.-dimstyle" "_save" "HG-100")
      (setvar "DIMSCALE" 100)
      (setvar "DIMTXT" 2.5)
      (setvar "DIMGAP" 0.625)
      (setvar "DIMASZ" 2.5)
      (setvar "DIMCEN" 2.5)
      (setvar "DIMEXE" 1.25)
      (setvar "DIMEXO" 0.625)
      (setvar "DIMTAD" 1)
      (setvar "DIMTIH" 0)
      (setvar "DIMTOH" 0)
      (setvar "DIMDEC" 0)
      (setvar "DIMTDEC" 0)
      (setvar "DIMALT" 0)
      (command "_.-dimstyle" "_save" "HG-100")
      (prompt "  ✅ 已创建 HG-100 (1:100)\n")
    )
  )
  
  ; 创建 HG-50 (1:50比例)
  (if (not (tblsearch "DIMSTYLE" "HG-50"))
    (progn
      (setvar "DIMSCALE" 50)
      (setvar "DIMTXT" 2.5)
      (setvar "DIMGAP" 0.625)
      (setvar "DIMASZ" 2.5)
      (setvar "DIMCEN" 2.5)
      (setvar "DIMEXE" 1.25)
      (setvar "DIMEXO" 0.625)
      (setvar "DIMTAD" 1)
      (setvar "DIMTIH" 0)
      (setvar "DIMTOH" 0)
      (command "_.-dimstyle" "_save" "HG-50")
      (prompt "  ✅ 已创建 HG-50 (1:50)\n")
    )
  )
  
  (setvar "DIMSCALE" 100)
  (setvar "DIMSTYLE" "HG-100")
  (prompt "\n=== 标注样式设置完成 ===\n")
  (princ)
)

; ============================================================
(defun C:LB-CLEAN (/)
  ; 图纸清理 — 删除多余元素
  (prompt "\n=== LB-CLEAN: 清理图纸 ===\n")
  
  ; 1. 清理0长度几何体
  (setq ss (ssget "X" '((0 . "LINE") (-4 . "=") (10 0.0 0.0 0.0) (11 0.0 0.0 0.0))))
  (if ss (progn (command "_.erase" ss "") (prompt (strcat "  删除零长度LINE: " (itoa (sslength ss)) "个\n"))))
  
  ; 2. 清理空文本
  (setq ss (ssget "X" '((0 . "TEXT,MTEXT") (1 . ""))))
  (if ss (progn (command "_.erase" ss "") (prompt (strcat "  删除空文本: " (itoa (sslength ss)) "个\n"))))
  
  ; 3. 冗余图元清理
  (command "_.-purge" "_all" "" "_no")
  (command "_.-purge" "_regapps" "" "_no")
  
  (prompt "  ✅ PURGE 完成\n")
  
  ; 4. 审计修复
  (setvar "AUDITCTL" 0)
  (command "_.audit" "_yes")
  (prompt "  ✅ AUDIT 完成\n")
  
  (prompt "\n=== 清理完成 ===\n")
  (princ)
)

; ============================================================
(defun C:LB-PLOT (/)
  ; 批量打印 — A3横版 1:100
  (setq *plot-cfg* (list
    (cons "printer" "DWG To PDF.pc3")
    (cons "papersize" "ISO_A3_(420.00_x_297.00_MM)")
    (cons "drawing_orientation" "_landscape")
    (cons "plot_style" "monochrome.ctb")
    (cons "plot_area" "_extents")
    (cons "plot_scale" 1)
    (cons "center" "_yes")
  ))
  
  (prompt "\n=== LB-PLOT: 批量打印 ===\n")
  (setq ss (ssget "X" '((0 . "LAYOUT"))))
  
  (if ss
    (progn
      (setq i 0)
      (while (setq layout (ssname ss i))
        (setq name (cdr (assoc 2 (entget layout))))
        (if (not (wcmatch name "*Model*"))
          (progn
            (setvar "CTAB" name)
            (command "_.-plot" "_yes" "" "DWG To PDF.pc3" "ISO_A3_(420.00_x_297.00_MM)"
                     "_m" "_landscape" "_no" "_extents" "_fit" "_center" "_yes"
                     "monochrome.ctb" "_yes" "" "_no" "_no" "_no" "_yes" "_yes")
            (prompt (strcat "  ✅ 已打印: " name "\n"))
          )
        )
        (setq i (1+ i))
      )
    )
    (prompt "  无布局\n")
  )
  (prompt "\n=== 批量打印完成 ===\n")
  (princ)
)

; ============================================================
(defun C:LB-EXPORT (/)
  ; 一键导出PDF — 当前布局
  (prompt "\n=== LB-EXPORT: 导出PDF ===\n")
  (setq lname (getvar "CTAB"))
  (setq fname (strcat (getvar "DWGNAME") "_" lname ".pdf"))
  (command "_.-export" "_pdf" fname "_m" "_current" "_w" "0,0" "420,297" "_fit" "_center" "_yes" "monochrome.ctb" "" "")
  (prompt (strcat "  ✅ PDF: " fname "\n"))
  (princ)
)

; ============================================================
(defun C:LB-AREA (/)
  ; 累加选择对象面积
  (setq ss (ssget '((0 . "LWPOLYLINE,POLYLINE,CIRCLE,ELLIPSE"))))
  (if ss
    (progn
      (setq total 0 i 0)
      (while (setq e (ssname ss i))
        (command "_.area" "_o" e)
        (setq total (+ total (getvar "AREA")))
        (setq i (1+ i))
      )
      (prompt (strcat "\n=== 选择对象: " (itoa i) "个 ===\n"))
      (prompt (strcat "  总面积: " (rtos total 2 0) " mm²\n"))
      (prompt (strcat "          " (rtos (/ total 1e6) 2 2) " m²\n"))
    )
    (prompt "\n  未选择对象\n")
  )
  (princ)
)

; ============================================================
; 加载提示
(prompt "\n============================================\n")
(prompt "  CAD Master 自动化脚本已加载\n")
(prompt "  命令: LB-LAYER, LB-DIMSTYLE, LB-PLOT\n")
(prompt "        LB-CLEAN, LB-EXPORT, LB-AREA\n")
(prompt "============================================\n")
(princ)
