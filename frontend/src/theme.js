import { createTheme } from '@mui/material/styles';

// ─────────────────────────────────────────────────────────────
// Livestock Health — design theme (C0: Pine + Ochre on Sage mist)
// Changing values here restyles the whole app. No component logic
// depends on this file — it's purely visual.
// ─────────────────────────────────────────────────────────────

const PINE = '#1F5244';
const PINE_DARK = '#163A30';
const PINE_LIGHT = '#3C7A68';
const OCHRE = '#C4893D';
const OCHRE_DARK = '#A06F2E';
const OCHRE_LIGHT = '#E0B06A';

const BG = '#E8ECE6';       // sage mist canvas
const CARD = '#FFFFFF';
const INK = '#1B241F';
const MUTED = '#5C6862';
const LINE = 'rgba(27,36,31,0.10)';

const SANS = '"Plus Jakarta Sans","-apple-system","BlinkMacSystemFont","Segoe UI","Roboto","Helvetica","Arial",sans-serif';
const SERIF = '"Fraunces","Georgia","Times New Roman",serif';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary:   { main: PINE, dark: PINE_DARK, light: PINE_LIGHT, contrastText: '#FFFFFF' },
    secondary: { main: OCHRE, dark: OCHRE_DARK, light: OCHRE_LIGHT, contrastText: '#1B241F' },
    success:   { main: '#2E7D5B', contrastText: '#FFFFFF' },
    warning:   { main: '#C77D34', contrastText: '#FFFFFF' },
    error:     { main: '#B4432C', contrastText: '#FFFFFF' },
    info:      { main: PINE, contrastText: '#FFFFFF' },
    background: { default: BG, paper: CARD },
    text: { primary: INK, secondary: MUTED },
    divider: LINE,
  },

  shape: { borderRadius: 12 },

  typography: {
    fontFamily: SANS,
    // Display / headings use the warm serif, kept for larger sizes only
    h1: { fontFamily: SERIF, fontWeight: 600, letterSpacing: '-0.02em' },
    h2: { fontFamily: SERIF, fontWeight: 600, letterSpacing: '-0.02em' },
    h3: { fontFamily: SERIF, fontWeight: 600, letterSpacing: '-0.02em' },
    h4: { fontFamily: SERIF, fontWeight: 600, letterSpacing: '-0.015em' },
    h5: { fontFamily: SANS, fontWeight: 700, letterSpacing: '-0.01em' },
    h6: { fontFamily: SANS, fontWeight: 700 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600, letterSpacing: 0 },
    caption: { color: MUTED },
  },

  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: BG,
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale',
        },
      },
    },

    // Cards / surfaces: hairline border + soft shadow, no MUI elevation gradient
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${LINE}`,
          boxShadow: '0 1px 2px rgba(16,24,20,0.04), 0 6px 20px rgba(16,24,20,0.05)',
        },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: `1px solid ${LINE}`,
          boxShadow: '0 1px 2px rgba(16,24,20,0.04), 0 6px 20px rgba(16,24,20,0.05)',
        },
      },
    },
    MuiCardContent: {
      styleOverrides: { root: { padding: 22, '&:last-child': { paddingBottom: 22 } } },
    },

    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 10, paddingTop: 9, paddingBottom: 9, paddingLeft: 18, paddingRight: 18 },
        containedPrimary: { '&:hover': { backgroundColor: PINE_DARK } },
      },
    },

    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 500 },
        outlined: { borderColor: LINE },
      },
    },

    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          '& fieldset': { borderColor: LINE },
          '&:hover fieldset': { borderColor: 'rgba(27,36,31,0.2)' },
        },
      },
    },

    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: LINE },
        head: { fontWeight: 700, color: INK, backgroundColor: 'rgba(31,82,68,0.04)' },
      },
    },

    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 999, height: 8, backgroundColor: 'rgba(27,36,31,0.08)' },
        bar: { borderRadius: 999 },
      },
    },

    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 12, border: `1px solid ${LINE}` },
        standardInfo: { backgroundColor: 'rgba(31,82,68,0.05)', color: '#31473f' },
        standardWarning: { backgroundColor: 'rgba(196,137,61,0.10)', color: '#6b5124' },
      },
    },
  },
});

export default theme;
