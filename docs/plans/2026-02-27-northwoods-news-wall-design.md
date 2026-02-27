# Northwoods News Wall — Design Document

**Date:** 2026-02-27
**Project:** TechNewsFeed (Northwoods Tech shop display)
**Target device:** 40" Vizio E40-C2 (1080p), PC + browser in fullscreen

## Overview

Redesign the TechNewsFeed digital signage app from a single-slide purple glass-morphism slideshow into a multi-zone "Northwoods News Wall" with a warm, local aesthetic. Broaden the feed sources from all-security to a balanced consumer tech mix, and replace text-heavy scam tips with visual "Spot the Scam" slides featuring real screenshots.

## Architecture Decision

**Keep Flask + browser.** No Electron, no npm migration.

- Flask handles RSS fetching, caching, and serving — Python's feedparser is excellent for this
- Browser in fullscreen kiosk mode on the PC connected to the TV
- Network-accessible so the shop can check it from other devices

## Layout (3-Zone)

```
+-----------------------------------+--------------+
|                                   |              |
|         FEATURED STORY            |   SIDEBAR    |
|                                   |              |
|   [Large Image]                   |  [Story 2]   |
|                                   |  [Story 3]   |
|   Headline Text                   |  [Story 4]   |
|   Source badge • Time ago         |              |
|   Brief summary...               |              |
|                                   |              |
+-----------------------------------+--------------+
| Northwoods Tech | 715-715-7167 | OPEN | Thu 2:15p |
+--------------------------------------------------+
```

- **Featured story** (~70% width): Large image, headline, source badge, short summary. Rotates every 20 seconds with crossfade.
- **Sidebar** (~30% width): Stack of 3 smaller story cards (thumbnail + headline + source). Slides up every 15 seconds independently.
- **Bottom bar** (fixed): Business name, phone, open/closed status with pulse dot, date & time.
- Featured and sidebar pull from the same pool but never show duplicates.
- On screens < 768px, sidebar hides and falls back to single-zone.

## Color Palette

| Role             | Color       | Hex       |
|------------------|-------------|-----------|
| Background       | Deep pine   | #1B2E1F   |
| Surface/Cards    | Bark brown  | #2A2118   |
| Primary accent   | Amber gold  | #D4A843   |
| Secondary accent | Forest green| #4A7C59   |
| Text primary     | Warm cream  | #F5F0E8   |
| Text secondary   | Soft sage   | #A8B5A0   |
| Scam alert       | Warm red    | #C45C4A   |
| Bottom bar       | Dark walnut | #1A1510   |

## Visual Style

- No glass-morphism or blur. Subtle texture: faint wood-grain or paper-grain noise overlay.
- Rounded corners (12-16px). Soft shadows on cards.
- Small pine tree or mountain icon in the footer branding.
- Category badges as colored pills on each story.

## Typography

- **Font:** Nunito (Google Fonts) — rounded, friendly, readable at distance
- **Headlines:** Nunito Bold, responsive sizing for 1080p TV
- **Body/summaries:** Nunito Regular
- **Footer/metadata:** Nunito SemiBold, smaller

## Feed Sources (10 feeds)

### General Tech News (3)
1. **The Verge** — `https://www.theverge.com/rss/index.xml` — Excellent images, consumer-friendly
2. **Ars Technica** — `https://feeds.arstechnica.com/arstechnica/index` — Great structured image data
3. **Engadget** — `https://www.engadget.com/rss.xml` — Gadget-focused, covers products people repair

### Tips & How-To (2)
4. **How-To Geek** — `https://www.howtogeek.com/feed/` — Best fit for repair shop, practical tips
5. **Tom's Guide** — `https://www.tomsguide.com/feeds/all` — Reviews, buying guides, richest image data

### Security & Scams (3)
6. **Krebs on Security** — `https://krebsonsecurity.com/feed/` — Authoritative scam/breach reporting
7. **Malwarebytes Blog** — `https://www.malwarebytes.com/blog/feed` — Accessible security news
8. **BleepingComputer** — `https://www.bleepingcomputer.com/feed/` — Daily security/malware news

### Official / Authority (1)
9. **FTC Consumer Protection** — `https://www.ftc.gov/feeds/press-release-consumer-protection.xml` — Government scam alerts (needs user-agent header)

### Broader Tech (1)
10. **WIRED** — `https://www.wired.com/feed/rss` — Magazine-quality images, varied content

## Content Categories & Badges

