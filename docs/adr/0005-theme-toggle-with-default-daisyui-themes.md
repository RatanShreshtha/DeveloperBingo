# A light and dark theme toggle, with daisyUI's default themes

**Status:** accepted. Supersedes the theme choice in [ADR 0003](0003-tailwind-daisyui-for-styling.md).

**Context:** ADR 0003 kept the theme to the operating system's preference, with no toggle. A visitor who wants the other theme for a session has no way to choose it.

**Decision:** Add a light and dark toggle in the header. A visitor's choice is saved in the browser; until they choose, the operating system's preference applies. The choice is written to the page's `data-theme` attribute, and the Tailwind `dark:` variant reads that attribute. Both themes are daisyUI's built-in light and dark themes, with no overrides.

**Why:** The toggle lets a visitor pick the theme without changing their system setting. Reading one attribute keeps the daisyUI theme and the `dark:` variant in step, so the page never mixes the two. Using the built-in themes keeps the app in line with daisyUI's documentation and leaves no palette to maintain.

**Consequences:**
- Without JavaScript, the page shows the light theme. An inline script in `index.html` sets `data-theme` before the page first paints, so a visitor who chose dark, or whose system is dark, does not see a light flash. That script repeats the rule in `src/theme.ts`, because a module cannot run that early.
- Storage can be blocked. Then the theme still applies for the visit, but the choice is not kept.
- Any new `dark:` class follows the toggle, not the operating system.
