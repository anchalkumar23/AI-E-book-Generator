'use client'

import { MagnifyingGlass, SquaresFour, List, Plus, SortAscending } from '@phosphor-icons/react'
import s from './topbar.module.css'

interface Props {
  view: 'grid' | 'list'
  onViewChange: (v: 'grid' | 'list') => void
  search: string
  onSearchChange: (v: string) => void
  onNewBook: () => void
}

export function Topbar({ view, onViewChange, search, onSearchChange, onNewBook }: Props) {
  return (
    <header className={s.topbar}>
      <div className={s.searchWrap}>
        <span className={s.searchIcon}>
          <MagnifyingGlass size={14} />
        </span>
        <input
          className={s.searchInput}
          placeholder="Search books…"
          value={search}
          onChange={e => onSearchChange(e.target.value)}
        />
      </div>

      <div className={s.spacer} />

      <div className={s.controls}>
        <button className={s.sortBtn}>
          <SortAscending size={13} />
          Newest
        </button>

        <div className={s.divider} />

        <button
          className={`${s.viewBtn} ${view === 'grid' ? s.viewActive : ''}`}
          onClick={() => onViewChange('grid')}
          title="Grid view"
        >
          <SquaresFour size={16} weight={view === 'grid' ? 'fill' : 'regular'} />
        </button>
        <button
          className={`${s.viewBtn} ${view === 'list' ? s.viewActive : ''}`}
          onClick={() => onViewChange('list')}
          title="List view"
        >
          <List size={16} weight={view === 'list' ? 'fill' : 'regular'} />
        </button>

        <div className={s.divider} />

        <button className={s.newBtn} onClick={onNewBook}>
          <Plus size={14} weight="bold" />
          New Book
        </button>
      </div>
    </header>
  )
}
