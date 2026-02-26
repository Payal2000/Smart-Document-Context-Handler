/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        tier1: '#22c55e',
        tier2: '#3b82f6',
        tier3: '#f59e0b',
        tier4: '#ef4444',
      },
    },
  },
  plugins: [],
}
