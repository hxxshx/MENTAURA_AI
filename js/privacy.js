/**
 * MENTAURA — Privacy & Consent Page JavaScript
 * Authentic data rendering, session capability checks, and accessible controls.
 */

// Helper: Escape HTML
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

// Helper: Format ISO date string into readable date & time
function formatDateTime(isoString) {
  if (!isoString) return 'Not available';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return 'Not available';
    return d.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return 'Not available';
  }
}

// Helper: Map channel key to user-friendly label
function formatChannelLabel(ch) {
  if (!ch) return 'Web Portal';
  const c = String(ch).toLowerCase();
  if (c === 'web' || c === 'web_portal') return 'Web Portal';
  if (c === 'sms') return 'SMS Notifications';
  if (c === 'ivrs' || c === 'voice') return 'IVRS Voice Calls';
  if (c === 'app' || c === 'mobile') return 'Mobile App';
  if (c === 'helpline') return 'Helpline Follow-up';
  return ch.charAt(0).toUpperCase() + ch.slice(1);
}

// Helper: Map language code to friendly label
function formatLanguageLabel(lang) {
  if (!lang) return 'English (EN)';
  const l = String(lang).toUpperCase();
  if (l === 'EN') return 'English (EN)';
  if (l === 'HI') return 'Hindi (HI)';
  if (l === 'TA') return 'Tamil (TA)';
  if (l === 'TE') return 'Telugu (TE)';
  if (l === 'BN') return 'Bengali (BN)';
  if (l === 'MR') return 'Marathi (MR)';
  return lang;
}

// Helper: Map processing mode to friendly label
function formatProcessingMode(mode) {
  if (!mode || mode === 'not_selected') return 'Not yet submitted';
  if (mode === 'ai_assisted') return 'AI-assisted support';
  if (mode === 'human_review_only') return 'Human review only';
  return mode;
}

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Authenticated Role Guard
  const user = await initAuthGuard(['victim', 'witness', 'affected_family_member']);
  if (!user) return; // Guard will handle redirect if unauthenticated

  // 2. Setup Navbar Controls (Popover, Language Selector, Mobile Drawer)
  setupProfilePopover(user);
  setupLanguageSelector(user);
  setupMobileDrawer();

  // 3. Load Authentic Privacy & Consent Data from Backend
  await loadPrivacyConsentData();

  // 4. Setup Modal Handlers
  setupPrivacyContactModal();
});

/**
 * Loads authentic privacy and consent data from the protected backend endpoint.
 */
async function loadPrivacyConsentData() {
  try {
    const res = await fetch('/api/victim/privacy-consent', {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      },
      credentials: 'include'
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        window.location.href = 'index.html';
        return;
      }
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    renderPrivacyPageData(data);
  } catch (err) {
    console.warn('Could not load dynamic privacy-consent data:', err);
    // Render graceful fallback without fabricating fake information
    renderPrivacyFallback();
  }
}

/**
 * Populates all dynamic fields on the Privacy & Consent page using real backend data.
 */
function renderPrivacyPageData(data) {
  const account = data.account || {};
  const processingChoice = data.processing_choice || 'not_selected';
  const consentRecords = data.consent_records || [];
  const capabilities = data.capabilities || {};
  const contact = data.contact || {};

  // 1. Summary Card Statuses
  const summaryProcessingValue = document.getElementById('summaryProcessingValue');
  if (summaryProcessingValue) {
    const modeLabel = formatProcessingMode(processingChoice);
    summaryProcessingValue.textContent = modeLabel;
  }

  // 2. Current Recorded Processing Choice Badge
  const activeProcessingChoiceChip = document.getElementById('activeProcessingChoiceChip');
  if (activeProcessingChoiceChip) {
    activeProcessingChoiceChip.innerHTML = `
      <i class="fa-solid fa-circle-check" style="color: #7E57C2;"></i>
      <span>Current recorded choice: <strong>${escapeHtml(formatProcessingMode(processingChoice))}</strong></span>
    `;
  }

  // 3. Current Privacy Controls List
  renderControlsList(capabilities);

  // 4. Consent Records Section
  renderConsentRecords(consentRecords);

  // 5. Communication Preferences Section
  const prefLanguageVal = document.getElementById('prefLanguageVal');
  const prefChannelVal = document.getElementById('prefChannelVal');
  if (prefLanguageVal) {
    prefLanguageVal.textContent = formatLanguageLabel(account.preferred_language);
  }
  if (prefChannelVal) {
    prefChannelVal.textContent = formatChannelLabel(account.preferred_channel);
  }

  // 6. Contact Support Info
  const contactUnitName = document.getElementById('contactUnitName');
  const contactEmailLink = document.getElementById('contactEmailLink');
  if (contactUnitName && contact.unit_name) {
    contactUnitName.textContent = contact.unit_name;
  }
  if (contactEmailLink && contact.support_email) {
    contactEmailLink.textContent = contact.support_email;
    contactEmailLink.href = `mailto:${contact.support_email}?subject=Mentaura%20Privacy%20Inquiry`;
  }
}

