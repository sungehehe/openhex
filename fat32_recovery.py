import os
import struct
import logging
from typing import List, Dict, Tuple, Optional, BinaryIO
from datetime import datetime

class FAT32Recovery:
    """FAT32文件系统删除文件恢复类"""
    
    # FAT32文件系统常量
    FAT_ENTRY_SIZE = 4  # FAT32表项大小为4字节
    DIR_ENTRY_SIZE = 32  # 目录项大小为32字节
    DELETED_MARKER = 0xE5  # 删除文件标记
    LFN_ATTR = 0x0F  # 长文件名属性标记
    
    # 文件签名定义（文件头魔数）
    FILE_SIGNATURES = {
        # 图片文件
        'jpg': [b'\xFF\xD8\xFF', b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xE1'],
        'png': [b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'],
        'gif': [b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61'],
        'bmp': [b'\x42\x4D'],
        'webp': [b'\x52\x49\x46\x46....WEBP'],  # RIFF....WEBP
        'heic': [b'\x00\x00\x00\x18\x66\x74\x79\x70\x68\x65\x69\x63'],
        # 文档文件
        'pdf': [b'\x25\x50\x44\x46'],  # %PDF
        'doc': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],
        'docx': [b'\x50\x4B\x03\x04'],  # DOCX/XLSX/PPTX都是ZIP格式
        # 压缩文件
        'zip': [b'\x50\x4B\x03\x04'],
        'rar': [b'\x52\x61\x72\x21\x1A\x07'],
        '7z': [b'\x37\x7A\xBC\xAF\x27\x1C'],
    }
    
    # 文件结尾签名
    FILE_EOF_SIGNATURES = {
        'jpg': [b'\xFF\xD9'],
        'png': [b'\x49\x45\x4E\x44\xAE\x42\x60\x82'],  # IEND块
    }
    
    def __init__(self, disk_path: str):
        """初始化FAT32恢复器
        
        Args:
            disk_path: 磁盘路径，可以是分区(C:)或物理磁盘(\\\\.\\PhysicalDrive0)
        """
        self.disk_path = disk_path
        self.disk_handle = None
        self.bytes_per_sector = 0
        self.sectors_per_cluster = 0
        self.reserved_sectors = 0
        self.number_of_fats = 0
        self.root_dir_sectors = 0
        self.sectors_per_fat = 0
        self.root_cluster = 0
        self.fat_begin_lba = 0
        self.cluster_begin_lba = 0
        self.total_sectors = 0
        self.fat_size = 0
        self.data_sectors = 0
        self.count_of_clusters = 0
        
        # 已删除的文件列表
        self.deleted_files = []
        
    def open_disk(self):
        """打开磁盘设备"""
        try:
            if len(self.disk_path) == 2 and self.disk_path[1] == ':':
                # 如果是分区，使用\\.\C: 格式
                self.disk_handle = open(f"\\\\.\\{self.disk_path}", "rb")
            else:
                # 否则直接打开
                self.disk_handle = open(self.disk_path, "rb")
            return True
        except Exception as e:
            logging.error(f"打开磁盘失败: {str(e)}")
            return False
    
    def close_disk(self):
        """关闭磁盘设备"""
        if self.disk_handle:
            self.disk_handle.close()
            self.disk_handle = None
    
    def read_sector(self, sector_number: int) -> bytes:
        """读取指定扇区数据
        
        Args:
            sector_number: 扇区编号
            
        Returns:
            扇区数据
        """
        if not self.disk_handle:
            raise Exception("磁盘未打开")
            
        # 使用默认扇区大小512字节读取第一个扇区
        if sector_number == 0 and self.bytes_per_sector == 0:
            self.disk_handle.seek(0)
            return self.disk_handle.read(512)
            
        # 对于其他扇区，使用已知的扇区大小
        bytes_per_sector = self.bytes_per_sector if self.bytes_per_sector > 0 else 512
        self.disk_handle.seek(sector_number * bytes_per_sector)
        return self.disk_handle.read(bytes_per_sector)
    
    def read_sectors(self, start_sector: int, count: int) -> bytes:
        """读取多个连续扇区
        
        Args:
            start_sector: 起始扇区编号
            count: 扇区数量
            
        Returns:
            连续扇区数据
        """
        if not self.disk_handle:
            raise Exception("磁盘未打开")
            
        bytes_per_sector = self.bytes_per_sector if self.bytes_per_sector > 0 else 512
        self.disk_handle.seek(start_sector * bytes_per_sector)
        return self.disk_handle.read(count * bytes_per_sector)
    
    def read_cluster(self, cluster_number: int) -> bytes:
        """读取指定簇数据
        
        Args:
            cluster_number: 簇编号(从2开始)
            
        Returns:
            簇数据
        """
        if cluster_number < 2:
            raise ValueError(f"无效的簇号: {cluster_number}")
            
        # 计算簇对应的起始扇区
        first_sector_of_cluster = self.cluster_begin_lba + (cluster_number - 2) * self.sectors_per_cluster
        
        # 读取整个簇的所有扇区
        return self.read_sectors(first_sector_of_cluster, self.sectors_per_cluster)
    
    def parse_boot_sector(self) -> bool:
        """解析FAT32引导扇区，获取文件系统参数
        
        Returns:
            解析是否成功
        """
        try:
            # 读取引导扇区(扇区0)
            boot_sector = self.read_sector(0)
            
            # 检查文件系统类型
            # 设置bytes_per_sector的初始值，以便后续的seek操作正常工作
            self.bytes_per_sector = struct.unpack("<H", boot_sector[11:13])[0]
            if self.bytes_per_sector == 0 or self.bytes_per_sector > 4096:
                self.bytes_per_sector = 512  # 使用默认值
            
            # 更灵活的FAT32检测
            # 1. 检查FAT32字符串
            fs_type = boot_sector[82:90]
            # 2. 检查FAT32特有的簇号字段
            root_cluster = struct.unpack("<I", boot_sector[44:48])[0]
            # 3. 检查保留扇区数（FAT32通常大于32）
            reserved_sectors = struct.unpack("<H", boot_sector[14:16])[0]
            
            # 如果满足以下任意条件，则认为是FAT32
            if not (fs_type == b'FAT32   ' or 
                   (root_cluster >= 2 and reserved_sectors >= 32)):
                # 尝试读取DBR扇区（FAT32的备份引导扇区通常在扇区6）
                try:
                    backup_boot = self.read_sector(6)
                    backup_fs_type = backup_boot[82:90]
                    if backup_fs_type == b'FAT32   ':
                        # 使用备份引导扇区的数据
                        boot_sector = backup_boot
                    else:
                        raise Exception("不是FAT32文件系统")
                except:
                    raise Exception("不是FAT32文件系统")
            
            # 解析BPB(BIOS Parameter Block)
            self.bytes_per_sector = struct.unpack("<H", boot_sector[11:13])[0]
            self.sectors_per_cluster = boot_sector[13]
            self.reserved_sectors = struct.unpack("<H", boot_sector[14:16])[0]
            self.number_of_fats = boot_sector[16]
            self.root_dir_sectors = 0  # FAT32中为0
            
            # 使用不同字段获取总扇区数（偏移32或偏移28）
            self.total_sectors = struct.unpack("<I", boot_sector[32:36])[0]
            if self.total_sectors == 0:
                self.total_sectors = struct.unpack("<H", boot_sector[19:21])[0]
                
            self.sectors_per_fat = struct.unpack("<I", boot_sector[36:40])[0]
            self.root_cluster = struct.unpack("<I", boot_sector[44:48])[0]
            
            # 检查参数合理性
            if self.bytes_per_sector == 0 or self.sectors_per_cluster == 0 or self.root_cluster < 2:
                raise Exception("FAT32参数无效")
                
            # 计算重要区域的位置
            self.fat_begin_lba = self.reserved_sectors
            self.cluster_begin_lba = self.fat_begin_lba + (self.number_of_fats * self.sectors_per_fat)
            
            # 计算FAT大小和簇数量
            self.fat_size = self.sectors_per_fat * self.bytes_per_sector
            self.data_sectors = self.total_sectors - self.cluster_begin_lba
            self.count_of_clusters = self.data_sectors // self.sectors_per_cluster
            
            logging.info(f"FAT32参数: 每扇区字节={self.bytes_per_sector}, 每簇扇区数={self.sectors_per_cluster}")
            logging.info(f"FAT32参数: FAT表数量={self.number_of_fats}, 每FAT扇区数={self.sectors_per_fat}")
            logging.info(f"FAT32参数: 根目录簇={self.root_cluster}, 总簇数={self.count_of_clusters}")
            
            return True
            
        except Exception as e:
            logging.error(f"解析引导扇区失败: {str(e)}")
            return False
    
    def read_fat_entry(self, cluster: int) -> int:
        """读取FAT表中的表项值
        
        Args:
            cluster: 簇号
            
        Returns:
            FAT表项值，指向下一个簇的簇号
        """
        if cluster < 2 or cluster >= self.count_of_clusters + 2:
            return 0x0FFFFFFF  # 链接结束标记
            
        # 计算FAT表项在FAT表中的偏移
        fat_offset = cluster * 4  # 每个FAT32表项4字节
        
        # 计算包含该表项的扇区
        fat_sector = self.fat_begin_lba + (fat_offset // self.bytes_per_sector)
        
        # 计算表项在扇区内的偏移
        entry_offset = fat_offset % self.bytes_per_sector
        
        # 读取扇区
        fat_sector_data = self.read_sector(fat_sector)
        
        # 提取FAT表项的值
        return struct.unpack("<I", fat_sector_data[entry_offset:entry_offset+4])[0] & 0x0FFFFFFF
    
    def get_cluster_chain(self, start_cluster: int) -> List[int]:
        """获取簇链
        
        Args:
            start_cluster: 起始簇号
            
        Returns:
            簇链列表
        """
        if start_cluster < 2:
            return []
            
        cluster_chain = [start_cluster]
        next_cluster = self.read_fat_entry(start_cluster)
        
        # FAT32中，0x0FFFFFF8-0x0FFFFFFF表示链接结束
        while next_cluster < 0x0FFFFFF8:
            cluster_chain.append(next_cluster)
            next_cluster = self.read_fat_entry(next_cluster)
            
            # 防止无限循环(簇链损坏)
            if len(cluster_chain) > 1000000:  # 设置一个合理的最大长度
                break
                
        return cluster_chain
    
    def parse_directory_entry(self, entry_data: bytes) -> Dict:
        """解析目录项
        
        Args:
            entry_data: 32字节的目录项数据
            
        Returns:
            目录项信息字典
        """
        # 检查第一个字节
        first_byte = entry_data[0]
        
        # 0x00表示未使用，0xE5表示已删除
        if first_byte == 0x00:
            return None
            
        # 检查是否是长文件名项
        attr = entry_data[11]
        if attr == self.LFN_ATTR:
            return {
                "is_lfn": True,
                "lfn_data": entry_data,
                "lfn_order": first_byte & 0x3F,
                "is_last": (first_byte & 0x40) > 0,
                "is_deleted": first_byte == self.DELETED_MARKER
            }
            
        # 标记删除状态
        is_deleted = (first_byte == self.DELETED_MARKER)
        
        # 提取文件名(8+3格式)
        name = entry_data[0:8].decode('ascii', errors='replace').strip()
        ext = entry_data[8:11].decode('ascii', errors='replace').strip()
        
        # 如果是删除的文件，修复第一个字符
        if is_deleted:
            name = '_' + name[1:]
            
        # 组合完整文件名
        if ext:
            filename = f"{name}.{ext}".strip()
        else:
            filename = name.strip()
            
        # 提取文件属性
        is_directory = (attr & 0x10) > 0
        is_system = (attr & 0x04) > 0
        is_hidden = (attr & 0x02) > 0
        
        # 提取创建时间和日期
        create_time = struct.unpack("<H", entry_data[14:16])[0]
        create_date = struct.unpack("<H", entry_data[16:18])[0]
        
        # 提取文件大小
        file_size = struct.unpack("<I", entry_data[28:32])[0]
        
        # 提取起始簇号(FAT32中簇号为4字节，分高2字节和低2字节存储)
        cluster_low = struct.unpack("<H", entry_data[26:28])[0]
        cluster_high = struct.unpack("<H", entry_data[20:22])[0]
        start_cluster = (cluster_high << 16) + cluster_low
        
        # 返回目录项信息
        return {
            "filename": filename,
            "is_deleted": is_deleted,
            "is_directory": is_directory,
            "is_system": is_system,
            "is_hidden": is_hidden,
            "file_size": file_size,
            "start_cluster": start_cluster,
            "create_time": create_time,
            "create_date": create_date,
            "raw_entry": entry_data,
            "is_lfn": False
        }
    
    def extract_lfn_text(self, lfn_entries: List[Dict]) -> str:
        """从长文件名条目中提取完整的文件名
        
        Args:
            lfn_entries: 长文件名条目列表，按顺序排列
            
        Returns:
            完整的文件名
        """
        # 按序号排序长文件名条目
        lfn_entries.sort(key=lambda x: x["lfn_order"])
        
        # 提取长文件名
        lfn_name = ""
        for entry in lfn_entries:
            data = entry["lfn_data"]
            
            # 长文件名分三段存储：1-10, 14-25, 28-31字节
            name_part1 = data[1:11]  # 5个字符
            name_part2 = data[14:26]  # 6个字符
            name_part3 = data[28:32]  # 2个字符
            
            # 合并所有部分
            name_parts = name_part1 + name_part2 + name_part3
            
            # 按2字节解码为UTF-16LE
            for i in range(0, len(name_parts), 2):
                char_value = name_parts[i] + (name_parts[i+1] << 8)
                # 0xFFFF和0x0000是填充符或结束符
                if char_value != 0xFFFF and char_value != 0x0000:
                    lfn_name += chr(char_value)
        
        return lfn_name
    
    def format_fat_time(self, time_value: int, date_value: int) -> str:
        """格式化FAT时间和日期
        
        Args:
            time_value: FAT时间值
            date_value: FAT日期值
            
        Returns:
            格式化的时间字符串
        """
        # 从FAT时间值提取时分秒
        hour = (time_value >> 11) & 0x1F
        minute = (time_value >> 5) & 0x3F
        second = (time_value & 0x1F) * 2
        
        # 从FAT日期值提取年月日
        year = ((date_value >> 9) & 0x7F) + 1980
        month = (date_value >> 5) & 0x0F
        day = date_value & 0x1F
        
        try:
            dt = datetime(year, month, day, hour, minute, second)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return "无效日期"
    
    def scan_directory(self, cluster: int, path: str = "") -> List[Dict]:
        """扫描目录，查找已删除的文件
        
        Args:
            cluster: 目录起始簇号
            path: 当前目录路径
            
        Returns:
            目录中的文件列表
        """
        files = []
        
        # 获取目录的簇链
        cluster_chain = self.get_cluster_chain(cluster)
        if not cluster_chain:
            return files
            
        # 遍历簇链中的每个簇
        for current_cluster in cluster_chain:
            # 读取簇数据
            cluster_data = self.read_cluster(current_cluster)
            
            # 用于保存长文件名条目
            lfn_entries = []
            is_deleted_lfn = False
            
            # 遍历簇中的每个目录项
            i = 0
            while i < len(cluster_data):
                if i + self.DIR_ENTRY_SIZE > len(cluster_data):
                    break
                    
                entry_data = cluster_data[i:i+self.DIR_ENTRY_SIZE]
                
                # 解析目录项
                entry = self.parse_directory_entry(entry_data)
                if not entry:
                    i += self.DIR_ENTRY_SIZE
                    continue
                
                # 如果是长文件名条目
                if entry.get("is_lfn", False):
                    if entry["is_deleted"]:
                        is_deleted_lfn = True
                    lfn_entries.append(entry)
                    i += self.DIR_ENTRY_SIZE
                    continue
                
                # 处理普通文件或目录条目
                filename = entry["filename"]
                
                # 如果有长文件名条目，提取完整的长文件名
                if lfn_entries:
                    lfn_filename = self.extract_lfn_text(lfn_entries)
                    if lfn_filename:
                        entry["long_filename"] = lfn_filename
                        # 使用长文件名替换短文件名
                        filename = lfn_filename
                        entry["filename"] = lfn_filename
                        
                    # 如果是删除的长文件名，标记文件为已删除
                    if is_deleted_lfn:
                        entry["is_deleted"] = True
                    
                    # 清空长文件名条目列表，准备处理下一个文件
                    lfn_entries = []
                    is_deleted_lfn = False
                
                # 跳过. 和 .. 目录
                if filename in [".", ".."]:
                    i += self.DIR_ENTRY_SIZE
                    continue
                    
                # 添加完整路径
                entry["path"] = path
                full_path = os.path.join(path, filename)
                entry["full_path"] = full_path
                
                # 添加到文件列表
                files.append(entry)
                
                # 如果是目录，递归扫描
                if entry["is_directory"] and not entry["is_deleted"] and entry["start_cluster"] >= 2:
                    subdir_files = self.scan_directory(entry["start_cluster"], full_path)
                    files.extend(subdir_files)
                
                i += self.DIR_ENTRY_SIZE
        
        return files
    
    def scan_for_deleted_files(self) -> List[Dict]:
        """扫描整个分区查找已删除的文件
        
        Returns:
            已删除的文件列表
        """
        if not self.open_disk():
            logging.error("无法打开磁盘")
            return []
            
        try:
            # 解析引导扇区
            if not self.parse_boot_sector():
                logging.error("解析引导扇区失败，尝试使用默认参数")
                # 使用一些常见默认参数
                self.bytes_per_sector = 512
                self.sectors_per_cluster = 8
                self.reserved_sectors = 32
                self.number_of_fats = 2
                self.sectors_per_fat = 8192  # 这是一个较大的值，以覆盖大多数FAT32分区
                self.root_cluster = 2  # FAT32的根目录通常从簇2开始
                
                # 计算重要区域的位置
                self.fat_begin_lba = self.reserved_sectors
                self.cluster_begin_lba = self.fat_begin_lba + (self.number_of_fats * self.sectors_per_fat)
                
                # 计算FAT大小和簇数量
                self.fat_size = self.sectors_per_fat * self.bytes_per_sector
                self.data_sectors = 1000000  # 假设一个较大的值
                self.count_of_clusters = self.data_sectors // self.sectors_per_cluster
                
                logging.info(f"使用默认FAT32参数: 每扇区字节={self.bytes_per_sector}, 每簇扇区数={self.sectors_per_cluster}")
                
            # 从根目录开始扫描
            logging.info(f"开始从根目录簇 {self.root_cluster} 扫描文件")
            all_files = []
            
            # 尝试从根目录扫描
            try:
                root_files = self.scan_directory(self.root_cluster, "")
                all_files.extend(root_files)
            except Exception as e:
                logging.error(f"从根目录扫描失败: {str(e)}")
            
            # 如果从根目录扫描失败或没有找到文件，尝试扫描常见的起始簇
            if not all_files:
                logging.info("从根目录未找到文件，尝试扫描其他可能的目录簇")
                for cluster in range(2, min(100, self.count_of_clusters)):  # 尝试前100个簇
                    try:
                        cluster_files = self.scan_directory(cluster, f"/未知目录_{cluster}")
                        if cluster_files:
                            logging.info(f"在簇 {cluster} 找到 {len(cluster_files)} 个文件")
                            all_files.extend(cluster_files)
                    except Exception as e:
                        logging.debug(f"扫描簇 {cluster} 失败: {str(e)}")
            
            # 过滤出已删除的文件
            self.deleted_files = [f for f in all_files if f.get("is_deleted", False)]
            
            # 基于文件签名添加识别出的文件类型信息
            for file in self.deleted_files:
                try:
                    if file["start_cluster"] >= 2:
                        cluster_data = self.read_cluster(file["start_cluster"])
                        detected_type = self.detect_file_type_by_signature(cluster_data[:50])
                        if detected_type:
                            file["detected_type"] = detected_type
                except Exception as e:
                    logging.debug(f"检测文件类型失败: {str(e)}")
            
            # 按路径排序
            self.deleted_files.sort(key=lambda x: x["full_path"])
            
            logging.info(f"扫描完成，共找到 {len(self.deleted_files)} 个已删除文件")
            return self.deleted_files
            
        except Exception as e:
            logging.error(f"扫描删除文件失败: {str(e)}")
            return []
            
        finally:
            self.close_disk()
    
    def detect_file_type_by_signature(self, data: bytes) -> str:
        """根据文件签名检测文件类型
        
        Args:
            data: 文件开头的数据
            
        Returns:
            文件类型，如jpg、png等，无法识别时返回空字符串
        """
        for ext, signatures in self.FILE_SIGNATURES.items():
            for sig in signatures:
                if b'....' in sig:  # 处理带通配符的签名
                    parts = sig.split(b'....')
                    if data.startswith(parts[0]) and parts[1] in data[:50]:
                        return ext
                elif data.startswith(sig):
                    return ext
        return ""
    
    def find_next_cluster_by_content(self, current_cluster: int, file_type: str) -> int:
        """根据内容相似性寻找下一个可能的簇
        
        Args:
            current_cluster: 当前簇号
            file_type: 文件类型
            
        Returns:
            可能的下一个簇号，如果找不到返回0
        """
        try:
            # 读取当前簇的数据
            current_data = self.read_cluster(current_cluster)
            
            # 计算当前簇所在区域的附近簇，优先检查
            nearby_clusters = []
            for i in range(1, 10):  # 检查前后10个簇
                if current_cluster + i < self.count_of_clusters + 2:
                    nearby_clusters.append(current_cluster + i)
                if current_cluster - i >= 2:
                    nearby_clusters.append(current_cluster - i)
            
            # 遍历附近的簇，查找可能的下一个簇
            for next_cluster in nearby_clusters:
                # 跳过已分配的簇（FAT表项不为0）
                if self.read_fat_entry(next_cluster) != 0:
                    continue
                    
                # 读取下一个簇的数据
                next_data = self.read_cluster(next_cluster)
                
                # 检查文件尾部特征
                if file_type in self.FILE_EOF_SIGNATURES:
                    for sig in self.FILE_EOF_SIGNATURES[file_type]:
                        if sig in next_data:
                            return next_cluster
                
                # 对于JPEG文件，寻找JPEG标记
                if file_type == 'jpg':
                    # 查找JPEG标记(0xFF后跟0xD0-0xD9或0xE0-0xEF)
                    for i in range(len(next_data) - 1):
                        if next_data[i] == 0xFF and (0xD0 <= next_data[i+1] <= 0xD9 or 0xE0 <= next_data[i+1] <= 0xEF):
                            return next_cluster
                
                # 对于PNG文件，寻找PNG块结构
                if file_type == 'png':
                    # 查找PNG块格式(4字节长度+4字节类型)
                    for i in range(0, len(next_data) - 8, 4):
                        if next_data[i+4:i+8] in [b'IDAT', b'IEND', b'PLTE', b'tRNS', b'gAMA']:
                            return next_cluster
            
            return 0  # 找不到合适的下一个簇
        except Exception as e:
            logging.error(f"查找下一个簇失败: {str(e)}")
            return 0
    
    def recover_file(self, deleted_file: Dict, output_path: str) -> bool:
        """恢复已删除的文件
        
        Args:
            deleted_file: 已删除的文件信息
            output_path: 输出文件路径
            
        Returns:
            恢复是否成功
        """
        if not deleted_file or not deleted_file["is_deleted"]:
            return False
            
        if not self.open_disk():
            return False
            
        try:
            # 解析引导扇区
            if not self.parse_boot_sector():
                return False
                
            # 获取文件的簇链
            start_cluster = deleted_file["start_cluster"]
            if start_cluster < 2:
                raise Exception(f"无效的起始簇号: {start_cluster}")
                
            # 文件大小和每簇字节数
            file_size = deleted_file["file_size"]
            bytes_per_cluster = self.bytes_per_sector * self.sectors_per_cluster
            
            # 创建输出目录
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # 写入恢复的文件
            with open(output_path, "wb") as out_file:
                # 读取起始簇
                current_data = self.read_cluster(start_cluster)
                
                # 检测文件类型（基于签名）
                file_ext = os.path.splitext(output_path)[1].lower().lstrip('.')
                detected_type = self.detect_file_type_by_signature(current_data[:50])
                
                # 如果文件扩展名不匹配，但检测到了类型，则修改输出路径
                if detected_type and not file_ext:
                    output_path = f"{output_path}.{detected_type}"
                    logging.info(f"检测到文件类型: {detected_type}, 输出路径更新为: {output_path}")
                elif detected_type and file_ext != detected_type:
                    logging.info(f"检测到文件类型({detected_type})与扩展名({file_ext})不匹配，使用检测到的类型")
                
                # 使用检测到的类型，如果有的话
                file_type = detected_type if detected_type else file_ext
                
                # 如果文件小于一个簇的大小，只写入实际文件大小的数据
                if file_size <= bytes_per_cluster:
                    out_file.write(current_data[:file_size])
                else:
                    # 写入第一个簇
                    out_file.write(current_data)
                    
                    # 尝试基于内容相似性恢复簇链
                    bytes_written = bytes_per_cluster
                    current_cluster = start_cluster
                    
                    # 最多尝试恢复所需的簇数量（加上一点余量）
                    max_clusters = (file_size + bytes_per_cluster - 1) // bytes_per_cluster + 10
                    cluster_count = 1
                    
                    while bytes_written < file_size and cluster_count < max_clusters:
                        # 尝试找到下一个簇
                        next_cluster = self.find_next_cluster_by_content(current_cluster, file_type)
                        
                        # 如果找不到下一个簇，就退出循环
                        if next_cluster == 0:
                            break
                            
                        # 读取下一个簇
                        next_data = self.read_cluster(next_cluster)
                        
                        # 计算本次需要写入的字节数
                        bytes_to_write = min(bytes_per_cluster, file_size - bytes_written)
                        
                        # 写入数据
                        out_file.write(next_data[:bytes_to_write])
                        bytes_written += bytes_to_write
                        
                        # 更新当前簇
                        current_cluster = next_cluster
                        cluster_count += 1
                        
                        # 如果发现文件结尾签名，提前结束
                        if file_type in self.FILE_EOF_SIGNATURES:
                            for sig in self.FILE_EOF_SIGNATURES[file_type]:
                                if sig in next_data:
                                    return True
            
            # 尝试进行简单恢复（假设簇是连续的）
            if bytes_written < file_size:
                logging.warning(f"基于内容的恢复未完成，尝试连续簇恢复，已恢复: {bytes_written}/{file_size} 字节")
                
                with open(output_path, "ab") as out_file:
                    # 计算还需要读取的簇数
                    remaining_bytes = file_size - bytes_written
                    clusters_needed = (remaining_bytes + bytes_per_cluster - 1) // bytes_per_cluster
                    
                    # 假设簇是连续的，读取后续簇
                    for i in range(1, clusters_needed + 1):
                        next_cluster = start_cluster + i
                        if next_cluster >= self.count_of_clusters + 2:
                            break
                            
                        # 读取下一个簇
                        next_data = self.read_cluster(next_cluster)
                        
                        # 计算本次需要写入的字节数
                        bytes_to_write = min(bytes_per_cluster, file_size - bytes_written)
                        
                        # 写入数据
                        out_file.write(next_data[:bytes_to_write])
                        bytes_written += bytes_to_write
                        
                        # 如果已写入足够的数据，停止
                        if bytes_written >= file_size:
                            break
            
            logging.info(f"文件恢复完成: {output_path}, 恢复了 {bytes_written}/{file_size} 字节")
            return True
            
        except Exception as e:
            logging.error(f"恢复文件失败: {str(e)}")
            return False
            
        finally:
            self.close_disk() 