import logging
import win32api
import win32file
import string
from typing import List, Tuple

class DiskUtils:
    @staticmethod
    def get_disk_list() -> List[Tuple[str, str]]:
        """获取所有可用的磁盘驱动器列表"""
        drives = []
        bitmask = win32api.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                try:
                    drive_type = win32file.GetDriveType(f"{letter}:")
                    if drive_type == win32file.DRIVE_FIXED:  # 只显示固定磁盘
                        drives.append((f"{letter}:", f"本地磁盘 ({letter}:)"))
                except Exception as e:
                    logging.error(f"获取磁盘 {letter}: 信息时出错: {str(e)}")
            bitmask >>= 1
        return drives

    @staticmethod
    def open_disk(drive_letter: str) -> bytes:
        """打开指定磁盘并读取数据"""
        logging.info(f"尝试打开磁盘: {drive_letter}")
        try:
            # 确保drive_letter格式正确
            if not (len(drive_letter) == 2 and drive_letter[1] == ':'):
                raise ValueError(f"无效的驱动器盘符格式: {drive_letter}")
            
            # 尝试使用win32file方式读取
            try:
                logging.info(f"尝试使用win32file方式读取: {drive_letter}")
                handle = win32file.CreateFile(
                    f"\\\\.\\{drive_letter}",
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                data = win32file.ReadFile(handle, 512)[1]
                handle.Close()
                if data:
                    logging.info(f"win32file方式读取成功，数据长度: {len(data)}")
                    return data
            except Exception as e:
                logging.error(f"win32file方式读取失败: {str(e)}")
            
            # 如果win32file方式失败，尝试使用open方式
            logging.info(f"尝试使用open方式读取: {drive_letter}")
            with open(drive_letter, "rb") as f:
                data = f.read(512)
                if not data:
                    raise ValueError("读取到的数据为空")
                logging.info(f"open方式读取成功，数据长度: {len(data)}")
                return data
        except Exception as e:
            logging.error(f"打开磁盘失败: {str(e)}")
            raise

    @staticmethod
    def read_sector(disk_path: str, sector_number: int, sector_size: int = 512) -> bytes:
        """读取指定扇区的数据，支持分区、物理磁盘、虚拟磁盘文件"""
        logging.info(f"尝试读取扇区: {disk_path}, 扇区号: {sector_number}")
        try:
            # 物理磁盘
            if disk_path.startswith('\\\\.\\PhysicalDrive'):
                open_path = disk_path
                logging.info(f"使用win32file读取物理磁盘: {open_path}")
                try:
                    handle = win32file.CreateFile(
                        open_path,
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    win32file.SetFilePointer(handle, sector_number * sector_size, win32file.FILE_BEGIN)
                    data = win32file.ReadFile(handle, sector_size)[1]
                    handle.Close()
                    if not data:
                        raise ValueError("读取到的数据为空")
                    logging.info(f"物理磁盘读取成功，数据长度: {len(data)}")
                    return data
                except Exception as e:
                    logging.error(f"物理磁盘读取失败: {str(e)}")
                    raise
            # 逻辑卷
            elif len(disk_path) == 2 and disk_path[1] == ':':
                # 首先尝试win32file方式
                try:
                    print(f"尝试使用win32file方式读取逻辑卷: {disk_path}")
                    handle = win32file.CreateFile(
                        f"\\\\.\\{disk_path}",
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    win32file.SetFilePointer(handle, sector_number * sector_size, win32file.FILE_BEGIN)
                    data = win32file.ReadFile(handle, sector_size)[1]
                    handle.Close()
                    if data:
                        print(f"win32file方式读取成功，数据长度: {len(data)}")
                        return data
                except Exception as e:
                    print(f"win32file方式读取失败: {str(e)}")
                
                # 如果win32file方式失败，尝试open方式
                print(f"尝试使用open方式读取逻辑卷: {disk_path}")
                try:
                    with open(disk_path, "rb") as f:
                        f.seek(sector_number * sector_size)
                        data = f.read(sector_size)
                        if not data:
                            raise Exception("读取到的数据为空")
                        print(f"open方式读取成功，数据长度: {len(data)}")
                        return data
                except Exception as e:
                    print(f"open方式读取失败: {str(e)}")
                    raise
            # 虚拟磁盘文件
            elif disk_path.lower().endswith(('.vhd', '.img', '.bin')):
                print(f"使用open方式读取虚拟磁盘: {disk_path}")
                try:
                    with open(disk_path, "rb") as f:
                        f.seek(sector_number * sector_size)
                        data = f.read(sector_size)
                        if not data:
                            raise Exception("读取到的数据为空")
                        print(f"虚拟磁盘读取成功，数据长度: {len(data)}")
                        return data
                except Exception as e:
                    print(f"虚拟磁盘读取失败: {str(e)}")
                    raise
            else:
                raise Exception(f'不支持的磁盘路径: {disk_path}')
        except Exception as e:
            print(f"读取扇区失败: {str(e)}")
            raise Exception(f"读取扇区失败: {str(e)}")

    @staticmethod
    def read_sector_range(disk_path: str, start_sector: int, end_sector: int, sector_size: int = 512) -> bytes:
        """读取指定扇区范围的数据"""
        all_data = bytearray()
        for sector in range(start_sector, end_sector + 1):
            try:
                data = DiskUtils.read_sector(disk_path, sector, sector_size)
                all_data.extend(data)
            except Exception as e:
                print(f"读取扇区 {sector} 失败: {str(e)}")
        return bytes(all_data)

    @staticmethod
    def read_cluster(disk_path: str, cluster_number: int, cluster_size: int = 4096) -> bytes:
        """读取指定簇的数据，支持分区、物理磁盘、虚拟磁盘文件"""
        print(f"尝试读取簇: {disk_path}, 簇号: {cluster_number}")
        try:
            # 物理磁盘
            if disk_path.startswith('\\.\\PhysicalDrive'):
                open_path = disk_path
                print(f"使用win32file读取物理磁盘簇: {open_path}")
                try:
                    handle = win32file.CreateFile(
                        open_path,
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    win32file.SetFilePointer(handle, cluster_number * cluster_size, win32file.FILE_BEGIN)
                    data = win32file.ReadFile(handle, cluster_size)[1]
                    handle.Close()
                    if not data:
                        raise Exception("读取到的数据为空")
                    print(f"物理磁盘簇读取成功，数据长度: {len(data)}")
                    return data
                except Exception as e:
                    print(f"物理磁盘簇读取失败: {str(e)}")
                    raise
            # 逻辑卷
            elif len(disk_path) == 2 and disk_path[1] == ':':
                # 首先尝试win32file方式
                try:
                    print(f"尝试使用win32file方式读取逻辑卷簇: {disk_path}")
                    handle = win32file.CreateFile(
                        f"\\\\.\\{disk_path}",
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    win32file.SetFilePointer(handle, cluster_number * cluster_size, win32file.FILE_BEGIN)
                    data = win32file.ReadFile(handle, cluster_size)[1]
                    handle.Close()
                    if data:
                        print(f"win32file方式读取成功，数据长度: {len(data)}")
                        return data
                except Exception as e:
                    print(f"win32file方式读取失败: {str(e)}")
                
                # 如果win32file方式失败，尝试open方式
                print(f"尝试使用open方式读取逻辑卷簇: {disk_path}")
                try:
                    with open(disk_path, "rb") as f:
                        f.seek(cluster_number * cluster_size)
                        data = f.read(cluster_size)
                        if not data:
                            raise Exception("读取到的数据为空")
                        print(f"open方式读取成功，数据长度: {len(data)}")
                        return data
                except Exception as e:
                    print(f"open方式读取失败: {str(e)}")
                    raise
            # 虚拟磁盘文件
            elif disk_path.lower().endswith(('.vhd', '.img', '.bin')):
                print(f"使用open方式读取虚拟磁盘簇: {disk_path}")
                try:
                    with open(disk_path, "rb") as f:
                        f.seek(cluster_number * cluster_size)
                        data = f.read(cluster_size)
                        if not data:
                            raise Exception("读取到的数据为空")
                        print(f"虚拟磁盘簇读取成功，数据长度: {len(data)}")
                        return data
                except Exception as e:
                    print(f"虚拟磁盘簇读取失败: {str(e)}")
                    raise
            else:
                raise Exception(f'不支持的磁盘路径: {disk_path}')
        except Exception as e:
            print(f"读取簇失败: {str(e)}")
            raise Exception(f"读取簇失败: {str(e)}")

    @staticmethod
    def get_disk_list_grouped():
        """返回(分区列表, 物理磁盘列表)，用于树形分组显示"""
        drives = []
        bitmask = win32api.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                try:
                    drive_type = win32file.GetDriveType(f"{letter}:")
                    if drive_type == win32file.DRIVE_FIXED:
                        try:
                            vol_name = win32api.GetVolumeInformation(f"{letter}:\\")[0]
                        except Exception as e:
                            logging.error(f"获取磁盘 {letter}: 卷名时出错: {str(e)}")
                            vol_name = "本地磁盘"
                        drives.append((f"{letter}:", f"{vol_name} ({letter}:)"))
                except Exception as e:
                    logging.error(f"获取磁盘 {letter}: 信息时出错: {str(e)}")
            bitmask >>= 1
        # 物理磁盘
        physicals = []
        for i in range(10):
            phy_path = f"\\\\.\\PhysicalDrive{i}"  # 修正路径格式
            device_name = f"HD{i}"
            size_gb = 0.0
            try:
                handle = win32file.CreateFile(
                    phy_path,
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                # 获取磁盘容量
                try:
                    buf = win32file.DeviceIoControl(handle, 0x7405c, None, 8)  # 只要8字节
                    size = int.from_bytes(buf[:8], 'little')
                    size_gb = size / (1024**3)
                except Exception as e:
                    logging.error(f"获取物理磁盘 {phy_path} 容量时出错: {str(e)}")
                    size_gb = 0.0
                # 获取设备名
                try:
                    import wmi
                    c = wmi.WMI()
                    for disk in c.Win32_DiskDrive():
                        # 精确匹配物理磁盘编号
                        if disk.DeviceID.endswith(str(i)):
                            device_name = disk.Model
                            break
                except Exception as e:
                    logging.error(f"获取物理磁盘 {phy_path} 设备名时出错: {str(e)}")
                    device_name = f"HD{i}"
                handle.Close()
            except Exception as e:
                logging.error(f"访问物理磁盘 {phy_path} 时出错: {str(e)}")
            name = f"HD{i}: {device_name} ({size_gb:.1f} GB)"
            physicals.append((phy_path, name))
        return drives, physicals

    @staticmethod
    def find_mft_location(disk_path: str) -> int:
        """查找 NTFS 的 $MFT 位置"""
        print(f"尝试查找 {disk_path} 的 $MFT 位置")
        try:
            # 读取引导扇区（第一个扇区）
            boot_sector = DiskUtils.read_sector(disk_path, 0)
            
            # 检查是否为 NTFS 文件系统
            if boot_sector[3:11].decode('ascii') != 'NTFS    ':
                raise Exception("该磁盘不是 NTFS 文件系统")
            
            # 获取每簇扇区数
            sectors_per_cluster = boot_sector[0x0d]
            
            # 获取 $MFT 起始簇号
            mft_cluster = int.from_bytes(boot_sector[0x30:0x38], 'little')
            
            # 计算 $MFT 起始扇区号
            mft_sector = mft_cluster * sectors_per_cluster
            
            return mft_sector
        except Exception as e:
            print(f"查找 $MFT 位置失败: {str(e)}")
            raise Exception(f"查找 $MFT 位置失败: {str(e)}")

    @staticmethod
    def find_root_directory(disk_path: str) -> str:
        """查找根目录"""
        print(f"尝试查找 {disk_path} 的根目录")
        try:
            # 读取引导扇区（第一个扇区）
            boot_sector = DiskUtils.read_sector(disk_path, 0)
            if len(boot_sector) < 62:
                print("引导扇区数据长度不足，无法判断文件系统类型")
                raise Exception("引导扇区数据长度不足")
            
            # 检查是否为 NTFS 文件系统
            try:
                ntfs_identifier = boot_sector[3:11].decode('ascii')
                print(f"NTFS 标识符: {ntfs_identifier}")
                if ntfs_identifier == 'NTFS    ':
                    # NTFS 的根目录是 $MFT 的第一个记录，这里简单返回 $MFT 位置信息
                    mft_sector = DiskUtils.find_mft_location(disk_path)
                    return f"NTFS 根目录关联 $MFT，起始扇区号: {mft_sector}"
            except UnicodeDecodeError:
                print("解码 NTFS 标识符时出错")
            
            # 检查是否为 FAT32 文件系统
            try:
                fat32_identifier = boot_sector[3:11].decode('ascii')
                print(f"FAT32 标识符: {fat32_identifier}")
                if fat32_identifier == 'MSDOS5.0':
                    # 获取每扇区字节数
                    bytes_per_sector = int.from_bytes(boot_sector[11:13], 'little')
                    # 获取每簇扇区数
                    sectors_per_cluster = boot_sector[13]
                    # 获取保留扇区数
                    reserved_sectors = int.from_bytes(boot_sector[14:16], 'little')
                    # 获取 FAT 表数量
                    fat_count = boot_sector[16]
                    # 获取每个 FAT 表的扇区数
                    sectors_per_fat = int.from_bytes(boot_sector[36:40], 'little')
                
                    # 计算根目录起始簇号
                    root_cluster = 2
                    # 计算根目录起始扇区号
                    root_sector = reserved_sectors + (fat_count * sectors_per_fat) + ((root_cluster - 2) * sectors_per_cluster)
                
                    return f"FAT32 根目录起始扇区号: {root_sector}"
            except UnicodeDecodeError:
                print("解码 FAT32 标识符时出错")
        
            # 可在此添加对其他文件系统的支持，例如 FAT16
            try:
                fat16_identifier = boot_sector[54:62].decode('ascii')
                if fat16_identifier == 'FAT16   ':
                    # 简化示例，实际需要根据 FAT16 规范计算
                    root_sector = 19  # 假设根目录起始扇区为 19
                    return f"FAT16 根目录起始扇区号: {root_sector}"
            except UnicodeDecodeError:
                print("解码 FAT16 标识符时出错")
        
            print("暂不支持该文件系统的根目录查找")
            raise Exception("暂不支持该文件系统的根目录查找")
        except Exception as e:
            print(f"查找根目录失败: {str(e)}")
            raise Exception(f"查找根目录失败: {str(e)}")
