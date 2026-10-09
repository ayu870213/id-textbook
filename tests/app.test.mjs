// index.html의 계산·구간 판정·mg/kg 계산 test.
// 기대값은 index.html 코드가 아니라 별도로 계산한 값(MDCalc 방식 수식)이다.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const root = new URL('../', import.meta.url);
const drugs = JSON.parse(readFileSync(new URL('tests/fixtures/drugs.json', root), 'utf8')).drugs;
const guides = [{ id: 's01', group: '질환', title: '테스트', subsections: [], html: '<p>본문</p>' }];

function load() {
  const html = readFileSync(new URL('index.html', root), 'utf8');
  const marker = 'const EMBED=/*__DATA__*/null;';
  assert.ok(html.includes(marker), 'index.html에 데이터 삽입 위치가 없음');
  const data = { revised: '2026-01-01', meta: {}, drugs, guides };
  const dom = new JSDOM(html.replace(marker, `const EMBED=${JSON.stringify(data)};`), {
    runScripts: 'dangerously',
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false });
      w.HTMLElement.prototype.scrollTo = () => {};
    },
  });
  return dom.window;
}

const w = load();
const app = w.__app;
const $ = id => w.document.getElementById(id);

function patient({ sex, age, wt, ht, scr, rrt = '' }) {
  $('sx-m').checked = sex === 'M'; $('sx-f').checked = sex === 'F';
  $('age').value = age; $('wt').value = wt; $('ht').value = ht; $('cr').value = scr; $('rrt').value = rrt;
  app.renderP();
  return app.P;
}
const reg = (id, i = 0) => drugs.find(d => d.id === id).regimens[i];
const drug = id => drugs.find(d => d.id === id);
const near = (actual, expected, label) =>
  assert.ok(Math.abs(actual - expected) < 0.06, `${label}: ${actual.toFixed(2)} ≠ ${expected}`);

// ---------------------------------------------------------------- CrCl · eGFR
const CASES = [
  { p: { sex: 'M', age: 72, wt: 84, ht: 168, scr: 1.6 }, key: 'adj', ibw: 64.1, adj: 72.1, crcl: 42.5, egfr: 45.5 },
  { p: { sex: 'F', age: 45, wt: 55, ht: 160, scr: 0.6 }, key: 'ibw', ibw: 52.4, adj: 53.4, crcl: 97.9, egfr: 112.7 },
  { p: { sex: 'M', age: 30, wt: 50, ht: 175, scr: 0.7 }, key: 'tbw', ibw: 70.5, adj: 62.3, crcl: 109.1, egfr: 127.1 },
  { p: { sex: 'M', age: 50, wt: 58, ht: 175, scr: 1.1 }, key: 'tbw', ibw: 70.5, adj: 65.5, crcl: 65.9, egfr: 81.8 },
  { p: { sex: 'F', age: 80, wt: 95, ht: 155, scr: 2.5 }, key: 'adj', ibw: 47.9, adj: 66.7, crcl: 18.9, egfr: 19.0 },
];
for (const [i, c] of CASES.entries()) {
  test(`환자 ${i + 1}: CrCl·eGFR·체중 선택`, () => {
    const P = patient(c.p);
    assert.equal(P.key, c.key, 'CrCl 체중 선택');
    near(P.ibw, c.ibw, 'IBW'); near(P.adj, c.adj, 'AdjBW');
    near(P.crcl, c.crcl, 'CrCl'); near(P.egfr, c.egfr, 'eGFR');
  });
}

test('처음 열면 성별 포함 모든 칸이 비어 있고, 오류 없이 입력 안내만 표시', () => {
  const w2 = load(), d = w2.document;
  for (const id of ['age', 'wt', 'ht', 'cr']) assert.equal(d.getElementById(id).value, '', id);
  assert.equal(d.querySelector('input[name=sex]:checked'), null);
  assert.equal(w2.__app.P, null);
  assert.equal(d.getElementById('perr').textContent, '');
  assert.match(d.getElementById('dOut').textContent, /환자 정보를 입력하면.*남은 항목: 성별, 나이, 체중, 키, SCr/);
  assert.equal(d.querySelector('#dOut tr.hit, #dOut tr.amb'), null, '입력 전에는 강조된 구간이 없어야 함');
});

test('성별만 빠져도 계산하지 않음', () => {
  assert.equal(patient({ ...CASES[0].p, sex: null }), null);
  assert.equal($('perr').textContent, '');
  assert.match($('dOut').textContent, /남은 항목: 성별\s/);
});

test('입력값 범위 밖이면 계산하지 않고 빨간 문구로 알림', () => {
  assert.equal(patient({ sex: 'M', age: 15, wt: 60, ht: 170, scr: 1 }), null);
  assert.match($('perr').textContent, /나이\(18–120\)/);
  assert.equal(patient({ sex: 'M', age: 50, wt: 60, ht: 170, scr: 0 }), null);
  assert.match($('perr').textContent, /SCr/);
});

// ---------------------------------------------------------------- 구간 판정
// jsdom 안에서 만든 배열은 prototype이 달라 deepEqual이 실패하므로 복사한다
const texts = J => [...J.hits.map(b => b.text)];

