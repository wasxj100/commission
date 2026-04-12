import sys
import sqlite3
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QGridLayout,
    QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import QDate, QDateTime, Qt
from PyQt6.QtGui import QFont, QTextDocument

from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

# ===================== 中文名称 ↔ 英文字段 ↔ 单价 =====================
FIELD_MAP = [
    ("姓名", "name"),
    ("拍片", "pp"),
    ("牙粉", "yf"),
    ("漱口水", "sks"),
    ("牙套清洁液", "qjy"),
    ("洁牙机头", "jyj"),
    ("指尖采血", "cx"),
    ("美团89", "m1"),
    ("美团69", "m2"),
    ("美团喷砂149", "m3"),
    ("抖音89", "d1"),
    ("抖音69", "d2"),
    ("抖音喷砂149", "d3"),
    ("未收费洁牙", "free"),
]

VALUE = [20, 5, 2, 2, 3, 5, 30, 10, 40, 30, 10, 40, 20]
CHINESE_NAMES = [item[0] for item in FIELD_MAP]
ENGLISH_FIELDS = [item[1] for item in FIELD_MAP]
# ITEM_FIELDS = FIELD_MAP[1:]


# ====================================================================

# ===================== 数据库 =====================
def init_db():
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()
    fields = [
        "id INTEGER PRIMARY KEY AUTOINCREMENT",
        "date TEXT NOT NULL",
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    ]
    for f in ENGLISH_FIELDS:
        fields.append(f"{f} INTEGER DEFAULT 0")
    sql = f'''CREATE TABLE IF NOT EXISTS records ({",".join(fields)})'''
    cursor.execute(sql)
    conn.commit()
    conn.close()


def get_existing_id(date_str, name):
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM records WHERE date=? AND name=?", (date_str, name))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None


def save_or_update(date_str, data_dict):
    conn = sqlite3.connect("commission.db")
    cursor = conn.cursor()
    record_id = get_existing_id(date_str, data_dict["name"])
    now = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
    if record_id:
        updates = [f"{k}=?" for k in data_dict]
        sql = f"UPDATE records SET {','.join(updates)}, created_at=? WHERE id=?"
        cursor.execute(sql, list(data_dict.values()) + [now, record_id])
    else:
        cols = ",".join(data_dict.keys())
        holders = ",".join(["?"] * len(data_dict))
        sql = f"INSERT INTO records (date, {cols}, created_at) VALUES (?, {holders}, ?)"
        cursor.execute(sql, [date_str] + list(data_dict.values()) + [now])
    conn.commit()
    conn.close()


def get_month_data_as_df(year, month):
    conn = sqlite3.connect("commission.db")
    date_filter = f"{year}-{month:02d}-%"
    df = pd.read_sql_query("SELECT * FROM records WHERE date LIKE ?", conn, params=[date_filter])
    conn.close()
    return df


# ======================================================

# ===================== 主窗口 =====================
class CommissionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("提成计算系统")
        self.setGeometry(100, 100, 1300, 720)
        init_db()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        self.nav = QListWidget()
        self.nav.setFixedWidth(160)
        self.nav.addItems(["日历录入", "数据查询", "数据统计"])
        main_layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.stack.addWidget(CalendarPage())
        self.stack.addWidget(DataQueryPage())
        self.stack.addWidget(StatsPage())
        main_layout.addWidget(self.stack)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)


# ===================== 日历页面 =====================
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.y = QSpinBox()
        self.y.setRange(2000, 2100)
        self.y.setValue(QDate.currentDate().year())
        self.m = QSpinBox()
        self.m.setRange(1, 12)
        self.m.setValue(QDate.currentDate().month())
        bar.addWidget(self.y)
        bar.addWidget(self.m)
        layout.addLayout(bar)

        btn = QPushButton("刷新日历")
        btn.clicked.connect(self.show)
        layout.addWidget(btn)

        self.g = QGridLayout()
        layout.addLayout(self.g)
        self.show()

    def show(self):
        while self.g.count():
            w = self.g.takeAt(0).widget()
            if w: w.deleteLater()
        y = self.y.value()
        m = self.m.value()
        days = QDate(y, m, 1).daysInMonth()
        r, c = 0, 0
        for d in range(1, days + 1):
            b = QPushButton(str(d))
            b.setMinimumHeight(60)
            b.clicked.connect(lambda _, dd=d: AddDataDialog(f"{y}-{m:02d}-{dd:02d}").exec())
            self.g.addWidget(b, r, c)
            c += 1
            if c == 7: c = 0; r += 1


# ===================== 录入对话框 =====================
class AddDataDialog(QDialog):
    def __init__(self, date_str):
        super().__init__()
        self.date = date_str
        self.setWindowTitle(f"录入 - {date_str}")
        self.setFixedSize(520, 580)
        self.widgets = {}
        layout = QFormLayout()
        for ch, en in FIELD_MAP:
            e = QLineEdit()
            self.widgets[en] = e
            layout.addRow(f"{ch}：", e)
        btn = QPushButton("保存")
        btn.clicked.connect(self.save)
        layout.addRow(btn)
        self.setLayout(layout)

    def save(self):
        name = self.widgets["name"].text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "姓名不能为空！")
            return

        data = {"name": name}
        for ch, en in FIELD_MAP[1:]:
            t = self.widgets[en].text().strip()
            data[en] = int(t) if t and t.isdigit() and int(t) > 0 else 0

        save_or_update(self.date, data)
        QMessageBox.information(self, "成功", "保存成功")
        self.accept()


