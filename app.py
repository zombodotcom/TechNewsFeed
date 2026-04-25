"""
Tech News RSS Slideshow Feed
A Flask application that displays tech news from RSS feeds in a fullscreen slideshow.
"""

from flask import Flask, render_template, jsonify
import feedparser
from datetime import datetime
import json
import os
import time
from typing import List, Dict, Optional
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    requests = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Feed history log ────────────────────────────────────────
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)
_FEED_LOG = os.path.join(_LOG_DIR, 'feed_history.log')

def _log_feed_item(status: str, title: str, source: str):
    """Append one line per item: timestamp | SHOWN/FILTERED | source | title"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(_FEED_LOG, 'a', encoding='utf-8') as f:
        f.write(f'{ts} | {status:<8} | {source:<35} | {title}\n')

app = Flask(__name__)

# Load business config
_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(_config_path, 'r') as _f:
    BUSINESS_CONFIG = json.load(_f)

# Curated tech news RSS feeds with categories
RSS_FEEDS = [
    # General Tech News (editorial, not product reviews)
    {"url": "https://www.theverge.com/rss/index.xml", "category": "tech_news", "badge": "TECH NEWS"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "category": "tech_news", "badge": "TECH NEWS"},
    {"url": "https://www.techmeme.com/feed.xml", "category": "tech_news", "badge": "TECH NEWS"},
    # Security & Scams
    {"url": "https://krebsonsecurity.com/feed/", "category": "security", "badge": "SECURITY"},
    {"url": "https://www.bleepingcomputer.com/feed/", "category": "security", "badge": "SECURITY"},
    {"url": "https://feeds.feedburner.com/TheHackersNews", "category": "security", "badge": "SECURITY"},
    # Official / Government
    {"url": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml", "category": "official", "badge": "CONSUMER ALERT"},
    # Broader Tech & Science
    {"url": "https://arstechnica.com/science/feed/", "category": "broad_tech", "badge": "TECH & SCIENCE"},
]

# ── Title filter ─────────────────────────────────────────────
# Plain keywords / phrases — auto-wrapped with \b word boundaries.
# Just add a string to the right list; no regex needed.
_JUNK_KEYWORDS = {
    # ── Shopping / deals / promos ──
    "coupon", "discount", "on sale", "promo", "affiliate",
    "buy now", "shop now", "clearance", "voucher", "sponsored",
    "gift guide", "price drop", "price cut",
    "tested and reviewed", "reviewed and rated",
    "buying guide",
    "you need to buy", "you should buy",
    "worth buying", "worth the money", "worth the price", "worth every penny",
    "get one free", "BOGO",

    # ── Personal experience / "I used X" fluff ──
    "I tried", "we tried", "I tested", "we tested",
    "I let", "I used", "I spent", "I switched",
    "I replaced", "I ditched", "I gave up",
    "went surprisingly well", "changed my mind",
    "and here's what happened", "here's what I learned",
    "my dream", "my favorite", "my favourite",

    # ── Product reviews / hands-on ──
    "hands-on", "first look", "unboxing",
    "first impressions", "early impressions",

    # ── Urgency / sales pressure ──
    "last chance", "last day", "limited time", "act fast", "act now",
    "hurry", "don't miss", "don't wait", "before prices go up",
    "prices go up", "price goes up", "price increase",
    "lowest price", "all-time low", "flash sale", "doorbuster",
    "black friday", "cyber monday", "prime day", "amazon prime",
    "early access", "exclusive offer", "special offer",
    "ends today", "ends tonight", "ends soon", "ends tomorrow",
    "hours left", "minutes left",
    "add to cart", "checkout", "free shipping",
    "just dropped", "just went on sale",
    "massive savings", "huge savings", "big savings",
    "get it before", "grab it before", "snag it before",
    "stock up", "selling fast", "selling out", "almost gone",
    "while supplies last", "while stocks last",

    # ── Entertainment / streaming / media ──
    "to watch this weekend", "to stream this weekend",
    "movies to watch", "shows to watch",
    "trailer",
    "season finale", "series finale", "series premiere",
    "binge", "bingeworthy",

    # ── How-to / consumer guides ──
    "step by step", "everything you need to know",
    "what you need to know", "tips and tricks",

    # ── Comparison shopping ──
    "versus", "compared to",

    # ── Podcast promos ──
    "Vergecast", "Decoder",

    # ── Sponsored / vendor whitepaper content (THN, BleepingComputer) ──
    "webinar", "playbook", "ultimate guide", "defender's guide", "defenders guide",
    "security posture", "operational resilience", "credential management",
    "third-party risk", "third party risk", "best practices",
    "evolution of ransomware", "evolution of phishing", "evolution of malware",
    "decision engine", "authority gap", "observability",
    "threatsday", "weekly recap", "monthly recap",
    "as a service", "as-a-service",
    "defense in depth", "zero trust",  # vendor speak
    "as you think", "than you think",  # clickbait
    "no longer enough", "not enough anymore",
    "who's going to fix", "who is going to fix",

    # ── Seasonal fluff ──
    "April Fools", "April Fool",

    # ── Adult / NSFW content (kids walk past the screen) ──
    "porn", "pornography", "porno", "nudes", "OnlyFans",
    "sex tape", "sexual", "explicit content",
    "strip club", "escort", "brothel",

    # ── Gaming / entertainment fluff ──
    "PlayStation", "PS5", "PS4", "Nintendo Switch",
    "Double Fine", "indie game", "indie games",
    "video game", "video games", "videogame", "videogames",
    "weirdest studio", "weirdest game",

    # ── Non-tech science / nature / paleontology / medical fluff ──
    "shark", "sharks", "octopus", "octopi", "parrot", "parrots",
    "kraken", "mosasaur", "dinosaur", "dinosaurs",
    "cretaceous", "jurassic", "triassic", "paleozoic", "cambrian",
    "fossil", "fossils",
    "ice age",
    "chickenpox", "measles", "polio",
    "Amelia Earhart",
    "polygraph", "polygraphs",

    # ── Retailer names (always shopping context in headlines) ──
    "at Target", "at Walmart", "at Best Buy", "at Costco", "at B&H",

    # ── Politics / partisan — keep the shop TV neutral ──
    # Figures
    "Trump", "Biden", "Obama", "RFK", "Kennedy",
    "DeSantis", "Vance", "Pence", "Harris",
    "Pelosi", "McConnell", "Schumer", "AOC",
    "Marjorie Taylor", "Elon Musk", "Vivek",
    "Alex Jones", "Infowars",
    # Parties & labels
    "Republican", "GOP", "MAGA",
    "liberal", "conservative", "partisan", "bipartisan",
    # Institutions
    "White House", "Capitol Hill", "Oval Office",
    "Congress", "Senate", "House of Representatives",
    "Supreme Court", "DOGE", "HHS",
    # Titles
    "Senator", "Congressman", "Congresswoman", "lawmaker", "legislator",
    # Elections
    "election", "ballot", "voter", "caucus", "midterm",
    "campaign trail", "poll shows",
    # Political actions
    "impeach", "executive order", "veto",
    "filibuster",  "debt ceiling",
    # Culture war
    "woke", "cancel culture", "DEI",
    "gun control", "gun rights", "Second Amendment",
    "abortion", "Roe v", "immigration", "border wall",
    # Opinion
    "The Lancet", "editorial board",
}

# Patterns that need actual regex (wildcards, numbers, etc.).
# NOTE: these are NOT auto-prefixed with \b — each pattern manages its own
# boundaries so that $-prefixed patterns and ^-anchored patterns work.
_JUNK_REGEX = [
    # ── Deals / pricing ──
    r'\bdeal(s)?\b',
    r'save \$', r'save (?:up to )?\d+', r'\d+% off',
    r'under \$\d+', r'starting at \$',
    r'\$\d+.{0,10}\boff\b', r'for (?:just|only) \$\d+',
    r'\bspring sale', r'\bsummer sale', r'\bwinter sale', r'\bfall sale',
    r'\bbig .{0,10} sale', r'\bmega sale',
    r'\byou can (?:still )?(?:get|grab|snag)',
    r'\bbuy .{1,10},?\s*get\b',

    # ── Listicles / "best of" ──
    r'\bbest .{0,40}\b20[2-3]\d', r'\bbest .{0,20} to buy',
    r'\bbest .{0,20} we.ve tested', r'\bbest .{0,20} right now',
    r'\bbest .{0,40} overall',
    r'\b\d+ best\b', r'\btop \d+ ',
    r'\bbuyer.s guide',
    r'\bto buy in 20[2-3]\d', r'for 20[2-3]\d\)',
    r'\b\d+ (?:tips|ways|things|reasons) (?:for|to|you|why)\b',
    r'\b\d+ (?:movies|shows|albums|songs|podcasts) (?:to|you)\b',

    # ── Personal experience / "I did X" ──
    r'\b(?:I|we) (?:finally|actually|really) .{0,20}(?:love|hate|need|want)\b',
    r'\b(?:I|we) (?:can.t|cannot) (?:stop|quit|resist)\b',
    r'\b(?:I|we) (?:ranked|rated|scored)\b',
    r'\bfinally got me\b',
    r'\bfor a (?:week|month|day|year)\b',
    r'\bthis is my .{1,20}(?:time|attempt|try)\b',
    r'\bmy .{1,30} needs? to have\b',

    # ── Reviews / comparison ──
    r'\b(?:is|are) (?:it|they) worth\b',
    r'\bhow (?:good|bad) is\b',
    r'\bvs\.?\s',
    r'\bwhich (?:is|should you)\b',
    r'\b(?:better|faster|cheaper) than\b',

    # ── How-to / explainer ──
    r'^how to ',
    r'\bhere.s (?:how|what|why|everything)\b',
    r'\bin \d+ steps?\b',                  # "in 3 steps"
    r'^\[webinar\]',                       # "[Webinar] ..."
    r'\b\+\s*\d+ new stories\b',           # "+25 New Stories" bulletin

    # ── Personal review / fluff opinion pieces ──
    r'^the most (?:exciting|amazing|incredible|beautiful)\b',
    r'\bi.ve (?:ever )?seen .{0,20}\bin forever\b',
    r'\bbrightened (?:up )?my\b',
    r'\b(?:and then|then) my life\b',
    r'^six things\b', r'^seven things\b', r'^eight things\b', r'^nine things\b',
    r'^ten things\b', r'^five things\b', r'^four things\b', r'^three things\b',
    r'\bthings? (?:i|we).ll remember\b',
    r'\b(?:my|our) version of\b',

    # ── Entertainment / streaming ──
    r'\b(?:new|official|first|final|full) .{0,20}trailer\b',
    r'\b(?:movie|film|show|series|season) (?:review|recap|premiere|finale)\b',
    r'\b(?:watch|stream|listen to) (?:this|these|now|today|tonight)\b',
    r'\bwhat .{1,30} reveals about\b',

    # ── Politics (regex patterns) ──
    r'\bDemocrat(s|ic)?\b',
    r'\bleft.wing', r'\bright.wing',
    r'\binaugur', r'\bpolling\b',
    r'\bop.ed\b', r'\bshutdown\b', r'\bprimary\b',
]

# Build one compiled regex from both lists
_JUNK_PATTERNS = re.compile(
    r'|'.join(
        # Keywords get auto-wrapped with \b
        [r'\b' + re.escape(kw) + r'\b' for kw in _JUNK_KEYWORDS]
        # Regex patterns manage their own boundaries (no auto \b)
        + _JUNK_REGEX
    ),
    re.IGNORECASE,
)


def _is_junk_title(title: str) -> bool:
    """Return True if the title looks like an ad, deal, or clickbait."""
    return bool(_JUNK_PATTERNS.search(title))


# URL path segments that indicate non-tech content (gaming, entertainment, etc.)
_JUNK_URL_SEGMENTS = (
    '/games/', '/gaming/', '/entertainment/',
    '/movies/', '/music/', '/tv/',
    '/culture/', '/podcast/',
    '/lifestyle/', '/wellness/',
)


def _is_junk_link(link: str) -> bool:
    """Return True if the URL path indicates non-tech content."""
    if not link:
        return False
    return any(seg in link.lower() for seg in _JUNK_URL_SEGMENTS)

# Badge color mapping (used by frontend)
BADGE_COLORS = {
    "TECH NEWS": "#D4A843",
    "TECH TIP": "#4A7C59",
    "SECURITY": "#2D5A3D",
    "CONSUMER ALERT": "#C45C4A",
    "TECH & SCIENCE": "#D4A843",
    "SCAM ALERT": "#C45C4A",
}

# Visual "Spot the Scam" tips for digital signage
# Each tip pairs a real screenshot with a simple action step
SCAM_TIPS = [
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Pop-ups Like This Are FAKE",
        "action": "Close your browser. Don't call the number. Bring it to us.",
        "image": "/static/scam-images/fake-virus-popup.svg",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This Screen Is Lying To You",
        "action": "Press Ctrl+Alt+Delete. Close your browser. You're fine.",
        "image": "/static/scam-images/browser-lockscreen.svg",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This Text Is a Scam",
        "action": "Don't click. Check tracking on the real site or app.",
        "image": "/static/scam-images/fake-package-text.svg",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Your Bank Won't Text Like This",
        "action": "Delete it. Call the number on the back of your card.",
        "image": "/static/scam-images/fake-bank-text.svg",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "This 'Free Scan' Will Infect You",
        "action": "Don't download it. Windows already protects you for free.",
        "image": "/static/scam-images/fake-antivirus.svg",
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
        "image": "/static/scam-images/remote-access-prompt.svg",
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
        "image": "/static/scam-images/fake-apple-email.svg",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "If You See These Apps — DELETE Them",
        "action": "These cleaner apps are scams. Bring your phone in — we'll remove them free.",
        "image": "/static/scam-images/cleaner-apps-wall-of-shame.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Cleaner Apps ARE the Virus Popups",
        "action": "That 'speed up your phone' app is what's spamming you. Delete it. We'll help.",
        "image": "/static/scam-images/cleaner-apps-wall-of-shame.png",
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Deleting an App Doesn't Cancel It",
        "action": "Subscriptions keep billing after you uninstall. Cancel in Settings → Subscriptions. We'll help.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Your Phone Already Has a Cleaner — Free",
        "action": "iPhone: Settings → General → iPhone Storage. Android: Files app. No subscription. Ask us.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Cancel the Subscription First",
        "action": "iPhone: Settings → Subscriptions. Android: Play Store. Then dispute with your bank.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "'Hi Mom, New Number' Is a Scam",
        "action": "Voice and video can be faked now. Hang up, call the real number you know.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Random WhatsApp Group? Leave It",
        "action": "Crypto and 'insider tip' groups are scams. Everyone bragging is in on it.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Real PayPal Invoices Have No Phone Number",
        "action": "If an invoice says 'call to dispute,' it's fake. Log into paypal.com yourself.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "PayPal Won't Call You About a Refund",
        "action": "If 'PayPal' calls about an unauthorized charge, hang up. Don't install anything they say.",
        "image": None,
    },
    {
        "type": "scam",
        "category": "SCAM ALERT",
        "headline": "Not Sure? Just Ask Us.",
        "action": "Come in anytime. We'll check it for free. That's what we're here for.",
        "image": None,
    },
]

# Cache for RSS feeds (refresh every 5 minutes)
feed_cache = {
    'items': [],
    'last_update': 0,
    'cache_duration': 300,  # 5 minutes
    'fetching': False,  # Lock to prevent concurrent fetches
    'lock': threading.Lock()  # Thread lock
}



def extract_image_url(entry) -> Optional[str]:
    """
    Extract image URL from RSS entry.
    Tries multiple methods to find an image.
    
    Returns:
        Image URL string or None if no image found
    """
    # Method 1: Check for media:content or media:thumbnail (Media RSS)
    if hasattr(entry, 'media_content'):
        for media in entry.media_content:
            if media.get('type', '').startswith('image/'):
                return media.get('url')
    
    if hasattr(entry, 'media_thumbnail'):
        for thumb in entry.media_thumbnail:
            return thumb.get('url')
    
    # Method 2: Check for enclosure (image type)
    if hasattr(entry, 'enclosures'):
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                return enc.get('href')
    
    # Method 3: Extract from summary/description HTML
    summary = entry.get('summary', entry.get('description', ''))
    if summary:
        # Look for img tags
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(img_pattern, summary, re.IGNORECASE)
        if matches:
            return matches[0]
        
        # Look for background-image in style
        bg_pattern = r'background-image:\s*url\(["\']?([^"\']+)["\']?\)'
        matches = re.findall(bg_pattern, summary, re.IGNORECASE)
        if matches:
            return matches[0]
    
    # Method 4: Check for image field
    if hasattr(entry, 'image') and entry.image:
        return entry.image.get('href') if isinstance(entry.image, dict) else entry.image

    return None


# Cache og:image lookups so we don't re-fetch the same URL every refresh.
_OG_IMAGE_CACHE: Dict[str, Optional[str]] = {}
_OG_IMAGE_LOCK = threading.Lock()
_OG_META_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.IGNORECASE,
)


def fetch_og_image(article_url: str, timeout: float = 4.0) -> Optional[str]:
    """Fetch the article URL and parse its og:image meta tag."""
    if not article_url or requests is None:
        return None
    with _OG_IMAGE_LOCK:
        if article_url in _OG_IMAGE_CACHE:
            return _OG_IMAGE_CACHE[article_url]
    result: Optional[str] = None
    try:
        resp = requests.get(
            article_url,
            timeout=timeout,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            },
            stream=True,
        )
        # Only read the head — og:image is always in <head>
        chunk = resp.raw.read(64 * 1024, decode_content=True)
        html = chunk.decode('utf-8', errors='ignore')
        resp.close()
        m = _OG_META_RE.search(html)
        if m:
            result = m.group(1) or m.group(2)
    except Exception as e:
        logger.debug(f"og:image fetch failed for {article_url}: {e}")
    with _OG_IMAGE_LOCK:
        _OG_IMAGE_CACHE[article_url] = result
    return result


def backfill_missing_images(items: List[Dict], max_workers: int = 8) -> None:
    """Fill in og:image for items missing an image. Mutates items in place."""
    if requests is None:
        return
    needs_image = [it for it in items if not it.get('image') and it.get('link')]
    if not needs_image:
        return
    logger.info(f"Backfilling og:image for {len(needs_image)} items")
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_og_image, it['link']): it for it in needs_image}
        for fut in as_completed(futures):
            it = futures[fut]
            try:
                img = fut.result()
                if img:
                    it['image'] = img
            except Exception:
                pass


def parse_rss_feeds() -> List[Dict]:
    """
    Parse all RSS feeds and return a list of news items.
    Uses cached data if feeds fail to ensure the app still works.
    
    Returns:
        List of dictionaries containing news item data
    """
    all_items = []
    seen_links = set()
    seen_titles = set()
    successful_feeds = 0

    for feed_info in RSS_FEEDS:
        feed_url = feed_info['url']
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url, etag=None, modified=None,
                                      agent='NorthwoodsTechNewsFeed/1.0 (+http://localhost:5000)')

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                continue

            if not feed.entries:
                logger.warning(f"No entries found in feed {feed_url}")
                continue

            successful_feeds += 1
            for entry in feed.entries[:15]:  # Check up to 15, some may be filtered
                try:
                    title = entry.get('title', 'No Title')
                    source_name = feed.feed.get('title', 'Unknown Source')
                    if _is_junk_title(title):
                        logger.info(f"Filtered junk title: {title}")
                        _log_feed_item('FILTERED', title, source_name)
                        continue

                    raw_link = entry.get('link', '')
                    if _is_junk_link(raw_link):
                        logger.info(f"Filtered junk URL path: {raw_link}")
                        _log_feed_item('FILTERED', title, source_name)
                        continue

                    # Dedupe across feeds — same article often cross-posts
                    # (e.g. Ars main + Ars Science). Strip query strings so
                    # tracking params don't defeat matching.
                    link = entry.get('link', '').split('?')[0].rstrip('/').lower()
                    title_key = title.strip().lower()
                    if link and link in seen_links:
                        _log_feed_item('DUPLICATE', title, source_name)
                        continue
                    if title_key in seen_titles:
                        _log_feed_item('DUPLICATE', title, source_name)
                        continue
                    if link:
                        seen_links.add(link)
                    seen_titles.add(title_key)

                    image_url = extract_image_url(entry)

                    # Handle published_parsed safely
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
                        'source': source_name,
                        'timestamp': timestamp,
                        'image': image_url,
                        'category': feed_info['category'],
                        'badge': feed_info['badge'],
                    }
                    all_items.append(item)
                    _log_feed_item('SHOWN', title, source_name)
                except Exception as e:
                    logger.warning(f"Error processing entry from {feed_url}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            continue
    
    logger.info(f"Successfully fetched {successful_feeds}/{len(RSS_FEEDS)} feeds, {len(all_items)} total items")

    # Filter out articles older than 7 days
    cutoff = time.time() - 7 * 86400
    fresh_items = [item for item in all_items if item['timestamp'] >= cutoff]
    logger.info(f"After stale filter: {len(fresh_items)} items (dropped {len(all_items) - len(fresh_items)} old articles)")

    # Sort by timestamp (newest first)
    fresh_items.sort(key=lambda x: x['timestamp'], reverse=True)

    # Fall back to fetching og:image for items the RSS feed didn't supply
    backfill_missing_images(fresh_items)

    return fresh_items


def _fetch_feeds_background():
    """Fetch feeds in background thread."""
    try:
        logger.info("Fetching feeds in background...")
        new_items = parse_rss_feeds()
        if new_items:
            feed_cache['items'] = new_items
            feed_cache['last_update'] = time.time()
            logger.info(f"Successfully updated cache with {len(new_items)} items")
        else:
            logger.warning("No items fetched, keeping cached data")
    except Exception as e:
        logger.error(f"Error fetching feeds in background: {str(e)}")
    finally:
        feed_cache['fetching'] = False


def get_cached_feeds() -> List[Dict]:
    """
    Get cached RSS feeds. Returns immediately with cached data.
    Fetches new feeds in background if cache is expired.
    
    Returns:
        List of news items (always returns cached data immediately)
    """
    current_time = time.time()
    cache_expired = (current_time - feed_cache['last_update']) > feed_cache['cache_duration']
    
    # If cache expired and not already fetching, start background fetch
    if cache_expired and not feed_cache['fetching']:
        with feed_cache['lock']:
            # Double-check after acquiring lock
            if not feed_cache['fetching']:
                feed_cache['fetching'] = True
                thread = threading.Thread(target=_fetch_feeds_background, daemon=True)
                thread.start()
    
    # Always return cached data immediately (even if empty or stale)
    return feed_cache['items'] if feed_cache['items'] else []


@app.route('/')
def index():
    """Render the main slideshow page."""
    return render_template('index.html',
                           config=BUSINESS_CONFIG,
                           config_json=json.dumps(BUSINESS_CONFIG))


@app.route('/api/feeds')
def get_feeds():
    """API endpoint to get RSS feed items."""
    try:
        items = get_cached_feeds()
        return jsonify({
            'success': True,
            'items': items,
            'count': len(items),
            'last_update': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in get_feeds: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'items': []
        }), 500


@app.route('/api/refresh')
def refresh_feeds():
    """Force refresh of RSS feeds and return new data."""
    try:
        # Force refresh by fetching new feeds
        new_items = parse_rss_feeds()
        if new_items:
            feed_cache['items'] = new_items
            feed_cache['last_update'] = time.time()
            return jsonify({
                'success': True,
                'message': 'Feeds refreshed successfully',
                'items': new_items,
                'count': len(new_items),
                'last_update': datetime.now().isoformat()
            })
        else:
            # Return cached data if refresh got nothing
            return jsonify({
                'success': True,
                'message': 'No new items found, using cached data',
                'items': feed_cache['items'],
                'count': len(feed_cache['items']),
                'last_update': datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Error refreshing feeds: {str(e)}")
        # Return cached data on error
        return jsonify({
            'success': False,
            'error': str(e),
            'items': feed_cache['items'],
            'count': len(feed_cache['items'])
        }), 500


@app.route('/api/scam-tips')
def scam_tips():
    """Static scam tip cards for digital signage."""
    return jsonify({
        'success': True,
        'items': SCAM_TIPS,
        'count': len(SCAM_TIPS),
        'last_update': datetime.now().isoformat()
    })




def _daily_refresh_loop():
    """Background thread that force-refreshes all feeds at 5:00 AM daily."""
    while True:
        now = datetime.now()
        # Calculate seconds until next 5:00 AM
        target = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=target.day)  # later today already passed
            from datetime import timedelta
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Daily refresh scheduled in {wait_seconds/3600:.1f} hours (at {target})")
        time.sleep(wait_seconds)

        # Force a full feed refresh
        logger.info("=== Daily 5 AM refresh triggered ===")
        try:
            new_items = parse_rss_feeds()
            if new_items:
                feed_cache['items'] = new_items
                feed_cache['last_update'] = time.time()
                logger.info(f"Daily refresh: cached {len(new_items)} items")
        except Exception as e:
            logger.error(f"Daily refresh failed: {e}")


# Track server start time so the frontend knows when to reload
_server_start_time = time.time()


@app.route('/api/server-start')
def server_start():
    """Return server start time so the frontend can detect restarts."""
    return jsonify({'start_time': _server_start_time})


if __name__ == '__main__':
    logger.info("Starting Tech News RSS Slideshow...")

    # Start daily 5 AM refresh thread
    daily_thread = threading.Thread(target=_daily_refresh_loop, daemon=True)
    daily_thread.start()

    # Pre-fetch feeds so the first page load has data immediately
    logger.info("Fetching feeds on startup...")
    initial = parse_rss_feeds()
    if initial:
        feed_cache['items'] = initial
        feed_cache['last_update'] = time.time()
        logger.info(f"Startup: cached {len(initial)} items")

    app.run(host='0.0.0.0', port=5000, debug=True)

