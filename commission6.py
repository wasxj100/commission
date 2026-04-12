import sys
import sqlite3
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QGridLayout,
    QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import QDate, QDateTime
from PyQt6.QtGui import QFont

# ===================== 中文显示 ↔ 英文字段 =====================
FIELD_MAP = [
    ("姓名", "name"),
    ("拍片", "pp"),
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

VALUE = [20, 5, 2, 2, 3, 5, 30, 10, 40, 30, 10, 40, 20]
CHINESE_NAMES = [item[0] for item in FIELD_MAP]
ENGLISH_FIELDS = [item[1] for item in FIELD_MAP]


# ===============================================================

# ===================== SQLite 数据库 =====================
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
        update_items = [f"{k}=?" for k in data_dict.keys()]
        update_items.append("created_at=?")
        sql = f"UPDATE records SET {','.join(update_items)} WHERE id=?"
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


def get_month_raw_data(year, month):
    conn = sqlite3.connect("commission.db")
    date_filter = f"{year}-{month:02d}-%"
    cursor = conn.cursor()
    # 正确写法：SELECT * 只查一遍所有列（含 date）
    cursor.execute("SELECT * FROM records WHERE date LIKE ?", (date_filter,))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return columns, rows


# ==========================================================

# ===================== 主窗口 =====================
class CommissionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("提成计算系统")
        self.setGeometry(100, 100, 1200, 700)
        init_db()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧导航（3项：日历录入 → 数据查询 → 数据统计）
        self.nav = QListWidget()
        self.nav.setFixedWidth(160)
        self.nav.addItems(["日历录入", "数据查询", "数据统计"])
        main_layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        self.stack.addWidget(CalendarPage())
        self.stack.addWidget(DataQueryPage())  # 数据查询页
        self.stack.addWidget(StatsPage())  # 数据统计页
        main_layout.addWidget(self.stack)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)


# ===================== 日历录入页面 =====================
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        date_layout = QHBoxLayout()

        self.y = QSpinBox()
        self.y.setRange(2000, 2100)
        self.y.setValue(QDate.currentDate().year())

        self.m = QSpinBox()
        self.m.setRange(1, 12)
        self.m.setValue(QDate.currentDate().month())

        date_layout.addWidget(self.y)
        date_layout.addWidget(self.m)
        layout.addLayout(date_layout)

        btn = QPushButton("刷新日历")
        btn.clicked.connect(self.show_calendar)
        layout.addWidget(btn)

        self.g = QGridLayout()
        layout.addLayout(self.g)
        self.show_calendar()

    def show_calendar(self):
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
            b.setFont(QFont("微软雅黑", 12))
            b.clicked.connect(lambda _, dd=d: self.open_d(y, m, dd))
            self.g.addWidget(b, r, c)
            c += 1
            if c == 7:
                c = 0
                r += 1

    def open_d(self, y, m, d):
        dialog = AddDataDialog(f"{y}-{m:02d}-{d:02d}")
        dialog.exec()


# ===================== 新增数据对话框 =====================
class AddDataDialog(QDialog):
    def __init__(self, date_str):
        super().__init__()
        self.date = date_str
        self.setWindowTitle(f"录入数据 - {date_str}")
        self.setFixedSize(520, 580)
        self.widgets = {}
        self.init_ui()

    def init_ui(self):
        lay = QFormLayout(self)
        for ch, en in FIELD_MAP:
            e = QLineEdit()
            self.widgets[en] = e
            lay.addRow(f"{ch}：", e)

        save = QPushButton("保存数据")
        save.clicked.connect(self.save)
        lay.addRow(save)

    def save(self):
        data = {}
        name_text = self.widgets["name"].text().strip()

        if not name_text:
            QMessageBox.warning(self, "警告", "姓名不能为空！")
            return

        data["name"] = name_text

        for ch, en in FIELD_MAP[1:]:
            txt = self.widgets[en].text().strip()
            data[en] = int(txt) if txt and txt.isdigit() and int(txt) > 0 else 0

        save_or_update(self.date, data)
        QMessageBox.information(self, "成功", "数据已保存")
        self.accept()


# ###########################################################################
# ###################### 【新增】数据查询页面  ###########################
# ###########################################################################
class DataQueryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 顶部：年份 + 月份 + 查询按钮
        query_layout = QHBoxLayout()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(QDate.currentDate().year())

        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(QDate.currentDate().month())

        self.query_btn = QPushButton("查询当月所有数据")
        self.query_btn.clicked.connect(self.query_data)

        query_layout.addWidget(self.year_spin)
        query_layout.addWidget(self.month_spin)
        query_layout.addWidget(self.query_btn)
        layout.addLayout(query_layout)

        # 表格展示
        self.table = QTableWidget()
        self.table.setFont(QFont("微软雅黑", 10))
        layout.addWidget(self.table)
        self.setLayout(layout)

    def query_data(self):
        year = self.year_spin.value()
        month = self.month_spin.value()
        columns, rows = get_month_raw_data(year, month)

        if not rows:
            QMessageBox.information(self, "提示", "当月无数据")
            self.table.setRowCount(0)
            return

        # 英文列名 → 中文显示
        field_dict = dict(zip(ENGLISH_FIELDS, CHINESE_NAMES))
        headers = []
        for col in columns:
            if col == "date":
                headers.append("日期")
            elif col == "created_at":
                headers.append("创建时间")
            elif col == "id":
                headers.append("ID")
            else:
                headers.append(field_dict.get(col, col))

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        # 填充数据
        for row_idx, row_data in enumerate(rows):
            for col_idx, val in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


# ###########################################################################
# ###################### 数据统计页面（Pandas分组） ########################
# ###########################################################################
class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        query_layout = QHBoxLayout()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(QDate.currentDate().year())
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(QDate.currentDate().month())
        self.query_btn = QPushButton("按姓名分组统计")
        self.query_btn.clicked.connect(self.show_by_pandas)
        query_layout.addWidget(self.year_spin)
        query_layout.addWidget(self.month_spin)
        query_layout.addWidget(self.query_btn)
        layout.addLayout(query_layout)

        self.table = QTableWidget()
        self.table.setFont(QFont("微软雅黑", 10))
        layout.addWidget(self.table)
        self.setLayout(layout)

    def show_by_pandas(self):
        year = self.year_spin.value()
        month = self.month_spin.value()
        df = get_month_data_as_df(year, month)

        if df.empty:
            QMessageBox.information(self, "提示", "当月无数据")
            self.table.setRowCount(0)
            return

        # 按姓名分组求和
        df_group = df.groupby("name", as_index=False)[ENGLISH_FIELDS[1:]].sum()
        print(df_group)
        _df_group = df_group.iloc[:,1:] * VALUE
        df_group['总提成'] = _df_group.sum(axis = 1)
        # 显示中文表头
        mapping = dict(zip(ENGLISH_FIELDS, CHINESE_NAMES))
        headers = [mapping.get(c, c) for c in df_group.columns]

        self.table.setRowCount(df_group.shape[0])
        self.table.setColumnCount(df_group.shape[1])
        self.table.setHorizontalHeaderLabels(headers)

        for r in range(df_group.shape[0]):
            for c in range(df_group.shape[1]):
                self.table.setItem(r, c, QTableWidgetItem(str(df_group.iloc[r, c])))





# ======================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CommissionApp()
    w.show()
    sys.exit(app.exec())