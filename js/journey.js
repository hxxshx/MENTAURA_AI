/**
 * MENTAURA — MY CASE JOURNEY (Client Script)
 * Handles authenticated session validation, fetches read-only case journey data,
 * renders timeline stages, Support Pulse history, and support requests.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Authenticated Role Guard
  const user = await initAuthGuard(['victim', 'witness', 'affected_family_member']);
  if (!user) return; // Guard will handle redirect

  // 2. Setup Navbar Controls (Popover, Language Selector, Mobile Drawer)
  setupProfilePopover(user);
  setupLanguageSelector(user);
  setupMobileDrawer();

  // 3. Fetch & Render Case Journey Data
  await loadCaseJourneyData();
  await loadStatutoryReliefData();
  await loadThreatReports();
  setupThreatReportingModal();
  setupJourneySafetyControls();
});

/**
 * Loads read-only case journey data from secure backend endpoint.
 */
async function loadCaseJourneyData() {
  const loadingIndicator = document.getElementById('journeyLoadingIndicator');
  const errorBanner = document.getElementById('journeyErrorBanner');
  const mainContent = document.getElementById('journeyContentArea');

  try {
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    if (errorBanner) errorBanner.style.display = 'none';

    const response = await fetch('/api/victim/case-journey', {
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

    renderJourneySummary(data);
    renderTimeline(data.timeline || []);
    renderPulseHistory(data.support_pulses || []);
    renderSupportRequests(data.support_requests || []);
    renderNextUpdate(data.next_authorised_update);

  } catch (error) {
    console.error('Failed to load case journey:', error);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    if (errorBanner) {
      errorBanner.style.display = 'block';
      errorBanner.textContent = 'We could not load your case journey right now. Please try again later or contact your authorised support team.';
    }
  }
}

/**
 * Renders the 3-block journey summary card.
 */
function renderJourneySummary(data) {
  const currentStageEl = document.getElementById('summaryCurrentStage');
  const latestUpdateEl = document.getElementById('summaryLatestUpdate');
  const latestDateEl = document.getElementById('summaryLatestDate');
  const nextStepEl = document.getElementById('summaryNextStep');

  if (currentStageEl) {
    currentStageEl.textContent = data.current_stage || 'Case linking pending';
  }

  if (latestUpdateEl) {
    if (data.latest_update && data.latest_update.label) {
      latestUpdateEl.textContent = data.latest_update.label;
      if (latestDateEl) {
        latestDateEl.textContent = data.latest_update.date ? `Date: ${data.latest_update.date}` : '';
      }
    } else {
      latestUpdateEl.textContent = 'No update available';
      if (latestDateEl) latestDateEl.textContent = '';
    }
  }

  if (nextStepEl) {
    if (data.next_step && data.next_step.label) {
      nextStepEl.textContent = data.next_step.label;
    } else {
      nextStepEl.textContent = 'Awaiting authorised case linking';
    }
  }
}

/**
 * Renders the 6 vertical timeline stages.
 */
function renderTimeline(timelineStages) {
  const timelineContainer = document.getElementById('timelineContainer');
  if (!timelineContainer) return;

  if (timelineStages.length === 0) {
    timelineContainer.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-state-title">No timeline events available</div>
        <div class="empty-state-desc">Your case journey will appear here once an authorised case is linked to your account.</div>
      </div>
    `;
    return;
  }

  timelineContainer.innerHTML = timelineStages.map((stage) => {
    let itemModifier = '';
    if (stage.status === 'Completed') {
      itemModifier = 'stage-completed';
    } else if (stage.status === 'Active') {
      itemModifier = 'stage-active';
    }

    const badgeClass = stage.status_badge_class || 'badge-not-available';

    return `
      <div class="timeline-stage-item ${itemModifier}">
        <div class="stage-marker" aria-label="Stage ${stage.stage_num}">
          ${stage.status === 'Completed' ? '<i class="fa-solid fa-check"></i>' : stage.stage_num}
        </div>
        <div class="stage-content-card">
          <div class="stage-main">
            <h3 class="stage-title">${escapeHtml(stage.title)}</h3>
            <p class="stage-desc">${escapeHtml(stage.description)}</p>
          </div>
          <span class="status-badge ${badgeClass}">${escapeHtml(stage.status)}</span>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Renders Support Pulse history list or clean empty state.
 */
function renderPulseHistory(pulses) {
  const pulseContainer = document.getElementById('pulseHistoryContainer');
  if (!pulseContainer) return;

  if (pulses.length === 0) {
    pulseContainer.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-state-icon">
          <i class="fa-solid fa-heart-pulse"></i>
        </div>
        <div class="empty-state-title">You have not submitted a Support Pulse yet.</div>
        <div class="empty-state-desc">Share how you are doing anytime to record private check-ins and request targeted support.</div>
        <a href="checkin.html" class="btn btn-hero-primary" style="padding: 8px 22px; font-size: 0.86rem; display: inline-flex;">
          <i class="fa-solid fa-plus" style="margin-right: 6px;"></i> Start a Support Pulse
        </a>
      </div>
    `;
    return;
  }

  pulseContainer.innerHTML = pulses.map((p) => {
    const isAi = p.processing_mode === 'ai_assisted';
    const modeIcon = isAi ? '<i class="fa-solid fa-brain"></i>' : '<i class="fa-solid fa-user-shield"></i>';
    const modeLabel = isAi ? 'AI-assisted support' : 'Human review only';

    // Safe attachment indicators
    const attachments = [];
    if (p.has_written_note) {
      attachments.push('<span class="attachment-chip"><i class="fa-solid fa-file-lines"></i> Written note</span>');
    }
    if (p.has_voice_note) {
      const timeStr = p.voice_duration_display ? ` — ${p.voice_duration_display}` : '';
      attachments.push(`<span class="attachment-chip"><i class="fa-solid fa-microphone"></i> Voice note${timeStr}</span>`);
    }

    return `
      <div class="history-item-row">
        <div class="history-col-date">
          <div class="history-date">${escapeHtml(p.submission_date || p.submitted_at_display)}</div>
          <div class="history-channel"><i class="fa-solid fa-globe" style="margin-right: 4px;"></i>${escapeHtml(p.channel || 'Web Portal')}</div>
        </div>
        <div class="history-col-mode">
          <span class="processing-chip-sm">${modeIcon} ${modeLabel}</span>
          ${attachments.join(' ')}
        </div>
        <div class="history-col-status">
          <div class="history-status-main">${escapeHtml(p.submission_status || 'Update submitted')}</div>
          <div class="history-status-sub">${escapeHtml(p.human_review_status_display || 'Submitted for authorised review')}</div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Renders Support Requests list or clean empty state.
 */
function renderSupportRequests(requests) {
  const requestContainer = document.getElementById('supportRequestsContainer');
  if (!requestContainer) return;

  if (requests.length === 0) {
    requestContainer.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-state-icon">
          <i class="fa-solid fa-hands-holding-child"></i>
        </div>
        <div class="empty-state-title">No support requests yet.</div>
        <div class="empty-state-desc">You can request counselling, legal, safety, medical, financial, or rehabilitation support through your Support Pulse or My Support.</div>
        <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
          <a href="checkin.html" class="btn btn-hero-primary" style="padding: 8px 20px; font-size: 0.86rem; display: inline-flex;">
            Start a Support Pulse
          </a>
          <a href="my-support.html" class="btn btn-secondary-pill" style="padding: 8px 20px; font-size: 0.86rem; display: inline-flex;">
            View My Support
          </a>
        </div>
      </div>
    `;
    return;
  }

  requestContainer.innerHTML = requests.map((req) => {
    return `
      <div class="request-item-row">
        <div>
          <div class="request-title">${escapeHtml(req.request_type)}</div>
          <div class="request-meta">Submitted: ${escapeHtml(req.submitted_date || 'Recently')} • ${escapeHtml(req.next_step || 'Support team will review your request')}</div>
        </div>
        <div>
          <span class="status-badge badge-under-review"><i class="fa-solid fa-clock"></i> ${escapeHtml(req.status_display || req.status || 'Under review')}</span>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Renders next authorised update card.
 */
function renderNextUpdate(nextUpdate) {
  const nextUpdateContainer = document.getElementById('nextUpdateContainer');
  if (!nextUpdateContainer) return;

  if (nextUpdate && nextUpdate.date) {
    nextUpdateContainer.innerHTML = `
      <div class="next-update-block">
        <div class="next-update-icon">
          <i class="fa-solid fa-calendar-check"></i>
        </div>
        <div>
          <h3 class="next-update-title">Scheduled Update: ${escapeHtml(nextUpdate.date)}</h3>
          <p class="next-update-text">${escapeHtml(nextUpdate.reason || 'Authorised case review follow-up')}</p>
        </div>
      </div>
    `;
  } else {
    nextUpdateContainer.innerHTML = `
      <div class="next-update-block">
        <div class="next-update-icon">
          <i class="fa-solid fa-calendar-xmark"></i>
        </div>
        <div>
          <h3 class="next-update-title">No future update has been scheduled yet.</h3>
          <p class="next-update-text">An authorised support person may update this information when appropriate.</p>
        </div>
      </div>
    `;
  }
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

/**
 * Loads statutory relief data under SC/ST PoA Act Rules
 */
async function loadStatutoryReliefData() {
  try {
    const res = await fetch('/api/victim/statutory-relief', { credentials: 'include' });
    if (res.ok) {
      const data = await res.json();
      const sanctionedEl = document.getElementById('reliefTotalSanctioned');
      const badgeEl = document.getElementById('reliefDisbursedBadge');
      if (sanctionedEl && data.total_relief_sanctioned_display) {
        sanctionedEl.textContent = data.total_relief_sanctioned_display;
      }
      if (badgeEl && data.total_disbursed_display) {
        badgeEl.textContent = `${data.total_disbursed_display} (25%) Disbursed`;
      }
    }
  } catch (err) {
    console.warn('Statutory relief load notice:', err);
  }
}

/**
 * Loads existing Section 15A threat reports
 */
async function loadThreatReports() {
  const container = document.getElementById('threatReportsContainer');
  if (!container) return;
  try {
    const res = await fetch('/api/victim/intimidation-reports', { credentials: 'include' });
    if (res.ok) {
      const reports = await res.json();
      if (reports && reports.length > 0) {
        container.innerHTML = reports.map(r => `
          <div style="background: #FFF5F5; border: 1px solid #FED7D7; border-radius: 10px; padding: 10px 14px; font-size: 0.82rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <strong style="color: #991B1B;"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(r.incident_type_display || r.incident_type)}</strong>
              <span style="font-size: 0.72rem; background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 999px; font-weight: 700;">${escapeHtml(r.status_display || r.status)}</span>
            </div>
            <div style="color: #4B5563; font-size: 0.78rem; margin-bottom: 2px;">${escapeHtml(r.narrative)}</div>
            <div style="color: #6B7280; font-size: 0.72rem;">Location: ${escapeHtml(r.incident_location)} &bull; Reported: ${escapeHtml(r.incident_date || r.submitted_at)} &bull; Officer: ${escapeHtml(r.protection_officer_reference)}</div>
          </div>
        `).join('');
      }
    }
  } catch (err) {
    console.warn('Threat reports fetch notice:', err);
  }
}

/**
 * Setup Section 15A Intimidation Reporting Modal
 */
function setupThreatReportingModal() {
  const openBtn = document.getElementById('openThreatModalBtn');
  const modal = document.getElementById('threatReportModal');
  const closeBtn = document.getElementById('closeThreatModalBtn');
  const cancelBtn = document.getElementById('cancelThreatModalBtn');
  const form = document.getElementById('threatReportForm');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
  }
  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });
  }
  if (cancelBtn && modal) {
    cancelBtn.addEventListener('click', () => { modal.style.display = 'none'; });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById('submitThreatBtn');
      if (submitBtn) submitBtn.disabled = true;

      const incidentType = document.getElementById('threatTypeSelect').value;
      const source = document.getElementById('threatSourceInput').value;
      const location = document.getElementById('threatLocationInput').value;
      const narrative = document.getElementById('threatNarrativeInput').value;
      const urgency = document.querySelector('input[name="threatUrgency"]:checked')?.value || 'high';

      try {
        const res = await fetch('/api/victim/report-intimidation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_type: incidentType,
            threat_source: source,
            incident_location: location,
            narrative: narrative,
            urgency_level: urgency
          }),
          credentials: 'include'
        });

        if (res.ok) {
          alert('Section 15A Protection Report filed successfully. The District Protection Officer and DSP have been formally notified.');
          modal.style.display = 'none';
          form.reset();
          loadThreatReports();
        } else {
          alert('Could not submit report. Please contact NHAA 14566 directly.');
        }
      } catch (err) {
        alert('Network error submitting threat report. Please call 14566 or 112 directly.');
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }
}

/**
 * Setup Safety Controls (Camouflage & SOS) on Journey Page
 */
function setupJourneySafetyControls() {
  const sosBtn = document.getElementById('headerSosBtn') || document.getElementById('journeySosBtn');
  const sosModal = document.getElementById('homeSosModal');
  const sosCount = document.getElementById('homeSosCount');
  const sosCancel = document.getElementById('homeSosCancelBtn');
  const sosConfirm = document.getElementById('homeSosConfirmBtn');
  let sosTimer = null;
  let sosSeconds = 5;

  function triggerSos() {
    sosSeconds = 5;
    if (sosCount) sosCount.textContent = '5';
    if (sosModal) sosModal.style.display = 'flex';

    clearInterval(sosTimer);
    sosTimer = setInterval(() => {
      sosSeconds--;
      if (sosCount) sosCount.textContent = String(sosSeconds);
      if (sosSeconds <= 0) {
        clearInterval(sosTimer);
        dispatchSos();
      }
    }, 1000);
  }

  async function dispatchSos() {
    clearInterval(sosTimer);
    if (sosModal) sosModal.style.display = 'none';

    try {
      const res = await fetch('/api/victim/sos-alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ immediate_danger_type: "Section 15A Witness Intimidation SOS Triggered via Case Journey" }),
        credentials: 'include'
      });
      alert('EMERGENCY SOS ALERT ACTIVATED!\n\nYour alert has been broadcast to the District Police Control Room (SP/DSP Atrocities Cell) and designated Protection Officer under Section 15A.');
    } catch (e) {
      alert('Emergency alert registered. Please call 14566 or 112 immediately.');
    }
  }

  if (sosBtn) sosBtn.addEventListener('click', triggerSos);
  if (sosCancel) {
    sosCancel.addEventListener('click', () => {
      clearInterval(sosTimer);
      if (sosModal) sosModal.style.display = 'none';
    });
  }
  if (sosConfirm) {
    sosConfirm.addEventListener('click', dispatchSos);
  }

  // Stealth Camouflage Overlay System
  const stealthBtn = document.getElementById('headerStealthBtn') || document.getElementById('journeyStealthBtn');
  const overlay = document.getElementById('homeCamouflageOverlay');
  const exitStealth = document.getElementById('homeStealthExit');

  function toggleStealth() {
    if (!overlay) return;
    const isShown = overlay.style.display === 'block';
    overlay.style.display = isShown ? 'none' : 'block';
  }

  if (stealthBtn) stealthBtn.addEventListener('click', toggleStealth);
  if (exitStealth) exitStealth.addEventListener('click', toggleStealth);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (sosModal && sosModal.style.display === 'flex') {
        clearInterval(sosTimer);
        sosModal.style.display = 'none';
        return;
      }
      toggleStealth();
    }
  });

  // Disguised Calculator logic
  let calcBuffer = '0';
  window.calcDigit = function(btn) {
    const disp = document.getElementById('homeCalcDisplay');
    if (!disp) return;

    if (btn === 'C') {
      calcBuffer = '0';
    } else if (btn === '=') {
      try {
        calcBuffer = String(eval(calcBuffer.replace(/[^0-9+\-*/.]/g, '')) || '0');
      } catch {
        calcBuffer = 'Error';
      }
    } else if (btn === '+/-') {
      if (calcBuffer.startsWith('-')) calcBuffer = calcBuffer.substring(1);
      else if (calcBuffer !== '0') calcBuffer = '-' + calcBuffer;
    } else {
      if (calcBuffer === '0' || calcBuffer === 'Error') calcBuffer = btn;
      else calcBuffer += btn;
    }
    disp.textContent = calcBuffer;
  };
}


