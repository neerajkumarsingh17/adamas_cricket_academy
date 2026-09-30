import colors from 'tailwindcss/colors'

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Single source of truth for the app's accent color — swap this
        // one alias instead of hunting down every brand-* class. Orange,
        // matching the academy's own uniform/crest branding (the public
        // landing and login pages already use this same orange, plus a
        // navy secondary — see those pages for where navy is used
        // directly rather than through this token).
        brand: colors.orange,
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
