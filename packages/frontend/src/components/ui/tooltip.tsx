"use client"

import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import { clsx } from "clsx"

export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  sideOffset = 6,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={clsx(
          "surface-elevated z-50 max-w-xs rounded-lg px-3 py-2 text-xs text-[var(--text-secondary)] shadow-[var(--shadow-lg)] animate-scale-in",
          className,
        )}
        {...props}
      >
        {children}
        <TooltipPrimitive.Arrow className="fill-[var(--bg-surface-elevated)]" />
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  )
}

/** Convenience wrapper: <HelpTip text="..."><Info/></HelpTip> */
export function HelpTip({
  text,
  children,
  side = "top",
}: {
  text: string
  children: React.ReactNode
  side?: "top" | "right" | "bottom" | "left"
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{text}</TooltipContent>
    </Tooltip>
  )
}
