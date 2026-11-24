---
name: Sanctuary Modern
colors:
  surface: '#fbf9f5'
  surface-dim: '#dbdad6'
  surface-bright: '#fbf9f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3ef'
  surface-container: '#efeeea'
  surface-container-high: '#eae8e4'
  surface-container-highest: '#e4e2de'
  on-surface: '#1b1c1a'
  on-surface-variant: '#44474d'
  inverse-surface: '#30312e'
  inverse-on-surface: '#f2f0ed'
  outline: '#75777e'
  outline-variant: '#c5c6ce'
  surface-tint: '#4f5e7e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#091b37'
  on-primary-container: '#7484a5'
  inverse-primary: '#b7c7eb'
  secondary: '#775a19'
  on-secondary: '#ffffff'
  secondary-container: '#fdd587'
  on-secondary-container: '#785a19'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#042012'
  on-tertiary-container: '#6d8b76'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d7e2ff'
  primary-fixed-dim: '#b7c7eb'
  on-primary-fixed: '#091b37'
  on-primary-fixed-variant: '#374765'
  secondary-fixed: '#ffdea3'
  secondary-fixed-dim: '#e8c176'
  on-secondary-fixed: '#261900'
  on-secondary-fixed-variant: '#5c4200'
  tertiary-fixed: '#caead2'
  tertiary-fixed-dim: '#aeceb7'
  on-tertiary-fixed: '#042012'
  on-tertiary-fixed-variant: '#314d3b'
  background: '#fbf9f5'
  on-background: '#1b1c1a'
  surface-variant: '#e4e2de'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
  display-lg-mobile:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  headline-sm:
    fontFamily: Playfair Display
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  title-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.08em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.1em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system expresses a reverent, trustworthy, and calm aesthetic tailored for ecclesiastical operations. Combining architectural permanence with quiet administrative clarity, the visual tone honors pastoral tradition while serving practical frontline workflows—from rapid sanctuary check-ins by volunteer ushers to confidential pastoral care logs and financial record-keeping by the church secretary.

The design movement mixes **Minimalism** with subtle **Tactile / Classical Editorial** cues:
- **Atmospheric Calm:** Warm parchment and alabaster surfaces banish the cold, clinical feel of standard enterprise SaaS.
- **Dignified Authority:** High-contrast navy anchors navigation and major headers, evoking classic leather-bound hymnals and historical scripture bindings.
- **Sacred Nuance:** Muted antique gold and sanctuary evergreen accents serve purposeful contextual feedback without sensationalism or visual noise.
- **Clarity under Pressure:** High-contrast touch zones and clear hierarchy cater to Sunday morning rush windows on tablets and mobile devices.

## Colors

The palette draws directly from the enduring materiality of the sanctuary: aged paper, polished brass, dark mahogany pews, and archival ink.

### Palette Architecture
- **Primary (`#041632` Deep Sanctuary Navy):** The structural backbone. Applied across permanent sidebars, primary interactive buttons, and high-level headings. Its container companion `#1B2B48` handles selected navigation tiles and highlighted states.
- **Secondary (`#775A19` Antique Gold):** Used with discipline for active tab indicators, sacred designations, badge borders, and accessibility focus rings. Paired with `#FED488` for gold status containers and `#E3D1AC` for subtle borders on elevated elements.
- **Tertiary (`#153121` Deep Forest Green):** The indicator for fellowship presence, active attendance roll calls, and confirmed contributions. Paired with `#CAEAD3` for attendance chip fills and positive financial balances.
- **Neutral Canvas (`#FBF9F5` Warm Paper):** The foundational canvas. Backed by `#FFFFFF` for primary content cards, `#F5F3EF` / `#EFEEEA` for muted sub-panels, and `#F2EEE6` for inset data tables.
- **Semantic Feedback:** Critical alerts utilize `#BA1A1A` text over `#FFDAD6` warning containers.
- **Text & Borders:** High-legibility ink (`#121C2F` / `#1B1C1A`), supporting administrative body (`#44474D`), and delicate dividers (`#C5C6CE` at 60–100% opacity).

## Typography

The typographic hierarchy bridges liturgical distinction and clerical speed:

- **Display & Headings (Playfair Display):** Used for ministry metrics, member and event directory titles, sermon dates, and dashboard greetings. Headings must always maintain a formal serif structure to ground the application in reverent grace.
- **Body & Data (Inter):** Clean, neutral, and highly legible for long pastoral notes, financial ledgers, and contact registries.
- **Labels & Microcopy (Inter Uppercase):** All category tags, status pills, table headers, and sub-section metadata utilize `label-md` or `label-sm` with explicit tracking (`0.08em` to `0.1em`) to maintain crisp, legible delineation against soft paper backgrounds.

