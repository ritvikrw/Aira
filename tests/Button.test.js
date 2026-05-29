const React = require('react')
const { render, screen, fireEvent } = require('@testing-library/react')
const { Button } = require('../frontend/src/components/ui/Button')

describe('Button component', () => {
  test('renders children', () => {
    render(React.createElement(Button, {}, 'Click me'))
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  test('disabled state adds opacity class', () => {
    const { container } = render(React.createElement(Button, { disabled: true }, 'Submit'))
    expect(container.firstChild).toHaveClass('opacity-50')
  })

  test('calls onClick when clicked', () => {
    const handleClick = jest.fn()
    render(React.createElement(Button, { onClick: handleClick }, 'Click'))
    fireEvent.click(screen.getByText('Click'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  test('does not call onClick when disabled', () => {
    const handleClick = jest.fn()
    render(React.createElement(Button, { onClick: handleClick, disabled: true }, 'Click'))
    fireEvent.click(screen.getByText('Click'))
    expect(handleClick).not.toHaveBeenCalled()
  })

  test('applies accent variant classes', () => {
    const { container } = render(React.createElement(Button, { variant: 'accent' }, 'Accent'))
    expect(container.firstChild.className).toContain('bg-accent-500')
  })

  test('applies danger variant classes', () => {
    const { container } = render(React.createElement(Button, { variant: 'danger' }, 'Danger'))
    expect(container.firstChild.className).toContain('bg-red-600')
  })

  test('applies outline variant classes', () => {
    const { container } = render(React.createElement(Button, { variant: 'outline' }, 'Outline'))
    expect(container.firstChild.className).toContain('bg-white')
  })

  test('applies sm size classes', () => {
    const { container } = render(React.createElement(Button, { size: 'sm' }, 'Small'))
    expect(container.firstChild.className).toContain('px-3')
  })

  test('applies md size classes', () => {
    const { container } = render(React.createElement(Button, { size: 'md' }, 'Medium'))
    expect(container.firstChild.className).toContain('px-4')
  })

  test('applies lg size classes', () => {
    const { container } = render(React.createElement(Button, { size: 'lg' }, 'Large'))
    expect(container.firstChild.className).toContain('px-5')
  })
})
