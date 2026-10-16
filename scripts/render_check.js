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
const need = ['heroStats', 'stack', 'stackLegend', 'per100', 'sankey', 'curve', 'curveLegend',
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
  '总表行数': 16, '参数卡数': 7, '曲线图例项': 5, '堆叠图例项': 7, '全国柱数': 112 };
Object.entries(expect).forEach(([k, v]) => {
  if (stats[k] !== v) problems.push(`${k} 期望 ${v}，实际 ${stats[k]}`);
});
// 热力图 31 行 × 16 列 = 496
if (stats['热力图单元格'] !== 496) problems.push('热力图单元格期望 496，实际 ' + stats['热力图单元格']);

console.log('\n关键文本抽样:');
console.log('  成本标题:', (written.bdCost || '').slice(0, 40));
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
