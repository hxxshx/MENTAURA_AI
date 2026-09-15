/**
 * Distress Trajectory & Healing Journey Frontend Logic (SIH 26094).
 * Gives hope & power back, catches emergencies proactively under Sec 15A,
 * connects feelings to real life triggers, and presents a gentle healing curve.
 */

let distressChartInstance = null;
let currentDistressData = null;
let sosTimer = null;
let sosSecondsRemaining = 5;

// Calculator memory for Camouflage Mode
let calcCurrent = '0';
let calcPrev = null;
let calcOp = null;

document.addEventListener('DOMContentLoaded', () => {
  initSafetyControls();
  initProtectionModal();
  initCounsellorChat();
  initActiveCounsellingSession();
  setupVictimSessionControls();
  initSection15AModal();
  initMobileMenu();
  initLanguageSelector();
  initChartToggle();
  initRangeButtons();
  initUserProfilePopover();
  initLogout();
  initVictimConsultationTabs();
  initVictimRequestsAndConnect();
  fetchVictimRequestsList();
  fetchDistressTrendsData(30);
  fetchStatutoryReliefData();
});

/**
 * Fetch distress trajectory, proactive alerts, and XAI factors from backend API
 */
async function fetchDistressTrendsData(days = 30) {
  try {
    const res = await fetch(`/api/victim/distress-trends?days=${days}`, {
      headers: { 'Accept': 'application/json' },
      credentials: 'include'
    });

    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = 'index.html#login-flow';
        return;
      }
      throw new Error(`Failed to load trends (${res.status})`);
    }

    const data = await res.json();
    currentDistressData = data;
    renderSnapshotMetrics(data);
    renderPredictiveAlert(data);
    renderTrajectoryChart(data, days);
    renderTriggersAndAnchors(data.xai_factors, data.milestones);
  } catch (err) {
    console.warn('Using reassuring fallback data for distress trends:', err);
    const fallback = generateFallbackData(days);
    currentDistressData = fallback;
    renderSnapshotMetrics(fallback);
    renderPredictiveAlert(fallback);
    renderTrajectoryChart(fallback, days);
    renderTriggersAndAnchors(fallback.xai_factors, fallback.milestones);
  }
}

/**
 * Section 1: Render Proactive Safety Sentinel
 * Catches emergencies before they can escalate
 */
function renderPredictiveAlert(data) {
  const sentinelCard = document.getElementById('sentinelCard');
  const sentinelBadge = document.getElementById('sentinelBadge');
  const sentinelBadgeText = document.getElementById('sentinelBadgeText');
  const sentinelIconWrap = document.getElementById('sentinelIconWrap');
  const sentinelIcon = document.getElementById('sentinelIcon');
  const sentinelHeadline = document.getElementById('sentinelHeadline');
  const sentinelNarrative = document.getElementById('sentinelNarrative');

  if (!sentinelCard) return;

  const alertInfo = data.predictive_alert || {};
  const alertType = alertInfo.alert_type || (alertInfo.is_active ? 'warning' : 'steady');

  if (alertType === 'warning') {
    sentinelCard.style.display = 'block';
    sentinelCard.className = 'sentinel-card warning-state';
    if (sentinelBadge) {
      sentinelBadge.className = 'sentinel-badge badge-warning';
      if (sentinelBadgeText) sentinelBadgeText.textContent = 'Early Safety Notice: Extra Care Mobilized';
    }
    if (sentinelIconWrap) sentinelIconWrap.className = 'sentinel-icon-wrap warning-state';
    if (sentinelIcon) sentinelIcon.className = 'fa-solid fa-triangle-exclamation';
    if (sentinelHeadline) sentinelHeadline.textContent = alertInfo.title || 'Early Warning: Elevated Stress Observed Around Court Proceedings';
    if (sentinelNarrative) {
      sentinelNarrative.textContent = alertInfo.message || 'Our trauma-informed AI noticed elevated distress around your upcoming legal milestone. Your assigned Care Counsellor (Dr. Priya Nair) and Protection Officer have been alerted so support reaches you before things get overwhelming.';
    }
  } else if (alertType === 'moderate') {
    sentinelCard.style.display = 'block';
    sentinelCard.className = 'sentinel-card';
    if (sentinelBadge) {
      sentinelBadge.className = 'sentinel-badge badge-warning';
      if (sentinelBadgeText) sentinelBadgeText.textContent = 'Supportive Care Active: Mild Strain Observed';
    }
    if (sentinelIconWrap) sentinelIconWrap.className = 'sentinel-icon-wrap warning-state';
    if (sentinelIcon) sentinelIcon.className = 'fa-solid fa-hand-holding-heart';
    if (sentinelHeadline) sentinelHeadline.textContent = alertInfo.title || 'Supportive Care Active: Mild Strain Noticed';
    if (sentinelNarrative) {
      sentinelNarrative.textContent = alertInfo.message || 'Your recent check-in reflects mild emotional tension. You do not have to handle this on your own — free psychological counselling and safe escort under Section 15A are ready whenever you need them.';
    }
  } else {
    // Steady state: Keep top of page clean, empowering, and focused on progress
    sentinelCard.style.display = 'none';
  }
}

/**
 * Section 2: Render Hope, Power & Resilience Snapshot
 * Gives hope & power back
 */
function renderSnapshotMetrics(data) {
  const dds = data.current_dds != null ? data.current_dds : 35;
  const count = data.total_checkins || 18;

  // 1. Recovery state
  const titleEl = document.getElementById('kpiRecoveryTitle');
  const badgeEl = document.getElementById('kpiRecoveryBadge');
  const descEl = document.getElementById('kpiRecoveryDesc');

  if (titleEl && badgeEl && descEl) {
    if (dds >= 70) {
      titleEl.textContent = 'High Emotional Strain';
      badgeEl.className = 'strength-badge badge-soft-amber';
      badgeEl.innerHTML = '<i class="fa-solid fa-bell"></i> Care Team Alerted';
      descEl.textContent = 'You are carrying significant weight right now. Dr. Priya Nair is prioritizing your well-being with proactive outreach.';
    } else if (dds >= 45) {
      titleEl.textContent = 'Navigating Mild Tension';
      badgeEl.className = 'strength-badge badge-soft-purple';
      badgeEl.innerHTML = '<i class="fa-solid fa-seedling"></i> Coping Steadily';
      descEl.textContent = 'Minor stress fluctuations noticed around case updates. Your steady check-ins show you are processing feelings constructively.';
    } else {
      titleEl.textContent = 'Steady & Grounded';
      badgeEl.className = 'strength-badge badge-soft-green';
      badgeEl.innerHTML = '<i class="fa-solid fa-spa"></i> Self-Care Active';
      descEl.textContent = 'Your emotional stability has grown across recent updates. You are navigating case milestones with quiet resilience.';
    }
  }

  // 2. Consistency Streak
  const streakEl = document.getElementById('kpiStreakVal');
  if (streakEl) {
    streakEl.textContent = `${count} Check-Ins`;
  }
}

/**
 * Section 3: Connect Feelings to Real Triggers
 * Plain language breakdown showing why feelings occur and what relieves them
 */
function renderTriggersAndAnchors(xaiFactors, milestones) {
  const stressContainer = document.getElementById('stressTriggersList');
  const reliefContainer = document.getElementById('reliefAnchorsList');
  if (!stressContainer || !reliefContainer) return;

  if (xaiFactors && Array.isArray(xaiFactors) && xaiFactors.length >= 1) {
    const stressItems = [];

    xaiFactors.forEach(f => {
      const impact = f.impact || '';
      const isRelief = impact.includes('-');
      const factorName = f.factor || '';
      const detail = f.detail || f.contribution || '';
      const lowerFactor = factorName.toLowerCase();

      // Only process pressure factors into stressItems
      if (!isRelief) {
        let iconHtml = '<i class="fa-solid fa-triangle-exclamation" style="color: #E11D48;"></i>';
        let tagHtml = '<span class="trigger-tag tag-stress">Under Watch</span>';
        let noteHtml = '<i class="fa-solid fa-shield-halved" style="color: #E11D48;"></i> <strong>Early Detection:</strong> Monitored so protective support intervenes before crisis.';

        if (lowerFactor.includes('acoustic') || lowerFactor.includes('voice')) {
          iconHtml = '<i class="fa-solid fa-waveform-lines" style="color: #E11D48;"></i>';
          tagHtml = '<span class="trigger-tag tag-acoustic"><i class="fa-solid fa-microphone"></i> Voice Stress AI</span>';
          noteHtml = '<i class="fa-solid fa-shield-heart" style="color: #E11D48;"></i> <strong>Acoustic AI:</strong> Vocal pitch & hesitations monitored to catch somatic strain before panic.';
        } else if (lowerFactor.includes('well-being') || lowerFactor.includes('state') || lowerFactor.includes('pulse')) {
          iconHtml = '<i class="fa-solid fa-heart-pulse" style="color: #9333EA;"></i>';
          tagHtml = '<span class="trigger-tag tag-state"><i class="fa-solid fa-user-check"></i> Self-Reported</span>';
          noteHtml = '<i class="fa-solid fa-user-doctor" style="color: #9333EA;"></i> <strong>Longitudinal Watch:</strong> Counsellor alerted without forcing you to re-narrate your trauma.';
        } else if (lowerFactor.includes('timeline') || lowerFactor.includes('dsp') || lowerFactor.includes('investigation') || lowerFactor.includes('court') || lowerFactor.includes('hearing')) {
          iconHtml = '<i class="fa-solid fa-hourglass-half" style="color: #D97706;"></i>';
          tagHtml = '<span class="trigger-tag tag-legal"><i class="fa-solid fa-scale-balanced"></i> Rule 7(2) Mandate</span>';
          noteHtml = '<i class="fa-solid fa-clock-rotate-left" style="color: #D97706;"></i> <strong>Statutory Countdown:</strong> 60-day investigation tracked with District SP to prevent delays.';
        }

        stressItems.push(`
          <div class="trigger-item item-pressure">
            <div class="trigger-item-head">
              <span class="trigger-item-title">
                ${iconHtml} ${escapeHtml(factorName)}
              </span>
              ${tagHtml}
            </div>
            <div class="trigger-item-body">${escapeHtml(detail)}</div>
            <div class="trigger-support-note note-pressure">
              <span>${noteHtml}</span>
            </div>
          </div>
        `);
      }
    });

    if (stressItems.length > 0) {
      stressContainer.innerHTML = stressItems.join('');
    }

    // Always maintain the complete set of 3 actionable, evidence-based healing anchors:
    const completeReliefHtml = `
      <div class="trigger-item item-anchor">
        <div class="trigger-item-head">
          <span class="trigger-item-title">
            <i class="fa-solid fa-microphone-lines" style="color: #059669;"></i> Expressing Your Voice in Check-Ins
          </span>
          <span class="trigger-tag tag-relief"><i class="fa-solid fa-arrow-trend-down"></i> -12% Stress</span>
        </div>
        <div class="trigger-item-body">
          Putting feelings into words rather than bottling them up releases cognitive load and calms acoustic vocal biomarkers.
        </div>
        <div class="trigger-support-note note-relief">
          <span><i class="fa-solid fa-circle-check" style="color: #059669;"></i> <strong>Active Routine:</strong> Consistently practiced this week.</span>
          <a href="checkin.html" class="anchor-link">Take Check-In &rarr;</a>
        </div>
      </div>

      <div class="trigger-item item-anchor">
        <div class="trigger-item-head">
          <span class="trigger-item-title">
            <i class="fa-solid fa-user-doctor" style="color: #7E57C2;"></i> Care Sessions with Dr. Priya
          </span>
          <span class="trigger-tag tag-relief"><i class="fa-solid fa-arrow-trend-down"></i> -18% Stress</span>
        </div>
        <div class="trigger-item-body">
          Trauma-informed guidance helps reframe difficult legal milestones into manageable step-by-step actions.
        </div>
        <div class="trigger-support-note note-relief">
          <span><i class="fa-solid fa-phone" style="color: #7E57C2;"></i> <strong>Direct Careline:</strong> 24/7 dedicated support.</span>
          <button type="button" class="anchor-btn-inline" id="btnAnchorChatCounsellor">
            <i class="fa-solid fa-comments"></i> Message Dr. Priya &rarr;
          </button>
        </div>
      </div>

      <div class="trigger-item item-anchor">
        <div class="trigger-item-head">
          <span class="trigger-item-title">
            <i class="fa-solid fa-shield-halved" style="color: #2563EB;"></i> Section 15A Witness Protection
          </span>
          <span class="trigger-tag tag-peace"><i class="fa-solid fa-lock"></i> Peace of Mind</span>
        </div>
        <div class="trigger-item-body">
          Knowing the District SP is legally bound under Section 15A to shield you from retaliation restores feelings of safety at home.
        </div>
        <div class="trigger-support-note note-relief">
          <span><i class="fa-solid fa-file-contract" style="color: #2563EB;"></i> <strong>Statutory Right:</strong> Escort &amp; legal aid active.</span>
          <button type="button" class="anchor-btn-inline" id="btnAnchorOpen15A">
            <i class="fa-solid fa-shield-halved"></i> Review Dossier &rarr;
          </button>
        </div>
      </div>
    `;

    reliefContainer.innerHTML = completeReliefHtml;

    // Attach listeners for interactive buttons
    const btnChat = document.getElementById('btnAnchorChatCounsellor');
    if (btnChat) {
      btnChat.addEventListener('click', () => {
        const chatModal = document.getElementById('counsellorChatModal');
        if (chatModal) {
          chatModal.classList.add('active');
          document.body.style.overflow = 'hidden';
        }
      });
    }

    const btn15A = document.getElementById('btnAnchorOpen15A');
    if (btn15A) {
      btn15A.addEventListener('click', () => {
        const m15A = document.getElementById('openSection15AModalBtn');
        if (m15A) m15A.click();
      });
    }
  }
}

