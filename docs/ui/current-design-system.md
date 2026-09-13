# Current UI Design System

This is a visual reference for colors, spacing and components. Runtime status and safety claims must come from the backend, not from mockups.

See [the screenshot guide](../submission/test-product.md) and
[progress](../progress.md) for the reviewer path and current evidence.

<details>
<summary>Detailed visual record</summary>

## Source and confidence

This specification is extracted from all four images in `docs/references/ui/current/`, each at
`1448 x 1086`. Measurements are approximate and should be tuned through screen-by-screen screenshot
comparison. The images are authoritative for visual treatment; backend contracts are authoritative
for content and available actions.

## Visual character

A restrained enterprise operations workspace: deep navy navigation, bright white working surfaces,
pale cool-blue canvas, compact information density, and high-contrast royal-blue actions. Status
colors are semantic accents rather than page themes. Surfaces use fine borders, small radii, and
very light shadows.

## Colors

| Token | Approximate value | Use |
| --- | --- | --- |
| `--canvas` | `#f5f8fd` | application content background |
| `--surface` | `#ffffff` | cards, tables, header |
| `--surface-soft` | `#f6f9ff` | schema blocks, selected/secondary regions |
| `--sidebar` | `#102a46` | shared sidebar |
| `--sidebar-deep` | `#0d243d` | sidebar depth at lower edge |
| `--primary` | `#1664f6` | primary actions, active navigation, links |
| `--primary-hover` | `#0c52d9` | inferred hover/focus state |
| `--primary-soft` | `#eaf2ff` | icon wells, selected rows, secondary buttons |
| `--text-primary` | `#07133d` | headings and primary values |
| `--text-secondary` | `#53678f` | descriptions and metadata |
| `--text-muted` | `#7d8dab` | placeholders and inactive labels |
| `--border` | `#dbe4f1` | card and control borders |
| `--border-strong` | `#b9c8dc` | focused controls and separators |
| `--success` | `#15ae68` | success/healthy/connected |
| `--success-soft` | `#e3f8ed` | success badges and notices |
| `--warning` | `#f3a012` | review/warning state |
| `--warning-soft` | `#fff2d8` | warning badges |
| `--error` | `#ef3651` | destructive/failure action |
| `--error-soft` | `#ffe7e8` | failure/paused accents |
| `--violet` | `#6841e8` | teaching/intervention secondary accent |
| `--violet-soft` | `#eee7ff` | teaching/intervention surfaces |
| `--neutral-soft` | `#eef2f7` | pending/draft badges |

Avoid a monochrome blue page: white working surfaces, mint status, lavender teaching/intervention,
amber review, and coral failure states are all visible in the references.

## Typography

Use `Manrope` as the bundled product family, with a sans-serif fallback only for loading failure.
Its rounded geometric forms best approximate the reference while avoiding a generic system-default
appearance.

| Role | Size / line height | Weight |
| --- | --- | --- |
| Hero greeting | `43px / 1.12` | 700 |
| Run/page display title | `36-38px / 1.15` | 700 |
| Standard page title | `30-34px / 1.15` | 700 |
| Section title | `17-20px / 1.25` | 700 |
| Card title | `16-18px / 1.25` | 700 |
| Body | `14-16px / 1.45` | 400-500 |
| Small/meta | `12-13px / 1.4` | 400-600 |
| Label/table header | `12-13px / 1.3` | 600 |
| Badge | `12px / 1` | 600 |
| Button | `14px / 1` | 600 |

Letter spacing is `0`. The banner eyebrow is the only exception: uppercase with approximately
`0.20em` tracking because the reference visibly uses it as a label rather than body text.

## Geometry

| Token | Desktop value | Notes |
| --- | --- | --- |
| Reference viewport | `1448 x 1086` | mandatory comparison viewport |
| Sidebar width | `226px` | fixed at desktop; compact drawer below tablet |
| Header height | `70px` | fixed visual band |
| Content max width | none inside shell | fills remaining viewport width |
| Page padding | `22-26px` | mostly 25px in references |
| Card radius | `8px` | never pill-shaped except statuses/avatar |
| Button radius | `7px` | 44px standard height |
| Input radius | `7px` | 40-44px standard height |
| Compact gap | `8px` | labels/actions |
| Standard gap | `14-18px` | cards/grid |
| Section gap | `22-26px` | major bands |
| Border | `1px solid var(--border)` | all framed working surfaces |
| Shadow | `0 6px 24px rgb(32 71 117 / 0.05)` | restrained, no floating-card effect |

