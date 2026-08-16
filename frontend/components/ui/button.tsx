import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type Size = "sm" | "md" | "lg" | "icon";

const variants: Record<Variant, string> = {
  primary:
    "bg-cyan-500/90 hover:bg-cyan-400 text-slate-950 font-semibold shadow-[0_0_20px_-4px_rgba(34,211,238,0.6)]",
  secondary: "bg-slate-800/80 hover:bg-slate-700/80 text-slate-100 border border-slate-700",
  outline: "border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/10",
  ghost: "hover:bg-slate-800/60 text-slate-300",
  danger: "bg-rose-500/90 hover:bg-rose-400 text-white font-semibold",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
  icon: "h-9 w-9",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98] cursor-pointer",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  )
);
Button.displayName = "Button";
