let currentStudentCode = "0206968";
let currentAccessToken = null;
let currentStudentProfile = null;
let isAuthenticated = false;
let idleSeconds = 30;
let idleInterval = null;
let activeStream = null;
let faceTrackTimer = null;
let lastUploadedB64 = null;
let consecutiveFaceHits = 0;
let isExpandedFullscreen = false;
let isObjectCover = false;
let isDetectionInflight = false;
let sessionEpoch = 0;
let isListeningVoice = false;

function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function resetIdleTimer() {
  idleSeconds = 30;
  const el = document.getElementById("idleCountdown");
  if (el) el.textContent = idleSeconds;
}

document.addEventListener("click", resetIdleTimer);
document.addEventListener("keydown", (e) => {
  resetIdleTimer();
  if (e.key === "Escape" && isExpandedFullscreen) {
    toggleExpandCameraModal();
  }
});
document.addEventListener("touchstart", resetIdleTimer);

window.addEventListener("DOMContentLoaded", async () => {
  await populateCameraList();
  await startCamera(false);
});

function toggleMirrorCamera() {
  const chk = document.getElementById("chkMirrorCamera");
  const video = document.getElementById("webcamVideo");
  if (video) {
    video.style.transform = chk && chk.checked ? "scaleX(-1)" : "none";
  }
}

function toggleVideoFitMode() {
  const video = document.getElementById("webcamVideo");
  const btn = document.getElementById("btnFitMode");
  const lbl = document.getElementById("liveResolutionLabel");
  isObjectCover = !isObjectCover;
  if (isObjectCover) {
    video.classList.remove("object-contain");
    video.classList.add("object-cover");
    btn.textContent = "📐 Chế độ: Lấp đầy khung";
    lbl.textContent = "Chế độ Lấp đầy (Cover)";
  } else {
    video.classList.remove("object-cover");
    video.classList.add("object-contain");
    btn.textContent = "📐 Hiện toàn cảnh (Không cắt)";
    lbl.textContent = "Tỷ lệ gốc 100% (Không cắt góc)";
  }
}

function toggleExpandCameraModal() {
  const container = document.getElementById("cameraViewportContainer");
  const btnClose = document.getElementById("btnCloseExpand");
  const btnExpand = document.getElementById("btnExpandCam");
  isExpandedFullscreen = !isExpandedFullscreen;
  if (isExpandedFullscreen) {
    container.classList.remove("camera-viewport-normal");
    container.classList.add("camera-viewport-expanded");
    btnClose.classList.remove("hidden");
    btnExpand.textContent = "🗕 Thu nhỏ khung Camera";
  } else {
    container.classList.remove("camera-viewport-expanded");
    container.classList.add("camera-viewport-normal");
    btnClose.classList.add("hidden");
    btnExpand.textContent = "🔍 Phóng to toàn màn hình";
  }
}

async function populateCameraList() {
  const sel = document.getElementById("cameraSelect");
  if (!sel) return;
  sel.innerHTML = "";
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Trình duyệt chặn WebRTC (Hãy mở qua http://localhost:8000)";
    sel.appendChild(opt);
    return;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(d => d.kind === "videoinput");
    if (videoDevices.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Không tìm thấy Webcam (Dùng Ảnh Thẻ SV hoặc Server Cam)";
      sel.appendChild(opt);
      return;
    }
    videoDevices.forEach((d, idx) => {
      const opt = document.createElement("option");
      opt.value = d.deviceId;
      opt.textContent = d.label || `Camera / Webcam #${idx + 1}`;
      sel.appendChild(opt);
    });
  } catch (e) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Chưa cấp quyền đọc danh sách Camera";
    sel.appendChild(opt);
  }
}

async function switchCameraDevice() {
  await startCamera(true);
}

