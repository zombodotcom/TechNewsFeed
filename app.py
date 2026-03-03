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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    # Shopping / deals
    "coupon", "discount", "on sale", "promo", "affiliate",
    "buy now", "shop now", "clearance", "voucher", "sponsored",
    "gift guide", "price drop", "price cut",
    "tested and reviewed", "reviewed and rated",
    "buying guide",
    "I tried", "we tried", "I tested", "we tested",
    "you need to buy", "you should buy",
    "worth buying", "worth the money", "worth the price", "worth every penny",
    "to watch this weekend", "to stream this weekend",
    "movies to watch", "shows to watch",

    # ── Politics / partisan — keep the shop TV neutral ──
    # Figures
    "Trump", "Biden", "Obama", "RFK", "Kennedy",
    "DeSantis", "Vance", "Pence", "Harris",
    "Pelosi", "McConnell", "Schumer", "AOC",
    "Marjorie Taylor", "Elon Musk", "Vivek",
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

# Patterns that need actual regex (wildcards, numbers, etc.)
_JUNK_REGEX = [
    r'deal(s)?\b',
    r'save \$', r'\d+% off', r'under \$\d+', r'starting at \$',
    r'best .{0,40}\b20[2-3]\d', r'best .{0,20} to buy',
    r'best .{0,20} we.ve tested', r'best .{0,20} right now',
    r'best .{0,40} overall',
    r'\d+ best', r'top \d+ ',
    r'buyer.s guide',
    r'to buy in 20[2-3]\d', r'for 20[2-3]\d\)',
    r'Democrat(s|ic)?',
    r'left.wing', r'right.wing',
    r'inaugur', r'polling\b',
    r'op.ed\b', r'shutdown\b', r'primary\b',
]

# Build one compiled regex from both lists
_JUNK_PATTERNS = re.compile(
    r'|'.join(
        [r'\b' + re.escape(kw) + r'\b' for kw in _JUNK_KEYWORDS]
        + [r'\b' + p for p in _JUNK_REGEX]
    ),
    re.IGNORECASE,
)


def _is_junk_title(title: str) -> bool:
    """Return True if the title looks like an ad, deal, or clickbait."""
    return bool(_JUNK_PATTERNS.search(title))

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


def parse_rss_feeds() -> List[Dict]:
    """
    Parse all RSS feeds and return a list of news items.
    Uses cached data if feeds fail to ensure the app still works.
    
    Returns:
        List of dictionaries containing news item data
    """
    all_items = []
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
                    if _is_junk_title(title):
                        logger.info(f"Filtered junk title: {title}")
                        continue

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

    # Filter out articles older than 7 days
    cutoff = time.time() - 7 * 86400
    fresh_items = [item for item in all_items if item['timestamp'] >= cutoff]
    logger.info(f"After stale filter: {len(fresh_items)} items (dropped {len(all_items) - len(fresh_items)} old articles)")

    # Sort by timestamp (newest first)
    fresh_items.sort(key=lambda x: x['timestamp'], reverse=True)

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




if __name__ == '__main__':
    logger.info("Starting Tech News RSS Slideshow...")

    # Pre-fetch feeds so the first page load has data immediately
    logger.info("Fetching feeds on startup...")
    initial = parse_rss_feeds()
    if initial:
        feed_cache['items'] = initial
        feed_cache['last_update'] = time.time()
        logger.info(f"Startup: cached {len(initial)} items")

    app.run(host='0.0.0.0', port=5000, debug=True)

