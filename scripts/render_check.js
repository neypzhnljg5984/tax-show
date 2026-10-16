// 用最小 DOM 桩执行 index.html 中的页面脚本，捕获运行时错误并回读关键渲染结果
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

// 取出 payload JSON 与主脚本
const payloadMatch = html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/);
if (!payloadMatch) throw new Error('未找到数据载荷');
const PAYLOAD_TEXT = payloadMatch[1];

const scripts = [...html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)];
if (scripts.length !== 1) throw new Error('脚本块数量异常: ' + scripts.length);
const code = scripts[0][1];

const written = {};
function mkEl(id) {
  const el = {
    id, _html: '', _text: '', value: '', className: '', clientWidth: 1000,
    style: {}, dataset: {}, children: [], onclick: null,
    set innerHTML(v) { this._html = String(v); written[id] = String(v); },
    get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); written[id] = String(v); },
    get textContent() { return this._text; },
    appendChild(c) { this.children.push(c); return c; },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    addEventListener() {},
  };
  return el;
}
const els = {};
const document = {
  getElementById(id) {
    if (!els[id]) els[id] = mkEl(id);
    if (id === 'payload') els[id].textContent = PAYLOAD_TEXT;
    return els[id];
  },
  createElement: (t) => mkEl('new-' + t),
  querySelectorAll: () => [],
  addEventListener: () => {},
};
const window = { addEventListener: () => {}, innerWidth: 1440 };
const sandbox = {
  document, window, console,
  JSON, Math, Number, String, Array, Object, Boolean, Date, isNaN, parseInt, parseFloat,
  setTimeout: () => 0, clearTimeout: () => {},
  Blob: function () {}, URL: { createObjectURL: () => '', revokeObjectURL: () => {} },
};
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
try {
  vm.runInContext(code, ctx, { filename: 'page-script.js' });
} catch (e) {
  console.error('❌ 页面脚本执行失败:', e.message);
  console.error(e.stack.split('\n').slice(0, 6).join('\n'));
  process.exit(1);
}

// ---- 断言关键渲染结果 ----
const problems = [];
const need = ['heroStats', 'stack', 'stackLegend', 'per100', 'readGuide', 'sankey', 'curve', 'curveLegend',
  'curveNote', 'heat', 'heatRange', 'rank', 'regionRank', 'regionNote', 'fullTable',
  'natChart', 'natTable', 'insights', 'policyCards', 'sources', 'assumptions', 'limits',
  'bdCost', 'bdHint', 'tblProv', 'asof'];
need.forEach(id => {
  const el = els[id];
  const v = written[id];
  const viaChildren = el && el.children.length;
  if ((v === undefined || v === '') && !viaChildren) problems.push(id + ' 未渲染');
  else if (/undefined|NaN|\[object Object\]/.test(String(v || ''))) problems.push(id + ' 含 undefined/NaN');
});

const stats = {
  '堆叠条分段数': (els.stack ? els.stack.children.length : 0),
  '桑基图节点数': (written.sankey || '').match(/<rect /g)?.length || 0,
  '曲线数据点数': (written.curve || '').match(/<circle/g)?.length || 0,
  '热力图单元格': (written.heat || '').match(/<td data-p/g)?.length || 0,
  '排名条目': (written.rank || '').match(/class="row/g)?.length || 0,
  '总表行数': (written.fullTable || '').match(/<tr data-i/g)?.length || 0,
  '全国柱数': (written.natChart || '').match(/<rect /g)?.length || 0,
  '参数卡数': (written.policyCards || '').match(/class="param"/g)?.length || 0,
  '曲线图例项': (els.curveLegend ? els.curveLegend.children.length : 0),
  '堆叠图例项': (els.stackLegend ? els.stackLegend.children.length : 0),
};
console.log('渲染结果统计:');
Object.entries(stats).forEach(([k, v]) => console.log('  ' + k + ': ' + v));

// 期望值检查
const expect = { '堆叠条分段数': 7, '桑基图节点数': 10, '曲线数据点数': 80, '排名条目': 31,
  '总表行数': 16, '参数卡数': 9, '曲线图例项': 5, '堆叠图例项': 7, '全国柱数': 112 };
Object.entries(expect).forEach(([k, v]) => {
  if (stats[k] !== v) problems.push(`${k} 期望 ${v}，实际 ${stats[k]}`);
});
// 热力图 31 行 × 16 列 = 496
if (stats['热力图单元格'] !== 496) problems.push('热力图单元格期望 496，实际 ' + stats['热力图单元格']);

// ---- 桑基图几何校验（顶点级）----
// 1) 每条连线两端必须落在自己柱子的纵向区间内
// 2) 每根柱子上所有流出段高度之和 = 柱高；所有流入段高度之和 = 柱高（不允许"凸出一截"）
const sankey = written.sankey || '';
const bars = [...sankey.matchAll(/<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/g)]
  .map(m => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));
