'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
let snapshot;
let pending = false;
const hints = [
  'The open question determines what the review should check.',
  'A scheduled instruction and a completed run are different things.',
  'The finding is ready. Its implication needs your judgment.',
  'Accept the distinction in this fictional example.',
  'A timeline jump, with no actual publishing action.',
  'Keep the next question linked to this article and review.',
  'The loop is complete. The answer to the next question is still unknown.'
];
const card = (eyebrow, content, type='') => `<section class="card ${type}"><div class="eyebrow">${eyebrow}</div>${content}</section>`;
function scene(view) {
  const {article:a, routine:r, run, finding:f, decision:d, publication:p, reader_question:q, next_question:n} = view.state;
  switch(view.step) {
    case 0: return `<p class="intro">I paused this draft. Before doing more work, I need to know exactly where I left it.</p><div class="grid">${card('DRAFT v3 · WORKING ARGUMENT',`<p class="quote">“${esc(a.argument)}”</p><p class="metadata">The manuscript holds the wording.<br>The linked research record holds context.</p>`)}${card('THE UNRESOLVED QUESTION',`<h3>${esc(a.question)}</h3><p class="divider"><strong>Next action</strong><br>${esc(a.next_action)}</p>`,'soft')}</div>`;
    case 1: return `<p class="intro">The same article has a recurring research instruction. Here is what its next run is meant to do.</p>${card('RECURRING INSTRUCTION',`<h3>${esc(r.name)}</h3><p class="quote">${esc(r.instruction)}</p><div class="schedule-row"><div><small>Cadence</small><strong>${esc(r.recurrence)}</strong></div><div><small>Next scheduled run</small><strong>${esc(r.next_run)}</strong></div><div><small>Current state</small><span class="pill">Scheduled</span></div></div>`)}<p class="tiny">No run has been shown yet. The next click reveals a prepared fictional run; it does not start a real automation.</p>`;
    case 2: return `<p class="intro">The review found a relevant example. It also left a visible gap.</p><div class="grid">${card('REVIEW RUN · 12 SEPTEMBER',`<div class="run-summary"><strong>${run.sources_read}/${run.sources_total}</strong><div>sources read<br><span class="pill amber">${esc(run.status)}</span></div></div><ul class="source-list">${run.sources.map(s=>`<li class="${s.status==='Unavailable'?'gap':''}"><div>${esc(s.name)}<small>${esc(s.date)}</small></div><b>${esc(s.status)}</b></li>`).join('')}</ul>`)}${card('ARTICLE UPDATE · YOUR REVIEW NEEDED',`<h3>${esc(f.summary)}</h3><p class="metadata">${esc(f.source)}</p><p class="divider">The finding is linked to this article. Draft v3 and its argument are still unchanged.</p><p><span class="pill amber">${esc(a.decision_status)}</span></p>`,'warm')}</div>`;
    case 3: return `<p class="intro">Read the finding, compare it with the draft, then make the editorial call.</p><div class="grid">${card('WHAT THE EXAMPLE SHOWS',`<h3>${esc(f.summary)}</h3><p class="metadata">Source: ${esc(f.source)}<br>Linked from the 12 September review run.</p><div class="divider"><div class="eyebrow">WHAT THE DRAFT CURRENTLY SAYS</div><p>“A purchasing agent needs limits beyond a budget.”</p></div>`)}${card('THE DECISION YOU CAN RECORD',`<div class="decision"><p class="quote">Price negotiation and changes to contractual terms need separate permissions.</p></div><p>Having permission to negotiate a price does not establish authority to change cancellation terms.</p><p class="metadata">An agent proposed the implication. You decide whether it belongs in the article.</p>`,'soft')}</div>`;
    case 4: return `<p class="intro">Your decision is now recorded. The revised manuscript gives you a clear place to resume.</p><div class="grid">${card('DECISION SAVED · MOCK RESEARCH RECORD',`<h3>${esc(d.text)}</h3><p class="metadata">Decision by you · ${esc(d.date)}<br>Linked to the same finding and article.</p><div class="checkline"><span class="checkmark">✓</span><span>A simulated agent saved the decision and source reference.</span></div>`,'soft')}${card('MANUSCRIPT · REVISED FOR REVIEW',`<div class="beforeafter"><span>v3 · broad claim</span><span>→</span><strong>v4 · separate permissions</strong></div><p class="divider">${esc(a.argument)}</p><p class="metadata"><strong>Next action:</strong> ${esc(a.next_action)}</p><div class="checkline"><span class="checkmark">✓</span><span>The local reporting snapshot reflects the change.</span></div>`)}</div>`;
    case 5: return `<p class="intro">Jump ahead: the same article was published on 20 September in this fictional timeline. Observations were collected on 30 September.</p><div class="grid metrics">${p.metrics.map(m=>card(`${esc(m.platform.toUpperCase())} · SEPARATE DESTINATION`,`<div class="metric-value">${m.value.toLocaleString('en-US')} <small>${esc(m.unit)}</small></div><p class="tiny">${esc(m.definition)}</p><p class="metadata">Period: ${esc(m.period)} · collected ${esc(m.collected_at)}<br>${esc(m.destination)}</p>`)).join('')}</div><div class="reader">${card('A READER BRINGS THE NEXT QUESTION',`<h3>“${esc(q.text)}”</h3><p class="tiny">Subscriber impact: <strong>Unknown</strong>. These observations do not establish attribution.</p>`,'soft')}</div>`;
    case 6: return `<p class="intro">The reader’s question returns to the existing review, with its connection to the article intact.</p>${card('NEXT INSTRUCTION · SAME RECURRING REVIEW',`<h3>${esc(n.text)}</h3><p class="metadata">${esc(r.name)} · ${esc(r.recurrence.toLowerCase())}<br>Next in the story: ${esc(r.next_run)}</p><p><span class="pill">Research queued · answer not established</span></p><div class="loop"><span>Article</span>→<span>Review</span>→<span>Your decision</span>→<span>Draft</span>→<span>Reader question</span>↻</div>`,'soft')}<p class="tiny">You can see where the work stands, why the argument changed and what the next review should investigate. No new agent or real schedule was created.</p>`;
    default: throw new Error('Unknown story step');
  }
}
function render(view) {
  snapshot = view;
  const a = view.state.article;
  $('article-status').textContent = a.status;
  $('draft-version').textContent = `v${a.draft_version}`;
  $('next-run').textContent = view.state.routine.next_run;
  $('progress').innerHTML = view.steps.map((s,i)=>`<div class="progress-item ${i<view.step?'done':i===view.step?'active':''}" ${i===view.step?'aria-current="step"':''}><div class="progress-line"></div><span>${esc(s.label)}</span></div>`).join('');
  $('scene-number').textContent = `${String(view.step+1).padStart(2,'0')} / 07`;
  $('scene-date').textContent = view.guide.date;
  $('scene-title').textContent = view.guide.title;
  $('scene').innerHTML = scene(view);
  $('timing').textContent = view.guide.time;
  $('narration').textContent = view.guide.say;
  $('action-hint').textContent = hints[view.step];
  $('advance').textContent = view.guide.button;
  $('advance').disabled = !view.interactive;
  $('restart').disabled = !view.interactive;
  if (!view.interactive) showError('This server is in read-only mode. Use Launch Mission Control.command to enable the walkthrough.');
}
function showError(message) { $('error').textContent = message; $('error').hidden = false; }
async function load() {
  const response = await fetch('/api/story', {cache:'no-store'});
  if (!response.ok) throw new Error('The local story server could not load. Run Launch Mission Control.command again.');
  render(await response.json());
}
async function advance(reset=false) {
  if (pending || !snapshot) return;
  pending = true;
  $('advance').disabled = true; $('restart').disabled = true; $('error').hidden = true;
  try {
    const response = await fetch('/api/story/advance', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:reset?'reset':snapshot.guide.action, revision:snapshot.revision})});
    const result = await response.json();
    if (!response.ok) { await load(); throw new Error(result.error || 'Could not advance the story.'); }
    render(result);
    $('main').focus({preventScroll:true});
  } catch(error) { showError(error.message); }
  finally { pending = false; if(snapshot?.interactive) { $('advance').disabled = false; $('restart').disabled = false; } }
}
$('advance').addEventListener('click', ()=>advance());
$('restart').addEventListener('click', ()=>advance(true));
$('architecture-open').addEventListener('click', ()=>$('architecture').showModal());
$('architecture-close').addEventListener('click', ()=>$('architecture').close());
$('architecture').addEventListener('click', event=>{if(event.target===$('architecture')) { const r=$('architecture').getBoundingClientRect(); if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) $('architecture').close(); }});
function openArticleTarget(kind) {
  if(!snapshot) return;
  const {article:a,finding:f,decision:d}=snapshot.state;
  let title,content;
  if(kind==='manuscript') {
    title=`Manuscript · version ${a.draft_version}`;
    content=`<div class="target-notice">Fictional excerpt for this demo. This is not your actual manuscript file.</div><article class="target-document"><div class="eyebrow">${esc(a.project)} · ${esc(a.status)}</div><h3>${esc(a.title)}</h3><p class="quote">${esc(a.argument)}</p><p>A budget alone does not establish which terms a purchasing agent may agree to. The argument needs examples that distinguish choosing an offer from negotiating it.</p>${d?`<p>The reviewed example separates price negotiation from changes to cancellation terms. An agent may have authority for the first while needing human approval for the second.</p>`:`<p class="target-question"><strong>Still to resolve:</strong> ${esc(a.question)}</p>`}<div class="divider"><strong>Next action</strong><p>${esc(a.next_action)}</p></div></article>`;
  } else if(kind==='record') {
    title='Research record · mock Notion';
    content=`<div class="target-notice">Local fictional record linked to ${esc(a.id)}. No Notion page is connected.</div><dl class="target-properties"><dt>Article</dt><dd>${esc(a.title)}</dd><dt>Manuscript</dt><dd>Version ${a.draft_version}</dd><dt>Status</dt><dd>${esc(a.status)}</dd><dt>Open question</dt><dd>${esc(a.question)}</dd><dt>Latest finding</dt><dd>${f?esc(f.summary):'No review finding shown yet.'}</dd><dt>Owner decision</dt><dd>${d?esc(d.text):'Not recorded; owner review is still required.'}</dd><dt>Next action</dt><dd>${esc(a.next_action)}</dd></dl>`;
  } else {
    title='Continue the article conversation';
    const handoff=`Continue work on “${a.title}” in its existing conversation.\nCurrent manuscript: v${a.draft_version}.\nWorking argument: ${a.argument}\nOpen question: ${a.question}\n${d?'Recorded owner decision: '+d.text+'\n':''}Next action: ${a.next_action}\nThe article and all source evidence in this demo are fictional.`;
    content=`<div class="target-notice">Existing chat link not configured. This is a local demo handoff, not a live AI conversation.</div><div class="target-document"><h3>Return with the article’s context</h3><p>The destination should be this article’s existing AI conversation, after its link and access have been verified. A fresh blank chat would not preserve that history.</p><label for="resume-context">Saved resume context · ${esc(a.id)}</label><textarea id="resume-context" readonly>${esc(handoff)}</textarea><p class="tiny">To connect your actual work, supply the corresponding manuscript location, Notion record URL and existing article-conversation URL. None has been supplied or verified for this fictional article.</p></div>`;
  }
  $('target-title').textContent=title;
  $('target-content').innerHTML=content;
  $('article-target').showModal();
}
$('open-manuscript').addEventListener('click',()=>openArticleTarget('manuscript'));
$('open-record').addEventListener('click',()=>openArticleTarget('record'));
$('open-conversation').addEventListener('click',()=>openArticleTarget('conversation'));
$('target-close').addEventListener('click',()=>$('article-target').close());
// Old #architecture links land in the same narrative; architecture is optional.
load().catch(error=>showError(error.message));