# ===================== 数据查询页 =====================
class DataQueryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.y = QSpinBox()
        self.y.setRange(2000, 2100)
        self.y.setValue(QDate.currentDate().year())
        self.m = QSpinBox()
        self.m.setRange(1, 12)
        self.m.setValue(QDate.currentDate().month())
        btn = QPushButton("查询")
        btn.clicked.connect(self.query)
        bar.addWidget(self.y)
        bar.addWidget(self.m)
        bar.addWidget(btn)
        layout.addLayout(bar)

        self.table = QTableWidget()
        layout.addWidget(self.table)
        self.setLayout(layout)

    def query(self):
        df = get_month_data_as_df(self.y.value(), self.m.value())
        if df.empty:
            QMessageBox.information(self, "提示", "无数据")
            self.table.setRowCount(0)
            return

        rename_map = {"date": "日期", "created_at": "创建时间", "id": "ID"}
        for ch, en in FIELD_MAP: rename_map[en] = ch
        df = df.rename(columns=rename_map)

        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])
        self.table.setHorizontalHeaderLabels(df.columns.tolist())
        for r in range(df.shape[0]):
            for c in range(df.shape[1]):
                self.table.setItem(r, c, QTableWidgetItem(str(df.iloc[r, c])))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


# ###########################################################################
# ###################### 数据统计页 + 打印功能（修复版） ###########################
# ###########################################################################
class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.result_df = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()

        self.y = QSpinBox()
        self.y.setRange(2000, 2100)
        self.y.setValue(QDate.currentDate().year())

        self.m = QSpinBox()
        self.m.setRange(1, 12)
        self.m.setValue(QDate.currentDate().month())

        self.btn_calc = QPushButton("计算提成")
        self.btn_calc.clicked.connect(self.show_report)

        self.btn_print = QPushButton("打印报表")
        self.btn_print.clicked.connect(self.print_final)
        self.btn_print.setEnabled(False)

        bar.addWidget(self.y)
        bar.addWidget(self.m)
        bar.addWidget(self.btn_calc)
        bar.addWidget(self.btn_print)
        layout.addLayout(bar)

        self.table = QTableWidget()
        self.table.setFont(QFont("微软雅黑", 10))
        layout.addWidget(self.table)
        self.setLayout(layout)
    def show_report(self):
        year = self.y.value()
        month = self.m.value()
        df = get_month_data_as_df(year, month)
        print(df)
        if df.empty:
            QMessageBox.information(self, "提示", "当月无数据")
            self.table.setRowCount(0)
            self.btn_print.setEnabled(False)
            self.btn_print.update() # 强制刷新
            return

        # 按姓名分组求和
        df_group = df.groupby("name", as_index=False)[ENGLISH_FIELDS[1:]].sum()
        print(df_group)
        _df_group = df_group.iloc[:, 1:] * VALUE
        df_group['总提成'] = _df_group.sum(axis=1)
        self.result_df = df_group
        # 显示中文表头
        mapping = dict(zip(ENGLISH_FIELDS, CHINESE_NAMES))
        headers = [mapping.get(c, c) for c in df_group.columns]

        self.table.setRowCount(df_group.shape[0])
        self.table.setColumnCount(df_group.shape[1])
        self.table.setHorizontalHeaderLabels(headers)

        for r in range(df_group.shape[0]):
            for c in range(df_group.shape[1]):
                self.table.setItem(r, c, QTableWidgetItem(str(df_group.iloc[r, c])))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # ✅ 修复：启用打印按钮+强制刷新
        self.btn_print.setEnabled(True)
        # self.btn_print.update()  # 强制界面刷新
        # self.btn_print.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def print_final(self):

        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QPainter
            from PyQt6.QtCore import Qt, QRectF

            if self.result_df is None:
                QMessageBox.warning(self, "提示", "请先查询数据")
                return

            # 极简初始化
            printer = QPrinter()
            dialog = QPrintDialog(printer)
            if not dialog.exec():
                return

            painter = QPainter()
            painter.begin(printer)

            # 标题（固定坐标，彻底不调用 pageRect）
            title = f"{self.y.value()}年{self.m.value()}月 提成统计报表"
            painter.setFont(QFont("微软雅黑", 14, QFont.Weight.Bold))
            painter.drawText(QRectF(0, 50, 1000, 50), Qt.AlignmentFlag.AlignCenter, title)

            # 表格配置
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            row_h = 30
            col_w = 90
            x = 20
            y = 120

            # 画表头
            painter.setFont(QFont("微软雅黑", 9, QFont.Weight.Bold))
            for i, h in enumerate(headers):
                painter.drawRect(x + i * col_w, y, col_w, row_h)
                painter.drawText(QRectF(x + i * col_w, y, col_w, row_h), Qt.AlignmentFlag.AlignCenter, h)

            # 画数据
            painter.setFont(QFont("微软雅黑", 8))
            for r in range(self.table.rowCount()):
                cy = y + (r + 1) * row_h
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    txt = item.text() if item else ""
                    painter.drawRect(x + c * col_w, cy, col_w, row_h)
                    painter.drawText(QRectF(x + c * col_w, cy, col_w, row_h), Qt.AlignmentFlag.AlignCenter, txt)

            painter.end()
            QMessageBox.information(self, "成功", "打印已发送！")

        except Exception as e:
            QMessageBox.critical(self, "打印失败", f"错误：{str(e)}")
# ============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CommissionApp()
    w.show()
    sys.exit(app.exec())