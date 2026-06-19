"""Citation Converter - main PyQt6 application."""

import sys
import re
import html
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QScrollArea,
    QFrame, QStatusBar, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer

from parsers import parse_citation
from utils import convert_all, FORMAT_KEYS


STYLE = """
QMainWindow { background-color: #f5f5f5; }
QWidget#central { background-color: #f5f5f5; }
QLabel#title {
    font-size: 16px; font-weight: bold; color: #1a1a2e; padding: 6px 0px;
}
QLabel#section {
    font-size: 11px; font-weight: bold; color: #555; padding: 4px 0px 2px 0px;
}
QTextEdit {
    border: 1px solid #ccc; border-radius: 6px; padding: 8px;
    font-size: 12px; background-color: #ffffff; color: #222;
}
QTextEdit:focus { border: 1px solid #4a90d9; }
QPushButton {
    border: 1px solid #bbb; border-radius: 5px; padding: 5px 14px;
    font-size: 12px; background-color: #fff; color: #333;
}
QPushButton:hover { background-color: #e8f0fe; border-color: #4a90d9; color: #1a56db; }
QPushButton:pressed { background-color: #d0e4ff; }
QPushButton#copyBtn {
    font-size: 11px; padding: 3px 10px; border-color: #aaa; color: #555;
}
QPushButton#copyBtn:hover { background-color: #e8f0fe; }
QScrollArea { border: 1px solid #ccc; border-radius: 6px; background-color: #fff; }
QFrame#outputBlock { border: none; background-color: #fff; }
QLabel#formatTitle {
    font-size: 11px; font-weight: bold; color: #1a56db; padding: 4px 8px 0px 8px;
}
QLabel#formatBody {
    font-size: 12px; color: #222; padding: 2px 8px 6px 8px;
}
QStatusBar { font-size: 11px; color: #555; }
"""

HELP_TEXT = """Citation Converter - Yardım

Kullanım:
1. Atıfı giriş kutusuna yapıştırın (Ctrl+V).
2. Tüm formatlar otomatik olarak görüntülenir.
3. Her format bloğundaki [Kopyala] butonu ile
   istediğiniz formatı panoya kopyalayın.

Desteklenen çıktı formatları:
• APA (7th Edition)
• ACS (American Chemical Society)
• Chicago (Notes and Bibliography)
• Harvard
• MLA (9th Edition)
• IEEE
• BibTeX
• Vancouver

Tanınan giriş formatları:
• Nature/Springer stili
• APA, Chicago, Harvard, Vancouver, MLA
• IEEE, Taylor & Francis, ACS, Frontiers
• BibTeX
"""

ABOUT_TEXT = """Citation Converter — Atıf Dönüştürücü

Sürüm: v1.7-beta

Geliştirici: Sertaç Emre Kara

Atıfları 9 farklı akademik formata
otomatik dönüştüren masaüstü uygulaması.

Lisans: MIT
"""

FORMAT_LABELS = {
    "APA": "APA",
    "IEEE": "IEEE",
    "Springer/Nature": "Springer/Nature",
    "Nature/Springer": "Nature/Springer",
    "Chicago": "Chicago",
    "Harvard": "Harvard",
    "MLA": "MLA",
    "BibTeX": "BibTeX",
    "Vancouver": "Vancouver",
    "Taylor & Francis": "Taylor & Francis",
    "ACS": "ACS",
    "Frontiers": "Frontiers",
    None: "belirsiz",
}


def _md_to_html(text: str) -> str:
    """Convert minimal markdown (**bold**, *italic*) to HTML for QLabel."""
    t = html.escape(text)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
    return t


def _md_to_rtf(text: str) -> bytes:
    """Convert minimal markdown (**bold**, *italic*) to RTF bytes for clipboard."""
    # RTF özel karakterleri kaçır
    def rtf_escape(s: str) -> str:
        out = []
        for ch in s:
            if ch == '\\':
                out.append('\\\\')
            elif ch == '{':
                out.append('\\{')
            elif ch == '}':
                out.append('\\}')
            elif ord(ch) > 127:
                out.append(f'\\u{ord(ch)}?')
            else:
                out.append(ch)
        return ''.join(out)

    # Önce **bold** sonra *italic* dönüştür
    parts = []
    i = 0
    while i < len(text):
        if text[i:i+2] == '**':
            end = text.find('**', i + 2)
            if end != -1:
                parts.append(f'\\b {rtf_escape(text[i+2:end])}\\b0 ')
                i = end + 2
                continue
        if text[i] == '*':
            end = text.find('*', i + 1)
            if end != -1:
                parts.append(f'\\i {rtf_escape(text[i+1:end])}\\i0 ')
                i = end + 1
                continue
        parts.append(rtf_escape(text[i]))
        i += 1

    content = ''.join(parts)
    rtf = (
        r'{\rtf1\ansi\deff0'
        r'{\fonttbl{\f0\froman\fcharset0 Times New Roman;}}'
        r'{\colortbl;}'
        r'\f0\fs24 ' + content + r'}'
    )
    return rtf.encode('ascii', errors='replace')


def _copy_rtf(text: str) -> None:
    """Copy text with RTF formatting to clipboard using win32clipboard."""
    try:
        import win32clipboard
        rtf_data = _md_to_rtf(text)
        plain = re.sub(r'\*+', '', text)  # markdown sembollerini sil
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        # RTF formatı
        rtf_format = win32clipboard.RegisterClipboardFormat("Rich Text Format")
        win32clipboard.SetClipboardData(rtf_format, rtf_data)
        # Düz metin de ekle (fallback)
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, plain)
        win32clipboard.CloseClipboard()
    except Exception:
        # win32clipboard yoksa veya hata olursa düz metin kopyala
        QApplication.clipboard().setText(re.sub(r'\*+', '', text))


