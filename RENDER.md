# Publicar no Render

Use um único **Web Service**, com runtime **Docker** e o `Dockerfile` da raiz. Ele compila o React e serve a interface e a API pelo FastAPI no mesmo endereço HTTPS. O PostgreSQL continua no Neon.

1. Envie o código atualizado ao GitHub, incluindo Dockerfile, .dockerignore, backend e frontend. Não envie arquivos .env.
2. No Render: New > Web Service > selecione o repositório.
3. Nome: cvjorg (ou outro disponível). Branch: a branch com o código. Language/Runtime: Docker.
4. Root Directory: vazio. Dockerfile Path: ./Dockerfile. Docker Build Context: raiz (.). Docker Command: vazio, para usar o CMD da imagem.
5. Em Environment, configure DATABASE_URL com a conexão do Neon (com SSL), MEDIUM_TABLE=public.mediuns e COOKIE_SECURE=true.
6. Health Check Path: /api/health.
7. Crie o serviço. O Dockerfile usa PORT fornecida pelo Render. Não são necessários Build Command, Start Command, disco persistente ou um novo banco.
8. Abra o endereço HTTPS fornecido e teste login, consulta e saída. As contas existentes no Neon continuam válidas; não é necessário executar init novamente.

A origem RENDER_EXTERNAL_URL fornecida pelo Render é autorizada automaticamente para login/logout. Se usar domínio próprio, configure CORS_ORIGINS com a origem HTTPS exata (por exemplo https://app.exemplo.com), sem barra final.

Não configure VITE_API_URL: a interface usa /api no mesmo domínio. Não selecione backend/Dockerfile ou frontend/Dockerfile; eles pertencem ao fluxo antigo de Docker Compose.

O endpoint de saúde confirma que o processo está respondendo; não valida a conexão ao banco. Valide a consulta de cadastros após o deploy.

Documentação: https://render.com/docs/docker e https://render.com/docs/web-services
