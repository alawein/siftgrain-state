"""Self-contained viewer enhancement. User data never enters executable source."""

import base64
import hashlib
import html
import json

from siftgrain_state._brand import LOGO

STYLE = """
body{background:var(--bg);color:var(--ink)}
.brand-mark{width:48px;height:48px;vertical-align:middle;margin-right:16px}
main{max-width:1200px;padding-top:24px}h1{font-family:Georgia,serif;font-size:clamp(2rem,5vw,4rem)}
.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;padding:16px 0}
.toolbar label{display:flex;gap:8px;align-items:center}.toolbar select,.toolbar button,input{
font:inherit;padding:10px;border:1px solid var(--muted);border-radius:8px;
background:var(--surface);color:var(--ink);min-height:44px}
.card,tbody tr,pre,.downloads a{background:var(--surface);color:var(--ink);
border-color:var(--muted)}caption,td:before,.metadata dt{color:var(--muted)}
a{color:var(--accent)}:focus-visible{outline:3px solid var(--accent);outline-offset:4px}
.cards{grid-template-columns:repeat(auto-fit,minmax(130px,1fr))}.card{border-radius:6px}
.st-confirmed{background:var(--surface);color:var(--pass)}
.st-contradicted{background:var(--surface);color:var(--fail)}
.st-unobserved,.st-unconfirmed{background:var(--surface);color:var(--pending)}
.timeline{list-style:none;padding:0;display:grid;gap:20px}.event{border:1px solid var(--muted);
border-inline-start:4px solid var(--accent);padding:20px;border-radius:8px;
background:var(--surface)}.event h3{margin:0 0 12px}.stages{display:grid;
grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.stages p{margin:0;overflow-wrap:anywhere}
.stages b{display:block}.event[data-status=confirmed]{border-inline-start-color:var(--pass);
animation:settle .45s both}.event[data-status=contradicted]{border-inline-start-color:var(--fail);
animation:shake .35s both}.event[data-status=unobserved]{border-style:dashed}
.event[data-status=unobserved] .stages{opacity:1}.event[data-status=unconfirmed]{
border-inline-start-color:var(--pending)}.event small{display:block;margin-top:12px}
[data-vibe=cartoon] .event,[data-vibe=cartoon] .card{border-radius:18px 24px 20px 16px;
box-shadow:5px 5px 0 var(--muted);animation-timing-function:cubic-bezier(.2,1.7,.4,1)}
[data-vibe=calm] .event{animation-duration:.8s}[data-vibe=pixel] *{border-radius:0!important}
[data-vibe=pixel] .hero{
background-image:repeating-conic-gradient(var(--surface) 0 25%,transparent 0 50%);
background-size:4px 4px}
[data-vibe=pixel] .event{animation-timing-function:steps(5)}[data-vibe=lab] main{max-width:1440px}
[data-vibe=lab] .event{padding:12px;animation-duration:.12s}[data-vibe=lab]{font-size:15px}
.hero{width:100%;height:80px;display:block;border-radius:8px;background:var(--surface)}
[hidden]{display:none!important}@keyframes settle{from{transform:translateY(8px)}
to{transform:translateY(0)}}@keyframes shake{25%{transform:translateX(-4px)}
75%{transform:translateX(4px)}}.hidden-page *, .paused *{animation:none!important;
transition:none!important}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}
.hero{display:none}}@media(max-width:600px){.stages{grid-template-columns:1fr}.toolbar{gap:8px}}
"""

BOOT = """(()=>{const r=document.documentElement;
try{const v=localStorage.getItem('outcome-vibe');
if(['cartoon','calm','pixel','lab'].includes(v))r.dataset.vibe=v}catch{}
try{const v=localStorage.getItem('outcome-appearance');
if(['dark','light'].includes(v))r.dataset.theme=v}catch{}
})();"""

