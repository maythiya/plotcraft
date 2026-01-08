module.exports = {
  content: [
    './**/templates/**/*.html',
    '../../plotcraft/templates/**/*.html',
    '/code/plotcraft/templates/**/*.html',
    '/code/**/*.html',
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}
