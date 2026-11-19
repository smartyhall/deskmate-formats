'use strict';

const get = id => document.getElementById(id);
const viewport = get('viewport'), stage = get('stage');
const state = { model: null, original: null, past: [], future: [], name: '', selected: null,
  scale: 1, x: 0, y: 0, box: [0, 0, 8000, 4840], faces: new Map(),
  tool: 'select', points: [], cursor: [4000, 2420], color: 1, fill: null, profile: null };
const svgNS = 'http://www.w3.org/2000/svg';
const names = { L: 'Line', R: 'Rectangle', E: 'Ellipse', UA: 'Arc', UP: 'Polyline / polygon',
  OO: 'Object group', T: 'Stroke text', Uf: 'External-font text' };
const examples = JSON.parse(get('samples').textContent);
const number = value => Number(value.toFixed(5));
const hex = data => [...data].map(value => value.toString(16).padStart(2, '0')).join(' ');
let drag;

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
  draft();
}

function activeEntry() {
  return state.model?.entries.find(item => item.offset === state.selected);
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
  updateMenus();
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
  const box = document.createElementNS(svgNS, 'rect'), selection = document.createElementNS(svgNS, 'g');
  selection.id = 'selection-outline';
  selection.setAttribute('pointer-events', 'none');
  const s = Math.max(state.box[2] / 640, state.box[3] / 418);
  const left = Math.min(x0, x1) - s, right = Math.max(x0, x1) + s;
  const top = Math.min(y0, y1) - s, bottom = Math.max(y0, y1) + s;
  for (const [key, value] of Object.entries({
    x: left, y: top, width: right - left, height: bottom - top,
    fill: 'none', stroke: '#fff0c0', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke',
  })) box.setAttribute(key, value);
  selection.append(box);
  if (right - left > 8 * s && bottom - top > 8 * s) {
    for (const [x, y] of [[left, top], [right, top], [left, bottom], [right, bottom]]) {
      const handle = document.createElementNS(svgNS, 'rect');
      for (const [key, value] of Object.entries({ x: x - 2 * s, y: y - 2 * s, width: 4 * s, height: 4 * s,
        fill: '#fff0c0' })) handle.setAttribute(key, value);
      selection.append(handle);
    }
  }
  stage.querySelector('svg')?.append(selection);
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
    openModel(name, model);
  } catch (error) {
    report(`${name}: ${error.message}`);
  }
}

function openModel(name, model) {
  Object.assign(state, { model, original: model, past: [], future: [], name, selected: null,
    x: 0, y: 0, scale: 1, box: [0, 0, 8000, 4840], profile: DrawFig.structuralProfile(model) });
  get('document-name').textContent = name;
  setTool('select');
  fillInspector(model);
  frame();
  editStatus();
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
  get('local-fonts').replaceChildren(...Array.from(state.faces.values(), face => {
    const entry = node('li', `${face.name} · ${face.filename}`);
    if (face.sha256) entry.title = `SHA-256 ${face.sha256}`;
    return entry;
  }));
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
      const sha256 = globalThis.crypto?.subtle ? hex(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)))
        .replaceAll(' ', '') : null;
      state.faces.set(key, { ...face, filename: file.name, sha256 });
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
  if (state.original && !state.original.blank) download(state.name, state.original.copy(), 'application/octet-stream');
});
get('save').addEventListener('click', () => {
  if (state.model && !state.model.blank) {
    const name = state.original.blank ? 'drawing.fig' : `${stem()}-edited.fig`;
    download(name, state.model.copy(), 'application/octet-stream');
  }
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
  const message = state.model.blank ? 'Choose a drawing tool from Tools.'
    : state.original !== state.model ? 'Edited locally. Save As downloads the FIG.'
    : state.profile === 'flat' ? 'Choose a tool to add objects or select a record to edit.'
    : supported === state.model.elements.size && supported
      ? 'Select a line or rectangle to edit. Original FIG remains available.'
      : supported ? 'Partly editable. Select a top-level line or rectangle.'
      : 'Read-only drawing. Original FIG remains available.';
  report(message);
  updateMenus();
}

function showRevision(model, tag) {
  state.model = model;
  state.profile = DrawFig.structuralProfile(model);
  state.selected = model.entries.find(e => e.tag === tag)?.offset ?? null;
  state.points = [];
  if (state.profile !== 'flat') setTool('select');
  fillInspector(model);
  frame();
  editStatus();
}

function commitRevision(model, tag = activeEntry()?.tag) {
  if (state.past.length === 32) state.past.shift();
  state.past.push({ model: state.model, tag: activeEntry()?.tag });
  state.future.length = 0;
  showRevision(model, tag);
}

function restore(source, destination) {
  if (!source.length) return;
  destination.push({ model: state.model, tag: activeEntry()?.tag });
  const { model, tag } = source.pop();
  showRevision(model, tag);
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
    dialog.close();
    commitRevision(next);
  } catch (error) {
    get('edit-error').textContent = error.message;
  }
});
const menuBar = get('classic-menus');
const menus = [...menuBar.querySelectorAll('details')];

