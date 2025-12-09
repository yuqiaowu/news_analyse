// Language State
let currentLang = 'CN'; // Default to Chinese

const TRANSLATIONS = {
    'CN': {
        'global_title': '🌍 AI 全球市场洞察',
        'news_title': '📰 叙事 vs 现实 (Narrative vs Reality)',
        'refresh_text': '刷新',
        'last_updated': '最后更新: ',
        'next_update': '下次更新: ',
        'loading': '正在使用 Gemini 2.5 Flash 分析全球市场数据...',
        'fed_title': '🏦 美联储利率预期 (30天期货)',
        'fed_rate': '隐含利率',
        'fed_zone': '区间',
        'fed_price': '价格',
        'fed_change': '5日变动',
        'japan_title': '💴 日本宏观 (美元/日元)',
        'japan_price': '价格',
        'japan_zone': '区间',
        'japan_change': '5日变动',
        'liq_title': '💧 全球流动性监控',
        'metrics': {
            'RSI': 'RSI',
            'Fund': '费率',
            'OI': '持仓'
        }
    },
    'EN': {
        'global_title': '🌍 AI Global Market Insight',
        'news_title': '📰 Narrative vs Reality Check',
        'refresh_text': 'Refresh',
        'last_updated': 'Last Updated: ',
        'next_update': 'Next Update: ',
        'loading': 'Analyzing Global Market Data with Gemini 2.5 Flash...',
        'fed_title': '🏦 Fed Rate Expectations (30-Day Futures)',
        'fed_rate': 'Implied Rate',
        'fed_zone': 'Zone',
        'fed_price': 'Price',
        'fed_change': '5D Change',
        'japan_title': '💴 Japan Macro (USD/JPY)',
        'japan_price': 'Price',
        'japan_zone': 'Zone',
        'japan_change': '5D Change',
        'liq_title': '💧 Global Liquidity Monitor',
        'metrics': {
            'RSI': 'RSI',
            'Fund': 'Fund',
            'OI': 'OI'
        }
    }
};

const BADGE_TRANSLATIONS = {
    'IMPULSE': '冲击 (Impulse)',
    'PRICED IN': '已计价 (Priced In)',
    'DISTRIBUTION': '派发 (Distribution)',
    'DIVERGENCE': '背离 (Divergence)',
    'NEUTRAL': '中性 (Neutral)'
};

function toggleLanguage() {
    currentLang = currentLang === 'CN' ? 'EN' : 'CN';
    updateStaticText();

    // Re-render data if available
    if (window.latestData) {
        renderDashboard(window.latestData);
    }

    // Update button
    const langIcon = document.getElementById('lang-icon');
    const langText = document.getElementById('lang-text');
    if (currentLang === 'CN') {
        langIcon.textContent = '🇺🇸';
        langText.textContent = 'EN'; // Show what clicking will do
    } else {
        langIcon.textContent = '🇨🇳';
        langText.textContent = 'CN';
    }
}

function updateStaticText() {
    const t = TRANSLATIONS[currentLang];
    document.getElementById('global-title').textContent = t.global_title;
    document.getElementById('news-title').textContent = t.news_title;
    document.getElementById('refresh-text').textContent = t.refresh_text;
    document.getElementById('loading-text').textContent = t.loading;

    // Fed Rate Labels
    document.getElementById('fed-title').textContent = t.fed_title;
    document.getElementById('fed-rate-label').textContent = t.fed_rate;
    document.getElementById('fed-zone-label').textContent = t.fed_zone;
    document.getElementById('fed-price-label').textContent = t.fed_price;
    document.getElementById('fed-change-label').textContent = t.fed_change;

    // Japan Macro Labels
    document.getElementById('japan-title').textContent = t.japan_title;
    document.getElementById('japan-price-label').textContent = t.japan_price;
    document.getElementById('japan-zone-label').textContent = t.japan_zone;
    document.getElementById('japan-change-label').textContent = t.japan_change;

    // Liquidity Monitor Title
    document.getElementById('liq-title').textContent = t.liq_title;

    // Metrics Labelstamp label part (keep time)
    const lastUpdated = document.getElementById('last-updated');
    const timePart = lastUpdated.textContent.split(': ')[1] || '';
    lastUpdated.textContent = `${t.last_updated}${timePart}`;

    updateTimerDisplay();
}

