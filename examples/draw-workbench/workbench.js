'use strict';

const get = id => document.getElementById(id);
const viewport = get('viewport'), stage = get('stage');
const state = { model: null, original: null, past: [], future: [], name: '', selected: null,
  scale: 1, x: 0, y: 0, box: [0, 0, 8000, 4840], faces: new Map() };
const svgNS = 'http://www.w3.org/2000/svg';
const names = { L: 'Line', R: 'Rectangle', E: 'Ellipse', UA: 'Arc', UP: 'Polyline / polygon',
  OO: 'Object group', T: 'Stroke text', Uf: 'External-font text' };
const examples = JSON.parse(get('samples').textContent);
const number = value => Number(value.toFixed(5));
const hex = data => [...data].map(value => value.toString(16).padStart(2, '0')).join(' ');

function node(tag, text) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  return result;
}

function report(text) {
  get('status').textContent = text;
}

function viewportTransform() {
  stage.style.transform = `translate(calc(-50% + ${state.x}px), calc(-50% + ${state.y}px)) scale(${state.scale})`;
  get('zoom').value = `${Math.round(state.scale * 100)}%`;
}

function svgImage(preview, box) {
  const [x, y, w, h] = box;
  const description = preview.substituted ? '<desc>External fonts shown using generic monospace substitutes.</desc>' : '';
  return `<svg xmlns="${svgNS}" viewBox="${box.join(' ')}" width="640" height="418" preserveAspectRatio="none">${description}<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${preview.background}"/>${preview.shapes}</svg>`;
}

function documentPreview(inspect = false) {
  return DrawFig.preview(state.model, { inspect, substitute: get('substitute').checked, faces: state.faces });
}

function frame() {
  if (!state.model) return;
  const preview = documentPreview(true);
  const doc = new DOMParser().parseFromString(svgImage(preview, state.box), 'image/svg+xml');
  stage.replaceChildren(document.importNode(doc.documentElement, true));
  get('drawing-stats').textContent = `${state.model.elements.size} records · ${preview.omissions.length} omitted`
    + (preview.resolved ? ` · ${preview.resolved} runs with local FF1` : '')
    + (preview.substituted ? ` · ${preview.substituted} generic font substitutions` : '');
  get('omissions').replaceChildren(...preview.omissions.map(item =>
    node('li', `${names[item.kind] ?? 'Record'} at list byte ${item.offset} · ${item.reason}`)));
  if (!preview.omissions.length) get('omissions').append(node('li', 'No records omitted in this preview.'));
  selection(state.selected);
  viewportTransform();
}

function selection(offset) {
  state.selected = offset;
  stage.querySelector('#selection-outline')?.remove();
  for (const button of get('objects').querySelectorAll('button')) {
    button.setAttribute('aria-current', String(Number(button.dataset.offset) === offset));
  }
  const record = state.model?.elements.get(offset);
  const entry = state.model?.entries.find(item => item.offset === offset);
  get('edit').disabled = !entry || !DrawFig.canEdit(state.model, entry.tag);
  const inspect = get('inspection');
  if (!record) {
    inspect.textContent = 'Select a record or shape.';
    return;
  }
  const [x0, y0, x1, y1] = record.bounds;
  const details = node('dl');
  const rows = [
    ['Type', `${names[record.kind] ?? 'Unknown'} (${hex(record.raw.slice(0, 2))})`],
    ['List offset', `${record.offset} bytes`],
    ['Bounds', record.bounds.map(number).join(', ')],
    ['16.16 words', record.coords.join(', ')],
    ['Record size', `${record.raw.length} bytes`],
    ['Attributes', hex(record.raw.slice(18, 42)) || '—'],
  ];
  if (record.fontName) {
    const view = new DataView(record.raw.buffer);
    rows.push(['Font reference', record.fontName],
      ['Font size / width words', `${view.getUint16(56, true)}, ${view.getUint16(58, true)}`]);
  }
  if (record.text) rows.push(['Text bytes', hex(record.text.slice(0, 48))]);
  if (record.children.length) rows.push(['Children', record.children.join(', ')]);
  for (const [k, v] of rows) details.append(node('dt', k), node('dd', v));
  inspect.replaceChildren(details);
  const box = document.createElementNS(svgNS, 'rect');
  box.id = 'selection-outline';
  const s = Math.max(state.box[2] / 640, state.box[3] / 418);
  for (const [key, value] of Object.entries({
    x: Math.min(x0, x1) - s, y: Math.min(y0, y1) - s,
    width: Math.abs(x1 - x0) + 2 * s, height: Math.abs(y1 - y0) + 2 * s,
    fill: 'none', stroke: '#fff0c0', 'stroke-width': 1,
    'stroke-dasharray': '3 3', 'vector-effect': 'non-scaling-stroke', 'pointer-events': 'none',
  })) box.setAttribute(key, value);
  stage.querySelector('svg')?.append(box);
}

