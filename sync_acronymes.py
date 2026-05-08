#!/usr/bin/env python3
"""
Synchronise la feuille « Liste combinée » publiée en CSV vers acronymes.html.

S'exécute dans GitHub Actions (voir .github/workflows/sync.yml).
Lit l'URL CSV via la variable d'environnement CSV_URL et régénère le
fichier acronymes.html à la racine du dépôt.

Aucune dépendance externe (utilise uniquement la bibliothèque standard).
"""

import csv
import html
import io
import os
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CSV_URL = os.environ.get("CSV_URL", "").strip()
HTML_PATH = Path(__file__).resolve().parent.parent / "acronymes.html"

MOIS_FR = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


# ---------------------------------------------------------------------------
# Gabarit HTML — voir SETUP.md pour la procédure complète
# ---------------------------------------------------------------------------
TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1480">
<title>Glossaire des acronymes, DRSP</title>
<style>
  :root {
    --ink: #1a1a1a;
    --muted: #5a5a5a;
    --hairline: #e5e5e5;
    --accent: #3b6fa8;
    --tag-bg: #f1f1f1;
    --tag-ink: #5a5a5a;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: var(--ink);
    background: #ffffff;
    font-size: 12pt;
    line-height: 1.45;
    -webkit-font-smoothing: antialiased;
  }
  nav.toc {
    position: sticky; top: 0;
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--hairline);
    padding: 14px 48px;
    font-size: 10pt;
    z-index: 10;
    display: flex; gap: 24px; align-items: center;
  }
  nav.toc a { color: var(--muted); text-decoration: none; }
  nav.toc a:hover { color: var(--accent); }
  nav.toc .brand { font-weight: 500; color: var(--ink); margin-right: auto; }

  main { max-width: 1100px; margin: 0 auto; padding: 0 48px; }

  .hero {
    padding: 96px 0 56px;
    border-bottom: 1px solid var(--hairline);
  }
  .hero .label {
    font-size: 10pt; color: var(--muted);
    letter-spacing: 0.06em; margin-bottom: 24px;
  }
  .hero h1 {
    font-size: 48pt; font-weight: 400;
    line-height: 1.05; letter-spacing: -0.02em;
    margin: 0 0 24px;
  }
  .hero p.lead {
    font-size: 13pt; color: var(--muted);
    max-width: 720px; margin: 0;
    line-height: 1.55;
  }

  .controls {
    display: flex; gap: 16px; align-items: center;
    padding: 24px 0 8px;
    border-bottom: 1px solid var(--hairline);
    margin-bottom: 32px;
    position: sticky; top: 50px;
    background: #fff; z-index: 5;
  }
  .controls input {
    flex: 1; max-width: 360px;
    padding: 10px 14px;
    border: 1px solid var(--hairline);
    border-radius: 6px;
    font-size: 11pt;
    font-family: inherit;
    color: var(--ink);
    outline: none;
  }
  .controls input:focus { border-color: var(--accent); }
  .controls .count {
    font-size: 10pt; color: var(--muted);
  }
  .alpha-index {
    display: flex; flex-wrap: wrap; gap: 4px;
    padding: 16px 0;
    border-bottom: 1px solid var(--hairline);
    margin-bottom: 32px;
    font-size: 10pt;
  }
  .alpha-index a {
    display: inline-block;
    min-width: 28px;
    text-align: center;
    padding: 4px 8px;
    color: var(--muted);
    text-decoration: none;
    border-radius: 4px;
  }
  .alpha-index a:hover {
    color: var(--accent);
    background: #f4f4f4;
  }

  .letter-block { margin-bottom: 40px; scroll-margin-top: 120px; }
  .letter-block h3.letter {
    font-size: 24pt; font-weight: 400;
    color: var(--accent);
    margin: 0 0 16px;
    letter-spacing: -0.02em;
    border-bottom: 1px solid var(--hairline);
    padding-bottom: 8px;
  }
  .letter-block dl { margin: 0; }
  .entry {
    display: grid;
    grid-template-columns: 180px 1fr;
    gap: 16px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
  }
  .entry dt {
    font-weight: 500;
    font-size: 10.5pt;
    color: var(--ink);
  }
  .entry dd {
    margin: 0;
    font-size: 10.5pt;
    color: var(--ink);
    line-height: 1.5;
  }
  .entry .src {
    display: inline-block;
    margin-left: 8px;
    padding: 1px 8px;
    background: var(--tag-bg);
    color: var(--tag-ink);
    font-size: 8.5pt;
    border-radius: 3px;
    font-weight: 400;
    vertical-align: 2px;
    white-space: nowrap;
  }
  .entry.hidden { display: none; }

  footer {
    border-top: 1px solid var(--hairline);
    padding: 32px 48px 64px;
    color: var(--muted);
    font-size: 10pt;
    max-width: 1100px;
    margin: 56px auto 0;
  }
</style>
</head>
<body>

<nav class="toc">
  <span class="brand">Ressources EUSP</span>
  <a href="index.html">Structure organisationnelle</a>
  <a href="concertations.html">Concertations et partenariats</a>
  <a href="acronymes.html">Glossaire</a>