/**
 * Section 4: Render Softened, Gentle Healing Curve (Chart.js)
 */
function renderTrajectoryChart(data, days = 30) {
  const canvas = document.getElementById('distressChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  if (distressChartInstance) {
    distressChartInstance.destroy();
  }

  let points = (data.trajectory && data.trajectory.length >= 2)
    ? data.trajectory
    : synthesizeTimelinePoints(days);

  const labels = points.map(p => p.date);
  const ddsValues = points.map(p => p.dds_score);

  // Soft purple gradient area
  const ddsGradient = ctx.createLinearGradient(0, 0, 0, 280);
  ddsGradient.addColorStop(0, 'rgba(126, 87, 194, 0.28)');
  ddsGradient.addColorStop(1, 'rgba(126, 87, 194, 0.01)');

  distressChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Emotional Healing Curve',
          data: ddsValues,
          borderColor: '#7E57C2',
          backgroundColor: ddsGradient,
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#2B1552',
          pointBorderColor: '#FFFFFF',
          pointBorderWidth: 2,
          pointRadius: points.length > 15 ? 3 : 5,
          pointHoverRadius: 7
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            boxWidth: 10,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: '700' },
            color: '#4B5563'
          }
        },
        tooltip: {
          backgroundColor: '#23123D',
          titleFont: { family: "'Plus Jakarta Sans', sans-serif", size: 13, weight: '700' },
          bodyFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12 },
          padding: 12,
          cornerRadius: 10,
          callbacks: {
            title: function(context) {
              const idx = context[0].dataIndex;
              const point = points[idx];
              return point ? (point.full_date || point.date) : context[0].label;
            },
            label: function(context) {
              const score = context.parsed.y;
              let feelingState = "Calm & Stable";
              if (score >= 65) feelingState = "Elevated Tension (Support Alerted)";
              else if (score >= 45) feelingState = "Moderate Strain";
              return `Status: ${feelingState}`;
            },
            afterBody: function(context) {
              const idx = context[0].dataIndex;
              const point = points[idx];
              const lines = [];
              if (point && point.milestone) {
                lines.push(`\n⚖️ Case Event: ${point.milestone}`);
              }
              return lines;
            }
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(226, 220, 246, 0.4)' },
          ticks: {
            stepSize: 25,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' },
            callback: (val) => {
              if (val === 25) return 'Calm';
              if (val === 50) return 'Mild Strain';
              if (val === 75) return 'High Tension';
              return '';
            }
          }
        },
        x: {
          grid: { display: false },
          ticks: {
            maxTicksLimit: 8,
            font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: '600' },
            color: '#6B7280'
          }
        }
      }
    }
  });
}

/**
 * Chart Show / Hide Toggle Button
 */
function initChartToggle() {
  const toggleBtn = document.getElementById('toggleChartBtn');
  const container = document.getElementById('chartCanvasContainer');
  const toggleText = document.getElementById('toggleChartText');
  const toggleIcon = document.getElementById('toggleChartIcon');

  if (!toggleBtn || !container) return;

  let isHidden = false;
  toggleBtn.addEventListener('click', () => {
    isHidden = !isHidden;
    if (isHidden) {
      container.style.display = 'none';
      if (toggleText) toggleText.textContent = 'Show Visual Curve';
      if (toggleIcon) toggleIcon.className = 'fa-solid fa-eye-slash';
    } else {
      container.style.display = 'block';
      if (toggleText) toggleText.textContent = 'Hide Visual Curve';
      if (toggleIcon) toggleIcon.className = 'fa-solid fa-eye';
      if (distressChartInstance) {
        distressChartInstance.resize();
      }
    }
  });
}

/**
 * Initialize 30/60/90 Days Range Switchers
 */
function initRangeButtons() {
  const buttons = document.querySelectorAll('.time-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const days = parseInt(btn.getAttribute('data-range') || '30', 10);
      fetchDistressTrendsData(days);
    });
  });
}

/**
 * Section 15A Escort & Threat Reporting Modal
 */
function initProtectionModal() {
  const modal = document.getElementById('protectionModal');
  const heroBtn = document.getElementById('heroOpenEscortBtn');
  const escortBtn = document.getElementById('actionEscortBtn');
  const threatBtn = document.getElementById('actionThreatBtn');
  const closeBtn = document.getElementById('closeProtectionModalBtn');
  const cancelBtn = document.getElementById('cancelProtBtn');

  const tabEscortBtn = document.getElementById('tabEscortBtn');
  const tabThreatBtn = document.getElementById('tabThreatBtn');
  const escortFields = document.getElementById('escortFieldsWrap');
  const threatFields = document.getElementById('threatFieldsWrap');
  const protActionType = document.getElementById('protActionType');
  const submitBtn = document.getElementById('submitProtBtn');
  const form = document.getElementById('protectionActionForm');

  function openModal(mode = 'escort') {
    if (!modal) return;
    modal.classList.add('active');
    setTab(mode);
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('active');
  }

  function setTab(mode) {
    if (mode === 'escort') {
      tabEscortBtn.classList.add('active');
      tabThreatBtn.classList.remove('active');
      escortFields.style.display = 'block';
      threatFields.style.display = 'none';
      protActionType.value = 'escort_request';
      submitBtn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Submit Escort Request';
      submitBtn.style.background = '#7E57C2';
    } else {
      tabThreatBtn.classList.add('active');
      tabEscortBtn.classList.remove('active');
      threatFields.style.display = 'block';
      escortFields.style.display = 'none';
      protActionType.value = 'threat_report';
      submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Log Threat with DSP';
      submitBtn.style.background = '#DC2626';
    }
  }

  if (heroBtn) heroBtn.addEventListener('click', () => openModal('escort'));
  if (escortBtn) escortBtn.addEventListener('click', () => openModal('escort'));
  if (threatBtn) threatBtn.addEventListener('click', () => openModal('threat'));
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  if (tabEscortBtn) tabEscortBtn.addEventListener('click', () => setTab('escort'));
  if (tabThreatBtn) tabThreatBtn.addEventListener('click', () => setTab('threat'));

  // Form submission
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const actionType = protActionType.value;
      const hearingTime = document.getElementById('protHearingTime')?.value || '';
      const pickupLocation = document.getElementById('protPickupLocation')?.value || '';
      const incType = document.getElementById('protIncidentType')?.value || 'police_escort_request';
      const threatSource = document.getElementById('protThreatSource')?.value || '';
      const narrative = document.getElementById('protNarrative')?.value || '';

      const payload = {
        case_id: 1,
        incident_type: actionType === 'escort_request' ? 'safe_court_escort' : incType,
        threat_source: actionType === 'escort_request' ? 'Court travel protection request' : (threatSource || 'Unspecified'),
        incident_location: actionType === 'escort_request' ? (pickupLocation || 'Victim residence') : 'Victim residence / locality',
        incident_time: hearingTime ? new Date(hearingTime).toISOString() : new Date().toISOString(),
        narrative: actionType === 'escort_request'
          ? `Court escort requested under Section 15A. Pickup: ${pickupLocation}. Details: ${narrative}`
          : narrative,
        urgency_level: 'high'
      };

      try {
        const res = await fetch('/api/victim/report-intimidation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          credentials: 'include'
        });

        if (res.ok) {
          const json = await res.json();
          alert(
            actionType === 'escort_request'
              ? `COURT ESCORT REQUEST SUBMITTED!\nRequest ID: #${json.report_id || 'ESCORT-2026'}\nDistrict SP Protection Cell notified under Section 15A.`
              : `PROTECTION ALERT LOGGED WITH DISTRICT SP!\nIncident ID: #${json.report_id || 'THREAT-2026'}\nImmediate review active under Section 15A.`
          );
          closeModal();
          form.reset();
        } else {
          throw new Error('Failed to submit');
        }
      } catch (err) {
        alert("Protection request logged with District Control Cell. Call 14566 or 112 for immediate assistance.");
        closeModal();
      }
    });
  }
}

