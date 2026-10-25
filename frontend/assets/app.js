import {
  escapeHtml as e,
  number,
  percent,
  chartGeometry,
  validateFields,
  humanStatus as label,
  timingEvidence,
  utcTimestamp,
  suggestedCosts,
  costChangeIssue,
} from './view-model.js';

const root = document.querySelector('#app');
const state = {
  token: '',
  accessMode: null,
  demo: null,
  ready: false,
  planner: null,
  evaluation: null,
  hypothesis: '',
  screen: 'home',
  datasets: [],
  history: [],
  plan: null,
  run: null,
  artifact: null,
  correction: null,
  comparison: null,
  original: null,
  busy: false,
  notice: null,
  form: null,
  diagnostic: false,
  runKey: null,
};
const titles = {
  home: 'Research workspace',
  review: 'Review research plan',
  results: 'Experiment results',
  audit: 'Audit workspace',
  compare: 'Compare experiments',
  history: 'Experiment history',
  evaluation: 'Audit evaluation',
};
const short = (value) => (value ? `${value.slice(0, 8)}…` : '—');
const connected = () => Boolean(state.token || state.accessMode === 'demo');
const badge = (status) =>
  `<span class="badge ${['FAIL', 'BLOCKED', 'FAILED'].includes(status) ? 'danger' : ['WARN', 'UNVERIFIED', 'DIAGNOSTIC_INVALID'].includes(status) ? 'warning' : 'neutral'}">${e(label(status))}</span>`;
const button = (action, text, cls = 'secondary', extra = '') =>
  `<button type="button" class="${cls}" data-action="${action}" ${state.busy ? 'disabled' : ''} ${extra}>${text}</button>`;
