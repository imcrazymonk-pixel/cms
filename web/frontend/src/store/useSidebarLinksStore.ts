import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface SidebarLink {
  id: string
  label: string
  url: string
  icon: string
  enabled: boolean
}

interface SidebarLinksState {
  links: SidebarLink[]
  setLinks: (links: SidebarLink[]) => void
  resetToDefaults: () => void
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

export const useSidebarLinksStore = create<SidebarLinksState>()(
  persist(
    (set) => ({
      links: [...defaultLinks],

      setLinks: (links) => set({ links }),
      resetToDefaults: () => set({ links: [...defaultLinks] }),
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