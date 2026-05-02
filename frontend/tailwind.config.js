/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        // Palette inspirée du screenshot Football Bingo
        bingo: {
          bg: '#0d0d12',           // fond très sombre
          header: '#3b3aff',       // bandeau bleu/violet du titre
          banner: '#3a3aef',       // bandeau "Play Football Games at..."
          cell: '#d3f04a',         // lime — cases validées (correct)
          cellEmpty: '#1f1f28',    // gris foncé — cases pas encore jouées
          cellLocked: '#e85f5f',   // rouge — cases ratées
          accent: '#d3f04a',       // accent lime pour CTA
          textDark: '#0d0d12',     // texte noir sur fond lime
          textMuted: '#9ca3af',    // gris clair sur cases vides
        },
      },
      fontFamily: {
        display: ['"Inter"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
