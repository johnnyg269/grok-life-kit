import { useState, Page, Section, Metrics, Properties, Segmented, Button, useGrokTheme } from "grok/canvas";

// ---- Grok Life dashboard v4. Fixed layout: do not reorder, rename, or restyle. ----
// Only the two marked blocks below change after onboarding. Update them with EditCanvas.
// One page, two levels: an overview (tabs plus one tile per module) and a detail view per module.
// Modules that are off, or have no data yet, are null in DATA and are not drawn: no tab, no tile, no placeholder.

type Pal = string[]; // recovery, sleep, nutrition, hydration, activity, medication
type Ring = { key: string; label: string; value: number; target: number; shown: string; sub: string };
type Weight = { unit: string; labels: string[]; daily: (number | null)[]; avg: (number | null)[]; goal: number | null; current: number | null; change: number | null };
type Workouts = {
  sessions: number; planned: number; minutes: number; kcal: number; avg: number; last: string;
  days: { label: string; done: boolean; mins: number }[];
  weeks: { labels: string[]; values: number[] };
  recent: { when: string; name: string; mins: number; kcal: number }[];
};
type Nutrition = {
  kcalLeft: number; rings: Ring[]; meals: { label: string; value: number }[];
  cal7: { labels: string[]; values: number[]; target: number };
  avgIntake: string; avgProtein: string; proteinDays: string;
};
type Activity = {
  steps: number; goal: number; pct: number; week: { labels: string[]; values: number[] };
  avg30: string; goalDays: string; best: string;
};
type Health = {
  recovery: { value: number | null; state: string; coach: string };
  sleep: { labels: string[]; values: number[]; avg: number; last: number | null; goal: number; pct: number | null } | null;
  weight: Weight | null;
  water: { labels: string[]; values: number[]; unit: string; today: string; goal: number; pct: number | null } | null;
};
type Treatment = {
  compound: string; brand: string; cadence: string;
  levelNow: number; levelNext: number; ssHigh: number; ssLow: number;
  lastMg: string; lastWhen: string; lastSite: string; lastSiteKey: string;
  nextWhen: string; nextCountdown: string; nextSite: string; nextSiteKey: string; elapsed: number;
  past: [number, number][]; future: [number, number][]; doseX: number[]; nowX: number; ticks: [number, number | string][];
  effects: Ring[];
  coach: string;
};
type Dash = {
  name: string; dateLabel: string; updated: string; streak: number;
  pal: { light: Pal; dark: Pal };
  shown: string[];
  titles: Record<string, string>;
  workouts: Workouts | null; nutrition: Nutrition | null; activity: Activity | null; health: Health | null; peptides: Treatment | null;
};
type PhotoData = { src: string; pose: string; before: string; after: string; days: number; weight: string };

