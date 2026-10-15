# PDF 文本层批量检查

运行 `python scripts/audit_pdf_text.py <PDF目录> --out <报告.json>`，输出逐页可抽取字符数、数字/CJK 字符数、CID 标记、替换字符及预览。无文本层、稀疏页、CID/替换字符均要求渲染/OCR。有效 Unicode 中文仍可能是字体映射乱码，必须 native 对照原页。
