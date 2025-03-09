# 游戏截图自动上传器

这是一个自动将游戏截图上传到 Google Photos 的工具。它会监控指定的文件夹，当发现新的截图时，自动将其上传到对应游戏名称的相册中。

## 功能特点

- 自动监控指定文件夹中的新截图
- 根据文件路径自动识别游戏名称
- 自动创建对应游戏的 Google Photos 相册
- 支持多个监控路径
- 支持 jpg、jpeg、png、gif 格式的图片

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置 Google Photos API：
   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 创建新项目或选择现有项目
   - 启用 Google Photos Library API
   - 创建 OAuth 2.0 客户端凭据
   - 下载凭据并重命名为 `credentials.json`，放在项目根目录

3. 配置监控路径：
   - 打开 `monitor.py`
   - 在 `monitor_paths` 列表中添加需要监控的文件夹路径

4. 运行程序：
```bash
python monitor.py
```

## 注意事项

- 首次运行时需要进行 Google 账号授权
- 确保监控的路径存在且有读取权限
- 程序会自动跳过不支持的文件格式
- 使用 Ctrl+C 可以安全停止程序

## 技术支持

如有问题，请提交 Issue。

## 开机自启动设置

如果你想让程序在 Windows 开机时自动运行，可以按照以下步骤操作：

1. 首先将程序打包为 EXE 文件：
```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包成 EXE（在项目根目录下运行）
pyinstaller --onefile monitor.py
```

2. 设置开机自启动：
   - 按 `Win + R` 键
   - 输入 `shell:startup` 打开启动文件夹
   - 将生成的 EXE 文件（在 `dist` 文件夹中）的快捷方式复制到启动文件夹中

这样，每次开机时程序就会自动运行了。