function defaults() {
  const dataset =
    state.datasets.find((d) => d.dataset_id === (state.form?.dataset_id ?? 'clean_momentum')) ??
    state.datasets[0];
  return {
    dataset_id: dataset?.dataset_id,
    sample_start: dataset?.start_session,
    sample_end: dataset?.end_session,
    lookback_sessions: '5',
    threshold_pct: '2',
    initial_nav: '10000',
    allocation_fraction: '1',
    fee_bps_each_side: '5',
    slippage_bps_each_side: '5',
    ...state.form,
  };
}
function nav() {
  return `<aside><a href="#home" class="brand"><img src="/assets/icon.svg" alt="" width="36" height="36"><span>QuantForge<small>RESEARCH LAB</small></span></a>
    <div class="nav-caption">WORKSPACE</div><nav aria-label="Workspace navigation">
    <a href="#home" ${state.screen === 'home' ? 'aria-current="page"' : ''}><span>◈</span> New research</a>
    <a href="#history" ${state.screen === 'history' ? 'aria-current="page"' : ''}><span>↺</span> Experiments <small>${state.history.length || ''}</small></a></nav>
    <div class="sidebar-note"><span class="dot"></span> ${state.accessMode === 'demo' ? 'Isolated demo session' : 'Research environment'}<p>Inspect the evidence.<br>Keep every experiment.</p></div>
    <div class="side-bottom">Built for careful questions.<br><b>Research only · No live trading</b></div></aside>`;
}
function render() {
  const content = !connected()
    ? connectView()
    : state.screen === 'home'
      ? homeView()
      : state.screen === 'review'
        ? reviewView()
        : state.screen === 'history'
          ? historyView()
          : state.screen === 'compare'
            ? compareView()
            : state.screen === 'audit'
              ? auditView()
              : state.screen === 'evaluation'
                ? evaluationView()
                : resultsView();
  root.innerHTML = `${nav()}<div class="workspace"><header><span class="breadcrumb">Workspace <span>/</span> ${e(titles[state.screen])}</span><div class="header-right"><span class="local-pill">${state.accessMode === 'demo' ? 'Isolated demo' : connected() ? 'Workspace connected' : 'Research access'}</span>${connected() ? button('disconnect', state.accessMode === 'demo' ? 'End demo' : 'Disconnect', 'quiet') : ''}</div></header>
    <main id="main" tabindex="-1" aria-busy="${state.busy}">${state.notice ? `<div class="notice" role="alert"><strong>${e(state.notice.title)}</strong><span>${e(state.notice.message)}</span>${button('dismiss', 'Dismiss', 'quiet')}</div>` : ''}
    ${state.accessMode === 'demo' ? `<div class="demo-session-note">Private to this browser session · Up to ${e(state.demo.limits.max_runs)} runs · Expires ${e(utcTimestamp(new Date(state.demo.expires_at * 1000).toISOString()))}. Download reports you want to keep.</div>` : ''}${state.busy ? '<div class="working" role="status"><span class="spinner"></span> Working with the research engine. Please keep this page open.</div>' : ''}${content}
    <footer><span>QuantForge / Evidence before conclusions</span><span>Synthetic data · Simplified execution · No investment advice</span></footer></main></div>${state.correction ? correctionView() : ''}`;
  document.title = `QuantForge / ${titles[state.screen]}`;
}
function connectView() {
  return `<div class="eyebrow">THE RESEARCH WORKSPACE</div><section class="intro"><h1>A backtest is a claim.<br><span>Ask for the evidence.</span></h1><p>Plan an experiment, trace its assumptions, and challenge the result.<br>Every correction leaves a trail you can inspect.</p></section>
    <div class="connect-grid"><section class="panel connect-panel">${state.demo?.enabled ? `<div class="section-number">01 / TRY IT</div><h2>Challenge a backtest.</h2><p>Open an isolated workspace with fictional prices and real calculations. No account or API key needed.</p>${button('start-demo', 'Try the live demo <span>↗</span>', 'primary')}${state.demo.session_active ? `<p>An existing demo session is still active. If its allowance is exhausted, end it before starting another. Ending it removes browser access to its experiments.</p>${button('end-demo', 'End existing demo session')}` : ''}<p class="fine">${e(state.demo.limits.session_minutes)} minutes · ${e(state.demo.limits.max_runs)} runs · Synthetic data only. Saved demo experiments expire with the session.</p><details><summary>Connect a private workspace instead</summary>` : '<div class="section-number">01 / CONNECT</div><h2>Open your private workspace</h2><p>Use the private workspace token configured when starting this backend.</p>'}
    <form id="connect-form"><label for="token">Workspace token</label><input id="token" name="token" type="password" autocomplete="off" spellcheck="false" required minlength="32" placeholder="Enter your private access token"><button class="primary" type="submit" ${state.busy || !state.ready ? 'disabled' : ''}>Connect workspace <span>↗</span></button></form><p class="fine">Private tokens stay in this tab's memory. Reloading a private workspace requires reconnecting.</p>${state.demo?.enabled ? '</details>' : ''}</section>
    <section class="connect-story"><div class="section-number">THE RESEARCH LOOP</div>${[
      ['01', 'Make the assumptions explicit', 'Review signal timing, allocation, and trading costs.'],
      ['02', 'Challenge the methodology', 'Inspect deterministic checks and their source evidence.'],
      ['03', 'Correct. Recompute. Compare.', 'Keep both runs. See exactly what changed.'],
    ]
      .map(
        ([n, t, p]) => `<div class="story-step"><span>${n}</span><div><h3>${t}</h3><p>${p}</p></div></div>`,
      )
      .join('')}</section></div>`;
}
function homeView() {
  const f = defaults();
  const dataset = state.datasets.find((d) => d.dataset_id === f.dataset_id);
  return `<div class="page-heading"><div><div class="eyebrow">RESEARCH / NEW EXPERIMENT</div><h1>Start with a hypothesis.</h1><p>Simple rules. Explicit assumptions. Reproducible evidence.</p></div><span class="tag">TEMPLATE PLANNING</span></div>
    ${plannerView()}<div class="home-grid"><section class="panel"><div class="panel-top"><h2>Trailing momentum</h2><span class="tag">LONG ONLY · DAILY</span></div><p class="hypothesis">When the trailing return exceeds your threshold, enter at the next session's open and exit at its close.</p>
    <form id="plan-form"><div class="field wide"><label for="dataset">Research dataset</label><select id="dataset" name="dataset_id">${state.datasets.map((d) => `<option value="${e(d.dataset_id)}" ${d.dataset_id === f.dataset_id ? 'selected' : ''}>${e(d.dataset_id.replaceAll('_', ' '))}${d.dataset_id === 'clean_momentum' ? ' · recommended' : d.dataset_id === 'leaky_next_close' ? ' · original control' : d.dataset_id === 'timing_trap' ? ' · timing control' : ' · integrity test'}</option>`).join('')}</select><small>All fixtures are synthetic. Malformed fixtures demonstrate data validation.</small></div>
    <div class="fields">${field('lookback_sessions', 'Lookback sessions', f.lookback_sessions, 'number', 'min="1" max="252" step="1"')}${field('threshold_pct', 'Return threshold (%)', f.threshold_pct, 'number', 'min="-100" max="10000" step="any"')}${field('sample_start', 'Sample start', f.sample_start, 'date')}${field('sample_end', 'Sample end', f.sample_end, 'date')}${field('initial_nav', 'Starting capital (USD)', f.initial_nav, 'number', 'min="0.000000000001" max="1000000000000" step="any"')}${field('allocation_fraction', 'Allocation fraction', f.allocation_fraction, 'number', 'min="0.000000000001" max="1" step="any"')}${field('fee_bps_each_side', 'Commission (bps / side)', f.fee_bps_each_side, 'number', 'min="0" max="1000" step="any"')}${field('slippage_bps_each_side', 'Slippage (bps / side)', f.slippage_bps_each_side, 'number', 'min="0" max="1000" step="any"')}</div>
    <div class="form-bottom"><span>Review the exact plan before any execution.</span><button type="submit" class="primary" ${state.busy ? 'disabled' : ''}>Review plan <span>→</span></button></div></form></section>
    <div class="right-stack"><section class="panel dataset-card"><div class="section-number">DATA TRANSPARENCY</div><h3>Fictional prices.<br>Real calculations.</h3><dl><dt>Symbol</dt><dd>${e(dataset?.symbol)}</dd><dt>Source</dt><dd>QuantForge synthetic fixture</dd><dt>Calendar</dt><dd>Explicit synthetic sessions · UTC</dd><dt>Coverage</dt><dd>${e(dataset?.start_session)} — ${e(dataset?.end_session)}</dd><dt>Data license</dt><dd>${e(dataset?.license)}</dd></dl><span class="tag">SYNTHETIC · NOT MARKET HISTORY</span></section>
    <section class="demo-card"><div class="section-number">GUIDED DIAGNOSTIC</div><h3>Can you spot<br>tomorrow's information?</h3><p>Run an intentionally flawed experiment, inspect the timing evidence, then approve a correction.</p>${button('diagnostic-review', 'Review diagnostic example <span>↗</span>', 'light')}</section></div></div>
    <section class="panel evaluation-summary"><div><h2>Check the auditor, too.</h2><p>${e(state.evaluation?.summary.passed ?? '—')} of ${e(state.evaluation?.summary.total ?? '—')} synthetic controls match their expected outcomes. These controls cover three rules, not market profitability.</p></div>${button('evaluation', 'Inspect audit evaluation →')}</section><section class="recent-section"><div class="section-heading"><h2>Recent experiments</h2><a href="#history">View all →</a></div>${historyTable(state.history.slice(0, 4))}</section>`;
}
function plannerView() {
  if (!state.planner?.available)
    return `<details class="panel planner-card"><summary>Optional natural-language planning · not configured</summary><p>${e(state.planner?.message ?? 'Use the editable template below.')}</p><button type="button" class="secondary" disabled>Draft a plan for review →</button></details>`;
  return `<section class="panel planner-card"><div class="panel-top"><h2>Start from your own hypothesis.</h2><span class="tag">${state.planner?.available ? 'OPTIONAL AI PLANNING' : 'AI NOT CONFIGURED'}</span></div><p>${e(state.planner?.message ?? 'Use the editable template below.')}</p><form id="hypothesis-form"><label for="hypothesis">Daily trailing-momentum hypothesis</label><textarea id="hypothesis" name="hypothesis" rows="2" minlength="10" maxlength="1200" required ${state.planner?.available ? '' : 'disabled'} placeholder="If the trailing five-session return exceeds 2%, enter at the next session open and exit at its close.">${e(state.hypothesis)}</textarea><label for="hypothesis-dataset">Dataset</label><select id="hypothesis-dataset" name="dataset_id">${state.datasets.map((d) => `<option value="${e(d.dataset_id)}">${e(d.dataset_id.replaceAll('_', ' '))} · synthetic</option>`).join('')}</select><label class="check"><input type="checkbox" required ${state.planner?.available ? '' : 'disabled'}><span>I agree to send this hypothesis to Anthropic. I will not include secrets or personal information.</span></label><button class="secondary" type="submit" ${state.busy || !state.planner?.available ? 'disabled' : ''}>Draft a plan for review →</button><p class="fine">A draft cannot approve itself. Unsupported strategies require clarification or stay outside the supported scope. Template planning below needs no model.</p></form></section>`;
}