async function startCamera(showAlertOnError = true) {
  const video = document.getElementById("webcamVideo");
  const previewImg = document.getElementById("uploadedFacePreview");
  const placeholder = document.getElementById("cameraPlaceholder");
  const badge = document.getElementById("cameraStatusBadge");
  const sel = document.getElementById("cameraSelect");

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    if (showAlertOnError) {
      alert("Hãy mở trang qua http://localhost:8000 để trình duyệt cấp quyền Camera, hoặc bấm nút '🖼️ Quét Ảnh Mặt Trước Thẻ (0206968)'!");
    }
    return;
  }

  try {
    stopLiveFaceTracking();
    if (activeStream) {
      activeStream.getTracks().forEach(t => t.stop());
    }

    const selectedDeviceId = sel && sel.value ? sel.value : undefined;
    const constraintsList = [
      selectedDeviceId
        ? { video: { deviceId: { exact: selectedDeviceId }, width: { ideal: 640 }, height: { ideal: 480 } }, audio: false }
        : { video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } }, audio: false },
      { video: true, audio: false }
    ];

    let stream = null;
    let lastErr = null;
    for (const c of constraintsList) {
      try {
        stream = await navigator.mediaDevices.getUserMedia(c);
        if (stream) break;
      } catch (err) {
        lastErr = err;
      }
    }

    if (!stream) {
      throw lastErr || new Error("Không thể khởi tạo luồng video từ Webcam.");
    }

    activeStream = stream;
    lastUploadedB64 = null;
    previewImg.classList.add("hidden");
    video.srcObject = stream;
    await video.play();
    video.classList.remove("hidden");
    placeholder.classList.add("hidden");

    const actualW = video.videoWidth || 640;
    const actualH = video.videoHeight || 480;
    document.getElementById("liveResolutionLabel").textContent = `Góc rộng ${actualW}x${actualH}px (100% Không cắt góc)`;

    badge.textContent = `🟢 Camera: ${actualW}x${actualH} Đang quét`;
    badge.className = "px-3 py-1.5 rounded-lg bg-emerald-600/30 border border-emerald-400/40 text-emerald-300 text-xs font-semibold";

    await populateCameraList();
    startLiveFaceTrackingLoop();

  } catch (err) {
    badge.textContent = "🟠 Camera: Đang dùng chế độ Ảnh Thẻ";
    badge.className = "px-3 py-1.5 rounded-lg bg-amber-600/30 border border-amber-400/40 text-amber-300 text-xs font-semibold";
    document.getElementById("cameraPlaceholderTitle").textContent =
      "Chưa mở được Webcam (" + (err.name || "No Camera") + ")";
    document.getElementById("cameraPlaceholderHint").innerHTML =
      "Bạn có thể bấm ngay nút <strong>🖼️ Quét Ảnh Mặt Trước Thẻ (0206968)</strong> hoặc <strong>📊 Quét Ảnh Mặt Sau Barcode (0206968)</strong> ở bên dưới để xác thực!";
  }
}

function captureCurrentFrameBase64() {
  if (lastUploadedB64) {
    return lastUploadedB64;
  }
  const video = document.getElementById("webcamVideo");
  if (!video || video.classList.contains("hidden") || video.readyState < 2) {
    return null;
  }
  const canvas = document.getElementById("captureCanvas");
  const w = video.videoWidth || 640;
  const h = video.videoHeight || 480;
  canvas.width = 480;
  canvas.height = Math.round((h / w) * 480) || 360;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.88);
}

function drawOverlayBox(bbox, frameW, frameH, labelText, colorHex = "#10b981", isMirrored = false) {
  const overlay = document.getElementById("overlayCanvas");
  if (!overlay) return;
  const video = document.getElementById("webcamVideo");
  const clientW = overlay.clientWidth || 560;
  const clientH = overlay.clientHeight || 430;
  overlay.width = clientW;
  overlay.height = clientH;
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);

  if (!bbox) return;

  const natW = frameW || (video && video.videoWidth) || 640;
  const natH = frameH || (video && video.videoHeight) || 480;
  const scale = isObjectCover ? Math.max(clientW / natW, clientH / natH) : Math.min(clientW / natW, clientH / natH);
  const offsetX = (clientW - natW * scale) / 2;
  const offsetY = (clientH - natH * scale) / 2;

  let x = offsetX + bbox.x * scale;
  const y = offsetY + bbox.y * scale;
  const w = bbox.w * scale;
  const h = bbox.h * scale;

  if (isMirrored) {
    x = offsetX + (natW - bbox.x - bbox.w) * scale;
  }

  ctx.strokeStyle = colorHex;
  ctx.lineWidth = 3;
  ctx.strokeRect(x, y, w, h);

  if (labelText) {
    ctx.font = "bold 12px Segoe UI, sans-serif";
    const textWidth = ctx.measureText(labelText).width + 16;
    ctx.fillStyle = colorHex;
    ctx.fillRect(x, Math.max(0, y - 26), textWidth, 24);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(labelText, x + 8, Math.max(16, y - 9));
  }
}

