'use client'

import { useState } from 'react'
import { BookOpen, Sparkle, Globe } from '@phosphor-icons/react'
import type { BookCreate } from '@/lib/types'
import s from './home-screen.module.css'

const BOOK_TYPES = [
  { value: 'guide',       label: 'Guide'       },
  { value: 'story',       label: 'Story'       },
  { value: 'childrens',   label: "Children's" },
  { value: 'tutorial',    label: 'Tutorial'    },
  { value: 'educational', label: 'Educational' },
  { value: 'custom',      label: 'Custom'      },
] as const

const WRITING_STYLES = [
  { value: 'expository',  label: 'Expository'  },
  { value: 'descriptive', label: 'Descriptive' },
  { value: 'narrative',   label: 'Narrative'   },
  { value: 'persuasive',  label: 'Persuasive'  },
] as const

const EMPTY: BookCreate = {
  title: '',
  prompt: '',
  book_type: 'guide',
  page_count: 12,
  illustration_style: 'watercolor',
  cover_hue: 264,
  use_research: true,
  writing_style: '',
}

interface Props {
  onSubmit: (data: BookCreate) => Promise<void>
}

export function HomeScreen({ onSubmit }: Props) {
  const [form, setForm]     = useState<BookCreate>(EMPTY)
  const [loading, setLoading] = useState(false)

  function set<K extends keyof BookCreate>(k: K, v: BookCreate[K]) {
    setForm(prev => ({ ...prev, [k]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.title.trim() || !form.prompt.trim()) return
    setLoading(true)
    try { await onSubmit(form) }
    finally { setLoading(false) }
  }

  const canSubmit = form.title.trim().length > 0 && form.prompt.trim().length > 0

  return (
    <div className={s.page}>
      <div className={s.center}>

        {/* Logo */}
        <div className={s.hero}>
          <div className={s.logoMark}>
            <BookOpen size={20} weight="bold" />
          </div>
          <h1 className={s.name}>Pageforge</h1>
          <p className={s.tagline}>Create beautiful illustrated books with AI</p>
        </div>

        {/* Form */}
        <form className={s.form} onSubmit={handleSubmit}>
          <input
            className={s.titleInput}
            placeholder="Book title"
            value={form.title}
            onChange={e => set('title', e.target.value)}
            maxLength={120}
            autoFocus
          />

          <textarea
            className={s.promptInput}
            placeholder="What's this book about? Describe the story, topic, or lesson in detail…"
            value={form.prompt}
            onChange={e => set('prompt', e.target.value)}
            rows={4}
          />

          {/* Book type */}
          <div className={s.typeRow}>
            {BOOK_TYPES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`${s.typePill} ${form.book_type === value ? s.typePillActive : ''}`}
                onClick={() => set('book_type', value)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Generate */}
          <button className={s.generateBtn} type="submit" disabled={!canSubmit || loading}>
            {loading
              ? <><div className={s.spinner} />Generating…</>
              : <><Sparkle size={15} weight="fill" />Generate Book</>
            }
          </button>

          {/* Secondary controls */}
          <div className={s.secondary}>
            <button
              type="button"
              className={`${s.researchBtn} ${form.use_research ? s.researchOn : ''}`}
              onClick={() => set('use_research', !form.use_research)}
            >
              <Globe size={13} weight={form.use_research ? 'fill' : 'regular'} />
              {form.use_research ? 'Research ON' : 'Research OFF'}
            </button>

            <div className={s.pagesControl}>
              <span className={s.pagesVal}>{form.page_count} pages</span>
              <input
                type="range"
                min={6} max={48} step={2}
                value={form.page_count}
                onChange={e => set('page_count', Number(e.target.value))}
                className={s.slider}
              />
            </div>
          </div>

          {/* Writing style */}
          <div className={s.styleRow}>
            <span className={s.styleLabel}>Writing style</span>
            <div className={s.stylePills}>
              {WRITING_STYLES.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  className={`${s.stylePill} ${form.writing_style === value ? s.stylePillActive : ''}`}
                  onClick={() => set('writing_style', form.writing_style === value ? '' : value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
