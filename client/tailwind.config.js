/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        databricks: {
          red: '#FF3621',
          orange: '#FF6B35',
          dark: '#1B3139',
        }
      }
    },
  },
  plugins: [],
}