function closeMenus(except = null) {
  for (const menu of menus) if (menu !== except) menu.open = false;
}

function updateMenus() {
  const entry = activeEntry(), model = state.model;
  if (!model) return;
  const limits = {
    save: model === state.original || model.blank,
    download: state.original.blank,
    undo: !state.past.length, redo: !state.future.length,
    edit: get('edit').disabled, label: !entry || !DrawFig.canPermute(model, entry.tag),
    delete: !entry || state.profile !== 'flat' || model.entries.length <= 1,
    top: !entry || model.entries.at(-1) === entry, bottom: !entry || model.entries[0] === entry,
    group: state.profile !== 'flat' || model.entries.length < 2, ungroup: state.profile !== 'group',
    'palette-edit': model.blank, 'font-clear': state.faces.size === 0,
  };
  for (const [name, disabled] of Object.entries(limits)) {
    menuBar.querySelector(`[data-command="${name}"]`).disabled = Boolean(disabled);
  }
  for (const button of menuBar.querySelectorAll('[data-tool]')) {
    button.disabled = state.profile !== 'flat' && button.dataset.tool !== 'select';
    button.setAttribute('aria-pressed', String(state.tool === button.dataset.tool));
  }
}

function commandDialog(title, fields, apply) {
  const form = get('command-form'), dialog = get('command-dialog');
  get('command-title').textContent = title;
  get('command-error').textContent = '';
  get('command-fields').replaceChildren(...fields.map(([key, caption, type, value]) => {
    const label = node('label', caption), field = node('input');
    field.name = key;
    field.type = type;
    field.value = value;
    field.required = key !== 'fill';
    label.append(field);
    return label;
  }));
  form.onsubmit = event => {
    event.preventDefault();
    try {
      apply(Object.fromEntries(new FormData(form)));
      dialog.close();
    } catch (error) {
      get('command-error').textContent = error.message;
    }
  };
  dialog.showModal();
}

get('command-cancel').addEventListener('click', () => get('command-dialog').close());

function order(top) {
  const tag = activeEntry().tag;
  const other = state.model.entries.filter(e => e.tag !== tag).map(e => e.tag);
  commitRevision(DrawFig.reorder(state.model, top ? [...other, tag] : [tag, ...other]));
}

const commands = {
  help: () => report('O opens a FIG. Shift+1–7 opens menus. Arrows and Space place points. Enter finishes a path. Escape cancels.'),
  new: () => openModel('Untitled', DrawFig.blank()),
  inspector: () => {
    document.querySelector('main').classList.toggle('inspection-hidden');
  },
  delete: () => commitRevision(DrawFig.remove(state.model, activeEntry().tag), null),
  top: () => order(true), bottom: () => order(false),
  group: () => {
    const next = DrawFig.group(state.model);
    commitRevision(next, next.entries[0].tag);
  },
  ungroup: () => commitRevision(DrawFig.ungroup(state.model), null),
  label: () => {
    const entry = activeEntry(), item = state.model.elements.get(entry.offset);
    commandDialog('Edit outline label', [['label', 'Use the same characters', 'text', String.fromCharCode(...item.text)]],
      values => commitRevision(DrawFig.permuteLabel(state.model, entry.tag, values.label)));
  },
  'palette-edit': () => {
    const index = state.color, rgb = state.model.palette.get(index);
    commandDialog('Palette color', [['index', 'Index (0–15)', 'number', index], ['rgb', 'RGB', 'color', '#' + rgb.map(v => v.toString(16).padStart(2, '0')).join('')]],
      values => commitRevision(DrawFig.paletteColor(state.model, Number(values.index),
        values.rgb.slice(1).match(/../g).map(v => Number.parseInt(v, 16)))));
  },
  ink: () => commandDialog('New object ink and fill', [
    ['color', 'Ink index (0–15)', 'number', state.color],
    ['fill', 'Fill index (blank for none)', 'number', state.fill ?? ''],
  ], values => {
    const color = Number(values.color), fill = values.fill === '' ? null : Number(values.fill);
    const valid = v => Number.isInteger(v) && v >= 0 && v <= 15;
    if (!valid(color) || (fill !== null && !valid(fill))) throw new Error('Use palette indices 0–15.');
    Object.assign(state, { color, fill });
    draft();
  }),
};

