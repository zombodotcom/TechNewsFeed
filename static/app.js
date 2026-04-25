/* =============================================================
   Northwoods Tech News Wall
   3-zone digital signage for a 40" 1080p TV
   ============================================================= */

// ---- Config (injected by server into #appConfig) ----
const APP_CONFIG = JSON.parse(
    document.getElementById('appConfig').textContent
);

// ---- State ----
let storyPool = [];           // Combined & shuffled news + scam tips
let featuredIndex = 0;        // Current featured story index in pool
let sidebarOffset = 0;        // Current sidebar window offset
let featuredTimer = null;
let sidebarTimer = null;
let progressTimer = null;

const FEATURED_DURATION = 30000;     // 30s for news
const FEATURED_SCAM_DURATION = 35000; // 35s for scam tips
const SIDEBAR_DURATION = 25000;       // 25s
const SIDEBAR_COUNT = 3;
const AUTO_REFRESH_MS = 30 * 60 * 1000; // 30 min

// Badge color map
const BADGE_COLORS = {
    'TECH NEWS': '#D4A843',
    'TECH TIP': '#4A7C59',
    'SECURITY': '#2D5A3D',
    'CONSUMER ALERT': '#C45C4A',
    'TECH & SCIENCE': '#D4A843',
    'SCAM ALERT': '#C45C4A',
};

// Category icons (SVG paths) for placeholders
const CATEGORY_ICONS = {
    'TECH NEWS': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="placeholder-icon"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    'SECURITY': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="placeholder-icon"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    'CONSUMER ALERT': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="placeholder-icon"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    'TECH & SCIENCE': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="placeholder-icon"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>',
};
// Default icon for unknown categories
const DEFAULT_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="placeholder-icon"><path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V9a2 2 0 012-2h2a2 2 0 012 2v9a2 2 0 01-2 2h-2z"/></svg>';

// ---- Utility ----
function decodeEntities(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.innerHTML = text;
    return d.textContent || d.innerText || '';
}

function escapeHtml(text) {
    if (!text) return '';
    // Decode HTML entities first (RSS feeds contain &#8217; etc), then re-escape safely
    const decoded = decodeEntities(text);
    const d = document.createElement('div');
    d.textContent = decoded;
    return d.innerHTML;
}

