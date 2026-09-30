/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        nle: {
          bg: '#121212',
          panel: '#1e1e1e',
          panelLight: '#2a2a2a',
          border: '#333333',
          borderHover: '#444444',
          text: '#e0e0e0',
          textMuted: '#9e9e9e',
          accent: '#2b82d9',
          accentHover: '#3b92e9',
          warning: '#f39c12',
          trackBg: '#181818',
          trackAltBg: '#222222',
        },
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
      },
      fontSize: {
        'nle-xs': '10px',
        'nle-sm': '12px',
        'nle-base': '13px',
      },
      fontFamily: {
        nle: ['Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'sans-serif'],
      },
    },
  },
  plugins: [],
};