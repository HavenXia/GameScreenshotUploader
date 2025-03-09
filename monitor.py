import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from uploader import GooglePhotosUploader
from config import MONITORING_PATHS
import glob

class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, uploader, monitored_paths):
        self.uploader = uploader
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
        # 存储监控路径的绝对路径
        self.monitored_paths = set(os.path.abspath(path) for path in monitored_paths)

    def on_created(self, event):
        if event.is_directory:
            return
        
        # 获取文件所在的直接父目录
        parent_dir = os.path.abspath(os.path.dirname(event.src_path))
        
        # 检查文件是否在直接监控的目录中（不包括子目录）
        if parent_dir not in self.monitored_paths:
            return
            
        file_ext = os.path.splitext(event.src_path)[1].lower()
        if file_ext in self.supported_extensions:
            print(f'检测到新的截图: {event.src_path}')
            # 等待文件写入完成
            time.sleep(1)
            self.uploader.upload_screenshot(event.src_path)

def expand_path_patterns(path_patterns):
    """
    展开路径通配符模式，返回实际存在的目录路径列表
    """
    expanded_paths = set()
    for pattern in path_patterns:
        # 检查路径是否包含通配符
        if '*' in pattern:
            # 如果包含通配符，获取不包含文件名部分的目录路径
            dir_pattern = os.path.dirname(pattern)
            # 展开目录通配符
            for dir_path in glob.glob(dir_pattern):
                if os.path.exists(dir_path):
                    expanded_paths.add(dir_path)
        else:
            # 如果不包含通配符，直接使用完整路径
            if os.path.exists(pattern):
                expanded_paths.add(pattern)
    return list(expanded_paths)

def start_monitoring(path_patterns, credentials_path='credentials.json'):
    """
    开始监控指定的路径模式列表
    
    Args:
        path_patterns: 需要监控的路径模式列表（支持通配符）
        credentials_path: Google API credentials.json 文件的路径
    """
    # 展开路径模式为实际目录
    monitor_paths = expand_path_patterns(path_patterns)
    
    if not monitor_paths:
        print('警告：没有找到任何匹配的目录路径')
        return
        
    uploader = GooglePhotosUploader(credentials_path)
    event_handler = ScreenshotHandler(uploader, monitor_paths)
    observer = Observer()
    
    for path in monitor_paths:
        # 设置为不递归监控
        observer.schedule(event_handler, path, recursive=False)
        print(f'开始监控路径: {path}')
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print('停止监控')
    observer.join()

if __name__ == "__main__":
    # 使用config.py中定义的监控路径
    credentials_path = "credentials.json"
    start_monitoring(MONITORING_PATHS, credentials_path) 