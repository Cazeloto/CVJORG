"""Email/password authentication with revocable server-side sessions."""
import hashlib
import hmac
import os
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator

COOKIE = 'cvj_session'
SESSION_SECONDS = 8 * 60 * 60


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise ValueError('Informe um e-mail válido.')
    return value


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=131072,
                            r=8, p=1, maxmem=256 * 1024 * 1024).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, _ = encoded.split('$')
        return algorithm == 'scrypt' and hmac.compare_digest(hash_password(password, salt), encoded)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def init_auth(connect):
    with connect() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS public.cvj_users (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email text NOT NULL UNIQUE CHECK (email = lower(email)),
            password_hash text NOT NULL,
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now())''')
        conn.execute('''CREATE TABLE IF NOT EXISTS public.cvj_sessions (
            token_hash text PRIMARY KEY,
            user_id bigint NOT NULL REFERENCES public.cvj_users(id) ON DELETE CASCADE,
            expires_at timestamptz NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS public.cvj_login_limits (
            email_hash text PRIMARY KEY,
            attempts integer NOT NULL,
            window_start timestamptz NOT NULL DEFAULT now())''')


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=6, max_length=256)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        return normalize_email(value)


def build_auth(connect):
    router = APIRouter(prefix='/api/auth')
    dummy = hash_password(secrets.token_urlsafe(32))

    def current_user(request: Request):
        token = request.cookies.get(COOKIE, '')
        if not token or len(token) > 128:
            raise HTTPException(401, 'Entre para continuar.')
        with connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute('''SELECT u.id, u.email FROM public.cvj_sessions s
                    JOIN public.cvj_users u ON u.id=s.user_id
                    WHERE s.token_hash=%s AND s.expires_at>now() AND u.active''', (token_hash(token),))
                user = cur.fetchone()
        if not user:
            raise HTTPException(401, 'Sua sessão expirou. Entre novamente.')
        return user

    @router.post('/login')
    def login(body: Login, request: Request, response: Response):
        # Atomic counter shared by all workers; failures and attempts for unknown users count alike.
        with connect() as conn:
            row = conn.execute('''INSERT INTO public.cvj_login_limits (email_hash, attempts)
                VALUES (%s, 1) ON CONFLICT (email_hash) DO UPDATE SET
                attempts=CASE WHEN cvj_login_limits.window_start < now()-interval '15 minutes'
                    THEN 1 ELSE cvj_login_limits.attempts+1 END,
                window_start=CASE WHEN cvj_login_limits.window_start < now()-interval '15 minutes'
                    THEN now() ELSE cvj_login_limits.window_start END RETURNING attempts''',
                (token_hash(body.email),)).fetchone()
        if row[0] > 5:
            raise HTTPException(429, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.', headers={'Retry-After': '900'})
        with connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute('SELECT * FROM public.cvj_users WHERE email=%s', (body.email,))
                user = cur.fetchone()
                valid = verify_password(body.password, user['password_hash'] if user else dummy)
                if not valid or not user or not user['active']:
                    raise HTTPException(401, 'E-mail ou senha inválidos.')
                token = secrets.token_urlsafe(32)
                cur.execute('DELETE FROM public.cvj_sessions WHERE expires_at<=now() OR token_hash=%s',
                            (token_hash(request.cookies.get(COOKIE, '')),))
                cur.execute('''INSERT INTO public.cvj_sessions (token_hash,user_id,expires_at)
                    VALUES (%s,%s,now()+interval '8 hours')''', (token_hash(token), user['id']))
                cur.execute('DELETE FROM public.cvj_login_limits WHERE email_hash=%s OR window_start<now()-interval \'1 day\'', (token_hash(body.email),))
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
                            secure=os.getenv('COOKIE_SECURE', 'true').lower() == 'true', samesite='lax', path='/api')
        return {'email': user['email']}

    @router.get('/me')
    def me(user=Depends(current_user)):
        return {'email': user['email']}

    @router.post('/logout')
    def logout(request: Request, response: Response):
        with connect() as conn:
            conn.execute('DELETE FROM public.cvj_sessions WHERE token_hash=%s',
                         (token_hash(request.cookies.get(COOKIE, '')),))
        response.delete_cookie(COOKIE, path='/api')
        return {'ok': True}

    return router, current_user
