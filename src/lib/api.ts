import { apiBase, authHeaders } from './engine'
import type { Book, BookCreate, Chat, Message } from './types'

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${await apiBase()}${path}`, {
    ...init,
    headers: { ...(await authHeaders()), ...(init.headers ?? {}) },
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  books: {
    list: () => req<Book[]>('/books/'),
    get: (id: number) => req<Book>(`/books/${id}`),
    create: (data: BookCreate & { cover_hue: number }) =>
      req<Book>('/books/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Book>) =>
      req<Book>(`/books/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: number) => req<void>(`/books/${id}`, { method: 'DELETE' }),
  },
  settings: {
    get: () => req<Record<string, string>>('/settings/'),
    update: (data: Record<string, string>) =>
      req<Record<string, string>>('/settings/', { method: 'PUT', body: JSON.stringify(data) }),
  },
  chats: {
    list: () => req<Chat[]>('/chats/'),
    create: (title: string) =>
      req<Chat>('/chats/', { method: 'POST', body: JSON.stringify({ title }) }),
    delete: (id: number) => req<void>(`/chats/${id}`, { method: 'DELETE' }),
    messages: (id: number) => req<Message[]>(`/chats/${id}/messages`),
    addMessage: (id: number, role: string, content: string, book_id?: number) =>
      req<Message>(`/chats/${id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ role, content, book_id }),
      }),
  },
}
