/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'luxarmonie': {
          terracotta: '#a98977',
          'terracotta-dark': '#8a6f60',
          'terracotta-light': '#c4a596',
          black: '#000000',
          white: '#ffffff',
          gray: {
            50: '#fafafa',
            100: '#f5f5f5',
            200: '#e5e5e5',
            300: '#d4d4d4',
            400: '#a3a3a3',
            500: '#737373',
            600: '#525252',
            700: '#404040',
            800: '#262626',
            900: '#171717',
          }
        }
      },
      fontFamily: {
        'inter': ['Inter', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        'title': '-0.04em',  // -4% pour les titres
        'body': '-0.03em',   // -3% pour le texte
      },
    },
  },
  plugins: [],
}
