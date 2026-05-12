/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  // hoverOnlyWhenSupported : les variantes `hover:` ne s'appliquent que sur
  // les devices qui supportent vraiment le hover (pointer fine). Élimine
  // les états "hover stuck" sur mobile après tap, qui faisaient parfois
  // sauter le premier tap (le user devait taper deux fois).
  future: {
    hoverOnlyWhenSupported: true,
  },
  theme: {
    extend: {
      colors: {
        // Palette alignée sur Football Bingo (couleurs scrappées de leur
        // CSS : body dark = #1e0d30, gradient vers #b837c6).
        bingo: {
          bg: '#1e0d30',                // exact FB body bg dark mode (au lieu du quasi-noir)
          bgGradient: '#b837c6',        // accent magenta du gradient FB
          header: '#3b3aff',
          headerLight: '#5857ff',
          banner: '#3a3aef',
          playerBand: '#3b3aff',
          playerBandLight: '#5554ff',
          cell: '#cce83e',              // lime — case correcte
          cellEmpty: '#2c1f3f',         // case vide sombre — relevé pour mieux ressortir sur le bg
          cellEmptyLight: '#3a2956',    // case vide claire — checkerboard plus lisible
          cellLocked: '#e85f5f',
          accent: '#cce83e',
          textDark: '#111118',
          // Le label de cellule passe en blanc franc (cf. GridCell.vue) ;
          // ce token reste pour les sous-labels et tags secondaires.
          textMuted: '#cdb8e3',
        },
      },
      fontFamily: {
        bebas: ['"Bebas Neue"', 'Impact', 'sans-serif'],
        display: ['"Montserrat"', 'system-ui', 'sans-serif'],
        sans: ['"Montserrat"', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        cellIn: {
          '0%': { opacity: '0', transform: 'scale(0.92)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        // Animation "stamp" : la tuile inset apparaît avec un overshoot
        // (scale 0.6 → 1.08 → 1) + fade-in. Donne un feedback visuel net
        // au moment de la pose, plus marqué que cellIn.
        cellStamp: {
          '0%':   { opacity: '0', transform: 'scale(0.6)' },
          '55%':  { opacity: '1', transform: 'scale(1.08)' },
          '80%':  { opacity: '1', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'cell-in': 'cellIn 180ms ease-out forwards',
        'cell-stamp': 'cellStamp 280ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
      },
    },
  },
  plugins: [],
}
