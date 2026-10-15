from __future__ import annotations
import argparse,json,re
from pathlib import Path

def audit(pdf_path,include_preview=False):
    import pdfplumber
    pages=[]
    with pdfplumber.open(pdf_path) as pdf:
        for i,p in enumerate(pdf.pages,1):
            text=p.extract_text() or ""
            cid=len(re.findall(r"\(cid:\d+\)",text)); replacement=text.count("\ufffd")
            cjk=len(re.findall(r"[\u3400-\u9fff]",text)); digits=len(re.findall(r"\d",text))
            pages.append({"page":i,"text_chars":len(text),"cjk_chars":cjk,"digits":digits,"cid_markers":cid,"replacement_chars":replacement,**({"preview":text[:500]} if include_preview else {})})
    flags=[]
    if not any(p["text_chars"] for p in pages): flags.append("no_text_layer_render_and_ocr")
    if any(p["cid_markers"] or p["replacement_chars"] for p in pages): flags.append("encoded_or_corrupt_text_render_and_ocr")
    if any(p["text_chars"]<40 for p in pages): flags.append("sparse_page_text_check_image_and_ocr")
    # Chinese semantic corruption can remain valid Unicode; native must visually compare every critical table.
    flags.append("native_must_verify_chinese_and_table_alignment")
    return {"file":Path(pdf_path).name,"page_count":len(pages),"flags":sorted(set(flags)),"pages":pages}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input_dir"); ap.add_argument("--out"); ap.add_argument("--include-preview",action="store_true"); a=ap.parse_args()
    paths=sorted(Path(a.input_dir).glob("*.pdf")); result={"pdf_count":len(paths),"documents":[audit(p,a.include_preview) for p in paths]}
    data=json.dumps(result,ensure_ascii=False,indent=2)
    if a.out: Path(a.out).write_text(data+"\n",encoding="utf-8")
    print(data)
if __name__=="__main__": main()