function cleanHtml(html) {
    if (!html) return '';
    const d = document.createElement('div');
    d.innerHTML = html;
    let text = d.textContent || d.innerText || '';
    if (text.length > 800) text = text.substring(0, 800) + '...';
    return text;
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    try {
        const then = new Date(dateStr);
        const now = new Date();
        const diffMs = now - then;
        const mins = Math.floor(diffMs / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return mins + 'm ago';
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return hrs + 'h ago';
        const days = Math.floor(hrs / 24);
        if (days === 1) return 'Yesterday';
        if (days < 7) return days + 'd ago';
        return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch (e) {
        return '';
    }
}

function getCategoryIcon(badge) {
    return CATEGORY_ICONS[badge] || DEFAULT_ICON;
}

// ---- Auto-shrink long headlines ----
function shrinkToFit(el, minPx) {
    // If text is overflowing (clamped), step the font size down until it fits
    var size = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollHeight > el.clientHeight && size > minPx) {
        size -= 1;
        el.style.fontSize = size + 'px';
    }
}

// ---- Data Fetching ----
async function fetchFeeds(retryCount) {
    retryCount = retryCount || 0;
    try {
        setLoadingText('Loading tech news...');
        const [feedsRes, scamRes] = await Promise.all([
            fetch('/api/feeds'),
            fetch('/api/scam-tips'),
        ]);
        const feedsData = await feedsRes.json();
        const scamData = await scamRes.json();

        let newsItems = [];
        let scamItems = [];

        if (feedsData.success && feedsData.items && feedsData.items.length > 0) {
            newsItems = feedsData.items;
        }
        if (scamData.success && scamData.items && scamData.items.length > 0) {
            scamItems = scamData.items;
        }

        if (newsItems.length === 0 && scamItems.length === 0) {
            if (retryCount < 10) {
                setLoadingText('Waiting for feeds...');
                await delay(1000);
                return fetchFeeds(retryCount + 1);
            }
            showNoData();
            return;
        }

        // Preload images
        setLoadingText('Loading images...');
        await preloadImages([...newsItems, ...scamItems]);

        // Combine and shuffle
        storyPool = shuffleByCategory(newsItems, scamItems);
        console.log('Story pool ready:', storyPool.length, 'items');

        // Reset indices
        featuredIndex = 0;
        sidebarOffset = 0;

        // Render
        renderFeatured(storyPool[featuredIndex]);
        renderSidebar(getSidebarItems());
        hideLoading();

        // Start timer (sidebar advances together with featured now)
        startFeaturedTimer();
    } catch (err) {
        console.error('Fetch error:', err);
        if (retryCount < 5) {
            await delay(1000);
            return fetchFeeds(retryCount + 1);
        }
        showNoData();
    }
}

function delay(ms) {
    return new Promise(function(r) { setTimeout(r, ms); });
}

// ---- No-Data / Error State ----
function showNoData() {
    var overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;
    overlay.classList.remove('hidden');
    overlay.innerHTML =
        '<img src="/static/northwoods-icon.svg" alt="" class="loading-icon">' +
        '<div class="loading-text">News loading, check back soon</div>' +
        '<div class="loading-subtext">' + escapeHtml(APP_CONFIG.business_name) +
        ' &middot; ' + escapeHtml(APP_CONFIG.phone) + '</div>';
}

// ---- Image Preloading ----
async function preloadImages(items) {
    const promises = items.map(function(item) {
        if (!item.image) return Promise.resolve();
        return new Promise(function(resolve) {
            const img = new Image();
            img.onload = resolve;
            img.onerror = function() {
                item._imageFailed = true;
                resolve();
            };
            img.src = item.image;
        });
    });
    await Promise.all(promises);
}

// ---- Shuffle by Category ----
// Interleave categories so you don't get 5 security articles in a row.
// Scam tips appear roughly every 5th-6th item.
function shuffleByCategory(newsItems, scamItems) {
    // Group news by category
    const buckets = {};
    newsItems.forEach(function(item) {
        const cat = item.badge || item.category || 'OTHER';
        if (!buckets[cat]) buckets[cat] = [];
        buckets[cat].push(item);
    });

    // Shuffle within each bucket
    Object.keys(buckets).forEach(function(key) {
        shuffleArray(buckets[key]);
    });

    // Round-robin interleave news items
    const categoryKeys = Object.keys(buckets);
    shuffleArray(categoryKeys);
    const interleaved = [];
    let emptied = 0;
    while (emptied < categoryKeys.length) {
        emptied = 0;
        for (let i = 0; i < categoryKeys.length; i++) {
            const bucket = buckets[categoryKeys[i]];
            if (bucket.length > 0) {
                interleaved.push(bucket.shift());
            } else {
                emptied++;
            }
        }
    }

    // Distribute scam tips evenly across the entire feed so they're
    // scattered, not clumped at the end. Pre-compute slot positions
    // by even spacing with a small random jitter so consecutive
    // rotations don't show tips in the exact same slots.
    shuffleArray(scamItems);
    const total = interleaved.length + scamItems.length;
    const scamSlots = new Set();
    if (scamItems.length > 0) {
        const gap = total / scamItems.length;
        for (let i = 0; i < scamItems.length; i++) {
            const base = (i + 0.5) * gap;
            const jitter = (Math.random() - 0.5) * gap * 0.4;
            let slot = Math.max(0, Math.min(total - 1, Math.floor(base + jitter)));
            // Resolve collisions by walking forward
            while (scamSlots.has(slot) && slot < total - 1) slot++;
            scamSlots.add(slot);
        }
    }

    const result = [];
    let newsIdx = 0;
    let scamIdx = 0;
    for (let i = 0; i < total; i++) {
        if (scamSlots.has(i) && scamIdx < scamItems.length) {
            result.push(scamItems[scamIdx++]);
        } else if (newsIdx < interleaved.length) {
            result.push(interleaved[newsIdx++]);
        } else if (scamIdx < scamItems.length) {
            result.push(scamItems[scamIdx++]);
        }
    }

    return result;
}

function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        const tmp = arr[i];
        arr[i] = arr[j];
        arr[j] = tmp;
    }
}

// ---- Sidebar = preview of next upcoming items ----
// Always shows the next SIDEBAR_COUNT items in rotation order, so the
// leftmost sidebar item is what becomes featured next when right-arrow
// is pressed (or the timer fires).
function getSidebarItems() {
    const items = [];
    if (!storyPool.length) return items;
    for (let i = 1; i <= SIDEBAR_COUNT; i++) {
        items.push(storyPool[(featuredIndex + i) % storyPool.length]);
    }
    return items;
}