class FormatBlock(QFrame):
    def __init__(self, fmt_name: str, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("outputBlock")
        self.citation_text = text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 0, 8, 0)

        title_lbl = QLabel(fmt_name)
        title_lbl.setObjectName("formatTitle")
        header.addWidget(title_lbl)
        header.addStretch()

        self.copy_btn = QPushButton("Kopyala")
        self.copy_btn.setObjectName("copyBtn")
        self.copy_btn.setFixedHeight(24)
        self.copy_btn.clicked.connect(self._copy)
        header.addWidget(self.copy_btn)

        layout.addLayout(header)

        self.body_lbl = QLabel(_md_to_html(text))
        self.body_lbl.setObjectName("formatBody")
        self.body_lbl.setWordWrap(True)
        self.body_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.body_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #eee;")
        layout.addWidget(sep)

    def _copy(self):
        _copy_rtf(self.citation_text)
        orig = self.copy_btn.text()
        self.copy_btn.setText("Kopyalandı!")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(orig))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Citation Converter - Atıf Dönüştürücü")
        self.setMinimumSize(680, 580)
        self._build_ui()
        self._connect()
        self._position_window()

    def _position_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = screen.width() // 3
        self.resize(width, screen.height())
        self.move(screen.left() + (screen.width() - width) // 2, screen.top())

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 8)
        root.setSpacing(8)

        title = QLabel("Citation Converter — Atıf Dönüştürücü")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        # Toolbar: only Temizle + Yardım
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addStretch()
        self.clear_btn = QPushButton("Temizle")
        self.help_btn = QPushButton("Yardım")
        self.about_btn = QPushButton("Hakkında")
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.help_btn)
        toolbar.addWidget(self.about_btn)
        root.addLayout(toolbar)

        in_label = QLabel("GİRİŞ — Atıfı yapıştırın (Ctrl+V):")
        in_label.setObjectName("section")
        root.addWidget(in_label)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Atıfı buraya yapıştırın...\n\n"
            "Örnek:\n"
            "Bartkowski, P., Ciemiorek, M., Bukowiecki, H. et al. "
            "Granular jamming for soft robotics: experiments and modelling of cyclic loading. "
            "Arch. Civ. Mech. Eng. 25, 123 (2025). https://doi.org/10.1007/s43452-025-01176-9"
        )
        self.input_edit.setFixedHeight(110)
        root.addWidget(self.input_edit)

        self.status_msg = QLabel("")
        self.status_msg.setObjectName("section")
        root.addWidget(self.status_msg)

        out_label = QLabel("ÇIKTI — Tüm Formatlar:")
        out_label.setObjectName("section")
        root.addWidget(out_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.output_container = QWidget()
        self.output_container.setStyleSheet("background-color: #fff;")
        self.output_layout = QVBoxLayout(self.output_container)
        self.output_layout.setContentsMargins(4, 4, 4, 4)
        self.output_layout.setSpacing(0)
        self.output_layout.addStretch()

        self.scroll.setWidget(self.output_container)
        root.addWidget(self.scroll, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Hazır")

    def _connect(self):
        self.input_edit.textChanged.connect(self._on_input_changed)
        self.clear_btn.clicked.connect(self._clear)
        self.help_btn.clicked.connect(self._show_help)
        self.about_btn.clicked.connect(self._show_about)

    def _on_input_changed(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            self._clear_output()
            self.status_msg.setText("")
            self.status_bar.showMessage("Hazır")
            return
        self._process(text)

    def _process(self, text: str):
        self.status_bar.showMessage("İşleniyor...")
        QApplication.processEvents()

        cd = parse_citation(text)

        if not cd.is_valid:
            self._clear_output()
            self.status_msg.setText("Geçerli bir atıf değil. Lütfen tam atıf yapıştırın.")
            self.status_msg.setStyleSheet("color: #c62828; font-size: 11px;")
            self.status_bar.showMessage("Hata: Geçerli atıf bulunamadı")
            return

        # Build status message
        detected = FORMAT_LABELS.get(cd.detected_format, cd.detected_format or "belirsiz")
        doc_type = "Konferans Bildirisi" if cd.conference else "Dergi Makalesi"
        if cd.missing_fields:
            missing = ", ".join(cd.missing_fields)
            msg = f"Algılanan format: {detected}  |  Tür: {doc_type}  |  Uyarı — eksik alanlar: {missing}"
            color = "#e65100"
        else:
            msg = f"Algılanan format: {detected}  |  Tür: {doc_type}"
            color = "#555"
        self.status_msg.setText(msg)
        self.status_msg.setStyleSheet(f"color: {color}; font-size: 11px;")

        results = convert_all(cd)
        self._update_output_blocks(results)
        self.status_bar.showMessage(f"Dönüştürüldü — {len(results)} format")

    def _update_output_blocks(self, results: dict[str, str]):
        while self.output_layout.count() > 1:
            item = self.output_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for fmt in FORMAT_KEYS:
            if fmt not in results:
                continue
            block = FormatBlock(fmt, results[fmt])
            self.output_layout.insertWidget(self.output_layout.count() - 1, block)

    def _clear_output(self):
        while self.output_layout.count() > 1:
            item = self.output_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear(self):
        self.input_edit.clear()
        self._clear_output()
        self.status_msg.setText("")
        self.status_bar.showMessage("Temizlendi")

    def _show_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Yardım")
        msg.setText(HELP_TEXT)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def _show_about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Hakkında")
        msg.setText(ABOUT_TEXT)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
