import { chromium, firefox, webkit } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const output=path.resolve('build/browser');await fs.mkdir(output,{recursive:true});
const axe=await fs.readFile('node_modules/axe-core/axe.min.js','utf8');
const url=pathToFileURL(path.resolve('site/state.html')).href;
const results=[];
for(const [name,engine] of Object.entries({chromium,firefox,webkit})){
  console.log(`CHECK: ${name}`);
  const browser=await engine.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1280,height:800}});
  await context.route(/https?:\/\//,route=>route.abort());
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{window.metrics={lcp:null,events:[]};
    try{new PerformanceObserver(list=>{for(const e of list.getEntries())window.metrics.lcp=e.startTime})
      .observe({type:'largest-contentful-paint',buffered:true})}catch{}
    try{new PerformanceObserver(list=>{for(const e of list.getEntries())if(e.interactionId)
      window.metrics.events.push(e.duration)}).observe({type:'event',buffered:true,durationThreshold:16})}catch{}
  });
  await page.goto(url,{waitUntil:'domcontentloaded'});await page.waitForTimeout(200);
  assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
  await page.locator('.suite-nav a').first().focus();
  for(const label of ['Audit','State','Cite']){
    assert.equal(await page.locator(':focus').textContent(),label);
    assert.notEqual(await page.locator(':focus').evaluate(e=>getComputedStyle(e).outlineStyle),'none');
    if(label!=='Cite') await page.keyboard.press('Tab');
  }
  assert.equal(await page.locator('.suite-nav [aria-current="page"]').textContent(),'State');
  await page.locator('#vibe').focus();assert.equal(await page.locator(':focus').getAttribute('id'),'vibe');
  assert.notEqual(await page.locator('#vibe').evaluate(e=>getComputedStyle(e).outlineStyle),'none');
  await page.keyboard.press('Tab');assert.equal(await page.locator(':focus').getAttribute('id'),'appearance');
  await page.keyboard.press('Tab');assert.equal(await page.locator(':focus').getAttribute('id'),'pause-motion');
  await page.keyboard.press('Space');assert.equal(await page.locator('#pause-motion').getAttribute('aria-pressed'),'true');
  await page.keyboard.press('Space');assert.equal(await page.locator('#pause-motion').getAttribute('aria-pressed'),'false');
  for(const vibe of ['cartoon','calm','pixel','lab']){
    await page.selectOption('#vibe',vibe);
    for(const appearance of ['dark','light']){
      await page.selectOption('#appearance',appearance);
      await page.evaluate(axe);
      const audit=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}}));
      const serious=audit.violations;
      results.push({browser:name,vibe,appearance,axeViolations:audit.violations.map(v=>({id:v.id,impact:v.impact,count:v.nodes.length}))});
      assert.deepEqual(serious,[],`${name} ${vibe} ${appearance} axe`);
    }
  }
  await page.selectOption('#vibe','pixel');await page.goto('about:blank');
  await page.goto(url,{waitUntil:'domcontentloaded'});
  assert.equal(await page.locator('html').getAttribute('data-vibe'),'pixel');
  await page.selectOption('#verdict-filter','contradicted');
  assert.equal(await page.locator('.event:visible:not([data-status=contradicted])').count(),0);
  await page.click('#replay');
  await page.click('#pause-motion');assert.equal(await page.locator('#pause-motion').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('.event').evaluateAll(es=>es.some(e=>e.getAnimations().some(a=>a.playState==='running'))),false);
  await page.emulateMedia({reducedMotion:'reduce'});
  assert.equal(await page.locator('.event').first().evaluate(e=>getComputedStyle(e).animationName),'none');
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(output,`${name}-mobile.png`),fullPage:true});
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.click('#pause-motion');
  await page.selectOption('#verdict-filter','all');
  await page.locator('.event').first().scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>typeof IntersectionObserver==='undefined'||document.querySelector('.event').dataset.inView==='true');
  assert.equal(await page.evaluate(()=>{document.getElementById('replay').click();
    return document.querySelector('.event').getAnimations().some(a=>a.playState==='running')}),true);
  const frames=await page.evaluate(()=>new Promise(resolve=>{const deltas=[];let last=performance.now();
    function step(now){deltas.push(now-last);last=now;
    if(deltas.length===20||deltas.length===40)document.getElementById('replay').click();
    if(deltas.length<61)requestAnimationFrame(step);else resolve(deltas.slice(1))}requestAnimationFrame(step)}));
  results.push({browser:name,metrics:await page.evaluate(()=>window.metrics),frameMedianMs:frames.sort((a,b)=>a-b)[30],frameP95Ms:frames[57],sample:'60 rAF deltas with a visible confirmed row; active replay verified and restarted at frames20/40',browserVersion:browser.version(),renderer:await page.locator("#evidence-field").getAttribute("data-renderer"),errors});
  assert.deepEqual(errors,[]);
  await fs.writeFile(path.join(output,"results.json"),JSON.stringify(results,null,2)+"\n");
  assert.ok(frames[30]<=18&&frames[57]<25,`${name} cadence median=${frames[30]} p95=${frames[57]}`);
  const measured=await page.evaluate(()=>window.metrics.events);
  assert.ok(measured.every(value=>value<200),`${name} measured event latency budget`);
  // Storage-denied and GPU-unavailable fallbacks use the actual default CSP.
  const blocked=await context.newPage();await blocked.addInitScript(()=>{
    Object.defineProperty(window,'localStorage',{get(){throw Error('blocked')}});
    HTMLCanvasElement.prototype.getContext=()=>null;
  });await blocked.goto(url,{waitUntil:'domcontentloaded'});await blocked.selectOption('#vibe','cartoon');
  await blocked.selectOption('#appearance','light');await blocked.goto('about:blank');
  await blocked.goto(url,{waitUntil:'domcontentloaded'});
  assert.equal(await blocked.locator('html').getAttribute('data-theme'),'dark');
  await context.close();await browser.close();
}
await fs.writeFile(path.join(output,'results.json'),JSON.stringify(results,null,2)+'\n');
console.log(`PASS: ${results.length} browser/theme/a11y/performance observations`);
