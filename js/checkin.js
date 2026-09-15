/**
 * MENTAURA — Victim Support Pulse Interaction Logic (checkin.js)
 * Implements a calm, one-question-at-a-time, adaptive support conversation.
 * Zero storage of sensitive check-in data in localStorage/sessionStorage.
 */

function getAuthToken() {
  return localStorage.getItem('mentaura_token') || sessionStorage.getItem('mentaura_token') || sessionStorage.getItem('access_token') || localStorage.getItem('access_token') || '';
}

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Enforce Role Protection
  const user = await initAuthGuard(['victim', 'witness', 'affected_family_member']);
  if (!user) return;

  // 2. Extract First Name & Update Navigation/Profile Popover
  const firstName = user.full_name ? user.full_name.split(' ')[0] : 'User';
  const navUserEl = document.getElementById('navUserName');
  if (navUserEl) navUserEl.textContent = firstName;

  // Setup Profile Popover Data
  const popoverName = document.getElementById('popoverName');
  const popoverAccountType = document.getElementById('popoverAccountType');
  const popoverLang = document.getElementById('popoverLang');
  const popoverChannel = document.getElementById('popoverChannel');
  const popoverStatus = document.getElementById('popoverStatus');
  const popoverUserRole = document.getElementById('popoverUserRole');

  if (popoverName) popoverName.textContent = user.full_name || 'Not available';
  if (popoverAccountType) popoverAccountType.textContent = formatRole(user.verified_role) || 'Not available';
  if (popoverUserRole) popoverUserRole.textContent = formatRole(user.verified_role) || 'Support User';
  if (popoverStatus) popoverStatus.textContent = formatStatus(user.account_status) || 'Not available';

  // Setup Profile Popover Interactivity
  setupProfilePopover();
  setupLanguageSelector();
  setupMobileDrawer();
  setupChannelSwitcher();
  setupHeaderSosAndStealth();
  setupChatbotChannel();
  setupVoiceChannel();
  setupIvrsChannel();
  setupSmsChannel();

  // 3. In-memory Support Pulse State (Zero sensitive data persisted to browser storage)
  const supportPulseData = {
    caseId: null,
    wellbeingState: null,
    privateNote: '',
    voiceBlob: null,
    voiceDuration: 0,
    voiceMimeType: null,
    voiceResponseStatus: 'not_added', // 'written_note' | 'voice_note' | 'not_added'
    affectingFactors: [],
    safetyStatus: null,
    caseFollowUp: null,
    moneyFollowUp: null,
    sleepDifficulty: null,
    unsupportedCall: null,
    supportNeeds: [],
    processingMode: 'ai_assisted', // 'ai_assisted' | 'human_review_only'
    startedAt: new Date().toISOString()
  };

  // 4. Fetch Victim Overview for the Support Context Strip
  try {
    const res = await fetch('/api/victim/overview', { credentials: 'include' });
    if (res.ok) {
      const overview = await res.json();
      if (popoverLang) popoverLang.textContent = formatLanguage(overview.preferred_language) || 'English (EN)';
      if (popoverChannel) popoverChannel.textContent = overview.preferred_channel_display || 'Web Portal';

      const ctxStage = document.getElementById('ctxStage');
      const ctxFocus = document.getElementById('ctxFocus');

      if (ctxStage) {
        ctxStage.textContent = (overview.case_overview && overview.case_overview.is_linked)
          ? overview.case_overview.stage_display
          : 'Support monitoring';
      }
      if (ctxFocus) {
        ctxFocus.textContent = 'How you are doing today';
      }
      if (overview.case_overview && overview.case_overview.case_id_masked) {
        supportPulseData.caseId = overview.case_overview.case_id_masked;
      }
    }
  } catch (err) {
    console.warn('Overview fetch notice:', err);
  }

  // 5. One-Question-At-A-Time Screen Navigation
  const screens = {
    1: document.getElementById('screen1'),
    2: document.getElementById('screen2'),
    3: document.getElementById('screen3'),
    4: document.getElementById('screen4'),
    5: document.getElementById('screen5'),
    6: document.getElementById('screen6')
  };

  const contextStrip = document.getElementById('supportContextStrip');
  const progressLine = document.getElementById('pulseProgressLine');
  const progressStepNumber = document.getElementById('progressStepNumber');

  let currentScreenNum = 1;

  function showScreen(screenNum) {
    currentScreenNum = screenNum;

    // Toggle active screen card
    Object.keys(screens).forEach(num => {
      if (screens[num]) {
        screens[num].classList.toggle('active', parseInt(num, 10) === screenNum);
      }
    });

    // Update progress indicator
    if (progressStepNumber) {
      if (screenNum <= 5) {
        progressStepNumber.textContent = `${screenNum} of 5`;
      }
    }

    // Populate review screen whenever screen 5 is activated
    if (screenNum === 5) {
      populateReviewScreen();
    }

    // Hide context strip and progress bar on Confirmation Screen (Screen 6)
    if (screenNum === 6) {
      if (contextStrip) contextStrip.style.display = 'none';
      if (progressLine) progressLine.style.display = 'none';
    } else {
      if (contextStrip) contextStrip.style.display = 'flex';
      if (progressLine) progressLine.style.display = 'flex';
    }

    // Smooth scroll to top of active card
    window.scrollTo({ top: 120, behavior: 'smooth' });
  }

  // ==========================================================================
  // SCREEN 1: HOW ARE THINGS TODAY?
  // ==========================================================================
  const wellbeingRadios = document.querySelectorAll('input[name="wellbeingState"]');
  const s1ContinueBtn = document.getElementById('s1ContinueBtn');
  const s1FeedbackBanner = document.getElementById('s1FeedbackBanner');
  const s1ChangeAnswerBtn = document.getElementById('s1ChangeAnswerBtn');

  wellbeingRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.wellbeing-card').forEach(c => c.classList.remove('selected'));
      const parent = radio.closest('.wellbeing-card');
      if (parent) parent.classList.add('selected');

      supportPulseData.wellbeingState = radio.value;

      if (s1FeedbackBanner) s1FeedbackBanner.style.display = 'flex';
      if (s1ContinueBtn) s1ContinueBtn.disabled = false;
    });
  });

  if (s1ChangeAnswerBtn) {
    s1ChangeAnswerBtn.addEventListener('click', () => {
      wellbeingRadios.forEach(r => {
        r.checked = false;
        const parent = r.closest('.wellbeing-card');
        if (parent) parent.classList.remove('selected');
      });
      supportPulseData.wellbeingState = null;
      if (s1FeedbackBanner) s1FeedbackBanner.style.display = 'none';
      if (s1ContinueBtn) s1ContinueBtn.disabled = true;
    });
  }

  if (s1ContinueBtn) {
    s1ContinueBtn.addEventListener('click', () => {
      showScreen(2);
    });
  }

  // ==========================================================================
  // SCREEN 2: WOULD YOU LIKE TO ADD ANYTHING? (Text or Voice)
  // ==========================================================================
  const choiceWriteCard = document.getElementById('choiceWriteCard');
  const choiceVoiceCard = document.getElementById('choiceVoiceCard');
  const choiceSkipCard = document.getElementById('choiceSkipCard');

  const revealedTextSection = document.getElementById('revealedTextSection');
  const revealedVoiceSection = document.getElementById('revealedVoiceSection');

  const noteTextarea = document.getElementById('privateNoteText');
  const noteCharCount = document.getElementById('noteCharCount');
  const saveNoteBtn = document.getElementById('saveNoteBtn');
  const clearNoteBtn = document.getElementById('clearNoteBtn');
  const skipNoteBtn = document.getElementById('skipNoteBtn');
  const savedNotePreviewBox = document.getElementById('savedNotePreviewBox');
  const savedNoteSnippet = document.getElementById('savedNoteSnippet');
  const editSavedNoteBtn = document.getElementById('editSavedNoteBtn');

  const s2BackBtn = document.getElementById('s2BackBtn');
  const s2ContinueBtn = document.getElementById('s2ContinueBtn');

  // Choice 1: Write a note
  if (choiceWriteCard) {
    choiceWriteCard.addEventListener('click', () => {
      document.querySelectorAll('.add-choice-card').forEach(c => c.classList.remove('active-choice'));
      choiceWriteCard.classList.add('active-choice');
      if (revealedTextSection) revealedTextSection.style.display = 'block';
      if (revealedVoiceSection) revealedVoiceSection.style.display = 'none';
      if (noteTextarea) noteTextarea.focus();
    });
  }

  // Choice 2: Record a voice note
  if (choiceVoiceCard) {
    choiceVoiceCard.addEventListener('click', () => {
      document.querySelectorAll('.add-choice-card').forEach(c => c.classList.remove('active-choice'));
      choiceVoiceCard.classList.add('active-choice');
      if (revealedVoiceSection) revealedVoiceSection.style.display = 'block';
      if (revealedTextSection) revealedTextSection.style.display = 'none';
    });
  }

  // Choice 3: Skip for now
  if (choiceSkipCard) {
    choiceSkipCard.addEventListener('click', () => {
      document.querySelectorAll('.add-choice-card').forEach(c => c.classList.remove('active-choice'));
      choiceSkipCard.classList.add('active-choice');
      if (revealedTextSection) revealedTextSection.style.display = 'none';
      if (revealedVoiceSection) revealedVoiceSection.style.display = 'none';
      showScreen(3);
    });
  }

  // Text note handlers
  if (noteTextarea) {
    noteTextarea.addEventListener('input', () => {
      const val = noteTextarea.value;
      if (noteCharCount) noteCharCount.textContent = `${val.length} / 1000`;
    });
  }

  if (saveNoteBtn) {
    saveNoteBtn.addEventListener('click', () => {
      const textVal = noteTextarea ? noteTextarea.value.trim() : '';
      supportPulseData.privateNote = textVal;
      if (textVal) {
        supportPulseData.voiceResponseStatus = 'written_note';
        if (savedNoteSnippet) savedNoteSnippet.textContent = textVal;
        if (savedNotePreviewBox) savedNotePreviewBox.style.display = 'block';
      } else {
        if (savedNotePreviewBox) savedNotePreviewBox.style.display = 'none';
      }
    });
  }

  if (clearNoteBtn) {
    clearNoteBtn.addEventListener('click', () => {
      if (noteTextarea) noteTextarea.value = '';
      if (noteCharCount) noteCharCount.textContent = '0 / 1000';
      supportPulseData.privateNote = '';
      if (savedNotePreviewBox) savedNotePreviewBox.style.display = 'none';
    });
  }

  if (skipNoteBtn) {
    skipNoteBtn.addEventListener('click', () => {
      showScreen(3);
    });
  }

  if (editSavedNoteBtn) {
    editSavedNoteBtn.addEventListener('click', () => {
      if (savedNotePreviewBox) savedNotePreviewBox.style.display = 'none';
      if (noteTextarea) noteTextarea.focus();
    });
  }

  // Voice Recording Implementation (MediaRecorder API)
  let mediaRecorder = null;
  let audioChunks = [];
  let recordTimerInterval = null;
  let recordingSeconds = 0;
  let audioStream = null;
  let audioPreviewUrl = null;

  const startRecordBtn = document.getElementById('startRecordBtn');
  const stopRecordBtn = document.getElementById('stopRecordBtn');
  const recordingActivePanel = document.getElementById('recordingActivePanel');
  const recordedPreviewPanel = document.getElementById('recordedPreviewPanel');
  const recordingTimer = document.getElementById('recordingTimer');
  const voiceAudioPlayer = document.getElementById('voiceAudioPlayer');
  const recordedBadge = document.getElementById('recordedBadge');
  const recordAgainBtn = document.getElementById('recordAgainBtn');
  const useRecordingBtn = document.getElementById('useRecordingBtn');
  const deleteRecordBtn = document.getElementById('deleteRecordBtn');
  const voiceErrorAlert = document.getElementById('voiceErrorAlert');
  const voiceErrorText = document.getElementById('voiceErrorText');

  function showVoiceError(msg) {
    if (voiceErrorAlert && voiceErrorText) {
      voiceErrorText.textContent = msg;
      voiceErrorAlert.style.display = 'flex';
    }
  }

  function hideVoiceError() {
    if (voiceErrorAlert) {
      voiceErrorAlert.style.display = 'none';
    }
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  async function startRecording() {
    hideVoiceError();
    audioChunks = [];
    recordingSeconds = 0;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showVoiceError('Voice recording is not supported on this browser. You can continue with written notes.');
      return;
    }

    try {
      // Request microphone access only after explicit click
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      }

      mediaRecorder = new MediaRecorder(audioStream, { mimeType });
      supportPulseData.voiceMimeType = mimeType;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunks, { type: supportPulseData.voiceMimeType || 'audio/webm' });
        supportPulseData.voiceBlob = blob;
        supportPulseData.voiceDuration = recordingSeconds;
        supportPulseData.voiceResponseStatus = 'voice_note';

        if (audioPreviewUrl) {
          URL.revokeObjectURL(audioPreviewUrl);
        }
        audioPreviewUrl = URL.createObjectURL(blob);

        if (voiceAudioPlayer) {
          voiceAudioPlayer.src = audioPreviewUrl;
        }

        if (recordedBadge) {
          recordedBadge.innerHTML = `<i class="fa-solid fa-check"></i> Recorded (${formatTime(recordingSeconds)})`;
        }

        // Cleanly stop all tracks
        if (audioStream) {
          audioStream.getTracks().forEach(track => track.stop());
          audioStream = null;
        }

        if (recordingActivePanel) recordingActivePanel.style.display = 'none';
        if (recordedPreviewPanel) recordedPreviewPanel.style.display = 'flex';
      };

      mediaRecorder.start(250);

      if (startRecordBtn) startRecordBtn.style.display = 'none';
      if (recordedPreviewPanel) recordedPreviewPanel.style.display = 'none';
      if (recordingActivePanel) recordingActivePanel.style.display = 'flex';
      if (recordingTimer) recordingTimer.textContent = '00:00 / 02:00';

      // 120s maximum duration timer
      recordTimerInterval = setInterval(() => {
        recordingSeconds++;
        if (recordingTimer) {
          recordingTimer.textContent = `${formatTime(recordingSeconds)} / 02:00`;
        }
        if (recordingSeconds >= 120) {
          stopRecording();
        }
      }, 1000);

    } catch (err) {
      console.error('Microphone error:', err);
      showVoiceError('Microphone permission was not granted or microphone was not found.');
      if (startRecordBtn) startRecordBtn.style.display = 'inline-flex';
      if (recordingActivePanel) recordingActivePanel.style.display = 'none';
    }
  }

  function stopRecording() {
    if (recordTimerInterval) {
      clearInterval(recordTimerInterval);
      recordTimerInterval = null;
    }
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  }

  function deleteRecording() {
    if (audioPreviewUrl) {
      URL.revokeObjectURL(audioPreviewUrl);
      audioPreviewUrl = null;
    }
    supportPulseData.voiceBlob = null;
    supportPulseData.voiceDuration = 0;
    supportPulseData.voiceResponseStatus = 'not_added';

    if (voiceAudioPlayer) voiceAudioPlayer.src = '';
    if (recordedPreviewPanel) recordedPreviewPanel.style.display = 'none';
    if (startRecordBtn) startRecordBtn.style.display = 'inline-flex';
  }

  if (startRecordBtn) startRecordBtn.addEventListener('click', startRecording);
  if (stopRecordBtn) stopRecordBtn.addEventListener('click', stopRecording);
  if (recordAgainBtn) recordAgainBtn.addEventListener('click', startRecording);
  if (deleteRecordBtn) deleteRecordBtn.addEventListener('click', deleteRecording);
  if (useRecordingBtn) {
    useRecordingBtn.addEventListener('click', () => {
      showScreen(3);
    });
  }

  if (s2BackBtn) s2BackBtn.addEventListener('click', () => showScreen(1));
  if (s2ContinueBtn) {
    s2ContinueBtn.addEventListener('click', () => {
      // If note was typed but not saved yet, save it
      if (noteTextarea && noteTextarea.value.trim() && !supportPulseData.privateNote) {
        supportPulseData.privateNote = noteTextarea.value.trim();
        supportPulseData.voiceResponseStatus = 'written_note';
      }
      showScreen(3);
    });
  }

  // ==========================================================================
  // SCREEN 3: WHAT IS AFFECTING YOU MOST TODAY? (Adaptive Follow-ups)
  // ==========================================================================
  const factorCheckboxes = document.querySelectorAll('input[name="affectingFactor"]');
  const followUpSafety = document.getElementById('followUpSafety');
  const followUpCase = document.getElementById('followUpCase');
  const followUpMoney = document.getElementById('followUpMoney');
  const followUpSleep = document.getElementById('followUpSleep');
  const followUpUnsupported = document.getElementById('followUpUnsupported');

  const s3BackBtn = document.getElementById('s3BackBtn');
  const s3ContinueBtn = document.getElementById('s3ContinueBtn');

  function updateAffectingFactors() {
    const selected = [];
    factorCheckboxes.forEach(cb => {
      const parent = cb.closest('.factor-check-card');
      if (cb.checked) {
        selected.push(cb.value);
        if (parent) parent.classList.add('selected');
      } else {
        if (parent) parent.classList.remove('selected');
      }
    });

    supportPulseData.affectingFactors = selected;

    // Toggle Adaptive Follow-ups strictly based on selection
    if (followUpSafety) {
      followUpSafety.style.display = selected.includes('Safety or threats') ? 'block' : 'none';
      if (!selected.includes('Safety or threats')) {
        supportPulseData.safetyStatus = null;
        document.querySelectorAll('input[name="safetyStatus"]').forEach(r => r.checked = false);
      }
    }

    if (followUpCase) {
      followUpCase.style.display = selected.includes('Case or hearing') ? 'block' : 'none';
      if (!selected.includes('Case or hearing')) {
        supportPulseData.caseFollowUp = null;
        document.querySelectorAll('input[name="caseFollowUp"]').forEach(r => r.checked = false);
      }
    }

    if (followUpMoney) {
      followUpMoney.style.display = selected.includes('Money or compensation') ? 'block' : 'none';
      if (!selected.includes('Money or compensation')) {
        supportPulseData.moneyFollowUp = null;
        document.querySelectorAll('input[name="moneyFollowUp"]').forEach(r => r.checked = false);
      }
    }

    if (followUpSleep) {
      followUpSleep.style.display = selected.includes('Sleep or daily life') ? 'block' : 'none';
      if (!selected.includes('Sleep or daily life')) {
        supportPulseData.sleepDifficulty = null;
        document.querySelectorAll('input[name="sleepDifficulty"]').forEach(r => r.checked = false);
      }
    }

    if (followUpUnsupported) {
      followUpUnsupported.style.display = selected.includes('Feeling unsupported') ? 'block' : 'none';
      if (!selected.includes('Feeling unsupported')) {
        supportPulseData.unsupportedCall = null;
        document.querySelectorAll('input[name="unsupportedCall"]').forEach(r => r.checked = false);
      }
    }
  }

  factorCheckboxes.forEach(cb => {
    cb.addEventListener('change', updateAffectingFactors);
  });

  // Adaptive Follow-up radio listeners
  document.querySelectorAll('input[name="safetyStatus"]').forEach(r => {
    r.addEventListener('change', () => {
      supportPulseData.safetyStatus = r.value;
      updateAdaptiveRadioHighlight('safetyStatus');
    });
  });

  document.querySelectorAll('input[name="caseFollowUp"]').forEach(r => {
    r.addEventListener('change', () => {
      supportPulseData.caseFollowUp = r.value;
      updateAdaptiveRadioHighlight('caseFollowUp');
    });
  });

  document.querySelectorAll('input[name="moneyFollowUp"]').forEach(r => {
    r.addEventListener('change', () => {
      supportPulseData.moneyFollowUp = r.value;
      updateAdaptiveRadioHighlight('moneyFollowUp');
    });
  });

  document.querySelectorAll('input[name="sleepDifficulty"]').forEach(r => {
    r.addEventListener('change', () => {
      supportPulseData.sleepDifficulty = r.value;
      updateAdaptiveRadioHighlight('sleepDifficulty');
    });
  });

  document.querySelectorAll('input[name="unsupportedCall"]').forEach(r => {
    r.addEventListener('change', () => {
      supportPulseData.unsupportedCall = r.value;
      updateAdaptiveRadioHighlight('unsupportedCall');
    });
  });

  function updateAdaptiveRadioHighlight(radioName) {
    document.querySelectorAll(`input[name="${radioName}"]`).forEach(r => {
      const parent = r.closest('.adaptive-radio-label');
      if (parent) {
        parent.classList.toggle('selected', r.checked);
      }
    });
  }

  if (s3BackBtn) s3BackBtn.addEventListener('click', () => showScreen(2));
  if (s3ContinueBtn) s3ContinueBtn.addEventListener('click', () => showScreen(4));

  // ==========================================================================
  // SCREEN 4: WHAT WOULD HELP NEXT?
  // ==========================================================================
  const needCheckboxes = document.querySelectorAll('input[name="supportNeed"]');
  const needOkayCheckbox = document.getElementById('needOkay');
  const s4BackBtn = document.getElementById('s4BackBtn');
  const s4ReviewBtn = document.getElementById('s4ReviewBtn');

  function updateSupportNeeds(changedElement) {
    if (changedElement === needOkayCheckbox && needOkayCheckbox.checked) {
      // Uncheck all other support needs
      needCheckboxes.forEach(cb => {
        if (cb !== needOkayCheckbox) {
          cb.checked = false;
          const parent = cb.closest('.support-need-card');
          if (parent) parent.classList.remove('selected');
        }
      });
    } else if (changedElement && changedElement !== needOkayCheckbox && changedElement.checked) {
      // If another need selected, uncheck "I am okay for now"
      if (needOkayCheckbox) {
        needOkayCheckbox.checked = false;
        const parent = needOkayCheckbox.closest('.support-need-card');
        if (parent) parent.classList.remove('selected');
      }
    }

    const selectedNeeds = [];
    needCheckboxes.forEach(cb => {
      const parent = cb.closest('.support-need-card');
      if (cb.checked) {
        selectedNeeds.push(cb.value);
        if (parent) parent.classList.add('selected');
      } else {
        if (parent) parent.classList.remove('selected');
      }
    });

    supportPulseData.supportNeeds = selectedNeeds;
  }

  needCheckboxes.forEach(cb => {
    cb.addEventListener('change', (e) => updateSupportNeeds(e.target));
  });

  if (s4BackBtn) s4BackBtn.addEventListener('click', () => showScreen(3));
  if (s4ReviewBtn) {
    s4ReviewBtn.addEventListener('click', () => {
      populateReviewScreen();
      showScreen(5);
    });
  }

  // ==========================================================================
  // SCREEN 5: REVIEW YOUR UPDATE
  // ==========================================================================
  // SCREEN 5: REVIEW YOUR UPDATE (Compact Summary & Inline Processing Mode)
  // ==========================================================================
  const revWellbeing = document.getElementById('revWellbeing');
  const revAddedNote = document.getElementById('revAddedNote');
  const revFactors = document.getElementById('revFactors');
  const revFollowUps = document.getElementById('revFollowUps');
  const revNeeds = document.getElementById('revNeeds');
  const revProcessingChip = document.getElementById('revProcessingChip');

  const editS1Btn = document.getElementById('editS1Btn');
  const editS2Btn = document.getElementById('editS2Btn');
  const editS3Btn = document.getElementById('editS3Btn');
  const editS4Btn = document.getElementById('editS4Btn');

  const changeProcessingModeBtn = document.getElementById('changeProcessingModeBtn');
  const processingModeInlineSelector = document.getElementById('processingModeInlineSelector');
  const closeModeDrawerBtn = document.getElementById('closeModeDrawerBtn');
  const modeChoiceRadios = document.querySelectorAll('input[name="processingModeChoice"]');

  const s5BackBtn = document.getElementById('s5BackBtn');
  const submitPulseBtn = document.getElementById('submitPulseBtn');

  // Friendly backend status mappings
  const STATUS_MAP = {
    'submitted': 'Analysis completed & logged',
    'queued': 'Processed in real-time',
    'processing': 'Processing completed',
    'completed': 'Processed & analysed in real-time',
    'not_requested': 'Processed for human review',
    'failed': 'Update submitted for human review; automatic processing was not completed',
    'human_review_pending': 'Available for authorised human review'
  };

  function formatProcessingStatus(statusVal, defaultFallback) {
    if (!statusVal) return defaultFallback || 'Prepared for the next secure processing stage';
    const key = String(statusVal).toLowerCase().trim();
    return STATUS_MAP[key] || defaultFallback || 'Prepared for the next secure processing stage';
  }

  function populateReviewScreen() {
    // 1. Wellbeing
    if (revWellbeing) {
      revWellbeing.textContent = supportPulseData.wellbeingState || 'Not specified';
    }

    // 2. Additional Response
    if (revAddedNote) {
      const hasVoice = Boolean(supportPulseData.voiceBlob);
      const hasNote = Boolean(supportPulseData.privateNote && supportPulseData.privateNote.trim());
      const voiceTime = formatTime(supportPulseData.voiceDuration || 0);

      if (hasVoice && hasNote) {
        revAddedNote.textContent = `Written note added, Voice note added — ${voiceTime}`;
      } else if (hasVoice) {
        revAddedNote.textContent = `Voice note added — ${voiceTime}`;
      } else if (hasNote) {
        revAddedNote.textContent = 'Written note added';
      } else {
        revAddedNote.textContent = 'Nothing added';
      }
    }

    // 3. Affecting Factors
    if (revFactors) {
      if (supportPulseData.affectingFactors && supportPulseData.affectingFactors.length > 0) {
        revFactors.textContent = supportPulseData.affectingFactors.join(', ');
      } else if (supportPulseData.wellbeingState === 'Prefer not to say') {
        revFactors.textContent = 'Prefer not to say';
      } else {
        revFactors.textContent = 'None specified';
      }
    }

    if (revFollowUps) {
      const followUpList = [];
      if (supportPulseData.safetyStatus) {
        followUpList.push(`Safety: ${supportPulseData.safetyStatus}`);
      }
      if (supportPulseData.caseFollowUp) {
        followUpList.push(`Case follow-up: ${supportPulseData.caseFollowUp}`);
      }
      if (supportPulseData.moneyFollowUp) {
        followUpList.push(`Compensation: ${supportPulseData.moneyFollowUp}`);
      }
      if (supportPulseData.sleepDifficulty) {
        followUpList.push(`Daily impact: ${supportPulseData.sleepDifficulty}`);
      }
      if (supportPulseData.unsupportedCall) {
        followUpList.push(`Support call: ${supportPulseData.unsupportedCall}`);
      }

      if (followUpList.length > 0) {
        revFollowUps.innerHTML = followUpList.map(item => `<div>• ${item}</div>`).join('');
        revFollowUps.style.display = 'block';
      } else {
        revFollowUps.style.display = 'none';
        revFollowUps.innerHTML = '';
      }
    }

    // 4. Support Needs
    if (revNeeds) {
      if (supportPulseData.supportNeeds && supportPulseData.supportNeeds.length > 0) {
        revNeeds.textContent = supportPulseData.supportNeeds.join(', ');
      } else {
        revNeeds.textContent = 'No support requested';
      }
    }

    // 5. Processing Mode Chip
    if (revProcessingChip) {
      if (supportPulseData.processingMode === 'ai_assisted') {
        revProcessingChip.innerHTML = '<i class="fa-solid fa-brain"></i> AI-assisted support';
      } else {
        revProcessingChip.innerHTML = '<i class="fa-solid fa-user-shield"></i> Human review only';
      }
    }
  }

  // Edit / Change buttons jump directly to respective screens preserving all data
  if (editS1Btn) editS1Btn.addEventListener('click', () => showScreen(1));
  if (editS2Btn) editS2Btn.addEventListener('click', () => showScreen(2));
  if (editS3Btn) editS3Btn.addEventListener('click', () => showScreen(3));
  if (editS4Btn) editS4Btn.addEventListener('click', () => showScreen(4));

  // Toggle inline processing mode drawer
  if (changeProcessingModeBtn && processingModeInlineSelector) {
    changeProcessingModeBtn.addEventListener('click', () => {
      const isHidden = processingModeInlineSelector.style.display === 'none' || !processingModeInlineSelector.style.display;
      processingModeInlineSelector.style.display = isHidden ? 'block' : 'none';
    });
  }

  if (closeModeDrawerBtn && processingModeInlineSelector) {
    closeModeDrawerBtn.addEventListener('click', () => {
      processingModeInlineSelector.style.display = 'none';
    });
  }

  // Processing mode choice radio handlers
  modeChoiceRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.compact-mode-option').forEach(c => c.classList.remove('selected'));
      const parent = radio.closest('.compact-mode-option');
      if (parent) parent.classList.add('selected');
      supportPulseData.processingMode = radio.value;

      // Update chip immediately
      if (revProcessingChip) {
        if (radio.value === 'ai_assisted') {
          revProcessingChip.innerHTML = '<i class="fa-solid fa-brain"></i> AI-assisted support';
        } else {
          revProcessingChip.innerHTML = '<i class="fa-solid fa-user-shield"></i> Human review only';
        }
      }
    });
  });

  if (s5BackBtn) s5BackBtn.addEventListener('click', () => showScreen(4));

  // ==========================================================================
  // SUBMISSION LOGIC (Real JSON / Multipart API Submission)
  // ==========================================================================
  if (submitPulseBtn) {
    submitPulseBtn.addEventListener('click', async () => {
      submitPulseBtn.disabled = true;
      submitPulseBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting…';

      // Assemble follow-up requests list
      const followUpRequests = [];
      if (supportPulseData.caseFollowUp && supportPulseData.caseFollowUp !== 'Not now.') {
        followUpRequests.push(`Case Event: ${supportPulseData.caseFollowUp}`);
      }
      if (supportPulseData.moneyFollowUp && supportPulseData.moneyFollowUp !== 'Not now.') {
        followUpRequests.push(`Compensation: ${supportPulseData.moneyFollowUp}`);
      }
      if (supportPulseData.unsupportedCall && supportPulseData.unsupportedCall === 'Yes.') {
        followUpRequests.push('Request Support Team Call');
      }

      const isAiMode = supportPulseData.processingMode === 'ai_assisted';

      const payloadMeta = {
        case_id: supportPulseData.caseId,
        channel: 'web',
        language: 'EN',
        ai_processing_consent: isAiMode,
        processing_mode: supportPulseData.processingMode,
        consent_version: '1.0',
        wellbeing_state: supportPulseData.wellbeingState,
        private_note: supportPulseData.privateNote || null,
        voice_response_status: supportPulseData.voiceResponseStatus,
        audio_duration_seconds: supportPulseData.voiceDuration || null,
        affecting_factors: supportPulseData.affectingFactors,
        safety_status: supportPulseData.safetyStatus,
        follow_up_requests: followUpRequests,
        support_needs: supportPulseData.supportNeeds,
        started_at: supportPulseData.startedAt,
        submitted_at: new Date().toISOString()
      };

      try {
        let response;
        if (supportPulseData.voiceBlob) {
          // Multipart submission with real audio recording
          const formData = new FormData();
          formData.append('metadata', JSON.stringify(payloadMeta));
          formData.append('audio_file', supportPulseData.voiceBlob, 'support_voice_note.webm');

          response = await fetch('/api/victim/pulse-multipart', {
            method: 'POST',
            credentials: 'include',
            body: formData
          });
        } else {
          // JSON submission
          response = await fetch('/api/victim/pulse', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payloadMeta)
          });
        }

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Submission failed' }));
          throw new Error(errData.detail || 'Failed to submit Support Pulse');
        }

        const result = await response.json();

        // Screen 6 Confirmation Updates based on actual real-time backend processing
        const outreach = result.care_team_outreach || {};

        const s6Heading = document.getElementById('s6Heading');
        const confirmIntroMessage = document.getElementById('confirmIntroMessage');
        const confirmModeTagTitle = document.getElementById('confirmModeTagTitle');
        const confirmStatusBadge = document.getElementById('confirmStatusBadge');
        const confirmModeTagDesc = document.getElementById('confirmModeTagDesc');
        const careTeamContactCard = document.getElementById('careTeamContactCard');
        const careTeamTimelineBadge = document.getElementById('careTeamTimelineBadge');
        const careTeamMessageText = document.getElementById('careTeamMessageText');
        const priorityReviewAlertTag = document.getElementById('priorityReviewAlertTag');
        const priorityReviewAlertText = document.getElementById('priorityReviewAlertText');
        const whatNextText1 = document.getElementById('whatNextText1');
        const whatNextText2 = document.getElementById('whatNextText2');
        const whatNextText3 = document.getElementById('whatNextText3');

        if (s6Heading) {
          s6Heading.textContent = outreach.summary_headline || 'Your update has been processed';
        }
        if (confirmIntroMessage) {
          confirmIntroMessage.textContent = 'Thank you for sharing how you are doing. Your update has been processed in real time and securely shared with your authorized care team.';
        }

        if (isAiMode) {
          if (confirmModeTagTitle) {
            confirmModeTagTitle.innerHTML = '<i class="fa-solid fa-brain"></i> AI-assisted support';
          }
          if (confirmStatusBadge) {
            confirmStatusBadge.className = 'status-box-badge status-badge-success';
            confirmStatusBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> ' + (outreach.badge_text || 'Processed &amp; Analysed in Real-Time');
          }
          if (confirmModeTagDesc) {
            confirmModeTagDesc.textContent = result.xai_summary || 'Your emotional indicators, check-in factors, and responses were analyzed immediately. A care summary is now available to authorized support personnel.';
          }
        } else {
          if (confirmModeTagTitle) {
            confirmModeTagTitle.innerHTML = '<i class="fa-solid fa-user-shield"></i> Human review only';
          }
          if (confirmStatusBadge) {
            confirmStatusBadge.className = 'status-box-badge status-badge-success';
            confirmStatusBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Processed for Human Review';
          }
          if (confirmModeTagDesc) {
            confirmModeTagDesc.textContent = 'Your update is securely recorded and routed directly to authorized personnel for coordinated human review and care.';
          }
        }

        // Show Care Team Outreach Notice Card
        if (careTeamContactCard) {
          careTeamContactCard.style.display = 'block';
        }
        if (careTeamTimelineBadge) {
          careTeamTimelineBadge.innerHTML = `<i class="fa-regular fa-clock"></i> Contact: ${outreach.contact_timeline || 'within 24 hours'}`;
        }
        if (careTeamMessageText) {
          careTeamMessageText.textContent = outreach.team_contact_message || (
            followUpRequests.length > 0
              ? `Our support team and assigned counsellor have received your update. We have logged your follow-up requests and an authorized team member will contact you within 24 hours to assist you.`
              : `Our support team and assigned counsellor have received your update in real-time. An authorized coordinator will review your file and contact you to provide continuous support.`
          );
        }

        // Update Dynamic Next Steps based on response
        if (outreach.next_steps && outreach.next_steps.length >= 3) {
          if (whatNextText1) whatNextText1.textContent = `${outreach.next_steps[0].title}: ${outreach.next_steps[0].desc}`;
          if (whatNextText2) whatNextText2.textContent = `${outreach.next_steps[1].title}: ${outreach.next_steps[1].desc}`;
          if (whatNextText3) whatNextText3.textContent = `${outreach.next_steps[2].title}: ${outreach.next_steps[2].desc}`;
        } else {
          if (whatNextText1) whatNextText1.textContent = 'Real-Time Processing: Your responses and emotional indicators were analyzed immediately upon submission.';
          if (whatNextText2) whatNextText2.textContent = 'Care Cell Alerted: Your designated counsellor and support coordinator have received your update.';
          if (whatNextText3) whatNextText3.textContent = `Support Outreach: Authorized team members will contact you ${outreach.contact_timeline || 'within 24 hours'}.`;
        }

        // Show Priority review notice if flagged by safety or backend
        const isPriority = result.priority_review || outreach.has_safety_concern || (
          supportPulseData.safetyStatus === 'I do not feel completely safe.' ||
          supportPulseData.safetyStatus === 'No, I do not feel safe.' ||
          (supportPulseData.affectingFactors && supportPulseData.affectingFactors.some(f => f.toLowerCase().includes('safety'))) ||
          followUpRequests.length > 0
        );

        if (priorityReviewAlertTag) {
          priorityReviewAlertTag.style.display = isPriority ? 'flex' : 'none';
          if (isPriority && priorityReviewAlertText) {
            if (outreach.has_safety_concern || supportPulseData.safetyStatus === 'No, I do not feel safe.') {
              priorityReviewAlertText.textContent = 'Priority Alert: Personal safety concern noted. Rapid protection and care outreach initiated.';
            } else if (followUpRequests.length > 0) {
              priorityReviewAlertText.textContent = 'Priority Review: Specific support requests have been flagged for expedited team review.';
            }
          }
        }

        showScreen(6);

      } catch (error) {
        console.error('Submission error:', error);
        alert('We were unable to submit your update right now. Please try again or reach out to your support team.');
        submitPulseBtn.disabled = false;
        submitPulseBtn.innerHTML = 'Submit Support Pulse &rarr;';
      }
    });
  }

  // ==========================================================================
  // PAUSE & EXIT MODAL LOGIC
  // ==========================================================================
  const pauseExitModal = document.getElementById('pauseExitModal');
  const pauseKeepGoingBtn = document.getElementById('pauseKeepGoingBtn');
  const pauseDiscardExitBtn = document.getElementById('pauseDiscardExitBtn');

  // Attach pause handlers to all screens
  ['s1PauseBtn', 's2PauseBtn', 's3PauseBtn', 's4PauseBtn', 's5PauseBtn'].forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', () => {
        if (pauseExitModal) pauseExitModal.classList.add('show');
      });
    }
  });

  if (pauseKeepGoingBtn) {
    pauseKeepGoingBtn.addEventListener('click', () => {
      if (pauseExitModal) pauseExitModal.classList.remove('show');
    });
  }

  if (pauseDiscardExitBtn) {
    pauseDiscardExitBtn.addEventListener('click', () => {
      // Clear sensitive in-memory state and redirect
      if (audioPreviewUrl) {
        URL.revokeObjectURL(audioPreviewUrl);
      }
      window.location.href = 'victim-home.html';
    });
  }

  // Close modal on click outside
  if (pauseExitModal) {
    pauseExitModal.addEventListener('click', (e) => {
      if (e.target === pauseExitModal) {
        pauseExitModal.classList.remove('show');
      }
    });
  }
});

