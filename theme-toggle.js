/**
 * theme-toggle.js
 * Include this script on ANY page to get a floating theme toggle button.
 * It auto-injects the button, applies saved theme, and handles toggling.
 * Uses localStorage key 'app-theme' shared across all pages.
 */
(function () {
    // 1. Apply saved theme IMMEDIATELY (before paint)
    var saved = localStorage.getItem('app-theme');
    if (saved === 'light') {
        document.body.classList.add('light-mode');
    }

    var existingBtn = document.getElementById('themeToggleBtn');
    var btn = existingBtn;

    // 2. If no button exists in HTML, create the floating one
    if (!existingBtn) {
        btn = document.createElement('button');
        btn.id = 'themeToggleBtn';
        btn.className = 'theme-toggle-btn';
        btn.title = 'Toggle Light/Dark Mode';
        btn.setAttribute('aria-label', 'Toggle Light/Dark Mode');

        // Sun icon (shown in light mode)
        var sunSvg = '<svg class="icon-sun" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>';

        // Moon icon (shown in dark mode)
        var moonSvg = '<svg class="icon-moon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';

        btn.innerHTML = sunSvg + moonSvg;
        document.body.appendChild(btn);
    }

    // 3. Click handler (works for both existing and newly created buttons)
    btn.addEventListener('click', function () {
        document.body.classList.toggle('light-mode');
        var isLight = document.body.classList.contains('light-mode');
        localStorage.setItem('app-theme', isLight ? 'light' : 'dark');
    });
})();
