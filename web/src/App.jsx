import { useAuth } from './hooks/useAuth.js'
import { ConnectScreen } from './components/ConnectScreen.jsx'
import { InboxScreen } from './components/InboxScreen.jsx'
import { MockScenarioBar } from './components/MockScenarioBar.jsx'
import { Spinner } from './components/Spinner.jsx'

export default function App() {
  const auth = useAuth()

  return (
    <>
      <MockScenarioBar />
      {auth.status === 'loading' ? (
        <main className="boot">
          <Spinner label="Checking your session" />
        </main>
      ) : auth.status === 'signed-in' ? (
        <InboxScreen email={auth.email} onSignOut={auth.signOut} onAuthError={auth.onAuthError} />
      ) : (
        <ConnectScreen expired={auth.expired} error={auth.error} onRetry={auth.check} />
      )}
    </>
  )
}
