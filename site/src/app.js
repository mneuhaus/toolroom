/* Static, offline documentation. Generated content is in site/data.js. */
(() => {
  "use strict";
  const D = window.CAD_DATA;
  const main = document.getElementById("main");
  if (!D) { main.innerHTML = '<h1>Documentation did not load</h1><p>Open the complete framework folder, including site/data.js.</p>'; return; }
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const normalize = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const categories = {workflow:"Workflow",cad:"CAD integration",construction:"Construction",manufacturing:"Manufacturing",design:"Design",documentation:"Documentation",reconstruction:"Reconstruction"};
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
    "scan-reverse-engineering":"Convert raw scans into justified functional CAD geometry. Check shape assumptions against the surfaces."
  };
  const navNames = {overview:"Overview",architecture:"Architecture",skills:"Skill library",examples:"In practice",profiles:"Profile workbench",evidence:"Verification lab",knowledge:"Knowledge base",roadmap:"Development",provenance:"Provenance & sources"};
  const state = {joint:"J06",jointPose:"separate",filter:"all",layer:0,style:"instrument",process:"fdm",lab:"solid",route:"overview",title:"Overview"};
  const pill = (label, cls="") => `<span class="pill ${cls}">${esc(label)}</span>`;
  const readLink = (path, label, cls="text-link") => `<a class="${cls}" href="#read/${esc(path)}">${esc(label)} <span aria-hidden="true">↗</span></a>`;
  const heading = (num, title, text) => `<div class="page-heading"><span class="eyebrow accent">${esc(num)}</span><h1 tabindex="-1">${esc(title)}</h1><p>${esc(text)}</p></div>`;
  const note = (text) => `<div class="wide-note"><span aria-hidden="true">↳</span><p>${text}</p></div>`;

  function overview() {
    return `<div class="page-meta">${pill("LOCAL WORKING EDITION", "warm")}<span class="eyebrow" style="margin:0;font-size:9px">KNOWLEDGE FROM 27 PROJECT & TOOL FOLDERS</span></div>
      <section class="hero"><div class="hero-copy"><span class="eyebrow accent">A SHARED TOOLKIT</span><h1 tabindex="-1">From idea<br>to part<span style="color:var(--accent)">.</span></h1><p>CAD knowledge that fits together. Construction, manufacturing and design, connected through traceable checks and real project examples.</p><div class="hero-actions"><a class="button" href="#architecture">Explore the framework <span>↗</span></a><a class="text-link" href="#examples">View examples <span>→</span></a></div></div><div class="hero-visual"><div class="drawing-meta"><span>SPARKY / R14</span><span>FIG. 001</span></div><img src="site/assets/sparky-after.png" alt="Rear view of the Sparky X/Z unit: light structure, graphite carriers and an orange control" width="1440" height="1080"><div class="hero-ticks" aria-hidden="true"><span>+</span><span>+</span></div><div class="drawing-caption"><span>FUNCTIONAL DESIGN LANGUAGE<br>NATIVE CAD GEOMETRY</span><a href="#case/sparky" aria-label="Open the Sparky case study">↗</a></div></div></section>
      <div class="stats-line"><div class="stat"><strong>${String(D.modules.length).padStart(2,"0")}</strong><span>composable skills</span></div><div class="stat"><strong>${String(D.cases.length).padStart(2,"0")}</strong><span>practical case studies</span></div><div class="stat"><strong>05</strong><span>shared layers</span></div></div>
      <div class="section-head"><h2>A good starting point</h2><span>READ · UNDERSTAND · DISCUSS</span></div>
      <div class="entry-grid"><a class="entry-card" href="#skills"><span class="eyebrow">01 /</span><h3>The right knowledge<br>for the task.</h3><p>Short skill entrypoints, specific technical references and clearly identified tool integrations.</p><div class="card-bottom"><span>SKILL LIBRARY</span><span class="arrow">↗</span></div></a><a class="entry-card" href="#profiles"><span class="eyebrow">02 /</span><h3>Give design<br>its own place.</h3><p>Combine design language and manufacturing while protecting mechanical interfaces.</p><div class="card-bottom"><span>PROFILE WORKBENCH</span><span class="arrow">↗</span></div></a><a class="entry-card" href="#evidence"><span class="eyebrow">03 /</span><h3>Evidence gives<br>results meaning.</h3><p>Four actual test cases show what the shared geometry checker detects.</p><div class="card-bottom"><span>VERIFICATION LAB</span><span class="arrow">↗</span></div></a></div>
      ${note('This edition brings current sources together for discussion. For locally verified helpers and separate CAD runtimes, see <a href="#read/docs/scope.md">Scope & maturity</a>.')}`;
  }

  const layers = [
    {title:"Core",headline:"A shared understanding of the project.",text:"Source, revision, units and part identity connect the handoffs. The current native design may contain more than its original generator.",items:["Authoritative source and protected interfaces","Native, assembly and print coordinates","Bind evidence to revision and inputs"],example:"Sparky: styling must preserve the established wheel stack and X travel.",doc:"knowledge/core.md"},
    {title:"Skills",headline:"An entrypoint for the specific task.",text:"A skill describes selection, working practice and relevant limits. Load detailed API and technical references when needed.",items:["Short entrypoints with clear scope","Shared technical rules in one place","Task-specific branches without a mandatory full pipeline"],example:"A PDF layout change uses the existing recipe and does not require regenerating CAD.",doc:"skills/cad-workflow/SKILL.md"},
    {title:"Integrations",headline:"Each tool keeps its strengths.",text:"Onshape, Build123d and Fusion have different source and execution models. Each integration handles its specific operations and failure modes.",items:["Preserve native user features","Resolve uncertain writes before retrying","Check return values and resulting artefacts"],example:"Onshape: uploading FeatureScript does not automatically update a reference pinned to a microversion.",doc:"docs/scope.md"},
    {title:"Profiles",headline:"Parameters with clear ownership.",text:"Design language, manufacturing process and mechanical interfaces are three independent profiles. Historical preferences remain identifiable.",items:["Colour roles, selected edges and labelling","Actual material, machine and print orientation","Separate calibrated data from starting values"],example:"The file trolley export already compensates for kerf. A second CAM offset would apply it twice.",doc:"profiles/README.md"},
    {title:"Evidence",headline:"Observable behaviour with specific evidence.",text:"CAD, assembly, slicer, simulation and physical tests answer different questions. Their results remain visible separately.",items:["Preserve original inputs and raw findings","Explicitly identify incomplete analysis","Reproduce small known failure cases"],example:"A narrow unsupported underside still needs an anchor. The shared checker includes this failure case.",doc:"knowledge/verification.md"}
  ];

  function architecture() {
    return `${heading("02 / CONNECTIONS", "Five layers. One shared workflow.", "Combine the building blocks to suit the task. Select a layer to explore its role.")}
      <div class="arch-grid" aria-label="Framework layers">${layers.map((l,i)=>`<button class="arch-step" data-layer="${i}" aria-pressed="${state.layer===i}"><span class="number">0${i+1} /</span><strong>${l.title}</strong></button>`).join("")}</div><section id="arch-detail" class="arch-detail" aria-live="polite">${layerDetail()}</section>
      <div class="section-head"><h2>For example: revise a mount</h2></div><div class="flow-line"><span>Task & interfaces</span><i>→</i><span>Onshape</span><i>+</i><span>Design-System</span><i>+</i><span>FDM</span><i>→</i><span>CAD & manufacturing evidence</span></div>
      ${note('A layout change, a scan and a new design need different branches. <a href="#read/knowledge/recipes.md">Six practical task recipes</a> explain the selection.')}
      <div class="section-head"><h2>Architecture in detail</h2></div>${readLink("docs/architecture.md","Read about responsibilities, maintained sources and limits")}`;
  }
  function layerDetail() {
    const l=layers[state.layer];
    return `<div><span class="eyebrow accent">LAYER 0${state.layer+1}</span><h3>${l.headline}</h3><p>${l.text}</p>${readLink(l.doc,"Read more")}</div><div class="scope-box"><span class="eyebrow">BELONGS HERE</span><ul>${l.items.map(x=>`<li>${x}</li>`).join("")}</ul><p style="font-size:12px">${l.example}</p></div>`;
  }

  function skillCards() {
    const list=D.modules.filter(m=>state.filter==="all"||m.category===state.filter);
    return list.map(m=>`<a class="skill-card" href="#read/${esc(m.document)}"><div class="skill-card-top"><span class="skill-icon" aria-hidden="true">${({workflow:"⌁",cad:"⌑",construction:"⊏",manufacturing:"≋",design:"◐",documentation:"▤",reconstruction:"⋈"})[m.category]}</span>${pill(categories[m.category])}</div><h2>${esc(m.title)}</h2><p>${esc(summaries[m.id])}</p><div class="skill-card-footer"><span>${m.state==="local-tools"?"WITH LOCAL HELPERS":"CURATED KNOWLEDGE"}</span><span>↗</span></div></a>`).join("");
  }
  function skills() {
    return `${heading("03 / SKILL LIBRARY", "The knowledge is now in one place.", "Ten short entrypoints connect the existing capabilities. Detailed references and practical helpers remain directly accessible.")}
      <div class="filter-bar" aria-label="Filter skills by area"><button class="filter-chip" data-filter="all" aria-pressed="${state.filter==="all"}">All skills</button>${Object.entries(categories).map(([id,title])=>`<button class="filter-chip" data-filter="${id}" aria-pressed="${state.filter===id}">${title}</button>`).join("")}<span id="filter-count" class="filter-count" role="status">${D.modules.filter(m=>state.filter==="all"||m.category===state.filter).length} ENTRIES</span></div><div class="skill-grid" id="skill-grid">${skillCards()}</div>
      ${note('All maintained documentation uses English. Shared rules, examples and context are collected in the <a href="#knowledge">knowledge base</a>.')}`;
  }

  function examples() {
    return `${heading("04 / IN PRACTICE", "Lessons that carry a project forward.", "Eight case studies show where the shared knowledge comes from. Each distinguishes method, evidence and the reusable rule.")}
      <div class="case-grid">${D.cases.map((c,i)=>`<a class="case-card" href="#case/${c.id}"><div class="case-image"><img src="${c.image}" alt="${esc(D.assets.find(a=>a.file===c.image)?.caption||c.title)}" loading="lazy"><span class="case-tag">${esc(c.tag)}</span></div><span class="eyebrow">0${i+1} / ${esc(c.project)}</span><h2>${esc(c.title)} <span style="color:var(--accent)">↗</span></h2><p>${esc(c.summary)}</p></a>`).join("")}</div>`;
  }
  function casePage(id) {
    const c=D.cases.find(x=>x.id===id);
    if(!c) return notFound();
    if(id==="printed-joints") return jointsPage(c);
    state.title=c.project;
    const doc=D.documents[c.document];
    const compare=id==="sparky"?`<section class="compare-section"><span class="eyebrow accent">SAME CAMERA · ACTUAL CAD GEOMETRY</span><h2>Compare R13 and R14 directly</h2><div class="compare" id="compare" style="--split:50%"><img src="site/assets/sparky-after.png" alt="Sparky R14, revised rear view"><img class="before" src="site/assets/sparky-before.png" alt="Sparky R13, previous rear view"><div class="compare-line"></div><div class="compare-labels"><span>R13 / BEFORE</span><span>R14 / AFTER</span></div></div><div class="range-row"><label for="compare-range">Move the comparison slider</label><input type="range" id="compare-range" min="0" max="100" value="50" aria-label="Proportion of the before view"><output id="compare-value">50 %</output></div></section>`:"";
    const second=id==="c2"?`<section class="compare-section"><span class="eyebrow accent">FROM THE ACTUAL MANUAL</span><h2>Build stages become readable pages</h2><img src="site/assets/c2-page.png" alt="Page 4 of the C2 assembly guide with CAD illustrations and part quantities" loading="lazy" style="outline:1px solid rgba(0,0,0,.1);outline-offset:-1px"></section>`:"";
    return `${heading("CASE STUDY / "+c.project,c.title,c.summary)}<div class="case-hero"><div class="case-image"><img src="${c.image}" alt="${esc(D.assets.find(a=>a.file===c.image)?.caption||c.title)}"></div><div class="case-facts"><span class="eyebrow accent">THE RECIPE</span><h3>${esc(c.tag)}</h3><p>These skills work together in this example:</p><div>${c.skills.map(id=>`<a href="#read/skills/${id}/SKILL.md">${pill(D.modules.find(m=>m.id===id)?.title||id)}</a>`).join("")}</div><p style="margin-top:15px;font-size:12px">The image comes from the recorded project revision. Translated labels are documented in provenance. The text explains the original verification scope and remaining questions.</p><a class="text-link" href="#examples">← All case studies</a></div></div>${compare}<div class="article-shell"><article class="article">${doc?.body||""}</article>${toc(doc,c.document)}</div>${second}<div class="source-reference">SOURCE: ${esc(c.source)}<br>SHA-256: ${esc(c.source_sha256)}</div>`;
  }

  function jointView() {
    const j=D.joints.find(j=>j.id===state.joint);
    return `<figure class="joint-figure"><img src="${j[state.jointPose]}" width="1100" height="650" alt="${esc(j.title)}: native Onshape render, ${state.jointPose==='separate'?'separated parts':'assembled state'}"><figcaption>${esc(j.id)} · NATIVE ONSHAPE RENDER · ${state.jointPose==='separate'?'SEPARATED PARTS':'ASSEMBLED'}</figcaption></figure><div class="joint-detail"><span class="eyebrow accent">${esc(j.tag)}</span><h2>${esc(j.title)}</h2><p>${esc(j.description)}</p><dl><dt>Assembly path</dt><dd>${esc(j.assembly)}</dd><dt>Geometry</dt><dd>${esc(j.parameters)}</dd></dl><p class="joint-limit">${esc(j.limits)}</p><div class="joint-links"><a class="button" href="${j.onshape}" target="_blank" rel="noopener">Open in Onshape ↗</a><a class="text-link" href="${j.step}" download>STEP ↓</a><a class="text-link" href="${j.source}" target="_blank" rel="noopener">Video timestamp ↗</a></div></div>`;
  }
  function jointsPage(c) {
    state.title=c.project;
    const doc=D.documents[c.document];
    return `${heading("JOINTS / PRINTED JOINTS LAB",c.title,c.summary)}<div class="joint-switch" role="group" aria-label="Select a joint principle">${D.joints.map(j=>`<button data-joint="${j.id}" aria-pressed="${state.joint===j.id}"><span>${j.id}</span>${esc(j.title)}</button>`).join('')}</div><section class="joint-lab" aria-label="Native model comparison"><div class="joint-toolbar"><span class="eyebrow">BLUE / A · ORANGE / B · OCHRE / WEDGES</span><div role="group" aria-label="Model view"><button class="filter-chip" data-joint-pose="assembled" aria-pressed="${state.jointPose==='assembled'}">Assembled</button><button class="filter-chip" data-joint-pose="separate" aria-pressed="${state.jointPose==='separate'}">Separate parts</button></div></div><div id="joint-view">${jointView()}</div><span id="joint-announcement" class="joint-announcement" role="status"></span></section>${note('16 native models, eight STEP exports and checked discrete assembly paths. Printing, measured fit and strength remain open. The separated views do not define print orientation.')}<div class="article-shell"><article class="article">${doc.body}</article>${toc(doc,c.document)}</div>`;
  }

  const styles={
    instrument:{title:"Instrument",colors:["#cecdc7","#535953","#ed602f"],radius:3,description:"Light structure, dark functional parts and a restrained accent. Short labels and deliberate facets.",path:"profiles/design-language/te-like.yaml",key:"01 / adjust"},
    soft:{title:"Soft Consumer",colors:["#dedfce","#a4ae95","#626b51"],radius:23,description:"Softer transitions and calm surfaces. Functional contacts retain their original geometry.",path:"profiles/design-language/soft-consumer.yaml",key:"Adjust"},
    rugged:{title:"Rugged Industrial",colors:["#717866","#313a31","#e5b044"],radius:2,description:"Substantial visible structure and contrasting control areas. Appearance alone establishes no additional strength.",path:"profiles/design-language/rugged-industrial.yaml",key:"ADJUST / 01"},
    workshop:{title:"Workshop 0.42",colors:["#dddcd4","#6c7267","#d57047"],radius:10,description:"The historical 0.42/4.2 edge family: flush transitions and continuous contours. A distinct style profile.",path:"profiles/design-language/workshop-042.yaml",key:"WORKSHOP"},
    mosey:{title:"Mosey",colors:["#BDD1BA","#F0EDDF","#C6B6D7"],radius:28,ink:"#383D3A",description:"Calm sculptural bodies, large tactile controls and functional colour fields. The soft variant is shown here; broad facets and useful supporting shells also belong to the language. Derived from concept images, not yet calibrated.",path:"profiles/design-language/mosey.yaml",document:"docs/design-languages/mosey.md",key:"turn"}
  };
  const processes={
    fdm:{title:"FDM",caption:"PRINT ORIENTATION · LAYERS · SUPPORT",detail:"Bed contact and layer direction define the assessment. Local walls, attachments and actual slicer paths are checked separately.",state:"Widely documented project workflow",path:"profiles/manufacturing/fdm-bambu-a1-0.4.yaml"},
    laser:{title:"Laser cutting",caption:"MATERIAL THICKNESS · KERF · ASSEMBLY",detail:"Flat parts need a known material thickness and a single owner for kerf compensation. The file trolley provides a concrete export example.",state:"Concrete export example",path:"profiles/manufacturing/laser-diode-3mm.yaml"},
    cnc:{title:"CNC",caption:"TOOL · ACCESS · WORKHOLDING",detail:"Tool access, internal radii and workholding belong to the process. The framework includes references; a general CAM workflow remains open.",state:"Reference profile / further development",path:"profiles/manufacturing/cnc-small-hobby.yaml"},
    sla:{title:"SLA / MSLA",caption:"ORIENTATION · SUPPORTS · FINISHING",detail:"Existing profile values are generic starting points. The reviewed collection does not yet establish a calibrated resin and machine example.",state:"Uncalibrated reference profile",path:"profiles/manufacturing/sla-generic.yaml"}
  };
  function schematic() {
    const s=styles[state.style],p=processes[state.process];
    return `<div class="drawing-meta"><span>PROFILE / ${esc(s.title.toUpperCase())}</span><span>FIG. 002</span></div><svg viewBox="0 0 400 310" role="img" aria-label="Schematic part in the style ${esc(s.title)}; four unchanged mounting positions"><defs><pattern id="print-lines" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M0 5.5H6" stroke="#fff" stroke-opacity=".28" stroke-width=".8"/></pattern></defs><path d="M40 256H360M200 32V276" stroke="#aab1a1" stroke-width=".8" stroke-dasharray="3 5"/><rect x="68" y="64" width="264" height="174" rx="${s.radius}" fill="${s.colors[1]}" stroke="#1f291d" stroke-opacity=".35"/><rect x="68" y="55" width="264" height="174" rx="${s.radius}" fill="${s.colors[0]}" stroke="#333a2f" stroke-opacity=".6" stroke-width="1"/>${state.process==="fdm"?`<rect x="69" y="56" width="262" height="172" rx="${s.radius}" fill="url(#print-lines)"/>`:""}${[[95,81],[305,81],[95,203],[305,203]].map(([x,y])=>`<g class="fixed-interface"><circle cx="${x}" cy="${y}" r="8" fill="#f4f3ef" stroke="#59664b"/><path d="M${x-12} ${y}h24M${x} ${y-12}v24" stroke="#809271" stroke-width=".8"/></g>`).join("")}<rect x="114" y="106" width="172" height="68" rx="${Math.min(s.radius,10)}" fill="${s.colors[1]}"/><path d="M130 122h43M130 132h27M130 150h78" stroke="${s.ink||s.colors[0]}" stroke-width="2" opacity=".7"/><circle cx="254" cy="140" r="${state.style==="mosey"?26:20}" fill="${s.colors[2]}"/><path d="M254 126v10" stroke="#fff" stroke-width="2" opacity=".8"/><text x="119" y="195" fill="${s.ink||(state.style==="rugged"?'#fff':s.colors[1])}" font-size="10" font-family="monospace">${esc(s.key)}</text><path d="M48 55v174M43 55h10M43 229h10M95 248h210M95 243v10M305 243v10" stroke="#939e85" stroke-width=".8"/><text x="200" y="279" text-anchor="middle" fill="#66715a" font-family="monospace" font-size="9">4 MOUNTING POSITIONS / PROTECTED</text></svg><p class="schematic-caption">SCHEMATIC COMPARISON · NOT CAD OR MANUFACTURING EVIDENCE</p>`;
  }
  function profileDetail() {
    const s=styles[state.style],p=processes[state.process];
    return `<h3>${esc(s.title)} × ${esc(p.title)}</h3><p>${esc(s.description)}</p><p>${esc(p.detail)}</p><div class="palette" aria-label="Illustrative colour palette">${s.colors.map(c=>`<span style="background:${c}" title="${c}"></span>`).join("")}</div><p style="margin-top:13px;font-family:var(--mono);font-size:9px">${esc(p.state)}</p>${s.document?`<a class="text-link" href="#read/${s.document}">Interpretation with examples ↗</a><br>`:""}<a class="text-link" href="#source/${s.path}">Read style profile ↗</a> <a class="text-link" href="#source/${p.path}">Read manufacturing profile ↗</a>`;
  }
  function profiles() {
    return `${heading("05 / PROFILE WORKBENCH", "One language. Several manufacturing paths.", "Explore the independent roles of design and manufacturing. Schematic palettes illustrate the idea; the original profiles remain separately readable.")}
      <div class="workbench"><div id="workbench-visual" class="workbench-visual">${schematic()}</div><div class="profile-controls"><div class="control-group"><label class="field-label" for="style-select">01 / Design Language</label><select id="style-select">${Object.entries(styles).map(([id,s])=>`<option value="${id}" ${id===state.style?"selected":""}>${s.title}</option>`).join("")}</select></div><div class="control-group"><label class="field-label" for="process-select">02 / Manufacturing process</label><select id="process-select">${Object.entries(processes).map(([id,p])=>`<option value="${id}" ${id===state.process?"selected":""}>${p.title}</option>`).join("")}</select></div><div class="profile-detail" id="profile-detail" aria-live="polite">${profileDetail()}</div><div class="locked-profile"><strong>03 / Interfaces remain protected.</strong><br>The four mounts remain unchanged across styles. A different profile does not authorise changes to function or assembly.</div></div></div>
      <div class="profile-cards"><div><span class="eyebrow accent">DESIGN</span><h3>What form supports the function?</h3><p>Colour roles, selected edges, labelling and recurring elements.</p></div><div><span class="eyebrow accent">MANUFACTURING</span><h3>How is the part manufactured?</h3><p>Machine, material, orientation and explicitly marked verification limits.</p></div><div><span class="eyebrow accent">INTERFACES</span><h3>What must be preserved?</h3><p>Fits, purchased parts, load paths, movement clearance and tool access.</p></div></div>
      <section class="language-feature"><img src="site/assets/mosey-family.svg" alt="Three original Mosey illustrations: soft hand controller, faceted desktop stand and tray with a supporting shell" width="1080" height="410" loading="lazy"><div><span class="eyebrow accent">NEW DESIGN LANGUAGE / MOSEY 0.1</span><h2>Calm form. Tactile controls.</h2><p>18 reference images, three form variants and an original application to other objects. Observations remain distinct from proposed CAD values.</p><a class="text-link" href="#read/docs/design-languages/mosey.md">Explore Mosey examples ↗</a></div></section>
      ${note('Generic starting profiles are <strong>not calibrated</strong>. Personal machine and style values retain their original scope. <a href="#read/profiles/README.md">Read profile conventions</a>.')}`;
  }

  const labIcons={solid:'<path d="m9 18 22-10 27 12-22 10Zm0 0v18l27 11 22-13V20M36 30v17"/>',thin:'<path d="m9 25 22-10 27 12-22 10Zm0 0v4l27 11 22-9v-4M36 37v3"/>',orientation:'<path d="M5 36h52V12H5Zm13-15h45v17H18Z"/><path d="m52 7 8-2 5 5" fill="none"/>',island:'<path d="m3 32 17-7 22 9-18 8Zm0 0v5l21 9 18-8v-4M49 8l9-4 6 4-9 4Zm0 0v17l6 4 9-5V8M55 12v17"/>'};
  function labResults() {
    const s=D.lab.find(x=>x.id===state.lab);if(!s)return '<p>The example report has not been generated yet.</p>';
    const r=D.reports[s.report];
    const format = v => typeof v==="number" ? new Intl.NumberFormat("en-GB",{maximumFractionDigits:2}).format(v) : v;
    return `<div><span class="eyebrow accent">ACTUAL LOCAL PROGRAM OUTPUT</span>${pill(r.status,r.status==="no_findings"?"green":"warm")}<h3>${esc(s.title)}</h3><p>${({solid:"The block meets the selected check conditions. This result applies to the small test body and stated scope.",thin:"The 0.4 mm plate remains a structural body and produces a wall-thickness finding.",orientation:"16 × 9 mm does not fit the specified 10 × 20 mm footprint. A hypothetical quarter-turn is reported separately.",island:"The narrow unsupported underside is not assumed to be a printable lip. Its missing attachment remains visible."})[state.lab]}</p><div class="article-toolbar"><a href="#source/${s.report}">Full JSON report ↗</a><a href="${s.mesh}" download>Test-STL ↓</a></div></div><div><div class="metric"><span>Analysis complete</span><strong>${r.analysis_complete?"yes":"no"}</strong></div><div class="metric"><span>Connected bodies</span><strong>${r.connected_components}</strong></div><div class="metric"><span>Dimensions in mm</span><strong>${r.bounds.extents_xyz.map(format).join(" × ")}</strong></div><div class="metric"><span>Fits in the supplied orientation</span><strong>${r.bounds.fits_build_volume?"yes":"no"}</strong></div><div class="metric"><span>Findings</span><strong>${r.problems.length}</strong></div>${r.problems.length?`<ul>${r.problems.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:'<p style="margin-top:18px">No findings within the configured screening scope.</p>'}</div>`;
  }
  function evidence() {
    const evidenceTypes=[["01","Native geometry","Bodies, dimensions and protected interfaces."],["02","Assembly & movement","Examined insertion paths, tool access and poses."],["03","Slicer & layers","Actual deposited paths for the selected profile."],["04","Simulation","Behaviour under documented modelling assumptions."],["05","Physical test","Measurement on the manufactured specimen."],["06","Artefact verification","Correct source, complete output and unchanged bytes."]];
    return `${heading("06 / VERIFICATION LAB", "What does a checker actually detect?", "Four small geometries, four traceable results. Reports were generated locally with the consolidated mesh checker and can be inspected in full.")}
      <div class="lab-grid" aria-label="Select a test case">${D.lab.map(s=>`<button class="lab-card" data-lab="${s.id}" aria-pressed="${state.lab===s.id}"><svg viewBox="0 0 70 50" aria-hidden="true">${labIcons[s.id]}</svg><strong>${esc(s.title)}</strong>${pill(s.status==="no_findings"?"NO FINDINGS":"FINDING",s.status==="no_findings"?"green":"warm")}</button>`).join("")}</div><div class="lab-results" id="lab-results" aria-live="polite">${labResults()}</div>
      ${readLink("examples/checker-lab/README.md","Run the example yourself")}
      <div class="section-head"><h2>Several checks. Different questions.</h2></div><div class="evidence-types">${evidenceTypes.map(([n,t,p])=>`<div><span class="eyebrow accent">${n} /</span><h3>${t}</h3><p>${p}</p></div>`).join("")}</div>${readLink("knowledge/verification.md","Understand verification scope and result states")}`;
  }

  const knowledgePages=[
    ["docs/joints/additional-references.md","Panels and elastic clips","Four additional video references, source dimensions and the limits of rigid assembly checks.","JOINTS"],
    ["knowledge/joints.md","Joints — how connections hold","Interlocking, assembly paths, clearance, print coupons and eight native examples.","JOINTS"],
    ["knowledge/core.md","The shared core","Source, identity, units and rule precedence.","FOUNDATIONS"],
    ["knowledge/recipes.md","Combine tasks","Six paths from a task to suitable skills and results.","WORKFLOW"],
    ["knowledge/assembly-review.md","Assembly before detailed design","Screws, purchased parts, tool corridors and preassemblies.","CONSTRUCTION"],
    ["knowledge/fits-and-retention.md","Fit, preload and snap retention","Consider rigid guidance and elastic retention separately.","CONSTRUCTION"],
    ["knowledge/construction-patterns.md","Reusable patterns","Joints, sliding guides, crush ribs and shared parts.","CONSTRUCTION"],
    ["knowledge/print-preparation.md","Slicer profiles and toolpaths","Inheritance, includes, supports and actual deposited material.","MANUFACTURING"],
    ["knowledge/verification.md","What a check establishes","Coverage, raw findings and incomplete analyses.","EVIDENCE"],
    ["knowledge/project-layout.md","Project layout and revisions","Keep sources, persistent state, cache and exports separate.","WORKFLOW"],
    ["profiles/README.md","Profiles with provenance","Maintain design, manufacturing and interfaces independently.","PROFILE"],
    ["docs/design-languages/mosey.md","Mosey — form and handling","Reference images, colour roles, three form variants and concrete CAD starting values.","DESIGN LANGUAGE"],
    ["docs/consolidation.md","Consolidation decisions","What was imported, consolidated and remains open.","FRAMEWORK"],
    ["docs/scope.md","Scope and maturity","Included helpers and separately installed runtimes.","FRAMEWORK"]
  ];
  function knowledge() {
    return `${heading("REFERENCE / KNOWLEDGE BASE", "The shared rules.", "The main concepts have a maintained source, backed by detailed skill references and traceable provenance.")}
    <div class="knowledge-list">${knowledgePages.map(([path,title,desc,cat],i)=>`<a class="knowledge-row" href="#read/${path}"><span class="idx">${String(i+1).padStart(2,"0")}</span><div><h3>${title}</h3><p>${desc}</p></div><span class="category">${cat}</span><span class="arrow">↗</span></a>`).join("")}</div>`;
  }

  function roadmap() {
    const done=[["One shared working edition","Ten short skill entrypoints, shared technical references and current sources."],["Geometry checks consolidated","Robust Sparky checks with Distributor rasterisation and anchored lip checks."],["Profile inheritance as a dedicated tool","Ordered includes, clear errors and a traceable resolution order."],["Practical examples","Eight case studies, four runnable test geometries and original CAD images."]];
    const next=[["Define maintenance boundaries","Which runtimes remain separate projects? Which helpers belong here permanently?"],["Choose a complete pilot case","Take a small independent model through construction, manufacturing and an assembly guide."],["Calibrate profiles physically","Which actual materials, machines and coupons establish our working values?"],["Define the public scope","Name, examples, our own licence and supported installations for a first release."]];
    return `${heading("DEVELOPMENT / DISCUSS TOGETHER", "A concrete foundation. Useful next questions.", "The first consolidation is ready to inspect. The next decisions concern scope and maintenance and can be discussed through the examples.")}
      <div class="roadmap-grid"><div class="roadmap-column"><span class="eyebrow accent">01 / IN THIS EDITION</span><h2>Already consolidated</h2>${done.map(([t,p])=>`<div class="roadmap-item"><span class="mark">✓</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join("")}</div><div class="roadmap-column"><span class="eyebrow">02 / NEXT</span><h2>Decide together</h2>${next.map(([t,p],i)=>`<div class="roadmap-item"><span class="mark">${i+1}</span><div><h3>${t}</h3><p>${p}</p></div></div>`).join("")}</div></div>
      <div class="discussion-card"><span class="eyebrow accent">NOTES WITH CONTEXT</span><h3>What should we organise differently?</h3><p>Record thoughts on each page in their context. Export collects the notes as Markdown for our next discussion.</p><button class="button" data-action="notes">Write a discussion note ↗</button></div>${readLink("docs/consolidation.md","Consolidation decisions in detail")}`;
  }

  function toc(doc,path) {
    if(!doc)return "";
    const entries=doc.headings.filter(x=>x.level>1&&x.level<4);
    if(!entries.length)return "";
    return `<aside class="toc" aria-label="Table of contents"><span class="eyebrow">ON THIS PAGE</span>${entries.map(h=>`<a class="${h.level===3?"toc-sub":""}" href="#read/${esc(path)}::${esc(h.id)}">${esc(h.title)}</a>`).join("")}</aside>`;
  }
  function readPage(path) {
    const doc=D.documents[path];if(!doc)return sourcePage(path);
    state.title=doc.title;
    return `<div class="article-toolbar"><a href="#${path.startsWith("skills/")?"skills":path.startsWith("examples/")?"examples":"knowledge"}">← Back to overview</a><button data-copy="${esc(path)}">Copy Markdown</button><a href="#source/${esc(path)}">View source file ↗</a><button data-action="notes">Note on this topic</button></div><div class="article-shell"><article class="article">${doc.html}</article>${toc(doc,path)}</div><div class="source-reference">MAINTAINED SOURCE / ${esc(path)}</div>`;
  }
  function sourcePage(path) {
    const src=D.sources[path];if(!src)return notFound();
    state.title=path.split("/").pop();
    return `${heading("SOURCE FILE",state.title,"The version included in the framework. Provenance and imported revisions are recorded in the source index.")}<div class="article-toolbar"><a href="#${D.documents[path]?"read/"+esc(path):"knowledge"}">← Back to reading view</a><button data-copy="${esc(path)}">Copy content</button><a href="${esc(path)}" download>Download file ↓</a></div><h2 class="source-title">${esc(path)}</h2><pre class="source-pre"><code>${esc(src.text)}</code></pre>`;
  }
  function notFound() { state.title="Page not found";return `${heading("404 / NOT IN THE CATALOGUE","This page is not in the framework.","Use search or the knowledge base to find available content.")}<a class="button" href="#overview">Back to overview →</a>`; }

  function route() {
    let hash;
    try { hash=decodeURI(location.hash.slice(1)||"overview"); }
    catch { hash="invalid"; }
    const [routePath,anchor]=hash.split("::");state.route=routePath;
    const [section,...parts]=routePath.split("/");const path=parts.join("/");
    let nav=section;state.title=navNames[section]||"Documentation";
    const pages={overview,architecture,skills,examples,profiles,evidence,knowledge,roadmap};
    if(pages[section])main.innerHTML=pages[section]();
    else if(section==="case"){main.innerHTML=casePage(path);nav="examples";}
    else if(section==="read"||section==="source"){
      main.innerHTML=section==="read"?readPage(path):sourcePage(path);
      nav=path.startsWith("skills/")?"skills":path.startsWith("examples/")?"examples":path.startsWith("profiles/")?"profiles":path==="docs/provenance.md"?"provenance":"knowledge";
    } else main.innerHTML=notFound();
    $("#breadcrumb").textContent=state.title;
    document.title=`${state.title} — CAD Skills`;
    document.querySelectorAll("[data-nav]").forEach(a=>a.dataset.nav===nav?a.setAttribute("aria-current","page"):a.removeAttribute("aria-current"));
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

  const searchDocs=Object.entries(D.documents).map(([path,doc])=>{
    const entry=knowledgePages.find(p=>p[0]===path);
    const title=entry?.[1]||doc.title;
    return {path,...doc,title,index:normalize(title+" "+(entry?.[2]||"")+" "+doc.title+" "+path+" "+doc.plain)};
  });
  function search(){
    const term=normalize($("#search-input").value.trim());
    const matches=term?searchDocs.filter(d=>d.index.includes(term)).sort((a,b)=>Number(normalize(b.title).includes(term))-Number(normalize(a.title).includes(term))):searchDocs.filter(d=>d.path.startsWith("knowledge/"));
    $("#search-results").innerHTML=matches.length?matches.slice(0,14).map(d=>`<a class="search-result" href="#read/${esc(d.path)}" data-search-result><span>${esc(d.path)}</span><strong>${esc(d.title)}</strong><p>${esc(d.plain.replace(/^.*?\n/,"").slice(0,145))}…</p></a>`).join(""):'<div class="empty-state">No results. Try another term, such as “fit” or “support”.</div>';
  }
  function openSearch(){search();$("#search-dialog").showModal();$("#search-input").focus();}
  $("#search-open").addEventListener("click",openSearch);$("#search-input").addEventListener("input",search);
  $("#search-results").addEventListener("click",e=>{if(e.target.closest("[data-search-result]"))$("#search-dialog").close();});

  let notes={};let persistent=true;let noteRoute="";
  try{const parsed=JSON.parse(localStorage.getItem("cad-framework-notes-v1")||"{}");if(parsed&&typeof parsed==="object"&&!Array.isArray(parsed))notes=parsed;}catch{persistent=false;}
  function openNotes(){noteRoute=state.route;$("#notes-context").textContent=`Topic: ${state.title}`;$("#notes-input").value=notes[noteRoute]?.text||"";$("#notes-status").textContent=persistent?"Notes stay in this browser. Export them to share.":"Persistent storage is unavailable here. Please export your notes.";$("#notes-dialog").showModal();$("#notes-input").focus();}
  $("#notes-open").addEventListener("click",openNotes);
  $("#notes-input").addEventListener("input",()=>{
    const text=$("#notes-input").value;if(text.trim())notes[noteRoute]={title:state.title,text};else delete notes[noteRoute];
    try{localStorage.setItem("cad-framework-notes-v1",JSON.stringify(notes));$("#notes-status").textContent="Saved in this browser. Export the notes to share.";}catch{$("#notes-status").textContent="Saved for this session only. Please export your notes.";persistent=false;}
  });
  $("#notes-export").addEventListener("click",()=>{
    const entries=Object.entries(notes).filter(([,v])=>v&&typeof v.text==="string"&&v.text.trim());if(!entries.length){showToast("No notes yet.");return;}
    const text="# CAD Skills — Discussion notes\n\n"+entries.map(([r,n])=>`## ${n.title}\n\nTopic: #${r}\n\n${n.text}\n`).join("\n");
    const url=URL.createObjectURL(new Blob([text],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="cad-skills-discussion-notes.md";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);showToast("Notes exported");
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
  document.addEventListener("input",e=>{if(e.target.id==="compare-range"){$("#compare").style.setProperty("--split",e.target.value+"%");$("#compare-value").textContent=e.target.value+" %";}});
  document.addEventListener("keydown",e=>{
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();if(!$("#search-dialog").open&&!$("#notes-dialog").open)openSearch();}
    if(e.key==="Escape"){
      const dialog=document.querySelector("dialog[open]");
      if(dialog){e.preventDefault();dialog.close();}
      else if($("#sidebar").classList.contains("open")){closeMenu();$("#menu-toggle").focus();}
    }
  });
  window.addEventListener("hashchange",route);
  route();
})();
