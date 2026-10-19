// Telomy Console — one SPA, two workspaces (Centre + Doctor), consuming the FastAPI backend at /mgmt/*.
// Vanilla JS, hash routing, drawer forms driven by /mgmt/form so new therapies/fields/modules appear automatically.
'use strict';
const S = { api: localStorage.getItem('tc.api') || location.origin, token: localStorage.getItem('tc.token') || '', org: 'default', ws: 'centre', cfg: null };

// ---- api ----
async function api(path, { method = 'GET', body } = {}) {
  const r = await fetch(S.api + path, {
    method, headers: { 'Content-Type': 'application/json', ...(S.token ? { Authorization: 'Bearer ' + S.token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (r.status === 401) { showLogin(); throw new Error('unauthorised'); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || ('HTTP ' + r.status));
  return j;
}
const q = (o) => Object.entries(o).filter(([, v]) => v != null && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');

// ---- helpers ----
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
const money = (n) => n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN');
const fmtTime = (ts) => ts ? new Date(ts).toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
const hhmm = (ts) => ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
function toast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2200); }
function statusBadge(s) { const map = { active: 'ok', paid: 'ok', delivered: 'ok', received_at_lab: 'ok', completed: 'ok', checked_in: 'primary', booked: '', confirmed: 'primary', due: 'warn', frozen: 'warn', cancelled: 'danger', no_show: 'danger', created: '', dispatched: 'primary', in_transit: 'primary', scheduled: 'primary', packed: '', collected: 'primary', achieved: 'ok' }; return `<span class="badge ${map[s] ?? ''}">${(s || '').replace(/_/g, ' ')}</span>`; }

// ---- drawer ----
function drawer(title, bodyNode, actions) {
  document.getElementById('drawerTitle').textContent = title;
  const b = document.getElementById('drawerBody'); b.innerHTML = ''; b.appendChild(bodyNode);
  const f = document.getElementById('drawerFoot'); f.innerHTML = '';
  (actions || []).forEach(a => { const btn = el('button', 'btn ' + (a.kind || ''), a.label); btn.onclick = a.onClick; f.appendChild(btn); });
  document.getElementById('scrim').classList.add('show'); document.getElementById('drawer').classList.add('show');
}
function closeDrawer() { document.getElementById('scrim').classList.remove('show'); document.getElementById('drawer').classList.remove('show'); }
document.getElementById('drawerClose').onclick = closeDrawer; document.getElementById('scrim').onclick = closeDrawer;

// render a form from a field spec list: {key,label,type,options,required}
function formNode(fields, values = {}) {
  const wrap = el('div');
  fields.forEach(f => {
    const lab = el('label', 'field'); lab.appendChild(el('span', null, f.label + (f.required ? ' *' : '')));
    let input;
    if (f.type === 'textarea') input = el('textarea');
    else if (f.type === 'select') { input = el('select'); input.appendChild(el('option', null, '')); (f.options || []).forEach(o => { const v = o.value ?? o; input.appendChild(el('option', null, (o.label ?? o))); input.lastChild.value = v; }); }
    else if (f.type === 'bool') { input = el('select'); ['', 'Yes', 'No'].forEach(o => { input.appendChild(el('option', null, o)); }); }
    else { input = el('input'); input.type = (f.type === 'number' || f.type === 'money' || f.type === 'rating' || f.type === 'duration') ? 'number' : (f.type === 'date' ? 'date' : f.type === 'time' ? 'time' : 'text'); }
    input.dataset.key = f.key; if (values[f.key] != null) input.value = values[f.key];
    lab.appendChild(input); wrap.appendChild(lab);
  });
  return wrap;
}
const readForm = (node) => { const o = {}; node.querySelectorAll('[data-key]').forEach(i => { if (i.value !== '') o[i.dataset.key] = i.type === 'number' ? Number(i.value) : i.value; }); return o; };

// ---- navigation ----
const NAV = {
  centre: [
    { sect: 'Operate' }, { id: 'dashboard', ic: '◈', label: 'Dashboard' }, { id: 'schedule', ic: '🗓', label: 'Schedule' },
    { id: 'people', ic: '👤', label: 'Members & patients' }, { id: 'doctors', ic: '🩺', label: 'Doctors' },
    { id: 'fulfillment', ic: '📦', label: 'Orders & pickups' }, { id: 'goals', ic: '◎', label: 'Goals' },
    { sect: 'Resources' }, { id: 'therapies', ic: '✶', label: 'Therapies' }, { id: 'machines', ic: '⚙', label: 'Machines & rooms' },
    { sect: 'Business' }, { id: 'performance', ic: '📈', label: 'Staff performance' }, { id: 'revenue', ic: '₹', label: 'Revenue' },
    { sect: 'Configure' }, { id: 'config', ic: '⚙', label: 'Modules & catalog' }, { id: 'interop', ic: '🔌', label: 'Integrations' },
  ],
  doctor: [
    { sect: 'Clinic' }, { id: 'inbox', ic: '◈', label: 'Inbox' }, { id: 'patients', ic: '👤', label: 'Patients' },
    { id: 'tasks', ic: '✓', label: 'Tasks' }, { id: 'orders', ic: '℞', label: 'Prescriptions & orders' },
    { sect: 'Configure' }, { id: 'templates', ic: '▤', label: 'Note templates' },
  ],
  platform: [
    { sect: 'Network' }, { id: 'overview', ic: '◈', label: 'Overview' }, { id: 'centres', ic: '🏢', label: 'Centres' },
    { id: 'doctors', ic: '🩺', label: 'Doctors' }, { id: 'people', ic: '👤', label: 'People' },
  ],
};
// where each workspace lands on sign-in
const HOME = { centre: 'dashboard', doctor: 'inbox', platform: 'overview' };
function renderNav() {
  const n = document.getElementById('nav'); n.innerHTML = '';
  NAV[S.ws].forEach(item => {
    if (item.sect) { n.appendChild(el('div', 'sect', item.sect)); return; }
    const a = el('a'); a.dataset.route = item.id; a.innerHTML = `<span class="ic">${item.ic}</span><span>${item.label}</span>`;
    a.onclick = () => { location.hash = `${S.ws}/${item.id}`; }; n.appendChild(a);
  });
  if (S.me && S.me.admin) {  // admins manage their own team (separate doctor vs centre staff)
    n.appendChild(el('div', 'sect', 'Admin'));
    const a = el('a'); a.dataset.route = 'staff'; a.innerHTML = `<span class="ic">⊕</span><span>Team & access</span>`;
    a.onclick = () => { location.hash = `${S.ws}/staff`; }; n.appendChild(a);
  }
  document.querySelectorAll('.ws-switch button').forEach(b => b.classList.toggle('on', b.dataset.ws === S.ws));
}

// ---- views (centre) ----
const V = {};
V.dashboard = async () => {
  setTitle('Dashboard', []);
  const v = view(); v.appendChild(skeletonRow(4));
  const d = await api('/mgmt/centre/dashboard?' + q({ org: S.org }));
  v.innerHTML = '';
  v.appendChild(kpis([
    ['Active members', d.active_members, 'enrolled'], ['Today’s bookings', d.today_bookings, `${d.checked_in} checked in`],
    ['Revenue today', money(d.revenue_today), ''], ['Outstanding', money(d.outstanding), 'unpaid invoices'],
  ]));
  const c = el('div', 'card'); c.style.marginTop = '18px';
  c.appendChild(el('div', 'row between center', `<h3>Today’s schedule</h3>`));
  c.appendChild(tableOf(['Time', 'Service', 'Member', 'Status', ''], (d.schedule || []).map(b => [
    hhmm(b.start_ts), b.service_name || '—', '#' + (b.member_id ?? ''), statusBadge(b.status),
    b.status === 'booked' ? btn('Check in', 'primary sm', () => checkIn(b.id)) : '',
  ]), 'No bookings today.'));
  v.appendChild(c);
};
V.schedule = async () => {
  setTitle('Schedule', [btn('New booking', 'primary', newBooking)]);
  const v = view(); v.appendChild(skeletonRow(1));
  const day = new Date().toISOString().slice(0, 10);
  const rows = await api('/mgmt/centre/schedule?' + q({ org: S.org, day }));
  v.innerHTML = '';
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Time', 'Service', 'Member', 'Resource', 'Status', ''], rows.map(b => [
    hhmm(b.start_ts) + '–' + hhmm(new Date(new Date(b.start_ts).getTime() + (b.minutes || 0) * 60000)), b.service_name || '—',
    '#' + (b.member_id ?? ''), b.resource_id ? 'Room ' + b.resource_id : '—', statusBadge(b.status),
    b.status === 'booked' ? btn('Check in', 'primary sm', () => checkIn(b.id)) : btn('Complete', 'sm', () => setBookingStatus(b.id, 'completed')),
  ]), 'Nothing scheduled today.'));
  v.appendChild(c);
};
V.members = async () => {
  setTitle('Members', [btn('Add member', 'primary', newMember)]);
  const v = view(); v.appendChild(skeletonRow(1));
  const rows = await api('/mgmt/centre/members?' + q({ org: S.org }));
  v.innerHTML = '';
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Name', 'Phone', 'Joined', 'Status', ''], rows.map(m => [
    `<b>${m.name}</b>`, m.phone || '—', m.joined_on || '', statusBadge(m.status), btn('Open', 'sm', () => openMember(m.id)),
  ]), 'No members yet. Add your first.'));
  v.appendChild(c);
};
V.fulfillment = async () => {
  setTitle('Orders & pickups', [btn('New order', 'primary', newOrder), btn('Sample pickup', '', newPickup)]);
  const v = view(); v.appendChild(skeletonRow(1));
  const rows = await api('/mgmt/orders?' + q({ org: S.org }));
  v.innerHTML = '';
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Kind', 'Items', 'Direction', 'Total', 'Status', ''], rows.map(o => [
    `<span class="badge ${o.kind === 'medicine' ? 'copper' : 'primary'}">${o.kind}</span>`, (o.items || []).map(i => i.name).join(', '),
    o.direction, money(o.total), statusBadge(o.status), btn('Track', 'sm', () => openOrder(o.id)),
  ]), 'No orders yet.'));
  v.appendChild(c);
};
V.goals = async () => {
  setTitle('Goals', [btn('New goal', 'primary', newGoal)]);
  const v = view(); v.appendChild(skeletonRow(1));
  const rows = await api('/mgmt/goals?' + q({ org: S.org }));
  v.innerHTML = '';
  if (!rows.length) { v.appendChild(empty('No goals set. Add one for a member or patient.')); return; }
  const g = el('div', 'grid cols-2');
  rows.forEach(x => {
    const card = el('div', 'card');
    card.innerHTML = `<div class="row between"><b>${x.title}</b>${statusBadge(x.status)}</div>
      <div class="muted small" style="margin-top:4px">${x.metric ? x.metric + (x.target != null ? ' → ' + x.target : '') : 'No metric'}</div>`;
    if (x.pct != null) {
      const bar = el('div'); bar.style.cssText = 'height:8px;border-radius:5px;background:var(--surface-2);margin-top:12px;overflow:hidden';
      bar.innerHTML = `<div style="height:100%;width:${x.pct}%;background:var(--primary)"></div>`;
      card.appendChild(bar); card.appendChild(el('div', 'small muted', `${x.pct}% · now ${x.current ?? '—'}`));
    }
    g.appendChild(card);
  });
  v.appendChild(g);
};
V.config = async () => {
  setTitle('Modules & catalog', []);
  const v = view(); v.appendChild(skeletonRow(1));
  const o = await api('/mgmt/overview?' + q({ org: S.org }));
  v.innerHTML = '';
  // modules
  const mc = el('div', 'card');
  mc.appendChild(el('h3', null, 'Modules')); mc.appendChild(el('div', 'small muted', 'Turn parts of the console on or off for this centre.'));
  const grid = el('div', 'grid cols-3'); grid.style.marginTop = '12px';
  Object.entries(o.available_modules).forEach(([k, label]) => {
    const on = o.modules[k]; const chip = el('div', 'chip' + (on ? ' on' : ''), label);
    chip.onclick = async () => { await api('/mgmt/config', { method: 'POST', body: { org: S.org, modules: { [k]: !on } } }); toast('Updated'); V.config(); };
    grid.appendChild(chip);
  });
  mc.appendChild(grid); v.appendChild(mc);
  // catalog kinds
  const kinds = { service_type: 'Services / therapies', membership_plan: 'Membership plans', resource: 'Rooms / resources', role: 'Staff roles', note_template: 'Note templates' };
  for (const [kind, label] of Object.entries(kinds)) {
    const items = await api('/mgmt/catalog?' + q({ org: S.org, kind }));
    const c = el('div', 'card'); c.style.marginTop = '16px';
    c.appendChild(el('div', 'row between center', `<h3>${label}</h3>`));
    const add = btn('Add', 'sm', () => newCatalog(kind, label)); c.querySelector('.row').appendChild(add);
    c.appendChild(tableOf(['Name', 'Details', ''], items.map(it => [
      `<b>${it.name}</b>`, catalogDetail(kind, it.data), btn('Edit', 'ghost sm', () => newCatalog(kind, label, it)),
    ]), 'None yet — add one.'));
    v.appendChild(c);
  }
  // custom fields
  const fc = el('div', 'card'); fc.style.marginTop = '16px';
  fc.appendChild(el('h3', null, 'Custom fields'));
  fc.appendChild(el('div', 'small muted', 'Add fields to member / patient / service / booking / clinical-note forms.'));
  const efg = el('div', 'row wrap'); efg.style.marginTop = '10px';
  ['member', 'patient', 'service', 'booking', 'clinical_note'].forEach(e => { const b = btn(`${e} (${o.custom_field_entities[e] || 0})`, 'sm', () => newField(e)); efg.appendChild(b); });
  fc.appendChild(efg); v.appendChild(fc);
};
V.interop = async () => {
  setTitle('Integrations', [btn('New API key', 'primary', newKey), btn('Add webhook', '', newHook)]);
  const v = view();
  const keys = await api('/mgmt/api-keys?' + q({ org: S.org })).catch(() => []);
  const hooks = await api('/mgmt/webhooks?' + q({ org: S.org })).catch(() => []);
  v.innerHTML = '';
  v.appendChild(infoCard('Open by design', 'Export patients as FHIR (Patient / Observation / Bundle) for an EHR, issue scoped API keys, and register webhooks so your existing hospital systems stay in sync.'));
  const fc = el('div', 'card'); fc.style.marginTop = '16px'; fc.appendChild(el('h3', null, 'FHIR export'));
  fc.appendChild(el('div', 'row', '')); fc.querySelector('.row').append(linkBtn('Patient', S.api + '/interop/fhir/Patient'), linkBtn('Full Bundle', S.api + '/interop/fhir/Bundle'));
  v.appendChild(fc);
  const kc = el('div', 'card'); kc.style.marginTop = '16px'; kc.appendChild(el('h3', null, 'API keys'));
  kc.appendChild(tableOf(['Name', 'Prefix', 'Scopes', ''], keys.map(k => [k.name, k.prefix + '…', (k.scopes || []).join(', '), k.active ? btn('Revoke', 'danger sm', () => revokeKey(k.id)) : statusBadge('revoked')]), 'No keys yet.'));
  v.appendChild(kc);
  const hc = el('div', 'card'); hc.style.marginTop = '16px'; hc.appendChild(el('h3', null, 'Webhooks'));
  hc.appendChild(tableOf(['URL', 'Events', ''], hooks.map(h => [h.url, (h.events || []).join(', '), statusBadge(h.active ? 'active' : 'off')]), 'No webhooks yet.'));
  v.appendChild(hc);
};

