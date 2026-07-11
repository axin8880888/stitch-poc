#!/usr/bin/env python3
"""
DXF 重建器
根据解析后的结构化数据重新生成 DXF
"""

import os

def rebuild_dxf(parser, output_path):
    """根据解析器数据重建 DXF"""
    
    lines = []
    
    # ---- HEADER ----
    lines.append("0\nSECTION\n2\nHEADER")
    lines.append("9\n$ACADVER\n1\nAC1027")  # AutoCAD 2013
    lines.append("9\n$DWGCODEPAGE\n3\ngb2312")
    lines.append("9\n$INSUNITS\n70\n4")  # mm
    lines.append("0\nENDSEC")
    
    # ---- TABLES ----
    lines.append("0\nSECTION\n2\nTABLES")
    
    # 图层表
    lines.append("0\nTABLE\n2\nLAYER\n70")
    lines.append(str(len(parser.layers)))
    
    for name, info in sorted(parser.layers.items()):
        color = info.get('color', 7)
        lineweight = info.get('lineweight', 13)
        linetype = info.get('linetype', 'Continuous')
        state = info.get('state', 0)
        
        lines.append(
            f"0\nLAYER\n2\n{name}\n70\n{state}\n62\n{color}\n6\n{linetype}\n370\n{lineweight}"
        )
    
    lines.append("0\nENDTAB\n0\nENDSEC")
    
    # ---- BLOCKS ----
    lines.append("0\nSECTION\n2\nBLOCKS")
    
    for name, blk in sorted(parser.blocks.items()):
        lines.append(f"0\nBLOCK\n8\n{blk.get('layer','0')}\n2\n{name}\n70\n0\n10\n{blk['base_x']}\n20\n{blk['base_y']}\n0\nENDBLK")
    
    lines.append("0\nENDSEC")
    
    # ---- ENTITIES ----
    lines.append("0\nSECTION\n2\nENTITIES")
    
    for ent in parser.entities:
        try:
            etype = ent['type']
            layer = ent.get('layer', '0')
            color = ent.get('color', 256)
            
            if etype == 'LINE':
                lines.append(f"0\nLINE\n8\n{layer}\n62\n{color}\n10\n{ent['x1']}\n20\n{ent['y1']}\n30\n{ent.get('z1',0)}\n11\n{ent['x2']}\n21\n{ent['y2']}\n31\n{ent.get('z2',0)}")
            
            elif etype == 'CIRCLE':
                lines.append(f"0\nCIRCLE\n8\n{layer}\n62\n{color}\n10\n{ent['cx']}\n20\n{ent['cy']}\n30\n{ent.get('cz',0)}\n40\n{ent['r']}")
            
            elif etype == 'ARC':
                lines.append(f"0\nARC\n8\n{layer}\n62\n{color}\n10\n{ent['cx']}\n20\n{ent['cy']}\n30\n{ent.get('cz',0)}\n40\n{ent['r']}\n50\n{ent['angle_start']}\n51\n{ent['angle_end']}")
            
            elif etype == 'INSERT':
                name = ent.get('block_name', '')
                x = ent.get('insert_x', 0)
                y = ent.get('insert_y', 0)
                sx = ent.get('scale_x', 1)
                sy = ent.get('scale_y', 1)
                rot = ent.get('rotation', 0)
                lines.append(f"0\nINSERT\n8\n{layer}\n62\n{color}\n2\n{name}\n10\n{x}\n20\n{y}\n41\n{sx}\n42\n{sy}\n50\n{rot}")
            
            elif etype == 'TEXT':
                txt = ent.get('text', '')
                x = ent.get('x', 0)
                y = ent.get('y', 0)
                h = ent.get('height', 2.5)
                rot = ent.get('rotation', 0)
                style = ent.get('style', 'Standard')
                lines.append(f"0\nTEXT\n8\n{layer}\n62\n{color}\n10\n{x}\n20\n{y}\n40\n{h}\n50\n{rot}\n7\n{style}\n1\n{txt}")
            
            elif etype == 'MTEXT':
                txt = ent.get('text', '')
                x = ent.get('x', 0)
                y = ent.get('y', 0)
                h = ent.get('height', 2.5)
                rot = ent.get('rotation', 0)
                style = ent.get('style', 'Standard')
                attach = ent.get('attachment', 1)
                lines.append(f"0\nMTEXT\n8\n{layer}\n62\n{color}\n10\n{x}\n20\n{y}\n40\n{h}\n50\n{rot}\n7\n{style}\n71\n{attach}\n1\n{txt}")
            
            elif etype == 'DIMENSION':
                dt = ent.get('dim_type', 0)
                dx = ent.get('def_x', 0)
                dy = ent.get('def_y', 0)
                tx = ent.get('text_x', 0)
                ty = ent.get('text_y', 0)
                txt = ent.get('text', '')
                blk = ent.get('block', '')
                style = ent.get('style', 'Standard')
                lines.append(f"0\nDIMENSION\n8\n{layer}\n62\n{color}\n2\n{blk}\n3\n{style}\n10\n{dx}\n20\n{dy}\n11\n{tx}\n21\n{ty}\n70\n{dt}\n1\n{txt}")
            
            elif etype == 'LWPOLYLINE':
                closed = ent.get('closed', 0)
                elev = ent.get('elevation', 0)
                cw = ent.get('const_width', 0)
                verts = ent.get('vertices', [])
                lines.append(f"0\nLWPOLYLINE\n8\n{layer}\n62\n{color}\n90\n{len(verts)}\n70\n{closed}\n38\n{elev}\n43\n{cw}")
                for vx, vy in verts:
                    lines.append(f"10\n{vx}\n20\n{vy}")
            
            elif etype == 'POINT':
                x = float(ent['props'].get(10, 0))
                y = float(ent['props'].get(20, 0))
                lines.append(f"0\nPOINT\n8\n{layer}\n62\n{color}\n10\n{x}\n20\n{y}")
            
        except Exception as e:
            print(f"  ⚠️  跳过实体 {ent.get('type','?')}: {e}")
    
    lines.append("0\nENDSEC\n0\nEOF")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"✅ 重建 DXF: {output_path} ({len(lines)}行)")
        return True
    except Exception as e:
        print(f"❌ 写入失败: {e}")
        return False
