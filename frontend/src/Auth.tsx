import axios from 'axios'
import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { api } from './api'

type User = { email: string }

export default function Auth({ children }: { children: (user: User, logout: () => Promise<void>) => ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const interceptor = api.interceptors.response.use(response => response, error => {
      if (error.response?.status === 401 && !error.config?.url?.endsWith('/login')) setUser(null)
      return Promise.reject(error)
    })
    const controller = new AbortController()
    api.get<User>('/auth/me', { signal: controller.signal }).then(response => setUser(response.data)).catch(error => {
      if (!controller.signal.aborted && error.response?.status !== 401) setError('Não foi possível conectar. Tente entrar novamente.')
    }).finally(() => { if (!controller.signal.aborted) setChecking(false) })
    return () => { controller.abort(); api.interceptors.response.eject(interceptor) }
  }, [])
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      await api.post('/auth/login', { email, password })
      const response = await api.get<User>('/auth/me')
      setPassword(''); setUser(response.data)
    } catch (error) {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined
      setError(status === 429 ? 'Muitas tentativas. Aguarde 15 minutos.' : status === 401 ? 'E-mail ou senha inválidos, ou sessão indisponível.' : 'Não foi possível entrar. Confira a conexão e tente novamente.')
      setPassword('')
    } finally { setBusy(false) }
  }
  async function logout() {
    try {
      await api.post('/auth/logout')
      setUser(null); setPassword(''); setError(''); window.location.assign('#/')
    } catch { window.alert('Não foi possível encerrar a sessão. Tente novamente.') }
  }
  if (checking) return <main><section className="state-card" role="status">Verificando acesso…</section></main>
  if (user) return children(user, logout)
  return <main className="login-page"><section className="login-card">
    <p className="eyebrow">Casa da Vovó Joaquina</p>
    <h1>Entre na sua conta</h1>
    <p className="login-intro">Use seu e-mail e senha para acessar os cadastros.</p>
    <form onSubmit={login}>
      <label htmlFor="login-email">E-mail</label>
      <input id="login-email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} required maxLength={254} value={email} onChange={event => setEmail(event.target.value)} />
      <label htmlFor="login-password">Senha</label>
      <input id="login-password" type="password" autoComplete="current-password" required minLength={6} maxLength={256} value={password} onChange={event => setPassword(event.target.value)} />
      {error && <p className="login-error" role="alert">{error}</p>}
      <button className="login-submit" disabled={busy} type="submit">{busy ? 'Entrando…' : 'Entrar'}</button>
    </form>
    <p className="login-help">Para solicitar acesso ou redefinir sua senha, fale com o responsável pelo sistema.</p>
  </section></main>
}
