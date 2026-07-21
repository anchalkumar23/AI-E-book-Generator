import { useState, useEffect, useRef, useCallback } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowLeft, ArrowRight, CaretLeft, Image as ImageIcon } from '@phosphor-icons/react'
import { api } from '@/lib/api'
import { getEngine, wsBase, assetUrl } from '@/lib/engine'
import type { Book } from '@/lib/types'
import s from './reader.module.css'

interface Page {
  page_number: number
  heading: string
  text: string
  image_url: string | null
  image_message: string | null
}

interface Source {
  title: string
  url: string
}

function PageImage({ url, alt }: { url: string; alt: string }) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>('loading')
  const [src, setSrc]       = useState('')

  // Stored paths are engine-relative; resolve to the current port.
  useEffect(() => {
    setStatus('loading')
    let live = true
    assetUrl(url).then(u => { if (live) setSrc(u) })
    return () => { live = false }
  }, [url])

  return (
    <div className={s.illustration}>
      {status !== 'loaded' && (
        <div className={`${s.imgSkeleton} ${status === 'error' ? s.imgError : ''}`}>
          {status === 'error'
            ? <><ImageIcon size={28} /><span>Image unavailable</span></>
            : <div className={s.imgSpinner} />
          }
        </div>
      )}
      {src && (
        <img
          src={src}
          alt={alt}
          className={s.img}
          style={{ opacity: status === 'loaded' ? 1 : 0 }}
          onLoad={() => setStatus('loaded')}
          onError={() => setStatus('error')}
        />
      )}
    </div>
  )
}

interface Props {
  id: number
  onBack: () => void
}