// ---- Render Featured ----
function renderFeatured(item) {
    const zone = document.getElementById('featuredZone');
    const isScam = item.type === 'scam';
    const hasImage = item.image && !item._imageFailed;

    // Build card
    const card = document.createElement('div');
    let cardClass = 'featured-card';
    if (isScam) cardClass += ' scam-card';
    if (!hasImage) cardClass += ' no-image';
    card.className = cardClass;

    if (isScam) {
        card.innerHTML = buildScamFeatured(item, hasImage);
    } else {
        card.innerHTML = buildNewsFeatured(item, hasImage);
    }

    // Add progress bar
    const progress = document.createElement('div');
    progress.className = 'featured-progress';
    progress.id = 'featuredProgress';
    card.appendChild(progress);

    // Crossfade: deactivate old, activate new
    const oldCard = zone.querySelector('.featured-card.active');
    if (oldCard) {
        oldCard.classList.remove('active');
        // Remove old card after transition
        setTimeout(function() {
            if (oldCard.parentNode) oldCard.parentNode.removeChild(oldCard);
        }, 1100);
    }

    zone.appendChild(card);
    // Force reflow for transition
    void card.offsetWidth;
    card.classList.add('active');

    // Auto-shrink headline if it overflows
    if (!isScam) {
        var h = card.querySelector('.featured-headline');
        if (h) shrinkToFit(h, 11);
        var s = card.querySelector('.featured-summary');
        if (s) shrinkToFit(s, 10);
    }

    // Start progress bar animation
    startProgressBar(isScam ? FEATURED_SCAM_DURATION : FEATURED_DURATION);
}

function buildNewsFeatured(item, hasImage) {
    const badgeColor = BADGE_COLORS[item.badge] || BADGE_COLORS[item.category] || '#D4A843';
    const summary = cleanHtml(item.summary || '');
    const time = timeAgo(item.published);
    const source = escapeHtml(item.source || 'Unknown');
    const badge = item.badge || item.category || '';

    let imageHtml = '';
    if (hasImage) {
        imageHtml = '<div class="featured-image-wrap">' +
            '<img src="' + escapeHtml(item.image) + '" alt="" loading="eager">' +
            '</div>';
    } else if (item.image === undefined || item.image === null || item._imageFailed) {
        // Show placeholder with category icon
        imageHtml = '<div class="featured-image-wrap placeholder">' +
            getCategoryIcon(badge) +
            '</div>';
    }

    return '<div class="featured-inner">' +
        '<div class="featured-text">' +
            '<span class="featured-badge" style="background:' + badgeColor + '">' + escapeHtml(badge) + '</span>' +
            '<h1 class="featured-headline">' + escapeHtml(item.title || 'No Title') + '</h1>' +
            '<div class="featured-meta">' +
                '<span>' + source + '</span>' +
                (time ? '<span class="dot"></span><span>' + time + '</span>' : '') +
            '</div>' +
            '<p class="featured-summary">' + escapeHtml(summary) + '</p>' +
        '</div>' +
        imageHtml +
    '</div>';
}

function buildScamFeatured(item, hasImage) {
    let imageHtml = '';
    if (hasImage) {
        imageHtml = '<div class="scam-image-wrap">' +
            '<img src="' + escapeHtml(item.image) + '" alt="" loading="eager">' +
            '</div>';
    }

    return '<div class="scam-header">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>' +
            '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>' +
        '</svg>' +
        '<span>SCAM ALERT</span>' +
    '</div>' +
    '<div class="scam-inner">' +
        imageHtml +
        '<div class="scam-text">' +
            '<h1 class="scam-headline">' + escapeHtml(item.headline || item.title || '') + '</h1>' +
            '<p class="scam-action">' + escapeHtml(item.action || '') + '</p>' +
        '</div>' +
    '</div>';
}

// ---- Progress Bar ----
function startProgressBar(duration) {
    if (progressTimer) cancelAnimationFrame(progressTimer);
    const bar = document.getElementById('featuredProgress');
    if (!bar) return;
    const start = performance.now();
    function tick(now) {
        const elapsed = now - start;
        const pct = Math.min((elapsed / duration) * 100, 100);
        bar.style.width = pct + '%';
        if (pct < 100) {
            progressTimer = requestAnimationFrame(tick);
        }
    }
    bar.style.width = '0%';
    bar.style.transition = 'none';
    progressTimer = requestAnimationFrame(tick);
}

