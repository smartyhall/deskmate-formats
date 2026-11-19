'use strict';

// Native length fields are little endian. A coordinate is a signed whole
// word followed by an unsigned fraction. Keep both original words.
const DrawFig = (() => {
  const FORM = 22, LIST = 44, MAX_BYTES = 131182;
  const sizes = { L: 20, R: 24, E: 24 };
  const require = (test, reason) => { if (!test) throw new Error(reason); };
  const chunk = (data, start, end) => data.slice(start, end);
  const char = value => String.fromCharCode(value);
  const hex = value => value.toString(16).padStart(2, '0');

  function read(source) {
    require(source instanceof Uint8Array && source.length >= 113 && source.length <= MAX_BYTES,
      'Invalid FIG file size');
    const data = new Uint8Array(source);
    const view = new DataView(data.buffer);
    const u16 = offset => view.getUint16(offset, true);
    const i16 = offset => view.getInt16(offset, true);
    require(data[0] === 20 && char(data[1]) + char(data[2]) + char(data[3]) === 'FIG',
      'Unsupported FIG signature');
    const listBytes = u16(40), strokeBytes = u16(42);
    const listEnd = LIST + listBytes, formEnd = listEnd + strokeBytes, paletteStart = formEnd + 2;
    require(data.length === paletteStart + 65 && u16(formEnd) === 16, 'Inconsistent FIG form or palette extent');
    require(data[FORM] === 1 && data[FORM + 1] <= 1, 'Unsupported form flags');
    require(listBytes >= 2 && listBytes === 2 * u16(24) && strokeBytes === u16(26), 'Inconsistent form size fields');
    const palette = new Map();
    for (let i = paletteStart; i < paletteStart + 64; i += 4) {
      require(data[i] < 16 && !palette.has(data[i]), 'Invalid FIG palette indices');
      palette.set(data[i], [...data.slice(i + 1, i + 4)]);
    }
    const count = u16(LIST);
    const directoryEnd = 2 + 4 * count;
    require(directoryEnd <= listBytes, 'Form directory exceeds list');
    const entries = [], offsets = new Set(), tags = new Set(), group = new Map(), pending = [];
    function enqueue(offset) {
      require(!offsets.has(offset), 'Duplicate or cyclic group reference');
      require(offset >= directoryEnd && offset <= listBytes - 18, 'Element reference outside form list');
      offsets.add(offset);
      pending.push(offset);
    }
    for (let i = 0; i < count; i++) {
      const offset = 2 * u16(LIST + 2 + 4 * i), tag = u16(LIST + 4 + 4 * i);
      require(!tags.has(tag), 'Duplicate display-list tag');
      tags.add(tag);
      enqueue(offset);
      entries.push({ offset, tag });
    }
    for (const offset of pending) {
      const start = LIST + offset;
      if (data[start] !== 79 || data[start + 1] !== 79) continue;
      require(start + 20 <= listEnd, 'Truncated group header');
      const count = u16(start + 18), children = [];
      require(start + 20 + count * 2 <= listEnd, 'Truncated group references');
      for (let i = 0; i < count; i++) {
        const child = 2 * u16(start + 20 + i * 2);
        enqueue(child);
        children.push(child);
      }
      group.set(offset, children);
    }
    const sorted = [...offsets].sort((a, b) => a - b);
    const elements = new Map();
    for (let i = 0; i < sorted.length; i++) {
      const offset = sorted[i], start = LIST + offset;
      const next = sorted[i + 1] ?? listBytes, length = next - offset;
      require(length >= 18, 'Overlapping element records');
      const modifier = data[start + 1];
      const kind = char(data[start]) + (data[start] === 85 || group.has(offset) ? char(modifier) : '');
      const coords = [], bounds = [];
      for (let i = 0; i < 4; i++) {
        const at = start + 2 + 4 * i;
        const whole = i16(at), fraction = u16(at + 2);
        coords.push(whole, fraction);
        bounds.push(whole + fraction / 65536);
      }
      const children = group.get(offset) ?? [];
      const points = [];
      let text = null, fontName = null;
      if (Object.hasOwn(sizes, kind)) require(length >= sizes[kind], `Truncated ${kind} record`);
      else if (kind === 'OO') require(length >= 20 + 2 * children.length, 'Overlapping group records');
      else if (kind === 'T') {
        require(length >= 22 && length >= 22 + data[start + 20], 'Truncated text');
        text = data.slice(start + 22, start + 22 + data[start + 20]);
      } else if (kind.startsWith('U')) {
        require(length >= 20, 'Truncated extended record');
        const size = 2 * u16(start + 18);
        require(size >= 20 && size <= length, 'Extended element exceeds its record');
        if (kind === 'UP') {
          require(size >= 36, 'Truncated polyline header');
          const count = u16(start + 34);
          require(size === 36 + 4 * count, 'Polyline point count disagrees with size');
          for (let i = 0; i < count; i++) points.push([u16(start + 36 + i * 4), u16(start + 38 + i * 4)]);
        } else if (kind === 'Uf' && size >= 102) {
          const count = u16(start + 96), end = start + 100 + count;
          const area = data.slice(start + 26, start + 56);
          const boundary = area.indexOf(0);
          const name = area.slice(0, boundary);
          if (u16(start + 98) === 0 && end <= start + size && start + size <= end + 2
              && (start + size !== end + 2 || (data[end] === 0 && data[end + 1] === 0))
              && boundary > 0 && area.slice(boundary).every(value => value === 0)
              && name.every(value => 32 <= value && value <= 126)
              && !data.slice(start + 100, end).includes(0)) {
            text = data.slice(start + 100, end);
            fontName = String.fromCharCode(...name);
          }
        }
      }
      elements.set(offset, { offset, kind, modifier, coords, bounds, children, points, text, fontName,
        raw: chunk(data, start, LIST + next) });
    }
    const model = {
      entries, elements, palette, pageSetup: chunk(data, 0, FORM),
      header: chunk(data, FORM, 40), strokes: chunk(data, listEnd, formEnd),
      trailer: chunk(data, data.length - 1), copy: () => new Uint8Array(data),
    };
    return model;
  }

  function* leaves(model) {
    const pending = model.entries.map(entry => entry.offset).reverse();
    while (pending.length) {
      const item = model.elements.get(pending.pop());
      if (item.kind !== 'OO') yield item;
      else for (let i = item.children.length - 1; i >= 0; i--) pending.push(item.children[i]);
    }
  }

  const safeNumber = value => Number(value.toPrecision(9));

  function strokes(data) {
    const result = new Map();
    if (!data.length) return result;
    const view = new DataView(data.buffer);
    require(data.length >= 2 && view.getUint16(data.length - 2, true) === 0, 'Missing stroke terminator');
    let at = 0;
    const bound = data.length - 2;
    while (at < bound) {
      require(at + 4 <= bound, 'Truncated glyph header');
      const size = view.getUint16(at, true);
      const end = at + size, id = 256 * data[at + 2] + data[at + 3];
      require(size >= 4 && end <= bound && !result.has(id), 'Invalid glyph length or identity');
      const paths = [];
      for (let pos = at + 4; pos < end;) {
        let last = pos;
        while (last < end && data[last]) last++;
        const length = last - pos;
        if (length) {
          require(length >= 4 && length % 2 === 0, 'Invalid stroke path length');
          const path = [];
          for (let i = pos; i < last; i += 2) {
            require(data[i] <= 128 && data[i + 1] <= 128, 'Invalid stroke coordinates');
            path.push([data[i], data[i + 1]]);
          }
          paths.push(path);
        }
        pos = last + 1;
      }
      result.set(id, paths);
      at = end;
    }
    return result;
  }

  const escaped = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

  function arcQuadratic(part) {
    if (part.kind !== 'UA' || part.raw.length !== 44 || part.raw[18] !== 22 || part.raw[19] !== 0) return null;
    const [x0, y0, x1, y1] = part.bounds;
    const data = new DataView(part.raw.buffer);
    const v = index => data.getInt16(28 + 2 * index, true);
    if (v(0) <= 0 || v(1) <= 0 || x1 < x0 || y1 < y0) return null;
    const sx = (x1 - x0) / v(0), sy = (y1 - y0) / v(1);
    const a = [x0 + v(2) * sx, y0 + v(3) * sy];
    const b = [x0 + v(4) * sx, y0 + v(5) * sy];
    const p = [x0 + v(6) * sx, y0 + v(7) * sy];
    return [a, p.map((value, index) => 2 * value - (a[index] + b[index]) / 2), b];
  }

  const MAX_FF1_BYTES = 128 * 1024;

  function readOutlineFace(source) {
    require(source instanceof Uint8Array && source.length >= 66 && source.length <= MAX_FF1_BYTES,
      'Invalid FF1 file size');
    const data = new Uint8Array(source), view = new DataView(data.buffer);
    const word = pos => view.getUint16(pos, true), dword = pos => view.getUint32(pos, true);
    const variants = word(10), first = word(14), count = word(16);
    const inner = 70 + 46 * variants;
    require([189, 122, 0, 1, 1].every((v, i) => data[i] === v) && word(32) === 46
      && variants >= 1 && variants <= 64 && count > 0 && first + count <= 256
      && inner + 48 <= data.length, 'Unsupported FF1 directory profile');
    const names = [];
    for (let i = 0; i < variants; i++) {
      const area = data.subarray(66 + 46 * i, 98 + 46 * i);
      const end = area.indexOf(0);
      const name = area.subarray(0, end);
      require(end > 0 && name.every(code => code >= 32 && code <= 126), 'Invalid FF1 variant name');
      names.push(String.fromCharCode(...name).toLowerCase());
    }
    require(new Set(names).size === names.length, 'Duplicate FF1 variant name');
    const size = dword(inner + 4), units = word(inner + 12);
    const widths = word(inner - 2), index = word(inner + 46), glyphs = index + 4 * count;
    require(dword(inner) === 0x0101f31e && units > 0
      && word(inner + 14) === first && word(inner + 16) === count
      && widths >= 48 && widths + 2 * count === index && glyphs < size
      && inner + size <= data.length && dword(inner + index) === glyphs, 'Invalid FF1 inner glyph index');
    const entries = [];
    for (let i = 0; i < count; i++) {
      const at = dword(inner + index + 4 * i);
      const end = i + 1 === count ? size : dword(inner + index + 4 * (i + 1));
      require(at < end && end <= size, 'Overlapping or unordered FF1 glyph extents');
      entries.push({ at: inner + at, size: end - at, advance: word(inner + widths + 2 * i) });
    }
    const nameBytes = data.subarray(66, 98);
    return {
      name: String.fromCharCode(...nameBytes.subarray(0, nameBytes.indexOf(0))),
      first, units, entries,
      same: other => other instanceof Uint8Array && other.length === data.length && data.every((v, i) => v === other[i]),
      commands(code) {
        const { at, size } = entries[code - first];
        require(size >= 14, `Truncated FF1 glyph for code ${code}`);
        const i16 = pos => view.getInt16(pos, true);
        const end = at + 14 + word(at + 10);
        require(end + word(at + 12) === at + size && word(at) === 1
          && i16(at + 2) <= i16(at + 6) && i16(at + 4) <= i16(at + 8),
        `Unsupported FF1 glyph header for code ${code}`);
        const contours = [];
        let contour;
        for (let pos = at + 14; pos < end;) {
          const op = data[pos], next = pos + (op === 2 ? 13 : 5);
          require(op <= 2, `Unknown FF1 opcode ${hex(op)} at glyph byte ${pos - at} for code ${code}`);
          require(next <= end, `Truncated FF1 command for code ${code}`);
          const points = [];
          for (let i = pos + 1; i < next; i += 4) points.push([i16(i), i16(i + 2)]);
          if (op === 0) {
            contour = [points];
            contours.push(contour);
          } else {
            require(contour, `FF1 contour lacks a move for code ${code}`);
            contour.push(points);
          }
          pos = next;
        }
        return contours.filter(c => c.length > 1).map(c => {
          const [x, y] = c[0][0], [lastX, lastY] = c.at(-1).at(-1);
          require(x === lastX && y === lastY, `Open FF1 contour for code ${code}`);
          return c;
        });
      },
    };
  }

  function pathOutlines(part, face, budget) {
    const { raw, text } = part;
    const view = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);
    const word = pos => view.getUint16(pos, true);
    const pointSize = word(56), width = word(58);
    require(raw[21] === 255 && raw.slice(22, 26).every(v => v === 0)
      && (raw[20] === 1 || face.name.toLowerCase() === 'cobb')
      && raw.slice(60, 64).every(v => v === 0) && word(64) === 12 && word(66) === 255
      && raw.slice(68, 84).every(v => v === 0)
      && word(90) === 1 && pointSize && width, 'Unsupported external font transform or style');
    let cost = 0;
    for (const code of text) {
      const entry = face.entries[code - face.first];
      require(entry, `Code ${code} is outside the ${face.name} glyph index`);
      cost += entry.size;
    }
    require(cost <= budget, 'Outline byte budget');
    const x = view.getInt16(92, true), y = view.getInt16(94, true);
    const sy = pointSize * 1000 / (72 * face.units), sx = sy * width / 100;
    const cache = new Map(), paths = [];
    let advance = 0;
    for (const code of text) {
      if (!cache.has(code)) cache.set(code, face.commands(code));
      const contours = cache.get(code);
      const coord = ([px, py]) => `${safeNumber(x + (advance + px) * sx)} ${safeNumber(y + py * sy)}`;
      const commands = contours.map(([start, ...segments]) => [
        'M ' + coord(start[0]),
        ...segments.map(points => (points.length === 1 ? 'L ' : 'C ') + points.map(coord).join(' ')),
        'Z',
      ].join(' '));
      if (commands.length) paths.push(commands.join(' '));
      advance += face.entries[code - face.first].advance;
    }
    return { paths, cost };
  }

  function preview(model, { inspect = false, substitute = false, faces = new Map() } = {}) {
    const paint = (index, otherwise) => model.palette.has(index)
      ? '#' + model.palette.get(index).map(hex).join('') : otherwise;
    const result = [], omitted = [];
    let bank = new Map(), strokeBudget = 100000, outlineBudget = 200000, substituted = 0, resolved = 0;
    try { bank = strokes(model.strokes); } catch { /* Keep opaque stroke bytes. */ }
    const outline = index => `stroke="${paint(index, '#333333')}" stroke-width="1" vector-effect="non-scaling-stroke"`;
    for (const part of leaves(model)) {
      const [x0, y0, x1, y1] = part.bounds, { kind, raw } = part;
      const interactive = inspect ? ` data-offset="${part.offset}"` : '';
      if (kind === 'L') {
        result.push(`<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" ${outline(raw[18])}${interactive}/>`);
        continue;
      }
      if (kind === 'UA') {
        const arc = arcQuadratic(part);
        if (arc) {
          const [a, q, b] = arc.map(pair => pair.map(safeNumber).join(' '));
          result.push(`<path d="M ${a} Q ${q} ${b}" fill="none" ${outline(raw[20])}${interactive}/>`);
        } else omitted.push({ kind, offset: part.offset, reason: 'unsupported arc extent' });
        continue;
      }
      if (kind === 'T' && part.text?.length && raw[21] === 0) {
        const glyphs = Array.from(part.text, code => bank.get(256 * part.modifier + code));
        if (glyphs.every(Boolean)) {
          const cost = glyphs.reduce((total, glyph) => total + glyph.reduce((sum, path) => sum + path.length, 0), 0);
          if (cost > strokeBudget) {
            omitted.push({ kind, offset: part.offset, reason: 'stroke point budget' });
            continue;
          }
          strokeBudget -= cost;
          const advance = (x1 - x0) / glyphs.length, height = y1 - y0;
          const lines = glyphs.flatMap((glyph, index) => glyph.map(path => {
            const points = path.map(([x, y]) => `${safeNumber(x0 + advance * (index + x/128))},${safeNumber(y0 + height * y/128)}`).join(' ');
            return `<polyline points="${points}" ${outline(raw[19])}${interactive}/>`;
          }));
          result.push(`<g fill="none">${lines.join('')}</g>`);
          continue;
        }
      }
      if (kind === 'Uf') {
        const fill = paint(1, '#333333');
        const face = faces.get(part.fontName?.toLowerCase());
        let reason = part.fontName ? `Supply local ${part.fontName} FF1` : 'Invalid external font descriptor';
        if (face) {
          try {
            const { paths, cost } = pathOutlines(part, face, outlineBudget);
            outlineBudget -= cost;
            result.push(...paths.map(path => `<path d="${path}" fill="${fill}"${interactive}/>`));
            resolved++;
            continue;
          } catch (error) {
            // A rejected glyph must still consume its share of the decoding budget.
            outlineBudget -= Math.min(outlineBudget, Array.from(part.text, code =>
              face.entries[code - face.first]?.size ?? 0).reduce((a, b) => a + b, 0));
            reason = error.message;
          }
        }
        if (substitute && part.text?.length) {
          const label = Array.from(part.text, value => value >= 32 && value < 127 ? char(value) : '�').join('');
          result.push(`<text x="${Math.min(x0,x1)}" y="${Math.max(y0,y1)}" font-size="${Math.max(1,Math.abs(y1-y0))}" font-family="monospace" fill="${fill}"${interactive}>${escaped(label)}</text>`);
          substituted++;
        } else omitted.push({ kind, offset: part.offset, reason });
        continue;
      }
      const dx = x1 - x0, dy = y1 - y0;
      if (kind === 'UP' && part.points.length >= 2) {
        const view = new DataView(raw.buffer);
        const sx = view.getUint16(28, true), sy = view.getUint16(30, true);
        const coords = part.points.map(([x, y]) =>
          `${safeNumber(x0 + (sx ? x * dx / sx : 0))},${safeNumber(y0 + (sy ? y * dy / sy : 0))}`).join(' ');
        const tag = raw[32] || raw[33] ? 'polygon' : 'polyline';
        const fill = raw[32] && raw[24] !== 254 ? paint(raw[26], '#b0b0b0') : 'none';
        result.push(`<${tag} points="${coords}" fill="${fill}" ${outline(raw[20])}${interactive}/>`);
        continue;
      }
      if (kind === 'R' || kind === 'E') {
        const w = Math.abs(dx), h = Math.abs(dy);
        const fill = raw[1] === 254 ? 'none' : paint(raw[22], '#b0b0b0');
        const geom = kind === 'R'
          ? `rect x="${Math.min(x0, x1)}" y="${Math.min(y0, y1)}" width="${w}" height="${h}"`
          : `ellipse cx="${(x0+x1)/2}" cy="${(y0+y1)/2}" rx="${w/2}" ry="${h/2}"`;
        result.push(`<${geom} fill="${fill}" ${outline(raw[18])}${interactive}/>`);
        continue;
      }
      omitted.push({ kind, offset: part.offset, reason: 'unsupported preview record' });
    }
    return { shapes: result.join(''), background: paint(0, '#000080'), omissions: omitted, substituted, resolved };
  }

  const FIXED_ONE = 65536;
  const DEFAULT_PALETTE = [
    [0, 0, 128], [192, 192, 0], [192, 192, 192], [128, 0, 0], [0, 128, 128], [0, 0, 192],
    [192, 0, 0], [128, 128, 128], [64, 64, 64], [0, 128, 128], [0, 192, 0], [128, 0, 128],
    [128, 128, 0], [192, 0, 192], [0, 128, 0], [0, 0, 0],
  ];

  function fixed(value) {
    require(Number.isInteger(value) && value >= -2147483648 && value <= 2147483647,
      'Value outside exact signed 16.16 range');
    return value;
  }

  function setCoords(view, start, coordinates) {
    require(coordinates.length === 4, 'Expected four signed 16.16 coordinates');
    coordinates.forEach((v, i) => {
      const whole = Math.floor(fixed(v) / FIXED_ONE);
      view.setInt16(start + 4 * i, whole, true);
      view.setUint16(start + 4 * i + 2, v - whole * FIXED_ONE, true);
    });
  }

  function colorIndex(value) {
    require(Number.isInteger(value) && value >= 0 && value < 16, 'Palette index must be 0–15');
    return value;
  }

  function primitive(kind, geometry, color, fill) {
    colorIndex(color);
    if (fill !== null) colorIndex(fill);
    const pattern = fill === null ? 254 : 1, foreground = fill ?? 1;
    if (Object.hasOwn(sizes, kind)) {
      const raw = new Uint8Array(sizes[kind]);
      raw[0] = kind.charCodeAt(0);
      raw[1] = kind === 'L' ? 0 : pattern;
      const [x0, y0, x1, y1] = geometry;
      if (kind !== 'L') require(x1 > x0 && y1 > y0, 'Shape requires positive ordered bounds');
      else require(fill === null, 'Line does not take a fill color');
      setCoords(new DataView(raw.buffer), 2, geometry);
      raw[18] = color;
      if (kind !== 'L') raw[22] = foreground;
      return raw;
    }
    const closed = kind === 'polygon';
    require((closed || kind === 'polyline') && geometry.length >= 2 + Number(closed)
      && geometry.length <= 16374 && (closed || fill === null), 'Invalid polyline closure, fill, or point count');
    const xs = [], ys = [];
    for (const point of geometry) {
      require(point.length === 2 && point.every(v => Number.isInteger(v) && v >= -32768 && v <= 32767),
        'Polyline points require signed integral world units');
      xs.push(point[0]); ys.push(point[1]);
    }
    const x0 = Math.min(...xs), y0 = Math.min(...ys), x1 = Math.max(...xs), y1 = Math.max(...ys);
    const raw = new Uint8Array(36 + 4 * geometry.length), view = new DataView(raw.buffer);
    raw.set([85, 80]);
    setCoords(view, 2, [x0, y0, x1, y1].map(v => v * FIXED_ONE));
    view.setUint16(18, raw.length / 2, true);
    raw.set([color, color, 0, 0, pattern, 0, foreground, 0], 20);
    view.setUint16(28, x1 - x0, true);
    view.setUint16(30, y1 - y0, true);
    raw.set([fill === null ? 0 : 255, closed ? 255 : 0], 32);
    view.setUint16(34, geometry.length, true);
    geometry.forEach(([x, y], i) => {
      view.setUint16(36 + 4 * i, x - x0, true);
      view.setUint16(38 + 4 * i, y - y0, true);
    });
    return raw;
  }

  function blank() {
    return { blank: true, entries: [], elements: new Map(), strokes: new Uint8Array(),
      palette: new Map(DEFAULT_PALETTE.map((rgb, i) => [i, [...rgb]])) };
  }

  function defaultContainer() {
    const data = new Uint8Array(113);
    data.set([20, 70, 73, 71, 0, 0, 42, 40, 40, 0, 110, 45, 45, 0, 80, 66, 60, 0, 0, 0, 1, 0]);
    data.set([1, 1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x78, 0x1c], FORM);
    data.set([2, 0], 42);
    data.set([16, 0], LIST + 2);
    DEFAULT_PALETTE.forEach((rgb, i) => data.set([i, ...rgb], LIST + 4 + 4 * i));
    return data;
  }

  function packed(model) {
    if (model.blank) return { data: defaultContainer(), first: 0x1c78, hint: 0, listBytes: 0 };
    const data = model.copy(), view = new DataView(data.buffer);
    const word = pos => view.getUint16(pos, true);
    const count = model.entries.length, first = word(36), hint = word(32), listBytes = word(40);
    require(word(28) === count + 1 && word(30) === 2 * count + 1 && word(38) - first === listBytes
      && model.strokes.length === 2 && model.strokes.every(v => v === 0)
      && model.elements.keys().next().value === 2 + 4 * count, 'Structural edit requires a packed Draw list');
    return { data, first, hint, listBytes };
  }

  function knownLeaves(parts) {
    require(parts.every(e => {
      if (Object.hasOwn(sizes, e.kind)) return e.raw.length === sizes[e.kind];
      if (e.kind !== 'UA' && e.kind !== 'UP') return false;
      const size = 2 * (e.raw[18] + 256 * e.raw[19]);
      return size === e.raw.length && (e.kind !== 'UA' || size === 44);
    }), 'Structural edit would relocate an unsupported record');
  }

  function packList(ordered, first) {
    const count = ordered.length;
    require(count > 0, 'Native Draw has no qualified empty-file representation');
    const size = 2 + 4 * count + ordered.reduce((sum, item) => sum + item.raw.length, 0);
    require(size <= 65535 - first, 'Rebuilt Draw list exceeds the measured allocation bound');
    const listing = new Uint8Array(size), view = new DataView(listing.buffer);
    view.setUint16(0, count, true);
    let at = 2 + 4 * count;
    for (let i = count - 1; i >= 0; i--) {
      view.setUint16(2 + 4 * i, at / 2, true);
      view.setUint16(4 + 4 * i, ordered[i].tag, true);
      listing.set(ordered[i].raw, at);
      at += ordered[i].raw.length;
    }
    return listing;
  }

  function wrap({ data, first, listBytes }, listing, hint) {
    require(listing.length <= 65535 - first, 'Rebuilt Draw list exceeds the measured allocation bound');
    const count = new DataView(listing.buffer).getUint16(0, true);
    const result = new Uint8Array(data.length - listBytes + listing.length), view = new DataView(result.buffer);
    result.set(data.subarray(0, LIST));
    result.set(listing, LIST);
    result.set(data.subarray(LIST + listBytes), LIST + listing.length);
    for (const [pos, value] of [[24, listing.length / 2], [28, count + 1], [30, 2 * count + 1], [32, hint],
      [38, first + listing.length], [40, listing.length]]) view.setUint16(pos, value, true);
    return read(result);
  }

  function nextTag(model, hint, count = 1) {
    const tag = Math.max(hint, ...model.entries.map(e => e.tag)) + count;
    require(tag <= 65535, 'Draw tag space exhausted');
    return tag;
  }

  function flat(model) {
    const parts = model.entries.map(e => ({ ...e, raw: model.elements.get(e.offset).raw,
      kind: model.elements.get(e.offset).kind }));
    require(parts.length === model.elements.size, 'Structural edit requires a packed flat Draw list');
    knownLeaves(parts);
    return parts;
  }

  function add(model, kind, geometry, { color = 1, fill = null } = {}) {
    const profile = packed(model), parts = flat(model);
    const tag = nextTag(model, profile.hint);
    parts.push({ tag, raw: primitive(kind, geometry, color, fill) });
    return wrap(profile, packList(parts, profile.first), tag);
  }

  function remove(model, tag) {
    const profile = packed(model), parts = flat(model);
    require(parts.some(e => e.tag === tag), 'The requested top-level delete tag does not exist');
    return wrap(profile, packList(parts.filter(e => e.tag !== tag), profile.first), profile.hint);
  }

  function reorder(model, tags) {
    const parts = new Map(model.entries.map(e => [e.tag, e.offset]));
    require(!model.blank && tags.length === parts.size && new Set(tags).size === parts.size
      && tags.every(tag => parts.has(tag)), 'Display order must contain each top-level tag exactly once');
    const data = model.copy(), view = new DataView(data.buffer);
    tags.forEach((tag, i) => {
      view.setUint16(LIST + 2 + 4 * i, parts.get(tag) / 2, true);
      view.setUint16(LIST + 4 + 4 * i, tag, true);
    });
    return read(data);
  }

  function group(model) {
    const profile = packed(model), parts = flat(model), count = parts.length;
    require(count >= 2, 'Grouping requires at least two flat top-level elements');
    const offsets = new Map();
    const raw = new Uint8Array(20 + 2 * count + parts.reduce((sum, item) => sum + item.raw.length, 0));
    const view = new DataView(raw.buffer);
    raw.set([79, 79]);
    const coords = model.entries.map(e => model.elements.get(e.offset).bounds.map(v => v * FIXED_ONE));
    const xs = coords.flatMap(([a, , c]) => [a, c]), ys = coords.flatMap(([, b, , d]) => [b, d]);
    setCoords(view, 2, [Math.min(...xs), Math.min(...ys), Math.max(...xs) + FIXED_ONE, Math.max(...ys) + FIXED_ONE]);
    view.setUint16(18, count, true);
    let at = 20 + 2 * count;
    for (const part of [...parts].reverse()) {
      offsets.set(part.tag, (at + 6) / 2);
      raw.set(part.raw, at);
      at += part.raw.length;
    }
    parts.forEach((part, i) => view.setUint16(20 + 2 * i, offsets.get(part.tag), true));
    const tag = nextTag(model, profile.hint);
    return wrap(profile, packList([{ tag, raw }], profile.first), tag);
  }

  function ungroup(model) {
    const profile = packed(model), root = model.elements.get(model.entries[0]?.offset);
    require(model.entries.length === 1 && root?.kind === 'OO' && root.children.length >= 2
      && root.raw.length === 20 + 2 * root.children.length
      && model.elements.size === root.children.length + 1, 'Ungrouping requires one flat group containing only leaves');
    const parts = root.children.map(offset => model.elements.get(offset));
    knownLeaves(parts);
    const hint = nextTag(model, profile.hint, parts.length);
    const ordered = parts.map((item, i) => ({ raw: item.raw, tag: hint - parts.length + i + 1 }));
    return wrap(profile, packList(ordered, profile.first), hint);
  }

  function paletteColor(model, index, rgb) {
    colorIndex(index);
    require(!model.blank && rgb.length === 3 && rgb.every(v => Number.isInteger(v) && v >= 0 && v <= 255),
      'Palette channels require three byte values in a drawing');
    const data = model.copy(), offset = data.length - 65 + 4 * [...model.palette.keys()].indexOf(index);
    data.set(rgb, offset + 1);
    return read(data);
  }

  function canPermute(model, tag) {
    const entry = model.entries.find(e => e.tag === tag);
    const part = entry && model.elements.get(entry.offset);
    return part && ['Cobb', 'Dixon', 'Marin'].includes(part.fontName)
      && part.raw.length === 2 * (part.raw[18] + 256 * part.raw[19])
      && part.text.every(code => code >= 32 && code <= 126);
  }

  function permuteLabel(model, tag, label) {
    require(canPermute(model, tag), 'Text edit requires a top-level ASCII outline-font run');
    const offset = model.entries.find(e => e.tag === tag).offset, part = model.elements.get(offset);
    const codes = Array.from(label, value => value.codePointAt(0));
    const expected = [...part.text].sort().join(',');
    require(codes.slice().sort().join(',') === expected, 'Use a permutation of the original ASCII label');
    const result = model.copy();
    result.set(codes, LIST + offset + 100);
    return read(result);
  }

  function structuralProfile(model) {
    if (model.blank) return 'flat';
    try {
      packed(model);
      if (model.entries.length === 1) {
        const root = model.elements.get(model.entries[0].offset);
        if (root.kind === 'OO' && root.children.length >= 2 && root.raw.length === 20 + 2 * root.children.length
          && model.elements.size === root.children.length + 1) {
          knownLeaves(root.children.map(offset => model.elements.get(offset)));
          return 'group';
        }
      }
      flat(model);
      return 'flat';
    } catch {
      return null;
    }
  }

  function canEdit(model, tag) {
    const entry = model.entries.find(item => item.tag === tag);
    const record = entry && model.elements.get(entry.offset);
    return record && ['L', 'R'].includes(record.kind) && record.raw.length === sizes[record.kind]
      && (record.kind !== 'R' || (record.bounds[0] <= record.bounds[2] && record.bounds[1] <= record.bounds[3]))
      ? record.kind : null;
  }

  function edit(model, tag, options) {
    const kind = canEdit(model, tag);
    require(kind, 'Edit requires a supported top-level line or rectangle');
    const entry = model.entries.find(item => item.tag === tag);
    const record = model.elements.get(entry.offset);
    const data = model.copy();
    const start = LIST + entry.offset;
    const view = new DataView(data.buffer);
    const coordinates = record.bounds.map(value => value * FIXED_ONE);
    let coords;
    if (kind === 'L') {
      const dx = fixed(options.dx), dy = fixed(options.dy);
      data[start + 18] = colorIndex(options.color);
      coords = coordinates.map((value, index) => value + (index % 2 ? dy : dx));
    } else {
      const width = fixed(options.width), height = fixed(options.height);
      require(width > 0 && height > 0, 'Rectangle dimensions must be positive');
      coords = [coordinates[0], coordinates[1], coordinates[0] + width, coordinates[1] + height];
    }
    setCoords(view, start + 2, coords);
    return read(data);
  }

  return Object.freeze({ read, leaves, preview, arcQuadratic, canEdit, edit, readOutlineFace, MAX_BYTES, MAX_FF1_BYTES,
    blank, structuralProfile, add, remove, reorder, group, ungroup, paletteColor, canPermute, permuteLabel });
})();

if (typeof module === 'object') module.exports = DrawFig;
