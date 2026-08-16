# CoWorkConnect Design System

## Brand Tokens

| Token | Hex | Use |
| :--- | :--- | :--- |
| Ink | `#102033` | Primary text, logo text, important headings |
| Ink Soft | `#344054` | Secondary headings and dense UI labels |
| Muted | `#667085` | Body helper text, metadata, inactive navigation |
| Border | `#DDE5EE` | Inputs, cards, dividers, table lines |
| App Background | `#F7F9FB` | Page background |
| Surface | `#FFFFFF` | Cards, nav, modals, panels |
| Primary | `#0E9F6E` | Main actions, active states, success moments |
| Primary Hover | `#087A55` | Hover/focus for primary actions |
| Primary Soft | `#E8F7F1` | Active nav backgrounds, subtle highlights |
| Accent | `#2563EB` | Links, informational highlights, secondary data |
| Accent Soft | `#EFF6FF` | Informational chip backgrounds |
| Warm | `#F59E0B` | Ratings, attention counters |
| Danger | `#DC2626` | Delete, errors, destructive actions |

## UI Rules

- Font: `Outfit`, with system sans-serif fallback.
- Radius: `8px` for buttons, cards, inputs, menus, panels.
- Navbar: white, fixed, 72px high, active route highlighted with `Primary Soft`.
- Primary button: `#0E9F6E`, white text, hover `#087A55`.
- Page background: `#F7F9FB`; repeated content sits on white surfaces with `#DDE5EE` border.
- Avoid one-hue screens: use primary green for action, ink for structure, blue for informational accents, warm only for ratings/limited attention states.

## Page Template

Use `ui/template.html` as the starting structure for new MVP pages. It includes the shared navbar, app shell spacing, surface panels, and the same tokenized CSS used by production pages.
