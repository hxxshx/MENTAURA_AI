/**
 * MENTAURA — Admin Pending Approvals JavaScript (pending-approvals.js)
 * Manages fetching, approving, and rejecting pending official signups.
 */

let pendingData = [];
let autoSyncTimer = null;

// Helper: Escape HTML
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

// Helper: Format ISO datetime in local IST format
function formatDateTime(isoString) {
  if (!isoString) return 'Not available';
  try {
    let str = String(isoString);
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) {
      str = str + 'Z';
    }
    const d = new Date(str);
    if (isNaN(d.getTime())) return 'Not available';
    return d.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch (e) {
    return 'Not available';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Authenticated Admin Role Guard
  const user = await initAuthGuard([
    'state_admin', 'state_administrator', 'national_administrator',
    'district_admin', 'district_authority'
  ]);
  if (!user) return;

  // 2. Setup Navbar Controls
  setupProfilePopover(user);
  setupLanguageSelector(user);
  setupMobileDrawer();

  // 3. Load Pending Officials Queue
  await loadPendingOfficials();

  // 4. Setup Modals and Action Handlers
  setupModals();
  setupRefreshControls();

  // 5. Start Background Auto-Sync
  startAutoSync();
});

/**
 * Loads pending official account requests
 */
async function loadPendingOfficials() {
  const tbody = document.getElementById('pendingTableBody');
  const countBadge = document.getElementById('pendingCountBadge');
  if (!tbody) return;

  try {
    const res = await fetch('/api/admin/pending-officials', {
      method: 'GET',
      headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' },
      cache: 'no-store',
      credentials: 'include'
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    pendingData = data.pending_officials || [];

    if (countBadge) countBadge.textContent = pendingData.length;

    if (pendingData.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6">
            <div class="empty-approvals-card">
              <div class="empty-approvals-icon"><i class="fa-solid fa-user-check"></i></div>
              <div class="empty-approvals-title">All official requests reviewed!</div>
              <div class="empty-approvals-desc">There are no pending official registrations awaiting administrative verification.</div>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = pendingData.map(item => {
      return `
        <tr>
          <td>
            <div class="candidate-cell">
              <span class="candidate-name">${escapeHtml(item.full_name)}</span>
              <span class="candidate-email">${escapeHtml(item.email)}</span>
            </div>
          </td>
          <td>
            <span class="role-tag">
              <i class="fa-solid fa-id-badge"></i> ${escapeHtml(item.requested_role_display || item.requested_role)}
            </span>
          </td>
          <td>
            <div class="jurisdiction-cell">
              <span class="jurisdiction-district">${escapeHtml(item.district)}</span>
              <span class="jurisdiction-state">${escapeHtml(item.state)}</span>
            </div>
          </td>
          <td>${escapeHtml(formatDateTime(item.requested_at))}</td>
          <td>
            <span class="status-badge-pending">
              <i class="fa-solid fa-clock"></i> Pending Verification
            </span>
          </td>
          <td style="text-align: right;">
            <div class="actions-cell">
              <button type="button" class="btn-table-approve" onclick="window.openApproveModal('${escapeHtml(item.id)}')">
                <i class="fa-solid fa-check"></i> Approve
              </button>
              <button type="button" class="btn-table-reject" onclick="window.openRejectModal('${escapeHtml(item.id)}')">
                <i class="fa-solid fa-xmark"></i> Reject
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.error('Error loading pending officials:', err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #E11D48; padding: 24px;">Failed to load pending requests.</td></tr>`;
  }
}

/**
 * Setup Refresh Button
 */
function setupRefreshControls() {
  const btn = document.getElementById('refreshListBtn');
  if (btn) {
    btn.addEventListener('click', async () => {
      const icon = btn.querySelector('i');
      if (icon) icon.classList.add('fa-spin');
      btn.disabled = true;

      try {
        await loadPendingOfficials();
        showToast('Pending registrations refreshed.');
      } finally {
        setTimeout(() => {
          if (icon) icon.classList.remove('fa-spin');
          btn.disabled = false;
        }, 500);
      }
    });
  }
}

/**
 * Background auto-sync interval (every 6 seconds)
 */
function startAutoSync() {
  if (autoSyncTimer) clearInterval(autoSyncTimer);
  autoSyncTimer = setInterval(async () => {
    const isModalOpen = document.querySelector('.approval-modal.active, .approval-modal.show');
    if (!isModalOpen && !document.hidden) {
      await loadPendingOfficials();
    }
  }, 6000);
}

/**
 * Modal Handling
 */
function setupModals() {
  const approveModal = document.getElementById('approveModal');
  const rejectModal = document.getElementById('rejectModal');

  // Close buttons
  document.getElementById('closeApproveModalBtn')?.addEventListener('click', () => closeModal(approveModal));
  document.getElementById('cancelApproveBtn')?.addEventListener('click', () => closeModal(approveModal));
  document.getElementById('closeRejectModalBtn')?.addEventListener('click', () => closeModal(rejectModal));
  document.getElementById('cancelRejectBtn')?.addEventListener('click', () => closeModal(rejectModal));

  // Approve Form Submit
  const approveForm = document.getElementById('approveOfficialForm');
  if (approveForm) {
    approveForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const userId = document.getElementById('approveUserId').value;
      const verifiedRole = document.getElementById('approveRoleSelect').value;
      const district = document.getElementById('approveDistrictInput').value;
      const notes = document.getElementById('approveNotesInput').value;
      const submitBtn = document.getElementById('confirmApproveBtn');

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Approving...';
        }

        const res = await fetch('/api/admin/approve-official', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            user_id: userId,
            verified_role: verifiedRole,
            district: district,
            notes: notes
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to approve official');
        }
        const result = await res.json();

        closeModal(approveModal);
        showToast(result.message || 'Official approved successfully.');
        await loadPendingOfficials();
      } catch (err) {
        alert('Error approving official: ' + err.message);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fa-solid fa-check"></i> Confirm Approval';
        }
      }
    });
  }

  // Reject Form Submit
  const rejectForm = document.getElementById('rejectOfficialForm');
  if (rejectForm) {
    rejectForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const userId = document.getElementById('rejectUserId').value;
      const reason = document.getElementById('rejectReasonInput').value;
      const submitBtn = document.getElementById('confirmRejectBtn');

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Rejecting...';
        }

        const res = await fetch('/api/admin/reject-official', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            user_id: userId,
            reason: reason
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to reject official');
        }
        const result = await res.json();

        closeModal(rejectModal);
        showToast(result.message || 'Official request rejected.');
        await loadPendingOfficials();
      } catch (err) {
        alert('Error rejecting official: ' + err.message);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fa-solid fa-xmark"></i> Confirm Rejection';
        }
      }
    });
  }
}

