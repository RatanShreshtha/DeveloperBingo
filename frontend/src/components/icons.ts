// The icons the app uses: simple outline drawings on a 24-unit grid, each a few SVG shapes. They
// are written here, not loaded from a package, so the app adds no dependency for them.

export type IconShape = {
  tag: 'path' | 'circle' | 'rect' | 'line' | 'polyline' | 'polygon'
  attrs: Record<string, string | number>
}

export const ICONS = {
  plus: [{ tag: 'path', attrs: { d: 'M12 5v14M5 12h14' } }],
  sun: [
    { tag: 'circle', attrs: { cx: 12, cy: 12, r: 4 } },
    {
      tag: 'path',
      attrs: {
        d: 'M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41',
      },
    },
  ],
  moon: [
    {
      tag: 'path',
      attrs: { d: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z' },
    },
  ],
  book: [
    {
      tag: 'path',
      attrs: {
        d: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z',
      },
    },
  ],
  info: [
    { tag: 'circle', attrs: { cx: 12, cy: 12, r: 10 } },
    { tag: 'path', attrs: { d: 'M12 16v-4M12 8h.01' } },
  ],
  join: [
    { tag: 'path', attrs: { d: 'M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4' } },
    { tag: 'polyline', attrs: { points: '10 17 15 12 10 7' } },
    { tag: 'line', attrs: { x1: 15, y1: 12, x2: 3, y2: 12 } },
  ],
  play: [{ tag: 'polygon', attrs: { points: '6 4 20 12 6 20 6 4' } }],
  square: [
    { tag: 'rect', attrs: { x: 6, y: 6, width: 12, height: 12, rx: 2 } },
  ],
  shuffle: [
    { tag: 'polyline', attrs: { points: '16 3 21 3 21 8' } },
    { tag: 'line', attrs: { x1: 4, y1: 20, x2: 21, y2: 3 } },
    { tag: 'polyline', attrs: { points: '21 16 21 21 16 21' } },
    { tag: 'line', attrs: { x1: 15, y1: 15, x2: 21, y2: 21 } },
    { tag: 'line', attrs: { x1: 4, y1: 4, x2: 9, y2: 9 } },
  ],
  grid: [
    { tag: 'rect', attrs: { x: 3, y: 3, width: 7, height: 7, rx: 1 } },
    { tag: 'rect', attrs: { x: 14, y: 3, width: 7, height: 7, rx: 1 } },
    { tag: 'rect', attrs: { x: 14, y: 14, width: 7, height: 7, rx: 1 } },
    { tag: 'rect', attrs: { x: 3, y: 14, width: 7, height: 7, rx: 1 } },
  ],
  clock: [
    { tag: 'circle', attrs: { cx: 12, cy: 12, r: 10 } },
    { tag: 'polyline', attrs: { points: '12 6 12 12 16 14' } },
  ],
  users: [
    { tag: 'path', attrs: { d: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2' } },
    { tag: 'circle', attrs: { cx: 9, cy: 7, r: 4 } },
    { tag: 'path', attrs: { d: 'M23 21v-2a4 4 0 0 0-3-3.87' } },
    { tag: 'path', attrs: { d: 'M16 3.13a4 4 0 0 1 0 7.75' } },
  ],
  trophy: [
    { tag: 'path', attrs: { d: 'M8 21h8M12 17v4' } },
    { tag: 'path', attrs: { d: 'M7 4h10v5a5 5 0 0 1-10 0V4z' } },
    {
      tag: 'path',
      attrs: { d: 'M17 4h3v2a3 3 0 0 1-3 3M7 4H4v2a3 3 0 0 0 3 3' },
    },
  ],
  check: [{ tag: 'polyline', attrs: { points: '20 6 9 17 4 12' } }],
  'arrow-left': [
    { tag: 'line', attrs: { x1: 19, y1: 12, x2: 5, y2: 12 } },
    { tag: 'polyline', attrs: { points: '12 19 5 12 12 5' } },
  ],
} satisfies Record<string, IconShape[]>

export type IconName = keyof typeof ICONS