menuBar.addEventListener('click', event => {
  const summary = event.target.closest('summary');
  if (summary) closeMenus(summary.parentElement);
  const button = event.target.closest('button');
  if (!button || button.disabled) return;
  closeMenus();
  try {
    if (button.dataset.tool) setTool(button.dataset.tool);
    else if (button.dataset.zoom) adjust(Number(button.dataset.zoom));
    else if (commands[button.dataset.command]) commands[button.dataset.command]();
    else get(button.dataset.command)?.click();
  } catch (error) {
    report(error.message);
  }
});
menuBar.addEventListener('keydown', event => {
  const menu = event.target.closest('details');
  if (event.key === 'Escape') {
    closeMenus();
    menu?.querySelector('summary').focus();
    event.preventDefault();
    return;
  }
  if (!menu || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;
  menu.open = true;
  const buttons = [...menu.querySelectorAll('button:not(:disabled), select')];
  if (!buttons.length) return;
  const focused = buttons.indexOf(document.activeElement);
  const step = event.key === 'ArrowUp' ? -1 : 1;
  buttons[(focused < 0 ? (step < 0 ? buttons.length - 1 : 0) : (focused + step + buttons.length) % buttons.length)].focus();
  event.preventDefault();
});
document.addEventListener('pointerdown', event => {
  if (!menuBar.contains(event.target)) closeMenus();
});
window.addEventListener('keydown', event => {
  if (event.ctrlKey || event.metaKey || event.altKey || event.target.closest('dialog, input, select')) return;
  const fn = /^F([1-7])$/.exec(event.key);
  const digit = event.shiftKey && /^Digit([1-7])$/.exec(event.code);
  const menu = menus[Number((fn || digit)?.[1]) - 1];
  if (menu) {
    const opening = !menu.open;
    closeMenus();
    menu.open = opening;
    menu.querySelector('summary').focus();
    event.preventDefault();
  } else if (event.key.toLowerCase() === 'o') {
    get('file').click();
    event.preventDefault();
  }
});

function setTool(tool) {
  state.tool = tool;
  state.points = [];
  viewport.classList.toggle('drawing', tool !== 'select');
  updateMenus();
  draft();
  if (tool !== 'select') {
    viewport.focus();
    const path = tool === 'polyline' || tool === 'polygon';
    report(path ? 'Click or press Space to add points. Enter finishes. Escape cancels.'
      : 'Click or press Space to set each endpoint. Escape cancels.');
  }
}

function twoPointTool() {
  return ['L', 'R', 'E'].includes(state.tool);
}

function draft() {
  const svg = stage.querySelector('svg');
  const old = svg?.querySelector('#drawing-draft');
  old?.remove();
  if (!svg || state.tool === 'select') return;
  const group = document.createElementNS(svgNS, 'g');
  group.id = 'drawing-draft';
  const [x, y] = state.cursor;
  const transient = drag?.drawing && drag?.moved && !state.points.length ? [drag.start] : [];
  const points = state.points.length ? state.points : transient;
  const [a, b] = points[0] ?? state.cursor;
  let guide = '';
  if (points.length) {
    if (state.tool === 'E') guide = `<ellipse cx="${(a+x)/2}" cy="${(b+y)/2}" rx="${Math.abs(a-x)/2}" ry="${Math.abs(b-y)/2}"/>`;
    else if (state.tool === 'R') guide = `<rect x="${Math.min(a,x)}" y="${Math.min(b,y)}" width="${Math.abs(a-x)}" height="${Math.abs(b-y)}"/>`;
    else guide = `<polyline points="${[...points, state.cursor].map(p => p.join(',')).join(' ')}"/>`;
  }
  const unit = Math.max(state.box[2] / 640, state.box[3] / 418) / state.scale;
  group.setAttribute('fill', 'none');
  group.setAttribute('stroke', '#ffe7a0');
  group.setAttribute('pointer-events', 'none');
  group.innerHTML = guide + `<path d="M ${x-5*unit} ${y} H ${x+5*unit} M ${x} ${y-5*unit} V ${y+5*unit}"/>`;
  group.querySelectorAll('*').forEach(el => el.setAttribute('vector-effect', 'non-scaling-stroke'));
  svg.append(group);
}

function worldPoint(event) {
  const rect = stage.getBoundingClientRect(), [x, y, width, height] = state.box;
  return [x + width * (event.clientX - rect.left) / rect.width,
    y + height * (event.clientY - rect.top) / rect.height].map(v => Math.round(v * 65536) / 65536);
}

function finishDrawing(points) {
  try {
    let { tool, fill } = state;
    let geometry = points.map(point => point.map(Math.round));
    if (twoPointTool()) {
      const [[x, y], [a, b]] = points;
      const bounds = tool !== 'L' ? [Math.min(x,a), Math.min(y,b), Math.max(x,a), Math.max(y,b)] : [x,y,a,b];
      geometry = bounds.map(v => Math.round(v * 65536));
    }
    if (tool === 'L' || tool === 'polyline') fill = null;
    const model = DrawFig.add(state.model, tool, geometry, { color: state.color, fill });
    commitRevision(model, model.entries.at(-1).tag);
  } catch (error) {
    report(error.message);
  }
}

function placePoint() {
  const point = [...state.cursor];
  if (state.points.length && twoPointTool()) finishDrawing([state.points[0], point]);
  else if (state.points.length >= 4096) report('Finish the current path before adding more points.');
  else {
    state.points.push(point);
    draft();
  }
}

viewport.addEventListener('keydown', event => {
  const move = { ArrowUp: [0, 25], ArrowDown: [0, -25], ArrowLeft: [25, 0], ArrowRight: [-25, 0] }[event.key];
  if (state.tool !== 'select') {
    if (move) state.cursor = state.cursor.map((v, i) => v - move[i]);
    else if (event.key === ' ') placePoint();
    else if (event.key === 'Enter' && state.points.length >= (state.tool === 'polygon' ? 3 : 2)) finishDrawing(state.points);
    else if (event.key === 'Escape') state.points = [];
    else return;
    draft();
    event.preventDefault();
    return;
  }
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
  draft();
}, { passive: false });

function rootOffset(offset) {
  if (offset === null) return null;
  const parents = new Map();
  for (const part of state.model.elements.values()) {
    for (const child of part.children) parents.set(child, part.offset);
  }
  while (parents.has(offset)) offset = parents.get(offset);
  return offset;
}

viewport.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  if (state.tool !== 'select') {
    const start = worldPoint(event);
    drag = { drawing: true, start, x: event.clientX, y: event.clientY, moved: false };
    state.cursor = start;
    draft();
  } else {
    drag = { x: event.clientX, y: event.clientY, startX: state.x, startY: state.y,
      offset: event.target.getAttribute('data-offset'), moved: false };
  }
  viewport.setPointerCapture(event.pointerId);
});
viewport.addEventListener('pointermove', event => {
  if (state.tool !== 'select') {
    state.cursor = worldPoint(event);
    if (drag?.drawing && twoPointTool()) {
      drag.moved ||= Math.abs(event.clientX - drag.x) + Math.abs(event.clientY - drag.y) >= 4;
    }
    draft();
    return;
  }
  if (!drag) return;
  const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
  if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
  drag.moved = true;
  state.x = drag.startX + dx;
  state.y = drag.startY + dy;
  viewportTransform();
});
viewport.addEventListener('pointerup', event => {
  const finished = drag;
  drag = null;
  if (finished?.drawing) {
    state.cursor = worldPoint(event);
    if (finished.moved && !state.points.length) finishDrawing([finished.start, state.cursor]);
    else placePoint();
  } else if (finished && !finished.moved) selection(rootOffset(finished.offset === null ? null : Number(finished.offset)));
});
viewport.addEventListener('lostpointercapture', () => { drag = null; draft(); });
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
get('examples').addEventListener('change', () => {
  closeMenus();
  showExample(get('examples').value);
});
get('examples').value = 'compound-landscape';
showExample(get('examples').value);
