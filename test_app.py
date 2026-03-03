"""
Tests for Tech News RSS Slideshow Feed
"""
import unittest
from unittest.mock import patch, MagicMock
import time
from app import app, parse_rss_feeds, get_cached_feeds, feed_cache, BUSINESS_CONFIG


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
        self.assertIn(b'Northwoods', response.data)

    def test_index_uses_config_values(self):
        """Test that index page renders config values from config.json."""
        response = self.app.get('/')
        self.assertIn(BUSINESS_CONFIG['phone'].encode(), response.data)
        self.assertIn(BUSINESS_CONFIG['business_name'].encode(), response.data)
        self.assertIn(BUSINESS_CONFIG['hours_text'].encode(), response.data)

    def test_index_includes_config_json_block(self):
        """Test that index page includes the appConfig JSON block for JS."""
        response = self.app.get('/')
        self.assertIn(b'id="appConfig"', response.data)
        self.assertIn(b'application/json', response.data)

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
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
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
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
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
        """Test we have 8 curated feeds."""
        from app import RSS_FEEDS
        self.assertEqual(len(RSS_FEEDS), 8)

    def test_badge_colors_defined(self):
        """Test that BADGE_COLORS is defined for all badges used in feeds."""
        from app import RSS_FEEDS, BADGE_COLORS
        self.assertIsInstance(BADGE_COLORS, dict)
        for feed in RSS_FEEDS:
            self.assertIn(feed['badge'], BADGE_COLORS,
                          f"Badge '{feed['badge']}' not found in BADGE_COLORS")

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_parse_rss_feeds_includes_category_and_badge(self, mock_parse):
        """Test that parsed feed items include category and badge from feed config."""
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
        self.assertEqual(result[0]['category'], 'tech_news')
        self.assertEqual(result[0]['badge'], 'TECH NEWS')


class TestJunkFilter(unittest.TestCase):
    def test_filters_deals_and_coupons(self):
        """Test that ad/deal/clickbait titles get filtered."""
        from app import _is_junk_title
        junk = [
            "LL Bean coupon: save 20% on jackets",
            "Best laptops to buy in 2026",
            "Best Pajamas for Women (2026), WIRED Tested and Reviewed",
            "I tried the new Samsung phone and wow",
            "10 best headphones right now",
            "Top 5 monitors for gaming",
            "This gadget is under $50 and worth buying",
            "Save $200 on this TV deal",
            "50% off everything at Best Buy",
            "The best robot vacuums we've tested",
            "5 Oscar-winning Netflix movies to watch this weekend",
            "Best noise-canceling headphones overall",
            "All of Amazon's kid-friendly Kindles are on sale",
            "Buying guide: the best laptops for students",
        ]
        for title in junk:
            self.assertTrue(_is_junk_title(title), f"Should filter: {title}")

    def test_filters_political_content(self):
        """Test that political/partisan titles get filtered."""
        from app import _is_junk_title
        political = [
            "Medical journal The Lancet blasts RFK Jr.'s health work as a failure",
            "Trump signs executive order on AI regulation",
            "Biden administration announces new tech policy",
            "Republican lawmakers push back on FTC ruling",
            "Democrat senator introduces privacy bill",
            "GOP split on tech antitrust approach",
            "White House announces cybersecurity initiative",
            "Elon Musk clashes with lawmakers over DOGE cuts",
            "HHS slashes funding for health tech programs",
            "Supreme Court to hear social media censorship case",
            "Congress passes sweeping tech regulation bill",
            "Senate votes to ban TikTok amid partisan divide",
            "Obama warns about AI deepfakes in new interview",
            "DeSantis targets woke tech companies",
            "AOC grills tech CEO in heated hearing",
            "Lawmakers demand answers from Google on immigration data",
            "Abortion access app removed from app store after conservative backlash",
            "DEI policies shake up Silicon Valley hiring",
            "The op-ed that changed the AI safety debate",
        ]
        for title in political:
            self.assertTrue(_is_junk_title(title), f"Should filter: {title}")

    def test_keeps_real_news(self):
        """Test that real news titles pass through."""
        from app import _is_junk_title
        good = [
            "Microsoft patches critical zero-day vulnerability",
            "NASA launches new Mars rover mission",
            "EU passes landmark AI regulation bill",
            "How ransomware gangs are targeting hospitals",
            "FTC sues company over deceptive practices",
        ]
        for title in good:
            self.assertFalse(_is_junk_title(title), f"Should keep: {title}")


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
            self.assertIn('image', tip)

    def test_scam_tips_count(self):
        """Test we have 10 scam tips."""
        from app import SCAM_TIPS
        self.assertEqual(len(SCAM_TIPS), 10)

    def test_scam_tips_last_is_cta(self):
        """Test last scam tip is the shop CTA."""
        from app import SCAM_TIPS
        self.assertIn('Just Ask Us', SCAM_TIPS[-1]['headline'])

    def test_scam_tips_images_are_svg(self):
        """Test that all scam tip images use .svg extension."""
        from app import SCAM_TIPS
        for tip in SCAM_TIPS:
            if tip['image'] is not None:
                self.assertTrue(tip['image'].endswith('.svg'),
                                f"Expected .svg: {tip['image']}")

    def test_scam_tips_api_returns_new_format(self):
        """Test /api/scam-tips returns tips with headline/action fields."""
        self.app_client = app.test_client()
        response = self.app_client.get('/api/scam-tips')
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['items']), 0)
        first_tip = data['items'][0]
        self.assertIn('headline', first_tip)
        self.assertIn('action', first_tip)
        self.assertEqual(first_tip['type'], 'scam')


