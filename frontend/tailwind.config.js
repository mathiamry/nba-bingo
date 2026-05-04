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
          banner: '#3a3aef',            // bandeau "Play Football Games at..."
          cell: '#d3f04a',              // lime — cases validées (correct)
          cellEmpty: '#1c1c25',         // case vide "sombre" du plateau
          cellEmptyLight: '#262631',    // case vide "claire" — alternance checkerboard
          cellLocked: '#e85f5f',        // rouge — cases ratées
          accent: '#d3f04a',
          textDark: '#0d0d12',
          textMuted: '#9ca3af',
        },
      },
      fontFamily: {
        display: ['"Inter"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
