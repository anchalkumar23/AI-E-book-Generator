# Main Page Design — AI E-Book Generator

**Date:** 2026-07-05
**Scope:** Core app interface (post-login). Excludes landing page, sign-in, and pricing for now.
**Stack:** Python (FastAPI) backend · Next.js 15 frontend · Dark Editorial design system

---

## Design Direction

**Dark Editorial.** Deep near-black backgrounds (`oklch(0.09 0.010 268)`), indigo/violet/pink as accent colors (never gradient text — accents only on UI elements: borders, fills, glows, progress bars). Serif headings (`Georgia` or equivalent) for section titles. Clean, premium feel — Vercel/Linear/Framer aesthetic.

### Color tokens
| Token | Value | Use |
|---|---|---|
| `--bg` | `oklch(0.09 0.010 268)` | Page background |
| `--surface` | `oklch(0.12 0.012 268)` | Sidebar, cards |
| `--raised` | `oklch(0.15 0.013 268)` | Hover states, input backgrounds |
| `--border` | `oklch(0.20 0.014 268)` | All borders |
| `--ink` | `oklch(0.96 0.004 268)` | Primary text |
| `--muted` | `oklch(0.55 0.010 268)` | Secondary text, nav items |
| `--faint` | `oklch(0.32 0.010 268)` | Placeholder text, icons |
| `--indigo` | `oklch(0.62 0.21 264)` | Primary accent |
| `--violet` | `oklch(0.58 0.22 290)` | Secondary accent |
| `--pink` | `oklch(0.68 0.21 340)` | Tertiary accent |

### Motion
- Easing: `cubic-bezier(0.23, 1, 0.32, 1)` for all enter transitions
- Duration ceiling: 240ms for layout changes, 160ms for micro-interactions
- Active press: `scale(0.97)` on all interactive elements
- Enter state: from `scale(0.95) + opacity 0`, never from `scale(0)`
- Reduced motion: crossfade only (`opacity` transition, no transform)

---

## Layout

Two-column: fixed sidebar (220px) + scrollable main area.

### Sidebar
- **Logo** — icon mark + "Pageforge" wordmark (name TBD)
- **Nav sections:**
  - Library: All Books (count badge), Favorites (count), Generating (count)
  - Types: Children's, Tutorials, Guides, Educational
  - Account: Settings
- **Footer:** Credits meter — progress bar + remaining count + "Buy more credits" link

### Top Bar (56px, fixed within main)
- Search input (max 400px, left-aligned)
- Format filters: All / PDF / EPUB / Flipbook (pill buttons, active state: indigo tint)
- Grid/list view toggle
- "New Book" button (primary, indigo)

### Content Area
- Page title ("My Library") + book count
- **Book grid:** `repeat(auto-fill, minmax(170px, 1fr))`, 16px gap, 2:3 aspect ratio cards

---

## Components

### Book Card
- Aspect ratio 2:3 (portrait, matches real book proportions)
- Cover: gradient background (varies per book — generated or seeded from title hash)
- Bottom overlay: genre tag (small caps) + title
- Status badge (top-right): "Done" (green) or "Generating" (indigo)
- Favorite star (top-left, visible on hover or when active)
- **Hover state:** blur overlay with "Read" (primary) and "Download" (ghost) buttons
- **Generating state:** shimmer animation over the cover, live progress bar at bottom

### New Book Card
- Same 2:3 grid slot
- Dashed border, `+` icon, "Generate new book" label
- Hover: indigo dashed border + subtle indigo tint background
- Click: opens the New Book Drawer

### New Book Drawer
- Slides up from bottom of main area (not full page)
- Fields:
  - **Prompt** (textarea) — "What should your book be about?"
  - **Book type** (chip selector) — Children's, Tutorial, Guide, Educational, Story, Custom
  - **Length** (select) — Short (5–10p), Medium (15–25p), Long (30–50p)
  - **Illustration style** (select) — Watercolor, Digital flat, Pencil sketch, Photorealistic
- Footer: Cancel + "⚡ Generate book · 1 credit"

---

## States

| State | Description |
|---|---|
| Empty library | Show "Generate new book" card + empty state message |
| Generating | Card appears in grid immediately with shimmer + live progress text |
| Done | Cover renders, status badge turns green |
| Favorited | Star is gold, shown without hover |
| Error | Card shows error state with retry option |

---

## Pages in scope (this sprint)

| Route | Description |
|---|---|
| `/app` | Main library page (this design) |
| `/app/generate` | Redirect from drawer — or drawer stays on `/app` |
| `/app/book/[id]` | Book detail / flipbook reader (next sprint) |
| `/app/book/[id]/export` | Export options page (next sprint) |

---

## Deferred

- Landing page (`/`)
- Sign-in (`/sign-in`, `/sign-up`)
- Pricing page
- Flipbook reader UI
- Admin / API key settings
