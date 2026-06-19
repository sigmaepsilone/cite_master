"""Format CitationData into various citation styles."""

import re
from parsers import CitationData


def _title_case(title: str) -> str:
    small = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at",
             "to", "by", "in", "of", "up", "as", "is"}
    words = title.split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in small:
            result.append(w[0].upper() + w[1:] if w else w)
        else:
            result.append(w.lower())
    return " ".join(result)


def _sentence_case(title: str) -> str:
    if not title:
        return title
    return title[0].upper() + title[1:]


def _missing_note(fields: list[str]) -> str:
    if not fields:
        return ""
    return " [Eksik: " + ", ".join(fields) + "]"


def _is_et_al(a: str) -> bool:
    return a.strip().lower() in ("et al.", "et al")


def _ensure_dot(s: str) -> str:
    return s.rstrip(".") + "."


# ── APA 7th ──────────────────────────────────────────────────────────────────
# Journal:     Authors (year). Title. *Journal*, *vol*(issue), pages. DOI
# Conference:  Authors (year). Title. In *Conference* (pp. X–Y). Location. DOI
def format_apa(cd: CitationData) -> str:
    authors = _apa_authors(cd.authors)
    year = f"({cd.year})" if cd.year else "([yıl?])"
    title = _sentence_case(cd.title) if cd.title else "[başlık?]"
    doi_part = f" {cd.url}" if cd.url else (f" https://doi.org/{cd.doi}" if cd.doi else "")
    if cd.conference:
        conf = f"*{cd.conference}*"
        pages = f" (pp. {cd.pages})" if cd.pages else ""
        loc = f" {cd.location}." if cd.location else "."
        out = f"{authors} {year}. {title}. In {conf}{pages}.{loc}{doi_part}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        vol = f"*{cd.volume}*" if cd.volume else ""
        issue = f"({cd.issue})" if cd.issue else ""
        vol_iss = vol + issue if vol else ""
        pages = f", {cd.pages}" if cd.pages else ""
        out = f"{authors} {year}. {title}. {journal}"
        if vol_iss:
            out += f", {vol_iss}"
        out += pages + "." + doi_part
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _abbrev_initials(author: str) -> str:
    author = author.strip().rstrip(".")
    m = re.match(r'^([^,]+),\s*(.+)$', author)
    if not m:
        return _ensure_dot(author)
    surname = m.group(1).strip()
    given = m.group(2).strip()
    if re.match(r'^([A-Z]\.\s*)+$', given):
        return _ensure_dot(f"{surname}, {given.strip()}")
    initials = " ".join(w[0].upper() + "." for w in re.split(r'\s+', given) if w)
    return f"{surname}, {initials}"


def _apa_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    normed = [_abbrev_initials(a) for a in real]
    if has_et_al:
        return ", ".join(normed) + ", et al."
    if len(normed) == 1:
        return normed[0]
    if len(normed) == 2:
        return f"{normed[0]}, & {normed[1]}"
    return ", ".join(normed[:-1]) + ", & " + normed[-1]


# ── ACS ──────────────────────────────────────────────────────────────────────
# Journal:     Surname, I.; ... Title. *Journal* **year**, *vol* (issue), pages. DOI
# Conference:  Surname, I.; ... Title. In: *Conference*; Location, **year**; pp X–Y. DOI
def format_acs(cd: CitationData) -> str:
    authors = _acs_authors(cd.authors)
    title = cd.title or "[başlık?]"
    doi_part = f" {cd.url}" if cd.url else (f" https://doi.org/{cd.doi}" if cd.doi else "")
    if cd.conference:
        conf = f"*{cd.conference}*"
        year = f"**{cd.year}**" if cd.year else "**[yıl?]**"
        loc = f"{cd.location}, " if cd.location else ""
        pages = f"; pp {cd.pages}" if cd.pages else ""
        out = f"{authors} {title}. In: {conf}; {loc}{year}{pages}.{doi_part}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        year = f"**{cd.year}**" if cd.year else "**[yıl?]**"
        vol = f", *{cd.volume}*" if cd.volume else ""
        issue = f" ({cd.issue})" if cd.issue else ""
        pages = f", {cd.pages}" if cd.pages else ""
        out = f"{authors} {title}. {journal} {year}{vol}{issue}{pages}.{doi_part}"
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _acs_author_norm(author: str) -> str:
    author = author.strip().rstrip(".")
    if re.match(r'^[^,]+,\s*[A-Z]\.', author):
        return _ensure_dot(author)
    m = re.match(r'^((?:[A-Z]\.?\s*)+)\s+(.+)$', author)
    if m:
        initials = " ".join(
            (c + ".") if not c.endswith(".") else c
            for c in re.split(r'[\s.]+', m.group(1).strip()) if c
        )
        return f"{m.group(2).strip()}, {initials}"
    return _ensure_dot(author)


