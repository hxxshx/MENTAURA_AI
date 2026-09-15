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
      loadSupportTypeMetrics(),
      loadCaseStagesDistribution(),
      loadPriorityCases(),
      loadDistrictSummary()
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
  const timeSelect = document.getElementById('filterTimeRange');
  const supportSelect = document.getElementById('filterSupportType');
  const stageSelect = document.getElementById('filterCaseStage');
  const priorityBtn = document.getElementById('btnFilterPriorityOnly');

  if (timeSelect) {
    timeSelect.addEventListener('change', (e) => {
      currentFilters.time_range = e.target.value;
      refreshDashboardMetrics();
    });
  }

  if (supportSelect) {
    supportSelect.addEventListener('change', (e) => {
      currentFilters.support_type = e.target.value;
      refreshDashboardMetrics();
    });
  }

  if (stageSelect) {
    stageSelect.addEventListener('change', (e) => {
      currentFilters.case_stage = e.target.value;
      refreshDashboardMetrics();
    });
  }

  if (priorityBtn) {
    priorityBtn.addEventListener('click', () => {
      currentFilters.priority_only = !currentFilters.priority_only;
      priorityBtn.classList.toggle('active', currentFilters.priority_only);
      refreshDashboardMetrics();
    });
  }
}

async function refreshDashboardMetrics() {
  await Promise.all([
    loadOverviewMetrics(),
    loadSupportTypeMetrics(),
    loadPriorityCases()
  ]);
}

