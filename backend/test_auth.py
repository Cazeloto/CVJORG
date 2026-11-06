import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

from .auth import hash_password, normalize_email, verify_password
from .main import app


async def request(path, method='GET', body=None, cookie=None, origin='http://localhost:5173'):
    headers = [(b'host', b'localhost'), (b'origin', origin.encode()), (b'content-type', b'application/json')]
    if cookie:
        headers.append((b'cookie', cookie.encode()))
    payload = json.dumps(body or {}).encode()
    sent = False
    messages = []
    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {'type': 'http.request', 'body': payload, 'more_body': False}
        await asyncio.Event().wait()
    async def send(message):
        messages.append(message)
    await app({'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.4'},
               'http_version': '1.1', 'method': method, 'scheme': 'http', 'path': path,
               'raw_path': path.encode(), 'query_string': b'', 'root_path': '',
               'headers': headers, 'server': ('localhost', 80), 'client': ('127.0.0.1', 1234)}, receive, send)
    start = next(m for m in messages if m['type'] == 'http.response.start')
    return start['status'], dict(start['headers'])


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoded = hash_password('a long test password')

    def call(self, *args, **kwargs):
        return asyncio.run(request(*args, **kwargs))

    def test_password_and_normalization(self):
        self.assertTrue(verify_password('a long test password', self.encoded))
        self.assertFalse(verify_password('wrong password', self.encoded))
        self.assertEqual(normalize_email(' Person@Example.COM '), 'person@example.com')
        with self.assertRaises(ValueError):
            normalize_email('not-an-email')

    def test_anonymous_cannot_read_records(self):
        with patch('backend.main.psycopg.connect') as connect:
            status, headers = self.call('/api/mediums')
            self.assertEqual(status, 401)
            self.assertEqual(headers[b'cache-control'], b'no-store')
            connect.assert_not_called()

    def test_csrf_origin_rejected(self):
        with patch('backend.main.psycopg.connect') as connect:
            self.assertEqual(self.call('/api/auth/logout', 'POST', origin='https://untrusted.example')[0], 403)
            connect.assert_not_called()

    def db(self, connect):
        conn = MagicMock()
        connect.return_value.__enter__.return_value = conn
        conn.execute.return_value.fetchone.return_value = (1,)
        cur = conn.cursor.return_value.__enter__.return_value
        return conn, cur

    @patch('backend.main.psycopg.connect')
    def test_expired_or_revoked_session(self, connect):
        _, cur = self.db(connect)
        cur.fetchone.return_value = None
        self.assertEqual(self.call('/api/mediums', cookie='cvj_session=expired')[0], 401)

    @patch('backend.main.psycopg.connect')
    def test_login_cookie_and_logout(self, connect):
        conn, cur = self.db(connect)
        cur.fetchone.return_value = {'id': 1, 'email': 'person@example.com', 'active': True, 'password_hash': self.encoded}
        status, headers = self.call('/api/auth/login', 'POST', {'email': 'PERSON@example.com', 'password': 'a long test password'})
        self.assertEqual(status, 200)
        self.assertIn(b'HttpOnly', headers[b'set-cookie'])
        self.assertIn(b'SameSite=lax', headers[b'set-cookie'])
        self.assertEqual(self.call('/api/auth/me', cookie='cvj_session=valid')[0], 200)
        self.assertEqual(self.call('/api/auth/logout', 'POST', cookie='cvj_session=valid')[0], 200)
        self.assertIn('DELETE FROM public.cvj_sessions', conn.execute.call_args.args[0])

    @patch('backend.main.psycopg.connect')
    def test_bad_password_and_disabled_account(self, connect):
        _, cur = self.db(connect)
        cur.fetchone.return_value = {'id': 1, 'email': 'person@example.com', 'active': False, 'password_hash': self.encoded}
        for password in ['wrong', 'a long test password']:
            self.assertEqual(self.call('/api/auth/login', 'POST', {'email': 'person@example.com', 'password': password})[0], 401)

    @patch('backend.main.psycopg.connect')
    def test_rate_limit(self, connect):
        conn, _ = self.db(connect)
        conn.execute.return_value.fetchone.return_value = (6,)
        self.assertEqual(self.call('/api/auth/login', 'POST', {'email': 'person@example.com', 'password': 'wrong'})[0], 429)


if __name__ == '__main__':
    unittest.main()
