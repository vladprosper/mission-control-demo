/* Fictional reporting view. All imported text is assigned through textContent. */
'use strict';
const $ = id => document.getElementById(id);
const statuses = ['planned', 'drafted', 'scheduled', 'submitted', 'verified'];
const meanings = ['Intent recorded', 'Material prepared', 'Time assigned', 'Handoff recorded', 'Evidence referenced'];
let data;
function el(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; }
function renderRows() {
  const query = $('search').value.trim().toLowerCase();
  const rows = data.records.filter(r => (!query || `${r.title} ${r.source} ${r.workstream}`.toLowerCase().includes(query)) && (!$('status').value || r.status === $('status').value) && (!$('freshness').value || r.freshness === $('freshness').value) && (!$('source').value || r.source === $('source').value));
  $('rows').replaceChildren();
  for (const r of rows) {
    const tr = el('tr'), name = el('td'), title = el('button', r.title, 'record-title');
    title.type = 'button';
    title.addEventListener('click', () => {
      $('record-detail').textContent = JSON.stringify(r, null, 2); $('provenance').open = true;
      $('provenance-cards').replaceChildren();
      [['Source identity',`${r.source} / ${r.external_id}`],['Source observation',r.source_date || 'Unknown — not replaced with import time'],['Source snapshot updated',r.source_updated_at],['Accepted by importer',r.imported_at],['Scheduled / submitted',r.submitted_at || r.scheduled_for || 'No corresponding timestamp supplied'],['Verification evidence',r.verified_at ? `${r.verified_at} · ${r.evidence_url}` : 'No verification evidence supplied']].forEach(([label,value]) => { const card=el('div',undefined,'provenance-card');card.append(el('span',label),el('strong',value));$('provenance-cards').append(card); });
    });
    name.append(title, el('span', `${r.workstream} / ${r.source} / ${r.external_id}`, 'source-line'));
    const status = el('td'); status.append(el('span', r.status, `badge ${r.status}`));
    const metric = el('td', r.metric_value === null ? '— Unknown' : `${r.metric_value.toLocaleString()} ${r.metric_unit}`, r.metric_value === null ? 'muted' : '');
    const date = el('td', r.source_date ? r.source_date.slice(0, 10) : '— Unknown', r.source_date ? '' : 'muted');
    const freshness = el('td'); freshness.append(el('span', r.age_days === null ? 'Unknown' : `${r.freshness} · ${r.age_days}d`, `freshness ${r.freshness}`));
    tr.append(name, status, metric, date, freshness); $('rows').append(tr);
  }
  $('result-count').textContent = `${rows.length} of ${data.records.length} records`;
  $('empty').hidden = rows.length > 0;
}
function renderReport(value) {
    data=value;
    $('pipeline').replaceChildren(); $('quality').replaceChildren();
    $('as-of').textContent = new Date(data.as_of).toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
    $('clock-mode').textContent = `As of ${data.as_of.slice(11,16)}`;
    $('total').textContent = data.records.length;
    $('verified').textContent = data.statuses.verified;
    $('stale').textContent = data.quality.stale;
    $('missing').textContent = data.quality.missing_metrics;
    statuses.forEach((s,i) => {const card = el('button', undefined, 'stage'); card.type='button';card.setAttribute('aria-label',`Filter ${s} records`);card.addEventListener('click',()=>{$('status').value=s;renderRows();$('register').scrollIntoView({block:'start'});});card.append(el('span',`${String(i+1).padStart(2,'0')} / ${s}`),el('strong',data.statuses[s]),el('small',meanings[i])); $('pipeline').append(card);});
    [['Stale source dates',data.quality.stale],['Unknown source dates',data.quality.unknown_source_dates],['Missing metric values',data.quality.missing_metrics]].forEach(([label,count]) => { const row = el('div',undefined,'quality-row'); row.append(el('span',label),el('strong',count)); $('quality').append(row); });
    $('source-health').replaceChildren();
    [...new Set(data.records.map(r=>r.source))].forEach(source=>{ const rows=data.records.filter(r=>r.source===source),known=rows.filter(r=>r.source_date).length,card=el('article',undefined,'source-card');const meter=el('meter');meter.min=0;meter.max=rows.length;meter.value=known;meter.setAttribute('aria-label',`${source}: ${known} of ${rows.length} source dates known`);card.append(el('span',source,'eyebrow'),el('strong',`${rows.length} records`),el('p',`${rows.filter(r=>r.freshness==='stale').length} stale · ${rows.filter(r=>r.freshness==='unknown').length} undated · ${rows.filter(r=>r.metric_value===null).length} missing metrics`),meter,el('small',`${known}/${rows.length} observations dated`));$('source-health').append(card);});
    renderRows();
}
async function start() {
  try {
    const response = await fetch('/api/report');
    if (!response.ok) throw new Error('The report is unavailable. Check the local database and reporting time.');
    renderReport(await response.json());
    ['search','status','freshness','source'].forEach(id => $(id).addEventListener('input',renderRows));
    $('reset').addEventListener('click',() => {['search','status','freshness','source'].forEach(id => $(id).value='');renderRows();});
    await bootExperience();
  } catch(error) { $('error').hidden = false; $('error').textContent = error.message; }
}
window.addEventListener('DOMContentLoaded',start);
