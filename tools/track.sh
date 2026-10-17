# track.sh — acciones de instalación registradas en install_manifest.tsv (para que undo.sh las revierta).
# Uso: source tools/track.sh (bash o zsh); luego track_mkdir / track_copy / track_symlink / track_unpack / untrack_remove.
# Nunca sobrescribe nada: si el destino ya existe, falla.

# Carpeta del proyecto: la del repo donde está este archivo (bash: BASH_SOURCE; zsh: ${(%):-%x}); se puede fijar con ARMA_PROJECT.
if [ -z "${ARMA_PROJECT:-}" ]; then
  if [ -n "${BASH_VERSION:-}" ]; then _track_src="${BASH_SOURCE[0]}"; else _track_src="${(%):-%x}"; fi
  ARMA_PROJECT="$(cd "$(dirname "$_track_src")/.." && pwd)"
  unset _track_src
fi
MANIFEST="$ARMA_PROJECT/install_manifest.tsv"

# track_mkdir <carpeta>: crea la carpeta (y padres faltantes) y registra cada nivel nuevo.
track_mkdir() {
  local p="$1" missing=()
  while [ ! -e "$p" ]; do missing=("$p" "${missing[@]}"); p="$(dirname "$p")"; done
  for p in "${missing[@]}"; do
    mkdir "$p" || return 1
    printf 'dir\t%s\t-\n' "$p" >> "$MANIFEST"
    echo "carpeta creada: $p"
  done
}

# track_copy <origen> <archivo_destino>: copia un archivo y registra su SHA-256.
track_copy() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] || [ -L "$dst" ]; then echo "ERROR: ya existe $dst" >&2; return 1; fi
  cp "$src" "$dst" || return 1
  printf 'file\t%s\t%s\n' "$dst" "$(shasum -a 256 "$dst" | cut -d' ' -f1)" >> "$MANIFEST"
  echo "archivo instalado: $dst"
}

# tree_hash <carpeta>: huella del contenido (rutas relativas + sha256 de cada archivo, ignora .DS_Store).
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

# track_unpack <pbo> <carpeta_nueva>: desempaca un PBO en una carpeta nueva y la registra con su huella.
track_unpack() {
  local pbo="$1" dst="$2"
  if [ -e "$dst" ] || [ -L "$dst" ]; then echo "ERROR: ya existe $dst" >&2; return 1; fi
  python3 "$ARMA_PROJECT/tools/pbo_tool.py" unpack "$pbo" "$dst" || return 1
  printf 'tree\t%s\t%s\n' "$dst" "$(tree_hash "$dst")" >> "$MANIFEST"
  echo "carpeta instalada: $dst"
}

# track_tree <carpeta_preparada> <carpeta_nueva>: copia una carpeta ya preparada (p. ej. con vio_config.py)
# y la registra con la huella final, para que undo.sh la borre solo si nadie la cambió después.
track_tree() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] || [ -L "$dst" ]; then echo "ERROR: ya existe $dst" >&2; return 1; fi
  cp -R "$src" "$dst" || return 1
  printf 'tree\t%s\t%s\n' "$dst" "$(tree_hash "$dst")" >> "$MANIFEST"
  echo "carpeta instalada: $dst"
}

# untrack_remove <ruta>: deshace una acción registrada (archivo, symlink, carpeta de misión con su huella o carpeta vacía) y quita su línea del manifiesto.
untrack_remove() {
  # ojo: no usar una variable llamada "path" (en zsh está ligada a PATH)
  local target="$1" line kind extra
  line="$(awk -F'\t' -v p="$target" '$2 == p' "$MANIFEST" | tail -1)"
  if [ -z "$line" ]; then echo "ERROR: $target no está en el manifiesto" >&2; return 1; fi
  kind="$(printf '%s' "$line" | cut -f1)"
  extra="$(printf '%s' "$line" | cut -f3)"
  case "$kind" in
    file)
      if [ "$(shasum -a 256 "$target" | cut -d' ' -f1)" != "$extra" ]; then
        echo "ERROR: $target cambió desde que se instaló; no lo borro" >&2; return 1
      fi
      rm "$target" || return 1 ;;
    symlink)
      if [ ! -L "$target" ]; then echo "ERROR: $target no es un symlink" >&2; return 1; fi
      rm "$target" || return 1 ;;
    tree)
      if [ ! -d "$target" ] || [ -L "$target" ]; then echo "ERROR: $target no es una carpeta" >&2; return 1; fi
      if [ "$(tree_hash "$target")" != "$extra" ]; then
        echo "ERROR: $target cambió desde que se registró; no la borro" >&2; return 1
      fi
      rm -r "$target" || return 1 ;;
    dir)
      # solo si quedó vacía (ignora .DS_Store)
      if [ -d "$target" ] && [ -n "$(ls -A "$target" | grep -v '^\.DS_Store$')" ]; then
        echo "ERROR: $target no está vacía; no la borro" >&2; return 1
      fi
      if [ -d "$target" ]; then rm -f "$target/.DS_Store"; rmdir "$target" || return 1; fi ;;
    *) echo "ERROR: untrack_remove no maneja el tipo '$kind'" >&2; return 1 ;;
  esac
  awk -F'\t' -v p="$target" '$2 != p' "$MANIFEST" > "$MANIFEST.tmp" && mv "$MANIFEST.tmp" "$MANIFEST"
  echo "retirado: $target"
}

# track_symlink <destino_real> <enlace>: crea un symlink y lo registra.
track_symlink() {
  local tgt="$1" lnk="$2"
  if [ -e "$lnk" ] || [ -L "$lnk" ]; then echo "ERROR: ya existe $lnk" >&2; return 1; fi
  ln -s "$tgt" "$lnk" || return 1
  printf 'symlink\t%s\t%s\n' "$lnk" "$tgt" >> "$MANIFEST"
  echo "symlink creado: $lnk -> $tgt"
}
