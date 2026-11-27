# -*- coding: utf-8 -*-
"""
StudentLedgerPro - منظومة سجل قيد الطلاب والتدقيق الجنائي الديناميكية
All Rights Reserved (C) 2026.
"""

import sys
import os
import re
import json
import sqlite3
import datetime
import base64
import hashlib
import ctypes
import tempfile
import pandas as pd
from rapidfuzz import fuzz

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSlot, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

# =========================================================================
# COPYRIGHT & INTELLECTUAL PROPERTY VERIFICATION (FULLY ENCRYPTED SIGNATURE)
# =========================================================================
# Encrypted Owner: "Zaghloul Sayed Zaghloul Saad"
_CIPHER_PAYLOAD = b'WmFnaGxvdWwgU2F5ZWQgWmFnaGxvdWwgU2FhZA=='
__OWNER_HASH__ = "d1b58bf147e4499d63dd8dc7c12663996726e6d1eb2c6fe8686e9ea37b2d2db7"

def _verify_license():
    try:
        decoded = base64.b64decode(_CIPHER_PAYLOAD).decode('utf-8')
        computed_hash = hashlib.sha256(decoded.encode('utf-8')).hexdigest()
        if computed_hash != __OWNER_HASH__:
            sys.exit(0)
        return decoded
    except Exception:
        sys.exit(0)

__AUTHOR__ = _verify_license()
__COPYRIGHT__ = f"Copyright (C) 2026 {__AUTHOR__}. All Rights Reserved."
# =========================================================================

def get_resource_path(relative_path):
    """دالة للوصول إلى ملفات الموارد والأيقونة سواء داخل التطوير أو بعد التحويل لـ EXE"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SmartMemoryDB:
    def __init__(self, db_path="forensic_dynamic_ledger.db"):
        self.conn = sqlite3.connect(db_path)
        self.init_db()

    def init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    field_name TEXT,
                    alias TEXT,
                    confidence REAL DEFAULT 1.0,
                    success_count INTEGER DEFAULT 1,
                    PRIMARY KEY (field_name, alias)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS import_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    row_count INTEGER DEFAULT 0,
                    column_count INTEGER DEFAULT 0,
                    header_row INTEGER DEFAULT 0
                )
            """)

    def get_semantic_aliases(self, field):
        cur = self.conn.cursor()
        cur.execute("SELECT alias, confidence FROM semantic_memory WHERE field_name = ?", (field,))
        return dict(cur.fetchall())

    def remember_alias(self, field, alias, confidence=0.9):
        alias = normalize_txt(alias)
        if not field or not alias or len(alias) < 2:
            return
        with self.conn:
            self.conn.execute("""
                INSERT INTO semantic_memory(field_name, alias, confidence, success_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(field_name, alias) DO UPDATE SET
                    confidence = MIN(1.0, MAX(confidence, excluded.confidence)),
                    success_count = success_count + 1
            """, (field, alias, float(confidence)))

    def record_import(self, file_name, row_count, column_count, header_row):
        with self.conn:
            self.conn.execute("""
                INSERT INTO import_history(file_name, imported_at, row_count, column_count, header_row)
                VALUES (?, ?, ?, ?, ?)
            """, (os.path.basename(file_name), datetime.datetime.now().isoformat(timespec="seconds"),
                  int(row_count), int(column_count), int(header_row)))

EXPLICIT_FEMALE_NAMES = {
    'فاطمة', 'فاطمه', 'سارة', 'ساره', 'مريم', 'ايه', 'آية', 'نورهان', 'رغد', 'شهد',
    'ياسمين', 'هاجر', 'سما', 'سلمى', 'سلمي', 'داليا', 'منى', 'مني', 'منه', 'منة',
    'اسراء', 'إسراء', 'شيماء', 'كريمان', 'جودي', 'جودى', 'جمان', 'فرح', 'كلارا',
    'اميرة', 'أميرة', 'ندى', 'ندي', 'هبة', 'هبه', 'هدى', 'هدي', 'وردة', 'ورده',
    'ولاء', 'يارا', 'رؤى', 'رؤي', 'الزهراء', 'جنه', 'جنة', 'اماني', 'أماني', 'خلود',
    'رحاب', 'دعاء', 'نهى', 'نهي', 'بسمة', 'بسمه', 'رانيا', 'دينا', 'مي', 'علا', 'حبيبة'
}

EXPLICIT_MALE_NAMES = {
    'محمد', 'احمد', 'أحمد', 'محمود', 'مصطفى', 'مصطفي', 'يوسف', 'عمر', 'عمرو', 'علي', 'على',
    'حسن', 'حسين', 'خالد', 'عبدالرحمن', 'عبد الرحمن', 'عبدالله', 'عبد الله', 'ابراهيم', 'إبراهيم',
    'كريم', 'طارق', 'زياد', 'سيف', 'مهند', 'معاذ', 'مروان', 'مازن', 'انس', 'أنس', 'ادم', 'آدم',
    'ادهم', 'أدهم', 'ايمن', 'أيمن', 'حاتم', 'حازم', 'رامي', 'رامى', 'زينهم', 'سمير', 'صلاح',
    'عصام', 'عادل', 'كمال', 'معاوية', 'معاويه', 'يحيى', 'يحيي', 'شادي', 'اسلام', 'إسلام'
}

