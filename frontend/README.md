# Frontend

Vue app for DeveloperBingo. See the root `README.md` for how to run and test it.

## Styling

The frontend uses Tailwind CSS 4 and daisyUI 5 via the Vite plugin. Add daisyUI
component classes and Tailwind utilities directly in Vue templates; use scoped
CSS only when an app-specific layout needs it. The built-in `light` and `dark`
themes follow the operating system's color preference. Theme configuration lives
in `src/style.css`.

The player's nine-column ticket scrolls horizontally on narrow screens. Keep
the scroll region keyboard-focusable and ticket topics readable when disabled.
