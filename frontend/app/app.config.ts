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
      // Buttons stay flat: a colour change on hover, no lift and no glow, which is
      // what keeps the page reading as clean.
      slots: {
        base: 'font-medium transition-colors duration-200',
      },
    },
  },
})
