# Acesso por e-mail

O login usa e-mail e senha. Não existe cadastro público: o responsável cria as contas pelo terminal. Todos os usuários ativos têm acesso à consulta dos médiuns. Contas de acesso são independentes da tabela de médiuns; nenhum cadastro recebe acesso automaticamente.

## Preparar o banco e criar a primeira conta

No PowerShell, dentro de `C:\CVJORG`, com `backend/.env` configurado:

```powershell
.\.venv\Scripts\python.exe -m backend.manage_users init
.\.venv\Scripts\python.exe -m backend.manage_users create
```

O segundo comando solicita e-mail e senha (mínimo de 6 caracteres). A senha não aparece ao digitar. Não informe senhas pelo chat. `init` cria somente as tabelas `cvj_users`, `cvj_sessions` e `cvj_login_limits`, sem modificar os cadastros existentes.

Para trocar uma senha ou desativar uma conta:

```powershell
.\.venv\Scripts\python.exe -m backend.manage_users reset
.\.venv\Scripts\python.exe -m backend.manage_users disable
```

Essas operações encerram as sessões da conta. Não há recuperação automática por e-mail nesta etapa.

## Executar localmente

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Em outro terminal:

```powershell
cd frontend
npm.cmd run dev
```

Abra `http://localhost:5173`. O ambiente local usa `COOKIE_SECURE=false`. A API aceita alterações apenas quando o cabeçalho Origin corresponde a uma entrada em `CORS_ORIGINS` (incluindo a porta exata).

## Publicação

- Use HTTPS e `COOKIE_SECURE=true`.
- Sirva interface e `/api` no mesmo domínio, com proxy como o Nginx já incluído. A sessão usa SameSite=Lax: publicar interface e API em domínios independentes requer ajustar a arquitetura; não basta definir VITE_API_URL.
- Configure `CORS_ORIGINS` com a origem HTTPS exata da interface, sem barra final; não use `*`.
- Configure DATABASE_URL apenas no servidor. Não inclua `.env` no repositório ou imagem.
- Execute `init` antes de disponibilizar o login e crie as contas autorizadas.
- As sessões expiram em 8 horas; logout revoga a sessão no banco. Senhas usam scrypt com salt aleatório e o banco armazena somente o hash dos tokens de sessão.
- Há limite de 5 tentativas por e-mail a cada 15 minutos, compartilhado entre instâncias. Para publicação, complemente com limite por IP no proxy/provedor contra tentativas distribuídas em vários e-mails.
- Respostas da API usam `Cache-Control: no-store`; não configure cache de `/api` no proxy ou service worker.

## Verificação

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_auth -v
cd frontend
npm.cmd run build
npm.cmd run lint
```

Os testes de API usam conexões simuladas e não alteram dados no Neon. Após criar a conta, valide login, consulta e saída no navegador.
