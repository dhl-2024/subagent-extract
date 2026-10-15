from __future__ import annotations
import argparse,json,re
from pathlib import Path
from common import load_json,write_json,ExtractError
ANNOTATION=re.compile(r"共\s*(\d+)\s*块",re.I)
def read_dxf_entities(path):
    lines=Path(path).read_text(encoding="utf-8-sig",errors="replace").splitlines(); pairs=[]
    for i in range(0,len(lines)-1,2):
        try: pairs.append((int(lines[i].strip()),lines[i+1].strip()))
        except ValueError: continue
    entities=[]; current=None
    for code,value in pairs:
        if code==0:
            if current is not None: entities.append(current)
            current={"type":value,"pairs":[]}
        elif current is not None: current["pairs"].append((code,value))
    if current is not None: entities.append(current)
    return entities
def dxf_annotations(entities):
    found=[]
    for ent in entities:
        if ent["type"] in ("TEXT","MTEXT","ATTRIB","ATTDEF"):
            txt="".join(v for c,v in ent["pairs"] if c in (1,3))
            m=ANNOTATION.search(txt)
            if m: found.append({"count":int(m.group(1)),"text":m.group(0)})
    return found
def dxf_insert_count(entities,review):
    layers=set(review.get("component_layers",[])); blocks=set(review.get("component_blocks",[]))
    if not layers and not blocks: return None
    hits=[]
    for ent in entities:
        if ent["type"]!="INSERT": continue
        layer=next((v for c,v in ent["pairs"] if c==8),"")
        block=next((v for c,v in ent["pairs"] if c==2),"")
        if layer in layers or block in blocks: hits.append((layer,block))
    source=sorted({layer for layer,_ in hits})
    return {"count":len(hits),"source_layer":source[0] if len(source)==1 else None,"source_blocks":sorted({block for _,block in hits})}
def count_modules(drawing_path,native_result_json=None):
    p=Path(drawing_path); ext=p.suffix.lower()
    if ext not in (".pdf",".dxf"): raise ExtractError("E4001",f"不支持排布图格式 {ext or '(无扩展名)'}；支持 PDF/DXF",file=str(p),supported=["PDF","DXF"])
    if not p.is_file(): raise ExtractError("E3001","排布图文件不存在或不可读",file=str(p),attempted=["L0_annotation","L1_dxf_block","L2_pdf_vector","L3_visual"])
    recognition=native_result_json if isinstance(native_result_json,dict) else (load_json(native_result_json) if native_result_json else {})
    annotation=None; entities=[]; l1=None
    if ext==".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(p) as pdf: text="\n".join(page.extract_text() or "" for page in pdf.pages)
            m=ANNOTATION.search(text)
            if m: annotation={"count":int(m.group(1)),"text":m.group(0)}
        except Exception: pass
    else:
        try:
            entities=read_dxf_entities(p); notes=dxf_annotations(entities)
            if len({n["count"] for n in notes})==1 and notes: annotation=notes[0]
            elif len({n["count"] for n in notes})>1: raise ExtractError("E3002","DXF 图面存在互相矛盾的总数标注",file=str(p),annotations=notes)
            l1=dxf_insert_count(entities,recognition)
        except ExtractError: raise
        except Exception as e: raise ExtractError("E3001",f"DXF 解析失败：{e}",file=str(p),attempted=["L0_annotation","L1_dxf_block","L2_pdf_vector","L3_visual"])
    warnings=[]
    if annotation:
        count=annotation["count"]; path="L0_annotation"; conf="extracted"; source=None
        other=l1["count"] if l1 else recognition.get("module_count")
        if other is not None and other!=count: warnings.append({"code":"W3002","annotation_count":count,"recognized_count":other,"message":"标注与自动识别不一致；按 L0 标注值输出"})
    elif l1:
        count=l1["count"]; path="L1_dxf_block"; conf=recognition.get("confidence","extracted"); source=l1["source_layer"]
    elif recognition.get("module_count") is not None:
        count=recognition["module_count"]; path=recognition.get("recognition_path")
        if path not in ("L1_dxf_block","L2_pdf_vector","L3_visual"): raise ExtractError("E3001","native 识别结果缺少有效链路标记",attempted=["L1_dxf_block","L2_pdf_vector","L3_visual"])
        conf=recognition.get("confidence","extracted"); source=recognition.get("source_layer")
    else: raise ExtractError("E3001","无法可靠识别组件数量；已检查 L0 标注及可用 DXF L1 图块，需 native 依次判断 L1 图块语义、L2 PDF 矢量、L3 视觉链路。",file=str(p),attempted=["L0_annotation","L1_dxf_block","L2_pdf_vector","L3_visual"])
    if not isinstance(count,int) or count<=0: raise ExtractError("E3001","组件数量必须是正整数",count=count)
    density=recognition.get("density")
    if not isinstance(density,(int,float)): raise ExtractError("INPUT_ERROR","需求要求 layout.json 必须带数值 density，但排布资料/复核结果未提供可核对的密度。请提供可计算屋面范围或确认的密度值。",file=str(p))
    model=recognition.get("module_model","")
    layout={"module_count":count,"module_model":model,"drawing_annotation":annotation["text"] if annotation else recognition.get("drawing_annotation"),"density":density,"confidence":conf,"source_layer":source,"recognition_path":path}
    return {"layout":layout,"warnings":warnings}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("drawing_path"); ap.add_argument("--native-result-json"); ap.add_argument("--out-path"); a=ap.parse_args()
    try:
        result=count_modules(a.drawing_path,a.native_result_json)
        if a.out_path: write_json(a.out_path,result["layout"])
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except ExtractError as e: print(json.dumps({"status":"failed","errors":[e.as_dict()]},ensure_ascii=False)); raise SystemExit(2)
if __name__=="__main__": main()
