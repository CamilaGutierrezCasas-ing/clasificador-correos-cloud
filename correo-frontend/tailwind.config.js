/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          red: '#9E0B16',
          redDark: '#7D0A12',
          cream: '#F3ECDD',
          blueSoft: '#6E8C95',
          blue: '#355D6E',
          blueDark: '#183D4D',
        },
      },
      boxShadow: {
        soft: '0 10px 35px rgba(24, 61, 77, 0.12)',
      },
    },
  },
  plugins: [],
};