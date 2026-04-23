/**
 * Crypto Alpha Dashboard — Frontend Logic
 * Live feed with filters, auto-refresh, and real-time updates.
 */

const API = {
    feed: '/api/feed',
    stats: '/api/stats',
    filters: '/api/filters',
    botStatus: '/api/bot/status',
    botToggle: '/api/bot/toggle',
};

const state = {
    source: 'all',
    category: null,
    group: null,
    crossoverOnly: false,
    items: [],
    latestId: null,
    offset: 0,
    limit: 50,
    refreshInterval: null,
    filterData: null,
    stats: null,
    isBotActive: true,
    theme: localStorage.getItem('alpha-theme') || 'dark',
};

// Apply theme immediately to avoid flash
document.documentElement.setAttribute('data-theme', state.theme);

// ======== INIT ========
document.addEventListener('DOMContentLoaded', async () => {
    setupSidebar();
    setupSourceTabs();
    setupCrossoverFilter();
    setupRefreshButton();
    setupLoadMore();
    setupBotController();
    setupTheme();

    await loadFilters();
    await loadStats();
    await loadFeed();
    await updateBotStatus();

    // Auto-refresh every 30 seconds
    state.refreshInterval = setInterval(() => {
        pollNewItems();
        updateBotStatus();
    }, 30000);
});

// ======== SIDEBAR (Mobile) ========
function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('menuToggle');
    const close = document.getElementById('sidebarClose');

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.id = 'sidebarOverlay';
    document.body.appendChild(overlay);

    toggle.addEventListener('click', () => {
        sidebar.classList.add('open');
        overlay.classList.add('active');
    });

    const closeSidebar = () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    };

    close.addEventListener('click', closeSidebar);
    overlay.addEventListener('click', closeSidebar);
}

// ======== SOURCE TABS ========
function setupSourceTabs() {
    document.querySelectorAll('.source-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.source-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.source = tab.dataset.source;
            state.offset = 0;
            state.items = [];
            loadFeed();
        });
    });
}

// ======== CROSSOVER FILTER ========
function setupCrossoverFilter() {
    const cb = document.getElementById('filterCrossover');
    cb.addEventListener('change', () => {
        state.crossoverOnly = cb.checked;
        renderFeed();
    });
}

// ======== REFRESH ========
function setupRefreshButton() {
    const btn = document.getElementById('refreshBtn');
    btn.addEventListener('click', async () => {
        btn.classList.add('spinning');
        await pollNewItems();
        await loadStats();
        setTimeout(() => btn.classList.remove('spinning'), 600);
    });
}

// ======== LOAD MORE ========
function setupLoadMore() {
    document.getElementById('loadMoreBtn').addEventListener('click', async () => {
        state.offset += state.limit;
        const params = buildParams();
        params.offset = state.offset;
        const data = await fetchJSON(API.feed, params);
        if (data && data.items.length > 0) {
            state.items.push(...data.items);
            renderFeed();
            if (data.items.length < state.limit) {
                document.getElementById('loadMoreWrap').style.display = 'none';
            }
        } else {
            document.getElementById('loadMoreWrap').style.display = 'none';
        }
    });
}

// ======== LOAD FILTERS ========
async function loadFilters() {
    const data = await fetchJSON(API.filters);
    if (!data) return;
    state.filterData = data;

    const catContainer = document.getElementById('categoryFilters');
    catContainer.innerHTML = '';
    data.categories.forEach(cat => {
        catContainer.appendChild(createFilterItem(cat, 'category'));
    });

    const groupContainer = document.getElementById('groupFilters');
    groupContainer.innerHTML = '';
    data.groups.forEach(g => {
        groupContainer.appendChild(createFilterItem(g, 'group'));
    });
}

function createFilterItem(value, type) {
    const label = document.createElement('label');
    label.className = 'filter-item';

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'filter-checkbox';
    cb.dataset.type = type;
    cb.dataset.value = value;

    cb.addEventListener('change', () => {
        if (cb.checked) {
            // Uncheck others in same type for single-select behavior
            document.querySelectorAll(`.filter-checkbox[data-type="${type}"]`).forEach(other => {
                if (other !== cb) other.checked = false;
            });
            state[type] = value;
        } else {
            state[type] = null;
        }
        state.offset = 0;
        state.items = [];
        loadFeed();
    });

    const span = document.createElement('span');
    span.className = 'filter-label';
    span.textContent = value;

    label.appendChild(cb);
    label.appendChild(span);
    return label;
}