async function fetchData(forceRefresh = false) {
    const dashboard = document.getElementById('dashboard');
    const loading = document.getElementById('loading');
    const refreshBtn = document.getElementById('refresh-btn');
    const lastUpdated = document.getElementById('last-updated');
    const t = TRANSLATIONS[currentLang];

    // Show loading (but keep dashboard visible if it has content)
    loading.style.display = 'flex';
    refreshBtn.disabled = true;

    // Clear existing timer during fetch
    if (timerInterval) clearInterval(timerInterval);

    try {
        // Fetch static JSON file directly
        const url = forceRefresh ? `latest_analysis.json?t=${new Date().getTime()}` : 'latest_analysis.json';
        const response = await fetch(url);
        const data = await response.json();

        // Store for language switching
        window.latestData = data;

        renderDashboard(data);

        // Update timestamp
        const ts = data.timestamp ? new Date(data.timestamp) : new Date();
        lastUpdated.textContent = `${t.last_updated}${ts.toLocaleTimeString()}`;

        // Calculate remaining time based on timestamp
        const now = new Date();
        const elapsedSeconds = Math.floor((now - ts) / 1000);
        let remaining = REFRESH_INTERVAL - elapsedSeconds;

        // If expired (negative remaining), set to 0
        if (remaining < 0) remaining = 0;

        // If expired, don't loop immediately. Wait 30s then retry.
        if (remaining === 0) {
            console.log("Data expired, scheduling retry in 30s...");
            startTimer(30);
        } else {
            // Start timer with calculated remaining time
            startTimer(remaining);
        }

    } catch (error) {
        console.error('Error fetching analysis:', error);
        document.getElementById('loading').textContent = `数据加载失败: ${error.message}. 请稍后再试。`;
        // If error, restart timer with default interval to allow retry later
        startTimer(REFRESH_INTERVAL);
    } finally {
        loading.style.display = 'none';
        document.getElementById('global-summary').style.display = 'block';
        // news-analysis display is handled in renderDashboard
        dashboard.style.display = 'grid';
        refreshBtn.disabled = false;
    }
}

