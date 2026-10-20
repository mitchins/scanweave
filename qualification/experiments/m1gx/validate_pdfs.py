#!/usr/bin/env python3
"""Structural, font, raster-resource and search checks for all GX PDFs."""
import json,re,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"qualification"));sys.path.insert(0,str(Path(__file__).resolve().parent))
from tools_env import qpdf_bin,qpdf_env,ots_bin
import trial
OUT=ROOT/"qualification/experiments/m1gx/300"

def run(args,env=None):
    return subprocess.run(args,check=True,text=True,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,env=env).stdout

def main():
    rows=[]
    for pdf in sorted(OUT.glob("*.pdf")):
        qproc=subprocess.run([qpdf_bin(),"--check",str(pdf)],text=True,
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=qpdf_env())
        q=qproc.stdout
        info=run(["pdfinfo",str(pdf)])
        fonts=run(["pdffonts",str(pdf)])
        images=run(["pdfimages","-list",str(pdf)])
        text=run(["pdftotext",str(pdf),"-"])
        pages=int(re.search(r"^Pages:\s+(\d+)",info,re.M).group(1))
        rows.append({"file":pdf.name,"bytes":pdf.stat().st_size,"pages":pages,
                     "qpdf_ok":qproc.returncode==0 and "No syntax or stream encoding errors found" in q,
                     "qpdf_output":q,
                     "pdfinfo_page_size":re.search(r"^Page size:\s+(.+)$",info,re.M).group(1),
                     "pdffonts":fonts,"pdfimages_list":images,
                     "extracted_nonwhitespace_chars":len(re.sub(r"\s+","",text))})
    font,qdf=trial.extract_embedded_font(OUT/"canonical-uniform-300.pdf")
    fm=re.search(rb"/FontFile2\s+(\d+)\s+0\s+R",qdf)
    obj=re.search(rb"\n"+fm.group(1)+rb" 0 obj\s*<<(.*?)>>\s*stream\n(.*?)\nendstream",qdf,re.S)
    with tempfile.TemporaryDirectory(prefix="m1gx-ots-") as td:
        path=Path(td)/"scanweave.ttf";path.write_bytes(obj.group(2))
        ots=run([ots_bin(),str(path)])
    result={"pdfs":rows,"o5_embedded_font_ots_valid":True,"ots_output":ots,
            "o5_font_glyph_program_count":len(font.getGlyphOrder()),
            "o5_qpdf_poppler_metadata_images_and_text_checked":True,
            "pdfium_render_and_text_checks":"see gx_metrics.json; this script does not invoke PDFium"}
    (OUT/"pdf-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"pdfs":len(rows),"all_qpdf_ok":all(r["qpdf_ok"] for r in rows),
                      "o5_ots_valid":True,"o5_glyph_programs":len(font.getGlyphOrder())},indent=2))
if __name__=="__main__":main()
