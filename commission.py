import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QGridLayout,
    QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QSpinBox, QDateEdit
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont



# ===================== 常量：人员列表（在这里增删改人员）=====================
PERSON = ["姓名", "牙粉", "漱口水", "牙套清洁液", "洁牙机头","指尖采血", "美团89","美团69","美团喷砂149", "抖音89", "抖音69", "抖音喷砂149", "未收费洁牙"]
# ==========================================================================

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
        self.setGeometry(100, 100, 900, 600)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧导航栏
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(150)
        self.nav_list.addItems(["日历录入", "统计页面"])
        main_layout.addWidget(self.nav_list)

        # 右侧页面切换区域
        self.stacked_widget = QStackedWidget()
        self.page1 = CalendarPage()  # 日历页面
        self.page2 = StatsPage()  # 统计页面
        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)
        main_layout.addWidget(self.stacked_widget)

        # 导航切换
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)


# 第一页：日历选择页面
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 年份 月份选择
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

        # 2. 刷新日历按钮
        refresh_btn = QPushButton("刷新日历")
        refresh_btn.clicked.connect(self.show_calendar)
        layout.addWidget(refresh_btn)

        # 3. 日历网格（日期按钮）
        self.calendar_grid = QGridLayout()
        layout.addLayout(self.calendar_grid)

        # 初始化显示当月日历
        self.show_calendar()

    # 显示日历
    def show_calendar(self):
        # 清空旧日历
        while self.calendar_grid.count() > 0:
            child = self.calendar_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        year = self.year_spin.value()
        month = self.month_spin.value()

        # 获取当月第一天和天数
        first_day = QDate(year, month, 1)
        days_in_month = first_day.daysInMonth()

        row, col = 0, 0
        for day in range(1, days_in_month + 1):
            btn = QPushButton(str(day))
            btn.setMinimumHeight(60)
            btn.setFont(QFont("微软雅黑", 12))
            # 点击日期 → 弹出对话框
            btn.clicked.connect(lambda checked, d=day: self.open_add_dialog(year, month, d))
            self.calendar_grid.addWidget(btn, row, col)
            col += 1
            if col == 7:
                col = 0
                row += 1

    # 打开新增数据对话框
    def open_add_dialog(self, year, month, day):
        dialog = AddDataDialog(year, month, day)
        dialog.exec()


# 新增数据对话框
class AddDataDialog(QDialog):
    def __init__(self, year, month, day):
        super().__init__()
        self.setWindowTitle(f"新增提成数据 - {year}年{month}月{day}日")
        self.setFixedSize(420, 360)

        # 存储每个人对应的输入框
        self.edit_dict = {}
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        for idx, name in enumerate(PERSON):
            edit = QLineEdit()
            # 第一个人提示可填可不填
            if idx == 0:
                edit.setPlaceholderText("可填内容，无限制")
            else:
                edit.setPlaceholderText("必须输入正整数")
            self.edit_dict[name] = edit
            layout.addRow(f"{name}：", edit)

        add_btn = QPushButton("增加数据")
        add_btn.clicked.connect(self.save_data)
        layout.addRow(add_btn)
        self.setLayout(layout)

    def save_data(self):
        # 取出所有人的数据
        data = {}
        for name, edit in self.edit_dict.items():
            val = edit.text().strip()
            data[name] = val

        QMessageBox.information(self, "成功", "所有人员数据已保存！")
        self.close()


# ============================================================================

    def save_data(self):
        # ========== 正整数校验核心逻辑 ==========
        data = {}
        # 遍历校验
        for idx, (name, edit) in enumerate(self.edit_dict.items()):
            text = edit.text().strip()

            # ===================== 核心规则 =====================
            # 第一项：不校验，直接存
            if idx == 0:
                data[name] = text
                continue

            # 从第二项开始：必须是正整数
            # 1. 不能为空
            if not text:
                QMessageBox.warning(self, "输入错误", f"{name} 不能为空！")
                return

            # 2. 必须是数字
            if not text.isdigit():
                QMessageBox.warning(self, "输入错误", f"{name} 必须是正整数！")
                return

            # 3. 必须大于0
            num = int(text)
            if num <= 0:
                QMessageBox.warning(self, "输入错误", f"{name} 必须大于 0！")
                return
            # ====================================================

            data[name] = num

        # 全部校验通过
        QMessageBox.information(self, "成功", "数据已保存！")
        self.accept()


# ===============================================================

# 第二页：统计页面
class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QPushButton("统计功能可扩展"))


# 运行


# 运行程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommissionApp()
    window.show()
    sys.exit(app.exec())