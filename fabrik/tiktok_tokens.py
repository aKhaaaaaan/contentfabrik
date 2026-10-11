"""Rotierende TikTok-Tokens in CI verschluesselt sichern, nie als Artefakt/Repo-Datei."""
import base64
import hashlib
import json
import os
from pathlib import Path


def atomar(pfad, daten):
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + '.tmp')
    tmp.write_bytes(daten)
    tmp.replace(pfad)


def cache_pfad():
    wert = os.environ.get('TIKTOK_TOKEN_CACHE')
    return Path(wert) if wert else None


def _fernet(secret):
    from cryptography.fernet import Fernet
    key = hashlib.sha256(b'contentfabrik-tiktok-v1\0' + secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def laden(secret):
    """Secret als Ausgangspunkt; neu angemeldete Tokens ueberstimmen alte Cache-Eintraege."""
    try:
        basis = json.loads(os.environ['TIKTOK_TOKENS'])
        if not isinstance(basis, dict):
            raise ValueError
        pfad = cache_pfad()
        cache = json.loads(_fernet(secret).decrypt(pfad.read_bytes())) if pfad and pfad.exists() else {}
        for oid, token in basis.items():
            refresh = token.get('refresh_token') if isinstance(token, dict) else token
            seed = hashlib.sha256(str(refresh).encode()).hexdigest()
            if oid in cache and cache[oid].get('seed') == seed:
                if isinstance(token, dict):
                    basis[oid] = dict(token, refresh_token=cache[oid]['refresh_token'])
                else:
                    basis[oid] = cache[oid]['refresh_token']
        return basis
    except Exception:
        raise RuntimeError('TikTok-Tokenkonfiguration/verschluesselter Cache ungueltig') from None


def speichern(oid, refresh, secret):
    pfad = cache_pfad()
    if not pfad:
        raise RuntimeError('Rotierter TikTok-Token braucht TIKTOK_TOKEN_CACHE in CI')
    basis = json.loads(os.environ['TIKTOK_TOKENS'])
    token = basis[oid]
    seed = token.get('refresh_token') if isinstance(token, dict) else token
    cache = json.loads(_fernet(secret).decrypt(pfad.read_bytes())) if pfad.exists() else {}
    cache[oid] = {'seed': hashlib.sha256(seed.encode()).hexdigest(), 'refresh_token': refresh}
    atomar(pfad, _fernet(secret).encrypt(json.dumps(cache).encode()))