// ---- views (doctor) ----
V.inbox = async () => {
  setTitle('Inbox', [btn('New task', 'primary', newTask)]);
  const v = view(); v.appendChild(skeletonRow(3));
  const d = await api('/mgmt/clinic/inbox?' + q({ org: S.org }));
  v.innerHTML = '';
  v.appendChild(kpis([['Patients', (d.patients || []).length, 'on your panel'], ['Open tasks', (d.open_tasks || []).length, ''], ['Care queue', (d.care_queue || []).length, 'awaiting review']]));
  const tc = el('div', 'card'); tc.style.marginTop = '18px'; tc.appendChild(el('h3', null, 'Open tasks'));
  tc.appendChild(tableOf(['Task', 'Priority', ''], (d.open_tasks || []).map(t => [t.text, ['', 'Low', 'Normal', 'High'][t.priority] || '', btn('Done', 'sm', () => completeTask(t.id))]), 'Inbox zero.'));
  v.appendChild(tc);
  if ((d.care_queue || []).length) { const cc = el('div', 'card'); cc.style.marginTop = '16px'; cc.appendChild(el('h3', null, 'Care review queue')); cc.appendChild(tableOf(['Finding', ''], d.care_queue.map(c => [c.title, statusBadge('awaiting')]), '')); v.appendChild(cc); }
};
V.patients = async () => {
  setTitle('Patients', [btn('Intake patient', 'primary', doctorIntake)]);
  const v = view(); v.appendChild(skeletonRow(1));
  const [panel, centres] = await Promise.all([api('/mgmt/doctor/patients'), api('/mgmt/doctor/centres')]);
  S._centres = centres;
  v.innerHTML = '';
  v.appendChild(el('p', 'muted small', 'Your panel. Intake a new patient, chart them, and assign them to a wellness centre for therapy delivery.'));
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Name', 'Age', 'Sex', 'City', ''], (panel || []).map(p => [`<b>${p.name || ('#' + p.id)}</b>`, p.age ? Math.round(p.age) : '—', p.sex || '—', p.city || '—',
    spanActions([btn('Chart', 'sm', () => openChart(p.id, p.name)), btn('→ Centre', 'sm', () => assignCentre(p.id))])]), 'No patients yet — intake one.'));
  v.appendChild(c);
};
function spanActions(btns) { const d = el('div', 'row'); btns.forEach(b => d.appendChild(b)); return d; }
async function doctorIntake() {
  const centres = S._centres || await api('/mgmt/doctor/centres');
  const node = formNode([
    { key: 'name', label: 'Full name', type: 'text', required: true },
    { key: 'age', label: 'Age', type: 'number' }, { key: 'sex', label: 'Sex', type: 'select', options: ['male', 'female'] },
    { key: 'city', label: 'City', type: 'text' },
    { key: 'org', label: 'Refer to centre (optional)', type: 'select', options: centres.map(c => ({ value: c.slug, label: c.name })) },
  ]);
  drawer('Intake patient', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Intake', kind: 'primary', onClick: async () => {
    const v = readForm(node); if (!v.name) { toast('Name is required.'); return; }
    try { await api('/mgmt/patients/onboard', { method: 'POST', body: { name: v.name, age: v.age ?? null, sex: v.sex || null, city: v.city || '', org: v.org || null } }); closeDrawer(); toast('Patient intaken'); V.patients(); } catch (e) { toast(e.message); }
  } }]);
}
async function assignCentre(pid) {
  const centres = S._centres || await api('/mgmt/doctor/centres');
  if (!centres.length) { toast('You are not affiliated with any centre yet.'); return; }
  const node = formNode([{ key: 'org', label: 'Centre', type: 'select', options: centres.map(c => ({ value: c.slug, label: c.name })), required: true },
    { key: 'note', label: 'Referral note (optional)', type: 'textarea' }]);
  drawer('Assign to centre', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Assign', kind: 'primary', onClick: async () => {
    const v = readForm(node); if (!v.org) { toast('Pick a centre.'); return; }
    try { await api('/mgmt/assign/centre', { method: 'POST', body: { patient_id: pid, org: v.org, note: v.note || '' } }); closeDrawer(); toast('Assigned to centre'); } catch (e) { toast(e.message); }
  } }]);
}
V.tasks = async () => {
  setTitle('Tasks', [btn('New task', 'primary', newTask)]);
  const v = view(); const rows = await api('/mgmt/clinic/tasks?' + q({ org: S.org })); v.innerHTML = '';
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Task', 'Due', 'Priority', ''], rows.map(t => [t.text, t.due || '—', ['', 'Low', 'Normal', 'High'][t.priority], btn('Done', 'sm', () => completeTask(t.id))]), 'No open tasks.'));
  v.appendChild(c);
};
V.orders = async () => { S.ws = 'centre'; return V.fulfillment(); };
V.templates = async () => {
  setTitle('Note templates', [btn('Add template', 'primary', () => newCatalog('note_template', 'Note template'))]);
  const v = view(); const t = await api('/mgmt/clinic/templates?' + q({ org: S.org })); v.innerHTML = '';
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Name', 'Sections', ''], t.map(x => [`<b>${x.name}</b>`, (x.data.sections || []).map(s => s.title).join(' · '), '']), 'No templates.'));
  v.appendChild(c);
};
// ======================= PLATFORM (super-admin) =======================
V.overview = async () => {
  setTitle('Network overview');
  const v = view(); const d = await api('/mgmt/admin/overview');
  v.appendChild(kpis([['Centres', d.centres], ['Doctors', d.doctors], ['People', d.patients], ['Network revenue', money(d.total_revenue)]]));
  const c = el('div', 'card table-card'); c.style.marginTop = '16px';
  c.appendChild(tableOf(['Centre', 'City', 'Status', 'People', 'Staff', 'Revenue', 'Outstanding'],
    (d.rows || []).map(r => [`<b>${r.name}</b><div class="small muted">${r.slug}</div>`, r.city || '—', statusBadge(r.status),
      r.patients, r.staff, money(r.revenue), r.outstanding ? `<span class="badge warn">${money(r.outstanding)}</span>` : '—']),
    'No centres yet — onboard one from Centres.'));
  v.appendChild(c);
};
V.centres = async () => {
  setTitle('Centres', [btn('Onboard centre', 'primary', newCentre)]);
  const v = view(); const rows = await api('/mgmt/admin/centres');
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Centre', 'Slug', 'City', 'Status', ''], rows.map(r => [`<b>${r.name}</b>`, r.slug, r.city || '—', statusBadge(r.status),
    btn(r.status === 'active' ? 'Suspend' : 'Activate', 'sm' + (r.status === 'active' ? ' danger' : ''), () => setCentreStatus(r.slug, r.status === 'active' ? 'suspended' : 'active'))]), 'No centres yet.'));
  v.appendChild(c);
};
V.doctors = async () => {   // shared name: platform lists all doctors; centre lists its affiliated doctors
  if (S.ws === 'platform') {
    setTitle('Doctors', [btn('Onboard doctor', 'primary', newDoctor)]);
    const v = view(); const all = await api('/mgmt/admin/staff');
    const docs = all.filter(s => ['doctor', 'clinic_admin'].includes(s.role));
    const c = el('div', 'card table-card');
    c.appendChild(tableOf(['Doctor', 'Email', 'Role', 'Centre', 'Status'], docs.map(s => [`<b>${s.name}</b>`, s.email, s.label, s.org, s.active ? '<span class="badge ok">active</span>' : '<span class="badge">off</span>']), 'No doctors yet.'));
    v.appendChild(c); return;
  }
  // centre workspace: affiliated doctors (super-admin affiliates them)
  setTitle('Affiliated doctors');
  const v = view(); const docs = await api('/mgmt/centre/doctors?' + q({ org: S.org }));
  v.appendChild(el('p', 'muted small', 'Doctors affiliated to your centre. Patients can be assigned to them. New doctors are onboarded by the Telomy super-admin.'));
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Doctor', 'Email', 'Specialty'], docs.map(s => [`<b>${s.name}</b>`, s.email, (s.profile || {}).specialty || '—']), 'No affiliated doctors yet.'));
  v.appendChild(c);
};
V.people = async () => {    // shared name: platform = all people by centre; centre = its members/patients
  if (S.ws === 'platform') {
    setTitle('People');
    const v = view(); const d = await api('/mgmt/admin/overview');
    v.appendChild(el('p', 'muted small', 'People are managed inside each centre and clinic. Totals by centre:'));
    const c = el('div', 'card table-card');
    c.appendChild(tableOf(['Centre', 'People'], (d.rows || []).map(r => [`<b>${r.name}</b>`, r.patients]), 'No people yet.'));
    v.appendChild(c); return;
  }
  setTitle('Members & patients', [btn('Onboard person', 'primary', newPerson)]);
  const v = view(); const [people, docs] = await Promise.all([api('/mgmt/centre/people?' + q({ org: S.org })), api('/mgmt/centre/doctors?' + q({ org: S.org }))]);
  S._docs = docs;
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Name', 'Age', 'Sex', 'City', 'Doctor', ''], people.map(p => [`<b>${p.name}</b>`, p.age ? Math.round(p.age) : '—', p.sex || '—', p.city || '—',
    p.doctor ? p.doctor : '<span class="faint">unassigned</span>', btn(p.doctor ? 'Reassign' : 'Assign doctor', 'sm', () => assignDoctor(p.id))]), 'No members yet — onboard one.'));
  v.appendChild(c);
};
V.therapies = async () => {
  setTitle('Therapies', [btn('Add therapy', 'primary', () => newCatalog('service_type', 'Therapy / service'))]);
  const v = view(); const [items, staff] = await Promise.all([api('/mgmt/catalog?' + q({ org: S.org, kind: 'service_type' })), api('/mgmt/staff?' + q({ org: S.org }))]);
  await renderResourceList(v, items, 'service', staff, 'therapists');
};
V.machines = async () => {
  setTitle('Machines & rooms', [btn('Add machine / room', 'primary', () => newCatalog('resource', 'Machine / room'))]);
  const v = view(); const [items, staff] = await Promise.all([api('/mgmt/catalog?' + q({ org: S.org, kind: 'resource' })), api('/mgmt/staff?' + q({ org: S.org }))]);
  await renderResourceList(v, items, 'resource', staff, 'operators');
};
V.performance = async () => {
  setTitle('Staff performance');
  const v = view(); const rows = await api('/mgmt/centre/performance?' + q({ org: S.org }));
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Staff', 'Role', 'Delivered', 'No-show', 'Revenue'], rows.map(r => [
    `<b>${r.name}</b>`, r.label || r.role, r.delivered, r.no_show || 0, money(r.revenue)]), 'No staff activity yet.'));
  v.appendChild(c);
  v.appendChild(el('p', 'muted small', 'Delivered sessions and revenue are computed from the booking ledger — no separate bookkeeping.'));
};
V.revenue = async () => {
  setTitle('Revenue');
  const v = view(); const d = await api('/mgmt/centre/revenue?' + q({ org: S.org }));
  v.appendChild(kpis([['Total revenue', money(d.total_revenue)], ['Sessions', money(d.session_revenue), `${d.sessions_delivered} delivered`],
    ['Orders', money(d.orders_value), `${d.orders_n} orders`], ['Outstanding', money(d.outstanding)]]));
  v.appendChild(el('p', 'muted small', 'One app runs the whole centre — scheduling, memberships, fulfilment and billing roll into a single revenue view.'));
};
// a therapy/machine card list with an "assign delivering staff" drawer
async function renderResourceList(v, items, dutyKind, staff, who) {
  const delivering = staff.filter(s => s.delivers);
  const allDuties = await api('/mgmt/duties?' + q({ org: S.org }));
  const dutyMap = {};
  items.forEach(it => { dutyMap[it.id] = allDuties.filter(d => d.duty_kind === dutyKind && d.ref_id === it.id); });
  const grid = el('div', 'grid cols-2');
  items.forEach(it => {
    const assigned = (dutyMap[it.id] || []).map(d => d.staff_id);
    const names = delivering.filter(s => assigned.includes(s.id)).map(s => s.name);
    const card = el('div', 'card');
    card.innerHTML = `<div class="row between center"><b>${it.name}</b>${it.data?.price ? `<span class="badge primary">${money(it.data.price)}</span>` : ''}</div>
      <div class="small muted" style="margin:6px 0">${it.data?.minutes ? it.data.minutes + ' min · ' : ''}${names.length ? who + ': ' + names.join(', ') : 'No ' + who + ' assigned'}</div>`;
    card.appendChild(btn('Assign ' + who, 'sm', () => assignDuty(it, dutyKind, delivering, assigned, who)));
    grid.appendChild(card);
  });
  v.appendChild(items.length ? grid : empty('None yet — add one.'));
}
async function assignDuty(item, dutyKind, delivering, assigned, who) {
  const node = el('div'); node.innerHTML = `<p class="muted small">Choose which ${who} can run <b>${item.name}</b>.</p>`;
  const state = new Set(assigned);
  delivering.forEach(s => {
    const row = el('label', 'row center'); row.style.margin = '6px 0'; row.style.cursor = 'pointer';
    const cb = el('input'); cb.type = 'checkbox'; cb.style.width = 'auto'; cb.checked = state.has(s.id);
    cb.onchange = () => { cb.checked ? state.add(s.id) : state.delete(s.id); };
    row.appendChild(cb); row.appendChild(el('span', null, `&nbsp; ${s.name} <span class="faint small">· ${s.label}</span>`));
    node.appendChild(row);
  });
  drawer('Assign ' + who, node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Save', kind: 'primary', onClick: async () => {
    try {
      for (const s of delivering) {
        const now = state.has(s.id), was = assigned.includes(s.id);
        if (now && !was) await api('/mgmt/duties', { method: 'POST', body: { org: S.org, staff_id: s.id, duty_kind: dutyKind, ref_id: item.id } });
        if (!now && was) await api('/mgmt/duties?' + q({ org: S.org, staff_id: s.id, duty_kind: dutyKind, ref_id: item.id }), { method: 'DELETE' });
      }
      closeDrawer(); toast('Saved'); route();
    } catch (e) { toast(e.message); }
  } }]);
}
V.staff = async () => {
  if (!S.me || !S.me.admin) { setTitle('Team & access'); view().appendChild(empty('Admins only.')); return; }
  setTitle('Team & access', [btn('Add staff', 'primary', newStaff)]);
  const v = view();
  const [rows, status] = await Promise.all([api('/mgmt/staff?' + q({ org: S.org })), api('/mgmt/auth/status')]);
  S._roles = status.roles || {};
  v.innerHTML = '';
  v.appendChild(el('p', 'muted small', 'Centre and Doctor sides sign in separately. Add doctors and clinic admins for the Doctor side; centre admins and front-desk staff for the Centre side.'));
  const c = el('div', 'card table-card');
  c.appendChild(tableOf(['Name', 'Email', 'Role', 'Status', ''], rows.map(s => [
    `<b>${s.name}</b>`, s.email, `<span class="badge ${ (S._roles[s.role]?.workspace) === 'doctor' ? 'primary' : 'copper'}">${s.label}</span>`,
    s.active ? '<span class="badge ok">active</span>' : '<span class="badge">disabled</span>',
    s.id === S.me.staff_id ? '<span class="small muted">you</span>' : btn(s.active ? 'Disable' : 'Enable', 'sm' + (s.active ? ' danger' : ''), () => toggleStaff(s.id, !s.active)),
  ]), 'No staff yet.'));
  v.appendChild(c);
};

