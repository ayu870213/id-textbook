# 감염내과 참고서

CrCl·eGFR 기반 항생제 권장 용량과 질환별 가이드를 한 화면에서 보는 웹페이지입니다.

사이트: https://ayu870213.github.io/id-textbook/ (QR: [qr/감염내과참고서_QR.png](qr/감염내과참고서_QR.png))

## 내용을 고치는 방법

원본은 구글 드라이브의 **GitHub id-textbook** 폴더에 있습니다.

- **항생제 용량**: 스프레드시트(구글 시트 또는 .xlsx)
- **질환별 가이드**: 문서(구글 문서 또는 .docx). 질환 제목은 `제목 1`, 소제목은 `제목 2`

로컬에서 고친 파일을 폴더에 새로 올리면, 종류별로 **가장 최근에 올린 파일**이 사이트에 반영됩니다. 옛 파일은 남아 있어도 쓰이지 않으니 편할 때 지우면 됩니다. 어떤 파일이 쓰였는지는 사이트 맨 아래에 표시됩니다.

- 자동 반영: 매시간 변경을 확인해 바뀐 경우에만 반영
- 즉시 반영: 저장소 **Actions → 사이트 갱신 → Run workflow**

변환 중 문제가 생기거나 계산 test가 실패하면 배포하지 않고 기존 사이트를 유지하며, Actions 기록에 원인이 표시됩니다.

## 계산 기준

- CrCl: Cockcroft-Gault. 체중은 MDCalc 방식(BMI < 18.5 실제체중, 18.5–24.9 IBW(실제체중이 작으면 실제체중), ≥ 25 보정체중)
- eGFR: CKD-EPI 2021 (mL/min/1.73m²). 엑셀에 eGFR로 적힌 약만 eGFR로 구간 판정
- 구간 판정은 정수로 반올림한 값으로 하며, 원문 구간이 겹치거나 비는 값은 해당 용량을 모두 표시하고 확인 필요로 알림
- 투석(HD·CAPD·CRRT)을 고르면 SCr 없이 투석 칸 용량을 표시
- mg/kg 계산 체중은 약별 규칙(`config/rules.json`)을 따름

본 자료는 임상 판단을 보조하기 위한 것이며, 최종 처방 용량은 처방의의 판단과 책임에 따릅니다.

---

## 구조 (코드를 고칠 때)

```
config/rules.json     약별 mg/kg 체중 규칙, 약 이름 예외, 가이드 분류·순서, 처음 선택되는 약
web/                  사이트 화면 (그대로 복사됨)
  index.html            화면 틀
  style.css             스타일
  app.js                화면 표시
  renal.js              임상 계산만: CrCl·eGFR·체중 선택·mg/kg·구간 판정
scripts/              빌드 (GitHub Actions에서 실행)
  build.py              조립: 원본 → _site/
  drive.py              드라이브에서 가장 최근에 올린 원본 받기
  dosing_xlsx.py        용량표 → data/drugs.json
  guide_docx.py         가이드 → data/guides.json, 그림
tests/
  app.test.mjs          계산 test (별도로 계산한 기준값과 대조)
  compare_build.py      빌드 결과가 기준본과 같은지 비교 (로컬 전용)
tools/make_qr.py      QR 코드 만들기
.github/workflows/    test → 빌드 → 배포
```

### 약별 체중 규칙 바꾸기

`config/rules.json`의 `drug_weight`에 약 이름(엑셀 B열)과 규칙을 적습니다. 규칙 종류(`weight_rules`)를 새로 만들면 `web/renal.js`의 `doseWeight()`에도 계산을 추가해야 하며, 빠뜨리면 test가 실패합니다.

### 로컬에서 확인하기

처음 한 번: `python -m venv .venv`, `.venv/Scripts/pip install -r scripts/requirements.txt`, `npm install`

```
npm test                                        # 계산 test
python scripts/build.py --xlsx samples/용량.xlsx --docx samples/가이드.docx --out _site
python -m http.server -d _site 8000             # http://localhost:8000 에서 보기
python tests/compare_build.py --save            # 고치기 전 기준본 저장 (samples/ 필요)
python tests/compare_build.py                   # 고친 뒤 결과가 같은지 비교
```

`samples/`(원본 사본), `_site/`, `tests/baseline/`은 저장소에 올리지 않습니다.
