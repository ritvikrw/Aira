const React = require('react')
const { render, screen, fireEvent } = require('@testing-library/react')
const { CallCard } = require('../frontend/src/components/calls/CallCard')

const baseCall = {
  session_id: 'sess-1',
  caller_id: null,
  caller_name: null,
  caller_phone: null,
  status: 'ended',
  call_start_time: new Date().toISOString(),
  call_end_time: null,
  call_duration_seconds: 120,
  call_category: 'Other',
  summary_text: null,
  key_topics: [],
  action_items: [],
  room_name: null,
}

describe('CallCard component', () => {
  test('renders caller name when provided', () => {
    const call = { ...baseCall, caller_name: 'John Doe' }
    render(React.createElement(CallCard, { call, isSelected: false, onClick: jest.fn() }))
    expect(screen.getByText('John Doe')).toBeInTheDocument()
  })

  test('renders phone number when no name', () => {
    const call = { ...baseCall, caller_phone: '+919876543210' }
    render(React.createElement(CallCard, { call, isSelected: false, onClick: jest.fn() }))
    expect(screen.getByText('+91 98765 43210')).toBeInTheDocument()
  })

  test('renders "Unknown caller" when neither name nor phone', () => {
    render(React.createElement(CallCard, { call: baseCall, isSelected: false, onClick: jest.fn() }))
    expect(screen.getByText('Unknown caller')).toBeInTheDocument()
  })

  test('shows "Live" badge for active calls', () => {
    const call = { ...baseCall, status: 'active' }
    render(React.createElement(CallCard, { call, isSelected: false, onClick: jest.fn() }))
    expect(screen.getByText('Live')).toBeInTheDocument()
  })

  test('shows "Action needed" badge when action_items exist and not active', () => {
    const call = { ...baseCall, action_items: ['Send invoice'] }
    render(React.createElement(CallCard, { call, isSelected: false, onClick: jest.fn() }))
    expect(screen.getByText('Action needed')).toBeInTheDocument()
  })

  test('shows "Callback requested" badge when action item contains "call back"', () => {
    const call = { ...baseCall, action_items: ['Please call back the client'] }
    render(React.createElement(CallCard, { call, isSelected: false, onClick: jest.fn() }))
    expect(screen.getByText('Callback requested')).toBeInTheDocument()
  })

  test('calls onClick handler on click', () => {
    const onClick = jest.fn()
    render(React.createElement(CallCard, { call: baseCall, isSelected: false, onClick }))
    fireEvent.click(screen.getByText('Unknown caller').closest('div[class*="px-4"]'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  test('shows selected border when isSelected=true', () => {
    const { container } = render(
      React.createElement(CallCard, { call: baseCall, isSelected: true, onClick: jest.fn() })
    )
    expect(container.firstChild.className).toContain('bg-white')
  })
})
