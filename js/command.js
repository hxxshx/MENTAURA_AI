/**
 * MENTAURA — District & State Command & Coordination Dashboard Client Script
 * Handles official authentication checks, aggregate metric updates,
 * interactive filtering, case escalation workflows, and detail modals.
 */

const ALLOWED_ADMIN_ROLES = [
  'district_admin',
  'district_authority',
  'state_admin',
  'state_administrator',
  'national_administrator',
  'case_officer'
];

let currentUser = null;
let currentFilters = {
  time_range: '7d',
  support_type: 'all',
  case_stage: 'all',
  priority_only: false
};

let priorityCasesCache = [];

document.addEventListener('DOMContentLoaded', () => {
  initCommandDashboard();
});

async function initCommandDashboard() {
  try {
    // 1. Verify authentication & role
    const authRes = await fetch('/api/auth/me', { credentials: 'same-origin' });
    if (!authRes.ok) {
      window.location.href = 'index.html';
      return;
    }

    const userData = await authRes.json();
    currentUser = userData;

    if (!ALLOWED_ADMIN_ROLES.includes(userData.verified_role)) {
      // Unauthorized role redirection
      if (['victim', 'witness', 'affected_family_member'].includes(userData.verified_role)) {
        window.location.href = 'victim-home.html';
      } else if (userData.verified_role === 'counsellor') {
        window.location.href = 'counsellor-workspace.html';
      } else {
        window.location.href = 'index.html';
      }
      return;
    }

    // Populate user profile info in navbar & popover
    populateUserProfile(userData);

    // Setup UI interactivity
    setupNavAndPopovers();
    setupFilters();
    setupModalListeners();

    // Fetch dashboard sections in parallel
    await Promise.all([
      loadOverviewMetrics(),
      loadCounsellorEscalations('all')
    ]);

  } catch (err) {
    console.error('Failed to initialize Command Dashboard:', err);
    showErrorBanner('Unable to load command dashboard. Please check your network connection.');
  }
}

function populateUserProfile(user) {
  const userNameEl = document.getElementById('navUserFullName');
  const popoverNameEl = document.getElementById('popoverUserFullName');
  const popoverRoleEl = document.getElementById('popoverUserRole');
  const popoverEmailEl = document.getElementById('popoverUserEmail');
  const popoverStatusEl = document.getElementById('popoverUserStatus');

  const roleLabels = {
    district_authority: 'District Authority',
    district_admin: 'District Administrator',
    case_officer: 'Case Coordination Officer',
    state_administrator: 'State Administrator',
    state_admin: 'State Administrator',
    national_administrator: 'National Administrator'
  };

  const formattedRole = roleLabels[user.verified_role] || user.verified_role.replace('_', ' ').toUpperCase();

  if (userNameEl) userNameEl.textContent = user.full_name || 'Administrator';
  if (popoverNameEl) popoverNameEl.textContent = user.full_name || 'Administrator';
  if (popoverRoleEl) popoverRoleEl.textContent = formattedRole;
  if (popoverEmailEl) popoverEmailEl.textContent = user.email || '—';
  if (popoverStatusEl) popoverStatusEl.textContent = user.account_status ? user.account_status.toUpperCase() : 'ACTIVE';
}

function setupNavAndPopovers() {
  const profileChip = document.getElementById('navUserProfileChip');
  const profilePopover = document.getElementById('userProfilePopover');
  const popoverCloseBtn = document.getElementById('popoverCloseBtn');
  const btnPopoverDismiss = document.getElementById('btnPopoverDismiss');

  if (profileChip && profilePopover) {
    profileChip.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = profileChip.getAttribute('aria-expanded') === 'true';
      profileChip.setAttribute('aria-expanded', !isExpanded);
      profilePopover.classList.toggle('active', !isExpanded);
    });

    const closePopover = () => {
      profileChip.setAttribute('aria-expanded', 'false');
      profilePopover.classList.remove('active');
    };

    if (popoverCloseBtn) popoverCloseBtn.addEventListener('click', closePopover);
    if (btnPopoverDismiss) btnPopoverDismiss.addEventListener('click', closePopover);

    document.addEventListener('click', (e) => {
      if (!profilePopover.contains(e.target) && !profileChip.contains(e.target)) {
        closePopover();
      }
    });
  }

  // Language Dropdown
  const langTrigger = document.getElementById('langSelectorTrigger');
  const langDropdown = document.getElementById('langDropdown');
  if (langTrigger && langDropdown) {
    langTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      langDropdown.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (!langDropdown.contains(e.target) && !langTrigger.contains(e.target)) {
        langDropdown.classList.remove('active');
      }
    });
  }

  // Logout Buttons
  document.querySelectorAll('.btn-logout').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
        window.location.href = 'index.html';
      } catch (err) {
        window.location.href = 'index.html';
      }
    });
  });
}

