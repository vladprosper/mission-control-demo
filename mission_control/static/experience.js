/* Static UI templates; every fixture value is rendered with textContent. */
'use strict';
let context, lab, previewResult;
const architectureNodes = {
  workAgents:['Work-domain agents','The reference places example work agents such as IBM Bob and Microsoft Copilot within work account, context and processing permissions. Product name alone does not grant access.','Reference architecture · agent calls are not implemented in this demo.'],
  workStores:['Work source ownership','Box holds work files in the described model. Confidential source material stays in an appropriate encrypted local work store. The dashboard is not the authoritative source for document text.','Reference architecture · no Box client, private store or encryption is present here.'],
  personalAgents:['Personal-domain agents','The reference groups Codex, dots and Claude as examples of personal agents. Account, task and permission determine placement; credentials and retained context remain scoped to the domain.','Reference architecture · fixtures contain no credentials or agent context.'],
  personalStores:['Personal source ownership','Dropbox holds personal files in the described model. Sensitive personal material follows its own release and local processing restrictions. Ownership and sensitivity are separate dimensions.','Reference architecture · no Dropbox connection or private source content is present.'],
  release:['Destination-specific release policy','Before shared coordination receives anything, the owning domain decides which fields may leave. A neutral alias can be permitted for one item; another item may need complete exclusion. Read access does not imply permission to release.','Implemented demonstration · portfolio.py / evaluate_release over fictional allowlist fixtures.'],
  notion:['Durable decisions and next actions','Notion owns consequential conclusions, next actions, research questions and relationships. A useful conversation leaves its decision and a source pointer rather than a copy of the full conversation. Corrections belong in the owning source.','Reference architecture · mock_notion labels and fictional decision references only.'],
  sqlite:['Local reporting layer','SQLite holds permitted identifiers, relationships, dated observations and metrics. In this demo it also stores normalized snapshots and successful import summaries. Workbench writes use a disposable in-memory copy.','Implemented · store.py / import_records + report; workbench.py / Workbench.'],
  dashboard:['Mission Control reporting','The interface brings next actions, evidence gaps and observation history into view. It helps the owner return to the relevant source and does not establish whether an agent conclusion is true.','Implemented · server.py + static/app.js + static/experience.js; no external actions.'],
  adapter:['1 / File-only mock adapter','JSON and CSV fixtures supply dated observation packets. Parsing is separate from validation. No connector, browser collector, live account or network request participates in the importer.','Implemented · adapters.py / load_mock_file; examples/*.json and synthetic.csv.'],
  validation:['3 / Complete-batch validation','Every row is checked for identity, supported status, timezone-aware dates, metric types and fictional evidence requirements before a transaction opens. Structural checks do not prove that a source claim is true.','Implemented · store.py / validate. Try Reject an invalid packet in the workbench.'],
  transaction:['4 / Identity and transaction boundary','Rows match by source and external ID; canonical hashes detect identical content. Changed content needs a newer source timestamp. A conflict after a staged insert rolls the entire transaction back.','Implemented · store.py / import_records; BEGIN IMMEDIATE / COMMIT / ROLLBACK.'],
  projection:['5 / Reporting projection','Source observation time drives freshness. Missing values remain unknown; zero remains a measured zero. The reporting view is separate from import writes and source corrections.','Implemented · store.py / report; portfolio.py supplies additional fictional lineage fixtures.'],
  preview:['2 / Human-controlled sandbox','Preview runs the actual importer on a disposable SQLite copy. Apply requires the successful preview token at the same sandbox revision. A second apply or stale preview is rejected. This is a review interaction, not an identity/role system.','Implemented · workbench.py / preview + apply. The source database is never changed by web actions.']
};

