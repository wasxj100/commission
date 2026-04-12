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

# ===================== 你的常量列表（自动生成数据库字段）=====================
PERSON = ["姓名", "牙粉", "漱口水", "牙套清洁液", "洁牙机头",
          "指尖采血", "美团89", "美团69", "美团喷砂149",
          "抖音89", "抖音69", "抖音喷砂149", "未收费洁牙"]
# ============================================================================

# ===================== SQLite3 数据库操作 =====================
def init_db():
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()

    # 动态生成字段：id, date, + PERSON 所有项
    fields = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "date TEXT NOT NULL UNIQUE"]
    for item in PERSON:
        fields.append(f"{item} TEXT")

    sql = f'''CREATE TABLE IF NOT EXISTS records (
        {",".join(fields)}
    )'''
    cursor.execute(sql)
    conn.commit()
    conn.close()

# 保存数据
def save_record(date_str, data_dict):
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()

    keys = list(data_dict.keys())
    values = list(data_dict.values())
    placeholders = ",".join(["?"] * len(keys))
    columns = ",".join(keys)

    # 存在则更新，不存在则插入
    cursor.execute(f"REPLACE INTO records (date, {columns}) VALUES (?, {placeholders})",
                   [date_str] + values)
    conn.commit()
    conn.close()

# 读取某天数据
def get_record(date_str):
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records WHERE date=?", (date_str,))
    row = cursor.fetchone()
    conn.close()
    return row

# ==============================================================

# 主窗口
class CommissionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("提成计算系统")
        self.setGeometry(100, 100, 950, 650)
        init_db()  # 初始化数据库

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧导航
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(160)
        self.nav_list.addItems(["日历录入", "统计页面"])
        main_layout.addWidget(self.nav_list)

        # 右侧页面
        self.stacked_widget = QStackedWidget()
        self.page1 = CalendarPage()
        self.page2 = StatsPage()
        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)
        main_layout.addWidget(self.stacked_widget)

        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

# 日历页面
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 年月选择
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

        # 刷新按钮
        refresh_btn = QPushButton("刷新日历")
        refresh_btn.clicked.connect(self.show_calendar)
        layout.addWidget(refresh_btn)

        # 日历网格
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
        first_day = QDate(year, month, 1)
        days_in_month = first_day.daysInMonth()

        row, col = 0, 0
        for day in range(1, days_in_month + 1):
            btn = QPushButton(str(day))
            btn.setMinimumHeight(60)
            btn.setFont(QFont("微软雅黑", 12))
            btn.clicked.connect(lambda checked, d=day: self.open_add_dialog(year, month, d))
            self.calendar_grid.addWidget(btn, row, col)
            col += 1
            if col == 7:
                col = 0
                row += 1

    def open_add_dialog(self, year, month, day):
        date_str = f"{year}-{month:02d}-{day:02d}"
        dialog = AddDataDialog(date_str)
        dialog.exec()

# ===================== 新增数据对话框（自动加载 + 保存）=====================
class AddDataDialog(QDialog):
    def __init__(self, date_str):
        super().__init__()
        self.date_str = date_str
        self.setWindowTitle(f"录入数据 - {date_str}")
        self.setFixedSize(520, 580)
        self.edit_dict = {}
        self.init_ui()
        self.load_data()  # 自动加载当天已保存数据

    def init_ui(self):
        layout = QFormLayout(self)
        for idx, name in enumerate(PERSON):
            edit = QLineEdit()
            if idx == 0:
                edit.setPlaceholderText("可填写姓名/客户信息")
            else:
                edit.setPlaceholderText("必须输入正整数")
            self.edit_dict[name] = edit
            layout.addRow(f"{name}：", edit)

        add_btn = QPushButton("保存数据")
        add_btn.clicked.connect(self.save_data)
        layout.addRow(add_btn)
        self.setLayout(layout)

    # 加载当天已保存的数据
    def load_data(self):
        record = get_record(self.date_str)
        if not record:
            return
        # 数据库字段顺序：id, date, 字段1, 字段2...
        for i, name in enumerate(PERSON):
            value = record[i + 2] or ""
            self.edit_dict[name].setText(str(value))

    # 保存并校验
    def save_data(self):
        data = {}
        for idx, (name, edit) in enumerate(self.edit_dict.items()):
            text = edit.text().strip()

            # 第一项：姓名，不校验
            if idx == 0:
                data[name] = text
                continue

            # 从第二项开始：必须正整数
            if not text:
                QMessageBox.warning(self, "错误", f"{name} 不能为空！")
                return
            if not text.isdigit():
                QMessageBox.warning(self, "错误", f"{name} 必须是正整数！")
                return
            num = int(text)
            if num <= 0:
                QMessageBox.warning(self, "错误", f"{name} 必须大于0！")
                return
            data[name] = text

        # 保存到数据库
        save_record(self.date_str, data)
        QMessageBox.information(self, "成功", "数据已永久保存！")
        self.accept()

# ========================================================================

# 统计页面
class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QPushButton("统计功能可扩展：按月汇总/导出Excel"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommissionApp()
    window.show()
    sys.exit(app.exec())