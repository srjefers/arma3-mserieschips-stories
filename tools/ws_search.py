#!/usr/bin/env python3
"""ws_search.py — busca en el Steam Workshop de Arma 3 (app 107410).

La página de búsqueda del Workshop se renderiza en el navegador, pero trae los resultados
precargados en un JSON (<script id="valve-ssr-data">); este script lee ese JSON.

Uso:
  ws_search.py [--q TEXTO] [--sort textsearch|trend|mostrecent|lastupdated|totaluniquesubscribers|toprated]
               [--days N] [--tags Scenario,Singleplayer] [--pages N] [--json]
Ejemplos:
  ws_search.py --q "BECTI"
  ws_search.py --sort trend --days -1 --tags Scenario,Singleplayer --pages 2
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def fetch(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                time.sleep(10 * 2 ** i)  # Steam limita: esperar y reintentar despacio
                continue
            raise
        except urllib.error.URLError:
            if i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise


def browse(q, sort, days, tags, page):
    params = [("appid", "107410"), ("browsesort", sort), ("section", "readytouseitems"), ("p", str(page))]
    if q:
        params.append(("searchtext", q))
    if days is not None:
        params.append(("days", str(days)))
    for t in tags:
        params.append(("requiredtags[]", t))
    url = "https://steamcommunity.com/workshop/browse/?" + urllib.parse.urlencode(params)
    html = fetch(url)
    m = re.search(r'<script[^>]*id="valve-ssr-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("la página no trae valve-ssr-data (¿cambió el formato?)")
    data = json.loads(m.group(1))
    queries = json.loads(data["renderContext"]["queryData"])["queries"]
    wb = next(q["state"]["data"] for q in queries if q["queryKey"][0] == "workshop_browse")
    return url, wb


def iso(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%d") if ts else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", default="")
    ap.add_argument("--sort", default="textsearch")
    ap.add_argument("--days", type=int)
    ap.add_argument("--tags", default="")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tags = [t for t in a.tags.split(",") if t]
    rows = []
    for p in range(1, a.pages + 1):
        url, wb = browse(a.q, a.sort, a.days, tags, p)
        print(f"# página {p}/{wb.get('total_pages')} ({wb.get('total_count')} resultados): {url}", file=sys.stderr)
        for r in wb.get("results", []):
            rows.append({
                "id": r["publishedfileid"], "title": r["title"],
                "url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={r['publishedfileid']}",
                "updated": iso(r.get("time_updated")), "created": iso(r.get("time_created")),
                "subscriptions": r.get("subscriptions"), "lifetime_subscriptions": r.get("lifetime_subscriptions"),
                "star_rating": r.get("star_rating"), "total_votes": r.get("total_votes"),
                "size_MB": round(int(r.get("file_size") or 0) / 1e6, 1),
                "tags": [t["tag"] for t in r.get("tags", [])],
                "required_ids": [c["publishedfileid"] for c in r.get("children", [])],
            })
        if p < a.pages:
            time.sleep(3)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            print(f"{r['id']} | {r['title']} | upd {r['updated']} | subs {r['subscriptions']} | "
                  f"★{r['star_rating']} ({r['total_votes']}) | {r['size_MB']} MB | req {r['required_ids']} | {','.join(r['tags'])}")


if __name__ == "__main__":
    main()