function toggleAutoFaceScan() {
  const chk = document.getElementById("chkAutoScan");
  if (chk && chk.checked) {
    startLiveFaceTrackingLoop();
  } else {
    stopLiveFaceTracking();
  }
}

function stopLiveFaceTracking() {
  sessionEpoch++;
  if (faceTrackTimer) {
    clearTimeout(faceTrackTimer);
    faceTrackTimer = null;
  }
  isDetectionInflight = false;
}

function startLiveFaceTrackingLoop() {
  stopLiveFaceTracking();
  const currentEpoch = sessionEpoch;

  async function scheduleNext() {
    if (sessionEpoch !== currentEpoch) return;
    const chk = document.getElementById("chkAutoScan");
    if (!chk || !chk.checked) return;

    if (isAuthenticated || document.hidden) {
      if (sessionEpoch === currentEpoch) {
        faceTrackTimer = setTimeout(scheduleNext, 850);
      }
      return;
    }

    if (!isDetectionInflight) {
      const video = document.getElementById("webcamVideo");
      if (video && !video.classList.contains("hidden")) {
        const frameB64 = captureCurrentFrameBase64();
        if (frameB64) {
          isDetectionInflight = true;
          try {
            const res = await fetch("/api/v1/auth/detect-face", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ face_image_b64: frameB64 })
            });
            if (sessionEpoch === currentEpoch) {
              const det = await res.json();
              const chkMirror = document.getElementById("chkMirrorCamera");
              const mirrored = chkMirror && chkMirror.checked && !lastUploadedB64;
              const statusEl = document.getElementById("faceTrackStatus");
              const liveEl = document.getElementById("faceLivenessBadge");

              if (det.face_detected) {
                consecutiveFaceHits++;
                drawOverlayBox(
                  det.bbox,
                  det.frame_width,
                  det.frame_height,
                  `Khuôn mặt • Liveness: ${det.liveness_score}`,
                  "#10b981",
                  mirrored
                );
                if (statusEl) statusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✅ Đã bắt nét khuôn mặt (${det.bbox.w}x${det.bbox.h}px)</span>`;
                if (liveEl) liveEl.textContent = `Liveness: ${det.liveness_score} (Độ nét: ${det.laplacian_sharpness})`;

                if (!isAuthenticated && consecutiveFaceHits >= 2) {
                  consecutiveFaceHits = 0;
                  await scanRealCameraAndLogin(frameB64);
                }
              } else {
                consecutiveFaceHits = 0;
                drawOverlayBox(null);
                if (statusEl) statusEl.innerHTML = `<span class="text-amber-300">🔍 Đang quét khuôn mặt hoặc Thẻ sinh viên trong khung ngắm...</span>`;
                if (liveEl) liveEl.textContent = `Liveness: --`;
              }
            }
          } catch (e) {
            // Ignore transient errors
          } finally {
            isDetectionInflight = false;
          }
        }
      }
    }

    if (sessionEpoch === currentEpoch) {
      faceTrackTimer = setTimeout(scheduleNext, 850);
    }
  }

  faceTrackTimer = setTimeout(scheduleNext, 500);
}

// Physical Student ID Card Verification from Live Camera or Uploaded Image
async function scanStudentCardFromCamera(customB64 = null, sourceLabel = "Camera trực tiếp") {
  const frameB64 = customB64 || captureCurrentFrameBase64();
  const authBox = document.getElementById("authResultBox");

  if (!frameB64) {
    authBox.innerHTML = `<div class="text-amber-300 font-semibold">⚠️ Chưa có hình ảnh từ Camera. Bạn có thể bấm nút <strong>"🖼️ Quét Ảnh Mặt Trước Thẻ (0206968)"</strong> ngay bên dưới!</div>`;
    return;
  }

  authBox.innerHTML = `<span class="text-sky-300">🪪 Đang quét mã vạch 1D & phân tích Thẻ sinh viên HUCE (${sourceLabel})...</span>`;

  // Real 1D Barcode scanning via ZXing browser library
  let decodedBarcode = null;
  if (typeof ZXing !== "undefined" && ZXing.BrowserMultiFormatReader) {
    try {
      const codeReader = new ZXing.BrowserMultiFormatReader();
      const img = new Image();
      img.src = frameB64;
      await new Promise((resolve) => {
        img.onload = resolve;
        img.onerror = resolve;
      });
      const zxRes = await codeReader.decodeFromImageElement(img);
      if (zxRes && zxRes.getText()) {
        decodedBarcode = zxRes.getText();
      }
    } catch (err) {
      // Barcode not decoded by ZXing in this frame; backend CV will analyze
    }
  }

  try {
    const res = await fetch("/api/v1/auth/scan-card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_image_b64: frameB64,
        decoded_barcode: decodedBarcode,
      })
    });
    const cardData = await res.json();

    if (!res.ok || !cardData.card_detected) {
      authBox.innerHTML = `<div class="text-rose-400 font-semibold">❌ ${escapeHtml(cardData.message)}</div>`;
      return;
    }

    document.getElementById("cardInput").value = cardData.student_code;
    drawOverlayBox(
      cardData.bbox,
      cardData.frame_width,
      cardData.frame_height,
      `Thẻ SV: ${cardData.student_code} - ${cardData.full_name}`,
      "#f59e0b",
      false
    );

    document.getElementById("faceTrackStatus").innerHTML =
      `<span class="text-amber-300 font-bold">🪪 Đã nhận diện ${escapeHtml(cardData.card_side)}</span>`;

    authBox.innerHTML = `<div class="text-sky-300 font-semibold">✅ Đã nhận diện thẻ ${escapeHtml(cardData.student_code)} – Bước 2: Vui lòng nhìn vào Camera để xác thực khuôn mặt (hoặc nhập mã PIN)</div>`;

  } catch (err) {
    authBox.innerHTML = `<span class="text-rose-400">Lỗi khi quét thẻ sinh viên: ${escapeHtml(err.message)}</span>`;
  }
}

// Load user's card photo from /cards/ and run real card verification
async function verifyWithUploadedCardPhoto(cardUrl, labelText) {
  const authBox = document.getElementById("authResultBox");
  authBox.innerHTML = `<span class="text-sky-300">Đang tải hình ảnh <strong>${escapeHtml(labelText)}</strong> vào khung ngắm để phân tích...</span>`;

  try {
    const resp = await fetch(cardUrl);
    const blob = await resp.blob();
    const reader = new FileReader();
    reader.onload = async (e) => {
      const b64 = e.target.result;
      lastUploadedB64 = b64;

      const video = document.getElementById("webcamVideo");
      const previewImg = document.getElementById("uploadedFacePreview");
      const placeholder = document.getElementById("cameraPlaceholder");
      video.classList.add("hidden");
      placeholder.classList.add("hidden");
      previewImg.src = b64;
      previewImg.classList.remove("hidden");

      const badge = document.getElementById("cameraStatusBadge");
      badge.textContent = `🪪 Đang quét: ${labelText}`;
      badge.className = "px-3 py-1.5 rounded-lg bg-amber-600/30 border border-amber-400/40 text-amber-300 text-xs font-semibold";

      await scanStudentCardFromCamera(b64, labelText);
    };
    reader.readAsDataURL(blob);
  } catch (e) {
    authBox.innerHTML = `<span class="text-rose-400">Không thể tải ảnh mẫu thẻ: ${escapeHtml(e.message)}</span>`;
  }
}

async function handleUploadedFaceImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (e) => {
    lastUploadedB64 = e.target.result;
    const video = document.getElementById("webcamVideo");
    const previewImg = document.getElementById("uploadedFacePreview");
    const placeholder = document.getElementById("cameraPlaceholder");
    video.classList.add("hidden");
    placeholder.classList.add("hidden");
    previewImg.src = lastUploadedB64;
    previewImg.classList.remove("hidden");

    const badge = document.getElementById("cameraStatusBadge");
    badge.textContent = "🟢 Đã nạp ảnh Thẻ / Khuôn mặt";
    badge.className = "px-3 py-1.5 rounded-lg bg-emerald-600/30 border border-emerald-400/40 text-emerald-300 text-xs font-semibold";

    await scanStudentCardFromCamera(lastUploadedB64, "Ảnh tải lên");
  };
  reader.readAsDataURL(file);
}

async function captureViaServerOpenCV() {
  const authBox = document.getElementById("authResultBox");
  authBox.innerHTML = `<span class="text-sky-300">Đang gọi OpenCV VideoCapture(0) trên máy chủ...</span>`;
  try {
    const res = await fetch("/api/v1/auth/capture-local-camera");
    const data = await res.json();
    if (!res.ok || !data.captured) {
      authBox.innerHTML = `<div class="text-amber-300 font-semibold">⚠️ ${escapeHtml(data.message)}</div>`;
      return;
    }
    lastUploadedB64 = data.frame_b64;
    const video = document.getElementById("webcamVideo");
    const previewImg = document.getElementById("uploadedFacePreview");
    const placeholder = document.getElementById("cameraPlaceholder");
    video.classList.add("hidden");
    placeholder.classList.add("hidden");
    previewImg.src = lastUploadedB64;
    previewImg.classList.remove("hidden");

    await scanRealCameraAndLogin(lastUploadedB64);
  } catch (e) {
    authBox.innerHTML = `<span class="text-rose-400">Lỗi kết nối: ${escapeHtml(e.message)}</span>`;
  }
}

async function loginWithPinFallback() {
  const cardId = document.getElementById("cardInput").value.trim() || "0206968";
  const pinInput = document.getElementById("pinFallbackInput");
  const pin = pinInput ? pinInput.value.trim() : "";
  const authBox = document.getElementById("authResultBox");

  if (!pin) {
    authBox.innerHTML = `<div class="text-rose-400 font-semibold">⚠️ Vui lòng nhập mã PIN dự phòng.</div>`;
    return;
  }

  authBox.innerHTML = `<span class="text-sky-300">Đang xác thực bằng mã PIN dự phòng cho thẻ ${escapeHtml(cardId)}...</span>`;

  try {
    const res = await fetch("/api/v1/auth/kiosk-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_identifier: cardId,
        pin_fallback: pin,
        kiosk_id: "KIOSK_LOBBY_H1"
      })
    });
    const data = await res.json();
    if (pinInput) pinInput.value = "";
    handleLoginResponse(res.ok, data, "Mã PIN dự phòng");
  } catch (e) {
    authBox.innerHTML = `<span class="text-rose-400">Lỗi kết nối máy chủ: ${escapeHtml(e.message)}</span>`;
  }
}

async function enrollMyFaceToCard() {
  const cardId = document.getElementById("cardInput").value.trim() || "0206968";
  const frameB64 = captureCurrentFrameBase64();
  const authBox = document.getElementById("authResultBox");

  if (!frameB64) {
    authBox.innerHTML = `<div class="text-amber-300 font-semibold">⚠️ Chưa có khung hình từ Camera hoặc ảnh tải lên!</div>`;
    return;
  }

  const pinCode = prompt("Vui lòng nhập mã PIN chủ thẻ (Mặc định: 310305 cho thẻ 0206968) để xác nhận quyền cập nhật khuôn mặt:") || "";
  if (!pinCode.trim()) {
    authBox.innerHTML = `<div class="text-rose-400 font-semibold">⚠️ Bắt buộc phải nhập mã PIN chủ thẻ để đăng ký khuôn mặt mới.</div>`;
    return;
  }

  authBox.innerHTML = `<span class="text-sky-300">Đang trích xuất vector khuôn mặt 128-d qua OpenCV và lưu vào thẻ ${escapeHtml(cardId)}...</span>`;
  try {
    const res = await fetch("/api/v1/auth/enroll-face", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_identifier: cardId,
        face_image_b64: frameB64,
        pin_code: pinCode.trim(),
      })
    });
    const data = await res.json();
    if (!res.ok || !data.enrolled) {
      authBox.innerHTML = `<div class="text-rose-400 font-semibold">❌ ${escapeHtml(data.message)}</div>`;
      return;
    }
    authBox.innerHTML = `<div class="text-emerald-400 font-bold">✅ ${escapeHtml(data.message)}</div>`;
    await scanRealCameraAndLogin(frameB64);
  } catch (e) {
    authBox.innerHTML = `<span class="text-rose-400">Lỗi đăng ký khuôn mặt: ${escapeHtml(e.message)}</span>`;
  }
}

async function scanRealCameraAndLogin(existingFrameB64 = null) {
  const cardId = document.getElementById("cardInput").value.trim() || "0206968";
  const frameB64 = existingFrameB64 || captureCurrentFrameBase64();
  const authBox = document.getElementById("authResultBox");

  if (!frameB64) {
    authBox.innerHTML = `<div class="text-amber-300 font-semibold">⚠️ Chưa thu được hình ảnh từ Camera. Hãy bật Camera hoặc bấm nút <strong>"🖼️ Quét Ảnh Mặt Trước Thẻ (0206968)"</strong>!</div>`;
    return;
  }

  authBox.innerHTML = `<span class="text-sky-300">Đang quét khuôn mặt qua OpenCV & đối sánh Cosine với thẻ ${escapeHtml(cardId)}...</span>`;

  try {
    const res = await fetch("/api/v1/auth/kiosk-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_identifier: cardId,
        face_image_b64: frameB64,
        kiosk_id: "KIOSK_LOBBY_H1"
      })
    });
    const data = await res.json();
    handleLoginResponse(res.ok, data);
  } catch (e) {
    authBox.innerHTML = `<span class="text-rose-400">Lỗi kết nối máy chủ: ${escapeHtml(e.message)}</span>`;
  }
}

function handleLoginResponse(isOk, data, cardSideNote = null) {
  const authBox = document.getElementById("authResultBox");
  if (!isOk || !data.authenticated) {
    authBox.innerHTML = `<div class="text-rose-400 font-semibold">❌ ${escapeHtml(data.message)}</div>`;
    return;
  }

  isAuthenticated = true;
  currentStudentCode = data.student.student_code;
  currentAccessToken = data.access_token || data.session_token || null;
  currentStudentProfile = data.student;
  const m = data.biometric_metrics;

  const extraCardNote = cardSideNote ? `<div class="text-amber-300 font-semibold">🪪 Phương thức Thẻ: Quét ${escapeHtml(cardSideNote)}</div>` : "";

  authBox.innerHTML = `
    <div class="text-emerald-400 font-bold mb-1">✅ ${escapeHtml(data.message)}</div>
    ${extraCardNote}
    <div class="text-[11px] text-slate-300">
      • Độ tương đồng Cosine: <strong>${m.cosine_similarity}</strong> (Ngưỡng >= ${m.threshold_required}) | Liveness: <strong>${m.liveness_score}</strong> | Thời gian: <strong>${m.verification_latency_ms}ms</strong>
    </div>
  `;

  const st = data.student;
  document.getElementById("studentProfileBox").innerHTML = `
    <div class="p-3.5 rounded-xl bg-slate-800 border border-sky-500/40 space-y-1.5">
      <div class="flex items-center justify-between">
        <div class="text-sm font-bold text-white">${escapeHtml(st.full_name)} (<span class="text-amber-300">MSSV: ${escapeHtml(st.student_code)}</span>)</div>
        <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">ĐÃ XÁC THỰC 2FA</span>
      </div>
      <div class="grid grid-cols-2 gap-1 text-xs pt-1">
        <div>• Ngày sinh: <strong>${escapeHtml(st.dob || "31/03/2005")}</strong></div>
        <div>• Lớp: <strong class="text-sky-300">${escapeHtml(st.class_name)}</strong></div>
        <div>• Khóa học: <strong>${escapeHtml(st.course_period || "2023-2027")}</strong></div>
        <div>• Email: <span class="text-sky-200">${escapeHtml(st.email || "dong" + st.student_code + "@huce.edu.vn")}</span></div>
      </div>
      <div>• Khoa / Ngành: <strong>${escapeHtml(st.major_name)}</strong></div>
      <div>• Mã Thẻ & Barcode: <code class="text-amber-300">${escapeHtml(st.card_uid)}</code> / <code class="text-purple-300">${escapeHtml(st.barcode_data)}</code></div>
      <div class="pt-1.5 border-t border-slate-700 flex justify-between">
        <span>GPA Học kỳ: <strong class="text-emerald-400">${st.gpa_semester}/4.0</strong></span>
        <span>GPA Tích lũy: <strong>${st.gpa_cumulative}/4.0</strong></span>
        <span>ĐRL: <strong class="text-sky-300">${st.training_score}/100</strong></span>
      </div>
    </div>
  `;

  document.getElementById("authStatusBadge").textContent = `Đã xác thực: ${st.full_name} (${st.student_code} - ${st.class_name})`;
  document.getElementById("authStatusBadge").className = "px-3.5 py-1.5 rounded-lg bg-emerald-600/30 border border-emerald-400/40 text-emerald-300 text-xs font-semibold";
  document.getElementById("sessionTimerBadge").classList.remove("hidden");
  document.getElementById("btnLogout").classList.remove("hidden");

  if (idleInterval) clearInterval(idleInterval);
  idleSeconds = 30;
  idleInterval = setInterval(() => {
    idleSeconds--;
    const el = document.getElementById("idleCountdown");
    if (el) el.textContent = idleSeconds;
    if (idleSeconds <= 0) {
      logoutKiosk();
    }
  }, 1000);
}

async function logoutKiosk() {
  const tokenToRevoke = currentAccessToken;
  currentAccessToken = null;
  currentStudentProfile = null;
  isAuthenticated = false;
  consecutiveFaceHits = 0;
  sessionEpoch++;
  lastUploadedB64 = null;

  if (idleInterval) {
    clearInterval(idleInterval);
    idleInterval = null;
  }

  const qInput = document.getElementById("questionInput");
  if (qInput) qInput.value = "";
  const pinInput = document.getElementById("pinFallbackInput");
  if (pinInput) pinInput.value = "";

  const previewImg = document.getElementById("uploadedFacePreview");
  if (previewImg) previewImg.classList.add("hidden");
  const video = document.getElementById("webcamVideo");
  if (video && activeStream) {
    video.classList.remove("hidden");
  }

  document.getElementById("sessionTimerBadge").classList.add("hidden");
  document.getElementById("btnLogout").classList.add("hidden");
  document.getElementById("authStatusBadge").textContent = "Chưa đăng nhập";
  document.getElementById("authStatusBadge").className = "px-3.5 py-1.5 rounded-lg bg-slate-700 text-slate-200 text-xs font-semibold";
  document.getElementById("studentProfileBox").innerHTML = `<p class="text-slate-400 italic">Đã tự động xóa phiên làm việc để bảo mật thông tin sinh viên tại sảnh.</p>`;
  document.getElementById("authResultBox").innerHTML = "Phiên làm việc đã kết thúc an toàn. Nhìn vào Camera hoặc giơ Thẻ sinh viên để bắt đầu phiên mới.";

  const chatBox = document.getElementById("chatMessages");
  if (chatBox) {
    chatBox.innerHTML = `
      <div class="p-3.5 rounded-xl bg-slate-800/95 border border-slate-600 text-sm leading-relaxed mr-8">
        <div class="flex items-center justify-between mb-1">
          <span class="font-bold text-emerald-400">🤖 Trợ lý Học vụ AI</span>
          <span class="text-[11px] text-slate-400">Sẵn sàng</span>
        </div>
        <div class="text-slate-100">
          Xin chào! Tôi là Trợ lý Học vụ AI tại Sảnh Giảng đường H1 – HUCE. Bạn có thể hỏi về Quy chế đào tạo tín chỉ, Điều kiện xét Học bổng KKHT, Lịch học, Lịch thi, hoặc Lộ trình gợi ý môn học. Vui lòng quét Thẻ sinh viên hoặc xác thực khuôn mặt để tra cứu thông tin cá nhân.
        </div>
      </div>
    `;
  }

  drawOverlayBox(null);

  const chkAuto = document.getElementById("chkAutoScan");
  if (chkAuto && chkAuto.checked && activeStream) {
    startLiveFaceTrackingLoop();
  }

  if (tokenToRevoke) {
    try {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: { "Authorization": `Bearer ${tokenToRevoke}` }
      });
    } catch (e) {
      // Ignore network errors on logout
    }
  }
}

function quickAsk(q) {
  document.getElementById("questionInput").value = q;
  sendQuestion();
}

function formatMarkdown(text) {
  if (text === null || text === undefined) return "";
  const safe = escapeHtml(text);
  return safe
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.*?)`/g, "<code class='px-1.5 py-0.5 rounded bg-slate-900 text-amber-300'>$1</code>")
    .replace(/\n/g, "<br/>");
}

async function sendQuestion() {
  const input = document.getElementById("questionInput");
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  resetIdleTimer();

  const chatBox = document.getElementById("chatMessages");

  const userMsgDiv = document.createElement("div");
  userMsgDiv.className = "p-3 rounded-xl bg-blue-600/30 border border-blue-400/40 text-sm text-right ml-12";
  const senderSpan = document.createElement("span");
  senderSpan.className = "font-bold text-sky-300";
  senderSpan.textContent = isAuthenticated ? `Sinh viên (${currentStudentCode}): ` : "Khách vãng lai: ";
  userMsgDiv.appendChild(senderSpan);
  userMsgDiv.appendChild(document.createTextNode(question));
  chatBox.appendChild(userMsgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;

  const headers = { "Content-Type": "application/json" };
  if (currentAccessToken) {
    headers["Authorization"] = `Bearer ${currentAccessToken}`;
  }

  try {
    const res = await fetch("/api/v1/chat/query", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        question: question,
        student_code: currentStudentCode,
        kiosk_id: "KIOSK_LOBBY_H1"
      })
    });
    const data = await res.json();

    const aiMsgDiv = document.createElement("div");
    if (!res.ok) {
      aiMsgDiv.className = "p-3.5 rounded-xl bg-rose-950/80 border border-rose-500/40 text-sm leading-relaxed mr-8";
      const titleDiv = document.createElement("div");
      titleDiv.className = "font-bold text-rose-300 mb-1";
      titleDiv.textContent = `⚠️ Yêu cầu Xác thực (Mã lỗi ${res.status}):`;
      const bodyDiv = document.createElement("div");
      bodyDiv.className = "text-rose-100";
      bodyDiv.textContent = data.detail || data.message || "Lỗi truy vấn học vụ";
      aiMsgDiv.appendChild(titleDiv);
      aiMsgDiv.appendChild(bodyDiv);
    } else {
      aiMsgDiv.className = "p-3.5 rounded-xl bg-slate-800/95 border border-slate-600 text-sm leading-relaxed mr-8";
      const headerDiv = document.createElement("div");
      headerDiv.className = "flex items-center justify-between mb-1";
      const intentSpan = document.createElement("span");
      intentSpan.className = "font-bold text-emerald-400";
      intentSpan.textContent = `🤖 Trợ lý Học vụ AI (Intent: ${data.intent_detected})`;
      const timeSpan = document.createElement("span");
      timeSpan.className = "text-[11px] text-slate-400";
      timeSpan.textContent = `Phản hồi: ${data.response_time_ms}ms`;
      headerDiv.appendChild(intentSpan);
      headerDiv.appendChild(timeSpan);

      const contentDiv = document.createElement("div");
      contentDiv.className = "text-slate-100";
      contentDiv.innerHTML = formatMarkdown(data.answer);

      aiMsgDiv.appendChild(headerDiv);
      aiMsgDiv.appendChild(contentDiv);
    }
    chatBox.appendChild(aiMsgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  } catch (err) {
    const errDiv = document.createElement("div");
    errDiv.className = "p-3 rounded-xl bg-rose-900/50 text-rose-200 text-xs";
    errDiv.textContent = `Lỗi gọi API: ${err.message}`;
    chatBox.appendChild(errDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}

function startVoiceInput() {
  if (isListeningVoice) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Trình duyệt hiện tại không hỗ trợ Web Speech API. Bạn vui lòng nhập câu hỏi hoặc dùng các phím chạm nhanh!");
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = "vi-VN";
  isListeningVoice = true;

  recognition.onstart = () => {
    const statusEl = document.getElementById("faceTrackStatus");
    if (statusEl) statusEl.innerHTML = `<span class="text-sky-300 font-semibold">🎙️ Đang nghe giọng nói tiếng Việt...</span>`;
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("questionInput").value = transcript;
    sendQuestion();
  };

  recognition.onerror = () => {
    isListeningVoice = false;
  };

  recognition.onend = () => {
    isListeningVoice = false;
  };

  try {
    recognition.start();
  } catch (e) {
    isListeningVoice = false;
  }
}
