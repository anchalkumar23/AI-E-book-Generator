import { useState, useEffect } from 'react'
import { CaretLeft, CheckCircle } from '@phosphor-icons/react'
import { api } from '@/lib/api'
import s from './settings.module.css'

type Settings = Record<string, string>

const LLM_PROVIDERS = [
  { value: 'groq',   label: 'Groq',   hint: 'Cloud. Fast, free tier, needs an API key.' },
  { value: 'ollama', label: 'Ollama', hint: 'Local and offline. Needs ~5 GB free RAM for an 8B model.' },
]

const IMAGE_PROVIDERS = [
  { value: 'huggingface', label: 'Hugging Face', hint: 'Free tier, needs a token. ~17s per image.' },
  { value: 'placeholder', label: 'None',         hint: 'Text-only books. Nothing is requested.' },
]

interface Props {
  onBack: () => void
}

export function SettingsView({ onBack }: Props) {
  const [values, setValues]   = useState<Settings | null>(null)
  const [saving, setSaving]   = useState(false)
  const [saved, setSaved]     = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    api.settings.get().then(setValues).catch(e => setError(String(e)))
  }, [])

  function set(key: string, value: string) {
    setValues(v => ({ ...(v ?? {}), [key]: value }))
    setSaved(false)
  }

  async function save() {
    if (!values) return
    setSaving(true)
    setError('')
    try {
      setValues(await api.settings.update(values))
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  if (!values) {
    return (
      <div className={s.page}>
        <div className={s.inner}>{error || 'Loading…'}</div>
      </div>
    )
  }

  return (
    <div className={s.page}>
      <div className={s.bar}>
        <button className={s.back} onClick={onBack}>
          <CaretLeft size={15} weight="bold" /> Library
        </button>
        <span className={s.barTitle}>Settings</span>
        <span className={s.barRight} />
      </div>

      <div className={s.inner}>
        <section className={s.section}>
          <h2 className={s.h2}>Text generation</h2>

          <div className={s.choices}>
            {LLM_PROVIDERS.map(p => (
              <button
                key={p.value}
                className={`${s.choice} ${values.llm_provider === p.value ? s.choiceOn : ''}`}
                onClick={() => set('llm_provider', p.value)}
              >
                <span className={s.choiceLabel}>{p.label}</span>
                <span className={s.choiceHint}>{p.hint}</span>
              </button>
            ))}
          </div>

          {values.llm_provider === 'groq' ? (
            <>
              <label className={s.label}>
                Groq API key
                <input
                  className={s.input}
                  type="password"
                  value={values.groq_api_key ?? ''}
                  onChange={e => set('groq_api_key', e.target.value)}
                  placeholder="gsk_…"
                  spellCheck={false}
                />
              </label>
              <p className={s.help}>Free key at console.groq.com</p>
              <label className={s.label}>
                Model
                <input
                  className={s.input}
                  value={values.groq_model ?? ''}
                  onChange={e => set('groq_model', e.target.value)}
                  spellCheck={false}
                />
              </label>
            </>
          ) : (
            <>
              <label className={s.label}>
                Ollama model
                <input
                  className={s.input}
                  value={values.ollama_model ?? ''}
                  onChange={e => set('ollama_model', e.target.value)}
                  spellCheck={false}
                />
              </label>
              <p className={s.help}>
                Must already be pulled — run <code>ollama list</code> to see what you have.
              </p>
            </>
          )}
        </section>

        <section className={s.section}>
          <h2 className={s.h2}>Illustrations</h2>

          <div className={s.choices}>
            {IMAGE_PROVIDERS.map(p => (
              <button
                key={p.value}
                className={`${s.choice} ${values.image_provider === p.value ? s.choiceOn : ''}`}
                onClick={() => set('image_provider', p.value)}
              >
                <span className={s.choiceLabel}>{p.label}</span>
                <span className={s.choiceHint}>{p.hint}</span>
              </button>
            ))}
          </div>

          {values.image_provider === 'huggingface' && (
            <>
              <label className={s.label}>
                Hugging Face token
                <input
                  className={s.input}
                  type="password"
                  value={values.hf_token ?? ''}
                  onChange={e => set('hf_token', e.target.value)}
                  placeholder="hf_…"
                  spellCheck={false}
                />
              </label>
              <p className={s.help}>
                Free token (no card) at huggingface.co/settings/tokens. Leave empty
                for text-only books.
              </p>
            </>
          )}
        </section>

        <div className={s.actions}>
          <button className={s.save} onClick={save} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          {saved && (
            <span className={s.savedNote}>
              <CheckCircle size={15} weight="fill" /> Saved
            </span>
          )}
          {error && <span className={s.error}>{error}</span>}
        </div>
      </div>
    </div>
  )
}
