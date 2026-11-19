'use strict';

const catalogue = window.drawComparisons;
const lookup = id => document.getElementById(id);
const state = { milestone: 'baseline-pr120', id: 'compound-landscape', mode: 'split',
  scale: null, x: 0, y: 0, alternate: false };
const panels = lookup('panels');
const formats = {
  'native.png': 'Native PNG',
  'renderer.png': 'Renderer PNG',
  'diff.png': 'Difference PNG',
  'renderer.svg': 'Scalable SVG',
};

function element(tag, text, options = {}) {
  const node = Object.assign(document.createElement(tag), options);
  if (text !== null) node.textContent = text;
  return node;
}

function selected() {
  const milestone = catalogue[state.milestone];
  return { milestone, drawing: milestone.cases.find(item => item.id === state.id) };
}

function fitScale() {
  const { drawing } = selected();
  const [width, height] = drawing.dimensions;
  const views = panels.querySelectorAll('.viewport');
  return Math.max(.1, Math.min(...[...views].map(view =>
    Math.min(view.clientWidth / width, view.clientHeight / height))));
}

function position() {
  const scale = state.scale ?? fitScale();
  for (const stack of panels.querySelectorAll('.image-stack')) {
    stack.style.transform = `translate(calc(-50% + ${state.x}px),calc(-50% + ${state.y}px)) scale(${scale})`;
  }
  lookup('zoom-status').value = state.scale === null ? 'Fit' : `${Math.round(scale*100)}%`;
}

function scaleTo(scale, anchorX = 0, anchorY = 0) {
  const before = state.scale ?? fitScale();
  state.scale = Math.max(.1, Math.min(8, scale));
  const ratio = state.scale / before;
  state.x = anchorX + (state.x - anchorX) * ratio;
  state.y = anchorY + (state.y - anchorY) * ratio;
  position();
}

function figure(title, drawing, kinds) {
  const fig = element('figure', null);
  const field = element('div', null, { className: 'viewport', tabIndex: 0 });
  field.setAttribute('aria-label', `${title}. Use arrow keys to pan.`);
  const layer = element('div', null, { className: 'image-stack' });
  const [width, height] = drawing.dimensions;
  Object.assign(layer.style, { width: `${width}px`, height: `${height}px` });
  for (const kind of kinds) {
    const img = element('img', null, { src: drawing.artifacts[kind].href, alt: `${drawing.title} · ${formats[kind]}`,
      width, height, draggable: false });
    if (state.mode === 'overlay' && kind === 'renderer.png') {
      img.id = 'overlay-image';
      img.style.opacity = lookup('opacity').value / 100;
    }
    layer.append(img);
  }
  let anchor;
  field.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    anchor = [event.clientX - state.x, event.clientY - state.y];
    field.setPointerCapture(event.pointerId);
  });
  field.addEventListener('pointermove', event => {
    if (!anchor) return;
    [state.x, state.y] = [event.clientX - anchor[0], event.clientY - anchor[1]];
    position();
  });
  field.addEventListener('lostpointercapture', () => { anchor = null; });
  field.addEventListener('wheel', event => {
    event.preventDefault();
    const rect = field.getBoundingClientRect();
    scaleTo((state.scale ?? fitScale()) * (event.deltaY < 0 ? 1.2 : 1 / 1.2),
      event.clientX - rect.left - rect.width / 2, event.clientY - rect.top - rect.height / 2);
  }, { passive: false });
  field.addEventListener('keydown', event => {
    const offset = { ArrowUp: [0, 24], ArrowDown: [0, -24], ArrowLeft: [24, 0], ArrowRight: [-24, 0] }[event.key];
    if (!offset) return;
    event.preventDefault();
    state.x += offset[0];
    state.y += offset[1];
    position();
  });
  field.append(layer);
  fig.append(element('figcaption', title), field);
  return fig;
}

function showPanels() {
  const { drawing } = selected();
  const show = (...views) => panels.replaceChildren(...views.map(([title, ...kinds]) => figure(title, drawing, kinds)));
  panels.classList.toggle('single', state.mode !== 'split');
  lookup('overlay-tools').hidden = state.mode !== 'overlay';
  const toggle = lookup('switch');
  toggle.hidden = state.mode !== 'switch';
  toggle.textContent = state.alternate ? 'Show native' : 'Show renderer';
  lookup('legend').hidden = state.mode !== 'difference';
  lookup('view-help').textContent = state.mode === 'switch'
    ? 'Press A to switch sides. Drag to pan or use the wheel to zoom.'
    : 'Drag to pan. Use the wheel or zoom controls to enlarge pixels.';
  switch (state.mode) {
    case 'split': show(['Native Draw', 'native.png'], ['Independent renderer', 'renderer.png']); break;
    case 'overlay': show(['Native Draw + independent renderer', 'native.png', 'renderer.png']); break;
    case 'switch':
      show(state.alternate ? ['Independent renderer', 'renderer.png'] : ['Native Draw', 'native.png']); break;
    case 'difference': show(['Drawing pixel difference', 'diff.png']); break;
  }
  position();
}

