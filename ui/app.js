const API_URL = '/api';

// Alpine.js Global Stores & Reactivity
document.addEventListener('alpine:init', () => {
    if (window.Alpine) {
        Alpine.store('auth', {
            user: getStoredUser(),
            token: getToken(),
            isLoggedIn() {
                return !!this.token;
            },
            setUser(userData, tokenVal) {
                this.user = userData;
                this.token = tokenVal;
                if (userData) localStorage.setItem('user', JSON.stringify(userData));
                if (tokenVal) localStorage.setItem('token', tokenVal);
            },
            logout() {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                this.user = null;
                this.token = null;
                window.location.href = 'index.html';
            }
        });

        Alpine.store('ui', {
            activeModal: null,
            openModal(id) { this.activeModal = id; },
            closeModal() { this.activeModal = null; },
            isOpen(id) { return this.activeModal === id; }
        });
    }
});

const PROTECTED_PAGES = new Set(['community.html']);
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

function sanitizeHtml(dirty = '') {
    return escapeHtml(dirty);
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

    try {
        if (user && authLinks && userLinks) {
            authLinks.classList.add('hidden');
            authLinks.style.display = 'none';
            
            userLinks.classList.remove('hidden');
            userLinks.style.display = 'flex';

            const isAdmin = user.role === 'admin';
            const displayName = user.name || 'Member';
            const initial = displayName[0].toUpperCase();
            const avatarContent = user.avatar_url 
                ? `<img src="${safeImageUrl(user.avatar_url)}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">` 
                : escapeHtml(initial);

            userLinks.innerHTML = `
                <div class="user-menu" id="user-menu-trigger">
                    <div class="user-avatar" style="width:36px;height:36px;border-radius:50%;overflow:hidden;background:#ecfdf5;display:flex;align-items:center;justify-content:center;font-weight:800;color:#059669;">${avatarContent}</div>
                    <span id="user-name">${escapeHtml(displayName)}</span>
                    <i data-lucide="chevron-down" size="14"></i>
                    <div class="dropdown-menu">
                        <a href="login.html" class="dropdown-item">
                            <i data-lucide="log-in" size="18"></i> Login
                        </a>
                        <a href="profile.html" class="dropdown-item">
                            <i data-lucide="user" size="18"></i> Profile
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
        } else if (authLinks && userLinks) {
            userLinks.classList.add('hidden');
            userLinks.style.display = 'none';
            
            authLinks.classList.remove('hidden');
            authLinks.style.display = 'flex';
            
            authLinks.innerHTML = `
                <a href="login.html" class="btn btn-outline" style="border-radius:10px;padding:0.45rem 1rem;font-weight:700;font-size:0.85rem;text-decoration:none;">Login</a>
                <a href="register.html" class="btn btn-primary" style="border-radius:10px;padding:0.45rem 1rem;font-weight:800;font-size:0.85rem;text-decoration:none;">Register</a>
            `;
        }

        setActiveNav();
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error('Error in updateNavbar:', e);
    }
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

const EMAIL_FORMAT_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

function isValidEmailAddress(email) {
    return EMAIL_FORMAT_REGEX.test(String(email || '').trim());
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
        const errorMsg = form.closest('.auth-card')?.querySelector('.auth-message, #error-message, #inline-login-error');
        const submitBtn = form.querySelector('button[type="submit"]');
        const defaultLabel = submitBtn.innerHTML;

        if (!isValidEmailAddress(email)) {
            if (errorMsg) {
                errorMsg.querySelector('.msg-content').textContent = 'Please enter a valid email address (e.g. user@example.com).';
                errorMsg.classList.remove('hidden');
            } else {
                showToast('Please enter a valid email address.', 'error');
            }
            return;
        }

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
                if (errorMsg) {
                    errorMsg.querySelector('.msg-content').textContent = data.message || 'Could not sign in.';
                    errorMsg.classList.remove('hidden');
                } else {
                    showToast(data.message || 'Could not sign in.', 'error');
                }
            }
        } catch (error) {
            if (errorMsg) {
                errorMsg.querySelector('.msg-content').textContent = 'Server error. Please try again.';
                errorMsg.classList.remove('hidden');
            } else {
                showToast('Server error. Please try again.', 'error');
            }
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

        if (!isValidEmailAddress(email)) {
            errorMsg.querySelector('.msg-content').textContent = 'Please enter a valid email address (e.g. user@example.com).';
            errorMsg.classList.remove('hidden');
            return;
        }

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
                    window.location.href = 'login.html';
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

/**
 * Client-Side Image Compression using HTML5 Canvas
 * Resizes images exceeding maxWidth x maxHeight and compresses raster output to ~82% quality.
 */
async function compressImageFile(file, maxWidth = 1920, maxHeight = 1920, quality = 0.82) {
    if (!file || !file.type.startsWith('image/') || file.type === 'image/svg+xml' || file.size < 150 * 1024) {
        return file; // Return original if small, non-image, or vector SVG
    }

    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                let width = img.width;
                let height = img.height;

                if (width > maxWidth || height > maxHeight) {
                    if (width > height) {
                        height = Math.round((height * maxWidth) / width);
                        width = maxWidth;
                    } else {
                        width = Math.round((width * maxHeight) / height);
                        height = maxHeight;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                const mimeType = file.type === 'image/png' ? 'image/png' : 'image/jpeg';
                canvas.toBlob(
                    (blob) => {
                        if (!blob || blob.size >= file.size) {
                            resolve(file); // Keep original if compression yields larger size
                        } else {
                            const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, "") + (mimeType === 'image/png' ? '.png' : '.jpg'), {
                                type: mimeType,
                                lastModified: Date.now(),
                            });
                            resolve(compressedFile);
                        }
                    },
                    mimeType,
                    quality
                );
            };
            img.onerror = () => resolve(file);
        };
        reader.onerror = () => resolve(file);
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
    compressImageFile,
    openUserProfileModal,
};
window.escapeHtml = escapeHtml;
window.safeImageUrl = safeImageUrl;
window.fallbackImage = fallbackImage;
window.applyImageFallbacks = applyImageFallbacks;
window.showToast = showToast;
window.getStoredUser = getStoredUser;
window.getCurrentUser = getStoredUser;
window.compressImageFile = compressImageFile;
window.openUserProfileModal = openUserProfileModal;
window.closeUserProfileModal = closeUserProfileModal;
window.handleFriendAction = handleFriendAction;

// Open User Profile Page (Page Navigation)
function openUserProfileModal(userId) {
    if (!userId) return;
    window.location.href = `user-profile.html?id=${userId}`;
}

// Full-Screen Image Lightbox Popup Modal with Scroll & Download
function openImageLightbox(src) {
    if (!src) return;
    let lightbox = document.getElementById('global-image-lightbox');
    if (!lightbox) {
        lightbox = document.createElement('div');
        lightbox.id = 'global-image-lightbox';
        lightbox.style.cssText = 'position: fixed; inset: 0; background: rgba(15, 23, 42, 0.94); z-index: 99999; display: flex; flex-direction: column; align-items: center; justify-content: center; backdrop-filter: blur(12px); padding: 1.5rem; opacity: 0; transition: opacity 0.25s ease;';
        lightbox.innerHTML = `
            <div style="position: absolute; top: 1.5rem; right: 1.5rem; display: flex; gap: 0.75rem; z-index: 100000; align-items: center;">
                <a id="lightbox-download-btn" href="" download="coworkconnect-image" target="_blank" class="btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); border-radius: 50px; padding: 0.55rem 1.2rem; font-size: 0.88rem; font-weight: 800; text-decoration: none; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px); transition: all 0.2s ease;">
                    <span>⬇ Download Image</span>
                </a>
                <button type="button" onclick="closeImageLightbox()" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; cursor: pointer; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 800; backdrop-filter: blur(8px);">✕</button>
            </div>
            <div style="max-width: 92vw; max-height: 88vh; overflow: auto; display: flex; align-items: center; justify-content: center; border-radius: 16px; padding: 0.5rem;">
                <img id="lightbox-img-element" src="" style="max-width: 100%; max-height: 84vh; width: auto; height: auto; object-fit: contain; border-radius: 12px; box-shadow: 0 30px 60px rgba(0,0,0,0.6); cursor: default;">
            </div>
        `;
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) closeImageLightbox();
        });
        document.body.appendChild(lightbox);
    }

    const imgEl = document.getElementById('lightbox-img-element');
    const downloadBtn = document.getElementById('lightbox-download-btn');
    if (imgEl) imgEl.src = src;
    if (downloadBtn) downloadBtn.href = src;
    lightbox.style.display = 'flex';
    setTimeout(() => { lightbox.style.opacity = '1'; }, 10);
}

function closeImageLightbox() {
    const lightbox = document.getElementById('global-image-lightbox');
    if (lightbox) {
        lightbox.style.opacity = '0';
        setTimeout(() => { lightbox.style.display = 'none'; }, 250);
    }
}

window.openImageLightbox = openImageLightbox;
window.closeImageLightbox = closeImageLightbox;

// Delegate clickable image lightbox across all pages
document.addEventListener('click', (e) => {
    const target = e.target;
    if (target instanceof HTMLImageElement && (target.classList.contains('post-image') || target.classList.contains('msg-photo-attach') || target.id === 'e-banner' || target.classList.contains('evt-card-img') || target.classList.contains('space-card-img'))) {
        openImageLightbox(target.src);
    }
});

enforceAuth();

document.addEventListener('DOMContentLoaded', () => {
    applyImageFallbacks();
    updateNavbar();
    if (!authChecked) enforceAuth();
    
    // Redirect logged-in users away from auth pages
    const page = currentPage();
    if ((page === 'login.html' || page === 'register.html') && getToken()) {
        window.location.href = 'index.html';
        return;
    }

    renderInlineLoginGate();
});

document.addEventListener('error', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLImageElement) || target.dataset.fallbackApplied === 'true') return;
    target.dataset.fallbackApplied = 'true';
    target.src = imageFallbackFor(target);
}, true);