function renderDashboard(data) {
    const dashboard = document.getElementById('dashboard');
    const summaryContent = document.getElementById('global-summary-text');
    const newsList = document.getElementById('news-list');
    const t = TRANSLATIONS[currentLang];

    // Render Global Summary
    const summaryText = currentLang === 'CN' ? data.global_summary_cn : data.global_summary_en;
    // Fallback if new fields missing (old cache)
    const finalSummary = summaryText || data.global_summary;

    if (typeof marked !== 'undefined') {
        summaryContent.innerHTML = marked.parse(finalSummary);
    } else {
        summaryContent.textContent = finalSummary; // Fallback to raw text
        console.warn('Marked.js not loaded, displaying raw markdown.');
    }

    // Render Fed Rate
    const fedContainer = document.getElementById('fed-rate-container');
    if (data.fed_futures && !data.fed_futures.error) {
        fedContainer.style.display = 'block';
        const fed = data.fed_futures;
        document.getElementById('fed-rate').textContent = `${fed.implied_rate}%`;
        document.getElementById('fed-rate').textContent = `${fed.implied_rate}%`;

        // Zone Translation
        let zoneText = fed.zone || 'N/A';
        if (currentLang === 'CN') {
            if (zoneText.includes('Restrictive')) zoneText = '限制性 (高位)';
            else if (zoneText.includes('Accommodative')) zoneText = '宽松 (低位)';
            else if (zoneText.includes('Neutral')) zoneText = '中性 (适中)';
        }
        document.getElementById('fed-zone').textContent = zoneText;

        document.getElementById('fed-price').textContent = fed.price;

        // Change Label
        let changeLabel = '';
        if (currentLang === 'CN') {
            if (fed.trend.includes('Hawkish')) changeLabel = ' (鹰派)';
            else if (fed.trend.includes('Dovish')) changeLabel = ' (鸽派)';
            else changeLabel = ' (中性)';
        } else {
            if (fed.trend.includes('Hawkish')) changeLabel = ' (Hawkish)';
            else if (fed.trend.includes('Dovish')) changeLabel = ' (Dovish)';
            else changeLabel = ' (Neutral)';
        }
        document.getElementById('fed-change').textContent = `${fed.change_5d_bps} bps${changeLabel}`;

        const trendEl = document.getElementById('fed-trend');
        let trendText = fed.trend || 'Neutral';

        // Simple translation for trend
        if (currentLang === 'CN') {
            if (trendText.includes('Hawkish')) trendText = '鹰派 (预期上升)';
            else if (trendText.includes('Dovish')) trendText = '鸽派 (预期下降)';
            else if (trendText.includes('Neutral')) trendText = '中性 (预期稳定)';
        }

        trendEl.textContent = trendText;

        // Color coding
        if (trendText.includes('Hawkish') || trendText.includes('鹰派')) {
            trendEl.style.background = 'rgba(239, 68, 68, 0.2)';
            trendEl.style.color = '#f87171';
        } else if (trendText.includes('Dovish') || trendText.includes('鸽派')) {
            trendEl.style.background = 'rgba(34, 197, 94, 0.2)';
            trendEl.style.color = '#4ade80';
        } else {
            trendEl.style.background = 'rgba(59, 130, 246, 0.2)';
            trendEl.style.color = '#60a5fa';
        }
    } else {
        fedContainer.style.display = 'none';
    }

    // Render Japan Macro
    const japanContainer = document.getElementById('japan-macro-container');
    if (data.japan_macro && !data.japan_macro.error) {
        japanContainer.style.display = 'block';
        const jp = data.japan_macro;

        document.getElementById('japan-price').textContent = jp.price;

        let changeSuffix = '';
        if (currentLang === 'CN') {
            changeSuffix = jp.change_5d_pct < 0 ? ' (升值)' : ' (贬值)';
        }
        document.getElementById('japan-change').textContent = `${jp.change_5d_pct}%${changeSuffix}`;

        // Zone Translation
        let zoneText = jp.zone || 'N/A';
        if (currentLang === 'CN') {
            if (zoneText.includes('Weak Yen')) zoneText = '弱日元 (干预风险)';
            else if (zoneText.includes('Strong Yen')) zoneText = '强日元';
            else if (zoneText.includes('Neutral')) zoneText = '中性';
        }
        document.getElementById('japan-zone').textContent = zoneText;

        // Trend Translation & Color
        const trendEl = document.getElementById('japan-trend');
        let trendText = jp.trend || 'Neutral';

        if (currentLang === 'CN') {
            if (trendText.includes('Yen Strength')) trendText = '日元升值 (避险/利空)';
            else if (trendText.includes('Yen Weakness')) trendText = '日元贬值 (利好)';
            else trendText = '中性 (波动小)';
        }

        trendEl.textContent = trendText;

        // Color Coding (Yen Strength = Bad for Risk Assets)
        if (trendText.includes('Strength') || trendText.includes('升值')) {
            trendEl.style.background = 'rgba(239, 68, 68, 0.2)'; // Red
            trendEl.style.color = '#f87171';
        } else if (trendText.includes('Weakness') || trendText.includes('贬值')) {
            trendEl.style.background = 'rgba(34, 197, 94, 0.2)'; // Green
            trendEl.style.color = '#4ade80';
        } else {
            trendEl.style.background = 'rgba(59, 130, 246, 0.2)'; // Blue
            trendEl.style.color = '#60a5fa';
        }
    } else {
        japanContainer.style.display = 'none';
    }

    // Render Liquidity Monitor
    const liqContainer = document.getElementById('liquidity-monitor-container');
    if (data.liquidity_monitor && !data.liquidity_monitor.error) {
        liqContainer.style.display = 'block';
        const liq = data.liquidity_monitor;

        // Helper to render item
        const renderLiqItem = (key, prefix) => {
            const item = liq[key];
            if (!item) return;

            // Handle nulls
            const price = item.price !== null ? item.price : 'N/A';
            const change = item.change_5d_pct !== null ? item.change_5d_pct : null;

            document.getElementById(`${prefix}-price`).textContent = price;

            // Change Color
            const changeEl = document.getElementById(`${prefix}-change`);
            if (change !== null) {
                changeEl.textContent = `${change > 0 ? '+' : ''}${change}%`;
                changeEl.style.color = change > 0 ? '#f87171' : '#4ade80'; // Default
                if (key === 'dxy' || key === 'us10y' || key === 'vix') {
                    // For these, Up is usually Bad (Risk Off)
                    changeEl.style.color = change > 0 ? '#f87171' : '#4ade80';
                }
            } else {
                changeEl.textContent = '--';
                changeEl.style.color = '#94a3b8';
            }

            // Trend Translation
            const trendEl = document.getElementById(`${prefix}-trend`);
            let trendText = item.trend || 'Neutral';

            if (currentLang === 'CN') {
                // DXY
                if (trendText.includes('Stronger')) trendText = '美元走强 (利空)';
                else if (trendText.includes('Weaker')) trendText = '美元走弱 (利好)';
                // US10Y
                else if (trendText.includes('Critical High')) trendText = '极高危 (崩盘风险)';
                else if (trendText.includes('High')) trendText = '高位 (施压)';
                else if (trendText.includes('Low')) trendText = '低位 (支撑)';

                // Movement modifiers
                if (trendText.includes('Rising')) trendText += ' / 上升';
                else if (trendText.includes('Falling')) trendText += ' / 下降';

                // Special case for "Neutral Rising" -> "收益率上升"
                if (trendText.includes('Neutral') && trendText.includes('Rising')) trendText = '收益率上升 (施压)';
                else if (trendText.includes('Neutral') && trendText.includes('Falling')) trendText = '收益率下降 (喘息)';
                else if (trendText === 'Neutral') trendText = '收益率平稳';
                // VIX
                else if (trendText.includes('Extreme Panic')) trendText = '极端恐慌 (崩盘风险)';
                else if (trendText.includes('High Fear')) trendText = '高度恐慌 (避险)';
                else if (trendText.includes('Greed')) trendText = '贪婪 (利好)';

                // Movement modifiers
                if (trendText.includes('Rising')) trendText += ' / 升温';
                else if (trendText.includes('Subsiding')) trendText += ' / 消退';

                // Special case for "Neutral Subsiding" -> "恐慌消退"
                if (trendText.includes('Neutral') && trendText.includes('Subsiding')) trendText = '恐慌消退 (利好)';
                else if (trendText.includes('Neutral') && trendText.includes('Rising')) trendText = '恐慌升温 (警惕)';
                else if (trendText.includes('Calm')) trendText = '情绪平稳'; // Legacy support
                else if (trendText === 'Neutral') trendText = '情绪平稳';

                else if (trendText === 'Neutral') trendText = '中性';
            }
            trendEl.textContent = trendText;
        };

        renderLiqItem('dxy', 'dxy');
        renderLiqItem('us10y', 'us10y');
        renderLiqItem('vix', 'vix');

    } else {
        liqContainer.style.display = 'none';
    }

    // Render News Analysis
    if (data.news_analysis && data.news_analysis.length > 0) {
        document.getElementById('news-analysis').style.display = 'block';
        newsList.innerHTML = data.news_analysis.map(item => {
            let badgeClass = 'badge-neutral';
            const cls = item.classification.toUpperCase();
            if (cls === 'IMPULSE') badgeClass = 'badge-impulse';
            if (cls === 'PRICED IN') badgeClass = 'badge-priced-in';
            if (cls === 'DISTRIBUTION') badgeClass = 'badge-distribution';
            if (cls === 'DIVERGENCE') badgeClass = 'badge-divergence';

            // Title Translation (Fallback to 'title' if specific lang missing)
            const title = currentLang === 'CN' ? (item.title_cn || item.title) : (item.title_en || item.title);

            // Reason Translation
            const reason = currentLang === 'CN' ? (item.reason_cn || item.reason) : (item.reason_en || item.reason);

            // Badge Translation
            const badgeText = currentLang === 'CN' ? (BADGE_TRANSLATIONS[cls] || cls) : cls;

            return `
                <div class="news-analysis-item">
                    <div class="news-header">
                        <span class="news-title">${title}</span>
                        <span class="news-badge ${badgeClass}">${badgeText}</span>
                    </div>
                    <div class="news-reason">${reason}</div>
                </div>
            `;
        }).join('');
    } else {
        document.getElementById('news-analysis').style.display = 'none';
    }

    // Render Coins
    dashboard.innerHTML = ''; // Clear existing

    data.coins.forEach(coin => {
        const card = createCard(coin);
        dashboard.appendChild(card);
    });
}

