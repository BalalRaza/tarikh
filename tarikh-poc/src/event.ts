import { esc, type Ev, type Ref } from './data';
import { miniMap } from './map';

const BACK =
  '<svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>';

const TYPE_NAME: Record<Ref['type'], string> = {
  quran: 'Quran',
  hadith: 'Hadith',
  ibn_kathir: 'Ibn Kathir',
  ibn_hisham: 'Ibn Hisham',
};

// Unicode 14 honorific ligatures that common fonts lack: show them spelled out (data keeps the source text).
const spell = (s: string) => s.replace(/﵇/g, 'عليه السلام').replace(/﵁/g, 'رضي الله عنه');

function refItem(r: Ref): string {
  const meta = [TYPE_NAME[r.type], r.grade ? `Grade: ${r.grade}` : '', r.location ? spell(r.location) : ''].filter(Boolean);
  return `
  <li class="ref">
    <a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.label)}</a>
    <div class="ref-meta">${meta.map(esc).join(' · ')}</div>
    <p class="ref-supports">${esc(r.supports)}</p>
    ${r.arabic ? `<blockquote class="ref-ar" lang="ar" dir="rtl">${esc(spell(r.arabic))}</blockquote>` : ''}
  </li>`;
}

export function renderEvent(root: HTMLElement, e: Ev) {
  document.body.dataset.view = 'event';
  document.title = `${e.title} · Tarikh`;
  const scene = import.meta.env.BASE_URL + e.scene;
  const order: Ref['type'][] = ['quran', 'hadith', 'ibn_kathir', 'ibn_hisham'];
  const refs = e.refs.slice().sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type));
  const kinds = order.filter((k) => refs.some((r) => r.type === k)).map((k) => TYPE_NAME[k]);

  root.innerHTML = `
  <article class="ev">
    <div class="ev-scene" role="img" aria-label="${esc(e.sceneAlt)}">
      <svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <radialGradient id="glow-g">
            <stop offset="0" stop-color="#FFFBE0"/>
            <stop offset="0.35" stop-color="#FFEC96" stop-opacity="0.85"/>
            <stop offset="1" stop-color="#FFE078" stop-opacity="0"/>
          </radialGradient>
          <filter id="glow-b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
        </defs>
        <image href="${esc(scene)}" width="1600" height="900"/>
        <circle cx="${e.glow.x}" cy="${e.glow.y}" r="70" fill="url(#glow-g)" filter="url(#glow-b)"/>
      </svg>
      <a class="ev-back" href="#/at/${e.id}" aria-label="Back to timeline">${BACK}</a>
      <div class="ev-mini" aria-hidden="true">${miniMap(e.place.lat, e.place.lng, esc(e.place.name))}</div>
    </div>

    <div class="ev-body">
      <div>
        <div class="kicker">${esc(e.type)} · ${esc(e.era.toUpperCase())}</div>
        <div class="ev-titlerow">
          <h1>${esc(e.title)}</h1>
          <div class="ev-ar" lang="ar" dir="rtl">${esc(e.ar)}</div>
        </div>
      </div>

      <div class="facts">
        <div class="fact"><div class="fact-k">WHEN</div><div class="fact-v">${esc(e.ce)} CE</div></div>
        <div class="fact"><div class="fact-k">WHERE</div><div class="fact-v">${esc(e.place.name)}</div></div>
        <div class="fact"><div class="fact-k">HIJRI</div><div class="fact-v">${esc(e.ah ?? 'Before Hijra')}</div></div>
      </div>

      <section>
        <h2 class="kicker muted">IN SHORT</h2>
        <p class="ev-short">${esc(e.short)}</p>
      </section>

      <section>
        <h2 class="kicker muted">MORE DETAIL</h2>
        <p class="ev-full">${esc(e.full)}</p>
      </section>

      <details class="ev-date">
        <summary>About the date</summary>
        <p>${esc(e.dateNote)}</p>
      </details>

      <section class="src">
        <div class="src-head">
          <div class="src-grade" aria-hidden="true">${esc(e.grade)}</div>
          <div>
            <div class="src-title">Sources: grade ${esc(e.grade)}</div>
            <div class="src-kinds">${kinds.join(' · ')}</div>
          </div>
        </div>
        <p class="src-reason">${esc(e.gradeReason)}</p>
        <details class="src-list">
          <summary>Show all ${refs.length} sources</summary>
          <ol>${refs.map(refItem).join('')}</ol>
        </details>
      </section>
    </div>
  </article>`;
  window.scrollTo(0, 0);
}