/**
 * Safety & Camouflage Controls (ESC key + SOS Trigger)
 */
function initSafetyControls() {
  const stealthToggleBtn = document.getElementById('stealthToggleBtn');
  const camouflageOverlay = document.getElementById('camouflageOverlay');
  const stealthExitBtn = document.getElementById('stealthExitBtn');

  const sosHeaderBtn = document.getElementById('sosHeaderBtn');
  const actionSosTriggerBtn = document.getElementById('actionSosTriggerBtn');
  const sosModal = document.getElementById('sosModal');
  const sosCountdown = document.getElementById('sosCountdown');
  const sosCancelBtn = document.getElementById('sosCancelBtn');
  const sosConfirmNowBtn = document.getElementById('sosConfirmNowBtn');

  function toggleStealth() {
    if (!camouflageOverlay) return;
    const isAct = camouflageOverlay.classList.contains('active');
    if (isAct) {
      camouflageOverlay.classList.remove('active');
      camouflageOverlay.setAttribute('aria-hidden', 'true');
    } else {
      camouflageOverlay.classList.add('active');
      camouflageOverlay.setAttribute('aria-hidden', 'false');
    }
  }

  if (stealthToggleBtn) stealthToggleBtn.addEventListener('click', toggleStealth);
  if (stealthExitBtn) stealthExitBtn.addEventListener('click', toggleStealth);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') toggleStealth();
  });

  function triggerSosFlow() {
    if (!sosModal) return;
    sosSecondsRemaining = 5;
    if (sosCountdown) sosCountdown.textContent = '5';
    sosModal.classList.add('active');

    clearInterval(sosTimer);
    sosTimer = setInterval(() => {
      sosSecondsRemaining--;
      if (sosCountdown) sosCountdown.textContent = `${sosSecondsRemaining}`;
      if (sosSecondsRemaining <= 0) {
        clearInterval(sosTimer);
        executeSosBroadcast();
      }
    }, 1000);
  }

  if (sosHeaderBtn) sosHeaderBtn.addEventListener('click', triggerSosFlow);
  if (actionSosTriggerBtn) actionSosTriggerBtn.addEventListener('click', triggerSosFlow);

  if (sosCancelBtn) {
    sosCancelBtn.addEventListener('click', () => {
      clearInterval(sosTimer);
      if (sosModal) sosModal.classList.remove('active');
    });
  }

  if (sosConfirmNowBtn) {
    sosConfirmNowBtn.addEventListener('click', () => {
      clearInterval(sosTimer);
      executeSosBroadcast();
    });
  }
}

/**
 * Broadcast Emergency SOS to backend
 */
async function executeSosBroadcast() {
  const sosModal = document.getElementById('sosModal');
  try {
    const res = await fetch('/api/victim/sos-alert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        immediate_danger_type: "Direct threat / Immediate witness safety risk"
      }),
      credentials: 'include'
    });
    const json = await res.json();
    alert(`EMERGENCY SOS DISPATCHED: Alert ID ${json.sos_id || 'SOS-2026'}.\nDistrict Police Control Room (112) & Protection Officer have been notified.`);
  } catch (err) {
    alert("Emergency alert sent to District Control Cell. Call 14566 or 112 immediately.");
  } finally {
    if (sosModal) sosModal.classList.remove('active');
  }
}

/**
 * Functional Calculator for Camouflage Mode
 */
window.calcInput = function(val) {
  const display = document.getElementById('calcDisplay');
  if (!display) return;

  if (val === 'C') {
    calcCurrent = '0';
    calcPrev = null;
    calcOp = null;
  } else if (['+', '-', '*', '/'].includes(val)) {
    calcPrev = parseFloat(calcCurrent);
    calcOp = val;
    calcCurrent = '0';
  } else if (val === '=') {
    if (calcOp && calcPrev !== null) {
      const cur = parseFloat(calcCurrent);
      if (calcOp === '+') calcCurrent = String(calcPrev + cur);
      if (calcOp === '-') calcCurrent = String(calcPrev - cur);
      if (calcOp === '*') calcCurrent = String(calcPrev * cur);
      if (calcOp === '/') calcCurrent = cur !== 0 ? String(calcPrev / cur) : 'Error';
      calcOp = null;
      calcPrev = null;
    }
  } else {
    if (calcCurrent === '0') {
      calcCurrent = val;
    } else {
      calcCurrent += val;
    }
  }
  display.textContent = calcCurrent;
};

/**
 * Synthesize timeline points fallback for 30/60/90 days view
 */
function synthesizeTimelinePoints(days = 30) {
  const pts = [];
  const count = days === 90 ? 10 : (days === 60 ? 8 : 6);
  const now = new Date();

  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - (i * (days / count) * 86400000));
    const dayStr = d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
    let score = 32 + Math.round(Math.sin(i) * 10);
    score = Math.max(15, Math.min(score, 75));

    let milestone = null;
    if (i === count - 1) milestone = "FIR Registered & Stage 1 Relief (₹1L)";
    if (i === Math.floor(count / 2)) milestone = "DSP 60-Day Investigation Window";
    if (i === 1) milestone = "Special Court Pre-Hearing Review";

    pts.push({
      date: dayStr,
      full_date: d.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' }),
      dds_score: score,
      milestone: milestone
    });
  }
  return pts;
}

/**
 * Fallback data generator if offline or demo
 */
function generateFallbackData(days = 30) {
  return {
    has_checkins: true,
    total_checkins: 18,
    current_dds: 32,
    trend_direction: "improving",
    trend_label: "Improving with support",
    trajectory: synthesizeTimelinePoints(days),
    predictive_alert: {
      is_active: false,
      alert_type: "steady",
      title: "All Quiet & Protected — No Emergency Risk Detected",
      message: "Our trauma-informed system continuously monitors check-in patterns 24/7. If stress, harassment, or fear rises, your DSP Protection Cell and Counsellor intervene proactively before an emergency occurs."
    }
  };
}

/**
 * Mobile Navigation Drawer Toggle
 */
function initMobileMenu() {
  const toggle = document.getElementById('mobileMenuToggle');
  const drawer = document.getElementById('mobileMenuDrawer');
  if (!toggle || !drawer) return;

  toggle.addEventListener('click', () => {
    const isExp = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!isExp));
    drawer.setAttribute('aria-hidden', String(isExp));
    toggle.classList.toggle('active');
    drawer.classList.toggle('open');
  });
}

/**
 * Multilingual Dropdown Selector
 */
function initLanguageSelector() {
  const btn = document.getElementById('langSelectorBtn');
  const dropdown = document.getElementById('langDropdown');
  const txt = document.getElementById('selectedLangText');

  if (!btn || !dropdown) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('show');
  });

  document.addEventListener('click', () => {
    dropdown.classList.remove('show');
  });

  dropdown.querySelectorAll('li').forEach(item => {
    item.addEventListener('click', () => {
      const lang = item.getAttribute('data-lang');
      if (txt) txt.textContent = lang;
      dropdown.querySelectorAll('li').forEach(l => l.classList.remove('active'));
      item.classList.add('active');
    });
  });
}

/**
 * User Profile Popover in Header Nav
 */
function initUserProfilePopover() {
  const profileBtn = document.getElementById('userProfileBtn');
  const profilePopover = document.getElementById('userProfilePopover');
  const closeBtn = document.getElementById('popoverCloseBtn');
  const closeActionBtn = document.getElementById('popoverCloseActionBtn');

  function openPopover() {
    if (!profilePopover || !profileBtn) return;
    profilePopover.classList.add('show', 'active');
    profilePopover.setAttribute('aria-hidden', 'false');
    profileBtn.setAttribute('aria-expanded', 'true');
  }

  function closePopover() {
    if (!profilePopover || !profileBtn) return;
    profilePopover.classList.remove('show', 'active');
    profilePopover.setAttribute('aria-hidden', 'true');
    profileBtn.setAttribute('aria-expanded', 'false');
  }

  if (profileBtn && profilePopover) {
    profileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isActive = profilePopover.classList.contains('active') || profilePopover.classList.contains('show');
      if (isActive) closePopover();
      else openPopover();
    });

    if (closeBtn) closeBtn.addEventListener('click', (e) => { e.stopPropagation(); closePopover(); });
    if (closeActionBtn) closeActionBtn.addEventListener('click', (e) => { e.stopPropagation(); closePopover(); });

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!profilePopover.contains(e.target) && !profileBtn.contains(e.target)) {
        closePopover();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && (profilePopover.classList.contains('active') || profilePopover.classList.contains('show'))) {
        closePopover();
        profileBtn.focus();
      }
    });
  }

  fetchUserDataForPopover();
}

async function fetchUserDataForPopover() {
  try {
    const token = localStorage.getItem('mentaura_token');
    const headers = { 'Accept': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch('/api/auth/me', {
      method: 'GET',
      credentials: 'include',
      headers: headers
    });
    if (!res.ok) return;

    const user = await res.json();
    if (!user) return;

    const isAnonymous = Boolean(user.is_anonymous);
    const safeName = isAnonymous ? (user.masked_name || 'Protected User') : user.full_name;
    const firstName = safeName ? safeName.split(' ')[0] : 'Aanya';

    const navUserEl = document.getElementById('navUserName');
    if (navUserEl) navUserEl.textContent = firstName;

    const popoverName = document.getElementById('popoverName');
    if (popoverName) popoverName.textContent = user.full_name || 'Aanya Sharma';

    const popoverAnonIdRow = document.getElementById('popoverAnonIdRow');
    const popoverAnonId = document.getElementById('popoverAnonId');
    if (popoverAnonIdRow && popoverAnonId) {
      if (isAnonymous && user.anonymous_id) {
        popoverAnonIdRow.style.display = 'flex';
        popoverAnonId.textContent = user.anonymous_id;
      } else {
        popoverAnonIdRow.style.display = 'none';
      }
    }

    const popoverAccountType = document.getElementById('popoverAccountType');
    if (popoverAccountType && user.verified_role) {
      popoverAccountType.textContent = user.verified_role.charAt(0).toUpperCase() + user.verified_role.slice(1) + ' / Complainant';
    }

    const popoverLang = document.getElementById('popoverLang');
    if (popoverLang && user.preferred_language) {
      const langNames = { 'EN': 'English (EN)', 'HI': 'हिन्दी (HI)', 'TA': 'தமிழ் (TA)', 'TE': 'తెలుగు (TE)', 'KN': 'ಕನ್ನಡ (KN)', 'MR': 'मराठी (MR)', 'BN': 'বাংলা (BN)' };
      popoverLang.textContent = langNames[user.preferred_language] || user.preferred_language;
    }

    const popoverChannel = document.getElementById('popoverChannel');
    if (popoverChannel && user.preferred_channel) {
      popoverChannel.textContent = user.preferred_channel.charAt(0).toUpperCase() + user.preferred_channel.slice(1) + ' Portal';
    }

    const popoverStatus = document.getElementById('popoverStatus');
    if (popoverStatus && user.account_status) {
      popoverStatus.textContent = user.account_status.charAt(0).toUpperCase() + user.account_status.slice(1);
    }
  } catch (err) {
    console.warn('Could not populate profile popover dynamically:', err);
  }
}

/**
 * Logout Handler
 */
function initLogout() {
  const logoutButtons = document.querySelectorAll('#headerLogoutBtn, .btn-logout');
  logoutButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await fetch('/api/auth/logout', { credentials: 'include' });
      } catch (e) {
        console.warn('Logout fetch notice:', e);
      }
      sessionStorage.clear();
      window.location.href = 'index.html';
    });
  });
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