// ======== LOAD FEED ========
async function loadFeed() {
    showLoading(true);
    const params = buildParams();
    const data = await fetchJSON(API.feed, params);

    showLoading(false);

    if (!data || data.items.length === 0) {
        if (state.items.length === 0) {
            showEmpty(true);
        }
        document.getElementById('loadMoreWrap').style.display = 'none';
        return;
    }

    showEmpty(false);
    state.items = data.items;
    if (data.items.length > 0) {
        state.latestId = data.items[0].id;
    }
    renderFeed();

    document.getElementById('loadMoreWrap').style.display =
        data.items.length >= state.limit ? '' : 'none';
}

// ======== POLL NEW ITEMS ========
async function pollNewItems() {
    if (!state.latestId) return;

    const params = buildParams();
    params.since_id = state.latestId;
    params.offset = 0; // Always check the very beginning when polling for new
    const data = await fetchJSON(API.feed, params);

    if (data && data.items.length > 0) {
        // Prepend new items
        state.items = [...data.items, ...state.items];
        state.latestId = data.items[0].id;
        renderFeed(data.items.length);
        showEmpty(false);

        // Flash the live indicator
        const indicator = document.getElementById('liveIndicator');
        indicator.style.background = 'rgba(0, 206, 201, 0.2)';
        setTimeout(() => indicator.style.background = '', 1500);
    }
    // Also update stats
    loadStats();
}

// ======== LOAD STATS ========
async function loadStats() {
    const data = await fetchJSON(API.stats);
    if (!data) return;
    state.stats = data;

    document.getElementById('statTotal').textContent = formatNum(data.total || 0);
    document.getElementById('statToday').textContent = formatNum(data.today || 0);
    document.getElementById('statTwitter').textContent = formatNum((data.by_source || {}).twitter || 0);
    document.getElementById('statReddit').textContent = formatNum((data.by_source || {}).reddit || 0);
    document.getElementById('statCrossovers').textContent = formatNum(data.crossovers || 0);

    // Update filter counts
    if (data.by_category) {
        document.querySelectorAll('.filter-checkbox[data-type="category"]').forEach(cb => {
            const count = data.by_category[cb.dataset.value] || 0;
            const existing = cb.parentElement.querySelector('.filter-count');
            if (existing) existing.remove();
            if (count > 0) {
                const badge = document.createElement('span');
                badge.className = 'filter-count';
                badge.textContent = count;
                cb.parentElement.appendChild(badge);
            }
        });
    }

    if (data.by_group) {
        document.querySelectorAll('.filter-checkbox[data-type="group"]').forEach(cb => {
            const count = data.by_group[cb.dataset.value] || 0;
            const existing = cb.parentElement.querySelector('.filter-count');
            if (existing) existing.remove();
            if (count > 0) {
                const badge = document.createElement('span');
                badge.className = 'filter-count';
                badge.textContent = count;
                cb.parentElement.appendChild(badge);
            }
        });
    }
}

// ======== RENDER FEED ========
function renderFeed(newCount = 0) {
    const list = document.getElementById('feedList');
    let items = state.items;

    // Apply crossover filter client-side
    if (state.crossoverOnly) {
        items = items.filter(i => i.priority === 'crossover');
    }

    list.innerHTML = '';
    items.forEach((item, idx) => {
        const card = createFeedCard(item, idx < newCount);
        list.appendChild(card);
    });
}