// DATA-START
const DATA: Dash = {
  "name": "Alex",
  "dateLabel": "Wednesday, Nov 18",
  "updated": "5:08 PM",
  "streak": 6,
  "pal": {"light":["#089678","#4F80CA","#A97500","#058FAA","#BF6052","#619824"],"dark":["#57D8B4","#95C0FF","#EDB24D","#46D1F3","#FFA191","#9ED96A"]},
  "shown": ["workouts","nutrition","activity","health","peptides"],
  "titles": {"workouts":"Workouts","nutrition":"Diet and macros","activity":"Steps and activity","health":"Health","peptides":"Peptides and meds"},
  "workouts": {"sessions":4,"planned":4,"minutes":220,"kcal":1000,"avg":55,"last":"Last: Upper/lower, Wed","days":[{"label":"T","done":false,"mins":0},{"label":"F","done":true,"mins":55},{"label":"S","done":true,"mins":55},{"label":"S","done":false,"mins":0},{"label":"M","done":true,"mins":55},{"label":"T","done":false,"mins":0},{"label":"W","done":true,"mins":55}],"weeks":{"labels":["Sep 30","Oct 7","Oct 14","Oct 21","Oct 28","Nov 4","Nov 11","Nov 18"],"values":[165,165,55,220,165,220,165,220]},"recent":[{"when":"Nov 18","name":"Upper/lower","mins":55,"kcal":250},{"when":"Nov 16","name":"Upper/lower","mins":55,"kcal":250},{"when":"Nov 14","name":"Upper/lower","mins":55,"kcal":250},{"when":"Nov 13","name":"Upper/lower","mins":55,"kcal":250},{"when":"Nov 9","name":"Upper/lower","mins":55,"kcal":250},{"when":"Nov 7","name":"Upper/lower","mins":55,"kcal":250}]},
  "nutrition": {"kcalLeft":540,"rings":[{"key":"calories","label":"Calories","value":1660,"target":2200,"shown":"1,660","sub":"of 2,200"},{"key":"protein","label":"Protein","value":124,"target":170,"shown":"124 g","sub":"of 170 g"},{"key":"carbs","label":"Carbs","value":174,"target":230,"shown":"174 g","sub":"of 230 g"},{"key":"fat","label":"Fat","value":51,"target":65,"shown":"51 g","sub":"of 65 g"}],"meals":[{"label":"Breakfast","value":415},{"label":"Lunch","value":498},{"label":"Dinner","value":581},{"label":"Snack","value":166}],"cal7":{"labels":["Thu","Fri","Sat","Sun","Mon","Tue","Wed"],"values":[0,1943,2333,2083,2467,2431,1660],"target":2200},"avgIntake":"2,153","avgProtein":"161 g","proteinDays":"4/6"},
  "activity": {"steps":6357,"goal":9000,"pct":71,"week":{"labels":["Thu","Fri","Sat","Sun","Mon","Tue","Wed"],"values":[10312,6333,4511,10222,8903,12369,6357]},"avg30":"8,334","goalDays":"12/30","best":"12,369"},
  "health": {"recovery":{"value":66,"state":"Steady","coach":"Sleep was short. Keep today light and hit your protein."},"sleep":{"labels":["Thu","Fri","Sat","Sun","Mon","Tue","Wed"],"values":[0,6.4,6.0,7.2,7.4,7.2,6.0],"avg":6.7,"last":6.0,"goal":7.5,"pct":57},"weight":{"unit":"lb","labels":["Oct 22","Oct 23","Oct 24","Oct 25","Oct 26","Oct 27","Oct 28","Oct 29","Oct 30","Oct 31","Nov 1","Nov 2","Nov 3","Nov 4","Nov 5","Nov 6","Nov 7","Nov 8","Nov 9","Nov 10","Nov 11","Nov 12","Nov 13","Nov 14","Nov 15","Nov 16","Nov 17","Nov 18"],"daily":[186.3,187.8,186.5,185.6,185.4,187.0,null,185.8,null,185.4,184.3,185.0,185.0,185.8,184.7,184.7,184.3,184.1,183.9,185.0,184.5,184.7,184.7,184.1,184.3,null,183.9,181.9],"avg":[187.17,187.26,187.04,186.73,186.33,186.44,186.44,186.36,186.07,185.85,185.58,185.5,185.1,185.22,185.04,185.0,184.84,184.81,184.65,184.65,184.46,184.46,184.46,184.43,184.46,184.56,184.38,183.94],"goal":173.1,"current":183.9,"change":-3.2},"water":{"labels":["Thu","Fri","Sat","Sun","Mon","Tue","Wed"],"values":[0.0,97.4,105.7,69.7,74.1,93.8,54.1],"unit":"oz","today":"54","goal":101.4,"pct":53}},
  "peptides": {"compound":"Tirzepatide","brand":"Zepbound","cadence":"weekly","levelNow":6.27,"levelNext":3.1,"ssHigh":7.2,"ssLow":3.2,"lastMg":"5 mg","lastWhen":"Mon, Nov 16, 7:30 pm","lastSite":"Abdomen, upper right","nextSite":"Abdomen, lower left","nextCountdown":"5d 2h","nextWhen":"Mon, Nov 23, 7:30 pm","elapsed":0.272,"lastSiteKey":"abdomen_ur","nextSiteKey":"abdomen_ll","past":[[0.0,1.729],[0.0111,1.651],[0.0222,1.577],[0.0333,1.505],[0.0444,3.064],[0.0556,3.465],[0.0667,3.487],[0.0778,3.389],[0.0889,3.255],[0.1,3.115],[0.1111,2.976],[0.1222,2.843],[0.1333,2.714],[0.1444,2.592],[0.1556,2.475],[0.1667,2.363],[0.1778,2.256],[0.1889,2.155],[0.2,2.057],[0.2111,1.964],[0.2222,1.876],[0.2333,1.791],[0.2444,1.71],[0.2556,1.633],[0.2667,1.559],[0.2778,4.741],[0.2889,5.606],[0.3,5.71],[0.3111,5.571],[0.3222,5.358],[0.3333,5.129],[0.3444,4.902],[0.3556,4.682],[0.3667,4.471],[0.3778,4.269],[0.3889,4.077],[0.4,3.893],[0.4111,3.717],[0.4222,3.549],[0.4333,3.389],[0.4444,3.236],[0.4556,3.09],[0.4667,2.95],[0.4778,2.817],[0.4889,2.69],[0.5,2.568],[0.5111,5.705],[0.5222,6.526],[0.5333,6.589],[0.5444,6.409],[0.5556,6.159],[0.5667,5.894],[0.5778,5.632],[0.5889,5.379],[0.6,5.137],[0.6111,4.905],[0.6222,4.684],[0.6333,4.472],[0.6444,4.27],[0.6556,4.077],[0.6667,3.893],[0.6778,3.717],[0.6889,3.55],[0.7,3.389],[0.7111,3.236],[0.7222,3.09],[0.7333,2.951],[0.7444,6.07],[0.7556,6.874],[0.7667,6.921],[0.7778,6.727],[0.7889,6.463],[0.7967,6.266]],"future":[[0.7967,6.266],[0.8078,5.989],[0.819,5.721],[0.8301,5.463],[0.8412,5.216],[0.8523,4.981],[0.8634,4.756],[0.8745,4.541],[0.8856,4.336],[0.8967,4.14],[0.9078,3.953],[0.919,3.775],[0.9301,3.604],[0.9412,3.442],[0.9523,3.286],[0.9634,3.138],[0.9745,5.653],[0.9856,6.89],[0.9967,7.074]],"doseX":[0.0333,0.2667,0.5,0.7333,0.9667],"nowX":0.7967,"ticks":[[0.0,"Oct 25"],[0.3333,"Nov 4"],[0.6667,"Nov 14"],[1.0,"Nov 24"]],"effects":[{"key":"nausea","label":"Nausea","value":6.0,"target":10,"shown":"6/10","sub":""},{"key":"heartburn","label":"Heartburn","value":2.0,"target":10,"shown":"2/10","sub":""},{"key":"food_noise","label":"Food noise","value":3.0,"target":10,"shown":"3/10","sub":""},{"key":"suppressed_appetite","label":"Suppressed appetite","value":6.0,"target":10,"shown":"6/10","sub":""},{"key":"fatigue","label":"Fatigue","value":5.0,"target":10,"shown":"5/10","sub":""},{"key":"constipation","label":"Constipation","value":3.0,"target":10,"shown":"3/10","sub":""}],"coach":"Appetite is suppressed. Small, protein-rich meals keep intake up."}
};
// DATA-END
// PHOTO-START
const PHOTO = {"src": "data:image/jpeg;base64,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", "pose": "front", "before": "Nov 1, 2026", "after": "Nov 18, 2026", "days": 17, "weight": "-2.4 lb"} as PhotoData | null;
// PHOTO-END