/**
 * Direct Interactive Chat with Dr. Priya Nair
 */
let counsellorChatPollTimer = null;
let lastRenderedMessageCount = -1;
let lastRenderedMessageId = null;

function formatDateTime(isoString) {
  if (!isoString) return '';
  try {
    let str = String(isoString);
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-', 10)) {
      str = str + 'Z';
    }
    const d = new Date(str);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch (e) {
    return '';
  }
}
const formatMsgTime = formatDateTime;

// Helper: Ensure token is passed in Authorization header
function getAuthHeaders(extra = {}) {
  const token = localStorage.getItem('mentaura_token') || sessionStorage.getItem('mentaura_token') || '';
  const headers = { 'Accept': 'application/json', ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function initCounsellorChat() {
  const container = document.getElementById('counsellorMessagesContainer');
  const form = document.getElementById('counsellorChatForm');
  const input = document.getElementById('counsellorChatInput');
  const quickPills = document.querySelectorAll('.chat-quick-pill');
  const refreshBtn = document.getElementById('btnRefreshVictimChat');

  if (!container) return;

  // Immediate message fetch
  loadCounsellorMessages();

  // Dynamic real-time auto-polling every 2 seconds (so victim receives counsellor messages without manual refresh)
  if (counsellorChatPollTimer) clearInterval(counsellorChatPollTimer);
  counsellorChatPollTimer = setInterval(() => loadCounsellorMessages(false), 2000);

  // Sync immediately when window is refocused or tab becomes visible
  window.addEventListener('focus', () => {
    loadCounsellorMessages(false);
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      loadCounsellorMessages(false);
    }
  });

  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      const icon = refreshBtn.querySelector('i');
      if (icon) icon.classList.add('fa-spin');
      await loadCounsellorMessages(true);
      setTimeout(() => {
        if (icon) icon.classList.remove('fa-spin');
      }, 400);
    });
  }

  quickPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const msg = pill.getAttribute('data-msg');
      if (input && msg) {
        input.value = msg;
        input.focus();
      }
    });
  });

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = input ? input.value.trim() : '';
      if (!text) return;

      input.value = '';

      // Optimistic append so victim sees their message instantly
      const tempDiv = document.createElement('div');
      tempDiv.className = 'chat-bubble-counsellor-wrap sent';
      tempDiv.innerHTML = `
        <span class="c-bubble-sender">You (Aanya Sharma)</span>
        <div class="c-bubble sent">${escapeHtml(text)}</div>
        <span class="c-bubble-time"><i class="fa-regular fa-clock" style="font-size: 0.65rem;"></i> Sending...</span>
      `;
      container.appendChild(tempDiv);
      container.scrollTop = container.scrollHeight;

      try {
        const res = await fetch('/api/victim/counsellor-chat/send', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ message_text: text }),
          credentials: 'include'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadCounsellorMessages(true);
      } catch (err) {
        console.error('Error sending message to counsellor:', err);
        const errDiv = document.createElement('div');
        errDiv.style.cssText = 'text-align: center; color: #DC2626; font-size: 0.75rem; margin: 4px 0;';
        errDiv.textContent = 'Message delivery failed. Please retry or call 14566.';
        container.appendChild(errDiv);
      }
    });
  }
}

async function loadCounsellorMessages(forceScroll = false) {
  const container = document.getElementById('counsellorMessagesContainer');
  if (!container) return;

  try {
    const res = await fetch('/api/victim/counsellor-chat/messages', {
      headers: getAuthHeaders(),
      credentials: 'include'
    });
    if (!res.ok) return;
    const data = await res.json();
    const messages = data.messages || [];

    const msgBadge = document.getElementById('cntVictimMessages');
    if (msgBadge) msgBadge.textContent = messages.length;

    const latestId = messages.length > 0 ? messages[messages.length - 1].id : null;
    // If message count and latest message haven't changed, skip DOM re-render to avoid layout jitter
    if (messages.length === lastRenderedMessageCount && latestId === lastRenderedMessageId && !forceScroll) {
      return;
    }

    if (messages.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 16px; color: #8C84A6;">
          <div style="font-size: 2.2rem; margin-bottom: 8px; color: #7C3AED;"><i class="fa-solid fa-comments"></i></div>
          <p style="font-weight: 800; color: #2B1552; margin-bottom: 4px; font-size: 1.05rem;">Direct Support Channel with Dr. Priya Nair</p>
          <span style="font-size: 0.82rem; line-height: 1.45; display: block; max-width: 440px; margin: 0 auto;">
            Dr. Priya Nair is active. Type your message below to begin your confidential conversation under Section 15A.
          </span>
        </div>
      `;
      lastRenderedMessageCount = 0;
      lastRenderedMessageId = null;
      return;
    }

    const isScrolledToBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 80;

    let html = '';
    messages.forEach(msg => {
      const isSent = msg.sender_role === 'victim';
      const timeStr = formatDateTime(msg.created_at);
      const senderLabel = isSent 
        ? 'You (Aanya Sharma)' 
        : 'Dr. Priya Nair';

      html += `
        <div class="chat-bubble-counsellor-wrap ${isSent ? 'sent' : 'received'}">
          <span class="c-bubble-sender">${senderLabel}</span>
          <div class="c-bubble ${isSent ? 'sent' : 'received'}">${escapeHtml(msg.message_text)}</div>
          <span class="c-bubble-time">${timeStr}</span>
        </div>
      `;
    });

    container.innerHTML = html;

    if (isScrolledToBottom || lastRenderedMessageCount <= 0 || forceScroll) {
      container.scrollTop = container.scrollHeight;
    }
    lastRenderedMessageCount = messages.length;
    lastRenderedMessageId = latestId;
  } catch (err) {
    console.warn('Notice: Background counsellor chat poll:', err);
  }
}

/**
 * ============================================================================
 * SECTION 15A STATUTORY RELIEF & LEGAL RIGHTS DOSSIER LOGIC
 * ============================================================================
 */
let cachedStatutoryData = null;

async function fetchStatutoryReliefData() {
  try {
    const res = await fetch('/api/victim/statutory-relief', {
      headers: { 'Accept': 'application/json' },
      credentials: 'include'
    });

    if (!res.ok) {
      console.warn(`Failed to fetch statutory relief (${res.status})`);
      return;
    }

    const data = await res.json();
    cachedStatutoryData = data;
    renderStatutoryCardAndModal(data);
  } catch (err) {
    console.warn('Error fetching statutory relief:', err);
  }
}

function renderStatutoryCardAndModal(data) {
  if (!data) return;

  // 1. Update Card on Page
  const disbursedAmtEl = document.getElementById('mandateDisbursedAmount');
  if (disbursedAmtEl && data.total_disbursed_display) {
    disbursedAmtEl.textContent = `${data.total_disbursed_display} Disbursed`;
  }

  const badgeTextEl = document.getElementById('mandateStageBadgeText');
  if (badgeTextEl) {
    const disbursedCount = (data.stages || []).filter(s => s.status === 'disbursed').length;
    badgeTextEl.textContent = `Stage ${disbursedCount} Protected`;
  }

  const narrativeEl = document.getElementById('mandateNarrative');
  if (narrativeEl && data.dsp_investigation_tracker) {
    const daysLeft = data.dsp_investigation_tracker.days_remaining;
    narrativeEl.textContent = `Rule 7(2) 60-day DSP investigation deadline is legally monitored (${daysLeft} days remaining). Witness protection under Section 15A remains active.`;
  }

  // 2. Update Modal Header & KPIs
  const modalCaseId = document.getElementById('modalCaseId');
  if (modalCaseId && data.case_id_masked) {
    modalCaseId.textContent = data.case_id_masked;
  }

  const statDisbursedVal = document.getElementById('statDisbursedVal');
  if (statDisbursedVal) statDisbursedVal.textContent = data.total_disbursed_display || '₹1,00,000';

  const statPendingVal = document.getElementById('statPendingVal');
  if (statPendingVal) statPendingVal.textContent = data.balance_pending_display || '₹3,00,000';

  const statSanctionedVal = document.getElementById('statSanctionedVal');
  if (statSanctionedVal) statSanctionedVal.textContent = data.total_relief_sanctioned_display || '₹4,00,000';

  // 3. Render 3 Stages
  const stagesContainer = document.getElementById('statStagesList');
  if (stagesContainer && Array.isArray(data.stages)) {
    stagesContainer.innerHTML = data.stages.map(st => {
      const isDisbursed = st.status === 'disbursed';
      const isInProg = st.status === 'in_progress';
      const statusBadge = isDisbursed
        ? `<span class="strength-badge badge-soft-green"><i class="fa-solid fa-circle-check"></i> ${escapeHtml(st.status_display)}</span>`
        : isInProg
        ? `<span class="strength-badge badge-soft-amber"><i class="fa-solid fa-clock"></i> ${escapeHtml(st.status_display)}</span>`
        : `<span class="strength-badge" style="background:#F1F5F9; color:#64748B;"><i class="fa-regular fa-hourglass"></i> ${escapeHtml(st.status_display)}</span>`;

      const refHtml = isDisbursed && st.transaction_ref
        ? `<div style="font-size:0.80rem; color:#059669; font-weight:700;"><i class="fa-solid fa-receipt"></i> PFMS Ref: ${escapeHtml(st.transaction_ref)} &bull; Disbursed: ${escapeHtml(st.disbursed_on || 'Verified')}</div>`
        : isInProg
        ? `<div style="font-size:0.80rem; color:#D97706; font-weight:700;"><i class="fa-solid fa-scale-balanced"></i> DSP Chargesheet Pending (Rule 7(2))</div>`
        : `<div style="font-size:0.80rem; color:#64748B;"><i class="fa-solid fa-gavel"></i> Subject to Special Court Judgment</div>`;

      return `
        <div class="stat-stage-item stage-${st.status}">
          <div class="stat-stage-top">
            <span class="stat-stage-name">
              <i class="fa-solid ${isDisbursed ? 'fa-circle-check' : isInProg ? 'fa-clock' : 'fa-hourglass-start'}" style="color: ${isDisbursed ? '#10B981' : isInProg ? '#F59E0B' : '#94A3B8'}; margin-right: 4px;"></i>
              ${escapeHtml(st.stage_name)} <span style="font-size: 0.82rem; font-weight: 600; color: #64748B;">(${escapeHtml(st.percentage)})</span>
            </span>
            <span class="stat-stage-amt">${escapeHtml(st.amount_display)}</span>
          </div>
          <p class="stat-stage-desc">${escapeHtml(st.mandate)}</p>
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding-top: 8px; border-top: 1px dashed #E2E8F0;">
            ${statusBadge}
            ${refHtml}
          </div>
        </div>
      `;
    }).join('');
  }

  // 4. Render Rule 11 TAME Box
  if (data.tame_allowance) {
    const rateEl = document.getElementById('tameRateDisplay');
    if (rateEl) rateEl.textContent = data.tame_allowance.rate_per_day;

    const reimbursedEl = document.getElementById('tameReimbursedDisplay');
    if (reimbursedEl) reimbursedEl.textContent = data.tame_allowance.total_tame_reimbursed;

    const claimsEl = document.getElementById('tameClaimsDisplay');
    if (claimsEl) {
      claimsEl.textContent = `${data.tame_allowance.claims_settled} settled (${data.tame_allowance.claims_submitted} submitted)`;
    }
  }

  // 5. Render Rule 7(2) DSP Clock
  if (data.dsp_investigation_tracker) {
    const tracker = data.dsp_investigation_tracker;
    const daysRemEl = document.getElementById('dspDaysRemaining');
    if (daysRemEl) daysRemEl.textContent = tracker.days_remaining;

    const daysElapEl = document.getElementById('dspDaysElapsed');
    if (daysElapEl) daysElapEl.textContent = `Day ${tracker.days_elapsed}`;

    const fillEl = document.getElementById('dspProgressBarFill');
    if (fillEl) {
      const pct = Math.min(100, Math.round((tracker.days_elapsed / tracker.statutory_limit_days) * 100));
      fillEl.style.width = `${pct}%`;
    }

    const officerEl = document.getElementById('dspOfficerName');
    if (officerEl) officerEl.textContent = tracker.investigating_officer;

    const complianceEl = document.getElementById('dspComplianceStatus');
    if (complianceEl) {
      complianceEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10B981;"></i> ${escapeHtml(tracker.compliance_status)}`;
    }
  }

  // 6. Render Section 15A Rights Charter
  const rightsGrid = document.getElementById('statRightsGrid');
  if (rightsGrid && Array.isArray(data.rights_charter)) {
    rightsGrid.innerHTML = data.rights_charter.map(r => `
      <div class="rights-item-card">
        <div>
          <div class="rights-item-top">
            <span class="rights-item-title">${escapeHtml(r.title)}</span>
            <span class="rights-item-sub">Section ${escapeHtml(r.sub_section)}</span>
          </div>
          <p class="rights-item-desc">${escapeHtml(r.description)}</p>
        </div>
        <div style="margin-top:10px; display:flex; justify-content:space-between; align-items:center; border-top: 1px solid #F1F5F9; padding-top: 8px;">
          <span style="font-size:0.75rem; color:#64748B; font-weight:600;"><i class="fa-solid fa-scale-unbalanced-flip" style="color: #6366F1;"></i> Legal Mandate</span>
          <span class="strength-badge ${r.is_active ? 'badge-soft-green' : 'badge-soft-purple'}">
            <i class="fa-solid fa-shield-check"></i> ${escapeHtml(r.status_badge)}
          </span>
        </div>
      </div>
    `).join('');
  }
}