/**
 * Renders the status of all current system privacy controls.
 */
function renderControlsList(capabilities) {
  const controlsContainer = document.getElementById('privacyControlsGrid');
  if (!controlsContainer) return;

  const controls = [
    {
      name: 'Role-based access',
      icon: 'fa-solid fa-shield-halved',
      isImplemented: capabilities.role_based_access !== false
    },
    {
      name: 'Authenticated session protection',
      icon: 'fa-solid fa-key',
      isImplemented: capabilities.authenticated_sessions !== false
    },
    {
      name: 'Consent capture for Support Pulse',
      icon: 'fa-solid fa-clipboard-check',
      isImplemented: capabilities.support_pulse_consent !== false
    },
    {
      name: 'AI-assisted vs Human-review choice',
      icon: 'fa-solid fa-sliders',
      isImplemented: capabilities.processing_choice !== false
    },
    {
      name: 'Audit logging & security events',
      icon: 'fa-solid fa-list-check',
      isImplemented: capabilities.audit_logs !== false
    },
    {
      name: 'Self-service consent withdrawal',
      icon: 'fa-solid fa-ban',
      isImplemented: capabilities.consent_withdrawal === true
    },
    {
      name: 'Automated data export',
      icon: 'fa-solid fa-file-export',
      isImplemented: capabilities.data_export === true
    },
    {
      name: 'Automated data deletion request',
      icon: 'fa-solid fa-trash-can',
      isImplemented: capabilities.data_deletion_request === true
    }
  ];

  controlsContainer.innerHTML = controls.map(c => `
    <div class="control-item-row">
      <div class="control-name">
        <i class="${escapeHtml(c.icon)}" aria-hidden="true"></i>
        <span>${escapeHtml(c.name)}</span>
      </div>
      <span class="control-status-badge ${c.isImplemented ? 'control-status-implemented' : 'control-status-pending'}">
        <i class="fa-solid ${c.isImplemented ? 'fa-check' : 'fa-clock'}" aria-hidden="true"></i>
        <span>${c.isImplemented ? 'Implemented' : 'Not yet available'}</span>
      </span>
    </div>
  `).join('');
}

/**
 * Renders verified consent records.
 */