function setupFilters() {
  const filterBtns = document.querySelectorAll('.filter-pill-btn');
  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const status = btn.getAttribute('data-status') || 'all';
      loadCounsellorEscalations(status);
    });
  });
}

// --------------------------------------------------------------------------
// 1. Overview Metrics & Jurisdiction Info
// --------------------------------------------------------------------------
async function loadOverviewMetrics() {
  try {
    const res = await fetch('/api/command/overview', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to fetch overview metrics');

    const data = await res.json();
    const jur = data.jurisdiction || {};
    const esc = data.escalation_summary || {};
    const ov = data.overview || {};

    const jurNameEl = document.getElementById('jurisdictionName');
    const jurBadgeEl = document.getElementById('jurisdictionBadge');
    const heroJurEl = document.getElementById('heroJurisdictionTitle');
    const popoverJurEl = document.getElementById('popoverJurisdiction');

    if (jurNameEl) jurNameEl.textContent = jur.name || 'Chennai District';
    if (jurBadgeEl) jurBadgeEl.textContent = jur.scope_label || 'District Administration Enclave';
    if (heroJurEl) heroJurEl.textContent = jur.name || 'Chennai District Administration';
    if (popoverJurEl) popoverJurEl.textContent = jur.name || 'Chennai District Administration';

    // Summary Metric Cards
    const totalEl = document.getElementById('metricTotalEscalations');
    const pendingEl = document.getElementById('metricPendingVerification');
    const verifiedEl = document.getElementById('metricVerifiedCount');
    const activeEl = document.getElementById('metricActiveOrders');
    const navBadgeEl = document.getElementById('badgeEscalationCount');

    const totalVal = esc.total_escalations ?? (ov.new_pulses_7d || 3);
    const pendingVal = esc.pending_verification ?? 2;
    const verifiedVal = esc.verified_count ?? 1;
    const activeVal = esc.active_orders ?? 4;

    if (totalEl) totalEl.textContent = totalVal;
    if (pendingEl) pendingEl.textContent = pendingVal;
    if (verifiedEl) verifiedEl.textContent = verifiedVal;
    if (activeEl) activeEl.textContent = activeVal;
    if (navBadgeEl) navBadgeEl.textContent = pendingVal;

  } catch (err) {
    console.error('Error loading overview metrics:', err);
  }
}

// --------------------------------------------------------------------------
// 2. Counsellor Escalation Intake Queue
// --------------------------------------------------------------------------
let escalationsCache = [];

async function loadCounsellorEscalations(statusFilter = 'all') {
  const container = document.getElementById('escalationsListContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="loading-state-card" style="text-align: center; padding: 36px; color: #5C5574;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.8rem; color: #7E57C2;"></i>
      <p style="margin-top: 12px; font-weight: 600;">Connecting to District Enclave &amp; Fetching Counsellor Escalations...</p>
    </div>
  `;

  try {
    const res = await fetch(`/api/command/counsellor-escalations?status_filter=${statusFilter}`, {
      credentials: 'same-origin'
    });
    if (!res.ok) throw new Error('Failed to fetch counsellor escalations');

    const data = await res.json();
    escalationsCache = data.escalations || [];

    // Update filter counts
    const countAllEl = document.getElementById('countFilterAll');
    const countPendingEl = document.getElementById('countFilterPending');
    const countVerifiedEl = document.getElementById('countFilterVerified');
    const navBadgeEl = document.getElementById('badgeEscalationCount');

    if (countAllEl) countAllEl.textContent = data.total_count ?? escalationsCache.length;
    if (countPendingEl) countPendingEl.textContent = data.pending_count ?? 0;
    if (countVerifiedEl) countVerifiedEl.textContent = data.verified_count ?? 0;
    if (navBadgeEl && data.pending_count !== undefined) navBadgeEl.textContent = data.pending_count;

    renderEscalationCards(escalationsCache, container);

  } catch (err) {
    console.error('Error loading counsellor escalations:', err);
    container.innerHTML = `
      <div style="background: #FEE2E2; border: 1px solid #FECACA; border-radius: 14px; padding: 20px; color: #991B1B; text-align: center;">
        <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.6rem; margin-bottom: 8px;"></i>
        <h4 style="margin: 0 0 6px 0; font-weight: 800;">Unable to load counsellor escalations</h4>
        <p style="margin: 0; font-size: 0.88rem;">Please verify official network session or refresh the page.</p>
      </div>
    `;
  }
}

function renderEscalationCards(items, container) {
  container.innerHTML = '';

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div style="background: #FFFFFF; border: 1px solid rgba(220, 214, 245, 0.9); border-radius: 16px; padding: 40px 20px; text-align: center;">
        <i class="fa-solid fa-circle-check" style="font-size: 2rem; color: #059669; margin-bottom: 10px;"></i>
        <h3 style="color: #2B1552; font-size: 1.15rem; font-weight: 800; margin: 0 0 6px 0;">No Escalations in Selected View</h3>
        <p style="color: #5C5574; font-size: 0.88rem; margin: 0; max-width: 450px; margin: 0 auto;">
          All priority cases escalated by clinical counsellors have been verified and processed by District Administration.
        </p>
      </div>
    `;
    return;
  }

  items.forEach((item) => {
    const isPending = item.verification_status === 'pending';
    const card = document.createElement('div');
    card.className = `escalation-card-item ${isPending ? 'is-pending' : 'is-verified'}`;

    const urgencyBadge = item.urgency === 'critical'
      ? `<span class="badge-urgency-critical"><i class="fa-solid fa-bolt"></i> Critical Escalation</span>`
      : `<span class="badge-urgency-urgent"><i class="fa-solid fa-triangle-exclamation"></i> Urgent Counsellor Escalation</span>`;

    const statusPill = isPending
      ? `<span class="status-pill-pending"><i class="fa-solid fa-clock"></i> Awaiting District Verification</span>`
      : `<span class="status-pill-verified"><i class="fa-solid fa-circle-check"></i> Verified &bull; Order #${item.district_order?.order_reference || 'ENFORCED'}</span>`;

    const actionButton = isPending
      ? `<button type="button" class="btn btn-hero-primary" onclick="openVerificationModal('${item.id}')" style="padding: 9px 22px; font-size: 0.86rem;">
           <i class="fa-solid fa-clipboard-check" style="margin-right: 6px;"></i> Verify &amp; Check Escalation
         </button>`
      : `<button type="button" class="btn btn-secondary-pill" onclick="openOrderSlipModal('${item.id}')" style="padding: 9px 20px; font-size: 0.86rem; border: 1px solid #C4B5FD;">
           <i class="fa-solid fa-file-shield" style="color: #7E57C2; margin-right: 6px;"></i> View Official Order Slip
         </button>`;

    // Factors and Needs Tags
    const factorsHtml = (item.factors || [])
      .map(f => `<span class="factor-tag-pill"><i class="fa-solid fa-tag" style="font-size: 0.68rem;"></i> ${escapeHtml(f)}</span>`)
      .join('');

    const needsHtml = (item.support_needs || [])
      .map(n => `<span class="need-tag-pill"><i class="fa-solid fa-shield-halved" style="font-size: 0.68rem;"></i> ${escapeHtml(n)}</span>`)
      .join('');

    card.innerHTML = `
      <!-- Top Row: Urgency, Case ID, Beneficiary, Timestamp -->
      <div class="card-top-row">
        <div class="card-top-left">
          ${urgencyBadge}
          <span class="badge-case-number">${escapeHtml(item.case_id_masked || 'CASE-***')}</span>
          <span class="badge-beneficiary-tag"><i class="fa-solid fa-user-shield"></i> ${escapeHtml(item.beneficiary_masked || 'Beneficiary')}</span>
        </div>
        <div class="card-timestamp-text">
          <i class="fa-regular fa-clock"></i> ${formatTimeAgo(item.escalated_at)}
        </div>
      </div>

      <!-- Origin Counsellor Banner -->
      <div class="counsellor-origin-banner">
        <div class="counsellor-origin-info">
          <i class="fa-solid fa-user-doctor" style="color: #7E57C2; font-size: 1rem;"></i>
          <span>Escalated by <strong>${escapeHtml(item.counsellor_name || 'Dr. Priya Nair')}</strong> (${escapeHtml(item.counsellor_role || 'Psychological Counsellor')})</span>
        </div>
        <div class="risk-score-chip">
          <i class="fa-solid fa-heart-pulse"></i> Risk Score: ${item.risk_score || 8}/10
        </div>
      </div>

      <!-- Counsellor Clinical Triage Notes Callout -->
      <div class="counsellor-notes-quote-box">
        <div class="quote-label">
          <i class="fa-solid fa-comment-medical"></i> Counsellor's Clinical Triage Assessment &amp; Rationale:
        </div>
        <p class="quote-body-text">
          "${escapeHtml(item.counsellor_notes || 'Immediate district authority protection and statutory review required under Section 15A.')}"
        </p>
        <div class="factors-tags-row">
          ${factorsHtml}
          ${needsHtml}
        </div>
      </div>

      <!-- Bottom Bar: Status & District Verification Action -->
      <div class="card-bottom-bar">
        <div>
          ${statusPill}
        </div>
        <div>
          ${actionButton}
        </div>
      </div>
    `;

    container.appendChild(card);
  });
}

// --------------------------------------------------------------------------
// 3. Verification & Check Modal Actions
// --------------------------------------------------------------------------
window.openVerificationModal = function(itemId) {
  const item = escalationsCache.find(e => e.id === itemId);
  if (!item) return;

  document.getElementById('modalEscalationId').value = item.id;
  document.getElementById('modalTargetType').value = item.target_type || 'support_pulse';
  document.getElementById('modalTargetId').value = item.target_id || item.id;

  document.getElementById('modalVerifyCaseNumber').textContent = item.case_id_masked || 'CASE-***';
  document.getElementById('modalVerifyBeneficiary').textContent = item.beneficiary_masked || 'Beneficiary';
  document.getElementById('modalVerifyCounsellor').textContent = item.counsellor_name || 'Dr. Priya Nair (Lead Counsellor)';
  document.getElementById('modalVerifyTimestamp').textContent = formatDateTime(item.escalated_at);

  const riskEl = document.getElementById('modalVerifyRiskBadge');
  if (riskEl) {
    riskEl.innerHTML = `<span style="color: #B91C1C; font-weight: 800;"><i class="fa-solid fa-triangle-exclamation"></i> ${item.risk_level?.toUpperCase() || 'HIGH'} (Score: ${item.risk_score || 8}/10)</span>`;
  }

  document.getElementById('modalVerifyCounsellorNotes').textContent = item.counsellor_notes || '—';

  const factorsRow = document.getElementById('modalVerifyFactorsRow');
  if (factorsRow) {
    factorsRow.innerHTML = (item.factors || [])
      .concat(item.support_needs || [])
      .map(f => `<span class="factor-tag-pill">${escapeHtml(f)}</span>`)
      .join('');
  }

  // Pre-fill default directives
  const officerInput = document.getElementById('inputAssignedOfficer');
  if (officerInput && !officerInput.value) {
    officerInput.value = 'Inspector K. Saravanan (District SP Protection Cell)';
  }

  const modal = document.getElementById('verifyEscalationModal');
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
};

window.closeVerificationModal = function() {
  const modal = document.getElementById('verifyEscalationModal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
};

// --------------------------------------------------------------------------
// 4. Official Order Slip Modal Actions
// --------------------------------------------------------------------------
window.openOrderSlipModal = function(itemId) {
  const item = escalationsCache.find(e => e.id === itemId);
  if (!item) return;

  const ord = item.district_order || {};
  const orderRef = ord.order_reference || `DIST-ORD-TN-CHN-2026-${itemId.slice(0, 6).toUpperCase()}`;

  document.getElementById('orderSlipReferenceId').textContent = `ORDER REF: #${orderRef}`;
  document.getElementById('slipCaseNumber').textContent = item.case_id_masked || 'CASE-***';
  document.getElementById('slipBeneficiaryName').textContent = item.beneficiary_masked || 'Protected Beneficiary';
  document.getElementById('slipVerifiedBy').textContent = ord.verified_by || (currentUser ? currentUser.full_name : 'Rajesh Varma, IAS');
  document.getElementById('slipDecisionText').textContent = ord.decision_label || 'Section 15A Police Protection Order Dispatched';
  document.getElementById('slipNotesText').textContent = ord.official_notes || 'Verified under Section 15A. SP Protection Cell instructed to deploy security escort.';
  document.getElementById('slipAssignedOfficer').textContent = ord.assigned_officer || 'Inspector K. Saravanan (SP Protection Cell)';
  document.getElementById('slipTimestamp').textContent = ord.verified_at ? formatDateTime(ord.verified_at) : 'Today, Confirmed Active';

  const modal = document.getElementById('officialOrderSlipModal');
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
};

window.closeOrderSlipModal = function() {
  const modal = document.getElementById('officialOrderSlipModal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
};

// --------------------------------------------------------------------------
// 5. Modal Listeners & Submit Verification
// --------------------------------------------------------------------------
function setupModalListeners() {
  // Modal Dismiss buttons
  document.querySelectorAll('.modal-backdrop').forEach((modal) => {
    modal.querySelectorAll('.modal-close-btn, .btn-modal-cancel').forEach((btn) => {
      btn.addEventListener('click', () => {
        modal.style.display = 'none';
        document.body.style.overflow = '';
      });
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
      }
    });
  });

  // Escape key closes modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop').forEach((m) => {
        m.style.display = 'none';
      });
      document.body.style.overflow = '';
    }
  });

  // Submit District Verification Button
  const btnSubmitVerif = document.getElementById('btnSubmitVerification');
  if (btnSubmitVerif) {
    btnSubmitVerif.addEventListener('click', async () => {
      const escalationId = document.getElementById('modalEscalationId').value;
      const targetType = document.getElementById('modalTargetType').value;
      const targetId = document.getElementById('modalTargetId').value;
      const decision = document.getElementById('selectVerificationDecision').value;
      const officer = document.getElementById('inputAssignedOfficer').value.trim();
      const notes = document.getElementById('textareaOfficialNotes').value.trim();

      if (!notes) {
        alert('Please enter official directives and remarks for the order.');
        return;
      }

      btnSubmitVerif.disabled = true;
      btnSubmitVerif.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Issuing Official Order...';

      try {
        const res = await fetch('/api/command/verify-escalation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            escalation_id: escalationId,
            target_type: targetType,
            target_id: targetId,
            verification_decision: decision,
            official_notes: notes,
            assigned_officer: officer,
            statutory_mandate: 'Section 15A & Rule 12'
          })
        });

        if (!res.ok) throw new Error('Failed to record verification');

        const result = await res.json();
        closeVerificationModal();

        // Refresh overview and escalations queue
        await Promise.all([
          loadOverviewMetrics(),
          loadCounsellorEscalations('all')
        ]);

        // Launch Official Order Slip
        setTimeout(() => {
          openOrderSlipModal(escalationId);
        }, 300);

      } catch (err) {
        console.error('Verification error:', err);
        alert('Failed to issue official verification order. Please try again.');
      } finally {
        btnSubmitVerif.disabled = false;
        btnSubmitVerif.innerHTML = '<i class="fa-solid fa-stamp" style="margin-right: 6px;"></i> Issue Official District Order';
      }
    });
  }
}

// --------------------------------------------------------------------------
// Helper Utilities
// --------------------------------------------------------------------------
function formatDateTime(isoStr) {
  if (!isoStr) return 'Just now';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return isoStr;
  }
}

function formatTimeAgo(isoStr) {
  if (!isoStr) return 'Recently';
  try {
    const diffMs = Date.now() - new Date(isoStr).getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  } catch (e) {
    return 'Recently';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showErrorBanner(msg) {
  const container = document.querySelector('.command-main-container');
  if (!container) return;
  const banner = document.createElement('div');
  banner.style.cssText = 'background: #FEE2E2; color: #B91C1C; padding: 14px 20px; border-radius: 12px; font-weight: 700; border: 1px solid #FECACA; margin-bottom: 20px;';
  banner.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="margin-right: 8px;"></i> ${msg}`;
  container.prepend(banner);
}

// Legacy compatibility stubs
async function loadSupportTypeMetrics() {}
async function loadCaseStagesDistribution() {}
async function loadPriorityCases() {}
async function loadDistrictSummary() {}
async function refreshDashboardMetrics() {
  await Promise.all([loadOverviewMetrics(), loadCounsellorEscalations('all')]);
}
