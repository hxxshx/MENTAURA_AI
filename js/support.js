/**
 * MENTAURA — MY SUPPORT (Client Script)
 * Handles authenticated session validation, fetches read-only support requests,
 * renders summary overview, available categories, request cards, and details modal.
 */

let cachedSupportRequests = [];

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Authenticated Role Guard
  const user = await initAuthGuard(['victim', 'witness', 'affected_family_member']);
  if (!user) return; // Guard will handle redirect

  // 2. Setup Navbar Controls (Popover, Language Selector, Mobile Drawer)
  setupProfilePopover(user);
  setupLanguageSelector(user);
  setupMobileDrawer();

  // 3. Setup Modal Close Handlers
  setupModalHandlers();

  // 4. Fetch & Render Support Data
  await loadSupportData();
});

/**
 * Loads read-only support data from secure backend endpoint.
 */
async function loadSupportData() {
  const loadingIndicator = document.getElementById('supportLoadingIndicator');
  const errorBanner = document.getElementById('supportErrorBanner');
  const mainContent = document.getElementById('supportContentArea');

  try {
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    if (errorBanner) errorBanner.style.display = 'none';

    const response = await fetch('/api/victim/support', {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}`);
    }

    const data = await response.json();

    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (mainContent) mainContent.style.display = 'flex';

    cachedSupportRequests = data.requests || [];

    renderSupportSummary(data.summary || {});
    renderSupportRequests(data.requests || []);
    renderCategoriesGrid(data.available_categories || []);

  } catch (error) {
    console.error('Failed to load support data:', error);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorBanner) {
      errorBanner.style.display = 'block';
      errorBanner.textContent = 'We could not load your support requests right now. Please try again later or contact your authorised support team.';
    }
  }
}

/**
 * Renders the 3 overview counters.
 */
function renderSupportSummary(summary) {
  const activeEl = document.getElementById('summaryActiveCount');
  const underReviewEl = document.getElementById('summaryUnderReviewCount');
  const completedEl = document.getElementById('summaryCompletedCount');

  if (activeEl) activeEl.textContent = summary.active_requests ?? 0;
  if (underReviewEl) underReviewEl.textContent = summary.under_review ?? 0;
  if (completedEl) completedEl.textContent = summary.completed ?? 0;
}

/**
 * Renders the list of active support requests or clean empty state.
 */
function renderSupportRequests(requests) {
  const container = document.getElementById('supportRequestsListContainer');
  if (!container) return;

  if (requests.length === 0) {
    container.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-state-icon">
          <i class="fa-solid fa-hands-holding-child"></i>
        </div>
        <div class="empty-state-title">No active support requests yet.</div>
        <div class="empty-state-desc">When you need support, you can request it through a Support Pulse. Your request will be reviewed by authorised personnel.</div>
        <a href="checkin.html" class="btn btn-hero-primary" style="padding: 8px 22px; font-size: 0.88rem; display: inline-flex;">
          <i class="fa-solid fa-plus" style="margin-right: 6px;"></i> Start a Support Pulse
        </a>
      </div>
    `;
    return;
  }

  container.innerHTML = requests.map((req, index) => {
    const iconClass = req.icon_class || 'fa-solid fa-hands-holding-child';
    const badgeClass = req.status_badge_class || 'badge-under-review';

    return `
      <div class="request-card-item">
        <div class="request-card-header">
          <div class="request-title-box">
            <div class="request-type-icon">
              <i class="${escapeHtml(iconClass)}"></i>
            </div>
            <div>
              <div class="request-main-title">${escapeHtml(req.support_type)}</div>
              <div class="request-meta-date">Submitted: ${escapeHtml(req.submitted_date_display || 'Recently')}</div>
            </div>
          </div>
          <div>
            <span class="status-badge ${badgeClass}">
              <i class="fa-solid fa-clock"></i> ${escapeHtml(req.status_display || req.status)}
            </span>
          </div>
        </div>

        <div class="request-card-body">
          <div class="request-next-step-snippet">
            <i class="fa-solid fa-arrow-right-long" style="color: #7E57C2;"></i>
            <span>Next: ${escapeHtml(req.next_step || 'Awaiting authorised review')}</span>
          </div>
          <button type="button" class="btn-view-details" onclick="openRequestDetailsModal(${index})" aria-label="View details for ${escapeHtml(req.support_type)}">
            View details <i class="fa-solid fa-chevron-right" style="font-size: 0.70rem; margin-left: 2px;"></i>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Renders the 6 support category cards.
 */
function renderCategoriesGrid(categories) {
  const container = document.getElementById('categoriesGridContainer');
  if (!container) return;

  container.innerHTML = categories.map((cat) => {
    return `
      <div class="category-card">
        <div>
          <div class="category-header">
            <div class="category-icon-badge">
              <i class="${escapeHtml(cat.icon)}"></i>
            </div>
            <h3 class="category-title">${escapeHtml(cat.title)}</h3>
          </div>
          <p class="category-desc" style="margin-top: 6px;">${escapeHtml(cat.description)}</p>
        </div>
        <div>
          <a href="${escapeHtml(cat.action_url)}" class="category-action-link">
            <span>${escapeHtml(cat.action_label)}</span>
            <i class="fa-solid fa-arrow-right" style="font-size: 0.72rem;"></i>
          </a>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Opens the Request Details Modal with safe authorized fields & status timeline.
 */
function openRequestDetailsModal(reqIndex) {
  const req = cachedSupportRequests[reqIndex];
  if (!req) return;

  const modal = document.getElementById('requestDetailsModal');
  if (!modal) return;

  // Title & Icon
  const modalTitle = document.getElementById('modalTitle');
  const modalSub = document.getElementById('modalSubmittedDate');
  const modalCategoryIcon = document.getElementById('modalCategoryIcon');
  const modalStatusBadge = document.getElementById('modalStatusBadge');
  const modalLastUpdatedBox = document.getElementById('modalLastUpdatedBox');
  const modalNextStepText = document.getElementById('modalNextStepText');
  const modalTimeline = document.getElementById('modalStatusTimeline');
  const modalAppointmentSection = document.getElementById('modalAppointmentSection');
  const modalAppointmentContent = document.getElementById('modalAppointmentContent');

  if (modalTitle) modalTitle.textContent = req.support_type;
  if (modalSub) modalSub.textContent = `Submitted: ${req.submitted_date_display || 'Recently'}`;
  
  if (modalCategoryIcon) {
    modalCategoryIcon.innerHTML = `<i class="${escapeHtml(req.icon_class || 'fa-solid fa-hands-holding-child')}"></i>`;
  }

  // Status & Badge
  if (modalStatusBadge) {
    modalStatusBadge.className = `status-badge ${req.status_badge_class || 'badge-under-review'}`;
    modalStatusBadge.innerHTML = `<i class="fa-solid fa-clock"></i> ${escapeHtml(req.status_display || req.status)}`;
  }

  if (modalLastUpdatedBox) {
    if (req.last_updated_display) {
      modalLastUpdatedBox.textContent = `Last updated: ${req.last_updated_display}`;
    } else {
      modalLastUpdatedBox.textContent = '';
    }
  }

  // Status Timeline (Backend Confirmed)
  if (modalTimeline && req.status_timeline) {
    modalTimeline.innerHTML = req.status_timeline.map((step) => {
      let icon = '';
      if (step.state === 'completed') {
        icon = '<i class="fa-solid fa-check"></i>';
      } else if (step.state === 'active') {
        icon = '<i class="fa-solid fa-circle-dot"></i>';
      } else {
        icon = '<i class="fa-regular fa-circle"></i>';
      }

      return `
        <div class="timeline-step ${escapeHtml(step.state)}">
          <div class="timeline-node">${icon}</div>
          <span class="timeline-step-label">${escapeHtml(step.label)}</span>
        </div>
      `;
    }).join('');
  }

  // Next Steps
  if (modalNextStepText) {
    modalNextStepText.textContent = req.next_step || 'An authorised support person will review the request and update its status when appropriate.';
  }

  // Authorized Appointment / Assignment Details (only if backend confirmed)
  if (modalAppointmentSection && modalAppointmentContent) {
    if (req.appointment_display || req.assigned_role_display) {
      modalAppointmentSection.style.display = 'block';
      let infoHtml = '';
      if (req.assigned_role_display) {
        infoHtml += `<p style="margin: 0 0 6px; font-size: 0.86rem; color: #2B1552;"><strong>Assigned support:</strong> ${escapeHtml(req.assigned_role_display)}</p>`;
      }
      if (req.appointment_display) {
        infoHtml += `<p style="margin: 0; font-size: 0.86rem; color: #2B1552;"><strong>Confirmed appointment:</strong> ${escapeHtml(req.appointment_display)}</p>`;
      }
      modalAppointmentContent.innerHTML = infoHtml;
    } else {
      modalAppointmentSection.style.display = 'none';
      modalAppointmentContent.innerHTML = '';
    }
  }

  // Show Modal
  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

/**
 * Closes the modal.
 */
function closeRequestDetailsModal() {
  const modal = document.getElementById('requestDetailsModal');
  if (!modal) return;
  modal.style.display = 'none';
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

/**
 * Sets up modal close listeners.
 */
function setupModalHandlers() {
  const modal = document.getElementById('requestDetailsModal');
  const closeBtn = document.getElementById('modalCloseBtn');
  const closeActionBtn = document.getElementById('modalCloseActionBtn');

  if (closeBtn) closeBtn.addEventListener('click', closeRequestDetailsModal);
  if (closeActionBtn) closeActionBtn.addEventListener('click', closeRequestDetailsModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeRequestDetailsModal();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeRequestDetailsModal();
    }
  });
}

/**
 * Setup Profile Popover modal dropdown.
 */
function setupProfilePopover(user) {
  const profileBtn = document.getElementById('userProfileBtn');
  const popover = document.getElementById('userProfilePopover');
  const popoverCloseBtn = document.getElementById('popoverCloseBtn');
  const popoverCloseActionBtn = document.getElementById('popoverCloseActionBtn');
  const navUserName = document.getElementById('navUserName');

  if (navUserName && user.full_name) {
    navUserName.textContent = user.full_name.split(' ')[0];
  }

  // Populate popover fields
  const popoverName = document.getElementById('popoverName');
  const popoverUserRole = document.getElementById('popoverUserRole');
  const popoverAccountType = document.getElementById('popoverAccountType');
  const popoverLang = document.getElementById('popoverLang');
  const popoverChannel = document.getElementById('popoverChannel');
  const popoverStatus = document.getElementById('popoverStatus');

  if (popoverName) popoverName.textContent = user.full_name;
  if (popoverUserRole) popoverUserRole.textContent = formatRole(user.verified_role);
  if (popoverAccountType) popoverAccountType.textContent = formatRole(user.requested_category || user.verified_role);
  if (popoverLang) popoverLang.textContent = `${user.preferred_language || 'EN'}`;
  if (popoverChannel) popoverChannel.textContent = user.preferred_channel === 'web' ? 'Web Portal' : user.preferred_channel;
  if (popoverStatus) popoverStatus.textContent = formatStatus(user.account_status);

  if (profileBtn && popover) {
    profileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = profileBtn.getAttribute('aria-expanded') === 'true';
      profileBtn.setAttribute('aria-expanded', !isExpanded);
      popover.classList.toggle('show', !isExpanded);
    });

    document.addEventListener('click', (e) => {
      if (!popover.contains(e.target) && !profileBtn.contains(e.target)) {
        profileBtn.setAttribute('aria-expanded', 'false');
        popover.classList.remove('show');
      }
    });

    if (popoverCloseBtn) {
      popoverCloseBtn.addEventListener('click', () => {
        profileBtn.setAttribute('aria-expanded', 'false');
        popover.classList.remove('show');
      });
    }

    if (popoverCloseActionBtn) {
      popoverCloseActionBtn.addEventListener('click', () => {
        profileBtn.setAttribute('aria-expanded', 'false');
        popover.classList.remove('show');
      });
    }
  }
}

/**
 * Setup Language dropdown.
 */
function setupLanguageSelector(user) {
  const langBtn = document.getElementById('langSelectorBtn');
  const langDropdown = document.getElementById('langDropdown');
  const selectedLangText = document.getElementById('selectedLangText');

  if (selectedLangText && user.preferred_language) {
    selectedLangText.textContent = user.preferred_language;
  }

  if (langBtn && langDropdown) {
    langBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = langBtn.getAttribute('aria-expanded') === 'true';
      langBtn.setAttribute('aria-expanded', !isExpanded);
      langDropdown.classList.toggle('show', !isExpanded);
    });

    document.addEventListener('click', (e) => {
      if (!langDropdown.contains(e.target) && !langBtn.contains(e.target)) {
        langBtn.setAttribute('aria-expanded', 'false');
        langDropdown.classList.remove('show');
      }
    });

    langDropdown.querySelectorAll('li[data-lang]').forEach(item => {
      item.addEventListener('click', () => {
        const lang = item.getAttribute('data-lang');
        if (selectedLangText) selectedLangText.textContent = lang;
        langDropdown.querySelectorAll('li').forEach(li => li.classList.remove('active'));
        item.classList.add('active');
        langBtn.setAttribute('aria-expanded', 'false');
        langDropdown.classList.remove('show');
      });
    });
  }
}

/**
 * Setup Mobile hamburger menu drawer.
 */
function setupMobileDrawer() {
  const toggleBtn = document.getElementById('mobileMenuToggle');
  const drawer = document.getElementById('mobileMenuDrawer') || document.getElementById('mobileDrawer');

  if (toggleBtn && drawer) {
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      drawer.classList.toggle('open');
      toggleBtn.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (!drawer.contains(e.target) && !toggleBtn.contains(e.target)) {
        drawer.classList.remove('open');
        toggleBtn.classList.remove('active');
      }
    });
  }
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
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