const percent = value => value === null ? '—' : value > 0 && value < .0005
  ? '<0.1%' : `${(value * 100).toFixed(1)}%`;
const number = value => new Intl.NumberFormat('en').format(value);
const link = (title, href) => element('a', title, { href });

function rows(container, pairs, wrapped) {
  const children = [];
  for (const [name, value] of pairs) {
    const description = element('dd', null);
    description.append(value);
    const row = [element('dt', name), description];
    if (wrapped) {
      const div = element('div', null);
      div.append(...row);
      children.push(div);
    } else children.push(...row);
  }
  container.replaceChildren(...children);
}

function render() {
  const { milestone, drawing } = selected();
  const items = milestone.cases.filter(item => item.featured).map(item => {
    const button = element('button', null, { className: 'case', type: 'button' });
    button.append(element('img', null, { src: item.artifacts['native.png'].href, alt: '', width: 640, height: 418 }),
      element('span', item.title));
    button.setAttribute('aria-current', String(item.id === drawing.id));
    button.addEventListener('click', () => change(item.id));
    return button;
  });
  lookup('featured').replaceChildren(...items);
  const controls = milestone.cases.filter(item => !item.featured);
  lookup('diagnostics').replaceChildren(element('option', 'Choose a control', { value: '' }),
    ...controls.map(item => element('option', item.title, { value: item.id })));
  lookup('diagnostics').value = drawing.featured ? '' : drawing.id;
  lookup('case-title').textContent = drawing.title;
  lookup('case-description').textContent = drawing.description;
  const metrics = drawing.metrics;
  rows(lookup('metrics'), [
    ['Foreground IoU', percent(metrics.foreground_iou)],
    ['Exact foreground RGB', percent(metrics.exact_rgb_on_foreground_union)],
    ['Native drawing pixels', number(metrics.native_foreground_pixels)],
    ['Renderer omissions', number(drawing.omissions.length)],
  ], true);
  const sources = [...Object.entries(formats).map(([kind, title]) => link(title, drawing.artifacts[kind].href)),
    link('Native FIG', drawing.source_href), link('Milestone manifest', milestone.href)];
  lookup('artifacts').replaceChildren(...sources.map(a => {
    const row = element('li', null);
    row.append(a);
    return row;
  }));
  const cap = drawing.native_capture;
  const omissions = drawing.omissions.map(item => `${item.kind_hex} at list byte ${item.offset} (${item.reason.replaceAll('_', ' ')})`);
  rows(lookup('provenance'), [
    ['Native source', `${cap.dos_name} · ${drawing.source_sha256}`],
    ['Framebuffer SHA-256', cap.framebuffer_sha256],
    ['Capture', `${cap.source_role.replaceAll('-', ' ')} · ${cap.zoom} zoom · crop ${cap.crop_xyxy.join(', ')}`],
    ['Renderer revision', milestone.renderer_revision],
    ['Rasterizer', `${milestone.rasterizer.name} ${milestone.rasterizer.version}`],
    ['View mapping', milestone.view_mapping.method],
    ['Limits', milestone.limits],
    ['Omitted records', omissions.join('; ') || 'None reported'],
  ], false);
  showPanels();
}

function reset(scale = null) {
  Object.assign(state, { x: 0, y: 0, scale });
  position();
}

function change(id) {
  state.id = id;
  state.alternate = false;
  reset();
  render();
}

function flip() {
  state.alternate = !state.alternate;
  showPanels();
}

const version = lookup('milestone');
const milestoneNames = {
  'baseline-pr120': 'PR #120 baseline',
  'arc-vector-01': 'Quadratic SVG',
  'vga-raster-01': 'RSX VGA raster',
  'vga-strokes-02': 'RSX VGA raster + axis strokes',
};
for (const key of Object.keys(catalogue)) {
  version.append(element('option', milestoneNames[key] ?? key, { value: key }));
}
version.value = state.milestone;
version.addEventListener('change', () => { state.milestone = version.value; change(state.id); });
lookup('diagnostics').addEventListener('change', event => { if (event.target.value) change(event.target.value); });
lookup('modes').addEventListener('click', event => {
  if (!event.target.dataset.mode) return;
  state.mode = event.target.dataset.mode;
  for (const button of lookup('modes').querySelectorAll('button')) {
    button.setAttribute('aria-pressed', String(button === event.target));
  }
  showPanels();
});
lookup('opacity').addEventListener('input', event => { lookup('overlay-image').style.opacity = event.target.value / 100; });
lookup('switch').addEventListener('click', flip);
lookup('zoom-in').addEventListener('click', () => scaleTo((state.scale ?? fitScale()) * 1.4));
lookup('zoom-out').addEventListener('click', () => scaleTo((state.scale ?? fitScale()) / 1.4));
lookup('fit').addEventListener('click', () => reset());
lookup('pixel').addEventListener('click', () => reset(1));
window.addEventListener('resize', position);
window.addEventListener('keydown', event => {
  if (state.mode === 'switch' && !event.repeat && event.key.toLowerCase() === 'a' &&
      !['INPUT', 'SELECT', 'TEXTAREA'].includes(event.target.tagName)) flip();
});
render();
