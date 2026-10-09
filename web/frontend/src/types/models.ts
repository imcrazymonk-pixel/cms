/**
 * Central CMS entity types — mirrors remnawave's `src/types/`.
 *
 * Canonical definitions live in the per-domain `api/*` modules; they are
 * re-exported here so components can import entity types from one place.
 */
export type { Post } from '../api/posts'
export type { Page } from '../api/pages'
export type { User } from '../api/users'
export type { Category } from '../api/categories'
export type { MenuItem } from '../api/menus'
export type { Widget } from '../api/widgets'
export type { MediaItem } from '../api/media'
export type { LogEntry } from '../api/logs'
export type { Notification } from '../api/notifications'
export type { Transaction, ChartPoint, FinanceData } from '../api/finance'
export type { ThemeSettingsResponse } from '../api/themes'
