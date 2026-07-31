export default defineAppConfig({
  ui: {
    // Points Nuxt UI's `primary` alias at the accent scale in main.css.
    // Without this it falls back to its default green, so buttons clashed
    // with the accent used everywhere else.
    colors: {
      primary: 'accent',
      neutral: 'slate',
    },
    button: {
      // Every button here is either the safelight or invisible, and both should
      // feel physical under the pointer.
      slots: {
        base: 'font-medium transition-all duration-200 active:scale-[0.97]',
      },
    },
  },
})
