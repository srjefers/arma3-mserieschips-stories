#!/bin/bash
# arma_memlog.sh — registra la memoria REAL del proceso de Arma 3 medida por macOS (no por el juego).
# Solo lectura: no toca el juego ni Steam. Pensado para correr mientras juegas.
# Uso: tools/arma_memlog.sh [segundos_entre_muestras]   (por defecto 30)
#      Espera a que Arma arranque, mide hasta que se cierra y deja un CSV en work/perf/.
# Columnas:
#   footprint_mb  = memoria del proceso según macOS (la columna "Memoria" del Monitor de Actividad)
#   peak_mb       = máximo de footprint desde que arrancó el proceso
#   graphics_mb   = parte de footprint que son texturas y búferes de la GPU (IOAccelerator); en Apple Silicon es la misma RAM
#   rss_mb        = memoria residente (ps)
#   swap_used_mb  = swap usado por todo el sistema
#   free_pct      = memoria libre del sistema según memory_pressure (bajo = presión)
set -u
EVERY="${1:-30}"
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="$PROJECT/work/perf"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/memlog_$(date +%Y%m%d_%H%M).csv"

find_pid() { pgrep -x ArmA3 | head -1; }

echo "Esperando a que Arma 3 arranque (Ctrl+C para salir)..."
PID="$(find_pid)"
while [ -z "$PID" ]; do sleep 5; PID="$(find_pid)"; done
echo "Arma 3 encontrado (pid $PID). Registro cada ${EVERY}s en: $OUT"
echo "hora,footprint_mb,peak_mb,graphics_mb,rss_mb,swap_used_mb,free_pct" > "$OUT"

while kill -0 "$PID" 2>/dev/null; do
  FP="$(footprint -p "$PID" -f bytes 2>/dev/null)"
  fp=$(printf '%s\n' "$FP" | awk '/phys_footprint:/ {printf "%.0f", $2/1048576}')
  peak=$(printf '%s\n' "$FP" | awk '/phys_footprint_peak:/ {printf "%.0f", $2/1048576}')
  gfx=$(printf '%s\n' "$FP" | awk '/IOAccelerator/ && $2=="B" {s+=$1} END {printf "%.0f", s/1048576}')
  rss=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{printf "%.0f", $1/1024}')
  swap=$(sysctl -n vm.swapusage | awk '{v=$6; u=substr(v,length(v)); n=substr(v,1,length(v)-1); if (u=="G") n*=1024; printf "%.0f", n}')
  free=$(memory_pressure -Q 2>/dev/null | awk -F': ' '/free percentage/ {gsub("%","",$2); print $2}')
  echo "$(date +%H:%M:%S),${fp:-},${peak:-},${gfx:-},${rss:-},${swap:-},${free:-}" >> "$OUT"
  sleep "$EVERY"
done
echo "Arma 3 se cerró. Registro en: $OUT"