function fillInspector(model) {
  const stack = [...model.entries].reverse().map(entry => ({ ...entry, depth: 0 }));
  const content = document.createDocumentFragment();
  for (let index = 0; stack.length && index < 1500; index++) {
    const { offset, tag, depth } = stack.pop();
    const record = model.elements.get(offset);
    const b = node('button', `${tag === undefined ? '↳' : `#${tag}`} ${names[record.kind] ?? 'Record'}`);
    b.type = 'button';
    b.dataset.offset = offset;
    b.style.paddingInlineStart = `${6 + 12 * Math.min(depth, 12)}px`;
    b.addEventListener('click', () => selection(offset));
    const row = node('li');
    row.append(b);
    content.append(row);
    for (const child of [...record.children].reverse()) stack.push({ offset: child, depth: depth + 1 });
  }
  if (stack.length) content.append(node('li', 'Display list limited to the first 1,500 rows.'));
  get('objects').replaceChildren(content);
  get('palette').replaceChildren(...Array.from(model.palette.entries()).sort((a, b) => a[0] - b[0]).map(([i, rgb]) => {
    const tile = node('span', i);
    const color = '#' + hex(rgb).replaceAll(' ', '');
    tile.style.background = color;
    tile.title = `Palette index ${i} · ${color.toUpperCase()}`;
    return tile;
  }));
}

function load(name, bytes) {
  try {
    const model = DrawFig.read(bytes);
    Object.assign(state, { model, original: model, past: [], future: [], name, selected: null,
      x: 0, y: 0, scale: 1, box: [0, 0, 8000, 4840] });
    get('document-name').textContent = name;
    fillInspector(model);
    frame();
    editStatus();
  } catch (error) {
    report(`${name}: ${error.message}`);
  }
}

async function openFile(file) {
  if (!file) return;
  if (file.size > DrawFig.MAX_BYTES) {
    report('File exceeds the supported FIG size.');
    return;
  }
  try {
    load(file.name, new Uint8Array(await file.arrayBuffer()));
  } catch (error) {
    report(`Could not open ${file.name}: ${error.message}`);
  }
}

function adjust(scale, x = 0, y = 0) {
  const before = state.scale;
  state.scale = Math.max(.125, Math.min(8, scale));
  state.x = x + (state.x - x) * state.scale / before;
  state.y = y + (state.y - y) * state.scale / before;
  viewportTransform();
}

function fit() {
  if (!state.model) return;
  let loX = Infinity, loY = Infinity, hiX = -Infinity, hiY = -Infinity;
  for (const item of DrawFig.leaves(state.model)) {
    const [x0, y0, x1, y1] = item.bounds;
    loX = Math.min(loX, x0, x1); loY = Math.min(loY, y0, y1);
    hiX = Math.max(hiX, x0, x1); hiY = Math.max(hiY, y0, y1);
  }
  if (!Number.isFinite(loX)) return;
  const pad = Math.max(12, (hiX - loX) / 40, (hiY - loY) / 40);
  const cx = (loX + hiX) / 2, cy = (loY + hiY) / 2;
  const w = Math.max(hiX - loX + 2 * pad, (hiY - loY + 2 * pad) * 8000 / 4840);
  const h = w * 4840 / 8000;
  Object.assign(state, { box: [cx - w / 2, cy - h / 2, w, h], x: 0, y: 0,
    scale: Math.max(.125, Math.min(1, (viewport.clientWidth - 12) / 640, (viewport.clientHeight - 12) / 418)) });
  frame();
}

function download(name, data, media) {
  const value = new Blob([data], { type: media });
  const url = URL.createObjectURL(value);
  const a = node('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

const stem = () => state.name.replace(/\.fig$/i, '');
get('open').addEventListener('click', () => get('file').click());
get('file').addEventListener('change', event => {
  openFile(event.target.files[0]);
  event.target.value = '';
});
get('font-open').addEventListener('click', () => get('font-file').click());
function showFonts() {
  get('font-clear').disabled = state.faces.size === 0;
  get('local-fonts').replaceChildren(...Array.from(state.faces.values(), face =>
    node('li', `${face.name} · ${face.filename}`)));
  frame();
}
get('font-file').addEventListener('change', async event => {
  const files = Array.from(event.target.files);
  event.target.value = '';
  const omissions = [];
  for (const file of files) {
    try {
      if (file.size > DrawFig.MAX_FF1_BYTES) throw new Error('File exceeds the FF1 size limit');
      const bytes = new Uint8Array(await file.arrayBuffer());
      const face = DrawFig.readOutlineFace(bytes);
      const key = face.name.toLowerCase(), existing = state.faces.get(key);
      if (existing && !existing.same(bytes)) throw new Error(`Conflicting local resource for ${face.name}`);
      if (!existing && state.faces.size >= 32) throw new Error('Local font resource limit reached');
      state.faces.set(key, { ...face, filename: file.name });
    } catch (error) {
      omissions.push(`${file.name}: ${error.message}`);
    }
  }
  showFonts();
  report(omissions.length ? omissions.join(' · ') : `${state.faces.size} local FF1 resources available`);
});
get('font-clear').addEventListener('click', () => {
  state.faces.clear();
  showFonts();
  report('Cleared local FF1 resources.');
});
get('download').addEventListener('click', () => {
  if (state.original) download(state.name, state.original.copy(), 'application/octet-stream');
});
get('save').addEventListener('click', () => {
  if (state.model) download(`${stem()}-edited.fig`, state.model.copy(), 'application/octet-stream');
});
get('svg-export').addEventListener('click', () => {
  if (state.model) download(`${stem()}.svg`,
    svgImage(documentPreview(), state.box), 'image/svg+xml');
});
get('png-export').addEventListener('click', () => {
  if (!state.model) return;
  const name = stem();
  const data = svgImage(documentPreview(), state.box);
  const url = URL.createObjectURL(new Blob([data], { type: 'image/svg+xml' }));
  const preview = new Image();
  preview.onload = () => {
    const canvas = node('canvas');
    canvas.width = 640;
    canvas.height = 418;
    canvas.getContext('2d').drawImage(preview, 0, 0);
    canvas.toBlob(png => { if (png) download(`${name}.png`, png, 'image/png'); }, 'image/png');
    URL.revokeObjectURL(url);
  };
  preview.onerror = () => { URL.revokeObjectURL(url); report('PNG preview could not be exported.'); };
  preview.src = url;
});
get('minus').addEventListener('click', () => adjust(state.scale / 2));
get('plus').addEventListener('click', () => adjust(state.scale * 2));
get('normal').addEventListener('click', () => {
  Object.assign(state, { box: [0, 0, 8000, 4840], scale: 1, x: 0, y: 0 });
  frame();
});
get('fit').addEventListener('click', fit);
get('substitute').addEventListener('change', frame);

function editStatus() {
  get('save').disabled = state.original === state.model;
  get('undo').disabled = !state.past.length;
  get('redo').disabled = !state.future.length;
  const supported = state.model.entries.filter(entry => DrawFig.canEdit(state.model, entry.tag)).length;
  const message = state.original !== state.model ? 'Edited locally. Save FIG As downloads the edited copy.'
    : supported === state.model.elements.size && supported
      ? 'Select a line or rectangle to edit. Original FIG remains available.'
      : supported ? 'Partly editable. Select a top-level line or rectangle.'
      : 'Read-only drawing. Original FIG remains available.';
  report(message);
}

function restore(source, destination) {
  if (!source.length) return;
  destination.push(state.model);
  state.model = source.pop();
  frame();
  editStatus();
}
get('undo').addEventListener('click', () => restore(state.past, state.future));
get('redo').addEventListener('click', () => restore(state.future, state.past));

const dialog = get('edit-dialog');
get('edit-cancel').addEventListener('click', () => dialog.close());
get('edit').addEventListener('click', () => {
  const entry = state.model.entries.find(item => item.offset === state.selected);
  if (!entry) return;
  const kind = DrawFig.canEdit(state.model, entry.tag);
  if (!kind) return;
  const record = state.model.elements.get(entry.offset);
  const [x0, y0, x1, y1] = record.bounds;
  const fields = kind === 'L' ? [['dx', 'Horizontal move', 0], ['dy', 'Vertical move', 0],
    ['color', 'Palette index', record.raw[18]]] : [['width', 'Width', x1 - x0], ['height', 'Height', y1 - y0]];
  get('edit-title').textContent = `Edit ${names[kind].toLowerCase()} #${entry.tag}`;
  get('edit-fields').replaceChildren(...fields.map(([key, label, value]) => {
    const row = node('label', label);
    const field = node('input');
    field.name = key;
    field.type = 'number';
    field.step = 'any';
    field.required = true;
    field.value = value;
    row.append(field);
    return row;
  }));
  get('edit-form').dataset.tag = entry.tag;
  get('edit-error').textContent = '';
  dialog.showModal();
});
get('edit-form').addEventListener('submit', event => {
  event.preventDefault();
  const options = Object.fromEntries([...new FormData(event.target)].map(([key, value]) =>
    [key, Number(value) * (key === 'color' ? 1 : 65536)]));
  try {
    const next = DrawFig.edit(state.model, Number(event.target.dataset.tag), options);
    if (state.past.length === 32) state.past.shift();
    state.past.push(state.model);
    state.future.length = 0;
    state.model = next;
    dialog.close();
    frame();
    editStatus();
  } catch (error) {
    get('edit-error').textContent = error.message;
  }
});
window.addEventListener('keydown', event => {
  if (event.ctrlKey || event.metaKey || event.altKey || ['INPUT', 'SELECT', 'BUTTON'].includes(event.target.tagName)) return;
  if (event.key.toLowerCase() === 'o') {
    event.preventDefault();
    get('file').click();
  }
});
viewport.addEventListener('keydown', event => {
  const move = { ArrowUp: [0, 25], ArrowDown: [0, -25], ArrowLeft: [25, 0], ArrowRight: [-25, 0] }[event.key];
  if (!move) return;
  event.preventDefault();
  state.x += move[0];
  state.y += move[1];
  viewportTransform();
});
viewport.addEventListener('wheel', event => {
  event.preventDefault();
  const rect = viewport.getBoundingClientRect();
  adjust(state.scale * (event.deltaY < 0 ? 1.25 : .8),
    event.clientX - rect.left - rect.width / 2, event.clientY - rect.top - rect.height / 2);
}, { passive: false });

let drag;
viewport.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  drag = { x: event.clientX, y: event.clientY, startX: state.x, startY: state.y,
    offset: event.target.getAttribute('data-offset'), moved: false };
  viewport.setPointerCapture(event.pointerId);
});
viewport.addEventListener('pointermove', event => {
  if (!drag) return;
  const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
  if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
  drag.moved = true;
  state.x = drag.startX + dx;
  state.y = drag.startY + dy;
  viewportTransform();
});
viewport.addEventListener('pointerup', () => {
  if (drag && !drag.moved) selection(drag.offset === null ? null : Number(drag.offset));
  drag = null;
});
viewport.addEventListener('lostpointercapture', () => { drag = null; });
window.addEventListener('dragover', event => event.preventDefault());
window.addEventListener('drop', event => {
  event.preventDefault();
  if (event.dataTransfer.files.length !== 1) report('Drop one FIG file at a time.');
  else openFile(event.dataTransfer.files[0]);
});

for (const sample of examples) {
  const option = node('option', sample.title);
  option.value = sample.id;
  get('examples').append(option);
}
function showExample(id) {
  const sample = examples.find(item => item.id === id);
  if (!sample) return;
  load(sample.name, Uint8Array.from(atob(sample.data), char => char.charCodeAt(0)));
  if (viewport.clientWidth < 640) fit();
}
get('examples').addEventListener('change', () => showExample(get('examples').value));
get('examples').value = 'compound-landscape';
showExample(get('examples').value);
