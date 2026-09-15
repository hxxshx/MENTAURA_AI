/**
 * MENTAURA — RESOURCES & SUPPORT INFORMATION (Client Script)
 * Handles role-based authentication guard, structured resource rendering,
 * search filtering, category filtering, and accessible detail modal.
 */

// Structured Approved Resources Dataset (Multilingual-ready structure)
const APPROVED_RESOURCES = [
  {
    id: "case-journey-support",
    category_id: "case_journey",
    category_label: "Case journey",
    icon: "fa-solid fa-timeline",
    title: "Understanding the support journey",
    description: "Learn about the stages of complaint support, investigation updates, authorised case information, compensation, rehabilitation, and follow-up.",
    sections: [
      "Support onboarding & account verification.",
      "Investigation-stage updates recorded by authorised personnel.",
      "Hearing or case-event updates when linked to your account.",
      "Compensation and welfare follow-up tracking.",
      "Rehabilitation and future longitudinal support."
    ],
    note: "Available case information depends on authorisation and case linking.",
    action_label: "Explore",
    primary_action_url: "case-journey.html",
    primary_action_text: "View My Case Journey"
  },
  {
    id: "legal-welfare-support",
    category_id: "legal_welfare",
    category_label: "Legal and welfare",
    icon: "fa-solid fa-scale-balanced",
    title: "Legal and welfare support",
    description: "Learn about approved legal-aid, relief, compensation, welfare, and case-status support pathways.",
    sections: [
      "Legal-aid support and case-counsel coordination.",
      "Relief and compensation information under atrocity welfare rules.",
      "Welfare assistance and district relief coordination.",
      "Case-status support and authorised updates.",
      "Transport or court-support information where approved."
    ],
    note: "This information is general guidance and does not replace advice from an authorised legal or welfare officer.",
    action_label: "Explore",
    primary_action_url: "my-support.html",
    primary_action_text: "View My Support"
  },
  {
    id: "safety-protection-support",
    category_id: "safety_protection",
    category_label: "Safety and protection",
    icon: "fa-solid fa-shield-halved",
    title: "Safety and protection",
    description: "Learn how to request review of safety, intimidation, protection, or relocation concerns.",
    sections: [
      "Reporting a safety concern securely through Support Pulse.",
      "Requesting authorised protection review from case officers.",
      "Relocation-support information under witness protection schemes.",
      "Safe communication preferences (discrete channels, language choices).",
      "Human follow-up options for immediate review."
    ],
    note: "Mentaura does not make automatic protection decisions. Authorised personnel review support requests.",
    action_label: "Explore",
    primary_action_url: "checkin.html",
    primary_action_text: "Start a Support Pulse"
  },
  {
    id: "medical-counselling-support",
    category_id: "medical_counselling",
    category_label: "Medical and counselling",
    icon: "fa-solid fa-heart-pulse",
    title: "Medical and counselling support",
    description: "Explore approved counselling, medical-referral, and mental-health support pathways.",
    sections: [
      "Counselling support with verified mental-health professionals.",
      "Medical referral and health assessment coordination.",
      "Mental-health professional support and psycho-social care.",
      "Tele-support information if approved by your support team.",
      "How to request human follow-up through Support Pulse."
    ],
    note: "Mentaura does not diagnose or replace medical professionals.",
    action_label: "Explore",
    primary_action_url: "checkin.html",
    primary_action_text: "Request through Support Pulse"
  },
  {
    id: "rehabilitation-recovery-support",
    category_id: "rehabilitation",
    category_label: "Rehabilitation",
    icon: "fa-solid fa-seedling",
    title: "Rehabilitation and recovery support",
    description: "Learn about rehabilitation, social support, financial assistance, and longer-term recovery pathways.",
    sections: [
      "Rehabilitation support and vocational skill guidance.",
      "Financial assistance and relief disbursement follow-up.",
      "Social support and community integration schemes.",
      "Family support and dependent welfare programs.",
      "Follow-up and outcome updates tracked longitudinally."
    ],
    note: "Availability and eligibility must be verified by authorised personnel.",
    action_label: "Explore",
    primary_action_url: "my-support.html",
    primary_action_text: "View My Support"
  },
  {
    id: "privacy-consent-info",
    category_id: "privacy_consent",
    category_label: "Privacy and consent",
    icon: "fa-solid fa-user-lock",
    title: "Privacy and consent",
    description: "Understand what information Mentaura collects, why it is used, and who may access it.",
    sections: [
      "Consent-based monitoring: voluntary participation at all stages.",
      "Role-based access: strict boundaries between victim and official spaces.",
      "AI-assisted versus human-review-only processing choices.",
      "Data minimisation: raw audio and text narratives are kept isolated.",
      "Access permissions & cryptographic session token verification.",
      "Retention and deletion information governed by safety protocols.",
      "How to raise a privacy concern or update preferences anytime."
    ],
    note: "Your data is protected under role-based authorization and cryptographic session management.",
    action_label: "View Privacy & Consent",
    primary_action_url: "privacy-consent.html",
    primary_action_text: "View Privacy & Consent"
  }
];

