import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QGridLayout,
    QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QSpinBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QFont

# ===================== 【中文显示名】 ↔ 【英文字段名】 映射 =====================
FIELD_MAP = [
    ("姓名", "name"),
    ("牙粉", "p1"),
    ("漱口水", "p2"),
    ("牙套清洁液", "p3"),
    ("洁牙机头", "p4"),
    ("指尖采血", "p5"),
    ("美团89", "m1"),
    ("美团69", "m2"),
    ("美团喷砂149", "m3"),
    ("抖音89", "d1"),
    ("抖音69", "d2"),
    ("抖音喷砂149", "d3"),
    ("未收费洁牙", "free"),
]

# 自动提取
CHINESE_NAMES = [item[0] for item in FIELD_MAP]  # 界面显示用
ENGLISH_FIELDS = [item[1] for item in FIELD_MAP]  # 数据库字段用
# ================================================================================

# ===================== SQLite 数据库（全英文字段） =====================
def init_db():
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()

    fields = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "date TEXT NOT NULL"]
    for field in ENGLISH_FIELDS:
        fields.append(f"{field} TEXT")

    sql = f'''CREATE TABLE IF NOT EXISTS records (
        {",".join(fields)}
    )'''
    cursor.execute(sql)
    conn.commit()
    conn.close()

# 查询：日期 + 姓名 是否存在
def get_existing_id(date_str, name):
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM records WHERE date=? AND name=?", (date_str, name))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

# 保存/更新
def save_or_update(date_str, data_dict):
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()
    name = data_dict["name"]
    record_id = get_existing_id(date_str, name)

    if record_id:
        # 更新
        update_items = [f"{k}=?" for k in data_dict.keys()]
        sql = f"UPDATE records SET {','.join(update_items)} WHERE id=?"
        values = list(data_dict.values()) + [record_id]
        cursor.execute(sql, values)
    else:
        # 新增
        cols = ",".join(data_dict.keys())
        placeholders = ",".join(["?"] * len(data_dict))
        sql = f"INSERT INTO records (date, {cols}) VALUES (?, {placeholders})"
        cursor.execute(sql, [date_str] + list(data_dict.values()))

    conn.commit()
    conn.close()

# ======================================================================

# 主窗口
class CommissionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("提成计算系统")
        self.setGeometry(100, 100, 950, 650)
        init_db()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(160)
        self.nav_list.addItems(["日历录入", "统计页面"])
        main_layout.addWidget(self.nav_list)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(CalendarPage())
        self.stacked_widget.addWidget(StatsPage())
        main_layout.addWidget(self.stacked_widget)

        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

# 日历页面
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        date_layout = QHBoxLayout()

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(QDate.currentDate().year())

        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(QDate.currentDate().month())

        date_layout.addWidget(self.year_spin)
        date_layout.addWidget(self.month_spin)
        layout.addLayout(date_layout)

        refresh_btn = QPushButton("刷新日历")
        refresh_btn.clicked.connect(self.show_calendar)
        layout.addWidget(refresh_btn)

        self.calendar_grid = QGridLayout()
        layout.addLayout(self.calendar_grid)
        self.show_calendar()

    def show_calendar(self):
        while self.calendar_grid.count() > 0:
            child = self.calendar_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        year = self.year_spin.value()
        month = self.month_spin.value()
        days = QDate(year, month, 1).daysInMonth()

        row, col = 0, 0
        for day in range(1, days + 1):
            btn = QPushButton(str(day))
            btn.setMinimumHeight(60)
            btn.setFont(QFont("微软雅黑", 12))
            btn.clicked.connect(lambda checked, d=day: self.open_dialog(year, month, d))
            self.calendar_grid.addWidget(btn, row, col)
            col += 1
            if col == 7:
                col = 0
                row += 1

    def open_dialog(self, year, month, day):
        date_str = f"{year}-{month:02d}-{day:02d}"
        dialog = AddDataDialog(date_str)
        dialog.exec()

# ===================== 录入对话框（中文显示，英文字段存储） =====================
class AddDataDialog(QDialog):
    def __init__(self, date_str):
        super().__init__()
        self.date_str = date_str
        self.setWindowTitle(f"录入数据 - {date_str}")
        self.setFixedSize(520, 580)
        self.edit_widgets = {}  # 存储输入框
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        for idx, (chinese, english) in enumerate(FIELD_MAP):
            edit = QLineEdit()
            if idx == 0:
                edit.setPlaceholderText("姓名（重复则自动更新）")
            else:
                edit.setPlaceholderText("必须输入正整数")
            self.edit_widgets[english] = edit
            layout.addRow(f"{chinese}：", edit)

        save_btn = QPushButton("保存数据")
        save_btn.clicked.connect(self.save_data)
        layout.addRow(save_btn)
        self.setLayout(layout)

    def save_data(self):
        data = {}
        for idx, (chinese, english) in enumerate(FIELD_MAP):
            text = self.edit_widgets[english].text().strip()

            # 第一项：姓名，不校验
            if idx == 0:
                data[english] = text
                continue

            # 其余必须正整数
            if not text:
                QMessageBox.warning(self, "错误", f"{chinese} 不能为空！")
                return
            if not text.isdigit():
                QMessageBox.warning(self, "错误", f"{chinese} 必须是正整数！")
                return
            if int(text) <= 0:
                QMessageBox.warning(self, "错误", f"{chinese} 必须大于 0！")
                return
            data[english] = text

        # 保存到数据库
        save_or_update(self.date_str, data)
        QMessageBox.information(self, "成功", "数据已保存！")
        self.accept()

# ============================================================================

# 统计页面
class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QPushButton("统计功能可扩展"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommissionApp()
    window.show()
    sys.exit(app.exec())