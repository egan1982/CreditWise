/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./assets/**/*.html",
    "./scripts/**/*.{js,ts}",
    "./components/**/*.{js,ts}",
    "./styles/**/*.{css,scss}",
  ],
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Inter', 'Microsoft YaHei', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}