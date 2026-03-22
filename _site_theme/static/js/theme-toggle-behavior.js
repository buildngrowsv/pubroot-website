/**
 * =============================================================================
 * Pubroot — Theme Toggle Behavior (Dark/Light Mode)
 * =============================================================================
 *
 * PURPOSE:
 * This script powers the dark/light mode toggle button in the site header.
 * It manages the data-theme attribute on <html>, persists the user's
 * preference to localStorage, and updates the theme-color meta tag so
 * the browser chrome (address bar, tab bar) matches the selected theme.
 *
 * HOW IT WORKS:
 * 1. An inline anti-flash script in <head> (NOT this file) reads localStorage
 *    and sets data-theme="dark" immediately before first paint. This prevents
 *    the flash-of-wrong-theme (FOWT) that happens when JS loads after CSS.
 * 2. This file runs after DOMContentLoaded and sets up the toggle button's
 *    click handler. The button is a <button id="theme-toggle"> element in
 *    the header with two Lucide icons inside — moon (light mode) and sun
 *    (dark mode). CSS in main.css toggles their visibility based on
 *    [data-theme="dark"], so this JS doesn't need to touch icons at all.
 * 3. When toggled, this script:
 *    a. Flips data-theme on <html>
 *    b. Saves the preference to localStorage (key: 'pubroot-theme')
 *    c. Updates <meta name="theme-color"> for browser chrome matching
 *
 * WHY SEPARATE FILE:
 * - The anti-flash inline script MUST be in <head> (render-blocking by design)
 * - The toggle behavior script can be deferred (loaded after DOM is ready)
 * - Keeping them separate makes the inline script minimal (~200 bytes) while
 *   this behavior file has full comments and maintainability
 *
 * BROWSER SUPPORT:
 * - Works in all modern browsers (Chrome, Firefox, Safari, Edge)
 * - Uses localStorage (supported since IE8, universally available)
 * - Uses window.matchMedia for system preference detection (Chrome 9+, FF 6+)
 * - Gracefully degrades: if localStorage or matchMedia aren't available,
 *   defaults to light mode with no toggle persistence
 *
 * LOADED BY:
 * Every page on the site — baseof.html, index.html, and all static HTML pages
 * include a <script src="/js/theme-toggle-behavior.js"></script> tag at the
 * bottom of <body>, just after the Lucide icon initialization.
 *
 * DEPENDS ON:
 * - #theme-toggle button element in the page header
 * - data-theme attribute on <html> (set by anti-flash script or this script)
 * - CSS variables in main.css that respond to [data-theme="dark"]
 * =============================================================================
 */

document.addEventListener('DOMContentLoaded', function() {
  /**
   * THEME TOGGLE CLICK HANDLER
   * --------------------------
   * Finds the #theme-toggle button and attaches a click listener.
   * If the button doesn't exist (e.g., in an error page), this
   * script silently does nothing — it doesn't throw or log errors.
   */
  var toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;

  /**
   * getCurrentTheme
   * Returns 'dark' or 'light' based on the current data-theme attribute.
   * Falls back to 'light' if the attribute is not set or is empty.
   */
  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  /**
   * setTheme
   * Sets the theme on the <html> element, persists to localStorage,
   * and updates the browser chrome color via <meta name="theme-color">.
   *
   * @param {string} theme - Either 'dark' or 'light'
   *
   * WHY data-theme ATTRIBUTE (not class):
   * We use data-theme on <html> instead of a body class because:
   * 1. It's set before <body> even exists (anti-flash script runs in <head>)
   * 2. It's a semantic attribute (data-* attributes are for custom data)
   * 3. CSS [data-theme="dark"] selectors are fast and unambiguous
   * 4. Doesn't interfere with any class-based styling on <html> or <body>
   */
  function setTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    /* Persist the user's explicit choice to localStorage.
       The anti-flash script reads this on next page load to set the
       theme before first paint, preventing flash-of-wrong-theme. */
    try {
      localStorage.setItem('pubroot-theme', theme);
    } catch (e) {
      /* localStorage may be blocked in private browsing modes
         or by strict browser policies. Silently ignore — the toggle
         will still work for the current session, just won't persist. */
    }

    /* Update browser chrome color (address bar in mobile browsers,
       PWA title bar, etc.) to match the selected theme. The teal
       #00B4A0 matches light mode's brand color; the dark #0F1117
       matches dark mode's --bg variable. */
    var metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', theme === 'dark' ? '#0F1117' : '#00B4A0');
    }
  }

  /**
   * Toggle click handler — flips between dark and light.
   * Simple binary toggle; we don't have a "system" mode (yet).
   * If users want to follow system preference, they can clear
   * localStorage and the anti-flash script will respect prefers-color-scheme.
   */
  toggleBtn.addEventListener('click', function() {
    var current = getCurrentTheme();
    setTheme(current === 'dark' ? 'light' : 'dark');
  });

  /**
   * SYSTEM PREFERENCE CHANGE LISTENER
   * ----------------------------------
   * If the user hasn't explicitly chosen a theme (no localStorage entry),
   * we follow the OS dark/light preference. This listener handles the
   * case where the user changes their OS preference while the page is open.
   *
   * IMPORTANT: This only fires if there's NO stored preference. Once
   * the user clicks the toggle, their explicit choice overrides the
   * system preference permanently (until they clear localStorage).
   */
  try {
    var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', function(e) {
      /* Only follow system preference if user hasn't made an explicit choice */
      var stored = localStorage.getItem('pubroot-theme');
      if (!stored) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });
  } catch (e) {
    /* matchMedia.addEventListener may not be supported in very old browsers.
       Not critical — the toggle button still works for manual switching. */
  }
});
