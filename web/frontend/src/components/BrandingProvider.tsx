import { useEffect } from 'react'
import { useBrandingStore } from '../store/useBrandingStore'

/**
 * Loads public branding (CMS name, tab title, favicon) once on app boot.
 * Renders nothing itself — just triggers the fetch.
 */
export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const load = useBrandingStore((s) => s.load)
  useEffect(() => {
    load()
  }, [load])
  return <>{children}</>
}
