import sys
import os
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QMenuBar, QStatusBar, QToolBar, 
                            QFileDialog, QMessageBox, QComboBox, QDialog,
                            QLabel, QLineEdit, QPushButton, QFormLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from hex_editor import HexEditor
from disk_utils import DiskUtils

class SectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("跳转到扇区")
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        layout = QFormLayout(self)
        layout.setSpacing(10)
        
        self.sector_input = QLineEdit()
        self.sector_input.setPlaceholderText("请输入扇区号")
        layout.addRow("扇区号:", self.sector_input)
        
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

class ClusterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("跳转到簇")
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        layout = QFormLayout(self)
        layout.setSpacing(10)
        
        self.cluster_input = QLineEdit()
        self.cluster_input.setPlaceholderText("请输入簇号")
        layout.addRow("簇号:", self.cluster_input)
        
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

class WinHexClone(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinHex 克隆版")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton#goto_sector_btn, QPushButton#goto_cluster_btn {
                color:  #ffffff;
                background-color: #0078d7;
            }
            QPushButton#goto_sector_btn:hover, QPushButton#goto_cluster_btn:hover {
                background-color: #106ebe;
                color: #ffffff;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
                color: #222222;
                font-size: 14px;
            }
            QComboBox QAbstractItemView {
                color: #222222;
                background: #ffffff;
                selection-background-color: #e0e0e0;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
                color: #222222;
                font-size: 14px;
            }
            QLineEdit:disabled {
                color: #aaaaaa;
            }
            QToolBar {
                background: #f0f0f0;
                border: none;
            }
            QToolButton {
                color: #222222;
                background: transparent;
                font-size: 14px;
                padding: 5px 10px;
            }
            QToolButton:hover {
                background: #e0e0e0;
                color: #222222;
            }
            QMenuBar {
                background-color: #f0f0f0;
                color: #333333;
            }
            QMenuBar::item {
                background-color: #f0f0f0;
                color: #333333;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QMessageBox {
                background-color: #f0f0f0;
                color: #333333;
            }
        """)
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(10)
        
        # 创建磁盘选择下拉框
        self.disk_layout = QHBoxLayout()
        self.disk_label = QLabel("选择磁盘:")
        self.disk_combo = QComboBox()
        self.disk_layout.addWidget(self.disk_label)
        self.disk_layout.addWidget(self.disk_combo)
        
        # 添加查找 $MFT 按钮
        self.find_mft_btn = QPushButton("查找NTFS的$MFT位置")
        self.find_mft_btn.clicked.connect(self.find_mft)
        self.disk_layout.addWidget(self.find_mft_btn)
        
        # 添加查找根目录按钮
        self.find_root_dir_btn = QPushButton("查找根目录")
        self.find_root_dir_btn.clicked.connect(self.find_root_directory)
        self.disk_layout.addWidget(self.find_root_dir_btn)
        
        self.disk_layout.addStretch()
        self.main_layout.addLayout(self.disk_layout)
        
        # 创建十六进制编辑器
        self.hex_editor = HexEditor()
        self.main_layout.addWidget(self.hex_editor)
        
        # 连接信号
        self.hex_editor.goto_sector_btn.clicked.connect(self.goto_sector)
        self.hex_editor.goto_cluster_btn.clicked.connect(self.goto_cluster)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 当前文件路径
        self.current_file = None
        self.current_disk = None
        
        # 初始化磁盘列表
        self.init_disk_list()
    def find_mft(self):
        """查找 NTFS 的 $MFT 位置"""
        try:
            if not self.current_disk:
                QMessageBox.warning(self, "警告", "请先选择一个磁盘")
                return

            mft_sector = DiskUtils.find_mft_location(self.current_disk)
            data = DiskUtils.read_sector(self.current_disk, mft_sector)
            self.hex_editor.set_data(data)
            self.hex_editor.is_mft = True  # 设置MFT标志
            self.hex_editor.update()
            QMessageBox.information(self, "结果", f"NTFS 的 $MFT 起始扇区号为: {mft_sector}")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
    def init_disk_list(self):
        """初始化磁盘列表，分区和物理磁盘合并下拉显示"""
        try:
            self.disk_combo.blockSignals(True)
            self.disk_combo.clear()
            drives, physicals = DiskUtils.get_disk_list_grouped()
            if drives:
                self.disk_combo.addItem("--- 逻辑卷/分区 ---")
                for drive_letter, drive_name in drives:
                    self.disk_combo.addItem(drive_name, drive_letter)
            if physicals:
                self.disk_combo.addItem("--- 物理存储介质 ---")
                for phy_id, phy_name in physicals:
                    self.disk_combo.addItem(phy_name, phy_id)
            self.disk_combo.addItem("打开虚拟磁盘...", "__open_vdisk__")
            self.disk_combo.blockSignals(False)
            self.disk_combo.currentIndexChanged.connect(self.on_disk_changed)
            # 自动加载第一个有效磁盘内容
            for i in range(self.disk_combo.count()):
                if self.disk_combo.itemData(i) and self.disk_combo.itemData(i) not in ("__open_vdisk__", None):
                    self.disk_combo.setCurrentIndex(i)
                    self.on_disk_changed(i)
                    break
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法获取磁盘列表: {str(e)}")
    
    def on_disk_changed(self, index):
        disk_id = self.disk_combo.itemData(index)
        if disk_id:
            try:
                if disk_id.startswith('\\\\.\\PhysicalDrive'):
                    # 读取物理磁盘的前几个扇区数据
                    start_sector = 0
                    end_sector = self.hex_editor.sectors_per_view - 1
                    data = DiskUtils.read_sector_range(disk_id, start_sector, end_sector)
                    sector_data = [data[i*512:(i+1)*512] for i in range(self.hex_editor.sectors_per_view)]
                    self.hex_editor.set_sector_data(sector_data, start_sector)
                elif disk_id == "__open_vdisk__":
                    file_name, _ = QFileDialog.getOpenFileName(self, "打开虚拟磁盘", "", "磁盘镜像 (*.vhd *.vmdk *.img *.bin);;所有文件 (*.*)")
                    if file_name:
                        try:
                            with open(file_name, 'rb') as f:
                                data = f.read(512 * self.hex_editor.sectors_per_view)
                            sector_data = [data[i*512:(i+1)*512] for i in range(self.hex_editor.sectors_per_view)]
                            self.hex_editor.set_sector_data(sector_data, 0)
                            self.current_disk = file_name  # 只保存文件路径
                            self.setWindowTitle(f"WinHex 克隆版 - 虚拟磁盘 {file_name}")
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"无法打开虚拟磁盘：{str(e)}")
                    return
                if disk_id and (disk_id.startswith("\\.\\") or (len(disk_id) == 2 and disk_id[1] == ':')):
                    try:
                        # 读取多个扇区
                        sector_size = 512
                        sectors_per_view = self.hex_editor.sectors_per_view
                        base_sector = 0
                        sector_data = []
                        for i in range(sectors_per_view):
                            try:
                                data = DiskUtils.read_sector(disk_id, base_sector + i, sector_size)
                            except Exception as e:
                                if disk_id.startswith('\\.\\PhysicalDrive'):
                                    QMessageBox.critical(self, "错误", "物理磁盘读取失败，请以管理员身份运行！")
                                    return
                                data = b'\x00' * sector_size
                            sector_data.append(data)
                        self.hex_editor.set_sector_data(sector_data, base_sector)
                        self.current_disk = disk_id  # 只保存盘符或物理磁盘路径
                        self.setWindowTitle(f"WinHex 克隆版 - 磁盘 {disk_id}")
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"无法打开磁盘: {str(e)}")
                else:
                    self.current_disk = None
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取磁盘数据：{str(e)}")
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        copy_action = QAction("复制", self)
        paste_action = QAction("粘贴", self)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        search_action = QAction("搜索", self)
        tools_menu.addAction(search_action)
    
    def goto_sector(self):
        """跳转到指定扇区"""
        if not self.current_disk:
            QMessageBox.warning(self, "警告", "请先选择一个磁盘")
            return
        
        dialog = SectorDialog(self)
        if dialog.exec():
            try:
                sector_number = int(dialog.sector_input.text())
                data = DiskUtils.read_sector(self.current_disk, sector_number)
                self.hex_editor.set_data(data)
                self.hex_editor.set_current_sector(sector_number)
                self.statusBar.showMessage(f"当前扇区: {sector_number}")
            except ValueError:
                QMessageBox.warning(self, "警告", "请输入有效的扇区号")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取扇区: {str(e)}")
    
    def goto_cluster(self):
        """跳转到指定簇"""
        if not self.current_disk:
            QMessageBox.warning(self, "警告", "请先选择一个磁盘")
            return
        
        dialog = ClusterDialog(self)
        if dialog.exec():
            try:
                cluster_number = int(dialog.cluster_input.text())
                data = DiskUtils.read_cluster(self.current_disk, cluster_number)
                self.hex_editor.set_data(data)
                self.hex_editor.set_current_cluster(cluster_number)
                self.statusBar.showMessage(f"当前簇: {cluster_number}")
            except ValueError:
                QMessageBox.warning(self, "警告", "请输入有效的簇号")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取簇: {str(e)}")
    
    def create_tool_bar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 添加工具栏按钮
        new_action = QAction("新建", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
    
    def new_file(self):
        self.hex_editor.set_data(bytearray())
        self.current_file = None
        self.current_disk = None
        self.setWindowTitle("WinHex 克隆版 - 未命名")
    
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "所有文件 (*.*)")
        if file_name:
            try:
                with open(file_name, 'rb') as f:
                    data = f.read()
                self.hex_editor.set_data(data)
                self.current_file = file_name
                self.current_disk = None
                self.setWindowTitle(f"WinHex 克隆版 - {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件：{str(e)}")
    
    def save_file(self):
        if not self.current_file:
            file_name, _ = QFileDialog.getSaveFileName(self, "保存文件", "", "所有文件 (*.*)")
            if not file_name:
                return
            self.current_file = file_name
        
        try:
            with open(self.current_file, 'wb') as f:
                f.write(self.hex_editor.data)
            self.setWindowTitle(f"WinHex 克隆版 - {self.current_file}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存文件：{str(e)}")

    def find_root_directory(self):
        """查找根目录"""
        if not self.current_disk:
            QMessageBox.warning(self, "警告", "请先选择一个磁盘")
            return
        
        try:
            root_dir_info = DiskUtils.find_root_directory(self.current_disk)
            QMessageBox.information(self, "结果", f"根目录信息: {root_dir_info}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查找根目录失败: {str(e)}")

    def read_sector_range(self):
        """读取指定扇区范围的数据"""
        if not self.current_disk:
            QMessageBox.warning(self, "警告", "请先选择一个磁盘")
            return
        
        dialog = SectorRangeDialog(self)  # 假设存在这个对话框类
        if dialog.exec():
            try:
                start_sector = int(dialog.start_sector_input.text())
                end_sector = int(dialog.end_sector_input.text())
                data = DiskUtils.read_sector_range(self.current_disk, start_sector, end_sector)
                self.hex_editor.set_data(data)
                self.statusBar.showMessage(f"已读取扇区 {start_sector} 到 {end_sector} 的数据")
            except ValueError:
                QMessageBox.warning(self, "警告", "请输入有效的扇区号")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取扇区范围失败: {str(e)}")

def main():
    app = QApplication(sys.argv)
    # 检查管理员权限
    try:
        is_admin = (os.name == 'nt' and ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        is_admin = False
    if not is_admin:
        QMessageBox.critical(None, "权限不足", "请以管理员身份重新运行本程序，否则无法访问物理磁盘！")
        sys.exit(1)
    window = WinHexClone()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()