</nav>

<main>

  <section class="hero">
    <div class="label">DRSP</div>
    <h1>Glossaire des acronymes</h1>
    <p class="lead">Liste combinée des sigles et acronymes utilisés à la DRSP, dans le PNSP et dans le PARI-SP.</p>
  </section>

  <div class="controls">
    <input id="q" type="search" placeholder="Rechercher un acronyme ou une signification…" autocomplete="off">
    <span class="count" id="count">{{COUNT}} entrées</span>
  </div>

  <div class="alpha-index">
{{ALPHA_INDEX}}
  </div>

{{LETTER_BLOCKS}}
</main>

<footer>
  Direction régionale de santé publique, CIUSSS du Centre-Sud-de-l'Île-de-Montréal. {{FOOTER_DATE}}.
</footer>

<script>
(function(){
  const q = document.getElementById('q');
  const countEl = document.getElementById('count');
  const entries = Array.from(document.querySelectorAll('.entry'));
  const blocks = Array.from(document.querySelectorAll('.letter-block'));
  const total = entries.length;
  function norm(s){ return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,''); }
  q.addEventListener('input', () => {
    const term = norm(q.value.trim());
    let visible = 0;
    entries.forEach(e => {
      if (!term) { e.classList.remove('hidden'); visible++; return; }
      const text = norm(e.textContent);
      if (text.includes(term)) { e.classList.remove('hidden'); visible++; }
      else e.classList.add('hidden');
    });
    blocks.forEach(b => {
      const anyVisible = b.querySelectorAll('.entry:not(.hidden)').length > 0;
      b.style.display = anyVisible ? '' : 'none';
    });
    countEl.textContent = visible + (visible === 1 ? ' entrée' : ' entrées') + (term ? ' (filtré)' : '');
  });
})();
</script>

</body>
</html>
"""


def base_letter(s: str) -> str:
    """Première lettre normalisée (sans accent), en majuscule."""
    if not s:
        return "#"
    first = s.strip()[:1]
    nfkd = unicodedata.normalize("NFKD", first)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.upper() if stripped.isalpha() else "#"


def fetch_csv_rows(url: str):
    """Télécharge le CSV publié et retourne la liste des rangées."""
    if not url:
        sys.exit(
            "Erreur : la variable d'environnement CSV_URL n'est pas définie. "
            "Voir SETUP.md pour la configuration."
        )
    print(f"[info] Téléchargement du CSV depuis : {url}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "DRSP-Acronymes-Sync/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(data))
    return list(reader)


def parse_entries(rows):
    """Saute l'en-tête, normalise les rangées en (acronyme, signification, source)."""
    entries = []
    for i, row in enumerate(rows):
        if i == 0:
            continue  # en-tête
        if not row or not row[0]:
            continue
        acronyme = row[0].strip()
        signification = row[1].strip() if len(row) > 1 else ""
        source = row[2].strip() if len(row) > 2 else ""
        if not acronyme:
            continue
        entries.append((acronyme, signification, source))
    return entries


def render_entry(acronyme: str, signification: str, source: str) -> str:
    a = html.escape(acronyme, quote=True)
    s = html.escape(signification, quote=True)
    return f'    <div class="entry"><dt>{a}</dt><dd>{s}</dd></div>'


def build_letter_blocks(entries):
    groups = {}
    order = []
    for entry in entries:
        letter = base_letter(entry[0])
        if letter not in groups:
            groups[letter] = []
            order.append(letter)
        groups[letter].append(entry)

    order.sort(key=lambda l: (l == "#", l))

    blocks_html = []
    for letter in order:
        rows = "\n".join(render_entry(*e) for e in groups[letter])
        block = (
            f'<section class="letter-block" id="lt-{letter}">\n'
            f'  <h3 class="letter">{letter}</h3>\n'
            f'  <dl>\n'
            f'{rows}\n'
            f'  </dl>\n'
            f'</section>'
        )
        blocks_html.append(block)

    alpha_links = " ".join(f'<a href="#lt-{l}">{l}</a>' for l in order)
    return alpha_links, "\n".join(blocks_html), len(entries)


def french_month_year(now=None):
    now = now or datetime.now()
    return f"{MOIS_FR[now.month]} {now.year}"


def main():
    rows = fetch_csv_rows(CSV_URL)
    entries = parse_entries(rows)
    if not entries:
        sys.exit("Erreur : aucune entrée trouvée dans le CSV.")

    alpha_links, letter_blocks, count = build_letter_blocks(entries)

    output = (
        TEMPLATE
        .replace("{{COUNT}}", str(count))
        .replace("{{ALPHA_INDEX}}", alpha_links)
        .replace("{{LETTER_BLOCKS}}", letter_blocks)
        .replace("{{FOOTER_DATE}}", french_month_year())
    )

    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(output, encoding="utf-8")
    print(f"[ok] {count} entrées écrites dans {HTML_PATH}")


if __name__ == "__main__":
    main()
