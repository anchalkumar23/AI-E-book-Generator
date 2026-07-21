import { useState, useEffect } from 'react'
import { EngineGate } from './components/engine-gate/engine-gate'
import { ChatView } from './views/chat/chat'
import { LibraryView } from './views/library/library'
import { ReaderView } from './views/reader/reader'
import { SettingsView } from './views/settings/settings'
import { api } from './lib/api'

type Route =
  | { name: 'chat' }
  | { name: 'library' }
  | { name: 'reader'; id: number }
  | { name: 'settings' }

/** Three screens — a state machine beats pulling in a router library. */
function Router() {
  const [route, setRoute]       = useState<Route | null>(null)
  const [hasBooks, setHasBooks] = useState(false)

  // Land on the library if books exist, otherwise the composer — an empty
  // library is a dead end for a first-run user.
  useEffect(() => {
    api.books.list()
      .then(books => {
        setHasBooks(books.length > 0)
        setRoute(books.length ? { name: 'library' } : { name: 'chat' })
      })
      .catch(() => setRoute({ name: 'chat' }))
  }, [])

  if (!route) return null // EngineGate already showed a spinner; avoid a flash

  if (route.name === 'reader') {
    return <ReaderView id={route.id} onBack={() => setRoute({ name: 'library' })} />
  }
  if (route.name === 'settings') {
    return <SettingsView onBack={() => setRoute({ name: 'library' })} />
  }
  if (route.name === 'library') {
    return (
      <LibraryView
        onOpenBook={id => setRoute({ name: 'reader', id })}
        onNewBook={() => setRoute({ name: 'chat' })}
        onOpenSettings={() => setRoute({ name: 'settings' })}
      />
    )
  }
  return (
    <ChatView
      hasBooks={hasBooks}
      onLibrary={() => setRoute({ name: 'library' })}
      onOpenBook={id => setRoute({ name: 'reader', id })}
    />
  )
}

export function App() {
  return (
    <EngineGate>
      <Router />
    </EngineGate>
  )
}