function showView(name) {
  if (!['overview','architecture','evidence','workbench'].includes(name)) name='overview';
  document.querySelectorAll('.page-view').forEach(view=>view.hidden=view.id!==`view-${name}`);
  document.querySelectorAll('nav [data-view]').forEach(button=>{if(button.dataset.view===name)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
  history.replaceState(null,'',`#${name}`);
  window.scrollTo({top:0,behavior:'instant'});
}
function intro(kicker,title,description) {
  const section=el('section',undefined,'view-intro');section.append(el('span',kicker,'eyebrow'),el('h1',title),el('p',description));return section;
}
function panel(kicker,title) {
  const section=el('section',undefined,'panel'),heading=el('div',undefined,'section-head'),text=el('div');text.append(el('span',kicker,'eyebrow'),el('h2',title));heading.append(text);section.append(heading);return section;
}
function button(text,cls,handler) { const b=el('button',text,cls);b.type='button';if(handler)b.addEventListener('click',handler);return b; }
function table(headers,rows,cls) {
  const wrap=el('div',undefined,'table-scroll'),t=el('table',undefined,cls),head=el('thead'),hr=el('tr'),body=el('tbody');
  headers.forEach(h=>{const th=el('th',h);th.scope='col';hr.append(th);});head.append(hr);
  rows.forEach(row=>{const tr=el('tr');row.forEach(value=>{const td=el('td');td.append(value instanceof Node?value:document.createTextNode(value??'—'));tr.append(td);});body.append(tr);});t.append(head,body);wrap.append(t);return wrap;
}
function architectureNode(id,title,sub,cls='') {
  const node=button(title,`arch-node ${cls}`,()=>selectArchitecture(id));node.dataset.arch=id;node.append(el('span',sub));return node;
}
function selectArchitecture(id) {
  const [title,description,implementation]=architectureNodes[id];
  document.querySelectorAll('[data-arch]').forEach(n=>n.classList.toggle('active',n.dataset.arch===id));
  $('architecture-detail').replaceChildren(el('h3',title),el('p',description),el('div',implementation,'code-ref'));
}
function renderArchitecture() {
  const view=el('div',undefined,'page-view');view.id='view-architecture';view.hidden=true;
  view.append(intro('ARCHITECTURE / RESPONSIBILITY & CONTROL','Continuity without access to everything.','The supplied architecture separates source ownership, agent permissions, permitted reporting and recovery. Explore that reference, then inspect exactly which parts execute in this demo.'));
  const section=panel('01 / SYSTEM MAP','Select a component to inspect its responsibility.'),seg=el('div',undefined,'segmented');
  const refButton=button('Documented system','',()=>{reference.hidden=false;implemented.hidden=true;refButton.setAttribute('aria-pressed','true');implButton.setAttribute('aria-pressed','false');selectArchitecture('sqlite');});
  const implButton=button('Implemented demo','',()=>{reference.hidden=true;implemented.hidden=false;refButton.setAttribute('aria-pressed','false');implButton.setAttribute('aria-pressed','true');selectArchitecture('adapter');});
  refButton.setAttribute('aria-pressed','true');implButton.setAttribute('aria-pressed','false');seg.append(refButton,implButton);section.append(seg);
  const reference=el('div'),domains=el('div',undefined,'arch-domain-grid');
  [['WORK OWNERSHIP','Work domain','workAgents','workStores','Box · encrypted local work store','domain'],['PERSONAL OWNERSHIP','Personal domain','personalAgents','personalStores','Dropbox · encrypted local personal store','domain personal']].forEach(([label,title,agent,store,sub,cls])=>{const domain=el('div',undefined,cls);domain.append(el('span',label,'boundary-label'),el('h3',title),architectureNode(agent,'Domain-scoped agents','Own account · credentials · retrieval · retained context'),architectureNode(store,'Authoritative file stores',sub),architectureNode('release','Release policy gate','Allowlisted fields / neutral alias / exclude entirely','release'));domains.append(domain);});
  const shared=el('div',undefined,'shared-layer'),sharedNodes=el('div',undefined,'shared-grid');shared.append(el('span','PERMITTED METADATA ONLY','eyebrow'));sharedNodes.append(architectureNode('notion','Notion','Durable decisions · next actions · relationships'),architectureNode('sqlite','Local SQLite','Identifiers · dates · history · metrics'),architectureNode('dashboard','Mission Control','Portfolio · evidence gaps · source drill-down'));shared.append(sharedNodes);
  reference.append(domains,el('div','↓ Permitted fields pass into shared coordination ↓','flow-arrow'),shared,el('p','Source corrections and decisions return to the tool that owns them. Manuscripts own their wording; platforms establish destinations; reporting preserves the connecting observations.','scope-note'));
  const recovery=el('div',undefined,'recovery-strip');recovery.append(el('strong','Recovery follows ownership. '),document.createTextNode('Approved work reporting export → local encryption → Box. Approved personal reporting export → local encryption → Dropbox. Separate 1Password vaults keep keys outside archives. The reference calls for fresh-download, decryption, manifest, integrity and relationship checks. Encryption, vaults and remote restore are described here; they are not implemented by this demo.'));reference.append(recovery);
  const implemented=el('div',undefined,'implemented-flow');implemented.hidden=true;
  [['adapter','1 / Mock packet','Synthetic JSON / CSV'],['preview','2 / Preview / apply','Choose isolated SQLite copy / human review'],['validation','3 / Validate','Complete batch before writes'],['transaction','4 / Atomic import','Deduplicate · enforce source precedence'],['projection','5 / Project observations','Dates · explicit nulls · separate units'],['dashboard','6 / Inspect report','Filters · provenance · trace · audit']].forEach(([id,title,sub])=>implemented.append(architectureNode(id,title,sub)));
  const detail=el('div',undefined,'arch-explanation');detail.id='architecture-detail';detail.setAttribute('aria-live','polite');section.append(reference,implemented,detail);view.append(section);
  const policy=panel('02 / RELEASE POLICY LAB','Ownership and sensitivity answer different questions.');policy.append(el('p','Try four fictional cases. The backend evaluates an explicit destination allowlist; source text is withheld. A public work item still does not authorize processing by a personal-domain agent.','scope-note'));
  const select=el('select',undefined,'full-select');select.id='release-case';select.setAttribute('aria-label','Release policy case');context.release_candidates.forEach(c=>{const o=el('option',c.label);o.value=c.id;select.append(o);});policy.append(select);
  const status=el('div');status.id='release-status';status.setAttribute('aria-live','polite');const grid=el('div',undefined,'policy-grid'),left=el('div'),right=el('div'),input=el('pre'),output=el('pre');input.id='release-input';output.id='release-output';left.append(el('span','FICTIONAL SOURCE CANDIDATE','field-caption'),input);right.append(el('span','PERMITTED REPORTING PACKET','field-caption'),output);grid.append(left,right);policy.append(status,grid,el('p','This illustrates the release boundary in code. It does not implement identity verification, encrypted storage, local-model processing guarantees, or a production authorization service.','scope-note'));select.addEventListener('change',()=>renderRelease(select.value));view.append(policy);
  const matrix=panel('03 / IMPLEMENTATION BOUNDARY','A reference map is not an integration claim.');matrix.append(table(['Responsibility','Demo behaviour','Boundary'],[
    ['Agents and collectors','File-only mock packets','No models, live connectors, credentials or retained agent context.'],
    ['Domain release gate','Executable fixture allowlist + domain-match checks','Illustrative policy, not authentication or a complete authorization engine.'],
    ['Reporting import','Actual validation, hashing and atomic SQLite writes','Workbench changes are in memory; original database remains unchanged.'],
    ['Evidence relationships','Fictional manuscript / decision / destination / metric chain','No destination is opened or externally verified.'],
    ['Private processing and recovery','Explained from the supplied architecture document','No encryption, vault access, private workspace or backup service is implemented.']
  ],'architecture-matrix'));matrix.append(el('p','Source: owner-supplied “The Architecture Behind My AI Assisted Work”, especially ownership/source authority (pp. 1–4), evidence and observable refresh (pp. 5–7), recovery (pp. 7–9). The description is a reference, not independent verification of an operational system.','scope-note'));view.append(matrix);$('experience-views').append(view);selectArchitecture('sqlite');renderRelease(select.value);
}
function renderRelease(id) {
  const c=context.release_candidates.find(c=>c.id===id),r=c.result;
  $('release-input').textContent=JSON.stringify({owner:c.owner,agent_domain:c.agent_domain,sensitivity:c.sensitivity,fields:c.fields},null,2);
  $('release-output').textContent=JSON.stringify(r.released,null,2);
  $('release-status').className=`policy-status ${r.allowed?'':'blocked'}`;
  $('release-status').replaceChildren(el('strong',r.allowed?'Permitted metadata released':'Release blocked'),el('span',r.reason));
}
function renderEvidence() {
  const view=el('div',undefined,'page-view');view.id='view-evidence';view.hidden=true;
  view.append(intro('EVIDENCE / SOURCE AUTHORITY','Follow the work to its evidence.','A decision, a manuscript, a destination and a measurement have different owners and meanings. These fictional relationships show why a plausible link or a nearby metric is not enough.'));
  const chain=panel('01 / ONE PIECE OF WORK',context.article.project);chain.append(el('h3',context.article.title,'article-title'));const nodes=el('div',undefined,'lineage-chain');
  [['01 / DECISION','Durable conclusion',context.article.decision,context.article.decision_ref],['02 / MANUSCRIPT','Authoritative text','The file owns the article wording. Its version is referenced rather than copied into reporting.',context.article.manuscript],['03 / DESTINATIONS','Separate platform identities','One article relationship matches. The other points to a homepage and needs reconciliation.','DEST-SUB-21 / DEST-LI-21'],['04 / OBSERVATIONS','Dated measurements','Source, period and metric definition stay with each observation. Subscriber change has publication scope.','No cross-platform total']].forEach(([label,title,description,ref])=>{const n=el('div',undefined,'lineage-node');n.append(el('span',label,'eyebrow'),el('strong',title),el('p',description),el('div',ref,'code-ref'));nodes.append(n);});chain.append(nodes);
  const destinations=el('div',undefined,'destination-grid');context.destinations.forEach(d=>{const card=el('article',undefined,'destination');card.append(el('h3',d.platform),el('span',d.relationship,`flag ${d.relationship==='matched'?'':'warning'}`),el('p',d.note),el('span',d.url,'code-ref'),el('p',`${d.expected_article} → ${d.resolved_article||'No resolved article identity'}`));destinations.append(card);});chain.append(destinations,el('p',`Next action: ${context.article.next_action}`,'scope-note'));view.append(chain);
  const metrics=panel('02 / OBSERVATION REGISTER','Preserve the meaning behind every number.');metrics.append(table(['Measurement / definition','Observed value','Source / collection time','Reporting period','Relationship'],context.observations.map(o=>{const name=el('div');name.append(el('b',o.metric),el('div',o.definition,'definition'));const value=el('div');value.append(el('strong',o.value===null?'—':o.value.toLocaleString()),el('span',o.value===null?'Unknown':o.unit));return [name,value,`${o.source}\n${o.collected_at||'No collection timestamp'}`,o.period,el('span',o.state,`flag ${o.attributable?'':'warning'}`)];}),'metric-table'));metrics.append(el('p','Values are invented. Views and impressions are not added together. Publication subscriber change is not attributed to an article. Relationship matches and collection failures are explicit fixtures, not live verification.','scope-note'));view.append(metrics);
  const refresh=panel('03 / OBSERVABLE REFRESH','An attempted collection is not a new observation.');const cards=el('div',undefined,'source-health');context.refresh_sources.forEach(s=>{const card=el('article',undefined,'source-card');card.append(el('span',s.source,'eyebrow'),el('h3',s.state),el('p',s.note),el('div',`Last observation: ${s.last_observation}`,'code-ref'),el('div',`Latest attempted collection: ${s.attempted_at}`,'code-ref'));cards.append(card);});refresh.append(cards,el('p','Reloading this page does not update these source dates. Use “Refresh an observed zero” in the workbench to see a dated packet change a source observation through the importer.','scope-note'));view.append(refresh);
  const routine=panel('04 / RECURRING WORK',context.routine.title),grid=el('div',undefined,'routine-grid');[['Schedule',context.routine.scheduled_for],['Observed run',context.routine.observed_run],['Checklist',context.routine.checklist],['Approval',context.routine.approval],['Completion',context.routine.completion]].forEach(([label,value])=>{const item=el('div');item.append(el('span',label),el('strong',value));grid.append(item);});routine.append(grid,el('p',context.routine.note,'routine-note'));view.append(routine);$('experience-views').append(view);
}
function renderWorkbench() {
  const view=el('div',undefined,'page-view');view.id='view-workbench';view.hidden=true;
  view.append(intro('OPERATIONS / EXECUTABLE SCENARIOS','Inspect what the importer actually does.','Preview a collection packet, inspect the transaction trace, then choose whether to apply it. The same Python validation and SQLite importer used by the CLI powers these scenarios.'));
  const status=el('div',undefined,'lab-status'),label=el('div');label.append(el('strong','Disposable synthetic sandbox'),el('span','The source database and all external systems remain unchanged. Resets affect this in-memory session only.'));status.append(label,button('Reset sandbox','secondary',resetSandbox));view.append(status);
  const section=panel('01 / COLLECTION PACKET','A preview is required before apply.'),grid=el('div',undefined,'workbench-grid'),input=el('div'),select=el('select',undefined,'full-select');select.id='scenario';select.setAttribute('aria-label','Import scenario');
  (lab?.scenarios||[]).forEach(s=>{const option=el('option',s.title);option.value=s.id;select.append(option);});input.append(el('label','Choose a scenario','field-caption'),select);const desc=el('p',undefined,'scenario-description');desc.id='scenario-description';input.append(desc);
  const actions=el('div',undefined,'action-row');actions.append(button('1. Preview import','primary',previewScenario),button('2. Apply to sandbox','secondary',applyScenario));actions.children[0].id='preview-import';actions.children[1].id='apply-import';actions.children[1].disabled=true;input.append(actions,el('span','SYNTHETIC PACKET / READ-ONLY INPUT','field-caption'));const payload=el('pre',undefined,'packet-preview');payload.id='scenario-payload';input.append(payload);
  const trace=el('div',undefined,'trace-box');trace.id='run-trace';trace.setAttribute('aria-live','polite');trace.append(el('h3','Execution trace'),el('p','Choose a scenario and preview it. You will see the actual validation, identity, storage and transaction events, followed by a before/after comparison.','trace-placeholder'));grid.append(input,trace);section.append(grid);view.append(section);
  const diff=panel('02 / CHANGE REVIEW','Compare source fields before committing.');const diffbody=el('div');diffbody.id='run-diff';diffbody.append(el('p','No preview yet. A rejected packet produces no retained field changes.','scope-note'));diff.append(diffbody,button('View current sandbox report ↗','text-button',()=>showView('overview')));view.append(diff);
  const ledger=panel('03 / SESSION HISTORY','Keep attempts distinct from accepted imports.');const history=el('div');history.id='session-history';ledger.append(history,el('p','Preview attempts and failures are retained in this server session only. The SQLite successful-import ledger is separate. Restart or reset clears the sandbox history; there is no durable failure audit service.','scope-note'));view.append(ledger);
  $('experience-views').append(view);select.addEventListener('change',selectScenario);selectScenario();renderHistory();
  if(!lab){$('preview-import').disabled=true;$('run-trace').textContent='Workbench is disabled in CLI read-only mode. Start scripts/review.py to enable it.';}
}
function selectScenario() {
  previewResult=null;$('apply-import').disabled=true;
  const scenario=lab?.scenarios.find(s=>s.id===$('scenario').value);
  $('scenario-description').textContent=scenario?.description||'No scenarios available.';
  $('scenario-payload').textContent=JSON.stringify(scenario?.rows||[],null,2);
}
async function action(path,body) {
  const response=await fetch(`/api/workbench/${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const value=await response.json();if(!response.ok)throw new Error(value.error||'Workbench action failed');return value;
}
async function refreshLab() {
  const response=await fetch('/api/workbench');if(!response.ok)return;lab=await response.json();
  $('sandbox-revision').textContent=`IN-MEMORY SANDBOX · REV ${lab.revision}`;renderReport(lab.report);renderHistory();
}
async function runAction(operation) {
  $('error').hidden=true;$('preview-import').disabled=true;$('apply-import').disabled=true;
  $('scenario').disabled=true;const reset=document.querySelector('.lab-status button');reset.disabled=true;
  try{await operation();}catch(error){previewResult=null;$('error').hidden=false;$('error').textContent=error.message;}
  finally{$('scenario').disabled=false;reset.disabled=!lab;$('preview-import').disabled=!lab;$('apply-import').disabled=!(previewResult?.accepted);}
}
async function previewScenario() {
  previewResult=null;await runAction(async()=>{previewResult=await action('preview',{scenario:$('scenario').value});renderTrace(previewResult);await refreshLab();});
}
async function applyScenario() {
  if(!previewResult?.accepted)return;
  await runAction(async()=>{const result=await action('apply',{scenario:previewResult.scenario,preview_token:previewResult.preview_token});previewResult=null;renderTrace(result);await refreshLab();});
}
async function resetSandbox() {
  if(!lab)return;
  await runAction(async()=>{lab=await action('reset',{});previewResult=null;renderReport(lab.report);$('sandbox-revision').textContent=`IN-MEMORY SANDBOX · REV ${lab.revision}`;renderHistory();$('run-trace').replaceChildren(el('h3','Sandbox restored'),el('p','The original fictional baseline is restored. Previous preview tokens are invalid.','scope-note'));$('run-diff').replaceChildren(el('p','Choose a scenario to preview a fresh comparison.','scope-note'));});
}
function renderTrace(result) {
  const trace=$('run-trace');trace.replaceChildren(el('h3',result.mode==='preview'?'Preview execution':'Applied execution'));
  const outcome=el('div',undefined,`outcome ${result.accepted?'':'rejected'}`);outcome.append(el('strong',result.accepted?(result.mode==='preview'?'Accepted in preview copy':'Committed to sandbox'):'Rejected · no retained changes'));
  outcome.append(el('span',result.error||`${result.counts.inserted} inserted · ${result.counts.updated} updated · ${result.counts.duplicates} duplicate skips`));
  if(result.mode==='preview')outcome.append(el('p','Preview executes on a temporary SQLite copy. The current sandbox report has not changed.'));
  trace.append(outcome);result.events.forEach((event,i)=>{const step=el('div',undefined,'trace-step'),body=el('div');body.append(el('strong',`${event.stage} / ${event.outcome}`),el('p',event.message));step.append(el('span',String(i+1).padStart(2,'0'),'trace-number'),body);trace.append(step);});
  trace.append(el('div',`State fingerprint (records + import audit)\nBefore ${result.before_hash}\nAfter  ${result.after_hash}\n${result.unchanged?'State unchanged':'State differs; inspect record changes and successful import audit'}`,'hash-pair'));
  const diff=$('run-diff');diff.replaceChildren();
  if(!result.changes.length)diff.append(el('p',result.accepted?'No source field changes. Identical rows are skipped; a successful import summary is still recorded in the trial or sandbox.':'No source field changes survived validation or rollback.','scope-note'));
  else diff.append(table(['Source / ID','Field','Before','After'],result.changes.map(c=>[c.record,c.field,el('span',c.before===null?'null':String(c.before),'before'),el('span',c.after===null?'null':String(c.after),'after')]),'diff-table'));
}
function renderHistory() {
  if(!$('session-history'))return;const target=$('session-history');target.replaceChildren();
  if(!lab?.history.length){target.append(el('p','No workbench runs yet. Try a preview to create a trace.','audit-empty'));return;}
  target.append(table(['Run','Action','Scenario','Outcome','Revision'],lab.history.map(r=>[r.sequence,r.mode,r.scenario,r.accepted?'Accepted':`Rejected: ${r.error}`,r.revision]),'history-table'));
}
async function bootExperience() {
  const response=await fetch('/api/context');if(!response.ok)throw new Error('Architecture context unavailable');context=await response.json();
  const state=await fetch('/api/workbench');lab=state.ok?await state.json():null;
  renderArchitecture();renderEvidence();renderWorkbench();
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
  if(lab){renderReport(lab.report);$('sandbox-revision').textContent=`IN-MEMORY SANDBOX · REV ${lab.revision}`;}else $('sandbox-revision').textContent='READ-ONLY CLI REPORT';
  showView(location.hash.slice(1)||'overview');
}