def _acs_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    normed = [_acs_author_norm(a) for a in real]
    if has_et_al:
        return "; ".join(normed) + " et al."
    if len(normed) == 1:
        return normed[0]
    return "; ".join(normed)


# ── IEEE ─────────────────────────────────────────────────────────────────────
# Journal:     Authors, "Title," *Journal*, vol. X, no. Y, pp. Z, year. doi: ...
# Conference:  Authors, "Title," *Conference*, City, year, pp. X–Y. doi: ...
def format_ieee(cd: CitationData) -> str:
    authors = _ieee_authors(cd.authors)
    title = f'"{cd.title},"' if cd.title else '"[başlık?],"'
    year = cd.year or "[yıl?]"
    doi_part = f" doi: {cd.doi}" if cd.doi else ""
    if cd.conference:
        conf = f"*{cd.conference}*"
        loc = f", {cd.location}" if cd.location else ""
        pp = f"pp. {cd.pages}" if cd.pages else ""
        if pp:
            out = f"{authors} {title} {conf}{loc}, {year}, {pp}.{doi_part}"
        else:
            out = f"{authors} {title} {conf}{loc}, {year}.{doi_part}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        vol = f"vol. {cd.volume}" if cd.volume else ""
        iss = f"no. {cd.issue}" if cd.issue else ""
        pp = f"pp. {cd.pages}" if cd.pages else ""
        parts = [p for p in [vol, iss, pp, year] if p]
        meta = ", ".join(parts)
        out = f"{authors} {title} {journal}, {meta}.{doi_part}"
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _ieee_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    normed = []
    for a in real:
        m = re.match(r'^([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\-]+(?:\s+[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\-]+)*),\s*(.+)$', a.rstrip("."))
        if m:
            initials = m.group(2).strip().rstrip(".")
            initials = re.sub(r'([A-Z])\.?\s*(?=[A-Z]|$)', r'\1. ', initials).strip()
            normed.append(f"{initials} {m.group(1)}")
        else:
            normed.append(a.rstrip("."))
    suffix = " et al." if has_et_al else ""
    return ", ".join(normed) + suffix + ","


# ── Springer/Nature ───────────────────────────────────────────────────────────
# Journal:     Surname, I. et al. Title. *Journal* **vol**, issue (year). DOI
# Conference:  Surname, I. et al. Title. In: *Conference*. Location; year. pp. X–Y. DOI
def format_springer(cd: CitationData) -> str:
    authors = _springer_authors(cd.authors)
    title = _sentence_case(cd.title) if cd.title else "[başlık?]"
    doi_part = f" {cd.url}" if cd.url else (f" https://doi.org/{cd.doi}" if cd.doi else "")
    if cd.conference:
        conf = f"*{cd.conference}*"
        loc = f" {cd.location};" if cd.location else ";"
        year = cd.year or "[yıl?]"
        pages = f" pp. {cd.pages}." if cd.pages else "."
        out = f"{authors} {title}. In: {conf}.{loc} {year}.{pages}{doi_part}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        vol = f"**{cd.volume}**" if cd.volume else "**[cilt?]**"
        issue = f", {cd.issue}" if cd.issue else ""
        year = f"({cd.year})" if cd.year else "([yıl?])"
        out = f"{authors} {title}. {journal} {vol}{issue} {year}.{doi_part}"
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _springer_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    normed = [_ensure_dot(a) for a in real]
    joined = ", ".join(normed)
    if has_et_al:
        return joined + " et al."
    return joined


