/**
 * MENTAURA — Counsellor & Official Review Workspace JavaScript
 * Manages triage queues, support request actions, milestone updates, and review auditing.
 */

// Global State (Strictly 3 Dedicated Tabs)
let currentTab = 'messages';
let triageData = [];
let supportRequestsData = [];
let allSupportRequestsData = [];

// Helper: Escape HTML
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

// Helper: Format ISO date string in user's local timezone (e.g. IST)
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

// Helper: Format date only
function formatDateOnly(isoString) {
  if (!isoString) return 'Not available';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return 'Not available';
    return d.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return 'Not available';
  }
}

// Helper: Ensure token is passed in Authorization header for robust authentication
function getAuthHeaders(extra = {}) {
  const token = localStorage.getItem('mentaura_token') || sessionStorage.getItem('mentaura_token') || '';
  const headers = { 'Accept': 'application/json', ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Authenticated Official Role Guard
  const user = await initAuthGuard([
    'counsellor', 'case_officer', 'district_authority', 'district_admin',
    'state_administrator', 'state_admin', 'legal_aid_officer',
    'protection_officer', 'medical_rehabilitation_officer', 'national_administrator'
  ]);
  if (!user) return; // Guard handles redirect if unauthenticated

  // 2. Setup Navbar Controls
  setupProfilePopover(user);
  setupLanguageSelector(user);
  setupMobileDrawer();

  // 3. Setup Workspace Tab Switchers (Strictly 3 Dedicated Tabs)
  setupTabSwitchers();

  // 4. Load Overview Metrics & Queue Data
  await loadAllWorkspaceData();

  // 5. Setup Action Modals & Refresh Button
  setupModals();
  setupRefreshControls();
  initCounsellorMessagingHandlers();

  // 6. Start Live Background Auto-Sync
  startLiveAutoSync();
});

/**
 * Loads all workspace data and counts for the 3 tabs
 */
async function loadAllWorkspaceData() {
  await Promise.allSettled([
    loadSupportRequests(),
    loadDirectMessagesConversations(),
    loadWorkspaceOverview(),
    loadDirectMessages(true)
  ]);
}

/**
 * Sets up manual refresh button and live sync indicator
 */
function setupRefreshControls() {
  const refreshBtn = document.getElementById('refreshTriageBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      const icon = document.getElementById('refreshIcon');
      if (icon) icon.classList.add('fa-spin');
      await loadAllWorkspaceData();
      setTimeout(() => {
        if (icon) icon.classList.remove('fa-spin');
      }, 500);
    });
  }
}

/**
 * Live auto-sync interval for fresh submissions without page reloads
 */
let liveSyncInterval = null;
function startLiveAutoSync() {
  if (liveSyncInterval) clearInterval(liveSyncInterval);
  liveSyncInterval = setInterval(async () => {
    // Only refresh in background if user is not currently inside an open action modal
    const openModal = document.querySelector('.action-modal.active, .modal-backdrop[style*="display: flex"]:not(#counsellorDirectChatModal)');
    if (!openModal) {
      if (currentTab === 'messages' && currentSelectedVictimId) {
        await loadVictimThread(currentSelectedVictimId, currentSelectedVictimName, true);
        await loadDirectMessagesConversations();
      } else if (currentTab === 'messages') {
        await loadDirectMessages(true);
      } else if (currentTab === 'requests') {
        await loadSupportRequests();
      } else if (currentTab === 'video') {
        renderVideoConsultationsTable();
      }
    }
  }, 2000); // Live poll every 2 seconds for instant WhatsApp-like feel
}

// Instant synchronization when counsellor focuses the window/tab
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    if (currentTab === 'messages' && currentSelectedVictimId) {
      loadVictimThread(currentSelectedVictimId, currentSelectedVictimName, true);
      loadDirectMessagesConversations();
    } else {
      loadWorkspaceOverview();
    }
  }
});

/**
 * Loads Workspace Overview Metrics for the 3 Focused Caseload Counters
 */
async function loadWorkspaceOverview() {
  try {
    const res = await fetch('/api/counsellor/overview', {
      method: 'GET',
      headers: getAuthHeaders({ 'Cache-Control': 'no-cache' }),
      cache: 'no-store',
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const summary = data.summary || {};

    const cntDirectMessages = document.getElementById('cntDirectMessages');
    const cntScheduledVideo = document.getElementById('cntScheduledVideo');
    const cntPendingRequests = document.getElementById('cntPendingRequests');

    // 1. Direct Messages Count & Badge
    let unreadTotal = 0;
    let convoCount = 0;
    try {
      const convos = await loadDirectMessagesConversations();
      convoCount = convos.length;
      convos.forEach(c => { unreadTotal += (c.unread_count || 0); });
    } catch (e) {
      console.warn('Convo counter check note:', e);
    }

    if (cntDirectMessages) {
      cntDirectMessages.textContent = unreadTotal > 0 ? `${unreadTotal} new` : convoCount;
    }

    // 2. Video Consultations Count & Badge
    const videoCount = Array.isArray(allSupportRequestsData)
      ? allSupportRequestsData.filter(r => (r.session_format === 'video' || (r.session_metadata && r.session_metadata.format === 'video') || (r.category && r.category.toLowerCase().includes('video'))) && r.status !== 'cancelled').length
      : 0;

    if (cntScheduledVideo) cntScheduledVideo.textContent = videoCount;

    // 3. Intake / Counselling Requests Count & Badge
    const requestsCount = Array.isArray(allSupportRequestsData)
      ? allSupportRequestsData.length
      : (summary.pending_requests_count ?? 0);

    if (cntPendingRequests) cntPendingRequests.textContent = requestsCount;

    // Synchronize Tab Badges in Workspace Tabs and Header Navbar
    const tabMessages = document.getElementById('tabBadgeMessages');
    const tabVideo = document.getElementById('tabBadgeVideo');
    const tabRequests = document.getElementById('tabBadgeRequests');

    const headerBadgeMessages = document.getElementById('headerBadgeMessages');
    const headerBadgeVideo = document.getElementById('headerBadgeVideo');
    const headerBadgeRequests = document.getElementById('headerBadgeRequests');

    const mobileBadgeMessages = document.getElementById('mobileBadgeMessages');
    const mobileBadgeVideo = document.getElementById('mobileBadgeVideo');
    const mobileBadgeRequests = document.getElementById('mobileBadgeRequests');

    const msgDisplay = (unreadTotal > 0 || convoCount > 0) ? 'inline-flex' : 'none';
    const msgText = unreadTotal > 0 ? unreadTotal : convoCount;
    if (tabMessages) { tabMessages.textContent = msgText; tabMessages.style.display = msgDisplay; }
    if (headerBadgeMessages) { headerBadgeMessages.textContent = msgText; headerBadgeMessages.style.display = msgDisplay; }
    if (mobileBadgeMessages) { mobileBadgeMessages.textContent = msgText; mobileBadgeMessages.style.display = msgDisplay; }

    const videoDisplay = videoCount > 0 ? 'inline-flex' : 'none';
    if (tabVideo) { tabVideo.textContent = videoCount; tabVideo.style.display = videoDisplay; }
    if (headerBadgeVideo) { headerBadgeVideo.textContent = videoCount; headerBadgeVideo.style.display = videoDisplay; }
    if (mobileBadgeVideo) { mobileBadgeVideo.textContent = videoCount; mobileBadgeVideo.style.display = videoDisplay; }

    const reqDisplay = requestsCount > 0 ? 'inline-flex' : 'none';
    if (tabRequests) { tabRequests.textContent = requestsCount; tabRequests.style.display = reqDisplay; }
    if (headerBadgeRequests) { headerBadgeRequests.textContent = requestsCount; headerBadgeRequests.style.display = reqDisplay; }
    if (mobileBadgeRequests) { mobileBadgeRequests.textContent = requestsCount; mobileBadgeRequests.style.display = reqDisplay; }
  } catch (e) {
    console.warn('Could not load overview metrics:', e);
  }
}

/**
 * Setup Tab Switching (Strictly 3 Dedicated Tabs: messages, video, requests)
 * Synchronizes workspace tab bar, header navbar pill, mobile drawer, and summary counters.
 */
function setupTabSwitchers() {
  const tabs = document.querySelectorAll('.workspace-tab-btn');
  const headerTabs = document.querySelectorAll('.header-nav-tab');
  const mobileTabs = document.querySelectorAll('.mobile-nav-tab');
  const panels = document.querySelectorAll('.queue-panel-container');
  const heroPills = document.querySelectorAll('.hero-counter-pill');

  function switchWorkspaceTab(tabName) {
    if (!tabName) return;
    currentTab = tabName;

    // 1. Workspace tabs bar (if present)
    tabs.forEach(t => {
      const match = t.getAttribute('data-tab') === tabName;
      t.classList.toggle('active', match);
      t.setAttribute('aria-selected', match ? 'true' : 'false');
    });

    // 2. Header navbar tabs
    headerTabs.forEach(h => {
      const match = h.getAttribute('data-tab') === tabName;
      h.classList.toggle('active', match);
      h.setAttribute('aria-selected', match ? 'true' : 'false');
    });

    // 3. Mobile drawer tabs
    mobileTabs.forEach(m => {
      m.classList.toggle('active', m.getAttribute('data-tab') === tabName);
    });

    // 4. Panels (only selected panel displayed)
    panels.forEach(p => {
      p.style.display = p.getAttribute('id') === `panel-${tabName}` ? 'block' : 'none';
    });

    // 5. Hero counter pills & summary items
    document.querySelectorAll('.hero-counter-pill, .summary-counter-item').forEach(c => {
      const match = c.getAttribute('data-target-tab') === tabName;
      c.classList.toggle('active', match);
    });

    if (tabName === 'messages') {
      loadDirectMessages();
    } else if (tabName === 'video') {
      renderVideoConsultationsTable();
    } else if (tabName === 'requests') {
      loadSupportRequests();
    }
  }

  // Expose globally for action buttons or empty-state links
  window.switchWorkspaceTab = switchWorkspaceTab;

  // Bind workspace tab buttons (if present)
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      switchWorkspaceTab(tab.getAttribute('data-tab'));
    });
  });

  // Bind header navbar tabs
  headerTabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      switchWorkspaceTab(tab.getAttribute('data-tab'));
    });
  });

  // Bind mobile drawer tabs
  mobileTabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      switchWorkspaceTab(tab.getAttribute('data-tab'));
      const drawer = document.getElementById('mobileMenuDrawer');
      if (drawer) {
        drawer.classList.remove('open', 'active');
      }
    });
  });

  // Bind Hero counter pills & summary counter items
  document.querySelectorAll('.hero-counter-pill, .summary-counter-item').forEach(item => {
    item.addEventListener('click', () => {
      switchWorkspaceTab(item.getAttribute('data-target-tab'));
    });
  });
}

/**
 * Loads Support Pulse Triage Queue
 */
