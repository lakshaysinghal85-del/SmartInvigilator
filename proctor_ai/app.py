"""
Biometric Liveness Detection Exam System — Server
Features:
  • Teacher creates exam room with unique ID + time window
  • Student can only join during the scheduled window
  • Session cannot be paused or ended by student
  • Auto-ends when time expires
  • Full report exported to Excel (.xlsx)
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2, numpy as np, base64, json, time, os, uuid, logging, io
from datetime import datetime, timedelta
from detector import ProctoringDetector

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    EXCEL_OK = True
except ImportError:
    EXCEL_OK = False

# ── App setup ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blds-secret-2025'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading',
                    logger=False, engineio_logger=False,
                    ping_timeout=60, ping_interval=25)

detector = ProctoringDetector()

os.makedirs('logs',    exist_ok=True)
os.makedirs('reports', exist_ok=True)

# ── In-memory stores ───────────────────────────────────────────────────────────
# exam_rooms[exam_code] = {
#   exam_code, title, teacher, password, start_dt (ISO), end_dt (ISO),
#   duration_min, created_at, sessions: []
# }
exam_rooms: dict = {}

# sessions[session_id] = {...}
sessions: dict = {}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_str():
    return datetime.now().isoformat(timespec='seconds')

def _mk_exam_code():
    """6-char alphanumeric code, e.g. XK9P2M"""
    import random, string
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if code not in exam_rooms:
            return code

def _parse_dt(date_str: str, time_str: str) -> datetime:
    """Parse 'YYYY-MM-DD' + 'HH:MM' → datetime."""
    return datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')

def _exam_is_open(room: dict) -> tuple[bool, str]:
    """Returns (is_open, reason_string)."""
    now = datetime.now()
    start = datetime.fromisoformat(room['start_dt'])
    end   = datetime.fromisoformat(room['end_dt'])
    if now < start:
        delta = int((start - now).total_seconds())
        m, s = divmod(delta, 60)
        h, m = divmod(m, 60)
        return False, f'Exam opens in {h:02d}:{m:02d}:{s:02d}'
    if now > end:
        return False, 'Exam window has closed'
    return True, 'open'

def _attention_score(total_violations: int) -> int:
    return max(0, 100 - total_violations * 5)

# ── Excel export ───────────────────────────────────────────────────────────────

def _export_excel(session_id: str) -> str | None:
    if not EXCEL_OK:
        return None
    sess = sessions.get(session_id)
    if not sess:
        return None

    wb = openpyxl.Workbook()

    # ── Summary sheet ──
    ws = wb.active
    ws.title = 'Summary'

    # Header colours
    hdr_fill  = PatternFill('solid', fgColor='0D1220')
    hdr_font  = Font(bold=True, color='00E5FF', name='Calibri', size=11)
    val_font  = Font(color='E2E8F0', name='Calibri', size=11)
    red_font  = Font(bold=True, color='FF3D5A', name='Calibri', size=13)
    grn_font  = Font(bold=True, color='00FF88', name='Calibri', size=13)
    thin      = Side(style='thin', color='1E2D47')
    bdr       = Border(left=thin, right=thin, top=thin, bottom=thin)

    def hdr_cell(row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill  = hdr_fill
        c.font  = hdr_font
        c.border = bdr
        c.alignment = Alignment(horizontal='center', vertical='center')

    def val_cell(row, col, val, font=None):
        c = ws.cell(row=row, column=col, value=val)
        c.font  = font or val_font
        c.border = bdr
        c.alignment = Alignment(horizontal='left', vertical='center')

    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 38

    title_cell = ws.cell(row=1, column=1,
                         value='BIOMETRIC LIVENESS DETECTION EXAM SYSTEM')
    title_cell.font = Font(bold=True, color='00E5FF', size=14, name='Calibri')
    title_cell.fill = PatternFill('solid', fgColor='070A14')
    ws.merge_cells('A1:B1')
    ws.row_dimensions[1].height = 28

    summary = [
        ('Session ID',       sess['session_id']),
        ('Student Name',     sess['student_name']),
        ('Exam Title',       sess['exam_name']),
        ('Exam Code',        sess.get('exam_code', '—')),
        ('Start Time',       sess.get('start_time', '—')),
        ('End Time',         sess.get('end_time', '—')),
        ('Total Violations', sess['total_violations']),
        ('Attention Score',  f"{sess['attention_score']}%"),
        ('Status',           sess.get('status', 'completed')),
    ]
    for i, (k, v) in enumerate(summary, start=2):
        hdr_cell(i, 1, k)
        vf = red_font if k == 'Total Violations' and sess['total_violations'] > 5 else \
             grn_font if k == 'Attention Score' else val_font
        val_cell(i, 2, v, font=vf)
        ws.row_dimensions[i].height = 20

    # ── Violations sheet ──
    wv = wb.create_sheet('Violations')
    cols = ['#', 'Time', 'Type', 'Severity', 'Message']
    widths = [6, 12, 22, 12, 50]
    for ci, (col, wd) in enumerate(zip(cols, widths), 1):
        hdr_cell(1, ci, col)
        wv.column_dimensions[wv.cell(1, ci).column_letter].width = wd

    sev_fill = {
        'HIGH':   PatternFill('solid', fgColor='3D0A0A'),
        'MEDIUM': PatternFill('solid', fgColor='3D2500'),
        'LOW':    PatternFill('solid', fgColor='001A1F'),
    }
    sev_font = {
        'HIGH':   Font(color='FF3D5A', name='Calibri', size=10),
        'MEDIUM': Font(color='FFB347', name='Calibri', size=10),
        'LOW':    Font(color='00E5FF', name='Calibri', size=10),
    }

    for row_i, v in enumerate(sess.get('violations', []), start=2):
        sev = v.get('severity', 'MEDIUM')
        fill = sev_fill.get(sev, PatternFill('solid', fgColor='111827'))
        row_vals = [row_i - 1, v.get('time',''), v.get('type',''),
                    sev, v.get('message','')]
        for ci, rv in enumerate(row_vals, 1):
            c = wv.cell(row=row_i, column=ci, value=rv)
            c.fill   = fill
            c.font   = sev_font.get(sev, val_font)
            c.border = bdr
            c.alignment = Alignment(horizontal='left', vertical='center')
        wv.row_dimensions[row_i].height = 18

    # ── Save ──
    path = f'reports/report_{session_id}.xlsx'
    wb.save(path)
    return path

# ── Routes — Teacher ───────────────────────────────────────────────────────────

@app.route('/teacher')
def teacher_page():
    return render_template('teacher.html')


@app.route('/api/exam/create', methods=['POST'])
def create_exam():
    d    = request.json or {}
    code = _mk_exam_code()

    try:
        start_dt = _parse_dt(d['date'], d['start_time'])
        end_dt   = _parse_dt(d['date'], d['end_time'])
    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid date/time: {e}'}), 400

    if end_dt <= start_dt:
        return jsonify({'error': 'End time must be after start time'}), 400

    duration_min = int((end_dt - start_dt).total_seconds() / 60)

    exam_rooms[code] = {
        'exam_code':    code,
        'title':        d.get('title', 'Exam'),
        'teacher':      d.get('teacher', 'Teacher'),
        'subject':      d.get('subject', ''),
        'password':     d.get('password', ''),
        'date':         d['date'],
        'start_dt':     start_dt.isoformat(),
        'end_dt':       end_dt.isoformat(),
        'duration_min': duration_min,
        'created_at':   _now_str(),
        'sessions':     [],
    }
    logger.info(f'Exam created: {code} | {d.get("title")} | {start_dt} – {end_dt}')
    return jsonify({'exam_code': code, 'duration_min': duration_min,
                    'start_dt': start_dt.isoformat(), 'end_dt': end_dt.isoformat()})


@app.route('/api/exam/list')
def list_exams():
    return jsonify(list(exam_rooms.values()))


@app.route('/api/exam/<code>')
def get_exam(code):
    r = exam_rooms.get(code.upper())
    if not r:
        return jsonify({'error': 'Exam not found'}), 404
    return jsonify(r)


@app.route('/api/exam/<code>/students')
def exam_students(code):
    """Return all session data for an exam (for teacher view)."""
    room = exam_rooms.get(code.upper())
    if not room:
        return jsonify({'error': 'Not found'}), 404
    result = []
    for sid in room['sessions']:
        s = sessions.get(sid)
        if s:
            result.append({k: v for k, v in s.items() if not k.startswith('_')})
    return jsonify(result)

# ── Routes — Student ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/monitor')
def monitor():
    return render_template(
        'dashboard.html',
        session_id   = request.args.get('session_id', ''),
        student_name = request.args.get('name', 'Student'),
        exam_name    = request.args.get('exam', 'Exam'),
        exam_code    = request.args.get('code', ''),
        end_dt       = request.args.get('end_dt', ''),
        duration_min = request.args.get('duration', '60'),
    )


@app.route('/api/session/join', methods=['POST'])
def join_session():
    """Student joins an exam room."""
    d    = request.json or {}
    code = d.get('exam_code', '').strip().upper()
    pwd  = d.get('password', '').strip()
    name = d.get('student_name', '').strip()

    if not code or not name:
        return jsonify({'error': 'Exam code and name are required'}), 400

    room = exam_rooms.get(code)
    if not room:
        return jsonify({'error': 'Exam code not found'}), 404

    if room['password'] and pwd != room['password']:
        return jsonify({'error': 'Incorrect exam password'}), 403

    is_open, reason = _exam_is_open(room)
    if not is_open:
        return jsonify({'error': reason}), 403

    session_id = str(uuid.uuid4())[:8].upper()
    sess = {
        'session_id':       session_id,
        'student_name':     name,
        'exam_name':        room['title'],
        'exam_code':        code,
        'subject':          room['subject'],
        'start_time':       _now_str(),
        'end_time':         None,
        'scheduled_end':    room['end_dt'],
        'duration_min':     room['duration_min'],
        'violations':       [],
        'attention_score':  100,
        'total_violations': 0,
        'status':           'active',
        '_last_audio_time': 0,
    }
    sessions[session_id] = sess
    room['sessions'].append(session_id)

    logger.info(f'Student joined: {name} → session {session_id} (exam {code})')
    return jsonify({
        'session_id':   session_id,
        'exam_name':    room['title'],
        'end_dt':       room['end_dt'],
        'duration_min': room['duration_min'],
        'status':       'joined',
    })


@app.route('/api/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """Auto-end (called by server timer or teacher override only)."""
    force = request.json.get('force', False) if request.json else False
    sess  = sessions.get(session_id)
    if not sess:
        return jsonify({'error': 'Not found'}), 404

    sess['end_time'] = _now_str()
    sess['status']   = 'completed'

    # Save JSON log
    log_path = f'logs/session_{session_id}.json'
    save_data = {k: v for k, v in sess.items() if not k.startswith('_')}
    with open(log_path, 'w') as f:
        json.dump(save_data, f, indent=2)

    # Export Excel
    xlsx_path = _export_excel(session_id)

    logger.info(f'Session ended: {session_id} | violations: {sess["total_violations"]}')
    return jsonify({'status': 'ended', 'log': log_path,
                    'excel': xlsx_path, 'data': save_data})


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    s = sessions.get(session_id)
    if s:
        return jsonify({k: v for k, v in s.items() if not k.startswith('_')})
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/sessions')
def all_sessions():
    return jsonify([{k: v for k, v in s.items() if not k.startswith('_')}
                    for s in sessions.values()])


@app.route('/api/report/<session_id>/download')
def download_report(session_id):
    path = f'reports/report_{session_id}.xlsx'
    if not os.path.exists(path):
        _export_excel(session_id)
    if os.path.exists(path):
        return send_file(path, as_attachment=True,
                         download_name=f'report_{session_id}.xlsx')
    return jsonify({'error': 'Report not found'}), 404

# ── WebSocket events ───────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    emit('status', {'message': 'Connected'})


@socketio.on('analyze_frame')
def handle_frame(data):
    try:
        session_id = data.get('session_id', '')
        frame_b64  = data.get('frame', '')
        if not frame_b64:
            return

        if ',' in frame_b64:
            frame_b64 = frame_b64.split(',')[1]
        img_bytes = base64.b64decode(frame_b64)
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        violations, stats, annotated_b64 = detector.analyze(frame, session_id)

        if session_id in sessions:
            sess = sessions[session_id]

            # Check if scheduled time expired — auto end
            sched_end = sess.get('scheduled_end')
            if sched_end and datetime.now() > datetime.fromisoformat(sched_end):
                if sess['status'] == 'active':
                    sess['status'] = 'completed'
                    sess['end_time'] = _now_str()
                    emit('exam_ended', {'reason': 'Time limit reached'})
                    return

            for v in violations:
                sess['violations'].append(v)
            total = len(sess['violations'])
            sess['total_violations'] = total
            sess['attention_score']  = _attention_score(total)

            stats['attention_score']  = sess['attention_score']
            stats['total_violations'] = total

            # Remaining seconds
            if sched_end:
                rem = max(0, int((datetime.fromisoformat(sched_end)
                                   - datetime.now()).total_seconds()))
                stats['remaining_seconds'] = rem
            else:
                stats['remaining_seconds'] = -1

        emit('analysis_result', {
            'violations':      violations,
            'stats':           stats,
            'annotated_frame': annotated_b64,
            'timestamp':       datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f'Frame error: {e}', exc_info=True)


@socketio.on('audio_level')
def handle_audio(data):
    try:
        session_id = data.get('session_id', '')
        level      = float(data.get('level', 0))

        # ── Raised threshold: 0.35 ──
        # Only flag genuinely loud speech, ignore background/keyboard noise
        if level < 0.35:
            return

        sess = sessions.get(session_id)
        if not sess:
            return

        # 10-second cooldown for audio violations
        if time.time() - sess.get('_last_audio_time', 0) < 10:
            return
        sess['_last_audio_time'] = time.time()

        violation = {
            'type': 'SPEECH_DETECTED', 'severity': 'MEDIUM',
            'message': f'Speech / loud audio detected (level {level:.2f})',
            'time': datetime.now().strftime('%H:%M:%S'), 'icon': '🔊',
        }
        sess['violations'].append(violation)
        total = len(sess['violations'])
        sess['total_violations'] = total
        sess['attention_score']  = _attention_score(total)

        emit('analysis_result', {
            'violations': [violation],
            'stats': {'attention_score': sess['attention_score'],
                      'total_violations': total},
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f'Audio error: {e}')

# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('\n' + '=' * 65)
    print('  🔬  BIOMETRIC LIVENESS DETECTION EXAM SYSTEM')
    print('=' * 65)
    print('  Student URL : http://localhost:5000')
    print('  Teacher URL : http://localhost:5000/teacher')
    print(f'  Models      : {detector.get_model_status()}')
    print(f'  Excel Export: {"✓ openpyxl" if EXCEL_OK else "✗ run: pip install openpyxl"}')
    print('=' * 65 + '\n')
    socketio.run(app, host='0.0.0.0', port=5000,
                 debug=False, allow_unsafe_werkzeug=True)
