'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/sidebar/sidebar'
import { Topbar } from '@/components/topbar/topbar'
import { BookGrid } from '@/components/book-grid/book-grid'
import { NewBookDrawer } from '@/components/new-book-drawer/new-book-drawer'
import { HomeScreen } from '@/components/home-screen/home-screen'
import { api } from '@/lib/api'
import type { Book, BookCreate, Credits } from '@/lib/types'
import s from './library.module.css'

const HUE_CYCLE = [264, 155, 340, 40, 200, 290, 175]

export function LibraryClient() {
  const router = useRouter()
  const [books,    setBooks]    = useState<Book[]>([])
  const [credits,  setCredits]  = useState<Credits>({ remaining: 0, total: 50 })
  const [loading,  setLoading]  = useState(true)
  const [navItem,  setNavItem]  = useState('all')
  const [search,   setSearch]   = useState('')
  const [view,     setView]     = useState<'grid' | 'list'>('grid')
  const [drawer,   setDrawer]   = useState(false)
  const wsRefs = useRef<Record<number, WebSocket>>({})

  useEffect(() => {
    Promise.all([api.books.list(), api.credits.get()])
      .then(([b, c]) => { setBooks(b); setCredits(c) })
      .finally(() => setLoading(false))
  }, [])

  // WebSocket connections for generating books — replaces polling
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api'
    const wsBase = apiUrl.replace(/^http:\/\//, 'ws://').replace(/^https:\/\//, 'wss://')

    const generating = books.filter(b => b.status === 'generating')

    generating.forEach(book => {
      if (wsRefs.current[book.id]) return
      const ws = new WebSocket(`${wsBase}/books/${book.id}/ws`)
      wsRefs.current[book.id] = ws

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'state' || data.type === 'progress') {
          setBooks(prev => prev.map(b => b.id === book.id
            ? { ...b, progress: data.progress ?? b.progress, progress_label: data.label ?? b.progress_label }
            : b
          ))
        }
        if (data.type === 'done') {
          setBooks(prev => prev.map(b => b.id === book.id
            ? { ...b, status: 'done', progress: 100, progress_label: 'Done', content: data.content ?? b.content }
            : b
          ))
          ws.close()
          delete wsRefs.current[book.id]
        }
        if (data.type === 'error') {
          setBooks(prev => prev.map(b => b.id === book.id
            ? { ...b, status: 'error', progress_label: 'Generation failed' }
            : b
          ))
          ws.close()
          delete wsRefs.current[book.id]
        }
      }

      ws.onerror = () => { delete wsRefs.current[book.id] }
      ws.onclose = () => { delete wsRefs.current[book.id] }
    })

    // Close sockets for books no longer generating
    const genIds = new Set(generating.map(b => b.id))
    Object.keys(wsRefs.current).forEach(id => {
      if (!genIds.has(Number(id))) {
        wsRefs.current[Number(id)]?.close()
        delete wsRefs.current[Number(id)]
      }
    })
  }, [books])

  // Cleanup on unmount
  useEffect(() => () => {
    Object.values(wsRefs.current).forEach(ws => ws?.close())
  }, [])

  const filtered = useMemo(() => {
    let list = [...books]

    if (navItem === 'favorites')  list = list.filter(b => b.favorite)
    if (navItem === 'generating') list = list.filter(b => b.status === 'generating')
    if (['childrens','tutorial','guide','educational','story','custom'].includes(navItem)) {
      list = list.filter(b => b.book_type === navItem)
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(b => b.title.toLowerCase().includes(q))
    }

    return list
  }, [books, navItem, search])

  const bookCounts = useMemo(() => ({
    all:        books.length,
    favorites:  books.filter(b => b.favorite).length,
    generating: books.filter(b => b.status === 'generating').length,
  }), [books])

  async function handleCreate(data: BookCreate) {
    const hue = HUE_CYCLE[books.length % HUE_CYCLE.length]
    const book = await api.books.create({ ...data, cover_hue: hue })
    setBooks(prev => [book, ...prev])
    await api.credits.consume().then(c => setCredits(c)).catch(() => {})
  }

  function handleFavoriteToggle(id: number, val: boolean) {
    setBooks(prev => prev.map(b => b.id === id ? { ...b, favorite: val } : b))
  }

  function handleDelete(id: number) {
    setBooks(prev => prev.filter(b => b.id !== id))
  }

  function handleRead(id: number) {
    router.push(`/library/${id}`)
  }

  const title =
    navItem === 'all'        ? 'All Books'   :
    navItem === 'favorites'  ? 'Favorites'   :
    navItem === 'generating' ? 'Generating'  :
    navItem.charAt(0).toUpperCase() + navItem.slice(1) + 's'

  // No books yet → ChatGPT-style home screen
  if (!loading && books.length === 0) {
    return <HomeScreen onSubmit={handleCreate} />
  }

  return (
    <div className={s.shell}>
      <Sidebar
        active={navItem}
        bookCounts={bookCounts}
        credits={credits}
        onNavChange={setNavItem}
      />

      <div className={s.main}>
        <Topbar
          view={view}
          onViewChange={setView}
          search={search}
          onSearchChange={setSearch}
          onNewBook={() => setDrawer(true)}
        />

        <div className={s.content}>
          <div className={s.pageHead}>
            <h1 className={s.pageTitle}>{title}</h1>
            {!loading && (
              <span className={s.pageCount}>{filtered.length} books</span>
            )}
          </div>

          <BookGrid
            books={filtered}
            loading={loading}
            onFavoriteToggle={handleFavoriteToggle}
            onRead={handleRead}
            onDelete={handleDelete}
            onNewBook={() => setDrawer(true)}
          />
        </div>
      </div>

      <NewBookDrawer
        open={drawer}
        onClose={() => setDrawer(false)}
        onSubmit={handleCreate}
      />
    </div>
  )
}