ONTOLOGY_RULES = {
    'nationalId': {'headers': ['الرقم القومى', 'الرقم القومي', 'بطاقة الرقم القومي', 'national id', 'nid', 'جواز السفر', 'رقم الجواز'], 'regex': r'^[23]\d{13}$|^[A-Za-z]\d{6,}$'},
    'tripleNo': {'headers': ['الرقم الثلاثى', 'الرقم الثلاثي', 'رقم التجنيد', 'ثلاثي', '6 جند'], 'regex': r'^\d{1,4}\/\d{1,4}\/\d{2,4}$'},
    'code': {'headers': ['كود الطالب', 'الكود', 'كود', 'رقم القيد', 'student id', 'code'], 'regex': r'^\d{6,10}$'},
    'name': {'headers': ['الاسم', 'اسم الطالب', 'الاسم رباعي', 'الاسم بالكامل', 'student name'], 'regex': r'^[\u0621-\u064A\s]{9,}$'},
    'seatingNo': {'headers': ['رقم الجلوس', 'جلوس', 'seat no'], 'regex': r'^\d{3,7}$'},
    'militaryStatus': {'headers': ['الموقف من التجنيد', 'التجنيد', 'military status'], 'regex': r'وافد|مؤجل|اعفاء|إعفاء|طالبة|غير مطلوب|تجنيد'}
}

def to_western(val):
    if val is None or pd.isna(val): return ''
    return str(val).strip().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'))

def normalize_txt(text):
    if not text: return ''
    text = str(text).strip().lower()
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'[أإآ]', 'ا', text).replace('ة', 'ه').replace('ى', 'ي')
    return re.sub(r'\s+', ' ', re.sub(r'[-_,\.]', ' ', text)).strip()

