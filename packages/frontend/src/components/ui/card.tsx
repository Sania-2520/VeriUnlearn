import { clsx } from "clsx"

interface CardProps {
  className?: string
  children: React.ReactNode
}

export function Card({ className, children }: CardProps) {
  return (
    <div className={clsx("rounded-xl border border-gray-200 bg-white shadow-sm", className)}>
      {children}
    </div>
  )
}

export function CardHeader({ className, children }: CardProps) {
  return <div className={clsx("px-6 py-4 border-b border-gray-100", className)}>{children}</div>
}

export function CardContent({ className, children }: CardProps) {
  return <div className={clsx("px-6 py-4", className)}>{children}</div>
}

export function CardFooter({ className, children }: CardProps) {
  return <div className={clsx("px-6 py-4 border-t border-gray-100", className)}>{children}</div>
}
