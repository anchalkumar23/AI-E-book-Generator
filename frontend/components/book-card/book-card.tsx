'use client'

import { Star, BookOpen, Trash } from '@phosphor-icons/react'
import type { Book } from '@/lib/types'
import { api } from '@/lib/api'
import s from './book-card.module.css'

/* Deterministic gradient from cover_hue — each book looks different */
const GRADIENTS: Record<number, string> = {
  264: 'linear-gradient(160deg, #160a30 0%, #4c1d95 55%, #6d28d9 100%)',
  155: 'linear-gradient(160deg, #071a0e 0%, #064e3b 55%, #059669 100%)',
  340: 'linear-gradient(160deg, #200710 0%, #881337 55%, #e11d48 100%)',
  40:  'linear-gradient(160deg, #150b00 0%, #78350f 55%, #d97706 100%)',
  200: 'linear-gradient(160deg, #001422 0%, #075985 55%, #0284c7 100%)',
  290: 'linear-gradient(160deg, #0e0020 0%, #5b21b6 55%, #8b5cf6 100%)',
  175: 'linear-gradient(160deg, #010f0c 0%, #134e4a 55%, #0d9488 100%)',
}

function gradient(hue: number): string {
  const keys = Object.keys(GRADIENTS).map(Number)
  const nearest = keys.reduce((a, b) => (Math.abs(b - hue) < Math.abs(a - hue) ? b : a))
  return GRADIENTS[nearest]
}

const TYPE_LABELS: Record<string, string> = {
  childrens:   "Children's",
  tutorial:    'Tutorial',
  guide:       'Guide',
  educational: 'Educational',
  story:       'Story',
  custom:      'Custom',
}

interface Props {
  book: Book
  onFavoriteToggle: (id: number, val: boolean) => void
  onRead:   (id: number) => void
  onDelete: (id: number) => void
}

export function BookCard({ book, onFavoriteToggle, onRead, onDelete }: Props) {
  const isGenerating = book.status === 'generating'
  const isError      = book.status === 'error'
  const isDone       = book.status === 'done'

  async function toggleFav(e: React.MouseEvent) {
    e.stopPropagation()
    const next = !book.favorite
    await api.books.update(book.id, { favorite: next })
    onFavoriteToggle(book.id, next)
  }

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation()
    await api.books.delete(book.id)
    onDelete(book.id)
  }

  const currentPage = Math.max(1, Math.round((book.progress / 100) * book.page_count))

  return (
    <div className={s.wrap}>
      <div className={s.card}>
        {/* Cover */}
        <div className={s.cover} style={{ background: gradient(book.cover_hue) }} />

        {/* Spine shadow */}
        <div className={s.spine} />

        {/* Generating shimmer */}
        {isGenerating && (
          <div className={s.shimmerWrap}>
            <div className={s.shimmerBar} />
          </div>
        )}

        {!isGenerating && <div className={s.vignette} />}

        {/* Status badge */}
        <div className={`${s.badge} ${
          isDone       ? s.badgeDone       :
          isGenerating ? s.badgeGenerating :
                         s.badgeError
        }`}>
          {isDone ? 'Done' : isGenerating ? 'Generating' : 'Error'}
        </div>

        {/* Favorite button */}
        {!isGenerating && (
          <button
            className={`${s.favBtn} ${book.favorite ? s.favActive : ''}`}
            onClick={toggleFav}
            title={book.favorite ? 'Remove favorite' : 'Add to favorites'}
          >
            <Star size={14} weight={book.favorite ? 'fill' : 'regular'} />
          </button>
        )}

        {/* Generating info */}
        {isGenerating && (
          <div className={s.genInfo}>
            <div className={s.genTitle}>{book.title}</div>
            <div className={s.genPage}>
              {book.progress_label || `Page ${currentPage} of ${book.page_count}`}
            </div>
            <div className={s.genTrack}>
              <div className={s.genFill} style={{ width: `${Math.max(8, book.progress)}%` }} />
            </div>
          </div>
        )}

        {/* Book metadata */}
        {!isGenerating && (
          <div className={s.meta}>
            <div className={s.genre}>{TYPE_LABELS[book.book_type] ?? book.book_type}</div>
            <div className={s.title}>{book.title}</div>
          </div>
        )}

        {/* Hover overlay */}
        {!isGenerating && (
          <div className={s.overlay}>
            <button className={`${s.overlayBtn} ${s.overlayPrimary}`} onClick={() => onRead(book.id)}>
              <BookOpen size={13} weight="bold" /> Read
            </button>
            <button className={`${s.overlayBtn} ${s.overlayGhost}`} onClick={handleDelete}>
              <Trash size={13} /> Delete
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