const fmt = (n: number) => Math.round(n).toLocaleString("en-US");
const TAB: Record<string, string> = { workouts: "Workouts", nutrition: "Diet", activity: "Activity", health: "Health", peptides: "Meds" };

// Monotone cubic (Fritsch-Carlson) path through points: smooth, never overshoots the data.
function smoothPath(pts: [number, number][]): string {
  const n = pts.length;
  if (n === 0) return "";
  if (n === 1) return "M" + pts[0][0].toFixed(1) + " " + pts[0][1].toFixed(1);
  const dx: number[] = [], m: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    dx.push(pts[i + 1][0] - pts[i][0]);
    m.push(dx[i] ? (pts[i + 1][1] - pts[i][1]) / dx[i] : 0);
  }
  const t: number[] = [m[0]];
  for (let i = 1; i < n - 1; i++) t.push(m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2);
  t.push(m[n - 2]);
  for (let i = 0; i < n - 1; i++) {
    if (m[i] === 0) { t[i] = 0; t[i + 1] = 0; continue; }
    const a = t[i] / m[i], b = t[i + 1] / m[i], q = a * a + b * b;
    if (q > 9) { const k = 3 / Math.sqrt(q); t[i] = k * a * m[i]; t[i + 1] = k * b * m[i]; }
  }
  let d = "M" + pts[0][0].toFixed(1) + " " + pts[0][1].toFixed(1);
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3;
    d += " C" + (pts[i][0] + h).toFixed(1) + " " + (pts[i][1] + t[i] * h).toFixed(1) + " " +
      (pts[i + 1][0] - h).toFixed(1) + " " + (pts[i + 1][1] - t[i + 1] * h).toFixed(1) + " " +
      pts[i + 1][0].toFixed(1) + " " + pts[i + 1][1].toFixed(1);
  }
  return d;
}

// Arc as an SVG path (clockwise from 12 o'clock) so round caps and a second lap are easy.
function arc(c: number, r: number, frac: number): string {
  const f = Math.min(Math.max(frac, 0), 0.9999);
  const a = f * 2 * Math.PI - Math.PI / 2;
  const x = c + r * Math.cos(a), y = c + r * Math.sin(a);
  return "M" + c + " " + (c - r) + " A" + r + " " + r + " 0 " + (f > 0.5 ? 1 : 0) + " 1 " + x.toFixed(2) + " " + y.toFixed(2);
}

type Ink = { ink: string; muted: string; track: string; font: string };

// Hero readiness ring: one arc, round caps, big tabular number.
function ScoreRing(p: Ink & { value: number | null; state: string; color: string }) {
  const S = 220, c = 110, stroke = 16, rad = c - stroke / 2 - 2;
  const frac = (p.value ?? 0) / 100;
  return (
    <svg viewBox={"0 0 " + S + " " + S} width="100%" style={{ maxWidth: 260, display: "block", margin: "0 auto" }} role="img"
      aria-label={"Recovery " + (p.value === null ? "not available" : p.value + " percent, " + p.state)}>
      <circle cx={c} cy={c} r={rad} fill="none" stroke={p.color} strokeOpacity={0.16} strokeWidth={stroke} />
      {frac > 0 && <path d={arc(c, rad, frac)} fill="none" stroke={p.color} strokeWidth={stroke} strokeLinecap="round" />}
      <text x={c} y={c - 30} textAnchor="middle" fontSize={12} fontWeight={600} fill={p.muted} fontFamily={p.font}>Recovery</text>
      <text x={c} y={c + 24} textAnchor="middle" fontSize={64} fontWeight={800} fill={p.ink} fontFamily={p.font} style={{ letterSpacing: -2.5 }}>{p.value === null ? "\u2013" : String(p.value)}</text>
      <text x={c} y={c + 50} textAnchor="middle" fontSize={14} fontWeight={600} fill={p.color} fontFamily={p.font}>{p.state}</text>
    </svg>
  );
}

// Concentric rings: calories (outer), protein, carbs, fat. Overflow draws a second lap.
function Rings(p: Ink & { rings: Ring[]; color: string; kcalLeft: number }) {
  const S = 260, c = 130, stroke = 16, gap = 4;
  const over = p.kcalLeft < 0;
  return (
    <svg viewBox={"0 0 " + S + " " + S} width="100%" style={{ maxWidth: 320, display: "block", margin: "0 auto" }} role="img"
      aria-label={"Calories, protein, carbs and fat today. " + fmt(Math.abs(p.kcalLeft)) + (over ? " kcal over" : " kcal left")}>
      {p.rings.slice(0, 4).map((r, i) => {
        const rad = c - stroke / 2 - 4 - i * (stroke + gap);
        const tone = 1 - i * 0.2;
        const frac = r.target > 0 ? r.value / r.target : 0;
        return (
          <g key={r.key}>
            <circle cx={c} cy={c} r={rad} fill="none" stroke={p.color} strokeOpacity={0.18} strokeWidth={stroke} />
            {frac > 0 && <path d={arc(c, rad, Math.min(frac, 1))} fill="none" stroke={p.color} strokeOpacity={tone} strokeWidth={stroke} strokeLinecap="round" />}
            {frac > 1 && <path d={arc(c, rad, frac - 1)} fill="none" stroke={p.color} strokeOpacity={tone} strokeWidth={stroke} strokeLinecap="round" />}
          </g>
        );
      })}
      <text x={c} y={c + 6} textAnchor="middle" fontSize={44} fontWeight={700} fill={p.ink} fontFamily={p.font} style={{ letterSpacing: -1.5 }}>{fmt(Math.abs(p.kcalLeft))}</text>
      <text x={c} y={c + 28} textAnchor="middle" fontSize={13} fontWeight={500} fill={p.muted} fontFamily={p.font}>{over ? "kcal over" : "kcal left"}</text>
    </svg>
  );
}

