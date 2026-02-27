# Northwoods News Wall Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use frontend-design skill for Task 4 (the HTML/CSS rewrite).

**Goal:** Transform the TechNewsFeed app from a single-slide purple slideshow into a multi-zone "Northwoods News Wall" with warm local aesthetic, curated feeds, and visual scam tips with real screenshots.

**Architecture:** Flask backend stays the same (feed fetching, caching, API endpoints). Frontend gets a complete rewrite: 3-zone layout (featured story 70%, sidebar 30%, bottom bar), dual independent rotation timers, Nunito font, Northwoods earthy color palette. Scam tips become visual "Spot the Scam" slides with real screenshots served from `/static/scam-images/`.

**Tech Stack:** Python/Flask, feedparser, vanilla HTML/CSS/JS, Google Fonts (Nunito)

---

### Task 1: Update RSS Feed Sources and Add Category Metadata

**Files:**
- Modify: `app.py:22-35` (RSS_FEEDS)

**Step 1: Write the failing test**

Add to `test_app.py`:

```python
class TestFeedCategories(unittest.TestCase):

    def test_rss_feeds_have_categories(self):
        """Test that RSS_FEEDS is a list of dicts with url and category."""
        from app import RSS_FEEDS
        self.assertIsInstance(RSS_FEEDS, list)
        self.assertGreater(len(RSS_FEEDS), 0)
        for feed in RSS_FEEDS:
            self.assertIsInstance(feed, dict)
            self.assertIn('url', feed)
            self.assertIn('category', feed)
            self.assertIn('badge', feed)
            self.assertIn(feed['category'], ['tech_news', 'tech_tip', 'security', 'official', 'broad_tech'])

    def test_rss_feeds_count(self):
        """Test we have 10 curated feeds."""
        from app import RSS_FEEDS
        self.assertEqual(len(RSS_FEEDS), 10)
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py::TestFeedCategories -v`
Expected: FAIL — RSS_FEEDS is a list of strings, not dicts

**Step 3: Replace RSS_FEEDS in app.py**

Replace lines 22-35 with:

```python
# Curated tech news RSS feeds with categories
RSS_FEEDS = [
    # General Tech News
    {"url": "https://www.theverge.com/rss/index.xml", "category": "tech_news", "badge": "TECH NEWS"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "category": "tech_news", "badge": "TECH NEWS"},
    {"url": "https://www.engadget.com/rss.xml", "category": "tech_news", "badge": "TECH NEWS"},
    # Tips & How-To
    {"url": "https://www.howtogeek.com/feed/", "category": "tech_tip", "badge": "TECH TIP"},
    {"url": "https://www.tomsguide.com/feeds/all", "category": "tech_tip", "badge": "TECH TIP"},
    # Security & Scams
    {"url": "https://krebsonsecurity.com/feed/", "category": "security", "badge": "SECURITY"},
    {"url": "https://www.malwarebytes.com/blog/feed", "category": "security", "badge": "SECURITY"},
    {"url": "https://www.bleepingcomputer.com/feed/", "category": "security", "badge": "SECURITY"},
    # Official / Government
    {"url": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml", "category": "official", "badge": "CONSUMER ALERT"},
    # Broader Tech
    {"url": "https://www.wired.com/feed/rss", "category": "broad_tech", "badge": "TECH & SCIENCE"},
]

# Badge color mapping (used by frontend)
BADGE_COLORS = {
    "TECH NEWS": "#D4A843",
    "TECH TIP": "#4A7C59",
    "SECURITY": "#2D5A3D",
    "CONSUMER ALERT": "#C45C4A",
    "TECH & SCIENCE": "#D4A843",
    "SCAM ALERT": "#C45C4A",
}
```

**Step 4: Update parse_rss_feeds to use new feed structure**

In `app.py`, update `parse_rss_feeds()` (line 253 onward). Change `for feed_url in RSS_FEEDS:` to iterate dicts, and add `category` and `badge` to each item:

