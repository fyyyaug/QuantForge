// Presentation helpers only. Financial calculations remain on the server.
export const escapeHtml = (value) =>
  String(value ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );
export function number(value, digits = 2) {
  if (value === null || value === undefined || value === '') return 'N/A';
  const n = Number(value);
  return Number.isFinite(n)
    ? n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    : 'N/A';
}
export function percent(value) {
  if (value === null || value === undefined || value === '') return 'N/A';
  const n = Number(value);
  return Number.isFinite(n) ? `${number(n * 100)}%` : 'N/A';
}
export function chartGeometry(series, width = 800, height = 250) {
  const values = series.map((p) => Number(p.nav));
  if (!values.length || values.some((n) => !Number.isFinite(n))) return null;
  const lo = Math.min(...values),
    hi = Math.max(...values);
  const pad = Math.max((hi - lo) * 0.15, hi * 0.005, 1);
  const min = lo - pad,
    max = hi + pad;
  const points = values.map((v, i) => [
    50 + (i / Math.max(1, values.length - 1)) * (width - 70),
    20 + ((max - v) / (max - min)) * (height - 60),
  ]);
  return {
    points: points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' '),
    ticks: [max, (max + min) / 2, min],
    baseline: 20 + ((max - values[0]) / (max - min)) * (height - 60),
    first: series.find((p) => p.session)?.session ?? 'Initial NAV',
    last: series.at(-1)?.session ?? 'Initial NAV',
  };
}
export function validateFields(values) {
  const bounds = {
    lookback_sessions: [1, 252],
    threshold_pct: [-100, 10000],
    initial_nav: [0.000000000001, 1e12],
    allocation_fraction: [0.000000000001, 1],
    fee_bps_each_side: [0, 1000],
    slippage_bps_each_side: [0, 1000],
  };
  for (const [field, [min, max]] of Object.entries(bounds)) {
    if (typeof values[field] !== 'string' || !values[field].trim())
      return 'Complete every strategy parameter.';
    const n = Number(values[field]);
    if (!Number.isFinite(n) || n < min || n > max || (field === 'lookback_sessions' && !Number.isInteger(n)))
      return `Check ${field.replaceAll('_', ' ')}: expected ${min} to ${max}.`;
  }
  if (!values.sample_start || !values.sample_end || values.sample_end < values.sample_start)
    return 'The end date must be on or after the start date.';
  return null;
}
export function humanStatus(status) {
  return (
    {
      ADMISSIBLE_WITHIN_CHECKED_SCOPE: 'Within checked scope',
      BLOCKED: 'Blocked',
      UNVERIFIED: 'Unverified',
      PASS: 'Passed',
      WARN: 'Warning',
      FAIL: 'Failed',
      NOT_APPLICABLE: 'Not applicable',
      METHODOLOGY_CORRECTION: 'Methodology correction',
      CONTROLLED_ASSUMPTION_CHANGE: 'Controlled assumption change',
      IDENTICAL_CONFIGURATION: 'Identical configuration',
      NOT_DIRECTLY_COMPARABLE: 'Not directly comparable',
    }[status] ?? status
  );
}

export function utcTimestamp(value) {
  if (!value) return 'N/A';
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? date.toISOString().replace('T', ' ').replace('.000Z', ' UTC')
    : 'N/A';
}

export function timingEvidence(evidence) {
  return evidence.filter((item) =>
    ['available_at', 'decision_at', 'entry_at'].every((key) => utcTimestamp(item[key]) !== 'N/A'),
  );
}

export function suggestedCosts(spec) {
  const fee = Number(spec.fee_bps_each_side),
    slip = Number(spec.slippage_bps_each_side);
  const format = (value) => value.toFixed(6).replace(/\.?0+$/, '') || '0';
  return fee + slip === 0
    ? { correction_fee: '5', correction_slippage: '5' }
    : {
        correction_fee: format(fee < 1000 ? Math.min(1000, fee + 5) : fee - 5),
        correction_slippage: format(slip),
      };
}

export function costChangeIssue(spec, values) {
  for (const key of ['correction_fee', 'correction_slippage']) {
    const value = values[key];
    if (!/^\d+(\.\d{1,6})?$/.test(value ?? '') || Number(value) > 1000)
      return 'Enter costs from 0 to 1000 bps with at most six decimal places.';
  }
  const fee = Number(values.correction_fee),
    slip = Number(values.correction_slippage);
  if (fee + slip === 0) return 'Use at least one nonzero cost for this sensitivity experiment.';
  if (fee === Number(spec.fee_bps_each_side) && slip === Number(spec.slippage_bps_each_side))
    return 'Change commission or slippage before reviewing a new experiment.';
  return null;
}
