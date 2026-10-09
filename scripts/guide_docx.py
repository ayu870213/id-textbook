"""질환별 가이드(워드 문서) → 항목별 HTML과 그림."""
import html as H, io, os, re

import docx
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
import mammoth
from PIL import Image

from common import BuildError

GREY = {'808080', 'A5A5A5', 'BFBFBF', 'A6A6A6', 'D0CECE', '7F7F7F', 'AEAAAA', '767171', '595959', 'D9D9D9',
        '999999', '666666', 'B7B7B7', 'CCCCCC'}


def guide_group(title, rules):
    """가이드 항목의 목록 분류 (config/rules.json의 guide_groups)."""
    for g in rules['guide_groups']:
        if title.startswith(tuple(g.get('title_starts_with', ()))) or \
                any(k in title for k in g.get('title_contains', ())):
            return g['group']
    return rules['guide_group_default']


def convert_docx(path, img_dir, rules):
    d = docx.Document(path)
    st = d.styles.element
    for sid, name in [('Muted', 'Muted Text'), ('Alert', 'Alert Text')]:
        st.append(parse_xml(f'<w:style {nsdecls("w")} w:type="character" w:styleId="{sid}"><w:name w:val="{name}"/></w:style>'))
    for r in d.element.body.iter(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        if rpr is None: continue
        c = rpr.find(qn('w:color'))
        if c is None: continue
        v = (c.get(qn('w:val')) or '').upper()
        sty = 'Muted' if v in GREY else 'Alert' if v in ('FF0000', 'C00000') else None
        if not sty: continue
        rs = rpr.find(qn('w:rStyle'))
        if rs is None:
            rpr.insert(0, parse_xml(f'<w:rStyle {nsdecls("w")} w:val="{sty}"/>'))
        else:
            rs.set(qn('w:val'), sty)
    h1 = sum(1 for p in d.paragraphs if (p.style.name or '').lower() in ('heading 1', '제목 1'))
    if h1 == 0:
        raise BuildError('문서에 "제목 1" 스타일이 하나도 없습니다. 질환 제목에 제목 1을 지정해 주세요.')
    buf = io.BytesIO(); d.save(buf); buf.seek(0)

    os.makedirs(img_dir, exist_ok=True)
    imgs = []
    def conv(image):
        with image.open() as f: data = f.read()
        i = len(imgs)
        if image.content_type in ('image/jpeg', 'image/jpg'):
            fn = f'fig{i + 1:02d}.jpg'
            with open(os.path.join(img_dir, fn), 'wb') as f: f.write(data)
        else:
            im = Image.open(io.BytesIO(data))
            if im.mode not in ('RGB', 'RGBA'): im = im.convert('RGBA')
            fn = f'fig{i + 1:02d}.png'; im.save(os.path.join(img_dir, fn), optimize=True)
        imgs.append(fn)
        return {'src': 'data/img/' + fn, 'alt': ''}
    style_map = """
p[style-name='heading 1'] => h1:fresh
p[style-name='heading 2'] => h2:fresh
p[style-name='heading 3'] => h3:fresh
p[style-name='제목 1'] => h1:fresh
p[style-name='제목 2'] => h2:fresh
p[style-name='제목 3'] => h3:fresh
r[style-name='Muted Text'] => span.muted
r[style-name='Alert Text'] => span.alert
u => u
"""
    res = mammoth.convert_to_html(buf, style_map=style_map, convert_image=mammoth.images.img_element(conv))
    parts = re.split(r'(<h1>.*?</h1>)', res.value)
    out = []
    for i in range(1, len(parts), 2):
        title = H.unescape(re.sub('<[^>]+>', '', parts[i])).strip()
        body = parts[i + 1]
        sid = f's{len(out) + 1:02d}'
        subs = []
        def addid(m, sid=sid, subs=subs):
            k = len(subs) + 1
            txt = H.unescape(re.sub('<[^>]+>', '', m.group(2))).strip()
            subs.append({'level': int(m.group(1)), 'title': txt, 'anchor': f'{sid}-{k}'})
            return f'<h{m.group(1)} id="{sid}-{k}">{m.group(2)}</h{m.group(1)}>'
        body = re.sub(r'<h([23])>(.*?)</h\1>', addid, body)
        body = re.sub(r'<p>\s*</p>', '', body).strip()
        if not title: continue
        group = guide_group(title, rules)
        out.append({'id': sid, 'group': group, 'title': title, 'subsections': subs, 'html': body,
                    'tables': body.count('<table'), 'images': body.count('<img')})
    # 본문이 없는 항목(작성 중)은 숨김
    out = [s for s in out if re.sub('<[^>]+>', '', s['html']).strip()]
    order = rules['guide_group_order']
    out.sort(key=lambda s: order.index(s['group']))
    if len(out) < 3:
        raise BuildError(f'가이드 항목이 {len(out)}개뿐입니다. 제목 1 스타일을 확인해 주세요.')
    return out