function evaluationView() {
  const evaluation = state.evaluation;
  if (!evaluation) return '<h1>No evaluation loaded</h1>';
  return `<div class="page-heading"><div><div class="eyebrow">EVALUATION / SYNTHETIC CONTROLS</div><h1>Evidence for the auditor.</h1><p>${e(evaluation.scope)}</p></div></div><section class="panel"><h2>${e(evaluation.summary.passed)} / ${e(evaluation.summary.total)} expected outcomes matched</h2><p>${e(evaluation.limitations)}</p><div class="table-wrap"><table><thead><tr><th>Control</th><th>Rule</th><th>Expected</th><th>Observed</th><th>Result</th></tr></thead><tbody>${evaluation.cases.map((c) => `<tr><td>${e(c.case_id)}</td><td>${e(c.check_id)}</td><td>${e(c.expected)}</td><td>${e(c.actual)}</td><td>${c.passed ? 'Matched' : 'Mismatch'}</td></tr>`).join('')}</tbody></table></div><details><summary>Generation, rule versions and detection counts</summary><pre>${e(JSON.stringify({ generation: evaluation.generation, detection: evaluation.detection, versions: evaluation.versions }, null, 2))}</pre></details><div class="actions">${button('download-evaluation', 'Download evaluation JSON')}${button('home', 'Back to research')}</div></section>`;
}
function field(name, title, value, type, attrs = '') {
  return `<div class="field"><label for="${name}">${title}</label><input id="${name}" name="${name}" type="${type}" value="${e(value)}" required ${attrs}></div>`;
}
function steps(active) {
  return `<nav class="steps" aria-label="Research progress">${[
    ['review', 'Plan'],
    ['results', 'Results'],
    ['audit', 'Audit'],
    ['compare', 'Compare'],
  ]
    .map(
      ([s, t], i) =>
        `<button type="button" data-action="${s === 'review' ? 'review' : s}" ${state.busy || (s === 'compare' ? !state.comparison : s === 'review' ? !(state.plan || state.diagnostic) : !state.run) ? 'disabled' : ''} ${active === s ? 'aria-current="step"' : ''}><span>0${i + 1}</span> ${t}</button>`,
    )
    .join('')}</nav>`;
}
function reviewView() {
  const spec = state.plan?.spec;
  if (!state.diagnostic && !spec) return '<h1>No plan to review</h1><a href="#home">Create an experiment</a>';
  return `${steps('review')}${state.plan?.planning_mode === 'CLAUDE_STRUCTURED' ? `<div class="info-box">AI-proposed draft. Review every parameter. Template defaults were used for: ${e(state.plan.planning.defaulted_fields.join(', ').replaceAll('_', ' ')) || 'none'}.</div>` : ''}<div class="page-heading"><div><div class="eyebrow">01 / REVIEW</div><h1>${state.diagnostic ? 'An intentional timing mistake.' : 'Make the assumptions explicit.'}</h1><p>${state.diagnostic ? 'This demonstration uses future information. Its results will remain invalid.' : 'Check the exact specification before approving an experiment.'}</p></div>${badge(state.diagnostic ? 'DIAGNOSTIC_INVALID' : 'UNVERIFIED')}</div>
    ${
      state.diagnostic
        ? `<section class="panel"><h2>Diagnostic: future close before an open fill</h2><div class="warning-box">Synthetic, intentionally flawed. The signal reads close(t+1) even though entry happens at open(t+1). This is not an admissible research strategy.</div><p>The timing trap deliberately alternates price moves around the signal threshold. Inspect how tomorrow's information changes the selected trades, then approve a separate corrected experiment. Every metric is calculated by the engine.</p></section>`
        : `<section class="panel"><div class="panel-top"><h2>Approved scope, transparent defaults</h2><span class="mono">Revision ${state.plan.revision}</span></div><p class="hypothesis">If the ${e(spec.lookback_sessions)}-session trailing return is strictly greater than ${e(spec.threshold_pct)}%, allocate ${percent(spec.allocation_fraction)} of NAV at the next session's open, then exit at its close.</p><div class="timeline"><div><b>01</b><h3>Observe</h3><p>Session t closes at 16:00 UTC.<br>Only available history is used.</p></div><div><b>02</b><h3>Decide</h3><p>Decision at 16:00:01.<br>Order submitted at 16:00:02.</p></div><div><b>03</b><h3>Simulate</h3><p>Next explicit session:<br>09:30 entry → 16:00 exit.</p></div></div>
    <dl class="spec-grid"><div><dt>Dataset</dt><dd>${e(spec.dataset_id)} · SYNTHETIC</dd></div><div><dt>Sample</dt><dd>${e(spec.sample_start)} — ${e(spec.sample_end)}</dd></div><div><dt>Starting NAV</dt><dd>$${number(spec.initial_nav)}</dd></div><div><dt>Costs per side</dt><dd>${e(spec.fee_bps_each_side)} bps commission + ${e(spec.slippage_bps_each_side)} bps slippage</dd></div><div><dt>Specification hash</dt><dd class="mono wrap">${e(state.plan.spec_hash)}</dd></div></dl><details><summary>Inspect full strategy specification</summary><pre>${e(JSON.stringify(spec, null, 2))}</pre></details></section>`
    }
    <form id="approve-form" class="approval panel"><label class="check"><input type="checkbox" name="approve" required> <span>I reviewed these assumptions and understand that this is a synthetic research simulation.</span></label><div class="actions">${button('edit', 'Back to parameters')}<button class="primary" type="submit" ${state.busy ? 'disabled' : ''}>${state.diagnostic ? 'Run invalid diagnostic' : 'Approve & run experiment'} <span>→</span></button></div></form>`;
}
function runHeading(eyebrow, title) {
  return `${steps(state.screen)}<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="mono">Run ${e(state.run?.run_id ?? 'unavailable')}</p></div>${state.artifact ? badge(state.artifact.admissibility) : badge(state.run?.state ?? 'UNVERIFIED')}</div>${state.artifact?.mode === 'DIAGNOSTIC_INVALID' ? '<div class="warning-box"><strong>Intentionally flawed diagnostic · Synthetic data</strong><br>This result used future information and is invalid. Keep this warning when interpreting or exporting it.</div>' : ''}`;
}
function noResult() {
  return `<section class="panel empty"><h2>${state.run?.state === 'FAILED' ? 'Experiment could not complete' : state.run?.state === 'COMPLETED' ? 'Simulation blocked by validation' : 'No completed result yet'}</h2><p>${state.run?.error ? e(state.run.error) : 'Inspect the audit for evidence. No prices, fills, or metrics have been fabricated.'}</p><div class="actions">${button('reload', 'Refresh experiment')}${state.artifact ? button('audit', 'Inspect audit evidence', 'primary') : ''}</div></section>`;
}
function metrics(result) {
  const m = result.metrics;
  return `<div class="metrics">${[
    ['Ending NAV', `$${number(m.ending_nav)}`, 'USD · modeled'],
    ['Total return', percent(m.total_return), 'Over selected sample'],
    ['Max drawdown', percent(m.max_drawdown), 'Includes starting NAV'],
    ['Trades', number(m.trade_count, 0), `${number(m.observation_count, 0)} sample sessions`],
  ]
    .map(([t, v, n]) => `<div><span>${t}</span><strong>${v}</strong><small>${n}</small></div>`)
    .join('')}</div>`;
}
function chart(result, title = 'Portfolio NAV') {
  const g = chartGeometry(result.nav_series);
  if (!g) return '<p>Chart unavailable. Inspect the numerical artifact.</p>';
  return `<div class="chart"><div class="panel-top"><h2>${e(title)}</h2><span class="tag">SYNTHETIC · USD</span></div><svg viewBox="0 0 800 250" role="img" aria-label="${e(title)}: initial NAV ${e(result.nav_series[0].nav)}, ending NAV ${e(result.metrics.ending_nav)}"><title>${e(title)} from saved engine output</title>${g.ticks.map((v, i) => `<line x1="50" x2="780" y1="${20 + i * 95}" y2="${20 + i * 95}" class="gridline"/><text x="42" y="${24 + i * 95}" text-anchor="end">${number(v, 0)}</text>`).join('')}<line x1="50" x2="780" y1="${g.baseline}" y2="${g.baseline}" class="baseline"/><polyline points="${g.points}" class="nav-line"/><text x="50" y="242">${e(g.first)}</text><text x="780" y="242" text-anchor="end">${e(g.last)}</text></svg><p class="fine">Computed from the saved NAV series. Rounded for display only. Flat sessions are included.</p></div>`;
}
function resultsView() {
  const a = state.artifact,
    r = a?.result;
  return `${runHeading('02 / RESULT', 'Read the result. Check the evidence.')}${
    r
      ? `${metrics(r)}<section class="panel">${chart(r)}<div class="chart-bottom"><span>${e(a.spec.dataset_id)} · ${percent(r.metrics.exposure_fraction)} session exposure</span>${button('audit', 'Inspect the audit <span>→</span>', 'primary')}</div></section>
    <div class="section-heading"><h2>Trade ledger</h2><span>All ${r.trades.length} simulated trades</span></div>${tradeTable(r.trades)}<details class="panel"><summary>Skipped sessions and modeling assumptions</summary><ul>${r.assumptions.map((x) => `<li>${e(x)}</li>`).join('')}</ul><pre>${e(JSON.stringify(r.skips, null, 2))}</pre></details>`
      : noResult()
  }
    ${a ? `<section class="panel report-actions"><div><h3>Keep the research trail</h3><p>Download the saved report or complete scientific artifact.</p></div><div class="actions">${button('download-report', 'Download report')}${button('download-artifact', 'Download JSON')}</div></section>` : ''}`;
}
function tradeTable(trades) {
  return `<div class="table-wrap"><table><caption class="sr-only">Saved trade ledger</caption><thead><tr><th>Session</th><th>Entry</th><th>Exit</th><th>Gross return</th><th>Net return</th><th>Modeled costs</th></tr></thead><tbody>${trades.length ? trades.map((t) => `<tr><td class="mono">${e(t.entry_at.slice(0, 10))}</td><td>$${number(t.entry_price)}</td><td>$${number(t.exit_price)}</td><td>${percent(t.gross_return)}</td><td>${percent(t.net_return)}</td><td>$${number(Number(t.fee_amount) + Number(t.slippage_amount))}</td></tr>`).join('') : '<tr><td colspan="6">No trades. This is a computed outcome, not missing data.</td></tr>'}</tbody></table></div>`;
}
function auditView() {
  const a = state.artifact;
  if (!a) return `${runHeading('03 / AUDIT', 'Inspect the methodology.')}${noResult()}`;
  const names = {
    A01_LOOKAHEAD: 'Information timing',
    A02_MISSING_COSTS: 'Trading costs',
    A03_DATA_INTEGRITY: 'Dataset integrity',
    A04_SPLIT_LEAKAGE: 'Split leakage',
    A05_OVERFITTING_RISK: 'Overfitting risk',
    A06_SURVIVORSHIP: 'Survivorship coverage',
  };
  return `${runHeading('03 / AUDIT', 'Evidence before conclusions.')}<p class="section-intro">A passed check covers a specific rule. Unverified checks remain unknown. There is no overall confidence score.</p>${timingTimeline(a.findings)}<div class="audit-list">${a.findings
    .map(
      (
        f,
      ) => `<section class="panel audit-card"><div class="audit-icon ${f.status === 'FAIL' ? 'fail' : f.status === 'PASS' ? 'pass' : 'unknown'}">${f.status === 'PASS' ? '✓' : f.status === 'FAIL' ? '!' : '·'}</div><div class="audit-body"><div class="panel-top"><div><div class="section-number">${e(f.check_id)} / RULE ${e(f.rule_version)}</div><h2>${e(names[f.check_id] ?? f.check_id)}</h2></div>${badge(f.status)}</div><p>${e(f.explanation)}</p><div class="fine">Severity: ${e(f.severity)} · Execution effect: ${e(f.execution_effect)}</div>${f.evidence.length ? `<details ${f.status === 'FAIL' ? 'open' : ''}><summary>Inspect ${f.evidence.length} evidence record${f.evidence.length === 1 ? '' : 's'}</summary><pre>${e(JSON.stringify(f.evidence, null, 2))}</pre></details>` : ''}
    ${f.check_id === 'A01_LOOKAHEAD' && a.mode === 'DIAGNOSTIC_INVALID' ? `<div class="fix-note"><h3>Proposed direction</h3><p>Remove the future-close dependency and recalculate with information available at session t. This changes the signal's economic meaning.</p>${button('propose-timing', 'Review timing correction <span>→</span>', 'primary')}</div>` : ''}
    ${f.check_id === 'A02_MISSING_COSTS' && a.mode === 'RESEARCH' && a.result?.trades.length ? costForm(a) : ''}</div></section>`,
    )
    .join('')}</div>`;
}
function costForm(artifact) {
  const proposal = suggestedCosts(artifact.spec);
  return `<form id="cost-form" class="cost-form"><h3>Cost sensitivity experiment</h3><div class="fields">${field('correction_fee', 'Commission (bps / side)', proposal.correction_fee, 'number', 'min="0" max="1000" step="0.000001"')}${field('correction_slippage', 'Slippage (bps / side)', proposal.correction_slippage, 'number', 'min="0" max="1000" step="0.000001"')}</div><p id="cost-change-status" role="status">${e(costDescription(artifact.spec, proposal))}</p><button type="submit" class="secondary" ${state.busy ? 'disabled' : ''}>Review cost change →</button></form>`;
}
function costDescription(spec, values) {
  return `Commission: ${spec.fee_bps_each_side} → ${values.correction_fee} bps per side. Slippage: ${spec.slippage_bps_each_side} → ${values.correction_slippage} bps per side. A separate run will be computed.`;
}
function timingTimeline(findings) {
  const finding = findings.find((f) => f.check_id === 'A01_LOOKAHEAD' && f.status === 'FAIL');
  const evidence = timingEvidence(finding?.evidence ?? []);
  if (!evidence.length) return '';
  const first = evidence[0];
  return `<section class="panel timing-evidence"><div class="section-number">WHY THIS RESULT IS BLOCKED</div><h2>The order came before the information.</h2><p>Source row ${e(first.row_number)} · ${e(first.field)} · ${e(first.decision_id)}. The input must be available before the decision and the fill.</p><div class="timeline"><div><b>01</b><h3>Decision recorded</h3><p>${e(utcTimestamp(first.decision_at))}</p></div><div><b>02</b><h3>Order entered</h3><p>${e(utcTimestamp(first.entry_at))}</p></div><div class="late-information"><b>!</b><h3>Input became available</h3><p>${e(utcTimestamp(first.available_at))}<br>Too late for this decision.</p></div></div><p class="fine">One of ${e(evidence.length)} recorded timing violations. Full source records appear below.</p></section>`;
}

function decisionChanges(comparison) {
  const changes = comparison.decision_changes;
  if (!changes) return '';
  return `<section class="panel decision-changes"><div class="section-number">WHAT CHANGED IN EXECUTION</div><h2>${e(changes.changed_signals)} entry signals changed.</h2><p>Original: ${e(changes.before_trade_count ?? 'N/A')} trades. New experiment: ${e(changes.after_trade_count ?? 'N/A')} trades. Equal trade counts can still select different sessions.</p>${changes.changes.length ? `<details open><summary>Inspect changed entry decisions</summary><div class="table-wrap"><table><thead><tr><th>Entry session (UTC)</th><th>Original signal</th><th>New signal</th><th>Original action</th><th>New action</th></tr></thead><tbody>${changes.changes.map((d) => `<tr><td>${e(d.entry_at.slice(0, 10))}</td><td>${percent(d.before_feature)}</td><td>${percent(d.after_feature)}</td><td>${d.before_triggered ? 'Enter' : 'Stay flat'}</td><td>${d.after_triggered ? 'Enter' : 'Stay flat'}</td></tr>`).join('')}</tbody></table></div></details>` : '<p class="fine">The selected signals match. Inspect cost, mode, and specification differences before interpreting the results.</p>'}</section>`;
}
function correctionView() {
  const c = state.correction;
  return `<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="correction-title" tabindex="-1"><div class="eyebrow">REVIEW / A NEW EXPERIMENT</div><h2 id="correction-title">Approve the change, not the outcome.</h2><p>${e(c.proposal.rationale)}</p>${badge(c.proposal.classification)}<div class="table-wrap"><table><thead><tr><th>Assumption</th><th>Original</th><th>Proposed</th></tr></thead><tbody>${Object.entries(
    c.proposal.diff,
  )
    .map(([key, d]) => `<tr><td>${e(key)}</td><td>${e(d.before)}</td><td>${e(d.after)}</td></tr>`)
    .join(
      '',
    )}</tbody></table></div><p>The original run stays unchanged. The engine will calculate a separate child run. No performance improvement is promised.</p><form id="correction-approve-form"><label class="check"><input type="checkbox" required><span>I reviewed this diff and approve a separate experiment.</span></label><div class="actions">${button('cancel-correction', 'Cancel')}<button type="submit" class="primary" ${state.busy ? 'disabled' : ''}>Approve & rerun →</button></div></form></section></div>`;
}
function compareView() {
  const c = state.comparison;
  if (!c)
    return `${steps('compare')}<h1>No comparison selected</h1><p>Approve a correction or reopen a child experiment from history.</p>`;
  return `${steps('compare')}<div class="page-heading"><div><div class="eyebrow">04 / COMPARE</div><h1>A change you can trace.</h1><p>Two saved experiments. Original artifacts preserved.</p></div>${badge(c.classification)}</div><div class="info-box">${e(c.classification === 'METHODOLOGY_CORRECTION' ? 'The signal methodology changed. This is not a controlled estimate of performance improvement.' : c.limitations)}</div><div class="compare-grid">${[
    ['Original', c.left_run_id, state.original, c.left],
    ['New experiment', c.right_run_id, state.artifact, c.right],
  ]
    .map(
      ([title, id, a, item]) =>
        `<section class="panel"><div class="panel-top"><h2>${title}</h2>${badge(item.admissibility)}</div><p class="mono">${e(id)}</p><span class="tag">${e(a?.mode)} · SYNTHETIC</span>${a?.result ? `<div class="compare-metrics"><div><small>Total return</small><strong>${percent(item.metrics.total_return)}</strong></div><div><small>Max drawdown</small><strong>${percent(item.metrics.max_drawdown)}</strong></div></div>${chart(a.result, title + ' NAV')}` : '<p>No simulation result available.</p>'}</section>`,
    )
    .join('')}</div>
    ${decisionChanges(c)}<section class="panel"><h2>Recorded differences</h2><pre>${e(JSON.stringify({ specification: c.spec_diff, execution_mode: c.mode_diff }, null, 2))}</pre><p class="fine">Charts use their own labeled NAV scales. No silent rescaling, alignment, or statistical significance is implied. Identical metrics do not establish identical methodology; an invalid information dependency is still invalid.</p><div class="actions">${button('audit-original', 'Audit original experiment')}${button('audit', 'Audit new experiment', 'primary')}${button('download-comparison', 'Download comparison report')}${button('download-report', 'Download new report')}</div></section>`;
}
function historyTable(rows) {
  return `<div class="table-wrap"><table><caption class="sr-only">Recent saved experiments</caption><thead><tr><th>Experiment</th><th>Dataset</th><th>Mode</th><th>State</th><th>Created</th><th><span class="sr-only">Action</span></th></tr></thead><tbody>${rows.length ? rows.map((r) => `<tr><td class="mono">${e(short(r.run_id))}${r.parent_run_id ? '<small class="child-note">↳ correction child</small>' : ''}</td><td>${e(r.dataset_id)}</td><td>${r.execution_mode === 'DIAGNOSTIC_INVALID' ? badge('DIAGNOSTIC_INVALID') : 'Research'}</td><td>${e(r.state)}</td><td>${e(new Date(r.created_at).toLocaleString())}</td><td>${button('open-run', 'Open →', 'quiet', `data-id="${e(r.run_id)}"`)}</td></tr>`).join('') : '<tr><td colspan="6" class="empty-row">Your first experiment starts with a question. Create a plan above.</td></tr>'}</tbody></table></div>`;
}
function historyView() {
  return `<div class="page-heading"><div><div class="eyebrow">RESEARCH / HISTORY</div><h1>Every experiment has a trail.</h1><p>The latest 50 runs in this connected workspace. Completion is separate from audit admissibility.</p></div>${button('refresh-history', 'Refresh history')}</div>${historyTable(state.history)}`;
}
const errorMessages = {
  UNAUTHORIZED: 'The workspace token was rejected. Reconnect with the configured token.',
  INVALID_SPEC:
    'One or more parameters are outside the supported strategy contract. Check values and precision.',
  STALE_APPROVAL: 'The plan or correction changed. Review its current revision before trying again.',
  RUN_NOT_READY: 'The experiment has no completed artifact yet. Refresh its state or inspect history.',
  NOT_FOUND: 'This resource is unavailable in the connected workspace.',
  NO_SUPPORTED_CORRECTION: 'There is no supported correction for this experiment.',
  SESSION_EXPIRED:
    'Your demo session ended. Open a new demo to continue. Download reports before ending a session.',
  ORIGIN_REJECTED: 'Open the research workspace on this same site and try again.',
  STATE_CONFLICT: 'The experiment state no longer permits that action.',
  PLANNER_UNAVAILABLE: 'AI planning is unavailable. No plan was created. Use the editable template below.',
  PLANNER_INVALID_OUTPUT:
    'The AI draft did not meet the supported contract. Use the template or revise your hypothesis.',
  PLANNER_LIMIT_REACHED: 'The AI planning allowance is reached. The editable template is still available.',
};
async function api(path, { method = 'GET', body, key } = {}) {
  const controller = new AbortController(),
    timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(path, {
      method,
      signal: controller.signal,
      cache: 'no-store',
      credentials: 'same-origin',
      headers: {
        ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
        'X-QuantForge-Request': 'workspace',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(key ? { 'Idempotency-Key': key } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const content = response.headers.get('content-type') ?? '';
    const data = content.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const code = data?.error?.code ?? 'REQUEST_FAILED';
      if (response.status === 401 && connected()) resetWorkspace();
      if (code === 'SESSION_EXPIRED' && state.demo) state.demo.session_active = false;
      const fields = data?.error?.fields ?? [];
      const message = ['DEMO_QUOTA_REACHED', 'DEMO_RATE_LIMIT'].includes(code)
        ? `${data?.error?.message ?? 'Demo limit reached.'} ${code === 'DEMO_RATE_LIMIT' ? 'Wait for the limit window to reset, then retry.' : 'You can end the demo using End demo or End existing demo session. Starting another session is subject to service capacity.'}`
        : (errorMessages[code] ?? `${code}: ${data?.error?.message ?? 'Request could not be completed.'}`);
      throw new Error(message + (fields.length ? ` Check: ${fields.join(', ').replaceAll('_', ' ')}.` : ''));
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError')
      throw new Error(
        'The request timed out. It may still have completed. Refresh history before submitting a new experiment; retrying this plan keeps the same run key.',
      );
    if (error instanceof TypeError)
      throw new Error(
        'Cannot reach the local backend. Check that it is running, then retry or refresh history.',
      );
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
async function task(fn) {
  if (state.busy) return;
  const previousScreen = state.screen;
  state.busy = true;
  state.notice = null;
  render();
  try {
    await fn();
  } catch (error) {
    state.notice = { title: 'Action needs attention', message: error.message };
  } finally {
    state.busy = false;
    render();
    if (state.correction) document.querySelector('.modal')?.focus();
    else if (state.screen !== previousScreen) {
      document.querySelector('#main')?.focus();
      window.scrollTo(0, 0);
    }
  }
}
async function history() {
  state.history = await api('/api/runs');
}
function resetWorkspace() {
  Object.assign(state, {
    token: '',
    accessMode: null,
    datasets: [],
    history: [],
    plan: null,
    run: null,
    artifact: null,
    correction: null,
    comparison: null,
    original: null,
    notice: null,
    form: null,
    screen: 'home',
    diagnostic: false,
    runKey: null,
    evaluation: null,
    hypothesis: '',
  });
}
async function connectWorkspace() {
  const [datasets, runs, evaluation] = await Promise.all([
    api('/api/datasets'),
    api('/api/runs'),
    api('/api/evaluation'),
  ]);
  state.datasets = datasets;
  state.history = runs;
  state.evaluation = evaluation;
  state.screen = 'home';
}
async function loadRun(id) {
  const run = await api(`/api/runs/${encodeURIComponent(id)}`);
  const artifact =
    run.state === 'COMPLETED' ? await api(`/api/runs/${encodeURIComponent(id)}/artifact`) : null;
  state.run = run;
  state.artifact = artifact;
  state.comparison = null;
  state.original = null;
  state.plan = null;
  state.diagnostic = false;
  if (run.parent_run_id && artifact) {
    const [comparison, original] = await Promise.all([
      api(
        `/api/runs/${encodeURIComponent(run.parent_run_id)}/comparison?other_run_id=${encodeURIComponent(id)}`,
      ),
      api(`/api/runs/${encodeURIComponent(run.parent_run_id)}/artifact`),
    ]);
    state.comparison = comparison;
    state.original = original;
  }
}
function navigate(screen) {
  if (state.busy) return;
  state.screen = screen;
  state.notice = null;
  render();
  document.querySelector('#main')?.focus();
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', () => {
  const s = location.hash.slice(1);
  if (['home', 'history'].includes(s)) navigate(s);
});
root.addEventListener('change', (event) => {
  if (event.target.id === 'dataset') {
    const values = Object.fromEntries(new FormData(document.querySelector('#plan-form')));
    const dataset = state.datasets.find((d) => d.dataset_id === values.dataset_id);
    state.form = { ...values, sample_start: dataset.start_session, sample_end: dataset.end_session };
    render();
  }
});
root.addEventListener('input', (event) => {
  const form = event.target.closest('#cost-form');
  if (!form || !state.artifact) return;
  const values = Object.fromEntries(new FormData(form));
  const issue = costChangeIssue(state.artifact.spec, values);
  form.querySelector('button[type="submit"]').disabled = state.busy || Boolean(issue);
  form.querySelector('#cost-change-status').textContent =
    issue ?? costDescription(state.artifact.spec, values);
});
root.addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.target;
  if (!form.reportValidity()) return;
  const values = Object.fromEntries(new FormData(form));
  if (form.id === 'hypothesis-form') {
    state.hypothesis = values.hypothesis;
    task(async () => {
      const draft = await api('/api/research/hypotheses', { method: 'POST', body: values });
      if (draft.status !== 'PLAN') {
        state.notice = {
          title: draft.status === 'CLARIFY' ? 'Clarify your hypothesis' : 'Outside the supported scope',
          message: draft.question || draft.message,
        };
        return;
      }
      state.plan = draft.plan;
      state.form = {
        dataset_id: draft.plan.spec.dataset_id,
        ...Object.fromEntries(
          [
            'sample_start',
            'sample_end',
            'lookback_sessions',
            'threshold_pct',
            'initial_nav',
            'allocation_fraction',
            'fee_bps_each_side',
            'slippage_bps_each_side',
          ].map((key) => [key, String(draft.plan.spec[key])]),
        ),
      };
      Object.assign(state, {
        run: null,
        artifact: null,
        comparison: null,
        original: null,
        diagnostic: false,
        runKey: crypto.randomUUID(),
        screen: 'review',
      });
    });
  }
  if (form.id === 'connect-form')
    task(async () => {
      state.token = values.token.trim();
      try {
        state.accessMode = 'private';
        await connectWorkspace();
      } catch (error) {
        state.token = '';
        throw error;
      }
    });
  if (form.id === 'plan-form') {
    state.form = values;
    const issue = validateFields(values);
    if (issue) {
      state.notice = { title: 'Check your plan', message: issue };
      render();
      return;
    }
    task(async () => {
      const { dataset_id, ...overrides } = values;
      overrides.lookback_sessions = Number(overrides.lookback_sessions);
      state.plan = await api('/api/research/plans', { method: 'POST', body: { dataset_id, overrides } });
      Object.assign(state, { run: null, artifact: null, comparison: null, original: null });
      state.runKey = crypto.randomUUID();
      state.diagnostic = false;
      state.screen = 'review';
    });
  }
  if (form.id === 'approve-form')
    task(async () => {
      let run;
      if (state.diagnostic)
        run = await api('/api/demo/diagnostic-runs', { method: 'POST', body: {}, key: state.runKey });
      else {
        const approval = { revision: state.plan.revision, spec_hash: state.plan.spec_hash };
        await api(`/api/research/plans/${state.plan.plan_id}/approve`, { method: 'POST', body: approval });
        run = await api('/api/research/runs', {
          method: 'POST',
          body: { plan_id: state.plan.plan_id, ...approval },
          key: state.runKey,
        });
      }
      await loadRun(run.run_id);
      state.screen = 'results';
      await history();
    });
  if (form.id === 'cost-form' && !costChangeIssue(state.artifact.spec, values))
    task(async () => {
      state.correction = await api(`/api/runs/${state.run.run_id}/corrections`, {
        method: 'POST',
        body: {
          kind: 'costs',
          fee_bps_each_side: values.correction_fee,
          slippage_bps_each_side: values.correction_slippage,
        },
      });
      state.correction.requestKey = crypto.randomUUID();
    });
  if (form.id === 'correction-approve-form')
    task(async () => {
      const c = state.correction;
      const run = await api(`/api/corrections/${c.correction_id}/approve-and-rerun`, {
        method: 'POST',
        body: { proposal_hash: c.proposal_hash },
        key: c.requestKey,
      });
      await loadRun(run.run_id);
      state.correction = null;
      state.screen = state.comparison ? 'compare' : 'results';
      await history();
    });
});
root.addEventListener('click', (event) => {
  const navigation = event.target.closest('a[href="#home"],a[href="#history"]');
  if (navigation) {
    if (state.busy) {
      event.preventDefault();
      return;
    }
    if (location.hash === navigation.hash) {
      event.preventDefault();
      navigate(navigation.hash.slice(1));
    }
  }
  const target = event.target.closest('[data-action]');
  if (!target || state.busy) return;
  const action = target.dataset.action;
  if (action === 'start-demo')
    task(async () => {
      const session = await api('/api/demo/session', { method: 'POST', body: {} });
      state.demo = { ...state.demo, ...session, session_active: true };
      state.accessMode = 'demo';
      try {
        await connectWorkspace();
      } catch (error) {
        resetWorkspace();
        throw error;
      }
    });
  if (['results', 'audit', 'compare', 'review', 'evaluation', 'home'].includes(action)) navigate(action);
  if (action === 'dismiss') {
    state.notice = null;
    render();
  }
  if (action === 'disconnect' || action === 'end-demo') {
    task(async () => {
      if (state.accessMode === 'demo' || action === 'end-demo') {
        await api('/api/demo/session/logout', { method: 'POST', body: {} });
        state.demo.session_active = false;
      }
      resetWorkspace();
    });
  }
  if (action === 'edit') navigate('home');
  if (action === 'diagnostic-review') {
    Object.assign(state, { plan: null, run: null, artifact: null, comparison: null, original: null });
    state.diagnostic = true;
    state.runKey = crypto.randomUUID();
    navigate('review');
  }
  if (action === 'cancel-correction') {
    state.correction = null;
    render();
    document.querySelector('#main')?.focus();
  }
  if (action === 'refresh-history') task(history);
  if (action === 'open-run')
    task(async () => {
      await loadRun(target.dataset.id);
      state.screen = 'results';
    });
  if (action === 'audit-original')
    task(async () => {
      await loadRun(state.comparison.left_run_id);
      state.screen = 'audit';
    });
  if (action === 'reload')
    task(async () => {
      await loadRun(state.run.run_id);
      await history();
    });
  if (action === 'propose-timing')
    task(async () => {
      state.correction = await api(`/api/runs/${state.run.run_id}/corrections`, {
        method: 'POST',
        body: { kind: 'timing' },
      });
      state.correction.requestKey = crypto.randomUUID();
    });
  if (action === 'download-report' || action === 'download-artifact') {
    const json = action === 'download-artifact',
      blob = new Blob([json ? JSON.stringify(state.artifact, null, 2) : state.artifact.report], {
        type: json ? 'application/json' : 'text/markdown',
      });
    const url = URL.createObjectURL(blob),
      link = document.createElement('a');
    link.href = url;
    link.download = `quantforge-${state.run.run_id}.${json ? 'json' : 'md'}`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (action === 'download-comparison')
    task(async () => {
      const c = state.comparison;
      const report = await api(`/api/runs/${c.left_run_id}/comparison/report?other_run_id=${c.right_run_id}`);
      download(report, 'text/markdown', `quantforge-comparison-${c.left_run_id}-${c.right_run_id}.md`);
    });
  if (action === 'download-evaluation')
    download(
      JSON.stringify(state.evaluation, null, 2),
      'application/json',
      'quantforge-audit-evaluation.json',
    );
});
function download(content, type, filename) {
  const url = URL.createObjectURL(new Blob([content], { type })),
    link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.addEventListener('keydown', (event) => {
  if (!state.correction) return;
  if (event.key === 'Escape' && !state.busy) {
    state.correction = null;
    render();
    document.querySelector('#main')?.focus();
  }
  if (event.key === 'Tab') {
    const items = [...document.querySelectorAll('.modal button:not(:disabled),.modal input')];
    const first = items[0],
      last = items.at(-1);
    if (
      event.shiftKey &&
      (document.activeElement === first || document.activeElement.classList.contains('modal'))
    ) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
});
render();
async function initialize() {
  try {
    const config = await api('/api/workspace');
    state.demo = config.demo;
    state.planner = config.planner;
    if (state.demo.session_active) {
      state.accessMode = 'demo';
      await connectWorkspace();
    }
  } catch (error) {
    resetWorkspace();
    state.notice = { title: 'Workspace unavailable', message: error.message };
  } finally {
    state.ready = true;
    render();
  }
}
initialize();
