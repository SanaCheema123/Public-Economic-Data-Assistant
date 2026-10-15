/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ivory: '#FAF7F2', sand: '#F5EBE1', mist: '#EDEEE9', taupe: '#D6CCC2', blush: '#D7BDB0', clay: '#A98773', ink: '#151E2D'
      },
      boxShadow: { soft: '0 20px 60px rgba(67,49,39,.08)', card: '0 10px 30px rgba(67,49,39,.055)' },
      borderRadius: { '4xl': '2rem' }
    }
  },
  plugins: []
}