# ── Chicago Notes & Bibliography ──────────────────────────────────────────────
# Journal:     Authors. "Title." *Journal* vol, no. issue (year): pages. DOI
# Conference:  Authors. "Title." Paper presented at *Conference*, Location (year), pp. X–Y. DOI
def format_chicago(cd: CitationData) -> str:
    authors = _chicago_authors(cd.authors)
    title = f'"{_title_case(cd.title)}"' if cd.title else '"[başlık?]"'
    doi_part = f" {cd.url}" if cd.url else (f" https://doi.org/{cd.doi}" if cd.doi else "")
    year = f"({cd.year})" if cd.year else "([yıl?])"
    if cd.conference:
        conf = f"*{cd.conference}*"
        loc = f", {cd.location}" if cd.location else ""
        pages = f", pp. {cd.pages}" if cd.pages else ""
        out = f"{authors} {title} Paper presented at {conf}{loc} {year}{pages}.{doi_part}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        vol = cd.volume or "[cilt?]"
        issue_part = f", no. {cd.issue}" if cd.issue else ""
        pages = f": {cd.pages}" if cd.pages else ""
        out = f"{authors} {title} {journal} {vol}{issue_part} {year}{pages}.{doi_part}"
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _chicago_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    parts = [_ensure_dot(a) for a in real]
    joined = ", ".join(parts)
    if has_et_al:
        return joined + " et al."
    return joined


# ── Harvard ───────────────────────────────────────────────────────────────────
# Journal:     Authors, year. Title. *Journal*, vol(issue), pp. pages. Available at: DOI
# Conference:  Authors, year. Title. In: *Conference*, Location, pp. pages. Available at: DOI
def format_harvard(cd: CitationData) -> str:
    authors = _harvard_authors(cd.authors)
    year = cd.year or "[yıl?]"
    title = _sentence_case(cd.title) if cd.title else "[başlık?]"
    avail = f" Available at: {cd.url}" if cd.url else (f" Available at: https://doi.org/{cd.doi}" if cd.doi else "")
    if cd.conference:
        conf = f"*{cd.conference}*"
        pages = f", pp. {cd.pages}" if cd.pages else ""
        loc = f", {cd.location}" if cd.location else ""
        out = f"{authors}, {year}. {title}. In: {conf}{loc}{pages}.{avail}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        vol = cd.volume or ""
        issue = f"({cd.issue})" if cd.issue else ""
        vol_iss = vol + issue if vol else ""
        out = f"{authors}, {year}. {title}. {journal}"
        if vol_iss:
            out += f", {vol_iss}"
        if cd.pages:
            out += f", pp. {cd.pages}"
        out += "." + avail
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _harvard_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    normed = [_ensure_dot(a) for a in real]
    if has_et_al:
        return ", ".join(normed) + " et al."
    if len(normed) == 1:
        return normed[0]
    if len(normed) == 2:
        return f"{normed[0]} and {normed[1]}"
    return ", ".join(normed[:-1]) + " and " + normed[-1]


# ── MLA 9th ───────────────────────────────────────────────────────────────────
# Journal:     Authors. "Title." *Journal*, vol. X, no. Y, year, pp. pages. DOI
# Conference:  Authors. "Title." *Conference*, Location, year, pp. pages. DOI
def format_mla(cd: CitationData) -> str:
    authors = _mla_authors(cd.authors)
    title = f'"{_title_case(cd.title)}"' if cd.title else '"[başlık?]"'
    doi_part = f" {cd.url}" if cd.url else (f" https://doi.org/{cd.doi}" if cd.doi else "")
    year = cd.year or "[yıl?]"
    if cd.conference:
        conf = f"*{cd.conference}*"
        loc = f", {cd.location}" if cd.location else ""
        pages = f", pp. {cd.pages}" if cd.pages else ""
        out = f"{authors} {title} {conf}{loc}, {year}{pages}.{doi_part}"
    else:
        journal = f"*{cd.journal}*" if cd.journal else "*[dergi?]*"
        vol = f"vol. {cd.volume}" if cd.volume else ""
        iss = f"no. {cd.issue}" if cd.issue else ""
        pages = f"pp. {cd.pages}" if cd.pages else ""
        parts = [p for p in [vol, iss, year, pages] if p]
        meta = ", ".join(parts)
        out = f"{authors} {title} {journal}, {meta}.{doi_part}"
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _mla_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    if not real:
        return "et al."
    if has_et_al or len(real) > 3:
        return _ensure_dot(real[0].rstrip(".")) + " et al."
    normed = [_ensure_dot(a.rstrip(".")) for a in real]
    if len(normed) == 1:
        return normed[0]
    if len(normed) == 2:
        return normed[0] + ", and " + normed[1]
    return ", ".join(normed[:-1]) + ", and " + normed[-1]


