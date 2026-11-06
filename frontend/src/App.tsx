import Auth from './Auth'
import { api } from './api'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { ArrowLeft, ChevronRight, Home, Moon, Search, Sun, Users, UserRound, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import './App.css'

type Medium = Record<string, unknown>
const orixas = { med_frente: 'De frente', med_adjunto: 'Adjunto', med_ancestre: 'Ancestral' }
const entidades = {
  med_pretov: 'Preto-velho', med_caboc: 'Caboclo', med_boiad: 'Boiadeiro',
  med_malan: 'Malandro', med_marin: 'Marinheiro', med_pombog: 'Pombagira',
  med_exu: 'Exu', med_encant: 'Encantado', med_ere: 'Erê', med_baiano: 'Baiano',
  med_cigano: 'Cigano', med_egum: 'Egum', med_oriente: 'Oriente', med_guias: 'Guias',
}
const cadastro = {
  med_codigo: 'Código', med_nome: 'Nome', med_apelido: 'Apelido', med_nascim: 'Nascimento',
  med_admissao: 'Admissão', med_categoria: 'Categoria', med_equipe: 'Equipe',
  med_fonecel: 'Celular', med_email: 'E-mail', med_endereco: 'Endereço',
  med_complemento: 'Complemento', med_bairro: 'Bairro', med_cidade: 'Cidade', med_cep: 'CEP',
}
function displayValue(value: unknown): string {
  if (value === null || value === undefined || String(value).trim() === '') return 'Não informado'
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    const date = parseISO(value)
    if (!Number.isNaN(date.getTime())) return format(date, 'dd MMM yyyy', { locale: ptBR })
  }
  return String(value).trim()
}
function name(medium: Medium) { return displayValue(medium.med_nome ?? medium.nome) }
function Fields({ title, fields, medium }: { title: string; fields: Record<string, string>; medium: Medium }) {
  return <section className="field-section"><h2>{title}</h2><dl className="details">
    {Object.entries(fields).map(([key, label]) => <div className="detail-row" key={key}>
      <dt>{label}</dt><dd className={displayValue(medium[key]) === 'Não informado' ? 'empty-value' : ''}>{displayValue(medium[key])}</dd>
    </div>)}
  </dl></section>
}
function App({ email, logout }: { email: string; logout: () => Promise<void> }) {
  const [route, setRoute] = useState(() => window.location.hash || '#/')
  const [mediums, setMediums] = useState<Medium[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [dark, setDark] = useState(() => localStorage.getItem('theme') !== 'light')
  const isMediums = route.startsWith('#/mediums')
  const selectedId = route.split('/')[2]
  const selected = mediums.find(medium => String(medium.med_codigo) === selectedId)
  useEffect(() => {
    const update = () => { setRoute(window.location.hash || '#/'); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])
  useEffect(() => {
    if (!isMediums) return
    const controller = new AbortController()
    const load = async () => {
      setLoading(true); setError('')
      try {
        const response = await api.get('/mediums', { signal: controller.signal })
        setMediums(response.data.items)
      } catch {
        if (!controller.signal.aborted) setError('Não foi possível carregar os médiuns. Tente novamente.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [isMediums, retry])
  const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  const filtered = mediums.filter(medium => normalize(`${name(medium)} ${medium.med_apelido ?? ''}`).includes(normalize(search)))
  return <main>
    <header className="topbar">
      <div><p className="eyebrow">Casa da Vovó Joaquina</p><h1>{!isMediums ? 'Início' : selectedId ? 'Cadastro do médium' : 'Médiuns'}</h1></div>
      <button className="icon-button" type="button" onClick={() => setDark(value => !value)} aria-label="Alternar tema">{dark ? <Sun size={20} /> : <Moon size={20} />}</button>
    </header>
    <div className="account-bar"><span>{email}</span><button type="button" onClick={() => void logout()}>Sair</button></div>
    {!isMediums ? <>
      <section className="welcome"><span className="home-symbol"><Home size={30} /></span><p className="eyebrow">Bem-vindo à casa</p><h2>Tudo começa por aqui.</h2><p>Acesse as funções da Casa da Vovó Joaquina.</p></section>
      <h2 className="section-title">O que você deseja acessar?</h2>
      <a className="feature-card" href="#/mediums"><span className="avatar"><Users size={26} /></span><span><strong>Médiuns</strong><small>Consulte cadastros, orixás e entidades.</small></span><ChevronRight size={22} /></a>
    </> : <>
      <a className="back-link" href={selectedId ? '#/mediums' : '#/'}><ArrowLeft size={18} />{selectedId ? 'Voltar para médiuns' : 'Voltar ao início'}</a>
      {loading ? <section className="loading-list" aria-label="Carregando">{[1, 2, 3].map(item => <div className="skeleton" key={item} />)}</section> : error ? <section className="state-card error" role="alert"><strong>Cadastro indisponível</strong><span>{error}</span><button className="retry-button" onClick={() => setRetry(value => value + 1)}>Tentar novamente</button></section> : selectedId ? selected ? <>
        <section className="profile-heading"><span className="avatar"><UserRound size={28} /></span><div><h2>{name(selected)}</h2><p>{displayValue(selected.med_categoria)}</p></div></section>
        <Fields title="Orixás" fields={orixas} medium={selected} />
        <Fields title="Entidades" fields={entidades} medium={selected} />
        <Fields title="Dados cadastrais" fields={cadastro} medium={selected} />
      </> : <section className="state-card"><strong>Médium não encontrado</strong><span>Volte à lista e selecione um cadastro.</span></section> : <>
        <section className="search-wrap" aria-label="Filtros"><Search size={18} aria-hidden="true" /><input aria-label="Buscar médium por nome ou apelido" value={search} onChange={event => setSearch(event.target.value)} placeholder="Buscar por nome ou apelido" />{search && <button type="button" onClick={() => setSearch('')} aria-label="Limpar busca"><X size={18} /></button>}</section>
        <div className="list-count" aria-live="polite">{filtered.length} {filtered.length === 1 ? 'cadastro' : 'cadastros'}</div>
        {!filtered.length && <section className="state-card"><strong>Nenhum cadastro encontrado</strong><span>Tente outro nome ou apelido.</span></section>}
        <section className="medium-list">{filtered.map(medium => <a className="medium-card" key={String(medium.med_codigo)} href={`#/mediums/${medium.med_codigo}`}>
          <span className="avatar"><UserRound size={22} /></span><span className="medium-summary"><strong>{name(medium)}</strong><small>{displayValue(medium.med_categoria)}</small><small className="profile-link">Ver orixás e entidades</small></span><ChevronRight size={20} />
        </a>)}</section>
      </>}
    </>}
    <nav className="bottom-nav" aria-label="Navegação principal"><a href="#/" aria-current={!isMediums ? 'page' : undefined}><Home size={21} />Início</a><a href="#/mediums" aria-current={isMediums ? 'page' : undefined}><Users size={21} />Médiuns</a></nav>
  </main>
}
export default function ProtectedApp() {
  return <Auth>{(user, logout) => <App email={user.email} logout={logout} />}</Auth>
}