// Thin progress bar. Rule for every SVG here: never fill a rect with a neutral (ink or white) colour, the host reads it as a dark or light panel and re-themes the whole page. Pillar hues only.
function Bar(p: Ink & { label: string; shown: string; sub: string; frac: number; color: string }) {
  const frac = Math.min(Math.max(p.frac, 0), 1);
  return (
    <div style={{ fontFamily: p.font }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: p.muted }}>
        <span>{p.label}</span><span>{p.sub}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 600, color: p.ink, margin: "2px 0 6px" }}>{p.shown}</div>
      <svg viewBox="0 0 100 6" width="100%" height={6} preserveAspectRatio="none" role="img" aria-label={p.label + " progress"}>
        <rect x={0} y={0} width={100} height={6} rx={3} fill={p.color} fillOpacity={0.18} />
        <rect x={0} y={0} width={Math.max(frac * 100, frac > 0 ? 3 : 0)} height={6} rx={3} fill={p.color} />
      </svg>
    </div>
  );
}

// Column chart in a pillar colour: the last column is the strongest, a dashed line marks the goal.
function Cols(p: Ink & { labels: string[]; values: number[]; color: string; ref?: number; refLabel?: string; fmtv?: (v: number) => string; h?: number; every?: number }) {
  const bare = p.labels.every((l) => l === "");
  const W = 340, H = p.h ?? 150, L = 0, T = bare ? 4 : 22, B = bare ? 4 : 22, n = p.values.length;
  const top = Math.max(...p.values, p.ref ?? 0, 1) * 1.1;
  const bw = (W / n) * 0.66, step = W / n;
  const y = (v: number) => T + (1 - v / top) * (H - T - B);
  const f = p.fmtv ?? fmt;
  const ry = p.ref !== undefined ? y(p.ref) : null;
  return (
    <svg viewBox={"0 0 " + W + " " + H} width="100%" role="img" aria-label={(p.refLabel ?? "") + " " + p.labels.join(", ")} style={{ fontFamily: p.font }}>
      {p.values.map((v, i) => {
        const last = i === n - 1;
        const hh = Math.max(H - B - y(v), v > 0 ? 3 : 0);
        return (
          <g key={i}>
            <rect x={L + i * step + (step - bw) / 2} y={H - B - hh} width={bw} height={hh} rx={Math.min(5, bw / 2)} fill={p.color} fillOpacity={last ? 1 : 0.42} />
            {(n <= 8 || i % (p.every ?? 1) === 0 || last) && p.labels[i] !== "" && (
              <text x={L + i * step + step / 2} y={H - 6} textAnchor="middle" fontSize={11} fill={p.muted}>{p.labels[i]}</text>
            )}
          </g>
        );
      })}
      {ry !== null && <line x1={0} x2={W} y1={ry} y2={ry} stroke={p.ink} strokeOpacity={0.5} strokeWidth={1.2} strokeDasharray="3 4" />}
      {ry !== null && p.refLabel && <text x={0} y={ry - 5} fontSize={11} fontWeight={600} fill={p.ink} fillOpacity={0.8}>{p.refLabel}</text>}
      {n <= 8 && !bare && <text x={L + (n - 1) * step + step / 2} y={y(p.values[n - 1]) - 6} textAnchor="middle" fontSize={12} fontWeight={600} fill={p.ink}>{f(p.values[n - 1])}</text>}
    </svg>
  );
}

// A week of dots: filled = trained.
function Dots(p: Ink & { days: Workouts["days"]; color: string; check: string; big?: boolean }) {
  const r = p.big ? 14 : 10, gap = p.big ? 12 : 8;
  const W = 7 * (2 * r) + 6 * gap, H = 2 * r + (p.big ? 22 : 0);
  return (
    <svg viewBox={"0 0 " + W + " " + H} width="100%" style={{ maxWidth: W * (p.big ? 1.2 : 1), fontFamily: p.font, display: "block" }} role="img" aria-label="Workouts this week">
      {p.days.map((d, i) => {
        const cx = r + i * (2 * r + gap);
        return (
          <g key={i}>
            <circle cx={cx} cy={r} r={r - 1} fill={d.done ? p.color : "none"} stroke={d.done ? p.color : p.ink} strokeOpacity={d.done ? 1 : 0.28} strokeWidth={2} />
            {d.done && <path d={"M" + (cx - r * 0.38) + " " + r + " l" + r * 0.28 + " " + r * 0.3 + " l" + r * 0.5 + " " + -r * 0.6} fill="none" stroke={p.check} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />}
            {p.big && <text x={cx} y={H - 2} textAnchor="middle" fontSize={11} fill={p.muted}>{d.label}</text>}
          </g>
        );
      })}
    </svg>
  );
}