# ── BibTeX ────────────────────────────────────────────────────────────────────
def format_bibtex(cd: CitationData) -> str:
    def safe(s):
        return s.replace("{", "").replace("}", "")

    first_author = ""
    if cd.authors:
        a = cd.authors[0]
        m = re.match(r'^([A-ZÁÉÍÓÖŐÚÜŰ][A-ZÁÉÍÓÖŐÚÜŰa-záéíóöőúüű\-]+)', a)
        if m:
            first_author = m.group(1).lower()
        else:
            m2 = re.search(r'([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\-]{2,})\s*$', a)
            first_author = m2.group(1).lower() if m2 else "unknown"

    key = f"{first_author}{cd.year}" if (first_author and cd.year) else "cite_key"
    real = [a for a in cd.authors if not _is_et_al(a)]
    has_et_al = len(real) < len(cd.authors)
    bibtex_authors = " and ".join([a.rstrip(".") for a in real])
    if has_et_al:
        bibtex_authors += " and others"

    if cd.conference:
        lines = [f"@inproceedings{{{key},"]
        lines.append(f"  author    = {{{safe(bibtex_authors)}}},")
        lines.append(f"  title     = {{{safe(cd.title or '')}}},")
        lines.append(f"  booktitle = {{{safe(cd.conference)}}},")
        if cd.location:
            lines.append(f"  address   = {{{safe(cd.location)}}},")
    else:
        lines = [f"@article{{{key},"]
        lines.append(f"  author    = {{{safe(bibtex_authors)}}},")
        lines.append(f"  title     = {{{safe(cd.title or '')}}},")
        lines.append(f"  journal   = {{{safe(cd.journal or '')}}},")
        if cd.volume:
            lines.append(f"  volume    = {{{cd.volume}}},")
        if cd.issue:
            lines.append(f"  number    = {{{cd.issue}}},")
    if cd.pages:
        lines.append(f"  pages     = {{{cd.pages}}},")
    if cd.year:
        lines.append(f"  year      = {{{cd.year}}},")
    if cd.doi:
        lines.append(f"  doi       = {{{cd.doi}}},")
    lines.append("}")
    result = "\n".join(lines)
    if cd.missing_fields:
        result += "\n" + _missing_note(cd.missing_fields)
    return result


# ── Vancouver ─────────────────────────────────────────────────────────────────
# Journal:     Authors. Title. *Journal*. year;vol(issue):pages. doi:...
# Conference:  Authors. Title. In: *Conference*; Location: year. p. X–Y. doi:...
def format_vancouver(cd: CitationData) -> str:
    authors = _vancouver_authors(cd.authors)
    title = cd.title or "[başlık?]"
    year = cd.year or "[yıl?]"
    doi_part = f" doi:{cd.doi}" if cd.doi else ""
    if cd.conference:
        conf = f"*{cd.conference}*"
        loc = f" {cd.location}:" if cd.location else ":"
        pages = f" p. {cd.pages}." if cd.pages else "."
        out = f"{authors} {title}. In: {conf};{loc} {year}.{pages}{doi_part}"
    else:
        j = cd.journal or "[dergi?]"
        journal = f"*{j}*"
        vol = cd.volume or ""
        iss = f"({cd.issue})" if cd.issue else ""
        pages = f":{cd.pages}" if cd.pages else ""
        sep = " " if j.endswith(".") else ". "
        out = f"{authors} {title}. {journal}{sep}{year};{vol}{iss}{pages}.{doi_part}"
    out += _missing_note(cd.missing_fields)
    return out.strip()


def _vancouver_authors(authors: list[str]) -> str:
    if not authors:
        return "[yazar?]"
    real = [a.strip() for a in authors if not _is_et_al(a)]
    has_et_al = len(real) < len(authors)
    normed = []
    for a in real:
        a = a.rstrip(".")
        m = re.match(r'^([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\-]+(?:\s+[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\-]+)*),\s*(.+)$', a)
        if m:
            initials = re.sub(r'[\s.]', '', m.group(2))
            normed.append(f"{m.group(1)} {initials}")
        else:
            normed.append(a)
    if has_et_al:
        return ", ".join(normed) + ", et al."
    return ", ".join(normed) + "."


ALL_FORMATS = {
    "APA": format_apa,
    "ACS": format_acs,
    "IEEE": format_ieee,
    "Springer/Nature": format_springer,
    "Chicago": format_chicago,
    "Harvard": format_harvard,
    "MLA": format_mla,
    "BibTeX": format_bibtex,
    "Vancouver": format_vancouver,
}