```python
def parse_rss_feeds() -> List[Dict]:
    all_items = []
    successful_feeds = 0

    for feed_info in RSS_FEEDS:
        feed_url = feed_info['url']
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url, etag=None, modified=None)

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                continue

            if not feed.entries:
                logger.warning(f"No entries found in feed {feed_url}")
                continue

            successful_feeds += 1
            for entry in feed.entries[:10]:
                try:
                    image_url = extract_image_url(entry)

                    published_parsed = entry.get('published_parsed')
                    if published_parsed:
                        try:
                            timestamp = time.mktime(published_parsed)
                        except (ValueError, OverflowError):
                            timestamp = time.time()
                    else:
                        timestamp = time.time()

                    item = {
                        'title': entry.get('title', 'No Title'),
                        'link': entry.get('link', '#'),
                        'summary': entry.get('summary', entry.get('description', 'No description available')),
                        'published': entry.get('published', ''),
                        'source': feed.feed.get('title', 'Unknown Source'),
                        'timestamp': timestamp,
                        'image': image_url,
                        'category': feed_info['category'],
                        'badge': feed_info['badge'],
                    }
                    all_items.append(item)
                except Exception as e:
                    logger.warning(f"Error processing entry from {feed_url}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            continue

    logger.info(f"Successfully fetched {successful_feeds}/{len(RSS_FEEDS)} feeds, {len(all_items)} total items")
    all_items.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_items
```

**Step 5: Run test to verify it passes**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py::TestFeedCategories -v`
Expected: PASS

**Step 6: Fix existing tests that break**

The `test_parse_rss_feeds_handles_errors` and `test_parse_rss_feeds_success` tests reference `RSS_FEEDS` as a list of strings. Update the mock to iterate dicts. In `test_parse_rss_feeds_handles_errors`, the mock will still work since `feedparser.parse` is called with `feed_info['url']`. Verify all tests pass:

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py -v`

**Step 7: Commit**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add app.py test_app.py
git commit -m "feat: replace RSS feeds with curated sources and add category metadata"
```

---

### Task 2: Rewrite Scam Tips Data Structure

**Files:**
- Modify: `app.py:37-194` (SCAM_TIPS)

**Step 1: Write the failing test**

Add to `test_app.py`:

```python
class TestScamTips(unittest.TestCase):

    def test_scam_tips_have_visual_fields(self):
        """Test scam tips have headline, action, and optional image."""
        from app import SCAM_TIPS
        for tip in SCAM_TIPS:
            self.assertIn('type', tip)
            self.assertEqual(tip['type'], 'scam')
            self.assertIn('headline', tip)
            self.assertIn('action', tip)
            self.assertIn('category', tip)
            self.assertEqual(tip['category'], 'SCAM ALERT')
            # image is optional (some tips are text-only)
            self.assertIn('image', tip)

    def test_scam_tips_count(self):
        """Test we have 10 scam tips."""
        from app import SCAM_TIPS
        self.assertEqual(len(SCAM_TIPS), 10)

    def test_scam_tips_last_is_cta(self):
        """Test last scam tip is the shop CTA."""
        from app import SCAM_TIPS
        self.assertIn('Just Ask Us', SCAM_TIPS[-1]['headline'])
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py::TestScamTips -v`
Expected: FAIL — old SCAM_TIPS has 'title'/'detail', not 'headline'/'action'

**Step 3: Replace SCAM_TIPS in app.py**

Replace the entire SCAM_TIPS block (both the original at line 38 and the override at line 62) with:

```python
# Visual "Spot the Scam" tips for digital signage
# Each tip pairs a real screenshot with a simple action step
SCAM_TIPS = [
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Pop-ups Like This Are FAKE",
        "action": "Close your browser. Don't call the number. Bring it to us.",
        "image": "/static/scam-images/fake-virus-popup.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This Screen Is Lying To You",
        "action": "Press Ctrl+Alt+Delete. Close your browser. You're fine.",
        "image": "/static/scam-images/browser-lockscreen.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This Text Is a Scam",
        "action": "Don't click. Check tracking on the real site or app.",
        "image": "/static/scam-images/fake-package-text.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Your Bank Won't Text Like This",
        "action": "Delete it. Call the number on the back of your card.",
        "image": "/static/scam-images/fake-bank-text.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This 'Free Scan' Will Infect You",
        "action": "Don't download it. Windows already protects you for free.",
        "image": "/static/scam-images/fake-antivirus.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "You Don't Need to Buy Antivirus",
        "action": "Windows has built-in protection. It's free and it's good. Ask us.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Never Let a Stranger Into Your PC",
        "action": "If someone asks you to install remote software, hang up.",
        "image": "/static/scam-images/remote-access-prompt.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Microsoft Will Never Call You",
        "action": "Hang up. No real company cold-calls about your computer.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This Email Isn't From Apple",
        "action": "Don't click links in emails. Go to the website yourself.",
        "image": "/static/scam-images/fake-apple-email.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Not Sure? Just Ask Us.",
        "action": "Come in anytime. We'll check it for free. That's what we're here for.",
        "image": None,
    },
]
```

**Step 4: Update the /api/scam-tips endpoint**

The existing endpoint at line 421 returns SCAM_TIPS as-is, so no change needed to the route. But the frontend will need to handle the new field names (`headline`/`action` instead of `title`/`detail`).

**Step 5: Run test to verify it passes**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py::TestScamTips -v`
Expected: PASS