function WeightChart(p: { w: Weight; color: string; ink: string; muted: string; font: string }) {
  const W = 340, H = 220, L = 36, R = 12, T = 34, B = 30;
  const n = p.w.labels.length;
  const vals: number[] = [];
  p.w.daily.forEach((v) => { if (v !== null) vals.push(v); });
  p.w.avg.forEach((v) => { if (v !== null) vals.push(v); });
  let lo = Math.min(...vals);
  let hi = Math.max(...vals);
  const span = Math.max(hi - lo, 0.5);
  const goal = p.w.goal;
  // A goal inside the data range gets a dashed line; a far-away goal becomes a chip so the trend stays readable.
  const showGoal = goal !== null && lo - goal <= span && goal - hi <= span;
  if (goal !== null && showGoal) { lo = Math.min(lo, goal); hi = Math.max(hi, goal); }
  const pad = Math.max((hi - lo) * 0.18, 0.5);
  lo -= pad; hi += pad;
  const x = (i: number) => L + (n > 1 ? (i * (W - L - R)) / (n - 1) : 0);
  const y = (v: number) => T + ((hi - v) * (H - T - B)) / (hi - lo);
  const pts: [number, number][] = [];
  p.w.avg.forEach((v, i) => { if (v !== null) pts.push([x(i), y(v)]); });
  const keep = Math.max(1, Math.ceil(pts.length / 14));
  const thin = pts.filter((_, i) => i % keep === 0);
  if (pts.length > 0 && thin[thin.length - 1] !== pts[pts.length - 1]) thin.push(pts[pts.length - 1]);
  const line = smoothPath(thin);
  const base = H - B + 4;
  const fill = thin.length > 1 ? line + " L" + thin[thin.length - 1][0].toFixed(1) + " " + base + " L" + thin[0][0].toFixed(1) + " " + base + " Z" : "";
  const last = thin[thin.length - 1];
  const mid = (lo + hi) / 2;
  const xt = [0, Math.floor((n - 1) / 2), n - 1];
  return (
    <svg viewBox={"0 0 " + W + " " + H} width="100%" role="img" aria-label="Weight: daily weigh-ins, 7-day average curve, goal">
      <defs>
        <linearGradient id="wfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={p.color} stopOpacity="0.28" />
          <stop offset="1" stopColor={p.color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <text x={L - 8} y={y(mid) + 4} textAnchor="end" fontSize={11} fill={p.muted} fontFamily={p.font}>{mid.toFixed(0)}</text>
      {fill && <path d={fill} fill="url(#wfill)" />}
      {showGoal && goal !== null && (
        <g>
          <line x1={L} x2={W - R} y1={y(goal)} y2={y(goal)} stroke={p.muted} strokeWidth={1.5} strokeDasharray="2 5" strokeLinecap="round" />
          <text x={W - R} y={y(goal) - 7} textAnchor="end" fontSize={11} fontWeight={600} fill={p.ink} fontFamily={p.font}>{"Goal " + goal.toFixed(1)}</text>
        </g>
      )}
      {goal !== null && !showGoal && (
        <text x={W - R} y={T - 14} textAnchor="end" fontSize={11} fontWeight={600} fill={p.muted} fontFamily={p.font}>{(goal < lo ? "\u2193 " : "\u2191 ") + "Goal " + goal.toFixed(1)}</text>
      )}
      {p.w.daily.map((v, i) => (v === null ? null : <circle key={i} cx={x(i)} cy={y(v)} r={2.6} fill={p.ink} fillOpacity={0.28} />))}
      <path d={line} fill="none" stroke={p.color} strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" />
      {last && (<g><circle cx={last[0]} cy={last[1]} r={6.5} fill={p.color} /><circle cx={last[0]} cy={last[1]} r={2.5} fill={p.muted} fillOpacity={0.35} /></g>)}
      {xt.map((i, k) => (
        <text key={k} x={x(i)} y={H - 8} textAnchor={k === 0 ? "start" : k === 2 ? "end" : "middle"} fontSize={11} fill={p.muted} fontFamily={p.font}>{p.w.labels[i]}</text>
      ))}
    </svg>
  );
}

// Estimated medication level: solid past, dashed projection if the schedule is kept, dose ticks, now-dot with callout.
function MedChart(p: { t: Treatment; color: string; ink: string; muted: string; track: string; font: string }) {
  const W = 340, H = 210, L = 30, R = 8, T = 40, B = 28;
  const all = p.t.past.concat(p.t.future);
  const top = Math.max(...all.map((q) => q[1]), 0.01) * 1.2;
  const rough = top / 3;
  const mag = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((v) => v >= rough) || rough;
  const ticks: number[] = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const ymax = Math.max(top, ticks[ticks.length - 1] * 1.05);
  const x = (f: number) => L + f * (W - L - R);
  const y = (v: number) => T + (1 - v / ymax) * (H - T - B);
  const line = (pts: [number, number][]) => pts.map((q, i) => (i ? "L" : "M") + x(q[0]).toFixed(1) + " " + y(q[1]).toFixed(1)).join(" ");
  const nowPt = p.t.past[p.t.past.length - 1];
  const nx = x(p.t.nowX), ny = y(nowPt[1]);
  const fillPath = line(p.t.past) + " L" + x(p.t.past[p.t.past.length - 1][0]).toFixed(1) + " " + y(0).toFixed(1) + " L" + x(p.t.past[0][0]).toFixed(1) + " " + y(0).toFixed(1) + " Z";
  return (
    <svg viewBox={"0 0 " + W + " " + H} width="100%" role="img" aria-label={"Estimated " + p.t.compound + " level over the last 30 days, now " + p.t.levelNow.toFixed(2) + " mg"} style={{ fontFamily: p.font }}>
      {ticks.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={p.track} strokeWidth={1} />
          <text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill={p.muted}>{String(Math.round(v * 100) / 100)}</text>
        </g>
      ))}
      <path d={fillPath} fill={p.color} fillOpacity={0.14} />
      <path d={line(p.t.past)} fill="none" stroke={p.color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
      <path d={line(p.t.future)} fill="none" stroke={p.color} strokeWidth={2.5} strokeDasharray="5 5" strokeLinecap="round" />
      {p.t.doseX.map((f, i) => <line key={i} x1={x(f)} x2={x(f)} y1={y(0) - 7} y2={y(0)} stroke={p.color} strokeWidth={2} strokeLinecap="round" />)}
      <line x1={nx} x2={nx} y1={ny} y2={y(0)} stroke={p.muted} strokeWidth={1} strokeDasharray="2 3" />
      <circle cx={nx} cy={ny} r={5} fill={p.color} stroke={p.ink} strokeOpacity={0.5} strokeWidth={1.5} />
      <text x={Math.min(nx, W - 44)} y={14} textAnchor="middle" fontSize={15} fontWeight={600} fill={p.ink}>{nowPt[1].toFixed(2) + " mg"}</text>
      <text x={Math.min(nx, W - 44)} y={29} textAnchor="middle" fontSize={11} fill={p.muted}>Now</text>
      {p.t.ticks.map((tk, i) => <text key={i} x={x(tk[0] as number)} y={H - 8} textAnchor={i === 0 ? "start" : i === p.t.ticks.length - 1 ? "end" : "middle"} fontSize={11} fill={p.muted}>{String(tk[1])}</text>)}
    </svg>
  );
}

