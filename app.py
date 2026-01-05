"""
Tech News RSS Slideshow Feed
A Flask application that displays tech news from RSS feeds in a fullscreen slideshow.
"""

from flask import Flask, render_template, jsonify
import feedparser
from datetime import datetime
import time
from typing import List, Dict, Optional
import logging
import re
import threading
import datetime as dt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Tech and security news RSS feeds
RSS_FEEDS = [
    # Security News (Primary Focus) - Only reliable, working feeds
    "https://www.bleepingcomputer.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/",
    "https://thehackernews.com/feeds/posts/default",
    "https://www.darkreading.com/rss.xml",
    "https://threatpost.com/feed/",
    "https://www.securityweek.com/feed/",
    "https://www.helpnetsecurity.com/feed/",
    "https://www.securityaffairs.com/feed",
    "https://grahamcluley.com/feed/",
]

# Scam tip cards for digital signage (static, concise)
SCAM_TIPS = [
    # Core rules
    {"type": "scam", "category": "rule", "source": "Scam Tips", "title": "Hang up. Look up. Call back.", "detail": "If they call you, hang up. Use the official number you find yourself."},
    {"type": "scam", "category": "rule", "source": "Scam Tips", "title": "Never pay with gift cards/crypto/wires.", "detail": "No real company or agency asks for gift cards, crypto, wire, or cash courier."},
    {"type": "scam", "category": "rule", "source": "Scam Tips", "title": "Urgent & secret = scam.", "detail": "If they say act now and tell no one, stop and verify with family or the official number."},
    {"type": "scam", "category": "rule", "source": "Scam Tips", "title": "Don’t click surprise links.", "detail": "Delivery/account texts: open the official app or site instead."},
    {"type": "scam", "category": "rule", "source": "Scam Tips", "title": "Protect your numbers.", "detail": "Never share SSN, bank info, PINs, or Medicare number with unsolicited callers."},

    # Fast alerts with actions
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Package delivery scam", "detail": "“Missed delivery—click/pay fee.” Go to USPS/UPS/FedEx app directly; never pay from a text link."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Grandparent scam", "detail": "“I’m in jail—don’t tell anyone.” Hang up; call the person/family on their real number."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Utility shutoff threat", "detail": "“Power off in 1 hour.” Real utilities send notices; pay only in your official account."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "IRS/SSA impostor", "detail": "“SSN suspended/you owe—pay now.” They send letters; they don’t call or text for instant payment."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Tech support pop-up", "detail": "“Virus—call now.” Close the tab; run your own antivirus. Never allow remote access."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Romance emergency", "detail": "Online “partner” needs money. No money to someone you’ve never met in person."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Job offer fee", "detail": "“You’re hired—pay for gear or background check.” Legit employers never charge you."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Overpayment/refund", "detail": "Buyer “overpays” and wants a refund. Check is fake; keep nothing, refund nothing."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Charity pressure", "detail": "Disaster donation pressure. Verify on CharityNavigator/GuideStar; donate on official sites only."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Jury duty fine", "detail": "“Pay now or arrest.” Courts mail notices; no pay-now calls."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Medicare card scam", "detail": "“Verify your number for a new card.” Medicare won’t call to collect your number."},
    {"type": "scam", "category": "alert", "source": "Scam Tips", "title": "Tax preparer blank form", "detail": "“Sign this blank; bigger refund.” Never sign blank returns; you’re responsible."},
]

