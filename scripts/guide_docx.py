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


def normalize_tables(html):
    """표 칸을 모두 일반 칸(td)으로 통일한다.
    구글 문서에서 내보낸 docx는 모든 행이 '머리 행'으로 표시되어 전부 th·thead로 나온다.
    원본 형식(구글 문서/워드)과 관계없이 화면 스타일이 같게 적용되도록 한다."""
    html = re.sub(r'</?thead>', '', html)
    html = re.sub(r'<th(?=[\s>])', '<td', html)
    return html.replace('</th>', '</td>')


def _outside_tables(html, fn):
    """표 안은 그대로 두고 표 밖 부분에만 fn을 적용한다."""
    parts = re.split(r'(<table>.*?</table>)', html, flags=re.S)
    return ''.join(p if p.startswith('<table>') else fn(p) for p in parts)


def _text(h):
    return H.unescape(re.sub('<[^>]+>', '', h)).strip()


def restructure(html):
    """문서에서 손으로 만든 계층을 일관된 제목·목록으로 바꾼다 (원본 문서는 그대로).
    - 굵은 글씨만 있는 글머리표 한 줄 (예: '• **치료**')  → h3 주제 제목
    - 통째로 굵은 짧은 문단 (예: '**1) 언제 검사를 해야 하나?**') → h4 소제목
    - '- '로 시작하는 문단이 이어지면 → 목록
    - 제목 2의 '폐렴 (1) 지역사회획득 폐렴' → '1. 지역사회획득 폐렴' (질환명 반복 제거)
    - 문단 맨 앞의 그림은 따로 떼어 낸다 (그림 뒤 글이 위 규칙을 따르도록)"""
    def h2_number(m):
        inner = m.group(1)
        mm = re.match(r'(.+?)\s*\((\d+)\)\s*(.+)$', inner, re.S)
        return f'<h2>{mm[2]}. {mm[3]}</h2>' if mm else m.group(0)

    def topic(m):
        return f'<h3>{m.group(1).strip()}</h3>' if _text(m.group(1)) else m.group(0)

    def subhead(m):
        inner = m.group(1)
        t = _text(inner)
        if not t or len(t) > 80 or '<u>' in inner or '<img' in inner:
            return m.group(0)
        return f'<h4>{inner.strip()}</h4>'

    def dash_lists(h):
        h = re.sub(r'<p>((?:<(?:span|strong|u|em)\b[^>]*>)*)\s*[-–•]\s+(.*?)</p>', r'<li class="d">\1\2</li>', h, flags=re.S)
        h = re.sub(r'((?:<li class="d">.*?</li>)+)', r'<ul>\1</ul>', h, flags=re.S)
        return h.replace('<li class="d">', '<li>')

    def fix(h):
        h = re.sub(r'<p>(?:<strong>)?(<img [^>]*/>)(?:</strong>)?(.*?)</p>',
                   lambda m: f'<p>{m[1]}</p>' + (f'<p>{m[2].strip()}</p>' if _text(m[2]) else ''), h, flags=re.S)
        h = re.sub(r'<h2>(.*?)</h2>', h2_number, h, flags=re.S)
        h = re.sub(r'<ul><li><strong>((?:(?!</?(?:li|ul|strong)\b).)*?)</strong>\s*</li></ul>', topic, h, flags=re.S)
        h = re.sub(r'<p><strong>((?:(?!</?(?:p|strong)\b).)*?)</strong></p>', subhead, h, flags=re.S)
        return dash_lists(h)

    return _outside_tables(html, fix)


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
    parts = re.split(r'(<h1>.*?</h1>)', normalize_tables(res.value))
    out = []
    for i in range(1, len(parts), 2):
        title = H.unescape(re.sub('<[^>]+>', '', parts[i])).strip()
        body = restructure(parts[i + 1])
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