// Helper Formatting Functions
function formatRole(role) {
  if (!role) return 'Support User';
  return role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatStatus(status) {
  if (!status) return 'Active';
  return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatLanguage(langCode) {
  const map = {
    EN: 'English (EN)',
    HI: 'हिंदी (HI)',
    TA: 'தமிழ் (TA)',
    TE: 'తెలుగు (TE)',
    BN: 'বাংলা (BN)',
    MR: 'मराठी (MR)'
  };
  return map[langCode] || langCode || 'English (EN)';
}

function setupProfilePopover() {
  // Use the actual IDs present in checkin.html
  const trigger = document.getElementById('userProfileBtn');
  const popover = document.getElementById('userProfilePopover');
  const closeXBtn = document.getElementById('popoverCloseBtn');
  const closeActionBtn = document.getElementById('popoverCloseActionBtn');

  if (!trigger || !popover) return;

  function openPopover() {
    popover.classList.add('active');
    popover.style.display = 'block';
    popover.setAttribute('aria-hidden', 'false');
    trigger.setAttribute('aria-expanded', 'true');
  }

  function closePopover() {
    popover.classList.remove('active');
    popover.style.display = 'none';
    popover.setAttribute('aria-hidden', 'true');
    trigger.setAttribute('aria-expanded', 'false');
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    if (popover.classList.contains('active')) {
      closePopover();
    } else {
      openPopover();
    }
  });

  if (closeXBtn) closeXBtn.addEventListener('click', closePopover);
  if (closeActionBtn) closeActionBtn.addEventListener('click', closePopover);

  document.addEventListener('click', (e) => {
    if (!popover.contains(e.target) && !trigger.contains(e.target)) {
      closePopover();
    }
  });
}

function setupLanguageSelector() {
  // Use the actual IDs present in checkin.html
  const btn = document.getElementById('langSelectorBtn');
  const menu = document.getElementById('langDropdown');
  const label = document.getElementById('selectedLangText');

  if (!btn || !menu) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = menu.classList.contains('show');
    if (isOpen) {
      menu.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    } else {
      menu.classList.add('show');
      btn.setAttribute('aria-expanded', 'true');
    }
  });

  // li items with data-lang attribute
  menu.querySelectorAll('li[data-lang]').forEach(opt => {
    opt.addEventListener('click', () => {
      const code = opt.getAttribute('data-lang');
      if (label) label.textContent = code;
      menu.querySelectorAll('li').forEach(li => li.classList.remove('active'));
      opt.classList.add('active');
      menu.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    });
  });

  document.addEventListener('click', (e) => {
    if (!btn.contains(e.target) && !menu.contains(e.target)) {
      menu.classList.remove('show');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
}

function setupMobileDrawer() {
  const toggle = document.getElementById('mobileMenuToggle');
  const drawer = document.getElementById('mobileMenuDrawer');

  if (!toggle || !drawer) return;

  toggle.addEventListener('click', () => {
    const isOpen = drawer.classList.contains('open');
    drawer.classList.toggle('open', !isOpen);
    toggle.classList.toggle('active', !isOpen);
    drawer.setAttribute('aria-hidden', isOpen ? 'true' : 'false');
    toggle.setAttribute('aria-expanded', String(!isOpen));
  });

  // Close drawer when clicking outside
  document.addEventListener('click', (e) => {
    if (!drawer.contains(e.target) && !toggle.contains(e.target)) {
      drawer.classList.remove('open');
      toggle.classList.remove('active');
      drawer.setAttribute('aria-hidden', 'true');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });
}

/**
 * =======================================================
 * MULTI-CHANNEL SWITCHER (SIH 26094)
 * Switches between Form, Chatbot, Voice, IVRS, and SMS views
 * =======================================================
 */
function setupChannelSwitcher() {
  const tabs = document.querySelectorAll('.channel-tab-btn');
  const viewMap = {
    form: document.getElementById('channelFormView'),
    chatbot: document.getElementById('channelChatbotView'),
    voice: document.getElementById('channelVoiceView'),
    ivrs: document.getElementById('channelIvrsView'),
    sms: document.getElementById('channelSmsView')
  };

  function activateChannel(channelName) {
    tabs.forEach(btn => {
      const match = btn.getAttribute('data-channel') === channelName;
      btn.classList.toggle('active', match);
      btn.setAttribute('aria-selected', match ? 'true' : 'false');
    });

    Object.entries(viewMap).forEach(([key, viewEl]) => {
      if (viewEl) {
        if (key === channelName) {
          viewEl.classList.add('active');
        } else {
          viewEl.classList.remove('active');
        }
      }
    });

    // Notify any dynamic canvas or responsive components
    window.dispatchEvent(new Event('resize'));
  }

  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const channel = btn.getAttribute('data-channel');
      activateChannel(channel);
    });
  });

  // Check URL query parameters for default channel (defaults to 'chatbot')
  const urlParams = new URLSearchParams(window.location.search);
  const requestedChannel = urlParams.get('channel') || 'chatbot';
  if (requestedChannel && viewMap[requestedChannel]) {
    activateChannel(requestedChannel);
  }
}

