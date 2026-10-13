import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

PERMISSIONS = ['cats.submit', 'cats.photos', 'cats.status', 'medical.read', 'medical.write', 'adoptions.lookup']
LOCAL_TZ = timezone(timedelta(hours=-3))


def now():
    return int(time.time() * 1000)


def uid():
    import uuid
    return str(uuid.uuid4())


def fail(status, message):
    raise HTTPException(status, message)


def text(value, maximum=200, required=True):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        fail(400, 'Confira os campos obrigatórios.')
    return value.strip()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=5, dklen=32)
    return salt + ':' + key.hex()


def check_password(value, stored):
    if not isinstance(value, str) or len(value) > 128:
        return False
    return hmac.compare_digest(password_hash(value, stored.split(':')[0]), stored)


def validate_password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        fail(400, 'Use uma senha de 12 a 128 caracteres.')
    return value


def email(value):
    value = text(value, 254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        fail(400, 'Informe um e-mail válido.')
    return value


def cpf(value):
    value = re.sub(r'[.\-\s]', '', value) if isinstance(value, str) else ''
    if not re.fullmatch(r'\d{11}', value) or len(set(value)) == 1:
        fail(400, 'Informe um CPF válido.')
    for n in (9, 10):
        digit = sum(int(value[i]) * (n + 1 - i) for i in range(n)) * 10 % 11 % 10
        if digit != int(value[n]):
            fail(400, 'Informe um CPF válido.')
    return value


def cpf_hash(db, value):
    secret = db.execute("SELECT txt_valor FROM configuracoes WHERE txt_chave='segredo_cpf'").fetchone()['value']
    return digest(secret + ':' + cpf(value))


def limit(pool, key, maximum=10):
    # Separate transaction: failed requests must also consume the rate limit.
    import psycopg
    from .db import portuguese_row
    with psycopg.connect(pool.conninfo,row_factory=portuguese_row) as db:
        row = db.execute('INSERT INTO limites_requisicoes VALUES(%s,1,to_timestamp(%s/1000.0)) ON CONFLICT(txt_chave) DO UPDATE SET num_contagem=limites_requisicoes.num_contagem+1 RETURNING num_contagem',
                         (digest(key + ':' + str(now() // 900000)), now() + 1800000)).fetchone()
    if row['count'] > maximum:
        fail(429, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.')


def permissions(db, user):
    if user['role'] == 'admin':
        return PERMISSIONS.copy()
    return [r['permission'] for r in db.execute('SELECT txt_permissao FROM permissoes_usuarios WHERE cod_usuario=%s ORDER BY txt_permissao', (user['id'],))]


def get_user(db, request):
    token = request.cookies.get('__Host-peticas_session') or request.cookies.get('peticas_session')
    if not token:
        return None
    user = db.execute('SELECT u.* FROM usuarios u JOIN sessoes s ON s.cod_usuario=u.cod_identificador WHERE s.cod_identificador=%s AND s.dat_expiracao>to_timestamp(%s/1000.0)', (digest(token), now())).fetchone()
    if user:
        user['permissions'] = permissions(db, user)
    return user


def safe_user(user):
    return {k: user[k] for k in ('id', 'name', 'email', 'role', 'permissions')} if user else None


def staff(user):
    if not user:
        fail(401, 'Entre na sua conta.')
    if user['role'] not in ('admin', 'staff'):
        fail(403, 'Seu acesso à equipe aguarda aprovação.')


def admin(user):
    staff(user)
    if user['role'] != 'admin':
        fail(403, 'Somente a responsável pode realizar esta ação.')


def permit(user, permission):
    staff(user)
    if permission not in user['permissions']:
        fail(403, 'Sua conta não tem permissão para esta ação.')


def date(value):
    value = text(value, 10)
    try:
        if datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d') != value:
            raise ValueError()
    except ValueError:
        fail(400, 'Informe uma data válida.')
    return value
