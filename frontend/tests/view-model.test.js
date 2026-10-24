import test from 'node:test';
import assert from 'node:assert/strict';
import {
  escapeHtml,
  number,
  percent,
  chartGeometry,
  validateFields,
  humanStatus,
} from '../assets/view-model.js';

test('escape all HTML metacharacters and hostile strings', () => {
  assert.equal(
    escapeHtml('<img src=x onerror="alert(1)">'),
    '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;',
  );
  assert.equal(escapeHtml("&'"), '&amp;&#39;');
  assert.equal(escapeHtml(null), '');
});
test('unavailable metrics are not turned into zero', () => {
  for (const value of [null, undefined, '', 'NaN', Infinity]) {
    assert.equal(number(value), 'N/A');
    assert.equal(percent(value), 'N/A');
  }
  assert.equal(percent('0'), '0.00%');
  assert.equal(number('10057.84'), '10,057.84');
  assert.equal(percent('-0.012'), '-1.20%');
});
test('chart uses actual samples with finite coordinates even when flat', () => {
  for (const values of [[100], [100, 100, 100], [100, 101, 98]]) {
    const g = chartGeometry(values.map((v, i) => ({ nav: String(v), session: i ? '2026-01-05' : null })));
    assert.ok(g);
    assert.ok(!/NaN|Infinity/.test(g.points));
    assert.equal(g.points.split(' ').length, values.length);
  }
  assert.equal(chartGeometry([]), null);
  assert.equal(chartGeometry([{ nav: 'NaN' }]), null);
});
const valid = {
  lookback_sessions: '5',
  threshold_pct: '2',
  initial_nav: '10000',
  allocation_fraction: '1',
  fee_bps_each_side: '5',
  slippage_bps_each_side: '5',
  sample_start: '2026-01-01',
  sample_end: '2026-01-30',
};
test('valid and zero-cost assumptions accepted for server review', () => {
  assert.equal(validateFields(valid), null);
  assert.equal(validateFields({ ...valid, fee_bps_each_side: '0', slippage_bps_each_side: '0' }), null);
});
test('invalid fields and reversed dates rejected before creating plan', () => {
  for (const bad of [
    { lookback_sessions: '0' },
    { lookback_sessions: '1.5' },
    { threshold_pct: 'NaN' },
    { initial_nav: '' },
    { allocation_fraction: '1.01' },
    { fee_bps_each_side: '-1' },
    { sample_end: '2025-01-01' },
  ])
    assert.ok(validateFields({ ...valid, ...bad }));
});
test('audit labels preserve unknown and not-applicable status', () => {
  assert.equal(humanStatus('UNVERIFIED'), 'Unverified');
  assert.equal(humanStatus('NOT_APPLICABLE'), 'Not applicable');
  assert.equal(humanStatus('FAILED'), 'FAILED');
});
