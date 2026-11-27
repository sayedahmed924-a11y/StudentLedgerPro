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
import pandas as pd
from rapidfuzz import fuzz

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QDialog,
    QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QInputDialog
)
from student_database import StudentDatabase
from PyQt6.QtCore import Qt, QObject, pyqtSlot
from PyQt6.QtGui import QIcon
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

    def get_semantic_aliases(self, field):
        cur = self.conn.cursor()
        cur.execute("SELECT alias, confidence FROM semantic_memory WHERE field_name = ?", (field,))
        return dict(cur.fetchall())

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
        self.df = pd.read_excel(file_path, header=None, dtype=str)
        if self.df.empty or self.df.shape[1] == 0:
            raise ValueError("ملف Excel لا يحتوي على بيانات قابلة للقراءة.")
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
        candidates = []
        for field, spec in ONTOLOGY_RULES.items():
            aliases = self.db.get_semantic_aliases(field)
            known_headers = {normalize_txt(h): 1.0 for h in spec['headers']}
            known_headers.update(aliases)
            for col in self.all_columns:
                col_idx = col['idx']
                col_name = col['norm']
                vals = sample_df.iloc[:, col_idx].dropna().apply(to_western).tolist() if col_idx < sample_df.shape[1] else []
                h_score = max([max(fuzz.ratio(col_name, kh), fuzz.partial_ratio(col_name, kh)) * weight for kh, weight in known_headers.items()] or [0])
                r_score = ((sum(1 for value in vals if re.search(spec['regex'], str(value).split('\n')[0].strip())) / max(1, len(vals))) * 100.0) if spec.get('regex') and vals else 0.0
                combined = (h_score * 0.5) + (r_score * 0.5)
                if combined >= 35.0:
                    candidates.append((combined, field, col_idx))

        # A single Excel column must not be assigned to multiple semantic fields.
        self.classified_fields = {field: -1 for field in ONTOLOGY_RULES}
        assigned_fields, assigned_columns = set(), set()
        for score, field, col_idx in sorted(candidates, reverse=True):
            if field in assigned_fields or col_idx in assigned_columns:
                continue
            self.classified_fields[field] = col_idx
            assigned_fields.add(field)
            assigned_columns.add(col_idx)

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

            nid_header = self.all_columns[c_nid]['name'].lower() if c_nid != -1 else ''
            explicit_expat = any(k in f"{mil_val} {name_val}".lower() for k in ['وافد', 'سودان', 'فلسطين', 'يمن', 'سور'])
            passport_column = any(k in nid_header for k in ['جواز', 'passport'])
            is_expat = bool(explicit_expat or (passport_column and nid_val))

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
                duplicate_key = re.sub(r'\D', '', nid_val)
                if duplicate_key in seen_nids:
                    has_nid_error = True
                    error_notes.append(f"الرقم القومي مكرر مع الطالب ({seen_nids[duplicate_key]})")
                else:
                    seen_nids[duplicate_key] = name_val

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

        return {
            'title': title or "سجل قيد الطلاب المعتمد",
            'columns': [c['name'] for c in self.all_columns],
            'classified_fields': self.classified_fields,
            'students': students
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
        self.win.print_pdf()

    @pyqtSlot()
    def requestDatabaseManager(self):
        self.win.open_database_manager()

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
        self.student_db = StudentDatabase()
        self.current_user = self._authenticate_startup()
        self.current_data = None

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.channel = QWebChannel()
        self.bridge = PythonBridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.browser.setHtml(self.get_html())

    def _authenticate_startup(self):
        """Create the first administrator interactively, then require login."""
        if self.student_db.user_count() == 0:
            QMessageBox.information(self, "إعداد أول تشغيل",
                                    "أنشئ حساب المدير الأول. كلمة المرور لا تقل عن 8 أحرف.")
            while True:
                username, ok = QInputDialog.getText(self, "إنشاء المدير", "اسم المستخدم:")
                if not ok:
                    raise SystemExit(0)
                password, ok = QInputDialog.getText(
                    self, "إنشاء المدير", "كلمة المرور:",
                    QLineEdit.EchoMode.Password
                )
                if not ok:
                    raise SystemExit(0)
                try:
                    self.student_db.create_user(username, password, "admin")
                    break
                except Exception as exc:
                    QMessageBox.warning(self, "بيانات غير صحيحة", str(exc))

        while True:
            username, ok = QInputDialog.getText(self, "تسجيل الدخول", "اسم المستخدم:")
            if not ok:
                raise SystemExit(0)
            password, ok = QInputDialog.getText(
                self, "تسجيل الدخول", "كلمة المرور:",
                QLineEdit.EchoMode.Password
            )
            if not ok:
                raise SystemExit(0)
            user = self.student_db.authenticate(username, password)
            if user:
                self.student_db.log_activity(user["username"], "LOGIN", "تسجيل دخول ناجح")
                return user
            QMessageBox.warning(self, "فشل الدخول", "اسم المستخدم أو كلمة المرور غير صحيحة.")

    def _can_edit(self):
        return self.current_user and self.current_user["role"] in ("admin", "editor")

    def open_excel_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "📂 اختر ملف إكسيل الطلاب", "", "Excel Files (*.xlsx *.xls)")
        if not file_path: return
        try:
            processor = DynamicExcelProcessor(file_path, self.db)
            result = processor.classify_and_audit()
            if not result.get('students'):
                QMessageBox.warning(self, "ملف فارغ", "لم يتم العثور على سجلات طلاب في الملف المحدد.")
                return
            self.current_data = result
            if not self._can_edit():
                QMessageBox.warning(self, "صلاحية غير كافية", "حسابك يسمح بالمشاهدة فقط ولا يمكنه استيراد البيانات.")
                return
            try:
                self.student_db.import_students(result.get("students", []), os.path.basename(file_path))
                self.student_db.log_activity(self.current_user["username"], "IMPORT", os.path.basename(file_path))
            except Exception as db_exc:
                QMessageBox.warning(self, "تنبيه قاعدة البيانات",
                                    f"تم تحميل الملف للفحص، لكن تعذر حفظ نسخة البيانات في SQLite:\\n{db_exc}")
            payload = json.dumps(result, ensure_ascii=False).replace("</", "<\\/")
            self.browser.page().runJavaScript(f"loadDynamicDataFromPython({payload});")
        except Exception as exc:
            QMessageBox.critical(self, "تعذر قراءة الملف", f"حدث خطأ أثناء قراءة ملف Excel:\n{exc}")

    def open_database_manager(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إدارة قاعدة بيانات الطلاب")
        dialog.resize(850, 520)
        layout = QVBoxLayout(dialog)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("بحث بالاسم أو الكود أو الرقم القومي:"))
        search = QLineEdit()
        search.setPlaceholderText("اكتب كلمة البحث...")
        search_row.addWidget(search)
        layout.addLayout(search_row)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["المعرف", "اسم الطالب", "كود الطالب", "الرقم القومي", "وافد"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        def refresh():
            records = self.student_db.search_students(search.text(), limit=5000)
            table.setRowCount(len(records))
            for row_index, record in enumerate(records):
                values = [record["id"], record["name"], record["student_code"],
                          record["national_id"], "نعم" if record["is_expat"] else "لا"]
                for col_index, value in enumerate(values):
                    table.setItem(row_index, col_index, QTableWidgetItem(str(value)))

        def selected_id():
            row = table.currentRow()
            if row < 0:
                QMessageBox.information(dialog, "اختيار طالب", "اختر طالباً من الجدول أولاً.")
                return None
            return int(table.item(row, 0).text())

        def add_record():
            name, ok = QInputDialog.getText(dialog, "إضافة طالب", "اسم الطالب:")
            if not ok:
                return
            code, ok = QInputDialog.getText(dialog, "إضافة طالب", "كود الطالب:")
            if not ok:
                return
            nid, ok = QInputDialog.getText(dialog, "إضافة طالب", "الرقم القومي أو رقم الجواز:")
            if not ok:
                return
            try:
                self.student_db.add_student(name, code, nid)
                refresh()
            except Exception as exc:
                QMessageBox.critical(dialog, "تعذر الإضافة", str(exc))

        def edit_record():
            student_id = selected_id()
            if student_id is None:
                return
            record = next((r for r in self.student_db.search_students("", 5000)
                           if r["id"] == student_id), None)
            if not record:
                return
            name, ok = QInputDialog.getText(dialog, "تعديل طالب", "اسم الطالب:", text=record["name"])
            if not ok:
                return
            code, ok = QInputDialog.getText(dialog, "تعديل طالب", "كود الطالب:", text=record["student_code"])
            if not ok:
                return
            nid, ok = QInputDialog.getText(dialog, "تعديل طالب", "الرقم القومي أو رقم الجواز:", text=record["national_id"])
            if not ok:
                return
            try:
                self.student_db.update_student(student_id, name=name, student_code=code, national_id=nid)
                refresh()
            except Exception as exc:
                QMessageBox.critical(dialog, "تعذر التعديل", str(exc))

        def delete_record():
            student_id = selected_id()
            if student_id is None:
                return
            answer = QMessageBox.question(dialog, "تأكيد الحذف",
                                          "هل تريد حذف الطالب المحدد نهائياً؟")
            if answer == QMessageBox.StandardButton.Yes:
                self.student_db.delete_student(student_id)
                refresh()

        def backup_database():
            path, _ = QFileDialog.getSaveFileName(dialog, "حفظ نسخة احتياطية",
                                                  "StudentLedger_Backup.sqlite3",
                                                  "SQLite Database (*.sqlite3)")
            if path:
                try:
                    self.student_db.backup(path)
                    QMessageBox.information(dialog, "تم النسخ الاحتياطي", "تم إنشاء النسخة الاحتياطية بنجاح.")
                except Exception as exc:
                    QMessageBox.critical(dialog, "فشل النسخ الاحتياطي", str(exc))

        search.textChanged.connect(refresh)
        buttons = QHBoxLayout()
        for caption, callback in (("إضافة طالب", add_record), ("تعديل المحدد", edit_record),
                                  ("حذف المحدد", delete_record), ("نسخ احتياطي", backup_database)):
            button = QPushButton(caption)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        refresh()
        dialog.exec()

    def export_clean_excel(self):
        if not self.current_data: return
        path, _ = QFileDialog.getSaveFileName(self, "تصدير ملف الإكسيل المصحح", "StudentLedger_Clean.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        cols = ['م'] + self.current_data['columns'] + ['ملاحظات التدقيق الجنائي']
        rows = [[s['serial']] + s['cells'] + [" | ".join(s['errorNotes'])] for s in self.current_data['students']]
        try:
            pd.DataFrame(rows, columns=cols).to_excel(path, index=False)
            QMessageBox.information(self, "تم التصدير", "تم تصدير ملف الإكسيل بنجاح!")
        except Exception as exc:
            QMessageBox.critical(self, "فشل التصدير", f"تعذر حفظ ملف Excel:\\n{exc}")

    def print_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "تصدير السجل كملف PDF رسمي", "StudentLedger_A4.pdf", "PDF Files (*.pdf)")
        if not path: return
        def on_pdf_ready(pdf_data):
            if not pdf_data:
                QMessageBox.critical(self, "فشل الطباعة", "لم يتم إنشاء ملف PDF.")
                return
            try:
                with open(path, "wb") as pdf_file:
                    pdf_file.write(pdf_data)
                QMessageBox.information(self, "تم الحفظ", "تم حفظ ملف PDF بنجاح.")
            except OSError as exc:
                QMessageBox.critical(self, "فشل الحفظ", f"تعذر حفظ ملف PDF:\\n{exc}")

        self.browser.page().printToPdf(on_pdf_ready)

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

        /* Phase 2: clearer Arabic interface and responsive controls */
        body {{ background: #eef2f7; color: #243247; }}
        .controls-panel {{
            background: #ffffff; border: 1px solid #dbe3ed; border-radius: 14px;
            box-shadow: 0 8px 28px rgba(31, 48, 73, .09); padding: 20px;
        }}
        .app-header {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 12px; padding: 2px 2px 16px; margin-bottom: 16px;
            border-bottom: 1px solid #e8edf3;
        }}
        .app-brand {{ display: flex; flex-direction: column; gap: 4px; }}
        .app-brand h1 {{ margin: 0; color: #183b63; font-size: 21px; }}
        .app-brand p {{ margin: 0; color: #718096; font-size: 12px; }}
        .app-version {{
            background: #eaf2fb; color: #245b91; border: 1px solid #d5e5f5;
            padding: 6px 10px; border-radius: 20px; font-size: 11px; font-weight: bold;
            white-space: nowrap;
        }}
        .controls-grid {{ gap: 14px; }}
        .control-item {{ min-width: 0; }}
        label {{ color: #34445b; font-size: 12px; margin-bottom: 2px; }}
        input:not([type="checkbox"]), select, button.custom-file-btn {{
            min-height: 40px; width: 100%; background: #fff; border: 1px solid #cbd5e1;
            border-radius: 8px; color: #26364b; transition: border-color .15s, box-shadow .15s;
        }}
        input:focus, select:focus {{
            border-color: #3982c8; box-shadow: 0 0 0 3px rgba(57,130,200,.13);
        }}
        button.custom-file-btn {{ background: #1769aa !important; border: 0; }}
        button.custom-file-btn:hover {{ background: #12578e !important; }}
        .assistant-card {{
            background: #fff; border-radius: 10px; padding: 11px 13px;
            box-shadow: 0 2px 7px rgba(31,48,73,.05); transition: transform .15s, box-shadow .15s;
        }}
        .assistant-card:hover {{ transform: translateY(-2px); box-shadow: 0 5px 13px rgba(31,48,73,.10); }}
        .actions-bar {{ gap: 10px; }}
        .btn {{ min-height: 38px; border-radius: 8px; padding: 9px 15px; }}
        #pagesContainer {{ width: 100%; overflow-x: auto; padding-bottom: 12px; }}
        .page-sheet {{ border: 1px solid #e0e6ee; border-radius: 3px; }}

        @media screen and (max-width: 760px) {{
            body {{ padding: 8px; }}
            .controls-panel {{ padding: 13px; border-radius: 11px; }}
            .app-header {{ align-items: flex-start; }}
            .app-brand h1 {{ font-size: 18px; }}
            .controls-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
            .control-item {{ min-width: 0; }}
            .assistant-cards-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .actions-bar {{ justify-content: flex-start; }}
            .btn {{ flex: 1 1 135px; justify-content: center; }}
            #pagesContainer {{ align-items: flex-start; }}
            .page-sheet {{ min-width: 900px; }}
        }}
        @media screen and (max-width: 390px) {{
            .controls-grid {{ grid-template-columns: 1fr; }}
            .assistant-cards-grid {{ grid-template-columns: 1fr 1fr; }}
            .app-version {{ font-size: 10px; padding: 5px 7px; }}
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
    <header class="app-header">
        <div class="app-brand">
            <h1>StudentLedgerPro</h1>
            <p>منظومة سجل قيد الطلاب والتدقيق الذكي</p>
        </div>
        <span class="app-version">الإصدار المكتبي</span>
    </header>
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
            <button class="btn btn-success" id="btnPrint" onclick="pyBridge.requestPrint()" disabled><span>🖨️</span> طباعة / تصدير PDF</button>
            <button class="btn btn-primary" id="btnExportExcel" onclick="pyBridge.requestExportExcel('')" disabled><span>📊</span> تصدير إكسيل مُنظف</button>
            <button class="btn" id="btnDatabase" onclick="pyBridge.requestDatabaseManager()"><span>🗄️</span> قاعدة بيانات الطلاب</button>
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

    function loadDynamicDataFromPython(data) {{
        globalData = data;
        document.getElementById('titleInput').value = data.title;
        document.getElementById('btnPrint').disabled = false;
        document.getElementById('btnExportExcel').disabled = false;
        updateCards();
        renderDynamicLedger();
    }}

    function escapeHtml(value) {{
        return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
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

        const title = escapeHtml(toArabicDigits(document.getElementById('titleInput').value));
        const query = document.getElementById('searchInput').value.trim().toLowerCase();
        const rowsPerPage = parseInt(document.getElementById('rowsPerPageInput').value, 10) || 10;
        const colsPerPage = parseInt(document.getElementById('colsPerPageInput').value, 10) || 10;
        const serialMode = document.getElementById('serialModeSelect').value;
        const startBlank = document.getElementById('blankFirstPageCheck').checked;

        let filtered = globalData.students.filter(s => {{
            const matchQ = !query || s.name.toLowerCase().includes(query) || s.code.includes(query) || s.nationalId.includes(query);
            let matchF = true;
            if (activeErrorFilter === 'nid_error') matchF = s.hasNidError;
            else if (activeErrorFilter === 'biometric') matchF = s.hasBiometricError;
            else if (activeErrorFilter === 'military') matchF = (s.hasMilitaryError || s.isCriticalMilitary);
            else if (activeErrorFilter === 'seating_gaps') matchF = s.hasSeatingError;
            else if (activeErrorFilter === 'expat') matchF = s.isExpat;
            return matchQ && matchF;
        }});

        if (filtered.length === 0) {{
            container.innerHTML = '<div style="color:#fff; padding:30px;">لا توجد نتائج تطابق خيار الفرز.</div>';
            return;
        }}

        if (startBlank) {{
            const blank = document.createElement('div');
            blank.className = 'page-sheet blank-start-page';
            blank.innerHTML = '<div class="no-print" style="margin:auto; text-align:center; color:#777; border:2px dashed #aaa; padding:40px; border-radius:8px;">📄 <strong>صفحة بداية فارغة لضبط التقابل الدفتري وجه وظهر</strong></div>';
            container.appendChild(blank);
        }}

        const allColumns = globalData.columns;
        const totalColChunks = Math.ceil(allColumns.length / colsPerPage);
        const totalRowChunks = Math.ceil(filtered.length / rowsPerPage);
        let pageCounter = 1;
        const totalPages = totalRowChunks * totalColChunks;

        for (let rChunk = 0; rChunk < totalRowChunks; rChunk++) {{
            const studentSlice = filtered.slice(rChunk * rowsPerPage, (rChunk + 1) * rowsPerPage);
            for (let cChunk = 0; cChunk < totalColChunks; cChunk++) {{
                const colSlice = allColumns.slice(cChunk * colsPerPage, (cChunk + 1) * colsPerPage);
                const colStartIndex = cChunk * colsPerPage;
                const pageSheet = document.createElement('div');
                pageSheet.className = 'page-sheet';

                const partLabel = (totalColChunks > 1) ? ` (الجزء ${{toArabicDigits(cChunk + 1)}} من ${{toArabicDigits(totalColChunks)}})` : '';
                pageSheet.innerHTML = `
                    <div class="page-header">
                        <span class="page-tag">سجل ديناميكي</span>
                        <div class="page-title">${{title}} ${{partLabel}}</div>
                        <span class="page-tag">صفحة: ${{toArabicDigits(pageCounter)}} من ${{toArabicDigits(totalPages)}}</span>
                    </div>
                `;

                const table = document.createElement('table');
                table.className = 'ledger-table';
                let theadHtml = `<thead><tr><th style="width: 4.5%;">م</th>`;
                colSlice.forEach(colName => {{ theadHtml += `<th>${{escapeHtml(colName)}}</th>`; }});
                theadHtml += `</tr></thead>`;

                let tbodyHtml = `<tbody>`;
                studentSlice.forEach((s, idx) => {{
                    let serialNum = (serialMode === 'smart_continuous') ? ((rChunk * rowsPerPage) + idx + 1) : (idx + 1);
                    const badge = (s.errorNotes && s.errorNotes.length > 0 && cChunk === 0) ? `<span class="screen-error-badge">⚠️</span>` : '';
                    tbodyHtml += `<tr><td style="font-weight:bold;">${{toArabicDigits(serialNum)}}</td>`;

                    for (let c = 0; c < colSlice.length; c++) {{
                        const cellVal = s.cells[colStartIndex + c] || '';
                        let cellClass = '';
                        if (s.hasNidError && (colStartIndex + c) === globalData.classified_fields['nationalId']) cellClass = 'cell-has-danger';
                        if (s.hasSeatingError && (colStartIndex + c) === globalData.classified_fields['seatingNo']) cellClass = 'cell-has-danger';
                        if (s.hasMilitaryError && (colStartIndex + c) === globalData.classified_fields['militaryStatus']) cellClass = 'cell-has-error';

                        const isNameCol = ((colStartIndex + c) === globalData.classified_fields['name']);
                        const alignStyle = isNameCol ? 'text-align:right; font-weight:bold; padding-right:5px;' : '';
                        tbodyHtml += `<td class="${{cellClass}}" style="${{alignStyle}}">${{isNameCol ? badge : ''}}${{escapeHtml(toArabicDigits(cellVal))}}</td>`;
                    }}
                    tbodyHtml += `</tr>`;
                }});
                tbodyHtml += `</tbody>`;

                table.innerHTML = theadHtml + tbodyHtml;
                pageSheet.appendChild(table);
                container.appendChild(pageSheet);
                pageCounter++;
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
