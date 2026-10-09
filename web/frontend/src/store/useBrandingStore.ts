import { create } from 'zustand'
import { publicApi, type Branding } from '../api/public'

export const BRANDING_FALLBACK: Branding = {
  site_name: 'HexaVeil VPN',
  admin_title: 'HexaVeil CMS',
  browser_title: 'HexaVeil CMS',
  title_separator: '—',
  favicon_url: '',
}

function applyBranding(b: Branding) {
  if (typeof document === 'undefined') return
  document.title = b.browser_title || b.admin_title
  if (b.favicon_url) {
    let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement | null
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    link.href = b.favicon_url
  }
}

interface BrandingState extends Branding {
  loaded: boolean
  load: () => Promise<void>
}

/**
 * Public branding (site/CMS name, tab title) — fetched without auth so it
 * can be applied on the login page. Errors fall back to defaults silently.
 */
export const useBrandingStore = create<BrandingState>()((set) => ({
  ...BRANDING_FALLBACK,
  loaded: false,
  load: async () => {
    try {
      const res = await publicApi.getBranding()
      if (res?.success && res.data) {
        const d = res.data
        const branding: Branding = {
          site_name: d.site_name || BRANDING_FALLBACK.site_name,
          admin_title: d.admin_title || BRANDING_FALLBACK.admin_title,
          browser_title: d.browser_title || d.admin_title || BRANDING_FALLBACK.browser_title,
          title_separator: d.title_separator || BRANDING_FALLBACK.title_separator,
          favicon_url: d.favicon_url || '',
        }
        set({ ...branding, loaded: true })
        applyBranding(branding)
        return
      }
    } catch {
      /* fall through to defaults */
    }
    applyBranding(BRANDING_FALLBACK)
    set({ ...BRANDING_FALLBACK, loaded: true })
  },
}))
