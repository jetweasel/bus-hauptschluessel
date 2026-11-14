#!/usr/bin/env python3
"""Main key of the bus, kept by the owner (T-0330). Runs on the owner's own computer with nothing but Python 3:
no packages, no network. The server never sees the main key, only the operator document (op.jwt) it signs.

  python3 mainkey.py new <current-op.jwt-file|-> [keyfile]
      Create the main key in keyfile (default ./jetweasel-bus-hauptschluessel.nk, never overwritten) and print a
      new op.jwt that trusts the same signing key and system account as the current one: every account and every
      credential on the bus stays valid, the bus only needs one restart.
  python3 mainkey.py sign <current-op.jwt-file|-> [keyfile] [--signing-key O...]
      Re-sign with the existing main key, e.g. to add (or with --replace, to swap) a signing key.

The op.jwt printed contains public keys only; it may be pasted anywhere. The keyfile must stay with the owner.
"""
import base64
import hashlib
import json
import os
import sys
import time

# --- Ed25519 (RFC 8032, section 6), pure Python; slow but only used a few times ---
P = 2 ** 255 - 19
L = 2 ** 252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
I = pow(2, (P - 1) // 4, P)


def _recover_x(y, sign):
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P)
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P:
        x = x * I % P
    if x & 1 != sign:
        x = P - x
    return x


_GY = 4 * pow(5, P - 2, P) % P
G = (_recover_x(_GY, 0), _GY, 1, _recover_x(_GY, 0) * _GY % P)


def _add(a, b):
    A = (a[1] - a[0]) * (b[1] - b[0]) % P
    B = (a[1] + a[0]) * (b[1] + b[0]) % P
    C = 2 * a[3] * b[3] * D % P
    Dd = 2 * a[2] * b[2] % P
    E, F, Gg, H = B - A, Dd - C, Dd + C, B + A
    return (E * F % P, Gg * H % P, F * Gg % P, E * H % P)


def _mul(s, pt):
    q = (0, 1, 1, 0)
    while s:
        if s & 1:
            q = _add(q, pt)
        pt = _add(pt, pt)
        s >>= 1
    return q


def _enc(pt):
    zi = pow(pt[2], P - 2, P)
    x, y = pt[0] * zi % P, pt[1] * zi % P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _h(*parts):
    return int.from_bytes(hashlib.sha512(b"".join(parts)).digest(), "little")


def _expand(seed):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def ed_public(seed):
    return _enc(_mul(_expand(seed)[0], G))


def ed_sign(seed, msg):
    a, prefix = _expand(seed)
    pub = _enc(_mul(a, G))
    r = _h(prefix, msg) % L
    R = _enc(_mul(r, G))
    s = (r + _h(R, pub, msg) * a) % L
    return R + s.to_bytes(32, "little")


# --- nkeys encoding (same as the nats tooling) ---
PREFIX_SEED, PREFIX_OPERATOR = 18 << 3, 14 << 3


def _crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def _b32(raw):
    return base64.b32encode(raw + _crc16(raw).to_bytes(2, "little")).decode().rstrip("=")


def _unb32(text):
    raw = base64.b32decode(text + "=" * (-len(text) % 8))
    body, crc = raw[:-2], int.from_bytes(raw[-2:], "little")
    if _crc16(body) != crc:
        raise SystemExit("key file damaged: checksum does not match")
    return body


def seed_encode(seed):
    return _b32(bytes([PREFIX_SEED | (PREFIX_OPERATOR >> 5), (PREFIX_OPERATOR & 31) << 3]) + seed)


def seed_decode(text):
    body = _unb32(text.strip())
    if body[0] != PREFIX_SEED | (PREFIX_OPERATOR >> 5) or body[1] >> 3 != PREFIX_OPERATOR & 31 or len(body) != 34:
        raise SystemExit("not an operator seed")
    return body[2:]


def public_key(seed):
    return _b32(bytes([PREFIX_OPERATOR]) + ed_public(seed))


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def claims_of(jwt):
    body = jwt.strip().split(".")[1]
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def operator_jwt(seed, name, signing_keys, system_account):
    """Self-signed operator JWT, same layout as jw-groups issuer.njwt.sign."""
    pk = public_key(seed)
    claims = {"iat": int(time.time()), "iss": pk, "name": name, "sub": pk,
              "nats": {"type": "operator", "signing_keys": signing_keys, "system_account": system_account, "version": 2}}
    claims["jti"] = base64.b32encode(hashlib.sha256(json.dumps(claims, sort_keys=True).encode()).digest()).decode().rstrip("=")
    head = _b64(json.dumps({"typ": "JWT", "alg": "ed25519-nkey"}).encode())
    body = _b64(json.dumps(claims).encode())
    return f"{head}.{body}.{_b64(ed_sign(seed, f'{head}.{body}'.encode()))}"


def _read_current(src):
    text = sys.stdin.read() if src == "-" else open(src).read()
    c = claims_of(text)
    n = c.get("nats", {})
    if n.get("type") != "operator" or not n.get("signing_keys") or not n.get("system_account"):
        raise SystemExit("that is not an operator document with signing key and system account")
    return c, n


def main(argv):
    if len(argv) < 2 or argv[0] not in ("new", "sign"):
        raise SystemExit(__doc__)
    args = [a for a in argv[1:] if not a.startswith("--")]
    extra = argv[argv.index("--signing-key") + 1] if "--signing-key" in argv else None
    if extra:
        args.remove(extra)
    current, keyfile = args[0], (args[1] if len(args) > 1 else "jetweasel-bus-hauptschluessel.nk")
    c, n = _read_current(current)
    if argv[0] == "new":
        if os.path.exists(keyfile):
            raise SystemExit(f"{keyfile} exists already: use 'sign', a second main key is never made over it")
        seed = os.urandom(32)
        fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(seed_encode(seed) + "\n")
    else:
        seed = seed_decode(open(keyfile).read())
    signing = list(n["signing_keys"])
    if extra:
        if not (extra.startswith("O") and len(extra) == 56):
            raise SystemExit("--signing-key must be an operator public key (O..., 56 characters)")
        signing = [extra] if "--replace" in argv else signing + [k for k in [extra] if k not in signing]
    print(operator_jwt(seed, c.get("name", "jw"), signing, n["system_account"]))
    print(f"main key {public_key(seed)} in {os.path.abspath(keyfile)}: keep it safe, never on a server",
          file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
