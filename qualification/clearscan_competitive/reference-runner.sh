#!/usr/bin/env bash
# clearscan.sh - OCR a PDF with Acrobat XI Pro's ClearScan via GUI automation.
#
# Usage: clearscan.sh INPUT.pdf OUTPUT.pdf [clearscan|searchable-exact]
#
# Runs Adobe Acrobat XI Pro inside the Wine prefix on the virtual
# X display, drives the GUI with xdotool, and saves the ClearScan result.
#
# Environment overrides:
#   WINEPREFIX (default ~/.wine-acrobat-xi)
#   DISPLAY    (default :99)
#   XDO        (default ~/.local/bin/xdotool)
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 INPUT.pdf OUTPUT.pdf [clearscan|searchable-exact]" >&2
  exit 2
fi

INPUT="$(readlink -f "$1")"
OUTPUT="$(readlink -f "$2")"
STYLE="${3:-clearscan}"
[[ -f "$INPUT" ]] || { echo "input not found: $INPUT" >&2; exit 1; }
case "$STYLE" in
  clearscan|searchable-exact) ;;
  *) echo "unknown output style: $STYLE (use clearscan or searchable-exact)" >&2; exit 2 ;;
esac

export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-acrobat-xi}"
export WINEARCH="${WINEARCH:-win32}"
export DISPLAY="${DISPLAY:-:99}"
XDO="${XDO:-$HOME/.local/bin/xdotool}"

WORK="$WINEPREFIX/drive_c/work"
mkdir -p "$WORK"
cp "$INPUT" "$WORK/input.pdf"
rm -f "$WORK/output.pdf"

log() { echo "[clearscan] $*"; }

click() { "$XDO" mousemove "$1" "$2"; sleep 0.3; "$XDO" mousedown 1; sleep 0.25; "$XDO" mouseup 1; }
key()   { "$XDO" key "$1"; }
have_window() { xwininfo -root -tree -display "$DISPLAY" 2>/dev/null | grep -q -- "$1"; }

# position (top-left) of a named window, as "x y"
dlg_pos() {
  local wid
  wid="$("$XDO" search --name "$1" 2>/dev/null | head -1)"
  [[ -n "$wid" ]] || return 1
  "$XDO" getwindowgeometry "$wid" | grep -oE 'Position: [0-9]+,[0-9]+' | sed 's/Position: //; s/,/ /'
}

# window id of the document window titled "input.pdf ..."
input_wid() {
  local w t
  for w in $("$XDO" search --name "Adobe Acrobat Pro" 2>/dev/null); do
    t="$("$XDO" getwindowname "$w" 2>/dev/null || true)"
    case "$t" in input.pdf*) echo "$w"; return 0;; esac
  done
  return 1
}

# dismiss the 3-button "save changes" prompt with No (middle button)
dismiss_save_prompt() {
  if have_window '"Adobe Acrobat"'; then
    click 619 541; sleep 2
  fi
}

# --- 1. start Acrobat if needed ---------------------------------------------
if ! pgrep -x Acrobat.exe >/dev/null 2>&1; then
  log "starting Acrobat..."
  ( cd "$WINEPREFIX/drive_c/Program Files/Adobe/Acrobat 11.0/Acrobat" \
      && setsid wine Acrobat.exe >/dev/null 2>&1 & )
  for _ in $(seq 1 45); do
    sleep 2
    pgrep -x Acrobat.exe >/dev/null 2>&1 && break
  done
  sleep 20
fi

# --- 2. close every open document (discard changes) --------------------------
for _ in $(seq 1 6); do
  STRAY="$("$XDO" search --name "Adobe Acrobat Pro" 2>/dev/null | head -1)"
  [[ -n "$STRAY" ]] || break
  TITLE="$("$XDO" getwindowname "$STRAY" 2>/dev/null || true)"
  [[ "$TITLE" = "Adobe Acrobat Pro" ]] && break     # no document open
  "$XDO" windowactivate "$STRAY" 2>/dev/null || "$XDO" windowfocus "$STRAY"
  sleep 1
  key ctrl+w; sleep 2
  dismiss_save_prompt
done

# --- 3. open the input file and normalise geometry ---------------------------
WID="$("$XDO" search --name "Adobe Acrobat Pro" 2>/dev/null | head -1)"
"$XDO" windowactivate "$WID" 2>/dev/null || "$XDO" windowfocus "$WID"
sleep 1
log "opening C:\\work\\input.pdf"
key ctrl+o; sleep 3
click 400 525          # file name field (Open dialog)
key ctrl+a; sleep 0.3
"$XDO" type 'C:\work\input.pdf'; sleep 1
key Return; sleep 5

