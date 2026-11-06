"""Run from the repository root: python -m backend.manage_users init|create|reset|disable"""
import argparse
from getpass import getpass

from .auth import hash_password, init_auth, normalize_email
from .main import db_connection


def main():
    parser = argparse.ArgumentParser(description='Administrar acesso à Casa da Vovó Joaquina')
    parser.add_argument('action', choices=['init', 'create', 'reset', 'disable'])
    args = parser.parse_args()
    if args.action == 'init':
        init_auth(db_connection)
        print('Estrutura de acesso preparada.')
        return
    email = normalize_email(input('E-mail: '))
    password_hash = None
    if args.action in {'create', 'reset'}:
        password = getpass('Senha (mínimo 12 caracteres): ')
        if not 12 <= len(password) <= 256:
            raise ValueError('Use entre 12 e 256 caracteres.')
        if password != getpass('Confirme a senha: '):
            raise ValueError('As senhas não coincidem.')
        password_hash = hash_password(password)
    with db_connection() as conn:
        if args.action == 'create':
            row = conn.execute('''INSERT INTO public.cvj_users (email,password_hash)
                VALUES (%s,%s) ON CONFLICT (email) DO NOTHING RETURNING id''', (email, password_hash)).fetchone()
            if not row:
                raise ValueError('E-mail já cadastrado. Use reset para trocar a senha.')
        else:
            if args.action == 'reset':
                row = conn.execute('UPDATE public.cvj_users SET password_hash=%s WHERE email=%s RETURNING id',
                                   (password_hash, email)).fetchone()
            else:
                row = conn.execute('UPDATE public.cvj_users SET active=false WHERE email=%s RETURNING id', (email,)).fetchone()
            if not row:
                raise ValueError('Usuário não encontrado.')
            conn.execute('DELETE FROM public.cvj_sessions WHERE user_id=%s', (row[0],))
    print('Operação concluída.')


if __name__ == '__main__':
    try:
        main()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
