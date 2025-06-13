from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QScrollArea, QLabel, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics, QBrush

class HexEditor(QWidget):
    # 定义信号
    sector_changed = pyqtSignal(int)
    cluster_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = bytearray()
        self.cursor_position = 0
        self.selection_start = -1
        self.selection_end = -1
        self.bytes_per_line = 16
        self.cell_width = 25
        self.cell_height = 20
        self.offset_width = 100
        self.ascii_width = 200
        self.margin = 5
        self.current_sector = 0
        self.current_cluster = 0
        self.sector_size = 512
        self.sectors_per_view = 9  # 一次显示9个扇区
        self.sector_data = []      # 存储多个扇区数据
        self.sector_base = 0       # 当前显示的第一个扇区号
        
        # 设置固定字体
        self.font = QFont("Courier New", 10)
        self.setFont(self.font)
        
        # 设置背景色
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#FFFFFF")) #设置背景颜色
        self.setPalette(palette)
        
        # 计算字体度量
        self.font_metrics = QFontMetrics(self.font)
        self.char_width = self.font_metrics.horizontalAdvance("0")
        self.char_height = self.font_metrics.height()
        
        # 设置最小尺寸
        self.setMinimumSize(800, 400)
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建十六进制显示区域
        self.hex_area = HexArea(self)
        layout.addWidget(self.hex_area)
        
        # 创建状态栏
        status_layout = QHBoxLayout()
        
        # 左侧状态信息
        left_status = QHBoxLayout()
        self.offset_label = QLabel("偏移: 0x00000000")
        self.size_label = QLabel("大小: 0 字节")
        left_status.addWidget(self.offset_label)
        left_status.addWidget(self.size_label)
        
        # 中间状态信息
        middle_status = QHBoxLayout()
        self.sector_label = QLabel("扇区: 0")
        self.cluster_label = QLabel("簇: 0")
        middle_status.addWidget(self.sector_label)
        middle_status.addWidget(self.cluster_label)
        
        # 右侧跳转按钮
        right_status = QHBoxLayout()
        self.goto_sector_btn = QPushButton("跳转到扇区")
        self.goto_sector_btn.setObjectName("goto_sector_btn")
        self.goto_cluster_btn = QPushButton("跳转到簇")
        self.goto_cluster_btn.setObjectName("goto_cluster_btn")
        right_status.addWidget(self.goto_sector_btn)
        right_status.addWidget(self.goto_cluster_btn)
        
        # 添加所有状态组件
        status_layout.addLayout(left_status)
        status_layout.addStretch()
        status_layout.addLayout(middle_status)
        status_layout.addStretch()
        status_layout.addLayout(right_status)
        
        layout.addLayout(status_layout)
    
    def set_sector_data(self, sector_data: list, base_sector: int):
        """设置多个扇区的数据和基准扇区号"""
        self.sector_data = sector_data
        self.data = b''.join(sector_data)
        self.sector_base = base_sector
        self.cursor_position = 0
        self.selection_start = -1
        self.selection_end = -1
        self.hex_area.update()
        self.update_status()
    
    def update_status(self):
        self.offset_label.setText(f"偏移: 0x{self.cursor_position:08X}")
        self.size_label.setText(f"大小: {len(self.data)} 字节")
        self.sector_label.setText(f"扇区: {self.current_sector} (显示: {self.sector_base}-{self.sector_base+len(self.sector_data)-1})")
        self.cluster_label.setText(f"簇: {self.current_cluster}")
    
    def set_current_sector(self, sector):
        self.current_sector = sector
        self.update_status()
    
    def set_current_cluster(self, cluster):
        self.current_cluster = cluster
        self.update_status()

    def set_data(self, data: bytes):
        """直接设置编辑器数据（用于文件/扇区/簇跳转）"""
        self.data = bytearray(data)
        self.cursor_position = 0
        self.selection_start = -1
        self.selection_end = -1
        self.sector_data = []
        self.sector_base = 0
        self.hex_area.update()
        self.update_status()

class HexArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hex_editor = parent
        self.setMinimumHeight(400)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 设置背景色
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#FFFFFF"))
        self.setPalette(palette)
        
        # 滚动相关变量
        self.scroll_offset = 0
        self.last_y = 0
        self.is_selecting = False
        self.selection_start = -1
        self.selection_end = -1
    
    def paintEvent(self, event):
        if not self.hex_editor.data or len(self.hex_editor.data) == 0:
            return
        
        # 检查是否是NTFS的$MFT文件
        is_mft = hasattr(self.hex_editor, 'is_mft') and self.hex_editor.is_mft
        mft_record = None
        if is_mft:
            try:
                from disk_utils import DiskUtils
                mft_record = DiskUtils.parse_mft_record(bytes(self.hex_editor.data))
            except:
                is_mft = False
        
        painter = QPainter(self)
        painter.setFont(self.hex_editor.font)
        painter.fillRect(event.rect(), QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E0E0E0")))
        visible_rect = event.rect()
        start_y = max(0, int((visible_rect.y() + self.scroll_offset) // self.hex_editor.cell_height))
        end_y = min(len(self.hex_editor.data) // self.hex_editor.bytes_per_line + 1,
                   int((visible_rect.y() + visible_rect.height() + self.scroll_offset) // self.hex_editor.cell_height + 1))
        
        # 绘制水平网格线
        for y in range(start_y, end_y):
            line_y = int(y * self.hex_editor.cell_height - self.scroll_offset)
            painter.drawLine(0, line_y, self.width(), line_y)
        
        # 绘制扇区分隔虚线
        lines_per_sector = self.hex_editor.sector_size // self.hex_editor.bytes_per_line if self.hex_editor.bytes_per_line else 1
        for s in range(1, len(self.hex_editor.sector_data)):
            y = int(s * lines_per_sector * self.hex_editor.cell_height - self.scroll_offset)
            pen = QPen(QColor("#AAAAAA"), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(0, y, self.width(), y)
            painter.setPen(QPen(QColor("#E0E0E0")))
        
        # 绘制垂直网格线
        for x in range(0, self.hex_editor.bytes_per_line + 1):
            line_x = self.hex_editor.offset_width + x * self.hex_editor.cell_width
            painter.drawLine(line_x, 0, line_x, self.height())
        
        # 绘制ASCII区域分隔线
        ascii_start_x = self.hex_editor.offset_width + self.hex_editor.bytes_per_line * self.hex_editor.cell_width + 20
        painter.drawLine(ascii_start_x, 0, ascii_start_x, self.height())
        
        # 绘制偏移地址
        painter.setPen(QPen(QColor("#000000")))
        for i in range(start_y, end_y):
            offset = i * self.hex_editor.bytes_per_line
            y = int(i * self.hex_editor.cell_height - self.scroll_offset)
            rect = QRect(self.hex_editor.margin, y, 100, self.hex_editor.cell_height)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           f"{offset:08X}")
        
        # 绘制十六进制值
        for i in range(start_y * self.hex_editor.bytes_per_line,
                      min(len(self.hex_editor.data), end_y * self.hex_editor.bytes_per_line)):
            x = self.hex_editor.offset_width + (i % self.hex_editor.bytes_per_line) * self.hex_editor.cell_width
            y = int((i // self.hex_editor.bytes_per_line) * self.hex_editor.cell_height - self.scroll_offset)
            
            # 设置默认背景色
            bg_color = None
            
            # 如果是MFT记录，设置不同区域的背景色
            if is_mft and mft_record:
                # 文件头区域 - 着色56字节
                file_header_end = mft_record['header']['offset'] + 56
                if i >= mft_record['header']['offset'] and i < file_header_end:
                    bg_color = QColor("#FFE4B5")
                
                # 属性处理
                for attr in mft_record['attributes']:
                    # 10H和30H属性头 - 着色24字节
                    if attr['type'] in [0x10, 0x30]:
                        attr_header_end = attr['offset'] + 24
                        if i >= attr['offset'] and i < attr_header_end:
                            bg_color = QColor("#ADD8E6")
                        
                        # 10H属性体 - 着色72字节
                        if attr['type'] == 0x10 and 'content_offset' in attr:
                            attr_body_end = attr['offset'] + attr['content_offset'] + 72
                            if i >= attr['offset'] + attr['content_offset'] and i < attr_body_end:
                                bg_color = QColor("#90EE90")
                        
                        # 30H属性体 - 着色80字节（原90字节减少10字节）
                        elif attr['type'] == 0x30 and 'content_offset' in attr:
                            attr_body_end = attr['offset'] + attr['content_offset'] + 80
                            if i >= attr['offset'] + attr['content_offset'] and i < attr_body_end:
                                bg_color = QColor("#90EE90")
                    
                    # 其他属性值
                    elif 'content_offset' in attr and i >= attr['offset'] + attr['content_offset'] and i < attr['offset'] + attr['content_offset'] + attr['content_size']:
                        bg_color = QColor("#90EE90")
            
            # 绘制选中背景
            if self.selection_start != -1 and self.selection_end != -1:
                if min(self.selection_start, self.selection_end) <= i <= max(self.selection_start, self.selection_end):
                    bg_color = QColor("#0078D7")  # 选中区域 - 蓝色
            
            # 绘制背景
            if bg_color:
                rect = QRect(x, y, self.hex_editor.cell_width, self.hex_editor.cell_height)
                painter.fillRect(rect, bg_color)
            
            rect = QRect(x + self.hex_editor.margin, y, self.hex_editor.cell_width - 2 * self.hex_editor.margin,
                        self.hex_editor.cell_height)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           f"{self.hex_editor.data[i]:02X}")
        
        # 绘制ASCII值
        ascii_start_x = self.hex_editor.offset_width + self.hex_editor.bytes_per_line * self.hex_editor.cell_width + 20
        for i in range(start_y * self.hex_editor.bytes_per_line,
                      min(len(self.hex_editor.data), end_y * self.hex_editor.bytes_per_line)):
            x = ascii_start_x + (i % self.hex_editor.bytes_per_line) * 10
            y = int((i // self.hex_editor.bytes_per_line) * self.hex_editor.cell_height - self.scroll_offset)
            
            # 设置颜色和背景
            if self.selection_start != -1 and self.selection_end != -1:
                if min(self.selection_start, self.selection_end) <= i <= max(self.selection_start, self.selection_end):
                    rect = QRect(x, y, 10, self.hex_editor.cell_height)
                    painter.fillRect(rect, QColor("#0078D7"))
                    painter.setPen(QPen(QColor("#FFFFFF")))
                else:
                    painter.setPen(QPen(QColor("#000000")))
            else:
                painter.setPen(QPen(QColor("#000000")))
            
            # 只显示可打印字符
            char = chr(self.hex_editor.data[i]) if 32 <= self.hex_editor.data[i] <= 126 else '.'
            rect = QRect(x, y, 10, self.hex_editor.cell_height)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, char)
    
    def mousePressEvent(self, event):
        if not self.hex_editor.data or len(self.hex_editor.data) == 0:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = True
            self.last_y = event.position().y()
            x = event.position().x()
            y = event.position().y() + self.scroll_offset
            if x > self.hex_editor.offset_width:
                try:
                    col = int((x - self.hex_editor.offset_width) / self.hex_editor.cell_width)
                    row = int(y / self.hex_editor.cell_height)
                    pos = row * self.hex_editor.bytes_per_line + col
                    if not (0 <= pos < len(self.hex_editor.data)):
                        return
                    self.selection_start = pos
                    self.selection_end = pos
                    self.hex_editor.cursor_position = pos
                    self.hex_editor.update_status()
                    self.update()
                except Exception:
                    return
    
    def mouseMoveEvent(self, event):
        if not self.hex_editor.data or len(self.hex_editor.data) == 0:
            return
        if self.is_selecting:
            try:
                delta = self.last_y - event.position().y()
                max_scroll = max(0, len(self.hex_editor.data) * self.hex_editor.cell_height // self.hex_editor.bytes_per_line - self.height())
                self.scroll_offset = max(0, min(self.scroll_offset + delta, max_scroll))
                self.last_y = event.position().y()
                x = event.position().x()
                y = event.position().y() + self.scroll_offset
                if x > self.hex_editor.offset_width:
                    col = int((x - self.hex_editor.offset_width) / self.hex_editor.cell_width)
                    row = int(y / self.hex_editor.cell_height)
                    pos = row * self.hex_editor.bytes_per_line + col
                    if not (0 <= pos < len(self.hex_editor.data)):
                        return
                    self.selection_end = pos
                    if self.selection_start > self.selection_end:
                        self.selection_start, self.selection_end = self.selection_end, self.selection_start
                    self.hex_editor.cursor_position = pos
                    self.hex_editor.update_status()
                    self.update()
            except Exception:
                return
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = False
    
    def wheelEvent(self, event):
        if not self.hex_editor.data or len(self.hex_editor.data) == 0:
            return
        delta = event.angleDelta().y()
        max_scroll = max(0, len(self.hex_editor.data) * self.hex_editor.cell_height // self.hex_editor.bytes_per_line - self.height())
        self.scroll_offset = max(0, min(self.scroll_offset - delta, max_scroll))
        self.update()
    
    def keyPressEvent(self, event):
        if not self.hex_editor.data or len(self.hex_editor.data) == 0:
            return
        max_pos = len(self.hex_editor.data) - 1
        if event.key() == Qt.Key.Key_Left:
            if 0 < self.hex_editor.cursor_position <= max_pos:
                self.hex_editor.cursor_position -= 1
                self.selection_start = self.hex_editor.cursor_position
                self.selection_end = self.hex_editor.cursor_position
                self.hex_editor.update_status()
                self.update()
        elif event.key() == Qt.Key.Key_Right:
            if 0 <= self.hex_editor.cursor_position < max_pos:
                self.hex_editor.cursor_position += 1
                self.selection_start = self.hex_editor.cursor_position
                self.selection_end = self.hex_editor.cursor_position
                self.hex_editor.update_status()
                self.update()
        elif event.key() == Qt.Key.Key_Up:
            new_pos = self.hex_editor.cursor_position - self.hex_editor.bytes_per_line
            if new_pos >= 0:
                self.hex_editor.cursor_position = new_pos
                self.selection_start = self.hex_editor.cursor_position
                self.selection_end = self.hex_editor.cursor_position
                self.hex_editor.update_status()
                self.update()
        elif event.key() == Qt.Key.Key_Down:
            new_pos = self.hex_editor.cursor_position + self.hex_editor.bytes_per_line
            if new_pos <= max_pos:
                self.hex_editor.cursor_position = new_pos
                self.selection_start = self.hex_editor.cursor_position
                self.selection_end = self.hex_editor.cursor_position
                self.hex_editor.update_status()
                self.update()
    
    def mouseDoubleClickEvent(self, event):
        if not self.hex_editor.data or len(self.hex_editor.data) == 0:
            return
        x = event.position().x()
        y = event.position().y() + self.scroll_offset
        if x > self.hex_editor.offset_width:
            try:
                col = int((x - self.hex_editor.offset_width) / self.hex_editor.cell_width)
                row = int(y / self.hex_editor.cell_height)
                pos = row * self.hex_editor.bytes_per_line + col
                if not (0 <= pos < len(self.hex_editor.data)):
                    return
                self.hex_editor.cursor_position = pos
                self.selection_start = pos
                self.selection_end = pos
                self.hex_editor.update_status()
                self.update()
            except Exception:
                return