'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowLeft, ArrowRight, CaretLeft, Image as ImageIcon } from '@phosphor-icons/react'
import { api } from '@/lib/api'
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

  // Reset when URL changes (page turn)
  useEffect(() => { setStatus('loading') }, [url])

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
      <img
        src={url}
        alt={alt}
        className={s.img}
        style={{ opacity: status === 'loaded' ? 1 : 0 }}
        onLoad={() => setStatus('loaded')}
        onError={() => setStatus('error')}
      />
    </div>
  )
}

export function ReaderClient({ id }: { id: number }) {
  const router = useRouter()
  const [book,      setBook]      = useState<Book | null>(null)
  const [pages,     setPages]     = useState<Page[]>([])
  const [sources,   setSources]   = useState<Source[]>([])
  const [current,   setCurrent]   = useState(0)
  const [direction, setDirection] = useState(1)
  const [loading,   setLoading]   = useState(true)

  // total slides = pages + (sources slide if sources exist)
  const totalSlides = pages.length + (sources.length > 0 ? 1 : 0)
  const isSourcesSlide = sources.length > 0 && current === totalSlides - 1

  useEffect(() => {
    api.books.get(id).then(b => {
      setBook(b)
      if (b.content) {
        const data = JSON.parse(b.content)
        setPages(data.pages ?? [])
        setSources(data.sources ?? [])
      }
    }).finally(() => setLoading(false))
  }, [id])

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

  if (loading) return <div className={s.loading}>Loading…</div>
  if (!book)   return <div className={s.loading}>Book not found.</div>

  if (book.status === 'generating') {
    return <div className={s.loading}>Still generating — check back in a moment.</div>
  }

  if (book.status === 'error') {
    return (
      <div className={s.loading}>
        <div className={s.errorBox}>{book.error_message ?? 'Generation failed.'}</div>
      </div>
    )
  }

  if (pages.length === 0) return <div className={s.loading}>No pages found.</div>

  const page = pages[current]
  const pct  = Math.round(((current + 1) / totalSlides) * 100)
  const counterLabel = isSourcesSlide
    ? 'Sources'
    : `${current + 1} / ${pages.length}`

  return (
    <div className={s.reader}>
      <header className={s.topbar}>
        <button className={s.backBtn} onClick={() => router.push('/library')}>
          <CaretLeft size={15} weight="bold" /> Library
        </button>
        <div className={s.bookTitle}>{book.title}</div>
        <div className={s.pageCounter}>{counterLabel}</div>
      </header>

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
