/**
 * MENTAURA — Auth Guard & Role Verification Script
 * Validates active session on protected pages, enforces backend verified roles,
 * handles unauthorized access, and provides secure logout functionality.
 */

async function initAuthGuard(allowedRoles = []) {
  try {
    const token = localStorage.getItem('mentaura_token');
    const headers = { 'Accept': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch('/api/auth/me', {
      method: 'GET',
      credentials: 'include',
      headers: headers
    });

    if (!response.ok) {
      // Unauthenticated -> redirect to home login
      window.location.href = '/index.html?auth_required=true';
      return null;
    }

    const user = await response.json();

    // Check if user is pending verification
    if (user.account_status === 'pending_verification' || user.verified_role === 'pending_verification') {
      const isPendingPage = window.location.pathname.includes('verification-pending.html');
      if (!isPendingPage) {
        window.location.href = '/verification-pending.html';
        return null;
      }
    }

    // Role Enforcement check
    if (allowedRoles.length > 0 && !allowedRoles.includes(user.verified_role)) {
      // Show Forbidden state
      document.body.innerHTML = `
        <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #EEEDFD; font-family: 'Plus Jakarta Sans', sans-serif; padding: 20px;">
          <div style="background: #FFFFFF; border-radius: 20px; padding: 40px; max-width: 500px; text-align: center; box-shadow: 0 10px 30px rgba(45,20,85,0.08); border: 1px solid rgba(220,215,245,0.8);">
            <div style="width: 56px; height: 56px; border-radius: 14px; background: linear-gradient(135deg, #FF7B90, #EFA4CE); color: #fff; display: inline-flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 16px;">
              <i class="fa-solid fa-ban"></i>
            </div>
            <h2 style="color: #2B1552; font-size: 1.5rem; margin-bottom: 10px; font-weight: 800;">Access Restricted</h2>
            <p style="color: #5C5574; font-size: 0.95rem; margin-bottom: 24px; line-height: 1.55;">
              Your verified role (<strong>${user.verified_role.replace(/_/g, ' ')}</strong>) does not have access permissions for this workspace.
            </p>
            <div style="display: flex; gap: 10px; justify-content: center;">
              <a href="/index.html" style="background: #EDE8FB; color: #2B1552; padding: 10px 20px; border-radius: 9999px; text-decoration: none; font-weight: 600; font-size: 0.9rem;">Home</a>
              <button onclick="handleLogout()" style="background: #2B1552; color: #FFFFFF; border: none; padding: 10px 20px; border-radius: 9999px; font-weight: 600; font-size: 0.9rem; cursor: pointer;">Log Out</button>
            </div>
          </div>
        </div>
      `;
      return null;
    }

    // Populate user profile info in DOM elements if present
    const nameEl = document.getElementById('userFullName');
    const roleEl = document.getElementById('userVerifiedRole');
    const emailEl = document.getElementById('userEmail');
    const statusEl = document.getElementById('userStatus');

    if (nameEl) nameEl.textContent = user.full_name;
    if (roleEl) roleEl.textContent = formatRole(user.verified_role);
    if (emailEl) emailEl.textContent = user.email;
    if (statusEl) statusEl.textContent = formatStatus(user.account_status);

    // Bind logout buttons
    document.querySelectorAll('.btn-logout').forEach((btn) => {
      btn.addEventListener('click', handleLogout);
    });

    return user;
  } catch (error) {
    console.error('Auth Guard Error:', error);
    window.location.href = '/index.html?error=connection_failed';
    return null;
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include'
    });
  } catch (err) {
    console.warn('Logout API error:', err);
  } finally {
    localStorage.removeItem('mentaura_token');
    // Prevent back-button cache retention
    window.location.replace('/index.html?logged_out=true');
  }
}

function formatRole(role) {
  if (!role) return '';
  return role
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatStatus(status) {
  if (!status) return '';
  return status
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
