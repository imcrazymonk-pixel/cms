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
  loaded: boolean
  setLinks: (links: SidebarLink[]) => void
  resetToDefaults: () => void
  loadFromServer: () => Promise<void>
}

const defaultLinks: SidebarLink[] = [
  {
    id: 'github',
    label: 'GitHub',
    url: 'https://github.com/case211/remnawave-admin',
    icon: 'Github',
    enabled: true,
  },
  {
    id: 'telegram',
    label: 'Telegram',
    url: 'https://t.me/remnawave_admin',
    icon: 'MessageCircle',
    enabled: true,
  },
  {
    id: 'support',
    label: 'Support',
    url: 'https://github.com/case211/remnawave-admin#-поддержка',
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
      loaded: false,

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
        try {
          const res = await preferencesApi.getPreferences()
          const serverLinks = res?.data?.sidebarLinks ?? null
          if (isSidebarLinkArray(serverLinks) && serverLinks.length > 0) {
            set({ links: serverLinks, loaded: true })
            return
          }
          // Server has no links saved — push current (localStorage) state up once
          const current = get().links
          if (current.length > 0) {
            preferencesApi.savePreferences({ sidebarLinks: current }).catch(() => {
              /* silent */
            })
          }
        } catch {
          /* offline or not authenticated — keep localStorage state */
        }
        set({ loaded: true })
      },
    }),
    {
      name: 'hexaveil-sidebar-links',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        links: state.links,
      }),
    }
  )
)