function openApproveModal(userId) {
  const item = pendingData.find(u => u.id === userId);
  if (!item) return;

  const idInput = document.getElementById('approveUserId');
  const nameEl = document.getElementById('modalApproveName');
  const emailEl = document.getElementById('modalApproveEmail');
  const roleSelect = document.getElementById('approveRoleSelect');
  const notesInput = document.getElementById('approveNotesInput');

  if (idInput) idInput.value = item.id;
  if (nameEl) nameEl.textContent = item.full_name || 'Official Applicant';
  if (emailEl) emailEl.textContent = item.email || '—';
  if (notesInput) notesInput.value = '';

  if (roleSelect && item.requested_role) {
    roleSelect.value = item.requested_role;
  }

  const modal = document.getElementById('approveModal');
  if (modal) {
    modal.classList.add('active', 'show');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
}

function openRejectModal(userId) {
  const item = pendingData.find(u => u.id === userId);
  if (!item) return;

  const idInput = document.getElementById('rejectUserId');
  const nameEl = document.getElementById('modalRejectName');
  const emailEl = document.getElementById('modalRejectEmail');
  const reasonInput = document.getElementById('rejectReasonInput');

  if (idInput) idInput.value = item.id;
  if (nameEl) nameEl.textContent = item.full_name || 'Official Applicant';
  if (emailEl) emailEl.textContent = item.email || '—';
  if (reasonInput) reasonInput.value = '';

  const modal = document.getElementById('rejectModal');
  if (modal) {
    modal.classList.add('active', 'show');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.remove('active', 'show');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

function showToast(message) {
  const box = document.getElementById('toastBox');
  const msg = document.getElementById('toastMessage');
  if (!box || !msg) return;

  msg.textContent = message;
  box.style.display = 'flex';

  setTimeout(() => {
    box.style.display = 'none';
  }, 4000);
}

/**
 * Navbar Profile Popover Helpers
 */
function setupProfilePopover(user) {
  const chip = document.getElementById('navUserProfileChip');
  const popover = document.getElementById('userProfilePopover');
  const closeBtn = document.getElementById('popoverCloseBtn');
  const dismissBtn = document.getElementById('btnPopoverDismiss');

  const navName = document.getElementById('navUserFullName');
  const popName = document.getElementById('popoverUserFullName');
  const popRole = document.getElementById('popoverUserRole');
  const popEmail = document.getElementById('popoverUserEmail');
  const popStatus = document.getElementById('popoverUserStatus');
  const popJurisdiction = document.getElementById('popoverUserJurisdiction');

  const roleLabels = {
    district_authority: 'District Authority',
    district_admin: 'District Administrator',
    case_officer: 'Case Coordination Officer',
    state_administrator: 'State Administrator',
    state_admin: 'State Administrator',
    national_administrator: 'National Administrator'
  };

  const formattedRole = roleLabels[user.verified_role] || (user.verified_role || 'ADMIN').replace('_', ' ').toUpperCase();

  if (navName) navName.textContent = user.full_name || 'Administrator';
  if (popName) popName.textContent = user.full_name || 'Administrator';
  if (popRole) popRole.textContent = formattedRole;
  if (popEmail) popEmail.textContent = user.email || '—';
  if (popStatus) popStatus.textContent = user.account_status ? user.account_status.toUpperCase() : 'ACTIVE';
  if (popJurisdiction) popJurisdiction.textContent = user.district ? `${user.district} Command` : 'Tamil Nadu State Command';

  if (chip && popover) {
    const togglePopover = (e) => {
      e.stopPropagation();
      const isExpanded = chip.getAttribute('aria-expanded') === 'true';
      chip.setAttribute('aria-expanded', !isExpanded);
      popover.classList.toggle('active', !isExpanded);
    };

    const closePopover = () => {
      chip.setAttribute('aria-expanded', 'false');
      popover.classList.remove('active');
    };

    chip.addEventListener('click', togglePopover);
    closeBtn?.addEventListener('click', closePopover);
    dismissBtn?.addEventListener('click', closePopover);

    document.addEventListener('click', (e) => {
      if (!popover.contains(e.target) && !chip.contains(e.target)) {
        closePopover();
      }
    });
  }
}

function setupLanguageSelector(user) {
  const trigger = document.getElementById('langSelectorTrigger');
  const dropdown = document.getElementById('langDropdown');
  if (trigger && dropdown) {
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('active');
    });
    document.addEventListener('click', () => {
      dropdown.classList.remove('active');
    });
  }
}

function setupMobileDrawer() {
  const toggle = document.getElementById('mobileMenuToggle');
  const drawer = document.getElementById('mobileMenuDrawer');
  if (toggle && drawer) {
    toggle.addEventListener('click', () => {
      drawer.classList.toggle('active');
    });
  }
}

// Attach globally for inline HTML event triggers
window.openApproveModal = openApproveModal;
window.openRejectModal = openRejectModal;
window.loadPendingOfficials = loadPendingOfficials;
window.closeModal = closeModal;
