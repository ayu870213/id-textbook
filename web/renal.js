/* 신기능·체중·용량 구간 계산.
   화면(DOM)과 무관한 계산만 둔다. 검증: tests/app.test.mjs
   - CrCl: Cockcroft-Gault. 체중은 MDCalc 방식 (BMI <18.5 TBW, 18.5–24.9 IBW(TBW<IBW이면 TBW), ≥25 AdjBW)
   - eGFR: CKD-EPI 2021
   - IBW: Devine, AdjBW = IBW + 0.4 × (TBW − IBW) */
const Renal = (() => {
const f1 = x => (Math.round(x*10)/10).toFixed(1);

/* 입력 확인. raw는 입력칸 값 그대로(문자열, 빈 칸은 '').
   빈 칸은 missing('남은 항목'), 범위를 벗어난 값은 errors(빨간 '입력 확인') */
function check(raw){
  const missing=[], errors=[], n=k=>+raw[k];
  if(!raw.sex) missing.push('성별');
  const checks=[['age','나이',n('age')>=18&&n('age')<=120,'나이(18–120)'],['wt','체중',n('wt')>0,'체중'],
                ['ht','키',n('ht')>=100&&n('ht')<=250,'키(100–250 cm)']];
  if(!raw.rrt) checks.push(['scr','SCr',n('scr')>0,'SCr']); // 투석 중이면 SCr로 신기능을 추정할 수 없고 용량은 투석 칸에서 정함
  for(const [k,name,ok,msg] of checks){
    if(String(raw[k]??'').trim()==='') missing.push(name); else if(!ok) errors.push(msg);
  }
  return {missing, errors};
}

/* 확인을 통과한 입력으로 계산. 투석 중이면 CrCl·eGFR은 null */
function patient({sex,age,wt,ht,scr,rrt}){
  const inch=ht/2.54, ibw=(sex==='m'?50:45.5)+2.3*(inch-60), adj=ibw+0.4*(wt-ibw), bmi=wt/(ht/100)**2;
  const cg = w => rrt ? null : (140-age)*w/(72*scr)*(sex==='f'?0.85:1);
  let key, why;
  if(bmi<18.5){key='tbw';why='BMI '+f1(bmi)+' · 실제체중';}
  else if(bmi<25){ if(wt<ibw){key='tbw';why='BMI '+f1(bmi)+' · 실제체중(<IBW)';} else {key='ibw';why='BMI '+f1(bmi)+' · IBW';} }
  else {key='adj';why='BMI '+f1(bmi)+' · AdjBW';}
  const W={tbw:wt,ibw,adj};
  const k=sex==='f'?0.7:0.9, a=sex==='f'?-0.241:-0.302;
  const egfr=rrt ? null : 142*Math.min(scr/k,1)**a*Math.max(scr/k,1)**-1.2*0.9938**age*(sex==='f'?1.012:1);
  return {sex,age,wt,ht,scr,rrt,bmi,ibw,adj,W,key,why,crcl:cg(W[key]),egfr,
    rows:[['tbw','실제체중 (TBW)',wt],['ibw','이상체중 (IBW)',ibw],['adj','보정체중 (AdjBW)',adj]].map(([k,n,w])=>({k,n,w,c:cg(w)}))};
}

/* mg/kg 계산 체중. rule은 config/rules.json의 weight_rules 이름 → [kg, 'TBW'|'IBW'|'AdjBW'] */
function doseWeight(P, rule){
  if(!P) return null;
  const obese = P.wt > P.ibw*1.2;
  switch(rule){
    case 'IBW_AG': if(P.wt<P.ibw) return [P.wt,'TBW']; if(obese) return [P.adj,'AdjBW']; return [P.ibw,'IBW'];
    case 'TBW': return [P.wt,'TBW'];
    case 'TBW_OBESE_ADJ': return obese?[P.adj,'AdjBW']:[P.wt,'TBW'];
    case 'MIN_IBW_TBW': return P.ibw<P.wt?[P.ibw,'IBW']:[P.wt,'TBW'];
  }
  return null;
}

/* 용량 문구의 "a-b mg/kg (max N g)"를 mg로 환산 → [{expr, kg, basis, lo, hi}], lo·hi = {mg, capped} */
function mgkg(text, P, rule){
  const w=doseWeight(P, rule); if(!w||!text) return [];
  const out=[], seen=new Set(), re=/(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*mg\/kg/g; let m;
  while((m=re.exec(text))){
    const expr=m[0]; if(seen.has(expr)) continue; seen.add(expr);
    const after=text.slice(m.index+expr.length, m.index+expr.length+18);
    const cap=(after.match(/max\s*(\d+(?:\.\d+)?)\s*g/i)||[])[1];
    const capmg=cap?+cap*1000:null;
    const v=x=>{const r=Math.round(x*w[0]); return capmg&&r>capmg?{mg:capmg,capped:true}:{mg:r,capped:false};};
    out.push({expr, kg:w[0], basis:w[1], lo:v(+m[1]), hi:m[2]?v(+m[2]):null});
  }
  return out;
}

/* 용량 구간 판정: 정수로 반올림한 값으로 원문 구간을 찾는다 */
const inBand=(b,v)=>(b.lo==null||v>=b.lo)&&(b.hi==null||v<=b.hi);
function judge(P, reg){
  if(!P) return {type:'nopt'};
  if(P.rrt){ const x=reg.dialysis[P.rrt]; return {type:'dial',key:P.rrt,dose:x?x.dose:null}; }
  const val = reg.basis==='eGFR'?P.egfr:P.crcl;
  return judgeV(reg, Math.round(val));
}
function judgeV(reg, v){
  const hits=reg.bands.filter(b=>inBand(b,v));
  if(hits.length===1) return {type:'one',v,hits};
  if(hits.length>1){ if(new Set(hits.map(b=>b.dose)).size===1) return {type:'one',v,hits:[{...hits[0],text:hits.map(b=>b.text).join(' / ')}],all:hits}; return {type:'overlap',v,hits}; }
  const below=reg.bands.filter(b=>b.hi!=null&&b.hi<v).sort((a,b)=>b.hi-a.hi)[0];
  const above=reg.bands.filter(b=>b.lo!=null&&b.lo>v).sort((a,b)=>a.lo-b.lo)[0];
  if(below&&above) return {type:'gap',v,hits:[above,below]};
  return {type:'outside',v,hits:[below||above].filter(Boolean)};
}

/* 한 칸 안에 "CrCl a-b: ..." 줄이 여럿인 용량(colistin 등): 해당하는 줄 표시 → [{text, on}] 또는 null */
function lineHits(text, v){
  if(!text||v==null||!/CrCl\s*[\d<>≥≤]/.test(text.split('\n').slice(1).join('\n'))) return null;
  return text.split('\n').map(l=>{
    const m=l.match(/CrCl\s*(≥|>=|>|<|≤)?\s*(\d+)(?:\s*-\s*(\d+))?/); let on=false;
    if(m){ const a=+m[2], b=m[3]?+m[3]:null, op=m[1];
      if(b!=null) on=v>=a&&v<=b; else if(op==='≥'||op==='>=') on=v>=a; else if(op==='>') on=v>a; else if(op==='<') on=v<a; else if(op==='≤') on=v<=a; }
    return {text:l, on};
  });
}

return {f1, check, patient, doseWeight, mgkg, judge, judgeV, lineHits};
})();