class DynamicExcelProcessor:
    def __init__(self, file_path, db):
        self.file_path = file_path
        self.db = db
        # الاحتفاظ بالقيم كنصوص حتى لا تضيع الأصفار الموجودة في بداية الأكواد.
        self.df = pd.read_excel(file_path, header=None, dtype=str, na_filter=False)
        self.header_row = 0
        self.classified_fields = {}
        self.all_columns = []

    def classify_and_audit(self):
        best_row, max_score = 0, -1
        for r in range(min(15, len(self.df))):
            row_vals = [normalize_txt(str(x)) for x in self.df.iloc[r].dropna().tolist()]
            score = sum(2 for val in row_vals for f, spec in ONTOLOGY_RULES.items() if any(fuzz.partial_ratio(val, normalize_txt(h)) > 80 for h in spec['headers']))
            if score > max_score:
                max_score, best_row = score, r

        self.header_row = best_row
        raw_headers = self.df.iloc[self.header_row].tolist()
        self.all_columns = [{'idx': c, 'name': str(h).strip() if pd.notna(h) else f"عمود_{c+1}", 'norm': normalize_txt(str(h))} for c, h in enumerate(raw_headers)]

        sample_df = self.df.iloc[self.header_row + 1 : self.header_row + 80]
        for field, spec in ONTOLOGY_RULES.items():
            aliases = self.db.get_semantic_aliases(field)
            known_headers = {normalize_txt(h): 1.0 for h in spec['headers']}
            known_headers.update(aliases)
            best_col, best_score = -1, 0.0

            for col in self.all_columns:
                c = col['idx']
                col_name = col['norm']
                vals = sample_df.iloc[:, c].dropna().apply(to_western).tolist() if c < sample_df.shape[1] else []
                h_score = max([max(fuzz.ratio(col_name, kh), fuzz.partial_ratio(col_name, kh)) * w for kh, w in known_headers.items()] or [0])
                r_score = ((sum(1 for v in vals if re.search(spec['regex'], str(v).split('\n')[0].strip())) / max(1, len(vals))) * 100.0) if spec.get('regex') and vals else 0.0
                combined = (h_score * 0.5) + (r_score * 0.5)
                if combined > best_score and combined >= 35.0:
                    best_score, best_col = combined, c
            self.classified_fields[field] = best_col
            # التعلم التلقائي لا يحفظ إلا أسماء الأعمدة ذات درجة تطابق مرتفعة.
            if best_col >= 0 and best_score >= 85.0:
                self.db.remember_alias(field, self.all_columns[best_col]['name'], min(0.99, best_score / 100.0))

        title = ""
        for r in range(min(self.header_row + 1, 10)):
            r_str = " ".join([str(x) for x in self.df.iloc[r].dropna().tolist()])
            if not title and any(k in r_str for k in ['المستوى', 'العام الجامع', 'شئون الطلاب', 'كشف قيد', 'بيان']):
                title = r_str[:50]

        students = []
        current_year = datetime.datetime.now().year
        auto_serial = 1
        seen_nids, seen_seats = {}, {}

        for r_idx in range(self.header_row + 1, len(self.df)):
            row = self.df.iloc[r_idx]
            row_cells = [str(row[col['idx']]).strip() if pd.notna(row[col['idx']]) else '' for col in self.all_columns]
            if not any(row_cells): continue

            c_name = self.classified_fields.get('name', -1)
            c_nid = self.classified_fields.get('nationalId', -1)
            c_code = self.classified_fields.get('code', -1)
            c_mil = self.classified_fields.get('militaryStatus', -1)
            c_triple = self.classified_fields.get('tripleNo', -1)
            c_seat = self.classified_fields.get('seatingNo', -1)

            name_val = row_cells[c_name] if c_name != -1 else ''
            nid_val = to_western(row_cells[c_nid]) if c_nid != -1 else ''
            code_val = to_western(row_cells[c_code]) if c_code != -1 else ''
            mil_val = row_cells[c_mil] if c_mil != -1 else ''
            triple_val = to_western(row_cells[c_triple]) if c_triple != -1 else ''
            seat_val = to_western(row_cells[c_seat]).replace('.0', '') if c_seat != -1 else ''

            is_expat = bool(any(k in f"{mil_val} {name_val}".lower() for k in ['وافد', 'سودان', 'فلسطين', 'يمن', 'سور']) or (len(nid_val) > 0 and len(nid_val) != 14))

            error_notes = []
            has_nid_error = False
            has_biometric_error = False
            has_military_error = False
            is_critical_military = False
            has_seating_error = False

            first_name = name_val.split()[0].strip() if name_val else ''

            if nid_val and not is_expat:
                clean_nid = re.sub(r'\D', '', nid_val)
                if len(clean_nid) != 14:
                    has_nid_error = True
                    error_notes.append("الرقم القومي غير مكتمل (ليس 14 رقماً)")
                elif clean_nid[0] not in ('2', '3'):
                    has_nid_error = True
                    error_notes.append("رقم القرن غير صحيح بالرقم القومي")
                else:
                    century = 1900 if clean_nid[0] == '2' else 2000
                    yy = century + int(clean_nid[1:3])
                    mm = int(clean_nid[3:5])
                    dd = int(clean_nid[5:7])
                    sex_digit = int(clean_nid[12])
                    nid_is_female = (sex_digit % 2 == 0)

                    try:
                        datetime.date(yy, mm, dd)
                    except ValueError:
                        has_nid_error = True
                        error_notes.append("تاريخ الميلاد المشفر بالرقم القومي مستحيل تقويمياً")

                    if first_name in EXPLICIT_FEMALE_NAMES and not nid_is_female:
                        has_biometric_error = True
                        error_notes.append(f"تعارض بيولوجي: الاسم مؤنث صريح ({first_name}) والبطاقة مسجلة لذكر!")
                    if first_name in EXPLICIT_MALE_NAMES and nid_is_female:
                        has_biometric_error = True
                        error_notes.append(f"تعارض بيولوجي: الاسم مذكر صريح ({first_name}) والبطاقة مسجلة لأنثى!")

                    if not nid_is_female and first_name not in EXPLICIT_FEMALE_NAMES:
                        age = current_year - yy
                        if age >= 28:
                            is_critical_military = True
                            has_military_error = True
                            error_notes.append(f"تجنيد حرج: سن الطالب ({age} سنة) وتجاوز سن 28")

                        if triple_val:
                            parts = triple_val.split('/')
                            if len(parts) == 3:
                                t_yr = int(re.sub(r'\D', '', parts[2]) or 0)
                                if t_yr and t_yr != yy and (t_yr + 2000) != yy and (t_yr + 1900) != yy:
                                    has_military_error = True
                                    error_notes.append(f"تعارض سنة الميلاد بالثلاثي ({parts[2]}) مع القومي ({yy})")

            if nid_val and not is_expat:
                if nid_val in seen_nids:
                    has_nid_error = True
                    error_notes.append(f"الرقم القومي مكرر مع الطالب ({seen_nids[nid_val]})")
                else:
                    seen_nids[nid_val] = name_val

            if seat_val:
                if seat_val in seen_seats:
                    has_seating_error = True
                    error_notes.append(f"كارثة كنترول: رقم الجلوس ({seat_val}) مكرر مع الطالب ({seen_seats[seat_val]})")
                else:
                    seen_seats[seat_val] = name_val

            students.append({
                'serial': auto_serial,
                'cells': row_cells,
                'name': name_val or f"طالب_{auto_serial}",
                'code': code_val,
                'nationalId': nid_val,
                'isExpat': is_expat,
                'hasNidError': has_nid_error,
                'hasBiometricError': has_biometric_error,
                'hasMilitaryError': has_military_error,
                'isCriticalMilitary': is_critical_military,
                'hasSeatingError': has_seating_error,
                'errorNotes': error_notes
            })
            auto_serial += 1

        self.db.record_import(self.file_path, len(students), len(self.all_columns), self.header_row)
        return {
            'title': title or "سجل قيد الطلاب المعتمد",
            'columns': [c['name'] for c in self.all_columns],
            'classified_fields': self.classified_fields,
            'students': students,
            'audit_summary': {
                'rows': len(students), 'columns': len(self.all_columns),
                'header_row': self.header_row + 1,
                'errors': sum(1 for student in students if student['errorNotes'])
            }
        }

