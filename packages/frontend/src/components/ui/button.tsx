import { forwardRef } from "react"
import { clsx } from "clsx"
import { cva, type VariantProps } from "class-variance-authority"
import { Spinner } from "./spinner"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-[var(--bg-surface)] disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary: "bg-[var(--brand)] text-[var(--text-on-brand)] hover:bg-[var(--brand-strong)] shadow-[var(--shadow-sm)]",
        secondary: "bg-[var(--bg-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)]",
        outline: "border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]",
        ghost: "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]",
        danger: "bg-[var(--danger)] text-white hover:opacity-90 shadow-[var(--shadow-sm)]",
        subtle: "bg-[var(--brand-soft)] text-[var(--brand-strong)] hover:bg-[color-mix(in_srgb,var(--brand-soft)_80%,var(--brand-border))]",
      },
      size: {
        sm: "px-3 py-1.5 text-xs",
        md: "px-4 py-2 text-sm",
        lg: "px-5 py-2.5 text-sm",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={clsx(buttonVariants({ variant, size }), className)}
        {...props}
      >
        {loading && <Spinner size={16} className="text-current" />}
        {children}
      </button>
    )
  },
)
Button.displayName = "Button"