// ---- Render Sidebar ----
function renderSidebar(items) {
    const zone = document.getElementById('sidebarZone');

    // If first render (empty), just populate
    if (zone.children.length === 0) {
        items.forEach(function(item) {
            zone.appendChild(buildSidebarCard(item));
        });
        return;
    }

    // Slide-up animation: mark old cards as sliding out, then replace
    const oldCards = Array.from(zone.children);
    oldCards.forEach(function(c) {
        c.classList.add('sliding-out');
    });

    setTimeout(function() {
        zone.innerHTML = '';
        items.forEach(function(item) {
            const card = buildSidebarCard(item);
            card.classList.add('sliding-in');
            zone.appendChild(card);
            // Force reflow then remove sliding-in
            void card.offsetWidth;
            card.classList.remove('sliding-in');
        });
    }, 400);
}

function buildSidebarCard(item) {
    const isScam = item.type === 'scam';
    const hasImage = item.image && !item._imageFailed;
    const badge = isScam ? 'SCAM ALERT' : (item.badge || item.category || '');
    const badgeColor = BADGE_COLORS[badge] || '#D4A843';
    const headline = isScam ? (item.headline || '') : (item.title || '');
    const source = isScam ? 'Scam Tip' : (item.source || '');

    const card = document.createElement('div');
    card.className = 'sidebar-card' + (hasImage ? '' : ' no-image');

    let thumbHtml = '';
    if (hasImage) {
        thumbHtml = '<div class="sidebar-thumb">' +
            '<img src="' + escapeHtml(item.image) + '" alt="" loading="lazy">' +
            '</div>';
    } else if (!isScam && (item._imageFailed || item.image === null || item.image === undefined)) {
        // Show placeholder for news items without images
        thumbHtml = '<div class="sidebar-thumb placeholder">' +
            getCategoryIcon(badge) +
            '</div>';
        card.className = 'sidebar-card'; // Remove no-image since we have placeholder
    }

    card.innerHTML = thumbHtml +
        '<div class="sidebar-body">' +
            '<span class="sidebar-badge" style="background:' + badgeColor + '">' + escapeHtml(badge) + '</span>' +
            '<span class="sidebar-headline">' + escapeHtml(headline) + '</span>' +
            '<span class="sidebar-source">' + escapeHtml(source) + '</span>' +
        '</div>';

    return card;
}

// ---- Timers ----
function startFeaturedTimer() {
    if (featuredTimer) clearTimeout(featuredTimer);

    function advance() {
        featuredIndex = (featuredIndex + 1) % storyPool.length;
        renderFeatured(storyPool[featuredIndex]);
        // Also update sidebar to maintain deduplication
        renderSidebar(getSidebarItems());
        scheduleFeatured();
    }

    function scheduleFeatured() {
        const item = storyPool[featuredIndex];
        const dur = (item && item.type === 'scam') ? FEATURED_SCAM_DURATION : FEATURED_DURATION;
        featuredTimer = setTimeout(advance, dur);
    }

    scheduleFeatured();
}

// Sidebar no longer rotates independently — it tracks featured.

// ---- Featured Navigation (prev/next) ----
function nextFeatured() {
    if (featuredTimer) clearTimeout(featuredTimer);
    if (progressTimer) cancelAnimationFrame(progressTimer);
    featuredIndex = (featuredIndex + 1) % storyPool.length;
    renderFeatured(storyPool[featuredIndex]);
    renderSidebar(getSidebarItems());
    startFeaturedTimer();
}

function prevFeatured() {
    if (featuredTimer) clearTimeout(featuredTimer);
    if (progressTimer) cancelAnimationFrame(progressTimer);
    featuredIndex = (featuredIndex - 1 + storyPool.length) % storyPool.length;
    renderFeatured(storyPool[featuredIndex]);
    renderSidebar(getSidebarItems());
    startFeaturedTimer();
}

