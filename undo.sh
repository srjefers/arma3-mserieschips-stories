#!/bin/bash
# undo.sh — revierte lo instalado según install_manifest.tsv, en orden inverso.
# No toca el juego, ni Steam, ni el contenido del Workshop (solo borra symlinks, nunca a dónde apuntan).
# Uso: ./undo.sh --dry-run   (muestra qué haría, sin borrar nada)
#      ./undo.sh             (revierte)
set -u
ARMA_PROJECT="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="$ARMA_PROJECT/install_manifest.tsv"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1
if [ "$DRY" = 1 ]; then V="se eliminaría"; echo "(simulación: no se borra nada)"; else V="eliminado"; fi

if [ ! -s "$MANIFEST" ]; then
  echo "Nada que revertir: no existe $MANIFEST"
  exit 0
fi

# Misma huella que tools/track.sh (copiada aquí para que undo.sh funcione solo).
tree_hash() {
  python3 - "$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]
h = hashlib.sha256()
for dp, dn, fn in os.walk(root):
    dn.sort()
    for f in sorted(fn):
        if f == ".DS_Store":
            continue
        p = os.path.join(dp, f)
        h.update(os.path.relpath(p, root).encode() + b"\0")
        with open(p, "rb") as fh:
            h.update(hashlib.sha256(fh.read()).digest())
print(h.hexdigest())
PY
}

tail -r "$MANIFEST" | while IFS=$'\t' read -r type path extra; do
  case "$type" in
    tree)
      if [ -d "$path" ] && [ ! -L "$path" ]; then
        if [ "$(tree_hash "$path")" = "$extra" ]; then
          [ "$DRY" = 1 ] || rm -r "$path"
          echo "carpeta de misión $V: $path"
        else
          echo "OMITIDO (su contenido cambió, revísalo a mano): $path"
        fi
      else echo "ya no existe: $path"; fi ;;
    symlink)
      if [ -L "$path" ]; then
        [ "$DRY" = 1 ] || rm "$path"
        echo "symlink $V: $path"
      else echo "omitido (ya no es un symlink): $path"; fi ;;
    file)
      if [ -f "$path" ]; then
        if [ "$(shasum -a 256 "$path" | cut -d' ' -f1)" = "$extra" ]; then
          [ "$DRY" = 1 ] || rm "$path"
          echo "archivo $V: $path"
        else
          echo "OMITIDO (cambió desde que se instaló, revísalo a mano): $path"
        fi
      else echo "ya no existe: $path"; fi ;;
    dir)
      if [ "$DRY" = 1 ]; then
        echo "carpeta (se elimina solo si queda vacía): $path"
      elif [ -d "$path" ] && [ -z "$(ls -A "$path" | grep -v '^\.DS_Store$')" ]; then
        rm -f "$path/.DS_Store"; rmdir "$path"; echo "carpeta eliminada: $path"
      else echo "carpeta conservada (no está vacía o no existe): $path"; fi ;;
  esac
done

if [ "$DRY" = 0 ]; then
  mv "$MANIFEST" "$MANIFEST.reverted-$(date +%Y%m%d-%H%M%S)"
  echo "Listo. Manifiesto archivado."
fi
echo "Pendiente manual: borrar las Launch Options de Arma 3 en Steam y, si quieres, desuscribirte de CUP en el Workshop."
