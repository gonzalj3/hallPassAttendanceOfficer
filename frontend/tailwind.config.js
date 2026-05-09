/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#079da8',
          50: '#e8f5f6',
          100: '#d1ecee',
          200: '#a3d9dd',
          300: '#75c5cc',
          400: '#47b2bb',
          500: '#079da8',
          600: '#068090',
          700: '#056778',
          800: '#044d5e',
          900: '#033445',
        },
        emergency: '#dc2626',
        background: '#f0f0ea',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '8px',
      },
      minHeight: {
        touch: '44px',
      },
    },
  },
  plugins: [],
}
