const API_URL = '/api';

const PROTECTED_PAGES = new Set(['community.html', 'groups.html']);
const FALLBACK_IMAGES = {
    workspace: 'assets/fallback-workspace.svg',
    community: 'assets/fallback-community.svg',
    event: 'assets/fallback-event.svg',
    avatar: 'assets/fallback-avatar.svg',
};

let authChecked = false;

function currentPage() {
    const page = window.location.pathname.split('/').pop() || 'index.html';
    return page === 'login.html' ? 'index.html' : page;
}

function getStoredUser() {
    try {
        return JSON.parse(localStorage.getItem('user'));
    } catch (error) {
        localStorage.removeItem('user');
        return null;
    }
}

function getToken() {
    return localStorage.getItem('token');
}

function escapeHtml(value = '') {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function fallbackImage(type = 'workspace') {
    return FALLBACK_IMAGES[type] || FALLBACK_IMAGES.workspace;
}

function safeImageUrl(value, fallback = fallbackImage('workspace')) {
    const url = String(value || '').trim();
    if (!url) return fallback;
    if (url.startsWith('/uploads/')) return url;
    if (url.startsWith('uploads/')) return `/${url}`;
    if (url.startsWith('assets/')) return url;
    if (url.startsWith('/assets/')) return url;
    if (url.startsWith('./assets/')) return url.slice(2);
    if (/^\/[A-Za-z0-9/_-]+\.(png|jpe?g|gif|webp|svg)(\?[^\s"'<>]*)?$/i.test(url)) return url;
    if (/^[A-Za-z0-9][A-Za-z0-9/_-]*\.(png|jpe?g|gif|webp|svg)(\?[^\s"'<>]*)?$/i.test(url)) return url;
    if (/^https:\/\/[^\s"'<>]+$/i.test(url)) {
        return url;
    }
    return fallback;
}

function imageFallbackFor(img) {
    if (img.dataset.fallback) return safeImageUrl(img.dataset.fallback, fallbackImage('workspace'));
    if (img.classList.contains('avatar') || img.className.includes('avatar')) return fallbackImage('avatar');
    if (img.className.includes('event') || img.className.includes('evt')) return fallbackImage('event');
    if (img.className.includes('post') || img.className.includes('message') || img.className.includes('group') || img.className.includes('pinned') || img.className.includes('community')) return fallbackImage('community');
    return fallbackImage('workspace');
}

function applyImageFallbacks(root = document) {
    root.querySelectorAll('img').forEach((img) => {
        if (!img.dataset.fallback) img.dataset.fallback = imageFallbackFor(img);
        if (!img.getAttribute('src')) img.src = img.dataset.fallback;
    });
}

function showToast(message, type = 'success') {
    const oldToast = document.querySelector('.toast');
    if (oldToast) oldToast.remove();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 20);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 220);
    }, 2600);
}

function enforceAuth() {
    authChecked = true;
    const page = currentPage();
    return !(PROTECTED_PAGES.has(page) && !getToken());
}

function protectedPageLabel() {
    return currentPage() === 'groups.html' ? 'Groups' : 'Network';
}

function renderInlineLoginGate(message = '') {
    const page = currentPage();
    if (!PROTECTED_PAGES.has(page) || getToken()) return false;

    const main = document.querySelector('main');
    if (!main) return false;

    main.className = 'inline-auth-page';
    main.innerHTML = `
        <section class="inline-auth-shell">
            <div class="inline-auth-copy">
                <span class="eyebrow"><i data-lucide="lock-keyhole" size="16"></i> Members only</span>
                <h1>${protectedPageLabel()} is available after sign in.</h1>
                <p>Sign in here to continue without leaving this page. The rest of CoWorkConnect stays open for browsing.</p>
                <div class="inline-auth-points">
                    <span><i data-lucide="check" size="16"></i> Keep the same navbar</span>
                    <span><i data-lucide="check" size="16"></i> Open protected tools instantly</span>
                    <span><i data-lucide="check" size="16"></i> Return to this page after login</span>
                </div>
            </div>
            <div class="auth-card inline-auth-card">
                <div class="auth-card-head">
                    <div class="auth-icon"><i data-lucide="log-in" size="28"></i></div>
                    <h2>Sign in</h2>
                    <p>Use your CoWorkConnect account to continue.</p>
                </div>
                <div id="inline-login-error" class="auth-message ${message ? '' : 'hidden'}">
                    <i data-lucide="alert-circle" size="18"></i>
                    <span class="msg-content">${escapeHtml(message)}</span>
                </div>
                <form id="inline-login-form">
                    <div class="input-group">
                        <label>Email Address</label>
                        <input type="email" id="inline-email" class="input-field" placeholder="you@example.com" autocomplete="email" required>
                    </div>
                    <div class="input-group">
                        <label>Password</label>
                        <input type="password" id="inline-password" class="input-field" placeholder="Password" autocomplete="current-password" required>
                    </div>
                    <button type="submit" class="btn btn-primary inline-auth-submit">
                        <i data-lucide="arrow-right" size="18"></i> Sign in
                    </button>
                </form>
                <p class="inline-auth-footer">New here? <a href="register.html">Create an account</a></p>
            </div>
        </section>
    `;

    bindLoginForm(document.getElementById('inline-login-form'));
    applyImageFallbacks(main);
    if (window.lucide) lucide.createIcons();
    return true;
}

function setActiveNav() {
    const page = currentPage();
    document.querySelectorAll('.nav-link').forEach((link) => {
        const href = link.getAttribute('href') || '';
        link.classList.toggle('active', href === page || (page === 'index.html' && href === 'index.html'));
    });
}

function updateNavbar() {
    const user = getStoredUser();
    const authLinks = document.getElementById('auth-links');
    const userLinks = document.getElementById('user-links');
    const nav = document.querySelector('.navbar');
    const navContainer = document.querySelector('.nav-container');

    nav?.classList.add('navbar-solid');

    if (navContainer && !document.getElementById('mobile-nav-toggle')) {
        const toggle = document.createElement('button');
        toggle.id = 'mobile-nav-toggle';
        toggle.className = 'nav-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-label', 'Toggle navigation');
        toggle.innerHTML = '<i data-lucide="menu" size="20"></i>';
        navContainer.appendChild(toggle);
        toggle.addEventListener('click', () => {
            document.querySelector('.nav-links')?.classList.toggle('open');
        });
    }

    if (user && authLinks && userLinks) {
        authLinks.classList.add('hidden');
        userLinks.classList.remove('hidden');

        const isAdmin = user.role === 'admin';
        const displayName = user.name || 'Member';
        const initial = displayName[0].toUpperCase();

        userLinks.innerHTML = `
            <div class="user-menu" id="user-menu-trigger">
                <div class="user-avatar">${escapeHtml(initial)}</div>
                <span id="user-name">${escapeHtml(displayName)}</span>
                <i data-lucide="chevron-down" size="14"></i>
                <div class="dropdown-menu">
                    <div class="dropdown-header">Workspace Account</div>
                    ${isAdmin ? `
                    <a href="admin.html" class="dropdown-item">
                        <i data-lucide="shield" size="18"></i> Admin Hub
                    </a>` : ''}
                    <a href="profile.html" class="dropdown-item">
                        <i data-lucide="user" size="18"></i> Profile
                    </a>
                    <a href="community.html" class="dropdown-item">
                        <i data-lucide="users" size="18"></i> Network
                    </a>
                    <button class="dropdown-item logout" id="logout-trigger" type="button">
                        <i data-lucide="log-out" size="18"></i> Logout
                    </button>
                </div>
            </div>
        `;

        const trigger = document.getElementById('user-menu-trigger');
        trigger?.addEventListener('click', (event) => {
            event.stopPropagation();
            trigger.classList.toggle('active');
        });

        document.getElementById('logout-trigger')?.addEventListener('click', () => {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            window.location.href = 'index.html';
        });

        document.addEventListener('click', () => trigger?.classList.remove('active'));
    } else {
        authLinks?.classList.add('hidden');
        userLinks?.classList.add('hidden');
    }

    setActiveNav();
    if (window.lucide) lucide.createIcons();
}

async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = { ...(options.headers || {}) };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(`${API_URL}${path}`, { ...options, headers });
    if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (PROTECTED_PAGES.has(currentPage())) {
            renderInlineLoginGate('Your session expired. Please sign in again.');
        }
    }
    return response;
}

function bindLoginForm(form) {
    if (!form || form.dataset.bound === 'true') return;
    form.dataset.bound = 'true';

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const emailInput = form.querySelector('input[type="email"]');
        const passwordInput = form.querySelector('input[type="password"]');
        const email = emailInput.value.trim().toLowerCase();
        const password = passwordInput.value;
        const errorMsg = form.closest('.auth-card')?.querySelector('.auth-message, #error-message');
        const submitBtn = form.querySelector('button[type="submit"]');
        const defaultLabel = submitBtn.innerHTML;

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in...';
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();
            if (data.success) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                window.location.reload();
            } else {
                errorMsg.querySelector('.msg-content').textContent = data.message || 'Could not sign in.';
                errorMsg.classList.remove('hidden');
            }
        } catch (error) {
            errorMsg.querySelector('.msg-content').textContent = 'Server error. Please try again.';
            errorMsg.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = defaultLabel;
            if (window.lucide) lucide.createIcons();
        }
    });
}

