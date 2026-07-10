'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { X, Sparkle, Globe } from '@phosphor-icons/react'
import type { BookCreate } from '@/lib/types'
import s from './new-book-drawer.module.css'

const BOOK_TYPES = [
  { value: 'childrens',   label: "Children's" },
  { value: 'tutorial',    label: 'Tutorial'    },
  { value: 'guide',       label: 'Guide'       },
  { value: 'educational', label: 'Educational' },
  { value: 'story',       label: 'Story'       },
  { value: 'custom',      label: 'Custom'      },
] as const

/* Decorative art in style swatches — not navigation icons */
const ILLUSTRATION_STYLES = [
  { value: 'watercolor',   label: 'Watercolor',    art: '🎨' },
  { value: 'comic',        label: 'Comic',         art: '💥' },
  { value: 'minimalist',   label: 'Minimalist',    art: '◽' },
  { value: 'realistic',    label: 'Realistic',     art: '🖼️' },
  { value: 'anime',        label: 'Anime',         art: '⛩️' },
  { value: 'sketch',       label: 'Sketch',        art: '✏️' },
] as const

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (data: BookCreate) => Promise<void>
}

const EMPTY: BookCreate = {
  title: '',
  prompt: '',
  book_type: 'guide',
  page_count: 12,
  illustration_style: 'watercolor',
  cover_hue: 264,
  use_research: true,
}

export function NewBookDrawer({ open, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<BookCreate>(EMPTY)
  const [loading, setLoading] = useState(false)

  function set<K extends keyof BookCreate>(k: K, v: BookCreate[K]) {
    setForm(prev => ({ ...prev, [k]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.title.trim() || !form.prompt.trim()) return
    setLoading(true)
    try {
      await onSubmit(form)
      setForm(EMPTY)
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = form.title.trim().length > 0 && form.prompt.trim().length > 0

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={s.backdrop}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={e => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            className={s.drawer}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ duration: 0.38, ease: [0.32, 0.72, 0, 1] }}
          >
            <div className={s.handle} />

            <div className={s.head}>
              <div>
                <div className={s.headTitle}>New Book</div>
                <div className={s.headSub}>Describe what you want and AI handles the rest</div>
              </div>
              <button className={s.closeBtn} onClick={onClose} title="Close">
                <X size={14} weight="bold" />
              </button>
            </div>

            <form className={s.body} onSubmit={handleSubmit} id="new-book-form">
              {/* Title */}
              <div className={s.field}>
                <label className={s.label}>
                  Title <span className={s.required}>*</span>
                </label>
                <input
                  className={s.input}
                  placeholder="e.g. The Ocean Explorers"
                  value={form.title}
                  onChange={e => set('title', e.target.value)}
                  maxLength={120}
                />
              </div>

              {/* Prompt */}
              <div className={s.field}>
                <label className={s.label}>
                  What's this book about? <span className={s.required}>*</span>
                </label>
                <textarea
                  className={s.textarea}
                  placeholder="Describe the story, lesson, or topic. The more specific you are, the better the result."
                  value={form.prompt}
                  onChange={e => set('prompt', e.target.value)}
                  rows={4}
                />
              </div>

              {/* Type */}
              <div className={s.field}>
                <label className={s.label}>Book type</label>
                <div className={s.pillGroup}>
                  {BOOK_TYPES.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      className={`${s.pill} ${form.book_type === value ? s.pillActive : ''}`}
                      onClick={() => set('book_type', value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Page count */}
              <div className={s.field}>
                <label className={s.label}>Page count</label>
                <div className={s.sliderRow}>
                  <input
                    className={s.slider}
                    type="range"
                    min={6}
                    max={48}
                    step={2}
                    value={form.page_count}
                    onChange={e => set('page_count', Number(e.target.value))}
                  />
                  <span className={s.sliderVal}>{form.page_count} pg</span>
                </div>
              </div>

              {/* Internet Research toggle */}
              <div className={s.field}>
                <button
                  type="button"
                  className={`${s.researchToggle} ${form.use_research ? s.researchOn : ''}`}
                  onClick={() => set('use_research', !form.use_research)}
                >
                  <Globe size={15} weight={form.use_research ? 'fill' : 'regular'} />
                  <div className={s.researchText}>
                    <span className={s.researchLabel}>Internet Research</span>
                    <span className={s.researchDesc}>
                      {form.use_research
                        ? 'ON — searches web, Wikipedia & more before writing'
                        : 'OFF — uses only the AI\'s built-in knowledge'}
                    </span>
                  </div>
                  <div className={`${s.toggle} ${form.use_research ? s.toggleOn : ''}`}>
                    <div className={s.toggleThumb} />
                  </div>
                </button>
              </div>

              {/* Illustration style */}
              <div className={s.field}>
                <label className={s.label}>Illustration style</label>
                <div className={s.styleGrid}>
                  {ILLUSTRATION_STYLES.map(({ value, label, art }) => (
                    <button
                      key={value}
                      type="button"
                      className={`${s.styleSwatch} ${form.illustration_style === value ? s.styleSwatchActive : ''}`}
                      onClick={() => set('illustration_style', value)}
                    >
                      <span className={s.swatchEmoji}>{art}</span>
                      <span className={s.swatchLabel}>{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </form>

            <div className={s.foot}>
              <button className={s.cancelBtn} type="button" onClick={onClose}>Cancel</button>
              <button
                className={s.submitBtn}
                type="submit"
                form="new-book-form"
                disabled={!canSubmit || loading}
              >
                {loading
                  ? <><div className={s.spinner} /> Generating…</>
                  : <><Sparkle size={14} weight="fill" /> Generate Book</>
                }
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
