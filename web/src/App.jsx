import { useAuth } from './hooks/useAuth.js'
import { BrandMark } from './components/BrandMark.jsx'
import { ConnectScreen } from './components/ConnectScreen.jsx'
import { InboxScreen } from './components/InboxScreen.jsx'
import { MockScenarioBar } from './components/MockScenarioBar.jsx'

export default function App() {
  const auth = useAuth()

  return (
    <>
      <MockScenarioBar />
      {auth.status === 'loading' ? (
        <main className="boot">
          <div className="boot-mark">
            <BrandMark size={72} />
          </div>
          <span className="boot-name">DraftAgent</span>
          <span className="boot-bar" aria-hidden="true">
            <span />
          </span>
          <span className="sr-only">Checking your session</span>
        </main>
      ) : auth.status === 'signed-in' ? (
        <InboxScreen email={auth.email} onSignOut={auth.signOut} onAuthError={auth.onAuthError} />
      ) : (
        <ConnectScreen expired={auth.expired} error={auth.error} onRetry={auth.check} />
      )}
    </>
  )
}