let currentFilterCategory = "all";
let currentSearchQuery = "";

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Authenticated Role Guard (Allows verified victims and anonymous guest visitors)
  const user = await initAuthGuard(['victim', 'witness', 'affected_family', 'affected_family_member', 'anonymous']);
  if (!user) return; // Guard will handle redirect

  // Display anonymous safety banner if user is in anonymous mode
  if (user.is_anonymous || user.role === 'anonymous' || user.verified_role === 'anonymous') {
    const anonBanner = document.createElement('div');
    anonBanner.className = 'anonymous-notice-banner';
    anonBanner.style.cssText = 'background: #FAF5FF; border-bottom: 1px solid #E9D5FF; color: #581C87; padding: 10px 20px; text-align: center; font-size: 0.88rem; font-weight: 600; display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 10px;';
    anonBanner.innerHTML = `
      <i class="fa-solid fa-user-shield" style="color: #7C3AED; font-size: 1.05rem;"></i>
      <span>You are browsing with <strong>Identity Protection (Anonymous Mode)</strong> active. Your records are safeguarded from disclosure.</span>
    `;
    document.body.insertBefore(anonBanner, document.body.firstChild);
  }

  // 2. Setup Navbar Controls (Popover, Language Selector, Mobile Drawer)
  setupProfilePopover(user);
  setupLanguageSelector(user);
  setupMobileDrawer();

  // 3. Setup Filter & Search Event Listeners
  setupSearchAndFilters();

  // 4. Setup Modal Handlers
  setupModalHandlers();

  // 5. Initial Render
  renderResourcesGrid();
});

/**
 * Renders the filtered and searched resource cards.
 */
function renderResourcesGrid() {
  const container = document.getElementById('resourcesGridContainer');
  const emptyState = document.getElementById('noResourcesEmptyState');
  if (!container) return;

  const filtered = APPROVED_RESOURCES.filter((res) => {
    const matchesCategory = (currentFilterCategory === "all") || (res.category_id === currentFilterCategory);
    
    if (!matchesCategory) return false;

    if (!currentSearchQuery) return true;

    const q = currentSearchQuery.toLowerCase();
    const titleMatch = res.title.toLowerCase().includes(q);
    const descMatch = res.description.toLowerCase().includes(q);
    const catMatch = res.category_label.toLowerCase().includes(q);
    const secMatch = res.sections.some(s => s.toLowerCase().includes(q));

    return titleMatch || descMatch || catMatch || secMatch;
  });

  if (filtered.length === 0) {
    container.innerHTML = '';
    if (emptyState) emptyState.style.display = 'block';
    return;
  }

  if (emptyState) emptyState.style.display = 'none';

  container.innerHTML = filtered.map((res) => {
    return `
      <article class="resource-card" data-id="${escapeHtml(res.id)}" onclick="openResourceDetailModal('${escapeHtml(res.id)}')">
        <div class="resource-card-top">
          <div class="resource-card-header-row">
            <div class="resource-icon-badge">
              <i class="${escapeHtml(res.icon)}"></i>
            </div>
            <span class="resource-category-pill">${escapeHtml(res.category_label)}</span>
          </div>
          <h3 class="resource-card-title">${escapeHtml(res.title)}</h3>
          <p class="resource-card-desc">${escapeHtml(res.description)}</p>
        </div>

        <div class="resource-card-footer">
          <button type="button" class="btn-explore-resource" onclick="event.stopPropagation(); openResourceDetailModal('${escapeHtml(res.id)}')" aria-label="Explore ${escapeHtml(res.title)}">
            <span>${escapeHtml(res.action_label)}</span>
            <i class="fa-solid fa-arrow-right" style="font-size: 0.76rem;"></i>
          </button>
        </div>
      </article>
    `;
  }).join('');
}