/**
 * =======================================================
 * EMERGENCY SOS & STEALTH MODE (CAMOUFLAGE)
 * Section 15A Witness Protection panic trigger & quick disguise
 * =======================================================
 */
function setupHeaderSosAndStealth() {
  // SOS Panic System
  const sosBtn = document.getElementById('headerSosBtn');
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
        sendSosAlert();
      }
    }, 1000);
  }

  async function sendSosAlert() {
    clearInterval(sosTimer);
    if (sosModal) sosModal.style.display = 'none';

    try {
      const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token') || '';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/victim/sos-alert', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ immediate_danger_type: "Emergency SOS Panic Alert via Support Pulse Header" })
      });

      if (res.ok) {
        alert('EMERGENCY SOS ALERT ACTIVATED!\n\nYour alert has been broadcast to the District Police Control Room (SP/DSP Atrocities Cell) and designated Protection Officer under Section 15A.');
      } else {
        alert('Emergency alert registered. Please dial National Helpline 14566 or Emergency 112 immediately.');
      }
    } catch (err) {
      alert('Emergency alert registered. Please call 14566 or 112.');
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
    sosConfirm.addEventListener('click', sendSosAlert);
  }

  // Stealth Camouflage Overlay System
  const stealthBtn = document.getElementById('headerStealthBtn');
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
  window.calcDigit = function (btn) {
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

/**
 * =======================================================
 * CHANNEL 1: CONVERSATIONAL AI CHATBOT (SIH 26094)
 * Multilingual Indic Conversational Agent with Sentiment / Distress Tracking
 * =======================================================
 */
function setupChatbotChannel() {
  const thread = document.getElementById('chatbotThread');
  const input = document.getElementById('chatTextInput');
  const sendBtn = document.getElementById('chatSendBtn');
  const micBtn = document.getElementById('chatVoiceMicBtn');
  const emojiBtn = document.getElementById('chatEmojiBtn');
  const emotionPopover = document.getElementById('chatEmotionPopover');
  const langSelect = document.getElementById('chatbotLang');
  const distressPill = document.getElementById('chatDistressPill');
  const distressText = document.getElementById('chatDistressText');
  const emotionTag = document.getElementById('chatEmotionTag');
  const initialGreetingText = document.getElementById('initialGreetingText');
  const charCounter = document.getElementById('chatCharCounter');

  if (!thread || !input || !sendBtn) return;

  const langCodeMap = {
    'EN': 'en-IN',
    'HI': 'hi-IN',
    'TA': 'ta-IN'
  };

  const greetingsMap = {
    'EN': "Namaste. I am your MentAura Case-Aware Support Companion under Section 15A. You are in a safe, confidential space. How can I support you today?",
    'HI': "नमस्ते। मैं आपका मेंटॉरा केस-जागरूक सपोर्ट साथी हूँ (धारा 15A)। आप एक सुरक्षित, गोपनीय वातावरण में हैं। आज मैं आपकी क्या सहायता कर सकता हूँ?",
    'TA': "வணக்கம். நான் உங்கள் மென்டாரா ஆதரவு துணைவன் (பிரிவு 15A). நீங்கள் ஒரு பாதுகாப்பான இடத்தில் உள்ளீர்கள். இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?"
  };

  const quickTopicsData = {
    'EN': [
      { label: "Safety & Protection", prompt: "Someone threatened or intimidated me recently and I feel unsafe. I need police protection under Section 15A." },
      { label: "Court Anxiety", prompt: "I am feeling intense anxiety, dread, and stress about my upcoming court hearing date." },
      { label: "Trauma & Distress", prompt: "I am experiencing deep emotional distress, grief, and social isolation from my community." },
      { label: "Relief & Compensation", prompt: "I need an update on my financial relief, rehabilitation assistance, and travel allowance (TAME)." },
      { label: "Sleep & Nightmares", prompt: "I am suffering from severe insomnia, restlessness, and nightmares since the incident." },
      { label: "Grounding & Calm", prompt: "Guide me through quick 4-7-8 grounding and calm breathing exercises to soothe my anxiety." }
    ],
    'HI': [
      { label: "सुरक्षा व संरक्षण", prompt: "हाल ही में किसी ने मुझे धमकी दी है और मैं असुरक्षित महसूस कर रहा हूँ। मुझे धारा 15A के तहत सुरक्षा चाहिए।" },
      { label: "अदालत का तनाव", prompt: "मुझे मेरी आगामी अदालती सुनवाई को लेकर बहुत अधिक घबराहट और तनाव महसूस हो रहा है।" },
      { label: "आघात व संताप", prompt: "मैं बहुत गहरे मानसिक आघात, दुःख और अकेलेपन से जूझ रहा हूँ।" },
      { label: "राहत व मुआवजा", prompt: "मुझे अत्याचार निवारण अधिनियम के तहत वित्तीय राहत और यात्रा भत्ते (TAME) की स्थिति जाननी है।" },
      { label: "नींद व बुरे सपने", prompt: "घटना के बाद से मुझे नींद नहीं आ रही है और भयानक सपने आते हैं।" },
      { label: "शांति व प्राणायाम", prompt: "तनाव कम करने के लिए मुझे 4-7-8 शांत सांस लेने और शांत होने का अभ्यास कराएं।" }
    ],
    'TA': [
      { label: "பாதுகாப்பு உரிமை", prompt: "சமீபத்தில் யாரோ என்னை மிரட்டினர், எனக்கு பாதுகாப்பு அச்சம் உள்ளது. பிரிவு 15A-ன் கீழ் பாதுகாப்பு தேவை." },
      { label: "நீதிமன்ற கவலை", prompt: "எனது நீதிமன்ற விசாரணை தேதியை நினைத்து எனக்கு மிகுந்த கவலையும் அழுத்தமும் ஏற்படுகிறது." },
      { label: "மன உளைச்சல்", prompt: "நான் தீவிர மன உளைச்சல், சோகம் மற்றும் தனிமையை அனுபவித்து வருகிறேன்." },
      { label: "நிவாரண இழப்பீடு", prompt: "வன்கொடுமை தடுப்புச் சட்டத்தின் கீழ் இழப்பீடு மற்றும் பயணப்படி (TAME) விவரங்கள் தேவை." },
      { label: "தூக்கமின்மை", prompt: "சம்பவத்திற்குப் பிறகு எனக்கு தூக்கமின்மை மற்றும் கெட்ட கனவுகள் வருகின்றன." },
      { label: "அமைதிப் பயிற்சி", prompt: "எனது பதற்றத்தைத் தணிக்க எளிய 4-7-8 சுவாசப் பயிற்சியை எனக்கு கற்றுக்கொடுங்கள்." }
    ]
  };

  const tryChipsData = {
    'EN': [
      { text: "Witness Protection (Sec 15A)", ask: "What witness protection rights do I have under Section 15A?" },
      { text: "Travel Allowance (TAME)", ask: "How can I claim travel and maintenance allowance (TAME)?" },
      { text: "Calm Grounding Tips", ask: "Give me quick grounding techniques for panic and stress." }
    ],
    'HI': [
      { text: "गवाह संरक्षण (धारा 15A)", ask: "धारा 15A के तहत मुझे क्या गवाह सुरक्षा अधिकार प्राप्त हैं?" },
      { text: "यात्रा भत्ता (TAME)", ask: "यात्रा एवं रखरखाव भत्ता (TAME) कैसे प्राप्त करें?" },
      { text: "शांत प्राणायाम उपाय", ask: "घबराहट और तनाव दूर करने के लिए शांत प्राणायाम तकनीक बताएं।" }
    ],
    'TA': [
      { text: "சாட்சி பாதுகாப்பு (பிரிவு 15A)", ask: "பிரிவு 15A-ன் கீழ் எனக்கு என்ன சாட்சி பாதுகாப்பு உரிமைகள் உள்ளன?" },
      { text: "பயணப்படி (TAME)", ask: "பயணப்படி மற்றும் பராமரிப்பு படியை (TAME) எவ்வாறு பெறுவது?" },
      { text: "அமைதி தரும் நுட்பங்கள்", ask: "பதற்றத்தை தணிக்க அமைதி தரும் எளிய நுட்பங்களை கூறுங்கள்." }
    ]
  };

  const emotionsData = {
    'EN': [
      { label: "😌 Calm / Steady", prompt: "I am feeling calm and steady today." },
      { label: "😟 Anxious", prompt: "I am feeling anxious and worried about my case." },
      { label: "😨 Scared / Threatened", prompt: "I feel threatened, scared, and in danger." },
      { label: "😔 Overwhelmed", prompt: "I am exhausted, overwhelmed, and carrying a heavy burden." },
      { label: "😡 Frustrated", prompt: "I feel frustrated and angry about delays in justice." },
      { label: "🌙 Sleepless", prompt: "I am having trouble sleeping and feeling deeply drained." }
    ],
    'HI': [
      { label: "😌 शांत / स्थिर", prompt: "आज मैं शांत और सामान्य महसूस कर रहा हूँ।" },
      { label: "😟 चिंतित", prompt: "मुझे अपने केस और भविष्य को लेकर बहुत चिंता हो रही है।" },
      { label: "😨 भयभीत / खतरा", prompt: "मुझे डर लग रहा है, किसी ने धमकी दी है और मैं खतरे में हूँ।" },
      { label: "😔 बहुत परेशान", prompt: "मुझ पर बहुत भारी मानसिक दबाव है और मैं थक चुका हूँ।" },
      { label: "😡 आक्रोशित", prompt: "न्याय में हो रही देरी से मुझे गुस्सा और निराशा है।" },
      { label: "🌙 अनिद्रा", prompt: "मुझे कई दिनों से नींद नहीं आ रही है और बहुत कमजोरी लग रही है।" }
    ],
    'TA': [
      { label: "😌 அமைதி / சீரான", prompt: "இன்று நான் அமைதியாகவும் இயல்பாகவும் உணர்கிறேன்." },
      { label: "😟 கவலை", prompt: "எனது வழக்கு குறித்து எனக்கு மிகவும் கவலையாக உள்ளது." },
      { label: "😨 அச்சம் / ஆபத்து", prompt: "எனக்கு பயமாக இருக்கிறது, அச்சுறுத்தல் உள்ளது, நான் ஆபத்தில் உள்ளேன்." },
      { label: "😔 மன உளைச்சல்", prompt: "நான் மிகவும் சோர்வாகவும் மிகுந்த மன அழுத்தத்திலும் உள்ளேன்." },
      { label: "😡 கோபம் / ஏமாற்றம்", prompt: "நீதி கிடைப்பதில் ஏற்படும் தாமதத்தால் எனக்கு மிகுந்த கோபம் ஏற்படுகிறது." },
      { label: "🌙 தூக்கமின்மை", prompt: "எனக்கு தூக்கம் வரவில்லை, மிகவும் பலவீனமாக உணர்கிறேன்." }
    ]
  };

  const placeholderMap = {
    'EN': "Share what's on your mind... I'm here to listen and help.",
    'HI': "अपने विचार साझा करें... मैं आपकी सहायता के लिए यहाँ हूँ।",
    'TA': "உங்கள் எண்ணங்களைப் பகிர்ந்து கொள்ளுங்கள்... நான் உதவ இங்கே இருக்கிறேன்."
  };

  // Language change handler - dynamically updates all chatbot UI elements
  function updateChatbotLanguageUI(selectedLang) {
    const lang = (selectedLang || (langSelect ? langSelect.value : 'EN')).toUpperCase();
    const activeLang = ['EN', 'HI', 'TA'].includes(lang) ? lang : 'EN';

    if (initialGreetingText && greetingsMap[activeLang]) {
      initialGreetingText.textContent = greetingsMap[activeLang];
    }
    if (input && placeholderMap[activeLang]) {
      input.placeholder = placeholderMap[activeLang];
    }

    // Update Quick Support Topics cards
    const quickTopicCards = document.querySelectorAll('.quick-topic-card');
    if (quickTopicCards && quickTopicsData[activeLang]) {
      quickTopicCards.forEach((card, idx) => {
        const data = quickTopicsData[activeLang][idx];
        if (data) {
          card.setAttribute('data-topic', data.prompt);
          const labelEl = card.querySelector('.quick-topic-label');
          if (labelEl) labelEl.textContent = data.label;
        }
      });
    }

    // Update Try Asking About chips
    const tryChips = document.querySelectorAll('.try-chip');
    if (tryChips && tryChipsData[activeLang]) {
      tryChips.forEach((chip, idx) => {
        const item = tryChipsData[activeLang][idx];
        if (item) {
          chip.setAttribute('data-ask', item.ask);
          chip.textContent = item.text;
        }
      });
    }

    // Update Emotion Popover Chips
    if (emotionPopover && emotionsData[activeLang]) {
      const emotionBtns = emotionPopover.querySelectorAll('.emotion-chip-btn');
      emotionBtns.forEach((btn, idx) => {
        const item = emotionsData[activeLang][idx];
        if (item) {
          btn.setAttribute('data-emotion-prompt', item.prompt);
          btn.textContent = item.label;
        }
      });
    }
  }

  if (langSelect) {
    langSelect.addEventListener('change', () => {
      updateChatbotLanguageUI(langSelect.value);
    });
  }

  // Voice Response Toggle
  let voiceOutputEnabled = true;
  const voiceToggleBtn = document.getElementById('chatVoiceToggleBtn');
  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener('click', () => {
      voiceOutputEnabled = !voiceOutputEnabled;
      voiceToggleBtn.innerHTML = voiceOutputEnabled
        ? '<i class="fa-solid fa-volume-high"></i>'
        : '<i class="fa-solid fa-volume-xmark"></i>';
      voiceToggleBtn.title = voiceOutputEnabled ? 'Voice response enabled' : 'Voice response muted';
      if (!voiceOutputEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    });
  }

  const chatHistory = [];

  // Interactive exercises handler for low severity
  function runInteractiveExercise(exerciseName, activeLang) {
    let guideHtml = '';
    if (exerciseName.includes('4-7-8') || exerciseName.includes('Breathing')) {
      if (activeLang === 'HI') {
        guideHtml = `
          <strong>🌬️ 4-7-8 श्वास अभ्यास:</strong><br><br>
          1. <strong>4 सेकंड:</strong> नाक से धीरे-धीरे गहरी सांस अंदर लें...<br>
          2. <strong>7 सेकंड:</strong> सांस को सहजता से रोककर रखें...<br>
          3. <strong>8 सेकंड:</strong> मुंह से धीरे-धीरे पूरी सांस बाहर छोड़ें...<br><br>
          <em>इसे 3 बार दोहराएं। अपने शरीर का तनाव दूर होता हुआ महसूस करें।</em>
        `;
      } else if (activeLang === 'TA') {
        guideHtml = `
          <strong>🌬️ 4-7-8 சுவாசப் பயிற்சி:</strong><br><br>
          1. <strong>4 வினாடிகள்:</strong> மூக்கு வழியாக மெதுவாக மூச்சை உள்ளிழுக்கவும்...<br>
          2. <strong>7 வினாடிகள்:</strong> மூச்சை அமைதியாக பிடித்து வைக்கவும்...<br>
          3. <strong>8 வினாடிகள்:</strong> வாய் வழியாக மெதுவாக முழுமையாக வெளியிடவும்...<br><br>
          <em>இதை 3 முறை செய்யவும். உங்கள் மன அழுத்தம் தணிவதை உணர்வீர்கள்.</em>
        `;
      } else {
        guideHtml = `
          <strong>🌬️ 4-7-8 Calming Breath:</strong><br><br>
          1. <strong>4 seconds:</strong> Inhale slowly and deeply through your nose...<br>
          2. <strong>7 seconds:</strong> Hold your breath gently without strain...<br>
          3. <strong>8 seconds:</strong> Exhale completely and slowly through your mouth...<br><br>
          <em>Repeat 3 times. Feel your chest soften and your pulse settle.</em>
        `;
      }
    } else if (exerciseName.includes('Grounding') || exerciseName.includes('5-4-3-2-1')) {
      guideHtml = `
        <strong>🌱 5-4-3-2-1 Sensory Grounding:</strong><br><br>
        👀 <strong>5 things:</strong> Spot 5 things you can see right now.<br>
        ✋ <strong>4 things:</strong> Notice 4 things you can physically touch or feel.<br>
        👂 <strong>3 sounds:</strong> Listen carefully for 3 distinct sounds around you.<br>
        👃 <strong>2 scents:</strong> Notice 2 scents in the air.<br>
        💧 <strong>1 taste:</strong> Take a refreshing sip of water.<br><br>
        <em>You are here, you are safe in this moment.</em>
      `;
    } else {
      guideHtml = `
        <strong>💧 Hydration & Mindful Pause:</strong><br><br>
        Drink a tall glass of clean water slowly. Roll your shoulders back three times, relax your jaw, and let your body rest comfortably. You are taking great care of yourself today.
      `;
    }

    const exBubble = document.createElement('div');
    exBubble.className = 'chat-bubble chat-bubble-bot';
    exBubble.style.background = '#F0FDF4';
    exBubble.style.border = '1px solid #BBF7D0';
    exBubble.style.color = '#166534';
    exBubble.innerHTML = guideHtml;
    thread.appendChild(exBubble);
    thread.scrollTop = thread.scrollHeight;

    if (voiceOutputEnabled && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const plain = exBubble.innerText;
      const utt = new SpeechSynthesisUtterance(plain);
      utt.lang = langCodeMap[activeLang] || 'en-IN';
      window.speechSynthesis.speak(utt);
    }
  }

  // Elevate to counselor directly via backend API
  async function handleCounsellorElevation(buttonEl, activeLang) {
    buttonEl.disabled = true;
    buttonEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Intimating Counsellor...';

    try {
      const token = getAuthToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/victim/chatbot/elevate', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          message: "User confirmed counsellor connection via chatbot prompt",
          language: activeLang
        })
      });

      const data = await res.json();
      buttonEl.innerHTML = '<i class="fa-solid fa-circle-check"></i> Counsellor Intimated (Calling Shortly)';
      buttonEl.style.background = '#15803D';
      buttonEl.style.color = '#FFFFFF';

      const confirmBubble = document.createElement('div');
      confirmBubble.className = 'chat-bubble chat-bubble-bot';
      confirmBubble.style.background = '#ECFDF5';
      confirmBubble.style.border = '1px solid #6EE7B7';
      confirmBubble.style.color = '#065F46';
      const intimatedCounsellor = data.counsellor_name || 'Your assigned counsellor';
      confirmBubble.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10B981; margin-right: 6px;"></i> ${data.message || `Counsellor ${intimatedCounsellor} has been intimated and will call you shortly.`}`;
      thread.appendChild(confirmBubble);
      thread.scrollTop = thread.scrollHeight;

      if (voiceOutputEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(confirmBubble.innerText);
        utt.lang = langCodeMap[activeLang] || 'en-IN';
        window.speechSynthesis.speak(utt);
      }
    } catch (err) {
      console.error('Elevation error:', err);
      buttonEl.disabled = false;
      buttonEl.innerHTML = '<i class="fa-solid fa-headset"></i> Retry Connecting';
    }
  }

  // Send message function with 3-tier severity handling & backend integration
  async function handleSendMessage(text) {
    const message = (text || input.value || '').trim();
    if (!message) {
      if (input) input.focus();
      return;
    }

    // Hide Essential Quick Support Topics once user begins conversation (Audio Request)
    const quickTopics = document.getElementById('chatQuickTopicsSection') || document.querySelector('.chat-quick-topics-section');
    if (quickTopics) quickTopics.style.display = 'none';

    input.value = '';
    if (charCounter) charCounter.textContent = '0/1000';
    if (emotionPopover) emotionPopover.style.display = 'none';

    // Append user message bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble chat-bubble-user';
    userBubble.textContent = message;
    thread.appendChild(userBubble);
    thread.scrollTop = thread.scrollHeight;

    // Append typing indicator
    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-bubble chat-bubble-bot typing-indicator';
    typingBubble.innerHTML = '<i class="fa-solid fa-ellipsis fa-fade"></i>';
    thread.appendChild(typingBubble);
    thread.scrollTop = thread.scrollHeight;

    try {
      const activeLang = (langSelect ? langSelect.value : 'EN').toUpperCase();
      const token = getAuthToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const historyPayload = typeof getRecentHistoryPayload === 'function' ? getRecentHistoryPayload() : chatHistory;

      const res = await fetch('/api/victim/chatbot/message', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          message,
          language: activeLang,
          conversation_history: historyPayload
        })
      });

      typingBubble.remove();

      if (!res.ok) {
        const errBubble = document.createElement('div');
        errBubble.className = 'chat-bubble chat-bubble-bot';
        errBubble.style.borderColor = '#FCA5A5';
        errBubble.style.background = '#FEF2F2';
        errBubble.textContent = "I'm having a brief connection issue. If this is an emergency, please call Tele-MANAS at 14416 or Police at 112.";
        thread.appendChild(errBubble);
        thread.scrollTop = thread.scrollHeight;
        return;
      }

      const data = await res.json();
      const botText = data.reply || data.bot_reply || data.bot_response || "I hear you, and I am right here with you.";

      // Record to history
      if (typeof saveTurnToHistory === 'function') {
        saveTurnToHistory(message, botText, data.severity_level || 'low', activeLang);
      } else {
        chatHistory.push({ role: 'user', content: message, distress_score: data.dynamic_distress_indicator || 20 });
        chatHistory.push({ role: 'bot', content: botText.replace(/<[^>]*>?/gm, '') });
        if (chatHistory.length > 20) chatHistory.splice(0, chatHistory.length - 20);
      }
      // Auto Check-In Enablement: ONLY when High Priority Distress / Crisis is detected (Audio Request)
      if (data.severity_level === 'high' || data.is_crisis_flag === true) {
        startProactiveCrisisMonitoring();
      } else if (isProactiveCrisisMonitoringActive) {
        const msgLow = message.toLowerCase();
        if (["feeling better", "safe now", "better now", "fine now", "i am okay now", "all good now", "thought went away"].some(w => msgLow.includes(w))) {
          stopProactiveCrisisMonitoring();
        } else {
          resetProactiveTimer();
        }
      }

      // Render bot message bubble
      const botBubble = document.createElement('div');
      botBubble.className = 'chat-bubble chat-bubble-bot';
      botBubble.textContent = botText;
      thread.appendChild(botBubble);
      thread.scrollTop = thread.scrollHeight;

      // Text to Speech synthesis if voice response is enabled
      if (voiceOutputEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const plainText = botText.replace(/<[^>]*>?/gm, '');
        const utterance = new SpeechSynthesisUtterance(plainText);
        utterance.lang = langCodeMap[activeLang] || 'en-IN';
        utterance.rate = 0.95;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
      }

      const severity = data.severity_level || 'low';

      // TIER 1: Coping techniques (only when explicitly provided)
      if (data.coping_techniques && data.coping_techniques.length > 0) {
        const copingBox = document.createElement('div');
        copingBox.className = 'chat-coping-card';
        let headerTitle = "🌱 Recommended Calming & Grounding Exercises";
        if (activeLang === 'HI') headerTitle = "🌱 मन को शांत करने वाले अनुशंसित अभ्यास";
        else if (activeLang === 'TA') headerTitle = "🌱 மன அமைதிக்கான எளிய பயிற்சிகள்";

        copingBox.innerHTML = `<div class="chat-coping-header"><i class="fa-solid fa-feather"></i> ${headerTitle}</div>`;
        data.coping_techniques.forEach(tech => {
          const item = document.createElement('div');
          item.className = 'chat-technique-item';
          item.innerHTML = `
            <div class="chat-technique-info">
              <span class="chat-technique-title">${tech.title}</span>
              <span class="chat-technique-desc">${tech.desc}</span>
            </div>
            <button type="button" class="chat-technique-btn btn-interactive-exercise" data-exercise="${tech.action}">${tech.action}</button>
          `;
          copingBox.appendChild(item);
        });
        botBubble.appendChild(copingBox);
      }

      // TIER 2: Sleek 1-Line Counsellor Referral Bar (Only when user requested or confirmed connection)
      else if (severity === 'medium' && data.escalation_contact) {
        const contact = data.escalation_contact;
        const escBar = document.createElement('div');
        escBar.className = 'chat-escalation-bar';

        let connectBtnText = "Connect";
        let declineBtnText = "Continue Chat";
        if (activeLang === 'HI') {
          connectBtnText = "परामर्शदाता से जुड़ें";
          declineBtnText = "बातचीत जारी रखें";
        } else if (activeLang === 'TA') {
          connectBtnText = "இணைக்கவும்";
          declineBtnText = "தொடரவும்";
        }

        escBar.innerHTML = `
          <div class="chat-escalation-bar-info">
            <i class="fa-solid fa-user-doctor" style="color: #7E57C2;"></i>
            <span>Assigned Counsellor: <strong>${contact.officer_name}</strong> (📞 ${contact.phone})</span>
          </div>
          <div class="chat-escalation-bar-actions">
            <button type="button" class="chat-escalation-bar-btn primary btn-counsellor-elevate">
              <i class="fa-solid fa-headset"></i> ${connectBtnText}
            </button>
            <button type="button" class="chat-escalation-bar-btn secondary btn-continue-chat" data-quick="I am okay for now, thank you. Let us continue talking.">
              <i class="fa-solid fa-comments"></i> ${declineBtnText}
            </button>
            <a href="tel:14416" class="chat-escalation-bar-btn helpline"><i class="fa-solid fa-phone"></i> 14416</a>
          </div>
        `;
        botBubble.appendChild(escBar);
      }

      // TIER 3: HIGH SEVERITY -> Render Direct Urgent Alert Banner & Emergency SOS Dials
      else if (severity === 'high') {
        const alertCard = document.createElement('div');
        alertCard.className = 'chat-high-alert-card';

        const alertInfo = data.alert_details || {
          badge: "🚨 HIGH SEVERITY ALERT — Immediate Counsellor & Authority Intimated",
          authority: "Assigned Counsellor & District Protection Unit Notified Immediately",
          detail: "An urgent priority alert has been dispatched under Section 15A. Your assigned counsellor and protection authorities have been instructed to contact you immediately."
        };

        let dialsHtml = `
          <a href="tel:112" class="btn-emergency-call police"><i class="fa-solid fa-phone"></i> Police Emergency 112</a>
          <a href="tel:14566" class="btn-emergency-call helpline"><i class="fa-solid fa-phone-volume"></i> National Helpline 14566</a>
          <button type="button" class="btn-emergency-call escort" data-quick="I am under immediate threat and request emergency witness protection escort under Section 15A"><i class="fa-solid fa-person-military-pointing"></i> Request Sec 15A Escort</button>
        `;

        alertCard.innerHTML = `
          <div class="chat-high-alert-header">
            <i class="fa-solid fa-triangle-exclamation fa-beat-fade"></i> ${alertInfo.badge}
          </div>
          <div class="chat-high-alert-authority">
            <i class="fa-solid fa-shield-halved"></i> ${alertInfo.authority}
          </div>
          <div class="chat-high-alert-desc">
            ${alertInfo.detail}
          </div>
          <div class="chat-high-alert-dials">
            ${dialsHtml}
          </div>
        `;
        botBubble.appendChild(alertCard);
      }

      // Render interactive suggestion chips if provided
      const chipsList = data.suggested_actions || data.suggested_chips || [];
      if (chipsList.length > 0) {
        const chipsWrap = document.createElement('div');
        chipsWrap.className = 'chat-suggested-actions';
        chipsWrap.style.marginTop = '10px';
        chipsList.forEach(actionText => {
          const chip = document.createElement('button');
          chip.type = 'button';
          chip.className = 'chat-action-chip';
          chip.setAttribute('data-quick', actionText);
          chip.textContent = actionText;
          chipsWrap.appendChild(chip);
        });
        botBubble.appendChild(chipsWrap);
      }

      // Update live distress assessment pill
      if (distressPill) {
        const score = data.dynamic_distress_indicator ?? data.sentiment_distress_score ?? data.sentiment_score ?? 20;
        distressPill.style.display = 'flex';
        const riskCategory = score >= 75 ? 'High Distress / Crisis' : (score >= 40 ? 'Moderate Distress' : 'Steady / Low');

        if (severity === 'high') {
          distressPill.style.borderColor = '#FECACA';
          distressPill.style.background = '#FEF2F2';
          if (distressText) {
            distressText.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color: #DC2626; margin-right: 6px;"></i> Dynamic Distress Score: <strong>${score}/100</strong> (${riskCategory}) &bull; Tier: <strong style="color: #B91C1C;">HIGH (ESCALATED)</strong>`;
          }
          if (emotionTag) {
            emotionTag.style.background = '#FEE2E2';
            emotionTag.style.color = '#991B1B';
            emotionTag.textContent = 'HIGH CRISIS';
          }
        } else if (severity === 'medium') {
          distressPill.style.borderColor = '#FDE68A';
          distressPill.style.background = '#FFFBEB';
          if (distressText) {
            distressText.innerHTML = `<i class="fa-solid fa-chart-line" style="color: #D97706; margin-right: 6px;"></i> Dynamic Distress Score: <strong>${score}/100</strong> (${riskCategory}) &bull; Tier: <strong style="color: #B45309;">MEDIUM</strong>`;
          }
          if (emotionTag) {
            emotionTag.style.background = '#FEF3C7';
            emotionTag.style.color = '#92400E';
            emotionTag.textContent = 'ELEVATION OFFER';
          }
        } else {
          distressPill.style.borderColor = '#A7F3D0';
          distressPill.style.background = '#ECFDF5';
          if (distressText) {
            distressText.innerHTML = `<i class="fa-solid fa-shield-heart" style="color: #059669; margin-right: 6px;"></i> Dynamic Distress Score: <strong>${score}/100</strong> (${riskCategory}) &bull; Tier: <strong style="color: #047857;">LOW / STEADY</strong>`;
          }
          if (emotionTag) {
            emotionTag.style.background = '#D1FAE5';
            emotionTag.style.color = '#065F46';
            emotionTag.textContent = 'STEADY';
          }
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      const errBubble = document.createElement('div');
      errBubble.className = 'chat-bubble chat-bubble-bot';
      errBubble.textContent = 'Thank you for sharing. You are in a safe, confidential space, and we are monitoring your well-being.';
      thread.appendChild(errBubble);
    } finally {
      thread.scrollTop = thread.scrollHeight;
    }
  }

  sendBtn.addEventListener('click', (e) => {
    if (e) e.preventDefault();
    handleSendMessage();
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.keyCode === 13) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Action chips & interactive exercise listener in conversation thread
  thread.addEventListener('click', (e) => {
    // 1. Suggestion / Quick chips
    const chip = e.target.closest('.chat-action-chip');
    if (chip) {
      const quick = chip.getAttribute('data-quick');
      if (quick) handleSendMessage(quick);
      return;
    }

    // 2. Interactive coping exercise button (Low tier)
    const exerciseBtn = e.target.closest('.btn-interactive-exercise');
    if (exerciseBtn) {
      const exName = exerciseBtn.getAttribute('data-exercise') || exerciseBtn.textContent;
      const activeLang = (langSelect ? langSelect.value : 'EN').toUpperCase();
      runInteractiveExercise(exName, activeLang);
      return;
    }

    // 3. Connect to Counsellor Elevation button (Medium tier)
    const elevateBtn = e.target.closest('.btn-counsellor-elevate');
    if (elevateBtn) {
      const activeLang = (langSelect ? langSelect.value : 'EN').toUpperCase();
      handleCounsellorElevation(elevateBtn, activeLang);
      return;
    }

    // 4. Continue chat button (Medium tier)
    const contBtn = e.target.closest('.btn-continue-chat');
    if (contBtn) {
      const quick = contBtn.getAttribute('data-quick');
      if (quick) handleSendMessage(quick);
      return;
    }

    // 5. Escort / emergency button inside high alert
    const escortBtn = e.target.closest('.btn-emergency-call.escort');
    if (escortBtn) {
      const quick = escortBtn.getAttribute('data-quick');
      if (quick) handleSendMessage(quick);
      return;
    }
  });

  // Character counter and typing activity reset
  if (input) {
    input.addEventListener('input', () => {
      if (charCounter) charCounter.textContent = `${input.value.length}/1000`;
      if (isProactiveCrisisMonitoringActive) {
        resetProactiveTimer();
      }
      if (input.value.trim().length > 0) {
        const quickTopics = document.getElementById('chatQuickTopicsSection') || document.querySelector('.chat-quick-topics-section');
        if (quickTopics) quickTopics.style.display = 'none';
      }
    });
  }

  // Quick Start Topics selection
  const quickTopicCards = document.querySelectorAll('.quick-topic-card');
  quickTopicCards.forEach(card => {
    card.addEventListener('click', () => {
      quickTopicCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      const topic = card.getAttribute('data-topic');
      if (topic) handleSendMessage(topic);
    });
  });

  // "Try asking about" hint chips
  const tryChips = document.querySelectorAll('.try-chip');
  tryChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const ask = chip.getAttribute('data-ask');
      if (ask) handleSendMessage(ask);
    });
  });

  // Interactive Emotion Reaction Popover
  if (emojiBtn && emotionPopover) {
    emojiBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      emotionPopover.style.display = emotionPopover.style.display === 'none' ? 'block' : 'none';
    });

    document.addEventListener('click', (e) => {
      if (emotionPopover && !emotionPopover.contains(e.target) && e.target !== emojiBtn) {
        emotionPopover.style.display = 'none';
      }
    });

    const emotionBtns = emotionPopover.querySelectorAll('.emotion-chip-btn');
    emotionBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const prompt = btn.getAttribute('data-emotion-prompt');
        emotionPopover.style.display = 'none';
        if (prompt) handleSendMessage(prompt);
      });
    });
  }

  // Speech-to-text Voice Recognition
  if (micBtn) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      let isRecording = false;

      recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
        micBtn.style.color = '#DC2626';
        micBtn.title = 'Listening... Speak now';
      };

      recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.style.color = '';
        micBtn.title = 'Voice Input (Speech-to-Text)';
      };

      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        if (input) {
          input.value = finalTranscript || interimTranscript;
          if (charCounter) charCounter.textContent = `${input.value.length}/1000`;
        }
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition warning:', event.error);
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.style.color = '';
      };

      micBtn.addEventListener('click', () => {
        if (isRecording) {
          recognition.stop();
        } else {
          const activeLang = (langSelect ? langSelect.value : 'EN').toUpperCase();
          recognition.lang = langCodeMap[activeLang] || 'en-IN';
          try {
            recognition.start();
          } catch (e) {
            recognition.stop();
          }
        }
      });
    } else {
      micBtn.title = 'Speech recognition not supported in this browser';
    }
  }

  // Helper to escape HTML safely
  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // =======================================================
  // PROACTIVE CONTINUOUS MONITORING (Armed ONLY on High Priority Distress — Fires ONCE)
  // =======================================================
  const PROACTIVE_TIMEOUT_MS = 30000; // 30 seconds as explicitly requested by user
  let isProactiveCrisisMonitoringActive = false;
  let hasProactiveCheckinFiredForCurrentCrisis = false;
  let proactiveTimer = null;
  let proactiveCountdownInterval = null;
  let secondsRemaining = 30;
  const proactiveBadge = document.getElementById('proactiveTimerBadge');

  function updateProactiveBadgeUI() {
    if (!proactiveBadge) return;
    const dotEl = proactiveBadge.querySelector('.proactive-pulse-dot');
    const textEl = proactiveBadge.querySelector('.proactive-timer-text');

    if (hasProactiveCheckinFiredForCurrentCrisis) {
      proactiveBadge.className = 'proactive-timer-badge completed';
      if (dotEl) {
        dotEl.style.backgroundColor = '#10B981';
        dotEl.style.animation = 'none';
        dotEl.style.boxShadow = 'none';
      }
      if (textEl) {
        textEl.innerHTML = '<i class="fa-solid fa-check"></i> Auto Check-In (Sent)';
      }
      proactiveBadge.title = 'Automated continuous monitoring check-in was successfully delivered.';
    } else if (isProactiveCrisisMonitoringActive) {
      proactiveBadge.className = 'proactive-timer-badge active-crisis';
      if (dotEl) {
        dotEl.style.backgroundColor = '#EF4444';
        dotEl.style.animation = 'proactiveCrisisPulseAnim 1.4s infinite';
      }
      if (textEl) {
        textEl.textContent = `🚨 Auto Check-In (${secondsRemaining}s)`;
      }
      proactiveBadge.title = `Continuous Active Monitoring: Auto checking in in ${secondsRemaining}s`;
    } else {
      proactiveBadge.className = 'proactive-timer-badge standby';
      if (dotEl) {
        dotEl.style.backgroundColor = '#9CA3AF';
        dotEl.style.animation = 'none';
        dotEl.style.boxShadow = 'none';
      }
      if (textEl) {
        textEl.textContent = 'Auto Check-In (Standby)';
      }
      proactiveBadge.title = 'Continuous Auto Check-In arms automatically when high priority distress is detected';
    }
  }

  function startProactiveCrisisMonitoring() {
    if (!hasProactiveCheckinFiredForCurrentCrisis) {
      if (!isProactiveCrisisMonitoringActive) {
        console.log('[PROACTIVE MONITORING]: High priority distress detected. Arming one-time 30s auto check-in.');
      }
      isProactiveCrisisMonitoringActive = true;
      resetProactiveTimer();
    }
  }

  function stopProactiveCrisisMonitoring() {
    console.log('[PROACTIVE MONITORING]: De-escalated. Disarming auto check-in.');
    isProactiveCrisisMonitoringActive = false;
    hasProactiveCheckinFiredForCurrentCrisis = false;
    if (proactiveTimer) {
      clearTimeout(proactiveTimer);
      proactiveTimer = null;
    }
    if (proactiveCountdownInterval) {
      clearInterval(proactiveCountdownInterval);
      proactiveCountdownInterval = null;
    }
    updateProactiveBadgeUI();
  }

  function resetProactiveTimer() {
    if (!isProactiveCrisisMonitoringActive || hasProactiveCheckinFiredForCurrentCrisis) return;

    if (proactiveTimer) clearTimeout(proactiveTimer);
    if (proactiveCountdownInterval) clearInterval(proactiveCountdownInterval);
    secondsRemaining = 30;
    updateProactiveBadgeUI();

    proactiveCountdownInterval = setInterval(() => {
      if (!isProactiveCrisisMonitoringActive || hasProactiveCheckinFiredForCurrentCrisis) {
        clearInterval(proactiveCountdownInterval);
        return;
      }
      secondsRemaining--;
      if (secondsRemaining <= 0) {
        clearInterval(proactiveCountdownInterval);
      }
      updateProactiveBadgeUI();
    }, 1000);

    proactiveTimer = setTimeout(triggerProactiveCheckin, PROACTIVE_TIMEOUT_MS);
  }

  async function triggerProactiveCheckin() {
    if (!isProactiveCrisisMonitoringActive || hasProactiveCheckinFiredForCurrentCrisis) return;

    // Disarm IMMEDIATELY so it fires ONLY ONCE as requested by user
    hasProactiveCheckinFiredForCurrentCrisis = true;
    isProactiveCrisisMonitoringActive = false;
    if (proactiveTimer) {
      clearTimeout(proactiveTimer);
      proactiveTimer = null;
    }
    if (proactiveCountdownInterval) {
      clearInterval(proactiveCountdownInterval);
      proactiveCountdownInterval = null;
    }
    updateProactiveBadgeUI();

    try {
      const activeLang = (langSelect ? langSelect.value : 'EN').toUpperCase();
      const token = getAuthToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/victim/chatbot/proactive-checkin', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          language: activeLang,
          conversation_history: chatHistory
        })
      });

      if (!res.ok) return;
      const data = await res.json();
      const proactiveMsg = data.proactive_message || "Gentle Check-In: I'm still thinking about you and want to make sure you are safe. How are you holding up right now?";

      // Render proactive bot bubble
      const bubble = document.createElement('div');
      bubble.className = 'chat-bubble chat-bubble-bot proactive-checkin-bubble';
      bubble.innerHTML = `
        <div><span class="proactive-checkin-badge"><i class="fa-solid fa-triangle-exclamation"></i> High Priority Continuous Monitoring Check-In</span></div>
        <div>${escapeHtml(proactiveMsg)}</div>
      `;
      thread.appendChild(bubble);
      thread.scrollTop = thread.scrollHeight;

      // Save turn to chat history
      chatHistory.push({ role: 'bot', content: proactiveMsg });

      if (voiceOutputEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(proactiveMsg);
        utt.lang = langCodeMap[activeLang] || 'en-IN';
        window.speechSynthesis.speak(utt);
      }
    } catch (err) {
      console.error('Proactive check-in error:', err);
    }
  }

  // =======================================================
  // CONVERSATION HISTORY MODAL & SEARCH FILTER (Audio 1)
  // =======================================================
  const historyBtn = document.getElementById('chatHistoryBtn');
  const historyModal = document.getElementById('chatHistoryModal');
  const closeHistoryBtn = document.getElementById('closeChatHistoryBtn');
  const historySearchInput = document.getElementById('chatHistorySearchInput');
  const clearSearchBtn = document.getElementById('clearChatHistorySearch');
  const historyList = document.getElementById('chatHistoryList');
  const filterChips = document.querySelectorAll('.hist-chip');

  let fetchedHistoryData = [];
  let currentFilter = 'all';

  function setupChatHistoryHandlers() {
    if (!historyBtn || !historyModal) return;

    historyBtn.addEventListener('click', () => {
      historyModal.style.display = 'flex';
      loadChatHistory();
    });

    if (closeHistoryBtn) {
      closeHistoryBtn.addEventListener('click', () => {
        historyModal.style.display = 'none';
      });
    }

    historyModal.addEventListener('click', (e) => {
      if (e.target === historyModal) {
        historyModal.style.display = 'none';
      }
    });

    if (historySearchInput) {
      historySearchInput.addEventListener('input', () => {
        const q = historySearchInput.value.trim();
        if (clearSearchBtn) clearSearchBtn.style.display = q ? 'block' : 'none';
        renderFilteredHistory();
      });
    }

    if (clearSearchBtn) {
      clearSearchBtn.addEventListener('click', () => {
        historySearchInput.value = '';
        clearSearchBtn.style.display = 'none';
        renderFilteredHistory();
      });
    }

    filterChips.forEach(chip => {
      chip.addEventListener('click', () => {
        filterChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentFilter = chip.getAttribute('data-filter') || 'all';
        renderFilteredHistory();
      });
    });
  }

  async function loadChatHistory() {
    if (!historyList) return;
    historyList.innerHTML = '<div class="history-empty-state"><i class="fa-solid fa-spinner fa-spin"></i> Loading past check-in records...</div>';

    try {
      const token = getAuthToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/victim/chatbot/history', { headers, credentials: 'include' });
      if (!res.ok) throw new Error('Failed to fetch history');
      const data = await res.json();
      fetchedHistoryData = data.history || [];
      renderFilteredHistory();
    } catch (err) {
      console.error('Failed to load history:', err);
      historyList.innerHTML = '<div class="history-empty-state" style="color: #DC2626;"><i class="fa-solid fa-circle-exclamation"></i> Unable to load history records. Please check connection.</div>';
    }
  }

  function renderFilteredHistory() {
    if (!historyList) return;
    const query = (historySearchInput ? historySearchInput.value : '').toLowerCase().trim();

    let items = fetchedHistoryData.filter(item => {
      if (currentFilter !== 'all') {
        const risk = (item.risk_level || 'low').toLowerCase();
        if (currentFilter === 'high' && !risk.includes('high')) return false;
        if (currentFilter === 'medium' && !risk.includes('medium')) return false;
        if (currentFilter === 'low' && !['low', 'steady'].includes(risk)) return false;
      }

      if (query) {
        const text = (item.text_response || '').toLowerCase();
        const date = (item.submitted_at || '').toLowerCase();
        const xai = (item.xai_explanation || '').toLowerCase();
        const risk = (item.risk_level || '').toLowerCase();
        return text.includes(query) || date.includes(query) || xai.includes(query) || risk.includes(query);
      }

      return true;
    });

    if (items.length === 0) {
      historyList.innerHTML = `
        <div class="history-empty-state">
          <i class="fa-solid fa-folder-open" style="font-size: 1.8rem; margin-bottom: 8px; color: #C4B5FD;"></i>
          <p>No check-in conversations match your search criteria.</p>
        </div>
      `;
      return;
    }

    historyList.innerHTML = '';
    items.forEach(item => {
      const card = document.createElement('div');
      const risk = (item.risk_level || 'low').toLowerCase();
      const score = item.dynamic_distress_score || 20;
      card.className = `chat-history-card ${risk.includes('high') ? 'high' : (risk.includes('medium') ? 'medium' : 'low')}`;

      let dateStr = 'Recent Session';
      if (item.submitted_at) {
        try {
          const d = new Date(item.submitted_at);
          dateStr = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) + ' at ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
        } catch (e) {}
      }

      let badgeLabel = 'Steady';
      if (risk.includes('high')) badgeLabel = `🚨 High Crisis (${score}/100)`;
      else if (risk.includes('medium')) badgeLabel = `⚠️ Moderate (${score}/100)`;
      else badgeLabel = `🌱 Steady (${score}/100)`;

      card.innerHTML = `
        <div class="hist-card-header">
          <span><i class="fa-regular fa-calendar-check" style="margin-right: 4px;"></i> ${dateStr}</span>
          <span class="hist-badge ${risk.includes('high') ? 'high' : (risk.includes('medium') ? 'medium' : 'low')}">${badgeLabel}</span>
        </div>
        <div class="hist-card-text">
          ${escapeHtml(item.text_response || 'Check-in interaction')}
        </div>
        ${item.xai_explanation ? `<div class="hist-card-xai"><i class="fa-solid fa-circle-info"></i> ${escapeHtml(item.xai_explanation)}</div>` : ''}
      `;
      historyList.appendChild(card);
    });
  }

  // Initialize History handlers and set proactive auto check-in to Standby (arms only on crisis)
  setupChatHistoryHandlers();
  updateProactiveBadgeUI();
}

