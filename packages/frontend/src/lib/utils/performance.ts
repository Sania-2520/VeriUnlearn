export function measureRenderTime(componentName: string): () => void {
  const start = performance.now()
  return () => {
    const elapsed = performance.now() - start
    if (process.env.NODE_ENV === "development") {
      console.log(`[Render] ${componentName}: ${elapsed.toFixed(2)}ms`)
    }
  }
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), ms)
  }
}

export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number,
): (...args: Parameters<T>) => void {
  let lastCall = 0
  let timer: ReturnType<typeof setTimeout> | undefined
  let lastArgs: Parameters<T> | undefined

  return (...args: Parameters<T>) => {
    const now = Date.now()
    const remaining = ms - (now - lastCall)

    lastArgs = args

    if (remaining <= 0) {
      lastCall = now
      fn(...args)
      return
    }

    if (timer) return

    timer = setTimeout(() => {
      lastCall = Date.now()
      timer = undefined
      if (lastArgs) {
        fn(...lastArgs)
      }
    }, remaining)
  }
}

export function memoize<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => TResult,
): (...args: TArgs) => TResult {
  const cache = new Map<string, TResult>()

  return (...args: TArgs): TResult => {
    const key = JSON.stringify(args)
    if (cache.has(key)) {
      return cache.get(key)!
    }
    const result = fn(...args)
    cache.set(key, result)
    return result
  }
}

interface LazyLoadResult<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

export function lazyLoad<T>(
  importFn: () => Promise<{ default: T }>,
): Promise<LazyLoadResult<T>> {
  const start = performance.now()
  return importFn()
    .then((mod) => {
      const elapsed = performance.now() - start
      if (process.env.NODE_ENV === "development") {
        console.log(`[LazyLoad] Module loaded in ${elapsed.toFixed(2)}ms`)
      }
      return { data: mod.default as T, loading: false, error: null }
    })
    .catch((err: Error) => ({
      data: null,
      loading: false,
      error: err,
    }))
}
