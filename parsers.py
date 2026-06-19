"""Citation parsing: extract metadata from pasted citation text."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CitationData:
    authors: list[str] = field(default_factory=list)
    title: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    year: str = ""
    doi: str = ""
    url: str = ""
    raw: str = ""
    missing_fields: list[str] = field(default_factory=list)
    is_valid: bool = True
    detected_format: Optional[str] = None


# ---------------------------------------------------------------------------
# Author parsing helpers
# ---------------------------------------------------------------------------

def _split_authors_nature(raw: str) -> list[str]:
    """Parse 'Surname, I., Surname, I. & Surname, I. et al.' -> ['Surname, I.', ..., 'et al.']"""
    raw = raw.strip().rstrip(".")
    et_al = bool(re.search(r'\bet\s+al\.?', raw, re.IGNORECASE))
    raw = re.sub(r'\s*\bet\s+al\.?', '', raw, flags=re.IGNORECASE).strip().rstrip(",").strip()
    # & işaretini virgüle çevir (Springer/Nature: "Surname, I. & Surname, I.")
    raw = re.sub(r'\s*&\s*', ', ', raw)

    tokens = re.findall(
        r"[^\W\d_][^\W\d_\-''']*(?:[\-'''][^\W\d_]+)*(?:\s+[^\W\d_][^\W\d_\-''']*(?:[\-'''][^\W\d_]+)*)*"
        r',\s*[A-ZÁÉÍÓÖŐÚÜŰ]\.?(?:[A-ZÁÉÍÓÖŐÚÜŰ]\.?)*',
        raw
    )
    if not tokens:
        tokens = [p.strip() for p in re.split(r',\s*(?=[A-ZÁÉÍÓÖŐÚÜŰ])', raw) if p.strip()]

    # Her token'ın nokta ile bitmesini garantile
    tokens = [t.rstrip(".") + "." if not t.endswith(".") else t for t in tokens]

    if et_al:
        tokens.append("et al.")
    return tokens


def _split_authors_apa(raw: str) -> list[str]:
    """Parse APA 'Surname, I. I., Surname, I. I., & Surname, I. I.' -> list"""
    raw = raw.strip().rstrip(".")
    et_al = bool(re.search(r'\bet\s+al\.?', raw, re.IGNORECASE))
    raw = re.sub(r'\s*\bet\s+al\.?', '', raw, flags=re.IGNORECASE).strip().rstrip(",").strip()
    # ",\s*&" → virgül zaten var, sadece & sil; "\s*&\s*" → ", " ekle ama çift virgülden kaçın
    raw = re.sub(r',\s*&\s*', ', ', raw)   # "H., & M." → "H., M."
    raw = re.sub(r'\s*&\s*', ', ', raw)    # kalan & varsa

    tokens = re.findall(
        r"[^\W\d_][^\W\d_\-''’]*(?:[\-''’][^\W\d_]+)*(?:\s+[^\W\d_][^\W\d_\-''’]*(?:[\-''’][^\W\d_]+)*)*"
        r',\s*(?:[A-ZÁÉÍÓÖŐÚÜŰ]\.?\s*)+',
        raw
    )
    if not tokens:
        tokens = [p.strip() for p in re.split(r',\s*(?=[A-ZÁÉÍÓÖŐÚÜŰ][a-z])', raw) if p.strip()]

    tokens = [t.strip().rstrip(",").rstrip(".") + "." for t in tokens]

    if et_al:
        tokens.append("et al.")
    return tokens


# ---------------------------------------------------------------------------
# DOI / URL extraction
# ---------------------------------------------------------------------------

def _extract_doi(text: str) -> tuple[str, str]:
    m = re.search(r'https?://doi\.org/(10\.[^\s]+)', text, re.IGNORECASE)
    if m:
        doi = m.group(1).rstrip(".),")
        return doi, f"https://doi.org/{doi}"
    m = re.search(r'\bdoi:\s*(10\.[^\s,]+)', text, re.IGNORECASE)
    if m:
        doi = m.group(1).rstrip(".),")
        return doi, f"https://doi.org/{doi}"
    return "", ""


# ---------------------------------------------------------------------------
# Format detection heuristic
# ---------------------------------------------------------------------------

def _detect_format(text: str) -> Optional[str]:
    if re.search(r'@\w+\{', text):
        return "BibTeX"
    if re.search(r'Available at:', text, re.IGNORECASE):
        return "Harvard"
    if re.search(r'\.\s+\d{4};\s*\d+', text):
        return "Vancouver"
    # IEEE: "Title," Journal, vol. X, no. Y, pp. Z, year  — vol. + pp. birlikte
    if re.search(r'"[^"]+,"\s+\S', text) and re.search(r'vol\.\s*\d+', text, re.IGNORECASE) and re.search(r'pp\.\s*\d+', text, re.IGNORECASE):
        return "IEEE"
    if re.search(r'"[^"]+"\s+[A-Z]', text):
        if re.search(r'vol\.', text, re.IGNORECASE):
            return "MLA"
        return "Chicago"
    # Frontiers: Surname I, ... and Surname I (year) Title. Journal vol:article_no. doi: ...
    if re.search(r'\(\d{4}\)\s+[A-Z]', text) and re.search(r'\d+:\d+\.\s+doi:', text, re.IGNORECASE):
        return "Frontiers"
    # ACS: noktalı virgülle ayrılmış yazarlar + "Journal Year, Vol, Pages." kalıbı
    if re.search(r';\s*[A-Z]', text) and re.search(r'\d{4},\s*\d+,\s*[\d–—\-]+\.?\s*$', text.strip()):
        return "ACS"
    # ACS: noktalı virgülle ayrılmış yazarlar + "Journal Year, Vol (issue), pages" kalıbı
    if re.search(r';\s*[A-Z]', text) and re.search(r'\d{4},\s*\d+\s*\(\d+\)', text):
        return "ACS"
    # ACS: vol (issue) article_no, (year) — yıl en sonda parantezde, issue parantezli
    if re.search(r'\d+\s+\(\d+\)\s+\w+,', text) and re.search(r'\(\d{4}\)\s*\.?\s*$', text.strip()):
        return "ACS"
    # Taylor & Francis: Authors (year) Title, Journal, vol:issue, pages
    if re.search(r'\(\d{4}\)\s+\w', text) and re.search(r',\s*\d+:\d+,', text):
        return "Taylor & Francis"
    # Nature/Springer: digits, comma, token, space, (year)  — e.g. "25, 123 (2025)"
    if re.search(r'\d+,\s*\S+\s+\(\d{4}\)', text):
        return "Nature/Springer"
    # APA: authors list then "(year)." at start of sentence
    if re.search(r'\.\s*\(\d{4}\)', text):
        return "APA"
    return None


# ---------------------------------------------------------------------------
# Main parse entry point
# ---------------------------------------------------------------------------

def parse_citation(text: str) -> CitationData:
    text = re.sub(r'[\r\n]+', ' ', text).strip()
    text = re.sub(r' {2,}', ' ', text)
    cd = CitationData(raw=text)

    if len(text) < 20:
        cd.is_valid = False
        return cd

    if re.match(r'@\w+\{', text):
        cd.detected_format = "BibTeX"
        _parse_bibtex(text, cd)
        _validate(cd)
        return cd

    cd.detected_format = _detect_format(text)
    cd.doi, cd.url = _extract_doi(text)

    clean = re.sub(r'https?://doi\.org/\S+', '', text)
    clean = re.sub(r'\bdoi:\s*\S+', '', clean, flags=re.IGNORECASE).strip().rstrip(".")

    for parser in [_try_ieee, _try_frontiers, _try_acs, _try_taylor, _try_nature, _try_apa, _try_chicago, _try_harvard, _try_vancouver, _try_mla]:
        if parser(clean, cd):
            break
    else:
        _generic_parse(clean, cd)

    if not cd.year:
        m = re.search(r'\b(19|20)\d{2}\b', text)
        if m:
            cd.year = m.group(0)

    _validate(cd)
    return cd


# ---------------------------------------------------------------------------
# Style-specific parsers (return True on success)
# ---------------------------------------------------------------------------

def _try_nature(text: str, cd: CitationData) -> bool:
    """
    Nature/Springer: 'Authors. Title. Journal vol, issue (year).'
    Key insight: journal may be abbreviated with dots ('Arch. Civ. Mech. Eng.'),
    so we cannot naively split on '. '. Instead we use the (year) anchor and
    work backwards, then find sentence boundaries by looking for '. ' followed
    by a word with 2+ lowercase chars (not an initial like 'P.').
    """
    year_m = re.search(r'\((\d{4})\)', text)
    if not year_m:
        return False
    year = year_m.group(1)
    before_year = text[:year_m.start()].strip().rstrip(",").strip()

    # Strip 'vol, pages_or_issue' from end
    vi_m = re.search(r'\s+(\d+),\s*(\S+)\s*$', before_year)
    if vi_m:
        volume = vi_m.group(1)
        second = vi_m.group(2).rstrip(".,")
        # Tire veya en-dash içeriyorsa sayfa aralığı, aksi halde sayı/issue
        if re.search(r'[\-–—]', second):
            issue, pages = "", second
        else:
            issue, pages = second, ""
        body = before_year[:vi_m.start()].strip()
    else:
        vi_m2 = re.search(r'\s+(\d+)\s*$', before_year)
        if not vi_m2:
            return False
        volume, issue, pages = vi_m2.group(1), "", ""
        body = before_year[:vi_m2.start()].strip()

    # Find sentence split points: '. ' followed by an uppercase word that has
    # >=3 lowercase letters following (excludes abbreviations like 'Eng. ', 'Civ. ')
    split_points = []
    for m in re.finditer(r'\.\s+(?=[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű]{2,})', body):
        split_points.append(m.start())

    if len(split_points) < 2:
        return False

    # Among all split point pairs, pick the pair where the middle segment (title)
    # is the longest — that's the real title, not a journal abbreviation fragment.
    best = None
    best_len = 0
    for i in range(len(split_points) - 1):
        seg_len = split_points[i + 1] - split_points[i]
        if seg_len > best_len:
            best_len = seg_len
            best = i

    if best is None:
        return False

    second_last = split_points[best]
    last = split_points[best + 1]

    journal = body[last + 1:].strip()
    title = body[second_last + 1:last].strip()
    author_block = body[:second_last].strip()

    if not journal or not title or len(title) < 10:
        return False

    authors = _split_authors_nature(author_block)
    if not authors:
        return False

    cd.authors = authors
    cd.title = title
    cd.journal = journal
    cd.volume = volume
    cd.issue = issue
    cd.pages = pages
    cd.year = year
    return True


def _try_apa(text: str, cd: CitationData) -> bool:
    """APA: 'Authors (year). Title. Journal, vol(issue), pages.'"""
    m = re.match(
        r'^(.+?)\.\s*\((\d{4})\)[,.]?\s+'
        r'(.+?)\.\s+'
        r'([A-Z][^,]+),\s*'
        r'(\d+)'
        r'(?:\(([^\)]+)\))?'
        r'(?:,\s*([^\.\s][^\.]*))?',
        text
    )
    if not m:
        return False
    cd.authors = _split_authors_apa(m.group(1))
    cd.year = m.group(2)
    cd.title = m.group(3).strip()
    cd.journal = m.group(4).strip()
    cd.volume = m.group(5)
    cd.issue = m.group(6) or ""
    cd.pages = (m.group(7) or "").strip()
    return bool(cd.authors and cd.title)


def _try_chicago(text: str, cd: CitationData) -> bool:
    """Chicago: 'Authors. "Title." Journal vol, no. issue (year): pages.'"""
    # Önce tırnaklı başlığı bul
    title_m = re.search(r'"([^"]+)"', text)
    if not title_m:
        return False

    before_title = text[:title_m.start()].strip()
    after_title = text[title_m.end():].strip().lstrip(".,").strip()

    # Yazar bloğu: tırnak öncesi, son nokta + boşluğa kadar
    author_block = re.sub(r'\.\s*$', '', before_title).strip()
    if not author_block:
        return False

    # Dergi adı: sayıdan önce gelen kısım
    # "Journal of Medicine 10, no. 2 (2024): 100" → journal="Journal of Medicine", vol=10
    jv_m = re.match(r'(.+?)\s+(\d+)', after_title)
    if not jv_m:
        return False

    journal = jv_m.group(1).strip()
    rest = after_title[jv_m.start(2):]  # "10, no. 2 (2024): 100-110."

    # no. ile
    m = re.match(
        r'(\d+),?\s*no\.\s*([^\s(]+)\s*\((\d{4})\)'
        r'(?::\s*([\d\-–—]+))?',
        rest, re.IGNORECASE
    )
    if m:
        cd.authors = _split_authors_nature(author_block)
        cd.title = title_m.group(1).strip().rstrip(".")
        cd.journal = journal
        cd.volume = m.group(1)
        cd.issue = m.group(2)
        cd.year = m.group(3)
        cd.pages = (m.group(4) or "").strip()
        return bool(cd.authors and cd.title)

    # no. olmadan
    m2 = re.match(
        r'(\d+)\s*\((\d{4})\)'
        r'(?::\s*([\d\-–—]+))?',
        rest, re.IGNORECASE
    )
    if m2:
        cd.authors = _split_authors_nature(author_block)
        cd.title = title_m.group(1).strip().rstrip(".")
        cd.journal = journal
        cd.volume = m2.group(1)
        cd.year = m2.group(2)
        cd.pages = (m2.group(3) or "").strip()
        return bool(cd.authors and cd.title)

    return False


def _try_harvard(text: str, cd: CitationData) -> bool:
    """Harvard: 'Authors, year. Title. Journal, vol(issue). Available at: url'"""
    m = re.match(
        r'^(.+?),\s*(\d{4})\.\s+'
        r'(.+?)\.\s+'
        r'([A-Z][^,]+),\s*(\d+)'
        r'(?:\(([^\)]+)\))?'
        r'(?:,?\s*(?:pp\.\s*)?([^\.\s][^\.]*))?',
        text
    )
    if not m:
        return False
    cd.authors = _split_authors_nature(m.group(1))
    cd.year = m.group(2)
    cd.title = m.group(3).strip()
    cd.journal = m.group(4).strip()
    cd.volume = m.group(5)
    cd.issue = m.group(6) or ""
    cd.pages = (m.group(7) or "").strip()
    return bool(cd.authors and cd.title)


def _try_vancouver(text: str, cd: CitationData) -> bool:
    """Vancouver: 'Authors. Title. Journal. year;vol(issue):pages.'"""
    m = re.match(
        r'^(.+?)\.\s+'
        r'(.+?)\.\s+'
        r'([A-Z][^.]+)\.\s+'
        r'(\d{4});\s*(\d+)'
        r'(?:\(([^\)]+)\))?'
        r'(?::([^\s\.]+))?',
        text
    )
    if not m:
        return False
    cd.authors = _split_authors_nature(m.group(1))
    cd.title = m.group(2).strip()
    cd.journal = m.group(3).strip()
    cd.year = m.group(4)
    cd.volume = m.group(5)
    cd.issue = m.group(6) or ""
    cd.pages = m.group(7) or ""
    return bool(cd.authors and cd.title)


def _try_taylor(text: str, cd: CitationData) -> bool:
    """
    Taylor & Francis: 'Authors (year) Title, Journal, vol:issue, pages, DOI: ...'
    Örnek: Han Li, Jin Sun & J. Michael Herrmann (2024) Beyond jamming..., Advanced Robotics, 38:11, 715-729
    """
    m = re.match(
        r'^(.+?)\s*\((\d{4})\)\s+'       # yazarlar (yıl)
        r'(.+?),\s*'                       # başlık,
        r'([^,]+),\s*'                     # dergi,
        r'(\d+):(\d+),\s*'                # cilt:sayı,
        r'([\d–—\-]+)',                    # sayfalar (tire, en-dash, em-dash)
        text
    )
    if not m:
        return False

    author_raw = m.group(1).strip()
    # & ile ayrılmış yazarları böl
    author_raw = re.sub(r'\s*&\s*', ', ', author_raw)
    cd.authors = [a.strip() for a in re.split(r',\s*(?=[A-Z])', author_raw) if a.strip()]
    cd.year = m.group(2)
    cd.title = m.group(3).strip()
    cd.journal = m.group(4).strip()
    cd.volume = m.group(5)
    cd.issue = m.group(6)
    cd.pages = m.group(7)
    return bool(cd.authors and cd.title)


def _try_ieee(text: str, cd: CitationData) -> bool:
    """
    IEEE: 'I. Surname, I. Surname, and I. Surname, "Title," Journal, vol. X, no. Y, pp. Z, Mon. year.'
    Yazarlar I. SURNAME formatında, başlık çift tırnakta ve virgülle biter.
    """
    # Başlık: "..., " şeklinde virgülle biten tırnak içi metin
    m = re.match(
        r'^(.+?),\s*'                          # yazarlar
        r'"(.+?),"?\s+'                        # "Başlık," veya "Başlık"
        r'(.+?),\s*'                           # dergi adı
        r'vol\.\s*(\d+),\s*'                   # vol. X
        r'no\.\s*([^\s,]+),\s*'               # no. Y
        r'pp\.\s*([\d–—\-]+),?\s*'  # pp. Z (tire, en-dash, em-dash)
        r'(?:\w+\.?\s*)?(\d{4})',             # [Ay] yıl
        text, re.IGNORECASE
    )
    if not m:
        return False

    author_raw = m.group(1).strip()
    cd.authors = _split_authors_ieee(author_raw)
    cd.title = m.group(2).strip().rstrip(",")
    cd.journal = m.group(3).strip()
    cd.volume = m.group(4)
    cd.issue = m.group(5)
    cd.pages = m.group(6)
    cd.year = m.group(7)
    return bool(cd.authors and cd.title)


def _split_authors_ieee(raw: str) -> list[str]:
    """
    IEEE yazarları: 'I. SURNAME, I. SURNAME, and I. SURNAME'
    Çıktı: ['SURNAME, I.', ...] — diğer formatlarla tutarlı olsun.
    """
    raw = re.sub(r'\s+and\s+', ', ', raw, flags=re.IGNORECASE)
    tokens = re.split(r',\s*(?=[A-Z]\.)', raw)
    authors = []
    for t in tokens:
        t = t.strip().rstrip(",")
        # "I. SURNAME" → "SURNAME, I."
        m = re.match(r'^((?:[A-Z]\.\s*)+)\s*(.+)$', t)
        if m:
            initials = m.group(1).strip()
            surname = m.group(2).strip()
            authors.append(f"{surname}, {initials}")
        else:
            authors.append(t)
    return authors


def _try_frontiers(text: str, cd: CitationData) -> bool:
    """
    Frontiers: 'Surname I, Surname I and Surname I (year) Title. Journal vol:article_no. doi: ...'
    Örnek: Santos AP, Srivastava I, Silbert LE, Lechman JB and Grest GS (2024) Protocol-dependent...
           Front. Soft Matter 3:1326756. doi: 10.3389/frsfm.2023.1326756
    Strateji: (year) ile başlığı böl, ardından sondan "vol:article. doi:" kısmını bul.
    """
    # Yazarlar (yıl) — yıl parantezde, başından bul
    year_m = re.match(r'^(.+?)\s+\((\d{4})\)\s+', text)
    if not year_m:
        return False

    author_raw = year_m.group(1).strip()
    year = year_m.group(2)
    after_year = text[year_m.end():]  # "Title. Journal vol:article_no. doi: ..."

    # Sondan: "vol:article_no. doi: ..." veya "vol:article_no."
    # vol:article_no — sayısal cilt, iki nokta, alfanümerik makale no
    vi_m = re.search(r'\s+(\d+):([\w\d]+)\.?\s*(?:doi:\s*(\S+))?$', after_year, re.IGNORECASE)
    if not vi_m:
        return False

    volume = vi_m.group(1)
    article_no = vi_m.group(2)
    doi_raw = (vi_m.group(3) or "").rstrip(".),")
    body = after_year[:vi_m.start()].strip()  # "Title. Journal"

    # body: "Title. Journal" — dergi noktalı kısaltma içerebilir (Front. Soft Matter)
    # Kural: küçük harften sonra '. ' + büyük harf → cümle sınırı adayı
    # En uzun başlığı veren bölmeyi seç (Nature parser mantığı)
    split_points = [m.start() for m in re.finditer(r'(?<=[a-z])\.\s+(?=[A-Z])', body)]
    if not split_points:
        return False

    best_split = max(split_points, key=lambda p: p)  # en sağdaki değil, en uzun başlığı veren
    # En uzun başlık = en soldaki bölme noktası (tek bölme varsa o, birden fazlaysa ilki)
    best_split = split_points[0]
    title = body[:best_split].strip()
    journal = body[best_split + 1:].strip()

    if not title or not journal or len(title) < 10:
        return False

    # Yazar ayrıştırma: "and" → virgül, sonra büyük harfe göre böl
    author_raw = re.sub(r'\s+and\s+', ', ', author_raw, flags=re.IGNORECASE)
    authors = [a.strip() for a in re.split(r',\s*(?=[A-Z])', author_raw) if a.strip()]
    if not authors:
        return False

    cd.authors = authors
    cd.year = year
    cd.title = title
    cd.journal = journal
    cd.volume = volume
    cd.pages = article_no
    if doi_raw:
        cd.doi = doi_raw
        if not cd.url:
            cd.url = f"https://doi.org/{doi_raw}"
    return bool(cd.authors and cd.title)


def _try_acs(text: str, cd: CitationData) -> bool:
    """
    ACS iki alt format destekler:
    1. 'Authors. Title. Journal Year, Vol, Pages.'  (noktalı, yıl düz)
       Örnek: Van Niekerk, T.I.; Hua, T.; Hattingh, D.G. A Neuro-Fuzzy... IFAC Proc. Vol. 2006, 39, 113-118.
    2. 'Authors, Title, Journal vol (issue) article_no, (year).'  (virgüllü, yıl parantezde)
       Örnek: S. Poincloux, & K.A. Takeuchi, Rigidity transition..., Proc. Natl. Acad. Sci. U.S.A. 121 (49) e2408706121, (2024).
    """
    # Alt format 1: noktalı virgülle ayrılmış yazarlar, yıl düz sayı olarak
    # Tanıma: noktalı virgül içeriyor VE sonda "Year, Vol, Pages." kalıbı var
    if ";" in text:
        m = re.match(
            r'^(.+?)\.\s+'           # yazarlar (noktalı virgülle ayrılmış)
            r'(.+?)\.\s+'            # başlık
            r'(.+?)\s+'              # dergi
            r'(\d{4}),\s*'           # yıl,
            r'(\d+),\s*'             # cilt,
            r'([\d–—\-]+)\.?',       # sayfalar
            text
        )
        if m:
            raw_authors = m.group(1)
            authors = [a.strip() for a in re.split(r';\s*', raw_authors) if a.strip()]
            if authors:
                cd.authors = authors
                cd.title = m.group(2).strip()
                cd.journal = re.sub(r'\s*[Vv]ol\.?\s*$', '', m.group(3).strip()).strip()
                cd.year = m.group(4)
                cd.volume = m.group(5)
                cd.pages = m.group(6)
                return True

    # Alt format 2: yıl en sonda parantezde: (2024) veya (2024).
    year_m = re.search(r'\((\d{4})\)\s*\.?\s*$', text.strip())
    if not year_m:
        return False
    year = year_m.group(1)
    before_year = text[:year_m.start()].strip().rstrip(",").strip()

    # "Journal vol (issue) article_no" — vol (issue) article_no sondan bul
    vi_m = re.search(r',?\s*(\d+)\s+\((\d+)\)\s+(\S+)\s*$', before_year)
    if not vi_m:
        return False
    volume = vi_m.group(1)
    issue = vi_m.group(2)
    article_no = vi_m.group(3).rstrip(",")
    body = before_year[:vi_m.start()].strip().rstrip(",").strip()
    # body: "Authors, Title, Journal"

    # Yazarlar küçük harf kelime içermeyen, birden fazla virgülle ayrılan başlangıç kısmı.
    # Başlık: küçük harf içeren ilk uzun virgül parçası.
    # Journal: başlık sonrası kalan.
    # Yöntem: virgül split, başlık için küçük harf kriterini kullan.
    segments = [s.strip() for s in re.split(r',\s*(?=\S)', body) if s.strip()]
    if len(segments) < 3:
        return False

    title_idx = None
    for i, seg in enumerate(segments):
        if re.search(r'\b[a-z]{3,}\b', seg):
            title_idx = i
            break

    if title_idx is None or title_idx == 0:
        return False

    author_block = ", ".join(segments[:title_idx])
    title = segments[title_idx]
    journal = ", ".join(segments[title_idx + 1:])
    if not journal:
        return False

    # Yazar ayrıştırma: & ve virgülle
    author_raw = re.sub(r'\s*&\s*', ', ', author_block)
    authors = [a.strip().rstrip(",") for a in re.split(r',\s*(?=[A-Z])', author_raw) if a.strip()]
    if not authors:
        return False

    cd.authors = authors
    cd.title = title
    cd.journal = journal
    cd.volume = volume
    cd.issue = issue
    cd.pages = article_no  # ACS uses article number, not page range
    cd.year = year
    return bool(cd.authors and cd.title)


def _try_mla(text: str, cd: CitationData) -> bool:
    """MLA: 'Authors. "Title." Journal, vol. X, no. Y, year, pp. pages.'"""
    m = re.match(
        r'^(.+?)\.\s+"(.+?)"\s+'
        r'([A-Z][^,]+),\s*vol\.\s*(\d+),\s*no\.\s*([^\s,]+),\s*(\d{4})'
        r'(?:,\s*pp\.\s*([^\.\s][^\.]*))?',
        text, re.IGNORECASE
    )
    if not m:
        return False
    cd.authors = _split_authors_nature(m.group(1))
    cd.title = m.group(2).strip()
    cd.journal = m.group(3).strip()
    cd.volume = m.group(4)
    cd.issue = m.group(5)
    cd.year = m.group(6)
    cd.pages = (m.group(7) or "").strip()
    return bool(cd.authors and cd.title)


# ---------------------------------------------------------------------------
# BibTeX parser
# ---------------------------------------------------------------------------

def _parse_bibtex(text: str, cd: CitationData):
    def get_field(name):
        m = re.search(
            rf'{name}\s*=\s*[{{"](.+?)[}}"][\s,}}]',
            text, re.IGNORECASE | re.DOTALL
        )
        return m.group(1).strip() if m else ""

    author_raw = get_field("author")
    if author_raw:
        cd.authors = [a.strip() for a in re.split(r'\s+and\s+', author_raw, flags=re.IGNORECASE)]
    cd.title = get_field("title")
    cd.journal = get_field("journal") or get_field("booktitle")
    cd.volume = get_field("volume")
    cd.issue = get_field("number")
    cd.pages = get_field("pages")
    cd.year = get_field("year")
    cd.doi = get_field("doi")
    if cd.doi and not cd.url:
        cd.url = f"https://doi.org/{cd.doi}"


# ---------------------------------------------------------------------------
# Generic fallback
# ---------------------------------------------------------------------------

def _generic_parse(text: str, cd: CitationData):
    year_m = re.search(r'\b(19|20)\d{2}\b', text)
    if year_m:
        cd.year = year_m.group(0)

    title_m = re.search(r'"([^"]{10,})"', text)
    if title_m:
        cd.title = title_m.group(1).strip()

    sentences = re.split(r'(?<=[a-z])\.\s+(?=[A-Z])', text)
    if sentences:
        authors = _split_authors_nature(sentences[0].rstrip("."))
        if authors and len(authors[0]) < 60:
            cd.authors = authors
        if not cd.title and len(sentences) > 1:
            cd.title = sentences[1].strip().rstrip(".")

    j_m = re.search(r'(?<!\w)([A-Z][a-z]+\.(?:\s+[A-Z][a-z]*\.?){1,3})', text)
    if j_m:
        cd.journal = j_m.group(1).strip()

    vol_m = re.search(r'vol(?:ume)?\.?\s*(\d+)', text, re.IGNORECASE)
    if vol_m:
        cd.volume = vol_m.group(1)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(cd: CitationData):
    cd.missing_fields = []
    if not cd.authors:
        cd.missing_fields.append("authors")
    if not cd.title:
        cd.missing_fields.append("title")
    if not cd.journal:
        cd.missing_fields.append("journal")
    if not cd.year:
        cd.missing_fields.append("year")
    if not cd.volume:
        cd.missing_fields.append("volume")
    cd.is_valid = bool((cd.title and cd.year) or cd.doi)