bindLoginForm(document.getElementById('login-form'));

const registerForm = document.getElementById('register-form');
if (registerForm) {
    registerForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim().toLowerCase();
        const password = document.getElementById('password').value;
        const errorMsg = document.getElementById('error-message');
        const successMsg = document.getElementById('success-message');
        const submitBtn = registerForm.querySelector('button[type="submit"]');

        if (password.length < 8) {
            errorMsg.querySelector('.msg-content').textContent = 'Password must be at least 8 characters.';
            errorMsg.classList.remove('hidden');
            return;
        }

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating account...';
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password }),
            });

            const data = await response.json();
            if (data.success) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                successMsg.querySelector('.msg-content').textContent = 'Account created. Opening your workspace...';
                successMsg.classList.remove('hidden');
                errorMsg.classList.add('hidden');
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 500);
            } else {
                errorMsg.querySelector('.msg-content').textContent = data.message || 'Could not create account.';
                errorMsg.classList.remove('hidden');
                successMsg.classList.add('hidden');
            }
        } catch (error) {
            errorMsg.querySelector('.msg-content').textContent = 'Server error. Please try again.';
            errorMsg.classList.remove('hidden');
            successMsg.classList.add('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Account';
        }
    });
}

window.CoWorkConnect = {
    apiFetch,
    escapeHtml,
    safeImageUrl,
    fallbackImage,
    applyImageFallbacks,
    showToast,
    getStoredUser,
    getToken,
    renderInlineLoginGate,
};
window.escapeHtml = escapeHtml;
window.safeImageUrl = safeImageUrl;
window.fallbackImage = fallbackImage;
window.applyImageFallbacks = applyImageFallbacks;
window.showToast = showToast;

enforceAuth();

document.addEventListener('DOMContentLoaded', () => {
    applyImageFallbacks();
    updateNavbar();
    if (!authChecked) enforceAuth();
    renderInlineLoginGate();
});

document.addEventListener('error', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLImageElement) || target.dataset.fallbackApplied === 'true') return;
    target.dataset.fallbackApplied = 'true';
    target.src = imageFallbackFor(target);
}, true);