WORKER = (
    "\nlet gl,program,frame=0;let tint=[1,.77,.42];\nfunction shader(type,source){"
    "const s=gl.createShader(type);gl.shaderSource(s,source);\ngl.compileShader(s"
    ");if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error('shader');retu"
    "rn s}\nonmessage=e=>{try{const m=e.data;if(m.canvas){const c=m.canvas;c.widt"
    "h=1200;c.height=80;\ngl=c.getContext('webgl2',{alpha:true,antialias:false});"
    "if(!gl)return;\nprogram=gl.createProgram();gl.attachShader(program,shader(gl"
    ".VERTEX_SHADER,\n'#version 300 es\\nin vec2 p;void main(){gl_Position=vec4(p,"
    "0,1);}'));\ngl.attachShader(program,shader(gl.FRAGMENT_SHADER,\n'#version 300"
    " es\\nprecision mediump float;uniform vec3 tint;uniform float phase;out vec4"
    " color;'+\n'void main(){float grid=step(.85,fract(gl_FragCoord.x/24.))*step("
    ".85,fract(gl_FragCoord.y/24.));'+\n'float scan=max(0.,1.-abs(gl_FragCoord.x/"
    "1200.-phase)*12.);color=vec4(tint,.08+grid*(.2+.6*scan));}'));\ngl.linkProgr"
    "am(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error("
    "'link');\ngl.useProgram(program);const b=gl.createBuffer();gl.bindBuffer(gl."
    "ARRAY_BUFFER,b);\ngl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1"
    ",-1,3]),gl.STATIC_DRAW);\nconst a=gl.getAttribLocation(program,'p');gl.enabl"
    "eVertexAttribArray(a);\ngl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);gl.vi"
    'ewport(0,0,1200,80);\npostMessage({renderer:"webgl2"});return}\nif(!gl)return'
    ";cancelAnimationFrame(frame);if(m.stop){gl.clear(gl.COLOR_BUFFER_BIT);retur"
    "n}\nconst rgb=/^#([0-9a-f]{6})$/i.exec(m.tint||'');if(rgb){const n=parseInt("
    "rgb[1],16);\ntint=[((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255]}\nconst st"
    "art=performance.now();function render(now){const phase=Math.min(1,(now-star"
    "t)/600);\ngl.uniform3f(gl.getUniformLocation(program,'tint'),...tint);\ngl.un"
    "iform1f(gl.getUniformLocation(program,'phase'),phase);gl.drawArrays(gl.TRIA"
    "NGLES,0,3);\nif(phase<1)frame=requestAnimationFrame(render)}frame=requestAni"
    "mationFrame(render);\n}catch{if(gl)gl.clear(gl.COLOR_BUFFER_BIT)}};\n"
)

