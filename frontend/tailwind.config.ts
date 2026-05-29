import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#FDF8F3',
          100: '#FAF0E6',
          200: '#F0EAE0',
          300: '#E5DDD4',
          400: '#C9B8A8',
          500: '#A89580',
          600: '#8B7355',
          700: '#6B5340',
          800: '#4A3728',
          900: '#2A1F14',
        },
        accent: {
          50: '#FDF4EC',
          100: '#FBDFC4',
          200: '#F5BB88',
          300: '#EE9150',
          400: '#E06B28',
          500: '#C4621A',
          600: '#A3500F',
          700: '#7D3D09',
          800: '#562906',
          900: '#2E1503',
        },
        ink: {
          50: '#F5F4F3',
          100: '#E8E5E3',
          200: '#D1CBC6',
          300: '#B0A69E',
          400: '#897D74',
          500: '#6B5E55',
          600: '#544940',
          700: '#3D342C',
          800: '#2A221C',
          900: '#1C1917',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
