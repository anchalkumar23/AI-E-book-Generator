import type { Book, BookCreate, Credits } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  books: {
    list:   ()                          => req<Book[]>('/books/'),
    create: (data: BookCreate)          => req<Book>('/books/', { method: 'POST', body: JSON.stringify(data) }),
    get:    (id: number)                => req<Book>(`/books/${id}`),
    update: (id: number, patch: Partial<Book>) =>
      req<Book>(`/books/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
    delete: (id: number)                => req<void>(`/books/${id}`, { method: 'DELETE' }),
  },
  credits: {
    get:     () => req<Credits>('/credits/'),
    consume: () => req<Credits>('/credits/consume', { method: 'POST' }),
  },
}
