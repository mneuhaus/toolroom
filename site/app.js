/* Static, offline documentation. Generated content is in site/data.js. */
(() => {
  "use strict";
  const D = window.CAD_DATA;
  const main = document.getElementById("main");
  if (!D) { main.innerHTML = '<h1>Documentation did not load</h1><p>Open the complete Toolroom folder, including site/data.js.</p>'; return; }
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const normalize = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const categories = {workflow:"Workflow",cad:"CAD integration",construction:"Construction",manufacturing:"Manufacturing",design:"Design",documentation:"Documentation",reconstruction:"Reconstruction",simulation:"Simulation"};
  const summaries = {
    "cad-joints":"Select joint principles, construct native mating parts and check the complete assembly path.",
    "cad-workflow":"Establish the source, task and interfaces. Select the skills needed for the result.",
    "onshape-cad":"Develop native models and FeatureScript. Preserve user features and assembly references.",
    "onshape-bridge":"Operate the existing session connection. Resolve uncertain writes and verify transferred artefacts.",
    "cad-khana":"Parametric parts, assembly assertions and structured geometry diagnostics with Build123d.",
    "cad-fdm-design":"Consider print orientation, fit and assembly together. Resolve profiles and inspect deposited layers.",
    "cad-design-system":"Combine design language, manufacturing and protected interfaces through independent profiles.",
    "onshape-build-manuals":"Create clear instructions from reusable build stages, actual parts and a shared recipe.",
    "fusion360":"Build native Fusion geometry from source programs and verify changes with explicit volume accounting.",
    "cad-physics-simulation":"Turn a CAD assembly into a rigid-body simulation with driven joints and logged poses, then replay it in a renderer bound to its log.",
    "scan-reverse-engineering":"Convert raw scans into justified functional CAD geometry. Check shape assumptions against the surfaces."
  };
  const navNames = {overview:"Overview",architecture:"Architecture",skills:"Skills",knowledge:"Knowledge base",profiles:"Profiles",labs:"Labs",roadmap:"Development",provenance:"Provenance & sources"};
  const state = {joint:"J06",jointPose:"separate",filter:"all",layer:0,style:"instrument",process:"fdm",lab:"solid",route:"overview",title:"Overview"};
  const wordNum = (n)=>({1:"One",2:"Two",3:"Three",4:"Four",5:"Five",6:"Six",7:"Seven",8:"Eight",9:"Nine",10:"Ten",11:"Eleven",12:"Twelve"})[n]||String(n);
  const pill = (label, cls="") => `<span class="pill ${cls}">${esc(label)}</span>`;
  const readLink = (path, label, cls="text-link") => `<a class="${cls}" href="#read/${esc(path)}">${esc(label)} <span aria-hidden="true">↗</span></a>`;
  const heading = (num, title, text) => `<div class="page-heading"><span class="eyebrow accent">${esc(num)}</span><h1 tabindex="-1">${esc(title)}</h1><p>${esc(text)}</p></div>`;
  const note = (text) => `<div class="wide-note"><span aria-hidden="true">↳</span><p>${text}</p></div>`;
  const two = (n) => String(n).padStart(2, "0");

  function overview() {
    return `<div class="page-meta">${pill("LOCAL WORKING EDITION", "warm")}<span class="eyebrow" style="margin:0;font-size:9px">A CAD KNOWLEDGE BASE AND SKILL FRAMEWORK</span></div>
      <section class="hero"><div class="hero-copy"><span class="eyebrow accent">TOOLROOM</span><h1 tabindex="-1">From idea<br>to part<span style="color:var(--accent)">.</span></h1><p>CAD knowledge that fits together. Construction, manufacturing and design, connected through traceable checks and reproducible labs.</p><div class="hero-actions"><a class="button" href="#architecture">Explore the framework <span>↗</span></a><a class="text-link" href="#knowledge">Read the knowledge base <span>→</span></a></div></div><div class="hero-visual"><div class="drawing-meta"><span>JOINTS / J06</span><span>FIG. 001</span></div><img src="site/assets/joints-J06-assembled.png" alt="Two printed parts joined by the J06 echo-lock principle, native Onshape render" width="1100" height="650"><div class="hero-ticks" aria-hidden="true"><span>+</span><span>+</span></div><div class="drawing-caption"><span>PRINTED JOINTS LAB / J06 · NATIVE CAD GEOMETRY</span><a href="#lab/printed-joints" aria-label="Open the Printed Joints Lab">↗</a></div></div></section>
      <div class="stats-line"><div class="stat"><strong>${two(D.modules.length)}</strong><span>composable skills</span></div><div class="stat"><strong>${two(D.knowledge.articles.length)}</strong><span>knowledge articles</span></div><div class="stat"><strong>${two(D.labs.length)}</strong><span>reproducible labs</span></div></div>
      <div class="section-head"><h2>A good starting point</h2><span>READ · UNDERSTAND · DISCUSS</span></div>
      <div class="entry-grid"><a class="entry-card" href="#skills"><span class="eyebrow">01 /</span><h3>The right knowledge<br>for the task.</h3><p>Short skill entrypoints, specific technical references and clearly identified tool integrations.</p><div class="card-bottom"><span>SKILLS</span><span class="arrow">↗</span></div></a><a class="entry-card" href="#knowledge"><span class="eyebrow">02 /</span><h3>Rules that hold<br>across backends.</h3><p>Foundations, workflow, construction, manufacturing and design languages in one maintained catalogue.</p><div class="card-bottom"><span>KNOWLEDGE BASE</span><span class="arrow">↗</span></div></a><a class="entry-card" href="#labs"><span class="eyebrow">03 /</span><h3>Evidence gives<br>results meaning.</h3><p>Reproducible experiments show what a joint principle, a geometry checker and a scalable socket generator actually demonstrate.</p><div class="card-bottom"><span>LABS</span><span class="arrow">↗</span></div></a></div>
      <div class="section-head"><h2>Everything, one click away</h2><span>THE WHOLE MAP</span></div>
      <div class="map-grid"><div class="map-col"><h3>Skills · when and how</h3>${D.modules.map(m=>`<a href="#read/${esc(m.document)}">${esc(m.title)}</a>`).join("")}</div><div class="map-col"><h3>Knowledge · why</h3>${D.knowledge.sections.map(s=>{const arts=D.knowledge.articles.filter(a=>a.section===s.id);return arts.length?`<span class="tree-sub">${esc(s.title)}</span>${arts.map(a=>`<a href="#read/${esc(a.path)}">${esc(a.title)}</a>`).join("")}`:"";}).join("")}</div><div class="map-col"><h3>Labs · evidence</h3>${D.labs.map(l=>`<a href="#lab/${esc(l.id)}">${esc(l.title)}</a>`).join("")}<span class="tree-sub">Profiles</span><a href="#profiles">Profile workbench</a><a href="#read/profiles/README.md">Profile conventions</a><a href="#read/profiles/environment/README.md">Environment profiles</a><span class="tree-sub">About</span><a href="#architecture">Architecture</a><a href="#read/docs/scope.md">Scope and maturity</a><a href="#read/docs/history.md">History</a></div></div>
      ${note('This edition brings the current sources together for discussion. For locally verified helpers and separate CAD runtimes, see <a href="#read/docs/scope.md">Scope & maturity</a>.')}`;
  }

  const layers = [
    {title:"Core",headline:"A shared understanding of the project.",text:"Source, revision, units and part identity connect the handoffs. The current native design may contain more than its original generator.",items:["Authoritative source and protected interfaces","Native, assembly and print coordinates","Bind evidence to revision and inputs"],example:"A styling revision must preserve the established bearing stack and its travel.",doc:"knowledge/foundations/core.md"},
    {title:"Skills",headline:"An entrypoint for the specific task.",text:"A skill describes selection, working practice and relevant limits. Load detailed API and technical references when needed.",items:["Short entrypoints with clear scope","Shared technical rules in one place","Task-specific branches without a mandatory full pipeline"],example:"A PDF layout change uses the existing recipe and does not require regenerating CAD.",doc:"skills/cad-workflow/SKILL.md"},
    {title:"Integrations",headline:"Each tool keeps its strengths.",text:"Onshape, Build123d and Fusion have different source and execution models. Each integration handles its specific operations and failure modes.",items:["Preserve native user features","Resolve uncertain writes before retrying","Check return values and resulting artefacts"],example:"Uploading FeatureScript does not automatically update a reference pinned to a microversion.",doc:"docs/scope.md"},
    {title:"Profiles",headline:"Parameters with clear ownership.",text:"Design language, manufacturing process and mechanical interfaces are three independent profiles. Historical preferences remain identifiable.",items:["Colour roles, selected edges and labelling","Actual material, machine and print orientation","Separate calibrated data from starting values"],example:"A laser export that already compensates for kerf must not receive a second CAM offset.",doc:"profiles/README.md"},
    {title:"Evidence",headline:"Observable behaviour with specific evidence.",text:"CAD, assembly, slicer, simulation and physical tests answer different questions. Their results remain visible separately.",items:["Preserve original inputs and raw findings","Explicitly identify incomplete analysis","Reproduce small known failure cases"],example:"A narrow unsupported underside still needs an anchor. The shared checker includes this failure case.",doc:"knowledge/foundations/verification.md"}
  ];

  function architecture() {
    return `${heading("02 / CONNECTIONS", "Five layers. One shared workflow.", "Combine the building blocks to suit the task. Select a layer to explore its role.")}
      <div class="arch-grid" aria-label="Framework layers">${layers.map((l,i)=>`<button class="arch-step" data-layer="${i}" aria-pressed="${state.layer===i}"><span class="number">0${i+1} /</span><strong>${l.title}</strong></button>`).join("")}</div><section id="arch-detail" class="arch-detail" aria-live="polite">${layerDetail()}</section>
      <div class="section-head"><h2>For example: revise a mount</h2></div><div class="flow-line"><span>Task & interfaces</span><i>→</i><span>Onshape</span><i>+</i><span>Design-System</span><i>+</i><span>FDM</span><i>→</i><span>CAD & manufacturing evidence</span></div>
      ${note('A layout change, a scan and a new design need different branches. <a href="#read/knowledge/workflow/recipes.md">The practical task recipes</a> explain the selection.')}
      <div class="section-head"><h2>Architecture in detail</h2></div>${readLink("docs/architecture.md","Read about responsibilities, maintained sources and limits")}`;
  }
  function layerDetail() {
    const l=layers[state.layer];
    return `<div><span class="eyebrow accent">LAYER 0${state.layer+1}</span><h3>${l.headline}</h3><p>${l.text}</p>${readLink(l.doc,"Read more")}</div><div class="scope-box"><span class="eyebrow">BELONGS HERE</span><ul>${l.items.map(x=>`<li>${x}</li>`).join("")}</ul><p style="font-size:12px">${l.example}</p></div>`;
  }

  function skillCards() {
    const list=D.modules.filter(m=>state.filter==="all"||m.category===state.filter);
    return list.map(m=>`<a class="skill-card" href="#read/${esc(m.document)}"><div class="skill-card-top"><span class="skill-icon" aria-hidden="true">${({workflow:"⌁",cad:"⌑",construction:"⊏",manufacturing:"≋",design:"◐",documentation:"▤",reconstruction:"⋈",simulation:"∿"})[m.category]}</span>${pill(categories[m.category])}</div><h2>${esc(m.title)}</h2><p>${esc(summaries[m.id])}</p><div class="skill-card-footer"><span>${m.state==="local-tools"?"WITH LOCAL HELPERS":"CURATED KNOWLEDGE"}</span><span>↗</span></div></a>`).join("");
  }
  function skills() {
    return `${heading("03 / SKILLS", "An entrypoint for every task.", "${wordNum(D.modules.length)} short entrypoints connect the existing capabilities. Detailed references and practical helpers remain directly accessible.")}
      <div class="filter-bar" aria-label="Filter skills by area"><button class="filter-chip" data-filter="all" aria-pressed="${state.filter==="all"}">All skills</button>${Object.entries(categories).map(([id,title])=>`<button class="filter-chip" data-filter="${id}" aria-pressed="${state.filter===id}">${title}</button>`).join("")}<span id="filter-count" class="filter-count" role="status">${D.modules.filter(m=>state.filter==="all"||m.category===state.filter).length} ENTRIES</span></div><div class="skill-grid" id="skill-grid">${skillCards()}</div>
      ${note('All maintained documentation uses English. The rules a skill relies on are collected in the <a href="#knowledge">knowledge base</a>.')}`;
  }

  function labs() {
    return `${heading("06 / LABS", "Reproducible experiments with their own evidence.", "A lab is a small, non-personal experiment that can be rebuilt from this repository. It shows what a principle or a helper actually demonstrates.")}
      <div class="labs-grid">${D.labs.map((l,i)=>`<a class="labs-card" href="#lab/${esc(l.id)}"><div class="labs-image"><img src="${esc(l.image)}" alt="${esc(l.title)}" loading="lazy"><span class="labs-tag">${esc(l.kind)}</span></div><span class="eyebrow">${two(i+1)} / ${esc(l.tag)}</span><h2>${esc(l.title)} <span style="color:var(--accent)">↗</span></h2><p>${esc(l.summary)}</p></a>`).join("")}</div>
      ${note('A lab result is evidence about geometry or a helper, never a physical acceptance. <a href="#read/labs/README.md">How the labs are built and run</a>.')}`;
  }
  function labPage(id) {
    const lab=D.labs.find(x=>x.id===id);
    if(!lab) return notFound();
    return id==="printed-joints" ? jointsPage(lab) : id==="checker-lab" ? checkerLabPage(lab) : genericLabPage(lab);
  }
  function genericLabPage(lab) {
    state.title=lab.title;
    const doc=D.documents[lab.document];
    return `${heading("LAB / "+lab.tag.toUpperCase(),lab.title,lab.summary)}<div class="article-toolbar"><a href="#labs">← All labs</a><a href="#source/${esc(lab.document)}">View source file ↗</a></div><figure class="joint-figure"><img src="${esc(lab.image)}" alt="${esc(lab.title)}" loading="lazy"><figcaption>${esc(lab.kind).toUpperCase()} · GENERATED FROM THE LAB'S OWN GEOMETRY</figcaption></figure><div class="article-shell"><article class="article">${doc?doc.body:""}</article>${toc(doc,lab.document)}</div>${labFooter(lab)}`;
  }
  function labFooter(lab) {
    return `<div class="source-reference">RUN: ${esc(lab.runnable)}<br>SOURCE: ${esc(lab.source)}${lab.source_sha256?`<br>SHA-256: ${esc(lab.source_sha256)}`:""}</div>`;
  }

  function jointView() {
    const j=D.joints.find(j=>j.id===state.joint);
    return `<figure class="joint-figure"><img src="${j[state.jointPose]}" width="1100" height="650" alt="${esc(j.title)}: native Onshape render, ${state.jointPose==='separate'?'separated parts':'assembled state'}"><figcaption>${esc(j.id)} · NATIVE ONSHAPE RENDER · ${state.jointPose==='separate'?'SEPARATED PARTS':'ASSEMBLED'}</figcaption></figure><div class="joint-detail"><span class="eyebrow accent">${esc(j.tag)}</span><h2>${esc(j.title)}</h2><p>${esc(j.description)}</p><dl><dt>Assembly path</dt><dd>${esc(j.assembly)}</dd><dt>Geometry</dt><dd>${esc(j.parameters)}</dd></dl><p class="joint-limit">${esc(j.limits)}</p><div class="joint-links"><a class="button" href="${j.onshape}" target="_blank" rel="noopener">Open in Onshape ↗</a><a class="text-link" href="${j.step}" download>STEP ↓</a><a class="text-link" href="${j.source}" target="_blank" rel="noopener">Video timestamp ↗</a></div></div>`;
  }
  function jointsPage(lab) {
    state.title=lab.title;
    const doc=D.documents[lab.document];
    return `${heading("LAB / PRINTED JOINTS",lab.title,lab.summary)}<div class="article-toolbar"><a href="#labs">← All labs</a></div><div class="joint-switch" role="group" aria-label="Select a joint principle">${D.joints.map(j=>`<button data-joint="${j.id}" aria-pressed="${state.joint===j.id}"><span>${j.id}</span>${esc(j.title)}</button>`).join('')}</div><section class="joint-lab" aria-label="Native model comparison"><div class="joint-toolbar"><span class="eyebrow">BLUE / A · ORANGE / B · OCHRE / WEDGES</span><div role="group" aria-label="Model view"><button class="filter-chip" data-joint-pose="assembled" aria-pressed="${state.jointPose==='assembled'}">Assembled</button><button class="filter-chip" data-joint-pose="separate" aria-pressed="${state.jointPose==='separate'}">Separate parts</button></div></div><div id="joint-view">${jointView()}</div><span id="joint-announcement" class="joint-announcement" role="status"></span></section>${note('16 native models, eight STEP exports and checked discrete assembly paths. Printing, measured fit and strength remain open. The separated views do not define print orientation.')}<div class="article-shell"><article class="article">${doc.body}</article>${toc(doc,lab.document)}</div>${labFooter(lab)}`;
  }

  const styles={
    instrument:{title:"Instrument",colors:["#cecdc7","#535953","#ed602f"],radius:3,description:"Light structure, dark functional parts and a restrained accent. Short labels and deliberate facets.",path:"profiles/design-language/te-like.yaml",key:"01 / adjust"},
    soft:{title:"Soft Consumer",colors:["#dedfce","#a4ae95","#626b51"],radius:23,description:"Softer transitions and calm surfaces. Functional contacts retain their original geometry.",path:"profiles/design-language/soft-consumer.yaml",key:"Adjust"},
    rugged:{title:"Rugged Industrial",colors:["#717866","#313a31","#e5b044"],radius:2,description:"Substantial visible structure and contrasting control areas. Appearance alone establishes no additional strength.",path:"profiles/design-language/rugged-industrial.yaml",key:"ADJUST / 01"},
    workshop:{title:"Workshop 0.42",colors:["#dddcd4","#6c7267","#d57047"],radius:10,description:"The historical 0.42/4.2 edge family: flush transitions and continuous contours. A distinct style profile.",path:"profiles/design-language/workshop-042.yaml",key:"WORKSHOP"},
    mosey:{title:"Mosey",colors:["#BDD1BA","#F0EDDF","#C6B6D7"],radius:28,ink:"#383D3A",description:"Calm sculptural bodies, large tactile controls and functional colour fields. The soft variant is shown here; broad facets and useful supporting shells also belong to the language. Derived from concept images, not yet calibrated.",path:"profiles/design-language/mosey.yaml",document:"knowledge/design/mosey.md",key:"turn"}
  };
  const processes={
    fdm:{title:"FDM",caption:"PRINT ORIENTATION · LAYERS · SUPPORT",detail:"Bed contact and layer direction define the assessment. Local walls, attachments and actual slicer paths are checked separately.",state:"Widely documented workflow",path:"profiles/manufacturing/fdm-bambu-a1-0.4.yaml"},
    laser:{title:"Laser cutting",caption:"MATERIAL THICKNESS · KERF · ASSEMBLY",detail:"Flat parts need a known material thickness and a single owner for kerf compensation. Tab-and-slot joints carry the assembly sequence.",state:"Worked export example",path:"profiles/manufacturing/laser-diode-3mm.yaml"},
    cnc:{title:"CNC",caption:"TOOL · ACCESS · WORKHOLDING",detail:"Tool access, internal radii and workholding belong to the process. The framework includes references; a general CAM workflow remains open.",state:"Reference profile / further development",path:"profiles/manufacturing/cnc-small-hobby.yaml"},
    sla:{title:"SLA / MSLA",caption:"ORIENTATION · SUPPORTS · FINISHING",detail:"Existing profile values are generic starting points. The collection does not yet establish a calibrated resin and machine example.",state:"Uncalibrated reference profile",path:"profiles/manufacturing/sla-generic.yaml"}
  };
  function schematic() {
    const s=styles[state.style];
    return `<div class="drawing-meta"><span>PROFILE / ${esc(s.title.toUpperCase())}</span><span>FIG. 002</span></div><svg viewBox="0 0 400 310" role="img" aria-label="Schematic part in the style ${esc(s.title)}; four unchanged mounting positions"><defs><pattern id="print-lines" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M0 5.5H6" stroke="#fff" stroke-opacity=".28" stroke-width=".8"/></pattern></defs><path d="M40 256H360M200 32V276" stroke="#aab1a1" stroke-width=".8" stroke-dasharray="3 5"/><rect x="68" y="64" width="264" height="174" rx="${s.radius}" fill="${s.colors[1]}" stroke="#1f291d" stroke-opacity=".35"/><rect x="68" y="55" width="264" height="174" rx="${s.radius}" fill="${s.colors[0]}" stroke="#333a2f" stroke-opacity=".6" stroke-width="1"/>${state.process==="fdm"?`<rect x="69" y="56" width="262" height="172" rx="${s.radius}" fill="url(#print-lines)"/>`:""}${[[95,81],[305,81],[95,203],[305,203]].map(([x,y])=>`<g class="fixed-interface"><circle cx="${x}" cy="${y}" r="8" fill="#f4f3ef" stroke="#59664b"/><path d="M${x-12} ${y}h24M${x} ${y-12}v24" stroke="#809271" stroke-width=".8"/></g>`).join("")}<rect x="114" y="106" width="172" height="68" rx="${Math.min(s.radius,10)}" fill="${s.colors[1]}"/><path d="M130 122h43M130 132h27M130 150h78" stroke="${s.ink||s.colors[0]}" stroke-width="2" opacity=".7"/><circle cx="254" cy="140" r="${state.style==="mosey"?26:20}" fill="${s.colors[2]}"/><path d="M254 126v10" stroke="#fff" stroke-width="2" opacity=".8"/><text x="119" y="195" fill="${s.ink||(state.style==="rugged"?'#fff':s.colors[1])}" font-size="10" font-family="monospace">${esc(s.key)}</text><path d="M48 55v174M43 55h10M43 229h10M95 248h210M95 243v10M305 243v10" stroke="#939e85" stroke-width=".8"/><text x="200" y="279" text-anchor="middle" fill="#66715a" font-family="monospace" font-size="9">4 MOUNTING POSITIONS / PROTECTED</text></svg><p class="schematic-caption">SCHEMATIC COMPARISON · NOT CAD OR MANUFACTURING EVIDENCE</p>`;
  }
  function profileDetail() {
    const s=styles[state.style],p=processes[state.process];
    return `<h3>${esc(s.title)} × ${esc(p.title)}</h3><p>${esc(s.description)}</p><p>${esc(p.detail)}</p><div class="palette" aria-label="Illustrative colour palette">${s.colors.map(c=>`<span style="background:${c}" title="${c}"></span>`).join("")}</div><p style="margin-top:13px;font-family:var(--mono);font-size:9px">${esc(p.state)}</p>${s.document?`<a class="text-link" href="#read/${s.document}">Interpretation with examples ↗</a><br>`:""}<a class="text-link" href="#source/${s.path}">Read style profile ↗</a> <a class="text-link" href="#source/${p.path}">Read manufacturing profile ↗</a>`;
  }
  function profiles() {
    return `${heading("05 / PROFILES", "One language. Several manufacturing paths.", "Explore the independent roles of design and manufacturing. Schematic palettes illustrate the idea; the original profiles remain separately readable.")}
      <div class="workbench"><div id="workbench-visual" class="workbench-visual">${schematic()}</div><div class="profile-controls"><div class="control-group"><label class="field-label" for="style-select">01 / Design Language</label><select id="style-select">${Object.entries(styles).map(([id,s])=>`<option value="${id}" ${id===state.style?"selected":""}>${s.title}</option>`).join("")}</select></div><div class="control-group"><label class="field-label" for="process-select">02 / Manufacturing process</label><select id="process-select">${Object.entries(processes).map(([id,p])=>`<option value="${id}" ${id===state.process?"selected":""}>${p.title}</option>`).join("")}</select></div><div class="profile-detail" id="profile-detail" aria-live="polite">${profileDetail()}</div><div class="locked-profile"><strong>03 / Interfaces remain protected.</strong><br>The four mounts remain unchanged across styles. A different profile does not authorise changes to function or assembly.</div></div></div>
      <div class="profile-cards"><div><span class="eyebrow accent">DESIGN</span><h3>What form supports the function?</h3><p>Colour roles, selected edges, labelling and recurring elements.</p></div><div><span class="eyebrow accent">MANUFACTURING</span><h3>How is the part manufactured?</h3><p>Machine, material, orientation and explicitly marked verification limits.</p></div><div><span class="eyebrow accent">INTERFACES</span><h3>What must be preserved?</h3><p>Fits, purchased parts, load paths, movement clearance and tool access.</p></div></div>
      <section class="language-feature"><img src="site/assets/mosey-family.svg" alt="Three original Mosey illustrations: soft hand controller, faceted desktop stand and tray with a supporting shell" width="1080" height="410" loading="lazy"><div><span class="eyebrow accent">NEW DESIGN LANGUAGE / MOSEY 0.1</span><h2>Calm form. Tactile controls.</h2><p>18 reference images, three form variants and an original application to other objects. Observations remain distinct from proposed CAD values.</p><a class="text-link" href="#read/knowledge/design/mosey.md">Explore Mosey examples ↗</a></div></section>
      ${note('Generic starting profiles are <strong>not calibrated</strong>. Personal machine and style values retain their original scope. <a href="#read/profiles/README.md">Read profile conventions</a>.')}`;
  }

  const labIcons={solid:'<path d="m9 18 22-10 27 12-22 10Zm0 0v18l27 11 22-13V20M36 30v17"/>',thin:'<path d="m9 25 22-10 27 12-22 10Zm0 0v4l27 11 22-9v-4M36 37v3"/>',orientation:'<path d="M5 36h52V12H5Zm13-15h45v17H18Z"/><path d="m52 7 8-2 5 5" fill="none"/>',island:'<path d="m3 32 17-7 22 9-18 8Zm0 0v5l21 9 18-8v-4M49 8l9-4 6 4-9 4Zm0 0v17l6 4 9-5V8M55 12v17"/>'};
  function labResults() {
    const s=D.lab.find(x=>x.id===state.lab);if(!s)return '<p>The example report has not been generated yet.</p>';
    const r=D.reports[s.report];
    const format = v => typeof v==="number" ? new Intl.NumberFormat("en-GB",{maximumFractionDigits:2}).format(v) : v;
    return `<div><span class="eyebrow accent">ACTUAL LOCAL PROGRAM OUTPUT</span>${pill(r.status,r.status==="no_findings"?"green":"warm")}<h3>${esc(s.title)}</h3><p>${({solid:"The block meets the selected check conditions. This result applies to the small test body and stated scope.",thin:"The 0.4 mm plate remains a structural body and produces a wall-thickness finding.",orientation:"16 × 9 mm does not fit the specified 10 × 20 mm footprint. A hypothetical quarter-turn is reported separately.",island:"The narrow unsupported underside is not assumed to be a printable lip. Its missing attachment remains visible."})[state.lab]}</p><div class="article-toolbar"><a href="#source/${s.report}">Full JSON report ↗</a><a href="${s.mesh}" download>Test-STL ↓</a></div></div><div><div class="metric"><span>Analysis complete</span><strong>${r.analysis_complete?"yes":"no"}</strong></div><div class="metric"><span>Connected bodies</span><strong>${r.connected_components}</strong></div><div class="metric"><span>Dimensions in mm</span><strong>${r.bounds.extents_xyz.map(format).join(" × ")}</strong></div><div class="metric"><span>Fits in the supplied orientation</span><strong>${r.bounds.fits_build_volume?"yes":"no"}</strong></div><div class="metric"><span>Findings</span><strong>${r.problems.length}</strong></div>${r.problems.length?`<ul>${r.problems.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:'<p style="margin-top:18px">No findings within the configured screening scope.</p>'}</div>`;
  }
  function checkerLabPage(lab) {
    state.title=lab.title;
    const evidenceTypes=[["01","Native geometry","Bodies, dimensions and protected interfaces."],["02","Assembly & movement","Examined insertion paths, tool access and poses."],["03","Slicer & layers","Actual deposited paths for the selected profile."],["04","Simulation","Behaviour under documented modelling assumptions."],["05","Physical test","Measurement on the manufactured specimen."],["06","Artefact verification","Correct source, complete output and unchanged bytes."]];
    return `${heading("LAB / CHECKER LAB", lab.title, lab.summary)}<div class="article-toolbar"><a href="#labs">← All labs</a></div>
      <div class="lab-grid" aria-label="Select a test case">${D.lab.map(s=>`<button class="lab-card" data-lab="${s.id}" aria-pressed="${state.lab===s.id}"><svg viewBox="0 0 70 50" aria-hidden="true">${labIcons[s.id]}</svg><strong>${esc(s.title)}</strong>${pill(s.status==="no_findings"?"NO FINDINGS":"FINDING",s.status==="no_findings"?"green":"warm")}</button>`).join("")}</div><div class="lab-results" id="lab-results" aria-live="polite">${labResults()}</div>
      ${readLink(lab.document,"Run the lab yourself")}
      <div class="section-head"><h2>Several checks. Different questions.</h2></div><div class="evidence-types">${evidenceTypes.map(([n,t,p])=>`<div><span class="eyebrow accent">${n} /</span><h3>${t}</h3><p>${p}</p></div>`).join("")}</div>${readLink("knowledge/foundations/verification.md","Understand verification scope and result states")}${labFooter(lab)}`;
  }

  function knowledge() {
    const sections=D.knowledge.sections.map(section=>{
      const articles=D.knowledge.articles.filter(a=>a.section===section.id);
      if(!articles.length)return "";
      return `<div class="section-head"><h2>${esc(section.title)}</h2><span>${articles.length} ARTICLE${articles.length===1?"":"S"}</span></div><p style="max-width:660px;margin:-8px 0 6px;font-size:13px;color:var(--muted)">${esc(section.summary)}</p><div class="knowledge-list">${articles.map((a,i)=>`<a class="knowledge-row" href="#read/${esc(a.path)}"><span class="idx">${two(i+1)}</span><div><h3>${esc(a.title)}</h3><p>${esc(a.summary)}</p></div><span class="category">${esc(section.title.toUpperCase())}</span><span class="arrow">↗</span></a>`).join("")}</div>`;
    }).join("");
    return `${heading("04 / KNOWLEDGE BASE", "The shared rules.", "Backend-independent knowledge in six sections. Each article has a maintained source; skills link into it instead of repeating it.")}${sections}
      ${note('Skill folders keep only their backend-specific references. A rule that holds for every backend belongs here.')}`;
  }

  function roadmap() {
    const done=[["A knowledge base in sections","Foundations, workflow, construction, manufacturing, design languages, simulation and lessons, listed in one maintained catalogue."],[`${wordNum(D.modules.length)} short skill entrypoints`,"Selection, working practice and limits per skill, with backend references and helpers beside them."],["Profiles with clear ownership","Design language, manufacturing and interfaces resolved through ordered includes and a traceable resolution order."],[`${wordNum(D.labs.length)} reproducible labs`,"Native joint geometry with STEP evidence, a checker lab with actual program output, and a scalable tile-clip socket generator."],["Personal case studies removed","The project narratives were distilled into transferable rules in the lessons section."]];
    const next=[["Define maintenance boundaries","Which runtimes remain separate projects? Which helpers belong here permanently?"],["Choose a complete pilot case","Take a small independent model through construction, manufacturing and an assembly guide."],["Calibrate profiles physically","Which actual materials, machines and coupons establish our working values?"],["Define the public scope","Name, examples, our own licence and supported installations for a first release."]];
    return `${heading("DEVELOPMENT / DISCUSS TOGETHER", "A concrete foundation. Useful next questions.", "The restructure is ready to inspect. The next decisions concern scope and maintenance and can be discussed through the labs.")}
      <div class="roadmap-grid"><div class="roadmap-column"><span class="eyebrow accent">01 / IN THIS EDITION</span><h2>Already consolidated</h2>${done.map(([t,p])=>`<div class="roadmap-item"><span class="mark">✓</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join("")}</div><div class="roadmap-column"><span class="eyebrow">02 / NEXT</span><h2>Decide together</h2>${next.map(([t,p],i)=>`<div class="roadmap-item"><span class="mark">${i+1}</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join("")}</div></div>
      <div class="discussion-card"><span class="eyebrow accent">NOTES WITH CONTEXT</span><h3>What should we organise differently?</h3><p>Record thoughts on each page in their context. Export collects the notes as Markdown for our next discussion.</p><button class="button" data-action="notes">Write a discussion note ↗</button></div>${readLink("docs/history.md","How the repository got its current shape")}`;
  }

  function toc(doc,path) {
    if(!doc)return "";
    const entries=doc.headings.filter(x=>x.level>1&&x.level<4);
    if(!entries.length)return "";
    return `<aside class="toc" aria-label="Table of contents"><span class="eyebrow">ON THIS PAGE</span>${entries.map(h=>`<a class="${h.level===3?"toc-sub":""}" href="#read/${esc(path)}::${esc(h.id)}">${esc(h.title)}</a>`).join("")}</aside>`;
  }
  function navFor(path) {
    if(path.startsWith("knowledge/"))return "knowledge";
    if(path.startsWith("labs/"))return "labs";
    if(path.startsWith("skills/"))return "skills";
    if(path.startsWith("profiles/"))return "profiles";
    if(path==="docs/provenance.md")return "provenance";
    if(path.startsWith("docs/"))return "roadmap";
    return "knowledge";
  }
  const backHref = (path) => "#" + (navFor(path)==="provenance" ? "overview" : navFor(path));

  // ---- explorer tree: every document one click away ----
  function treeGroups(){
    const skills=[{href:"#skills",label:"All skills",all:true},...D.modules.map(m=>({href:"#read/"+m.document,label:m.title}))];
    const knowledge=D.knowledge.sections.map(s=>({label:s.title,items:D.knowledge.articles.filter(a=>a.section===s.id).map(a=>({href:"#read/"+a.path,label:a.title}))})).filter(s=>s.items.length);
    const labs=[{href:"#labs",label:"All labs",all:true},...D.labs.map(l=>({href:"#lab/"+l.id,label:l.title}))];
    return [
      {id:"skills",label:"Skills",items:skills},
      {id:"knowledge",label:"Knowledge",groups:[{label:"",items:[{href:"#knowledge",label:"All articles",all:true}]},...knowledge]},
      {id:"labs",label:"Labs",items:labs},
      {id:"profiles",label:"Profiles",items:[{href:"#profiles",label:"Profile workbench",all:true},{href:"#read/profiles/README.md",label:"Profile conventions"},{href:"#read/profiles/environment/README.md",label:"Environment profiles"},{href:"#read/knowledge/design/mosey.md",label:"Mosey design language"}]},
      {id:"about",label:"About Toolroom",items:[{href:"#architecture",label:"Architecture"},{href:"#read/docs/scope.md",label:"Scope and maturity"},{href:"#read/docs/history.md",label:"History"},{href:"#read/docs/provenance.md",label:"Provenance and sources"},{href:"#roadmap",label:"Development"}]}
    ];
  }
  function renderTree(){
    const host=$("#tree"); if(!host) return;
    const item=(it,g)=>`<a href="${it.href}" data-tree="${g}"${it.all?' class="tree-all"':''}>${esc(it.label)}</a>`;
    host.innerHTML=treeGroups().map(g=>{
      const count=g.items?g.items.filter(i=>!i.all).length:g.groups.reduce((n,s)=>n+s.items.filter(i=>!i.all).length,0);
      const body=g.items?g.items.map(it=>item(it,g.id)).join("")
        :g.groups.map(s=>`${s.label?`<span class="tree-sub">${esc(s.label)}</span>`:""}${s.items.map(it=>item(it,g.id)).join("")}`).join("");
      return `<details class="tree-group" data-group="${g.id}"><summary data-nav="${g.id}"><span>${esc(g.label)}</span><span class="nav-count">${count}</span></summary><div class="tree-items">${body}</div></details>`;
    }).join("");
  }
  function syncTree(nav,routePath){
    const group=({architecture:"about",roadmap:"about",provenance:"about"})[nav]||nav;
    document.querySelectorAll(".tree-group").forEach(d=>{if(d.dataset.group===group)d.open=true;});
    document.querySelectorAll(".tree-items a").forEach(a=>a.getAttribute("href")==="#"+routePath?a.setAttribute("aria-current","page"):a.removeAttribute("aria-current"));
  }

  // ---- structured skill page ----
  function skillPage(path){
    const doc=D.documents[path]; const mod=D.modules.find(m=>m.document===path);
    const root=new DOMParser().parseFromString(`<div>${doc.body}</div>`,"text/html").body.firstChild;
    let cur="intro"; const sec={intro:[]};
    for(const n of [...root.children]){ if(n.tagName==="H2"){cur=n.textContent.trim().toLowerCase();sec[cur]=[];} else sec[cur].push(n); }
    let useWhen="",notWhen=""; const introRest=[];
    for(const n of sec.intro){
      if(n.tagName==="P"&&/use when/i.test(n.textContent)&&!useWhen){
        const parts=n.innerHTML.split(/<strong>\s*Do not use when\s*<\/strong>/i);
        useWhen=parts[0].replace(/<strong>\s*Use when\s*<\/strong>/i,"").trim(); notWhen=(parts[1]||"").trim();
      } else introRest.push(n);
    }
    const html=(nodes)=>nodes.map(n=>n.outerHTML).join("");
    const proc=sec.procedure||[]; const stepsOl=proc.find(n=>n.tagName==="OL"); const procNotes=proc.filter(n=>n!==stepsOl);
    const cards=(list)=>{
      const ul=(list||[]).find(n=>n.tagName==="UL"); const others=(list||[]).filter(n=>n!==ul);
      const grid=ul?`<div class="link-cards">${[...ul.children].map(li=>{
        const links=[...li.querySelectorAll("a")]; if(!links.length) return `<div class="link-card"><p>${li.innerHTML}</p></div>`;
        const kindOf=(href)=>href.includes("labs/")?"LAB":href.includes("knowledge/")?"KNOWLEDGE":href.includes("SKILL.md")?"SKILL":/scripts\/|\.py|\.toml/.test(href)?"HELPER":"REFERENCE";
        if(links.length>1) return links.map(a=>`<a class="link-card" href="${a.getAttribute("href")}"><span class="eyebrow">${kindOf(a.getAttribute("href"))}</span><h3>${esc(a.textContent)}</h3></a>`).join("");
        const a=links[0]; const href=a.getAttribute("href"); const title=a.textContent; const clone=li.cloneNode(true); clone.querySelector("a").remove();
        const rest=clone.innerHTML.replace(/^\s*(—|–|-|:)\s*/,"").trim();
        return `<a class="link-card" href="${href}"><span class="eyebrow">${kindOf(href)}</span><h3>${esc(title)}</h3>${rest?`<p>${rest}</p>`:""}</a>`;}).join("")}</div>`:"";
      return grid+(others.length?`<div class="skill-notes">${html(others)}</div>`:"");
    };
    const env=html(sec.environment||[]);
    const known=["intro","procedure","knowledge","references","environment"];
    const extra=Object.entries(sec).filter(([k])=>!known.includes(k)).map(([k,v])=>`<div class="section-head"><h2>${esc(k[0].toUpperCase()+k.slice(1))}</h2></div><div class="skill-notes">${html(v)}</div>`).join("");
    state.title=doc.title;
    return `<div class="article-toolbar"><a href="#skills">← All skills</a><button data-copy="${esc(path)}">Copy Markdown</button><a href="#source/${esc(path)}">View source file ↗</a><button data-action="notes">Note on this topic</button></div>
      <div class="skill-head">${mod?pill(categories[mod.category]||mod.category):""}<h1 tabindex="-1">${esc(doc.title)}</h1>${mod?`<p class="lede">${esc(mod.description)}</p>`:""}</div>
      ${useWhen?`<div class="when-grid"><div class="when yes"><span class="eyebrow">USE WHEN</span><p>${useWhen}</p></div><div class="when no"><span class="eyebrow">NOT FOR</span><p>${notWhen||"See the description above."}</p></div></div>`:""}
      ${introRest.length?`<div class="skill-notes">${html(introRest)}</div>`:""}
      ${stepsOl?`<div class="section-head"><h2>Procedure</h2><span>${stepsOl.children.length} STEPS</span></div><ol class="steps">${[...stepsOl.children].map((li,i)=>`<li><span class="step-no">${two(i+1)}</span><div>${li.innerHTML}</div></li>`).join("")}</ol>`:""}
      ${procNotes.length?`<div class="skill-notes">${html(procNotes)}</div>`:""}
      ${sec.knowledge?`<div class="section-head"><h2>Knowledge to load</h2><span>THE WHY</span></div>${cards(sec.knowledge)}`:""}
      ${sec.references?`<div class="section-head"><h2>References and helpers</h2><span>THE HOW</span></div>${cards(sec.references)}`:""}
      ${env?`<div class="wide-note"><span aria-hidden="true">⌂</span><div class="note-body">${env}</div></div>`:""}
      ${extra}
      <div class="source-reference">MAINTAINED SOURCE / ${esc(path)}</div>`;
  }
  function articleIntro(path){
    const art=D.knowledge.articles.find(a=>a.path===path); if(!art) return "";
    const section=D.knowledge.sections.find(s=>s.id===art.section);
    const file=path.split("/").pop();
    const users=D.modules.filter(m=>(D.sources[m.document]?.text||"").includes(file));
    const words=(D.documents[path].plain||"").split(/\s+/).length; const mins=Math.max(1,Math.round(words/220));
    return `<div class="intro-card"><div><span class="eyebrow accent">${esc((section?section.title:"").toUpperCase())} · ${mins} MIN READ</span><p>${esc(art.summary)}</p></div>${users.length?`<div class="intro-users"><span class="eyebrow">LOADED BY</span>${users.map(m=>`<a class="pill" href="#read/${esc(m.document)}">${esc(m.title)}</a>`).join("")}</div>`:""}</div>`;
  }
  function readPage(path) {
    const doc=D.documents[path];if(!doc)return sourcePage(path);
    if(/^skills\/[^/]+\/SKILL\.md$/.test(path)) return skillPage(path);
    state.title=doc.title;
    return `<div class="article-toolbar"><a href="${backHref(path)}">← Back to overview</a><button data-copy="${esc(path)}">Copy Markdown</button><a href="#source/${esc(path)}">View source file ↗</a><button data-action="notes">Note on this topic</button></div>${articleIntro(path)}<div class="article-shell"><article class="article">${doc.html}</article>${toc(doc,path)}</div><div class="source-reference">MAINTAINED SOURCE / ${esc(path)}</div>`;
  }
  function sourcePage(path) {
    const src=D.sources[path];if(!src)return notFound();
    state.title=path.split("/").pop();
    return `${heading("SOURCE FILE",state.title,"The version included in Toolroom. Provenance and imported revisions are recorded in the source index.")}<div class="article-toolbar"><a href="#${D.documents[path]?"read/"+esc(path):"knowledge"}">← Back to reading view</a><button data-copy="${esc(path)}">Copy content</button><a href="${esc(path)}" download>Download file ↓</a></div><h2 class="source-title">${esc(path)}</h2><pre class="source-pre"><code>${esc(src.text)}</code></pre>`;
  }
  function notFound() { state.title="Page not found";return `${heading("404 / NOT IN THE CATALOGUE","This page is not in Toolroom.","Use search or the knowledge base to find available content.")}<a class="button" href="#overview">Back to overview →</a>`; }

  function route() {
    let hash;
    try { hash=decodeURI(location.hash.slice(1)||"overview"); }
    catch { hash="invalid"; }
    const [routePath,anchor]=hash.split("::");state.route=routePath;
    const [section,...parts]=routePath.split("/");const path=parts.join("/");
    let nav=section;state.title=navNames[section]||"Documentation";
    const pages={overview,architecture,skills,knowledge,profiles,labs,roadmap};
    if(pages[section])main.innerHTML=pages[section]();
    else if(section==="lab"){main.innerHTML=labPage(path);nav="labs";}
    else if(section==="evidence"){main.innerHTML=labPage("checker-lab");nav="labs";}
    else if(section==="read"||section==="source"){
      main.innerHTML=section==="read"?readPage(path):sourcePage(path);
      nav=navFor(path);
    } else main.innerHTML=notFound();
    $("#breadcrumb").textContent=state.title;
    document.title=`${state.title} — Toolroom`;
    document.querySelectorAll("[data-nav]").forEach(a=>a.dataset.nav===nav?a.setAttribute("aria-current","page"):a.removeAttribute("aria-current"));
    syncTree(nav,routePath);
    closeMenu();
    main.querySelectorAll("table").forEach(t=>{const wrapper=document.createElement("div");wrapper.className="table-wrap";t.replaceWith(wrapper);wrapper.append(t);});
    main.querySelectorAll("a[href^='http']").forEach(a=>{a.target="_blank";a.rel="noopener noreferrer";});
    if(anchor){requestAnimationFrame(()=>document.getElementById(anchor)?.scrollIntoView());}
    else {window.scrollTo({top:0,behavior:"instant"});main.focus({preventScroll:true});}
  }

  function showToast(text){const t=$("#toast");t.textContent=text;t.classList.add("visible");clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>t.classList.remove("visible"),2400);}
  async function copySource(path){
    const text=D.sources[path]?.text;if(text==null)return;
    try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);else{const t=document.createElement("textarea");t.value=text;t.style.position="fixed";t.style.left="-9999px";document.body.append(t);t.select();const ok=document.execCommand("copy");t.remove();if(!ok)throw Error("copy");}showToast("Content copied");}catch{showToast("Copy is unavailable — download the source file.");}
  }
  const mobileNav=matchMedia("(max-width:740px)");
  function openMenu(){ $("#sidebar").inert=false;$("#sidebar").classList.add("open");$("#nav-scrim").hidden=false;$("#menu-toggle").setAttribute("aria-expanded","true");$(".shell").inert=mobileNav.matches;$("#sidebar nav a").focus(); }
  function closeMenu(){ $("#sidebar").classList.remove("open");$("#sidebar").inert=mobileNav.matches;$(".shell").inert=false;$("#nav-scrim").hidden=true;$("#menu-toggle").setAttribute("aria-expanded","false"); }
  mobileNav.addEventListener("change",closeMenu);
  $("#menu-toggle").addEventListener("click",()=>$("#sidebar").classList.contains("open")?closeMenu():openMenu());
  $("#nav-scrim").addEventListener("click",closeMenu);
  $(".skip-link").addEventListener("click",e=>{e.preventDefault();main.focus();main.scrollIntoView();});

  const articleEntries=new Map(D.knowledge.articles.map(a=>[a.path,a]));
  const searchDocs=Object.entries(D.documents).map(([path,doc])=>{
    const entry=articleEntries.get(path);
    const title=entry?.title||doc.title;
    return {path,...doc,title,index:normalize(title+" "+(entry?.summary||"")+" "+doc.title+" "+path+" "+doc.plain)};
  });
  function search(){
    const term=normalize($("#search-input").value.trim());
    const matches=term?searchDocs.filter(d=>d.index.includes(term)).sort((a,b)=>Number(normalize(b.title).includes(term))-Number(normalize(a.title).includes(term))):searchDocs.filter(d=>articleEntries.has(d.path));
    $("#search-results").innerHTML=matches.length?matches.slice(0,14).map(d=>`<a class="search-result" href="#read/${esc(d.path)}" data-search-result><span>${esc(d.path)}</span><strong>${esc(d.title)}</strong><p>${esc(d.plain.replace(/^.*?\n/,"").slice(0,145))}…</p></a>`).join(""):'<div class="empty-state">No results. Try another term, such as “fit” or “support”.</div>';
  }
  function openSearch(){search();$("#search-dialog").showModal();$("#search-input").focus();}
  $("#search-open").addEventListener("click",openSearch);$("#search-input").addEventListener("input",search);
  $("#search-results").addEventListener("click",e=>{if(e.target.closest("[data-search-result]"))$("#search-dialog").close();});

  let notes={};let persistent=true;let noteRoute="";
  try{const parsed=JSON.parse(localStorage.getItem("toolroom-notes-v1")||"{}");if(parsed&&typeof parsed==="object"&&!Array.isArray(parsed))notes=parsed;}catch{persistent=false;}
  function openNotes(){noteRoute=state.route;$("#notes-context").textContent=`Topic: ${state.title}`;$("#notes-input").value=notes[noteRoute]?.text||"";$("#notes-status").textContent=persistent?"Notes stay in this browser. Export them to share.":"Persistent storage is unavailable here. Please export your notes.";$("#notes-dialog").showModal();$("#notes-input").focus();}
  $("#notes-open").addEventListener("click",openNotes);
  $("#notes-input").addEventListener("input",()=>{
    const text=$("#notes-input").value;if(text.trim())notes[noteRoute]={title:state.title,text};else delete notes[noteRoute];
    try{localStorage.setItem("toolroom-notes-v1",JSON.stringify(notes));$("#notes-status").textContent="Saved in this browser. Export the notes to share.";}catch{$("#notes-status").textContent="Saved for this session only. Please export your notes.";persistent=false;}
  });
  $("#notes-export").addEventListener("click",()=>{
    const entries=Object.entries(notes).filter(([,v])=>v&&typeof v.text==="string"&&v.text.trim());if(!entries.length){showToast("No notes yet.");return;}
    const text="# Toolroom — Discussion notes\n\n"+entries.map(([r,n])=>`## ${n.title}\n\nTopic: #${r}\n\n${n.text}\n`).join("\n");
    const url=URL.createObjectURL(new Blob([text],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="toolroom-discussion-notes.md";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);showToast("Notes exported");
  });
  document.addEventListener("click",e=>{
    if(e.target.closest("#sidebar a"))closeMenu();
    const close=e.target.closest("[data-close]");if(close)document.getElementById(close.dataset.close)?.close();
    const copy=e.target.closest("[data-copy]");if(copy)copySource(copy.dataset.copy);
    if(e.target.closest("[data-action='notes']"))openNotes();
    const joint=e.target.closest("[data-joint]");
    const pose=e.target.closest("[data-joint-pose]");
    if(joint||pose){
      if(joint)state.joint=joint.dataset.joint;
      if(pose)state.jointPose=pose.dataset.jointPose;
      document.querySelectorAll("[data-joint]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.joint===state.joint));
      document.querySelectorAll("[data-joint-pose]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.jointPose===state.jointPose));
      $("#joint-view").innerHTML=jointView();
      $("#joint-announcement").textContent=state.joint+": "+(state.jointPose==='assembled'?'assembled state':'separated parts');
    }
    const filter=e.target.closest("[data-filter]");if(filter){state.filter=filter.dataset.filter;document.querySelectorAll("[data-filter]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.filter===state.filter));$("#skill-grid").innerHTML=skillCards();$("#filter-count").textContent=`${D.modules.filter(m=>state.filter==="all"||m.category===state.filter).length} ENTRIES`;}
    const layer=e.target.closest("[data-layer]");if(layer){state.layer=Number(layer.dataset.layer);document.querySelectorAll("[data-layer]").forEach(b=>b.setAttribute("aria-pressed",Number(b.dataset.layer)===state.layer));$("#arch-detail").innerHTML=layerDetail();}
    const lab=e.target.closest("[data-lab]");if(lab){state.lab=lab.dataset.lab;document.querySelectorAll("[data-lab]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.lab===state.lab));$("#lab-results").innerHTML=labResults();}
  });
  document.addEventListener("change",e=>{if(e.target.id==="style-select"||e.target.id==="process-select"){state.style=$("#style-select").value;state.process=$("#process-select").value;$("#workbench-visual").innerHTML=schematic();$("#profile-detail").innerHTML=profileDetail();}});
  document.addEventListener("keydown",e=>{
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();if(!$("#search-dialog").open&&!$("#notes-dialog").open)openSearch();}
    if(e.key==="Escape"){
      const dialog=document.querySelector("dialog[open]");
      if(dialog){e.preventDefault();dialog.close();}
      else if($("#sidebar").classList.contains("open")){closeMenu();$("#menu-toggle").focus();}
    }
  });
  renderTree();
  window.addEventListener("hashchange",route);
  route();
})();