const ribbons = [...sankey.matchAll(/<path d="([^"]+)" fill="#[0-9a-f]{6}" fill-opacity="[\d.]+"/g)].map(m => {
  const n = m[1].match(/-?[\d.]+/g).map(Number);   // M x1,y1 C .. ,y2 x2,y2 L x2,y2+h2 C .. ,y1+h1 x1,y1+h1
  return { x1: n[0], y1: n[1], x2: n[6], y2: n[5], h1: n[13] - n[1], h2: n[9] - n[5] };
});
const EPS = 0.6;
const srcBars = x => bars.filter(b => Math.abs(b.x + b.w - x) < 0.01);
const dstBars = x => bars.filter(b => Math.abs(b.x - x) < 0.01);
let geomBad = 0, geomDetail = [];
ribbons.forEach((rb, i) => {
  const src = srcBars(rb.x1), dst = dstBars(rb.x2);
  if (!src.length) { geomBad++; geomDetail.push(`连线${i} 起点 x=${rb.x1} 无对应柱子`); return; }
  if (!dst.length) { geomBad++; geomDetail.push(`连线${i} 终点 x=${rb.x2} 无对应柱子`); return; }
  const inRange = (list, a, b) => list.some(n => a >= n.y - EPS && b <= n.y + n.h + EPS);
  if (!inRange(src, rb.y1, rb.y1 + rb.h1)) { geomBad++; geomDetail.push(`连线${i} 源端 [${rb.y1.toFixed(1)},${(rb.y1 + rb.h1).toFixed(1)}] 超出柱子 [${src[0].y.toFixed(1)},${(src[0].y + src[0].h).toFixed(1)}]`); }
  if (!inRange(dst, rb.y2, rb.y2 + rb.h2)) { geomBad++; geomDetail.push(`连线${i} 目标端 [${rb.y2.toFixed(1)},${(rb.y2 + rb.h2).toFixed(1)}] 超出柱子 [${dst[0].y.toFixed(1)},${(dst[0].y + dst[0].h).toFixed(1)}]`); }
});
let tileBad = 0, tileDetail = [];
bars.forEach((b, bi) => {
  if (b.h <= 2.5) return;                                  // 极小/零金额柱子不参与铺满校验
  const outR = ribbons.filter(r => Math.abs(r.x1 - (b.x + b.w)) < 0.01
    && r.y1 >= b.y - EPS && r.y1 + r.h1 <= b.y + b.h + EPS && r.h1 > 0);
  const inR = ribbons.filter(r => Math.abs(r.x2 - b.x) < 0.01
    && r.y2 >= b.y - EPS && r.y2 + r.h2 <= b.y + b.h + EPS && r.h2 > 0);
  const out = outR.reduce((a, r) => a + r.h1, 0);
  const inn = inR.reduce((a, r) => a + r.h2, 0);
  if (outR.length && Math.abs(out - b.h) > EPS) { tileBad++; tileDetail.push(`柱子${bi} 流出合计 ${out.toFixed(1)} ≠ 柱高 ${b.h.toFixed(1)}`); }
  if (inR.length && Math.abs(inn - b.h) > EPS) { tileBad++; tileDetail.push(`柱子${bi} 流入合计 ${inn.toFixed(1)} ≠ 柱高 ${b.h.toFixed(1)}（凸出一截）`); }
});
console.log('\n桑基图几何校验:');
console.log('  柱子数:', bars.length, ' 连线数:', ribbons.length);
console.log('  越界连线:', geomBad, ' 柱子未被连线铺满:', tileBad);
if (geomBad || tileBad) {
  geomDetail.slice(0, 6).forEach(d => console.error('  - ' + d));
  tileDetail.slice(0, 6).forEach(d => console.error('  - ' + d));
  problems.push('桑基图几何错位');
} else {
  console.log('  ✅ 连线两端均落在各自柱子内，且每根柱子的流入/流出段高度之和恰好等于柱高');
}

console.log('\n关键文本抽样:');console.log('  成本标题:', (written.bdCost || '').slice(0, 40));
console.log('  AS OF  :', written.asof);
console.log('  曲线说明:', (written.curveNote || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').slice(0, 170));
console.log('  区域看点:', (written.regionNote || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').slice(0, 150));
console.log('  每100元:', (written.per100 || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 240));

if (problems.length) {
  console.error('\n❌ 发现问题:');
  problems.forEach(p => console.error('  - ' + p));
  process.exit(1);
}
console.log('\n✅ 页面脚本执行通过，所有区块均成功渲染');
