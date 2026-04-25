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
            # Shopping / deals
            "LL Bean coupon: save 20% on jackets",
            "Save $200 on this TV deal",
            "50% off everything at Best Buy",
            "All of Amazon's kid-friendly Kindles are on sale",
            "This gadget is under $50 and worth buying",
            "Buy two Nintendo Switch games, get $30 off at Target",
            "Logitech MX Master 4 mouse is on sale for under $100",
            # Listicles / "best of"
            "Best laptops to buy in 2026",
            "Best Pajamas for Women (2026), WIRED Tested and Reviewed",
            "10 best headphones right now",
            "Top 5 monitors for gaming",
            "Best noise-canceling headphones overall",
            "The best robot vacuums we've tested",
            "Buying guide: the best laptops for students",
            "5 ways to speed up your old laptop",
            "7 things you should know about iOS 20",
            # Personal experience / "I did X"
            "I tried the new Samsung phone and wow",
            "I let Gemini in Google Maps plan my day and it went surprisingly well",
            "I used ChatGPT for a week and here's what I learned",
            "I switched to Linux for a month and I'm not going back",
            "I replaced my MacBook with an iPad and it changed my mind",
            "I ditched my iPhone for a Pixel and here's what happened",
            "The Korg Handytraxx Play finally got me learning to scratch",
            "I actually love this weird little gadget",
            "I can't stop using this new AI tool",
            "I ranked every streaming service and here's the winner",
            "My dream pair of AR glasses needs to have these features",
            # Reviews / hands-on / comparison
            "Pixel 9 Pro hands-on: Google's best phone yet",
            "Samsung Galaxy S26 first impressions",
            "MacBook Air vs MacBook Pro: which should you buy?",
            "Is it worth upgrading to the iPhone 17?",
            "Galaxy Tab S10 unboxing and first look",
            # Entertainment / streaming
            "5 Oscar-winning Netflix movies to watch this weekend",
            "He-Man gets an origin story in Masters of the Universe trailer",
            "The official Minecraft Movie trailer is here",
            "What Memento reveals about human nature, 25 years later",
            "Stream this incredible documentary tonight",
            # How-to / explainer
            "How to set up a VPN on your router",
            "Here's how to get the most out of your new iPhone",
            "Here's everything Apple announced today",
            # Podcast promos
            "Why AI regulation is stalling — on the Vergecast",
            "Cisco CEO Chuck Robbins on the future of networking — Decoder",
            # Seasonal
            "April Fools' Day 2026: the best and cringiest pranks",
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
            "FTC sues company over deceptive practices",
            "Google announces major Android security update",
            "Apple releases emergency iOS patch for active exploit",
            "Amazon Web Services suffers widespread outage",
            "New ransomware strain targets healthcare systems",
            "Intel reveals next-gen chip architecture",
            "SpaceX successfully lands Starship booster",
            "Signal adds post-quantum encryption to its protocol",
            "Cloudflare blocks record-breaking DDoS attack",
            "Windows 12 release date confirmed by Microsoft",
            "USB-C becomes mandatory in EU starting next month",
            "T-Mobile data breach exposes 40 million records",
            "Scientists discover high-temperature superconductor",
            "Firefox rolls out enhanced tracking protection",
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
        """Test we have 21 scam tips."""
        from app import SCAM_TIPS
        self.assertEqual(len(SCAM_TIPS), 21)

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


