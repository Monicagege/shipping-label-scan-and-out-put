import re, io, zipfile, threading, unicodedata
from pathlib import Path
import fitz
import numpy as np
import zxingcpp
from PIL import Image

STATES=set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
_ocr=None
LOCK=threading.Lock()
def engine():
    global _ocr
    if _ocr is None:
        from rapidocr import RapidOCR
        _ocr=RapidOCR(params={'Global.model_root_dir':str(Path(__file__).parent/'models'),'EngineConfig.onnxruntime.intra_op_num_threads':2,'EngineConfig.onnxruntime.inter_op_num_threads':1})
    return _ocr

def recognize(image):
    out=engine()(np.array(image))
    if out.txts is None:return []
    return [{'text':str(t),'box':[float(min(p[0] for p in b)),float(min(p[1] for p in b)),float(max(p[0] for p in b)),float(max(p[1] for p in b))],'score':float(s)} for b,t,s in zip(out.boxes,out.txts,out.scores)]

def parse(blocks,barcodes,source):
    notes=[]
    text='\n'.join(b['text'] for b in blocks)
    codes=[]
    for t in barcodes+[b['text'] for b in blocks]:
        compact=re.sub(r'\s+','',t.upper())
        codes+=re.findall(r'1Z[A-Z0-9]{16}(?![A-Z0-9])',compact)
        codes+=re.findall(r'AZN\d+(?!\d)',compact)
    codes=list(dict.fromkeys(codes))
    carrier='UPS' if any(t.startswith('1Z') for t in codes) else 'CEVA' if any(t.startswith('AZN') for t in codes) else 'FedEx' if 'FEDEX' in text.upper() else '未知'
    if carrier=='FedEx':
        for t in barcodes:
            if re.fullmatch(r'\d{12}|\d{15}|\d{20}|\d{22}',t):codes.append(t)
        for b in blocks:
            m=re.search(r'(?:TRK\s*#?|TRACKING\s*[:#]?)\s*([\d ]+)',b['text'],re.I)
            if m:
                t=m[1].replace(' ','')
                if re.fullmatch(r'\d{12}|\d{15}|\d{20}|\d{22}',t):codes.append(t)
    codes=list(dict.fromkeys(codes));tracking=codes[0] if len(codes)==1 else ''
    if not tracking:notes.append('单号缺失或存在多个候选')
    anchors=[b for b in blocks if re.search(r'\bSHIP[\s.]*TO\b',b['text'],re.I)]
    split=False
    if not anchors:
        anchors=[b for b in blocks if re.fullmatch(r'SHIP[:：]?',b['text'].strip(),re.I)];split=True
    selected=[]
    if anchors:
        a=min(anchors,key=lambda b:b['box'][1]);x,y,x2,y2=a['box'];height=y2-y
        # Split CEVA anchor sits to the left of the name/address, at the same height.
        for b in blocks:
            bx,by,bx2,by2=b['box']
            if b is a:continue
            if split:
                keep=bx>=x2-height*.25 and by>=y-height*.5
            else:keep=bx>=x-height and by>=y+height*.25
            if keep and by<y+height*12:selected.append(dict(b))
        inline=re.sub(r'^.*?SHIP[\s.]*TO\s*[:：]?','',a['text'],flags=re.I).strip()
        if not split and inline:selected.insert(0,dict(a,text=inline))
    else:notes.append('未定位 SHIP TO 收件区域')
    selected.sort(key=lambda b:(b['box'][1],b['box'][0]))
    # Merge boxes on the same visual line without mixing sender and recipient areas.
    rows=[]
    for b in selected:
        cy=(b['box'][1]+b['box'][3])/2;h=b['box'][3]-b['box'][1]
        row=next((r for r in rows if abs(r[0]-cy)<h*.45),None)
        if row:row[1].append(b)
        else:rows.append([cy,[b]])
    lines=[' '.join(b['text'] for b in sorted(r[1],key=lambda b:b['box'][0])) for r in rows]
    city=state=zipcode='';ci=-1
    for i,line in enumerate(lines):
        m=re.match(r"^([A-Z][A-Z .'-]*?)\s*,?\s+([A-Z]{2})\s*,?\s+(\d{5}(?:\s*-\s*\d{4})?)\b",line,re.I)
        if m and m[2].upper() in STATES:
            city=m[1].strip(' ,');state=m[2].upper();zipcode=re.sub(r'\s','',m[3]);ci=i;break
    before=lines[:ci] if ci>=0 else lines
    ai=next((i for i,l in enumerate(before) if re.match(r'^\d+[A-Z]?(?:[-/]\d+)?\s+\S|^P\.?\s*O\.?\s+BOX',l,re.I)),-1)
    name=before[0] if ai>0 else ''
    normalized=''.join(c for c in unicodedata.normalize('NFKD',name) if not unicodedata.combining(c))
    if normalized!=name:
        notes.append('姓名含 OCR 重音字符，已规范化，请核对')
        name=normalized
    if re.search(r'\d',name):
        name=re.sub('[1-9]','',name.replace('0','O'));notes.append('姓名数字已修正，请核对')
    address=' '.join(before[ai:]) if ai>=0 and ci>=0 else ''
    if not name:notes.append('姓名待核对')
    if not address:notes.append('地址待核对')
    if ci<0:notes.append('城市 / 州 / 邮编待核对')
    relevant=[b for b in selected if ci<0 or b['box'][1]<=rows[ci][0]]
    if any(b['score']<.85 for b in relevant):notes.append('收件区域含低置信度文字')
    return dict(source=source,carrier=carrier,tracking=tracking,name=name,address=address,city=city,state=state,zip=zipcode,notes=notes,issues=notes[:],raw=text)

def process_pdf(blob,name):
    result=[]
    with fitz.open(stream=blob,filetype='pdf') as doc:
        if len(doc)>100:raise ValueError('单个 PDF 最多 100 页')
        for i,page in enumerate(doc):
            scale=min(2.5,2400/max(page.rect.width,page.rect.height))
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
            image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            blocks=recognize(image)
            bars=[b.text for b in zxingcpp.read_barcodes(image)]
            r=parse(blocks,bars,f'{name} · p{i+1}');result.append(r)
    return result

def process(blob,name):
    with LOCK:
        if name.lower().endswith('.pdf'):return process_pdf(blob,name)
        if not name.lower().endswith('.zip'):raise ValueError('仅支持 PDF / ZIP')
        result=[]
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            entries=[e for e in z.infolist() if not e.is_dir() and e.filename.lower().endswith('.pdf')]
            if not entries or len(entries)>100:raise ValueError('ZIP 需包含 1–100 个 PDF')
            if sum(e.file_size for e in entries)>150*1024**2:raise ValueError('ZIP 解压内容超过 150 MB')
            for e in entries:result.extend(process_pdf(z.read(e),name+' / '+e.filename))
        return result
