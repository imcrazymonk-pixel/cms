import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { preferencesApi } from '../api/preferences'

export interface SidebarLink {
  id: string
  label: string
  url: string
  icon: string
  enabled: boolean
}

interface SidebarLinksState {
  links: SidebarLink[]
  hydrated: boolean
  _fetchPromise: Promise<void> | null
  setLinks: (links: SidebarLink[]) => void
  resetToDefaults: () => void
  loadFromServer: () => Promise<void>
}

const defaultLinks: SidebarLink[] = [
  {
    id: 'github',
    label: 'GitHub',
    url: 'https://github.com/',
    icon: 'Github',
    enabled: true,
  },
  {
    id: 'telegram',
    label: 'Telegram',
    url: 'https://t.me/',
    icon: 'MessageCircle',
    enabled: true,
  },
  {
    id: 'support',
    label: 'Support',
    url: 'https://github.com/',
    icon: 'Heart',
    enabled: true,
  },
]

function isSidebarLinkArray(val: unknown): val is SidebarLink[] {
  if (!Array.isArray(val)) return false
  return val.every(
    (item) =>
      typeof item === 'object' &&
      item !== null &&
      typeof (item as SidebarLink).id === 'string' &&
      typeof (item as SidebarLink).label === 'string' &&
      typeof (item as SidebarLink).url === 'string' &&
      typeof (item as SidebarLink).icon === 'string' &&
      typeof (item as SidebarLink).enabled === 'boolean',
  )
}

export const useSidebarLinksStore = create<SidebarLinksState>()(
  persist(
    (set, get) => ({
      links: [...defaultLinks],
      hydrated: false,
      _fetchPromise: null,

      setLinks: (links) => {
        set({ links })
        // Sync to server in background
        preferencesApi.savePreferences({ sidebarLinks: links }).catch(() => {
          /* silent — localStorage fallback works */
        })
      },

      resetToDefaults: () => {
        const defaults = [...defaultLinks]
        set({ links: defaults })
        preferencesApi.savePreferences({ sidebarLinks: defaults }).catch(() => {
          /* silent */
        })
      },

      loadFromServer: async () => {
        // Deduplicate concurrent calls
        const existing = get()._fetchPromise
        if (existing) return existing

        const promise = (async () => {
          try {
            const res = await preferencesApi.getPreferences()
            const serverLinks = res?.data?.sidebarLinks ?? null
            if (isSidebarLinkArray(serverLinks) && serverLinks.length > 0) {
              // Server data ALWAYS wins — overwrite localStorage cache
              set({ links: serverLinks })
              return
            }
            // Server has no links saved — push current (localStorage) state up once
            const current = get().links
            if (current.length > 0) {
              preferencesApi.savePreferences({ sidebarLinks: current }).catch(() => {
                /* silent */
              })
            }
          } catch (err) {
            console.warn('[SidebarLinksStore] Failed to load from server, using cache:', err)
          }
        })()

        set({ _fetchPromise: promise })
        await promise
        set({ _fetchPromise: null })
      },
    }),
    {
      name: 'hexaveil-sidebar-links',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        links: state.links,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) state.hydrated = true
      },
    }
  )
)