async function loadTriageQueue() {
  const container = document.getElementById('triageTableBody');
  if (!container) return;

  try {
    const res = await fetch('/api/counsellor/triage-queue', {
      method: 'GET',
      headers: getAuthHeaders({ 'Cache-Control': 'no-cache' }),
      cache: 'no-store',
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    triageData = data.triage_queue || [];

    // Keep Daily Check-Ins counter card and tab badge in exact sync with actual available list
    const actualCount = triageData.length;
    const cntNewPulses = document.getElementById('cntNewPulses');
    const tabTriage = document.getElementById('tabBadgeTriage');
    if (cntNewPulses) cntNewPulses.textContent = actualCount;
    if (tabTriage) tabTriage.textContent = actualCount;

    if (triageData.length === 0) {
      container.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 28px;">
            <div class="empty-queue-icon"><i class="fa-solid fa-clipboard-check"></i></div>
            <div class="empty-queue-title">All caught up!</div>
            <div class="empty-queue-desc">No Support Pulses currently awaiting review.</div>
          </td>
        </tr>
      `;
      return;
    }

    container.innerHTML = triageData.map(item => {
      const modeBadge = item.processing_mode === 'ai_assisted'
        ? `<span class="badge-mode-ai"><i class="fa-solid fa-wand-magic-sparkles"></i> AI-assisted</span>`
        : `<span class="badge-mode-human"><i class="fa-solid fa-user-shield"></i> Human only</span>`;

      const priorityBadge = item.priority_flag
        ? `<span class="badge-priority-high"><i class="fa-solid fa-circle-exclamation"></i> Priority</span>`
        : `<span class="badge-priority-normal"><i class="fa-solid fa-minus"></i> Standard</span>`;

      let riskBadge = `<span class="badge-risk-low"><i class="fa-solid fa-shield-check"></i> Low</span>`;
      if (item.risk_level === 'high') {
        riskBadge = `<span class="badge-risk-high"><i class="fa-solid fa-triangle-exclamation"></i> High</span>`;
      } else if (item.risk_level === 'medium') {
        riskBadge = `<span class="badge-risk-medium"><i class="fa-solid fa-circle-exclamation"></i> Medium</span>`;
      }

      let statusBadge = `<span class="badge-status-pending"><i class="fa-solid fa-clock"></i> Pending</span>`;
      if (item.human_review_status === 'reviewed') {
        statusBadge = `<span class="badge-status-reviewed"><i class="fa-solid fa-circle-check"></i> Reviewed</span>`;
      } else if (item.human_review_status === 'escalated') {
        statusBadge = `<span class="badge-status-escalated"><i class="fa-solid fa-triangle-exclamation"></i> Escalated</span>`;
      }

      const voiceIcon = item.has_voice_audio
        ? `<i class="fa-solid fa-microphone" style="color: #7E57C2; margin-left: 4px;" title="Voice note attached (${item.audio_duration_seconds || ''}s)"></i>`
        : '';

      const cleanDisplayName = (item.masked_identifier || '').replace(/\[[A-Za-z]\*{2,}[a-z]\]\s*/g, '').trim();

      return `
        <tr>
          <td>
            <div style="font-weight: 800; color: #261149;">${escapeHtml(cleanDisplayName || item.masked_identifier)}</div>
            <div style="font-size: 0.76rem; color: #6C5E8A;">${escapeHtml(item.case_id_masked)} ${voiceIcon}</div>
          </td>
          <td>${escapeHtml(formatDateTime(item.submission_date))}</td>
          <td><strong style="color: #2B1552;">${escapeHtml(item.wellbeing_state)}</strong></td>
          <td>${riskBadge}</td>
          <td>${modeBadge}</td>
          <td>${priorityBadge}</td>
          <td>${statusBadge}</td>
          <td style="text-align: right;">
            <button type="button" class="btn-action-sm" onclick="openPulseReviewModal('${escapeHtml(item.id)}')">
              <i class="fa-solid fa-eye"></i> Review
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.warn('Error loading triage queue:', e);
    container.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #A03030; padding: 20px;">Could not load triage queue.</td></tr>`;
  }
}

/**
 * Loads and renders Scheduled Video Consultations Queue (Tab 2)
 */
function renderVideoConsultationsTable() {
  const container = document.getElementById('videoScheduleTableBody');
  if (!container) return;

  const videoRequests = allSupportRequestsData.filter(r => 
    r.session_format === 'video' || 
    (r.session_metadata && r.session_metadata.format === 'video') ||
    (r.category && r.category.toLowerCase().includes('video'))
  );

  const tabVideo = document.getElementById('tabBadgeVideo');
  const cntScheduledVideo = document.getElementById('cntScheduledVideo');
  const headerBadgeVideo = document.getElementById('headerBadgeVideo');
  const mobileBadgeVideo = document.getElementById('mobileBadgeVideo');

  const videoDisplay = videoRequests.length > 0 ? 'inline-flex' : 'none';
  if (tabVideo) { tabVideo.textContent = videoRequests.length; tabVideo.style.display = videoDisplay; }
  if (headerBadgeVideo) { headerBadgeVideo.textContent = videoRequests.length; headerBadgeVideo.style.display = videoDisplay; }
  if (mobileBadgeVideo) { mobileBadgeVideo.textContent = videoRequests.length; mobileBadgeVideo.style.display = videoDisplay; }
  if (cntScheduledVideo) cntScheduledVideo.textContent = videoRequests.length;

  if (videoRequests.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 48px 20px;">
          <div class="empty-queue-icon" style="font-size: 2.5rem; color: #7C3AED; margin-bottom: 12px;">
            <i class="fa-solid fa-video"></i>
          </div>
          <div class="empty-queue-title" style="font-size: 1.15rem; font-weight: 800; color: #2B1552;">No video consultations scheduled yet</div>
          <div class="empty-queue-desc" style="color: #6C5E8A; font-size: 0.85rem; margin-top: 6px; max-width: 460px; margin-left: auto; margin-right: auto;">
            Go to the <a href="javascript:void(0)" onclick="switchWorkspaceTab('requests')" style="color: #7C3AED; font-weight: 700; text-decoration: underline;">Counselling Requests</a> tab and select a beneficiary to schedule a Google Meet consultation enclave.
          </div>
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = videoRequests.map(req => {
    let statusBadge = `<span class="badge-status-pending" style="background: #EDE8FB; color: #6D28D9; border: 1px solid #DDD6FE;"><i class="fa-solid fa-calendar-check"></i> Scheduled</span>`;
    if (req.status === 'in_progress') {
      statusBadge = `<span class="badge-status-reviewed" style="background: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0;"><i class="fa-solid fa-circle-play fa-spin"></i> In Progress</span>`;
    } else if (req.status === 'completed') {
      statusBadge = `<span class="badge-status-reviewed"><i class="fa-solid fa-check"></i> Completed</span>`;
    }

    const apptTime = req.appointment_at ? formatDateTime(req.appointment_at) : 'Immediate / On-demand';
    const roomId = (req.session_metadata && req.session_metadata.room_id) || `mentaura-room-${req.id.slice(0, 8)}`;
    const cleanName = (req.masked_requester || 'Beneficiary').replace(/\[[A-Za-z]\*{2,}[a-z]\]\s*/g, '').trim();

    return `
      <tr>
        <td>
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: #EDE8FB; color: #7C3AED; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.85rem;">
              <i class="fa-solid fa-user"></i>
            </div>
            <div>
              <div style="font-weight: 800; color: #261149;">${escapeHtml(cleanName)}</div>
              <div style="font-size: 0.76rem; color: #6C5E8A;">${escapeHtml(req.category_label || 'Psychological Consultation')}</div>
            </div>
          </div>
        </td>
        <td>
          <strong style="color: #2B1552; font-family: monospace;">${escapeHtml(req.case_id_masked || ('Case #' + req.id.slice(0, 8)))}</strong>
        </td>
        <td>
          <div style="font-weight: 700; color: #2B1552;">
            <i class="fa-regular fa-clock" style="color: #7C3AED; margin-right: 4px;"></i> ${escapeHtml(apptTime)}
          </div>
        </td>
        <td>
          <span class="badge-role-pill" style="background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; font-family: monospace; font-size: 0.78rem;">
            <i class="fa-solid fa-lock" style="font-size: 0.7rem; margin-right: 4px;"></i> ${escapeHtml(roomId)}
          </span>
        </td>
        <td>${statusBadge}</td>
        <td style="text-align: right;">
          <button type="button" class="btn btn-hero-primary" style="padding: 7px 18px; font-size: 0.82rem; border-radius: 9999px; display: inline-flex; align-items: center; gap: 6px;" onclick="openCounsellorVideoEnclave('${escapeHtml(req.id)}')">
            <i class="fa-solid fa-video"></i> Join Meeting
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Loads and renders Support & Referral Requests Queue (Tab 3)
 */
let currentSupportFilter = 'clinical'; // default to clinical counselling so counsellor is not overwhelmed
let _subfiltersInitialized = false;

function renderSupportRequestsTable() {
  const container = document.getElementById('requestsTableBody');
  if (!container) return;

  let filtered = allSupportRequestsData;
  if (currentSupportFilter === 'clinical') {
    filtered = allSupportRequestsData.filter(r => r.domain === 'clinical');
  } else if (currentSupportFilter === 'statutory') {
    filtered = allSupportRequestsData.filter(r => r.domain === 'statutory');
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 48px 20px;">
          <div class="empty-queue-icon"><i class="fa-solid fa-clipboard-list"></i></div>
          <div class="empty-queue-title">No pending counselling requests</div>
          <div class="empty-queue-desc">Victims requesting psychological support or statutory assistance will appear here.</div>
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = filtered.map(req => {
    let statusBadge = `<span class="badge-status-pending"><i class="fa-solid fa-clock"></i> ${escapeHtml(req.status)}</span>`;
    if (req.status === 'completed') {
      statusBadge = `<span class="badge-status-reviewed"><i class="fa-solid fa-check"></i> Completed</span>`;
    } else if (req.status === 'scheduled') {
      statusBadge = `<span class="badge-status-reviewed" style="background: #EDE8FB; color: #6D28D9; border-color: #DDD6FE;"><i class="fa-solid fa-calendar-check"></i> Scheduled</span>`;
    } else if (req.status === 'referred') {
      statusBadge = `<span class="badge-mode-ai" style="background: #FEF3C7; color: #92400E; border-color: #FDE68A;"><i class="fa-solid fa-share-nodes"></i> Referred</span>`;
    } else if (req.status === 'assigned') {
      statusBadge = `<span class="badge-mode-ai"><i class="fa-solid fa-user-check"></i> Assigned</span>`;
    }

    let domainBadge = req.domain === 'clinical' 
      ? `<span class="badge-domain-clinical"><i class="fa-solid fa-brain"></i> Counselling</span>`
      : `<span class="badge-domain-statutory"><i class="fa-solid fa-scale-balanced"></i> Statutory</span>`;

    const isInPerson = req.session_format === 'in_person' || (req.session_metadata && req.session_metadata.format === 'in_person');
    const isVideo = req.session_format === 'video' || (req.session_metadata && req.session_metadata.format === 'video');

    let actionBtn = '';
    if (req.domain === 'clinical') {
      actionBtn = `
        <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center; flex-wrap: wrap;">
          <button type="button" class="btn btn-hero-primary" style="padding: 7px 16px; font-size: 0.8rem; border-radius: 9999px; display: inline-flex; align-items: center; gap: 6px;" onclick="openCounsellingModal('${escapeHtml(req.id)}')" title="Review Requirements & Schedule Consultation">
            <i class="fa-solid fa-calendar-check"></i> Review &amp; Schedule
          </button>
          ${isInPerson ? `
            <button type="button" class="btn btn-outline-pill" style="padding: 6px 14px; font-size: 0.78rem; border-color: #7C3AED; color: #7C3AED; font-weight: 700; display: inline-flex; align-items: center; gap: 5px;" onclick="openInPersonSlipModal('${escapeHtml(req.id)}')" title="View Official OSC Verification Pass Slip">
              <i class="fa-solid fa-receipt"></i> Pass Slip
            </button>
          ` : ''}
          ${isVideo ? `
            <button type="button" class="btn-action-sm btn-counselling-video" style="background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;" onclick="openCounsellorVideoEnclave('${escapeHtml(req.id)}')" title="Launch Video Consultation Room">
              <i class="fa-solid fa-video"></i> Meet
            </button>
          ` : ''}
        </div>
      `;
    } else {
      actionBtn = `
        <button type="button" class="btn-action-sm btn-statutory-refer" onclick="openReferralModal('${escapeHtml(req.id)}')">
          <i class="fa-solid fa-share-nodes"></i> Refer / Escalate
        </button>
      `;
    }

    return `
      <tr>
        <td>
          <div style="font-weight: 800; color: #261149;">${escapeHtml(req.masked_requester)}</div>
          <div style="font-size: 0.76rem; color: #6C5E8A;">${escapeHtml(req.case_id_masked)}</div>
        </td>
        <td>
          <strong style="color: #2B1552;">${escapeHtml(req.category_label)}</strong>
          <div class="agency-target-tag">
            <i class="fa-solid fa-building-shield"></i> Target: ${escapeHtml(req.target_agency)}
          </div>
        </td>
        <td>${domainBadge}</td>
        <td>${escapeHtml(formatDateTime(req.submitted_at))}</td>
        <td>
          <div style="font-weight: 600; color: #374151;">${escapeHtml(req.assigned_to)}</div>
          ${req.next_step ? `<div style="font-size: 0.74rem; color: #6B7280; max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(req.next_step)}">${escapeHtml(req.next_step)}</div>` : ''}
        </td>
        <td>${statusBadge}</td>
        <td style="text-align: right;">
          ${actionBtn}
        </td>
      </tr>
    `;
  }).join('');
}

function setupSupportSubfilters() {
  if (_subfiltersInitialized) return;
  const filterBtns = document.querySelectorAll('.support-subfilter-btn');
  if (!filterBtns.length) return;
  _subfiltersInitialized = true;

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSupportFilter = btn.getAttribute('data-filter') || 'clinical';
      renderSupportRequestsTable();
    });
  });
}

async function loadSupportRequests() {
  const container = document.getElementById('requestsTableBody');
  if (!container) return;

  try {
    const res = await fetch('/api/counsellor/support-requests?include_inactive=false', {
      method: 'GET',
      headers: getAuthHeaders({ 'Cache-Control': 'no-cache' }),
      cache: 'no-store',
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allSupportRequestsData = data.support_requests || [];

    // Keep Support Requests counter card and tab badge in exact sync with active count
    const totalActiveCount = data.total_count || allSupportRequestsData.length;
    const cntPendingRequests = document.getElementById('cntPendingRequests');
    const tabRequests = document.getElementById('tabBadgeRequests');
    const cntRequestsSubtext = document.getElementById('cntRequestsSubtext');
    const subClinical = document.getElementById('subfilterBadgeClinical');
    const subStatutory = document.getElementById('subfilterBadgeStatutory');
    const subAll = document.getElementById('subfilterBadgeAll');

    const headerBadgeRequests = document.getElementById('headerBadgeRequests');
    const mobileBadgeRequests = document.getElementById('mobileBadgeRequests');
    const reqDisplay = totalActiveCount > 0 ? 'inline-flex' : 'none';

    if (cntPendingRequests) cntPendingRequests.textContent = totalActiveCount;
    if (tabRequests) { tabRequests.textContent = totalActiveCount; tabRequests.style.display = reqDisplay; }
    if (headerBadgeRequests) { headerBadgeRequests.textContent = totalActiveCount; headerBadgeRequests.style.display = reqDisplay; }
    if (mobileBadgeRequests) { mobileBadgeRequests.textContent = totalActiveCount; mobileBadgeRequests.style.display = reqDisplay; }
    if (cntRequestsSubtext) cntRequestsSubtext.textContent = `${data.clinical_count || 0} care • ${data.statutory_count || 0} referrals`;
    if (subClinical) subClinical.textContent = data.clinical_count || 0;
    if (subStatutory) subStatutory.textContent = data.statutory_count || 0;
    if (subAll) subAll.textContent = totalActiveCount;

    renderSupportRequestsTable();
    renderVideoConsultationsTable();
    setupSupportSubfilters();
  } catch (e) {
    console.warn('Error loading support requests:', e);
  }
}

/**
 * Loads Case Milestones
 */
async function loadCaseMilestones() {
  const container = document.getElementById('milestonesTableBody');
  if (!container) return;

  try {
    const res = await fetch('/api/counsellor/case-milestones', {
      method: 'GET',
      headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' },
      cache: 'no-store',
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    caseMilestonesData = data.case_milestones || [];

    container.innerHTML = caseMilestonesData.map(cs => {
      return `
        <tr>
          <td>
            <div style="font-weight: 800; color: #261149;">${escapeHtml(cs.case_id_masked)}</div>
            <div style="font-size: 0.76rem; color: #6C5E8A;">${escapeHtml(cs.victim_masked)}</div>
          </td>
          <td><strong>${escapeHtml(cs.current_stage)}</strong></td>
          <td>${escapeHtml(formatDateOnly(cs.last_update))}</td>
          <td>${escapeHtml(cs.assigned_officer)}</td>
          <td>
            <span class="badge-status-reviewed">
              <i class="fa-solid fa-circle-check"></i> ${cs.milestones_completed}/${cs.total_milestones} Done
            </span>
          </td>
          <td style="text-align: right;">
            <button type="button" class="btn-action-sm" onclick="openMilestoneModal('${escapeHtml(cs.id)}')">
              <i class="fa-solid fa-pen-to-square"></i> Update
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.warn('Error loading case milestones:', e);
  }
}

/**
 * Loads Active Interventions
 */
async function loadInterventions() {
  const container = document.getElementById('interventionsTableBody');
  if (!container) return;

  try {
    const res = await fetch('/api/counsellor/interventions', {
      method: 'GET',
      headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' },
      cache: 'no-store',
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    interventionsData = data.interventions || [];

    container.innerHTML = interventionsData.map(item => {
      let statusBadge = `<span class="badge-mode-ai"><i class="fa-solid fa-spinner fa-spin"></i> ${escapeHtml(item.status)}</span>`;
      if (item.status === 'scheduled') {
        statusBadge = `<span class="badge-status-pending"><i class="fa-solid fa-calendar"></i> Scheduled</span>`;
      } else if (item.status === 'approved') {
        statusBadge = `<span class="badge-status-reviewed"><i class="fa-solid fa-check"></i> Approved</span>`;
      }

      return `
        <tr>
          <td>
            <div style="font-weight: 800; color: #261149;">${escapeHtml(item.title)}</div>
            <div style="font-size: 0.76rem; color: #6C5E8A;">${escapeHtml(item.details)}</div>
          </td>
          <td>${escapeHtml(item.beneficiary_masked)}</td>
          <td>${escapeHtml(item.assigned_officer)}</td>
          <td>${escapeHtml(formatDateOnly(item.scheduled_date))}</td>
          <td>${statusBadge}</td>
          <td style="text-align: right;">
            <button type="button" class="btn-action-sm" onclick="openInterventionModal('${escapeHtml(item.id)}')">
              <i class="fa-solid fa-clipboard-list"></i> Details
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.warn('Error loading interventions:', e);
  }
}

/**
 * Helper to insert quick template note into pulse review modal
 */
window.insertPulseNote = function(text) {
  const textarea = document.getElementById('modalPulseReviewNotes');
  if (!textarea) return;
  if (textarea.value.trim().length > 0) {
    textarea.value += '\n' + text;
  } else {
    textarea.value = text;
  }
  textarea.focus();
};

/**
 * Opens Pulse Review Modal
 */
window.openPulseReviewModal = function(pulseId) {
  const item = triageData.find(p => p.id === pulseId);
  if (!item) return;

  const modal = document.getElementById('pulseReviewModal');
  if (!modal) return;

  document.getElementById('modalPulseId').value = item.id;

  // Clean identifier (strip any legacy [V****m] or bracketed role tags)
  let rawIdentifier = item.masked_identifier || 'Aanya Sharma (Victim)';
  let cleanIdentifier = rawIdentifier.replace(/\[[A-Za-z]\*{2,}[a-z]\]\s*/g, '').trim();

  // Parse name and role
  let roleMatch = cleanIdentifier.match(/\(([^)]+)\)$/);
  let roleText = roleMatch ? roleMatch[1] : 'Beneficiary';
  let nameOnly = cleanIdentifier.replace(/\s*\([^)]+\)$/, '').trim();

  // Initials for avatar
  let parts = nameOnly.split(/\s+/).filter(Boolean);
  let initials = 'BN';
  if (parts.length >= 2) {
    initials = (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  } else if (parts.length === 1) {
    initials = parts[0].slice(0, 2).toUpperCase();
  }

  const avatarEl = document.getElementById('modalPulseAvatar');
  if (avatarEl) avatarEl.textContent = initials;

  const victimEl = document.getElementById('modalPulseVictim');
  if (victimEl) victimEl.textContent = nameOnly;

  const roleBadgeEl = document.getElementById('modalPulseRoleBadge');
  if (roleBadgeEl) {
    roleBadgeEl.innerHTML = `<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Verified ${escapeHtml(roleText)}`;
  }

  const caseBadgeEl = document.getElementById('modalPulseCaseBadge');
  if (caseBadgeEl) {
    caseBadgeEl.innerHTML = `<i class="fa-solid fa-folder-closed" aria-hidden="true"></i> ${escapeHtml(item.case_id_masked || 'Case Enclave')}`;
  }

  const dateEl = document.getElementById('modalPulseDate');
  if (dateEl) dateEl.textContent = formatDateTime(item.submission_date);

  // Well-being state
  const wellbeingEl = document.getElementById('modalPulseWellbeing');
  const moodIconWrap = document.getElementById('modalPulseMoodIcon');
  if (wellbeingEl) {
    let wb = (item.wellbeing_state || 'managing').toLowerCase();
    let wbLabel = wb.charAt(0).toUpperCase() + wb.slice(1);
    wellbeingEl.textContent = wbLabel;
    if (moodIconWrap) {
      if (wb === 'thriving' || wb === 'good' || wb === 'managing') {
        moodIconWrap.innerHTML = '<i class="fa-solid fa-face-smile" aria-hidden="true"></i>';
        moodIconWrap.style.background = '#F0FDF4';
        moodIconWrap.style.color = '#15803D';
      } else if (wb === 'struggling' || wb === 'stressed') {
        moodIconWrap.innerHTML = '<i class="fa-solid fa-face-frown" aria-hidden="true"></i>';
        moodIconWrap.style.background = '#FFFBEB';
        moodIconWrap.style.color = '#B45309';
      } else {
        moodIconWrap.innerHTML = '<i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>';
        moodIconWrap.style.background = '#FEF2F2';
        moodIconWrap.style.color = '#DC2626';
      }
    }
  }

  // Risk badge & score (Distinguish between algorithmic AI distress score and clinical override)
  const riskBadgeEl = document.getElementById('modalPulseRiskBadge');
  const riskScoreTextEl = document.getElementById('modalPulseRiskScoreText');
  if (riskBadgeEl) {
    let rLevel = (item.risk_level || 'low').toLowerCase();
    let rScore = typeof item.risk_score === 'number' ? item.risk_score : 2;
    let isEscalated = item.human_review_status === 'escalated' || Boolean(item.priority_flag);

    if (isEscalated) {
      riskBadgeEl.innerHTML = `<span class="badge-risk-high"><i class="fa-solid fa-triangle-exclamation"></i> High Priority</span>`;
      if (riskScoreTextEl) {
        riskScoreTextEl.textContent = `(AI Score: ${rScore}/100 • Escalated)`;
      }
    } else if (rLevel === 'high' || rLevel === 'critical') {
      riskBadgeEl.innerHTML = `<span class="badge-risk-high"><i class="fa-solid fa-circle-exclamation"></i> High Risk</span>`;
      if (riskScoreTextEl) {
        riskScoreTextEl.textContent = `(Score: ${rScore}/100)`;
      }
    } else if (rLevel === 'medium') {
      riskBadgeEl.innerHTML = `<span class="badge-risk-medium"><i class="fa-solid fa-circle-exclamation"></i> Medium Risk</span>`;
      if (riskScoreTextEl) {
        riskScoreTextEl.textContent = `(Score: ${rScore}/100)`;
      }
    } else {
      riskBadgeEl.innerHTML = `<span class="badge-risk-low"><i class="fa-solid fa-circle-check"></i> Low Risk</span>`;
      if (riskScoreTextEl) {
        riskScoreTextEl.textContent = `(Score: ${rScore}/100)`;
      }
    }
  }

  // Processing mode
  const modeEl = document.getElementById('modalPulseMode');
  if (modeEl) {
    modeEl.textContent = item.processing_mode === 'ai_assisted' ? 'AI-assisted support' : 'Human review only';
  }

  // Channel
  const channelEl = document.getElementById('modalPulseChannel');
  if (channelEl) {
    channelEl.textContent = `${(item.channel || 'web').toUpperCase()} Portal • ${item.language || 'EN'}`;
  }

  // Narrative text
  const narrativeEl = document.getElementById('modalPulseNarrative');
  const narrativeTagEl = document.getElementById('modalPulseNarrativeTag');
  if (narrativeEl) {
    const fullNarrative = item.text_response || item.text_snippet;
    if (fullNarrative) {
      narrativeEl.textContent = fullNarrative;
      narrativeEl.style.fontStyle = 'normal';
      narrativeEl.style.color = '#261149';
      if (narrativeTagEl) {
        narrativeTagEl.textContent = 'Victim Reflection';
        narrativeTagEl.style.background = '#EDE8FB';
        narrativeTagEl.style.color = '#55338D';
      }
    } else {
      narrativeEl.textContent = 'No text narrative provided.';
      narrativeEl.style.fontStyle = 'italic';
      narrativeEl.style.color = '#7C7393';
      if (narrativeTagEl) {
        narrativeTagEl.textContent = 'No Text Entered';
        narrativeTagEl.style.background = '#F1F5F9';
        narrativeTagEl.style.color = '#64748B';
      }
    }
  }

  // Clear review notes textarea for fresh official input
  const notesEl = document.getElementById('modalPulseReviewNotes');
  if (notesEl) {
    notesEl.value = '';
  }

  // Voice player card
  const voiceBox = document.getElementById('modalPulseVoiceInfo');
  if (voiceBox) {
    if (item.has_voice_audio) {
      let durSec = item.audio_duration_seconds || 3;
      let durFormatted = `0:0${durSec}`;
      voiceBox.innerHTML = `
        <div class="voice-player-container">
          <button type="button" class="voice-play-toggle-btn" id="modalVoicePlayBtn" aria-label="Play recording preview">
            <i class="fa-solid fa-play" id="modalVoicePlayIcon"></i>
          </button>
          <div class="voice-player-details">
            <div class="voice-player-header-row">
              <span class="voice-player-title"><i class="fa-solid fa-microphone-lines"></i> Confidential Voice Audio Note</span>
              <span class="badge-enclave-secure"><i class="fa-solid fa-lock"></i> Protected Enclave (AES-256)</span>
            </div>
            <div class="voice-player-waveform-row">
              <div class="voice-waveform-bars" id="modalWaveformBars">
                <span></span><span></span><span></span><span></span><span></span>
                <span></span><span></span><span></span><span></span><span></span>
                <span></span><span></span><span></span><span></span><span></span>
                <span></span><span></span><span></span><span></span><span></span>
              </div>
              <span class="voice-player-timer" id="modalVoiceTimer">0:00 / ${durFormatted}</span>
            </div>
          </div>
        </div>
      `;
      voiceBox.style.display = 'block';

      // Real Enclave Audio Playback with Token Authorization & Resilient Audio Engine
      let isPlaying = false;
      const playBtn = document.getElementById('modalVoicePlayBtn');
      const playIcon = document.getElementById('modalVoicePlayIcon');
      const waveform = document.getElementById('modalWaveformBars');
      const timerText = document.getElementById('modalVoiceTimer');

      // Stop any previously playing modal audio / context
      if (window._currentModalAudio) {
        try {
          window._currentModalAudio.pause();
        } catch (e) {}
        window._currentModalAudio = null;
      }
      if (window._currentModalAudioSource) {
        try {
          window._currentModalAudioSource.stop();
        } catch (e) {}
        window._currentModalAudioSource = null;
      }

      const token = localStorage.getItem('mentaura_token') || sessionStorage.getItem('mentaura_token') || '';
      let audioSrc = item.audio_url || `/api/counsellor/audio/${item.id}`;
      if (token && !audioSrc.includes('token=')) {
        audioSrc += (audioSrc.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(token);
      }

      function formatTimeSec(sec) {
        let s = Math.max(0, Math.floor(sec || 0));
        let m = Math.floor(s / 60);
        let remSec = s % 60;
        return `${m}:${remSec < 10 ? '0' : ''}${remSec}`;
      }

      let audioContext = null;
      let decodedBuffer = null;
      let audioSourceNode = null;
      let playbackStartTime = 0;
      let pauseOffset = 0;
      let animFrameId = null;

      // Create standard HTML5 Audio
      const audio = new Audio();
      audio.preload = 'auto';
      audio.src = audioSrc;
      window._currentModalAudio = audio;

      // Pre-fetch ArrayBuffer for Web Audio API instant decoding
      // This eliminates any Chrome MediaRecorder WebM duration/ended bugs
      fetch(audioSrc, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        credentials: 'include'
      })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.arrayBuffer();
      })
      .then(buf => {
        const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
        if (AudioCtxClass) {
          audioContext = new AudioCtxClass();
          return audioContext.decodeAudioData(buf);
        }
      })
      .then(decoded => {
        if (decoded) {
          decodedBuffer = decoded;
          durSec = decoded.duration > 0 ? decoded.duration : durSec;
          timerText.textContent = `0:00 / ${formatTimeSec(durSec)}`;
        }
      })
      .catch(err => {
        console.warn('Web Audio pre-fetch fallback note:', err);
      });

      function setVisualState(playing) {
        isPlaying = playing;
        if (playIcon) {
          playIcon.className = playing ? 'fa-solid fa-pause' : 'fa-solid fa-play';
        }
        if (waveform) {
          if (playing) {
            waveform.classList.add('playing');
          } else {
            waveform.classList.remove('playing');
          }
        }
        if (playBtn) {
          playBtn.setAttribute('aria-label', playing ? 'Pause voice recording' : 'Play voice recording');
          playBtn.title = playing ? 'Pause' : 'Play';
          if (playing) {
            playBtn.classList.add('is-active-playing');
          } else {
            playBtn.classList.remove('is-active-playing');
          }
        }
      }

      function stopAllAudio() {
        if (animFrameId) {
          cancelAnimationFrame(animFrameId);
          animFrameId = null;
        }
        if (audioSourceNode) {
          try {
            audioSourceNode.onended = null;
            audioSourceNode.stop();
          } catch (e) {}
          audioSourceNode = null;
        }
        if (audio && !audio.paused) {
          try {
            audio.pause();
          } catch (e) {}
        }
        setVisualState(false);
      }

      function onPlaybackFinished() {
        stopAllAudio();
        pauseOffset = 0;
        if (audio) {
          try { audio.currentTime = 0; } catch (e) {}
        }
        timerText.textContent = `0:00 / ${formatTimeSec(durSec)}`;
      }

      function playWebAudioEngine() {
        if (!audioContext || !decodedBuffer) return false;
        try {
          if (audioContext.state === 'suspended') {
            audioContext.resume();
          }
          if (audioSourceNode) {
            try { audioSourceNode.stop(); } catch (e) {}
          }
          audioSourceNode = audioContext.createBufferSource();
          audioSourceNode.buffer = decodedBuffer;
          audioSourceNode.connect(audioContext.destination);
          window._currentModalAudioSource = audioSourceNode;

          const offset = pauseOffset % decodedBuffer.duration;
          playbackStartTime = audioContext.currentTime - offset;
          audioSourceNode.start(0, offset);
          setVisualState(true);

          audioSourceNode.onended = function() {
            if (isPlaying) {
              onPlaybackFinished();
            }
          };

          function updateWebAudioTimer() {
            if (!isPlaying || !audioContext) return;
            const current = audioContext.currentTime - playbackStartTime;
            if (current >= decodedBuffer.duration) {
              onPlaybackFinished();
              return;
            }
            timerText.textContent = `${formatTimeSec(current)} / ${formatTimeSec(decodedBuffer.duration)}`;
            animFrameId = requestAnimationFrame(updateWebAudioTimer);
          }
          animFrameId = requestAnimationFrame(updateWebAudioTimer);
          return true;
        } catch (e) {
          console.warn('Web Audio engine play failed:', e);
          return false;
        }
      }

      // HTML5 Audio Event Listeners with Duration & End Guards
      audio.addEventListener('loadedmetadata', () => {
        let total = audio.duration && isFinite(audio.duration) && audio.duration > 0 ? audio.duration : durSec;
        timerText.textContent = `0:00 / ${formatTimeSec(total)}`;
      });

      audio.addEventListener('timeupdate', () => {
        if (decodedBuffer && isPlaying) return; // Web Audio handler controls timer
        let current = audio.currentTime || 0;
        let total = audio.duration && isFinite(audio.duration) && audio.duration > 0 ? audio.duration : durSec;
        if (current >= total - 0.08) {
          onPlaybackFinished();
          return;
        }
        timerText.textContent = `${formatTimeSec(current)} / ${formatTimeSec(total)}`;
      });

      audio.addEventListener('ended', () => {
        onPlaybackFinished();
      });

      audio.addEventListener('error', (err) => {
        console.warn('HTML5 audio error:', err);
        if (decodedBuffer) {
          playWebAudioEngine();
        } else {
          setVisualState(false);
        }
      });

      function togglePlayPause() {
        if (isPlaying) {
          // User wants to pause
          if (audioContext && decodedBuffer) {
            pauseOffset = audioContext.currentTime - playbackStartTime;
          }
          stopAllAudio();
        } else {
          // User wants to play
          // Provide instant visual and haptic press feedback
          setVisualState(true);

          // 1. Try Web Audio first if buffer is ready (immune to MediaRecorder WebM bugs)
          if (decodedBuffer && playWebAudioEngine()) {
            return;
          }

          // 2. Fallback to HTML5 audio element
          if (audio.currentTime >= durSec - 0.1) {
            audio.currentTime = 0;
          }
          const p = audio.play();
          if (p !== undefined) {
            p.catch(e => {
              console.warn('HTML5 audio play request rejected:', e);
              // If rejected, retry with Web Audio if buffer became ready
              if (decodedBuffer && playWebAudioEngine()) {
                return;
              }
              setVisualState(false);
            });
          }
        }
      }

      // Explicit Tactile Button Press Bindings
      if (playBtn) {
        const triggerPress = (e) => {
          if (e) {
            e.preventDefault();
            e.stopPropagation();
          }
          playBtn.classList.add('pressing');
          setTimeout(() => playBtn.classList.remove('pressing'), 150);
          togglePlayPause();
        };

        playBtn.onclick = triggerPress;
        playBtn.addEventListener('keydown', (e) => {
          if (e.key === ' ' || e.key === 'Enter') {
            triggerPress(e);
          }
        });
      }

      // Also allow clicking on the waveform row to toggle play/pause
      const playerCard = voiceBox.querySelector('.voice-player-container');
      if (playerCard) {
        playerCard.onclick = function(e) {
          if (e.target !== playBtn && !playBtn.contains(e.target)) {
            togglePlayPause();
          }
        };
      }
    } else {
      voiceBox.style.display = 'none';
    }
  }

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
};

/**
 * Opens Clinical Counselling Session Modal
 */
window.openCounsellingModal = function(requestId) {
  const req = allSupportRequestsData.find(r => r.id === requestId);
  if (!req) return;

  const modal = document.getElementById('counsellingSessionModal');
  if (!modal) return;

  document.getElementById('modalCounsellingId').value = req.id;
  document.getElementById('modalCounsellingRequester').textContent = req.masked_requester;
  document.getElementById('modalCounsellingCategory').textContent = req.category_label;
  document.getElementById('modalCounsellingDate').textContent = formatDateTime(req.submitted_at);

  const dtInput = document.getElementById('modalCounsellingDatetime');
  if (dtInput) {
    if (req.appointment_at) {
      dtInput.value = req.appointment_at.slice(0, 16);
    } else {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(10, 0, 0, 0);
      const isoLocal = new Date(tomorrow.getTime() - (tomorrow.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
      dtInput.value = isoLocal;
    }
  }

  const statusSelect = document.getElementById('modalCounsellingStatusSelect');
  if (statusSelect) {
    statusSelect.value = req.status === 'completed' ? 'completed' : 'scheduled';
  }

  const notesEl = document.getElementById('modalCounsellingNotes');
  if (notesEl) {
    notesEl.value = (req.next_step && !req.next_step.startsWith('Awaiting')) ? req.next_step : '';
  }

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
};

/**
 * Opens Cross-Agency Statutory Referral Modal
 */
window.openReferralModal = function(requestId) {
  const req = allSupportRequestsData.find(r => r.id === requestId);
  if (!req) return;

  const modal = document.getElementById('requestManageModal');
  if (!modal) return;

  document.getElementById('modalRequestId').value = req.id;
  document.getElementById('modalRequestRequester').textContent = req.masked_requester;
  document.getElementById('modalRequestCategory').textContent = req.category_label;
  document.getElementById('modalRequestDate').textContent = formatDateTime(req.submitted_at);

  const agencySelect = document.getElementById('modalReferralAgencySelect');
  if (agencySelect) {
    for (let opt of agencySelect.options) {
      if (req.target_agency && req.target_agency.toLowerCase().includes(opt.value.slice(0, 5).toLowerCase())) {
        opt.selected = true;
        break;
      }
    }
  }

  const urgencySelect = document.getElementById('modalReferralUrgencySelect');
  if (urgencySelect) {
    urgencySelect.value = req.urgency === 'urgent' ? 'high_distress' : 'standard';
  }

  const notesEl = document.getElementById('modalRequestNotes');
  if (notesEl) {
    notesEl.value = (req.next_step && !req.next_step.startsWith('Awaiting')) ? req.next_step : '';
  }

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
};

/**
 * Backwards-compatible Router for Request Manage Modal
 */
window.openRequestManageModal = function(requestId) {
  const req = allSupportRequestsData.find(r => r.id === requestId);
  if (req && req.domain === 'clinical') {
    openCounsellingModal(requestId);
  } else {
    openReferralModal(requestId);
  }
};

/**
 * Opens Milestone Modal
 */
window.openMilestoneModal = function(caseId) {
  const cs = caseMilestonesData.find(c => c.id === caseId);
  if (!cs) return;

  const modal = document.getElementById('milestoneModal');
  if (!modal) return;

  document.getElementById('modalCaseId').value = cs.id;
  document.getElementById('modalCaseNumber').textContent = cs.case_id_masked;
  document.getElementById('modalCaseVictim').textContent = cs.victim_masked;
  document.getElementById('modalMilestoneStageSelect').value = cs.stage_key || 'stage_support';

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
};

/**
 * Opens Intervention Modal
 */
window.openInterventionModal = function(intId) {
  const item = interventionsData.find(i => i.id === intId);
  if (!item) return;

  const modal = document.getElementById('interventionModal');
  if (!modal) return;

  document.getElementById('modalIntId').value = item.id;
  document.getElementById('modalIntTitle').textContent = item.title;
  document.getElementById('modalIntBeneficiary').textContent = item.beneficiary_masked;
  document.getElementById('modalIntDetails').textContent = item.details;
  document.getElementById('modalIntStatusSelect').value = item.status || 'in_progress';

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
};

/**
 * Setup Modal Close & Submit Event Handlers
 */
function setupModals() {
  const modals = [
    'pulseReviewModal', 'counsellingSessionModal', 'requestManageModal', 
    'milestoneModal', 'interventionModal', 'counsellorTelephonicModal', 
    'counsellorVideoModal', 'counsellorOscModal', 'counsellorCrisisModal',
    'inPersonVerificationSlipModal'
  ];

  modals.forEach(modalId => {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.querySelectorAll('.modal-close-btn, .btn-modal-cancel').forEach(btn => {
      btn.addEventListener('click', () => {
        if (window._currentModalAudio) {
          window._currentModalAudio.pause();
          window._currentModalAudio = null;
        }
        stopAudioWaveform();
        stopConsoleTimer();
        stopBreathingPacer();
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
      });
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        if (window._currentModalAudio) {
          window._currentModalAudio.pause();
          window._currentModalAudio = null;
        }
        stopAudioWaveform();
        stopConsoleTimer();
        stopBreathingPacer();
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
      }
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (window._currentModalAudio) {
        window._currentModalAudio.pause();
        window._currentModalAudio = null;
      }
      stopAudioWaveform();
      stopConsoleTimer();
      stopBreathingPacer();
      modals.forEach(mId => {
        const m = document.getElementById(mId);
        if (m && m.style.display === 'flex') {
          m.style.display = 'none';
          m.setAttribute('aria-hidden', 'true');
          document.body.style.overflow = '';
        }
      });
    }
  });

  // Action Submissions
  // 1. Mark Pulse Reviewed
  const btnMarkReviewed = document.getElementById('btnSubmitPulseReviewed');
  if (btnMarkReviewed) {
    btnMarkReviewed.addEventListener('click', async () => {
      const pulseId = document.getElementById('modalPulseId').value;
      const notes = document.getElementById('modalPulseReviewNotes').value;
      await submitReviewAction('support_pulse', pulseId, 'mark_reviewed', 'reviewed', notes);
      document.getElementById('pulseReviewModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadTriageQueue();
      await loadWorkspaceOverview();
    });
  }

  // 2. Prioritize Pulse
  const btnPrioritizePulse = document.getElementById('btnSubmitPulsePrioritize');
  if (btnPrioritizePulse) {
    btnPrioritizePulse.addEventListener('click', async () => {
      const pulseId = document.getElementById('modalPulseId').value;
      const notes = document.getElementById('modalPulseReviewNotes').value;
      await submitReviewAction('support_pulse', pulseId, 'prioritize', 'escalated', notes);
      document.getElementById('pulseReviewModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadTriageQueue();
      await loadWorkspaceOverview();
    });
  }

  // 3A. Save Clinical Counselling Session
  const btnSubmitCounselling = document.getElementById('btnSubmitCounsellingSchedule');
  if (btnSubmitCounselling) {
    btnSubmitCounselling.addEventListener('click', async () => {
      const reqId = document.getElementById('modalCounsellingId').value;
      const statusVal = document.getElementById('modalCounsellingStatusSelect').value;
      const formatVal = document.getElementById('modalCounsellingFormatSelect').value;
      const datetimeVal = document.getElementById('modalCounsellingDatetime').value;
      const notes = document.getElementById('modalCounsellingNotes').value;

      let fullNotes = `Format: ${formatVal.replace('_', ' ').toUpperCase()}`;
      if (notes) fullNotes += ` | Clinical Assessment: ${notes}`;

      await submitReviewAction('support_request', reqId, 'schedule_session', statusVal, fullNotes, {
        appointment_date: datetimeVal ? new Date(datetimeVal).toISOString() : null,
        assigned_role: 'Psychological Counsellor',
        session_format: formatVal
      });
      document.getElementById('counsellingSessionModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadSupportRequests();
      await loadWorkspaceOverview();

      // Launch in-person verification slip or video consultation enclave
      setTimeout(() => {
        const req = allSupportRequestsData.find(r => r.id === reqId);
        if (formatVal === 'in_person') {
          openInPersonSlipModal(reqId);
        } else if (formatVal === 'video') {
          openCounsellorVideoEnclave(reqId);
        } else if (formatVal === 'direct_message') {
          openCounsellorDirectChat((req && req.user_id) || '', (req && req.masked_requester) || 'Beneficiary', reqId);
        }
      }, 350);
    });
  }

  // 3B. Forward Cross-Agency Statutory Referral
  const btnSaveRequest = document.getElementById('btnSubmitRequestManage');
  if (btnSaveRequest) {
    btnSaveRequest.addEventListener('click', async () => {
      const reqId = document.getElementById('modalRequestId').value;
      const agencyVal = document.getElementById('modalReferralAgencySelect').value;
      const urgencyVal = document.getElementById('modalReferralUrgencySelect').value;
      const notes = document.getElementById('modalRequestNotes').value;

      let referralNotes = `Urgency: ${urgencyVal.replace('_', ' ').toUpperCase()}`;
      if (notes) referralNotes += ` | Clinical Reason: ${notes}`;

      await submitReviewAction('support_request', reqId, 'refer_to_agency', 'referred', referralNotes, {
        target_agency: agencyVal,
        urgency: urgencyVal
      });
      document.getElementById('requestManageModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadSupportRequests();
      await loadWorkspaceOverview();
    });
  }

  // 4. Save Milestone Update
  const btnSaveMilestone = document.getElementById('btnSubmitMilestone');
  if (btnSaveMilestone) {
    btnSaveMilestone.addEventListener('click', async () => {
      const caseId = document.getElementById('modalCaseId').value;
      const stageVal = document.getElementById('modalMilestoneStageSelect').value;
      const notes = document.getElementById('modalMilestoneNotes').value;
      await submitReviewAction('case_milestone', caseId, 'update_status', stageVal, notes);
      document.getElementById('milestoneModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadCaseMilestones();
    });
  }

  // 5. Save Intervention Update
  const btnSaveIntervention = document.getElementById('btnSubmitIntervention');
  if (btnSaveIntervention) {
    btnSaveIntervention.addEventListener('click', async () => {
      const intId = document.getElementById('modalIntId').value;
      const statusVal = document.getElementById('modalIntStatusSelect').value;
      const notes = document.getElementById('modalIntNotes').value;
      await submitReviewAction('intervention', intId, 'update_status', statusVal, notes);
      document.getElementById('interventionModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadInterventions();
    });
  }
}

/**
 * Opens Official One-Stop Centre (OSC) In-Person Verification Slip Modal
 */
window.openInPersonSlipModal = function(sessionId) {
  const req = allSupportRequestsData.find(r => r.id === sessionId);
  const modal = document.getElementById('inPersonVerificationSlipModal');
  if (!modal) return;

  const passSuffix = sessionId ? sessionId.slice(0, 6).toUpperCase() : '9041A';
  let passNum = `OSC-TN-2026-${passSuffix}`;
  let meta = (req && req.session_metadata) || {};
  if (typeof meta === 'string') {
    try { meta = JSON.parse(meta); } catch (e) { meta = {}; }
  }
  if (meta.pass_number || meta.pass_code) {
    passNum = meta.pass_number || meta.pass_code;
  }

  const passEl = document.getElementById('slipPassNumber');
  if (passEl) passEl.textContent = passNum;

  const nameEl = document.getElementById('slipBeneficiaryName');
  if (nameEl) {
    let rawName = (req && req.masked_requester) || 'Protected Beneficiary';
    nameEl.textContent = rawName.replace(/\[[A-Za-z]\*{2,}[a-z]\]\s*/g, '').trim();
  }

  const caseEl = document.getElementById('slipCaseId');
  if (caseEl) {
    caseEl.textContent = (req && req.case_id_masked) || `Case #${sessionId.slice(0, 8)}`;
  }

  const timeEl = document.getElementById('slipAppointmentTime');
  if (timeEl) {
    timeEl.textContent = (req && req.appointment_at) ? formatDateTime(req.appointment_at) : 'Today, 3:00 PM IST (Confirmed)';
  }

  modal.style.display = 'flex';
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
};

window.closeInPersonSlipModal = function() {
  const modal = document.getElementById('inPersonVerificationSlipModal');
  if (modal) {
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
};

/**
 * Submits an official review action to the backend with optional extra parameters.
 */
async function submitReviewAction(targetType, targetId, actionType, statusVal, notes, extraFields = {}) {
  try {
    const res = await fetch('/api/counsellor/review-action', {
      method: 'POST',
      headers: getAuthHeaders({
        'Content-Type': 'application/json'
      }),
      credentials: 'include',
      body: JSON.stringify({
        target_type: targetType,
        target_id: targetId,
        action_type: actionType,
        status: statusVal,
        notes: notes || null,
        ...extraFields
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data;
  } catch (e) {
    console.error('Error recording review action:', e);
    alert('Could not record review action. Please try again.');
  }
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
    if (navUserName) navUserName.textContent = user.full_name || 'Official';
    if (fullNameEl) fullNameEl.textContent = user.full_name || 'Official';
    if (categoryEl) categoryEl.textContent = user.requested_category || 'counsellor';
    if (roleEl) roleEl.textContent = (user.verified_role || 'counsellor').toUpperCase();
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
  const btn = document.getElementById('langSelectorBtn') || document.getElementById('langSelectBtn');
  const dropdown = document.getElementById('langDropdown');
  const currentLangLabel = document.getElementById('selectedLangText') || document.getElementById('currentLangLabel');

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
    const isOpen = drawer.classList.contains('open') || drawer.classList.contains('active');
    drawer.classList.toggle('open', !isOpen);
    drawer.classList.toggle('active', !isOpen);
    toggleBtn.classList.toggle('active', !isOpen);
    toggleBtn.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
    const icon = toggleBtn.querySelector('i');
    if (icon) {
      icon.className = !isOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
    }
  });
}

/**
 * Direct Victim <-> Counsellor Messaging System (SIH 26094)
 */
let currentSelectedVictimId = null;
let currentSelectedVictimName = '';
let isCounsellorSendingReply = false;

async function loadDirectMessagesConversations() {
  try {
    const res = await fetch('/api/counsellor/messages/conversations', {
      headers: getAuthHeaders(),
      credentials: 'include'
    });
    if (!res.ok) return [];
    const data = await res.json();
    const convos = data.conversations || [];

    let totalUnread = 0;
    convos.forEach(c => { totalUnread += (c.unread_count || 0); });

    const badge = document.getElementById('tabBadgeMessages');
    const headerBadge = document.getElementById('headerBadgeMessages');
    const mobileBadge = document.getElementById('mobileBadgeMessages');
    const msgDisplay = (totalUnread > 0 || convos.length > 0) ? 'inline-flex' : 'none';
    const msgText = totalUnread > 0 ? totalUnread : convos.length;

    if (badge) { badge.textContent = msgText; badge.style.display = msgDisplay; }
    if (headerBadge) { headerBadge.textContent = msgText; headerBadge.style.display = msgDisplay; }
    if (mobileBadge) { mobileBadge.textContent = msgText; mobileBadge.style.display = msgDisplay; }

    const cntEl = document.getElementById('cntDirectMessages');
    if (cntEl) {
      cntEl.textContent = totalUnread > 0 ? `${totalUnread} new` : convos.length;
    }

    return convos;
  } catch (e) {
    console.warn('Failed to load conversations count:', e);
    return [];
  }
}

async function loadDirectMessages(isSilent = false) {
  const listContainer = document.getElementById('counsellorConvosList');
  if (!listContainer) return;

  if (!isSilent && !currentSelectedVictimId) {
    listContainer.innerHTML = `
      <div style="text-align: center; padding: 24px; color: #8C84A6;">
        <i class="fa-solid fa-spinner fa-spin"></i> Loading conversations...
      </div>
    `;
  }

  try {
    const res = await fetch('/api/counsellor/messages/conversations', {
      headers: getAuthHeaders(),
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const convos = data.conversations || [];

    const badge = document.getElementById('tabBadgeMessages');
    const headerBadge = document.getElementById('headerBadgeMessages');
    const mobileBadge = document.getElementById('mobileBadgeMessages');
    const cntEl = document.getElementById('cntDirectMessages');

    let totalUnread = 0;
    convos.forEach(c => { totalUnread += (c.unread_count || 0); });

    const msgDisplay = (totalUnread > 0 || convos.length > 0) ? 'inline-flex' : 'none';
    const msgText = totalUnread > 0 ? totalUnread : convos.length;

    if (badge) { badge.textContent = msgText; badge.style.display = msgDisplay; }
    if (headerBadge) { headerBadge.textContent = msgText; headerBadge.style.display = msgDisplay; }
    if (mobileBadge) { mobileBadge.textContent = msgText; mobileBadge.style.display = msgDisplay; }
    if (cntEl) {
      cntEl.textContent = totalUnread > 0 ? `${totalUnread} new` : convos.length;
    }

    if (convos.length === 0) {
      listContainer.innerHTML = `
        <div style="text-align: center; padding: 32px 14px; color: #8C84A6;">
          <i class="fa-regular fa-comment-dots" style="font-size: 1.8rem; margin-bottom: 8px;"></i>
          <p style="margin: 0; font-weight: 700; color: #2B1552;">No messages yet</p>
          <span style="font-size: 0.78rem;">When victims send messages from their trends dashboard, they will appear here.</span>
        </div>
      `;
      return;
    }

    let html = '';
    convos.forEach(c => {
      const isSelected = c.victim_id === currentSelectedVictimId;
      const unreadCount = c.unread_count || 0;
      const timeStr = formatDateTime(c.last_message_time);

      html += `
        <div class="convo-item ${isSelected ? 'active' : ''}" data-victim-id="${escapeHtml(c.victim_id)}" data-victim-name="${escapeHtml(c.victim_name)}">
          <div class="convo-item-header">
            <span class="convo-victim-name">
              <i class="fa-solid fa-user"></i> ${escapeHtml(c.victim_name)}
            </span>
            ${unreadCount > 0 ? `<span class="convo-unread-badge">${unreadCount}</span>` : ''}
          </div>
          <p class="convo-last-msg">${escapeHtml(c.last_message || 'New message')}</p>
          <span class="convo-time">${timeStr}</span>
        </div>
      `;
    });

    listContainer.innerHTML = html;

    listContainer.querySelectorAll('.convo-item').forEach(item => {
      item.addEventListener('click', () => {
        const vId = item.getAttribute('data-victim-id');
        const vName = item.getAttribute('data-victim-name');
        loadVictimThread(vId, vName);
      });
    });

    // Auto-select first conversation or update current selection
    if (currentSelectedVictimId) {
      const exists = convos.some(c => c.victim_id === currentSelectedVictimId);
      if (exists) {
        await loadVictimThread(currentSelectedVictimId, currentSelectedVictimName, true);
      } else if (convos.length > 0) {
        await loadVictimThread(convos[0].victim_id, convos[0].victim_name);
      }
    } else if (convos.length > 0) {
      await loadVictimThread(convos[0].victim_id, convos[0].victim_name);
    }
  } catch (err) {
    console.error('Failed to load conversations:', err);
  }
}

async function loadVictimThread(victimId, victimName, isSilent = false) {
  currentSelectedVictimId = victimId;
  currentSelectedVictimName = victimName || 'Victim';

  // Highlight active conversation in sidebar
  document.querySelectorAll('.convo-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-victim-id') === victimId);
  });

  const activeNameEl = document.getElementById('activeChatVictimName');
  const subtextEl = document.getElementById('activeChatSubtext');
  const actionsEl = document.getElementById('activeChatActions');
  const replyBar = document.getElementById('activeChatReplyBar');
  
  const primaryThread = document.getElementById('counsellorThreadMessages');
  const modalThread = document.getElementById('modalCounsellorThreadMessages');
  const targetThreads = [primaryThread, modalThread].filter(Boolean);

  if (activeNameEl) {
    activeNameEl.innerHTML = `<i class="fa-solid fa-user-shield" style="color: #7E57C2;"></i> ${escapeHtml(currentSelectedVictimName)}`;
  }
  if (subtextEl) {
    subtextEl.textContent = 'Direct Section 15A Protection & Psychological Care Channel';
  }
  if (actionsEl) actionsEl.style.display = 'block';
  if (replyBar) replyBar.style.display = 'block';

  if (!targetThreads.length) return;

  if (!isSilent) {
    targetThreads.forEach(t => {
      if (!t.querySelector('.chat-bubble-counsellor-wrap')) {
        t.innerHTML = `
          <div style="text-align: center; margin: auto; color: #8C84A6; padding: 20px;">
            <i class="fa-solid fa-spinner fa-spin"></i> Loading message history...
          </div>
        `;
      }
    });
  }

  try {
    const res = await fetch(`/api/counsellor/messages/${victimId}`, {
      headers: getAuthHeaders(),
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const messages = data.messages || [];

    let html = '';
    messages.forEach(msg => {
      const isCounsellor = msg.sender_role === 'counsellor';
      const timeStr = formatDateTime(msg.created_at);
      const senderLabel = isCounsellor ? 'You (Dr. Priya Nair)' : escapeHtml(msg.sender_name || currentSelectedVictimName);

      html += `
        <div class="chat-bubble-counsellor-wrap ${isCounsellor ? 'counsellor' : 'victim'}">
          <span class="c-bubble-sender">${senderLabel}</span>
          <div class="c-bubble ${isCounsellor ? 'counsellor' : 'victim'}">${escapeHtml(msg.message_text)}</div>
          <span class="c-bubble-time">${timeStr}</span>
        </div>
      `;
    });

    if (messages.length === 0) {
      html = `
        <div style="text-align: center; margin: auto; color: #8C84A6; padding: 20px;">
          <i class="fa-solid fa-comments" style="font-size: 2rem; color: #7E57C2; margin-bottom: 8px;"></i>
          <p style="font-weight: 700; color: #2B1552; margin: 0 0 4px;">Beginning of direct channel with ${escapeHtml(currentSelectedVictimName)}</p>
          <span style="font-size: 0.8rem;">Send a reassuring message to coordinate psychological care under Section 15A.</span>
        </div>
      `;
    }

    targetThreads.forEach(t => {
      const wasAtBottom = t.scrollHeight - t.scrollTop <= t.clientHeight + 100;
      t.innerHTML = html;
      if (wasAtBottom || !isSilent) {
        t.scrollTop = t.scrollHeight;
      }
    });
  } catch (err) {
    console.error('Failed to load victim thread:', err);
  }
}

function initCounsellorMessagingHandlers() {
  const refreshBtn = document.getElementById('refreshMessagesBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadDirectMessages();
      if (currentSelectedVictimId) {
        loadVictimThread(currentSelectedVictimId, currentSelectedVictimName);
      }
    });
  }

  const replyForm = document.getElementById('counsellorReplyForm');
  const textarea = document.getElementById('counsellorReplyText');

  if (replyForm) {
    replyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!currentSelectedVictimId || isCounsellorSendingReply) return;
      const text = textarea ? textarea.value.trim() : '';
      if (!text) return;

      isCounsellorSendingReply = true;
      textarea.value = '';

      // Optimistic append in visible thread
      const primaryThread = document.getElementById('counsellorThreadMessages');
      if (primaryThread) {
        if (!primaryThread.querySelector('.chat-bubble-counsellor-wrap')) {
          primaryThread.innerHTML = '';
        }
        const optimisticBubble = document.createElement('div');
        optimisticBubble.className = 'chat-bubble-counsellor-wrap counsellor';
        optimisticBubble.innerHTML = `
          <span class="c-bubble-sender">You (Dr. Priya Nair)</span>
          <div class="c-bubble counsellor">${escapeHtml(text)}</div>
          <span class="c-bubble-time"><i class="fa-regular fa-clock" style="font-size: 0.65rem;"></i> Just now</span>
        `;
        primaryThread.appendChild(optimisticBubble);
        primaryThread.scrollTop = primaryThread.scrollHeight;
      }

      try {
        const res = await fetch(`/api/counsellor/messages/${currentSelectedVictimId}/reply`, {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ message_text: text }),
          credentials: 'include'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadVictimThread(currentSelectedVictimId, currentSelectedVictimName, true);
        await loadDirectMessagesConversations();
      } catch (err) {
        console.error('Failed to send reply:', err);
        alert('Failed to send reply. Please try again.');
      } finally {
        isCounsellorSendingReply = false;
        if (textarea) textarea.focus();
      }
    });
  }

  // Modal Reply Form
  const modalReplyForm = document.getElementById('counsellorModalReplyForm');
  const modalTextarea = document.getElementById('counsellorModalReplyText');

  if (modalReplyForm) {
    modalReplyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!currentSelectedVictimId || isCounsellorSendingReply) return;
      const text = modalTextarea ? modalTextarea.value.trim() : '';
      if (!text) return;

      isCounsellorSendingReply = true;
      modalTextarea.value = '';

      try {
        const res = await fetch(`/api/counsellor/messages/${currentSelectedVictimId}/reply`, {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ message_text: text }),
          credentials: 'include'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadVictimThread(currentSelectedVictimId, currentSelectedVictimName, true);
      } catch (err) {
        alert('Failed to send reply. Please try again.');
      } finally {
        isCounsellorSendingReply = false;
      }
    });
  }

  // Quick reply templates
  document.querySelectorAll('.c-quick-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const template = btn.getAttribute('data-template');
      if (template) {
        if (modalTextarea) {
          modalTextarea.value = template;
          modalTextarea.focus();
        }
        if (textarea) {
          textarea.value = template;
          textarea.focus();
        }
      }
    });
  });
}

// Global hooks for direct chat and video modal
window.openCounsellorDirectChat = async function(victimUserId, victimName, requestId) {
  const modal = document.getElementById('counsellorDirectChatModal');
  if (!modal) return;

  currentSelectedVictimId = victimUserId;
  currentSelectedVictimName = victimName || 'Protected Beneficiary';

  const nameEl = document.getElementById('modalDirectChatVictim');
  if (nameEl) nameEl.textContent = currentSelectedVictimName;

  const subEl = document.getElementById('modalDirectChatSubtext');
  if (subEl) subEl.textContent = `Direct 1-on-1 Communication Channel • Case #${(requestId || '').slice(0, 8)}`;

  const btnVideo = document.getElementById('btnModalSwitchToVideo');
  if (btnVideo) {
    btnVideo.onclick = () => {
      closeCounsellorChatModal();
      openCounsellorVideoEnclave(requestId);
    };
  }

  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';

  await loadVictimThread(victimUserId, currentSelectedVictimName);
};

window.closeCounsellorChatModal = function() {
  const modal = document.getElementById('counsellorDirectChatModal');
  if (modal) modal.style.display = 'none';
  document.body.style.overflow = '';
};

window.openCounsellorVideoEnclave = function(sessionId) {
  const req = allSupportRequestsData.find(r => r.id === sessionId);
  _currentConsoleSessionId = sessionId;
  let roomId = 'mentaura-care-772110';
  if (req && req.session_metadata) {
    try {
      const meta = typeof req.session_metadata === 'string' ? JSON.parse(req.session_metadata) : req.session_metadata;
      roomId = meta.room_id || roomId;
    } catch (e) {}
  }
  const victimName = req ? (req.masked_requester || req.full_name || 'Aanya Sharma') : 'Aanya Sharma';

  if (window.openGoogleMeetRoom) {
    window.openGoogleMeetRoom({
      role: 'counsellor',
      sessionId: sessionId,
      roomId: roomId,
      victimName: victimName
    });
  }
};

// ==============================================================================
// 4 MULTI-MODE INTERACTIVE COUNSELLING CONSOLES (COUNSELLOR RUNTIME)
// ==============================================================================

let _activeWaveformAnimId = null;
let _activeSessionTimerInterval = null;
let _activeBreathingInterval = null;
let _currentConsoleSessionId = null;

function startAudioWaveform(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let phase = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const width = canvas.width;
    const height = canvas.height;
    const centerY = height / 2;

    ctx.strokeStyle = 'rgba(126, 87, 194, 0.2)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();

    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#7C3AED';
    ctx.beginPath();
    for (let x = 0; x < width; x++) {
      const slice = (x / width) * Math.PI * 8;
      const amp = Math.sin(phase * 0.05 + slice * 0.5) * 16 + Math.cos(phase * 0.08 + slice) * 8;
      const y = centerY + Math.sin(slice + phase * 0.1) * amp;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    ctx.lineWidth = 1.5;
    ctx.strokeStyle = 'rgba(167, 139, 250, 0.6)';
    ctx.beginPath();
    for (let x = 0; x < width; x++) {
      const slice = (x / width) * Math.PI * 6;
      const y = centerY + Math.sin(slice - phase * 0.08) * 12;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    phase++;
    _activeWaveformAnimId = requestAnimationFrame(draw);
  }

  if (_activeWaveformAnimId) cancelAnimationFrame(_activeWaveformAnimId);
  draw();
}

function stopAudioWaveform() {
  if (_activeWaveformAnimId) {
    cancelAnimationFrame(_activeWaveformAnimId);
    _activeWaveformAnimId = null;
  }
}

function startConsoleTimer(timerElementId) {
  const el = document.getElementById(timerElementId);
  if (!el) return;
  if (_activeSessionTimerInterval) clearInterval(_activeSessionTimerInterval);
  let totalSec = 0;
  el.textContent = '00:00';
  _activeSessionTimerInterval = setInterval(() => {
    totalSec++;
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    el.textContent = `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  }, 1000);
}

function stopConsoleTimer() {
  if (_activeSessionTimerInterval) {
    clearInterval(_activeSessionTimerInterval);
    _activeSessionTimerInterval = null;
  }
}

function startBreathingPacer(circleId, textId, stepInhaleId, stepHoldId, stepExhaleId) {
  const circle = document.getElementById(circleId);
  const text = document.getElementById(textId);
  const stepIn = document.getElementById(stepInhaleId);
  const stepHold = document.getElementById(stepHoldId);
  const stepEx = document.getElementById(stepExhaleId);

  if (!circle || !text) return;
  if (_activeBreathingInterval) clearInterval(_activeBreathingInterval);

  let phase = 0;
  let counter = 0;

  function setStep(step) {
    if (stepIn) stepIn.classList.toggle('active', step === 0);
    if (stepHold) stepHold.classList.toggle('active', step === 1);
    if (stepEx) stepEx.classList.toggle('active', step === 2);
  }

  function cycle() {
    if (phase === 0) {
      circle.style.transform = 'scale(1.35)';
      circle.style.background = '#EDE8FB';
      circle.style.borderColor = '#7C3AED';
      text.textContent = `Inhale (${4 - counter}s)`;
      setStep(0);
      counter++;
      if (counter >= 4) {
        phase = 1;
        counter = 0;
      }
    } else if (phase === 1) {
      circle.style.transform = 'scale(1.35)';
      circle.style.background = '#FEF3C7';
      circle.style.borderColor = '#D97706';
      text.textContent = `Hold (${7 - counter}s)`;
      setStep(1);
      counter++;
      if (counter >= 7) {
        phase = 2;
        counter = 0;
      }
    } else {
      circle.style.transform = 'scale(1.0)';
      circle.style.background = '#F0FDF4';
      circle.style.borderColor = '#15803D';
      text.textContent = `Exhale (${8 - counter}s)`;
      setStep(2);
      counter++;
      if (counter >= 8) {
        phase = 0;
        counter = 0;
      }
    }
  }

  cycle();
  _activeBreathingInterval = setInterval(cycle, 1000);
}

function stopBreathingPacer() {
  if (_activeBreathingInterval) {
    clearInterval(_activeBreathingInterval);
    _activeBreathingInterval = null;
  }
}

window.openCounsellorSessionConsole = function(sessionId) {
  const req = allSupportRequestsData.find(r => r.id === sessionId);
  if (!req) return;
  _currentConsoleSessionId = sessionId;

  let format = req.session_format || (req.session_metadata && req.session_metadata.format) || 'telephonic';
  let meta = req.session_metadata || {};
  if (typeof meta === 'string') {
    try { meta = JSON.parse(meta); } catch (e) { meta = {}; }
  }

  if (format === 'telephonic') {
    const modal = document.getElementById('counsellorTelephonicModal');
    if (!modal) return;
    document.getElementById('modalTelSessionId').value = sessionId;
    document.getElementById('modalTelVictimName').textContent = req.masked_requester || 'Beneficiary';
    document.getElementById('modalTelCaseId').textContent = req.case_id_masked || 'Case #MUM-2026-9041';
    document.getElementById('modalTelPassCode').textContent = meta.pass_code || `OSC-TN-2026-${sessionId.slice(0,6).toUpperCase()}`;
    
    const statusBadge = document.getElementById('modalTelStatusBadge');
    if (statusBadge) {
      statusBadge.textContent = req.status === 'in_progress' ? 'Call In Progress' : 'Ready to Connect';
      statusBadge.style.background = req.status === 'in_progress' ? '#DCFCE7' : '#EDE8FB';
      statusBadge.style.color = req.status === 'in_progress' ? '#15803D' : '#6D28D9';
    }

    startAudioWaveform('counsellorAudioWaveformCanvas');
    startConsoleTimer('modalTelTimer');
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

  } else if (format === 'video') {
    window.openCounsellorVideoEnclave(sessionId);

  } else if (format === 'in_person') {
    const modal = document.getElementById('counsellorOscModal');
    if (!modal) return;
    document.getElementById('modalOscSessionId').value = sessionId;
    document.getElementById('modalOscBeneficiary').textContent = req.masked_requester || 'Beneficiary';
    document.getElementById('modalOscPassNumber').textContent = meta.pass_number || meta.pass_code || `OSC-TN-2026-${sessionId.slice(0,6).toUpperCase()}`;
    const gateBadge = document.getElementById('modalOscGateStatusBadge');
    if (gateBadge) {
      if (meta.visitor_arrived || meta.gate_checked_in) {
        gateBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> Visitor Verified at Gate`;
        gateBadge.style.color = '#15803D';
      } else {
        gateBadge.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Awaiting Gate Arrival`;
        gateBadge.style.color = '#B45309';
      }
    }
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

  } else if (format === 'emergency_crisis') {
    const modal = document.getElementById('counsellorCrisisModal');
    if (!modal) return;
    document.getElementById('modalCrisisSessionId').value = sessionId;
    startBreathingPacer('counsellorBreathingCircle', 'counsellorBreathingText', 'bStepInhale', 'bStepHold', 'bStepExhale');
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
};

async function dispatchSessionAction(sessionId, action, payload = {}) {
  try {
    const res = await fetch(`/api/counsellor/sessions/${sessionId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ action, ...payload }),
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Session action error:', err);
    alert('Action failed. Please retry.');
    return null;
  }
}

// Attach console buttons
document.addEventListener('DOMContentLoaded', () => {
  // Telephonic buttons
  const btnDial = document.getElementById('btnCounsellorDialLine');
  if (btnDial) {
    btnDial.addEventListener('click', async () => {
      if (!_currentConsoleSessionId) return;
      const res = await dispatchSessionAction(_currentConsoleSessionId, 'start_call', { notes: 'IVRS Gateway connected.' });
      if (res) {
        const badge = document.getElementById('modalTelStatusBadge');
        if (badge) {
          badge.textContent = '📞 Connected (Live IVRS)';
          badge.style.background = '#DCFCE7';
          badge.style.color = '#15803D';
        }
        btnDial.innerHTML = '<i class="fa-solid fa-signal"></i> <span>Connected</span>';
        btnDial.disabled = true;
      }
    });
  }

  const btnMute = document.getElementById('btnCounsellorMuteLine');
  if (btnMute) {
    let muted = false;
    btnMute.addEventListener('click', () => {
      muted = !muted;
      btnMute.innerHTML = muted 
        ? '<i class="fa-solid fa-microphone-slash"></i> <span>Unmute</span>' 
        : '<i class="fa-solid fa-microphone"></i> <span>Mute Mic</span>';
      btnMute.style.background = muted ? '#FEE2E2' : '#EDE8FB';
      btnMute.style.color = muted ? '#DC2626' : '#6D28D9';
    });
  }

  const btnEndCall = document.getElementById('btnCounsellorEndLine');
  const btnSaveTel = document.getElementById('btnCounsellorSaveTelNotes');
  async function concludeTelephonicSession() {
    if (!_currentConsoleSessionId) return;
    const notes = document.getElementById('modalTelClinicalNotes').value;
    await dispatchSessionAction(_currentConsoleSessionId, 'end_call', { notes: notes || 'Callback session concluded.' });
    stopAudioWaveform();
    stopConsoleTimer();
    document.getElementById('counsellorTelephonicModal').style.display = 'none';
    document.body.style.overflow = '';
    await loadSupportRequests();
    await loadWorkspaceOverview();
  }
  if (btnEndCall) btnEndCall.addEventListener('click', concludeTelephonicSession);
  if (btnSaveTel) btnSaveTel.addEventListener('click', concludeTelephonicSession);

  // Video buttons
  const btnVidMic = document.getElementById('btnVideoToggleMic');
  if (btnVidMic) {
    let micOn = true;
    btnVidMic.addEventListener('click', () => {
      micOn = !micOn;
      btnVidMic.innerHTML = micOn ? '<i class="fa-solid fa-microphone"></i>' : '<i class="fa-solid fa-microphone-slash"></i>';
      btnVidMic.style.background = micOn ? '#2E214A' : '#DC2626';
    });
  }

  const btnVidCam = document.getElementById('btnVideoToggleCam');
  if (btnVidCam) {
    let camOn = true;
    btnVidCam.addEventListener('click', () => {
      camOn = !camOn;
      btnVidCam.innerHTML = camOn ? '<i class="fa-solid fa-camera"></i>' : '<i class="fa-solid fa-video-slash"></i>';
      btnVidCam.style.background = camOn ? '#2E214A' : '#DC2626';
    });
  }

  const btnVidEnd = document.getElementById('btnVideoEndConsult');
  const btnVidSave = document.getElementById('btnCounsellorSaveVideoNotes');
  async function concludeVideoSession() {
    if (!_currentConsoleSessionId) return;
    const notes = document.getElementById('modalVideoClinicalNotes').value;
    await dispatchSessionAction(_currentConsoleSessionId, 'end_video', { notes: notes || 'Video consultation finalized.' });
    stopConsoleTimer();
    document.getElementById('counsellorVideoModal').style.display = 'none';
    document.body.style.overflow = '';
    await loadSupportRequests();
    await loadWorkspaceOverview();
  }
  if (btnVidEnd) btnVidEnd.addEventListener('click', concludeVideoSession);
  if (btnVidSave) btnVidSave.addEventListener('click', concludeVideoSession);

  // OSC In-Person buttons
  const btnAdmit = document.getElementById('btnOscAdmitVisitor');
  if (btnAdmit) {
    btnAdmit.addEventListener('click', async () => {
      if (!_currentConsoleSessionId) return;
      const res = await dispatchSessionAction(_currentConsoleSessionId, 'admit_visitor');
      if (res) {
        const badge = document.getElementById('modalOscGateStatusBadge');
        if (badge) {
          badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Admitted to Clinical Enclave 104';
          badge.style.color = '#15803D';
        }
        btnAdmit.innerHTML = '<i class="fa-solid fa-check"></i> Admitted';
        btnAdmit.disabled = true;
      }
    });
  }

  const btnSaveOsc = document.getElementById('btnCounsellorSaveOscVisit');
  if (btnSaveOsc) {
    btnSaveOsc.addEventListener('click', async () => {
      if (!_currentConsoleSessionId) return;
      const hr = document.getElementById('oscVitalsHeartRate').value;
      const bp = document.getElementById('oscVitalsBP').value;
      const mse = document.getElementById('oscVitalsMentalStatus').value;
      const notes = document.getElementById('modalOscClinicalNotes').value;

      await dispatchSessionAction(_currentConsoleSessionId, 'complete_visit', {
        vitals: { heart_rate_bpm: parseInt(hr, 10) || 76, blood_pressure: bp || '120/80', mental_status_exam: mse },
        notes: notes || 'In-person OSC assessment concluded.'
      });
      document.getElementById('counsellorOscModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadSupportRequests();
      await loadWorkspaceOverview();
    });
  }

  // Crisis Suite buttons
  const btnPriCall = document.getElementById('btnCrisisPriorityCall');
  if (btnPriCall) {
    btnPriCall.addEventListener('click', async () => {
      if (!_currentConsoleSessionId) return;
      await dispatchSessionAction(_currentConsoleSessionId, 'start_call', { notes: 'Priority IVRS Emergency Call triggered.' });
      alert('Priority 1 IVRS Bridge Dispatched to Dr. Priya Nair and Beneficiary line.');
    });
  }

  const btnStabCrisis = document.getElementById('btnCounsellorStabilizeCrisis');
  if (btnStabCrisis) {
    btnStabCrisis.addEventListener('click', async () => {
      if (!_currentConsoleSessionId) return;
      const notes = document.getElementById('modalCrisisProtocolNotes').value;
      await dispatchSessionAction(_currentConsoleSessionId, 'stabilize_crisis', { notes: notes || 'Crisis stabilization protocol accomplished.' });
      stopBreathingPacer();
      document.getElementById('counsellorCrisisModal').style.display = 'none';
      document.body.style.overflow = '';
      await loadSupportRequests();
      await loadWorkspaceOverview();
    });
  }
});