**Step 6: Commit**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add app.py test_app.py
git commit -m "feat: rewrite scam tips as visual 'Spot the Scam' slides with screenshot refs"
```

---

### Task 3: Create Static Assets Directory and Placeholder Images

**Files:**
- Create: `static/scam-images/` directory
- Create: `static/scam-images/README.md` (instructions for adding real screenshots)
- Create: `static/northwoods-icon.svg` (pine tree branding icon)

**Step 1: Create directory structure**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
mkdir -p static/scam-images
```

**Step 2: Create placeholder README for scam images**

Create `static/scam-images/README.md`:

```markdown
# Scam Screenshot Images

Save real scam screenshots here for the "Spot the Scam" slides.

## Required files:
- `fake-virus-popup.png` — Screenshot of a fake "Your computer is infected" popup
- `browser-lockscreen.png` — Screenshot of a browser lockscreen scam
- `fake-package-text.png` — Screenshot of a fake package delivery text message
- `fake-bank-text.png` — Screenshot of a fake bank/toll text message
- `fake-antivirus.png` — Screenshot of a fake antivirus scan popup
- `remote-access-prompt.png` — Screenshot of AnyDesk/TeamViewer install prompt
- `fake-apple-email.png` — Screenshot of a fake Apple/PayPal phishing email

## Where to get screenshots:
- MalwareTips.com removal guides (fake virus popups)
- PCRisk.com removal guides (fake antivirus, browser lockscreens)
- Panda Security — "20 Text Message Scams" article (scam texts)
- Aura — "20 Phishing Email Examples" article (fake Apple/PayPal emails)
- BleepingComputer — fake Windows desktop lockscreen articles

All sources are educational/public awareness content.

## Image specs:
- PNG format preferred
- Any resolution (will be scaled by CSS)
- Crop to show just the scam content, not the full desktop
```

**Step 3: Create pine tree SVG icon**

Create `static/northwoods-icon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
  <path d="M32 4L20 24h8L18 40h10L20 56h24L36 40h10L36 24h8L32 4z" fill="#4A7C59"/>
  <rect x="28" y="56" width="8" height="6" rx="1" fill="#8B6914"/>
</svg>
```

**Step 4: Verify Flask serves static files**

Flask serves `/static/` by default. Verify:

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -c "from app import app; print(app.static_folder)"`
Expected: prints the static folder path

**Step 5: Commit**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add static/
git commit -m "feat: add static assets directory with scam image README and branding icon"
```

---

### Task 4: Rewrite Frontend — 3-Zone Layout with Northwoods Theme

> **REQUIRED SUB-SKILL:** Use `frontend-design` skill for this task. This is the core UI rewrite.

**Files:**
- Rewrite: `templates/index.html` (complete rewrite, all 800 lines)

**Step 1: Write the complete new index.html**

This is a full rewrite. The new file implements:

1. **Google Fonts** — Nunito loaded via CDN
2. **3-zone layout** — `.main-grid` with `.featured-zone` (70%) and `.sidebar-zone` (30%)
3. **Northwoods color palette** — CSS custom properties for all colors
4. **Featured story area** — Large image, headline, source badge, summary
5. **Sidebar** — 3 stacked story cards with thumbnails
6. **Bottom bar** — Business info, open/closed, date/time
7. **Scam tip visual layout** — Screenshot on left, headline + action on right
8. **Category badges** — Colored pills matching badge colors from backend
9. **Dual independent timers** — Featured rotates every 20s, sidebar every 15s
10. **Responsive** — Sidebar hides on < 768px, falls back to single zone
11. **Keyboard controls** — Arrow keys, R to refresh (kept from original)

Key CSS custom properties:

```css
:root {
    --bg-deep-pine: #1B2E1F;
    --surface-bark: #2A2118;
    --accent-amber: #D4A843;
    --accent-forest: #4A7C59;
    --text-cream: #F5F0E8;
    --text-sage: #A8B5A0;
    --alert-red: #C45C4A;
    --bar-walnut: #1A1510;
}
```

The HTML structure:

```html
<div class="main-grid">
    <div class="featured-zone" id="featuredZone">
        <!-- Featured story slides rendered by JS -->
    </div>
    <div class="sidebar-zone" id="sidebarZone">
        <!-- 3 sidebar cards rendered by JS -->
    </div>
</div>
<div class="bottom-bar">
    <!-- Business info, status, time -->
</div>
```