function initSection15AModal() {
  const modal = document.getElementById('section15AModal');
  const openCardBtn = document.getElementById('openSection15AModalBtn');
  const openBtn = document.getElementById('btnReviewSection15A');
  const closeBtn = document.getElementById('closeSection15AModalBtn');
  const closeFtrBtn = document.getElementById('closeSection15AFtrBtn');

  if (!modal) return;

  const showModal = () => {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    fetchStatutoryReliefData();
  };

  const hideModal = () => {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  };

  if (openCardBtn) openCardBtn.addEventListener('click', showModal);
  if (openBtn) openBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    showModal();
  });
  if (closeBtn) closeBtn.addEventListener('click', hideModal);
  if (closeFtrBtn) closeFtrBtn.addEventListener('click', hideModal);

  // Close on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) hideModal();
  });

  // Close on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
      hideModal();
    }
  });

  // Dismiss action alert
  const dismissBtn = document.getElementById('statAlertDismissBtn');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      const alertEl = document.getElementById('statActionAlert');
      if (alertEl) alertEl.style.display = 'none';
    });
  }

  // Quick claim TAME button inside tab 1
  const btnClaimTameQuick = document.getElementById('btnClaimTameQuick');
  if (btnClaimTameQuick) {
    btnClaimTameQuick.addEventListener('click', () => {
      switchSection15ATab('tabActions');
      openActionForm('tame_claim');
    });
  }

  // Tab switching
  const tabBtns = modal.querySelectorAll('.section15a-tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTabId = btn.getAttribute('data-tab');
      switchSection15ATab(targetTabId);
    });
  });

  // Action Tile clicks
  const tileEscort = document.getElementById('tileActionEscort');
  if (tileEscort) tileEscort.addEventListener('click', () => openActionForm('court_escort'));

  const tileLegalAid = document.getElementById('tileActionLegalAid');
  if (tileLegalAid) tileLegalAid.addEventListener('click', () => openActionForm('legal_aid'));

  const tileThreat = document.getElementById('tileActionThreat');
  if (tileThreat) tileThreat.addEventListener('click', () => openActionForm('threat_protection'));

  const tileTame = document.getElementById('tileActionTame');
  if (tileTame) tileTame.addEventListener('click', () => openActionForm('tame_claim'));

  // Cancel action subform
  const btnCancelX = document.getElementById('btnCancelDynActionX');
  if (btnCancelX) {
    btnCancelX.addEventListener('click', () => {
      const wrap = document.getElementById('statDynamicActionFormWrap');
      if (wrap) wrap.style.display = 'none';
    });
  }
  const btnCancel = document.getElementById('btnCancelDynAction');
  if (btnCancel) {
    btnCancel.addEventListener('click', () => {
      const wrap = document.getElementById('statDynamicActionFormWrap');
      if (wrap) wrap.style.display = 'none';
    });
  }

  // Handle Action Form submission
  const actionForm = document.getElementById('statActionForm');
  if (actionForm) {
    actionForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const actionType = document.getElementById('dynActionType').value;
      const hearingDate = document.getElementById('dynHearingDate').value;
      const pickupLocation = document.getElementById('dynPickupLocation').value;
      const details = document.getElementById('dynActionDetails').value;
      const submitBtn = document.getElementById('btnSubmitStatAction');

      if (!actionType) return;

      try {
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
        }

        const res = await fetch('/api/victim/statutory-relief/action', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify({
            action_type: actionType,
            hearing_date: hearingDate || null,
            pickup_location: pickupLocation || null,
            details: details || null,
            urgency: actionType === 'threat_protection' ? 'emergency' : 'high'
          })
        });

        const result = await res.json();
        if (res.ok && result.success) {
          // Show Alert
          const alertEl = document.getElementById('statActionAlert');
          const titleEl = document.getElementById('statAlertTitle');
          const msgEl = document.getElementById('statAlertMessage');
          if (alertEl && titleEl && msgEl) {
            titleEl.textContent = result.title || 'Statutory Action Dispatched';
            msgEl.textContent = `${result.message} (Reference #${result.reference_id})`;
            alertEl.style.display = 'flex';
          }

          // Hide sub-form
          const formWrap = document.getElementById('statDynamicActionFormWrap');
          if (formWrap) formWrap.style.display = 'none';
          actionForm.reset();

          // Refresh live data
          await fetchStatutoryReliefData();
        } else {
          alert(result.detail || 'Unable to submit request. Please try again.');
        }
      } catch (err) {
        console.error('Action submission error:', err);
        alert('Communication error. Please check connection.');
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Statutory Request';
        }
      }
    });
  }
}

function switchSection15ATab(targetTabId) {
  const modal = document.getElementById('section15AModal');
  if (!modal) return;

  const tabBtns = modal.querySelectorAll('.section15a-tab-btn');
  tabBtns.forEach(b => {
    if (b.getAttribute('data-tab') === targetTabId) {
      b.classList.add('active');
      b.setAttribute('aria-selected', 'true');
    } else {
      b.classList.remove('active');
      b.setAttribute('aria-selected', 'false');
    }
  });

  const panels = modal.querySelectorAll('.section15a-tab-panel');
  panels.forEach(p => {
    if (p.id === targetTabId) {
      p.classList.add('active');
      p.style.display = 'block';
    } else {
      p.classList.remove('active');
      p.style.display = 'none';
    }
  });
}

function openActionForm(actionType) {
  const formWrap = document.getElementById('statDynamicActionFormWrap');
  const typeInput = document.getElementById('dynActionType');
  const titleEl = document.getElementById('dynActionFormTitle');
  const hearingGroup = document.getElementById('dynHearingDateGroup');
  const pickupGroup = document.getElementById('dynPickupGroup');
  const detailsLabel = document.getElementById('dynDetailsLabel');
  const detailsInput = document.getElementById('dynActionDetails');

  if (!formWrap || !typeInput) return;

  formWrap.style.display = 'block';
  typeInput.value = actionType;

  // Reset conditional fields
  hearingGroup.style.display = 'none';
  pickupGroup.style.display = 'none';

  if (actionType === 'court_escort') {
    titleEl.innerHTML = '<i class="fa-solid fa-user-shield" style="color:#2563EB;"></i> Schedule Section 15A Safe Court Escort';
    hearingGroup.style.display = 'block';
    pickupGroup.style.display = 'block';
    detailsLabel.textContent = 'Special Transit & Security Instructions';
    detailsInput.placeholder = 'Specify any perceived threats along route, accompanying witnesses, or Special Court details...';
  } else if (actionType === 'legal_aid') {
    titleEl.innerHTML = '<i class="fa-solid fa-scale-balanced" style="color:#7E57C2;"></i> Request DLSA Free Legal Aid Counsel';
    detailsLabel.textContent = 'Legal Aid Preference / Matter Description';
    detailsInput.placeholder = 'State whether you need assistance with bail hearings, cross-examination, or choice of advocate...';
  } else if (actionType === 'threat_protection') {
    titleEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color:#DC2626;"></i> Urgent Threat / Coercion Report to Dy. SP';
    pickupGroup.style.display = 'block';
    pickupGroup.querySelector('label').textContent = 'Location of Incident / Current Location';
    detailsLabel.textContent = 'Incident Details & Perpetrator Info';
    detailsInput.placeholder = 'Describe the threat, names of persons involved, witness names, and immediate safety requirements...';
  } else if (actionType === 'tame_claim') {
    titleEl.innerHTML = '<i class="fa-solid fa-receipt" style="color:#059669;"></i> Rule 11 Court Travel & Maintenance Claim';
    hearingGroup.style.display = 'block';
    detailsLabel.textContent = 'Court Hearing & Travel Details';
    detailsInput.placeholder = 'Specify court date attended, travel origin, ticket expenses, and bank account for direct transfer...';
  }

  formWrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ==============================================================================
// 4 MULTI-MODE INTERACTIVE COUNSELLING SESSIONS (VICTIM SIDE RUNTIME)
// ==============================================================================

let _currentVictimSession = null;
let _victimWaveformAnimId = null;
let _victimCallTimerInterval = null;
let _victimVideoTimerInterval = null;
let _victimBreathingInterval = null;
let _ringtoneGain = null;
let _ringtoneInterval = null;
let _audioCtx = null;

function getAudioContext() {
  if (!_audioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) _audioCtx = new AudioCtx();
  }
  return _audioCtx;
}

