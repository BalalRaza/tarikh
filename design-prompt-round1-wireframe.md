# Round 1 Prompt: Wireframe Fidelity — Tarikh

Paste this into Claude Design. It has full project context + specific wireframe instructions.

---

## PROMPT START

You are designing the complete mobile-first UI for **Tarikh** — an interactive Islamic history timeline that renders 846+ historical events (scaling to 5M) extracted from classical Arabic primary sources (al-Tabari's chronicle). The app is bilingual (Arabic primary, English secondary).

### Tech stack (design within these constraints)
- Vite + TypeScript, no framework (vanilla)
- GSAP + ScrollTrigger for animations
- Lenis for smooth scroll
- Three.js for 3D elements (globe on hero)
- Barba.js for page transitions
- MapLibre GL JS for map view
- Canvas renderer for timeline (NOT DOM nodes — it must handle 100K+ items)
- Fonts: **Amiri** (Arabic, variable), **Inter** (Latin, variable)
- Icons: **Phosphor** icon set

### Color palette
- Background: `#0A1628` (deep navy)
- Gold accent: `#D4A853`
- Warm white: `#F5F0E8`
- Event type colors:
  - Battle: `#EF4444` (red)
  - Treaty: `#3B82F6` (blue)
  - Birth: `#22C55E` (green)
  - Death: `#F97316` (orange)
  - Migration: `#A855F7` (purple)
  - Revelation: `#EAB308` (yellow)
  - Political: `#10B981` (emerald)
  - Construction: `#06B6D4` (cyan)
  - Social: `#F59E0B` (amber)
  - Other: `#6B7280` (gray)

### What I need (Round 1 — wireframe fidelity)

Design ALL of these screens at **375px width** (iPhone 15 Pro). Show layout, hierarchy, spacing, component placement. Use the real color palette and fonts — this is high-fidelity wireframe, not gray boxes. No placeholder "lorem ipsum" — use the real data samples below.

---

## SCREENS TO DESIGN

### 1. Landing / Hero (`/`)
- Full-viewport hero with Three.js globe placeholder (show as a circle with event marker dots on it)
- Arabic calligraphy title: **تاريخ** (large, centered, Amiri)
- English subtitle: "A Primary-Source Timeline of Islamic History"
- Tagline: "846 events from al-Tabari's chronicle — extracted, structured, explorable"
- Scroll cue at bottom (animated chevron)
- Below hero: "Era Overview" section — horizontal scrollable cards for major eras:
  - Pre-Islamic (before 610 CE)
  - Prophetic Era (610–632 CE)
  - Rashidun Caliphate (632–661 CE)
  - Umayyad Period (661–750 CE)
- Each era card shows: era name (AR + EN), date range, event count, dominant event type
- Bottom nav bar (persistent across all screens): Timeline | Map | Search | About

### 2. Timeline View (`/timeline`)
- This is the CORE screen. The timeline is vertical on mobile (horizontal doesn't work on 375px).
- Top: sticky header with current era label + date range indicator
- Filter bar (horizontally scrollable chips): All, Battle, Political, Death, Birth, Migration, Revelation, Treaty, Construction, Social
- Importance toggle: 3 dots (filled = active) for importance 1/2/3. Default: only importance 1 shown.
- The timeline itself:
  - Vertical line (gold, 2px) running down the center-left (not dead center — offset to leave room for cards on the right)
  - Year markers on the line: "2 AH / 624 CE" style
  - Event nodes: small circles on the line, color = event type
  - Event cards appear to the RIGHT of the line, connected by a small horizontal line to the node
  - Cards show: type badge (colored dot + label), title_en (Inter, 14px), title_ar (Amiri, 16px, RTL, gold-tinted), date (AH / CE), importance indicator (1 = star icon)
  - Pinch-to-zoom concept: show a "zoomed out" state (only importance=1, large year gaps) AND a "zoomed in" state (importance 1+2+3, dense)
- Show these REAL events on the timeline:
  1. **Death of Khadijah bint Khuwaylid** — 619 CE — importance 1 — death type
  2. **Migration to Abyssinia** — 615 CE — importance 2 — migration type
  3. **Battle of Badr** — 624 CE / 2 AH — importance 1 — battle type

### 3. Event Detail (`/event/:id`)
- Full-screen slide-up from timeline (Barba transition)
- Back arrow top-left
- Type badge (colored pill) + importance indicator
- Title (English, large, Inter bold)
- Title (Arabic, Amiri, RTL, gold color, larger than English)
- Date line: "2 AH / 624 CE" with calendar icon
- Location line: "Badr" with pin icon + mini map thumbnail (if lat/lng exists)
- Divider
- Summary section:
  - English summary (Inter, 14px, warm white)
  - Arabic summary (Amiri, 16px, RTL, muted gold)
- People section: horizontal scrollable chips showing name_en + role
- Source citation: "al-Tabari, Tarikh al-Rusul wa'l-Muluk" with "View in OpenITI →" link
- Confidence score (subtle, bottom): "90% confidence" with small bar

Use this REAL event for the detail screen:
```
Title EN: "Death of Khadijah bint Khuwaylid"
Title AR: "وفاة خديجة بنت خويلد"
Type: death
Date: ~619 CE / ~3 BH (Before Hijra)
Summary EN: "Khadijah bint Khuwaylid passed away approximately three years before the Prophet's departure from Mecca."
Summary AR: "توفيت خديجة بنت خويلد قبل خروج الرسول صلى الله عليه وسلم من مكة بثلاث سنين أو ما يقارب ذلك."
People: Khadijah bint Khuwaylid (Deceased)
Source: al-Tabari, Tarikh al-Rusul wa'l-Muluk
Importance: 1 (era-defining)
Confidence: 90%
```

### 4. Map View (`/map`)
- MapLibre dark tiles (Carto Dark Matter style) filling the screen
- Clustered markers (show a few clusters: one large cluster on Arabian Peninsula with "342" count, smaller ones on Abyssinia "17", Damascus "89", Iraq "156")
- When a cluster is tapped, it zooms in and breaks into individual markers
- Individual markers: colored dots by event type
- Bottom sheet (draggable): shows event cards for selected marker/cluster
- Filter chips floating at top (same as timeline view)

### 5. Search (`/search`)
- Full-screen overlay
- Large search input at top (supports Arabic input — show Arabic placeholder: "ابحث في الأحداث...")
- Below input: "Recent searches" section (empty state initially)
- Results stream in as cards (same card component as timeline)
- Show a search for "خديجة" (Khadijah) with 3 result cards
- Each result: highlighted matching text in the summary

### 6. About (`/about`)
- Project description
- Methodology: "Events extracted from OpenITI digital corpus using NLP + AI"
- Source texts listed: al-Tabari's Tarikh (with event count)
- Credits / GitHub link placeholder
- Stats: "846 events | 10 types | 615–775 CE | 1 primary source"

---

## DESIGN PRINCIPLES

1. **Arabic is primary.** Arabic text is always more prominent (larger font, gold-tinted color). English is the translation, not the other way around.
2. **Dark theme only.** Deep navy background, no light mode.
3. **Information density matters.** This is a research tool, not a marketing site. Users want to see data, not decorative whitespace. But it should still breathe — use spacing to create hierarchy, not emptiness.
4. **Every screen must handle RTL.** Arabic text blocks are right-aligned. Mixed content (bilingual cards) needs clear visual separation between AR and EN.
5. **The timeline is king.** It's the primary navigation method. Everything else (map, search, detail) is secondary.
6. **Type colors are sacred.** Battle = red, Death = orange, etc. These colors are the primary visual language for categorization. They appear on dots, badges, card accents, and map markers.
7. **Mobile gestures:** pinch-to-zoom on timeline, swipe between eras, pull-up for event detail, drag bottom sheet on map.

---

## DELIVERABLES

Create each screen as a separate frame/artboard at 375x812px. Show:
- All text at real size (readable, not placeholder squiggles)
- Real colors from the palette
- Component boundaries clearly defined
- Touch target sizes (minimum 44x44px)
- Spacing values annotated where important
- State variations where relevant (e.g., timeline zoomed out vs zoomed in, search empty vs with results)

This is Round 1. I will review these wireframes and come back with feedback before we move to Round 2 (visual polish, micro-interactions, animation specs).