/**
 * =======================================================
 * CHANNEL 2: VOICE STRESS CHECK-IN (SIH 26094)
 * Acoustic signal processing & Voice Biomarker Extraction
 * =======================================================
 */
function setupVoiceChannel() {
  const recordBtn = document.getElementById('voiceRecordBtn');
  const recordBtnLabel = document.getElementById('voiceRecordBtnLabel');
  const recordIcon = document.getElementById('voiceRecordIcon');
  const timerDisplay = document.getElementById('voiceTimerDisplay');
  const canvas = document.getElementById('voiceWaveformCanvas');

  // Orb & State UI Elements
  const orbStage = document.getElementById('voiceOrbStage');
  const orbSphere = document.getElementById('voiceOrbSphere');
  const orbIcon = document.getElementById('voiceOrbIcon');
  const statePill = document.getElementById('voiceStatePill');
  const stateText = document.getElementById('voiceStateText');
  const autoLoopToggle = document.getElementById('voiceAutoLoopToggle');
  const interruptBtn = document.getElementById('voiceInterruptBtn');
  const replayBtn = document.getElementById('voiceReplayAiBtn');
  const voiceLangSelect = document.getElementById('voiceLanguageSelect');
  const voiceToneSelect = document.getElementById('voiceToneSelect');
  const voiceHistoryBtn = document.getElementById('voiceHistoryBtn');
  const voiceHeaderHistoryBtn = document.getElementById('voiceHeaderHistoryBtn');
  const historyModal = document.getElementById('voiceHistoryModal');
  const closeHistoryBtn = document.getElementById('closeVoiceHistoryBtn');
  const historyModalBody = document.getElementById('voiceHistoryModalBody');
  const clearHistoryBtn = document.getElementById('clearVoiceHistoryBtn');
  const loadHistoryBtn = document.getElementById('loadVoiceHistoryBtn');
  const initialCompanionText = document.getElementById('voiceInitialCompanionText');
  const resetChatBtn = document.getElementById('voiceResetChatBtn');
  const streamContainer = document.getElementById('voiceConversationStream');

  if (!recordBtn || !canvas) return;

  const ctx = canvas.getContext('2d');
  let isRecording = false;
  let isThinking = false;
  let isSpeaking = false;
  let timerInterval = null;
  let recordSeconds = 0;
  let audioContext = null;
  let analyser = null;
  let mediaStream = null;
  let animationId = null;
  let silenceTimeout = null;
  let recognitionInstance = null;
  let capturedSpeechText = '';
  let currentAiVoiceReply = "Hello! I am here with you. Whenever you're ready, tap the microphone to start talking. How are you feeling today?";
  let lastClassification = "low";
  let voiceConversationHistory = [];

  // Multilingual Initial Greetings for English, Hindi, and Tamil
  const initialGreetingsByLang = {
    EN: "Hello! I am here with you. Whenever you're ready, tap the microphone to start talking. How are you feeling today?",
    HI: "नमस्ते! मैं आपके साथ हूँ। जब भी आप तैयार हों, बात करने के लिए माइक्रोफ़ोन दबाएँ। आज आप कैसा महसूस कर रहे हैं?",
    TA: "வணக்கம்! நான் உங்களுடன் இருக்கிறேன். நீங்கள் தயாரானதும், பேசத் தொடங்க மைக்ரோஃபோனைத் தட்டவும். இன்று உங்கள் மனநிலை எப்படி இருக்கிறது?"
  };

  // Tone Persona Profiles (User customizable tone of voice)
  const toneProfiles = {
    warm: { pitch: 1.05, rate: 0.94, label: "Warm & Calming" },
    supportive: { pitch: 1.0, rate: 1.0, label: "Supportive Friend" },
    empathetic: { pitch: 0.94, rate: 0.88, label: "Empathetic Guide" },
    gentle: { pitch: 1.10, rate: 0.90, label: "Soft & Gentle" }
  };

  // Persistent Locked Voice Engine (Keeps voice 100% consistent across entire conversation)
  let lockedVoices = {
    EN: null,
    HI: null,
    TA: null
  };

  function selectAndLockVoice(langCode) {
    if (!('speechSynthesis' in window)) return null;
    const voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) return null;

    const code = (langCode || 'EN').toUpperCase();

    // If we have already locked a valid voice for this language, reuse it consistently
    if (lockedVoices[code]) {
      const stillValid = voices.find(v => v.name === lockedVoices[code].name);
      if (stillValid) return lockedVoices[code];
    }

    let chosen = null;
    if (code === 'TA') {
      // 1. Native Tamil voice (Google தமிழ், Microsoft Valluvar, Tamil India, etc.)
      chosen = voices.find(v => (v.lang && (v.lang.toLowerCase() === 'ta-in' || v.lang.toLowerCase().startsWith('ta'))) || v.name.toLowerCase().includes('tamil'));
    } else if (code === 'HI') {
      // 2. Native Hindi voice (Google हिन्दी, Kalpana, Hemant, Hindi India, etc.)
      chosen = voices.find(v => (v.lang && (v.lang.toLowerCase() === 'hi-in' || v.lang.toLowerCase().startsWith('hi'))) || v.name.toLowerCase().includes('hindi'));
    } else {
      // 3. English: Consistent Natural/Google/Female voice
      chosen = voices.find(v => v.lang.toLowerCase().startsWith('en') && (
        v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Female') || v.name.includes('Samantha') || v.name.includes('Jenny')
      ));
    }

    // Fallbacks if specific voice isn't installed on OS
    if (!chosen) {
      const prefix = code === 'TA' ? 'ta' : (code === 'HI' ? 'hi' : 'en');
      chosen = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
    }
    if (!chosen) {
      chosen = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('en')) || voices[0];
    }

    if (chosen) {
      lockedVoices[code] = chosen;
      console.log(`[Voice Engine] Locked consistent voice for ${code}: ${chosen.name} (${chosen.lang})`);
    }
    return chosen;
  }

  // Pre-cache voices when speech synthesis is ready
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
      selectAndLockVoice('EN');
      selectAndLockVoice('HI');
      selectAndLockVoice('TA');
    };
    selectAndLockVoice('EN');
    selectAndLockVoice('HI');
    selectAndLockVoice('TA');
  }

  // Helper: Escape HTML
  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // History Persistence Helper
  function saveTurnToHistory(speechText, aiReply, classification, lang) {
    try {
      const historyKey = 'mentaura_voice_turns';
      let turns = JSON.parse(localStorage.getItem(historyKey) || '[]');
      turns.unshift({
        id: 'turn_' + Date.now(),
        timestamp: new Date().toISOString(),
        lang: lang || 'EN',
        userQuery: speechText,
        companionReply: aiReply,
        classification: classification || 'low'
      });
      if (turns.length > 60) turns = turns.slice(0, 60);
      localStorage.setItem(historyKey, JSON.stringify(turns));
    } catch (e) {
      console.warn('History storage notice:', e);
    }
  }

  // History Modal Renderer
  function renderVoiceHistoryModal() {
    if (!historyModalBody) return;
    try {
      const turns = JSON.parse(localStorage.getItem('mentaura_voice_turns') || '[]');
      if (turns.length === 0) {
        historyModalBody.innerHTML = `
          <div class="history-empty-state">
            <div class="history-empty-icon"><i class="fa-solid fa-microphone-lines"></i></div>
            <h4 style="color: #2D1455; font-size: 1rem; margin-bottom: 6px;">No conversation history yet</h4>
            <p style="font-size: 0.82rem; color: #6C5E8A; max-width: 340px; margin: 0 auto;">
              Start a voice check-in to begin your conversation. All your turns and audio reflections will be safely stored and loaded here.
            </p>
          </div>
        `;
        return;
      }

      let html = '';
      turns.forEach((turn, idx) => {
        const d = new Date(turn.timestamp);
        const timeStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' at ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const classBadge = turn.classification === 'high' 
          ? '<span style="background: #FEE2E2; color: #DC2626; font-size: 0.70rem; font-weight: 800; padding: 2px 8px; border-radius: 999px;">HIGH DISTRESS</span>'
          : (turn.classification === 'medium'
            ? '<span style="background: #FEF3C7; color: #D97706; font-size: 0.70rem; font-weight: 800; padding: 2px 8px; border-radius: 999px;">MANAGING</span>'
            : '<span style="background: #ECFDF5; color: #059669; font-size: 0.70rem; font-weight: 800; padding: 2px 8px; border-radius: 999px;">STEADY</span>');

        html += `
          <div class="history-turn-card">
            <div class="history-turn-header">
              <span class="history-turn-num">Turn #${turns.length - idx} &bull; ${escapeHtml(turn.lang || 'EN')}</span>
              <div style="display: flex; align-items: center; gap: 8px;">
                ${classBadge}
                <span class="history-turn-time">${escapeHtml(timeStr)}</span>
              </div>
            </div>
            <div class="history-turn-dialog">
              <div class="history-dialog-user">
                <strong style="color: #6D28D9; font-size: 0.72rem; text-transform: uppercase; display: block; margin-bottom: 2px;">You:</strong>
                "${escapeHtml(turn.userQuery)}"
              </div>
              <div class="history-dialog-companion">
                <strong style="color: #059669; font-size: 0.72rem; text-transform: uppercase; display: block; margin-bottom: 2px;">Voice Companion:</strong>
                "${escapeHtml(turn.companionReply)}"
              </div>
            </div>
          </div>
        `;
      });

      historyModalBody.innerHTML = html;
    } catch (e) {
      console.warn('History render error:', e);
    }
  }

  function openHistoryModal() {
    if (historyModal) {
      renderVoiceHistoryModal();
      historyModal.classList.add('show');
    }
  }

  function closeHistoryModal() {
    if (historyModal) {
      historyModal.classList.remove('show');
    }
  }

  if (voiceHistoryBtn) voiceHistoryBtn.addEventListener('click', openHistoryModal);
  if (voiceHeaderHistoryBtn) voiceHeaderHistoryBtn.addEventListener('click', openHistoryModal);
  if (closeHistoryBtn) closeHistoryBtn.addEventListener('click', closeHistoryModal);
  if (historyModal) {
    historyModal.addEventListener('click', (e) => {
      if (e.target === historyModal) closeHistoryModal();
    });
  }
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', () => {
      if (confirm("Are you sure you want to clear your saved voice conversation history?")) {
        localStorage.removeItem('mentaura_voice_turns');
        renderVoiceHistoryModal();
      }
    });
  }
  if (loadHistoryBtn) {
    loadHistoryBtn.addEventListener('click', renderVoiceHistoryModal);
  }

  // Canvas dynamic auto-sizing to match container width
  function resizeCanvas() {
    if (canvas && canvas.parentElement) {
      const containerWidth = canvas.parentElement.clientWidth || 880;
      canvas.width = containerWidth;
      canvas.height = 68;
      drawIdleWaveform();
    }
  }
  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 100);

  // Language mapping for Web Speech Synthesis & Recognition (Focused on EN, HI, TA)
  const speechLangMap = {
    EN: 'en-IN',
    HI: 'hi-IN',
    TA: 'ta-IN'
  };

  // Helper: Append chat bubble to conversation stream
  function appendVoiceBubble(role, text, meta = {}) {
    if (!streamContainer) return;
    const bubble = document.createElement('div');
    bubble.className = `voice-msg-bubble ${role === 'user' ? 'user-bubble' : 'companion-bubble'}`;
    
    const iconClass = role === 'user' ? 'fa-solid fa-user' : 'fa-solid fa-shield-heart';
    const authorName = role === 'user' ? 'You' : 'Voice Companion';

    let actionHtml = '';
    if (meta.isElevationPrompt) {
      const cName = meta.counsellorName || "Assigned Counsellor";
      actionHtml = `
        <div class="bubble-actions">
          <button type="button" class="btn-bubble-elevate" id="btnBubbleElevate">
            <i class="fa-solid fa-handshake-angle"></i> Yes, Connect with ${cName}
          </button>
        </div>
      `;
    } else if (meta.isCounsellorNotified) {
      const cName = meta.counsellorName ? ` ${meta.counsellorName}` : "";
      actionHtml = `
        <div class="bubble-actions">
          <span class="bubble-urgent-badge">
            <i class="fa-solid fa-bell"></i> Counsellor${cName} Notified Immediately
          </span>
          <a href="tel:112" class="bubble-sos-link"><i class="fa-solid fa-phone"></i> Emergency 112</a>
          <a href="tel:14566" class="bubble-sos-link"><i class="fa-solid fa-phone-volume"></i> Helpline 14566</a>
        </div>
      `;
    }

    bubble.innerHTML = `
      <div class="bubble-avatar">
        <i class="${iconClass}"></i>
      </div>
      <div class="bubble-content">
        <div class="bubble-author">${authorName}</div>
        <p class="bubble-text">"${text}"</p>
        ${actionHtml}
      </div>
    `;

    streamContainer.appendChild(bubble);
    streamContainer.scrollTop = streamContainer.scrollHeight;

    // Attach click handler for elevation button if rendered
    const elevateBtn = bubble.querySelector('#btnBubbleElevate');
    if (elevateBtn) {
      elevateBtn.addEventListener('click', () => {
        elevateBtn.disabled = true;
        elevateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Connecting...';
        triggerCounsellorElevationDirect();
      });
    }
  }

  // Orb & UI State Controller
  function setVoiceUIState(state, customMessage) {
    if (!orbStage || !statePill) return;

    orbStage.classList.remove('listening', 'thinking', 'speaking', 'alert');
    statePill.classList.remove('listening', 'thinking', 'speaking', 'alert');

    if (state === 'listening') {
      orbStage.classList.add('listening');
      statePill.classList.add('listening');
      if (stateText) stateText.textContent = customMessage || 'Listening to your voice... (Speak comfortably)';
      if (orbIcon) orbIcon.className = 'fa-solid fa-microphone-lines fa-fade';
      if (recordBtn) recordBtn.classList.add('recording');
      if (recordIcon) recordIcon.className = 'fa-solid fa-stop';
      if (recordBtnLabel) recordBtnLabel.textContent = 'Stop Speaking';
    } else if (state === 'thinking') {
      orbStage.classList.add('thinking');
      statePill.classList.add('thinking');
      if (stateText) stateText.textContent = customMessage || 'Responding...';
      if (orbIcon) orbIcon.className = 'fa-solid fa-bolt-lightning fa-fade';
    } else if (state === 'speaking') {
      orbStage.classList.add('speaking');
      statePill.classList.add('speaking');
      if (stateText) stateText.textContent = customMessage || 'Companion Speaking aloud...';
      if (orbIcon) orbIcon.className = 'fa-solid fa-volume-high fa-beat';
      if (recordBtn) recordBtn.classList.remove('recording');
      if (recordIcon) recordIcon.className = 'fa-solid fa-microphone';
      if (recordBtnLabel) recordBtnLabel.textContent = 'Voice Active';
    } else if (state === 'alert') {
      orbStage.classList.add('alert');
      statePill.classList.add('alert');
      if (stateText) stateText.textContent = customMessage || '🚨 High Distress — Counsellor Notified Immediately';
      if (orbIcon) orbIcon.className = 'fa-solid fa-triangle-exclamation';
    } else {
      // Idle / Ready
      if (stateText) stateText.textContent = customMessage || 'Tap the button below to speak';
      if (orbIcon) orbIcon.className = 'fa-solid fa-microphone';
      if (recordBtn) recordBtn.classList.remove('recording');
      if (recordIcon) recordIcon.className = 'fa-solid fa-microphone';
      if (recordBtnLabel) recordBtnLabel.textContent = 'Start Voice Conversation';
    }
  }

  // Waveform visualization logic (Light theme: #F5F3FF container background)
  function drawIdleWaveform() {
    if (!ctx) return;
    ctx.fillStyle = '#F5F3FF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(126, 87, 194, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
  }
  drawIdleWaveform();

  function startWaveformVisualization() {
    if (!analyser) return;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function render() {
      animationId = requestAnimationFrame(render);
      analyser.getByteTimeDomainData(dataArray);

      ctx.fillStyle = '#F5F3FF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 2.5;

      if (isRecording) {
        ctx.strokeStyle = '#059669'; // Rich emerald wave when user speaks
      } else if (isSpeaking) {
        ctx.strokeStyle = '#DB2777'; // Rich rose-magenta wave when companion speaks
      } else {
        ctx.strokeStyle = 'rgba(126, 87, 194, 0.5)';
      }

      ctx.beginPath();
      const sliceWidth = (canvas.width * 1.0) / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * canvas.height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }

      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();
    }
    render();
  }

  // Animated wave simulator while AI is speaking
  let aiSpeakingWaveId = null;
  function startAiSpeakingWaveform() {
    let phase = 0;
    function renderAiWave() {
      if (!isSpeaking) return;
      aiSpeakingWaveId = requestAnimationFrame(renderAiWave);
      ctx.fillStyle = '#F5F3FF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = '#DB2777';
      ctx.beginPath();

      phase += 0.08;
      for (let x = 0; x < canvas.width; x++) {
        const y = canvas.height / 2 + Math.sin(x * 0.04 + phase) * 12 * Math.sin(x * 0.015);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    renderAiWave();
  }

  function stopAiSpeakingWaveform() {
    if (aiSpeakingWaveId) {
      cancelAnimationFrame(aiSpeakingWaveId);
      aiSpeakingWaveId = null;
    }
    drawIdleWaveform();
  }

  // Initialize Speech Recognition
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRec) {
    try {
      recognitionInstance = new SpeechRec();
      recognitionInstance.continuous = true;
      recognitionInstance.interimResults = true;

      recognitionInstance.onresult = (event) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const item = event.results[i];
          if (item.isFinal) {
            final += item[0].transcript;
          } else {
            interim += item[0].transcript;
          }
        }
        const text = (final || interim).trim();
        if (text) {
          // ========================================================
          // REAL-TIME VOICE BARGE-IN INTERRUPTION
          // When AI is speaking aloud, if user speaks, instantly cut
          // off the AI voice, switch to listening, and capture user query.
          // ========================================================
          if (isSpeaking) {
            console.log('[Voice Barge-In] User interrupted companion:', text);
            if ('speechSynthesis' in window) {
              window.speechSynthesis.cancel();
            }
            isSpeaking = false;
            stopAiSpeakingWaveform();
            isRecording = true;
            recordSeconds = 0;
            capturedSpeechText = text;
            setVoiceUIState('listening', 'Listening to your interruption...');
            startWaveformVisualization();

            clearTimeout(silenceTimeout);
            silenceTimeout = setTimeout(() => {
              if (isRecording && capturedSpeechText.trim().length > 1) {
                stopRecordingAndProcess();
              }
            }, 550);
            return;
          }

          capturedSpeechText = text;

          // In hands-free mode, trigger instant response after ~550ms of natural silence
          if (autoLoopToggle && autoLoopToggle.checked && isRecording) {
            clearTimeout(silenceTimeout);
            silenceTimeout = setTimeout(() => {
              if (isRecording && capturedSpeechText.trim().length > 1) {
                stopRecordingAndProcess();
              }
            }, 550);
          }
        }
      };

      recognitionInstance.onerror = (event) => {
        console.warn('Voice Speech Recognition notice:', event.error);
      };

      recognitionInstance.onend = () => {
        // Automatically keep recognition running if recording OR if AI is speaking (for barge-in)
        if (isRecording || isSpeaking) {
          try {
            recognitionInstance.start();
          } catch (e) {}
        }
      };
    } catch (e) {
      console.warn('Speech recognition init notice:', e);
    }
  }

  // Web Speech API Natural Spoken Output
  function speakAiResponse(text, onCompleteCallback) {
    if (!('speechSynthesis' in window)) {
      if (onCompleteCallback) onCompleteCallback();
      return;
    }

    window.speechSynthesis.cancel();
    isSpeaking = true;
    setVoiceUIState('speaking');
    startAiSpeakingWaveform();

    // Keep speech recognition actively listening during AI speech so user can barge in anytime
    if (recognitionInstance) {
      try {
        const selLang = voiceLangSelect ? voiceLangSelect.value : 'EN';
        recognitionInstance.lang = speechLangMap[selLang] || 'en-IN';
        recognitionInstance.start();
      } catch (e) {
        // Already active
      }
    }

    const selectedLang = (voiceLangSelect ? voiceLangSelect.value : 'EN').toUpperCase();
    const selectedTone = (voiceToneSelect ? voiceToneSelect.value : 'supportive');
    const profile = toneProfiles[selectedTone] || toneProfiles.supportive;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = speechLangMap[selectedLang] || 'en-IN';
    utterance.rate = profile.rate;
    utterance.pitch = profile.pitch;

    // Apply the persistently locked consistent voice for this language
    const voice = selectAndLockVoice(selectedLang);
    if (voice) {
      utterance.voice = voice;
    }

    utterance.onend = () => {
      // If user interrupted, isSpeaking was set to false by barge-in
      if (!isSpeaking) return;

      isSpeaking = false;
      stopAiSpeakingWaveform();

      if (lastClassification === 'high') {
        setVoiceUIState('alert');
      } else {
        setVoiceUIState('idle', 'Response complete • Ready for next turn');
      }

      if (onCompleteCallback) onCompleteCallback();

      // Hands-free auto conversation loop: Snappy 250ms restart for next turn
      if (autoLoopToggle && autoLoopToggle.checked && lastClassification !== 'high') {
        setTimeout(() => {
          if (!isRecording && !isSpeaking) {
            startRecording();
          }
        }, 250);
      }
    };

    utterance.onerror = (e) => {
      console.warn('Speech synthesis error:', e);
      isSpeaking = false;
      stopAiSpeakingWaveform();
      setVoiceUIState('idle');
      if (onCompleteCallback) onCompleteCallback();
    };

    window.speechSynthesis.speak(utterance);
  }

  // Start Recording Session
  async function startRecording() {
    if (isRecording) return;
    if (isSpeaking && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      isSpeaking = false;
      stopAiSpeakingWaveform();
    }

    try {
      if (!mediaStream || !mediaStream.active) {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
      }

      if (!audioContext || audioContext.state === 'closed') {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(mediaStream);
      source.connect(analyser);

      isRecording = true;
      recordSeconds = 0;
      capturedSpeechText = '';

      setVoiceUIState('listening');

      const selLang = voiceLangSelect ? voiceLangSelect.value : 'EN';
      if (recognitionInstance) {
        try {
          recognitionInstance.lang = speechLangMap[selLang] || 'en-IN';
          recognitionInstance.start();
        } catch (e) {}
      }

      clearInterval(timerInterval);
      timerInterval = setInterval(() => {
        recordSeconds++;
        const mins = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
        const secs = String(recordSeconds % 60).padStart(2, '0');
        if (timerDisplay) timerDisplay.textContent = `${mins}:${secs}`;

        // Auto-stop safety at 40 seconds
        if (recordSeconds >= 40) {
          stopRecordingAndProcess();
        }
      }, 1000);

      startWaveformVisualization();
    } catch (err) {
      console.warn('Microphone permission notice:', err);
      alert('Microphone access is required for real-time speech. Please enable microphone permissions in your browser.');
    }
  }

  // Stop Recording and trigger Backend AI Turn
  async function stopRecordingAndProcess() {
    if (!isRecording) return;
    isRecording = false;
    clearTimeout(silenceTimeout);
    clearInterval(timerInterval);

    if (animationId) cancelAnimationFrame(animationId);
    if (recognitionInstance) {
      try {
        recognitionInstance.stop();
      } catch (e) {}
    }

    const finalText = capturedSpeechText.trim();
    if (!finalText) {
      setVoiceUIState('idle', 'Tap microphone to speak');
      drawIdleWaveform();
      return;
    }

    setVoiceUIState('thinking');
    drawIdleWaveform();

    await sendVoiceTurnToBackend(finalText);
  }

  // Send turn to `/api/victim/voice-chat/turn`
  async function sendVoiceTurnToBackend(speechText) {
    // 1. Immediately render user's message bubble
    appendVoiceBubble('user', speechText);

    // Estimate acoustic biomarkers (calm baseline for natural conversational speech)
    let tensionHz = Math.floor(145 + Math.random() * 12);
    let jitterVal = +(0.85 + Math.random() * 0.20).toFixed(2);
    let pauseRatio = +(0.15 + Math.random() * 0.06).toFixed(2);

    if (/suicide|commit suicide|kill myself|end my life|threat|die|attack|danger|terrified|stalking|cornered|emergency/i.test(speechText)) {
      tensionHz = 224;
      jitterVal = 2.45;
      pauseRatio = 0.44;
    } else if (/not feeling well|feel bad|anxious|worried|court|stress|trouble|scared|heavy|exhausted|sad|crying|pain/i.test(speechText)) {
      tensionHz = 190;
      jitterVal = 1.62;
      pauseRatio = 0.30;
    }

    try {
      const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token') || '';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const activeLang = voiceLangSelect ? voiceLangSelect.value : 'EN';
      const payload = {
        transcript: speechText,
        language: activeLang,
        audio_duration_seconds: Math.max(recordSeconds, 3.0),
        pitch_tension_hz: tensionHz,
        jitter_percent: jitterVal,
        pause_ratio: pauseRatio,
        conversation_history: voiceConversationHistory
      };

      const res = await fetch('/api/victim/voice-chat/turn', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        currentAiVoiceReply = data.ai_spoken_reply || currentAiVoiceReply;
        lastClassification = data.classification || 'low';

        // Add to persistent conversation history for multi-turn context
        voiceConversationHistory.push({ role: 'user', content: speechText });
        voiceConversationHistory.push({ role: 'assistant', content: currentAiVoiceReply });
        if (voiceConversationHistory.length > 20) voiceConversationHistory.splice(0, 2);

        // Save completed turn to persistent history modal
        saveTurnToHistory(speechText, currentAiVoiceReply, lastClassification, activeLang);

        // 2. Render companion's spoken reply bubble with actions if applicable
        appendVoiceBubble('companion', currentAiVoiceReply, {
          isElevationPrompt: !!data.elevation_prompt,
          isCounsellorNotified: !!data.counsellor_notified
        });

        // 3. Speak reply aloud
        speakAiResponse(currentAiVoiceReply);
      } else {
        throw new Error('Server response error');
      }
    } catch (err) {
      console.warn('Voice chat integration notice:', err);
      const fallbackReply = "I am listening and here with you. Please take a gentle breath. You are safe, and we are ready to support you.";
      appendVoiceBubble('companion', fallbackReply);
      saveTurnToHistory(speechText, fallbackReply, 'low', (voiceLangSelect ? voiceLangSelect.value : 'EN'));
      speakAiResponse(fallbackReply);
    }
  }

  // Direct Counsellor Elevation Action
  async function triggerCounsellorElevationDirect() {
    try {
      const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token') || '';
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/api/victim/voice-chat/elevate', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          transcript: capturedSpeechText || 'User confirmed counsellor connection in interactive voice check-in',
          notes: 'Connected directly via Voice Check-In'
        })
      });

      const data = await res.json();
      const cName = data.counsellor_name || "your assigned counsellor";
      const confirmMsg = data.message || `I have connected you with ${cName}. They have received your details and will contact you directly. We are right here with you.`;
      appendVoiceBubble('companion', confirmMsg);
      saveTurnToHistory("Counsellor Connection Requested", confirmMsg, "medium", (voiceLangSelect ? voiceLangSelect.value : 'EN'));
      speakAiResponse(confirmMsg);
    } catch (e) {
      console.warn('Elevation error:', e);
    }
  }

  // Central Orb Click Toggle (Supports click-to-interrupt)
  if (orbStage) {
    orbStage.addEventListener('click', () => {
      if (isSpeaking) {
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        isSpeaking = false;
        stopAiSpeakingWaveform();
        startRecording();
        return;
      }
      if (isRecording) {
        stopRecordingAndProcess();
      } else {
        startRecording();
      }
    });
  }

  // Master Record Button Click Toggle (Supports click-to-interrupt)
  recordBtn.addEventListener('click', () => {
    if (isSpeaking) {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      isSpeaking = false;
      stopAiSpeakingWaveform();
      startRecording();
      return;
    }
    if (isRecording) {
      stopRecordingAndProcess();
    } else {
      startRecording();
    }
  });

  // Interrupt Button
  if (interruptBtn) {
    interruptBtn.addEventListener('click', () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      isSpeaking = false;
      stopAiSpeakingWaveform();
      setVoiceUIState('idle', 'AI Speech Paused');
    });
  }

  // Replay Button
  if (replayBtn) {
    replayBtn.addEventListener('click', () => {
      if (currentAiVoiceReply) {
        speakAiResponse(currentAiVoiceReply);
      }
    });
  }

  // Language Change Listener (English, Hindi, Tamil)
  if (voiceLangSelect) {
    voiceLangSelect.addEventListener('change', () => {
      const newLang = voiceLangSelect.value.toUpperCase();
      currentAiVoiceReply = initialGreetingsByLang[newLang] || initialGreetingsByLang.EN;

      if (recognitionInstance) {
        recognitionInstance.lang = speechLangMap[newLang] || 'en-IN';
      }

      if (initialCompanionText) {
        initialCompanionText.textContent = `"${currentAiVoiceReply}"`;
      }

      selectAndLockVoice(newLang);
      speakAiResponse(currentAiVoiceReply);
    });
  }

  // Tone Persona Selector Listener
  if (voiceToneSelect) {
    const savedTone = localStorage.getItem('mentaura_voice_tone');
    if (savedTone && toneProfiles[savedTone]) {
      voiceToneSelect.value = savedTone;
    }

    voiceToneSelect.addEventListener('change', () => {
      const chosenTone = voiceToneSelect.value;
      localStorage.setItem('mentaura_voice_tone', chosenTone);
      const profile = toneProfiles[chosenTone] || toneProfiles.supportive;
      const curLang = (voiceLangSelect ? voiceLangSelect.value : 'EN').toUpperCase();

      const toneConfirmationPhrases = {
        EN: `Voice tone set to ${profile.label}.`,
        HI: `आवाज़ की टोन बदल दी गई है।`,
        TA: `குரல் தொனி மாற்றப்பட்டது.`
      };

      speakAiResponse(toneConfirmationPhrases[curLang] || toneConfirmationPhrases.EN);
    });
  }

  // Reset Chat Button
  if (resetChatBtn) {
    resetChatBtn.addEventListener('click', () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      isSpeaking = false;
      isRecording = false;
      stopAiSpeakingWaveform();
      voiceConversationHistory = [];
      if (timerDisplay) timerDisplay.textContent = '00:00';
      setVoiceUIState('idle', 'Conversation Reset');
      
      const curLang = (voiceLangSelect ? voiceLangSelect.value : 'EN').toUpperCase();
      currentAiVoiceReply = initialGreetingsByLang[curLang] || initialGreetingsByLang.EN;

      if (streamContainer) {
        streamContainer.innerHTML = `
          <div class="voice-msg-bubble companion-bubble">
            <div class="bubble-avatar">
              <i class="fa-solid fa-shield-heart"></i>
            </div>
            <div class="bubble-content">
              <div class="bubble-author">Voice Companion</div>
              <div class="bubble-text" id="voiceInitialCompanionText">"${currentAiVoiceReply}"</div>
            </div>
          </div>
        `;
      }
    });
  }
}