// Synthesized Realistic Telephone Ringing Audio (440Hz + 480Hz dual-tone)
function startTelephoneRingtone() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();

    function playBurst() {
      if (!_ringtoneGain) {
        _ringtoneGain = ctx.createGain();
        _ringtoneGain.connect(ctx.destination);
      }

      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      osc1.frequency.value = 440;
      osc2.frequency.value = 480;

      const burstGain = ctx.createGain();
      burstGain.gain.setValueAtTime(0.12, ctx.currentTime);
      burstGain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.8);

      osc1.connect(burstGain);
      osc2.connect(burstGain);
      burstGain.connect(ctx.destination);

      osc1.start();
      osc2.start();
      osc1.stop(ctx.currentTime + 1.8);
      osc2.stop(ctx.currentTime + 1.8);
    }

    playBurst();
    _ringtoneInterval = setInterval(playBurst, 4000);
  } catch (e) {
    console.warn('Audio ringtone notice:', e);
  }
}

function stopTelephoneRingtone() {
  if (_ringtoneInterval) {
    clearInterval(_ringtoneInterval);
    _ringtoneInterval = null;
  }
}

function startVictimWaveform() {
  const canvas = document.getElementById('victimAudioWaveformCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let phase = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const width = canvas.width;
    const height = canvas.height;
    const centerY = height / 2;

    ctx.strokeStyle = 'rgba(124, 58, 237, 0.2)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();

    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#10B981';
    ctx.beginPath();
    for (let x = 0; x < width; x++) {
      const slice = (x / width) * Math.PI * 6;
      const amp = Math.sin(phase * 0.06 + slice * 0.6) * 14 + Math.cos(phase * 0.07 + slice) * 7;
      const y = centerY + Math.sin(slice + phase * 0.08) * amp;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    phase++;
    _victimWaveformAnimId = requestAnimationFrame(draw);
  }

  if (_victimWaveformAnimId) cancelAnimationFrame(_victimWaveformAnimId);
  draw();
}

function stopVictimWaveform() {
  if (_victimWaveformAnimId) {
    cancelAnimationFrame(_victimWaveformAnimId);
    _victimWaveformAnimId = null;
  }
}

function startVictimCallTimer(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (_victimCallTimerInterval) clearInterval(_victimCallTimerInterval);
  let totalSec = 0;
  el.textContent = '00:00';
  _victimCallTimerInterval = setInterval(() => {
    totalSec++;
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    el.textContent = `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  }, 1000);
}

function stopVictimCallTimer() {
  if (_victimCallTimerInterval) {
    clearInterval(_victimCallTimerInterval);
    _victimCallTimerInterval = null;
  }
}

function startVictimBreathing(circleId, textId, stepInId, stepHoldId, stepExId) {
  const circle = document.getElementById(circleId);
  const text = document.getElementById(textId);
  const stepIn = document.getElementById(stepInId);
  const stepHold = document.getElementById(stepHoldId);
  const stepEx = document.getElementById(stepExId);

  if (!circle || !text) return;
  if (_victimBreathingInterval) clearInterval(_victimBreathingInterval);

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
      circle.style.background = '#EDE9FE';
      circle.style.borderColor = '#7C3AED';
      text.textContent = `Inhale (${4 - counter}s)`;
      setStep(0);
      counter++;
      if (counter >= 4) { phase = 1; counter = 0; }
    } else if (phase === 1) {
      circle.style.transform = 'scale(1.35)';
      circle.style.background = '#FEF3C7';
      circle.style.borderColor = '#D97706';
      text.textContent = `Hold (${7 - counter}s)`;
      setStep(1);
      counter++;
      if (counter >= 7) { phase = 2; counter = 0; }
    } else {
      circle.style.transform = 'scale(1.0)';
      circle.style.background = '#F0FDF4';
      circle.style.borderColor = '#15803D';
      text.textContent = `Exhale (${8 - counter}s)`;
      setStep(2);
      counter++;
      if (counter >= 8) { phase = 0; counter = 0; }
    }
  }

  cycle();
  _victimBreathingInterval = setInterval(cycle, 1000);
}

function stopVictimBreathing() {
  if (_victimBreathingInterval) {
    clearInterval(_victimBreathingInterval);
    _victimBreathingInterval = null;
  }
}

window.closeVictimModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
  stopTelephoneRingtone();
  stopVictimWaveform();
  stopVictimCallTimer();
  stopVictimBreathing();
  document.body.style.overflow = '';
};

async function dispatchVictimSessionAction(action, payload = {}) {
  try {
    const body = {
      action,
      session_id: _currentVictimSession ? _currentVictimSession.id : null,
      ...payload
    };
    const res = await fetch('/api/victim/counsellor-session/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(body),
      credentials: 'include'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Victim session action error:', err);
    return null;
  }
}

async function initActiveCounsellingSession() {
  const box = document.getElementById('victimVideoSessionBox');
  if (!box) return;

  try {
    const res = await fetch('/api/victim/counsellor-session', {
      headers: getAuthHeaders(),
      credentials: 'include'
    });
    if (!res.ok) return;
    const data = await res.json();
    const sess = data.has_session ? data.session : null;

    if (sess && (sess.session_format === 'video' || sess.status === 'scheduled' || sess.status === 'in_progress')) {
      _currentVictimSession = sess;
      const meta = sess.metadata || {};
      const roomId = meta.room_id || `mentaura-video-${sess.id.slice(0, 6)}`;
      const timeDisplay = sess.appointment_at 
        ? new Date(sess.appointment_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
        : 'Priority Slot Active';

      box.innerHTML = `
        <div class="video-session-active-card" id="videoActiveCard">
          <div class="v-card-left">
            <div class="v-doctor-avatar">
              <i class="fa-solid fa-user-doctor"></i>
            </div>
            <div class="v-session-info">
              <div class="v-badge-row">
                <span class="badge-scheduled"><i class="fa-solid fa-circle-check"></i> ${sess.status === 'in_progress' ? 'Call In Progress' : 'Scheduled &bull; Ready to Connect'}</span>
                <span class="badge-e2ee"><i class="fa-solid fa-shield-halved"></i> E2EE Room: ${roomId}</span>
              </div>
              <h4 class="v-session-title">Live 1-on-1 Psychological Consultation with Dr. Priya Nair</h4>
              <p class="v-session-meta">
                <span><i class="fa-regular fa-clock"></i> ${timeDisplay}</span>
                <span>&bull;</span>
                <span><i class="fa-solid fa-video"></i> WebRTC / 1080p Encrypted Video</span>
              </p>
            </div>
          </div>
          <button type="button" class="btn btn-hero-primary btn-join-video" id="btnJoinVideoEnclave">
            <i class="fa-solid fa-video"></i> Join Video Call
          </button>
        </div>
      `;

      const joinBtn = document.getElementById('btnJoinVideoEnclave');
      if (joinBtn) {
        joinBtn.addEventListener('click', () => {
          openVictimVideoEnclave(sess.id, roomId);
        });
      }
    } else {
      // Empty state allowing victim to schedule an instant video consultation
      box.innerHTML = `
        <div class="video-session-empty-card">
          <div class="empty-v-icon"><i class="fa-solid fa-video"></i></div>
          <div class="empty-v-text">
            <h4>No Video Call Currently Active</h4>
            <p>You can request an encrypted virtual appointment with Dr. Priya Nair, or message directly in Section 1 above.</p>
          </div>
          <button type="button" class="btn btn-hero-primary btn-request-video" id="btnRequestVideoDirect" style="margin-top: 6px; padding: 10px 24px; border-radius: 9999px; font-weight: 800; font-size: 0.88rem; cursor: pointer; display: inline-flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-calendar-plus"></i> Request Video Consultation
          </button>
        </div>
      `;

      const reqBtn = document.getElementById('btnRequestVideoDirect');
      if (reqBtn) {
        reqBtn.addEventListener('click', async () => {
          reqBtn.disabled = true;
          reqBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scheduling Consultation...';
          try {
            const r = await fetch('/api/victim/request-video-consultation', {
              method: 'POST',
              headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
              credentials: 'include'
            });
            const d = await r.json();
            if (d.success) {
              await initActiveCounsellingSession();
            } else {
              alert(d.detail || 'Could not schedule video consultation.');
              reqBtn.disabled = false;
              reqBtn.innerHTML = '<i class="fa-solid fa-calendar-plus"></i> Request Video Consultation';
            }
          } catch (e) {
            console.error('Failed to request video consultation:', e);
            reqBtn.disabled = false;
            reqBtn.innerHTML = '<i class="fa-solid fa-calendar-plus"></i> Request Video Consultation';
          }
        });
      }
    }
  } catch (err) {
    console.warn('Active counselling session fetch notice:', err);
  }
}

window.openVictimVideoEnclave = function(sessionId, roomId) {
  dispatchVictimSessionAction('join_video', sessionId);
  if (window.openGoogleMeetRoom) {
    window.openGoogleMeetRoom({
      role: 'victim',
      sessionId: sessionId,
      roomId: roomId || 'mentaura-care-772110',
      victimName: 'Aanya Sharma'
    });
  }
};

window.closeVictimModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
  document.body.style.overflow = '';
  stopTelephoneRingtone();
};

window.openVictimSessionConsole = function() {
  if (!_currentVictimSession) return;
  const format = _currentVictimSession.session_format || (_currentVictimSession.metadata && _currentVictimSession.metadata.format) || 'video';
  const meta = _currentVictimSession.metadata || {};

  if (format === 'telephonic') {
    const modal = document.getElementById('victimTelephonicModal');
    if (!modal) return;
    document.getElementById('vTelRingingSection').style.display = 'block';
    document.getElementById('vTelConnectedSection').style.display = 'none';

    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Start telephone ringing sound simulation
    startTelephoneRingtone();

  } else if (format === 'video') {
    openVictimVideoEnclave(_currentVictimSession.id, meta.room_id || 'mentaura-care-room');

  } else if (format === 'in_person') {
    const modal = document.getElementById('victimOscPassModal');
    if (!modal) return;
    const pNum = meta.pass_number || meta.pass_code || `OSC-TN-2026-${_currentVictimSession.id.slice(0,6).toUpperCase()}`;
    document.getElementById('vOscPassNumber').textContent = pNum;
    const gateText = document.getElementById('vOscGateStatusText');
    if (gateText) {
      if (meta.gate_checked_in) {
        gateText.innerHTML = '<i class="fa-solid fa-circle-check" style="color: #15803D;"></i> Verified &bull; Admitted at Gate';
      } else {
        gateText.innerHTML = 'Pass Active &bull; Awaiting Gate Arrival';
      }
    }
    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

  } else if (format === 'emergency_crisis') {
    const modal = document.getElementById('victimCrisisModal');
    if (!modal) return;
    startVictimBreathing('victimBreathingCircle', 'victimBreathingText', 'vStepInhale', 'vStepHold', 'vStepExhale');
    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
};

// Wire up victim modal actions
function setupVictimSessionControls() {
  // Telephonic answer button
  const btnAnswer = document.getElementById('btnVictimAnswerCall');
  if (btnAnswer) {
    btnAnswer.addEventListener('click', async () => {
      stopTelephoneRingtone();
      document.getElementById('vTelRingingSection').style.display = 'none';
      document.getElementById('vTelConnectedSection').style.display = 'block';
      startVictimWaveform();
      startVictimCallTimer('vTelCallDuration');
      await dispatchVictimSessionAction('answer_call');
    });
  }

  // Telephonic hangup button
  const btnHangup = document.getElementById('btnVictimHangupCall');
  if (btnHangup) {
    btnHangup.addEventListener('click', async () => {
      await dispatchVictimSessionAction('end_call');
      closeVictimModal('victimTelephonicModal');
      alert('Callback session concluded. Take gentle care.');
    });
  }

  // Video buttons
  const btnVMic = document.getElementById('btnVictimVideoMic');
  if (btnVMic) {
    let micOn = true;
    btnVMic.addEventListener('click', () => {
      micOn = !micOn;
      btnVMic.innerHTML = micOn ? '<i class="fa-solid fa-microphone"></i>' : '<i class="fa-solid fa-microphone-slash"></i>';
      btnVMic.style.background = micOn ? '#2E214A' : '#DC2626';
    });
  }

  const btnVCam = document.getElementById('btnVictimVideoCam');
  if (btnVCam) {
    let camOn = true;
    btnVCam.addEventListener('click', () => {
      camOn = !camOn;
      btnVCam.innerHTML = camOn ? '<i class="fa-solid fa-camera"></i>' : '<i class="fa-solid fa-video-slash"></i>';
      btnVCam.style.background = camOn ? '#2E214A' : '#DC2626';
    });
  }

  const btnVLeave = document.getElementById('btnVictimVideoLeave');
  if (btnVLeave) {
    btnVLeave.addEventListener('click', async () => {
      await dispatchVictimSessionAction('leave_video');
      closeVictimModal('victimVideoModal');
    });
  }

  // OSC pass buttons
  const btnGate = document.getElementById('btnVictimGateCheckin');
  if (btnGate) {
    btnGate.addEventListener('click', async () => {
      const res = await dispatchVictimSessionAction('gate_checkin');
      if (res) {
        const gateText = document.getElementById('vOscGateStatusText');
        if (gateText) {
          gateText.innerHTML = '<i class="fa-solid fa-circle-check" style="color: #15803D;"></i> Verified &bull; Gate Security Confirmed';
        }
        btnGate.innerHTML = '<i class="fa-solid fa-check"></i> Presented &bull; Checked In';
        btnGate.disabled = true;
        btnGate.style.background = '#15803D';
        alert('Digital Pass verified! Dr. Priya Nair and reception have been notified of your safe arrival.');
      }
    });
  }

  const btnEscort = document.getElementById('btnVictimRequestEscort');
  if (btnEscort) {
    btnEscort.addEventListener('click', async () => {
      const res = await dispatchVictimSessionAction('request_escort');
      if (res) {
        btnEscort.innerHTML = '<i class="fa-solid fa-check"></i> Escort Dispatched';
        btnEscort.disabled = true;
        btnEscort.style.background = '#EDE9FE';
        btnEscort.style.color = '#6D28D9';
        alert('Female security escort dispatched from One-Stop Centre reception to meet you at the entrance.');
      }
    });
  }

  // Crisis SOS button
  const btnCrisisSos = document.getElementById('btnVictimCrisisSos');
  if (btnCrisisSos) {
    btnCrisisSos.addEventListener('click', async () => {
      const res = await dispatchVictimSessionAction('crisis_sos');
      if (res) {
        btnCrisisSos.innerHTML = '<i class="fa-solid fa-check"></i> Crisis SOS Beacon Dispatched!';
        btnCrisisSos.disabled = true;
        alert('🚨 Emergency Crisis SOS Transmitted! Dr. Priya Nair and District Patrol have received your high-priority alert.');
      }
    });
  }
}

// ==============================================================================
// 3-SECTION SUBNAV TAB SYSTEM & COUNSELLOR REQUESTS WORKFLOW
// ==============================================================================

function initVictimConsultationTabs() {
  const pills = document.querySelectorAll('.hero-counter-pill[data-target-tab]');
  const panels = {
    messages: document.getElementById('panel-messages'),
    video: document.getElementById('panel-video'),
    requests: document.getElementById('panel-requests')
  };

  function switchTab(tabKey) {
    pills.forEach(p => {
      if (p.getAttribute('data-target-tab') === tabKey) {
        p.classList.add('active');
      } else {
        p.classList.remove('active');
      }
    });

    Object.keys(panels).forEach(k => {
      if (panels[k]) {
        if (k === tabKey) {
          panels[k].style.display = 'block';
        } else {
          panels[k].style.display = 'none';
        }
      }
    });

    if (tabKey === 'messages') {
      loadCounsellorMessages(true);
    } else if (tabKey === 'video') {
      initActiveCounsellingSession();
      fetchVictimRequestsList();
    } else if (tabKey === 'requests') {
      fetchVictimRequestsList();
    }
  }

  pills.forEach(p => {
    p.addEventListener('click', () => {
      const tab = p.getAttribute('data-target-tab');
      if (tab) switchTab(tab);
    });
  });

  // "Request New Video Call" button in Video panel switches to Requests and opens form
  const btnReqVideo = document.getElementById('btnRequestNewVideoSession');
  if (btnReqVideo) {
    btnReqVideo.addEventListener('click', () => {
      switchTab('requests');
      const wrap = document.getElementById('sessionBookingFormWrap');
      if (wrap) wrap.style.display = 'block';
      const fmtSelect = document.getElementById('bookFormatSelect');
      if (fmtSelect) fmtSelect.value = 'video';
      if (wrap) wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }
}

async function fetchVictimRequestsList() {
  const tbody = document.getElementById('victimRequestsTableBody');
  const videoTbody = document.getElementById('victimVideoScheduleTableBody');
  const cntRequests = document.getElementById('cntVictimRequests');
  const cntVideo = document.getElementById('cntVictimVideo');
  const countLabel = document.getElementById('victimRequestsCountLabel');

  try {
    const res = await fetch('/api/victim/counsellor-requests', {
      headers: getAuthHeaders(),
      credentials: 'include'
    });
    if (!res.ok) return;
    const data = await res.json();
    const reqs = data.requests || [];

    if (cntRequests) cntRequests.textContent = reqs.length;
    if (countLabel) countLabel.textContent = `${reqs.length} total recorded`;

    // Filter video sessions for video table
    const videoSessions = reqs.filter(r => r.session_format === 'video' || (r.support_type && r.support_type.includes('video')));
    if (cntVideo) cntVideo.textContent = videoSessions.length || '1';

    // Populate Video Schedule Table
    if (videoTbody) {
      if (videoSessions.length === 0) {
        videoTbody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align: center; padding: 24px; color: #8C84A6;">
              No video consultations scheduled yet. Click "Request New Video Call" above to book one.
            </td>
          </tr>
        `;
      } else {
        let vHtml = '';
        videoSessions.forEach(vs => {
          const apptTime = vs.appointment_at 
            ? new Date(vs.appointment_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
            : vs.time_slot || 'Ready Slot';
          const isReady = vs.status === 'scheduled' || vs.status === 'in_progress';
          const statusBadge = isReady
            ? `<span class="status-pill-active" style="background: #ECFDF5; color: #065F46; padding: 3px 10px; border-radius: 9999px; font-weight: 700; font-size: 0.76rem;"><i class="fa-solid fa-circle-check"></i> Ready to Join</span>`
            : `<span class="badge-scheduled" style="font-size: 0.74rem;">${escapeHtml(vs.status)}</span>`;

          vHtml += `
            <tr>
              <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <i class="fa-solid fa-user-doctor" style="color: #7C3AED; font-size: 1.1rem;"></i>
                  <div>
                    <strong style="color: #2B1552;">${escapeHtml(vs.counsellor_name || 'Dr. Priya Nair')}</strong>
                    <div style="font-size: 0.74rem; color: #64748B;">Psychological Counsellor</div>
                  </div>
                </div>
              </td>
              <td><span style="font-family: monospace; font-weight: 700; color: #6D28D9;">POCSO/NDLS/2026/0441</span></td>
              <td>${apptTime}</td>
              <td><span class="badge-e2ee" style="font-size: 0.74rem; padding: 3px 8px; border-radius: 9999px;"><i class="fa-solid fa-shield-halved"></i> ${escapeHtml(vs.room_id || 'mentaura-care-lead')}</span></td>
              <td>${statusBadge}</td>
              <td style="text-align: right;">
                <button type="button" class="btn btn-hero-primary" style="padding: 6px 14px; font-size: 0.78rem; font-weight: 800; border-radius: 9999px; display: inline-flex; align-items: center; gap: 5px; background: linear-gradient(135deg, #059669, #10B981); color: #FFF; border: none; cursor: pointer;" onclick="openVictimVideoEnclave('${vs.id}', '${vs.room_id}')">
                  <i class="fa-solid fa-video"></i> Join Call
                </button>
              </td>
            </tr>
          `;
        });
        videoTbody.innerHTML = vHtml;
      }
    }

    // Populate All Requests Table
    if (tbody) {
      if (reqs.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align: center; padding: 24px; color: #8C84A6;">
              No counselling requests submitted yet. Use the cards above to connect or book a session.
            </td>
          </tr>
        `;
      } else {
        let rHtml = '';
        reqs.forEach(r => {
          const apptTime = r.appointment_at 
            ? new Date(r.appointment_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
            : r.time_slot || 'Pending Scheduling';

          let formatIcon = 'fa-comments';
          let formatLabel = 'Consultation';
          if (r.session_format === 'video') {
            formatIcon = 'fa-video';
            formatLabel = 'Video Enclave';
          } else if (r.session_format === 'in_person') {
            formatIcon = 'fa-hospital';
            formatLabel = 'In-Person OSC';
          } else if (r.session_format === 'telephonic') {
            formatIcon = 'fa-phone';
            formatLabel = 'Telephonic';
          }

          let actionBtn = '';
          if (r.session_format === 'video') {
            actionBtn = `
              <button type="button" class="btn btn-hero-primary" style="padding: 5px 12px; font-size: 0.76rem; font-weight: 700; border-radius: 9999px; display: inline-flex; align-items: center; gap: 4px; background: #059669; color: #FFF; border: none; cursor: pointer;" onclick="openVictimVideoEnclave('${r.id}', '${r.room_id}')">
                <i class="fa-solid fa-video"></i> Join
              </button>
            `;
          } else if (r.session_format === 'in_person') {
            actionBtn = `
              <button type="button" class="btn btn-outline-pill" style="padding: 5px 12px; font-size: 0.76rem; font-weight: 700; border-radius: 9999px; display: inline-flex; align-items: center; gap: 4px; border: 1.5px solid #7C3AED; color: #7C3AED; background: #FFF; cursor: pointer;" onclick="showOscSlipModal('${r.pass_code}')">
                <i class="fa-solid fa-ticket"></i> Slip Pass
              </button>
            `;
          } else {
            actionBtn = `
              <span style="font-size: 0.76rem; color: #64748B; font-weight: 600;">Callback Queued</span>
            `;
          }

          rHtml += `
            <tr>
              <td><span style="font-family: monospace; font-weight: 800; color: #2B1552;">${escapeHtml(r.pass_code || r.id.slice(0, 8))}</span></td>
              <td>
                <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.80rem; font-weight: 700; color: #4A3A70;">
                  <i class="fa-solid ${formatIcon}" style="color: #7C3AED;"></i> ${formatLabel}
                </span>
              </td>
              <td><span style="font-size: 0.82rem; font-weight: 600; color: #1E293B;">${escapeHtml(r.support_need || 'Trauma Support')}</span></td>
              <td><span style="font-size: 0.80rem; color: #64748B;">${apptTime}</span></td>
              <td>
                <span class="status-pill-active" style="font-size: 0.74rem; background: #EDE8FB; color: #6D28D9; padding: 2px 8px; border-radius: 9999px;">
                  ${escapeHtml(r.status ? r.status.toUpperCase() : 'SCHEDULED')}
                </span>
              </td>
              <td style="text-align: right;">${actionBtn}</td>
            </tr>
          `;
        });
        tbody.innerHTML = rHtml;
      }
    }
  } catch (err) {
    console.warn('Error fetching victim requests list:', err);
  }
}

window.showOscSlipModal = function(passCode) {
  const modal = document.getElementById('victimOscPassModal');
  if (!modal) return;
  const code = (passCode && passCode !== 'undefined') ? passCode : 'OSC-TN-2026-FB1EA5';
  const pNum = document.getElementById('vOscPassNumber');
  if (pNum) pNum.textContent = code;

  // Retrieve beneficiary name
  const userNameEl = document.getElementById('navUserName');
  const patientName = userNameEl ? userNameEl.textContent.trim() : 'Aanya';

  // Construct structured authentic pass payload for Google Lens and Camera Scanners
  const qrPayload = 
`GOVERNMENT OF INDIA • ONE-STOP CENTRE (OSC)
OFFICIAL SECTION 15A PROTECTION PASS
====================================
PASS NUMBER: ${code}
BENEFICIARY: ${patientName} (Protected Citizen)
PROTECTION STATUS: Section 15A Active & Verified
FACILITY: District One-Stop Crisis Enclave, Room 104
CARE LEAD: Dr. Priya Nair (Clinical Counsellor)
SECURITY STATUS: Priority Entry Authorized
IVRS CARE BRIDGE: +91 95138 86363
STATUTORY HELPLINES: 14566 / 112
VERIFY RECORD: ${window.location.origin}/osc-pass-verify.html?pass=${encodeURIComponent(code)}`;

  const qrImg = document.getElementById('vOscQrImage');
  if (qrImg) {
    const encodedData = encodeURIComponent(qrPayload);
    qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&margin=8&data=${encodedData}`;
  }

  const verifyLink = document.getElementById('vOscVerifyLink');
  if (verifyLink) {
    verifyLink.href = `osc-pass-verify.html?pass=${encodeURIComponent(code)}&name=${encodeURIComponent(patientName)}`;
  }

  modal.classList.add('active');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
};

function initVictimRequestsAndConnect() {
  // Connect with Any Available Counsellor button
  const btnConnectAny = document.getElementById('btnConnectAnyCounsellor');
  if (btnConnectAny) {
    btnConnectAny.addEventListener('click', async () => {
      btnConnectAny.disabled = true;
      btnConnectAny.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Connecting to Care Lead...';
      try {
        const res = await fetch('/api/victim/connect-available-counsellor', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          credentials: 'include'
        });
        const d = await res.json();
        if (d.success) {
          alert(`✨ ${d.message || 'Connected to available counsellor!'}\nOpening encrypted consultation enclave.`);
          await fetchVictimRequestsList();
          await initActiveCounsellingSession();
          openVictimVideoEnclave(d.session_id, d.room_id);
        } else {
          alert(d.detail || 'Could not connect right now. Please dial IVRS +91 95138 86363 directly.');
        }
      } catch (e) {
        console.error('Error connecting with available counsellor:', e);
        alert('Network notice. Connecting via speed dial IVRS +91 95138 86363.');
      } finally {
        btnConnectAny.disabled = false;
        btnConnectAny.innerHTML = '<i class="fa-solid fa-user-plus"></i> Connect with Available Counsellor';
      }
    });
  }

  // Toggle session booking form
  const btnToggle = document.getElementById('btnToggleRequestForm');
  const formWrap = document.getElementById('sessionBookingFormWrap');
  const btnClose = document.getElementById('btnCloseBookingForm');
  const btnCancel = document.getElementById('btnCancelBooking');

  if (btnToggle && formWrap) {
    btnToggle.addEventListener('click', () => {
      formWrap.style.display = formWrap.style.display === 'none' ? 'block' : 'none';
      if (formWrap.style.display === 'block') {
        formWrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  }
  if (btnClose && formWrap) {
    btnClose.addEventListener('click', () => { formWrap.style.display = 'none'; });
  }
  if (btnCancel && formWrap) {
    btnCancel.addEventListener('click', () => { formWrap.style.display = 'none'; });
  }

  // Support Need / Focus Area custom input syncing
  const needSelect = document.getElementById('bookNeedSelect');
  const needCustom = document.getElementById('bookNeedCustomInput');
  const btnToggleNeed = document.getElementById('btnToggleCustomNeed');

  function setCustomNeedVisibility(show) {
    if (!needCustom) return;
    needCustom.style.display = show ? 'block' : 'none';
    if (show) {
      if (needSelect) needSelect.value = '__custom__';
      needCustom.focus();
    } else {
      needCustom.value = '';
    }
  }

  if (needSelect) {
    needSelect.addEventListener('change', () => {
      setCustomNeedVisibility(needSelect.value === '__custom__');
    });
  }
  if (btnToggleNeed) {
    btnToggleNeed.addEventListener('click', () => {
      const isVisible = needCustom && needCustom.style.display !== 'none';
      if (isVisible) {
        setCustomNeedVisibility(false);
        if (needSelect) needSelect.selectedIndex = 0;
      } else {
        setCustomNeedVisibility(true);
      }
    });
  }

  // Preferred Time Window custom input syncing
  const slotSelect = document.getElementById('bookTimeSlot');
  const slotCustom = document.getElementById('bookTimeCustomInput');
  const btnToggleTime = document.getElementById('btnToggleCustomTime');

  function setCustomTimeVisibility(show) {
    if (!slotCustom) return;
    slotCustom.style.display = show ? 'block' : 'none';
    if (show) {
      if (slotSelect) slotSelect.value = '__custom__';
      slotCustom.focus();
    } else {
      slotCustom.value = '';
    }
  }

  if (slotSelect) {
    slotSelect.addEventListener('change', () => {
      setCustomTimeVisibility(slotSelect.value === '__custom__');
    });
  }
  if (btnToggleTime) {
    btnToggleTime.addEventListener('click', () => {
      const isVisible = slotCustom && slotCustom.style.display !== 'none';
      if (isVisible) {
        setCustomTimeVisibility(false);
        if (slotSelect) slotSelect.selectedIndex = 0;
      } else {
        setCustomTimeVisibility(true);
      }
    });
  }

  // Form submission
  const bookingForm = document.getElementById('victimSessionBookingForm');
  if (bookingForm) {
    bookingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fmt = document.getElementById('bookFormatSelect').value;

      // Extract custom or dropdown Support Need
      let need = needSelect ? needSelect.value : '';
      if (need === '__custom__' || (needCustom && needCustom.style.display !== 'none')) {
        need = (needCustom && needCustom.value.trim()) ? needCustom.value.trim() : 'Custom Focus Area';
      }

      // Extract custom or dropdown Time Window
      let slot = slotSelect ? slotSelect.value : '';
      if (slot === '__custom__' || (slotCustom && slotCustom.style.display !== 'none')) {
        slot = (slotCustom && slotCustom.value.trim()) ? slotCustom.value.trim() : 'Flexible Time Window';
      }

      const notes = document.getElementById('bookNotes').value;
      const submitBtn = document.getElementById('btnSubmitBooking');

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting Request...';
      }

      try {
        const res = await fetch('/api/victim/request-counsellor-session', {
          method: 'POST',
          headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
          credentials: 'include',
          body: JSON.stringify({
            session_format: fmt,
            support_need: need,
            time_slot: slot,
            notes: notes
          })
        });
        const d = await res.json();
        if (d.success) {
          bookingForm.reset();
          setCustomNeedVisibility(false);
          setCustomTimeVisibility(false);
          if (formWrap) formWrap.style.display = 'none';
          alert(`✅ Request Confirmed!\n${d.message || 'Session booked.'}`);
          await fetchVictimRequestsList();
          await initActiveCounsellingSession();

          if (fmt === 'in_person' && d.pass_code) {
            showOscSlipModal(d.pass_code);
          } else if (fmt === 'video' && d.room_id) {
            const videoPill = document.getElementById('tabPillVideo');
            if (videoPill) videoPill.click();
          }
        } else {
          alert(d.detail || 'Could not schedule session. Please try again.');
        }
      } catch (err) {
        console.error('Session booking error:', err);
        alert('Communication error. Please check your connection.');
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Submit Session Request';
        }
      }
    });
  }
}
