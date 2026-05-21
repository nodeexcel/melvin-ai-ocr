/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          yellow: '#F5C518',
          black: '#1A1A1A',
          gray: '#2A2A2A',
          lightgray: '#3A3A3A',
        },
      },
    },
  },
  plugins: [],
}
