import { clsx } from "clsx"

interface VisuallyHiddenProps extends React.HTMLAttributes<HTMLSpanElement> {
  asChild?: boolean
}

export function VisuallyHidden({ className, children, ...props }: VisuallyHiddenProps) {
  return (
    <span
      className={clsx(
        "sr-only",
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