## Layout & Spacing

The layout balances operational density with unhurried negative space:

- **Grid Architecture:** Desktop views operate on a 12-column responsive fluid grid with a permanent left rail (`280px` width) bathed in `#041632`. Content work areas maintain a maximum width of `1440px` to prevent sprawling data entries on ultra-wide screens.
- **Breakpoints:**
  - **Desktop (1024px+):** Fixed deep navy sidebar, multi-column metrics, master-detail side sheets for member profiling.
  - **Tablet (768px – 1023px):** Compact icon sidebar (`72px`), dual-column card arrangements, optimized for volunteer ushers stationing check-in kiosks.
  - **Mobile (< 768px):** Bottom navigation rail, single-column vertical flows, full-width touch lists for usher check-ins.
- **Rhythm & Touch Safety:** Dense statistical tables employ `space-sm` row padding, while content panels and pastoral note editors breathe with `space-lg` to `space-xl` insets.

## Elevation & Depth

Visual hierarchy eschews artificial heavy drops in favor of tonal stepping and diffused ambient warmth:

- **The Navy Anchor:** The left desktop sidebar represents the deepest grounding plane, existing in solid `#041632` without shadow, holding active selections via `#1B2B48` containers with a `3px` solid `#775A19` left border.
- **Tonal Stepping:** Inset sheets and sidebars sit on `#F5F3EF` or `#F2EEE6`, while interactive surfaces rise to crisp `#FFFFFF`.
- **Sanctuary Ambient Shadow:** Active cards, floating modals, and action popovers use a tinted ambient projection: `0 4px 20px rgba(4, 22, 50, 0.08)`. This avoids muddy gray tones and maintains chromatic harmony with the deep navy base.
- **Subtle Dividers:** Structural separations rely on a fine hairline border (`1px solid #C5C6CE` with 60% opacity), delivering boundary clarity without cluttering clerical views.

## Shapes

The shape system adopts a tailored, disciplined posture:

- **Baseline Components (4px):** Form fields, action buttons, table cell selections, and dropdown menus utilize compact `0.25rem` corners to communicate order and administrative precision.
- **Containers & Cards (8px):** Surface cards, member record modules, and metric blocks employ `0.5rem` corners (`rounded-lg`).
- **Major Modals & Sheets (12px):** Dialog windows, check-in drawers, and pastoral log panels soften to `0.75rem` (`rounded-xl`).
- **Complete Radials:** Status badges, attendance counters, volunteer tags, and member avatar rings use full circular pill shapes (`rounded-full`).

## Components

### Buttons & Interactive Controls
- **Primary Button:** `#041632` background with `#FFFFFF` text. Hover transitions to `#1B2B48`. Min touch height of `44px` on mobile/tablet.
- **Secondary / Accent Button:** `#FFFFFF` card background with a `1px` border of `#775A19`, text in `#775A19`.
- **Tertiary / Success Action (e.g., Mark Present):** `#153121` background, `#FFFFFF` text, active focus ring in `#FED488`.
- **Focus Rings:** High-visibility double outline using `#775A19` with a `2px` offset, ensuring total WCAG AA accessibility compliance.

### Form Inputs & Pastoral Notes
- **Text Inputs:** Crisp `#FFFFFF` surface framed by `1px solid #C5C6CE` at `4px` radius. Active state illuminates the border to `#041632` with an ambient glow.
- **Labels:** Rendered in `label-md` uppercase using `#44474D` tracking at `0.08em` above the input.
- **Checkboxes & Radios:** Minimalist square/circular controls with a `2px` border in `#041632`. Selected states fill with `#041632` bearing a sharp white tick mark.

### Attendance Chips & Status Badges
- **Present / Confirmed:** `#CAEAD3` fill with `#153121` text and an optional `#153121` leading icon dot.
- **Follow-Up / Pending:** `#FED488` fill with `#775A19` text.
- **Absent / Critical:** `#FFDAD6` fill with `#BA1A1A` text.
- Form factor is pill-shaped (`rounded-full`) with `label-sm` uppercase styling.

### Cards & Data Panels
- **Member & Directory Cards:** Crisp `#FFFFFF` background, `8px` corner radius, `1px solid #C5C6CE` border, and sanctuary ambient shadow (`0 4px 20px rgba(4, 22, 50, 0.08)`).
- **Metric Tiles:** Feature prominent numbers set in `Playfair Display` (`headline-lg`), resting above an uppercase `label-md` metric category.

### Navigation Sidebar (Desktop)
- Fixed left column in deep `#041632`.
- Navigation items use `Inter` 14px with `Material Symbols Outlined` icons.
- Active item states use a background pill of `#1B2B48` with a vertical accent edge of `#775A19` (`3px` width) aligned flush to the left rail border.