function renderConsentRecords(consentRecords) {
  const container = document.getElementById('consentRecordsContainer');
  if (!container) return;

  if (!consentRecords || consentRecords.length === 0) {
    container.innerHTML = `
      <div class="empty-consent-box">
        <i class="fa-solid fa-circle-info" style="font-size: 1.3rem; color: #7E57C2; margin-bottom: 6px;"></i>
        <div>Your consent record will appear here when consent history is connected to this account.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = consentRecords.map(rec => `
    <div class="consent-record-box">
      <div class="consent-record-header">
        <span class="consent-record-title">
          <i class="fa-solid fa-file-signature" style="color: #7E57C2; margin-right: 6px;"></i>
          ${escapeHtml(rec.consent_type_label || 'Account & Support Processing')}
        </span>
        <span class="status-pill-active" style="font-size: 0.76rem;">
          <i class="fa-solid fa-circle-check" style="margin-right: 4px;"></i>${escapeHtml(rec.status || 'Active')}
        </span>
      </div>
      <div class="consent-record-meta">
        <div><strong>Version:</strong> ${escapeHtml(rec.consent_version || '1.0')} (Notice v${escapeHtml(rec.notice_version || '1.0')})</div>
        <div><strong>Recorded:</strong> ${escapeHtml(formatDateTime(rec.given_at))}</div>
      </div>
      <div class="consent-record-purpose">
        <strong>Purpose:</strong> ${escapeHtml(rec.purpose || 'Role-appropriate support processing.')}
      </div>
    </div>
  `).join('');
}

/**
 * Fallback renderer when dynamic endpoint fails.
 */
function renderPrivacyFallback() {
  const summaryProcessingValue = document.getElementById('summaryProcessingValue');
  if (summaryProcessingValue) {
    summaryProcessingValue.textContent = 'Not available';
  }

  const activeProcessingChoiceChip = document.getElementById('activeProcessingChoiceChip');
  if (activeProcessingChoiceChip) {
    activeProcessingChoiceChip.innerHTML = `
      <i class="fa-solid fa-circle-info" style="color: #7E57C2;"></i>
      <span>Current recorded choice: <strong>Not available</strong></span>
    `;
  }

  renderControlsList({
    role_based_access: true,
    authenticated_sessions: true,
    support_pulse_consent: true,
    processing_choice: true,
    audit_logs: true,
    consent_withdrawal: false,
    data_export: false,
    data_deletion_request: false
  });

  const container = document.getElementById('consentRecordsContainer');
  if (container) {
    container.innerHTML = `
      <div class="empty-consent-box">
        <i class="fa-solid fa-circle-info" style="font-size: 1.3rem; color: #7E57C2; margin-bottom: 6px;"></i>
        <div>Your consent record will appear here when consent history is connected to this account.</div>
      </div>
    `;
  }
}

/**
 * Setup Privacy Contact Modal Dialog
 */
function setupPrivacyContactModal() {
  const openBtn = document.getElementById('openPrivacyContactBtn');
  const modal = document.getElementById('privacyContactModal');
  const closeBtn = document.getElementById('closePrivacyContactBtn');
  const closeActionBtn = document.getElementById('closePrivacyContactActionBtn');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.style.display = 'flex';
      modal.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    });
  }

  function closeModal() {
    if (modal) {
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (closeActionBtn) closeActionBtn.addEventListener('click', closeModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && modal.style.display === 'flex') {
      closeModal();
    }
  });
}

/**
 * Setup Profile Popover
 */
function setupProfilePopover(user) {
  const triggerBtn = document.getElementById('userProfileChip');
  const popover = document.getElementById('userProfilePopover');
  const closeBtn = document.getElementById('popoverCloseBtn');
  const closeActionBtn = document.getElementById('popoverCloseActionBtn');

  if (!triggerBtn || !popover) return;

  const fullNameEl = document.getElementById('popoverFullName');
  const categoryEl = document.getElementById('popoverCategory');
  const roleEl = document.getElementById('popoverRole');
  const emailEl = document.getElementById('popoverEmail');
  const langEl = document.getElementById('popoverLanguage');
  const navUserName = document.getElementById('navUserName');

  if (user) {
    if (navUserName) navUserName.textContent = user.full_name || 'Victim Space';
    if (fullNameEl) fullNameEl.textContent = user.full_name || 'Victim Space';
    if (categoryEl) categoryEl.textContent = user.requested_category || 'victim_complainant';
    if (roleEl) roleEl.textContent = (user.verified_role || 'victim').toUpperCase();
    if (emailEl) emailEl.textContent = user.email || '—';
    if (langEl) langEl.textContent = user.preferred_language || 'EN';
  }

  function togglePopover(show) {
    const isShowing = show !== undefined ? show : !popover.classList.contains('show');
    popover.classList.toggle('show', isShowing);
    triggerBtn.setAttribute('aria-expanded', isShowing ? 'true' : 'false');
  }

  triggerBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePopover();
  });

  if (closeBtn) closeBtn.addEventListener('click', () => togglePopover(false));
  if (closeActionBtn) closeActionBtn.addEventListener('click', () => togglePopover(false));

  document.addEventListener('click', (e) => {
    if (!popover.contains(e.target) && !triggerBtn.contains(e.target)) {
      togglePopover(false);
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') togglePopover(false);
  });
}

/**
 * Setup Language Selector
 */
function setupLanguageSelector(user) {
  const btn = document.getElementById('langSelectBtn');
  const dropdown = document.getElementById('langDropdown');
  const currentLangLabel = document.getElementById('currentLangLabel');

  if (!btn || !dropdown) return;

  if (user && user.preferred_language && currentLangLabel) {
    currentLangLabel.textContent = user.preferred_language.toUpperCase();
  }

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('show');
    btn.setAttribute('aria-expanded', dropdown.classList.contains('show') ? 'true' : 'false');
  });

  dropdown.querySelectorAll('li').forEach(item => {
    item.addEventListener('click', () => {
      const selectedLang = item.getAttribute('data-lang');
      if (selectedLang && currentLangLabel) {
        currentLangLabel.textContent = selectedLang.toUpperCase();
      }
      dropdown.querySelectorAll('li').forEach(li => li.classList.remove('active'));
      item.classList.add('active');
      dropdown.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    });
  });

  document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
      dropdown.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
}

/**
 * Setup Mobile Menu Drawer
 */
function setupMobileDrawer() {
  const toggleBtn = document.getElementById('mobileMenuToggle');
  const drawer = document.getElementById('mobileMenuDrawer');

  if (!toggleBtn || !drawer) return;

  toggleBtn.addEventListener('click', () => {
    const isOpen = drawer.classList.contains('open');
    drawer.classList.toggle('open', !isOpen);
    toggleBtn.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
    const icon = toggleBtn.querySelector('i');
    if (icon) {
      icon.className = !isOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
    }
  });
}