WID="$(input_wid)" || { log "ERROR: input.pdf window not found"; exit 1; }
"$XDO" windowmove "$WID" 34 60
"$XDO" windowsize "$WID" 1005 884
"$XDO" windowactivate "$WID" 2>/dev/null || "$XDO" windowfocus "$WID"
sleep 2

# --- 4. select page content and open the OCR dialog --------------------------
log "selecting page region"
"$XDO" mousemove 150 200; sleep 0.3
"$XDO" mousedown 1; sleep 0.4
"$XDO" mousemove 400 280; sleep 0.3
"$XDO" mousemove 700 350; sleep 0.5
"$XDO" mouseup 1; sleep 1.5

"$XDO" mousemove 400 280; sleep 0.5
"$XDO" click 3; sleep 2

if have_window "Scanned Page Alert"; then
  log "scanned page alert -> recognize"
  key Return; sleep 3
else
  log "context menu -> recognize text using OCR"
  click 500 417; sleep 3
fi

for _ in $(seq 1 5); do
  have_window '"Recognize Text"' && break
  sleep 2
done
if ! have_window '"Recognize Text"'; then
  # Landscape pages can be vertically centred below the fixed selection area.
  # Acrobat's normal select-all alert opens OCR without a page coordinate.
  log "fixed selection missed page; select-all OCR fallback"
  key Escape
  key ctrl+a; sleep 2
  if have_window "Scanned Page Alert"; then key Return; sleep 3; fi
fi
have_window '"Recognize Text"' || { log "ERROR: OCR dialog did not open"; exit 1; }

read -r DX DY <<< "$(dlg_pos 'Recognize Text')"
log "OCR dialog at $DX,$DY"

# --- 5. all pages + ClearScan output style -----------------------------------
log "setting all pages + $STYLE"
click $((DX + 35)) $((DY + 47)); sleep 1     # radio: All pages

# Edit... -> General Settings dialog (retry a few times)
SETTINGS_OK=0
for _ in 1 2 3; do
  click $((DX + 132)) $((DY + 264)); sleep 3
  if have_window "General Settings"; then SETTINGS_OK=1; break; fi
done
[[ "$SETTINGS_OK" = 1 ]] || { log "ERROR: settings dialog did not open"; exit 1; }

read -r SX SY <<< "$(dlg_pos 'General Settings')"
log "settings dialog at $SX,$SY"
click $((SX + 174)) $((SY + 50)); sleep 1    # PDF Output Style dropdown
if [[ "$STYLE" = "clearscan" ]]; then
  key End; sleep 0.5                         # ClearScan (last item)
else
  key Home; key Down; sleep 0.5
fi
key Return; sleep 0.4                        # commit sticky output-style selection
# Wine can deliver popup dismissal after the first confirmation click.
# Confirm settings again rather than cancelling the parent OCR dialog.
for _ in 1 2 3; do
  click $((SX + 62)) $((SY + 119)); sleep 3
  have_window "General Settings" || break
done
have_window "General Settings" && { log "ERROR: settings did not close"; exit 1; }

# --- 6. run OCR --------------------------------------------------------------
log "running OCR..."
for _ in 1 2 3; do
  click $((DX + 64)) $((DY + 307)); sleep 3
  have_window '"Recognize Text"' || break
done
for _ in $(seq 1 90); do
  sleep 2
  have_window '"Recognize Text"' || break
done
sleep 30 # the OCR dialog closes before asynchronous page processing completes

# --- 7. save as output.pdf ---------------------------------------------------
log "saving result"
key ctrl+shift+s; sleep 3
for _ in $(seq 1 5); do
  have_window '"Save As"' && break
  sleep 2
done
read -r AX AY <<< "$(dlg_pos 'Save As')" || { log "ERROR: Save As dialog did not open"; exit 1; }
click $((AX + 365)) $((AY + 446))            # file name field
key ctrl+a; sleep 0.3
"$XDO" type "output.pdf"; sleep 1
key Return                                    # Save (filename field is focused)
LAST_SIZE=0
STABLE=0
for _ in $(seq 1 60); do
  if [[ -s "$WORK/output.pdf" ]]; then
    CURRENT_SIZE="$(stat -c%s "$WORK/output.pdf")"
    if [[ "$CURRENT_SIZE" = "$LAST_SIZE" ]]; then
      STABLE=$((STABLE + 1))
      [[ "$STABLE" -ge 2 ]] && break
    else
      STABLE=0
      LAST_SIZE="$CURRENT_SIZE"
    fi
  fi
  sleep 1
done

[[ -f "$WORK/output.pdf" ]] || { log "ERROR: output.pdf was not saved"; exit 1; }
cp "$WORK/output.pdf" "$OUTPUT"
log "done: $OUTPUT"