// Front-view body map. The person's left is on the right of the picture. Filled dot: last site. Dashed ring: suggested next.
const SITE_POS: Record<string, [number, number]> = {
  abdomen_ur: [64, 98], abdomen_ul: [96, 98], abdomen_lr: [64, 116], abdomen_ll: [96, 116],
  thigh_r: [60, 168], thigh_l: [100, 168], arm_r: [28, 84], arm_l: [132, 84],
};
function SiteMap(p: { last: string; next: string; color: string; muted: string; track: string; font: string }) {
  const body = { fill: "none", stroke: p.muted, strokeOpacity: 0.5, strokeWidth: 1.5 } as const;
  return (
    <svg viewBox="0 0 160 220" width="100%" role="img" aria-label={"Last site " + p.last + ", suggested next " + p.next} style={{ fontFamily: p.font, maxWidth: 200 }}>
      <circle cx={80} cy={26} r={16} {...body} />
      <rect x={72} y={42} width={16} height={8} rx={4} {...body} />
      <rect x={46} y={50} width={68} height={86} rx={16} {...body} />
      <rect x={20} y={56} width={22} height={64} rx={11} {...body} />
      <rect x={118} y={56} width={22} height={64} rx={11} {...body} />
      <rect x={48} y={140} width={30} height={72} rx={14} {...body} />
      <rect x={82} y={140} width={30} height={72} rx={14} {...body} />
      <text x={10} y={14} fontSize={10} fill={p.muted}>R</text>
      <text x={144} y={14} fontSize={10} fill={p.muted}>L</text>
      {Object.keys(SITE_POS).map((k) => <circle key={k} cx={SITE_POS[k][0]} cy={SITE_POS[k][1]} r={2.5} fill={p.muted} fillOpacity={0.5} />)}
      {SITE_POS[p.last] && <circle cx={SITE_POS[p.last][0]} cy={SITE_POS[p.last][1]} r={7} fill={p.color} />}
      {SITE_POS[p.next] && <circle cx={SITE_POS[p.next][0]} cy={SITE_POS[p.next][1]} r={9} fill="none" stroke={p.color} strokeWidth={2} strokeDasharray="3 3" />}
    </svg>
  );
}