export function ReaderView({ id, onBack }: Props) {
  const [book,       setBook]       = useState<Book | null>(null)
  const [pages,      setPages]      = useState<Page[]>([])
  const [sources,    setSources]    = useState<Source[]>([])
  const [current,    setCurrent]    = useState(0)
  const [direction,  setDirection]  = useState(1)
  const [loading,    setLoading]    = useState(true)
  const [streaming,  setStreaming]  = useState(false)
  const [genProgress, setGenProgress] = useState(0)
  const [genLabel,   setGenLabel]   = useState('')
  const [displayText, setDisplayText] = useState('')
  const wsRef     = useRef<WebSocket | null>(null)
  const bufferRef = useRef('')
  const streamRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.books.get(id).then(async b => {
      setBook(b)
      setGenProgress(b.progress)
      setGenLabel(b.progress_label)

      if (b.content) {
        const data = JSON.parse(b.content)
        setPages(data.pages ?? [])
        setSources(data.sources ?? [])
      }

      if (b.status === 'generating') {
        setStreaming(true)
        // The engine's port is assigned at runtime; the token authenticates us.
        // Browsers can't set WS headers, so it goes in the query string.
        const [base, { token }] = await Promise.all([wsBase(), getEngine()])
        const ws = new WebSocket(`${base}/books/${id}/ws?token=${token}`)
        wsRef.current = ws

        ws.onmessage = (e) => {
          const data = JSON.parse(e.data)
          if (data.type === 'state' || data.type === 'progress') {
            setGenProgress(data.progress ?? 0)
            setGenLabel(data.label ?? '')
          }
          if (data.type === 'token') {
            bufferRef.current += data.token
          }
          if (data.type === 'page') {
            setPages(prev => {
              const exists = prev.some(p => p.page_number === data.page.page_number)
              return exists ? prev : [...prev, data.page]
            })
          }
          if (data.type === 'done') {
            if (data.content) {
              const parsed = JSON.parse(data.content)
              setPages(parsed.pages ?? [])
              setSources(parsed.sources ?? [])
            }
            setStreaming(false)
            bufferRef.current = ''
            setDisplayText('')
            setGenProgress(100)
            setGenLabel('Done')
            ws.close()
          }
          if (data.type === 'error') {
            setStreaming(false)
            bufferRef.current = ''
            setDisplayText('')
            setBook(prev => prev ? { ...prev, status: 'error', error_message: data.message } : prev)
            ws.close()
          }
        }
      }
    }).finally(() => setLoading(false))

    return () => { wsRef.current?.close() }
  }, [id])

  const totalSlides   = pages.length + (sources.length > 0 ? 1 : 0)
  const isSourcesSlide = sources.length > 0 && current === totalSlides - 1

  const go = useCallback((dir: number) => {
    const next = current + dir
    if (next < 0 || next >= totalSlides) return
    setDirection(dir)
    setCurrent(next)
  }, [current, totalSlides])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') go(1)
      if (e.key === 'ArrowLeft')  go(-1)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [go])

  // Reveal buffered tokens at a readable typewriter pace (not a blur)
  useEffect(() => {
    if (!streaming) return
    const id = setInterval(() => {
      setDisplayText(prev => {
        const full = bufferRef.current
        if (prev.length >= full.length) return prev
        const behind = full.length - prev.length
        const step = behind > 300 ? 4 : behind > 80 ? 2 : 1
        return full.slice(0, prev.length + step)
      })
    }, 28)
    return () => clearInterval(id)
  }, [streaming])

  useEffect(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight
  }, [displayText])

  if (loading) return <div className={s.loading}>Loading…</div>
  if (!book)   return <div className={s.loading}>Book not found.</div>

  if (book.status === 'error' && !streaming) {
    return (
      <div className={s.loading}>
        <div className={s.errorBox}>{book.error_message ?? 'Generation failed.'}</div>
      </div>
    )
  }

  // Generating — live view: illustration on the left, prose typing on the right
  if (streaming) {
    const latest = pages.length ? pages[pages.length - 1] : null
    const paras  = displayText.split('\n').filter(Boolean)
    return (
      <div className={s.reader}>
        <header className={s.topbar}>
          <button className={s.backBtn} onClick={onBack}>
            <CaretLeft size={15} weight="bold" /> Library
          </button>
          <div className={s.bookTitle}>{book.title}</div>
          <div className={s.pageCounter}>{genProgress}%</div>
        </header>

        <div className={s.liveBanner}>
          <span className={s.livePulse} />
          <span>{genLabel || 'Generating…'}</span>
        </div>

        <div className={s.page}>
          {/* Left — illustration */}
          <div className={s.illustration}>
            {latest?.image_url ? (
              <PageImage key={latest.image_url} url={latest.image_url} alt="" />
            ) : (
              <div className={s.imgGen}>
                <div className={s.imgSpinner} />
                <span>{latest ? 'Generating illustration…' : 'Writing the story…'}</span>
              </div>
            )}
          </div>

          {/* Right — streaming text */}
          <div className={s.textArea} ref={streamRef}>
            <div className={s.text}>
              {paras.length === 0 ? (
                <p><span className={s.cursor} /></p>
              ) : (
                paras.map((para, i) => (
                  <p key={i}>
                    {para}
                    {i === paras.length - 1 && <span className={s.cursor} />}
                  </p>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (pages.length === 0) return <div className={s.loading}>No pages found.</div>

  const page = pages[current]
  const pct  = Math.round(((current + 1) / Math.max(totalSlides, 1)) * 100)
  const counterLabel = isSourcesSlide ? 'Sources' : `${current + 1} / ${pages.length}`

  return (
    <div className={s.reader}>
      <header className={s.topbar}>
        <button className={s.backBtn} onClick={onBack}>
          <CaretLeft size={15} weight="bold" /> Library
        </button>
        <div className={s.bookTitle}>{book.title}</div>
        <div className={s.pageCounter}>{counterLabel}</div>
      </header>

      {/* Live generation banner */}
      {streaming && (
        <div className={s.liveBanner}>
          <span className={s.livePulse} />
          <span>{genLabel || 'Generating…'}</span>
        </div>
      )}

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={current}
          className={s.page}
          initial={{ opacity: 0, x: direction * 48 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: direction * -48 }}
          transition={{ duration: 0.22, ease: [0.23, 1, 0.32, 1] }}
        >
          {isSourcesSlide ? (
            <div className={s.sourcesSlide}>
              <h2 className={s.sourcesTitle}>Research Sources</h2>
              <p className={s.sourcesSub}>Content researched via DuckDuckGo</p>
              <ol className={s.sourcesList}>
                {sources.map((src, i) => (
                  <li key={i} className={s.sourceItem}>
                    <a href={src.url} target="_blank" rel="noopener noreferrer" className={s.sourceLink}>
                      {src.title}
                    </a>
                    <span className={s.sourceUrl}>{src.url}</span>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <>
              {page.image_url ? (
                <PageImage url={page.image_url} alt={page.heading} />
              ) : page.image_message ? (
                <div className={s.realPersonNotice}>{page.image_message}</div>
              ) : (
                <div className={s.noImage}>
                  <ImageIcon size={32} />
                </div>
              )}

              <div className={s.textArea}>
                {page.heading && <h2 className={s.heading}>{page.heading}</h2>}
                <div className={s.text}>
                  {page.text.split('\n').filter(Boolean).map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
              </div>
            </>
          )}
        </motion.div>
      </AnimatePresence>

      <footer className={s.nav}>
        <button className={s.navBtn} onClick={() => go(-1)} disabled={current === 0}>
          <ArrowLeft size={16} weight="bold" />
        </button>
        <div className={s.progress}>
          <div className={s.progressTrack}>
            <div className={s.progressFill} style={{ width: `${pct}%` }} />
          </div>
          <span className={s.progressLabel}>
            {isSourcesSlide ? 'Sources' : `Page ${current + 1} of ${pages.length}`}
          </span>
        </div>
        <button className={s.navBtn} onClick={() => go(1)} disabled={current === totalSlides - 1}>
          <ArrowRight size={16} weight="bold" />
        </button>
      </footer>
    </div>
  )
}