// ---- Business Hours ----
function updateBusinessHours() {
    const now = new Date();
    const day = now.getDay(); // 0=Sun ... 6=Sat
    const currentMins = now.getHours() * 60 + now.getMinutes();

    // Parse open/close times from config
    const openParts = APP_CONFIG.open_time.split(':');
    const closeParts = APP_CONFIG.close_time.split(':');
    const openTime = parseInt(openParts[0]) * 60 + parseInt(openParts[1]);
    const closeTime = parseInt(closeParts[0]) * 60 + parseInt(closeParts[1]);
    const openDays = APP_CONFIG.open_days;

    const isOpenDay = openDays.indexOf(day) !== -1;
    const isOpen = isOpenDay && currentMins >= openTime && currentMins < closeTime;

    const dot = document.getElementById('statusDot');
    const label = document.getElementById('statusLabel');
    const countdown = document.getElementById('barCountdown');
    const countdownDivider = document.getElementById('countdownDivider');

    if (isOpen) {
        dot.className = 'status-dot open';
        label.className = 'bar-status-text open';
        label.textContent = 'Open Now';
        countdown.textContent = '';
        countdownDivider.style.display = 'none';
    } else {
        dot.className = 'status-dot closed';
        label.className = 'bar-status-text closed';
        label.textContent = 'Closed';
        countdownDivider.style.display = '';

        // Compute next opening
        let nextOpen = new Date(now);
        if (!isOpenDay) {
            // Find next open day
            for (let offset = 1; offset <= 7; offset++) {
                var candidateDay = (day + offset) % 7;
                if (openDays.indexOf(candidateDay) !== -1) {
                    nextOpen.setDate(now.getDate() + offset);
                    break;
                }
            }
            nextOpen.setHours(parseInt(openParts[0]), parseInt(openParts[1]), 0, 0);
        } else {
            if (currentMins < openTime) {
                nextOpen.setHours(parseInt(openParts[0]), parseInt(openParts[1]), 0, 0);
            } else {
                // After close - find next open day
                for (let offset = 1; offset <= 7; offset++) {
                    var candidateDay2 = (day + offset) % 7;
                    if (openDays.indexOf(candidateDay2) !== -1) {
                        nextOpen.setDate(now.getDate() + offset);
                        break;
                    }
                }
                nextOpen.setHours(parseInt(openParts[0]), parseInt(openParts[1]), 0, 0);
            }
        }

        const diff = nextOpen - now;
        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);

        let text = 'Opens in ';
        if (d > 0) text += d + 'd ' + h + 'h';
        else if (h > 0) text += h + 'h ' + m + 'm';
        else text += m + 'm';

        countdown.textContent = text;
    }
}

// ---- Clock ----
function updateClock() {
    const el = document.getElementById('barDatetime');
    if (!el) return;
    const now = new Date();
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const dayName = dayNames[now.getDay()];
    const month = monthNames[now.getMonth()];
    const date = now.getDate();
    let hours = now.getHours();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    if (hours === 0) hours = 12;
    const mins = now.getMinutes().toString().padStart(2, '0');
    el.textContent = dayName + ' ' + month + ' ' + date + ', ' + hours + ':' + mins + ' ' + ampm;
}

// ---- Loading / Error UI ----
function setLoadingText(txt) {
    const el = document.getElementById('loadingText');
    if (el) el.textContent = txt;
}

function hideLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.add('hidden');
}

// ---- Keyboard Controls ----
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight' || e.key === ' ') {
        nextFeatured();
    } else if (e.key === 'ArrowLeft') {
        prevFeatured();
    } else if (e.key === 'r' || e.key === 'R') {
        fetch('/api/refresh').then(function() {
            return fetchFeeds();
        }).catch(console.error);
    }
});

// ---- Init ----
updateBusinessHours();
updateClock();
setInterval(updateBusinessHours, 60000);
setInterval(updateClock, 60000);

// Auto-refresh every 30 min
setInterval(function() {
    console.log('Auto-refresh triggered');
    fetchFeeds();
}, AUTO_REFRESH_MS);

// Full page reload at 5:05 AM daily to pick up fresh server state
(function scheduleDailyReload() {
    var now = new Date();
    var target = new Date(now);
    target.setHours(5, 5, 0, 0);
    if (now >= target) target.setDate(target.getDate() + 1);
    var ms = target - now;
    console.log('Page reload scheduled in ' + (ms/3600000).toFixed(1) + ' hours');
    setTimeout(function() { location.reload(); }, ms);
})();

// Go!
fetchFeeds();