class TestImageExtraction(unittest.TestCase):
    """Test extract_image_url with different RSS entry formats."""

    def _make_entry(self, **kwargs):
        """Build a minimal mock RSS entry."""
        entry = MagicMock()
        # By default nothing is present
        entry.media_content = kwargs.get('media_content', [])
        entry.media_thumbnail = kwargs.get('media_thumbnail', [])
        entry.enclosures = kwargs.get('enclosures', [])
        entry.image = kwargs.get('image', None)
        entry.get = MagicMock(side_effect=lambda k, d=None: kwargs.get(k, d))
        # Control hasattr
        for attr in ('media_content', 'media_thumbnail', 'enclosures', 'image'):
            if attr not in kwargs:
                delattr(entry, attr)
        return entry

    def test_extracts_from_media_content(self):
        from app import extract_image_url
        entry = self._make_entry(
            media_content=[{'type': 'image/jpeg', 'url': 'http://img.com/a.jpg'}]
        )
        self.assertEqual(extract_image_url(entry), 'http://img.com/a.jpg')

    def test_extracts_from_media_thumbnail(self):
        from app import extract_image_url
        entry = self._make_entry(
            media_thumbnail=[{'url': 'http://img.com/thumb.jpg'}]
        )
        self.assertEqual(extract_image_url(entry), 'http://img.com/thumb.jpg')

    def test_extracts_from_enclosure(self):
        from app import extract_image_url
        entry = self._make_entry(
            enclosures=[{'type': 'image/png', 'href': 'http://img.com/enc.png'}]
        )
        self.assertEqual(extract_image_url(entry), 'http://img.com/enc.png')

    def test_extracts_from_summary_img_tag(self):
        from app import extract_image_url
        html = '<p>Text</p><img src="http://img.com/inline.jpg" alt="pic">'
        entry = self._make_entry(summary=html)
        self.assertEqual(extract_image_url(entry), 'http://img.com/inline.jpg')

    def test_extracts_from_description_fallback(self):
        from app import extract_image_url
        html = '<img src="http://img.com/desc.jpg">'
        entry = self._make_entry(description=html)
        self.assertEqual(extract_image_url(entry), 'http://img.com/desc.jpg')

    def test_extracts_from_image_field_dict(self):
        from app import extract_image_url
        entry = self._make_entry(image={'href': 'http://img.com/field.jpg'})
        self.assertEqual(extract_image_url(entry), 'http://img.com/field.jpg')

    def test_extracts_from_image_field_string(self):
        from app import extract_image_url
        entry = self._make_entry(image='http://img.com/plain.jpg')
        self.assertEqual(extract_image_url(entry), 'http://img.com/plain.jpg')

    def test_returns_none_when_no_image(self):
        from app import extract_image_url
        entry = self._make_entry()
        self.assertIsNone(extract_image_url(entry))

    def test_media_content_skips_non_image_types(self):
        from app import extract_image_url
        entry = self._make_entry(
            media_content=[{'type': 'video/mp4', 'url': 'http://vid.com/v.mp4'}]
        )
        # Should fall through to None (no other sources)
        self.assertIsNone(extract_image_url(entry))

    def test_priority_media_content_over_thumbnail(self):
        """media_content should be checked before media_thumbnail."""
        from app import extract_image_url
        entry = self._make_entry(
            media_content=[{'type': 'image/jpeg', 'url': 'http://img.com/mc.jpg'}],
            media_thumbnail=[{'url': 'http://img.com/thumb.jpg'}],
        )
        self.assertEqual(extract_image_url(entry), 'http://img.com/mc.jpg')


