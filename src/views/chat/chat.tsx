import { useState } from 'react'
import { BookOpen, PaperPlaneRight, Books } from '@phosphor-icons/react'
import { api } from '@/lib/api'
import s from './chat.module.css'

const HUE_CYCLE = [264, 155, 340, 40, 200, 290, 175]

const WRITING_STYLES = [
  { value: 'expository',  label: 'Expository'  },
  { value: 'descriptive', label: 'Descriptive' },
  { value: 'narrative',   label: 'Narrative'   },
  { value: 'persuasive',  label: 'Persuasive'  },
] as const

const BOOK_TYPES = [
  { value: 'guide',       label: 'Guide'       },
  { value: 'story',       label: 'Story'       },
  { value: 'childrens',   label: "Children's" },
  { value: 'tutorial',    label: 'Tutorial'    },
  { value: 'educational', label: 'Educational' },
  { value: 'custom',      label: 'Custom'      },
] as const

type BookType = (typeof BOOK_TYPES)[number]['value']

/** Parses "Write a 15 page book about Ancient Rome" -> { title, pages }. */
export function parsePrompt(text: string): { title: string; pages: number } {
  const pages = Number(text.match(/(\d+)\s*[- ]?page/i)?.[1] ?? 12)
  const title = text.match(/about\s+(.+?)[.?!]*$/i)?.[1]?.trim() || text.slice(0, 60)
  return { title, pages: Math.min(Math.max(pages, 6), 48) }
}

interface Props {
  onOpenBook: (id: number) => void
  onLibrary: () => void
  hasBooks: boolean
}

export function ChatView({ onOpenBook, onLibrary, hasBooks }: Props) {
  const [input, setInput]     = useState('')
  const [style, setStyle]     = useState('')
  const [type, setType]       = useState<BookType>('guide')
  const [sending, setSending] = useState(false)
  const [error, setError]     = useState('')

  async function send(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || sending) return
    setSending(true)
    setError('')
    try {
      const { title, pages } = parsePrompt(input)
      const created = await api.books.create({
        title,
        prompt: input,
        book_type: type,
        page_count: pages,
        illustration_style: 'watercolor',
        use_research: true,
        writing_style: style,
        cover_hue: HUE_CYCLE[Math.floor(Math.random() * HUE_CYCLE.length)],
      })
      onOpenBook(created.id) // jump straight into the live reader
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className={s.page}>
      {/* Without this the composer is a dead end — there's no other way back. */}
      {hasBooks && (
        <button className={s.libraryLink} onClick={onLibrary}>
          <Books size={15} weight="bold" />
          Your Library
        </button>
      )}

      <div className={s.center}>
        <div className={s.hero}>
          <div className={s.logoMark}><BookOpen size={20} weight="bold" /></div>
          <h1 className={s.name}>Pageforge</h1>
          <p className={s.tagline}>Describe a book and watch it write itself</p>
        </div>

        <form className={s.form} onSubmit={send}>
          <textarea
            className={s.input}
            placeholder="Write a 15 page book about Ancient Rome"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send(e)
              }
            }}
            rows={3}
            autoFocus
          />

          <div className={s.pillRow}>
            {BOOK_TYPES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`${s.pill} ${type === value ? s.pillActive : ''}`}
                onClick={() => setType(value)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className={s.styleRow}>
            <span className={s.styleLabel}>Style</span>
            <div className={s.pillRow}>
              {WRITING_STYLES.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  className={`${s.pill} ${style === value ? s.pillActive : ''}`}
                  onClick={() => setStyle(style === value ? '' : value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <button className={s.send} type="submit" disabled={!input.trim() || sending}>
            {sending ? 'Starting…' : <><PaperPlaneRight size={15} weight="fill" /> Generate Book</>}
          </button>

          {error && <div className={s.error}>{error}</div>}
        </form>
      </div>
    </div>
  )
}
