import { getEvents } from '../api';
import type { EventSummary } from '../api';
import { Timeline } from '../components/Timeline';

export async function mountTimelinePage(container: HTMLElement): Promise<void> {
  container.innerHTML = '';
  container.style.cssText = 'width:100%;height:100%;display:flex;flex-direction:column;';

  // Header
  const header = document.createElement('div');
  header.style.cssText = 'padding:12px 20px;border-bottom:1px solid #1E3050;display:flex;align-items:center;gap:16px;flex-shrink:0;';
  header.innerHTML = `
    <span style="color:#D4A853;font-size:18px;font-weight:700;letter-spacing:0.04em;">تاريخ</span>
    <span style="color:#8AA0C0;font-size:12px;">Islamic History Timeline</span>
    <span id="tl-status" style="margin-left:auto;color:#8AA0C0;font-size:12px;">Loading…</span>
  `;
  container.appendChild(header);

  // Canvas wrapper
  const canvasWrap = document.createElement('div');
  canvasWrap.style.cssText = 'flex:1;min-height:0;';
  container.appendChild(canvasWrap);

  const timeline = new Timeline(canvasWrap);

  const statusEl = header.querySelector<HTMLElement>('#tl-status')!;

  const allEvents: EventSummary[] = [];
  let total = 0;
  let cursor: string | null = null;
  let fetching = false;

  async function fetchNext(): Promise<void> {
    if (fetching) return;
    fetching = true;
    try {
      const res = await getEvents({ limit: 200, cursor: cursor ?? undefined });
      total = res.total;
      allEvents.push(...res.events);
      cursor = res.next_cursor;
      timeline.setEvents(allEvents);
      statusEl.textContent = cursor
        ? `${allEvents.length} / ${total} events`
        : `${allEvents.length} events`;
    } catch (err) {
      statusEl.textContent = 'API unavailable — no data';
      console.warn('[tarikh] API error:', err);
    } finally {
      fetching = false;
    }
  }

  // Initial load
  await fetchNext();

  // Fetch more as user pans (debounced)
  let panTimer: ReturnType<typeof setTimeout> | null = null;
  const canvasEl = canvasWrap.querySelector('canvas')!;
  canvasEl.addEventListener('mousemove', () => {
    if (!cursor || fetching) return;
    if (panTimer) clearTimeout(panTimer);
    panTimer = setTimeout(() => { void fetchNext(); }, 600);
  });

  canvasEl.addEventListener('touchmove', () => {
    if (!cursor || fetching) return;
    if (panTimer) clearTimeout(panTimer);
    panTimer = setTimeout(() => { void fetchNext(); }, 600);
  });
}
