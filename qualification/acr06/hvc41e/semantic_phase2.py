"""Native semantics, original resources, PDF validation and byte accounting."""
import pathlib,json,hashlib,subprocess,os,sys
import pikepdf,pypdfium2 as pdfium
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';baseline=R/'local/ink33r/historical.pdf';candidate=L/'historical-composed.pdf';sha=lambda b:hashlib.sha256(b).hexdigest();rows=[r for r in json.loads((E/'review-decisions.json').read_text()) if r['decision']=='accept'];sys.path.insert(0,str(R/'ink33r'));from prepare import chars_from_hocr
side=json.loads((R/'local/ink33r/historical.pdf.json').read_text());words=[w for line in chars_from_hocr(side['pages'][0]['hocr']) for w in line['words']]
def pdfium_text(path):
 doc=pdfium.PdfDocument(str(path));a=[]
 for page in doc:
  t=page.get_textpage();a.append(t.get_text_range());t.close();page.close()
 doc.close();return a
def pdfium_search(path,query):
 doc=pdfium.PdfDocument(str(path));p=doc[0];t=p.get_textpage();s=t.search(query);hits=[]
 while (z:=s.get_next()) is not None:hits.append(z)
 s.close();t.close();p.close();doc.close();return hits
bt=pdfium_text(baseline);ct=pdfium_text(candidate);queries=['Bacharias'];
for r in rows:
 word=''.join(x['text'] for x in words[r['word_index']]['chars']).strip()
 if len(word)>=3 and word not in queries and pdfium_search(baseline,word):queries.append(word)
 if len(queries)==6:break
search=[{'word':q,'baseline_hits':pdfium_search(baseline,q),'candidate_hits':pdfium_search(candidate,q),'from_accepted_word':q!='Bacharias'} for q in queries]
def pop(path,i):return subprocess.check_output(['pdftotext','-f',str(i),'-l',str(i),'-enc','UTF-8',str(path),'-'])
def resource(path):
 pdf=pikepdf.open(path);out=[]
 for page in pdf.pages:
  cont=page.Contents;streams=list(cont) if isinstance(cont,pikepdf.Array) else [cont];images={str(k):sha(v.read_raw_bytes()) for k,v in page.Resources.get('/XObject',pikepdf.Dictionary()).items() if str(v.get('/Subtype'))=='/Image'};fonts={}
  for name,font in page.Resources.get('/Font',pikepdf.Dictionary()).items():
   ft={'subtype':str(font.get('/Subtype')),'encoding':str(font.get('/Encoding')),'to_unicode_sha256':sha(font.ToUnicode.read_bytes()) if font.get('/ToUnicode') else None,'descendants':[]}
   for sub in font.get('/DescendantFonts',[]):
    desc=sub.get('/FontDescriptor',pikepdf.Dictionary());m=sub.get('/CIDToGIDMap');f=desc.get('/FontFile2');ft['descendants'].append({'subtype':str(sub.get('/Subtype')),'cid_to_gid_sha256':sha(m.read_bytes()) if m and isinstance(m,pikepdf.Stream) else str(m),'font_program_sha256':sha(f.read_bytes()) if f else None,'widths':str(sub.get('/W')),'default_width':str(sub.get('/DW'))})
   fonts[str(name)]=ft
  out.append({'content_decoded':list(map(lambda z:sha(z.read_bytes()),streams)),'content_raw':list(map(lambda z:sha(z.read_raw_bytes()),streams)),'images':images,'fonts':fonts})
 pdf.close();return out
br=resource(baseline);cr=resource(candidate);env=os.environ.copy();env['LD_LIBRARY_PATH']='/data/coding/scanweave/tools/dist/lib';q=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(candidate)],env=env,capture_output=True,text=True);pdffonts=subprocess.check_output(['pdffonts',str(candidate)]).decode();pdf=pikepdf.open(candidate);page=pdf.pages[0];pat=page.Resources.Pattern.Research41E;f=pat.Resources.Font.FR;content=page.Contents;glyphstreams=[v for v in f.CharProcs.values()];font_structure={'subtype':str(f.Subtype),'charproc_count':len(glyphstreams),'width_count':len(f.Widths),'first_char':int(f.FirstChar),'last_char':int(f.LastChar),'font_matrix':str(f.FontMatrix),'charproc_raw_bytes':sum(len(v.read_raw_bytes()) for v in glyphstreams),'charproc_decoded_bytes':sum(len(v.read_bytes()) for v in glyphstreams),'pattern_raw_bytes':len(pat.read_raw_bytes()),'pattern_decoded_bytes':len(pat.read_bytes()),'patch_stream_raw_bytes':len(content[1].read_raw_bytes()),'patch_stream_decoded_bytes':len(content[1].read_bytes()),'invocation_raw_bytes':len(content[2].read_raw_bytes()),'invocation_decoded_bytes':len(content[2].read_bytes())};program=f.get('/FontFile2')
# OTS applies to the original TrueType program; the embedded Type 3 has PDF charprocs and no OTS font file.
original=page.Resources.Font.F1.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes();fontfile=L/'baseline-font.ttf';fontfile.write_bytes(original);ots=subprocess.run(['/data/coding/scanweave/tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(fontfile)],capture_output=True,text=True);pdf.close();streams_total=font_structure['charproc_raw_bytes']+font_structure['pattern_raw_bytes']+font_structure['patch_stream_raw_bytes']+font_structure['invocation_raw_bytes'];out={'baseline_sha256':sha(baseline.read_bytes()),'candidate_sha256':sha(candidate.read_bytes()),'baseline_bytes':baseline.stat().st_size,'candidate_bytes':candidate.stat().st_size,'document_delta_bytes':candidate.stat().st_size-baseline.stat().st_size,'new_stream_raw_bytes':streams_total,'remaining_delta_serialization_and_objects':candidate.stat().st_size-baseline.stat().st_size-streams_total,'pdfium_page_text_identical':[x==y for x,y in zip(bt,ct)],'poppler_page_text_identical':[pop(baseline,i)==pop(candidate,i) for i in range(1,6)],'pdfium_search':search,'baseline_content_decoded_equal':[x['content_decoded'][0]==y['content_decoded'][0] for x,y in zip(br,cr)],'baseline_content_raw_equal':[x['content_raw'][0]==y['content_raw'][0] for x,y in zip(br,cr)],'image_streams_equal':[x['images']==y['images'] for x,y in zip(br,cr)],'original_fonts_equal':[x['fonts']==y['fonts'] for x,y in zip(br,cr)],'original_resources':br,'candidate_resources':cr,'type3_font':font_structure,'type3_ots':'not applicable: PDF Type 3 character procedures have no standalone OTS font program','original_truetype_ots_exit':ots.returncode,'original_truetype_ots_output':(ots.stdout+ots.stderr).strip(),'qpdf_exit':q.returncode,'qpdf_output':(q.stdout+q.stderr).strip(),'pdffonts':pdffonts,'ocr_stub_not_invoked':not (L/'ocr-invoked').exists()};(E/'semantic-phase2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('original_resources','candidate_resources')},indent=2))
