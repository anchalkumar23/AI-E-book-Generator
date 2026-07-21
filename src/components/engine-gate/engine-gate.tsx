import { useCallback, useEffect, useState } from 'react'
import { getEngine, restartEngine } from '@/lib/engine'
import s from './engine-gate.module.css'

type Phase = 'starting' | 'ready' | 'failed'

/** Owns "is the engine up?" for the whole app, so a dead engine shows a real
 *  reason and a Restart button instead of an infinite spinner. */
export function EngineGate({ children }: { children: React.ReactNode }) {
  const [phase, setPhase] = useState<Phase>('starting')
  const [message, setMessage] = useState('')

  const connect = useCallback(async () => {
    setPhase('starting')
    try {
      await getEngine()
      setPhase('ready')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e))
      setPhase('failed')
    }
  }, [])

  useEffect(() => {
    connect()
  }, [connect])

  async function retry() {
    setPhase('starting')
    try {
      await restartEngine()
      setPhase('ready')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e))
      setPhase('failed')
    }
  }

  if (phase === 'ready') return <>{children}</>

  return (
    <div className={s.screen}>
      {phase === 'starting' ? (
        <>
          <div className={s.spinner} />
          <div className={s.label}>Starting engine…</div>
        </>
      ) : (
        <>
          <div className={s.title}>The engine stopped</div>
          <pre className={s.detail}>{message}</pre>
          <button className={s.retry} onClick={retry}>Restart engine</button>
        </>
      )}
    </div>
  )
}
