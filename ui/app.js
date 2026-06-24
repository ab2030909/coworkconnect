const API_URL = '/api';

const PUBLIC_PAGES = new Set(['login.html', 'register.html']);
const APP_PAGES = new Set([
    '',
    'index.html',
    'spaces.html',
    'community.html',
    'groups.html',
    'events.html',
    'event-details.html',
    'profile.html',
    'admin.html',
]);

let authChecked = false;
let authAllowed = true;

function currentPage() {
    return window.location.pathname.split('/').pop() || 'index.html';
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

function safeImageUrl(value, fallback = '') {
    const url = String(value || '').trim();
    if (!url) return fallback;
    if (url.startsWith('/uploads/') || url.startsWith('https://images.unsplash.com/') || url.startsWith('https://i.pravatar.cc/') || url.startsWith('https://ui-avatars.com/')) {
        return url;
    }
    return fallback;
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
    const token = getToken();
    if (APP_PAGES.has(page) && !PUBLIC_PAGES.has(page) && !token) {
        authAllowed = false;
        window.location.replace('login.html');
        return false;
    }
    if (PUBLIC_PAGES.has(page) && token) {
        authAllowed = false;
        window.location.replace('index.html');
        return false;
    }
    authAllowed = true;
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
            window.location.href = 'login.html';
        });

        document.addEventListener('click', () => trigger?.classList.remove('active'));
    } else {
        authLinks?.classList.remove('hidden');
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
        window.location.href = 'login.html';
    }
    return response;
}

const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = document.getElementById('email').value.trim().toLowerCase();
        const password = document.getElementById('password').value;
        const errorMsg = document.getElementById('error-message');
        const submitBtn = loginForm.querySelector('button[type="submit"]');

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
                window.location.href = 'index.html';
            } else {
                errorMsg.querySelector('.msg-content').textContent = data.message || 'Could not sign in.';
                errorMsg.classList.remove('hidden');
            }
        } catch (error) {
            errorMsg.querySelector('.msg-content').textContent = 'Server error. Please try again.';
            errorMsg.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Log In';
        }
    });
}

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
    showToast,
    getStoredUser,
    getToken,
};
window.escapeHtml = escapeHtml;
window.safeImageUrl = safeImageUrl;
window.showToast = showToast;

enforceAuth();

document.addEventListener('DOMContentLoaded', () => {
    if ((!authChecked && !enforceAuth()) || !authAllowed) return;
    updateNavbar();
});
