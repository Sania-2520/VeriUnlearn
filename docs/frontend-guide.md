# Frontend Guide — VeriUnlearn

## Architecture

The frontend is a Next.js 15 application with App Router, React 19, and Tailwind CSS.

## Key Packages

| Package | Purpose |
|---|---|
| `next` | Framework |
| `react` | UI library |
| `tailwindcss` | Styling |
| `shadcn/ui` | Component library |
| `lucide-react` | Icons |
| `recharts` | Charts and graphs |
| `react-hook-form` | Form management |
| `zod` | Validation |

## Page Structure

```
frontend/app/
├── page.tsx              # Landing / Home
├── dashboard/
│   ├── page.tsx          # Main dashboard
│   ├── explainability/   # XAI visualizations
│   ├── adapters/         # LoRA adapter management
│   ├── benchmarks/       # Benchmark results
│   └── unlearning/       # Unlearning requests
├── chat/
│   ├── page.tsx          # Chat interface
│   └── sessions/         # Session history
└── settings/
    └── page.tsx          # Account settings
```

## Development

```bash
cd packages/frontend
npm run dev          # Development server (port 3000)
npm run build        # Production build
npm run lint         # Lint check
npx tsc --noEmit     # Type check
```

## State Management

- Server state: React Query (TanStack Query)
- Client state: React Context + useReducer
- Form state: react-hook-form + zod

## API Integration

All API calls go through a centralized client at `frontend/lib/api.ts`:

```typescript
const api = {
  get: (path: string) => fetch(`/api/v1${path}`),
  post: (path: string, body: any) => fetch(`/api/v1${path}`, { method: 'POST', body: JSON.stringify(body) }),
};
```

## Adding a New Page

1. Create the page at `frontend/app/<route>/page.tsx`
2. Add navigation link in sidebar (if needed)
3. Create API hooks in `frontend/hooks/`
4. Add tests in `frontend/__tests__/`
