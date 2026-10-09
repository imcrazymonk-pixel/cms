import { create } from 'zustand'
import { authApi } from '../api/auth'

/**
 * Permission store — seam for RBAC (parity with remnawave's permissionStore).
 *
 * HexaVeil CMS has no RBAC matrix yet: the backend `/api/auth/me` returns only
 * `{ id, login, email, role }`. This store resolves the current admin's role
 * and, once RBAC is added, will hold the permission list unchanged.
 */
interface Permission {
  resource: string
  action: string
}

interface PermissionState {
  permissions: Permission[]
  role: string | null
  roleId: number | null
  isLoaded: boolean
  mustChangePassword: boolean

  // Actions
  loadPermissions: () => Promise<void>
  hasPermission: (resource: string, action: string) => boolean
  clearPermissions: () => void
  setMustChangePassword: (v: boolean) => void
}

export const usePermissionStore = create<PermissionState>((set, get) => ({
  permissions: [],
  role: null,
  roleId: null,
  isLoaded: false,
  mustChangePassword: false,

  loadPermissions: async () => {
    try {
      const res = await authApi.me()
      set({
        permissions: [],
        role: res.user?.role || 'admin',
        roleId: null,
        isLoaded: true,
        mustChangePassword: false,
      })
    } catch {
      // If the endpoint fails, treat as full-access admin (matches backend role model)
      set({
        permissions: [],
        role: 'admin',
        roleId: null,
        isLoaded: true,
        mustChangePassword: false,
      })
    }
  },

  hasPermission: (resource: string, action: string) => {
    const { role, permissions } = get()
    // Superadmin / legacy admin bypass — CMS has no RBAC yet
    if (role === 'superadmin' || !role || role === 'admin') return true
    return permissions.some((p) => p.resource === resource && p.action === action)
  },

  clearPermissions: () => {
    set({ permissions: [], role: null, roleId: null, isLoaded: false, mustChangePassword: false })
  },

  setMustChangePassword: (v: boolean) => {
    set({ mustChangePassword: v })
  },
}))