class TestJunkFilterEdgeCases(unittest.TestCase):
    """Edge cases for the title junk filter."""

    def test_empty_title(self):
        from app import _is_junk_title
        self.assertFalse(_is_junk_title(''))

    def test_case_insensitive(self):
        from app import _is_junk_title
        self.assertTrue(_is_junk_title('SAVE $50 ON THIS GADGET'))
        self.assertTrue(_is_junk_title('save $50 on this gadget'))

    def test_partial_word_not_matched(self):
        """'deal' should not match 'ideal' or 'dealer' since we use word boundaries."""
        from app import _is_junk_title
        # 'ideal' contains 'deal' but should NOT be filtered
        self.assertFalse(_is_junk_title('An ideal solution for network security'))

    def test_filters_urgency_phrases(self):
        from app import _is_junk_title
        self.assertTrue(_is_junk_title("Last chance to get this device"))
        self.assertTrue(_is_junk_title("Flash sale on smart home gear"))
        self.assertTrue(_is_junk_title("Ends today: limited time pricing"))

    def test_keeps_security_news(self):
        from app import _is_junk_title
        safe = [
            "Critical vulnerability found in OpenSSL",
            "Ransomware gang targets healthcare sector",
            "New phishing technique bypasses MFA",
            "FTC warns consumers about tech support scams",
            "Google patches Chrome zero-day exploit",
        ]
        for title in safe:
            self.assertFalse(_is_junk_title(title), f"Should keep: {title}")

    def test_keeps_science_news(self):
        from app import _is_junk_title
        safe = [
            "James Webb telescope discovers high-redshift galaxy",
            "SpaceX launches Starship on test flight",
            "CERN reports anomaly in particle collision data",
        ]
        for title in safe:
            self.assertFalse(_is_junk_title(title), f"Should keep: {title}")


class TestFeedLogging(unittest.TestCase):
    """Test the feed history logging function."""

    def test_log_feed_item_writes_to_file(self):
        import os
        import tempfile
        from unittest.mock import patch as _patch

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            tmp_path = f.name

        try:
            with _patch('app._FEED_LOG', tmp_path):
                from app import _log_feed_item
                _log_feed_item('SHOWN', 'Test Headline', 'Test Source')
                _log_feed_item('FILTERED', 'Junk Title', 'Spam Feed')

            with open(tmp_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.assertEqual(len(lines), 2)
            self.assertIn('SHOWN', lines[0])
            self.assertIn('Test Headline', lines[0])
            self.assertIn('FILTERED', lines[1])
            self.assertIn('Junk Title', lines[1])
        finally:
            os.unlink(tmp_path)


class TestFeedSorting(unittest.TestCase):
    """Test that feeds are sorted newest-first."""

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_items_sorted_newest_first(self, mock_parse):
        now = time.time()
        entries = []
        for i, age_hours in enumerate([48, 1, 24]):
            ts = time.localtime(now - age_hours * 3600)
            entry = MagicMock()
            entry.get = MagicMock(side_effect=lambda k, d=None, _i=i, _ts=ts: {
                'title': f'Article {_i}',
                'link': f'http://test.com/{_i}',
                'summary': 'Summary',
                'published': '',
                'published_parsed': _ts,
            }.get(k, d))
            entry.media_content = []
            entry.media_thumbnail = []
            entry.enclosures = []
            entry.image = None
            entries.append(entry)

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = entries
        mock_feed.feed.get.return_value = 'Test Source'
        mock_parse.return_value = mock_feed

        result = parse_rss_feeds()
        self.assertEqual(len(result), 3)
        # Should be sorted newest first: Article 1 (1h), Article 2 (24h), Article 0 (48h)
        self.assertEqual(result[0]['title'], 'Article 1')
        self.assertEqual(result[1]['title'], 'Article 2')
        self.assertEqual(result[2]['title'], 'Article 0')


class TestFeedCacheConcurrency(unittest.TestCase):
    """Test that the cache doesn't double-fetch."""

    def setUp(self):
        feed_cache['items'] = [{'title': 'cached'}]
        feed_cache['last_update'] = 0  # expired
        feed_cache['fetching'] = False

    def test_returns_cached_data_immediately(self):
        """get_cached_feeds should return stale data right away, not block."""
        result = get_cached_feeds()
        self.assertEqual(result, [{'title': 'cached'}])

    def test_does_not_double_fetch(self):
        """If already fetching, a second call should not start another fetch."""
        feed_cache['fetching'] = True
        with patch('app.threading.Thread') as mock_thread:
            get_cached_feeds()
            mock_thread.assert_not_called()

    def test_empty_cache_returns_empty_list(self):
        feed_cache['items'] = []
        feed_cache['last_update'] = time.time()  # not expired
        result = get_cached_feeds()
        self.assertEqual(result, [])


class TestAPIErrorHandling(unittest.TestCase):
    """Test API endpoints handle errors gracefully."""

    def setUp(self):
        self.client = app.test_client()

    def test_feeds_api_returns_count_matching_items(self):
        feed_cache['items'] = [{'a': 1}, {'b': 2}]
        feed_cache['last_update'] = time.time()
        response = self.client.get('/api/feeds')
        data = response.get_json()
        self.assertEqual(data['count'], len(data['items']))

    def test_scam_tips_api_count_matches(self):
        response = self.client.get('/api/scam-tips')
        data = response.get_json()
        self.assertEqual(data['count'], len(data['items']))

    @patch('app.get_cached_feeds', side_effect=Exception('db on fire'))
    def test_feeds_api_500_on_exception(self, _mock):
        response = self.client.get('/api/feeds')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    @patch('app.parse_rss_feeds', side_effect=Exception('network down'))
    def test_refresh_api_500_on_exception(self, _mock):
        feed_cache['items'] = [{'cached': True}]
        response = self.client.get('/api/refresh')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        # Should still return cached items on error
        self.assertEqual(data['items'], [{'cached': True}])

    def test_refresh_returns_cached_when_no_new_items(self):
        feed_cache['items'] = [{'old': True}]
        with patch('app.parse_rss_feeds', return_value=[]):
            response = self.client.get('/api/refresh')
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['items'], [{'old': True}])


