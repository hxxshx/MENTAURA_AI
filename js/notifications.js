/**
 * MENTAURA — In-App Notifications & Alerts System
 * Handles notification bell badge, dropdown rendering, unread count polling,
 * and mark-as-read interactions across Counsellor and Admin dashboards.
 */

(function () {
  'use strict';

  let isDropdownOpen = false;
  let pollInterval = null;

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getAuthHeaders(extraHeaders = {}) {
    const token = localStorage.getItem('mentaura_token') ||
                  sessionStorage.getItem('mentaura_token') ||
                  sessionStorage.getItem('access_token') ||
                  localStorage.getItem('access_token') || '';
    const headers = {
      'Accept': 'application/json',
      ...extraHeaders
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  function formatTimeAgo(isoString) {
    if (!isoString) return 'Just now';
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffSec = Math.floor((now - date) / 1000);

      if (diffSec < 60) return 'Just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHrs = Math.floor(diffMin / 60);
      if (diffHrs < 24) return `${diffHrs}h ago`;
      const diffDays = Math.floor(diffHrs / 24);
      return `${diffDays}d ago`;
    } catch (e) {
      return 'Recent';
    }
  }

  function getNotificationIcon(type) {
    switch (type) {
      case 'high_risk_pulse':
        return '<i class="fa-solid fa-triangle-exclamation" style="color: #DC2626;" aria-hidden="true"></i>';
      case 'pulse_submitted':
        return '<i class="fa-solid fa-heart-pulse" style="color: #7E57C2;" aria-hidden="true"></i>';
      case 'case_escalated':
        return '<i class="fa-solid fa-arrow-trend-up" style="color: #D97706;" aria-hidden="true"></i>';
      case 'approval_request':
        return '<i class="fa-solid fa-clipboard-check" style="color: #7E57C2;" aria-hidden="true"></i>';
      case 'counsellor_message':
        return '<i class="fa-solid fa-comments" style="color: #2563EB;" aria-hidden="true"></i>';
      case 'threat_report':
      case 'intimidation':
        return '<i class="fa-solid fa-shield-halved" style="color: #DC2626;" aria-hidden="true"></i>';
      default:
        return '<i class="fa-solid fa-bell" style="color: #7E57C2;" aria-hidden="true"></i>';
    }
  }

  async function fetchUnreadCount() {
    try {
      const resp = await fetch('/api/notifications/unread-count', {
        headers: getAuthHeaders(),
        credentials: 'include'
      });
      if (!resp.ok) return;
      const data = await resp.json();
      updateBadge(data.unread_count || 0);
    } catch (err) {
      console.debug('Failed to fetch notification unread count:', err);
    }
  }

  function updateBadge(count) {
    const badge = document.getElementById('notificationBadge');
    const headerCount = document.getElementById('notificationHeaderCount');
    
    if (badge) {
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'inline-flex';
        badge.setAttribute('aria-label', `${count} unread notifications`);
      } else {
        badge.style.display = 'none';
        badge.setAttribute('aria-label', '0 unread notifications');
      }
    }

    if (headerCount) {
      headerCount.textContent = count > 0 ? `${count} new` : '0 new';
    }
  }

  async function fetchNotifications() {
    const listEl = document.getElementById('notificationList');
    if (!listEl) return;

    listEl.innerHTML = `
      <div class="notification-loading-state">
        <i class="fa-solid fa-circle-notch fa-spin" style="color: #7E57C2; font-size: 1.25rem;"></i>
        <p>Loading alerts...</p>
      </div>
    `;

    try {
      const resp = await fetch('/api/notifications?limit=100', {
        headers: getAuthHeaders(),
        credentials: 'include'
      });
      if (!resp.ok) {
        listEl.innerHTML = `
          <div class="notification-empty-state">
            <i class="fa-solid fa-circle-exclamation" style="color: #DC2626;" aria-hidden="true"></i>
            <p>Unable to load notifications</p>
          </div>
        `;
        return;
      }

      const data = await resp.json();
      updateBadge(data.unread_count || 0);

      const notifs = data.notifications || [];
      if (notifs.length === 0) {
        listEl.innerHTML = `
          <div class="notification-empty-state">
            <i class="fa-regular fa-bell-slash" style="color: #94A3B8; font-size: 1.5rem;" aria-hidden="true"></i>
            <p style="margin-top: 0.5rem; font-weight: 500; color: #64748B;">No recent notifications</p>
            <span style="font-size: 0.78rem; color: #94A3B8;">High-risk pulse and escalation alerts will appear here.</span>
          </div>
        `;
        return;
      }

      let html = '';
      notifs.forEach(notif => {
        const isUnread = !notif.is_read;
        const icon = getNotificationIcon(notif.type);
        const timeAgo = formatTimeAgo(notif.created_at);
        const meta = notif.metadata || {};
        const entityId = meta.victim_id || meta.pulse_id || meta.case_id || notif.entity_id || '';

        html += `
          <div class="notification-item ${isUnread ? 'unread' : 'read'}" data-id="${escapeHtml(notif.id)}" data-type="${escapeHtml(notif.type)}" data-entity-id="${escapeHtml(entityId)}" role="button" tabindex="0" title="Click to view details">
            <div class="notif-item-left">
              <div class="notif-icon-circle ${escapeHtml(notif.type)}">
                ${icon}
              </div>
            </div>
            <div class="notif-item-body">
              <div class="notif-item-header">
                <h4 class="notif-item-title">${escapeHtml(notif.title)}</h4>
                <span class="notif-item-time">${timeAgo}</span>
              </div>
              <p class="notif-item-message">${escapeHtml(notif.message)}</p>
            </div>
            ${isUnread ? '<span class="notif-unread-dot" title="Unread"></span>' : ''}
          </div>
        `;
      });

      listEl.innerHTML = html;

      // Attach click listeners to notification items
      listEl.querySelectorAll('.notification-item').forEach(item => {
        item.addEventListener('click', async () => {
          const notifId = item.dataset.id;
          const notifType = item.dataset.type;
          const entityId = item.dataset.entityId;

          if (item.classList.contains('unread')) {
            await markSingleAsRead(notifId, item);
          }

          // Route to matching tab / thread
          if (notifType === 'counsellor_message' && window.openCounsellorConversation) {
            closeDropdown();
            window.openCounsellorConversation(entityId);
          } else if (notifType === 'high_risk_pulse' || notifType === 'pulse_submitted') {
            closeDropdown();
            const triageTab = document.querySelector('.workspace-tab-btn[data-tab="triage"]');
            if (triageTab) triageTab.click();
          } else if (notifType === 'case_escalated' || notifType === 'case_milestone') {
            closeDropdown();
            const milestoneTab = document.querySelector('.workspace-tab-btn[data-tab="milestones"]');
            if (milestoneTab) milestoneTab.click();
          } else if (notifType === 'approval_request') {
            closeDropdown();
            const reqTab = document.querySelector('.workspace-tab-btn[data-tab="requests"]');
            if (reqTab) reqTab.click();
          } else if (notifType === 'threat_report' || notifType === 'intimidation') {
            closeDropdown();
            const intervTab = document.querySelector('.workspace-tab-btn[data-tab="interventions"]');
            if (intervTab) intervTab.click();
          }
        });

        item.addEventListener('keydown', async (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            item.click();
          }
        });
      });

    } catch (err) {
      console.error('Failed to load notifications:', err);
      listEl.innerHTML = `
        <div class="notification-empty-state">
          <i class="fa-solid fa-circle-exclamation" style="color: #DC2626;" aria-hidden="true"></i>
          <p>Error loading notifications</p>
        </div>
      `;
    }
  }

  async function markSingleAsRead(notifId, itemElement) {
    try {
      const resp = await fetch('/api/notifications/mark-read', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ notification_ids: [notifId] }),
        credentials: 'include'
      });
      if (resp.ok) {
        const data = await resp.json();
        updateBadge(data.unread_count || 0);
        if (itemElement) {
          itemElement.classList.remove('unread');
          itemElement.classList.add('read');
          const dot = itemElement.querySelector('.notif-unread-dot');
          if (dot) dot.remove();
        }
      }
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  }

  async function markAllAsRead() {
    const markAllBtn = document.getElementById('markAllReadBtn');
    if (markAllBtn) {
      markAllBtn.disabled = true;
      markAllBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Marking...';
    }

    try {
      const resp = await fetch('/api/notifications/mark-read', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ mark_all: true }),
        credentials: 'include'
      });
      if (resp.ok) {
        const data = await resp.json();
        updateBadge(0);
        const listEl = document.getElementById('notificationList');
        if (listEl) {
          listEl.querySelectorAll('.notification-item.unread').forEach(item => {
            item.classList.remove('unread');
            item.classList.add('read');
            const dot = item.querySelector('.notif-unread-dot');
            if (dot) dot.remove();
          });
        }
      }
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    } finally {
      if (markAllBtn) {
        markAllBtn.disabled = false;
        markAllBtn.innerHTML = '<i class="fa-solid fa-check-double" aria-hidden="true"></i> Mark all as read';
      }
    }
  }

  function toggleDropdown() {
    const dropdown = document.getElementById('notificationDropdown');
    const bellBtn = document.getElementById('notificationBellBtn');
    if (!dropdown || !bellBtn) return;

    isDropdownOpen = !isDropdownOpen;
    if (isDropdownOpen) {
      dropdown.style.display = 'flex';
      dropdown.classList.add('show');
      dropdown.classList.add('active');
      bellBtn.setAttribute('aria-expanded', 'true');
      fetchNotifications();
    } else {
      dropdown.style.display = 'none';
      dropdown.classList.remove('show');
      dropdown.classList.remove('active');
      bellBtn.setAttribute('aria-expanded', 'false');
    }
  }

  function closeDropdown() {
    const dropdown = document.getElementById('notificationDropdown');
    const bellBtn = document.getElementById('notificationBellBtn');
    if (dropdown && isDropdownOpen) {
      dropdown.style.display = 'none';
      dropdown.classList.remove('show');
      dropdown.classList.remove('active');
      if (bellBtn) bellBtn.setAttribute('aria-expanded', 'false');
      isDropdownOpen = false;
    }
  }

  function initNotifications() {
    const bellBtn = document.getElementById('notificationBellBtn');
    const markAllBtn = document.getElementById('markAllReadBtn');

    if (bellBtn) {
      bellBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleDropdown();
      });
    }

    if (markAllBtn) {
      markAllBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        markAllAsRead();
      });
    }

    // Close on outside click
    document.addEventListener('click', (e) => {
      const wrapper = document.querySelector('.nav-notification-wrapper');
      if (wrapper && !wrapper.contains(e.target)) {
        closeDropdown();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isDropdownOpen) {
        closeDropdown();
        if (bellBtn) bellBtn.focus();
      }
    });

    // Initial fetch of unread count
    fetchUnreadCount();

    // Poll every 30 seconds
    if (!pollInterval) {
      pollInterval = setInterval(fetchUnreadCount, 30000);
    }
  }

  // Auto initialize on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNotifications);
  } else {
    initNotifications();
  }

  // Export to window for debugging or manual triggers
  window.MentauraNotifications = {
    fetchUnreadCount,
    fetchNotifications,
    markAllAsRead,
    markSingleAsRead,
    toggleDropdown,
    closeDropdown
  };
})();