// ---- actions ----
async function newStaff() {
  const roles = S._roles || {};
  // an admin can only create roles in their own workspace (platform super-admins use Onboard centre/doctor instead)
  const roleOpts = Object.entries(roles).filter(([k, v]) => v.workspace === S.me.workspace && k !== 'super_admin')
    .map(([k, v]) => ({ value: k, label: v.label }));
  const node = formNode([
    { key: 'name', label: 'Full name', type: 'text', required: true },
    { key: 'email', label: 'Email (their login)', type: 'text', required: true },
    { key: 'role', label: 'Role', type: 'select', options: roleOpts, required: true },
    { key: 'password', label: 'Temporary password (8+ chars)', type: 'text', required: true },
  ]);
  drawer('Add staff', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Create account', kind: 'primary', onClick: async () => {
    const v = readForm(node);
    if (!v.name || !v.email || !v.role || !(v.password || '').length) { toast('All fields are required.'); return; }
    try { await api('/mgmt/staff', { method: 'POST', body: { org: S.org, role: v.role, name: v.name, email: v.email, password: String(v.password) } }); closeDrawer(); toast('Staff account created'); V.staff(); } catch (e) { toast(e.message); }
  } }]);
}
async function toggleStaff(id, active) {
  try { await api(`/mgmt/staff/${id}/active`, { method: 'POST', body: { active } }); toast(active ? 'Enabled' : 'Disabled'); V.staff(); } catch (e) { toast(e.message); }
}
// ---- platform (super-admin) actions ----
function newCentre() {
  const node = formNode([
    { key: 'name', label: 'Centre name', type: 'text', required: true },
    { key: 'city', label: 'City', type: 'text' },
    { key: 'admin_name', label: "Centre admin's name", type: 'text' },
    { key: 'admin_email', label: "Admin login email", type: 'text' },
    { key: 'admin_password', label: 'Temporary password (8+ chars)', type: 'text' },
  ]);
  drawer('Onboard centre', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Onboard', kind: 'primary', onClick: async () => {
    const v = readForm(node); if (!v.name) { toast('Name is required.'); return; }
    try { await api('/mgmt/admin/centres', { method: 'POST', body: { name: v.name, city: v.city || '', admin_name: v.admin_name || '', admin_email: v.admin_email || '', admin_password: v.admin_password ? String(v.admin_password) : '' } }); closeDrawer(); toast('Centre onboarded'); V.centres(); } catch (e) { toast(e.message); }
  } }]);
}
async function setCentreStatus(slug, status) {
  try { await api(`/mgmt/admin/centres/${slug}/status`, { method: 'POST', body: { status } }); toast('Updated'); V.centres(); } catch (e) { toast(e.message); }
}
async function newDoctor() {
  const centres = await api('/mgmt/admin/centres');
  const node = formNode([
    { key: 'name', label: 'Doctor name', type: 'text', required: true },
    { key: 'email', label: 'Login email', type: 'text', required: true },
    { key: 'password', label: 'Temporary password (8+ chars)', type: 'text', required: true },
    { key: 'org', label: 'Affiliate to centre (optional)', type: 'select', options: [{ value: '', label: 'Independent' }, ...centres.map(c => ({ value: c.slug, label: c.name }))] },
    { key: 'clinic_admin', label: 'Clinic admin (manages the clinic)?', type: 'bool' },
  ]);
  drawer('Onboard doctor', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Onboard', kind: 'primary', onClick: async () => {
    const v = readForm(node); if (!v.name || !v.email || !v.password) { toast('Name, email and password are required.'); return; }
    try { await api('/mgmt/admin/doctors', { method: 'POST', body: { name: v.name, email: v.email, password: String(v.password), org: v.org || null, clinic_admin: v.clinic_admin === 'Yes' } }); closeDrawer(); toast('Doctor onboarded'); V.doctors(); } catch (e) { toast(e.message); }
  } }]);
}
// ---- centre: onboard a person & assign to a doctor ----
async function newPerson() {
  const docs = S._docs || await api('/mgmt/centre/doctors?' + q({ org: S.org }));
  const node = formNode([
    { key: 'name', label: 'Full name', type: 'text', required: true },
    { key: 'age', label: 'Age', type: 'number' }, { key: 'sex', label: 'Sex', type: 'select', options: ['male', 'female'] },
    { key: 'city', label: 'City', type: 'text' },
    { key: 'doctor_id', label: 'Assign to doctor (optional)', type: 'select', options: docs.map(d => ({ value: d.id, label: d.name })) },
  ]);
  drawer('Onboard person', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Onboard', kind: 'primary', onClick: async () => {
    const v = readForm(node); if (!v.name) { toast('Name is required.'); return; }
    try { await api('/mgmt/patients/onboard', { method: 'POST', body: { name: v.name, age: v.age ?? null, sex: v.sex || null, city: v.city || '', doctor_id: v.doctor_id ? Number(v.doctor_id) : null } }); closeDrawer(); toast('Onboarded'); V.people(); } catch (e) { toast(e.message); }
  } }]);
}
async function assignDoctor(pid) {
  const docs = S._docs || await api('/mgmt/centre/doctors?' + q({ org: S.org }));
  if (!docs.length) { toast('No affiliated doctors yet — ask the super-admin to add one.'); return; }
  const node = formNode([{ key: 'doctor_id', label: 'Doctor', type: 'select', options: docs.map(d => ({ value: d.id, label: `${d.name} · ${d.label || 'Doctor'}` })), required: true },
    { key: 'note', label: 'Note (optional)', type: 'text' }]);
  drawer('Assign doctor', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Assign', kind: 'primary', onClick: async () => {
    const v = readForm(node); if (!v.doctor_id) { toast('Pick a doctor.'); return; }
    try { await api('/mgmt/assign/doctor', { method: 'POST', body: { patient_id: pid, doctor_id: Number(v.doctor_id), note: v.note || '' } }); closeDrawer(); toast('Assigned'); V.people(); } catch (e) { toast(e.message); }
  } }]);
}
async function newMember() {
  const schema = await api('/mgmt/form?' + q({ org: S.org, entity: 'member' }));
  const base = [{ key: 'name', label: 'Full name', type: 'text', required: true }, { key: 'phone', label: 'Phone', type: 'text' }, { key: 'email', label: 'Email', type: 'text' }];
  const custom = schema.sections.flatMap(s => s.fields);
  const node = formNode([...base, ...custom]);
  drawer('Add member', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Add member', kind: 'primary', onClick: async () => {
    const vals = readForm(node); const fields = {}; custom.forEach(f => { if (vals[f.key] != null) { fields[f.key] = vals[f.key]; delete vals[f.key]; } });
    try { await api('/mgmt/centre/members', { method: 'POST', body: { org: S.org, ...vals, fields } }); closeDrawer(); toast('Member added'); V.members(); } catch (e) { toast(e.message); }
  } }]);
}
async function openMember(id) {
  const m = await api('/mgmt/centre/members/' + id);
  const plans = await api('/mgmt/catalog?' + q({ org: S.org, kind: 'membership_plan' }));
  const node = el('div');
  node.innerHTML = `<div class="row between center"><h3 style="margin:0">${m.name}</h3>${statusBadge(m.status)}</div>
    <div class="muted small" style="margin:4px 0 16px">${m.phone || ''} ${m.email ? '· ' + m.email : ''} · joined ${m.joined_on}</div>`;
  const ms = el('div'); ms.innerHTML = '<div class="section-title">Memberships</div>';
  (m.memberships || []).forEach(x => ms.appendChild(el('div', 'card pad-sm', `<div class="row between"><b>${x.data.plan || 'Plan'}</b>${x.credits_left != null ? `<span class="badge primary">${x.credits_left} credits</span>` : statusBadge(x.status)}</div><div class="small muted">until ${x.ends_on}</div>`)));
  node.appendChild(ms);
  const enroll = el('div'); enroll.style.marginTop = '14px'; enroll.innerHTML = '<div class="section-title">Enroll in a plan</div>';
  const sel = el('select'); plans.forEach(p => { const o = el('option', null, `${p.name} · ${money(p.data.price)}`); o.value = p.id; sel.appendChild(o); });
  enroll.appendChild(sel); const eb = btn('Enroll', 'primary sm', async () => { try { await api(`/mgmt/centre/members/${id}/enroll`, { method: 'POST', body: { org: S.org, plan_id: Number(sel.value) } }); toast('Enrolled'); openMember(id); } catch (e) { toast(e.message); } });
  eb.style.marginTop = '8px'; enroll.appendChild(eb); node.appendChild(enroll);
  drawer('Member', node, [{ label: 'Close', onClick: closeDrawer }]);
}
async function newBooking() {
  const [members, services] = await Promise.all([api('/mgmt/centre/members?' + q({ org: S.org })), api('/mgmt/catalog?' + q({ org: S.org, kind: 'service_type' }))]);
  const node = el('div');
  const mSel = selectOf('Member', members.map(m => [m.id, m.name]));
  const sSel = selectOf('Service', services.map(s => [s.id, `${s.name} · ${s.data.minutes || 60}m · ${money(s.data.price)}`]));
  const when = labeled('When', inputEl('datetime-local'));
  const room = labeled('Room / resource #', inputEl('number'));
  [mSel.wrap, sSel.wrap, when.wrap, room.wrap].forEach(n => node.appendChild(n));
  drawer('New booking', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Book', kind: 'primary', onClick: async () => {
    try { await api('/mgmt/centre/book', { method: 'POST', body: { org: S.org, member_id: Number(mSel.input.value), service_id: Number(sSel.input.value), start_ts: when.input.value + ':00', resource_id: room.input.value ? Number(room.input.value) : null } }); closeDrawer(); toast('Booked'); route(); } catch (e) { toast(e.message); }
  } }]);
}
async function checkIn(id) { try { await api(`/mgmt/centre/bookings/${id}/checkin`, { method: 'POST' }); toast('Checked in'); route(); } catch (e) { toast(e.message); } }
async function setBookingStatus(id, status) { try { await api(`/mgmt/centre/bookings/${id}/status`, { method: 'POST', body: { status } }); toast('Updated'); route(); } catch (e) { toast(e.message); } }
async function newOrder() {
  const node = el('div');
  const kind = selectOf('Kind', [['supplement', 'Supplement'], ['medicine', 'Medicine (needs signed Rx)'], ['retail', 'Retail'], ['device', 'Device']]);
  const name = labeled('Item name', inputEl('text')); const price = labeled('Price', inputEl('number')); const addr = labeled('Delivery address', inputEl('text'));
  [kind.wrap, name.wrap, price.wrap, addr.wrap].forEach(n => node.appendChild(n));
  drawer('New order', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Create', kind: 'primary', onClick: async () => {
    try { await api('/mgmt/orders', { method: 'POST', body: { org: S.org, kind: kind.input.value, items: [{ name: name.input.value, qty: 1, price: Number(price.input.value || 0) }], address: addr.input.value } }); closeDrawer(); toast('Order created'); V.fulfillment(); } catch (e) { toast(e.message); }
  } }]);
}
async function newPickup() {
  const node = el('div'); const pid = labeled('Patient id', inputEl('number')); const tests = labeled('Tests (comma-separated)', inputEl('text')); const addr = labeled('Address', inputEl('text')); const slot = labeled('Slot', inputEl('datetime-local'));
  [pid.wrap, tests.wrap, addr.wrap, slot.wrap].forEach(n => node.appendChild(n));
  drawer('Schedule sample pickup', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Book pickup', kind: 'primary', onClick: async () => {
    try { await api('/mgmt/sample-pickup', { method: 'POST', body: { org: S.org, patient_id: Number(pid.input.value), tests: tests.input.value.split(',').map(s => s.trim()).filter(Boolean), address: addr.input.value, slot: slot.input.value } }); closeDrawer(); toast('Pickup booked'); V.fulfillment(); } catch (e) { toast(e.message); }
  } }]);
}
async function openOrder(id) {
  const o = await api('/mgmt/orders/' + id); const node = el('div');
  node.innerHTML = `<div class="row between"><b>${o.kind}</b>${statusBadge(o.status)}</div><div class="muted small">${(o.items || []).map(i => i.name).join(', ')} · ${money(o.total)}</div>`;
  const tl = el('div'); tl.style.marginTop = '14px'; tl.innerHTML = '<div class="section-title">Track</div>';
  o.flow.forEach(st => { const done = o.events.some(e => e.status === st); tl.appendChild(el('div', 'row center', `<span class="dot-status" style="background:${done ? 'var(--primary)' : 'var(--border-2)'}"></span>&nbsp;<span class="${done ? '' : 'muted'}">${st.replace(/_/g, ' ')}</span>`)); });
  node.appendChild(tl);
  const next = o.flow[o.flow.indexOf(o.status) + 1];
  drawer('Order', node, [{ label: 'Close', onClick: closeDrawer }, ...(next && next !== 'cancelled' ? [{ label: 'Mark ' + next.replace(/_/g, ' '), kind: 'primary', onClick: async () => { await api(`/mgmt/orders/${id}/advance`, { method: 'POST', body: { status: next } }); toast('Updated'); openOrder(id); V.fulfillment(); } }] : [])]);
}
async function newGoal() {
  const node = el('div'); const title = labeled('Goal', inputEl('text')); const metric = labeled('Metric (e.g. rhr, ldl, weight)', inputEl('text')); const target = labeled('Target', inputEl('number'));
  [title.wrap, metric.wrap, target.wrap].forEach(n => node.appendChild(n));
  drawer('New goal', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Add goal', kind: 'primary', onClick: async () => {
    try { await api('/mgmt/goals', { method: 'POST', body: { org: S.org, title: title.input.value, metric: metric.input.value || null, target: target.input.value ? Number(target.input.value) : null } }); closeDrawer(); toast('Goal added'); V.goals(); } catch (e) { toast(e.message); }
  } }]);
}
async function newCatalog(kind, label, existing) {
  const node = el('div'); const name = labeled('Name', inputEl('text')); if (existing) name.input.value = existing.name;
  node.appendChild(name.wrap);
  const extra = {};
  const add = (k, l, t) => { const f = labeled(l, inputEl(t)); if (existing && existing.data[k] != null) f.input.value = existing.data[k]; node.appendChild(f.wrap); extra[k] = f.input; };
  if (kind === 'service_type') { add('minutes', 'Duration (min)', 'number'); add('price', 'Price', 'number'); add('category', 'Category', 'text'); }
  else if (kind === 'membership_plan') { add('price', 'Price', 'number'); add('cycle_days', 'Cycle (days)', 'number'); add('credits', 'Credits (blank = unlimited)', 'number'); }
  else if (kind === 'resource') { add('type', 'Type (room/device/chair)', 'text'); }
  else if (kind === 'role') { add('permissions', 'Permissions (comma)', 'text'); }
  drawer((existing ? 'Edit ' : 'Add ') + label, node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Save', kind: 'primary', onClick: async () => {
    const data = {}; Object.entries(extra).forEach(([k, i]) => { if (i.value !== '') data[k] = i.type === 'number' ? Number(i.value) : i.value; });
    try { if (existing) await api('/mgmt/catalog/' + existing.id, { method: 'POST', body: { name: name.input.value, data } }); else await api('/mgmt/catalog', { method: 'POST', body: { org: S.org, kind, name: name.input.value, data } }); closeDrawer(); toast('Saved'); if (location.hash.includes('config')) V.config(); else if (location.hash.includes('templates')) V.templates(); } catch (e) { toast(e.message); }
  } }]);
}
async function newField(entity) {
  const node = el('div'); const label = labeled('Field label', inputEl('text'));
  const type = selectOf('Type', ['text', 'number', 'select', 'bool', 'date', 'textarea', 'rating', 'money'].map(t => [t, t]));
  const opts = labeled('Options (comma, for select)', inputEl('text')); const req = selectOf('Required', [['false', 'No'], ['true', 'Yes']]);
  [label.wrap, type.wrap, opts.wrap, req.wrap].forEach(n => node.appendChild(n));
  drawer(`Add field to ${entity}`, node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Add field', kind: 'primary', onClick: async () => {
    try { await api('/mgmt/fields', { method: 'POST', body: { org: S.org, entity, label: label.input.value, type: type.input.value, options: opts.input.value ? opts.input.value.split(',').map(s => s.trim()) : [], required: req.input.value === 'true' } }); closeDrawer(); toast('Field added'); V.config(); } catch (e) { toast(e.message); }
  } }]);
}
async function openChart(pid, name) {
  const [notes, templates] = await Promise.all([api('/mgmt/clinic/patients/' + pid + '/notes'), api('/mgmt/clinic/templates?' + q({ org: S.org }))]);
  const node = el('div'); node.innerHTML = `<h3 style="margin:0 0 10px">${name || '#' + pid}</h3>`;
  const tSel = selectOf('Template', templates.map(t => [t.id, t.name])); node.appendChild(tSel.wrap);
  const fieldWrap = el('div'); node.appendChild(fieldWrap);
  const renderTpl = () => { const tpl = templates.find(t => t.id == tSel.input.value); fieldWrap.innerHTML = ''; (tpl?.data.sections || []).forEach(s => { const f = labeled(s.title, el('textarea')); f.input.dataset.key = s.key; fieldWrap.appendChild(f.wrap); }); };
  tSel.input.onchange = renderTpl; renderTpl();
  node.appendChild(el('div', 'section-title', 'Past notes'));
  notes.forEach(n => node.appendChild(el('div', 'card pad-sm', `<div class="row between"><b>${n.title || 'Note'}</b><span class="small muted">${fmtTime(n.ts)}</span></div><div class="small muted">${Object.values(n.content || {}).join(' · ').slice(0, 120)}</div>`)));
  drawer('Chart', node, [{ label: 'Close', onClick: closeDrawer }, { label: 'Save note', kind: 'primary', onClick: async () => {
    const content = {}; fieldWrap.querySelectorAll('[data-key]').forEach(i => { if (i.value) content[i.dataset.key] = i.value; });
    try { await api('/mgmt/clinic/patients/' + pid + '/notes', { method: 'POST', body: { org: S.org, author: 'Doctor', template_id: Number(tSel.input.value), content } }); closeDrawer(); toast('Note saved'); } catch (e) { toast(e.message); }
  } }]);
}
async function newTask() {
  const node = el('div'); const text = labeled('Task', inputEl('text')); const pr = selectOf('Priority', [[1, 'Low'], [2, 'Normal'], [3, 'High']]);
  [text.wrap, pr.wrap].forEach(n => node.appendChild(n));
  drawer('New task', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Add', kind: 'primary', onClick: async () => {
    try { await api('/mgmt/clinic/tasks', { method: 'POST', body: { org: S.org, text: text.input.value, priority: Number(pr.input.value) } }); closeDrawer(); toast('Task added'); route(); } catch (e) { toast(e.message); }
  } }]);
}
async function completeTask(id) { await api(`/mgmt/clinic/tasks/${id}/complete`, { method: 'POST' }); toast('Done'); route(); }
async function newKey() {
  const node = el('div'); const name = labeled('Name', inputEl('text')); node.appendChild(name.wrap);
  drawer('New API key', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Create', kind: 'primary', onClick: async () => {
    const r = await api('/mgmt/api-keys', { method: 'POST', body: { org: S.org, name: name.input.value, scopes: ['read', 'write'] } });
    node.innerHTML = `<p class="small">Copy this key now — it is shown only once:</p><div class="card pad-sm" style="word-break:break-all"><code>${r.key}</code></div>`;
    document.getElementById('drawerFoot').innerHTML = ''; document.getElementById('drawerFoot').appendChild(btn('Done', 'primary', () => { closeDrawer(); V.interop(); }));
  } }]);
}
async function revokeKey(id) { await api('/mgmt/api-keys/' + id, { method: 'DELETE' }); toast('Revoked'); V.interop(); }
async function newHook() {
  const node = el('div'); const url = labeled('URL', inputEl('text')); const ev = labeled('Events (comma, * = all)', inputEl('text')); ev.input.value = '*';
  [url.wrap, ev.wrap].forEach(n => node.appendChild(n));
  drawer('Add webhook', node, [{ label: 'Cancel', onClick: closeDrawer }, { label: 'Add', kind: 'primary', onClick: async () => {
    await api('/mgmt/webhooks', { method: 'POST', body: { org: S.org, url: url.input.value, events: ev.input.value.split(',').map(s => s.trim()) } }); closeDrawer(); toast('Webhook added'); V.interop();
  } }]);
}

