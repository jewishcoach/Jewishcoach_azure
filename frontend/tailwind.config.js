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
          DEFAULT: '#0f172a', // slate-900 - Deep wisdom
          light: '#1e293b',   // slate-800
          dark: '#020617',    // slate-950
        },
        accent: {
          DEFAULT: '#f59e0b', // amber-500 - Gold sparks
          light: '#fbbf24',   // amber-400
          dark: '#d97706',    // amber-600
        },
        cream: {
          DEFAULT: '#fafaf9', // stone-50
          dark: '#f5f5f4',    // stone-100
        }
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
        'glow': '0 0 20px rgba(245, 158, 11, 0.3)',
      },
      backdropBlur: {
        'xs': '2px',
      }
    },
  },
  plugins: [],
}

