# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['main.py'],
             pathex=[r'c:\Users\45451\Desktop\openhex'],
             binaries=[],
             datas=[
                 # 添加所有必要的数据文件
                 ('fat32_recovery.py', '.'),
                 ('fat32_recovery_dialog.py', '.'),
                 ('disk_utils.py', '.'),
                 ('hex_editor.py', '.')
             ],
             hiddenimports=[
                 # 添加可能的隐藏导入
                 'struct', 'logging', 'datetime'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='openhex',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,  # 如果是GUI应用，设为False隐藏控制台
          icon='c:\\Users\\45451\\Desktop\\openhex\\a.ico')  # 可选：添加图标文件路径