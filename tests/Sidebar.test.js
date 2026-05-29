const React = require('react')
const { render, screen } = require('@testing-library/react')

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}))

// Mock next/link
jest.mock('next/link', () => {
  return function Link({ href, children, ...props }) {
    return React.createElement('a', { href, ...props }, children)
  }
})

// Mock fetch for sidebar data loading
beforeEach(() => {
  global.fetch = jest.fn().mockRejectedValue(new Error('no server'))
})
afterEach(() => {
  delete global.fetch
})

const { Sidebar } = require('../frontend/src/components/layout/Sidebar')

describe('Sidebar component', () => {
  test('renders "aira" logo text', () => {
    render(React.createElement(Sidebar))
    const elements = screen.getAllByText('aira')
    expect(elements.length).toBeGreaterThanOrEqual(1)
    expect(elements[0]).toBeInTheDocument()
  })

  test('renders Analytics navigation link', () => {
    render(React.createElement(Sidebar))
    expect(screen.getByText('Analytics')).toBeInTheDocument()
  })

  test('renders Call logs navigation link', () => {
    render(React.createElement(Sidebar))
    expect(screen.getByText('Call logs')).toBeInTheDocument()
  })

  test('renders Knowledge base navigation link', () => {
    render(React.createElement(Sidebar))
    expect(screen.getByText('Knowledge base')).toBeInTheDocument()
  })

  test('shows "Agent online" status', () => {
    render(React.createElement(Sidebar))
    expect(screen.getByText(/Agent online/i)).toBeInTheDocument()
  })
})
