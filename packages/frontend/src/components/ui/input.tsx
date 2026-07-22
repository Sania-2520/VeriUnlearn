import { forwardRef } from "react"
import { clsx } from "clsx"

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, leftIcon, ...props }, ref) => {
    const inputId = id || props.name
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-[var(--text-secondary)]">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              "block w-full rounded-lg border bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm transition-colors placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
              leftIcon && "pl-9",
              error
                ? "border-[var(--danger-border)] focus-visible:ring-[var(--danger)]"
                : "border-[var(--border-default)] focus:border-[var(--brand)]",
              className,
            )}
            {...props}
          />
        </div>
        {error ? (
          <p className="text-xs text-[var(--danger)]">{error}</p>
        ) : hint ? (
          <p className="text-xs text-[var(--text-tertiary)]">{hint}</p>
        ) : null}
      </div>
    )
  },
)
Input.displayName = "Input"

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  hint?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-[var(--text-secondary)]">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={id}
          className={clsx(
            "block w-full rounded-lg border bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm transition-colors placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
            error ? "border-[var(--danger-border)]" : "border-[var(--border-default)] focus:border-[var(--brand)]",
            className,
          )}
          {...props}
        />
        {error ? (
          <p className="text-xs text-[var(--danger)]">{error}</p>
        ) : hint ? (
          <p className="text-xs text-[var(--text-tertiary)]">{hint}</p>
        ) : null}
      </div>
    )
  },
)
Textarea.displayName = "Textarea"