# Override with full-text scam tips for signage
SCAM_TIPS = [
    {
        "type": "scam",
        "category": "rule",
        "source": "Scam Tips",
        "title": "Hang up. Look up. Call back.",
        "detail": "If someone calls you, hang up. Use the official number you find yourself to verify. Never trust numbers given by the caller.",
    },
    {
        "type": "scam",
        "category": "rule",
        "source": "Scam Tips",
        "title": "Never pay with gift cards, crypto, or wire.",
        "detail": "No real company or government agency will ask you to pay with gift cards, cryptocurrency, wire transfers, or cash handed to a courier.",
    },
    {
        "type": "scam",
        "category": "rule",
        "source": "Scam Tips",
        "title": "Urgent and secret = scam.",
        "detail": "Scammers push urgency and secrecy. Slow down, verify with family, and contact the organization directly through official channels.",
    },
    {
        "type": "scam",
        "category": "rule",
        "source": "Scam Tips",
        "title": "Don't click surprise links.",
        "detail": "Delivery or account texts that demand action: ignore the link and go to the official app or website yourself.",
    },
    {
        "type": "scam",
        "category": "rule",
        "source": "Scam Tips",
        "title": "Protect your numbers.",
        "detail": "Never share your Social Security number, bank info, PINs, or Medicare number with unsolicited callers or texters.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Package delivery scam",
        "detail": "Texts or emails claim a delivery is held or needs a fee. Links lead to fake sites that steal card info.",
        "avoid": "Check deliveries only in the official USPS/UPS/FedEx/Amazon app or site—never through a link in a message.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Grandparent scam",
        "detail": "Caller pretends to be a grandchild in trouble and begs you not to tell family. They demand urgent money.",
        "avoid": "Hang up and call the person or another family member on their real number.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Utility shutoff threat",
        "detail": "Caller claims your power/gas/water will be disconnected in an hour unless you pay immediately by prepaid card or wire.",
        "avoid": "Real utilities send written notices; pay only through your official account or known channels.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "IRS/SSA impostor",
        "detail": "“SSN suspended/you owe—pay now.” IRS/SSA send letters; they don’t call or text for instant payment.",
        "avoid": "Call the official IRS/SSA number you look up yourself. They never take gift cards, crypto, or wire.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Tech support pop-up",
        "detail": "Fake pop-ups say your computer is infected and give a number to call. They’ll ask for remote access or payment.",
        "avoid": "Close the tab, reboot if needed, and run your own antivirus. Never let unknown callers remote into your device.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Romance emergency",
        "detail": "Online “partner” you’ve never met suddenly needs money for an emergency and promises to repay.",
        "avoid": "Never send money to someone you haven’t met in person.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Job offer fee",
        "detail": "“You’re hired—just pay for gear or background check.”",
        "avoid": "Legit employers don’t make you pay to get a job.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Overpayment/refund scam",
        "detail": "A buyer “overpays” and asks you to refund the extra. Their payment is fake, but your refund is real money.",
        "avoid": "Never refund overpayments; wait for payments to clear through official channels.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Charity pressure",
        "detail": "After disasters, scammers use names similar to real charities and demand fast donations.",
        "avoid": "Verify on CharityNavigator/GuideStar and donate only through official charity sites—never via unsolicited links.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Jury duty fine",
        "detail": "Caller says you missed jury duty and must pay now or be arrested.",
        "avoid": "Courts send letters; they don’t call for immediate payment. Fines are paid through official court channels.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Medicare card scam",
        "detail": "Scammers ask for your Medicare number to issue a new card or benefit.",
        "avoid": "Medicare will not call unsolicited to collect your number. Guard it like a credit card.",
    },
    {
        "type": "scam",
        "category": "alert",
        "source": "Scam Tips",
        "title": "Tax preparer scam",
        "detail": "Dishonest preparers ask you to sign blank returns or promise huge refunds for a fee.",
        "avoid": "Never sign blank returns; use reputable preparers and review everything before signing.",
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
    
    for feed_url in RSS_FEEDS:
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
            for entry in feed.entries[:10]:  # Limit to 10 items per feed
                try:
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
                        'image': image_url
                    }
                    all_items.append(item)
                except Exception as e:
                    logger.warning(f"Error processing entry from {feed_url}: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            continue
    
    logger.info(f"Successfully fetched {successful_feeds}/{len(RSS_FEEDS)} feeds, {len(all_items)} total items")
    
    # Sort by timestamp (newest first)
    all_items.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return all_items


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
    return render_template('index.html')


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
    # Start the Flask app immediately
    logger.info("Starting Tech News RSS Slideshow...")
    logger.info("Site will load immediately, feeds will fetch in background...")
    
    # Run the Flask app
    # Use host='0.0.0.0' to make it accessible on the network
    # debug=True enables hot reloading and better error messages
    app.run(host='0.0.0.0', port=5000, debug=True)