// --------------------------------------------------------------------------
// 1. Overview Metrics
// --------------------------------------------------------------------------
async function loadOverviewMetrics() {
  try {
    const params = new URLSearchParams({
      time_range: currentFilters.time_range,
      support_type: currentFilters.support_type,
      case_stage: currentFilters.case_stage,
      priority_only: currentFilters.priority_only
    });

    const res = await fetch(`/api/command/overview?${params.toString()}`, { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to fetch overview metrics');

    const data = await res.json();
    const ov = data.overview;
    const jur = data.jurisdiction;

    const jurTitleEl = document.getElementById('jurisdictionName');
    const jurBadgeEl = document.getElementById('jurisdictionBadge');
    if (jurTitleEl) jurTitleEl.textContent = jur.name;
    if (jurBadgeEl) jurBadgeEl.textContent = jur.scope_label;

    document.getElementById('metricNewPulses').textContent = ov.new_pulses_7d;
    document.getElementById('metricPendingRequests').textContent = ov.pending_requests;
    document.getElementById('metricActiveCases').textContent = ov.active_cases;
    document.getElementById('metricActiveInterventions').textContent = ov.active_interventions;

  } catch (err) {
    console.error('Error loading overview:', err);
    document.getElementById('metricNewPulses').textContent = 'Not available';
    document.getElementById('metricPendingRequests').textContent = 'Not available';
    document.getElementById('metricActiveCases').textContent = 'Not available';
    document.getElementById('metricActiveInterventions').textContent = 'Not available';
  }
}

// --------------------------------------------------------------------------
// 2. Metrics by Support Type
// --------------------------------------------------------------------------
async function loadSupportTypeMetrics() {
  const container = document.getElementById('supportTypesGrid');
  if (!container) return;

  try {
    const res = await fetch('/api/command/metrics-by-support-type?time_range=30d', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to fetch support type metrics');

    const data = await res.json();
    container.innerHTML = '';

    data.categories.forEach((cat) => {
      const isSelected = currentFilters.support_type === cat.category;
      const isDimmed = currentFilters.support_type !== 'all' && !isSelected;

      const card = document.createElement('div');
      card.className = `support-type-card ${isSelected ? 'active-filter-card' : ''} ${isDimmed ? 'dimmed-filter-card' : ''}`;

      const badgeHtml = isSelected ? '<span class="badge-filter-active"><i class="fa-solid fa-check"></i> Filter Active</span>' : '';

      card.innerHTML = `
        <div class="support-card-header">
          <div class="support-card-title">
            <i class="fa-solid ${cat.icon}"></i>
            <span>${cat.category_label}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            ${badgeHtml}
            <span class="support-card-total">${cat.total_30d}</span>
          </div>
        </div>
        <div class="support-progress-bar">
          <div class="support-progress-fill" style="width: ${cat.percentage}%"></div>
        </div>
        <div class="support-breakdown-row">
          <span class="support-breakdown-item">Pending: <span>${cat.pending_count}</span></span>
          <span class="support-breakdown-item">In Progress: <span>${cat.in_progress_count}</span></span>
          <span class="support-breakdown-item">Completed: <span>${cat.completed_count}</span></span>
        </div>
      `;
      container.appendChild(card);
    });

  } catch (err) {
    console.error('Error loading support types:', err);
    container.innerHTML = '<p style="color: #5C5574; font-size: 0.90rem;">Support breakdown not available.</p>';
  }
}

// --------------------------------------------------------------------------
// 3. Case Stage Distribution
// --------------------------------------------------------------------------
async function loadCaseStagesDistribution() {
  const container = document.getElementById('caseStagesList');
  if (!container) return;

  try {
    const res = await fetch('/api/command/cases-by-stage?time_range=30d', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to fetch case stages');

    const data = await res.json();
    container.innerHTML = '';

    data.stages.forEach((stage) => {
      const item = document.createElement('div');
      item.className = 'stage-row-item';
      item.innerHTML = `
        <div class="stage-item-top">
          <span class="stage-item-name">${stage.stage_name}</span>
          <span class="stage-item-count">${stage.case_count} active</span>
        </div>
        <div class="stage-progress-bar">
          <div class="stage-progress-fill" style="width: ${stage.percentage}%; background-color: ${stage.status_color};"></div>
        </div>
      `;
      container.appendChild(item);
    });

  } catch (err) {
    console.error('Error loading case stages:', err);
    container.innerHTML = '<p style="color: #5C5574; font-size: 0.90rem;">Case stage distribution not available.</p>';
  }
}

// --------------------------------------------------------------------------
// 4. Priority Cases
// --------------------------------------------------------------------------
async function loadPriorityCases() {
  const tbody = document.getElementById('priorityCasesTableBody');
  if (!tbody) return;

  try {
    const params = new URLSearchParams({
      priority_only: currentFilters.priority_only,
      support_type: currentFilters.support_type,
      case_stage: currentFilters.case_stage
    });

    const res = await fetch(`/api/command/priority-cases?${params.toString()}`, { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to fetch priority cases');

    const data = await res.json();
    priorityCasesCache = data.priority_cases || [];
    tbody.innerHTML = '';

    if (priorityCasesCache.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 28px; color: #5C5574;">
            <i class="fa-solid fa-circle-check" style="color: #15803D; font-size: 1.4rem; margin-bottom: 6px; display: block;"></i>
            No active priority escalations matching the selected filters.
          </td>
        </tr>
      `;
      return;
    }

    priorityCasesCache.forEach((c) => {
      const tr = document.createElement('tr');
      const badgeClass = c.urgency === 'critical' ? 'badge-urgency-critical' : (c.urgency === 'urgent' ? 'badge-urgency-urgent' : 'badge-urgency-standard');

      let riskBadge = `<span class="badge-risk-low"><i class="fa-solid fa-shield-check"></i> Low</span>`;
      if (c.risk_level === 'high') {
        riskBadge = `<span class="badge-risk-high"><i class="fa-solid fa-triangle-exclamation"></i> High</span>`;
      } else if (c.risk_level === 'medium') {
        riskBadge = `<span class="badge-risk-medium"><i class="fa-solid fa-circle-exclamation"></i> Medium</span>`;
      }

      tr.innerHTML = `
        <td>
          <div style="font-weight: 800; color: #261149;">${c.case_id_masked}</div>
          <div style="font-size: 0.80rem; color: #5C5574;">${c.victim_masked}</div>
        </td>
        <td>${c.district}</td>
        <td>
          <span style="font-weight: 700; color: #2B1552;">${c.current_stage}</span>
        </td>
        <td>${riskBadge}</td>
        <td style="max-width: 260px;">
          <div style="font-size: 0.88rem; color: #2C2245; line-height: 1.4;">${c.priority_reason}</div>
        </td>
        <td>
          <span class="${badgeClass}">
            <i class="fa-solid fa-triangle-exclamation"></i> ${c.urgency.toUpperCase()}
          </span>
        </td>
        <td>
          <div style="font-weight: 700; color: #261149;">${c.assigned_officer}</div>
          <div style="font-size: 0.80rem; color: #7E57C2;">${c.assigned_counsellor}</div>
        </td>
        <td style="text-align: right;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <button type="button" class="btn btn-action-sm btn-view-case" data-id="${c.id}">
              <i class="fa-solid fa-eye"></i> Details
            </button>
            <button type="button" class="btn-action-escalate btn-escalate-case" data-id="${c.id}">
              <i class="fa-solid fa-bolt"></i> Escalate
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // Attach row button events
    tbody.querySelectorAll('.btn-view-case').forEach((btn) => {
      btn.addEventListener('click', () => openCaseDetailModal(btn.dataset.id));
    });

    tbody.querySelectorAll('.btn-escalate-case').forEach((btn) => {
      btn.addEventListener('click', () => openEscalateModal(btn.dataset.id));
    });

  } catch (err) {
    console.error('Error loading priority cases:', err);
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #B91C1C; padding: 20px;">Failed to load priority cases.</td></tr>';
  }
}

// --------------------------------------------------------------------------
// 5. District Summary (State / National View)
// --------------------------------------------------------------------------
async function loadDistrictSummary() {
  const section = document.getElementById('districtSummarySection');
  const tbody = document.getElementById('districtSummaryTableBody');
  if (!section || !tbody) return;

  try {
    const res = await fetch('/api/command/district-summary', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to fetch district summary');

    const data = await res.json();

    // Show section if user is state or national admin, or if visible
    section.style.display = 'block';
    tbody.innerHTML = '';

    data.districts.forEach((d) => {
      const tr = document.createElement('tr');
      const statusPill = d.status === 'healthy' 
        ? '<span class="status-pill-healthy"><i class="fa-solid fa-circle-check"></i> Normal</span>'
        : '<span class="status-pill-attention"><i class="fa-solid fa-triangle-exclamation"></i> High Load</span>';

      tr.innerHTML = `
        <td>
          <div style="font-weight: 800; color: #261149;">${d.district_name}</div>
          <div style="font-size: 0.78rem; color: #7E57C2;">Code: ${d.district_code}</div>
        </td>
        <td style="font-weight: 700; color: #2B1552;">${d.new_pulses_30d}</td>
        <td style="font-weight: 700; color: #92400E;">${d.pending_requests}</td>
        <td style="font-weight: 700; color: #1E3A8A;">${d.active_cases}</td>
        <td style="font-weight: 700; color: #15803D;">${d.active_interventions}</td>
        <td>${statusPill}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error('Error loading district summary:', err);
    if (section) section.style.display = 'none';
  }
}

// --------------------------------------------------------------------------
// 6. Modal Handlers (Case Details & Escalation)
// --------------------------------------------------------------------------
function closeModal(modal) {
  if (!modal) return;
  modal.style.display = 'none';
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  document.body.classList.remove('modal-open');
}

function openModal(modal) {
  if (!modal) return;
  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  document.body.classList.add('modal-open');
}

function setupModalListeners() {
  const caseModal = document.getElementById('caseDetailModal');
  const escalateModal = document.getElementById('escalateModal');

  // Close buttons on all modals
  document.querySelectorAll('.modal-backdrop').forEach((modal) => {
    modal.querySelectorAll('.modal-close-btn, .btn-modal-cancel').forEach((btn) => {
      btn.addEventListener('click', () => {
        closeModal(modal);
      });
    });

    // Dismiss on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal(modal);
      }
    });
  });

  // Keyboard accessibility (Escape key)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop').forEach((m) => {
        closeModal(m);
      });
    }
  });

  // Submit Escalation Action
  const btnSubmitEscalate = document.getElementById('btnSubmitEscalateAction');
  if (btnSubmitEscalate) {
    btnSubmitEscalate.addEventListener('click', async () => {
      const caseId = document.getElementById('modalEscalateCaseId').value;
      const level = document.getElementById('selectEscalateLevel').value;
      const reason = document.getElementById('inputEscalateReason').value.trim();
      const officer = document.getElementById('inputEscalateOfficer').value.trim();
      const notes = document.getElementById('textareaEscalateNotes').value.trim();

      if (!reason) {
        alert('Please enter a reason for escalation.');
        return;
      }

      btnSubmitEscalate.disabled = true;
      btnSubmitEscalate.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Escalating...';

      try {
        const res = await fetch('/api/command/escalate-case', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            case_id: caseId,
            escalation_level: level,
            reason: reason,
            assigned_officer: officer || currentUser.full_name,
            notes: notes
          })
        });

        if (!res.ok) throw new Error('Failed to record escalation');

        const result = await res.json();
        alert(result.message || 'Case escalated successfully.');
        closeModal(escalateModal);

        // Refresh overview and priority list
        await refreshDashboardMetrics();

      } catch (err) {
        console.error('Escalation error:', err);
        alert('Failed to escalate case. Please try again.');
      } finally {
        btnSubmitEscalate.disabled = false;
        btnSubmitEscalate.innerHTML = '<i class="fa-solid fa-bolt"></i> Confirm Escalation';
      }
    });
  }
}

function openCaseDetailModal(caseId) {
  const c = priorityCasesCache.find((item) => item.id === caseId);
  if (!c) return;

  document.getElementById('modalCaseDetailNumber').textContent = c.case_id_masked;
  document.getElementById('modalCaseDetailVictim').textContent = c.victim_masked;
  document.getElementById('modalCaseDetailDistrict').textContent = c.district;
  document.getElementById('modalCaseDetailStage').textContent = c.current_stage;
  document.getElementById('modalCaseDetailOfficer').textContent = c.assigned_officer;
  document.getElementById('modalCaseDetailCounsellor').textContent = c.assigned_counsellor;
  document.getElementById('modalCaseDetailPriorityReason').textContent = c.priority_reason;

  const timelineContainer = document.getElementById('modalCaseTimelineList');
  if (timelineContainer && c.timeline) {
    timelineContainer.innerHTML = '';
    c.timeline.forEach((event) => {
      const li = document.createElement('li');
      li.className = 'modal-timeline-item';
      li.innerHTML = `
        <span class="modal-timeline-date"><i class="fa-solid fa-clock"></i> ${event.date}</span>
        <span>${event.event}</span>
      `;
      timelineContainer.appendChild(li);
    });
  }

  const modal = document.getElementById('caseDetailModal');
  openModal(modal);
}

function openEscalateModal(caseId) {
  const c = priorityCasesCache.find((item) => item.id === caseId);
  if (!c) return;

  document.getElementById('modalEscalateCaseId').value = c.id;
  document.getElementById('modalEscalateCaseNumber').textContent = c.case_id_masked;
  document.getElementById('modalEscalateDistrict').textContent = c.district;
  document.getElementById('inputEscalateReason').value = c.priority_reason;
  document.getElementById('inputEscalateOfficer').value = c.assigned_officer;

  const modal = document.getElementById('escalateModal');
  openModal(modal);
}

function showErrorBanner(msg) {
  const container = document.querySelector('.command-main-container');
  if (!container) return;
  const banner = document.createElement('div');
  banner.style.cssText = 'background: #FEE2E2; color: #B91C1C; padding: 14px 20px; border-radius: 12px; font-weight: 700; border: 1px solid #FECACA;';
  banner.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="margin-right: 8px;"></i> ${msg}`;
  container.prepend(banner);
}
