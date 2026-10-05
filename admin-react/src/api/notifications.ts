// Stub — notifications not needed for CMS
export const notificationsApi = {
  list: () => Promise.resolve({ data: [], total: 0 }),
  markRead: () => Promise.resolve({}),
}