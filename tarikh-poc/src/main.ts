import './style.css';
import { events } from './data';
import { renderTimeline } from './timeline';
import { renderEvent } from './event';

const root = document.getElementById('app')!;
let cleanup: (() => void) | null = null;

function route() {
  cleanup?.();
  cleanup = null;
  const h = location.hash;
  const ev = h.match(/^#\/event\/([\w-]+)$/);
  const e = ev && events.find((x) => x.id === ev[1]);
  if (e) {
    renderEvent(root, e);
    return;
  }
  const at = h.match(/^#\/at\/([\w-]+)$/);
  cleanup = renderTimeline(root, at?.[1]);
}

window.addEventListener('hashchange', route);
route();
