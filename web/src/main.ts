import Lenis from 'lenis';
import { mountTimelinePage } from './pages/timeline';

// Lenis smooth scroll (useful when future pages scroll vertically)
const lenis = new Lenis({ autoRaf: true });
void lenis; // suppress unused warning — kept for future pages

const app = document.getElementById('app');
if (!app) throw new Error('#app element not found');

void mountTimelinePage(app);