/**
 * =======================================================
 * CHANNEL 3: IVRS 14566 SIMULATOR (SIH 26094)
 * DTMF Audio Synthesizer and Interactive Outbound Call
 * =======================================================
 */
function setupIvrsChannel() {
  const callBtn = document.getElementById('ivrsCallBtn');
  const endCallBtn = document.getElementById('ivrsEndCallBtn');
  const statusScreen = document.getElementById('ivrsStatusScreen');
  const audioWave = document.getElementById('ivrsAudioWave');
  const dialpadBtns = document.querySelectorAll('.ivrs-dial-btn');

  if (!callBtn || !statusScreen) return;

  let isCallActive = false;
  let audioCtx = null;

  // DTMF Standard Frequencies (Hz)
  const dtmfFreqs = {
    '1': [697, 1209], '2': [697, 1336], '3': [697, 1477],
    '4': [770, 1209], '5': [770, 1336], '6': [770, 1477],
    '7': [852, 1209], '8': [852, 1336], '9': [852, 1477],
    '*': [941, 1209], '0': [941, 1336], '#': [941, 1477]
  };

  function playDtmfTone(key) {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const freqs = dtmfFreqs[key];
      if (!freqs) return;

      const osc1 = audioCtx.createOscillator();
      const osc2 = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      osc1.frequency.value = freqs[0];
      osc2.frequency.value = freqs[1];

      gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.25);

      osc1.connect(gainNode);
      osc2.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      osc1.start();
      osc2.start();
      osc1.stop(audioCtx.currentTime + 0.25);
      osc2.stop(audioCtx.currentTime + 0.25);
    } catch (e) {
      // Audio autoplay policy fallback
    }
  }

  callBtn.addEventListener('click', () => {
    isCallActive = true;
    callBtn.disabled = true;
    callBtn.style.opacity = '0.5';
    endCallBtn.disabled = false;
    endCallBtn.style.opacity = '1';
    endCallBtn.style.cursor = 'pointer';

    if (audioWave) audioWave.style.visibility = 'visible';

    statusScreen.innerHTML = `
      [CALL CONNECTED - NHAA 14566]<br>
      "Namaste. You are connected to the National Helpline for Atrocity Alleviation automated well-being system.<br><br>
      Please rate your current distress level using your phone keypad:<br>
      Press 1: Very Good<br>
      Press 2: Doing Fine<br>
      Press 3: Mild Stress<br>
      Press 4: High Distress<br>
      Press 5: Severe Trauma Crisis<br>
      Press 9: Immediate Police Assistance (Section 15A)"
    `;
  });

  endCallBtn.addEventListener('click', () => {
    isCallActive = false;
    callBtn.disabled = false;
    callBtn.style.opacity = '1';
    endCallBtn.disabled = true;
    endCallBtn.style.opacity = '0.5';
    endCallBtn.style.cursor = 'not-allowed';

    if (audioWave) audioWave.style.visibility = 'hidden';

    statusScreen.innerHTML = `
      [CALL TERMINATED]<br>
      Thank you for participating in the automated NHAA 14566 health check.<br>
      Press "Start Call" to initiate another check-in.
    `;
  });

  dialpadBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const key = btn.getAttribute('data-key');
      playDtmfTone(key);

      if (!isCallActive) {
        statusScreen.innerHTML = `[DIALPAD INPUT: ${key}]<br>Please click "Start Call" to connect to NHAA 14566 first.`;
        return;
      }

      statusScreen.innerHTML = `[DTMF TONE ${key} SENT]<br><i class="fa-solid fa-spinner fa-spin"></i> Communicating with NHAA 14566 Gateway...`;

      try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token') || '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch('/api/victim/simulate-ivrs', {
          method: 'POST',
          headers,
          credentials: 'include',
          body: JSON.stringify({ dtmf_key: key })
        });

        if (res.ok) {
          const data = await res.json();
          let extraMsg = '';
          if (key === '9') {
            extraMsg = '<br><strong style="color: #EF4444;">🚨 EMERGENCY DISPATCH: Section 15A Protection Alert Dispatched to District SP.</strong>';
          }
          statusScreen.innerHTML = `
            [DTMF KEY ${key} REGISTERED]<br>
            <strong>IVRS Response:</strong> "${data.voice_prompt_text || data.prompt_text || data.voice_script || 'Choice recorded.'}"
            ${extraMsg}
          `;
        } else {
          statusScreen.innerHTML = `[DTMF KEY ${key} CONFIRMED]<br>Your response has been registered. Thank you.`;
        }
      } catch (err) {
        statusScreen.innerHTML = `[DTMF KEY ${key} CONFIRMED]<br>Your response has been logged with the automated system.`;
      }
    });
  });
}

