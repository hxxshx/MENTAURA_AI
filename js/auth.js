/**
 * MENTAURA — Client Authentication Module
 * Handles Signup, Email OTP Verification, Login, Forgot Password modals, validation, and session navigation.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Modal Elements
  const signupModal = document.getElementById('signupModal');
  const loginModal = document.getElementById('loginModal');
  const forgotPasswordModal = document.getElementById('forgotPasswordModal');

  // Modal Titles & Descriptions
  const signupTitle = document.getElementById('signupTitle');
  const signupDesc = document.getElementById('signupDesc');
  const signupFooter = document.getElementById('signupFooter');

  // Forms & Steps
  const signupForm = document.getElementById('signupForm');
  const otpSection = document.getElementById('otpSection');
  const otpVerificationForm = document.getElementById('otpVerificationForm');
  const loginForm = document.getElementById('loginForm');
  const forgotPasswordForm = document.getElementById('forgotPasswordForm');

  // Alert Banners
  const signupAlert = document.getElementById('signupAlert');
  const otpAlert = document.getElementById('otpAlert');
  const loginAlert = document.getElementById('loginAlert');
  const forgotAlert = document.getElementById('forgotAlert');

  // Role & Official ID Elements
  const categorySelect = document.getElementById('signupCategory');
  const officialIdGroup = document.getElementById('officialIdGroup');
  const officialIdInput = document.getElementById('signupOfficialId');
  const verifyOfficialIdBtn = document.getElementById('verifyOfficialIdBtn');
  const verifyOfficialIdBtnText = document.getElementById('verifyOfficialIdBtnText');
  const officialIdBadge = document.getElementById('officialIdBadge');
  const officialIdStatusMsg = document.getElementById('officialIdStatusMsg');
  const officialIdInputIcon = document.getElementById('officialIdInputIcon');

  // Anonymity Choice Elements (For Affected Individuals & Families)
  const anonymityChoiceGroup = document.getElementById('anonymityChoiceGroup');
  const anonymityChoiceYes = document.getElementById('anonymityChoiceYes');
  const anonymityChoiceNo = document.getElementById('anonymityChoiceNo');
  const labelAnonYes = document.getElementById('labelAnonYes');
  const labelAnonNo = document.getElementById('labelAnonNo');

  // Full Name, Email and Anonymous Dynamic Controls
  const signupFullNameGroup = document.getElementById('signupFullNameGroup');
  const signupFullName = document.getElementById('signupFullName');
  const signupFullNameLabel = document.getElementById('signupFullNameLabel');
  const signupEmailGroup = document.getElementById('signupEmailGroup');
  const signupEmail = document.getElementById('signupEmail');
  const signupEmailLabel = document.getElementById('signupEmailLabel');
  const signupEmailHelper = document.getElementById('signupEmailHelper');
  const anonNoticeBanner = document.getElementById('anonNoticeBanner');
  const anonSuccessSection = document.getElementById('anonSuccessSection');
  const anonCreatedIdDisplay = document.getElementById('anonCreatedIdDisplay');
  const copyAnonIdBtn = document.getElementById('copyAnonIdBtn');
  const copyAnonIdBtnText = document.getElementById('copyAnonIdBtnText');
  const anonProceedBtn = document.getElementById('anonProceedBtn');

  // Official ID Verification State
  let isOfficialIdVerified = false;
  let verifiedOfficialIdValue = '';

  // OTP State Elements
  const otpTargetEmail = document.getElementById('otpTargetEmail');
  const otpCodeInput = document.getElementById('otpCodeInput');
  const resendOtpBtn = document.getElementById('resendOtpBtn');
  const backToSignupForm = document.getElementById('backToSignupForm');

  // Tracking email for OTP verification step
  let pendingSignupEmail = '';

  // Official Roles requiring official/government/employee ID
  const OFFICIAL_ROLES = new Set([
    'counsellor',
    'case_officer',
    'district_authority',
    'legal_aid_officer',
    'protection_officer',
    'medical_rehab_officer',
    'state_admin',
    'national_admin',
  ]);

  // Affected Roles eligible for Anonymous Protection
  const AFFECTED_ROLES = new Set([
    'victim',
    'witness',
    'affected_family',
    'affected_family_member',
  ]);

  // Helper function to show alert in modal
  function showAlert(alertEl, message, type = 'error') {
    if (!alertEl) return;
    let text = message;
    if (Array.isArray(message)) {
      text = message
        .map((item) => (item && typeof item === 'object' ? (item.msg || item.detail || JSON.stringify(item)) : String(item)))
        .join('. ');
    } else if (message && typeof message === 'object') {
      text = message.msg || message.detail || JSON.stringify(message);
    }
    alertEl.textContent = text || 'An error occurred. Please try again.';
    alertEl.className = `auth-alert show auth-alert-${type}`;
  }

  function hideAlert(alertEl) {
    if (!alertEl) return;
    alertEl.className = 'auth-alert';
    alertEl.textContent = '';
  }

  // Reset official ID verification state
  function resetOfficialIdVerificationState() {
    isOfficialIdVerified = false;
    verifiedOfficialIdValue = '';
    if (officialIdInput) {
      officialIdInput.classList.remove('is-verified', 'is-invalid');
    }
    if (officialIdBadge) {
      officialIdBadge.className = 'official-verify-badge badge-pending';
      officialIdBadge.innerHTML = '<i class="fa-solid fa-id-card-clip"></i> Verification Required';
    }
    if (officialIdStatusMsg) {
      officialIdStatusMsg.style.display = 'none';
      officialIdStatusMsg.innerHTML = '';
      officialIdStatusMsg.className = 'official-verification-card';
    }
    if (verifyOfficialIdBtn) {
      verifyOfficialIdBtn.disabled = false;
      verifyOfficialIdBtn.classList.remove('is-verified');
      if (verifyOfficialIdBtnText) verifyOfficialIdBtnText.textContent = 'Verify ID';
    }
    if (officialIdInputIcon) {
      officialIdInputIcon.innerHTML = '<i class="fa-solid fa-building-columns"></i>';
    }
  }

  // Invalidate verification if user types a new ID
  if (officialIdInput) {
    officialIdInput.addEventListener('input', () => {
      const current = officialIdInput.value.trim().toUpperCase();
      if (isOfficialIdVerified && current !== verifiedOfficialIdValue) {
        resetOfficialIdVerificationState();
      }
    });
  }

  // Verification request to backend API
  async function performOfficialIdVerification() {
    if (!officialIdInput) return false;
    const cleanId = officialIdInput.value.trim().toUpperCase();
    const role = (categorySelect?.value || 'national_admin').trim();

    if (!cleanId || cleanId.length < 4) {
      if (officialIdStatusMsg) {
        officialIdStatusMsg.style.display = 'block';
        officialIdStatusMsg.className = 'official-verification-card card-error';
        officialIdStatusMsg.innerHTML = '<div class="card-title"><i class="fa-solid fa-circle-xmark"></i> Credential Required</div><div>Please enter your Government Official ID (at least 4 characters).</div>';
      }
      if (officialIdInput) {
        officialIdInput.classList.add('is-invalid');
        officialIdInput.focus();
      }
      return false;
    }

    if (verifyOfficialIdBtn) {
      verifyOfficialIdBtn.disabled = true;
      if (verifyOfficialIdBtnText) verifyOfficialIdBtnText.textContent = 'Verifying...';
    }
    if (officialIdStatusMsg) {
      officialIdStatusMsg.style.display = 'block';
      officialIdStatusMsg.className = 'official-verification-card card-loading';
      officialIdStatusMsg.innerHTML = '<div class="card-title"><i class="fa-solid fa-spinner fa-spin"></i> Checking Government Credential Registry...</div><div>Validating official cadre authority, state/central registry records, and designation...</div>';
    }

    try {
      const resp = await fetch('/api/auth/verify-official-id', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          official_id: cleanId,
          role: role,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        isOfficialIdVerified = false;
        verifiedOfficialIdValue = '';
        if (officialIdInput) {
          officialIdInput.classList.remove('is-verified');
          officialIdInput.classList.add('is-invalid');
        }
        if (officialIdBadge) {
          officialIdBadge.className = 'official-verify-badge badge-invalid';
          officialIdBadge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Verification Failed';
        }
        if (officialIdStatusMsg) {
          officialIdStatusMsg.style.display = 'block';
          officialIdStatusMsg.className = 'official-verification-card card-error';
          officialIdStatusMsg.innerHTML = `
            <div class="card-title"><i class="fa-solid fa-triangle-exclamation"></i> Official ID Verification Failed</div>
            <div>${data.detail || 'Unrecognized Government Official ID. Credential must match authorized state/cadre registry.'}</div>
          `;
        }
        if (verifyOfficialIdBtn) {
          verifyOfficialIdBtn.disabled = false;
          verifyOfficialIdBtn.classList.remove('is-verified');
          if (verifyOfficialIdBtnText) verifyOfficialIdBtnText.textContent = 'Verify ID';
        }
        return false;
      }

      // Successful verification
      isOfficialIdVerified = true;
      verifiedOfficialIdValue = cleanId;
      officialIdInput.value = cleanId;

      if (officialIdInput) {
        officialIdInput.classList.remove('is-invalid');
        officialIdInput.classList.add('is-verified');
      }
      if (officialIdBadge) {
        officialIdBadge.className = 'official-verify-badge badge-verified';
        officialIdBadge.innerHTML = '<i class="fa-solid fa-shield-check"></i> Government Verified';
      }
      if (officialIdInputIcon) {
        officialIdInputIcon.innerHTML = '<i class="fa-solid fa-check" style="color: #10B981;"></i>';
      }
      if (verifyOfficialIdBtn) {
        verifyOfficialIdBtn.disabled = false;
        verifyOfficialIdBtn.classList.add('is-verified');
        if (verifyOfficialIdBtnText) verifyOfficialIdBtnText.textContent = '✓ Verified';
      }
      if (officialIdStatusMsg) {
        const d = data.data || {};
        officialIdStatusMsg.style.display = 'block';
        officialIdStatusMsg.className = 'official-verification-card card-success';
        officialIdStatusMsg.innerHTML = `
          <div class="card-title">
            <i class="fa-solid fa-circle-check"></i>
            <span>Government Official ID Verified</span>
          </div>
          <div class="card-meta">
            <div><strong>Department:</strong> ${d.department || 'Authorised Government Administrative Department'}</div>
            <div><strong>Designation:</strong> ${d.designation || 'Authorised Official'}</div>
            <div><strong>Cadre:</strong> ${d.cadre || 'Civil Services Authority'}</div>
            <div style="font-size: 0.72rem; color: #047857; margin-top: 2px;">
              <i class="fa-solid fa-building-shield"></i> Validated by ${d.verification_agency || 'Mentaura Credential Authority'}
            </div>
          </div>
        `;
      }
      hideAlert(signupAlert);
      return true;

    } catch (err) {
      console.error('Official ID Verification Error:', err);
      if (officialIdStatusMsg) {
        officialIdStatusMsg.style.display = 'block';
        officialIdStatusMsg.className = 'official-verification-card card-error';
        officialIdStatusMsg.innerHTML = '<div class="card-title"><i class="fa-solid fa-triangle-exclamation"></i> Connection Error</div><div>Could not connect to government verification service. Please try again.</div>';
      }
      if (verifyOfficialIdBtn) {
        verifyOfficialIdBtn.disabled = false;
        if (verifyOfficialIdBtnText) verifyOfficialIdBtnText.textContent = 'Verify ID';
      }
      return false;
    }
  }

  if (verifyOfficialIdBtn) {
    verifyOfficialIdBtn.addEventListener('click', (e) => {
      e.preventDefault();
      performOfficialIdVerification();
    });
  }

  // Update styling and form fields for Anonymity choice options
  function updateAnonymityOptionStyles() {
    const isAnon = anonymityChoiceYes?.checked ?? true;
    if (labelAnonYes && labelAnonNo) {
      if (isAnon) {
        labelAnonYes.style.border = '1.5px solid #6366F1';
        labelAnonYes.style.background = '#F5F3FF';
        labelAnonYes.style.boxShadow = '0 2px 8px rgba(99, 102, 241, 0.08)';
        labelAnonNo.style.border = '1.5px solid #E2E8F0';
        labelAnonNo.style.background = '#FFFFFF';
        labelAnonNo.style.boxShadow = 'none';
      } else {
        labelAnonNo.style.border = '1.5px solid #6366F1';
        labelAnonNo.style.background = '#F5F3FF';
        labelAnonNo.style.boxShadow = '0 2px 8px rgba(99, 102, 241, 0.08)';
        labelAnonYes.style.border = '1.5px solid #E2E8F0';
        labelAnonYes.style.background = '#FFFFFF';
        labelAnonYes.style.boxShadow = 'none';
      }
    }

    const selected = (categorySelect?.value || '').trim().toLowerCase();
    const isAffected = AFFECTED_ROLES.has(selected);

    if (isAffected && isAnon) {
      if (anonNoticeBanner) anonNoticeBanner.style.display = 'block';
      if (signupFullNameGroup) {
        signupFullNameGroup.style.display = 'none';
        if (signupFullName) signupFullName.required = false;
      }
      if (signupEmailLabel) signupEmailLabel.textContent = 'Delivery Email (Optional)';
      if (signupEmail) {
        signupEmail.placeholder = 'Optional - leave blank for instant Anonymous ID access';
        signupEmail.required = false;
      }
      if (signupEmailHelper) signupEmailHelper.style.display = 'block';
    } else {
      if (anonNoticeBanner) anonNoticeBanner.style.display = 'none';
      if (signupFullNameGroup) {
        signupFullNameGroup.style.display = 'block';
        if (signupFullName) signupFullName.required = true;
      }
      if (signupEmailLabel) signupEmailLabel.textContent = 'Email Address *';
      if (signupEmail) {
        signupEmail.placeholder = 'Enter your email address';
        signupEmail.required = true;
      }
      if (signupEmailHelper) signupEmailHelper.style.display = 'none';
    }
  }

  if (anonymityChoiceYes) anonymityChoiceYes.addEventListener('change', updateAnonymityOptionStyles);
  if (anonymityChoiceNo) anonymityChoiceNo.addEventListener('change', updateAnonymityOptionStyles);

  // Toggle Official ID and Anonymity Choice visibility based on selected role
  function updateRoleVisibility() {
    if (!categorySelect) return;
    const selected = (categorySelect.value || '').trim().toLowerCase();

    // 1. Official ID Visibility & Requirement
    if (officialIdGroup) {
      if (OFFICIAL_ROLES.has(selected)) {
        officialIdGroup.style.display = 'block';
        if (officialIdInput) officialIdInput.required = true;
      } else {
        officialIdGroup.style.display = 'none';
        if (officialIdInput) {
          officialIdInput.required = false;
          officialIdInput.value = '';
        }
        resetOfficialIdVerificationState();
      }
    }

    // 2. Anonymity Choice Visibility (strictly for Affected Individuals & Families)
    if (anonymityChoiceGroup) {
      if (AFFECTED_ROLES.has(selected)) {
        anonymityChoiceGroup.style.display = 'block';
        // Default to protected anonymity for safety
        if (anonymityChoiceYes && !anonymityChoiceYes.checked && !anonymityChoiceNo?.checked) {
          anonymityChoiceYes.checked = true;
        }
      } else {
        anonymityChoiceGroup.style.display = 'none';
      }
    }

    updateAnonymityOptionStyles();
  }

  if (categorySelect) {
    categorySelect.addEventListener('change', () => {
      resetOfficialIdVerificationState();
      updateRoleVisibility();
    });
    categorySelect.addEventListener('input', () => {
      resetOfficialIdVerificationState();
      updateRoleVisibility();
    });
  }

  // Modal open/close helpers
  window.openSignupModal = function () {
    closeAllModals();
    if (signupModal) {
      signupModal.classList.add('active');
      signupModal.setAttribute('aria-hidden', 'false');

      // Reset to signup form view (if previously in OTP or anon success step)
      if (signupForm) signupForm.style.display = 'grid';
      if (otpSection) otpSection.style.display = 'none';
      if (anonSuccessSection) anonSuccessSection.style.display = 'none';
      if (signupFooter) signupFooter.style.display = 'block';
      if (signupDesc) signupDesc.style.display = 'block';
      if (signupTitle) signupTitle.textContent = 'Create a Mentaura Support Account';

      hideAlert(signupAlert);
      hideAlert(otpAlert);
      resetOfficialIdVerificationState();
      updateRoleVisibility();

      const firstInput = signupModal.querySelector('input');
      if (firstInput) firstInput.focus();
    }
  };

  window.openLoginModal = function () {
    closeAllModals();
    if (loginModal) {
      loginModal.classList.add('active');
      loginModal.setAttribute('aria-hidden', 'false');
      hideAlert(loginAlert);
      const firstInput = loginModal.querySelector('input');
      if (firstInput) firstInput.focus();
    }
  };

  window.openForgotPasswordModal = function () {
    closeAllModals();
    if (forgotPasswordModal) {
      forgotPasswordModal.classList.add('active');
      forgotPasswordModal.setAttribute('aria-hidden', 'false');
      hideAlert(forgotAlert);
      const firstInput = forgotPasswordModal.querySelector('input');
      if (firstInput) firstInput.focus();
    }
  };

  window.closeAllModals = function () {
    document.querySelectorAll('.auth-modal-overlay').forEach((modal) => {
      modal.classList.remove('active');
      modal.setAttribute('aria-hidden', 'true');
    });
  };

  // Privacy Policy Modal Box Elements & Handlers
  const privacyPolicyModal = document.getElementById('privacyPolicyModal');
  const openPrivacyModalLink = document.getElementById('openPrivacyModalLink');
  const closePrivacyModalBtn = document.getElementById('closePrivacyModalBtn');
  const acceptPrivacyPolicyBtn = document.getElementById('acceptPrivacyPolicyBtn');
  const modalPrivacyConsent = document.getElementById('modalPrivacyConsent');
  const signupConsent = document.getElementById('signupConsent');

  function openPrivacyModal() {
    if (privacyPolicyModal) {
      privacyPolicyModal.classList.add('active');
      privacyPolicyModal.setAttribute('aria-hidden', 'false');
      if (modalPrivacyConsent && signupConsent) {
        modalPrivacyConsent.checked = signupConsent.checked;
      }
    }
  }

  function closePrivacyModal() {
    if (privacyPolicyModal) {
      privacyPolicyModal.classList.remove('active');
      privacyPolicyModal.setAttribute('aria-hidden', 'true');
    }
  }

  if (openPrivacyModalLink) {
    openPrivacyModalLink.addEventListener('click', (e) => {
      e.preventDefault();
      openPrivacyModal();
    });
  }

  if (closePrivacyModalBtn) {
    closePrivacyModalBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      closePrivacyModal();
    });
  }

  if (privacyPolicyModal) {
    privacyPolicyModal.addEventListener('click', (e) => {
      if (e.target === privacyPolicyModal) {
        e.stopPropagation();
        closePrivacyModal();
      }
    });
  }

  if (acceptPrivacyPolicyBtn) {
    acceptPrivacyPolicyBtn.addEventListener('click', (e) => {
      e.preventDefault();
      if (signupConsent) {
        signupConsent.checked = true;
      }
      closePrivacyModal();
    });
  }

  if (modalPrivacyConsent) {
    modalPrivacyConsent.addEventListener('change', () => {
      if (signupConsent) {
        signupConsent.checked = modalPrivacyConsent.checked;
      }
    });
  }

  // Bind close buttons (for all modals except privacyPolicyModal which has dedicated handler)
  document.querySelectorAll('.auth-modal-close-btn').forEach((btn) => {
    if (btn.id === 'closePrivacyModalBtn') return;
    btn.addEventListener('click', closeAllModals);
  });

  // Close on backdrop click (for all modals except privacyPolicyModal)
  document.querySelectorAll('.auth-modal-overlay').forEach((overlay) => {
    if (overlay.id === 'privacyPolicyModal') return;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeAllModals();
      }
    });
  });

  // Close on Escape key (close privacy modal first if active, otherwise close all)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (privacyPolicyModal && privacyPolicyModal.classList.contains('active')) {
        closePrivacyModal();
      } else {
        closeAllModals();
      }
    }
  });

  // Password Visibility Toggle
  document.querySelectorAll('.password-toggle-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        btn.innerHTML = isPassword
          ? '<i class="fa-regular fa-eye-slash"></i>'
          : '<i class="fa-regular fa-eye"></i>';
      }
    });
  });

  // =========================================================================
  // 1. Signup Form Submission
  // =========================================================================
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(signupAlert);

      const fullName = document.getElementById('signupFullName')?.value.trim();
      const email = document.getElementById('signupEmail')?.value.trim();
      const password = document.getElementById('signupPassword')?.value;
      const confirmPassword = document.getElementById('signupConfirmPassword')?.value;
      const category = document.getElementById('signupCategory')?.value;
      const officialId = officialIdInput?.value.trim();
      const language = document.getElementById('signupLanguage')?.value || 'en';
      const channel = document.getElementById('signupChannel')?.value || 'web_portal';
      const consentChecked = document.getElementById('signupConsent')?.checked;
      const submitBtn = document.getElementById('signupSubmitBtn');

      // Determine whether user opted for Anonymity Protection (affected individuals & families only)
      const isAnonymousMode = AFFECTED_ROLES.has(category) && Boolean(anonymityChoiceYes && anonymityChoiceYes.checked);

      // Client-side Validation
      if (!isAnonymousMode) {
        if (!fullName || fullName.length < 2) {
          showAlert(signupAlert, 'Please enter your full name (minimum 2 characters).');
          return;
        }

        if (!email || !email.includes('@')) {
          showAlert(signupAlert, 'Please enter a valid email address.');
          return;
        }
      } else {
        // In anonymous mode, email is optional. If provided, validate format.
        if (email && (!email.includes('@') || !email.includes('.'))) {
          showAlert(signupAlert, 'Please enter a valid email format or leave blank for instant Anonymous ID access.');
          return;
        }
      }

      if (!password || password.length < 8) {
        showAlert(signupAlert, 'Password must be at least 8 characters long.');
        return;
      }

      if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
        showAlert(signupAlert, 'Password must contain at least one letter and one number.');
        return;
      }

      if (password !== confirmPassword) {
        showAlert(signupAlert, 'Passwords do not match. Please re-enter.');
        return;
      }

      if (!category) {
        showAlert(signupAlert, 'Please select how you will use Mentaura.');
        return;
      }

      if (OFFICIAL_ROLES.has(category)) {
        if (!officialId || officialId.length < 4) {
          showAlert(signupAlert, 'Official ID / Government Credential is mandatory (min 4 characters).');
          if (officialIdInput) officialIdInput.focus();
          return;
        }
        if (!isOfficialIdVerified || officialId.toUpperCase() !== verifiedOfficialIdValue) {
          showAlert(signupAlert, 'Verifying Government Official ID credential...', 'info');
          const verified = await performOfficialIdVerification();
          if (!verified) {
            showAlert(signupAlert, 'Government Official ID verification must succeed before creating an official account.');
            if (officialIdInput) officialIdInput.focus();
            return;
          }
        }
      }

      if (!consentChecked) {
        showAlert(signupAlert, 'You must agree to the consent notice to create an account.');
        return;
      }

      // Submit to backend
      submitBtn.disabled = true;
      submitBtn.textContent = isAnonymousMode ? 'Creating Protected Anonymous Account...' : 'Creating Account & Sending OTP...';

      try {
        const response = await fetch('/api/auth/signup', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            full_name: isAnonymousMode ? (fullName || null) : fullName,
            email: isAnonymousMode ? (email || null) : email,
            password: password,
            confirm_password: confirmPassword,
            role: category,
            official_id: officialId || null,
            is_anonymous: isAnonymousMode,
            preferred_language: language,
            preferred_channel: channel,
            consent: true,
            consent_given: true,
            consent_version: '1.0',
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          showAlert(signupAlert, data.detail || 'Could not complete registration. Please try again.');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Create Support Account';
          return;
        }

        // Case A: Pure Anonymous Registration (Active immediately without OTP)
        if (data.account_status === 'active' && data.anonymous_id) {
          if (data.token) {
            localStorage.setItem('mentaura_token', data.token);
            localStorage.setItem('mentaura_user_role', data.verified_role || category);
            localStorage.setItem('mentaura_anonymous', 'true');
          }

          if (signupForm) signupForm.style.display = 'none';
          if (signupFooter) signupFooter.style.display = 'none';
          if (signupDesc) signupDesc.style.display = 'none';
          if (signupTitle) signupTitle.textContent = 'Protected Account Created';

          if (anonCreatedIdDisplay) {
            anonCreatedIdDisplay.textContent = data.anonymous_id;
          }
          if (anonSuccessSection) {
            anonSuccessSection.style.display = 'block';
          }

          if (copyAnonIdBtn) {
            copyAnonIdBtn.onclick = () => {
              if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(data.anonymous_id);
              }
              if (copyAnonIdBtnText) copyAnonIdBtnText.textContent = '✓ Copied!';
              setTimeout(() => {
                if (copyAnonIdBtnText) copyAnonIdBtnText.textContent = 'Copy Anonymous ID';
              }, 2500);
            };
          }

          if (anonProceedBtn) {
            anonProceedBtn.onclick = () => {
              window.location.href = data.redirect_url || 'victim-home.html';
            };
          }

          submitBtn.disabled = false;
          submitBtn.textContent = 'Create Support Account';
          return;
        }

        // Case B: Requires OTP verification (delivery email provided)
        localStorage.removeItem('mentaura_token');
        localStorage.removeItem('mentaura_anonymous');

        pendingSignupEmail = data.anonymous_id || email;
        if (signupForm) signupForm.style.display = 'none';
        if (signupFooter) signupFooter.style.display = 'none';
        if (signupDesc) signupDesc.style.display = 'none';
        if (signupTitle) signupTitle.textContent = data.anonymous_id ? 'Verify Anonymous Account' : 'Verify Your Email';

        if (otpTargetEmail) {
          otpTargetEmail.textContent = data.anonymous_id ? `Protected ID: ${data.anonymous_id}` : email;
        }
        if (otpSection) otpSection.style.display = 'block';
        if (otpCodeInput) {
          otpCodeInput.value = data.dev_otp || '';
          otpCodeInput.focus();
        }

        if (data.dev_otp) {
          showAlert(
            otpAlert,
            `<i class="fa-solid fa-key"></i> Verification Code: <strong style="font-size:16px;letter-spacing:2px;background:rgba(255,255,255,0.25);padding:2px 8px;border-radius:4px;">${data.dev_otp}</strong><br><small style="opacity:0.9;">Cloud hosting firewall blocks SMTP delivery. The verification code has been automatically filled for you.</small>`,
            'info'
          );
        } else {
          hideAlert(otpAlert);
        }

        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Support Account';

      } catch (err) {
        console.error('Signup Network Error:', err);
        showAlert(signupAlert, 'We could not connect to Mentaura right now. Please try again later.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Support Account';
      }
    });
  }

  // =========================================================================
  // 1b. OTP Verification Submission (Auto-Logs in ONLY Active Accounts)
  // =========================================================================
  if (otpVerificationForm) {
    otpVerificationForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(otpAlert);

      const code = otpCodeInput?.value.trim();
      const otpSubmitBtn = document.getElementById('otpSubmitBtn');

      if (!code || code.length !== 6 || !/^\d{6}$/.test(code)) {
        showAlert(otpAlert, 'Please enter a valid 6-digit numeric verification code.');
        if (otpCodeInput) otpCodeInput.focus();
        return;
      }

      otpSubmitBtn.disabled = true;
      otpSubmitBtn.textContent = 'Verifying Code...';

      try {
        const response = await fetch('/api/auth/verify-email-otp', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            email: pendingSignupEmail,
            otp: code,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          showAlert(otpAlert, data.detail || 'Invalid or expired verification code.');
          otpSubmitBtn.disabled = false;
          otpSubmitBtn.textContent = 'Verify Email & Continue';
          return;
        }

        // Branching based on verified account_status
        if (data.account_status === 'pending_verification') {
          showAlert(
            otpAlert,
            'Email verified successfully! Your official credentials have been submitted for administrator review.',
            'info'
          );
          otpSubmitBtn.textContent = 'Verification Pending...';
          otpSubmitBtn.disabled = true;
          setTimeout(() => {
            closeAllModals();
            window.location.href = data.redirect_url || '/verification-pending.html';
          }, 1400);
        } else if (data.account_status === 'active') {
          showAlert(otpAlert, 'Email verified successfully! Logging you in...', 'success');
          otpSubmitBtn.textContent = 'Redirecting to Dashboard...';
          otpSubmitBtn.disabled = true;

          // Store JWT token issued by backend on successful OTP verification
          if (data.token) {
            localStorage.setItem('mentaura_token', data.token);
          }
          localStorage.removeItem('mentaura_anonymous');

          setTimeout(() => {
            closeAllModals();
            const targetUrl = data.redirect_url ? (data.redirect_url.startsWith('/') ? data.redirect_url : '/' + data.redirect_url) : '/victim-home.html';
            window.location.href = targetUrl;
          }, 800);
        } else {
          showAlert(otpAlert, data.message || 'Email verified successfully.', 'info');
          otpSubmitBtn.disabled = false;
          otpSubmitBtn.textContent = 'Verify Email & Continue';
        }

      } catch (err) {
        console.error('OTP Verification Error:', err);
        showAlert(otpAlert, 'Could not verify code right now. Please try again.');
        otpSubmitBtn.disabled = false;
        otpSubmitBtn.textContent = 'Verify Email & Continue';
      }
    });
  }


  // Resend OTP button
  if (resendOtpBtn) {
    resendOtpBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      if (!pendingSignupEmail) {
        showAlert(otpAlert, 'Email address missing. Please go back and fill the form.');
        return;
      }

      resendOtpBtn.disabled = true;
      resendOtpBtn.textContent = 'Sending...';

      try {
        const res = await fetch('/api/auth/resend-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: pendingSignupEmail }),
        });
        const data = await res.json();
        if (data.dev_otp && otpCodeInput) {
          otpCodeInput.value = data.dev_otp;
        }
        if (data.dev_otp) {
          showAlert(
            otpAlert,
            `<i class="fa-solid fa-key"></i> New Verification Code: <strong style="font-size:16px;letter-spacing:2px;background:rgba(255,255,255,0.25);padding:2px 8px;border-radius:4px;">${data.dev_otp}</strong><br><small style="opacity:0.9;">Code has been automatically pre-filled.</small>`,
            'info'
          );
        } else {
          showAlert(otpAlert, data.message || 'A new verification code has been sent to your email.', 'info');
        }
      } catch (err) {
        showAlert(otpAlert, 'Could not resend verification code right now.');
      } finally {
        setTimeout(() => {
          resendOtpBtn.disabled = false;
          resendOtpBtn.textContent = 'Resend Code';
        }, 5000);
      }
    });
  }

  // Return to registration details from OTP view
  if (backToSignupForm) {
    backToSignupForm.addEventListener('click', (e) => {
      e.preventDefault();
      if (otpSection) otpSection.style.display = 'none';
      if (anonSuccessSection) anonSuccessSection.style.display = 'none';
      if (signupForm) signupForm.style.display = 'grid';
      if (signupFooter) signupFooter.style.display = 'block';
      if (signupDesc) signupDesc.style.display = 'block';
      if (signupTitle) signupTitle.textContent = 'Create a Mentaura Support Account';
      hideAlert(otpAlert);
      hideAlert(signupAlert);
    });
  }

  // =========================================================================
  // 2. Login Form Submission
  // =========================================================================
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(loginAlert);

      const email = document.getElementById('loginEmail')?.value.trim();
      const password = document.getElementById('loginPassword')?.value;
      const submitBtn = document.getElementById('loginSubmitBtn');

      if (!email || !password) {
        showAlert(loginAlert, 'Please provide both email address and password.');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Verifying Credentials...';

      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            email: email,
            password: password,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          showAlert(loginAlert, data.detail || 'The email or password is incorrect. Please try again.');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Log In Securely';
          return;
        }

        // Save JWT access token if provided
        if (data.token) {
          localStorage.setItem('mentaura_token', data.token);
        }

        // Success state
        showAlert(loginAlert, data.message, 'success');
        setTimeout(() => {
          window.location.href = data.redirect_url || '/victim-home.html';
        }, 800);

      } catch (err) {
        console.error('Login Network Error:', err);
        showAlert(loginAlert, 'We could not connect to Mentaura right now. Please try again later.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Log In Securely';
      }
    });
  }

  // =========================================================================
  // 3. Forgot Password Form Submission
  // =========================================================================
  if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAlert(forgotAlert);

      const email = document.getElementById('forgotEmail')?.value.trim();
      const submitBtn = document.getElementById('forgotSubmitBtn');

      if (!email || !email.includes('@')) {
        showAlert(forgotAlert, 'Please enter a valid email address.');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting Request...';

      try {
        const response = await fetch('/api/auth/forgot-password', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({ email: email }),
        });

        const data = await response.json();
        showAlert(forgotAlert, data.message, 'info');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Request Reset Link';
      } catch (err) {
        showAlert(forgotAlert, 'We could not reach the support service right now.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Request Reset Link';
      }
    });
  }

  // =========================================================================
  // 4. Hook Header & Page Buttons to Modals
  // =========================================================================
  const signupTriggerIds = [
    'headerSignUpBtn',
    'heroPrimaryCta',
    'ctaPrimaryBtn',
  ];

  signupTriggerIds.forEach((id) => {
    const btn = document.getElementById(id);
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        openSignupModal();
      });
    }
  });

  const loginTriggerIds = ['headerLoginBtn'];
  loginTriggerIds.forEach((id) => {
    const btn = document.getElementById(id);
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        openLoginModal();
      });
    }
  });

  // Mobile drawer buttons
  document.querySelectorAll('.mobile-actions .btn-secondary-pill').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openSignupModal();
    });
  });

  document.querySelectorAll('.mobile-actions .btn-outline-pill').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openLoginModal();
    });
  });

  // Switchers inside modals
  const switchToLoginBtn = document.getElementById('switchToLogin');
  if (switchToLoginBtn) {
    switchToLoginBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openLoginModal();
    });
  }

  const switchToSignupBtn = document.getElementById('switchToSignup');
  if (switchToSignupBtn) {
    switchToSignupBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openSignupModal();
    });
  }

  const openForgotBtn = document.getElementById('openForgotPassword');
  if (openForgotBtn) {
    openForgotBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openForgotPasswordModal();
    });
  }

  const backToLoginBtn = document.getElementById('backToLogin');
  if (backToLoginBtn) {
    backToLoginBtn.addEventListener('click', (e) => {
      e.preventDefault();
      openLoginModal();
    });
  }

  // Check URL parameters (e.g. ?login=true or ?auth_required=true)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('login') || urlParams.has('auth_required')) {
    openLoginModal();
    if (urlParams.has('auth_required')) {
      showAlert(loginAlert, 'Please log in with your verified account to access that page.', 'info');
    }
  } else if (urlParams.has('signup')) {
    openSignupModal();
  }
});
