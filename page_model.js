/* The model half of the published page, copied verbatim.

   This is not a reimplementation - it is the code the interactive page runs,
   lifted out of it whole, with the drawing left behind. run_all.py runs this
   and the Python side on the same seeds and checks that every count agrees.

   Live page: https://quest-for-entropy.web.app/two-observers
*/
const NP = 3, PN = ["A","B","C"], STEPS = 15;
const PCOL = ["#2563a8","#1e7a55","#7a3fa0"];
const C_PAST="#1d4ed8", C_FUT="#c2410c", C_ELSE="#9aa5b4", C_SEL="#111827",
      C_INK="#2b3648", C_RAY="#b3701a", C_LINE="#dde3ea", C_DIM="#5d6b7d";

function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0; let t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }; }
function hashSeed(s){ let h=2166136261>>>0; s=String(s);
  for(let i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619)>>>0; } return h>>>0; }

/* All randomness is drawn ONCE from the seed, before the rate is applied, so
   moving the message slider reshapes the same world instead of rolling a new one. */
function drawDice(seed){
  const r = mulberry32(hashSeed(seed)), d = [];
  for (let s=0;s<STEPS;s++){ const row=[];
    for (let p=0;p<NP;p++) row.push({act:r(), send:r(), dest:r(), delay:r(), both:r(), delay2:r()});
    d.push(row); }
  return d;
}

function buildWorld(seed, rate){
  const dice = drawDice(seed);
  const sendProb = 0.05 + 0.88*rate;                    // more messages as the slider rises
  const minD     = Math.max(1, Math.round(3 - 2*rate)); // the fastest a message can possibly be
  const extra    = Math.max(1, Math.round(5 - 4*rate)); // spread of delays above that floor
  const bothProb = Math.max(0, (rate - 0.35) / 0.65);   // eventually one send reaches everyone
  const ACT = 0.62;

  const V = [[0,0,0],[0,0,0],[0,0,0]];
  const events = [], msgs = [];
  let flight = [];

  for (let s=0; s<STEPS; s++){
    const busy = [false,false,false];

    // Deliveries first. A process reads its whole inbox in one event: it ticks
    // its own counter once, then takes the componentwise max over every message
    // that has landed. That keeps exactly one event per process per step.
    for (let q=0;q<NP;q++){
      const inbox = flight.filter(m => m.to === q && m.at <= s);
      if (!inbox.length) continue;
      busy[q] = true;
      V[q][q] += 1;
      for (const m of inbox) for (let k=0;k<NP;k++) V[q][k] = Math.max(V[q][k], m.V[k]);
      const ev = { id:events.length, p:q, step:s, kind:"recv", V:V[q].slice(), c:V[q][q] };
      events.push(ev);
      for (const m of inbox){ m.done = true; msgs.push({ from:m.src, to:ev.id }); }
    }
    flight = flight.filter(m => !m.done);

    // then each idle process may do a local event, possibly a send
    for (let p=0;p<NP;p++){
      if (busy[p]) continue;
      const u = dice[s][p];
      if (u.act >= ACT) continue;
      V[p][p] += 1;
      const sending = (s < STEPS - minD) && (u.send < sendProb);
      const ev = { id:events.length, p:p, step:s, kind:sending?"send":"local", V:V[p].slice(), c:V[p][p] };
      events.push(ev);
      if (sending){
        const q = (p + 1 + Math.floor(u.dest*(NP-1))) % NP;
        const at = s + minD + Math.floor(u.delay*extra);
        let any = false;
        if (at < STEPS){ flight.push({ to:q, at:at, src:ev.id, V:ev.V.slice() }); any = true; }
        if (u.both < bothProb){                        // same news, sent to the third process too
          const q2 = 3 - p - q, at2 = s + minD + Math.floor(u.delay2*extra);
          if (at2 < STEPS){ flight.push({ to:q2, at:at2, src:ev.id, V:ev.V.slice() }); any = true; }
        }
        if (!any) ev.kind = "local";
      }
    }
  }
  // sends whose message never landed are just local events
  const landed = new Set(msgs.map(m => m.from));
  for (const e of events) if (e.kind === "send" && !landed.has(e.id)) e.kind = "local";

  return { events, msgs, minD, byProc: [0,1,2].map(p => events.filter(e => e.p===p)) };
}

/* ---- causal order ---- */
const leq = (a,b) => a[0]<=b[0] && a[1]<=b[1] && a[2]<=b[2];
const before = (e,f) => e !== f && leq(e.V, f.V);
const concurrent = (e,f) => !leq(e.V,f.V) && !leq(f.V,e.V);

function pairStats(w){
  const E = w.events, n = E.length; let tot=0, conc=0;
  for (let i=0;i<n;i++) for (let j=i+1;j<n;j++){ tot++; if (concurrent(E[i],E[j])) conc++; }
  return { tot, conc, frac: tot ? conc/tot : 0 };
}

/* 0 = past, 1 = future, 2 = elsewhere, 3 = the selected event itself */
function classify(w, sel){
  const E = w.events, cls = new Array(E.length).fill(2);
  if (sel == null) return null;
  const e = E[sel];
  for (const f of E){
    if (f === e) { cls[f.id] = 3; continue; }
    if (leq(f.V, e.V)) cls[f.id] = 0;
    else if (leq(e.V, f.V)) cls[f.id] = 1;
  }
  return cls;
}

/* ---- the DAG and its linear extensions ----
   Edges: program order (consecutive events on one process) + every message
   (send -> receive). The transitive closure of these edges IS happens-before,
   which is what the vector clocks compute, so any topological order of this
   DAG is guaranteed to respect every causal pair. Panel 3 checks that. */
function buildDag(w){
  const n = w.events.length, adj = Array.from({length:n}, () => []), indeg = new Array(n).fill(0);
  const add = (u,v) => { adj[u].push(v); indeg[v]++; };
  for (const lane of w.byProc) for (let i=0;i+1<lane.length;i++) add(lane[i].id, lane[i+1].id);
  for (const m of w.msgs) add(m.from, m.to);
  return { adj, indeg };
}

function topoSort(w, dag, pick){
  const n = w.events.length, indeg = dag.indeg.slice(), ready = [], out = [];
  for (let i=0;i<n;i++) if (indeg[i]===0) ready.push(i);
  while (ready.length){
    const k = pick(ready, w);
    const v = ready.splice(k,1)[0];
    out.push(v);
    for (const u of dag.adj[v]) if (--indeg[u] === 0) ready.push(u);
  }
  return out;
}
// observer 1: the obvious "wall clock" reading — earliest step, then A before B before C
const pickNatural = (ready, w) => {
  let k=0, best=Infinity;
  for (let i=0;i<ready.length;i++){ const e=w.events[ready[i]], key=e.step*10+e.p;
    if (key < best){ best=key; k=i; } }
  return k;
};

function compareLogs(w, o1, o2){
  const n = w.events.length, p1 = new Array(n), p2 = new Array(n);
  o1.forEach((id,i) => p1[id]=i);
  o2.forEach((id,i) => p2[id]=i);
  let swapped = 0, bad = 0;
  for (let i=0;i<n;i++) for (let j=i+1;j<n;j++){
    const a = w.events[i], b = w.events[j];
    if ((p1[i] < p1[j]) !== (p2[i] < p2[j])){ swapped++; if (!concurrent(a,b)) bad++; }
  }
  return { swapped, bad, p1, p2 };
}