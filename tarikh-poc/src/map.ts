// Map units: 1° longitude = 93, 1° latitude = 100, anchored on Makkah (542, 1108).
export const project = (lat: number, lng: number) => ({
  x: 542 + (lng - 39.8262) * 93,
  y: 1108 - (lat - 21.4225) * 100,
});

const COAST =
  '<path d="M93 300 L233 630 L377 840 L465 970 L481 1100 L583 1235 L658 1337 L795 1560 L874 1980 L813 1950 L507 1690 L298 1290 L140 860 L26 640 L-19 525 L-40 430 L23 480 Z" fill="#0A1A28" class="coast" stroke="#2E5673" stroke-width="2" stroke-linejoin="round"/>' +
  '<path d="M-60 150 L42 100 L70 45 L85 0 L-60 0 Z" fill="#0A1A28" class="coast" stroke="#2E5673" stroke-width="2" stroke-linejoin="round"/>';

export function mapSvg(): string {
  let grid = '';
  for (let y = 100; y < 2000; y += 100) grid += `<path d="M0 ${y} H900"/>`;
  for (let x = 93; x < 900; x += 93) grid += `<path d="M${x} 0 V2000"/>`;
  return (
    '<svg width="900" height="2000" viewBox="0 0 900 2000">' +
    `<g class="grid" stroke="#16324A" stroke-width="1">${grid}</g>` +
    COAST +
    '<text x="360" y="1160" text-anchor="middle" font-family="Nunito, sans-serif" font-size="13" font-style="italic" fill="#5E86A3">Red Sea</text>' +
    '</svg>'
  );
}

type Place = { name: string; lat: number; lng: number; city?: boolean; detail?: boolean; side?: 'right' | 'below' };

const PLACES: Place[] = [
  { name: 'Makkah', lat: 21.4225, lng: 39.8262, city: true },
  { name: 'Madinah', lat: 24.4672, lng: 39.6111, city: true },
  { name: 'Badr', lat: 23.7333, lng: 38.7833 },
  { name: "Ta'if", lat: 21.2703, lng: 40.4158, side: 'right' },
  { name: 'The Kaaba', lat: 21.4225, lng: 39.8262, detail: true },
  { name: 'Cave of Hira', lat: 21.4574, lng: 39.8576, detail: true, side: 'right' },
  { name: 'Arafat', lat: 21.3549, lng: 39.984, detail: true, side: 'right' },
  { name: "The Prophet's Mosque", lat: 24.4672, lng: 39.6111, detail: true, side: 'below' },
  { name: 'Mount Uhud', lat: 24.5175, lng: 39.6131, detail: true },
  { name: 'Quba', lat: 24.4393, lng: 39.6172, detail: true, side: 'right' },
];

export const places = PLACES.map((p) => ({ ...p, ...project(p.lat, p.lng) }));
