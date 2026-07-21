import { useState, useEffect, useRef, useMemo } from 'react'
import { Sidebar } from '@/components/sidebar/sidebar'
import { Topbar } from '@/components/topbar/topbar'
import { BookGrid } from '@/components/book-grid/book-grid'
import { api } from '@/lib/api'
import { getEngine, wsBase } from '@/lib/engine'
import type { Book } from '@/lib/types'
import s from './library.module.css'

interface Props {
  onOpenBook: (id: number) => void
  onNewBook: () => void
  onOpenSettings: () => void
}

export function LibraryView({ onOpenBook, onNewBook, onOpenSettings }: Props) {
  const [books,    setBooks]    = useState<Book[]>([])
  const [loading,  setLoading]  = useState(true)
  const [navItem,  setNavItem]  = useState('all')
  const [search,   setSearch]   = useState('')
  const [view,     setView]     = useState<'grid' | 'list'>('grid')
  const wsRefs = useRef<Record<number, WebSocket>>({})

  useEffect(() => {
    api.books.list()
      .then(setBooks)
      .finally(() => setLoading(false))
  }, [])

  // WebSocket connections for generating books — replaces polling
  useEffect(() => {
    const generating = books.filter(b => b.status === 'generating')
    if (!generating.length) return

    let cancelled = false
    ;(async () => {
      // The engine's port is assigned at runtime; the token authenticates us.
      const [base, { token }] = await Promise.all([wsBase(), getEngine()])
      if (cancelled) return

      generating.forEach(book => {
        if (wsRefs.current[book.id]) return
        const ws = new WebSocket(`${base}/books/${book.id}/ws?token=${token}`)
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
    })()

    // Close sockets for books no longer generating
    const genIds = new Set(generating.map(b => b.id))
    Object.keys(wsRefs.current).forEach(id => {
      if (!genIds.has(Number(id))) {
        wsRefs.current[Number(id)]?.close()
        delete wsRefs.current[Number(id)]
      }
    })

    return () => { cancelled = true }
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

  function handleFavoriteToggle(id: number, val: boolean) {
    setBooks(prev => prev.map(b => b.id === id ? { ...b, favorite: val } : b))
  }

  function handleDelete(id: number) {
    setBooks(prev => prev.filter(b => b.id !== id))
  }

  const title =
    navItem === 'all'        ? 'All Books'   :
    navItem === 'favorites'  ? 'Favorites'   :
    navItem === 'generating' ? 'Generating'  :
    navItem.charAt(0).toUpperCase() + navItem.slice(1) + 's'

  return (
    <div className={s.shell}>
      <Sidebar
        active={navItem}
        bookCounts={bookCounts}
        onNavChange={id => id === 'settings' ? onOpenSettings() : setNavItem(id)}
        onNewBook={onNewBook}
      />

      <div className={s.main}>
        <Topbar
          view={view}
          onViewChange={setView}
          search={search}
          onSearchChange={setSearch}
          onNewBook={onNewBook}
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
            onRead={onOpenBook}
            onDelete={handleDelete}
            onNewBook={onNewBook}
          />
        </div>
      </div>
    </div>
  )
}
