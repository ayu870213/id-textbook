"""감염내과 참고서 사이트 빌드 스크립트.

구글 드라이브 폴더에서 가장 최근에 올린 스프레드시트(용량표)와 문서(질환별 가이드)를 받아
웹용 데이터(data/*.json, data/img/*)로 바꾼 뒤 _site 폴더에 사이트를 만든다.

  drive.py        드라이브에서 원본 받기
  dosing_xlsx.py  용량표 → drugs.json
  guide_docx.py   가이드 → guides.json, 그림
  config/rules.json  약별 체중 규칙, 이름 예외, 가이드 분류, 기본 선택 약

로컬 테스트:  python scripts/build.py --xlsx 용량.xlsx --docx 가이드.docx --out _site
GitHub 자동화: 환경변수 GDRIVE_SA_KEY, GDRIVE_FOLDER_ID 사용
"""
import argparse, datetime as dt, glob, hashlib, json, os, shutil, sys, urllib.request

from common import ROOT, RULES_PATH, BuildError, load_rules
from dosing_xlsx import parse_xlsx
from guide_docx import convert_docx

KST = dt.timezone(dt.timedelta(hours=9))
WEB = os.path.join(ROOT, 'web')


def source_files():
    """사이트 결과에 영향을 주는 코드·설정 파일 (원본 제외)."""
    return sorted(glob.glob(os.path.join(WEB, '*'))) + [RULES_PATH] + \
        sorted(glob.glob(os.path.join(ROOT, 'scripts', '*.py')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx'); ap.add_argument('--docx'); ap.add_argument('--out', default='_site')
    a = ap.parse_args()
    rules = load_rules()
    work = os.path.join(ROOT, '_work'); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    if a.xlsx and a.docx:
        xp, dp = a.xlsx, a.docx
        mt = lambda p: dt.datetime.fromtimestamp(os.path.getmtime(p), dt.timezone.utc).isoformat()
        sheet = {'name': os.path.basename(xp), 'id': 'local', 'modifiedTime': mt(xp), 'createdTime': mt(xp)}
        doc = {'name': os.path.basename(dp), 'id': 'local', 'modifiedTime': mt(dp), 'createdTime': mt(dp)}
    else:
        from drive import fetch_from_drive
        xp, dp, sheet, doc = fetch_from_drive(os.environ['GDRIVE_FOLDER_ID'], work)

    def read(p):
        with open(p, 'rb') as f: return f.read()
    # 원본·화면·설정·빌드 코드 중 하나라도 바뀌면 달라지는 값 (정기 확인 때 배포 여부 판단)
    source_rev = hashlib.sha256(b''.join(read(p) for p in [xp, dp] + source_files())).hexdigest()[:16]
    out = os.path.join(ROOT, a.out)
    shutil.rmtree(out, ignore_errors=True); os.makedirs(os.path.join(out, 'data'))

    drugs = parse_xlsx(xp, rules)
    guides = convert_docx(dp, os.path.join(out, 'data', 'img'), rules)
    kst_date = lambda t: dt.datetime.fromisoformat(t.replace('Z', '+00:00')).astimezone(KST).strftime('%Y-%m-%d')
    revised = kst_date(max(sheet['modifiedTime'], doc['modifiedTime']))
    meta = {'revised': revised, 'source_rev': source_rev,
            'drugs_source': sheet['name'], 'drugs_uploaded': kst_date(sheet['createdTime']),
            'guides_source': doc['name'], 'guides_uploaded': kst_date(doc['createdTime']),
            'default_drug': rules['default_drug'],
            'built_at': dt.datetime.now(KST).isoformat(timespec='minutes')}

    def dump(o, name):
        with open(os.path.join(out, 'data', name), 'w', encoding='utf-8') as f:
            json.dump(o, f, ensure_ascii=False)
    dump({'source': sheet['name'], 'drugs': drugs}, 'drugs.json')
    dump({'source': doc['name'], 'sections': guides}, 'guides.json')
    dump(meta, 'meta.json')
    for p in glob.glob(os.path.join(WEB, '*')):
        shutil.copy(p, out)
    open(os.path.join(out, '.nojekyll'), 'w').close()

    # 정기 확인(schedule)일 때 바뀐 게 없으면 배포 생략
    changed = True
    site = os.environ.get('SITE_URL')
    if os.environ.get('GITHUB_EVENT_NAME') == 'schedule' and site:
        try:
            live = json.load(urllib.request.urlopen(site.rstrip('/') + '/data/meta.json', timeout=20))
            changed = live.get('source_rev') != source_rev
        except Exception:
            changed = True
    act = [d for d in drugs if d['status'] == 'active']
    print(f'용량표: {sheet["name"]} → 항생제 {len(act)}개, 용법 {sum(len(d["regimens"]) for d in act)}개')
    print(f'가이드: {doc["name"]} → 항목 {len(guides)}개, 표 {sum(s["tables"] for s in guides)}개, 그림 {sum(s["images"] for s in guides)}개')
    print(f'최종 개정일 {revised} · 변경 {"있음" if changed else "없음 (배포 생략)"}')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'changed={"true" if changed else "false"}\n')
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    try:
        main()
    except BuildError as e:
        print(f'::error::{e}')
        sys.exit(1)
