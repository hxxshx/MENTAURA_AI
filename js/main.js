/**
 * MENTAURA — Case-Aware Support Intelligence Platform
 * Main Client Script (js/main.js)
 * Clean, lightweight vanilla JS handling navigation, accessibility, and UI interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
  // =========================================================================
  // 1. Language Selector Dropdown
  // =========================================================================
  const langSelectorBtn = document.getElementById('langSelectorBtn');
  const langDropdown = document.getElementById('langDropdown');
  const selectedLangText = document.getElementById('selectedLangText');

  if (langSelectorBtn && langDropdown) {
    // Toggle dropdown
    langSelectorBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = langDropdown.classList.contains('show');
      langDropdown.classList.toggle('show');
      langSelectorBtn.setAttribute('aria-expanded', String(!isOpen));
    });

    // Option selection
    langDropdown.querySelectorAll('li').forEach((item) => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        const langCode = item.getAttribute('data-lang');
        if (selectedLangText) {
          selectedLangText.textContent = langCode;
        }

        // Update active state
        langDropdown.querySelectorAll('li').forEach((li) => {
          li.classList.remove('active');
          li.setAttribute('aria-selected', 'false');
        });
        item.classList.add('active');
        item.setAttribute('aria-selected', 'true');

        // Close dropdown
        langDropdown.classList.remove('show');
        langSelectorBtn.setAttribute('aria-expanded', 'false');
        langSelectorBtn.focus();
      });
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!langSelectorBtn.contains(e.target) && !langDropdown.contains(e.target)) {
        langDropdown.classList.remove('show');
        langSelectorBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && langDropdown.classList.contains('show')) {
        langDropdown.classList.remove('show');
        langSelectorBtn.setAttribute('aria-expanded', 'false');
        langSelectorBtn.focus();
      }
    });
  }

  // =========================================================================
  // 2. Mobile Hamburger Navigation Drawer
  // =========================================================================
  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const mobileMenuDrawer = document.getElementById('mobileMenuDrawer');

  if (mobileMenuToggle && mobileMenuDrawer) {
    mobileMenuToggle.addEventListener('click', () => {
      const isOpen = mobileMenuDrawer.classList.contains('open');
      mobileMenuDrawer.classList.toggle('open');
      mobileMenuToggle.classList.toggle('active');
      mobileMenuToggle.setAttribute('aria-expanded', String(!isOpen));
      mobileMenuDrawer.setAttribute('aria-hidden', String(isOpen));
    });

    // Close mobile menu when any mobile link is clicked
    mobileMenuDrawer.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        mobileMenuDrawer.classList.remove('open');
        mobileMenuToggle.classList.remove('active');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
        mobileMenuDrawer.setAttribute('aria-hidden', 'true');
      });
    });
  }

  // =========================================================================
  // 3. Smooth Scrolling & Active Nav Link Observer
  // =========================================================================
  const navLinks = document.querySelectorAll('.nav-links .nav-link, .mobile-nav-links .mobile-nav-link');
  const sections = [
    { id: 'hero', navId: 'nav-home' },
    { id: 'how-it-works', navId: 'nav-how' },
    { id: 'support-services', navId: 'nav-services' },
    { id: 'resources', navId: 'nav-resources' },
    { id: 'privacy-safety', navId: 'nav-privacy' },
  ];

  // Smooth scroll handler for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      
      // Handle Home link specifically to scroll to top
      if (targetId === '#hero' || targetId === '#') {
        e.preventDefault();
        window.scrollTo({
          top: 0,
          behavior: 'smooth',
        });
        return;
      }

      // Handle placeholder links
      if (targetId === '#signup-placeholder' || targetId === '#login-placeholder') {
        e.preventDefault();
        showToast('Authentication & portal features will be enabled in the next stage.');
        return;
      }

      const targetElem = document.querySelector(targetId);
      if (targetElem) {
        e.preventDefault();
        const headerOffset = 80;
        const elementPosition = targetElem.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth',
        });
      }
    });
  });

  // Active section observer on scroll
  const sectionElements = sections
    .map((s) => ({ elem: document.getElementById(s.id), navId: s.navId }))
    .filter((s) => s.elem !== null);

  function updateActiveNav() {
    const scrollPosition = window.scrollY + 120;

    sectionElements.forEach((item) => {
      const top = item.elem.offsetTop;
      const height = item.elem.offsetHeight;

      if (scrollPosition >= top && scrollPosition < top + height) {
        navLinks.forEach((link) => link.classList.remove('active'));
        const activeDesktopLink = document.getElementById(item.navId);
        if (activeDesktopLink) {
          activeDesktopLink.classList.add('active');
        }
      }
    });

    // If at top of page, ensure Home is active
    if (window.scrollY < 200) {
      navLinks.forEach((link) => link.classList.remove('active'));
      const homeLink = document.getElementById('nav-home');
      if (homeLink) homeLink.classList.add('active');
    }
  }

  window.addEventListener('scroll', updateActiveNav, { passive: true });

  // =========================================================================
  // 4. Toast Notification Utility (for placeholder actions)
  // =========================================================================
  const toastNotification = document.getElementById('toastNotification');
  const toastMessage = document.getElementById('toastMessage');
  let toastTimer = null;

  function showToast(message) {
    if (!toastNotification) return;

    if (toastMessage && message) {
      toastMessage.textContent = message;
    }

    toastNotification.classList.add('show');

    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastNotification.classList.remove('show');
    }, 3200);
  }

  // Hook placeholder buttons to toast
  const placeholderButtons = [
    'headerSignUpBtn',
    'headerLoginBtn',
    'heroPrimaryCta',
    'ctaPrimaryBtn',
  ];

  placeholderButtons.forEach((btnId) => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        showToast('Account creation & login will be introduced in the next module.');
      });
    }
  });
});
