function main(DATA){
for(const g of DATA.guides){ if(g.text==null){ const t=document.createElement('div'); t.innerHTML=g.html; g.text=t.textContent; } }
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const f1 = Renal.f1;
const narrow = () => matchMedia('(max-width:860px)').matches; // CSS의 좁은 화면 기준과 같은 값
$('rev').textContent = DATA.revised;
const M = DATA.meta;
if(M?.drugs_source) $('src').textContent = `원본: 용량표 ${M.drugs_source} (${M.drugs_uploaded} 업로드) · 가이드 ${M.guides_source} (${M.guides_uploaded} 업로드)`;

/* ---------- 환자 입력 ---------- */
let P = null, missing = [];
function calc(){
  const raw={sex:document.querySelector('input[name=sex]:checked')?.value, age:$('age').value, wt:$('wt').value,
             ht:$('ht').value, scr:$('cr').value, rrt:$('rrt').value};
  const c=Renal.check(raw); missing=c.missing;
  $('perr').textContent = c.errors.length ? '입력 확인: '+c.errors.join(', ') : '';
  if(c.errors.length||c.missing.length) return null;
  return Renal.patient({sex:raw.sex, age:+raw.age, wt:+raw.wt, ht:+raw.ht, scr:+raw.scr, rrt:raw.rrt});
}
function renderP(){
  P=calc();
  if(!P){ $('minibar').innerHTML='<span>환자 정보를 입력하세요</span><a href="#top">입력</a>'; $('vCrcl').innerHTML='–<i>mL/min</i>'; $('vEgfr').innerHTML='–<i>mL/min/1.73m²</i>'; $('vWhy').textContent=''; $('wRows').innerHTML=''; $('wMeta').textContent=''; }
  else if(P.rrt){
    $('vCrcl').innerHTML='–<i>mL/min</i>';
    $('vEgfr').innerHTML='–<i>mL/min/1.73m²</i>';
    $('vWhy').textContent=`${P.rrt} 중 · 투석 용량 사용`;
    $('minibar').innerHTML=`<span><b>${P.rrt}</b></span><span>투석 용량 사용</span><a href="#top">환자 정보 수정</a>`;
    $('wRows').innerHTML=P.rows.map(r=>`<tr><td>${r.n}</td><td class="n">${f1(r.w)}</td><td class="n">–</td></tr>`).join('');
  }
  else{
    $('vCrcl').innerHTML=Math.round(P.crcl)+'<i>mL/min</i>';
    $('vEgfr').innerHTML=Math.round(P.egfr)+'<i>mL/min/1.73m²</i>';
    $('vWhy').textContent=P.why;
    $('minibar').innerHTML=`<span>CrCl <b>${Math.round(P.crcl)}</b></span><span>eGFR <b>${Math.round(P.egfr)}</b></span><span>투석 없음</span><a href="#top">환자 정보 수정</a>`;
    $('wRows').innerHTML=P.rows.map(r=>`<tr class="${r.k===P.key?'on':''}"><td>${r.n}${r.k===P.key?' · CrCl 사용':''}</td><td class="n">${f1(r.w)}</td><td class="n">${f1(r.c)}</td></tr>`).join('');
  }
  if(P) $('wMeta').innerHTML=`BMI ${f1(P.bmi)} kg/m² · TBW/IBW ${Math.round(P.wt/P.ibw*100)}%${P.wt>P.ibw*1.2?' (비만 기준 초과)':''}${P.ht<152.4?'<br>키 152.4 cm 미만: IBW 해석 주의':''}`;
  renderDose();
}

/* ---------- 계산 결과 표시 (계산은 renal.js) ---------- */
const doseWeight = d => Renal.doseWeight(P, d.weight);
const judge = reg => Renal.judge(P, reg);
const judgeV = Renal.judgeV;
function mgkgLines(text, d){
  const v = x => x.capped ? `${x.mg.toLocaleString()}(최대)` : x.mg.toLocaleString();
  const out = Renal.mgkg(text, P, d.weight).map(r =>
    `<div><b>${esc(r.expr)}</b> × ${f1(r.kg)} kg (${r.basis}) = <b>${v(r.lo)}${r.hi?'–'+v(r.hi):''} mg</b></div>`);
  return out.length?`<div class="wt">${out.join('')}</div>`:'';
}
// 칸 안 CrCl별 용량: 표에는 전체를 두고 해당 줄 강조, 권장 용량 칸(onlyHit)에는 해당 줄과 조건 없는 줄(예: Load)만
function subLines(text, v, onlyHit){
  const lines = Renal.lineHits(text, v);
  return lines && lines.filter(l=>!onlyHit||l.on||!l.crcl).map(l=>`<span class="ln${l.on?' on':''}">${esc(l.text)||'&nbsp;'}</span>`).join('');
}

/* ---------- 권장 용량 ---------- */
const DRUGS=DATA.drugs.filter(d=>d.status==='active');
let sel=DRUGS.find(d=>d.id===DATA.meta?.default_drug)?.id||DRUGS[0].id, regIx=0;
function renderList(){
  const q=$('dq').value.trim().toLowerCase(); let html='', cls=null;
  const list=DRUGS.filter(d=>!q||(d.name+' '+(d.brand||'')).toLowerCase().includes(q));
  for(const d of list){
    if(d.class!==cls){ cls=d.class; html+=`<li class="grp">${esc(cls)}</li>`; }
    html+=`<li><button type="button" data-id="${d.id}" aria-current="${d.id===sel}"><span>${esc(d.name)}</span><span class="b">${esc((d.brand||'').split('\n')[0])}</span></button></li>`;
  }
  $('dList').innerHTML=html||'<li class="grp">검색 결과 없음</li>';
}
function renderDose(){
  const d=DRUGS.find(x=>x.id===sel); if(!d){$('dOut').innerHTML='';return;}
  if(regIx>=d.regimens.length) regIx=0;
  const reg=d.regimens[regIx], J=judge(reg);
  const basisTxt=reg.basis==='eGFR'?'eGFR 기준':'CrCl 기준';
  let card='';
  const hitSet=new Set((J.all||J.hits||[]).map(b=>b.text));
  const doseTxt=t=>t==null?'자료 없음':t;
  if(J.type==='nopt') card=`<div class="rec none"><div class="lab">권장 용량</div><div class="why">환자 정보를 입력하면 해당 구간을 표시합니다.${missing.length?` 남은 항목: ${missing.join(', ')}`:''}</div></div>`;
  else if(J.type==='dial') card=`<div class="rec ${J.dose?'':'none'}"><div class="lab">권장 용량 · ${J.key}</div><div class="dz">${esc(doseTxt(J.dose))}</div>${mgkgLines(J.dose,d)}</div>`;
  else if(J.type==='one'){ const b=J.hits[0]; const sub=subLines(b.dose,J.v,true);
    card=`<div class="rec ${b.dose?'':'none'}"><div class="lab">권장 용량 · ${basisTxt}</div><div class="dz">${sub||esc(doseTxt(b.dose))}</div><div class="why">${reg.basis} ${J.v} → ${esc(b.text)}</div>${mgkgLines(b.dose,d)}</div>`; }
  else { const title = J.type==='overlap' ? `원문 구간 경계값 · ${reg.basis} ${J.v}은 두 구간에 모두 해당합니다. 임상 상황에 맞게 선택하세요.`
         : J.type==='gap' ? `원문 구간 사이 값 · ${reg.basis} ${J.v}은 원문 구간 사이에 있습니다. 양쪽 용량을 참고하세요.`
         : `원문에 ${reg.basis} ${J.v}에 해당하는 구간이 없습니다. 가장 가까운 구간을 참고하세요.`;
    card=`<div class="rec warn"><div class="lab">⚠ 확인 필요 · ${basisTxt}</div><div class="why">${title}</div><div class="alt">${J.hits.map(b=>`<span>${esc(b.text)}</span><div>${subLines(b.dose,J.v,true)||esc(doseTxt(b.dose))}</div>`).join('')}</div>${[...new Set(J.hits.map(b=>mgkgLines(b.dose,d)))].join('')}</div>`; }
  const cls = b => !hitSet.has(b.text)?'':(J.type==='one'?'hit':'amb');
  const rows=reg.bands.map(b=>`<tr class="${cls(b)}"><td>${esc(b.text)}</td><td class="${b.dose?'dz':'na'}">${b.dose?(hitSet.has(b.text)&&subLines(b.dose,J.v))||esc(b.dose):'자료 없음'}</td></tr>`).join('')
    + ['HD','CAPD','CRRT'].map((k,i)=>{const x=reg.dialysis[k]; return `<tr class="dial${i===0?' sep':''} ${J.type==='dial'&&J.key===k?'hit':''}"><td>${k}</td><td class="${x.dose?'dz':'na'}">${x.dose?esc(x.dose):'자료 없음'}</td></tr>`;}).join('');
  const wnote=d.weight_label?`<p class="note">mg/kg 계산 체중: ${esc(d.weight_label)}</p>`:'';
  $('dOut').innerHTML=`<div class="dname"><h3>${esc(d.name)}</h3><span class="meta">${esc((d.brand||'').replace(/\n/g,' · '))} · ${esc(d.class)}</span></div>
    ${d.regimens.length>1?`<div class="tabs" role="group" aria-label="용법">${d.regimens.map((r,i)=>`<button type="button" data-r="${i}" aria-pressed="${i===regIx}">${esc(r.label)}</button>`).join('')}</div>`:''}
    ${card}
    <div class="tblw"><table class="bt"><thead><tr><th>${reg.basis} (mL/min${reg.basis==='eGFR'?'/1.73m²':''})</th><th>용량</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${wnote}${d.note?`<p class="note">${esc(d.note)}</p>`:''}`;
}
$('dq').addEventListener('input',renderList);
$('dList').addEventListener('click',e=>{const b=e.target.closest('button[data-id]'); if(!b) return; sel=b.dataset.id; regIx=0; renderList(); renderDose();});
$('dOut').addEventListener('click',e=>{const b=e.target.closest('button[data-r]'); if(!b) return; regIx=+b.dataset.r; renderDose();});

/* ---------- 가이드 ---------- */
const G=DATA.guides; let gSel=G[0].id;
function renderGList(){
  const q=$('gq').value.trim().toLowerCase(); let html='', grp=null;
  for(const s of G){
    if(q && !(s.title+' '+s.text).toLowerCase().includes(q)) continue;
    if(s.group!==grp){grp=s.group; html+=`<li class="grp">${esc(grp)}</li>`;}
    const m=s.title.match(/^(.*?)\s*(\(.*\))?$/);
    html+=`<li><button type="button" data-g="${s.id}" aria-current="${s.id===gSel}">${esc(m[1])}${m[2]?`<small>${esc(m[2].slice(1,-1))}</small>`:''}</button></li>`;
  }
  $('gList').innerHTML=html||'<li class="grp">검색 결과 없음</li>';
}
function renderG(){
  const s=G.find(x=>x.id===gSel), h2=s.subsections.filter(x=>x.level===2);
  $('gHead').innerHTML=`<h3>${esc(s.title)}</h3>${h2.length?`<nav class="toc" aria-label="소제목">${h2.map(x=>`<a href="#${x.anchor}" data-a="${x.anchor}">${esc(x.title.replace(/\s*\(.*$/,''))}</a>`).join('')}</nav>`:''}`;
  $('gBody').innerHTML=s.html.replace(/<table>/g,'<div class="tw"><table>').replace(/<\/table>/g,'</table></div>');
  $('gBody').scrollTop=0;
}
$('gq').addEventListener('input',renderGList);
$('gList').addEventListener('click',e=>{const b=e.target.closest('button[data-g]'); if(!b) return; gSel=b.dataset.g; renderGList(); renderG(); if(narrow()) $('gHead').scrollIntoView({behavior:'smooth'});});
$('gHead').addEventListener('click',e=>{const a=e.target.closest('a[data-a]'); if(!a) return; e.preventDefault(); const t=document.getElementById(a.dataset.a); if(!t) return;
  if(narrow()) t.scrollIntoView({behavior:'smooth'}); else $('gBody').scrollTo({top:t.offsetTop-$('gBody').offsetTop-4,behavior:'smooth'});});

/* ---------- 공통 ---------- */
$('pf').addEventListener('input',renderP);
$('pf').addEventListener('submit',e=>e.preventDefault());
$('btnDetail').addEventListener('click',()=>{const d=$('detail'); d.hidden=!d.hidden; $('btnDetail').setAttribute('aria-expanded',String(!d.hidden)); pad();});
function pad(){document.documentElement.style.scrollPaddingTop=((narrow()?$('minibar').offsetHeight:$('top').offsetHeight)+10)+'px';}
addEventListener('resize',pad);
renderList(); renderGList(); renderG(); renderP(); pad();
window.__app={ // tests/app.test.mjs에서 사용
calc,judge,judgeV,renderP,get P(){return P},DRUGS,doseWeight,mgkgLines};
}
// tests/app.test.mjs는 window.__DATA__에 test 데이터를 넣는다
if(window.__DATA__) main(window.__DATA__);
else Promise.all(['data/drugs.json','data/guides.json','data/meta.json'].map(u=>fetch(u,{cache:'no-cache'}).then(r=>{if(!r.ok) throw r.status; return r.json();})))
  .then(([d,g,m])=>main({revised:m.revised,meta:m,drugs:d.drugs,guides:g.sections}))
  .catch(()=>{document.getElementById('dOut').textContent='데이터를 불러오지 못했습니다. 새로고침해 주세요.';});
