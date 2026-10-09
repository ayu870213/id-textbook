"""build.py 결과가 기준본(tests/baseline/)과 같은지 확인한다.

samples/에 있는 원본으로 빌드해 data/*.json과 그림을 기준본과 비교한다.
원본과 기준본은 로컬에만 둔다(.gitignore).

  기준본 저장:  python tests/compare_build.py --save
  비교:         python tests/compare_build.py
"""
import glob, hashlib, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'tests', 'baseline')


def build(out):
    xlsx = glob.glob(os.path.join(ROOT, 'samples', '*.xlsx'))
    docx = glob.glob(os.path.join(ROOT, 'samples', '*.docx'))
    if len(xlsx) != 1 or len(docx) != 1:
        sys.exit('samples/에 .xlsx와 .docx가 하나씩 있어야 합니다.')
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build.py'),
                    '--xlsx', xlsx[0], '--docx', docx[0], '--out', out],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


def digest(data_dir):
    """비교 대상: 용량·가이드 데이터와 그림. 빌드 시각·hash가 든 meta.json은 뺀다."""
    out = {}
    for f in ('drugs.json', 'guides.json'):
        with open(os.path.join(data_dir, f), encoding='utf-8') as fh:
            out[f] = json.load(fh)
    for p in sorted(glob.glob(os.path.join(data_dir, 'img', '*'))):
        with open(p, 'rb') as fh:
            out['img/' + os.path.basename(p)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def main():
    tmp = tempfile.mkdtemp()
    try:
        out = os.path.relpath(os.path.join(tmp, 'site'), ROOT)
        build(out)
        data = os.path.join(ROOT, out, 'data')
        if '--save' in sys.argv:
            shutil.rmtree(BASE, ignore_errors=True)
            shutil.copytree(data, BASE)
            print(f'기준본 저장: {BASE}')
            return
        new, old = digest(data), digest(BASE)
        diff = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        if diff:
            sys.exit('기준본과 다름: ' + ', '.join(diff))
        print('기준본과 같음 (drugs.json, guides.json, 그림 %d개)' % sum(k.startswith('img/') for k in new))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