test('구간 경계값 (piperacillin-tazobactam: >40 / 20-40 / <20)', () => {
  const r = reg('piperacillin-tazobactam');
  assert.deepEqual(texts(app.judgeV(r, 41)), ['CrCl >40']);
  assert.deepEqual(texts(app.judgeV(r, 40)), ['CrCl 20-40']);
  assert.deepEqual(texts(app.judgeV(r, 20)), ['CrCl 20-40']);
  assert.deepEqual(texts(app.judgeV(r, 19)), ['CrCl <20']);
});

test('원문 구간이 겹치면 두 용량을 모두 보여 줌 (ampicillin CrCl 30)', () => {
  const J = app.judgeV(reg('ampicillin'), 30);
  assert.equal(J.type, 'overlap');
  assert.deepEqual(texts(J).sort(), ['CrCl 10-30', 'CrCl 30-50']);
});

test('원문 구간 사이 값은 양쪽을 보여 줌 (cefepime CrCl 10)', () => {
  const J = app.judgeV(reg('cefepime'), 10);
  assert.equal(J.type, 'gap');
  assert.deepEqual(texts(J), ['CrCl 11-29', 'CrCl <10']);
});

test('원문 구간 밖이면 가장 가까운 구간 (ampicillin-sulbactam CrCl 3)', () => {
  const J = app.judgeV(reg('ampicillin-sulbactam'), 3);
  assert.equal(J.type, 'outside');
  assert.deepEqual(texts(J), ['CrCl 5-14']);
});

test('정수로 반올림해 판정하고, 약에 따라 CrCl/eGFR을 골라 씀', () => {
  const P = patient(CASES[0].p); // CrCl 42.55, eGFR 45.5
  const J1 = app.judge(reg('piperacillin-tazobactam'));
  assert.equal(J1.v, 43); assert.deepEqual(texts(J1), ['CrCl >40']);
  const J2 = app.judge(reg('teicoplanin'));
  assert.equal(J2.v, Math.round(P.egfr)); assert.deepEqual(texts(J2), ['eGFR 30-60']);
});

test('투석을 고르면 투석 용량을 씀', () => {
  patient({ ...CASES[0].p, rrt: 'HD' });
  const J = app.judge(reg('piperacillin-tazobactam'));
  assert.equal(J.type, 'dial'); assert.equal(J.key, 'HD');
});

test('투석 중이면 SCr 없이 계산하고 CrCl·eGFR은 표시하지 않음', () => {
  const P = patient({ ...CASES[0].p, scr: '', rrt: 'CRRT' });
  assert.ok(P, 'SCr 없이도 계산되어야 함');
  assert.equal(P.crcl, null); assert.equal(P.egfr, null);
  assert.equal($('vCrcl').textContent, '–mL/min');
  assert.match($('minibar').textContent, /CRRT.*투석 용량 사용/);
  assert.equal(app.judge(reg('piperacillin-tazobactam')).type, 'dial');
  // mg/kg 계산은 투석 중에도 체중으로 계속됨
  assert.match(mgkg('vancomycin', '20-30mg/kg (max 3g)'), /1,680–2,520 mg/);
});

test('투석을 해제하면 다시 SCr이 필요함', () => {
  assert.equal(patient({ ...CASES[0].p, scr: '', rrt: '' }), null);
  assert.match($('dOut').textContent, /남은 항목: SCr/);
});

// ---------------------------------------------------------------- mg/kg
const mgkg = (id, text) => app.mgkgLines(text, drug(id)).replace(/<[^>]+>/g, '');

test('vancomycin: TBW 사용', () => {
  patient(CASES[0].p); // TBW 84
  const out = mgkg('vancomycin', '20-30mg/kg (max 3g),\nthen 15-20mg/kg q12h');
  assert.match(out, /1,680–2,520 mg/); assert.match(out, /1,260–1,680 mg/); assert.match(out, /\(TBW\)/);
});

test('vancomycin: 부하 용량 최대 3 g', () => {
  patient({ sex: 'M', age: 40, wt: 110, ht: 175, scr: 1 });
  assert.match(mgkg('vancomycin', '20-30mg/kg (max 3g)'), /2,200–3,000\(최대\) mg/);
});

test('amikacin: 비만이면 AdjBW, TBW<IBW이면 TBW, 그 외 IBW', () => {
  patient(CASES[0].p); // TBW 84 > IBW 64.1×1.2 → AdjBW 72.08
  assert.match(mgkg('amikacin', '7.5mg/kg q12h'), /541 mg.*\(AdjBW\)|\(AdjBW\).*541 mg/s);
  patient(CASES[3].p); // TBW 58 < IBW 70.5
  assert.match(mgkg('amikacin', '7.5mg/kg q12h'), /435 mg/);
  patient(CASES[1].p); // IBW 52.38
  assert.match(mgkg('amikacin', '7.5mg/kg q12h'), /393 mg/);
});

test('colistin 부하 용량: IBW와 TBW 중 작은 값', () => {
  patient(CASES[2].p); // TBW 50 < IBW 70.5
  assert.match(mgkg('colistin', 'Load 4mg/kg,'), /200 mg/);
});

test('TMP-SMX: 비만이면 AdjBW', () => {
  patient(CASES[4].p); // AdjBW 66.71
  assert.match(mgkg('trimethoprim-sulfamethoxazole', '10-20mg/kg\ndivided q6-12h'), /667–1,334 mg/);
});

test('체중 규칙이 없는 약은 mg/kg 계산을 표시하지 않음', () => {
  patient(CASES[0].p);
  assert.equal(mgkg('piperacillin-tazobactam', '4.5g q6h'), '');
});