At mobile widths the sidebar becomes a top-triggered drawer, the header search contracts, split
rails stack, and tables gain horizontal scrolling. Fixed-format controls retain stable dimensions.
No font size scales directly with viewport width.

## Shared shell

### Sidebar

- 226px deep navy vertical rail.
- Brand block is approximately 70px high with faceted blue mark and two-line white name.
- Navigation starts around 108px; each item is 48px high with 14px side inset, 58px width from icon
  to label, and approximately 8px vertical gap.
- Active item uses royal-blue fill, subtle blue depth, 8px radius, and white icon/text.
- Footer has a top separator and compact two-line aspiration text.
- Use Lucide icons corresponding to the visible symbols: House, Search, Play, LayoutGrid,
  MessageSquare, FileText, Settings.

### Header

- 70px white band with bottom border.
- Left page label is 24-26px/700.
- Search is approximately 320px x 40px and sits right-of-center.
- Notification button is icon-only with tooltip and unread dot.
- User identity is compact with circular initial avatar and disclosure chevron. It must not imply a
  real authenticated identity when none exists; local product mode should say `Local Reviewer`.

## Components

### Sidebar item

44-48px stable height, icon at 20-22px, 12-14px inline gap, 8px radius. Hover is a low-opacity white
or blue overlay; active is solid royal blue.

### Status badge

Inline-flex, 24-28px height, full pill radius, 8-10px horizontal padding, 12px semibold text, and a
6-8px status dot/icon. Variants: success, running, review/warning, paused/error, draft/neutral.

### Primary button

44px height, 7px radius, royal-blue fill, white icon/text, 14px semibold, 16-20px horizontal
padding. Primary full-width actions may expand but do not become taller.

### Secondary button

44px height, white or pale-blue fill, thin border, navy/blue text. Lavender is reserved for Teach
or secondary intervention actions. Icon-only secondary buttons are 44px square with tooltips.

### Input and textarea

44px minimum height, 1px cool-gray border, 7px radius, white fill, 14px text. Focus uses blue border
and a subtle `0 0 0 3px` blue alpha ring. Sensitive values use password masking by default.
Textareas use 120-150px minimum height where required.

### Card / panel

White surface, 1px border, 8px radius, restrained shadow. Cards frame individual actions or data;
page sections themselves remain unframed unless the reference explicitly frames a working panel.
No cards inside decorative cards.

### Table / list

12-13px header labels, 48-73px rows depending on density, horizontal separators, no zebra striping.
Selected rows use pale blue fill and a 1px blue outline. Row overflow is an icon button.

### Timeline row

24px node column with continuous vertical line. Completed nodes are filled green with check;
current nodes are blue rings; pending nodes are gray rings. Main label is 13-14px semibold;
secondary text is 12px muted. Event content comes from safe structured evidence only.

### Workflow progress strip

Five equal columns connected by horizontal rules. Circular 38px node, 14-16px bold label, 12-13px
supporting copy. Completed/current/pending states use green/blue/gray semantics from backend events.

### Empty state

Unframed centered state within the existing table/panel geometry: icon well, concise factual title,
one-line explanation, and one relevant command. It must not use fabricated rows to preserve density.

### Modal, drawer, popover

No modal/drawer/popover appears in the current references. Do not add one for desktop flows. The
only responsive exception is a mobile navigation drawer derived from the fixed sidebar.

### Live SurfaceView

Large framed workspace with compact header row and image viewport. It displays only the existing
bounded ephemeral image endpoint. Controls are separate trusted semantic actions; no coordinate
clicking, arbitrary selector input, or screenshot persistence.

## Motion

Use one restrained initial reveal for major page regions (opacity plus 6px translation, 180-260ms)
and a short progress/timeline state transition. Respect `prefers-reduced-motion`. Avoid decorative
continuous animation; only running-state indicators may pulse subtly.

## Accessibility and truth rules

- Maintain visible focus states and WCAG-oriented contrast, particularly on blue and mint surfaces.
- Icon-only actions require accessible names and hover tooltips.
- Do not expose raw provider/model content, selectors, HTML, credentials, or sensitive input values.
- Replace illustrative reference metrics with actual computed values or `Unavailable`/empty states.
- Disabled Teach media controls must explicitly state that voice/screen sharing is not connected in
  P5.4b and must not simulate activity.

</details>