export default function App() {
  const theme = useGrokTheme();
  const [view, setView] = useState("overview");
  const pal = theme.kind === "dark" ? DATA.pal.dark : DATA.pal.light;
  const [cRec, cSleep, cNut, cWater, cAct, cMed] = pal;
  const cWork = cAct; // workouts and steps share the activity hue, as in the images
  const ink = theme.text.primary;
  const muted = theme.text.secondary;
  const track = theme.border.subtle;
  const font = theme.font.family;
  const k: Ink = { ink, muted, track, font };
  const shown = DATA.shown;
  const open = shown.indexOf(view) >= 0 ? view : "overview"; // a module that is switched off can never be opened
  const tabs = [{ value: "overview", label: "Overview" }, ...shown.map((m) => ({ value: m, label: TAB[m] || m }))];
  const col: Record<string, string> = { workouts: cWork, nutrition: cNut, activity: cAct, health: cRec, peptides: cMed };

  const tile = (id: string, children: any) => (
    <button type="button" onClick={() => setView(id)} aria-label={"Open " + DATA.titles[id]}
      style={{ display: "block", width: "100%", textAlign: "left", background: "none", border: "none", borderTop: "1px solid " + track, padding: "20px 0", cursor: "pointer", color: ink, fontFamily: font }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 15, fontWeight: 600 }}>
          <span style={{ width: 10, height: 10, borderRadius: 5, background: col[id], display: "inline-block" }} />{DATA.titles[id]}
        </span>
        <span style={{ color: muted, fontSize: 20, lineHeight: "20px" }} aria-hidden="true">{"\u203A"}</span>
      </div>
      {children}
    </button>
  );
  const big = (value: string, unit: string, label: string, color?: string) => (
    <div style={{ fontFamily: font }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
        <span style={{ fontSize: 40, fontWeight: 700, letterSpacing: -1, color: color ?? ink, lineHeight: "42px" }}>{value}</span>
        {unit && <span style={{ fontSize: 14, color: muted }}>{unit}</span>}
      </div>
      <div style={{ fontSize: 13, color: muted, marginTop: 4 }}>{label}</div>
    </div>
  );
  const trio = (items: { label: string; value: string; unit: string; sub: string; frac?: number; color: string }[]) => (
    <div style={{ display: "flex", gap: 16 }}>
      {items.map((it) => (
        <div key={it.label} style={{ flex: 1, minWidth: 0, fontFamily: font }}>
          <div style={{ fontSize: 13, color: muted }}>{it.label}</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginTop: 2 }}>
            <span style={{ fontSize: 26, fontWeight: 700, color: ink }}>{it.value}</span><span style={{ fontSize: 13, color: muted }}>{it.unit}</span>
          </div>
          {it.frac !== undefined ? (
            <svg viewBox="0 0 100 4" width="100%" height={4} preserveAspectRatio="none" style={{ display: "block", margin: "6px 0 4px" }} aria-hidden="true">
              <rect x={0} y={0} width={100} height={4} rx={2} fill={it.color} fillOpacity={0.18} />
              <rect x={0} y={0} width={Math.min(Math.max(it.frac, 0), 1) * 100} height={4} rx={2} fill={it.color} />
            </svg>
          ) : <div style={{ height: 4, margin: "6px 0 4px" }} />}
          <div style={{ fontSize: 12, color: muted }}>{it.sub}</div>
        </div>
      ))}
    </div>
  );

  const w = DATA.workouts, n = DATA.nutrition, a = DATA.activity, h = DATA.health, p = DATA.peptides;

  // ---------------------------------------------------------------- overview
  const overview = (
    <div>
      {h && (
        <Section>
          <ScoreRing {...k} value={h.recovery.value} state={h.recovery.state} color={cRec} />
          {h.recovery.coach && <div style={{ textAlign: "center", fontSize: 14, color: ink, fontFamily: font, padding: "4px 8px" }}>{h.recovery.coach}</div>}
        </Section>
      )}
      {w && tile("workouts", <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16 }}>
            {big(String(w.sessions) + (w.planned ? " of " + w.planned : ""), "", "sessions this week")}
            <div style={{ width: 190, flex: "none" }}><Dots {...k} days={w.days} color={cWork} check={theme.bg.base} /></div>
          </div>
          {w.last && <div style={{ fontSize: 13, color: muted, marginTop: 10 }}>{w.last}</div>}
        </div>)}
      {n && tile("nutrition", <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
            {big(fmt(Math.abs(n.kcalLeft)), "kcal", n.kcalLeft >= 0 ? "left today" : "over today")}
            <span style={{ fontSize: 26, fontWeight: 700, color: cNut, fontFamily: font }}>{n.rings[0].target > 0 ? Math.round((100 * n.rings[0].value) / n.rings[0].target) + "%" : ""}</span>
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 16 }}>
            {n.rings.slice(1, 4).map((r) => (
              <div key={r.key} style={{ flex: 1, minWidth: 0 }}>
                <Bar {...k} label={r.label} shown={r.shown} sub="" frac={r.target > 0 ? r.value / r.target : 0} color={cNut} />
              </div>
            ))}
          </div>
        </div>)}
      {a && tile("activity", <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16 }}>
            {big(a.steps ? fmt(a.steps) : "\u2013", "steps", a.pct + "% of " + fmt(a.goal))}
            <div style={{ width: 140, flex: "none" }}><Cols {...k} labels={a.week.labels.map(() => "")} values={a.week.values} color={cAct} h={110} /></div>
          </div>
        </div>)}
      {h && tile("health", <div>
          {trio([
            ...(h.sleep && h.sleep.last !== null ? [{ label: "Sleep", value: h.sleep.last.toFixed(1), unit: "h", sub: (h.sleep.pct ?? 0) + "% of goal", frac: (h.sleep.pct ?? 0) / 100, color: cSleep }] : []),
            ...(h.weight && h.weight.current !== null ? [{ label: "Weight", value: h.weight.current.toFixed(1), unit: h.weight.unit, sub: h.weight.change === null ? "steady" : (h.weight.change < 0 ? "down " : "up ") + Math.abs(h.weight.change).toFixed(1) + " in " + h.weight.labels.length + " days", color: ink }] : []),
            ...(h.water ? [{ label: "Water", value: h.water.today, unit: h.water.unit, sub: (h.water.pct ?? 0) + "% of goal", frac: (h.water.pct ?? 0) / 100, color: cWater }] : []),
          ])}
        </div>)}
      {p && tile("peptides", <div>
          {big(p.nextCountdown, "", "Next dose " + p.nextWhen, cMed)}
          <div style={{ fontSize: 13, color: muted, marginTop: 10 }}>{p.compound + " \u00B7 " + p.lastMg + " " + p.cadence + " \u00B7 " + p.levelNow.toFixed(1) + " mg estimated now"}</div>
        </div>)}
    </div>
  );

  // ----------------------------------------------------------------- details
  const detail = (id: string) => {
    if (id === "workouts" && w) return (
      <div>
        <Section heading="Sessions this week">
          {big(String(w.sessions) + (w.planned ? " of " + w.planned : ""), "", w.planned ? "planned this week" : "this week")}
          <Dots {...k} days={w.days} color={cWork} check={theme.bg.base} big />
          <Metrics metrics={[
            { value: fmt(w.minutes) + " min", label: "Minutes" },
            { value: fmt(w.kcal) + " kcal", label: "Estimated burn" },
            { value: w.avg + " min", label: "Average session" },
          ]} />
        </Section>
        <Section heading="Minutes per week, last 8 weeks">
          <Cols {...k} labels={w.weeks.labels} values={w.weeks.values} color={cWork} every={3} />
        </Section>
        {w.recent.length > 0 && (
          <Section heading="Recent sessions">
            <Properties items={w.recent.map((r) => ({ label: r.when, value: r.name + ", " + r.mins + " min, " + r.kcal + " kcal" }))} />
          </Section>
        )}
      </div>
    );
    if (id === "nutrition" && n) return (
      <div>
        <Section heading="Calories and macros today">
          <Rings {...k} rings={n.rings} color={cNut} kcalLeft={n.kcalLeft} />
          <Metrics metrics={n.rings.slice(1, 4).map((r) => ({ value: r.shown, label: r.label, detail: r.value > r.target ? fmt(r.value - r.target) + " g over" : fmt(Math.max(r.target - r.value, 0)) + " g left" }))} />
        </Section>
        {n.meals.length > 0 && (
          <Section heading="By meal">
            <Properties items={n.meals.map((m) => ({ label: m.label, value: fmt(m.value) + " kcal" }))} />
          </Section>
        )}
        <Section heading="Calories, last 7 days">
          <Cols {...k} labels={n.cal7.labels} values={n.cal7.values} color={cNut} ref={n.cal7.target} refLabel={"Target " + fmt(n.cal7.target)} />
          <Metrics metrics={[
            { value: n.avgIntake, label: "Average intake" },
            { value: n.avgProtein, label: "Average protein" },
            { value: n.proteinDays, label: "Protein days" },
          ]} />
        </Section>
      </div>
    );
    if (id === "activity" && a) return (
      <div>
        <Section heading="Steps today">
          {big(a.steps ? fmt(a.steps) : "\u2013", "", a.pct + "% of your " + fmt(a.goal) + " goal")}
          <Bar {...k} label="Goal" shown="" sub={fmt(a.goal)} frac={a.goal > 0 ? a.steps / a.goal : 0} color={cAct} />
        </Section>
        <Section heading="Last 7 days">
          <Cols {...k} labels={a.week.labels} values={a.week.values} color={cAct} ref={a.goal} refLabel={"Goal " + fmt(a.goal)} />
          <Metrics metrics={[
            { value: a.avg30, label: "30-day average" },
            { value: a.goalDays, label: "Goal days" },
            { value: a.best, label: "Best day" },
          ]} />
        </Section>
      </div>
    );
    if (id === "health" && h) return (
      <div>
        <Section>
          <ScoreRing {...k} value={h.recovery.value} state={h.recovery.state} color={cRec} />
          {h.recovery.coach && <div style={{ textAlign: "center", fontSize: 14, color: ink, fontFamily: font, padding: "4px 8px" }}>{h.recovery.coach}</div>}
        </Section>
        {h.sleep && (
          <Section heading="Sleep">
            {big(h.sleep.last !== null ? h.sleep.last.toFixed(1) : "\u2013", "h last night", h.sleep.avg.toFixed(1) + " h average")}
            <Cols {...k} labels={h.sleep.labels} values={h.sleep.values} color={cSleep} ref={h.sleep.goal} refLabel={"Goal " + h.sleep.goal + " h"} fmtv={(v) => v.toFixed(1)} />
          </Section>
        )}
        {h.weight && h.weight.daily.filter((v) => v !== null).length >= 2 && (
          <Section heading="Weight, last 28 days">
            <WeightChart w={h.weight} color={ink} ink={ink} muted={muted} font={font} />
          </Section>
        )}
        {h.water && (
          <Section heading="Water, last 7 days">
            {big(h.water.today, h.water.unit + " today", "goal " + h.water.goal + " " + h.water.unit)}
            <Cols {...k} labels={h.water.labels} values={h.water.values} color={cWater} ref={h.water.goal} refLabel={"Goal " + h.water.goal + " " + h.water.unit} />
          </Section>
        )}
        {PHOTO && (
          <Section heading={"Progress photos: " + PHOTO.pose}>
            <img src={PHOTO.src} alt={"Before and after, " + PHOTO.pose + " pose"} style={{ width: "100%", borderRadius: theme.radius.lg, display: "block" }} />
            <Properties items={[
              { label: "Before", value: PHOTO.before },
              { label: "After", value: PHOTO.after },
              { label: "Days between", value: String(PHOTO.days) },
              { label: "Weight change", value: PHOTO.weight },
            ]} />
          </Section>
        )}
      </div>
    );
    if (id === "peptides" && p) return (
      <div>
        <Section heading={p.compound + (p.brand ? " (" + p.brand + ")" : "")}>
          <Metrics metrics={[
            { value: p.levelNow.toFixed(2) + " mg", label: "Estimated level now", detail: "Model estimate, not a blood level" },
            { value: p.nextCountdown, label: "Next dose", detail: p.nextWhen },
          ]} />
          <MedChart t={p} color={cMed} ink={ink} muted={muted} track={track} font={font} />
          <div style={{ display: "flex", gap: 16, fontSize: 12, color: muted, fontFamily: font }}>
            <span>Solid: estimated so far</span><span>Dashed: if the schedule is kept</span>
          </div>
          <Metrics metrics={[
            { value: p.levelNext.toFixed(2) + " mg", label: "At next dose" },
            { value: p.ssHigh.toFixed(1) + " mg", label: "Steady-state high" },
            { value: p.ssLow.toFixed(1) + " mg", label: "Steady-state low" },
          ]} />
          {p.coach && <div style={{ fontSize: 14, color: ink, fontFamily: font, padding: "4px 0" }}>{p.coach}</div>}
        </Section>
        <Section heading="Last dose and injection site">
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <Metrics metrics={[{ value: p.lastMg, label: "Last dose", detail: p.lastWhen + ". " + p.lastSite }]} />
              <div style={{ fontSize: 13, color: muted, fontFamily: font, marginTop: 8 }}>Suggested next site: <span style={{ color: ink }}>{p.nextSite}</span></div>
            </div>
            <div style={{ width: 150, flex: "none" }}><SiteMap last={p.lastSiteKey} next={p.nextSiteKey} color={cMed} muted={muted} track={track} font={font} /></div>
          </div>
        </Section>
        {p.effects.length > 0 && (
          <Section heading="How you feel">
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {p.effects.map((r) => (
                <Bar key={r.key} {...k} label={r.label} shown={r.shown} sub={r.sub} frac={r.target > 0 ? r.value / r.target : 0} color={cMed} />
              ))}
            </div>
          </Section>
        )}
      </div>
    );
    return null;
  };

  return (
    <Page title={DATA.name + "'s Grok Life"} summary={DATA.dateLabel + ". " + DATA.streak + "-day streak. Updated " + DATA.updated + "."} width="column" palette={pal}>
      {shown.length > 0 && <Segmented options={tabs} value={open} onChange={setView} />}
      {open !== "overview" && <div><Button label={"\u2039 Overview"} onClick={() => setView("overview")} /></div>}
      {open === "overview" ? overview : detail(open)}
    </Page>
  );
}