function createCard(coin) {
    const { symbol, price, change_24h, rsi_4h, funding_rate, open_interest, sentiment, score } = coin;
    const t = TRANSLATIONS[currentLang];

    const comment = currentLang === 'CN' ? (coin.comment_cn || coin.comment) : (coin.comment_en || coin.comment);

    const sentimentClass = `sentiment-${sentiment.toLowerCase()}`;

    // Determine color for score bar
    let scoreColor = '#eab308'; // Neutral
    if (score >= 60) scoreColor = '#22c55e'; // Bullish
    if (score <= 40) scoreColor = '#ef4444'; // Bearish

    // Change color
    const changeColor = change_24h >= 0 ? '#22c55e' : '#ef4444';
    const changeSign = change_24h >= 0 ? '+' : '';

    // RSI Color
    let rsiColor = '#94a3b8';
    if (rsi_4h > 70) rsiColor = '#ef4444'; // Overbought
    if (rsi_4h < 30) rsiColor = '#22c55e'; // Oversold

    const card = document.createElement('div');
    card.className = 'card';

    // Format price
    const formattedPrice = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(price);

    card.innerHTML = `
        <div class="card-header">
            <div class="symbol-info">
                <h2>${symbol}</h2>
                <div class="price">
                    ${formattedPrice}
                    <span style="font-size: 0.8rem; color: ${changeColor}; margin-left: 5px;">
                        (${changeSign}${(change_24h || 0).toFixed(2)}%)
                    </span>
                </div>
            </div>
            <div class="sentiment-badge ${sentimentClass}">
                ${sentiment} (${score})
            </div>
        </div>
        
        <div class="metrics-grid" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; margin: 10px 0; font-size: 0.8rem; color: #cbd5e1;">
            <div title="RSI (4H)">${t.metrics.RSI}: <span style="color: ${rsiColor}">${(rsi_4h || 0).toFixed(1)}</span></div>
            <div title="Funding Rate">${t.metrics.Fund}: <span>${(funding_rate || 0).toFixed(4)}%</span></div>
            <div title="Open Interest">${t.metrics.OI}: <span>${((open_interest || 0) / 1000).toFixed(1)}k</span></div>
        </div>

        <div class="score-bar">
            <div class="score-fill" style="width: ${score}%; background-color: ${scoreColor};"></div>
        </div>

        <div class="analysis-content">
            ${comment}
        </div>
    `;

    return card;
}

