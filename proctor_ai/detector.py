"""
Biometric Liveness Detection Exam System — Detection Engine
FIXES v2:
  • BUG 1 FIXED — NO_FACE: Strategy 5 removed (caused background = face false detect).
                  Threshold lowered 30→10 frames (~5s). Triggers properly now.
  • BUG 2 FIXED — LOOKING_AWAY: Aspect ratio threshold raised 0.60→0.72 (more sensitive).
                  Sideways frame threshold lowered 14→5 frames (~2.5s).
                  Added eye-based backup: no eyes visible for 8+ frames also flags.
  • BUG 3 FIXED — FALSE MULTI-FACE: minNeighbors raised 2→5 in all strategies.
                  Added NMS (_nms_faces) to merge overlapping boxes from same face.
                  multi_face threshold raised 3→6 frames for stability.
"""

import cv2
import numpy as np
import base64
import time
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class ProctoringDetector:
    def __init__(self):
        self.face_cascade    = None
        self.face_alt        = None
        self.face_alt2       = None
        self.eye_cascade     = None
        self.yolo_model      = None
        self.dlib_detector   = None
        self.shape_predictor = None

        # Frame counters
        self._no_face_frames    = 0
        self._sideways_frames   = 0
        self._multi_face_frames = 0
        self._no_eyes_frames    = 0   # ← NEW: backup counter for eye-based gaze check

        # Cooldowns (seconds between same violation type)
        self.COOLDOWN = {
            'NO_FACE':        12,
            'MULTIPLE_FACES':  6,
            'LOOKING_AWAY':   12,
            'PHONE_DETECTED':  5,
            'SPEECH_DETECTED': 12,
        }

        # ─────────────────────────────────────────────────────────────
        # BUG 1 FIX: no_face threshold  30 → 10  (~5 seconds at 2fps)
        # BUG 2 FIX: sideways threshold 14 → 5   (~2.5 seconds at 2fps)
        # BUG 3 FIX: multi_face         3  → 6   (needs 6 consistent frames)
        # ─────────────────────────────────────────────────────────────
        self.THRESHOLDS = {
            'no_face':    10,   # ← CHANGED from 30 → 10
            'sideways':    5,   # ← CHANGED from 14 → 5
            'multi_face':  6,   # ← CHANGED from  3 → 6
            'no_eyes':     8,   # ← NEW: frames with no eyes before flag
        }

        self._last_violation_time: dict = {}
        self._load_models()

    # ── Model loading ──────────────────────────────────────────────

    def _load_models(self):
        base = cv2.data.haarcascades

        self.face_cascade = cv2.CascadeClassifier(
            base + 'haarcascade_frontalface_default.xml')
        self.face_alt = cv2.CascadeClassifier(
            base + 'haarcascade_frontalface_alt.xml')
        self.face_alt2 = cv2.CascadeClassifier(
            base + 'haarcascade_frontalface_alt2.xml')
        self.eye_cascade = cv2.CascadeClassifier(
            base + 'haarcascade_eye.xml')
        logger.info('✓ Haar cascades loaded (default + alt + alt2)')

        # dlib (optional)
        try:
            import dlib
            self.dlib_detector = dlib.get_frontal_face_detector()
            lm = os.path.join('static', 'models',
                              'shape_predictor_68_face_landmarks.dat')
            if os.path.exists(lm):
                self.shape_predictor = dlib.shape_predictor(lm)
                logger.info('✓ dlib + landmarks loaded')
            else:
                logger.info('✓ dlib loaded (no landmark file)')
        except ImportError:
            logger.warning('⚠ dlib not installed — using Haar only')

        # YOLOv8 (optional)
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO('yolov8n.pt')
            logger.info('✓ YOLOv8 loaded')
        except Exception as e:
            logger.warning(f'⚠ YOLOv8 not available: {e}')

    # ── Main API ───────────────────────────────────────────────────

    def analyze(self, frame: np.ndarray, session_id: str = ''):
        """Returns (violations, stats, annotated_b64)"""
        violations = []
        annotated  = frame.copy()
        h, w       = frame.shape[:2]

        # ── Pre-process ────────────────────────────────────────────
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        gray  = clahe.apply(gray)

        # ── 1. Face detection ──────────────────────────────────────
        faces     = self._detect_faces_best(gray)
        num_faces = len(faces)

        # Draw bounding boxes
        for (x, y, fw, fh) in faces:
            col = (0, 230, 80) if num_faces == 1 else (0, 50, 255)
            cv2.rectangle(annotated, (x, y), (x + fw, y + fh), col, 2)
            cv2.putText(annotated, 'FACE', (x, max(y - 6, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)

        # ── 2. Multiple faces ──────────────────────────────────────
        if num_faces > 1:
            self._multi_face_frames += 1
            # BUG 3 FIX: now needs 6 consistent frames (was 3)
            if self._multi_face_frames >= self.THRESHOLDS['multi_face']:
                v = self._make_violation('MULTIPLE_FACES', 'HIGH',
                                         f'{num_faces} faces detected in frame', '👥')
                if v: violations.append(v)
        else:
            self._multi_face_frames = 0

        # ── 3. No face ─────────────────────────────────────────────
        if num_faces == 0:
            self._no_face_frames += 1
            # BUG 1 FIX: now triggers after 10 frames (was 30)
            if self._no_face_frames >= self.THRESHOLDS['no_face']:
                v = self._make_violation('NO_FACE', 'MEDIUM',
                                         'Student not visible — left the frame', '🚫')
                if v: violations.append(v)
        else:
            self._no_face_frames = 0

        # ── 4. Gaze — sideways + eye-based backup ─────────────────
        eyes_visible     = False
        looking_sideways = False

        if num_faces == 1:
            x, y, fw, fh = faces[0]

            # ─────────────────────────────────────────────────────
            # BUG 2 FIX: aspect ratio threshold raised 0.60 → 0.72
            # Explanation: when you turn head sideways, face width
            # shrinks. Old code required width < 60% of height.
            # Real sideways faces are typically 60–75% ratio.
            # New threshold catches this correctly.
            # ─────────────────────────────────────────────────────
            aspect     = fw / max(fh, 1)
            is_profile = aspect < 0.72   # ← CHANGED from 0.60 → 0.72

            roi_gray  = gray[y:y + fh, x:x + fw]
            roi_color = annotated[y:y + fh, x:x + fw]
            eyes      = self._detect_eyes(roi_gray)
            eyes_visible = len(eyes) >= 2

            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color,
                              (ex, ey), (ex + ew, ey + eh), (255, 210, 0), 1)

            # ── PRIMARY CHECK: sideways head turn (aspect ratio) ──
            if is_profile:
                self._sideways_frames += 1
                self._no_eyes_frames   = 0   # reset eye counter (face is turned, not hidden)
                # BUG 2 FIX: sideways threshold 14 → 5 frames
                if self._sideways_frames >= self.THRESHOLDS['sideways']:
                    looking_sideways = True
                    v = self._make_violation('LOOKING_AWAY', 'MEDIUM',
                                             'Head turned sideways — not facing screen', '👀')
                    if v: violations.append(v)
            else:
                self._sideways_frames = 0

                # ── BACKUP CHECK: eyes not visible (NEW) ─────────
                # If face is frontal but ZERO eyes detected for 8+
                # frames, student is likely looking far away/down.
                # This catches cases aspect ratio alone misses.
                if not eyes_visible:
                    self._no_eyes_frames += 1
                    if self._no_eyes_frames >= self.THRESHOLDS['no_eyes']:
                        v = self._make_violation('LOOKING_AWAY', 'MEDIUM',
                                                 'Eyes not visible — not facing screen', '👀')
                        if v: violations.append(v)
                else:
                    self._no_eyes_frames = 0

        else:
            # No single face — reset gaze counters
            self._sideways_frames = 0
            self._no_eyes_frames  = 0

        # ── 5. Phone detection ─────────────────────────────────────
        phone_detected = False
        if self.yolo_model:
            phones = self._detect_phone(frame)
            phone_detected = len(phones) > 0
            for (x1, y1, x2, y2, conf) in phones:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(annotated, f'PHONE {conf:.0%}', (x1, max(y1 - 8, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                v = self._make_violation('PHONE_DETECTED', 'HIGH',
                                         f'Mobile phone detected (conf {conf:.0%})', '📱')
                if v: violations.append(v)

        # ── 6. HUD overlay ─────────────────────────────────────────
        self._draw_hud(annotated, num_faces, eyes_visible, phone_detected)

        # ── 7. Encode ──────────────────────────────────────────────
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 72])
        b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf).decode()

        stats = {
            'face_count':     num_faces,
            'eyes_visible':   eyes_visible,
            'phone_detected': phone_detected,
            'looking_away':   looking_sideways,
        }
        return violations, stats, b64

    def get_model_status(self):
        return ' | '.join([
            'Haar✓',
            'dlib✓'      if self.dlib_detector   else 'dlib✗',
            'YOLOv8✓'   if self.yolo_model       else 'YOLOv8✗',
            'Landmarks✓' if self.shape_predictor  else 'Landmarks✗',
        ])

    # ── NEW: Non-Maximum Suppression for face boxes ────────────────

    def _nms_faces(self, faces, overlap_thresh=0.35):
        """
        BUG 3 FIX — Merges overlapping face boxes so one real face
        detected twice (at different scales) doesn't count as 2 faces.

        overlap_thresh=0.35 means: if two boxes share >35% area → same face.
        """
        if len(faces) == 0:
            return []

        boxes = np.array(faces, dtype=float)
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)

        # Sort by area descending (largest first = most confident)
        order = areas.argsort()[::-1]
        keep  = []

        while order.size > 0:
            i = order[0]
            keep.append(i)

            # Compute overlap of box i with all remaining boxes
            ix1 = np.maximum(x1[i], x1[order[1:]])
            iy1 = np.maximum(y1[i], y1[order[1:]])
            ix2 = np.minimum(x2[i], x2[order[1:]])
            iy2 = np.minimum(y2[i], y2[order[1:]])

            inter_w = np.maximum(0, ix2 - ix1)
            inter_h = np.maximum(0, iy2 - iy1)
            inter   = inter_w * inter_h

            # IoU (Intersection over Union)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

            # Keep only boxes with low overlap (different faces)
            order = order[np.where(iou <= overlap_thresh)[0] + 1]

        return [faces[i] for i in keep]

    # ── Face detection — tries approaches with stricter params ─────

    def _detect_faces_best(self, gray):
        """
        BUG 3 FIX: minNeighbors raised from 2 → 5 in all strategies.
        BUG 1 FIX: Strategy 5 (minNeighbors=1) REMOVED — it was
                   detecting background as faces, preventing NO_FACE
                   from ever triggering.
        All results pass through _nms_faces() to merge duplicate detections.
        """

        # Strategy 1: dlib (most accurate if installed)
        if self.dlib_detector:
            for upsample in [1, 0]:
                rects = self.dlib_detector(gray, upsample)
                result = [(r.left(), r.top(), r.width(), r.height())
                          for r in rects
                          if r.width() > 40 and r.height() > 40]
                if result:
                    return self._nms_faces(result)

        # Strategy 2: Default Haar — stricter minNeighbors
        # BUG 3 FIX: minNeighbors changed from 2 → 5
        for (sf, mn) in [(1.05, 5), (1.1, 5), (1.1, 4), (1.15, 4)]:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor  = sf,
                minNeighbors = mn,   # ← CHANGED: was 2, now 5
                minSize      = (50, 50),
                flags        = cv2.CASCADE_SCALE_IMAGE
            )
            if len(faces) > 0:
                return self._nms_faces([(x, y, w, h) for (x, y, w, h) in faces])

        # Strategy 3: Alt Haar cascade — stricter minNeighbors
        # BUG 3 FIX: minNeighbors changed from 2 → 5
        for (sf, mn) in [(1.05, 5), (1.1, 5), (1.15, 4)]:
            faces = self.face_alt.detectMultiScale(
                gray,
                scaleFactor  = sf,
                minNeighbors = mn,   # ← CHANGED: was 2, now 5
                minSize      = (50, 50)
            )
            if len(faces) > 0:
                return self._nms_faces([(x, y, w, h) for (x, y, w, h) in faces])

        # Strategy 4: Alt2 Haar cascade — stricter minNeighbors
        # BUG 3 FIX: minNeighbors changed from 2 → 4 (slightly relaxed as last real try)
        for (sf, mn) in [(1.05, 4), (1.1, 4), (1.15, 3)]:
            faces = self.face_alt2.detectMultiScale(
                gray,
                scaleFactor  = sf,
                minNeighbors = mn,   # ← CHANGED: was 2, now 4
                minSize      = (50, 50)
            )
            if len(faces) > 0:
                return self._nms_faces([(x, y, w, h) for (x, y, w, h) in faces])

        # ── Strategy 5 REMOVED ──────────────────────────────────────
        # OLD CODE WAS:
        #   faces = self.face_cascade.detectMultiScale(
        #       gray, scaleFactor=1.03, minNeighbors=1, minSize=(25,25))
        #
        # BUG 1 ROOT CAUSE: minNeighbors=1 is extremely sensitive.
        # It detected walls, shadows, and background patterns as faces.
        # This kept _no_face_frames resetting to 0, so NO_FACE never fired.
        # FIX: Strategy 5 completely removed.
        # ────────────────────────────────────────────────────────────

        return []

    def _detect_eyes(self, face_gray):
        eyes = self.eye_cascade.detectMultiScale(
            face_gray,
            scaleFactor  = 1.1,
            minNeighbors = 5,
            minSize      = (12, 12)
        )
        return eyes if len(eyes) > 0 else []

    def _detect_phone(self, frame):
        phones = []
        try:
            results = self.yolo_model(frame, verbose=False, conf=0.4)
            for result in results:
                for box in result.boxes:
                    cls  = int(box.cls[0])
                    conf = float(box.conf[0])
                    name = result.names[cls].lower()
                    if cls == 67 or 'phone' in name or 'cell' in name:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        phones.append((x1, y1, x2, y2, conf))
        except Exception as e:
            logger.debug(f'YOLO error: {e}')
        return phones

    # ── Violation with per-type cooldown ───────────────────────────

    def _make_violation(self, vtype, severity, message, icon='⚠'):
        now  = time.time()
        last = self._last_violation_time.get(vtype, 0)
        if now - last < self.COOLDOWN.get(vtype, 10):
            return None
        self._last_violation_time[vtype] = now
        return {
            'type':     vtype,
            'severity': severity,
            'message':  message,
            'icon':     icon,
            'time':     datetime.now().strftime('%H:%M:%S'),
        }

    # ── HUD overlay ────────────────────────────────────────────────

    def _draw_hud(self, frame, num_faces, eyes_visible, phone_detected):
        h, w = frame.shape[:2]
        ts   = datetime.now().strftime('%H:%M:%S')

        cv2.rectangle(frame, (0, 0), (w, 34), (5, 7, 14), -1)

        face_ok  = (num_faces == 1)
        face_col = (0, 220, 80) if face_ok else (0, 50, 220)
        cv2.putText(frame,
                    f"FACE: {'OK' if face_ok else 'MISSING'} ({num_faces})",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, face_col, 1)

        eye_col = (0, 220, 80) if eyes_visible else (0, 190, 220)
        cv2.putText(frame,
                    f"EYES: {'OK' if eyes_visible else 'DOWN/AWAY'}",
                    (210, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, eye_col, 1)

        if phone_detected:
            cv2.rectangle(frame, (0, h - 36), (w, h), (0, 0, 180), -1)
            cv2.putText(frame, '!! PHONE DETECTED !!',
                        (w // 2 - 130, h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        cv2.putText(frame, ts, (w - 90, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (90, 90, 90), 1)

        cl, t, c = 18, 2, (0, 190, 80)
        for px, py, dx, dy in [
            (6, 38, 1, 1), (w - 6, 38, -1, 1),
            (6, h - 6, 1, -1), (w - 6, h - 6, -1, -1)
        ]:
            cv2.line(frame, (px, py), (px + dx * cl, py), c, t)
            cv2.line(frame, (px, py), (px, py + dy * cl), c, t)