import raw from './events.json';

export type Ref = {
  type: 'quran' | 'hadith' | 'ibn_kathir' | 'ibn_hisham';
  label: string;
  url: string;
  supports: string;
  verified: boolean;
  grade?: string | null;
  location?: string;
  arabic?: string;
};

export type Ev = {
  id: string;
  order: number;
  major: boolean;
  title: string;
  ar: string;
  type: string;
  era: string;
  y: string;
  ce: string;
  ah: string | null;
  dateNote: string;
  place: { name: string; lat: number; lng: number };
  short: string;
  full: string;
  refs: Ref[];
  grade: string;
  gradeReason: string;
  scene: string;
  sceneAlt: string;
  glow: { x: number; y: number };
};

export const events: Ev[] = (raw as unknown as Ev[]).slice().sort((a, b) => a.order - b.order);

export const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
