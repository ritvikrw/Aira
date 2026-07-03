import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          50:  '#0B1622',
          100: '#111E2E',
          200: '#162335',
          300: '#1F3450',
          400: '#2A4A6E',
        },
        slate: {
          400: '#5E7A95',
          300: '#8BA4BC',
          200: '#C4D4E3',
          100: '#EDF2F7',
        },
        accent: {
          500: '#C4621A',
          400: '#E06B28',
          300: '#EE9150',
        },
        teal: {
          500: '#00C9A7',
          400: '#2DD4B8',
        },
        red:   '#FF5F6D',
        amber: '#F5A623',
        green: '#2DD4A7',
      },
    },
  },
  plugins: [],
}

export default config
