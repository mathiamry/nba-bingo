/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        // Palette inspirée du screenshot Football Bingo
        bingo: {
          bg: '#0d0d12',                // fond très sombre
          header: '#3b3aff',            // bandeau bleu/violet du titre
          headerLight: '#5857ff',       // nuance plus claire pour dégradé header
          banner: '#3a3aef',            // bandeau "Play Football Games at..."
          playerBand: '#3b3aff',        // même teinte que header — ribbon joueur
          playerBandLight: '#5554ff',   // nuance plus claire pour dégradé ribbon
          cell: '#cce83e',              // lime légèrement désaturé — moins acide, contraste ✓
          cellEmpty: '#1e1a30',         // case vide "sombre" — purple plus profond
          cellEmptyLight: '#2d2748',    // case vide "claire" — écart plus lisible
          cellLocked: '#e85f5f',        // rouge — cases ratées
          accent: '#cce83e',
          textDark: '#111118',
          textMuted: '#b8a8cc',         // légèrement plus saturé — moins lavé sur fond sombre
        },
      },
      fontFamily: {
        display: ['"Montserrat"', 'system-ui', 'sans-serif'],
        sans: ['"Montserrat"', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        cellIn: {
          '0%': { opacity: '0', transform: 'scale(0.92)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'cell-in': 'cellIn 180ms ease-out forwards',
      },
    },
  },
  plugins: [],
}
