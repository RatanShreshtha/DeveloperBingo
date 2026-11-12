# Tailwind CSS and daisyUI for frontend styling

**Status:** accepted

**Context:** The Vue frontend needs consistent, responsive styling across hosting, playing, pool editing, and game history while retaining existing game interactions and accessibility.

**Decision:** Use Tailwind CSS 4 with its Vite plugin and daisyUI 5. Configure the built-in light and dark themes in CSS to follow the operating system preference, without a theme toggle. Use daisyUI classes and Tailwind utilities directly in Vue templates; use scoped CSS when an app-specific layout needs it.

**Why:** daisyUI supplies consistent components and theme tokens without requiring a separate Vue component library. Tailwind utilities cover layout and responsive behavior while the Vite integration keeps configuration in CSS.

**Consequences:** Frontend builds depend on Tailwind and daisyUI. Component markup and utilities must continue to preserve semantic controls, keyboard access, and readable game states. The nine-column ticket needs a horizontally scrollable, keyboard-focusable region on narrow screens.
