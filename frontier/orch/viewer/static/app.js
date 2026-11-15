'use strict';
const $ = s => document.querySelector(s);
const labels = {pending:'Pendiente',in_progress:'En curso',done:'Terminada',blocked:'Bloqueada',working:'Trabajando',cooldown:'Espera de cuota',idle:'Disponible',login:'Requiere acceso'};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge = status => `<span class="badge ${esc(status)}">${status==='working'?'● ':''}${esc(labels[status]||status)}</span>`;
const date = epoch => epoch ? new Date(epoch*1000).toLocaleString('es-ES',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Sin datos';
const ago = epoch => {if(!epoch)return 'Sin actividad registrada';const n=Math.max(0,Math.floor(Date.now()/1000-epoch));return n<60?'Hace unos segundos':n<3600?`Hace ${Math.floor(n/60)} min`:n<86400?`Hace ${Math.floor(n/3600)} h`:`Hace ${Math.floor(n/86400)} días`;};
const name = n => n==='any'?'Cualquier worker':n==='codex'?'Codex':n==='claude'?'Claude':n;
let controlKey = sessionStorage.getItem('frontier-control-key') || '', controlBusy = false;
let data = null, filter = 'open', selectedTask = null, lastGood = null, detailSignature = null;
function html(selector, value){const el=$(selector);if(el.innerHTML===value)return;const positions=[el,...el.querySelectorAll('.event-list,pre')].map(e=>e.scrollTop);el.innerHTML=value;[el,...el.querySelectorAll('.event-list,pre')].forEach((e,i)=>e.scrollTop=positions[i]||0);}
function route(){let p=location.hash.slice(1)||'overview';if(!['overview','queue','activity','tools'].includes(p))p='overview';document.querySelectorAll('.page').forEach(el=>el.hidden=el.id!==`page-${p}`);document.querySelectorAll('nav a').forEach(el=>el.classList.toggle('active',el.dataset.page===p));$('#crumb').textContent=({overview:'Vista general',queue:'Cola de tareas',activity:'Actividad',tools:'Herramientas'})[p];}
window.addEventListener('hashchange',route);
function renderWorkers(){
 html('#workers',data.workers.map(w=>{
 const e=w.events.filter(e=>e.kind!=='system').at(-1)||w.events.at(-1);
 const live=w.status==='working';
 const quota=w.status==='cooldown'?`Espera hasta ${date(w.cooldown_until)}`:w.status==='login'?'Inicio de sesión necesario':'Sin espera registrada';
 return `<article class="worker-card"><div class="worker-main"><div class="worker-top"><div class="avatar ${esc(w.name)}">${w.name==='codex'?'⌘':'✳'}</div><div><div class="worker-name">${name(w.name)}</div><div class="worker-meta">${esc(w.model||'Modelo no fijado en config')} · worker local</div></div>${badge(w.status)}</div><div class="worker-task"><span class="micro">${live?'TRABAJANDO AHORA':'ÚLTIMA TAREA REGISTRADA'}</span>${w.task_id?`<a href="#" data-task="${esc(w.task_id)}">${esc(w.task_title||w.task_id)}</a><div class="task-code">${esc(w.task_id)}</div>`:'<span class="caption">Todavía no hay ejecuciones.</span>'}</div><div class="worker-last"><span class="micro">${live?'ACTIVIDAD RECIENTE':'ÚLTIMA ACTIVIDAD · '+esc(ago(w.last_update))}</span><p>${esc(e?.text||'Sin eventos en el tramo reciente del log.')}</p></div></div><div class="worker-bottom"><span class="quota-date">${esc(quota)}</span><span>${live?`PID ${esc(w.pids.join(', '))}`:'Sin proceso activo'}</span></div></article>`;
 }).join(''));
}
function renderQueue(){
 const q=$('#search').value.toLowerCase();
 const tasks=data.tasks.filter(t=>(filter==='all'||filter==='open'&&t.status!=='done'||t.status===filter)&&`${t.id} ${t.title} ${t.owner} ${t.notes||''}`.toLowerCase().includes(q));
 $('#queue-count').textContent=`${tasks.length} de ${data.tasks.length} tareas`;
 html('#task-list',tasks.length?tasks.map(t=>`<button class="task-row" data-task="${esc(t.id)}"><span class="order">${String(t.order).padStart(2,'0')}</span><span><strong>${esc(t.title)}</strong><small>${esc(t.id)} · ${t.waiting_for.length?'Espera: '+esc(t.waiting_for.join(', ')):t.status==='done'?'Cerrada en el repositorio':t.status==='blocked'?'Necesita resolver el bloqueo':t.ready?'Dependencias cumplidas':'Sin dependencias pendientes'}</small></span><span>${badge(t.status)}</span><span class="owner">${esc(name(t.lane||t.owner))}</span><span class="arrow">↗</span></button>`).join(''):'<div class="panel empty">No hay tareas con este filtro.</div>');
}
function activity(){
 const kind={tool:'HERRAMIENTA',message:'MENSAJE DEL WORKER',file:'ARCHIVOS',error:'INCIDENCIA',system:'EJECUCIÓN'};
 html('#activity-workers',data.workers.map(w=>`<section class="panel"><div class="activity-head"><div class="avatar ${esc(w.name)}">${w.name==='codex'?'⌘':'✳'}</div><h2>${name(w.name)}</h2>${badge(w.status)}</div><div class="worker-bottom"><span>${esc(ago(w.last_update))}</span><span>${w.status==='working'?'En directo':'Última ejecución'}</span></div><div class="event-list">${w.events.length?[...w.events].reverse().map(e=>`<article class="event ${esc(e.kind)}"><div class="event-kind"><span>${kind[e.kind]||'EVENTO'}</span><span>${esc(e.status==='running'?'EN EJECUCIÓN':e.status==='failed'?'FALLO':e.status==='invoked'?'INVOCADA':'REGISTRADO')}</span></div><p>${esc(e.text)}</p></article>`).join(''):'<div class="empty">No hay eventos recientes.</div>'}</div></section>`).join(''));
 $('#supervisor-log').textContent=data.supervisor.events.join('\n')||'Todavía no hay eventos del supervisor.';
}
function render(){
 const c=data.counts, done=c.done||0, open=data.tasks.length-done, active=data.workers.filter(w=>w.status==='working').length;
 $('#nav-count').textContent=open;
 const alive=data.supervisor.running;
 html('#summary',`<article class="stat green"><span class="label">SUPERVISOR</span><span class="stat-mark">⌁</span><strong>${alive?(active?'En marcha':'A la espera'):'No detectado'}</strong><small>${alive?'Proceso local activo':'Sin proceso visible en este entorno'}</small></article><article class="stat"><span class="label">TAREAS TERMINADAS</span><span class="stat-mark">↗</span><strong>${done}<span class="muted"> / ${data.tasks.length}</span></strong><small>${open} tareas abiertas</small></article><article class="stat"><span class="label">WORKERS ACTIVOS</span><span class="stat-mark">◉</span><strong>${active}<span class="muted"> / ${data.workers.length}</span></strong><small>${data.supervisor.runs} ejecuciones registradas</small></article><article class="stat"><span class="label">BLOQUEOS</span><span class="stat-mark">◇</span><strong>${c.blocked||0}</strong><small>${c.blocked?'Requieren intervención':'Ningún bloqueo registrado'}</small></article>`);
 renderControls(); renderWorkers();
 const radar=data.tasks.filter(t=>t.status!=='done').sort((a,b)=>({blocked:0,in_progress:1,pending:2}[a.status]-{blocked:0,in_progress:1,pending:2}[b.status])||a.order-b.order).slice(0,5);
 html('#radar',radar.map(t=>`<button class="radar-row" data-task="${esc(t.id)}"><span class="radar-number">${String(t.order).padStart(2,'0')}</span><span class="radar-text"><strong>${esc(t.title)}</strong><small>${esc(t.id)}</small></span>${badge(t.status)}</button>`).join('')||'<div class="empty">Todas las tareas están terminadas.</div>');
 const j=data.journal.split('\n'), heading=j.find(l=>l.startsWith('## '))||'Sin entrada reciente';
 html('#journal',`<div class="journal-date">ÚLTIMA ENTRADA DEL REPOSITORIO</div><div class="journal-title">${esc(heading.replace(/^## /,''))}</div><div class="journal-copy">${esc(j.filter(l=>!l.startsWith('## ')).slice(0,13).join(' '))}</div><details><summary>Leer entrada completa</summary><pre>${esc(data.journal)}</pre></details>`);
 renderQueue(); activity();
 html('#sources',data.sources.map(s=>`<code>${esc(s)}</code>`).join(''));
 $('#clock').textContent=new Date(data.generated_at*1000).toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
 $('#footer-state').textContent=`Estado leído ${date(data.generated_at)} · ${data.control?.enabled?'Controles locales disponibles':'Solo lectura'}`;
 if(selectedTask&&$('#task-dialog').open)renderDetail(selectedTask);
}
function renderDetail(id){
 const t=data.tasks.find(t=>t.id===id);if(!t)return;
 $('#reply-form').hidden=!(t.status==='blocked'&&data.control?.enabled&&controlKey);
 const signature=JSON.stringify(t);if(signature===detailSignature)return;detailSignature=signature;
 const paragraphs=text=>String(text).replace(/([.!?])\s+(?=[A-ZÁÉÍÓÚÑ])/gu, '$1\n').split(/\n+/).filter(Boolean).map(p=>`<p>${esc(p)}</p>`).join('');
 const section=(title,text,fold=false)=>!text?'':fold?`<details class="detail-section detail-fold"><summary>${title}<span>Desplegar</span></summary><div class="detail-prose">${paragraphs(text)}</div></details>`:`<section class="detail-section"><h3>${title}</h3><div class="detail-prose">${paragraphs(text)}</div></section>`;
 html('#task-detail',`<span class="task-code">#${t.order} · ${esc(t.id)}</span><h2 id="task-detail-title" class="detail-title" tabindex="-1">${esc(t.title)}</h2><div class="detail-meta">${badge(t.status)}<span>Asignación: ${esc(name(t.owner))}</span>${t.lane?`<span>Último carril: ${esc(name(t.lane))}</span>`:''}</div><section class="detail-section"><h3>Dependencias</h3>${t.after?.length?t.after.map(d=>`<button class="dependency" data-task="${esc(d)}">${data.tasks.find(x=>x.id===d)?.status==='done'?'✓ ':'◷ '}${esc(d)}</button>`).join(''):'<p>Sin dependencias.</p>'}</section>${section('Estado y notas',t.notes)}${section('Evidencia',t.evidence,true)}${section('Criterios de aceptación',t.accept,true)}${section('Diseño',t.design)}`);
}
document.addEventListener('click',e=>{const task=e.target.closest('[data-task]');if(task&&data){e.preventDefault();if(selectedTask!==task.dataset.task){$('#task-answer').value='';$('#reply-feedback').textContent='';}selectedTask=task.dataset.task;renderDetail(selectedTask);if(!$('#task-dialog').open){$('#task-dialog').showModal();$('#task-detail-title').focus();}$('.dialog-body').scrollTop=0;}const f=e.target.closest('[data-filter]');if(f){filter=f.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('selected',b===f));if(data)renderQueue();}});
$('#close-dialog').addEventListener('click',()=>$('#task-dialog').close());
$('#task-dialog').addEventListener('click',e=>{if(e.target===$('#task-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('#search').addEventListener('input',()=>{if(data)renderQueue();});
const tools=[['CM','CTRMap-F5','Mapas, materiales y geometría','Lee y reconstruye los mapas de ORAS. Los helpers Java colocan piezas existentes y ajustan materiales, UV y cámaras.','Herramienta del proyecto'],['Py','Python + Java','Construcción reproducible','Coordinan los generadores, la distribución de la isla, los parches y las comprobaciones de archivos.','Scripts locales'],['Az','Azahar + GDB','Pruebas dentro del juego','Recorridos, combates, cámara y lectura de estado. Cada carril dispone de su laboratorio y puerto GDB.','El visor no inicia el emulador'],['✓','pytest + Unicorn','Verificación automática','Pruebas de generadores y lógica; ejecución de rutinas ARM sin necesitar un combate completo en el emulador.','La actividad indica si se invocan'],['↗','Git + worktrees','Trabajo e integración','Cada worker trabaja en su carril. El supervisor integra los cambios y registra los resultados y la evidencia.','Un carril por worker'],['◇','Blender','Fuera del flujo actual','No está integrado en el flujo visual documentado de la isla. La construcción actual usa piezas de ORAS con CTRMap-F5.','Sin MCP de Blender en este flujo']];
html('#tool-grid',tools.map(([icon,title,sub,body,foot])=>`<article class="tool-card"><div class="tool-icon">${icon}</div><h2>${title}</h2><span class="micro">${sub}</span><p>${body}</p><small>${foot}</small></article>`).join(''));
async function refresh(){
 try{const response=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(7000)});if(!response.ok)throw new Error('HTTP '+response.status);const next=await response.json();data=next;lastGood=Date.now();render();$('#connection-dot').classList.remove('offline');$('#connection-text').textContent='Datos en directo';$('#error').hidden=!data.warnings.length;$('#error').textContent=data.warnings.length?'Algunas fuentes no se han podido leer: '+data.warnings.join(' · '):'';}
 catch(error){$('#connection-dot').classList.add('offline');$('#connection-text').textContent='Sin conexión';$('#error').hidden=false;$('#error').textContent='No se puede actualizar el visor. '+(lastGood?'Se conserva la última lectura de '+new Date(lastGood).toLocaleTimeString('es-ES')+'.':'Comprueba que el servidor local está activo.');}
 finally{setTimeout(refresh,3000);}
}
$('#refresh').addEventListener('click',()=>location.reload());
route();refresh();

function renderControls(){
 const c=data.control||{}, running=c.running??data.supervisor.running, flags=data.supervisor.controls;
 $('#control-status').textContent=!c.enabled?'Servidor en modo de consulta. Los controles no están habilitados.':running?(flags.includes('stop')?'Parada tras ejecución solicitada':flags.includes('drain')?'Drain activo · terminando tareas':'Supervisor activo'):c.launch_exit?'El último arranque terminó con error. '+(c.launch_log||[]).join(' '):'Supervisor parado · listo para iniciar';
 $('#control-badge').textContent=!c.enabled?'SOLO LECTURA':controlKey?'CONTROLES HABILITADOS':'CONTROLES BLOQUEADOS';
 $('#unlock-controls').hidden=!c.enabled||!!controlKey;
 $('#control-actions').hidden=!c.enabled||!controlKey;
 document.querySelectorAll('[data-control]').forEach(b=>{b.disabled=controlBusy||(b.dataset.control==='start'&&running)||(b.dataset.control==='resume'&&!flags.length);});
 const states={pending:'Pendiente de parada limpia',applied:'Aplicada · tarea desbloqueada',failed:'No aplicada · requiere revisión'};
 html('#reply-requests',(c.replies||[]).slice(-5).reverse().map(r=>`<div class="reply-request ${esc(r.status)}"><strong>${esc(r.task_id)}</strong><span>${esc(states[r.status]||r.status)}</span>${r.error?`<p>${esc(r.error)}</p>`:''}</div>`).join(''));
}
async function command(action,extra={},feedback='#control-feedback'){
 if(controlBusy)return false;
 controlBusy=true;if(data)renderControls();
 $(feedback).textContent='Enviando…';
 try{
  const response=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+controlKey},body:JSON.stringify({action,...extra}),signal:AbortSignal.timeout(30000)});
  const result=await response.json();
  if(!response.ok){if(response.status===401){controlKey='';sessionStorage.removeItem('frontier-control-key');}throw new Error(result.error||'No se pudo enviar la acción.');}
  $(feedback).textContent=result.message;
  const state=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(7000)});
  if(state.ok){data=await state.json();render();}
  return true;
 }catch(error){$(feedback).textContent=error.message;return false;}
 finally{controlBusy=false;if(data)renderControls();}
}
$('#unlock-controls').addEventListener('submit',async e=>{e.preventDefault();controlKey=$('#control-key').value.trim();if(await command('unlock')){sessionStorage.setItem('frontier-control-key',controlKey);$('#control-key').value='';}else{controlKey='';}if(data)renderControls();});
$('#lock-controls').addEventListener('click',()=>{controlKey='';sessionStorage.removeItem('frontier-control-key');if(data)render();});
document.querySelectorAll('[data-control]').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.control==='start')$('#start-dialog').showModal();else command(b.dataset.control);}));
$('#confirm-start').addEventListener('click',()=>{$('#start-dialog').close();command('start',{mode:$('#launch-mode').value});});
$('#cancel-start').addEventListener('click',()=>$('#start-dialog').close());
$('#reply-form').addEventListener('submit',async e=>{e.preventDefault();if(await command('reply',{task_id:selectedTask,answer:$('#task-answer').value},'#reply-feedback'))$('#task-answer').value='';});
