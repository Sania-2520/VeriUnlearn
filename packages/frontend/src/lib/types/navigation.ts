export type UserRole =
  | "admin"
  | "researcher"
  | "ml-engineer"
  | "compliance-officer"
  | "executive"

export interface NavItem {
  label: string
  href: string
  icon: string
  roles: UserRole[]
  tourId?: string
  badge?: { label: string; tone: string }
  children?: NavItem[]
}

export interface NavSection {
  title: string
  items: NavItem[]
  roles: UserRole[]
  tourId?: string
}

export interface Breadcrumb {
  label: string
  href: string
}