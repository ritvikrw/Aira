import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'accent' | 'primary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

const variantClasses = {
  accent:  'bg-accent-500 text-white hover:bg-accent-600 border border-accent-500',
  primary: 'bg-accent-500 text-white hover:bg-accent-600 border border-accent-500',
  outline: 'bg-white text-ink-700 hover:bg-brand-50 border border-brand-300',
  ghost:   'bg-transparent text-ink-600 hover:bg-brand-100 border border-transparent',
  danger:  'bg-red-600 text-white hover:bg-red-700 border border-red-600',
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
}

export function Button({
  variant = 'accent',
  size = 'md',
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`
        inline-flex items-center gap-1.5 font-medium rounded-lg transition-colors
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  )
}

export default Button