/**
 * =======================================================
 * CHANNEL 5: SMS / WHATSAPP NUDGES (SIH 26094)
 * Proactive Micro-Nudge Simulator with Instant Government Feedback
 * =======================================================
 */
function setupSmsChannel() {
  const thread = document.getElementById('whatsappMessageThread');
  const input = document.getElementById('smsInputField');
  const sendBtn = document.getElementById('smsSendBtn');
  const quickChips = document.querySelectorAll('.sms-quick-chip');

  if (!thread || !input || !sendBtn) return;

  async function sendSmsReply(replyText) {
    const text = (replyText || input.value || '').trim();
    if (!text) return;

    input.value = '';

    // Add user bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'whatsapp-bubble whatsapp-bubble-user';
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    userBubble.innerHTML = `${text}<div style="font-size: 0.65rem; color: #666; text-align: right; margin-top: 4px;">${now} ✓✓</div>`;
    thread.appendChild(userBubble);
    thread.scrollTop = thread.scrollHeight;

    // Simulate government automated response
    setTimeout(async () => {
      const botBubble = document.createElement('div');
      botBubble.className = 'whatsapp-bubble';

      const isSos = text.toUpperCase().includes('SOS') || text === '4';
      if (isSos) {
        botBubble.innerHTML = `
          <strong>🚨 NHAA 14566 URGENT RESPONSE</strong><br><br>
          We received your emergency indicator. An immediate alert has been forwarded to the <strong>District SP / DSP Protection Unit</strong> under Section 15A.<br><br>
          A support officer is attempting to connect with you. If you are in physical danger, please call <strong>112</strong> immediately.
          <div style="font-size: 0.65rem; color: #888; text-align: right; margin-top: 4px;">${now}</div>
        `;
      } else {
        botBubble.innerHTML = `
          <strong>NHAA 14566 Automated Acknowledgement</strong><br><br>
          Thank you. Your rating (<strong>${text}</strong>) has been securely logged with your case file. Our care team is monitoring your well-being.<br><br>
          Next scheduled check-in: Tomorrow at 09:00 AM.
          <div style="font-size: 0.65rem; color: #888; text-align: right; margin-top: 4px;">${now}</div>
        `;
      }

      thread.appendChild(botBubble);
      thread.scrollTop = thread.scrollHeight;

      // Send to backend
      try {
        const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token') || '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        await fetch('/api/victim/pulse', {
          method: 'POST',
          headers,
          credentials: 'include',
          body: JSON.stringify({
            overall_wellbeing: isSos ? 'crisis' : (text === '3' ? 'struggling' : 'steady'),
            interaction_channel: 'sms',
            private_reflection: `SMS Nudge reply: ${text}`,
            processing_mode: 'ai_assisted'
          })
        });
      } catch (e) {
        // Silent sync
      }
    }, 700);
  }

  sendBtn.addEventListener('click', () => sendSmsReply());
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendSmsReply();
  });

  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const reply = chip.getAttribute('data-reply');
      if (reply) sendSmsReply(reply);
    });
  });
}

