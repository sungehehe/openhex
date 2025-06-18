from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTableWidget, QTableWidgetItem, 
                            QHeaderView, QProgressBar, QFileDialog, QMessageBox,
                            QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
import os
import logging
from fat32_recovery import FAT32Recovery

class FAT32RecoveryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FAT32文件恢复")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #2c2c2c;
            }
            QLabel {
                color: #ffffff;
                font-size: 12pt;
                font-weight: normal;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #999999;
            }
            QTableWidget {
                border: 1px solid #555555;
                background-color: #1e1e1e;
                alternate-background-color: #2a2a2a;
                gridline-color: #555555;
                color: white;
                font-size: 11pt;
            }
            QTableWidget::item {
                padding: 5px;
                color: white;
            }
            QTableWidget::item:selected {
                background-color: #0078d7;
            }
            QHeaderView::section {
                background-color: #333333;
                padding: 5px;
                border: 1px solid #555555;
                font-weight: bold;
                font-size: 11pt;
                color: white;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                font-size: 10pt;
                color: white;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                width: 10px;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #1e1e1e;
                color: white;
                font-size: 11pt;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: white;
                selection-background-color: #0078d7;
            }
            QCheckBox {
                font-size: 11pt;
                color: white;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
        """)
        
        # 恢复工具实例
        self.recovery_tool = None
        self.deleted_files = []
        self.selected_disk = ""
        
        # 创建布局
        self.init_ui()
    
    def init_ui(self):
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 磁盘选择区域
        disk_layout = QHBoxLayout()
        self.disk_label = QLabel("选择FAT32分区:")
        self.disk_combo = QComboBox()
        self.scan_button = QPushButton("扫描已删除文件")
        self.scan_button.clicked.connect(self.scan_deleted_files)
        
        disk_layout.addWidget(self.disk_label)
        disk_layout.addWidget(self.disk_combo)
        disk_layout.addWidget(self.scan_button)
        disk_layout.addStretch()
        
        # 过滤选项
        filter_layout = QHBoxLayout()
        self.show_system_files = QCheckBox("显示系统文件")
        self.show_hidden_files = QCheckBox("显示隐藏文件")
        self.min_size_label = QLabel("最小文件大小(KB):")
        self.min_size_combo = QComboBox()
        self.min_size_combo.addItems(["0", "1", "10", "100", "1000"])
        
        # 添加文件类型过滤
        self.file_type_label = QLabel("文件类型:")
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItem("全部文件", "")
        self.file_type_combo.addItem("图片文件", "image")
        self.file_type_combo.addItem("文档文件", "document")
        self.file_type_combo.addItem("压缩文件", "archive")
        
        filter_layout.addWidget(self.show_system_files)
        filter_layout.addWidget(self.show_hidden_files)
        filter_layout.addWidget(self.min_size_label)
        filter_layout.addWidget(self.min_size_combo)
        filter_layout.addWidget(self.file_type_label)
        filter_layout.addWidget(self.file_type_combo)
        filter_layout.addStretch()
        
        # 连接过滤选项信号
        self.show_system_files.stateChanged.connect(self.apply_filters)
        self.show_hidden_files.stateChanged.connect(self.apply_filters)
        self.min_size_combo.currentIndexChanged.connect(self.apply_filters)
        self.file_type_combo.currentIndexChanged.connect(self.apply_filters)
        
        # 文件表格
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(6)
        self.files_table.setHorizontalHeaderLabels(["文件名", "路径", "大小", "创建时间", "起始簇", "恢复概率"])
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSortingEnabled(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # 底部按钮
        buttons_layout = QHBoxLayout()
        self.recover_selected_btn = QPushButton("恢复选中文件")
        self.recover_selected_btn.clicked.connect(self.recover_selected_files)
        self.recover_selected_btn.setEnabled(False)
        
        self.recover_all_btn = QPushButton("恢复全部文件")
        self.recover_all_btn.clicked.connect(self.recover_all_files)
        self.recover_all_btn.setEnabled(False)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        buttons_layout.addWidget(self.recover_selected_btn)
        buttons_layout.addWidget(self.recover_all_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.close_btn)
        
        # 将所有布局添加到主布局
        layout.addLayout(disk_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.files_table)
        layout.addWidget(self.progress_bar)
        layout.addLayout(buttons_layout)
        
        # 初始化磁盘列表
        self.init_disk_list()
    
    def init_disk_list(self):
        """初始化FAT32分区列表"""
        try:
            from disk_utils import DiskUtils
            drives = DiskUtils.get_disk_list()
            self.disk_combo.clear()
            
            for drive, label in drives:
                self.disk_combo.addItem(f"{label}", drive)
                
            if self.disk_combo.count() > 0:
                self.scan_button.setEnabled(True)
            else:
                self.scan_button.setEnabled(False)
                
        except Exception as e:
            logging.error(f"初始化磁盘列表失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"初始化磁盘列表失败: {str(e)}")
    
    def scan_deleted_files(self):
        """扫描分区中的已删除文件"""
        if self.disk_combo.count() == 0:
            return
            
        # 获取选中的磁盘
        self.selected_disk = self.disk_combo.currentData()
        if not self.selected_disk:
            return
            
        # 清空表格
        self.files_table.setRowCount(0)
        self.deleted_files = []
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(0)  # 不确定进度
        
        # 禁用按钮
        self.scan_button.setEnabled(False)
        self.recover_selected_btn.setEnabled(False)
        self.recover_all_btn.setEnabled(False)
        
        try:
            # 创建恢复工具实例
            self.recovery_tool = FAT32Recovery(self.selected_disk)
            
            # 扫描已删除文件
            self.deleted_files = self.recovery_tool.scan_for_deleted_files()
            
            # 恢复按钮状态
            self.scan_button.setEnabled(True)
            if self.deleted_files:
                self.recover_selected_btn.setEnabled(True)
                self.recover_all_btn.setEnabled(True)
            
            # 应用过滤器并显示文件
            self.apply_filters()
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 显示结果信息
            QMessageBox.information(self, "扫描完成", f"扫描完成，共找到 {len(self.deleted_files)} 个已删除文件。")
            
        except Exception as e:
            logging.error(f"扫描删除文件失败: {str(e)}")
            self.scan_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "错误", f"扫描删除文件失败: {str(e)}")
    
    def apply_filters(self):
        """应用过滤条件并更新表格"""
        if not self.deleted_files:
            return
            
        # 获取过滤条件
        show_system = self.show_system_files.isChecked()
        show_hidden = self.show_hidden_files.isChecked()
        try:
            min_size_kb = int(self.min_size_combo.currentText())
        except ValueError:
            min_size_kb = 0
            
        # 获取文件类型过滤
        file_type_filter = self.file_type_combo.currentData()
        
        # 清空表格
        self.files_table.setRowCount(0)
        
        # 过滤并显示文件
        filtered_files = []
        for file in self.deleted_files:
            # 过滤系统文件
            if file["is_system"] and not show_system:
                continue
                
            # 过滤隐藏文件
            if file["is_hidden"] and not show_hidden:
                continue
                
            # 过滤小文件
            if file["file_size"] < min_size_kb * 1024:
                continue
                
            # 过滤文件类型
            if file_type_filter:
                detected_type = file.get("detected_type", "")
                filename = file["filename"].lower()
                
                if file_type_filter == "image":
                    # 检查是否是图片类型
                    is_image = (
                        detected_type in ["jpg", "png", "gif", "bmp", "webp", "heic"] or
                        filename.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"))
                    )
                    if not is_image:
                        continue
                        
                elif file_type_filter == "document":
                    # 检查是否是文档类型
                    is_document = (
                        detected_type in ["pdf", "doc", "docx"] or
                        filename.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"))
                    )
                    if not is_document:
                        continue
                        
                elif file_type_filter == "archive":
                    # 检查是否是压缩文件类型
                    is_archive = (
                        detected_type in ["zip", "rar", "7z"] or
                        filename.endswith((".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"))
                    )
                    if not is_archive:
                        continue
                
            filtered_files.append(file)
        
        # 更新表格
        self.files_table.setRowCount(len(filtered_files))
        for i, file in enumerate(filtered_files):
            # 文件名
            self.files_table.setItem(i, 0, QTableWidgetItem(file["filename"]))
            
            # 路径
            self.files_table.setItem(i, 1, QTableWidgetItem(file["path"]))
            
            # 文件大小
            size_str = self.format_file_size(file["file_size"])
            self.files_table.setItem(i, 2, QTableWidgetItem(size_str))
            
            # 创建时间
            if self.recovery_tool:
                time_str = self.recovery_tool.format_fat_time(file["create_time"], file["create_date"])
                self.files_table.setItem(i, 3, QTableWidgetItem(time_str))
            else:
                self.files_table.setItem(i, 3, QTableWidgetItem("未知"))
            
            # 起始簇
            self.files_table.setItem(i, 4, QTableWidgetItem(str(file["start_cluster"])))
            
            # 恢复概率 (简单估计)
            recovery_chance = self.estimate_recovery_chance(file)
            self.files_table.setItem(i, 5, QTableWidgetItem(recovery_chance))
    
    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} 字节"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def estimate_recovery_chance(self, file: dict) -> str:
        """估计文件恢复的成功概率"""
        # 简单估计，实际应根据文件系统状态、文件碎片化程度等进行更复杂的评估
        if file["file_size"] == 0:
            return "高"  # 空文件容易恢复
            
        if file["start_cluster"] < 2:
            return "低"  # 无效的起始簇号
        
        # 按文件大小简单估计，小文件恢复概率高，大文件可能碎片化
        if file["file_size"] < 1024 * 10:  # 10KB以下
            return "高"
        elif file["file_size"] < 1024 * 1024:  # 1MB以下
            return "中"
        else:
            return "低"
    
    def recover_selected_files(self):
        """恢复选中的文件"""
        selected_rows = self.files_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要恢复的文件")
            return
            
        # 选择恢复目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择恢复文件保存目录")
        if not output_dir:
            return
            
        # 进度条设置
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_rows))
        self.progress_bar.setValue(0)
        
        # 禁用按钮
        self.scan_button.setEnabled(False)
        self.recover_selected_btn.setEnabled(False)
        self.recover_all_btn.setEnabled(False)
        
        try:
            recovered_count = 0
            failed_count = 0
            
            for i, row in enumerate(selected_rows):
                row_idx = row.row()
                
                # 获取文件名和路径
                filename = self.files_table.item(row_idx, 0).text()
                path = self.files_table.item(row_idx, 1).text()
                
                # 在原始删除文件列表中查找对应的文件
                file_to_recover = None
                for file in self.deleted_files:
                    if file["filename"] == filename and file["path"] == path:
                        file_to_recover = file
                        break
                
                if file_to_recover:
                    # 创建恢复路径
                    full_path = os.path.join(path, filename).strip("\\").strip("/")
                    output_path = os.path.join(output_dir, full_path)
                    
                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    
                    # 恢复文件
                    if self.recovery_tool.recover_file(file_to_recover, output_path):
                        recovered_count += 1
                    else:
                        failed_count += 1
                
                # 更新进度条
                self.progress_bar.setValue(i + 1)
            
            # 恢复按钮状态
            self.scan_button.setEnabled(True)
            self.recover_selected_btn.setEnabled(True)
            self.recover_all_btn.setEnabled(True)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 显示结果信息
            QMessageBox.information(self, "恢复完成", 
                                   f"恢复完成，成功: {recovered_count}，失败: {failed_count}")
            
        except Exception as e:
            logging.error(f"恢复文件失败: {str(e)}")
            self.scan_button.setEnabled(True)
            self.recover_selected_btn.setEnabled(True)
            self.recover_all_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "错误", f"恢复文件失败: {str(e)}")
    
    def recover_all_files(self):
        """恢复所有文件"""
        if not self.deleted_files:
            QMessageBox.warning(self, "警告", "没有可恢复的文件")
            return
            
        # 确认是否恢复所有文件
        reply = QMessageBox.question(self, "确认", 
                                    f"确定要恢复所有 {len(self.deleted_files)} 个已删除文件吗？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # 选择恢复目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择恢复文件保存目录")
        if not output_dir:
            return
            
        # 进度条设置
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.deleted_files))
        self.progress_bar.setValue(0)
        
        # 禁用按钮
        self.scan_button.setEnabled(False)
        self.recover_selected_btn.setEnabled(False)
        self.recover_all_btn.setEnabled(False)
        
        try:
            recovered_count = 0
            failed_count = 0
            
            for i, file in enumerate(self.deleted_files):
                # 创建恢复路径
                full_path = os.path.join(file["path"], file["filename"]).strip("\\").strip("/")
                output_path = os.path.join(output_dir, full_path)
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                
                # 恢复文件
                if self.recovery_tool.recover_file(file, output_path):
                    recovered_count += 1
                else:
                    failed_count += 1
                
                # 更新进度条
                self.progress_bar.setValue(i + 1)
            
            # 恢复按钮状态
            self.scan_button.setEnabled(True)
            self.recover_selected_btn.setEnabled(True)
            self.recover_all_btn.setEnabled(True)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 显示结果信息
            QMessageBox.information(self, "恢复完成", 
                                   f"恢复完成，成功: {recovered_count}，失败: {failed_count}")
            
        except Exception as e:
            logging.error(f"恢复文件失败: {str(e)}")
            self.scan_button.setEnabled(True)
            self.recover_selected_btn.setEnabled(True)
            self.recover_all_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "错误", f"恢复文件失败: {str(e)}") 