/**
 * Setup Search input and Category filter chips listeners.
 */
function setupSearchAndFilters() {
  const searchInput = document.getElementById('resourceSearchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const filterChips = document.querySelectorAll('.filter-chip[data-category]');
  const resetFilterBtn = document.getElementById('resetFilterBtn');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearchQuery = e.target.value.trim();
      if (clearSearchBtn) {
        clearSearchBtn.style.display = currentSearchQuery ? 'flex' : 'none';
      }
      renderResourcesGrid();
    });
  }

  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', () => {
      if (searchInput) {
        searchInput.value = '';
        currentSearchQuery = '';
        clearSearchBtn.style.display = 'none';
        searchInput.focus();
        renderResourcesGrid();
      }
    });
  }

  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-checked', 'false');
      });
      chip.classList.add('active');
      chip.setAttribute('aria-checked', 'true');
      currentFilterCategory = chip.getAttribute('data-category') || 'all';
      renderResourcesGrid();
    });
  });

  if (resetFilterBtn) {
    resetFilterBtn.addEventListener('click', () => {
      currentFilterCategory = 'all';
      currentSearchQuery = '';
      if (searchInput) searchInput.value = '';
      if (clearSearchBtn) clearSearchBtn.style.display = 'none';

      filterChips.forEach(c => {
        const isAll = c.getAttribute('data-category') === 'all';
        c.classList.toggle('active', isAll);
        c.setAttribute('aria-checked', isAll ? 'true' : 'false');
      });

      renderResourcesGrid();
    });
  }
}

/**
 * Opens Resource Detail Modal with full section items and action buttons.
 */
function openResourceDetailModal(resId) {
  const res = APPROVED_RESOURCES.find(r => r.id === resId);
  if (!res) return;

  const modal = document.getElementById('resourceDetailModal');
  if (!modal) return;

  const modalTitle = document.getElementById('modalResourceTitle');
  const modalCategoryName = document.getElementById('modalCategoryName');
  const modalCategoryBadge = document.getElementById('modalCategoryBadge');
  const modalDesc = document.getElementById('modalResourceDesc');
  const modalSectionsList = document.getElementById('modalSectionsList');
  const modalDisclaimerText = document.getElementById('modalDisclaimerText');
  const modalActionButtons = document.getElementById('modalActionButtons');

  if (modalTitle) modalTitle.textContent = res.title;
  if (modalCategoryName) modalCategoryName.textContent = res.category_label;
  if (modalCategoryBadge) {
    modalCategoryBadge.innerHTML = `<i class="${escapeHtml(res.icon)}"></i>`;
  }
  if (modalDesc) modalDesc.textContent = res.description;
  if (modalDisclaimerText) modalDisclaimerText.textContent = res.note;

  if (modalSectionsList) {
    modalSectionsList.innerHTML = res.sections.map(sec => `
      <li>
        <i class="fa-solid fa-circle-check"></i>
        <span>${escapeHtml(sec)}</span>
      </li>
    `).join('');
  }

  if (modalActionButtons) {
    modalActionButtons.innerHTML = `
      <a href="${escapeHtml(res.primary_action_url)}" class="btn btn-hero-primary" style="padding: 9px 22px; font-size: 0.90rem;">
        ${escapeHtml(res.primary_action_text)} <i class="fa-solid fa-arrow-right" style="margin-left: 5px; font-size: 0.78rem;"></i>
      </a>
    `;
  }

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

/**
 * Closes the detail modal.
 */
function closeResourceDetailModal() {
  const modal = document.getElementById('resourceDetailModal');
  if (!modal) return;
  modal.style.display = 'none';
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

/**
 * Sets up modal event listeners.
 */
function setupModalHandlers() {
  const modal = document.getElementById('resourceDetailModal');
  const closeBtn = document.getElementById('modalCloseBtn');
  const closeActionBtn = document.getElementById('modalCloseActionBtn');

  if (closeBtn) closeBtn.addEventListener('click', closeResourceDetailModal);
  if (closeActionBtn) closeActionBtn.addEventListener('click', closeResourceDetailModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeResourceDetailModal();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeResourceDetailModal();
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
