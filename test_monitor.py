import unittest
from unittest.mock import Mock, patch
import os
import tempfile
import shutil
from monitor import ScreenshotHandler, start_monitoring
from watchdog.events import FileCreatedEvent

class TestScreenshotHandler(unittest.TestCase):
    def setUp(self):
        """
        测试前的设置:
        - 创建模拟的上传器
        - 创建临时目录用于测试文件操作
        - 初始化 ScreenshotHandler
        """
        self.mock_uploader = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.handler = ScreenshotHandler(self.mock_uploader, [self.temp_dir])

    def tearDown(self):
        """
        测试后的清理:
        - 删除临时目录及其内容
        """
        shutil.rmtree(self.temp_dir)

    def test_supported_file_extensions(self):
        """
        测试支持的文件扩展名是否正确:
        - 确保包含所有支持的图片格式
        - 确保大小写不敏感
        """
        expected_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
        self.assertEqual(self.handler.supported_extensions, expected_extensions)

    def test_on_created_with_supported_extension(self):
        """
        测试创建支持的文件格式时的处理:
        - 创建一个支持格式的文件
        - 验证是否调用了上传方法
        """
        # 创建测试文件路径
        test_file = os.path.join(self.temp_dir, "test.jpg")
        # 创建文件创建事件
        event = FileCreatedEvent(test_file)
        # 调用处理方法
        self.handler.on_created(event)
        # 验证上传方法是否被调用
        self.mock_uploader.upload_screenshot.assert_called_once_with(test_file)

    def test_on_created_with_unsupported_extension(self):
        """
        测试创建不支持的文件格式时的处理:
        - 创建一个不支持格式的文件
        - 验证是否正确忽略了该文件
        """
        test_file = os.path.join(self.temp_dir, "test.txt")
        event = FileCreatedEvent(test_file)
        self.handler.on_created(event)
        # 验证上传方法没有被调用
        self.mock_uploader.upload_screenshot.assert_not_called()

    def test_on_created_with_directory(self):
        """
        测试创建目录时的处理:
        - 创建一个目录事件
        - 验证是否正确忽略了目录
        """
        test_dir = os.path.join(self.temp_dir, "test_dir")
        event = FileCreatedEvent(test_dir)
        event.is_directory = True
        self.handler.on_created(event)
        # 验证上传方法没有被调用
        self.mock_uploader.upload_screenshot.assert_not_called()

    def test_on_created_in_subdirectory(self):
        """
        测试在子目录中创建文件时的处理:
        - 在子目录中创建一个支持格式的文件
        - 验证是否正确忽略了该文件
        """
        # 创建子目录
        sub_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(sub_dir)
        
        # 在子目录中创建测试文件
        test_file = os.path.join(sub_dir, "test.jpg")
        event = FileCreatedEvent(test_file)
        
        # 调用处理方法
        self.handler.on_created(event)
        
        # 验证上传方法没有被调用（因为文件在子目录中）
        self.mock_uploader.upload_screenshot.assert_not_called()

    @patch('monitor.Observer')
    @patch('monitor.GooglePhotosUploader')
    def test_start_monitoring_with_valid_path(self, mock_uploader_class, mock_observer_class):
        """
        测试开始监控有效路径:
        - 模拟有效的监控路径
        - 验证是否正确设置了观察者
        """
        # 设置模拟对象
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_uploader = Mock()
        mock_uploader_class.return_value = mock_uploader

        # 使用临时目录作为有效路径
        test_paths = [self.temp_dir]
        
        # 模拟键盘中断以结束无限循环
        with patch('time.sleep', side_effect=KeyboardInterrupt):
            start_monitoring(test_paths)

        # 验证观察者是否被正确设置和启动
        mock_observer.schedule.assert_called_once_with(mock_observer.schedule.call_args[0][0], 
                                                     self.temp_dir, 
                                                     recursive=False)
        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    @patch('monitor.Observer')
    @patch('monitor.GooglePhotosUploader')
    def test_start_monitoring_with_invalid_path(self, mock_uploader_class, mock_observer_class):
        """
        测试开始监控无效路径:
        - 使用不存在的路径
        - 验证是否正确处理了无效路径
        """
        # 设置模拟对象
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_uploader = Mock()
        mock_uploader_class.return_value = mock_uploader

        # 使用不存在的路径
        invalid_path = os.path.join(self.temp_dir, "nonexistent")
        test_paths = [invalid_path]
        
        # 模拟键盘中断以结束无限循环
        with patch('time.sleep', side_effect=KeyboardInterrupt):
            start_monitoring(test_paths)

        # 验证观察者没有被设置为监控无效路径
        mock_observer.schedule.assert_not_called()

if __name__ == '__main__':
    unittest.main() 