// ---- small ui builders ----
function view() { const v = document.getElementById('view'); v.innerHTML = ''; return v; }
function setTitle(t, actions) { document.getElementById('pageTitle').textContent = t; const a = document.getElementById('pageActions'); a.innerHTML = ''; (actions || []).forEach(x => a.appendChild(x)); }
function btn(label, cls, onClick) { const b = el('button', 'btn ' + (cls || ''), label); b.onclick = onClick; return b; }
function linkBtn(label, href) { const a = el('a', 'btn sm', label); a.href = href; a.target = '_blank'; a.style.marginRight = '8px'; return a; }
function kpis(items) { const g = el('div', 'grid cols-4'); items.forEach(([label, val, sub]) => g.appendChild(el('div', 'kpi', `<div class="label">${label}</div><div class="val num">${val ?? '—'}</div><div class="sub">${sub || ''}</div>`))); return g; }
function tableOf(head, rows, emptyMsg) {
  if (!rows.length) return empty(emptyMsg || 'Nothing here yet.');
  const t = el('table'); const thead = el('thead'); const tr = el('tr'); head.forEach(h => tr.appendChild(el('th', null, h))); thead.appendChild(tr); t.appendChild(thead);
  const tb = el('tbody'); rows.forEach(r => { const row = el('tr'); r.forEach(c => { const td = el('td'); if (c instanceof Node) td.appendChild(c); else td.innerHTML = c; row.appendChild(td); }); tb.appendChild(row); }); t.appendChild(tb); return t;
}
function empty(msg) { return el('div', 'empty', msg); }
function skeletonRow(n) { const g = el('div', 'grid cols-4'); for (let i = 0; i < (n === 1 ? 4 : n); i++) { const c = el('div', 'kpi'); c.innerHTML = '<div class="skel" style="width:60%"></div><div class="skel" style="width:40%;height:24px;margin-top:8px"></div>'; g.appendChild(c); } return g; }
function infoCard(t, b) { return el('div', 'card', `<h3>${t}</h3><div class="muted small" style="margin-top:4px">${b}</div>`); }
function catalogDetail(kind, d) { if (kind === 'service_type') return `${d.minutes || 60} min · ${money(d.price)} · ${d.category || ''}`; if (kind === 'membership_plan') return `${money(d.price)} / ${d.cycle_days || 30}d · ${d.credits ? d.credits + ' credits' : 'unlimited'}`; if (kind === 'resource') return d.type || ''; if (kind === 'note_template') return (d.sections || []).map(s => s.title).join(' · '); return JSON.stringify(d); }
function inputEl(type) { const i = el('input'); i.type = type; return i; }
function labeled(label, input) { const w = el('label', 'field'); w.appendChild(el('span', null, label)); w.appendChild(input); return { wrap: w, input }; }
function selectOf(label, pairs) { const s = el('select'); pairs.forEach(([v, t]) => { const o = el('option', null, t); o.value = v; s.appendChild(o); }); return { ...labeled(label, s), input: s }; }

