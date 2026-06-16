const API_URL = '/api';

// ─── Navbar & State Management ──────────────────────────────
function updateNavbar() {
    const user = JSON.parse(localStorage.getItem('user'));
    const authLinks = document.getElementById('auth-links');
    const userLinks = document.getElementById('user-links');

    if (user && authLinks && userLinks) {
        authLinks.classList.add('hidden');
        userLinks.classList.remove('hidden');
        
        const isAdmin = user.role === 'admin';
        const initial = user.name ? user.name[0].toUpperCase() : 'U';
        
        userLinks.innerHTML = `
            <div class="user-menu" id="user-menu-trigger" style="color: white; border-color: rgba(255,255,255,0.3);">
                <div class="user-avatar">${initial}</div>
                <span id="user-name" style="font-weight: 800; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">${user.name}</span>
                <i data-lucide="chevron-down" size="14"></i>
                
                <div class="dropdown-menu">
                    <div style="padding: 0.5rem 1rem 1rem; border-bottom: 1px solid #f1f5f9; margin-bottom: 0.5rem;">
                        <span style="font-size: 0.65rem; color: var(--gray); font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">Account Center</span>
                    </div>
                    ${isAdmin ? `
                    <a href="admin.html" class="dropdown-item">
                        <i data-lucide="shield" size="18"></i> Admin Hub
                    </a>` : ''}
                    <a href="profile.html" class="dropdown-item">
                        <i data-lucide="user" size="18"></i> My Portfolio
                    </a>
                    <a href="community.html" class="dropdown-item">
                        <i data-lucide="users" size="18"></i> Networking
                    </a>
                    <div class="dropdown-item logout" id="logout-trigger" style="cursor: pointer;">
                        <i data-lucide="log-out" size="18"></i> Logout
                    </div>
                </div>
            </div>
        `;
        
        lucide.createIcons();

        const trigger = document.getElementById('user-menu-trigger');
        trigger?.addEventListener('click', (e) => {
            e.stopPropagation();
            trigger.classList.toggle('active');
        });

        document.getElementById('logout-trigger')?.addEventListener('click', () => {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            window.location.href = 'index.html';
        });

        document.addEventListener('click', () => {
            trigger?.classList.remove('active');
        });
    } else {
        authLinks?.classList.remove('hidden');
        userLinks?.classList.add('hidden');
    }
}

// ─── Professional Scroll Effect ──────────────────────────
window.addEventListener('scroll', () => {
    const nav = document.querySelector('.navbar');
    const links = document.querySelectorAll('.nav-link, .logo');
    const userMenu = document.getElementById('user-menu-trigger');
    
    if (window.scrollY > 50) {
        nav.style.background = 'rgba(255, 255, 255, 0.95)';
        nav.style.backdropFilter = 'blur(10px)';
        nav.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
        nav.style.height = '70px';
        links.forEach(l => l.style.color = 'var(--dark)');
        if(userMenu) {
            userMenu.style.color = 'var(--primary)';
            userMenu.style.borderColor = 'var(--primary)';
            userMenu.style.background = 'rgba(16, 185, 129, 0.05)';
        }
    } else {
        if(window.location.pathname.includes('index.html') || window.location.pathname === '/') {
            nav.style.background = 'transparent';
            nav.style.backdropFilter = 'none';
            nav.style.boxShadow = 'none';
            nav.style.height = '90px';
            links.forEach(l => l.style.color = 'white');
            if(userMenu) {
                userMenu.style.color = 'white';
                userMenu.style.borderColor = 'rgba(255,255,255,0.3)';
                userMenu.style.background = 'rgba(255,255,255,0.05)';
            }
        } else {
            nav.style.background = 'white';
            nav.style.height = '70px';
            links.forEach(l => l.style.color = 'var(--dark)');
            if(userMenu) {
                userMenu.style.color = 'var(--primary)';
                userMenu.style.borderColor = 'var(--primary)';
            }
        }
    }
});

// ─── Login Logic ──────────────────────────────────────────
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
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
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.success) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                window.location.href = 'index.html';
            } else {
                errorMsg.querySelector('.msg-content').textContent = data.message;
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

// ─── Register Logic ───────────────────────────────────────
const registerForm = document.getElementById('register-form');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim().toLowerCase();
        const password = document.getElementById('password').value;
        const errorMsg = document.getElementById('error-message');
        const successMsg = document.getElementById('success-message');
        const submitBtn = registerForm.querySelector('button[type="submit"]');

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating account...';
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });

            const data = await response.json();

            if (data.success) {
                if (data.token && data.user) {
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                }
                successMsg.querySelector('.msg-content').textContent = 'Account created! Taking you to the app...';
                successMsg.classList.remove('hidden');
                errorMsg.classList.add('hidden');
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 700);
            } else {
                errorMsg.querySelector('.msg-content').textContent = data.message;
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

// Run on every page load
document.addEventListener('DOMContentLoaded', updateNavbar);
