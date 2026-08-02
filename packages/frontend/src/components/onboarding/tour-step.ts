export interface TourStep {
  targetSelector: string
  title: string
  content: string
  placement: "top" | "bottom" | "left" | "right" | "center"
  icon?: string
  action?: {
    label: string
    href?: string
    onClick?: () => void
  }
  showSkip?: boolean
  showDots?: boolean
}