SCRIPT = """(()=>{'use strict';const root=document.documentElement;
const vibe=document.getElementById('vibe'),appearance=document.getElementById('appearance');
vibe.value=root.dataset.vibe||'calm';appearance.value=root.dataset.theme||'dark';
vibe.addEventListener('change',()=>{root.dataset.vibe=vibe.value;
try{localStorage.setItem('outcome-vibe',vibe.value)}catch{};announce('Theme: '+vibe.value)});
appearance.addEventListener('change',()=>{root.dataset.theme=appearance.value;
try{localStorage.setItem('outcome-appearance',appearance.value)}catch{};
draw();
announce('Appearance: '+appearance.value)});

const live=document.getElementById('viewer-status');function announce(text){live.textContent=text}
const filter=document.getElementById('verdict-filter');filter.addEventListener('change',()=>{
let count=0;
document.querySelectorAll('.event').forEach(e=>{e.hidden=filter.value!=='all'&&e.dataset.status!==filter.value;

if(!e.hidden)count++});announce(count+' requirements shown')});
const pause=document.getElementById('pause-motion');pause.addEventListener('click',()=>{
const paused=root.classList.toggle('paused');pause.setAttribute('aria-pressed',String(paused));
pause.textContent=paused?'Resume motion':'Pause motion';
announce(paused?'Motion paused':'Motion resumed')});

document.addEventListener('visibilitychange',()=>{root.classList.toggle('hidden-page',document.hidden);

if(document.hidden)stopMotion();else if(attempted)draw()});
const canvas=document.getElementById('evidence-field');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let worker=null,attempted=false,fieldVisible=true;
function draw(){
if(!fieldVisible||document.hidden||reduced.matches||root.classList.contains('paused'))return;
initWorker();if(worker){
worker.postMessage({tint:getComputedStyle(root).getPropertyValue('--accent').trim(),animate:true})}}
function initWorker(){if(attempted)return;attempted=true;
try{if(canvas.transferControlToOffscreen&&typeof Worker!=='undefined'){
const blob=new Blob([WORKER_SOURCE],{type:'text/javascript'});
const url=URL.createObjectURL(blob);worker=new Worker(url);URL.revokeObjectURL(url);
worker.onerror=()=>{worker.terminate();worker=null;canvas.dataset.renderer="static"};
worker.onmessage=e=>{if(e.data.renderer)canvas.dataset.renderer=e.data.renderer};
const surface=canvas.transferControlToOffscreen();
worker.postMessage({canvas:surface},[surface]);}}
catch{worker=null}}
function stopMotion(){
document.querySelectorAll('.event, .hero').forEach(e=>e.getAnimations().forEach(a=>a.cancel()));
if(worker)worker.postMessage({stop:true})}
reduced.addEventListener('change',()=>{if(reduced.matches)stopMotion();else draw()});
pause.addEventListener('click',()=>{stopMotion();
if(!root.classList.contains('paused'))draw()});
function replay(){if(reduced.matches||root.classList.contains('paused')||document.hidden)return;
canvas.getAnimations().forEach(a=>a.cancel());
const easing=getComputedStyle(root).getPropertyValue('--ease').trim()||'ease-out';
document.querySelectorAll('.event').forEach(e=>{e.getAnimations().forEach(a=>a.cancel());
if(e.dataset.inView==='false')return;
if(e.dataset.status==='confirmed')e.animate(root.dataset.vibe==='cartoon'?
[{transform:'translateY(8px) scale(.97,1.03)'},{transform:'translateY(-2px) scale(1.02,.98)'},
{transform:'translateY(0) scale(1,1)'}]:[{transform:'translateY(8px)'},
{transform:'translateY(0)'}],{duration:600,easing});
if(e.dataset.status==='contradicted')e.animate([{transform:'translateX(0)'},
{transform:'translateX(-4px)'},{transform:'translateX(4px)'},{transform:'translateX(0)'}],
{duration:350,easing})});draw()}
if(typeof IntersectionObserver!=='undefined'){
const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
if(entry.target===canvas)fieldVisible=entry.isIntersecting;
else entry.target.dataset.inView=String(entry.isIntersecting);
if(!entry.isIntersecting){entry.target.getAnimations().forEach(a=>a.cancel());
if(entry.target===canvas&&worker)worker.postMessage({stop:true})}}));
observer.observe(canvas);document.querySelectorAll('.event').forEach(e=>observer.observe(e))}
canvas.addEventListener('pointermove',e=>{
if(!fieldVisible||root.dataset.vibe!=='calm'||reduced.matches||document.hidden||
root.classList.contains('paused'))return;
const r=canvas.getBoundingClientRect();
const x=((e.clientX-r.left)/r.width-.5)*4,y=((e.clientY-r.top)/r.height-.5)*4;
canvas.getAnimations().forEach(a=>a.cancel());
canvas.animate([{transform:'translate3d(0,0,0)'},{transform:`translate3d(${x}px,${y}px,0)`}],
{duration:220,easing:'ease-out',fill:'forwards'})});
canvas.addEventListener('pointerleave',()=>canvas.getAnimations().forEach(a=>a.cancel()));
document.getElementById('replay').addEventListener('click',replay);
vibe.addEventListener('change',replay);
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopMotion()});
window.addEventListener('pagehide',()=>{if(worker){worker.terminate();worker=null}});
})();"""


