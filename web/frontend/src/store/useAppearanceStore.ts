import { useState, useEffect } from 'react'
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { preferencesApi } from '../api/preferences'

export type UIDensity = 'compact' | 'comfortable' | 'spacious'
export type BorderRadius = 'sharp' | 'default' | 'rounded'
export type FontSize = 'small' | 'default' | 'large'
export type ThemePreset = 'obsidian' | 'arctic' | 'sakura' | 'twilight' | 'ember'
export type ColorMode = 'dark' | 'light' | 'auto'

export interface AppearanceSettings {
  theme: ThemePreset
  colorMode: ColorMode
  density: UIDensity
  borderRadius: BorderRadius
  fontSize: FontSize
  animationsEnabled: boolean
  sidebarCollapsed: boolean
}

interface AppearanceState extends AppearanceSettings {
  // Status
  loaded: boolean

  // Actions
  setTheme: (theme: ThemePreset) => void
  setColorMode: (mode: ColorMode) => void
  setDensity: (density: UIDensity) => void
  setBorderRadius: (radius: BorderRadius) => void
  setFontSize: (size: FontSize) => void
  setAnimationsEnabled: (enabled: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  toggleColorMode: () => void
  resetToDefaults: () => void
  loadFromServer: () => Promise<void>
}

const defaults: AppearanceSettings = {
  theme: 'obsidian' as ThemePreset,
  colorMode: 'dark' as ColorMode,
  density: 'comfortable' as UIDensity,
  borderRadius: 'default' as BorderRadius,
  fontSize: 'default' as FontSize,
  animationsEnabled: true,
  sidebarCollapsed: false,
}

// ---------------------------------------------------------------------------
// Debounced server sync
// ---------------------------------------------------------------------------
let _syncTimer: ReturnType<typeof setTimeout> | null = null

function toAppearanceBlob(state: AppearanceSettings): Record<string, unknown> {
  return {
    theme: state.theme,
    colorMode: state.colorMode,
    density: state.density,
    borderRadius: state.borderRadius,
    fontSize: state.fontSize,
    animationsEnabled: state.animationsEnabled,
    sidebarCollapsed: state.sidebarCollapsed,
  }
}

/** Schedule a server save with 1-second debounce. */
function scheduleSync(state: AppearanceSettings): void {
  if (_syncTimer) clearTimeout(_syncTimer)
  _syncTimer = setTimeout(() => {
    _syncTimer = null
    preferencesApi.savePreferences({ appearance: toAppearanceBlob(state) }).catch(() => {
      /* silent */
    })
  }, 1000)
}

// Guards against saving server data back to the server (infinite loop)
let _isLoadingFromServer = false

// ---------------------------------------------------------------------------
// Guard: validate partial server data so corrupt blobs don't nuke defaults
// ---------------------------------------------------------------------------
function isThemePreset(v: unknown): v is ThemePreset {
  return typeof v === 'string' && ['obsidian', 'arctic', 'sakura', 'twilight', 'ember'].includes(v)
}
function isColorMode(v: unknown): v is ColorMode {
  return typeof v === 'string' && ['dark', 'light', 'auto'].includes(v)
}
function isUIDensity(v: unknown): v is UIDensity {
  return typeof v === 'string' && ['compact', 'comfortable', 'spacious'].includes(v)
}
function isBorderRadius(v: unknown): v is BorderRadius {
  return typeof v === 'string' && ['sharp', 'default', 'rounded'].includes(v)
}
function isFontSize(v: unknown): v is FontSize {
  return typeof v === 'string' && ['small', 'default', 'large'].includes(v)
}

export const useAppearanceStore = create<AppearanceState>()(
  persist(
    (set, get) => {
      // Helper: set + sync to server
      const syncSet = (partial: Partial<AppearanceSettings>) => {
        set(partial)
        if (!_isLoadingFromServer) {
          scheduleSync({ ...get() })
        }
      }

      return {
        ...defaults,
        loaded: false,

        setTheme: (theme) => syncSet({ theme }),
        setColorMode: (colorMode) => syncSet({ colorMode }),
        setDensity: (density) => syncSet({ density }),
        setBorderRadius: (borderRadius) => syncSet({ borderRadius }),
        setFontSize: (fontSize) => syncSet({ fontSize }),
        setAnimationsEnabled: (animationsEnabled) => syncSet({ animationsEnabled }),
        setSidebarCollapsed: (sidebarCollapsed) => syncSet({ sidebarCollapsed }),
        toggleSidebar: () => syncSet({ sidebarCollapsed: !get().sidebarCollapsed }),
        toggleColorMode: () => {
          const mode = get().colorMode
          const next: ColorMode = mode === 'dark' ? 'light' : mode === 'light' ? 'auto' : 'dark'
          syncSet({ colorMode: next })
        },
        resetToDefaults: () => syncSet({ ...defaults }),

        loadFromServer: async () => {
          try {
            _isLoadingFromServer = true
            const res = await preferencesApi.getPreferences()
            const serverAppearance = res?.data?.appearance as Record<string, unknown> | null
            if (serverAppearance && typeof serverAppearance === 'object') {
              const patch: Partial<AppearanceSettings> = {}
              if (isThemePreset(serverAppearance.theme)) patch.theme = serverAppearance.theme
              if (isColorMode(serverAppearance.colorMode)) patch.colorMode = serverAppearance.colorMode
              if (isUIDensity(serverAppearance.density)) patch.density = serverAppearance.density
              if (isBorderRadius(serverAppearance.borderRadius)) patch.borderRadius = serverAppearance.borderRadius
              if (isFontSize(serverAppearance.fontSize)) patch.fontSize = serverAppearance.fontSize
              if (typeof serverAppearance.animationsEnabled === 'boolean') patch.animationsEnabled = serverAppearance.animationsEnabled
              if (typeof serverAppearance.sidebarCollapsed === 'boolean') patch.sidebarCollapsed = serverAppearance.sidebarCollapsed

              if (Object.keys(patch).length > 0) {
                set(patch)
              }
            } else {
              // Server has no appearance saved — push current state up once
              preferencesApi.savePreferences({
                appearance: toAppearanceBlob(get()),
              }).catch(() => { /* silent */ })
            }
          } catch {
            /* offline or not authenticated — keep localStorage state */
          } finally {
            _isLoadingFromServer = false
            set({ loaded: true })
          }
        },
      }
    },
    {
      name: 'remnawave-appearance',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        colorMode: state.colorMode,
        density: state.density,
        borderRadius: state.borderRadius,
        fontSize: state.fontSize,
        animationsEnabled: state.animationsEnabled,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
)

function getSystemPreference(): 'dark' | 'light' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useResolvedColorMode(): 'dark' | 'light' {
  const colorMode = useAppearanceStore((s) => s.colorMode)
  const [resolved, setResolved] = useState<'dark' | 'light'>(
    colorMode === 'auto' ? getSystemPreference() : colorMode
  )

  useEffect(() => {
    if (colorMode !== 'auto') {
      setResolved(colorMode)
      return
    }
    setResolved(getSystemPreference())
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => setResolved(e.matches ? 'dark' : 'light')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [colorMode])

  return resolved
}