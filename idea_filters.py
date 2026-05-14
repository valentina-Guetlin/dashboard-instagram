import re

URL_RE = re.compile(r"https?://\S+")
EMAIL_ONLY_RE = re.compile(r"^\s*[\w.+-]+@[\w-]+\.[\w.-]+\s*$")

ADORATION_PATTERNS = [
    r"\bte amo+\b", r"\bte adoro\b", r"\bte admiro\b",
    r"\beres mi (?:[íi]dola|[íi]dolo|favorita?)\b",
    r"\beres (?:mi |la |un |una )?(?:diosa?|reina?|reinota|favorita?|m[aá]xima?|crack|grande|inspiraci[óo]n)\b",
    r"\bdios[ae]\b", r"\breina\b", r"\breinota\b", r"\bpreciosa\b",
    r"\bhermosa\b", r"\blinda+\b", r"\blindo+\b", r"\bbonita\b",
    r"\bbonito\b", r"\bbella\b", r"\bdivina\b", r"\bbrutal\b",
    r"\bespectacular\b", r"\bfabulosa?\b", r"\bgenial\b", r"\bincre[ií]ble\b",
    r"\bperfecta?\b", r"\bmaravillosa?\b", r"\bbuen[íi]sim[ao]\b",
    r"\bbrav[oa]\b", r"\bfelicit\w*\b", r"\bfelicidades\b", r"\bgracias\b",
    r"\bque (?:linda|lindo|hermosa|preciosa|bella|bonita|chimba|chimbita|genia)\b",
    r"\bqu[eé] (?:linda|lindo|hermosa|preciosa|bella|bonita|chimba|chimbita|genia)\b",
    r"\bla (?:mejor|m[aá]xima|m[aá]s|number one)\b", r"\beres la mejor\b",
    r"\bsublim\w*\b", r"\bidola\b", r"\b[íi]dola\b", r"\b[íi]dolo\b",
    r"\bbb+\b", r"\b(?:hola|holi|holaa+)\b",
    r"\bi love (?:it|you|this)\b", r"\blove (?:it|you|this)\b",
    r"\bamazing\b", r"\bgorgeous\b", r"\bbeautiful\b", r"\bawesome\b",
    r"\bperfect\b", r"\bqueen\b", r"\bstunning\b", r"\bso cute\b",
    r"\byes\b", r"\bwow\b", r"\bomg\b", r"\bjajaja+\b", r"\bjeje+\b",
    r"\bjiji+\b", r"\bguau+\b", r"\bayyy+\b", r"\baaa+\b", r"\bsii+\b",
    r"\bs[íi]\b", r"\bclaro\b", r"\bok+\b", r"\bcierto\b", r"\btotal\b",
    r"\beso es\b", r"\bmuy bien\b", r"\bsuper\b", r"\bs[uú]per\b",
    r"\btal cual\b", r"\bexacto\b",
]

BOT_PATTERNS = [
    r"\bhaz cl[ií]ck? aqu[ií]\b", r"\bhaz clic aqu[ií]\b",
    r"\bd[eé]jame contarte\b", r"\bte prepar[eé]\b",
    r"\bnunca hab[ií]a compartido\b", r"\bes mi programa m[aá]s\b",
    r"\bmi programa m[aá]s completo\b", r"\bes mi curso m[aá]s\b",
    r"\baprende(?:r[aá]s|s) (?:todo|de cero)\b", r"\bcuando quieras acceder\b",
    r"\baccede al curso\b", r"\bcurso gratuito\b", r"\bnos vemos ah[ií]\b",
    r"\bestoy por aqu[ií]\b", r"\bsolo me quiero asegurar\b",
    r"\bme quiero asegurar de que\b", r"\bperfecto!? para tener acceso\b",
    r"\bperfecto!? ahora s[oó]?lo voy a necesitar\b",
    r"\bahora s[oó]lo voy a necesitar\b", r"\bveo en mi sistema\b",
    r"\bya tengo tu (?:correo|email|nombre)\b", r"\best[aá]s en l[ií]nea\b",
    r"\bescr[ií]belo abajo\b", r"\bconsiste en \d+ correos?\b",
    r"\bcada correo est[aá] dise[ñn]ado\b",
    r"\bes la misma estrategia que us[eé]\b",
    r"\bun gusto tenerte por aqu[ií]\b", r"\bya eres de la casa\b",
    r"\baqu[ií] lo tienes+\b", r"\bs[ií]i+ por aqu[ií]\b",
    r"\bun gusto saludarte+\b", r"\bqu[eé] lindo verte\b",
    r"\bsi quieres acceso\b", r"\bdale clic\b", r"\bhaz clic\b",
    # Add your bot name / program names here:
    # r"\bRuperta\b", r"\bCash Content\b",
]

_adoration_re = re.compile("|".join(ADORATION_PATTERNS), re.IGNORECASE)
_bot_re = re.compile("|".join(BOT_PATTERNS), re.IGNORECASE)


def _strip_adoration(text):
    return _adoration_re.sub("", text).strip()


def is_likely_bot_message(text):
    if _bot_re.search(text):
        return True
    url_stripped = URL_RE.sub("", text).strip()
    if EMAIL_ONLY_RE.match(text):
        return True
    if URL_RE.search(text) and len(url_stripped) < 20:
        return True
    return False


def is_substantive_comment(text, min_len=20):
    if not text or not text.strip():
        return False
    cleaned = _strip_adoration(text)
    if len(cleaned) < min_len and "?" not in text and "¿" not in text:
        return False
    if re.match(r"^[\s\W]+$", text):
        return False
    return True


def is_substantive_dm(text, min_len=15):
    if not text or not text.strip():
        return False
    if is_likely_bot_message(text):
        return False
    if re.match(r"^[\s\W]+$", text):
        return False
    cleaned = _strip_adoration(text)
    if len(cleaned) < min_len and "?" not in text and "¿" not in text:
        return False
    return True


def filter_comments(comments):
    return [c for c in comments if is_substantive_comment(c.get("text", "") or c.get("content", "") or "")]


def filter_dms(messages):
    return [m for m in messages if is_substantive_dm(m.get("text", "") or m.get("content", "") or "")]
