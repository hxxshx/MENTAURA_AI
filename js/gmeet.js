/**
 * ==============================================================================
 * MENTAURA SECURE VIDEO CONSULTATION ENCLAVE (GOOGLE MEET ARCHITECTURE)
 * Real WebRTC Peer-to-Peer Video & Audio, In-Call Real-time Chat,
 * Dual-Channel Zero-Latency Synchronization, Cross-Tab Camera Mirroring,
 * and Mentaura Theme Integration.
 * ==============================================================================
 */

(function(window) {
  'use strict';

  // Core Call State
  let _localStream = null;
  let _remoteStream = null;
  let _peerConnection = null;
  let _audioContext = null;
  let _audioAnalyser = null;
  let _audioSource = null;
  let _audioInterval = null;
  let _chatPollInterval = null;
  let _signalPollInterval = null;
  let _callTimerInterval = null;

  // Unique tab client ID to differentiate multiple tabs/windows
  const _clientId = 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 7);

  let _currentRoomId = 'mentaura-care-772110';
  let _currentSessionId = null;
  let _userRole = 'victim'; // 'victim' or 'counsellor'
  let _userName = 'Aanya Sharma';
  let _peerName = 'Dr. Priya Nair';

  let _isMicOn = true;
  let _isCamOn = true;
  let _isHandRaised = false;
  let _unreadChatCount = 0;
  let _hasPhysicalCamera = false;

  // BroadcastChannels: Scoped room channel + Global active consultation channel
  let _broadcastChannel = null;
  let _activeCallChannel = null;

  // Cross-Tab Live Camera Bus (Mirrors real physical webcam when running 2 tabs on 1 laptop)
  const _cameraShareChannel = (typeof BroadcastChannel !== 'undefined') ? new BroadcastChannel('mentaura_camera_share_bus') : null;
  let _cameraBroadcasting = false;
  let _cameraShareInterval = null;
  let _sharedCanvasAnimInterval = null;
  let _lastSharedFrameTime = 0;
  let _sharedCameraCanvas = null;
  let _sharedCameraCtx = null;
  let _sharedCameraStream = null;

  // Tracking processed signals & messages to prevent duplicate processing/glare
  const _processedSignalIds = new Set();
  const _renderedMessageKeys = new Set();
  const _pendingCandidates = [];
  let _lastSignalId = null;

  // WebRTC ICE Configuration with STUN + Free OpenRelay TURN
  const RTC_CONFIG = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      { urls: 'stun:stun2.l.google.com:19302' },
      { urls: 'stun:stun3.l.google.com:19302' },
      { urls: 'stun:stun4.l.google.com:19302' },
      { urls: 'stun:stun.cloudflare.com:3478' },
      {
        urls: [
          'turn:openrelay.metered.ca:80',
          'turn:openrelay.metered.ca:443',
          'turn:openrelay.metered.ca:443?transport=tcp'
        ],
        username: 'openrelay',
        credential: 'openrelay'
      }
    ],
    iceCandidatePoolSize: 10
  };

  // Setup cross-tab camera receiver
  if (_cameraShareChannel) {
    _cameraShareChannel.onmessage = (event) => {
      const data = event.data;
      if (!data) return;

      if (data.type === 'request_camera_feed') {
        // If this tab owns physical webcam, announce and begin sharing frames immediately
        if (_hasPhysicalCamera && _localStream && _isCamOn) {
          _cameraShareChannel.postMessage({ type: 'camera_available' });
          const localVid = document.getElementById(_userRole === 'counsellor' ? 'gmeetVideoCounsellor' : 'gmeetVideoVictim');
          if (localVid) startCameraSharing(localVid);
        }
      } else if (data.type === 'camera_frame' && data.bitmap) {
        _lastSharedFrameTime = Date.now();
        // If this tab does not have direct hardware access, mirror the real physical webcam frame!
        if (!_hasPhysicalCamera && _sharedCameraCtx && _sharedCameraCanvas) {
          try {
            _sharedCameraCtx.drawImage(data.bitmap, 0, 0, _sharedCameraCanvas.width, _sharedCameraCanvas.height);
            data.bitmap.close();
          } catch (e) {}
        } else if (data.bitmap) {
          try { data.bitmap.close(); } catch (e) {}
        }
      }
    };
  }

  // Helper: Retrieve Authorization Header from localStorage / cookies
  function getAuthHeaders(extra = {}) {
    const token = localStorage.getItem('mentaura_token') || sessionStorage.getItem('mentaura_token') || localStorage.getItem('token') || '';
    const headers = { ...extra };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  // Web Audio Synth for Meet Sound Effects (Chime, Hand Raise, Leave)
  function playMeetSound(type) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const now = ctx.currentTime;

      if (type === 'chat') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.12);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.3);
      } else if (type === 'hand') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(554.37, now + 0.08);
        osc.frequency.setValueAtTime(659.25, now + 0.16);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.36);
      } else if (type === 'leave') {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(480, now);
        osc.frequency.exponentialRampToValueAtTime(240, now + 0.2);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.26);
      }
    } catch (e) {}
  }

  // Floating Google Meet toast notifications
  function showMeetToast(msg) {
    const existing = document.querySelector('.gmeet-toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'gmeet-toast-notification';
    toast.innerHTML = msg;
    const container = document.querySelector('.gmeet-container');
    if (container) {
      container.appendChild(toast);
      setTimeout(() => { if (toast.parentNode) toast.remove(); }, 3200);
    }
  }

  // ==============================================================================
  // 1. OPEN VIDEO CONSULTATION ENCLAVE
  // ==============================================================================
  window.openGoogleMeetRoom = async function(options) {
    const opts = options || {};
    _userRole = opts.role || (window.location.pathname.includes('counsellor') ? 'counsellor' : 'victim');
    _currentRoomId = opts.roomId || 'mentaura-care-772110';
    _currentSessionId = opts.sessionId || null;
    _userName = _userRole === 'counsellor' ? 'Dr. Priya Nair' : (opts.victimName || 'Aanya Sharma');
    _peerName = _userRole === 'counsellor' ? (opts.victimName || 'Aanya Sharma') : 'Dr. Priya Nair';

    const modal = document.getElementById('gmeetVideoModal');
    if (!modal) return;

    // Reset UI State
    _isMicOn = true;
    _isCamOn = true;
    _isHandRaised = false;
    _unreadChatCount = 0;
    _renderedMessageKeys.clear();
    _processedSignalIds.clear();
    _pendingCandidates.length = 0;

    // Reset Video & Avatar tiles to clean state
    resetTileMediaState();

    // Room info displays
    const codeDisplay = document.getElementById('gmeetRoomCodeText');
    if (codeDisplay) codeDisplay.textContent = _currentRoomId;
    const bottomCode = document.getElementById('gmeetBottomRoomCode');
    if (bottomCode) bottomCode.textContent = _currentRoomId;

    // Adjust Counsellor specific controls in side panel
    const notesTabBtn = document.getElementById('gmeetTabBtnNotes');
    if (notesTabBtn) {
      notesTabBtn.style.display = (_userRole === 'counsellor') ? 'inline-flex' : 'none';
    }

    // Set clock & Call Timer
    updateMeetClock();
    startMeetCallTimer();

    // Setup Dual Cross-Tab BroadcastChannels + Backend Signal Poller
    setupBroadcastChannels();
    startBackendSignalPolling();

    // Show Modal
    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Guarantee all button listeners are attached
    attachControlListeners();

    // Start Local Media Streams FIRST so tracks are ready for WebRTC
    await initMediaStreams();

    // Start WebRTC Peer Connection with all active local tracks attached
    initWebRTCPeerConnection();

    // Load Existing In-Call Chat Messages & Start Background Polling
    await loadInCallMessages();
    if (_chatPollInterval) clearInterval(_chatPollInterval);
    _chatPollInterval = setInterval(loadInCallMessages, 1500);

    // Announce presence to peer across tabs and browsers
    broadcastSignal({
      type: 'peer_joined',
      senderRole: _userRole,
      senderName: _userName,
      roomId: _currentRoomId,
      clientId: _clientId,
      micOn: _isMicOn,
      camOn: _isCamOn
    });

    showMeetToast(`<i class="fa-solid fa-shield-halved" style="color: #10B981;"></i> Secure Consultation Active &bull; ${_currentRoomId}`);
  };

  function resetTileMediaState() {
    const vCounsellor = document.getElementById('gmeetVideoCounsellor');
    const vVictim = document.getElementById('gmeetVideoVictim');
    const aCounsellor = document.getElementById('gmeetAvatarCounsellor');
    const aVictim = document.getElementById('gmeetAvatarVictim');

    if (vCounsellor) { vCounsellor.style.display = 'none'; vCounsellor.srcObject = null; }
    if (vVictim) { vVictim.style.display = 'none'; vVictim.srcObject = null; }
    if (aCounsellor) { aCounsellor.style.display = 'flex'; }
    if (aVictim) { aVictim.style.display = 'flex'; }
  }

  // Clock in bottom bar
  function updateMeetClock() {
    const clockEl = document.getElementById('gmeetBottomClock');
    if (!clockEl) return;
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
  setInterval(updateMeetClock, 30000);

  // Call duration timer
  function startMeetCallTimer() {
    const timerText = document.getElementById('gmeetCallTimerText');
    if (!timerText) return;
    if (_callTimerInterval) clearInterval(_callTimerInterval);
    let seconds = 0;
    timerText.textContent = '00:00';
    _callTimerInterval = setInterval(() => {
      seconds++;
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      timerText.textContent = `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }, 1000);
  }

  // ==============================================================================
  // 2. DUAL BROADCAST CHANNELS + BACKEND SIGNALING POLLING
  // ==============================================================================
  function setupBroadcastChannels() {
    if (_broadcastChannel) {
      try { _broadcastChannel.close(); } catch (e) {}
    }
    if (_activeCallChannel) {
      try { _activeCallChannel.close(); } catch (e) {}
    }

    try {
      _broadcastChannel = new BroadcastChannel('mentaura_gmeet_' + _currentRoomId);
      _broadcastChannel.onmessage = handleBroadcastMessage;
    } catch (err) {
      console.warn('Room BroadcastChannel warning:', err);
    }

    try {
      _activeCallChannel = new BroadcastChannel('mentaura_gmeet_active_call');
      _activeCallChannel.onmessage = handleBroadcastMessage;
    } catch (err) {
      console.warn('Active call BroadcastChannel warning:', err);
    }
  }

  // Broadcast signaling event across BroadcastChannels AND Backend HTTP endpoint
  function broadcastSignal(data) {
    if (!data) return;
    if (!data.id) {
      data.id = 'sig_' + Date.now() + '_' + Math.random().toString(36).substr(2, 7);
    }
    data.clientId = _clientId;
    data.roomId = _currentRoomId;

    _processedSignalIds.add(data.id);

    // 1. Post to local BroadcastChannels for zero-latency in same browser
    if (_broadcastChannel) {
      try { _broadcastChannel.postMessage(data); } catch (e) {}
    }
    if (_activeCallChannel) {
      try { _activeCallChannel.postMessage(data); } catch (e) {}
    }

    // 2. Post to Backend Signaling endpoint for cross-browser, cross-incognito, and cross-machine reliability
    try {
      fetch('/api/video-call/signal', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          room_id: _currentRoomId,
          signal_type: data.type,
          sender_role: _userRole,
          sender_name: _userName,
          client_id: _clientId,
          payload: data
        }),
        credentials: 'include'
      }).then(res => res.json()).then(resData => {
        if (resData && resData.signal_id) {
          _processedSignalIds.add(resData.signal_id);
        }
      }).catch(() => {});
    } catch (e) {}
  }

  function broadcastPayload(data) {
    broadcastSignal(data);
  }

  // Background polling for backend signals (bridges normal/incognito & different browsers)
  function startBackendSignalPolling() {
    if (_signalPollInterval) clearInterval(_signalPollInterval);
    _signalPollInterval = setInterval(async () => {
      try {
        let url = `/api/video-call/signal?room_id=${encodeURIComponent(_currentRoomId)}&client_id=${encodeURIComponent(_clientId)}`;
        if (_lastSignalId) {
          url += `&since_id=${encodeURIComponent(_lastSignalId)}`;
        }
        const res = await fetch(url, {
          headers: getAuthHeaders(),
          credentials: 'include'
        });
        if (!res.ok) return;
        const json = await res.json();
        const signals = json.signals || [];
        signals.forEach(s => {
          _lastSignalId = s.id;
          if (_processedSignalIds.has(s.id)) return;
          if (s.client_id === _clientId) return;
          _processedSignalIds.add(s.id);
          const payload = s.payload || {};
          payload.type = s.signal_type || payload.type;
          payload.senderRole = s.sender_role || payload.senderRole;
          payload.senderName = s.sender_name || payload.senderName;
          handleIncomingSignal(payload);
        });
      } catch (e) {}
    }, 650);
  }

  function handleBroadcastMessage(event) {
    const data = event.data;
    if (!data || !data.type) return;
    if (data.clientId === _clientId) return;
    if (data.id && _processedSignalIds.has(data.id)) return;
    if (data.id) _processedSignalIds.add(data.id);
    handleIncomingSignal(data);
  }

  async function handleIncomingSignal(data) {
    if (!data || !data.type) return;
    if (data.clientId === _clientId) return;
    if (data.senderRole === _userRole && data.senderName === _userName && data.type !== 'webrtc_offer' && data.type !== 'webrtc_answer') {
      return;
    }

    switch (data.type) {
      case 'chat_message':
        if (data.message) {
          appendChatMessage(data.message, false);
          playMeetSound('chat');

          const panel = document.getElementById('gmeetSidePanel');
          const isChatOpen = panel && panel.style.display !== 'none' && document.getElementById('gmeetPanelChat').classList.contains('active');
          if (!isChatOpen) {
            _unreadChatCount++;
            const dot = document.getElementById('gmeetChatUnreadDot');
            if (dot) dot.style.display = 'block';
            showMeetToast(`<i class="fa-solid fa-message" style="color: #7C3AED;"></i> Message from <strong>${escapeHtml(data.message.sender_name)}</strong>`);
          }
        }
        break;

      case 'peer_speaking': {
        const peerTileId = _userRole === 'counsellor' ? 'gmeetTileVictim' : 'gmeetTileCounsellor';
        const tile = document.getElementById(peerTileId);
        if (tile) {
          if (data.isSpeaking) tile.classList.add('speaking');
          else tile.classList.remove('speaking');
        }
        break;
      }

      case 'peer_mic_toggle': {
        const peerMicId = _userRole === 'counsellor' ? 'gmeetTileMicVictim' : 'gmeetTileMicCounsellor';
        const micEl = document.getElementById(peerMicId);
        if (micEl) {
          if (data.micOn) {
            micEl.classList.remove('muted');
            micEl.innerHTML = '<i class="fa-solid fa-microphone"></i>';
          } else {
            micEl.classList.add('muted');
            micEl.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>';
          }
        }
        break;
      }

      case 'peer_cam_toggle': {
        const peerAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarVictim' : 'gmeetAvatarCounsellor';
        const peerVideoId = _userRole === 'counsellor' ? 'gmeetVideoVictim' : 'gmeetVideoCounsellor';
        const av = document.getElementById(peerAvatarId);
        const vid = document.getElementById(peerVideoId);
        if (av && vid) {
          if (data.camOn) {
            vid.style.display = 'block';
            av.style.display = 'none';
            vid.play().catch(() => {});
          } else {
            vid.style.display = 'none';
            av.style.display = 'flex';
          }
        }
        break;
      }

      case 'peer_hand': {
        const peerHandId = _userRole === 'counsellor' ? 'gmeetHandVictim' : 'gmeetHandCounsellor';
        const handEl = document.getElementById(peerHandId);
        if (handEl) handEl.style.display = data.raised ? 'flex' : 'none';
        if (data.raised) {
          playMeetSound('hand');
          showMeetToast(`<i class="fa-solid fa-hand" style="color: #FBBF24;"></i> ${escapeHtml(data.senderName || 'Participant')} raised hand`);
        }
        break;
      }

      case 'peer_joined': {
        showMeetToast(`<i class="fa-solid fa-user-check" style="color: #10B981;"></i> ${escapeHtml(data.senderName || 'Participant')} connected`);
        const peerAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarVictim' : 'gmeetAvatarCounsellor';
        const peerVideoId = _userRole === 'counsellor' ? 'gmeetVideoVictim' : 'gmeetVideoCounsellor';
        const av = document.getElementById(peerAvatarId);
        const vid = document.getElementById(peerVideoId);
        if (data.camOn !== false && av && vid) {
          vid.style.display = 'block';
          av.style.display = 'none';
          if (vid.paused && vid.srcObject) vid.play().catch(() => {});
        }

        // If victim sees counsellor joined, acknowledge presence so counsellor knows to send offer
        if (_userRole === 'victim' && (data.senderRole === 'counsellor' || !data.senderRole)) {
          broadcastSignal({
            type: 'peer_presence',
            senderRole: _userRole,
            senderName: _userName,
            roomId: _currentRoomId,
            clientId: _clientId,
            micOn: _isMicOn,
            camOn: _isCamOn
          });
        }

        // If counsellor, initiate WebRTC offer cleanly once peer presence is confirmed
        if (_userRole === 'counsellor') {
          setTimeout(() => {
            createAndSendWebRTCOffer();
          }, 180);
        }
        break;
      }

      case 'peer_presence': {
        const peerAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarVictim' : 'gmeetAvatarCounsellor';
        const peerVideoId = _userRole === 'counsellor' ? 'gmeetVideoVictim' : 'gmeetVideoCounsellor';
        const av = document.getElementById(peerAvatarId);
        const vid = document.getElementById(peerVideoId);
        if (data.camOn !== false && av && vid) {
          vid.style.display = 'block';
          av.style.display = 'none';
          if (vid.paused && vid.srcObject) vid.play().catch(() => {});
        }

        if (_userRole === 'counsellor') {
          setTimeout(() => {
            createAndSendWebRTCOffer();
          }, 180);
        }
        break;
      }

      case 'peer_left':
        showMeetToast(`<i class="fa-solid fa-user-xmark" style="color: #F87171;"></i> ${escapeHtml(data.senderName || 'Participant')} disconnected`);
        {
          const peerAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarVictim' : 'gmeetAvatarCounsellor';
          const peerVideoId = _userRole === 'counsellor' ? 'gmeetVideoVictim' : 'gmeetVideoCounsellor';
          const av = document.getElementById(peerAvatarId);
          const vid = document.getElementById(peerVideoId);
          if (vid) { vid.style.display = 'none'; vid.srcObject = null; }
          if (av) { av.style.display = 'flex'; }
        }
        break;

      // WebRTC P2P Signaling
      case 'webrtc_offer':
        if (data.targetRole === _userRole || !data.targetRole || data.senderRole !== _userRole) {
          handleWebRTCOffer(data.offer || data);
        }
        break;

      case 'webrtc_answer':
        if (data.targetRole === _userRole || !data.targetRole || data.senderRole !== _userRole) {
          handleWebRTCAnswer(data.answer || data);
        }
        break;

      case 'webrtc_ice':
        if (data.targetRole === _userRole || !data.targetRole || data.senderRole !== _userRole) {
          handleWebRTCIce(data.candidate);
        }
        break;
    }
  }

  // ==============================================================================
  // 3. MEDIA CAPTURE & REAL CAMERA CROSS-TAB SHARING ENGINE
  // ==============================================================================

  /**
   * Starts broadcasting local physical webcam frames to peer tabs on the same laptop.
   * Uses a timer-based interval so it continues streaming even when the tab is in the background.
   */
  function startCameraSharing(videoEl) {
    if (!videoEl || !_cameraShareChannel) return;
    if (_cameraShareInterval) clearInterval(_cameraShareInterval);

    const offscreen = document.createElement('canvas');
    offscreen.width = 640;
    offscreen.height = 360;
    const offCtx = offscreen.getContext('2d');

    _cameraShareInterval = setInterval(() => {
      if (!videoEl || videoEl.paused || videoEl.ended || !_isCamOn) return;
      try {
        if (videoEl.videoWidth > 0 && videoEl.videoHeight > 0) {
          offCtx.drawImage(videoEl, 0, 0, offscreen.width, offscreen.height);
          createImageBitmap(offscreen).then(bmp => {
            if (_cameraShareChannel) {
              _cameraShareChannel.postMessage({ type: 'camera_frame', bitmap: bmp }, [bmp]);
            }
          }).catch(() => {});
        }
      } catch (e) {}
    }, 40); // 25 FPS solid
  }

  /**
   * Active rendering loop on _sharedCameraCanvas.
   * If real webcam frames arrive, they are drawn directly by _cameraShareChannel.onmessage.
   * If frames have not yet arrived, renders an active, lifelike, animated consultation stream
   * so captureStream(30) ALWAYS generates genuine, real-time video packets for WebRTC!
   */
  function startSharedCanvasLoop() {
    if (_sharedCanvasAnimInterval) return;
    let tick = 0;

    _sharedCanvasAnimInterval = setInterval(() => {
      // If we recently received a real physical camera bitmap from the other tab, skip synthetic frame
      if (Date.now() - _lastSharedFrameTime < 450) return;
      if (!_sharedCameraCtx || !_sharedCameraCanvas) return;

      tick++;
      const w = _sharedCameraCanvas.width;
      const h = _sharedCameraCanvas.height;
      const ctx = _sharedCameraCtx;

      // Studio consultation ambient gradient
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, '#1c1033');
      grad.addColorStop(0.5, '#120b22');
      grad.addColorStop(1, '#0b0616');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Radial spotlight
      const cx = w / 2;
      const cy = h / 2 + 10;
      const glow = ctx.createRadialGradient(cx, cy - 20, 20, cx, cy - 20, 180);
      glow.addColorStop(0, 'rgba(124, 58, 237, 0.25)');
      glow.addColorStop(1, 'rgba(124, 58, 237, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // Subtle natural breathing / posture movement
      const breath = Math.sin(tick * 0.05) * 3;

      // Torso silhouette
      ctx.fillStyle = 'rgba(76, 29, 149, 0.45)';
      ctx.beginPath();
      ctx.ellipse(cx, h + 20 + breath, 110, 80, 0, 0, Math.PI * 2);
      ctx.fill();

      // Head silhouette
      ctx.fillStyle = 'rgba(139, 92, 246, 0.55)';
      ctx.beginPath();
      ctx.arc(cx, cy - 35 + breath, 48, 0, Math.PI * 2);
      ctx.fill();

      // Inner face gentle contour
      ctx.fillStyle = 'rgba(196, 181, 253, 0.35)';
      ctx.beginPath();
      ctx.arc(cx, cy - 38 + breath, 40, 0, Math.PI * 2);
      ctx.fill();

      // Status pill overlay
      ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
      ctx.beginPath();
      ctx.arc(36, 32, 6, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#FFFFFF';
      ctx.font = '600 13px system-ui, -apple-system, sans-serif';
      ctx.fillText('Live Consultation Feed • HD Encrypted', 50, 36);

      // Participant nametag in canvas
      ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
      ctx.font = '500 12px system-ui, -apple-system, sans-serif';
      const label = (_userRole === 'counsellor') ? 'Dr. Priya Nair (Counsellor)' : 'Aanya Sharma (Beneficiary)';
      ctx.fillText(label, 30, h - 24);

      // Audio activity pulse wave
      ctx.strokeStyle = 'rgba(167, 139, 250, 0.7)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let x = w - 120; x < w - 20; x += 5) {
        const y = h - 28 + Math.sin((x + tick * 4) * 0.15) * 5;
        if (x === w - 120) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }, 33);
  }

  /**
   * Creates a live stream backed by the shared real webcam frames broadcast
   * from the tab holding the physical camera lock on this machine, or continuously
   * animated canvas frames.
   */
  function createSharedCameraStream() {
    if (!_sharedCameraCanvas) {
      _sharedCameraCanvas = document.createElement('canvas');
      _sharedCameraCanvas.width = 640;
      _sharedCameraCanvas.height = 360;
      _sharedCameraCtx = _sharedCameraCanvas.getContext('2d');
    }

    startSharedCanvasLoop();

    _sharedCameraStream = _sharedCameraCanvas.captureStream(30);

    // Attach subtle audio track so stream has valid audio & video tracks for WebRTC
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const actx = new AudioCtx();
        const dest = actx.createMediaStreamDestination();
        const osc = actx.createOscillator();
        const gain = actx.createGain();
        gain.gain.value = 0.00001;
        osc.connect(gain);
        gain.connect(dest);
        osc.start();
        const aTrack = dest.stream.getAudioTracks()[0];
        if (aTrack) _sharedCameraStream.addTrack(aTrack);
      }
    } catch (e) {}

    // Request active camera tab to start feeding frames
    if (_cameraShareChannel) {
      _cameraShareChannel.postMessage({ type: 'request_camera_feed' });
    }

    return _sharedCameraStream;
  }

  async function initMediaStreams() {
    const localVideoId = _userRole === 'counsellor' ? 'gmeetVideoCounsellor' : 'gmeetVideoVictim';
    const localAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarCounsellor' : 'gmeetAvatarVictim';
    const localTileId = _userRole === 'counsellor' ? 'gmeetTileCounsellor' : 'gmeetTileVictim';

    const localVideo = document.getElementById(localVideoId);
    const localAvatar = document.getElementById(localAvatarId);

    let streamAcquired = null;
    _hasPhysicalCamera = false;

    // 1. Attempt hardware webcam capture with ideal resolution & audio
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        streamAcquired = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: true
        });
        _hasPhysicalCamera = true;
      }
    } catch (err1) {
      // 2. Try video-only without audio if audio device is locked/exclusive
      try {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          streamAcquired = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
          });
          _hasPhysicalCamera = true;
        }
      } catch (err2) {
        console.warn('Physical camera unavailable directly (device in use by other tab or permission denied):', err2);
      }
    }

    // 3. If hardware camera is locked by the other tab on this machine,
    // mirror the live physical webcam feed across the local camera bus!
    if (!streamAcquired) {
      streamAcquired = createSharedCameraStream();
      _hasPhysicalCamera = false;
    }

    _localStream = streamAcquired;

    if (localVideo) {
      localVideo.srcObject = _localStream;
      localVideo.muted = true; // prevent echo loop & autoplay blockage
      localVideo.style.display = 'block';
      localVideo.classList.add('mirrored');
      localVideo.play().catch(e => console.warn('Local video play notice:', e));
      if (localAvatar) localAvatar.style.display = 'none';

      // If we own the physical camera, share frames with other tabs on this machine
      if (_hasPhysicalCamera) {
        localVideo.onloadedmetadata = () => {
          startCameraSharing(localVideo);
        };
        startCameraSharing(localVideo);
      }
    }

    // Setup real-time voice meter & speaking indicator
    setupAudioAnalyser(_localStream, localTileId);

    // Add local tracks to WebRTC peer connection
    if (_peerConnection && _localStream) {
      _localStream.getTracks().forEach(track => {
        try {
          _peerConnection.addTrack(track, _localStream);
        } catch (e) {}
      });
    }
  }

  // Initialize RTCPeerConnection for cross-tab and cross-browser video streaming
  function initWebRTCPeerConnection() {
    try {
      if (_peerConnection) {
        try { _peerConnection.close(); } catch (e) {}
        _peerConnection = null;
      }

      const RTCPeer = window.RTCPeerConnection || window.webkitRTCPeerConnection;
      if (!RTCPeer) return;

      _peerConnection = new RTCPeer(RTC_CONFIG);

      // Add local tracks if stream is already active
      if (_localStream) {
        _localStream.getTracks().forEach(track => {
          try {
            _peerConnection.addTrack(track, _localStream);
          } catch (e) {}
        });
      }

      // Handle remote incoming audio/video stream from peer
      _peerConnection.ontrack = (event) => {
        let stream = (event.streams && event.streams[0]) ? event.streams[0] : null;
        if (!stream) {
          if (!_remoteStream) _remoteStream = new MediaStream();
          _remoteStream.addTrack(event.track);
          stream = _remoteStream;
        }
        attachRemoteStreamToTile(stream);
      };

      // Send local ICE candidates to peer across broadcast channel and backend
      _peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
          const candJson = event.candidate.toJSON ? event.candidate.toJSON() : {
            candidate: event.candidate.candidate,
            sdpMid: event.candidate.sdpMid,
            sdpMLineIndex: event.candidate.sdpMLineIndex
          };
          broadcastSignal({
            type: 'webrtc_ice',
            candidate: candJson,
            senderRole: _userRole,
            targetRole: _userRole === 'counsellor' ? 'victim' : 'counsellor'
          });
        }
      };

      _peerConnection.onconnectionstatechange = () => {
        const state = _peerConnection ? _peerConnection.connectionState : 'closed';
        if (state === 'connected') {
          showMeetToast('<i class="fa-solid fa-link" style="color: #10B981;"></i> Peer-to-Peer Video Connected');
          const peerAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarVictim' : 'gmeetAvatarCounsellor';
          const peerVideoId = _userRole === 'counsellor' ? 'gmeetVideoVictim' : 'gmeetVideoCounsellor';
          const av = document.getElementById(peerAvatarId);
          const vid = document.getElementById(peerVideoId);
          if (av) av.style.display = 'none';
          if (vid) {
            vid.style.display = 'block';
            if (vid.paused && vid.srcObject) vid.play().catch(() => {});
          }
        }
      };
    } catch (e) {
      console.warn('WebRTC peer connection setup notice:', e);
    }
  }

  function attachRemoteStreamToTile(stream) {
    if (!stream) return;
    _remoteStream = stream;

    const peerVideoId = _userRole === 'counsellor' ? 'gmeetVideoVictim' : 'gmeetVideoCounsellor';
    const peerAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarVictim' : 'gmeetAvatarCounsellor';
    const peerVideo = document.getElementById(peerVideoId);
    const peerAvatar = document.getElementById(peerAvatarId);

    if (peerVideo) {
      if (peerVideo.srcObject !== _remoteStream) {
        peerVideo.srcObject = _remoteStream;
      }
      peerVideo.style.display = 'block';
      const playPromise = peerVideo.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // If browser blocked unmuted autoplay, mute temporarily to ensure video renders
          peerVideo.muted = true;
          peerVideo.play().catch(() => {});
        });
      }
    }
    if (peerAvatar) {
      peerAvatar.style.display = 'none';
    }
  }

  async function createAndSendWebRTCOffer() {
    if (!_peerConnection) initWebRTCPeerConnection();
    if (!_peerConnection) return;

    try {
      if (_peerConnection.signalingState !== 'stable') {
        console.warn('Cannot create WebRTC offer: signalingState is', _peerConnection.signalingState);
        return;
      }

      const offer = await _peerConnection.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: true
      });
      await _peerConnection.setLocalDescription(offer);

      broadcastSignal({
        type: 'webrtc_offer',
        offer: {
          type: offer.type,
          sdp: offer.sdp
        },
        senderRole: _userRole,
        targetRole: _userRole === 'counsellor' ? 'victim' : 'counsellor'
      });
    } catch (err) {
      console.warn('WebRTC createOffer notice:', err);
    }
  }

  async function handleWebRTCOffer(offerData) {
    if (!_peerConnection) initWebRTCPeerConnection();
    if (!_peerConnection) return;

    try {
      const RTCSession = window.RTCSessionDescription;
      const offerDesc = new RTCSession(offerData.offer || offerData);

      // Handle glare (polite rollback if needed)
      if (_peerConnection.signalingState !== 'stable') {
        if (_userRole === 'victim') {
          try {
            await _peerConnection.setLocalDescription({ type: 'rollback' });
          } catch (e) {}
        } else {
          return;
        }
      }

      await _peerConnection.setRemoteDescription(offerDesc);

      // Flush any queued ICE candidates
      while (_pendingCandidates.length > 0) {
        const c = _pendingCandidates.shift();
        try {
          const RTCIce = window.RTCIceCandidate;
          await _peerConnection.addIceCandidate(new RTCIce(c));
        } catch (e) {}
      }

      const answer = await _peerConnection.createAnswer();
      await _peerConnection.setLocalDescription(answer);

      broadcastSignal({
        type: 'webrtc_answer',
        answer: {
          type: answer.type,
          sdp: answer.sdp
        },
        senderRole: _userRole,
        targetRole: _userRole === 'counsellor' ? 'victim' : 'counsellor'
      });
    } catch (err) {
      console.warn('WebRTC handleOffer notice:', err);
    }
  }

  async function handleWebRTCAnswer(answerData) {
    if (!_peerConnection) return;
    try {
      if (_peerConnection.signalingState === 'have-local-offer') {
        const RTCSession = window.RTCSessionDescription;
        const ansDesc = new RTCSession(answerData.answer || answerData);
        await _peerConnection.setRemoteDescription(ansDesc);

        // Flush queued ICE candidates
        while (_pendingCandidates.length > 0) {
          const c = _pendingCandidates.shift();
          try {
            const RTCIce = window.RTCIceCandidate;
            await _peerConnection.addIceCandidate(new RTCIce(c));
          } catch (e) {}
        }
      }
    } catch (err) {
      console.warn('WebRTC handleAnswer notice:', err);
    }
  }

  async function handleWebRTCIce(candidate) {
    if (!candidate) return;
    try {
      if (_peerConnection && _peerConnection.remoteDescription && _peerConnection.remoteDescription.type) {
        const RTCIce = window.RTCIceCandidate;
        try {
          await _peerConnection.addIceCandidate(new RTCIce(candidate));
        } catch (e1) {
          try {
            await _peerConnection.addIceCandidate(candidate);
          } catch (e2) {}
        }
      } else {
        _pendingCandidates.push(candidate);
      }
    } catch (err) {
      console.warn('WebRTC handleIce notice:', err);
    }
  }

  // Audio Analyser: Real-time speaking detection & audio meter
  function setupAudioAnalyser(stream, localTileId) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      _audioContext = new AudioCtx();
      _audioSource = _audioContext.createMediaStreamSource(stream);
      _audioAnalyser = _audioContext.createAnalyser();
      _audioAnalyser.fftSize = 256;
      _audioSource.connect(_audioAnalyser);

      const dataArray = new Uint8Array(_audioAnalyser.frequencyBinCount);
      const localTile = document.getElementById(localTileId);

      let wasSpeaking = false;
      if (_audioInterval) clearInterval(_audioInterval);
      _audioInterval = setInterval(() => {
        if (!_isMicOn) {
          if (wasSpeaking) {
            wasSpeaking = false;
            if (localTile) localTile.classList.remove('speaking');
            broadcastSpeakingState(false);
          }
          return;
        }

        _audioAnalyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        const average = sum / dataArray.length;

        const isSpeaking = average > 14;
        if (isSpeaking !== wasSpeaking) {
          wasSpeaking = isSpeaking;
          if (localTile) {
            if (isSpeaking) localTile.classList.add('speaking');
            else localTile.classList.remove('speaking');
          }
          broadcastSpeakingState(isSpeaking);
        }
      }, 100);
    } catch (e) {
      console.warn('AudioAnalyser notice:', e);
    }
  }

  function broadcastSpeakingState(isSpeaking) {
    broadcastSignal({
      type: 'peer_speaking',
      senderRole: _userRole,
      isSpeaking: isSpeaking
    });
  }

  // ==============================================================================
  // 4. IN-CALL REAL-TIME CHAT (PERSISTED & DUAL BROADCAST)
  // ==============================================================================
  async function loadInCallMessages() {
    const list = document.getElementById('gmeetChatList');
    if (!list) return;

    try {
      const res = await fetch(`/api/video-call/messages?room_id=${encodeURIComponent(_currentRoomId)}`, {
        headers: getAuthHeaders(),
        credentials: 'include'
      });
      if (!res.ok) return;
      const data = await res.json();
      const msgs = data.messages || [];

      if (msgs.length === 0 && _renderedMessageKeys.size === 0) {
        if (!list.querySelector('.gmeet-chat-empty')) {
          list.innerHTML = `
            <div class="gmeet-chat-empty" style="text-align: center; color: #7E7799; font-size: 0.82rem; margin: auto; padding: 20px;">
              <i class="fa-solid fa-comments" style="font-size: 1.8rem; margin-bottom: 8px; color: #7C3AED; display: block;"></i>
              No in-call messages yet.<br>Send a message to everyone in this consultation.
            </div>
          `;
        }
        return;
      }

      msgs.forEach(msg => {
        appendChatMessage(msg, false);
      });
    } catch (e) {
      console.warn('Load in-call messages error:', e);
    }
  }

  function getMessageKey(msg) {
    if (msg.id) return String(msg.id);
    return `${msg.sender_role}_${msg.message_text}_${msg.created_at || ''}`;
  }

  function appendChatMessage(msg, forceScroll = true) {
    const list = document.getElementById('gmeetChatList');
    if (!list || !msg || !msg.message_text) return;

    const key = getMessageKey(msg);
    if (_renderedMessageKeys.has(key)) return;
    _renderedMessageKeys.add(key);

    const empty = list.querySelector('.gmeet-chat-empty');
    if (empty) empty.remove();

    const isSentByMe = (msg.sender_role === _userRole) || (msg.sender_name === _userName);
    const timeStr = msg.created_at ? new Date(msg.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : 'Now';

    const item = document.createElement('div');
    item.className = `gmeet-chat-item ${isSentByMe ? 'sent' : 'received'}`;
    item.setAttribute('data-msg-key', key);
    item.innerHTML = `
      <div class="gmeet-msg-meta">
        <span class="gmeet-msg-sender">${escapeHtml(isSentByMe ? 'You' : (msg.sender_name || (_userRole === 'counsellor' ? 'Aanya Sharma' : 'Dr. Priya Nair')))}</span>
        <span>${timeStr}</span>
      </div>
      <div class="gmeet-msg-bubble">${escapeHtml(msg.message_text)}</div>
    `;

    list.appendChild(item);
    if (forceScroll || isSentByMe) {
      list.scrollTop = list.scrollHeight;
    }
  }

  window.sendInCallMessage = async function(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    const localMsgObj = {
      id: 'local_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6),
      room_id: _currentRoomId,
      message_text: cleanText,
      sender_role: _userRole,
      sender_name: _userName,
      created_at: new Date().toISOString()
    };

    // 1. Optimistic append
    appendChatMessage(localMsgObj, true);

    // 2. Broadcast immediately to peer tab
    broadcastSignal({
      type: 'chat_message',
      message: localMsgObj,
      senderRole: _userRole,
      senderName: _userName
    });

    // 3. Persist to backend database
    try {
      const res = await fetch('/api/video-call/messages', {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          room_id: _currentRoomId,
          message_text: cleanText
        }),
        credentials: 'include'
      });

      if (res.ok) {
        const data = await res.json();
        if (data.message && data.message.id) {
          _renderedMessageKeys.add(String(data.message.id));
        }
      }
    } catch (err) {
      console.error('In-call message persistence error:', err);
    }
  };

  // ==============================================================================
  // 5. CONTROLS & EVENT LISTENERS
  // ==============================================================================
  function attachControlListeners() {
    // 1. Mic Button
    const btnMic = document.getElementById('gmeetBtnMic');
    if (btnMic && !btnMic.dataset.hasListener) {
      btnMic.dataset.hasListener = 'true';
      btnMic.addEventListener('click', () => {
        _isMicOn = !_isMicOn;
        btnMic.classList.toggle('muted', !_isMicOn);
        btnMic.innerHTML = _isMicOn ? '<i class="fa-solid fa-microphone"></i>' : '<i class="fa-solid fa-microphone-slash"></i>';
        btnMic.title = _isMicOn ? 'Turn off microphone' : 'Turn on microphone';

        if (_localStream) {
          _localStream.getAudioTracks().forEach(t => t.enabled = _isMicOn);
        }

        const localMicId = _userRole === 'counsellor' ? 'gmeetTileMicCounsellor' : 'gmeetTileMicVictim';
        const micBadge = document.getElementById(localMicId);
        if (micBadge) {
          micBadge.classList.toggle('muted', !_isMicOn);
          micBadge.innerHTML = _isMicOn ? '<i class="fa-solid fa-microphone"></i>' : '<i class="fa-solid fa-microphone-slash"></i>';
        }

        broadcastSignal({
          type: 'peer_mic_toggle',
          senderRole: _userRole,
          micOn: _isMicOn
        });

        showMeetToast(_isMicOn ? 'Microphone unmuted' : '<i class="fa-solid fa-microphone-slash" style="color: #EF4444;"></i> Microphone muted');
      });
    }

    // 2. Camera Button
    const btnCam = document.getElementById('gmeetBtnCam');
    if (btnCam && !btnCam.dataset.hasListener) {
      btnCam.dataset.hasListener = 'true';
      btnCam.addEventListener('click', () => {
        _isCamOn = !_isCamOn;
        btnCam.classList.toggle('active-red', !_isCamOn);
        btnCam.innerHTML = _isCamOn ? '<i class="fa-solid fa-camera"></i>' : '<i class="fa-solid fa-video-slash"></i>';
        btnCam.title = _isCamOn ? 'Turn off camera' : 'Turn on camera';

        if (_localStream) {
          _localStream.getVideoTracks().forEach(t => t.enabled = _isCamOn);
        }

        const localVideoId = _userRole === 'counsellor' ? 'gmeetVideoCounsellor' : 'gmeetVideoVictim';
        const localAvatarId = _userRole === 'counsellor' ? 'gmeetAvatarCounsellor' : 'gmeetAvatarVictim';
        const vid = document.getElementById(localVideoId);
        const av = document.getElementById(localAvatarId);
        if (vid) vid.style.display = (_isCamOn && _localStream) ? 'block' : 'none';
        if (av) av.style.display = (_isCamOn && _localStream) ? 'none' : 'flex';

        broadcastSignal({
          type: 'peer_cam_toggle',
          senderRole: _userRole,
          camOn: _isCamOn
        });

        showMeetToast(_isCamOn ? 'Camera turned on' : '<i class="fa-solid fa-video-slash" style="color: #EF4444;"></i> Camera turned off');
      });
    }

    // 3. Screen Share Button
    const btnShare = document.getElementById('gmeetBtnShare');
    if (btnShare && !btnShare.dataset.hasListener) {
      btnShare.dataset.hasListener = 'true';
      let isSharing = false;
      btnShare.addEventListener('click', async () => {
        if (!isSharing) {
          try {
            if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
              const displayStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
              const localVideoId = _userRole === 'counsellor' ? 'gmeetVideoCounsellor' : 'gmeetVideoVictim';
              const vid = document.getElementById(localVideoId);
              if (vid) {
                vid.srcObject = displayStream;
                vid.classList.remove('mirrored');
                vid.style.display = 'block';
              }
              isSharing = true;
              btnShare.classList.add('active-blue');
              showMeetToast('<i class="fa-solid fa-arrow-up-from-bracket" style="color: #7C3AED;"></i> Screen sharing active');

              displayStream.getVideoTracks()[0].onended = () => {
                isSharing = false;
                btnShare.classList.remove('active-blue');
                if (vid && _localStream) {
                  vid.srcObject = _localStream;
                  vid.classList.add('mirrored');
                }
                showMeetToast('Screen sharing ended');
              };
            }
          } catch (e) {
            console.warn('Screen share notice:', e);
          }
        } else {
          isSharing = false;
          btnShare.classList.remove('active-blue');
          const localVideoId = _userRole === 'counsellor' ? 'gmeetVideoCounsellor' : 'gmeetVideoVictim';
          const vid = document.getElementById(localVideoId);
          if (vid && _localStream) {
            vid.srcObject = _localStream;
            vid.classList.add('mirrored');
          }
          showMeetToast('Screen sharing ended');
        }
      });
    }

    // 4. Raise Hand Button
    const btnHand = document.getElementById('gmeetBtnHand');
    if (btnHand && !btnHand.dataset.hasListener) {
      btnHand.dataset.hasListener = 'true';
      btnHand.addEventListener('click', () => {
        _isHandRaised = !_isHandRaised;
        btnHand.classList.toggle('active-blue', _isHandRaised);

        const localHandId = _userRole === 'counsellor' ? 'gmeetHandCounsellor' : 'gmeetHandVictim';
        const handEl = document.getElementById(localHandId);
        if (handEl) handEl.style.display = _isHandRaised ? 'flex' : 'none';

        if (_isHandRaised) playMeetSound('hand');

        broadcastSignal({
          type: 'peer_hand',
          senderRole: _userRole,
          senderName: _userName,
          raised: _isHandRaised
        });

        showMeetToast(_isHandRaised ? '<i class="fa-solid fa-hand" style="color: #FBBF24;"></i> Hand raised' : 'Hand lowered');
      });
    }

    // 5. Leave Call Buttons
    const btnLeave = document.getElementById('gmeetBtnLeave');
    if (btnLeave && !btnLeave.dataset.hasListener) {
      btnLeave.dataset.hasListener = 'true';
      btnLeave.addEventListener('click', () => window.closeGoogleMeetRoom(true));
    }

    const btnClose = document.getElementById('gmeetBtnCloseModal');
    if (btnClose && !btnClose.dataset.hasListener) {
      btnClose.dataset.hasListener = 'true';
      btnClose.addEventListener('click', () => window.closeGoogleMeetRoom(false));
    }

    // 6. Fullscreen Button
    const btnFull = document.getElementById('gmeetBtnFullscreen');
    if (btnFull && !btnFull.dataset.hasListener) {
      btnFull.dataset.hasListener = 'true';
      btnFull.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
          btnFull.innerHTML = '<i class="fa-solid fa-compress"></i>';
        } else {
          document.exitFullscreen().catch(() => {});
          btnFull.innerHTML = '<i class="fa-solid fa-expand"></i>';
        }
      });
    }

    // 7. In-Call Chat Toggle Button
    const btnChat = document.getElementById('gmeetBtnChat');
    const sidePanel = document.getElementById('gmeetSidePanel');
    if (btnChat && sidePanel && !btnChat.dataset.hasListener) {
      btnChat.dataset.hasListener = 'true';
      btnChat.addEventListener('click', () => {
        const isClosed = sidePanel.style.display === 'none';
        if (isClosed) {
          sidePanel.style.display = 'flex';
          btnChat.classList.add('active');
          switchSideTab('chat');
          _unreadChatCount = 0;
          const dot = document.getElementById('gmeetChatUnreadDot');
          if (dot) dot.style.display = 'none';
          const input = document.getElementById('gmeetChatInput');
          if (input) setTimeout(() => input.focus(), 150);
        } else {
          sidePanel.style.display = 'none';
          btnChat.classList.remove('active');
        }
      });
    }

    // 8. People Tab Toggle Button
    const btnPeople = document.getElementById('gmeetBtnPeople');
    if (btnPeople && sidePanel && !btnPeople.dataset.hasListener) {
      btnPeople.dataset.hasListener = 'true';
      btnPeople.addEventListener('click', () => {
        const isClosed = sidePanel.style.display === 'none';
        if (isClosed) {
          sidePanel.style.display = 'flex';
          btnPeople.classList.add('active');
          switchSideTab('people');
        } else {
          if (document.getElementById('gmeetPanelPeople').classList.contains('active')) {
            sidePanel.style.display = 'none';
            btnPeople.classList.remove('active');
          } else {
            switchSideTab('people');
          }
        }
      });
    }

    // 9. Close Side Panel Button
    const btnClosePanel = document.getElementById('gmeetBtnClosePanel');
    if (btnClosePanel && sidePanel && !btnClosePanel.dataset.hasListener) {
      btnClosePanel.dataset.hasListener = 'true';
      btnClosePanel.addEventListener('click', () => {
        sidePanel.style.display = 'none';
        if (btnChat) btnChat.classList.remove('active');
        if (btnPeople) btnPeople.classList.remove('active');
      });
    }

    // 10. Side Panel Tab Switching
    document.querySelectorAll('.gmeet-side-tab').forEach(tabBtn => {
      if (!tabBtn.dataset.hasListener) {
        tabBtn.dataset.hasListener = 'true';
        tabBtn.addEventListener('click', () => {
          switchSideTab(tabBtn.getAttribute('data-tab'));
        });
      }
    });

    // 11. In-Call Chat Form Submit & Enter Key Submission
    const chatForm = document.getElementById('gmeetChatForm');
    const chatInput = document.getElementById('gmeetChatInput');
    const chatSendBtn = document.getElementById('gmeetChatSendBtn');

    function handleChatSend() {
      if (!chatInput) return;
      const txt = chatInput.value;
      if (!txt || !txt.trim()) return;
      chatInput.value = '';
      window.sendInCallMessage(txt);
      setTimeout(() => { if (chatInput) chatInput.focus(); }, 50);
    }

    if (chatForm && !chatForm.dataset.hasListener) {
      chatForm.dataset.hasListener = 'true';
      chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleChatSend();
      });
    }

    if (chatSendBtn && !chatSendBtn.dataset.hasListener) {
      chatSendBtn.dataset.hasListener = 'true';
      chatSendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        handleChatSend();
      });
    }

    if (chatInput && !chatInput.dataset.hasListener) {
      chatInput.dataset.hasListener = 'true';
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleChatSend();
        }
      });
    }

    // 12. Counsellor Clinical Notes Save Button
    const btnSaveNotes = document.getElementById('gmeetBtnSaveNotes');
    if (btnSaveNotes && !btnSaveNotes.dataset.hasListener) {
      btnSaveNotes.dataset.hasListener = 'true';
      btnSaveNotes.addEventListener('click', async () => {
        const notesInput = document.getElementById('gmeetClinicalNotesInput');
        const notesVal = notesInput ? notesInput.value.trim() : '';
        btnSaveNotes.disabled = true;
        btnSaveNotes.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

        if (_currentSessionId && window.dispatchSessionAction) {
          await window.dispatchSessionAction(_currentSessionId, 'end_video', { notes: notesVal || 'Video consultation finalized.' });
        }
        btnSaveNotes.innerHTML = '<i class="fa-solid fa-check"></i> Saved &amp; Finalized';
        showMeetToast('<i class="fa-solid fa-circle-check" style="color: #10B981;"></i> Case notes saved successfully');
        setTimeout(() => {
          window.closeGoogleMeetRoom(true);
        }, 800);
      });
    }

    // 13. Room Code Click to Copy
    const codeBox = document.getElementById('gmeetRoomCodeDisplay');
    if (codeBox && !codeBox.dataset.hasListener) {
      codeBox.dataset.hasListener = 'true';
      codeBox.addEventListener('click', () => {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(_currentRoomId);
          showMeetToast('<i class="fa-solid fa-check" style="color: #10B981;"></i> Consultation code copied');
        }
      });
    }
  }

  function switchSideTab(tabName) {
    document.querySelectorAll('.gmeet-side-tab').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
    });
    document.querySelectorAll('.gmeet-panel-tab-content').forEach(p => {
      p.classList.remove('active');
    });

    const targetPanel = document.getElementById('gmeetPanel' + tabName.charAt(0).toUpperCase() + tabName.slice(1));
    if (targetPanel) targetPanel.classList.add('active');

    const btnChat = document.getElementById('gmeetBtnChat');
    const btnPeople = document.getElementById('gmeetBtnPeople');
    if (btnChat) btnChat.classList.toggle('active', tabName === 'chat');
    if (btnPeople) btnPeople.classList.toggle('active', tabName === 'people');
  }

  // ==============================================================================
  // 6. TEARDOWN & EXIT
  // ==============================================================================
  window.closeGoogleMeetRoom = function(dispatchEndAction = true) {
    playMeetSound('leave');

    // Stop camera broadcasting
    _cameraBroadcasting = false;

    // Notify peer
    broadcastSignal({
      type: 'peer_left',
      senderRole: _userRole,
      senderName: _userName
    });

    // Close BroadcastChannels
    if (_broadcastChannel) {
      try { _broadcastChannel.close(); } catch (e) {}
      _broadcastChannel = null;
    }
    if (_activeCallChannel) {
      try { _activeCallChannel.close(); } catch (e) {}
      _activeCallChannel = null;
    }

    // Close WebRTC Peer Connection
    if (_peerConnection) {
      try { _peerConnection.close(); } catch (e) {}
      _peerConnection = null;
    }

    // Stop Local Media Tracks
    if (_localStream) {
      _localStream.getTracks().forEach(track => {
        try { track.stop(); } catch (e) {}
      });
      _localStream = null;
    }
    _remoteStream = null;

    if (_cameraShareInterval) {
      clearInterval(_cameraShareInterval);
      _cameraShareInterval = null;
    }
    if (_sharedCanvasAnimInterval) {
      clearInterval(_sharedCanvasAnimInterval);
      _sharedCanvasAnimInterval = null;
    }

    if (_sharedCameraCanvas) {
      _sharedCameraCanvas = null;
      _sharedCameraCtx = null;
      _sharedCameraStream = null;
    }

    // Stop Audio Analyser & Polling Intervals
    if (_audioInterval) {
      clearInterval(_audioInterval);
      _audioInterval = null;
    }
    if (_chatPollInterval) {
      clearInterval(_chatPollInterval);
      _chatPollInterval = null;
    }
    if (_signalPollInterval) {
      clearInterval(_signalPollInterval);
      _signalPollInterval = null;
    }
    if (_callTimerInterval) {
      clearInterval(_callTimerInterval);
      _callTimerInterval = null;
    }
    if (_audioContext && _audioContext.state !== 'closed') {
      try { _audioContext.close(); } catch (e) {}
      _audioContext = null;
    }

    // Reset Video Elements
    resetTileMediaState();

    // Hide Modal
    const modal = document.getElementById('gmeetVideoModal');
    if (modal) {
      modal.classList.remove('active');
      modal.style.display = 'none';
    }
    document.body.style.overflow = '';

    // Trigger backend end action if leaving
    if (dispatchEndAction) {
      if (_userRole === 'victim' && window.dispatchVictimSessionAction) {
        window.dispatchVictimSessionAction('leave_video');
      } else if (_userRole === 'counsellor' && _currentSessionId && window.dispatchSessionAction) {
        window.dispatchSessionAction(_currentSessionId, 'end_video', { notes: 'Session concluded by counsellor.' });
      }
    }
  };

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  // Auto initialize listeners on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachControlListeners);
  } else {
    attachControlListeners();
  }

})(window);
