import { api } from './client'

export interface Branding {
  site_name: string
  admin_title: string
  browser_title: string
  title_separator: string
  favicon_url: string
}

export const publicApi = {
  getBranding: () =>
    api.get<{ success: boolean; data: Branding }>('/public/branding').then((r) => r.data),
}
