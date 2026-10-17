#!/usr/bin/env python3
"""ws_info.py ID [ID ...] — ficha verificada de items del Steam Workshop de Arma 3, en JSON.

Combina la API pública (GetPublishedFileDetails, sin key) con la página del item
(Required items, panel Required DLC, grupos de tags como DLC/Terrain, valoración, descripción).
Espera entre páginas para no disparar el límite de Steam.
"""
import datetime
import html as htmllib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
KEYWORDS = ["dll", "extension", "callextension", "intercept", "ace", "rhs", "cba", "incompatib",
            "not compatible", "conflict", "requires", "required", "dependenc", "dlc", "apex", "contact",
            "deprecated", "discontinued", "no longer", "abandon", "outdated", "mac", "linux", "battleye"]


def fetch(url, data=None, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                time.sleep(10 * 2 ** i)
                continue
            raise
        except urllib.error.URLError:
            if i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise


def iso(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%d") if ts else ""


def api(ids):
    form = {"itemcount": len(ids)}
    for i, x in enumerate(ids):
        form[f"publishedfileids[{i}]"] = x
    body = urllib.parse.urlencode(form).encode()
    j = json.loads(fetch("https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/", body))
    return {d["publishedfileid"]: d for d in j["response"]["publishedfiledetails"]}


def text(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment)
    t = re.sub(r"</(div|li|p|h\d)>", "\n", t)
    t = htmllib.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def page(item_id):
    s = fetch(f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}")
    out = {}
    req = []
    m = re.search(r'id="RequiredItems">(.*?)</div>\s*</div>', s, re.S)
    if m:
        for rid, name in re.findall(r'<a href="[^"]*?id=(\d+)"[^>]*>\s*<div class="requiredItem">\s*(.*?)\s*</div>',
                                    m.group(1), re.S):
            req.append({"id": rid, "title": text(name)})
    out["required_items"] = req
    # Panel "Required DLC" (distinto de los tags "DLC:"); vacío si el item no declara DLC obligatorios.
    out["required_dlc"] = [{"appid": a, "name": text(n)} for a, n in re.findall(
        r'class="requiredDLCName"><a href="[^"]*?/app/(\d+)[^"]*">(.*?)</a>', s, re.S)]
    groups = {}
    for title, body in re.findall(r'class="workshopTags"><span class="workshopTagsTitle">(.*?)(?:&nbsp;)?</span>(.*?)</div>',
                                  s, re.S):
        groups[text(title).rstrip(":")] = [text(x) for x in re.findall(r"<a[^>]*>(.*?)</a>", body)]
    out["tag_groups"] = groups
    star = re.search(r"/(\d)-star_large\.png", s)
    out["rating_stars"] = int(star.group(1)) if star else None
    nr = re.search(r'class="numRatings">([\d,]+) ratings', s)
    out["num_ratings"] = int(nr.group(1).replace(",", "")) if nr else None
    d = s.find('id="highlightContent"')
    desc = ""
    if d > 0:
        desc = text(s[s.find(">", d) + 1:d + 40000])
        cut = desc.find("Share to your Steam activity feed")
        desc = desc[:cut] if cut > 0 else desc
    out["description"] = desc[:4000]
    low = desc.lower()
    hits = {}
    for k in KEYWORDS:
        snippets = []
        for mm in re.finditer(re.escape(k), low):
            if len(snippets) >= 3:
                break
            snippets.append(desc[max(0, mm.start() - 70):mm.end() + 70].replace("\n", " "))
        if snippets:
            hits[k] = snippets
    out["keyword_hits"] = hits
    return out


def main(ids):
    meta = api(ids)
    res = []
    for n, i in enumerate(ids):
        m = meta.get(i, {})
        row = {
            "id": i, "url": f"https://steamcommunity.com/sharedfiles/filedetails/?id={i}",
            "api_result": m.get("result"), "title": m.get("title"),
            "created": iso(m.get("time_created")), "updated": iso(m.get("time_updated")),
            "size_MB": round(int(m.get("file_size") or 0) / 1e6, 1),
            "subscriptions": m.get("subscriptions"), "lifetime_subscriptions": m.get("lifetime_subscriptions"),
            "favorited": m.get("favorited"), "views": m.get("views"), "banned": m.get("banned"),
            "api_tags": [t.get("tag") for t in m.get("tags", [])],
        }
        try:
            row.update(page(i))
        except Exception as e:  # la ficha de la API sigue siendo útil
            row["page_error"] = repr(e)
        res.append(row)
        if n < len(ids) - 1:
            time.sleep(2.5)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