// Auto-refresh settings
const REFRESH_INTERVAL = 4 * 60 * 60; // 4 hours in seconds
let countdown = REFRESH_INTERVAL;
let timerInterval;

function startTimer(duration) {
    clearInterval(timerInterval);

    // Set countdown to provided duration or default
    countdown = (typeof duration === 'number') ? duration : REFRESH_INTERVAL;

    updateTimerDisplay();

    timerInterval = setInterval(() => {
        if (countdown > 0) {
            countdown--;
            updateTimerDisplay();
        } else {
            clearInterval(timerInterval);
            fetchData(true); // Force refresh on timer expiry
        }
    }, 1000);
}

function updateTimerDisplay() {
    const nextUpdate = document.getElementById('next-update');
    const t = TRANSLATIONS[currentLang];

    if (nextUpdate) {
        // Format seconds to HH:MM:SS
        const h = Math.floor(countdown / 3600);
        const m = Math.floor((countdown % 3600) / 60);
        const s = countdown % 60;

        const hStr = h > 0 ? `${h}h ` : '';
        const mStr = m > 0 ? `${m}m ` : '';
        const sStr = `${s}s`;

        nextUpdate.textContent = `${t.next_update}${hStr}${mStr}${sStr}`;
    }
}

// Initial fetch (Use cache if available)
document.addEventListener('DOMContentLoaded', () => {
    // Refresh Button (Disabled for Static Deployment)
    // document.getElementById('refresh-btn').addEventListener('click', () => fetchAnalysis(true));

    // Initialize text
    updateStaticText();

    fetchData(false);
});
