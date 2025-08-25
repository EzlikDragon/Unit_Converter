// Minimal mobile converter using same categories as our Python version
const REGISTRY = {
  length: ['m','km','cm','mm','μm','nm','in','ft','yd','mi','nmi'],
  mass: ['kg','g','mg','lb','oz','ton'],
  time: ['s','ms','μs','min','h','day'],
  speed: ['m/s','km/h','mph','ft/s','kn','kph','kmph'],
  pressure: ['Pa','kPa','bar','mbar','hPa','atm','psi'],
  energy: ['J','kJ','Wh','kWh','cal','kcal','eV'],
  power: ['W','kW','MW','hp'],
  frequency: ['Hz','kHz','MHz','GHz','rpm'],
  area: ['m^2','cm^2','mm^2','km^2','in^2','ft^2','yd^2','acre','hectare','ha'],
  volume: ['m^3','L','mL','cm^3','in^3','ft^3','gal','qt','pt','fl oz'],
  data: ['B','KB','MB','GB','TB','bit','Kb','Mb','Gb','Tb'],
  angle: ['rad','deg','grad','turn'],
  temperature: ['C','F','K','R']
};

// Factors to base units for linear cases, and converters for temperature
const FACT = {
  // length base m
  m:1, km:1000, cm:0.01, mm:0.001, 'μm':1e-6, nm:1e-9, in:0.0254, ft:0.3048, yd:0.9144, mi:1609.344, nmi:1852,
  // mass base kg
  kg:1, g:0.001, mg:1e-6, lb:0.45359237, oz:0.028349523125, ton:1000,
  // time base s
  s:1, ms:1e-3, 'μs':1e-6, min:60, h:3600, day:86400,
  // speed base m/s
  'm/s':1, 'km/h':1000/3600, mph:1609.344/3600, 'ft/s':0.3048, kn:1852/3600, kph:1000/3600, kmph:1000/3600,
  // pressure base Pa
  Pa:1, kPa:1000, bar:1e5, mbar:100, hPa:100, atm:101325, psi:6894.757293168,
  // energy base J
  J:1, kJ:1000, Wh:3600, kWh:3.6e6, cal:4.184, kcal:4184, eV:1.602176634e-19,
  // power base W
  W:1, kW:1000, MW:1e6, hp:745.6998715822702,
  // frequency base Hz
  Hz:1, kHz:1e3, MHz:1e6, GHz:1e9, rpm:1/60,
  // area base m^2
  'm^2':1, 'cm^2':1e-4, 'mm^2':1e-6, 'km^2':1e6, 'in^2':0.00064516, 'ft^2':0.09290304, 'yd^2':0.83612736, acre:4046.8564224, hectare:1e4, ha:1e4,
  // volume base m^3
  'm^3':1, L:0.001, mL:1e-6, 'cm^3':1e-6, 'in^3':1.6387064e-5, 'ft^3':0.028316846592, gal:0.003785411784, qt:0.000946352946, pt:0.000473176473, 'fl oz':2.95735295625e-5,
  // data base B
  B:1, KB:1024, MB:1024**2, GB:1024**3, TB:1024**4, bit:1/8, Kb:1024/8, Mb:(1024**2)/8, Gb:(1024**3)/8, Tb:(1024**4)/8,
  // angle base rad
  rad:1, deg:Math.PI/180, grad:Math.PI/200, turn:2*Math.PI
};

const TEMP = {
  toK: {
    C: x=> x+273.15, F: x=> (x-32)*5/9+273.15, K: x=> x, R: x=> x*5/9
  },
  fromK: {
    C: x=> x-273.15, F: x=> (x-273.15)*9/5+32, K: x=> x, R: x=> x*9/5
  }
};

function sameCategory(a,b){
  let ca=null, cb=null;
  for(const [k,arr] of Object.entries(REGISTRY)){
    if(arr.includes(a)) ca=k;
    if(arr.includes(b)) cb=k;
  }
  return (ca && ca===cb) ? ca : null;
}

function roundSmart(x){
  if(!isFinite(x)) return String(x);
  if(x===0) return "0";
  const mag=Math.abs(x);
  if(mag>=1e6 || mag<1e-4) return x.toExponential(5);
  const dp=Math.max(0, 6-1-Math.floor(Math.log10(mag)));
  let s=x.toFixed(dp);
  if(s.includes('.')) s=s.replace(/0+$/,'').replace(/\.$/,'');
  return s;
}

