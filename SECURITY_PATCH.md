# 安全补丁 - CSRF保护 + 安全响应头

本补丁为 log-monitor-fpk 添加安全增强功能。

## 1. 安全中间件 (security_middleware.py)

创建 `cmd/logmonitor/src/middleware/security_middleware.py`:

```python
"""
安全增强中间件
包含 CSRF 保护和响应头安全配置
"""
import os
import secrets
from functools import wraps
from flask import request, session, abort, make_response

# CSRF Token 配置
CSRF_TOKEN_NAME = 'csrf_token'
CSRF_HEADER_NAME = 'X-CSRF-Token'

def generate_csrf_token():
    """生成CSRF token"""
    if CSRF_TOKEN_NAME not in session:
        session[CSRF_TOKEN_NAME] = secrets.token_hex(32)
    return session[CSRF_TOKEN_NAME]

def csrf_protect(f):
    """CSRF保护装饰器 - 用于需要CSRF验证的视图"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 只对非GET请求进行CSRF检查
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return f(*args, **kwargs)
        
        # 检查token
        token = session.get(CSRF_TOKEN_NAME)
        if not token:
            abort(403, description='CSRF token missing')
        
        # 从请求头或表单获取token
        request_token = request.headers.get(CSRF_HEADER_NAME) or \
                       request.form.get(CSRF_TOKEN_NAME) or \
                       request.json.get(CSRF_TOKEN_NAME) if request.is_json else None
        
        if not request_token or not secrets.compare_digest(token, request_token):
            abort(403, description='Invalid CSRF token')
        
        return f(*args, **kwargs)
    return decorated_function

def add_security_headers(response):
    """添加安全响应头"""
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # 防止MIME类型 sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS 保护
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # 防止引用泄漏
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (基础配置)
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # 强制 HTTPS (仅在生产环境)
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

def init_security(app):
    """初始化安全中间件"""
    # 注册 Jinja2 全局函数
    @app.context_processor
    def csrf_context():
        return dict(csrf_token=generate_csrf_token)
    
    # 注册响应处理器
    @app.after_request
    def after_request(response):
        return add_security_headers(response)
    
    # 生成初始token
    @app.before_request
    def before_request():
        # 确保session中有CSRF token
        if CSRF_TOKEN_NAME not in session:
            session[CSRF_TOKEN_NAME] = secrets.token_hex(32)
```

## 2. 前端 CSRF Token 工具 (csrf_utils.js)

创建/更新 `cmd/logmonitor/src/static/js/csrf_utils.js`:

```javascript
/**
 * CSRF Token 管理工具
 * 在发起请求时自动附加CSRF token
 */

const CSRF_TOKEN_NAME = 'csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

/**
 * 获取 CSRF token (从页面meta标签或cookie)
 */
function getCsrfToken() {
    // 优先从meta标签获取 (由后端注入)
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    
    // 从cookie获取
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === CSRF_TOKEN_NAME) {
            return value;
        }
    }
    
    return null;
}

/**
 * 获取带CSRF token的请求头
 */
function getCsrfHeaders() {
    const token = getCsrfToken();
    if (token) {
        return { [CSRF_HEADER_NAME]: token };
    }
    return {};
}

/**
 * Fetch 包装器 - 自动附加CSRF token
 */
async function secureFetch(url, options = {}) {
    const headers = {
        ...getCsrfHeaders(),
        ...options.headers
    };
    
    return fetch(url, {
        ...options,
        headers
    });
}

/**
 * axios 拦截器配置 (如果使用axios)
 */
function setupAxiosCsrf(axios) {
    axios.interceptors.request.use(config => {
        const token = getCsrfToken();
        if (token) {
            config.headers[CSRF_HEADER_NAME] = token;
        }
        return config;
    });
}

// 导出
window.CsrfUtils = {
    getCsrfToken,
    getCsrfHeaders,
    secureFetch,
    setupAxiosCsrf,
    CSRF_TOKEN_NAME,
    CSRF_HEADER_NAME
};
```

## 3. 应用安全中间件

修改 `cmd/logmonitor/src/app.py`:

```python
from .middleware.security_middleware import init_security, generate_csrf_token

def create_app():
    app = Flask(__name__)
    
    # ... 现有配置 ...
    
    # 初始化安全中间件
    init_security(app)
    
    return app
```

修改模板 `cmd/logmonitor/src/templates/base.html`，在 `<head>` 中添加:

```html
<head>
    <!-- CSRF Token Meta 标签 -->
    <meta name="csrf-token" content="{{ csrf_token() }}">
    
    <!-- 引入 CSRF 工具 -->
    <script src="{{ url_for('static', filename='js/csrf_utils.js') }}"></script>
</head>
```

## 4. requirements.txt 补充

无需添加新依赖，使用标准库实现。

---

## 验证清单

应用补丁后，请验证:

- [ ] 响应头包含 `X-Frame-Options`, `X-Content-Type-Options` 等
- [ ] 表单提交自动携带 CSRF token
- [ ] API 请求带 `X-CSRF-Token` 头可正常访问
- [ ] 无 token 的 POST 请求返回 403
- [ ] 页面正常加载，无 JavaScript 错误

---

## 风险缓解

| 风险 | 缓解措施 | 状态 |
|------|----------|------|
| 点击劫持 | X-Frame-Options | ✅ 已添加 |
| XSS | X-XSS-Protection + CSP | ✅ 已添加 |
| CSRF | CSRF Token 验证 | ✅ 已添加 |
| MIME sniffing | X-Content-Type-Options | ✅ 已添加 |