| Category    | Badge Color   | Feeds                              |
|-------------|---------------|------------------------------------|
| TECH NEWS   | Amber (#D4A843) | The Verge, Ars Technica, Engadget |
| TECH TIP    | Green (#4A7C59) | How-To Geek, Tom's Guide          |
| SECURITY    | Forest (#2D5A3D) | Krebs, Malwarebytes, BleepingComputer |
| SCAM ALERT  | Red (#C45C4A)   | FTC, built-in scam tips           |
| TECH & SCIENCE | Amber (#D4A843) | WIRED                           |

## Content Rotation Logic

- Stories shuffled by category so types alternate (no 5 security articles in a row)
- Scam tip slides mixed in approximately every 5th-6th featured rotation
- Feeds refresh every 30 minutes (background thread, same as current)
- Stories sorted newest-first within each category before shuffling

## Scam Tips — Visual "Spot the Scam" Format

### Approach
Each scam tip is a visual slide showing a **real screenshot** of the scam alongside a **short, simple action step**. Language is dead simple — no jargon, written for elderly/non-tech-savvy audience.

### Slide Layout for Scam Tips
Left side: screenshot image (60%). Right side: headline + action text (40%).
Red-tinted card background to distinguish from news slides.

### The 10 Scam Tips

| # | Headline | Screenshot Source | Action |
|---|----------|-------------------|--------|
| 1 | Pop-ups Like This Are FAKE | MalwareTips.com fake virus popup | Close your browser. Don't call the number. |
| 2 | This Screen Is Lying To You | BleepingComputer browser lockscreen | Press Ctrl+Alt+Delete. Close your browser. |
| 3 | This Text Is a Scam | Panda Security package scam text | Don't click. Check tracking on the real site. |
| 4 | Your Bank Won't Text Like This | Trend Micro toll/bank text screenshots | Delete it. Call the number on your card. |
| 5 | This "Free Scan" Will Infect You | PCRisk fake antivirus screenshots | Don't download it. Windows already protects you. |
| 6 | You Don't Need to Buy Antivirus | Simple text slide (no screenshot) | Windows has built-in protection. It's free and good. Ask us. |
| 7 | Never Let a Stranger Into Your PC | AnyDesk/TeamViewer install prompt | If someone asks you to install this, hang up. |
| 8 | Microsoft Will Never Call You | Simple text slide (big bold) | Hang up. No real company cold-calls you. |
| 9 | This Email Isn't From Apple | Aura fake Apple receipt screenshot | Don't click links in emails. Go to the site yourself. |
| 10 | Not Sure? Just Ask Us. | Northwoods Tech branding | Come in anytime. We'll check it for free. |

### Screenshot Sources (educational/public)
- MalwareTips.com — fake virus popup screenshots
- PCRisk.com — fake antivirus and browser lockscreen screenshots
- Panda Security — scam text message screenshots
- Aura — phishing email screenshots (Apple, PayPal, Microsoft)
- BleepingComputer — fake Windows desktop lockscreen screenshots

## Animation & Timing

| Element | Duration | Animation |
|---------|----------|-----------|
| Featured story rotation | 20 seconds | Crossfade (1s ease) |
| Sidebar card rotation | 15 seconds | Slide-up (0.8s ease) |
| Scam tip display | 25 seconds | Crossfade (1s ease) |
| Bottom bar | Static | Time updates every minute |
| Open/closed dot | Continuous | Gentle pulse |

## Technical Changes

### Backend (app.py)
- Replace 10 feed URLs with new curated 10
- Add category metadata to each feed source
- Add shuffle logic to alternate categories
- Update scam tips data structure to include image paths
- Serve scam screenshots from `/static/scam-images/`
- Add user-agent header for FTC feed

### Frontend (templates/index.html — full rewrite)
- Three-zone layout: featured + sidebar + bottom bar
- Load Nunito from Google Fonts CDN
- Dual independent timers (featured @ 20s, sidebar @ 15s)
- Scam tip slides use visual layout with screenshots
- Category badge rendering based on feed source
- Responsive: sidebar hides on < 768px
- Keep keyboard controls (arrows, R to refresh)

### New Static Assets
- `/static/scam-images/` — 8-10 screenshot PNGs from educational sources
- Pine tree / mountain SVG icon for footer branding

### Testing
- Update test_app.py for new feed URLs and categories
- Test category tagging logic
- Test shuffle/alternation
- Test dual-timer independence
- Test scam tip image loading
- Test responsive sidebar hide
- Manual readability test on E40-C2 TV
