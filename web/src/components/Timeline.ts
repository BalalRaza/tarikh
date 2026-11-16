import type { EventSummary } from '../api';

const PALETTE = {
  bg: '#0A1628',
  gold: '#D4A853',
  white: '#F5F0E8',
  axis: '#1E3050',
  label: '#8AA0C0',
};

const TYPE_COLORS: Record<string, string> = {
  battle: '#C0392B',
  political: '#2980B9',
  religious: '#8E44AD',
  cultural: '#27AE60',
  scholarly: '#E67E22',
  default: '#D4A853',
};

function typeColor(type: string): string {
  return TYPE_COLORS[type] ?? TYPE_COLORS.default;
}

function dotRadius(importance: number): number {
  if (importance === 1) return 8;
  if (importance === 2) return 5;
  return 3;
}

export class Timeline {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private events: EventSummary[] = [];

  // View state: centerYear (CE) + scale (px per year)
  private centerYear = 700;
  private scale = 0.5; // px per year

  private dragging = false;
  private lastX = 0;

  private dpr = window.devicePixelRatio || 1;

  constructor(container: HTMLElement) {
    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'display:block;width:100%;height:100%;cursor:grab;';
    container.appendChild(this.canvas);

    const ctx = this.canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D not available');
    this.ctx = ctx;

    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.bindInput();
  }

  private resize(): void {
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * this.dpr;
    this.canvas.height = rect.height * this.dpr;
    this.ctx.scale(this.dpr, this.dpr);
    this.draw();
  }

  private logicalWidth(): number {
    return this.canvas.width / this.dpr;
  }

  private logicalHeight(): number {
    return this.canvas.height / this.dpr;
  }

  /** Convert a CE year to canvas x coordinate */
  private yearToX(year: number): number {
    return this.logicalWidth() / 2 + (year - this.centerYear) * this.scale;
  }

  /** Convert canvas x to CE year */
  private xToYear(x: number): number {
    return this.centerYear + (x - this.logicalWidth() / 2) / this.scale;
  }

  private bindInput(): void {
    const c = this.canvas;

    c.addEventListener('mousedown', (e) => {
      this.dragging = true;
      this.lastX = e.clientX;
      c.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.dragging) return;
      const dx = e.clientX - this.lastX;
      this.lastX = e.clientX;
      this.centerYear -= dx / this.scale;
      this.draw();
    });

    window.addEventListener('mouseup', () => {
      this.dragging = false;
      this.canvas.style.cursor = 'grab';
    });

