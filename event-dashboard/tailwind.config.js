/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: '#030712',
          surface: '#090d1a',
          card: '#0f172a',
          card2: '#020617',
          panel: '#0b192c',
          border: 'rgba(34, 211, 238, 0.2)',
          'border-hover': 'rgba(34, 211, 238, 0.45)',
          cyan: '#22d3ee',
          pink: '#ec4899',
          violet: '#818cf8',
        },
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        navy: {
          800: '#111c38',
          900: '#0b1329',
          950: '#070c1b',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        orbitron: ['Orbitron', 'sans-serif'],
        grotesk: ['"Space Grotesk"', 'sans-serif'],
        syne: ['Syne', 'sans-serif'],
        mono: ['"Fira Code"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        card: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'cyber-cyan': '0 0 20px rgba(6, 182, 212, 0.35)',
        'cyber-glow': '0 0 30px rgba(34, 211, 238, 0.2)',
        'cyber-pink': '0 0 20px rgba(236, 72, 153, 0.35)',
      },
    },
  },
  plugins: [],
}
