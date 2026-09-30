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
        iris: {
          bg: '#080c14',
          card: 'rgba(15, 23, 42, 0.75)',
          border: 'rgba(148, 163, 184, 0.12)',
          cyan: '#06b6d4',
          indigo: '#6366f1',
          emerald: '#10b981',
          amber: '#f59e0b',
          crimson: '#ef4444',
          dark: '#0f172a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Outfit', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px rgba(6, 182, 212, 0.25)',
        'glow-lg': '0 0 35px rgba(6, 182, 212, 0.35)',
        'glow-indigo': '0 0 25px rgba(99, 102, 241, 0.3)',
      }
    },
  },
  plugins: [],
}
