#!/usr/bin/env bash
# ==============================================================================
# HUCE SMART AI KIOSK LAUNCHER FOR LOW-SPEC HARDWARE (Raspberry Pi / Mini PC)
# Target RAM Usage: < 400 MB | Zero GPU Required
# ==============================================================================
set -e

KIOSK_SERVER_URL="${KIOSK_SERVER_URL:-http://localhost:8000}"

echo "[HUCE-KIOSK] Configuring screen power management (disable blanking)..."
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

echo "[HUCE-KIOSK] Launching Chromium in Low-Memory Touchscreen Kiosk Mode..."
chromium-browser \
  --kiosk \
  --incognito \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --disk-cache-size=33554432 \
  --use-fake-ui-for-media-stream \
  "$KIOSK_SERVER_URL"
