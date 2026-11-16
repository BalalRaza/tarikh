import events from './events.json';

const app = document.getElementById('app')!;
app.innerHTML = `<h1>Tarikh</h1><ol>${events
  .map((e) => `<li>${e.title} (${e.ce})</li>`)
  .join('')}</ol>`;