function safeEval(expr,{deg=false}={}){
  const allowed=/^[0-9+\-*/^().,\s]*$|pi|e|sqrt|sin|cos|tan/i;
  if(!allowed.test(expr)) throw new Error('Disallowed characters');
  const replaced=expr.replace(/\^/g,'**')
    .replace(/\bpi\b/gi,'Math.PI')
    .replace(/\be\b/gi,'Math.E')
    .replace(/\bsqrt\(/gi,'Math.sqrt(')
    .replace(/\bsin\(/gi, deg? '((x)=>Math.sin(x*Math.PI/180))(' : 'Math.sin(')
    .replace(/\bcos\(/gi, deg? '((x)=>Math.cos(x*Math.PI/180))(' : 'Math.cos(')
    .replace(/\btan\(/gi, deg? '((x)=>Math.tan(x*Math.PI/180))(' : 'Math.tan(');
  // eslint-disable-next-line no-new-func
  return Function(`"use strict";return (${replaced})`)();
}

function convert(value, src, dst){
  const cat = sameCategory(src,dst);
  if(!cat) throw new Error('Units are not in the same category');
  if(cat==='temperature'){
    const K = TEMP.toK[src](value);
    return TEMP.fromK[dst](K);
  }else{
    const base = value * FACT[src];
    return base / FACT[dst];
  }
}

const els = {
  value: document.getElementById('valueInput'),
  from: document.getElementById('fromUnit'),
  to: document.getElementById('toUnit'),
  fromSearch: document.getElementById('fromSearch'),
  toSearch: document.getElementById('toSearch'),
  pills: document.getElementById('categoryPills'),
  result: document.getElementById('result'),
  history: document.getElementById('history'),
  convertBtn: document.getElementById('convertBtn'),
  swapBtn: document.getElementById('swapBtn'),
  evalBtn: document.getElementById('evalBtn'),
  degMode: document.getElementById('degMode'),
  examples: document.getElementById('examples'),
  installBtn: document.getElementById('installBtn')
};

function populateUnits(cat){
  const units = REGISTRY[cat];
  fillSelect(els.from, units);
  fillSelect(els.to, units);
}

function fillSelect(sel, units){
  const q = sel===els.from ? els.fromSearch.value.trim().toLowerCase() : els.toSearch.value.trim().toLowerCase();
  sel.innerHTML='';
  units.filter(u => !q || u.toLowerCase().includes(q))
       .forEach(u => sel.append(new Option(u,u)));
}

function setActivePill(cat){
  [...els.pills.children].forEach(btn=>btn.classList.toggle('active', btn.dataset.cat===cat));
  populateUnits(cat);
}

function addPills(){
  Object.keys(REGISTRY).forEach((cat,i)=>{
    const b=document.createElement('button'); b.textContent=cat; b.dataset.cat=cat;
    b.onclick=()=>setActivePill(cat);
    if(i===0) b.classList.add('active');
    els.pills.appendChild(b);
  });
  setActivePill(Object.keys(REGISTRY)[0]);
}

function addExamples(){
  ['3 m to ft','5 kg in lb','100 km/h to mph','1 atm to kPa','32 F to C','2*pi m to ft'].forEach(ex => {
    const b=document.createElement('button'); b.textContent=ex; b.onclick=()=>{
      const [v, u1, , u2] = ex.split(/\s+/);
      els.value.value = v;
      els.from.value = u1;
      els.to.value = u2;
      doConvert();
    };
    els.examples.appendChild(b);
  });
}

function pushHistory(text){
  const li=document.createElement('li');
  li.textContent=text;
  li.onclick=()=>navigator.clipboard?.writeText(text);
  els.history.prepend(li);
  const items=[...els.history.children]; if(items.length>12) items.pop().remove();
}

function doConvert(){
  try{
    let v = els.value.value.trim();
    if(!v) return;
    v = safeEval(v, {deg: els.degMode.checked});
    const src = els.from.value, dst = els.to.value;
    const out = convert(v, src, dst);
    const line = `${roundSmart(v)} ${src} = ${roundSmart(out)} ${dst}`;
    els.result.textContent = line;
    pushHistory(line);
  }catch(e){
    els.result.textContent = 'Error: ' + e.message;
  }
}

function keypadInit(){
  document.querySelectorAll('.keypad button').forEach(btn => {
    btn.addEventListener('click', () => {
      const k = btn.dataset.k;
      if(k==='clr') els.value.value='';
      else if(k==='back') els.value.value = els.value.value.slice(0,-1);
      else if(k==='neg'){
        const s = els.value.value.trim();
        els.value.value = s.startsWith('-') ? s.slice(1) : ('-' + s);
      }else{
        els.value.setRangeText(k, els.value.selectionStart, els.value.selectionEnd, 'end');
        els.value.focus();
      }
    });
  });
  els.evalBtn.onclick = () => {
    try{ els.value.value = String(safeEval(els.value.value || '0', {deg: els.degMode.checked})); }
    catch(e){ els.result.textContent = 'Eval error: ' + e.message; }
  };
}

function installPrompt(){
  let deferred;
  window.addEventListener('beforeinstallprompt', (e)=>{
    e.preventDefault(); deferred = e;
    els.installBtn.hidden = false;
    els.installBtn.onclick = ()=> deferred.prompt();
  });
}

function init(){
  document.getElementById('yr').textContent = new Date().getFullYear();
  addPills();
  addExamples();
  keypadInit();
  els.fromSearch.addEventListener('input', ()=>populateUnits([...els.pills.children].find(b=>b.classList.contains('active')).dataset.cat));
  els.toSearch.addEventListener('input', ()=>populateUnits([...els.pills.children].find(b=>b.classList.contains('active')).dataset.cat));
  els.convertBtn.onclick = doConvert;
  els.swapBtn.onclick = () => { const a=els.from.value; els.from.value=els.to.value; els.to.value=a; };
  els.value.addEventListener('keydown', e => { if(e.key==='Enter') doConvert(); });
  if('serviceWorker' in navigator){ navigator.serviceWorker.register('./sw.js'); }
  installPrompt();
}
init();
