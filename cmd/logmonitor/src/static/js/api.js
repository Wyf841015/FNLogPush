// ========== API 请求模块 ==========

// 请求缓存
const apiCache = {
    data: {},
    timestamps: {},
    TTL: 5000, // 缓存 5 秒

    get(key) {
        const timestamp = this.timestamps[key];
        if (timestamp && Date.now() - timestamp < this.TTL) {
            return this.data[key];
        }
        return null;
    },

    set(key, value) {
        this.data[key] = value;
        this.timestamps[key] = Date.now();
    },

    clear() {
        this.data = {};
        this.timestamps = {};
    }
};

// 正在进行的请求（防止重复）
const pendingRequests = new Map();

// 统一的Fetch请求函数
async function apiFetch(url, options = {}) {
    // 请求去重
    if (pendingRequests.has(url)) {
        console.log(`请求去重: ${url}`);
        return pendingRequests.get(url);
    }

    const defaultOptions = {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    };
    const mergedOptions = { ...defaultOptions, ...options };

    const fetchPromise = fetch(url, mergedOptions);
    pendingRequests.set(url, fetchPromise);

    try {
        const response = await fetchPromise;
        return response;
    } finally {
        pendingRequests.delete(url);
    }
}

// 带缓存的 API 请求
async function apiFetchCached(url, options = {}) {
    const cacheKey = url + JSON.stringify(options.body || '');

    // 检查缓存
    const cached = apiCache.get(cacheKey);
    if (cached) {
        return cached;
    }

    const response = await apiFetch(url, options);
    const data = await response.clone().json();
    apiCache.set(cacheKey, data);
    return data;
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}
