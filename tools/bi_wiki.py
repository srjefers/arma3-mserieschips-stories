#!/usr/bin/env python3
"""bi_wiki.py — lee la wiki de Bohemia (community.bistudio.com) vía su API.
La página web directa responde 403 (Cloudflare) a herramientas; la API no.

Uso:
  bi_wiki.py "Arma 3: Play on Mac"          imprime el wikitext de la página
  bi_wiki.py --search "rpt mac"             lista páginas que coinciden
"""
import json
import re
import sys
import urllib.parse
import urllib.request

API = "https://community.bistudio.com/wikidata/api.php"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def call(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def main(argv):
    if len(argv) >= 3 and argv[1] == "--search":
        res = call({"action": "query", "list": "search", "srsearch": " ".join(argv[2:]), "srlimit": 20})
        for hit in res["query"]["search"]:
            print(hit["title"])
        return
    if len(argv) != 2:
        sys.exit(__doc__)
    # Cloudflare responde 403 a "redirects=1" y a títulos con "_": usar espacios y seguir redirecciones a mano.
    title = argv[1].replace("_", " ")
    for _ in range(3):
        res = call({"action": "parse", "page": title, "prop": "wikitext"})
        if "error" in res:
            sys.exit(f"ERROR: {res['error'].get('info')}")
        wikitext = res["parse"]["wikitext"]["*"]
        m = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", wikitext, re.I)
        if not m:
            break
        title = m.group(1).replace("_", " ").strip()
    print(f"# {res['parse']['title']}\n")
    print(wikitext)


if __name__ == "__main__":
    main(sys.argv)