**The full file is too large to inline here. Implementation should use the frontend-design skill to produce the complete HTML/CSS/JS, referencing the design doc at `docs/plans/2026-02-27-northwoods-news-wall-design.md` for all specifications.**

Key JavaScript changes:
- `fetchFeeds()` — same logic, but renders into featured zone + sidebar separately
- `renderFeatured(items)` — renders one featured story at a time
- `renderSidebar(items)` — renders 3 sidebar cards
- `startFeaturedTimer()` — rotates featured every 20s
- `startSidebarTimer()` — rotates sidebar every 15s
- `shuffleByCategory(items)` — alternates categories so types don't cluster
- Scam tips render with image + headline + action layout
- Items pool is shared but deduplicated between featured and sidebar
- `updateClock()` — shows current time in bottom bar

**Step 2: Verify the page loads**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python app.py`
Open browser to `http://localhost:5000`
Expected: 3-zone layout renders with loading state, then populates with feeds

**Step 3: Verify scam tips render with images**

Check that scam tip slides show the screenshot on one side and headline/action on the other. Tips with `image: null` should show as text-only centered slides.

**Step 4: Verify sidebar rotates independently**

Watch the display for 30+ seconds. Featured should change at 20s, sidebar should shift at 15s. They should not be synchronized.

**Step 5: Verify responsive fallback**

Resize browser to < 768px width. Sidebar should hide. Featured zone should take full width.

**Step 6: Commit**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add templates/index.html
git commit -m "feat: rewrite frontend with 3-zone Northwoods News Wall layout"
```

---

### Task 5: Update Existing Tests for New Data Structures

**Files:**
- Modify: `test_app.py`

**Step 1: Update test_index_route**

The page title will change from "Tech News RSS Slideshow" to "Northwoods Tech News". Update the assertion:

```python
def test_index_route(self):
    """Test that index page loads."""
    response = self.app.get('/')
    self.assertEqual(response.status_code, 200)
    self.assertIn(b'Northwoods', response.data)
```

**Step 2: Update test_parse_rss_feeds_success mock**

The mock needs to account for RSS_FEEDS being a list of dicts now. Patch `RSS_FEEDS` in the test:

```python
@patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
@patch('app.feedparser.parse')
def test_parse_rss_feeds_success(self, mock_parse):
    """Test successful feed parsing."""
    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [
        MagicMock(
            get=MagicMock(side_effect=lambda key, default=None: {
                'title': 'Test Title',
                'link': 'http://test.com',
                'summary': 'Test summary',
                'published': '2025-01-01',
                'published_parsed': time.localtime()
            }.get(key, default)),
            media_content=[],
            media_thumbnail=[],
            enclosures=[],
            image=None
        )
    ]
    mock_feed.feed.get.return_value = 'Test Source'
    mock_parse.return_value = mock_feed

    result = parse_rss_feeds()
    self.assertGreater(len(result), 0)
    self.assertEqual(result[0]['title'], 'Test Title')
    self.assertEqual(result[0]['category'], 'tech_news')
    self.assertEqual(result[0]['badge'], 'TECH NEWS')