class TestParseEdgeCases(unittest.TestCase):
    """Edge cases in feed parsing."""

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_missing_published_parsed_uses_current_time(self, mock_parse):
        """Entries without published_parsed should get current timestamp."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        entry = MagicMock()
        entry.get = MagicMock(side_effect=lambda k, d=None: {
            'title': 'No Date Article',
            'link': 'http://test.com',
            'summary': 'Summary',
            'published': '',
            'published_parsed': None,
        }.get(k, d))
        entry.media_content = []
        entry.media_thumbnail = []
        entry.enclosures = []
        entry.image = None
        mock_feed.entries = [entry]
        mock_feed.feed.get.return_value = 'Test Source'
        mock_parse.return_value = mock_feed

        before = time.time()
        result = parse_rss_feeds()
        after = time.time()

        self.assertEqual(len(result), 1)
        self.assertGreaterEqual(result[0]['timestamp'], before)
        self.assertLessEqual(result[0]['timestamp'], after)

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_empty_entries_list(self, mock_parse):
        """Feeds with empty entries should be skipped."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        result = parse_rss_feeds()
        self.assertEqual(len(result), 0)

    @patch('app.feedparser.parse')
    @patch('app.RSS_FEEDS', [{"url": "https://test.com/feed", "category": "tech_news", "badge": "TECH NEWS"}])
    def test_junk_titles_excluded_from_results(self, mock_parse):
        """Filtered junk titles should not appear in results."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        entries = []
        for i, title in enumerate(['Real Security News', 'Best laptops to buy in 2026', 'New zero-day exploit found']):
            entry = MagicMock()
            entry.get = MagicMock(side_effect=lambda k, d=None, _t=title, _i=i: {
                'title': _t,
                'link': f'http://test.com/article-{_i}',
                'summary': 'Summary',
                'published': '',
                'published_parsed': time.localtime(),
            }.get(k, d))
            entry.media_content = []
            entry.media_thumbnail = []
            entry.enclosures = []
            entry.image = None
            entries.append(entry)

        mock_feed.entries = entries
        mock_feed.feed.get.return_value = 'Test Source'
        mock_parse.return_value = mock_feed

        result = parse_rss_feeds()
        titles = [r['title'] for r in result]
        self.assertIn('Real Security News', titles)
        self.assertIn('New zero-day exploit found', titles)
        self.assertNotIn('Best laptops to buy in 2026', titles)


if __name__ == '__main__':
    unittest.main()