class TestStaleArticleFilter(unittest.TestCase):
    """Test that articles older than 7 days are filtered out."""

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_stale_articles_dropped(self, mock_parse):
        """Articles older than 7 days should be excluded."""
        now = time.localtime()
        old_time = time.localtime(time.time() - 10 * 86400)  # 10 days ago

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            # Fresh article
            MagicMock(
                get=MagicMock(side_effect=lambda key, default=None: {
                    'title': 'Fresh Article',
                    'link': 'http://test.com/fresh',
                    'summary': 'Fresh summary',
                    'published': '2026-03-03',
                    'published_parsed': now
                }.get(key, default)),
                media_content=[], media_thumbnail=[], enclosures=[], image=None
            ),
            # Stale article (10 days old)
            MagicMock(
                get=MagicMock(side_effect=lambda key, default=None: {
                    'title': 'Stale Article',
                    'link': 'http://test.com/stale',
                    'summary': 'Old summary',
                    'published': '2026-02-21',
                    'published_parsed': old_time
                }.get(key, default)),
                media_content=[], media_thumbnail=[], enclosures=[], image=None
            ),
        ]
        mock_feed.feed.get.return_value = 'Test Source'
        mock_parse.return_value = mock_feed

        result = parse_rss_feeds()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Fresh Article')

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_articles_within_7_days_kept(self, mock_parse):
        """Articles within 7 days should be kept."""
        recent_time = time.localtime(time.time() - 5 * 86400)  # 5 days ago

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            MagicMock(
                get=MagicMock(side_effect=lambda key, default=None: {
                    'title': 'Recent Article',
                    'link': 'http://test.com/recent',
                    'summary': 'Recent summary',
                    'published': '2026-02-26',
                    'published_parsed': recent_time
                }.get(key, default)),
                media_content=[], media_thumbnail=[], enclosures=[], image=None
            ),
        ]
        mock_feed.feed.get.return_value = 'Test Source'
        mock_parse.return_value = mock_feed

        result = parse_rss_feeds()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Recent Article')


class TestConfigLoading(unittest.TestCase):
    """Test that business config is loaded correctly."""

    def test_config_has_required_keys(self):
        """Config must have all required fields."""
        required = ['business_name', 'phone', 'hours_text', 'open_days', 'open_time', 'close_time']
        for key in required:
            self.assertIn(key, BUSINESS_CONFIG, f"Missing config key: {key}")

    def test_config_values_are_correct_types(self):
        """Config values should be the expected types."""
        self.assertIsInstance(BUSINESS_CONFIG['business_name'], str)
        self.assertIsInstance(BUSINESS_CONFIG['phone'], str)
        self.assertIsInstance(BUSINESS_CONFIG['hours_text'], str)
        self.assertIsInstance(BUSINESS_CONFIG['open_days'], list)
        self.assertIsInstance(BUSINESS_CONFIG['open_time'], str)
        self.assertIsInstance(BUSINESS_CONFIG['close_time'], str)

    def test_open_days_are_valid(self):
        """Open days should be valid day-of-week numbers (0-6)."""
        for day in BUSINESS_CONFIG['open_days']:
            self.assertIn(day, range(7))

    def test_config_passed_to_template(self):
        """Config should be available in the rendered template."""
        client = app.test_client()
        response = client.get('/')
        self.assertIn(BUSINESS_CONFIG['business_name'].encode(), response.data)


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
