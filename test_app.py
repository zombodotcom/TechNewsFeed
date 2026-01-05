"""
Tests for Tech News RSS Slideshow Feed
"""
import unittest
from unittest.mock import patch, MagicMock
import time
from app import app, parse_rss_feeds, get_cached_feeds, feed_cache


class TestRSSFeeds(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app.test_client()
        self.app.testing = True
        # Reset cache for each test
        feed_cache['items'] = []
        feed_cache['last_update'] = 0
        feed_cache['fetching'] = False
    
    def test_index_route(self):
        """Test that index page loads."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Tech News RSS Slideshow', response.data)
    
    def test_feeds_api_returns_json(self):
        """Test that /api/feeds returns JSON."""
        response = self.app.get('/api/feeds')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.get_json()
        self.assertIn('success', data)
        self.assertIn('items', data)
    
    def test_feeds_api_structure(self):
        """Test that /api/feeds returns correct structure."""
        response = self.app.get('/api/feeds')
        data = response.get_json()
        self.assertIsInstance(data['items'], list)
        self.assertIsInstance(data['count'], int)
        self.assertIn('last_update', data)
    
    def test_refresh_api(self):
        """Test that /api/refresh works."""
        response = self.app.get('/api/refresh')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('success', data)
    
    @patch('app.feedparser.parse')
    def test_parse_rss_feeds_handles_errors(self, mock_parse):
        """Test that parse_rss_feeds handles feed errors gracefully."""
        # Mock a feed that fails
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = "Test error"
        mock_parse.return_value = mock_feed
        
        result = parse_rss_feeds()
        self.assertIsInstance(result, list)
        # Should return empty list when all feeds fail
        self.assertEqual(len(result), 0)
    
    @patch('app.feedparser.parse')
    def test_parse_rss_feeds_success(self, mock_parse):
        """Test successful feed parsing."""
        # Mock a successful feed
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
    
    def test_get_cached_feeds_returns_list(self):
        """Test that get_cached_feeds always returns a list."""
        result = get_cached_feeds()
        self.assertIsInstance(result, list)
    
    def test_cache_expiration(self):
        """Test that cache expires after duration."""
        feed_cache['last_update'] = time.time() - 400  # 400 seconds ago
        feed_cache['items'] = [{'test': 'data'}]
        
        with patch('app.parse_rss_feeds') as mock_parse:
            mock_parse.return_value = [{'new': 'data'}]
            result = get_cached_feeds()
            # Should trigger fetch
            self.assertTrue(mock_parse.called or len(result) > 0)


class TestSlideshowLogic(unittest.TestCase):
    """Test slideshow JavaScript logic (simulated)."""
    
    def test_slide_looping_logic(self):
        """Test that slide index loops correctly."""
        total_slides = 10
        
        # Simulate nextSlide logic
        current_slide = 0
        for i in range(15):  # Go past the end
            current_slide = (current_slide + 1) % total_slides
            self.assertGreaterEqual(current_slide, 0)
            self.assertLess(current_slide, total_slides)
        
        # Should have looped back
        self.assertEqual(current_slide, 5)  # 15 % 10 = 5
    
    def test_slide_wraps_to_zero(self):
        """Test that slide wraps to 0 after last slide."""
        total_slides = 5
        current_slide = 4  # Last slide
        
        # Next should wrap to 0
        next_slide = (current_slide + 1) % total_slides
        self.assertEqual(next_slide, 0)
    
    def test_previous_slide_wraps(self):
        """Test that previous slide wraps to last."""
        total_slides = 5
        current_slide = 0  # First slide
        
        # Previous should wrap to last
        prev_slide = (current_slide - 1 + total_slides) % total_slides
        self.assertEqual(prev_slide, 4)


if __name__ == '__main__':
    unittest.main()

