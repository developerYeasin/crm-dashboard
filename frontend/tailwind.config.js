/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0a',
          800: '#1a1a1a',
          700: '#2a2a2a',
          600: '#3a3a3a',
          500: '#4a4a4a',
          400: '#5a5a5a',
          300: '#8a8a8a',
          200: '#b0b0b0',
          100: '#d0d0d0',
        },
        primary: {
          400: '#a855f7',
          500: '#a855f7',
          600: '#ec4899',
          700: '#be185d',
        },
      },
    },
  },
  plugins: [],
}