function createFeedCard(item, isNew) {
    const card = document.createElement('div');
    card.className = 'feed-card';
    if (item.priority === 'crossover') card.classList.add('crossover');
    if (isNew) card.classList.add('new-item');

    // Header
    const header = document.createElement('div');
    header.className = 'card-header';

    // Source badge
    const srcBadge = document.createElement('span');
    srcBadge.className = `source-badge ${item.source || 'twitter'}`;
    srcBadge.textContent = (item.source || 'twitter').toUpperCase();
    header.appendChild(srcBadge);

    // Category badge
    if (item.category) {
        const catBadge = document.createElement('span');
        catBadge.className = 'category-badge';
        catBadge.textContent = item.category;
        header.appendChild(catBadge);
    }

    // Group badge
    if (item.group_name) {
        const grpBadge = document.createElement('span');
        grpBadge.className = 'group-badge';
        grpBadge.textContent = item.group_name;
        header.appendChild(grpBadge);
    }

    // Priority badge
    if (item.priority === 'crossover') {
        const priBadge = document.createElement('span');
        priBadge.className = 'priority-badge';
        priBadge.textContent = '🔥 CROSSOVER';
        header.appendChild(priBadge);
    }

    // Time
    const time = document.createElement('span');
    time.className = 'card-time';
    time.textContent = formatTime(item.created_at);
    header.appendChild(time);

    card.appendChild(header);

    // Parse extra info for badges (like followers)
    let extra = {};
    if (item.extra_json) {
        try { extra = JSON.parse(item.extra_json); } catch(e) {}
    }

    // Author & Followers
    if (item.author) {
        const authorLine = document.createElement('div');
        authorLine.className = 'card-author-line';
        
        const author = document.createElement('span');
        author.className = 'card-author';
        author.textContent = item.author;
        authorLine.appendChild(author);

        if (extra.followers) {
            const folBadge = document.createElement('span');
            folBadge.className = 'follower-badge';
            folBadge.innerHTML = `<i class="fol-icon">👤</i> ${formatNum(extra.followers)} Followers`;
            authorLine.appendChild(folBadge);
        }
        
        card.appendChild(authorLine);
    }

    // Title (for Reddit)
    if (item.title) {
        const title = document.createElement('div');
        title.className = 'card-title';
        title.textContent = item.title;
        card.appendChild(title);
    }

    // Body
    if (item.body) {
        const body = document.createElement('div');
        body.className = 'card-body';
        body.textContent = item.body.length > 500 ? item.body.substring(0, 500) + '...' : item.body;
        card.appendChild(body);
    }

    // Footer
    if (item.url) {
        const footer = document.createElement('div');
        footer.className = 'card-footer';

        const link = document.createElement('a');
        link.className = 'card-link';
        link.href = item.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = item.source === 'reddit' ? 'View on Reddit →' : 'View on 𝕏 →';
        footer.appendChild(link);

        card.appendChild(footer);
    }

    return card;
}

// ======== HELPERS ========
function buildParams() {
    const params = { limit: state.limit, offset: state.offset };
    if (state.source && state.source !== 'all') params.source = state.source;
    if (state.category) params.category = state.category;
    if (state.group) params.group_name = state.group;
    return params;
}

async function fetchJSON(url, params = {}) {
    try {
        // Add cache buster
        params._t = Date.now();
        const qs = new URLSearchParams(params).toString();
        const resp = await fetch(qs ? `${url}?${qs}` : url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (e) {
        console.error('API Error:', e);
        return null;
    }
}

function showLoading(show) {
    document.getElementById('feedLoading').style.display = show ? '' : 'none';
}

function showEmpty(show) {
    document.getElementById('feedEmpty').style.display = show ? '' : 'none';
}

function formatNum(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    // SQLite returns 'YYYY-MM-DD HH:MM:SS'. 
    // We convert it to ISO 'YYYY-MM-DDTHH:MM:SSZ' to force UTC parsing.
    const utcStr = dateStr.replace(' ', 'T') + 'Z';
    const d = new Date(utcStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ======== BOT CONTROLLER ========
function setupBotController() {
    const btn = document.getElementById('botToggleBtn');
    btn.addEventListener('click', async () => {
        const oldText = btn.textContent;
        btn.textContent = 'Processing...';
        btn.disabled = true;

        try {
            const resp = await fetch(API.botToggle, { method: 'POST' });
            if (resp.ok) {
                const data = await resp.json();
                state.isBotActive = data.is_active;
                renderBotUI();
            }
        } catch (e) {
            console.error('Toggle error:', e);
            btn.textContent = oldText;
        } finally {
            btn.disabled = false;
        }
    });
}

async function updateBotStatus() {
    const data = await fetchJSON(API.botStatus);
    if (data) {
        state.isBotActive = data.is_active;
        renderBotUI();
    }
}

function renderBotUI() {
    const dot = document.getElementById('botStatusDot');
    const text = document.getElementById('botStatusText');
    const btn = document.getElementById('botToggleBtn');

    if (state.isBotActive) {
        dot.className = 'status-dot online';
        text.textContent = 'Online';
        text.style.color = 'var(--success)';
        btn.textContent = 'Stop Engine';
        btn.className = 'bot-toggle-btn active';
    } else {
        dot.className = 'status-dot paused';
        text.textContent = 'Paused';
        text.style.color = 'var(--danger)';
        btn.textContent = 'Start Engine';
        btn.className = 'bot-toggle-btn inactive';
    }
}

// ======== THEME TOGGLE ========
function setupTheme() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    btn.addEventListener('click', () => {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', state.theme);
        localStorage.setItem('alpha-theme', state.theme);
        
        // Update button icon/feedback if needed
        btn.style.transform = 'scale(1.2)';
        setTimeout(() => btn.style.transform = '', 200);
    });
}