// ---- router ----
function route() {
  let [ws, page] = (location.hash.replace('#', '') || 'centre/dashboard').split('/');
  // a role may only enter a workspace it is allowed — doctor, centre and platform logins are separate
  if (S.allowedWs && !S.allowedWs.includes(ws)) { ws = S.me ? S.me.workspace : 'centre'; location.hash = `${ws}/${HOME[ws]}`; return; }
  S.ws = ws;
  renderNav();
  document.querySelectorAll('.nav a').forEach(a => a.classList.toggle('active', a.dataset.route === page));
  const fn = V[page] || V[HOME[S.ws]] || V.dashboard;
  fn().catch(e => { if (e.message !== 'unauthorised') view().appendChild(empty('Could not load: ' + e.message)); });
}
window.addEventListener('hashchange', route);
document.querySelectorAll('.ws-switch button').forEach(b => b.onclick = () => { location.hash = `${b.dataset.ws}/${b.dataset.ws === 'doctor' ? 'inbox' : 'dashboard'}`; });
document.getElementById('signout').onclick = async () => { try { await api('/mgmt/auth/logout', { method: 'POST' }); } catch (e) {} localStorage.removeItem('tc.token'); S.token = ''; S.me = null; location.reload(); };

// ---- auth / boot (separate Centre vs Doctor logins) ----
let SIGNUP = false;
function showLogin() {
  document.getElementById('app').hidden = true;
  const L = document.getElementById('login'); L.hidden = false;
  document.getElementById('srv').value = S.api;
  // populate roles + decide if this is the very first account (bootstrap)
  fetch(S.api + '/mgmt/auth/status').then(r => r.json()).then(st => {
    const sel = document.getElementById('suRole'); sel.innerHTML = '';
    Object.entries(st.roles || {}).forEach(([k, v]) => { const o = document.createElement('option'); o.value = k; o.textContent = v.label; sel.appendChild(o); });
    const tog = document.getElementById('toggleSignup');
    if (!st.has_staff) { tog.textContent = 'No accounts yet — create the first admin'; } else { tog.textContent = 'First time? Ask your admin to add you'; }
  }).catch(() => {});
}
document.getElementById('toggleSignup').onclick = () => {
  SIGNUP = !SIGNUP;
  document.getElementById('signupFields').hidden = !SIGNUP;
  document.getElementById('loginBtn').textContent = SIGNUP ? 'Create account' : 'Sign in';
  document.getElementById('loginSub').textContent = SIGNUP ? 'Create a staff account (first one is the admin).' : 'Sign in — the Centre and Doctor sides use separate accounts.';
  document.getElementById('toggleSignup').textContent = SIGNUP ? 'Have an account? Sign in' : 'First time? Create the first admin account';
};
document.getElementById('loginBtn').onclick = async () => {
  S.api = document.getElementById('srv').value.replace(/\/$/, '') || location.origin;
  const email = document.getElementById('email').value.trim(), pw = document.getElementById('pw').value;
  const err = document.getElementById('loginErr'); err.textContent = '';
  try {
    if (SIGNUP) {
      const body = { org: S.org, role: document.getElementById('suRole').value, name: document.getElementById('suName').value || email, email, password: pw };
      const r = await fetch(S.api + '/mgmt/auth/signup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!r.ok) { err.textContent = (await r.json()).detail || 'Could not create account.'; return; }
      SIGNUP = false; document.getElementById('toggleSignup').onclick();  // flip back to sign in
    }
    const r = await fetch(S.api + '/mgmt/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: pw }) });
    const j = await r.json();
    if (!r.ok) { err.textContent = j.detail || 'Sign in failed.'; return; }
    S.token = j.token; S.me = j;
    localStorage.setItem('tc.api', S.api); localStorage.setItem('tc.token', S.token);
    boot();
  } catch (e) { err.textContent = 'Could not reach the server.'; }
};
async function boot() {
  try {
    if (!S.me) S.me = await api('/mgmt/auth/me');          // resolve role from the staff token
    S.org = S.me.org || 'default';
    // one login == one workspace. Centre and Doctor sign in separately; the super-admin lives in the platform workspace.
    S.ws = S.me.workspace;
    S.allowedWs = [S.ws];
    if (S.ws === 'platform') {
      document.getElementById('orgName').textContent = 'Telomy · Network';
    } else {
      S.cfg = await api('/mgmt/overview?' + q({ org: S.org })).catch(() => null);
      document.getElementById('orgName').textContent = S.cfg?.branding?.name || (S.ws === 'doctor' ? 'Telomy Clinic' : 'Telomy Centre');
      const prim = S.cfg?.branding?.primary; if (prim) document.documentElement.style.setProperty('--primary', prim);
    }
    document.getElementById('apiHost').textContent = `${S.me.name} · ${S.me.label}`;
    document.querySelector('.ws-switch').style.display = 'none';  // no cross-workspace switching — roles are separate
    document.getElementById('login').hidden = true; document.getElementById('app').hidden = false;
    location.hash = `${S.ws}/${HOME[S.ws]}`; route();
  } catch (e) { S.me = null; showLogin(); }
}
boot();
