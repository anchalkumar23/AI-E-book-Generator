'use client'

import { BookOpen, Plus } from '@phosphor-icons/react'
import type { Book } from '@/lib/types'
import { BookCard } from '@/components/book-card/book-card'
import s from './book-grid.module.css'

interface Props {
  books: Book[]
  loading: boolean
  onFavoriteToggle: (id: number, val: boolean) => void
  onRead: (id: number) => void
  onDelete: (id: number) => void
  onNewBook: () => void
}

const SKELETON_COUNT = 8

export function BookGrid({ books, loading, onFavoriteToggle, onRead, onDelete, onNewBook }: Props) {
  if (loading) {
    return (
      <div className={s.grid}>
        {Array.from({ length: SKELETON_COUNT }, (_, i) => (
          <div key={i} className={s.skeleton} />
        ))}
      </div>
    )
  }

  if (books.length === 0) {
    return (
      <div className={s.grid}>
        <div className={s.empty}>
          <div className={s.emptyIcon}>
            <BookOpen size={22} />
          </div>
          <div className={s.emptyTitle}>No books yet</div>
          <div className={s.emptyBody}>
            Generate your first illustrated ebook. Describe a topic, pick a style, and we'll handle the rest.
          </div>
          <button className={s.emptyBtn} onClick={onNewBook}>
            <Plus size={13} weight="bold" />
            Generate a book
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={s.grid}>
      {books.map(book => (
        <BookCard
          key={book.id}
          book={book}
          onFavoriteToggle={onFavoriteToggle}
          onRead={onRead}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