```

**Step 3: Update test_parse_rss_feeds_handles_errors mock**

```python
@patch('app.RSS_FEEDS', [{"url": "https://bad.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
@patch('app.feedparser.parse')
def test_parse_rss_feeds_handles_errors(self, mock_parse):
    """Test that parse_rss_feeds handles feed errors gracefully."""
    mock_feed = MagicMock()
    mock_feed.bozo = True
    mock_feed.bozo_exception = "Test error"
    mock_parse.return_value = mock_feed

    result = parse_rss_feeds()
    self.assertIsInstance(result, list)
    self.assertEqual(len(result), 0)
```

**Step 4: Add test for scam tips API with new format**

```python
def test_scam_tips_api_returns_new_format(self):
    """Test /api/scam-tips returns tips with headline/action fields."""
    response = self.app.get('/api/scam-tips')
    data = response.get_json()
    self.assertTrue(data['success'])
    self.assertGreater(len(data['items']), 0)
    first_tip = data['items'][0]
    self.assertIn('headline', first_tip)
    self.assertIn('action', first_tip)
    self.assertEqual(first_tip['type'], 'scam')
```

**Step 5: Run all tests**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add test_app.py
git commit -m "test: update tests for new feed categories and scam tip format"
```

---

### Task 6: Add FTC Feed User-Agent Header

**Files:**
- Modify: `app.py` (parse_rss_feeds function)

The FTC feed returns 403 without a proper user-agent. feedparser allows setting a custom agent.

**Step 1: Write the failing test**

```python
@patch('app.RSS_FEEDS', [{"url": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml", "category": "official", "badge": "CONSUMER ALERT"}])
@patch('app.feedparser.parse')
def test_ftc_feed_uses_user_agent(self, mock_parse):
    """Test that FTC feed is fetched with a user-agent header."""
    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = []
    mock_parse.return_value = mock_feed

    parse_rss_feeds()
    mock_parse.assert_called_once()
    call_kwargs = mock_parse.call_args
    # feedparser.parse accepts agent keyword
    self.assertIn('agent', call_kwargs.kwargs)
```

**Step 2: Run test to verify it fails**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py::TestRSSFeeds::test_ftc_feed_uses_user_agent -v`
Expected: FAIL

**Step 3: Add user-agent to feedparser.parse call**

In `parse_rss_feeds()`, change the parse call to:

```python
USER_AGENT = 'NorthwoodsTechNewsFeed/1.0 (+http://localhost:5000)'

# Inside parse_rss_feeds loop:
feed = feedparser.parse(feed_url, etag=None, modified=None, agent=USER_AGENT)
```

**Step 4: Run test to verify it passes**

Run: `cd C:/Users/zombo/Desktop/Programming/TechNewsFeed && python -m pytest test_app.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add app.py test_app.py
git commit -m "feat: add user-agent header for FTC feed compatibility"
```

---

### Task 7: Collect Scam Screenshot Images

**Files:**
- Add: `static/scam-images/*.png` (7 screenshot files)

**This is a manual task.** Download real scam screenshots from educational sources:

1. **fake-virus-popup.png** — From MalwareTips.com: https://malwaretips.com/blogs/remove-tech-support-scam-popups/
2. **browser-lockscreen.png** — From BleepingComputer: https://www.bleepingcomputer.com/news/security/fake-windows-10-desktop-used-in-new-police-browser-lock-scam/
3. **fake-package-text.png** — From Panda Security: https://www.pandasecurity.com/en/mediacenter/spam-text-message-examples/
4. **fake-bank-text.png** — From Trend Micro toll road scam articles
5. **fake-antivirus.png** — From PCRisk.com: https://www.pcrisk.com/removal-guides/23272-kaspersky-your-pc-is-infected-with-5-viruses-pop-up-scam
6. **remote-access-prompt.png** — Screenshot of AnyDesk install dialog
7. **fake-apple-email.png** — From Aura: https://www.aura.com/learn/phishing-email-examples

**Steps:**
1. Visit each source URL
2. Right-click the relevant screenshot image > Save As
3. Save to `static/scam-images/` with the filename above
4. Crop/resize if needed (CSS handles scaling, but keep aspect ratio reasonable)

**Commit:**

```bash
cd C:/Users/zombo/Desktop/Programming/TechNewsFeed
git add static/scam-images/
git commit -m "feat: add scam screenshot images from educational sources"
```

---

### Task 8: Manual TV Test and Polish

**Not a code task — integration testing on the actual E40-C2 TV.**

**Checklist:**
- [ ] Start the app: `python app.py`
- [ ] Open Chrome on the PC connected to the TV
- [ ] Navigate to `http://localhost:5000`
- [ ] Press F11 for fullscreen
- [ ] Verify text readability from 10-15 feet away
- [ ] Verify featured story rotates every ~20s
- [ ] Verify sidebar cards shift every ~15s
- [ ] Verify scam tip screenshots display correctly
- [ ] Verify scam tips with no image (tips 6, 8, 10) center the text
- [ ] Verify category badges show correct colors
- [ ] Verify bottom bar shows business name, phone, open/closed correctly
- [ ] Verify open/closed status matches actual hours
- [ ] Verify keyboard controls work (arrows, R)
- [ ] Let it run for 30+ minutes to verify no memory leaks or freezes
- [ ] Check that feeds auto-refresh at the 30-minute mark

**If text is too small:** Increase font sizes in CSS custom properties.
**If images are too dark:** Adjust card background opacity.
**If sidebar feels cramped:** Adjust grid template from 70/30 to 65/35.

---

## Task Dependency Order

```
Task 1 (feeds) ──┐
Task 2 (scam tips) ──┤── Task 4 (frontend rewrite) ── Task 5 (tests) ── Task 6 (FTC header)
Task 3 (static assets) ──┘                                                      │
                                                                          Task 7 (screenshots)
                                                                                 │
                                                                          Task 8 (TV test)
```

Tasks 1, 2, and 3 can be done in parallel. Task 4 depends on all three. Tasks 5-8 are sequential.