    c.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      // Zoom toward mouse position
      const rect = c.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const yearAtMouse = this.xToYear(mouseX);
      this.scale = Math.max(0.02, Math.min(50, this.scale * factor));
      // Keep yearAtMouse under mouse
      this.centerYear = yearAtMouse - (mouseX - this.logicalWidth() / 2) / this.scale;
      this.draw();
    }, { passive: false });

    // Touch pan
    let lastTouchX = 0;
    c.addEventListener('touchstart', (e) => { lastTouchX = e.touches[0].clientX; });
    c.addEventListener('touchmove', (e) => {
      e.preventDefault();
      const dx = e.touches[0].clientX - lastTouchX;
      lastTouchX = e.touches[0].clientX;
      this.centerYear -= dx / this.scale;
      this.draw();
    }, { passive: false });
  }

  setEvents(events: EventSummary[]): void {
    this.events = events;
    this.draw();
  }

  /** Returns [minYear, maxYear] of visible canvas area */
  visibleRange(): [number, number] {
    return [this.xToYear(0), this.xToYear(this.logicalWidth())];
  }

  /** True when zoomed in enough to show importance > 1 */
  private isZoomedIn(): boolean {
    return this.scale >= 0.3;
  }

  draw(): void {
    const w = this.logicalWidth();
    const h = this.logicalHeight();
    const ctx = this.ctx;
    ctx.save();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

    // Background
    ctx.fillStyle = PALETTE.bg;
    ctx.fillRect(0, 0, w, h);

    const axisY = h * 0.55;

    // Era bands (rough CE ranges)
    const eras: Array<{ from: number; to: number; color: string; label: string }> = [
      { from: 610, to: 661, color: 'rgba(212,168,83,0.06)', label: 'Prophetic Era' },
      { from: 661, to: 750, color: 'rgba(41,128,185,0.06)', label: 'Umayyad' },
      { from: 750, to: 1258, color: 'rgba(142,68,173,0.06)', label: 'Abbasid' },
      { from: 1258, to: 1517, color: 'rgba(192,57,43,0.06)', label: 'Post-Abbasid' },
      { from: 1299, to: 1922, color: 'rgba(39,174,96,0.06)', label: 'Ottoman' },
    ];

    for (const era of eras) {
      const x1 = this.yearToX(era.from);
      const x2 = this.yearToX(era.to);
      if (x2 < 0 || x1 > w) continue;
      ctx.fillStyle = era.color;
      ctx.fillRect(x1, 0, x2 - x1, h);
      // Era label at top
      const labelX = Math.max(x1 + 4, 4);
      if (labelX < w) {
        ctx.fillStyle = 'rgba(245,240,232,0.18)';
        ctx.font = '11px Inter, sans-serif';
        ctx.fillText(era.label, labelX, 18);
      }
    }

    // Axis line
    ctx.strokeStyle = PALETTE.axis;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, axisY);
    ctx.lineTo(w, axisY);
    ctx.stroke();

    // Year tick marks
    const tickInterval = this.pickTickInterval();
    const startYear = Math.floor(this.xToYear(0) / tickInterval) * tickInterval;
    const endYear = Math.ceil(this.xToYear(w) / tickInterval) * tickInterval;

    ctx.fillStyle = PALETTE.label;
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';

    for (let yr = startYear; yr <= endYear; yr += tickInterval) {
      const x = this.yearToX(yr);
      if (x < 0 || x > w) continue;
      ctx.strokeStyle = PALETTE.axis;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, axisY - 6);
      ctx.lineTo(x, axisY + 6);
      ctx.stroke();
      ctx.fillText(`${yr} CE`, x, axisY + 18);
    }

    // Events
    const zoomedIn = this.isZoomedIn();
    const visibleEvents = this.events.filter((ev) => {
      if (ev.date_ce == null && ev.sort_key == null) return false;
      if (!zoomedIn && ev.importance > 1) return false;
      const year = ev.date_ce ?? ev.sort_key!;
      const x = this.yearToX(year);
      return x >= -20 && x <= w + 20;
    });

    ctx.textAlign = 'center';

    for (const ev of visibleEvents) {
      const year = ev.date_ce ?? ev.sort_key!;
      const x = this.yearToX(year);
      const r = dotRadius(ev.importance);
      const color = typeColor(ev.event_type);

      // Dot
      ctx.beginPath();
      ctx.arc(x, axisY, r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();

      // Glow for importance=1
      if (ev.importance === 1) {
        ctx.beginPath();
        ctx.arc(x, axisY, r + 3, 0, Math.PI * 2);
        ctx.strokeStyle = color + '66';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Labels when zoomed in
      if (zoomedIn && this.scale >= 0.5) {
        ctx.font = ev.importance === 1 ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
        ctx.fillStyle = PALETTE.white;
        const label = ev.title_en.length > 28 ? ev.title_en.slice(0, 26) + '…' : ev.title_en;
        // Alternate above/below axis to reduce overlap
        const above = visibleEvents.indexOf(ev) % 2 === 0;
        const labelY = above ? axisY - r - 6 : axisY + r + 14;
        ctx.fillText(label, x, labelY);
      }
    }

    ctx.restore();
  }

  private pickTickInterval(): number {
    // Target ~6-10 ticks visible
    const yearsVisible = this.logicalWidth() / this.scale;
    const candidates = [1, 2, 5, 10, 25, 50, 100, 200, 500, 1000];
    for (const c of candidates) {
      if (yearsVisible / c <= 10) return c;
    }
    return 1000;
  }
}
