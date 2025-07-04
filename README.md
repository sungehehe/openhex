# WinHex 克隆版

这是一个使用Python和PyQt6开发的十六进制编辑器，模仿了WinHex的基本功能。

## 功能特点

- 十六进制和ASCII视图
- 文件打开和保存
- 基本的编辑功能
- 偏移地址显示
- 文件大小显示
- 鼠标点击导航
- FAT32文件系统删除文件恢复

## 安装要求

- Python 3.8+
- PyQt6
- numpy
- pywin32
- python-dateutil

## 安装步骤

1. 克隆或下载此仓库
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 运行程序

```bash
python main.py
```

## 使用说明

1. 文件操作：
   - 新建：创建新的空白文件
   - 打开：打开现有文件
   - 保存：保存当前文件

2. 编辑操作：
   - 使用鼠标点击选择要编辑的位置
   - 十六进制视图显示文件的十六进制内容
   - ASCII视图显示可打印字符

3. 磁盘操作：
   - 读取扇区范围：读取指定磁盘的扇区范围
   - 查找$MFT位置：查找NTFS文件系统的MFT表位置
   - 查找根目录：查找文件系统根目录

4. 文件恢复：
   - FAT32文件恢复：扫描FAT32分区中的已删除文件并恢复
   - 支持按照文件类型、大小等过滤
   - 支持恢复单个或多个文件

5. 状态栏显示：
   - 当前光标位置的偏移地址
   - 文件大小

## FAT32文件恢复功能

该功能允许用户扫描FAT32文件系统分区，查找并恢复已删除的文件：

1. 从"工具"菜单选择"FAT32文件恢复"
2. 选择要扫描的FAT32分区
3. 点击"扫描已删除文件"按钮开始扫描
4. 在结果列表中查看已删除的文件
5. 可以使用过滤选项（显示系统文件、显示隐藏文件、最小文件大小）来筛选文件
6. 选择要恢复的文件，然后点击"恢复选中文件"按钮
7. 选择恢复文件的保存目录
8. 等待恢复完成

注意：文件恢复的成功率取决于文件系统的状态和文件被删除后的时间长短。越早恢复，成功率越高。

## 注意事项

- 这是一个基础版本，功能还在不断完善中
- 建议在编辑重要文件前先备份
- 目前仅支持基本的文件操作，高级功能正在开发中
- FAT32文件恢复功能仅适用于FAT32文件系统分区

## 许可证

MIT License 