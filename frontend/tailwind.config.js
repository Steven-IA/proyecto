export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b1220',
        panel: '#111a2e',
        accent: '#3b82f6',
        cyan: '#06b6d4',
        muted: '#64748b'
      },
      boxShadow: {
        card: '0 10px 30px rgba(0,0,0,0.25)'
      }
    }
  },
  plugins: []
}