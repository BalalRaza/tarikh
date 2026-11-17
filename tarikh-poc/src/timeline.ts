import { events, esc } from './data';
import { mapSvg, places, project } from './map';

const S = 170; // spacing between points along the line
const UX = 0.5;
const UY = -0.866; // line runs bottom-left to top-right (60°)
const NEAR = 40; // map units: neighbours closer than this trigger auto-zoom
const ZOOM = 8;

let t = 0; // focus position, kept across page changes

const clamp = (v: number) => Math.max(0, Math.min(events.length - 1, v));
const pts = events.map((e) => project(e.place.lat, e.place.lng));

const ARROW =
  '<svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16324A" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>';

export function renderTimeline(root: HTMLElement, focusId?: string): () => void {
  if (focusId) {
    const i = events.findIndex((e) => e.id === focusId);
    if (i >= 0) t = i;
  }
  document.body.dataset.view = 'timeline';
  document.title = 'Tarikh · Seerah timeline';

  root.innerHTML = `
  <div class="tl">
    <div class="tl-map" aria-hidden="true">${mapSvg()}</div>
    ${places
      .map((p) => `<div class="pl ${p.side ?? ''}" aria-hidden="true"><span></span><div>${esc(p.name)}</div></div>`)
      .join('')}
    <div class="glow tl-glow" aria-hidden="true"></div>
    <div class="tl-line" aria-hidden="true"></div>
    ${events
      .map(
        (e, i) => `
    <div class="it ${i % 2 === 0 ? 'r' : 'l'}">
      <button type="button" aria-label="${esc(e.title)}, ${esc(e.ce)} CE"><span class="dot ${e.major ? 'major' : 'minor'}"></span></button>
      <div class="lbl"><div class="y">${esc(e.y)}</div><div class="tt">${esc(e.title)}</div></div>
    </div>`,
      )
      .join('')}
    <header class="tl-head">
      <div class="tl-brand"><span>SEERAH TIMELINE</span><span lang="ar" dir="rtl">تاريخ</span></div>
      <div class="tl-year"></div>
      <div class="tl-sub"><span class="tl-ah"></span><span class="tl-era"></span></div>
      <div class="tl-dots" aria-hidden="true">${events.map(() => '<span></span>').join('')}</div>
    </header>
    <a class="card" aria-live="polite">
      <div class="card-body">
        <div class="card-type"></div>
        <div class="card-title"></div>
        <div class="card-ar" lang="ar" dir="rtl"></div>
      </div>
      <div class="card-go">${ARROW}</div>
    </a>
  </div>`;

  const app = root.querySelector<HTMLElement>('.tl')!;
  const mapEl = app.querySelector<HTMLElement>('.tl-map')!;
  const plEls = [...app.querySelectorAll<HTMLElement>('.pl')];
  const itEls = [...app.querySelectorAll<HTMLElement>('.it')];
  const lblEls = itEls.map((el) => el.querySelector<HTMLElement>('.lbl')!);
  const glow = app.querySelector<HTMLElement>('.tl-glow')!;
  const line = app.querySelector<HTMLElement>('.tl-line')!;
  const dotEls = [...app.querySelectorAll<HTMLElement>('.tl-dots span')];
  const card = app.querySelector<HTMLAnchorElement>('.card')!;
  const q = (s: string) => app.querySelector<HTMLElement>(s)!;

  let drag: { x: number; y: number; t: number } | null = null;
  let moved = false;
  let lastF = -1;

  function apply() {
    const W = app.clientWidth;
    const H = app.clientHeight;
    const FX = W / 2;
    const FY = Math.round(H * 0.474);
    const f = Math.round(clamp(t));
    const cur = events[f];
    const c = pts[f];

    // line through the focus point
    const L = 2 * Math.hypot(W, H);
    line.style.width = `${L}px`;
    line.style.transform = `translate(${FX - L / 2}px, ${FY - 2}px) rotate(-60deg)`;
    glow.style.transform = `translate(${FX - 7}px, ${FY - 7}px)`;

    itEls.forEach((el, i) => {
      const d = i - t;
      const ad = Math.abs(d);
      const x = FX + d * S * UX;
      el.style.transform = `translate(${x}px, ${FY + d * S * UY}px)`;
      // labels alternate sides; flip to the other side when they would run off-screen
      let right = i % 2 === 0;
      if (right && W - x - 38 < 110) right = false;
      else if (!right && x - 38 < 110) right = true;
      el.classList.toggle('r', right);
      el.classList.toggle('l', !right);
      lblEls[i].style.width = `${Math.min(136, (right ? W - x : x) - 38)}px`;
      el.style.opacity = String(ad > 3.2 ? 0 : i === f ? 1 : Math.max(0.5, 0.85 - ad * 0.15));
      el.style.pointerEvents = ad > 3.2 ? 'none' : 'auto';
      el.classList.toggle('focus', i === f);
    });

    // map: pan so the focused place sits under the focus point; zoom in when neighbours are close
    const far = (a: number, b: number) => Math.hypot(pts[a].x - pts[b].x, pts[a].y - pts[b].y) >= NEAR;
    const near = (f > 0 && !far(f, f - 1)) || (f < events.length - 1 && !far(f, f + 1));
    const z = near ? ZOOM : 1;
    mapEl.style.transform = `translate(${FX - c.x * z}px, ${FY - c.y * z}px) scale(${z})`;
    mapEl.style.opacity = near ? '0.3' : '0.7';
    mapEl.style.setProperty('--z', String(z));
    plEls.forEach((el, i) => {
      const p = places[i];
      const px = (p.x - c.x) * z;
      const py = (p.y - c.y) * z;
      el.style.transform = `translate(${FX + px}px, ${FY + py}px)`;
      el.classList.toggle('at-focus', Math.hypot(px, py) < 30); // label clears the focus dot
      el.style.opacity = p.detail ? (near ? '0.85' : '0') : p.city && near ? '0' : '0.85';
    });

    if (f !== lastF) {
      lastF = f;
      q('.tl-year').textContent = `${cur.ce} CE`;
      q('.tl-ah').textContent = cur.ah ?? 'Before Hijra';
      q('.tl-era').textContent = cur.era;
      q('.card-type').textContent = `${cur.type} · ${cur.place.name.toUpperCase()}`;
      q('.card-title').textContent = cur.title;
      q('.card-ar').textContent = cur.ar;
      card.href = `#/event/${cur.id}`;
      card.setAttribute('aria-label', `Open ${cur.title}`);
      dotEls.forEach((d, i) => d.classList.toggle('on', i === f));
    }
  }

  function settle() {
    t = Math.round(clamp(t));
    apply();
  }

  const onDown = (e: PointerEvent) => {
    if (e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY, t };
    moved = false;
    app.classList.add('dragging');
  };
  const onMove = (e: PointerEvent) => {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    const dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 6) moved = true;
    t = clamp(drag.t - (dx * UX + dy * UY) / S);
    apply();
  };
  const onUp = () => {
    if (!drag) return;
    drag = null;
    app.classList.remove('dragging');
    settle();
  };
  let wheelTimer = 0;
  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    t = clamp(t + e.deltaY / 300);
    app.classList.add('dragging');
    apply();
    clearTimeout(wheelTimer);
    wheelTimer = window.setTimeout(() => {
      app.classList.remove('dragging');
      settle();
    }, 160);
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') t = clamp(Math.round(t) + 1);
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') t = clamp(Math.round(t) - 1);
    else return;
    e.preventDefault();
    apply();
  };

  itEls.forEach((el, i) =>
    el.querySelector('button')!.addEventListener('click', () => {
      if (moved) return;
      t = i;
      apply();
    }),
  );
  card.addEventListener('click', (e) => {
    if (moved) e.preventDefault();
  });

  app.addEventListener('pointerdown', onDown);
  window.addEventListener('pointermove', onMove);
  window.addEventListener('pointerup', onUp);
  window.addEventListener('pointercancel', onUp);
  app.addEventListener('wheel', onWheel, { passive: false });
  window.addEventListener('keydown', onKey);
  window.addEventListener('resize', apply);

  // first paint without animating in from the origin
  app.classList.add('dragging');
  apply();
  requestAnimationFrame(() => requestAnimationFrame(() => app.classList.remove('dragging')));

  return () => {
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    window.removeEventListener('pointercancel', onUp);
    window.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', apply);
    clearTimeout(wheelTimer);
  };
}
