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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Popular tech news RSS feeds
RSS_FEEDS = [
    "https://feeds.feedburner.com/oreilly/radar",
    "https://www.wired.com/feed/rss",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.engadget.com/rss.xml",
    "https://feeds.feedburner.com/oreilly/radar",
]

# Cache for RSS feeds (refresh every 5 minutes)
feed_cache = {
    'items': [],
    'last_update': 0,
    'cache_duration': 300  # 5 minutes
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
    
    Returns:
        List of dictionaries containing news item data
    """
    all_items = []
    
    for feed_url in RSS_FEEDS:
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                continue
            
            for entry in feed.entries[:10]:  # Limit to 10 items per feed
                image_url = extract_image_url(entry)
                
                item = {
                    'title': entry.get('title', 'No Title'),
                    'link': entry.get('link', '#'),
                    'summary': entry.get('summary', entry.get('description', 'No description available')),
                    'published': entry.get('published', ''),
                    'source': feed.feed.get('title', 'Unknown Source'),
                    'timestamp': time.mktime(entry.get('published_parsed', time.localtime())),
                    'image': image_url
                }
                all_items.append(item)
                
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
            continue
    
    # Sort by timestamp (newest first)
    all_items.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return all_items


def get_cached_feeds() -> List[Dict]:
    """
    Get cached RSS feeds or fetch new ones if cache is expired.
    
    Returns:
        List of news items
    """
    current_time = time.time()
    
    if (current_time - feed_cache['last_update']) > feed_cache['cache_duration']:
        logger.info("Cache expired, fetching new feeds...")
        feed_cache['items'] = parse_rss_feeds()
        feed_cache['last_update'] = current_time
    
    return feed_cache['items']


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
    """Force refresh of RSS feeds."""
    try:
        feed_cache['items'] = parse_rss_feeds()
        feed_cache['last_update'] = time.time()
        return jsonify({
            'success': True,
            'message': 'Feeds refreshed successfully',
            'count': len(feed_cache['items'])
        })
    except Exception as e:
        logger.error(f"Error refreshing feeds: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Pre-load feeds on startup
    logger.info("Starting Tech News RSS Slideshow...")
    logger.info("Pre-loading RSS feeds...")
    get_cached_feeds()
    
    # Run the Flask app
    # Use host='0.0.0.0' to make it accessible on the network
    app.run(host='0.0.0.0', port=5000, debug=False)

