const React = require('react')
const { render, screen } = require('@testing-library/react')
const { Badge } = require('../frontend/src/components/ui/Badge')

describe('Badge component', () => {
  test('renders "Active" for status="active"', () => {
    render(React.createElement(Badge, { status: 'active' }))
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  test('renders "Ended" for status="ended"', () => {
    render(React.createElement(Badge, { status: 'ended' }))
    expect(screen.getByText('Ended')).toBeInTheDocument()
  })

  test('renders "Urgent" for status="urgent"', () => {
    render(React.createElement(Badge, { status: 'urgent' }))
    expect(screen.getByText('Urgent')).toBeInTheDocument()
  })

  test('renders raw status string for unknown status', () => {
    render(React.createElement(Badge, { status: 'custom-status' }))
    expect(screen.getByText('custom-status')).toBeInTheDocument()
  })

  test('applies custom className', () => {
    const { container } = render(React.createElement(Badge, { status: 'active', className: 'my-custom-class' }))
    expect(container.firstChild).toHaveClass('my-custom-class')
  })
})