class PythonBridge(QObject):
    def __init__(self, main_win):
        super().__init__()
        self.win = main_win

    @pyqtSlot()
    def requestOpenExcel(self):
        self.win.open_excel_dialog()

    @pyqtSlot(str)
    def requestExportExcel(self, dummy):
        self.win.export_clean_excel()

    @pyqtSlot()
    def requestPrint(self):
        self.win.print_in_browser()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StudentLedgerPro - منظومة سجل قيد الطلاب والتدقيق الجنائي الديناميكية")
        
        self.setProperty("LegalCopyright", __COPYRIGHT__)
        self.setProperty("Author", __AUTHOR__)

        icon_path = get_resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinMaxButtonsHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        self.db = SmartMemoryDB()
        self.current_data = None

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.channel = QWebChannel()
        self.bridge = PythonBridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.browser.setHtml(self.get_html())

    def open_excel_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "📂 اختر ملف إكسيل الطلاب", "", "Excel Files (*.xlsx *.xls)")
        if not file_path: return
        try:
            processor = DynamicExcelProcessor(file_path, self.db)
            result = processor.classify_and_audit()
            if not result.get('columns'):
                raise ValueError("لم يتم العثور على أعمدة في ملف Excel.")
            self.current_data = result
            self.browser.page().runJavaScript(f"loadDynamicDataFromPython({json.dumps(result, ensure_ascii=False)});")
            summary = result.get('audit_summary', {})
            QMessageBox.information(self, "اكتمل فحص الملف",
                f"تم تحميل الملف بنجاح.\nالطلاب: {summary.get('rows', 0)}"
                f"\nالأعمدة: {summary.get('columns', 0)}"
                f"\nصف العناوين: {summary.get('header_row', 1)}"
                f"\nطلاب لديهم ملاحظات: {summary.get('errors', 0)}")
        except Exception as exc:
            QMessageBox.critical(self, "تعذر قراءة ملف Excel",
                "لم يتم تحميل الملف. تأكد أن الملف سليم وغير مفتوح بطريقة تمنع قراءته، "
                "وأنه بصيغة XLSX أو XLS.\n\nالتفاصيل: " + str(exc))

    def export_clean_excel(self):
        if not self.current_data: return
        path, _ = QFileDialog.getSaveFileName(self, "تصدير ملف الإكسيل المصحح", "StudentLedger_Clean.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        cols = ['م'] + self.current_data['columns'] + ['ملاحظات التدقيق الجنائي']
        rows = [[s['serial']] + s['cells'] + [" | ".join(s['errorNotes'])] for s in self.current_data['students']]
        pd.DataFrame(rows, columns=cols).to_excel(path, index=False)
        QMessageBox.information(self, "تم التصدير", "تم تصدير ملف الإكسيل بنجاح!")

    def print_in_browser(self):
        """فتح نسخة الطباعة في المتصفح الافتراضي واستخدام نافذة الطباعة المعتادة."""
        self.browser.page().toHtml(self._open_print_html)

    def _open_print_html(self, html):
        # نحفظ نسخة HTML من العرض الحالي؛ لا ننشئ PDF ولا نستخدم printToPdf.
        # نحذف سكربتات واجهة التطبيق لأن الصفحة المفتوحة خارج Qt لا تحتاج إلى WebChannel.
        printable_html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        auto_print = '''<script>
window.addEventListener('load', function () {
    setTimeout(function () { window.print(); }, 600);
});
</script>'''
        if '</body>' in printable_html.lower():
            match = re.search(r'</body>', printable_html, flags=re.IGNORECASE)
            printable_html = printable_html[:match.start()] + auto_print + printable_html[match.start():]
        else:
            printable_html += auto_print

        temp = tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.html',
            prefix='StudentLedgerPro_Print_', delete=False
        )
        try:
            with temp:
                temp.write(printable_html)
            QDesktopServices.openUrl(QUrl.fromLocalFile(temp.name))
        except Exception as exc:
            QMessageBox.critical(self, "خطأ في الطباعة", f"تعذر فتح صفحة الطباعة في المتصفح: {exc}")

    def get_html(self):
        return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>StudentLedgerPro</title>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background-color: #3e4245; margin: 0; padding: 15px; direction: rtl; display: flex; flex-direction: column; min-height: 100vh; }}
        .controls-panel {{ background: #fff; padding: 16px 20px; border-radius: 8px; box-shadow: 0 5px 18px rgba(0,0,0,0.25); max-width: 1400px; margin: 0 auto 15px auto; width: 100%; }}
        .controls-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; align-items: end; }}
        .control-item {{ display: flex; flex-direction: column; gap: 4px; }}
        label {{ font-weight: bold; font-size: 12px; color: #2c3e50; }}
        input, select, button.custom-file-btn {{ padding: 7px 10px; border: 1.5px solid #bbb; border-radius: 4px; font-size: 13px; outline: none; }}
        .assistant-cards-grid {{ display: none; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #dee2e6; }}
        .assistant-card {{ background: #f8f9fa; border: 1px solid #ced4da; border-radius: 6px; padding: 7px 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
        .assistant-card.alert-danger {{ border-right: 4px solid #dc3545; }}
        .assistant-card.alert-warning {{ border-right: 4px solid #ffc107; }}
        .assistant-card.alert-info {{ border-right: 4px solid #17a2b8; }}
        .assistant-card.alert-success {{ border-right: 4px solid #28a745; }}
        .actions-bar {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #dee2e6; justify-content: space-between; }}
        .btn {{ border: none; padding: 8px 14px; font-size: 13px; font-weight: bold; border-radius: 4px; cursor: pointer; color: white; display: inline-flex; align-items: center; gap: 6px; }}
        .btn-success {{ background: #1e7e34; }} .btn-primary {{ background: #0069d9; }} .btn-danger {{ background: #c82333; }} .btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        
        #pagesContainer {{ display: flex; flex-direction: column; gap: 25px; align-items: center; flex: 1; }}
        .empty-placeholder {{ background: #fff; padding: 50px 20px; text-align: center; border-radius: 8px; max-width: 650px; margin: 30px auto; color: #495057; }}
        .page-sheet {{ background: white; width: 297mm; min-height: 200mm; padding: 6mm 8mm; box-shadow: 0 0 14px rgba(0,0,0,0.3); display: flex; flex-direction: column; }}
        .page-header {{ text-align: center; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }}
        .page-title {{ font-size: 17px; font-weight: bold; margin: 0 auto; }}
        .page-tag {{ font-size: 11px; font-weight: bold; color: #555; border: 1px solid #aaa; padding: 2px 8px; border-radius: 4px; }}
        table.ledger-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        table.ledger-table th, table.ledger-table td {{ border: 1px solid #000; padding: 2px 3px; font-size: 11px; text-align: center; height: 13.5mm; word-wrap: break-word; overflow: hidden; }}
        table.ledger-table th {{ background: #f2f2f2; font-weight: bold; }}
        .screen-error-badge {{ display: inline-block; background: #ffc9c9; color: #c92a2a; font-size: 9px; padding: 1px 4px; border-radius: 3px; font-weight: bold; }}
        .cell-has-error {{ background-color: #fff3bf !important; }} .cell-has-danger {{ background-color: #ffe3e3 !important; }}
        
        .system-footer {{
            text-align: center;
            padding: 12px;
            color: #bdc3c7;
            font-size: 11.5px;
            letter-spacing: 0.8px;
            margin-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            user-select: none;
        }}
        .system-footer span {{
            color: #ffffff;
            font-weight: bold;
        }}

        @page {{ size: A4 landscape; margin: 8mm 10mm; }}
        @media print {{
            html, body {{ background: white !important; margin: 0 !important; padding: 0 !important; }}
            .controls-panel, .empty-placeholder, .no-print, .system-footer {{ display: none !important; visibility: hidden !important; height: 0 !important; }}
            .screen-error-badge, .cell-has-error, .cell-has-danger {{ background: transparent !important; display: none !important; }}
            .page-sheet {{ width: 100% !important; box-shadow: none !important; border: none !important; page-break-after: always !important; }}
        }}
    </style>
</head>
<body>
<div class="controls-panel">
    <div class="controls-grid">
        <div class="control-item">
            <label>📂 ملف Excel:</label>
            <button class="custom-file-btn" onclick="pyBridge.requestOpenExcel()" style="background:#007bff; color:#fff; font-weight:bold; cursor:pointer;">📂 جلب وفحص الملف ديناميكياً</button>
        </div>
        <div class="control-item"><label>📝 العنوان:</label><input type="text" id="titleInput" value="سجل قيد الطلاب المعتمد"></div>
        <div class="control-item"><label>🔢 الصفوف في الصفحة:</label><input type="number" id="rowsPerPageInput" value="10" min="4" max="30"></div>
        <div class="control-item"><label>📊 الأعمدة في الصفحة:</label><input type="number" id="colsPerPageInput" value="10" min="4" max="25"></div>
        <div class="control-item">
            <label>🔢 نظام الترقيم:</label>
            <select id="serialModeSelect">
                <option value="smart_continuous" selected>ترقيم تسلسلي ذكي مستمر (1..N)</option>
                <option value="smart_page">إعادة الترقيم بكل صفحة (1..10)</option>
            </select>
        </div>
        <div class="control-item"><label>🔍 بحث لحظي:</label><input type="text" id="searchInput" placeholder="اسم، كود، رقم قومي..."></div>
        <div class="control-item" style="justify-content: flex-end;">
            <label style="cursor: pointer; display: flex; align-items: center; gap: 6px; font-weight: bold; font-size: 12px; height: 35px; background: #eef2f5; padding: 4px 8px; border-radius: 4px; border: 1px solid #ced4da;">
                <input type="checkbox" id="blankFirstPageCheck" checked style="width: 17px; height: 17px; cursor: pointer;">
                <span>📄 أول صفحة فارغة للتقابل</span>
            </label>
        </div>
    </div>
    <div class="assistant-cards-grid" id="assistantCardsGrid">
        <div class="assistant-card alert-danger" onclick="filterByError('nid_error')"><div><div style="font-size:11px; color:#555;">❌ أخطاء قومي</div><div style="font-size:15px; font-weight:bold;" id="cardNidErrCount">0</div></div><span>🆔</span></div>
        <div class="assistant-card alert-danger" onclick="filterByError('biometric')"><div><div style="font-size:11px; color:#555;">⚧️ تعارض نوع</div><div style="font-size:15px; font-weight:bold;" id="cardBiometricCount">0</div></div><span>⚠️</span></div>
        <div class="assistant-card alert-warning" onclick="filterByError('military')"><div><div style="font-size:11px; color:#555;">🎖️ تجنيد حرج</div><div style="font-size:15px; font-weight:bold;" id="cardMilitaryCount">0</div></div><span>🛡️</span></div>
        <div class="assistant-card alert-danger" onclick="filterByError('seating_gaps')"><div><div style="font-size:11px; color:#555;">🔢 تكرار جلوس</div><div style="font-size:15px; font-weight:bold;" id="cardSeatingGapsCount">0</div></div><span>🎟️</span></div>
        <div class="assistant-card alert-info" onclick="filterByError('expat')"><div><div style="font-size:11px; color:#555;">🌍 وافدون</div><div style="font-size:15px; font-weight:bold;" id="cardExpatCount">0</div></div><span>✈️</span></div>
        <div class="assistant-card alert-success" onclick="filterByError('all')"><div><div style="font-size:11px; color:#555;">📋 إجمالي الطلاب</div><div style="font-size:15px; font-weight:bold;" id="cardTotalCount">0</div></div><span>✔️</span></div>
    </div>
    <div class="actions-bar">
        <div>
            <button class="btn btn-success" id="btnPrint" onclick="confirmPrintReview()" disabled><span>🖨️</span> مراجعة ثم طباعة</button>
            <button class="btn btn-primary" id="btnExportExcel" onclick="pyBridge.requestExportExcel('')" disabled><span>📊</span> تصدير إكسيل مُنظف</button>
        </div>
    </div>
</div>

<div id="pagesContainer">
    <div class="empty-placeholder">
        <h3>⚡ السجل جاهز لاستقبال أي ملف Excel ديناميكياً</h3>
        <p>انقر فوق "جلب وفحص الملف ديناميكياً" للبدء.</p>
    </div>
</div>

<div class="system-footer">
    StudentLedgerPro &bull; Developed by <span>{__AUTHOR__}</span> &bull; All Rights Reserved &copy; 2026
</div>

<script>
    let pyBridge = null;
    new QWebChannel(qt.webChannelTransport, function (channel) {{ pyBridge = channel.objects.pyBridge; }});
    let globalData = null;
    let activeErrorFilter = 'all';
    const SETTINGS_KEY = 'StudentLedgerPro.settings.v1';

    function saveUserSettings() {{
        const settings = {{ rows: document.getElementById('rowsPerPageInput').value, cols: document.getElementById('colsPerPageInput').value, serial: document.getElementById('serialModeSelect').value, blank: document.getElementById('blankFirstPageCheck').checked, title: document.getElementById('titleInput').value }};
        try {{ localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); }} catch (e) {{}}
    }}
    function restoreUserSettings() {{
        try {{ const v = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null'); if (!v) return;
            if (v.rows) document.getElementById('rowsPerPageInput').value = v.rows;
            if (v.cols) document.getElementById('colsPerPageInput').value = v.cols;
            if (v.serial) document.getElementById('serialModeSelect').value = v.serial;
            if (typeof v.blank === 'boolean') document.getElementById('blankFirstPageCheck').checked = v.blank;
            if (v.title) document.getElementById('titleInput').value = v.title;
        }} catch (e) {{}}
    }}
    function getFixedColumnIndexes() {{
        if (!globalData) return [];
        const fields = globalData.classified_fields || {{}};
        const result = [];
        ['code','name','nationalId','seatingNo'].forEach(field => {{ const i = Number(fields[field]); if (Number.isInteger(i) && i >= 0 && i < globalData.columns.length && !result.includes(i)) result.push(i); }});
        return result;
    }}
    function confirmPrintReview() {{
        if (!globalData) return;
        const rows = Math.max(1, parseInt(document.getElementById('rowsPerPageInput').value, 10) || 10);
        const cols = Math.max(1, parseInt(document.getElementById('colsPerPageInput').value, 10) || 10);
        const fixed = getFixedColumnIndexes().length;
        const capacity = Math.max(1, cols - fixed);
        const parts = Math.max(1, Math.ceil(Math.max(0, globalData.columns.length - fixed) / capacity));
        const rowParts = Math.max(1, Math.ceil(globalData.students.length / rows));
        const summary = globalData.audit_summary || {{}};
        const pages = parts * rowParts + (document.getElementById('blankFirstPageCheck').checked ? 1 : 0);
        const msg = 'مراجعة قبل الطباعة\\nعدد الطلاب: ' + globalData.students.length + '\\nعدد الأعمدة: ' + globalData.columns.length + '\\nأعمدة التعريف المتكررة في كل جزء: ' + fixed + '\\nأجزاء الأعمدة: ' + parts + '\\nالصفحات المتوقعة: ' + pages + '\\nطلاب لديهم ملاحظات: ' + (summary.errors || 0) + '\\n\\nفتح نافذة الطباعة العادية في المتصفح؟';
        if (window.confirm(msg)) pyBridge.requestPrint();
    }}
    restoreUserSettings();
    ['rowsPerPageInput','colsPerPageInput','serialModeSelect','titleInput','blankFirstPageCheck'].forEach(id => {{ const el = document.getElementById(id); el.addEventListener('change', saveUserSettings); el.addEventListener('input', saveUserSettings); }});

    function loadDynamicDataFromPython(data) {{
        globalData = data;
        document.getElementById('titleInput').value = data.title;
        document.getElementById('btnPrint').disabled = false;
        document.getElementById('btnExportExcel').disabled = false;
        updateCards();
        renderDynamicLedger();
    }}

    function toArabicDigits(str) {{
        if (!str && str !== 0) return '';
        return str.toString().replace(/\\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
    }}

    function updateCards() {{
        if (!globalData) return;
        const students = globalData.students;
        document.getElementById('cardNidErrCount').innerText = toArabicDigits(students.filter(s => s.hasNidError).length);
        document.getElementById('cardBiometricCount').innerText = toArabicDigits(students.filter(s => s.hasBiometricError).length);
        document.getElementById('cardMilitaryCount').innerText = toArabicDigits(students.filter(s => s.hasMilitaryError || s.isCriticalMilitary).length);
        document.getElementById('cardSeatingGapsCount').innerText = toArabicDigits(students.filter(s => s.hasSeatingError).length);
        document.getElementById('cardExpatCount').innerText = toArabicDigits(students.filter(s => s.isExpat).length);
        document.getElementById('cardTotalCount').innerText = toArabicDigits(students.length);
        document.getElementById('assistantCardsGrid').style.display = 'grid';
    }}

    function filterByError(type) {{ activeErrorFilter = (activeErrorFilter === type) ? 'all' : type; renderDynamicLedger(); }}

    document.getElementById('searchInput').addEventListener('input', renderDynamicLedger);
    document.getElementById('rowsPerPageInput').addEventListener('input', renderDynamicLedger);
    document.getElementById('colsPerPageInput').addEventListener('input', renderDynamicLedger);
    document.getElementById('serialModeSelect').addEventListener('change', renderDynamicLedger);
    document.getElementById('titleInput').addEventListener('input', renderDynamicLedger);
    document.getElementById('blankFirstPageCheck').addEventListener('change', renderDynamicLedger);

    function renderDynamicLedger() {{
        const container = document.getElementById('pagesContainer');
        container.innerHTML = '';
        if (!globalData) return;
        const title = toArabicDigits(document.getElementById('titleInput').value);
        const query = document.getElementById('searchInput').value.trim().toLowerCase();
        const rowsPerPage = Math.max(1, parseInt(document.getElementById('rowsPerPageInput').value, 10) || 10);
        const colsPerPage = Math.max(1, parseInt(document.getElementById('colsPerPageInput').value, 10) || 10);
        const serialMode = document.getElementById('serialModeSelect').value;
        const startBlank = document.getElementById('blankFirstPageCheck').checked;
        const filtered = globalData.students.filter(s => {{
            const matchQ = !query || (s.name || '').toLowerCase().includes(query) || (s.code || '').includes(query) || (s.nationalId || '').includes(query);
            let matchF = true;
            if (activeErrorFilter === 'nid_error') matchF = s.hasNidError;
            else if (activeErrorFilter === 'biometric') matchF = s.hasBiometricError;
            else if (activeErrorFilter === 'military') matchF = (s.hasMilitaryError || s.isCriticalMilitary);
            else if (activeErrorFilter === 'seating_gaps') matchF = s.hasSeatingError;
            else if (activeErrorFilter === 'expat') matchF = s.isExpat;
            return matchQ && matchF;
        }});
        if (!filtered.length) {{ container.innerHTML = '<div style="color:#fff;padding:30px;">لا توجد نتائج تطابق خيار الفرز.</div>'; return; }}
        if (startBlank) {{
            const blank = document.createElement('div'); blank.className = 'page-sheet blank-start-page';
            blank.innerHTML = '<div class="no-print" style="margin:auto;text-align:center;color:#777;border:2px dashed #aaa;padding:40px;border-radius:8px;">📄 <strong>صفحة بداية فارغة لضبط التقابل الدفتري وجه وظهر</strong></div>';
            container.appendChild(blank);
        }}
        const allColumns = globalData.columns;
        const fixedIndexes = getFixedColumnIndexes();
        const variableIndexes = allColumns.map((_, i) => i).filter(i => !fixedIndexes.includes(i));
        const variableCapacity = Math.max(1, colsPerPage - fixedIndexes.length);
        const variableChunks = [];
        if (!variableIndexes.length) variableChunks.push([]);
        else for (let i = 0; i < variableIndexes.length; i += variableCapacity) variableChunks.push(variableIndexes.slice(i, i + variableCapacity));
        const totalColChunks = variableChunks.length;
        const totalRowChunks = Math.ceil(filtered.length / rowsPerPage);
        let pageCounter = startBlank ? 2 : 1;
        const totalPages = totalRowChunks * totalColChunks + (startBlank ? 1 : 0);
        for (let rChunk = 0; rChunk < totalRowChunks; rChunk++) {{
            const studentSlice = filtered.slice(rChunk * rowsPerPage, (rChunk + 1) * rowsPerPage);
            const serialNumbers = studentSlice.map((student, idx) => serialMode === 'smart_continuous' ? (rChunk * rowsPerPage) + idx + 1 : idx + 1);
            for (let cChunk = 0; cChunk < totalColChunks; cChunk++) {{
                const colIndexes = [...fixedIndexes, ...variableChunks[cChunk]];
                const pageSheet = document.createElement('div'); pageSheet.className = 'page-sheet';
                const partLabel = totalColChunks > 1 ? ` (الجزء ${{toArabicDigits(cChunk + 1)}} من ${{toArabicDigits(totalColChunks)}})` : '';
                pageSheet.innerHTML = `<div class="page-header"><span class="page-tag">سجل ديناميكي</span><div class="page-title">${{title}}${{partLabel}}</div><span class="page-tag">صفحة: ${{toArabicDigits(pageCounter)}} من ${{toArabicDigits(totalPages)}}</span></div>`;
                const table = document.createElement('table'); table.className = 'ledger-table';
                let theadHtml = '<thead><tr><th style="width:4.5%;">م</th>';
                colIndexes.forEach(i => {{ theadHtml += `<th>${{allColumns[i]}}</th>`; }});
                theadHtml += '</tr></thead>';
                let tbodyHtml = '<tbody>';
                studentSlice.forEach((student, idx) => {{
                    const serialNum = serialNumbers[idx];
                    const badge = student.errorNotes && student.errorNotes.length && cChunk === 0 ? '<span class="screen-error-badge">⚠️</span>' : '';
                    tbodyHtml += `<tr><td style="font-weight:bold;">${{toArabicDigits(serialNum)}}</td>`;
                    colIndexes.forEach(i => {{
                        const cellVal = student.cells[i] || '';
                        let cellClass = '';
                        if (student.hasNidError && i === globalData.classified_fields['nationalId']) cellClass = 'cell-has-danger';
                        if (student.hasSeatingError && i === globalData.classified_fields['seatingNo']) cellClass = 'cell-has-danger';
                        if (student.hasMilitaryError && i === globalData.classified_fields['militaryStatus']) cellClass = 'cell-has-error';
                        const isName = i === globalData.classified_fields['name'];
                        const align = isName ? 'text-align:right;font-weight:bold;padding-right:5px;' : '';
                        tbodyHtml += `<td class="${{cellClass}}" style="${{align}}">${{isName ? badge : ''}}${{toArabicDigits(cellVal)}}</td>`;
                    }});
                    tbodyHtml += '</tr>';
                }});
                tbodyHtml += '</tbody>'; table.innerHTML = theadHtml + tbodyHtml;
                pageSheet.appendChild(table); container.appendChild(pageSheet); pageCounter++;
            }}
        }}
    }}
</script>
</body>
</html>
        """

if __name__ == "__main__":
    try:
        myappid = 'studentledgerpro.academic.audit.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    icon_file = get_resource_path("app_icon.ico")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))

    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