SCRIPT = "const WORKER_SOURCE=" + json.dumps(WORKER) + ";\n" + SCRIPT


def digest(source: str) -> str:
    return base64.b64encode(hashlib.sha256(source.encode()).digest()).decode()


def enhance(page: str, results: list[dict], tokens: str) -> str:
    controls = """<nav class="toolbar" aria-label="Viewer controls">
<label>Theme <select id="vibe"><option value="cartoon">Cartoon</option>
<option value="calm">Calm</option><option value="pixel">Pixel</option>
<option value="lab">Lab</option>
</select></label><label>Appearance <select id="appearance"><option value="dark">Dark</option>
<option value="light">Light</option></select></label>
<button id="pause-motion" aria-pressed="false" type="button">Pause motion</button>
<button id="replay" type="button" title="Replay presentation, keep verdicts">
Replay timeline</button>
<label>Timeline verdict <select id="verdict-filter"><option value="all">All</option>
<option value="confirmed">Confirmed</option><option value="contradicted">Contradicted</option>
<option value="unobserved">Unobserved</option>
<option value="unconfirmed">Unconfirmed-no-change</option>
</select></label></nav>
<p id="viewer-status" role="status" aria-live="polite">Supplied evidence ready.</p>
<canvas class="hero" id="evidence-field" data-renderer="static" aria-hidden="true"></canvas>"""
    events = []
    for row in results:
        if not isinstance(row, dict):
            continue
        status = row.get("status")
        status = (
            status
            if status in ("confirmed", "contradicted", "unobserved", "unconfirmed")
            else "unobserved"
        )
        label = "unconfirmed-no-change" if status == "unconfirmed" else status

        def esc(key: str, item: dict = row) -> str:
            value = item.get(key, "not supplied")
            if (key == "action_id" and value is None) or (
                key == "action" and value == "not_required"
            ):
                value = "not required"
            return html.escape(str(value))

        events.append(
            f'<li class="event" data-status="{status}"><h3>{esc("id")}: {label}</h3>'
            '<div class="stages"><p><b>1. Action</b>' + esc("action_id") + "</p>"
            "<p><b>2. Receipt</b>" + esc("action") + "</p>"
            "<p><b>3. Observation</b>"
            + esc("observation_id")
            + ": "
            + esc("outcome")
            + "</p></div>"
            "<small>" + esc("reason") + "</small></li>"
        )
    timeline = (
        '<section aria-label="Evidence timeline"><h2>Evidence timeline</h2><ol class="timeline">'
        + "".join(events)
        + "</ol></section>"
    )
    style = tokens + STYLE
    # Both the original renderer stylesheet and enhancement are authorized by exact hashes.
    original = page.split("<style>", 1)[1].split("</style>", 1)[0]
    csp = (
        "default-src 'none'; connect-src 'none'; img-src data:; base-uri 'none'; "
        "form-action 'none'; object-src 'none'; worker-src blob:; "
        f"style-src 'sha256-{digest(original)}' 'sha256-{digest(style)}'; "
        f"script-src 'sha256-{digest(BOOT)}' 'sha256-{digest(SCRIPT)}'"
    )
    head = f'<meta http-equiv="Content-Security-Policy" content="{html.escape(csp, quote=True)}">'
    policy = head
    head = f'<style>{style}</style><script type="text/javascript">{BOOT}</script>'
    page = page.replace('<html lang="en">', '<html lang="en" data-vibe="calm" data-theme="dark">')
    page = page.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + policy, 1)
    page = page.replace("</head>", head + "</head>")
    page = page.replace(
        '<div class="cards">',
        controls + '<div class="cards">',
        1,
    )
    page = page.replace(
        "<h1>", f'<h1><img class="brand-mark" alt="" src="data:image/svg+xml;base64,{LOGO}">', 1
    )
    page = page.replace(
        "<h2>Results by requirement</h2>", timeline + "<h2>Results by requirement</h2>"
    )
    return page.replace("</body>", f'<script type="text/javascript">{SCRIPT}</script></body>')
