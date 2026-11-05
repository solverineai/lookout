// Captures the running service (uvicorn on :8000, a fresh night) into shots/ for scene.html.
// Rebuild: restart the server, node capture.mjs, then render scene.html with the motion-graphics
// render_frames.mjs, synth_audio.py and mux.sh. The live steps make real Spark calls (about $0.05).
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
const OUT = new URL('./shots/', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const URL_ = 'http://localhost:8000/';
const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const K = 1920 / 1440; // shots are 1440x810 CSS px, shown at 1920x1080 in the video
const p = await b.newPage({ viewport: { width: 1440, height: 810 }, deviceScaleFactor: 8 / 3, colorScheme: 'light' });
const rects = {};
const wait = ms => p.waitForTimeout(ms);
async function snap(name, sels = {}) {
  rects[name] = await p.evaluate(([sels, K]) => Object.fromEntries(Object.entries(sels).map(([k, q]) => {
    const e = document.querySelector(q); if (!e) return [k, null];
    const r = e.getBoundingClientRect(); return [k, [r.x * K, r.y * K, r.width * K, Math.min(r.height, 810 - r.y) * K]];
  })), [sels, K]);
  await p.screenshot({ path: `${OUT}${name}.png` });
  console.log('shot', name);
}
const BOARD = { types: '#types', built: '.built', ask: '.col.ask', fix: '.col.fix', you: '.col.you', try: '#try', now: '#now', seg: '.seg', nav: '.nav', rec: '.col.rec' };

await p.goto(URL_); await p.evaluate(() => document.fonts.ready); await wait(1500);
await snap('board', BOARD);
await snap('board_fix1', { ...BOARD, first: '.col.fix .item' });

// a judge breaks an order; follow the strip through its stages (real Spark calls)
await p.click('[data-preset="unit"]');
const seen = new Set();
for (let i = 0; i < 120; i++) {
  await wait(700);
  const st = await p.evaluate(() => { const n = document.getElementById('now'); if (n.hidden) return null;
    const li = [...n.querySelectorAll('li')]; return { on: li.findIndex(x => x.classList.contains('on')), working: /Working on/.test(n.innerText) }; });
  if (st && st.working && !seen.has(st.on)) { seen.add(st.on); await snap(`live_${st.on}`, BOARD); }
  if (!st && i > 6) break;
}
await wait(1500);
await snap('after', { ...BOARD, first: '.col.ask .item', firstFix: '.col.fix .item' });

// the record pane beside the lists: it already follows the order just fixed, a click switches it
const REC = { rec: '.col.rec', board: '.board' };
const recAudit = () => p.evaluate(() => { const b = document.getElementById('recBody'), h = [...b.querySelectorAll('h4')].find(h => /Audit/.test(h.textContent)); if (h) b.scrollTop = h.offsetTop - 12; });
await snap('rec_live', REC);
await recAudit(); await wait(400);
await snap('rec_live_audit', REC);
const pickItem = async oid => { await p.locator('.item', { hasText: '#' + oid }).first().click(); await wait(1200); };
await pickItem('1042');
await snap('rec_fix', { ...REC, sel: '.item.sel' });
await pickItem('1149');
await snap('rec_block', { ...REC, sel: '.item.sel' });

// chat: its own screen; the seller approves by number, in Korean
await p.click('#chat'); await wait(900);
await snap('chat0', { thread: '#thread', composer: '.composer', seg: '.seg' });
await p.fill('#askText', 'Approve only the refund for #1055'); await p.press('#askText', 'Enter');
await wait(1200);
await snap('chat_typing', { thread: '#thread', composer: '.composer' });
for (let i = 0; i < 90; i++) { await wait(1000); if (!(await p.$('.typing'))) break; }
await wait(1500);
await snap('chat_done', { thread: '#thread', composer: '.composer', last: '.thread .in > .msg:last-child' });
await p.locator('.oref').last().click(); await wait(900);
await snap('chat_link', { sheet: '#sheet' });
await p.keyboard.press('Escape');

// phone
const m = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, colorScheme: 'light', hasTouch: true });
await m.goto(URL_); await m.evaluate(() => document.fonts.ready); await m.waitForTimeout(1500);
await m.screenshot({ path: `${OUT}phone_board.png` });
await m.goto(URL_ + '#chat'); await m.waitForTimeout(1500);
await m.screenshot({ path: `${OUT}phone_chat.png` });
console.log('shot phone');

writeFileSync(`${OUT}rects.js`, 'window.R = ' + JSON.stringify(rects) + ';\n');
await b.close();
