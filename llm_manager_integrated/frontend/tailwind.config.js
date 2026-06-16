/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./scripts/**/*.{js,ts}",
    "./shared/**/*.{js,ts}",
    "./components/**/*.{js,ts}",
    "./styles/**/*.{css,scss}",
  ],
  // safelist 确保动态拼接class、@apply引用的utility class不被purge
  safelist: [
    { pattern: /^(bg|text|border|ring|from|to|via)-/ },
    { pattern: /^(p|m|px|py|pt|pb|pl|pr|mx|my|mt|mb|ml|mr)-/ },
    { pattern: /^(w|h|min-w|min-h|max-w|max-h)-/ },
    { pattern: /^(flex|grid|block|inline|hidden|visible)/ },
    { pattern: /^(rounded|shadow|opacity|cursor|overflow|z)-/ },
    { pattern: /^(font|text|leading|tracking)-/ },
    { pattern: /^(justify|items|content|self|place)-/ },
    { pattern: /^(gap|space)-/ },
    { pattern: /^(fixed|absolute|relative|sticky|static)$/ },
    { pattern: /^(top|right|bottom|left|inset)-/ },
    { pattern: /^(transition|duration|ease|delay|animate)-/ },
    { pattern: /^(hover|focus|active|disabled):/ },
    'antialiased', 'container', 'mx-auto',
  ],
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Inter', 'Microsoft YaHei', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}