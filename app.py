# -*- coding: utf-8 -*-
"""
StudentLedgerPro - منظومة سجل قيد الطلاب والتدقيق الجنائي الديناميكية
All Rights Reserved (C) 2026.
"""

import sys
import os
import re
import json
import datetime
import base64
import hashlib
import ctypes
import pandas as pd
from rapidfuzz import fuzz

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QDialog,
    QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QInputDialog, QComboBox, QDialogButtonBox
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
        from excel_intelligence import load_best_sheet
        learned = {
            field: db.get_semantic_aliases(field)
            for field in ONTOLOGY_RULES
        }
        self.file_extension = os.path.splitext(file_path)[1].lower()
        self.df, self.sheet_name, self.header_row, self.detection = load_best_sheet(
            file_path, ONTOLOGY_RULES, learned
        )
        # Explicit employee corrections apply only to the same workbook extension and sheet.
        for field in ONTOLOGY_RULES:
            learned[field].update(db.get_user_mapping_corrections(
                field, self.file_extension, self.sheet_name
            ))
        self.classified_fields = {}
        self.all_columns = []

    def classify_and_audit(self):
        # Header row and worksheet are selected by the adaptive workbook scanner.
        best_row = self.header_row
        from excel_intelligence import compose_header_values, is_repeated_header_row
        header_depth = int(self.detection.get("header_depth", 1))
        raw_headers = compose_header_values(self.df, self.header_row, header_depth)
        self.all_columns = [
            {'idx': c, 'name': str(h).strip() if str(h).strip() else f"عمود_{c+1}",
             'norm': normalize_txt(str(h))}
            for c, h in enumerate(raw_headers)
        ]

        sample_df = self.df.iloc[self.header_row + header_depth : self.header_row + header_depth + 80]
        candidates = []
        for field, spec in ONTOLOGY_RULES.items():
            aliases = self.db.get_semantic_aliases(field)
            known_headers = {normalize_txt(h): 1.0 for h in spec['headers']}
            known_headers.update(aliases)
            corrections = self.db.get_user_mapping_corrections(
                field, self.file_extension, self.sheet_name
            )
            known_headers.update({normalize_txt(alias): confidence
                                  for alias, confidence in corrections.items()})
            for col in self.all_columns:
                col_idx = col['idx']
                col_name = col['norm']
                vals = sample_df.iloc[:, col_idx].dropna().apply(to_western).tolist() if col_idx < sample_df.shape[1] else []
                h_score = max([max(fuzz.ratio(col_name, kh), fuzz.partial_ratio(col_name, kh)) * weight for kh, weight in known_headers.items()] or [0])
                r_score = ((sum(1 for value in vals if re.search(spec['regex'], str(value).split('\n')[0].strip())) / max(1, len(vals))) * 100.0) if spec.get('regex') and vals else 0.0
                combined = (h_score * 0.5) + (r_score * 0.5)
                if combined >= 35.0:
                    candidates.append((combined, field, col_idx, h_score, r_score))

        # Explain every assignment and enforce one-to-one field/column mapping.
        from field_mapping_explainer import explain_assignments
        self.field_mapping_summary = explain_assignments(candidates, self.all_columns)
        self.classified_fields = {field: -1 for field in ONTOLOGY_RULES}
        learned_now = []
        for field, explanation in self.field_mapping_summary["assignments"].items():
            col_idx = explanation["column_index"]
            self.classified_fields[field] = col_idx
            # Persist only high-confidence mappings; uncertain guesses are never learned.
            if explanation["confidence"] == "high":
                header_alias = self.all_columns[col_idx]['name']
                if self.db.remember_semantic_mapping(field, header_alias, explanation["score"] / 100.0):
                    learned_now.append((field, header_alias, explanation["score"]))

        self.learning_summary = {
            "learned": len(learned_now),
            "memory": self.db.semantic_memory_stats(),
        }

        title = ""
        for r in range(min(self.header_row + 1, 10)):
            r_str = " ".join([str(x) for x in self.df.iloc[r].dropna().tolist()])
            if not title and any(k in r_str for k in ['المستوى', 'العام الجامع', 'شئون الطلاب', 'كشف قيد', 'بيان']):
                title = r_str[:50]

        students = []
        current_year = datetime.datetime.now().year
        auto_serial = 1
        seen_nids, seen_seats = {}, {}

        for r_idx in range(self.header_row + header_depth, len(self.df)):
            row = self.df.iloc[r_idx]
            row_cells = [str(row[col['idx']]).strip() if pd.notna(row[col['idx']]) else '' for col in self.all_columns]
            if not any(row_cells):
                continue
            # Repeated headings between page breaks are not student records.
            if is_repeated_header_row(row_cells, [c['name'] for c in self.all_columns], ONTOLOGY_RULES):
                continue

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
                'sourceRow': r_idx + 1,
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

        from excel_intelligence import find_duplicate_candidates
        duplicate_candidates = find_duplicate_candidates(students)
        return {
            'title': title or "سجل قيد الطلاب المعتمد",
            'columns': [c['name'] for c in self.all_columns],
            'classified_fields': self.classified_fields,
            'students': students,
            'duplicate_candidates': duplicate_candidates,
            'excel_detection': self.detection,
            'source_sheet': self.sheet_name
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

    @pyqtSlot()
    def requestAcademicReports(self):
        self.win.open_academic_reports()

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

    def open_academic_reports(self):
        from academic_reports import REPORTS, build_academic_report
        from extended_reports import REPORTS as EXTENDED_REPORTS, build_extended_report
        dialog = QDialog(self)
        dialog.setWindowTitle("التقارير الأكاديمية")
        dialog.resize(1050, 650)
        layout = QVBoxLayout(dialog)
        controls = QHBoxLayout()
        report_box = QComboBox()
        for key, title in REPORTS.items():
            report_box.addItem(title, key)
        report_box.insertSeparator(report_box.count())
        for key, title in EXTENDED_REPORTS.items():
            report_box.addItem(title, key)
        search_box = QLineEdit()
        search_box.setPlaceholderText("بحث بالاسم أو الكود أو الرقم القومي أو ملف المصدر")
        refresh_btn = QPushButton("عرض التقرير")
        controls.addWidget(report_box)
        controls.addWidget(search_box, 1)
        controls.addWidget(refresh_btn)
        layout.addLayout(controls)
        summary_label = QLabel("اختر نوع التقرير ثم اضغط عرض التقرير.")
        layout.addWidget(summary_label)
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        layout.addWidget(table, 1)
        buttons = QDialogButtonBox()
        export_btn = buttons.addButton("تصدير Excel", QDialogButtonBox.ButtonRole.ActionRole)
        close_btn = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(buttons)
        state = {"rows": [], "title": ""}
        def refresh():
            report_type = report_box.currentData()
            if report_type in REPORTS:
                title, rows, summary = build_academic_report(
                    self.student_db, report_type, search_box.text()
                )
                summary_text = (
                    "النتائج: " + str(summary["total"]) + " | وافدون: " + str(summary["expatriates"]) +
                    " | غير وافدين: " + str(summary["local"]) + " | أسماء ناقصة: " + str(summary["missing_name"]) +
                    " | أكواد ناقصة: " + str(summary["missing_code"]) + " | معرفات ناقصة: " + str(summary["missing_national_id"])
                )
            else:
                title, rows, summary = build_extended_report(
                    self.student_db, report_type, search_box.text()
                )
                summary_text = "إجمالي النتائج: " + str(summary["total"]) + " (الحد الأقصى للفحص: " + str(summary["limited_to"]) + ")"
            state["rows"], state["title"] = rows, title
            summary_label.setText(summary_text)
            headers = list(rows[0].keys()) if rows else []
            table.clear()
            table.setColumnCount(len(headers))
            table.setRowCount(len(rows))
            table.setHorizontalHeaderLabels(headers)
            for row_index, row in enumerate(rows):
                for col_index, header in enumerate(headers):
                    table.setItem(row_index, col_index, QTableWidgetItem(str(row.get(header, ""))))
            table.resizeColumnsToContents()
        def export_excel():
            if not state["rows"]:
                QMessageBox.information(dialog, "التصدير", "لا توجد بيانات لتصديرها.")
                return
            path, _ = QFileDialog.getSaveFileName(
                dialog, "حفظ التقرير", "academic_report.xlsx", "Excel (*.xlsx)"
            )
            if not path:
                return
            try:
                import pandas as pd
                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    pd.DataFrame(state["rows"]).to_excel(writer, index=False, sheet_name="التقرير")
                QMessageBox.information(dialog, "تم التصدير", f"تم حفظ التقرير في:\\n{path}")
            except Exception as exc:
                QMessageBox.critical(dialog, "خطأ التصدير", str(exc))
        refresh_btn.clicked.connect(refresh)
        search_box.returnPressed.connect(refresh)
        export_btn.clicked.connect(export_excel)
        close_btn.clicked.connect(dialog.accept)
        refresh()
        dialog.exec()


    def open_excel_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "📂 اختر ملفاً أو عدة ملفات Excel", "",
            "Excel Files (*.xlsx *.xls)"
        )
        if not file_paths:
            return
        if not self._can_edit():
            QMessageBox.warning(self, "صلاحية غير كافية",
                                "استيراد الملفات متاح للمدير والمحرر فقط.")
            return
        try:
            from excel_import_pipeline import prepare_import_preview, select_preview_rows
            from workbook_linker import analyze_workbooks

            workbook_results = []
            processors = []
            failures = []
            for file_path in file_paths:
                try:
                    processor = DynamicExcelProcessor(file_path, self.student_db)
                    result = processor.classify_and_audit()
                    if not result.get("students"):
                        failures.append(f"{os.path.basename(file_path)}: لا توجد سجلات طلاب")
                        continue
                    processors.append(processor)
                    headers = [column.get("name", "") for column in processor.all_columns]
                    profile_hints = self.student_db.find_similar_workbook_profiles(
                        os.path.splitext(file_path)[1], headers
                    )
                    workbook_results.append({
                        "file": os.path.basename(file_path),
                        "sheet": processor.sheet_name,
                        "students": result.get("students", []),
                        "result": result,
                        "headers": headers,
                        "profile_hints": profile_hints,
                        "mapping_summary": processor.field_mapping_summary,
                    })
                except Exception as file_exc:
                    failures.append(f"{os.path.basename(file_path)}: {file_exc}")

            if not workbook_results:
                QMessageBox.warning(self, "تعذر الاستيراد",
                                    "لم يتم العثور على ملفات صالحة.\\n" + "\\n".join(failures))
                return

            linking = analyze_workbooks(workbook_results)
            from workbook_audit import audit_workbooks
            audit = audit_workbooks(workbook_results)
            all_students = []
            for book in workbook_results:
                for student in book["students"]:
                    row = dict(student)
                    row["sourceFile"] = book["file"]
                    row["sourceSheet"] = book["sheet"]
                    all_students.append(row)

            preview = prepare_import_preview(
                all_students, source_file="MULTI-WORKBOOK",
                source_sheet="متعدد الأوراق والملفات"
            )
            academic_period, period_ok = QInputDialog.getText(
                self, "الفترة الدراسية",
                "أدخل العام أو الفترة الدراسية لحفظ سجل تاريخي (مثال: 2026/2027)\\n"
                "اتركه فارغاً لتخطي التتبع التاريخي:",
            )
            if not period_ok:
                academic_period = ""
            history_findings = (
                self.student_db.compare_student_history(all_students, academic_period)
                if academic_period.strip() else []
            )
            reference_comparison = None
            available_periods = self.student_db.list_history_periods()
            if available_periods:
                reference_period, reference_ok = QInputDialog.getItem(
                    self, "مقارنة بكشف مرجعي",
                    "اختر فترة محفوظة للمقارنة أو تخطَّ المقارنة:",
                    ["تخطي المقارنة"] + available_periods, 0, False
                )
                if reference_ok and reference_period != "تخطي المقارنة":
                    reference_comparison = self.student_db.compare_with_reference_roster(
                        all_students, reference_period
                    )
            answer_text = (
                f"عدد الملفات المقروءة: {len(workbook_results)}\\n"
                f"عدد السجلات: {preview['row_count']}\\n"
                f"مجموعات الربط بين الملفات: {linking['match_group_count']}\\n"
                f"مجموعات بها تعارضات: {linking['conflict_count']}\\n"
                f"سجلات تحتاج مراجعة حقول أساسية: {preview['warning_count']}\\n"
                f"أنماط ملفات سابقة متشابهة: {sum(1 for book in workbook_results if book['profile_hints'] and book['profile_hints'][0]['similarity'] >= 0.5)}\\n"
                f"تعيينات أعمدة تحتاج مراجعة: {sum(book['mapping_summary']['review_count'] for book in workbook_results)}\\n"
                f"نتائج التدقيق: أخطاء {audit['severity_counts']['error']}، تحذيرات {audit['severity_counts']['warning']}، ملاحظات {audit['severity_counts']['info']}\\n"
                f"تغيرات تاريخية مكتشفة: {len(history_findings)}\\n"
                + (f"مقارنة مع {reference_comparison['reference_period']}: "
                   f"مستجدون {len(reference_comparison['new_students'])}، "
                   f"مفقودون {len(reference_comparison['missing_students'])}، "
                   f"تغيرات {len(reference_comparison['changed_students'])}\\n"
                   if reference_comparison else "")
                + "\\n"
                "المطابقة تعتمد على كود الطالب أو الرقم القومي بعد توحيد الأرقام.\\n"
                "لن يتم دمج السجلات أو حذفها تلقائياً.\\n"
            )
            mapping_lines = []
            for book in workbook_results:
                for field, detail in book["mapping_summary"]["assignments"].items():
                    if detail["review_required"]:
                        mapping_lines.append(
                            f"{book['file']} — {field}: {detail['header']} "
                            f"({detail['confidence']} / {detail['score']:.0f}%) — {detail['reason']}"
                        )
            if mapping_lines:
                answer_text += "\\n\\nتعيينات تحتاج مراجعة:\\n" + "\\n".join(mapping_lines[:12])
            audit_lines = [
                f"{item['severity'].upper()}: {item['message']} — " +
                ", ".join(f"{source['file']} / {source['sheet']} / صف {source['row']}"
                          for source in item["sources"][:4])
                for item in audit["findings"] if item["severity"] in ("error", "warning")
            ]
            if audit_lines:
                answer_text += "\\n\\nنتائج التدقيق التي تستحق المراجعة:\\n" + "\\n".join(audit_lines[:15])
            history_lines = [
                f"{item['message']}: {item['old_value']} ← {item['new_value']} "
                f"(الفترة السابقة: {item['previous_period']}، المصدر: {item['source_file']})"
                for item in history_findings
            ]
            if history_lines:
                answer_text += "\\n\\nتغيرات مقارنة بالفترات السابقة:\\n" + "\\n".join(history_lines[:12])
            if reference_comparison:
                sections = [
                    ("طلاب مستجدون", "new_students", lambda x: f"{x.get('name','')} / كود {x.get('code','')}"),
                    ("طلاب غير موجودين في الكشف الحالي", "missing_students", lambda x: f"{x.get('name','')} / كود {x.get('code','')} — {x.get('source_file','')}"),
                    ("طلاب تغيرت بياناتهم", "changed_students", lambda x: f"{x.get('old_name','')} ← {x.get('new_name','')}، الكود {x.get('old_code','')} ← {x.get('new_code','')}"),
                ]
                for heading, key, formatter in sections:
                    entries = reference_comparison[key]
                    answer_text += f"\\n\\n{heading} ({len(entries)}):\\n"
                    answer_text += "\\n".join(formatter(x) for x in entries[:10]) or "لا يوجد"
            if failures:
                answer_text += "\\nملفات لم تُقرأ بالكامل:\\n" + "\\n".join(failures[:8])
            answer_text += "\\nهل تريد اعتماد استيراد السجلات المكتشفة؟"
            answer = QMessageBox.question(
                self, "تحليل وربط عدة ملفات Excel", answer_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                QMessageBox.information(self, "تم إلغاء الاستيراد",
                                        "لم يتم حفظ أي سجل في قاعدة البيانات.")
                return

            # Offer explicit, contextual correction learning for uncertain mappings.
            learned_corrections = 0
            for book in workbook_results:
                headers = list(dict.fromkeys(h for h in book["headers"] if h))
                for field, detail in book["mapping_summary"]["assignments"].items():
                    if not detail["review_required"] or not headers:
                        continue
                    choices = headers + ["عدم حفظ تصحيح"]
                    default = detail["header"] if detail["header"] in choices else choices[0]
                    selected_header, accepted = QInputDialog.getItem(
                        self, "تصحيح تعيين عمود",
                        f"اختر العنوان الصحيح للحقل ({field}) في الملف {book['file']}\\n"
                        "سيُستخدم التصحيح في الملفات القادمة المطابقة لهذا النوع والورقة.",
                        choices, choices.index(default), False
                    )
                    if accepted and selected_header != "عدم حفظ تصحيح":
                        if self.student_db.remember_user_mapping_correction(
                            field, selected_header, os.path.splitext(book["file"])[1],
                            book["sheet"], self.current_user["username"]
                        ):
                            learned_corrections += 1
                            self.student_db.log_activity(
                                self.current_user["username"], "MAPPING_CORRECTION",
                                f"{book['file']} | {field} -> {selected_header}"
                            )

            approved = select_preview_rows(preview, range(preview["row_count"]))
            self.current_data = workbook_results[0]["result"]
            imported = 0
            import_errors = []
            for book in workbook_results:
                batch = [student for student in approved
                         if student.get("sourceFile") == book["file"]]
                try:
                    if batch:
                        batch_id = self.student_db.import_students(batch, book["file"])
                        if academic_period.strip():
                            self.student_db.record_student_history(
                                batch, academic_period.strip(), book["file"], batch_id
                            )
                        self.student_db.log_activity(
                            self.current_user["username"], "IMPORT_BATCH", book["file"]
                        )
                        self.student_db.remember_workbook_profile(
                            os.path.splitext(book["file"])[1], book["sheet"], book["headers"]
                        )
                        imported += len(batch)
                except Exception as db_exc:
                    import_errors.append(f"{book['file']}: {db_exc}")

            learned_relationships = 0
            if imported > 0:
                for group in linking["match_groups"]:
                    sheet_names = sorted({source["sheet"] for source in group["sources"] if source["sheet"]})
                    for left_index in range(len(sheet_names)):
                        for right_index in range(left_index + 1, len(sheet_names)):
                            if self.student_db.remember_confirmed_relationship(
                                sheet_names[left_index], sheet_names[right_index]
                            ):
                                learned_relationships += 1
            memory_stats = self.student_db.workbook_learning_stats()
            summary = (
                f"الملفات المقروءة: {len(workbook_results)}\\n"
                f"السجلات التي تم إرسالها للحفظ: {imported}\\n"
                f"مجموعات المطابقة: {linking['match_group_count']}\\n"
                f"التعارضات التي تحتاج مراجعة: {linking['conflict_count']}\\n"
                f"علاقات الأوراق التي تم تأكيدها: {learned_relationships}\\n"
                f"أنماط الملفات المحفوظة: {memory_stats['profiles']}\\n"
                f"تأكيدات الاستيراد المتراكمة: {memory_stats['confirmations']}\\n"
                f"تصحيحات الأعمدة التي تم تعلمها: {learned_corrections}\\n"
                f"إجمالي التصحيحات المحفوظة: {self.student_db.mapping_correction_stats()['corrections']}\\n"
                f"السجلات المضافة للسجل التاريخي: {sum(1 for student in approved if academic_period.strip() and (self.student_db._history_normalize(student.get('nationalId')) or self.student_db._history_normalize(student.get('code'))))}\\n"
                f"الفترة الدراسية: {academic_period.strip() or 'غير محددة'}\\n"
                f"ملفات تعذر حفظها: {len(import_errors)}"
            )
            if import_errors:
                summary += "\\n" + "\\n".join(import_errors[:5])
            QMessageBox.information(self, "نتيجة الاستيراد متعدد الملفات", summary)
            payload = json.dumps(self.current_data, ensure_ascii=False).replace("</", "<\\/")
            self.browser.page().runJavaScript(f"loadDynamicDataFromPython({payload});")
        except Exception as exc:
            QMessageBox.critical(self, "تعذر تحليل ملفات Excel",
                                 f"حدث خطأ أثناء معالجة الملفات:\\n{exc}")

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
            if not self._can_edit():
                QMessageBox.warning(dialog, "صلاحية غير كافية", "لا تملك صلاحية إضافة السجلات.")
                return
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
                self.student_db.log_activity(self.current_user["username"], "ADD_STUDENT", code)
                refresh()
            except Exception as exc:
                QMessageBox.critical(dialog, "تعذر الإضافة", str(exc))

        def edit_record():
            if not self._can_edit():
                QMessageBox.warning(dialog, "صلاحية غير كافية", "لا تملك صلاحية تعديل السجلات.")
                return
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
                self.student_db.log_activity(self.current_user["username"], "EDIT_STUDENT", str(student_id))
                refresh()
            except Exception as exc:
                QMessageBox.critical(dialog, "تعذر التعديل", str(exc))

        def delete_record():
            if self.current_user["role"] != "admin":
                QMessageBox.warning(dialog, "صلاحية غير كافية", "حذف السجلات متاح للمدير فقط.")
                return
            student_id = selected_id()
            if student_id is None:
                return
            answer = QMessageBox.question(dialog, "تأكيد الحذف",
                                          "هل تريد حذف الطالب المحدد نهائياً؟")
            if answer == QMessageBox.StandardButton.Yes:
                self.student_db.delete_student(student_id)
                self.student_db.log_activity(self.current_user["username"], "DELETE_STUDENT", str(student_id))
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
        actions = []
        if self._can_edit():
            actions.extend((("إضافة طالب", add_record), ("تعديل المحدد", edit_record)))
        if self.current_user["role"] == "admin":
            actions.append(("حذف المحدد", delete_record))
        actions.append(("نسخ احتياطي", backup_database))
        for caption, callback in actions:
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
            <button class="btn btn-primary" id="btnAcademicReports" onclick="pyBridge.requestAcademicReports()"><span>📊</span> التقارير الأكاديمية</button>
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
