import unittest
from unittest.mock import Mock, patch, mock_open
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from uploader import GooglePhotosUploader
import requests

class TestGooglePhotosUploader(unittest.TestCase):
    def setUp(self):
        """
        测试前的设置:
        - 创建 credentials
        - 设置测试文件路径
        - 设置通用的 mock
        """
        # 创建真实的认证信息对象
        self.mock_credentials = Credentials(
            token="test_token",
            refresh_token="test_refresh_token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test_client_id",
            client_secret="test_client_secret",
            scopes=["https://www.googleapis.com/auth/photoslibrary"]
        )
        
        # 设置测试文件路径
        self.test_file_paths = {
            'steam': 'D:/Steam/userdata/3350395/760/remote/2246340/test.jpg',
            'games': 'D:/Steam/userdata/3350395/760/remote/1234567/test.jpg',
            'invalid': 'D:/Invalid/Path/test.jpg'
        }
        
        # 设置测试 credentials 路径
        self.test_credentials_path = 'test_credentials.json'
        
        # 开始通用的 patch
        self.mock_exists = patch('os.path.exists')
        self.mock_exists_func = self.mock_exists.start()
        self.mock_exists_func.return_value = True
        
        self.mock_open = patch('builtins.open', mock_open(read_data=pickle.dumps(self.mock_credentials)))
        self.mock_open_func = self.mock_open.start()
        
        # 设置 Google Photos API 相关的 mock
        self.mock_build = patch('uploader.build').start()
        self.mock_service = Mock()
        self.mock_albums = Mock()
        self.mock_service.albums.return_value = self.mock_albums
        self.mock_build.return_value = self.mock_service
        
        # 验证 build 调用参数
        def verify_build_args(*args, **kwargs):
            self.assertEqual(args[0], 'photoslibrary')
            self.assertEqual(args[1], 'v1')
            self.assertEqual(kwargs['static_discovery'], False)
            self.assertEqual(kwargs['discoveryServiceUrl'], 
                           'https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
            return self.mock_service
        self.mock_build.side_effect = verify_build_args
        
        # 默认返回空相册列表
        self.mock_albums.list.return_value.execute.return_value = {'albums': []}

    def tearDown(self):
        """
        测试后的清理:
        - 停止所有 patch
        - 删除测试过程中创建的文件
        """
        # 停止所有 patch
        self.mock_exists.stop()
        self.mock_open.stop()
        self.mock_build.stop()
        
        # 删除测试文件
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')

    def test_init_with_invalid_credentials_path(self):
        """
        测试使用无效的 credentials 路径:
        - 验证是否正确抛出 FileNotFoundError
        """
        with self.assertRaises(FileNotFoundError):
            with patch('os.path.exists') as mock_exists:
                # token.pickle 不存在
                mock_exists.side_effect = lambda p: p == self.test_credentials_path
                uploader = GooglePhotosUploader('nonexistent_credentials.json')

    @patch('uploader.build')
    def test_init_and_authenticate_with_valid_token(self, mock_build):
        """
        测试初始化和使用有效token认证:
        - 验证是否正确加载现有token
        - 验证是否正确初始化service
        """
        # 准备模拟数据
        mock_service = Mock()
        mock_albums = Mock()
        mock_service.albums.return_value = mock_albums
        mock_build.return_value = mock_service
        
        # 模拟相册列表
        mock_albums.list.return_value.execute.return_value = {'albums': []}
        
        # 模拟token文件
        with patch('builtins.open', mock_open(read_data=pickle.dumps(self.mock_credentials))):
            with patch('os.path.exists') as mock_exists:
                mock_exists.return_value = True
                uploader = GooglePhotosUploader(self.test_credentials_path)
        
        # 验证认证过程
        self.assertTrue(uploader.credentials.valid)
        mock_build.assert_called_once()

    @patch('uploader.InstalledAppFlow')
    @patch('uploader.build')
    def test_authenticate_without_token(self, mock_build, mock_flow):
        """
        测试首次认证（无token）:
        - 验证是否正确创建新的认证信息
        - 验证是否正确保存token
        """
        # 准备模拟数据
        mock_flow_instance = Mock()
        mock_flow_instance.run_local_server.return_value = self.mock_credentials
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        # 特别设置：模拟不存在token文件，但存在credentials文件
        def exists_side_effect(path):
            return path == self.test_credentials_path
        self.mock_exists_func.side_effect = exists_side_effect
        
        uploader = GooglePhotosUploader(self.test_credentials_path)
        
        # 验证认证流程
        mock_flow.from_client_secrets_file.assert_called_once()
        mock_flow_instance.run_local_server.assert_called_once()
        self.mock_open_func().write.assert_called()

    @patch('uploader.build')
    @patch('requests.get')
    def test_get_game_name_from_path(self, mock_requests_get, mock_build):
        """
        测试从文件路径中提取游戏名称或文件夹名称:
        - 测试Steam路径（从API获取游戏名称）
        - 测试Steam路径（API调用失败时返回游戏ID）
        - 测试普通文件夹路径
        - 测试无效路径
        """
        uploader = GooglePhotosUploader(self.test_credentials_path)
        
        # 模拟成功的Steam API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "2246340": {
                "success": True,
                "data": {
                    "name": "Monster Hunter Wilds",
                    "type": "game",
                    "steam_appid": 2246340
                }
            }
        }
        mock_requests_get.return_value = mock_response
        
        # 测试各种路径格式
        test_cases = {
            # Steam 路径测试（成功获取游戏名称）
            r'E:\Steam\userdata\3350395\760\remote\2246340\test.jpg': 'Monster Hunter Wilds',
            'E:/Steam/userdata/3350395/760/remote/2246340/test.jpg': 'Monster Hunter Wilds',
            r'E:\Steam\userdata\3350395\760\remote\2246340': 'Monster Hunter Wilds',
            
            # 普通文件夹路径测试
            r'C:\Users\47122\Desktop\Photos-001\test.jpg': 'Photos-001',
            'C:/Users/47122/Desktop/Photos-001/test.jpg': 'Photos-001',
            r'D:\Games\Screenshots-2023\test.jpg': 'Screenshots-2023',
        }
        
        for path, expected in test_cases.items():
            game_name = uploader.get_game_name_from_path(path)
            self.assertEqual(game_name, expected, f"路径 {path} 应该返回 {expected}")
            
        # 测试Steam API调用失败的情况
        mock_response.status_code = 404
        game_name = uploader.get_game_name_from_path(r'E:\Steam\userdata\3350395\760\remote\2246340\test.jpg')
        self.assertEqual(game_name, '2246340', "API调用失败时应返回游戏ID")
        
        # 测试Steam API返回无效数据的情况
        mock_response.status_code = 200
        mock_response.json.return_value = {"2246340": {"success": False}}
        game_name = uploader.get_game_name_from_path(r'E:\Steam\userdata\3350395\760\remote\2246340\test.jpg')
        self.assertEqual(game_name, '2246340', "API返回无效数据时应返回游戏ID")
        
        # 测试Steam路径但无效游戏ID
        game_name = uploader.get_game_name_from_path(r'E:\Steam\userdata\3350395\760\remote\invalid\test.jpg')
        self.assertEqual(game_name, 'invalid', "无效游戏ID应返回原始文件夹名")
        
        # 测试无效或根路径
        invalid_paths = {
            'test.jpg': '未分类游戏截图',
            '': '未分类游戏截图',
            '/': '未分类游戏截图'
        }
        for path, expected in invalid_paths.items():
            game_name = uploader.get_game_name_from_path(path)
            self.assertEqual(game_name, expected, f"无效路径 {path} 应返回默认值")

    @patch('uploader.build')
    def test_load_albums(self, mock_build):
        """
        测试加载相册列表:
        - 测试成功加载相册
        - 测试处理空相册列表
        - 测试处理API错误
        """
        # 准备模拟数据
        mock_service = Mock()
        mock_albums = Mock()
        mock_service.albums.return_value = mock_albums
        mock_build.return_value = mock_service
        
        # 模拟相册列表
        mock_albums.list.return_value.execute.return_value = {
            'albums': [
                {'title': 'GameName', 'id': 'album1'},
                {'title': 'AnotherGame', 'id': 'album2'}
            ]
        }
        
        # 初始化上传器并验证相册加载
        uploader = GooglePhotosUploader(self.test_credentials_path)
        self.assertEqual(uploader.albums['GameName'], 'album1')
        self.assertEqual(uploader.albums['AnotherGame'], 'album2')
        
        # 测试空相册列表
        mock_albums.list.return_value.execute.return_value = {'albums': []}
        uploader.albums.clear()  # 清空现有相册列表
        uploader._load_albums()
        self.assertEqual(len(uploader.albums), 0)
        
        # 测试API错误
        mock_albums.list.return_value.execute.side_effect = HttpError(
            resp=Mock(status=500), content=b'API Error'
        )
        uploader._load_albums()  # 不应抛出异常

    @patch('uploader.build')
    def test_create_album(self, mock_build):
        """
        测试创建相册:
        - 测试成功创建相册
        - 测试创建相册失败
        """
        # 准备模拟数据
        mock_service = Mock()
        mock_albums = Mock()
        mock_service.albums.return_value = mock_albums
        mock_build.return_value = mock_service
        
        # 模拟初始化时的空相册列表
        mock_albums.list.return_value.execute.return_value = {'albums': []}
        
        # 模拟成功创建相册
        mock_albums.create.return_value.execute.return_value = {
            'id': 'new_album_id',
            'title': 'NewGame'
        }
        
        uploader = GooglePhotosUploader(self.test_credentials_path)
        album_id = uploader.create_album('NewGame')
        
        # 验证相册创建
        self.assertEqual(album_id, 'new_album_id')
        self.assertEqual(uploader.albums['NewGame'], 'new_album_id')
        
        # 测试创建失败
        mock_albums.create.return_value.execute.side_effect = HttpError(
            resp=Mock(status=500), content=b'API Error'
        )
        album_id = uploader.create_album('FailGame')
        self.assertIsNone(album_id)

    @patch('uploader.build')
    def test_upload_media(self, mock_build):
        """
        测试媒体文件上传:
        - 测试成功上传
        - 测试上传失败
        - 测试文件读取错误
        - 测试不同文件类型的 MIME 类型
        """
        # 准备模拟数据
        mock_service = Mock()
        mock_albums = Mock()
        mock_service.albums.return_value = mock_albums
        mock_build.return_value = mock_service
        
        # 模拟初始化时的空相册列表
        mock_albums.list.return_value.execute.return_value = {'albums': []}
        
        uploader = GooglePhotosUploader(self.test_credentials_path)
        
        # 测试不同文件类型的上传
        test_cases = [
            ('test.jpg', 'image/jpeg'),
            ('test.png', 'image/png'),
            ('test.gif', 'image/gif')
        ]
        
        for filename, expected_mime_type in test_cases:
            # 重置 mock
            mock_service._http.request.reset_mock()
            
            # 模拟成功响应
            mock_service._http.request.return_value = (
                {'status': '200'},  # response
                b'upload_token'     # content
            )
            
            test_path = os.path.join(self.test_file_paths['steam'], filename)
            
            # 测试成功上传
            with patch('builtins.open', mock_open(read_data=b'test_data')):
                with patch('os.path.getsize') as mock_size:
                    mock_size.return_value = 100
                    token = uploader._upload_media(test_path)
                    
                    # 验证返回值
                    self.assertEqual(token, 'upload_token')
                    
                    # 验证请求头
                    actual_headers = mock_service._http.request.call_args[1]['headers']
                    self.assertEqual(actual_headers['Content-Type'], 'application/octet-stream')
                    self.assertEqual(actual_headers['Content-Length'], '100')
                    self.assertEqual(actual_headers['X-Goog-Upload-Protocol'], 'raw')
                    self.assertEqual(actual_headers['X-Goog-Upload-Content-Type'], expected_mime_type)
                    self.assertEqual(actual_headers['X-Goog-Upload-Content-Length'], '100')
                    self.assertEqual(actual_headers['Authorization'], 'Bearer test_token')
        
        # 测试上传失败（状态码不是200）
        mock_service._http.request.return_value = (
            {'status': '400'},  # response
            b'error'           # content
        )
        with patch('builtins.open', mock_open(read_data=b'test_data')):
            with patch('os.path.getsize') as mock_size:
                mock_size.return_value = 100
                token = uploader._upload_media(self.test_file_paths['steam'])
                self.assertIsNone(token)
        
        # 测试文件读取错误
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = IOError('File read error')
            token = uploader._upload_media(self.test_file_paths['steam'])
            self.assertIsNone(token)

    @patch('uploader.build')
    def test_upload_screenshot(self, mock_build):
        """
        测试上传截图:
        - 测试成功上传到现有相册
        - 测试上传到新相册
        - 测试上传失败
        - 测试文件不存在
        """
        # 准备模拟数据
        mock_service = Mock()
        mock_albums = Mock()
        mock_service.albums.return_value = mock_albums
        mock_build.return_value = mock_service
        
        # 模拟初始化时的空相册列表
        mock_albums.list.return_value.execute.return_value = {'albums': []}
        
        # 模拟上传成功
        mock_service._http.request.return_value = (
            {'status': '200'},  # response
            b'upload_token'     # content
        )
        
        # 模拟 batchCreate 成功响应
        mock_service.mediaItems.return_value.batchCreate.return_value.execute.return_value = {
            'newMediaItemResults': [{
                'mediaItem': {
                    'id': 'media1',
                    'productUrl': 'https://photos.google.com/photo/media1'
                }
            }]
        }
        
        # 模拟相册创建成功
        mock_albums.create.return_value.execute.return_value = {
            'id': 'album1',
            'title': '2246340'  # 使用游戏ID作为相册标题
        }
        
        # 创建上传器实例
        uploader = GooglePhotosUploader(self.test_credentials_path)
        
        # 模拟文件操作
        with patch('os.path.getsize') as mock_size:
            mock_size.return_value = 100
            
            # 测试上传到现有相册
            uploader.albums['2246340'] = 'album1'  # 使用游戏ID
            with patch('builtins.open', mock_open(read_data=b'test_data')) as mock_file:
                result = uploader.upload_screenshot(self.test_file_paths['steam'])
                self.assertTrue(result)
                
                # 验证 batchCreate 调用参数
                batch_create_body = mock_service.mediaItems.return_value.batchCreate.call_args[1]['body']
                self.assertEqual(batch_create_body['albumId'], 'album1')
                self.assertEqual(batch_create_body['newMediaItems'][0]['simpleMediaItem']['fileName'], 'test.jpg')
                self.assertEqual(batch_create_body['newMediaItems'][0]['description'], 'Screenshot from 2246340')
            
            # 测试上传到新相册
            with patch('builtins.open', mock_open(read_data=b'test_data')) as mock_file:
                result = uploader.upload_screenshot(self.test_file_paths['games'])
                self.assertTrue(result)
                
                # 验证 batchCreate 调用参数
                batch_create_body = mock_service.mediaItems.return_value.batchCreate.call_args[1]['body']
                self.assertEqual(batch_create_body['newMediaItems'][0]['description'], 'Screenshot from 1234567')
            
            # 测试上传失败 - 获取token失败
            mock_service._http.request.return_value = (
                {'status': '400'},  # response
                b'error'           # content
            )
            with patch('builtins.open', mock_open(read_data=b'test_data')) as mock_file:
                result = uploader.upload_screenshot(self.test_file_paths['steam'])
                self.assertFalse(result)
            
            # 测试上传失败 - batchCreate 失败
            mock_service._http.request.return_value = (
                {'status': '200'},  # response
                b'upload_token'     # content
            )
            mock_service.mediaItems.return_value.batchCreate.return_value.execute.return_value = {
                'newMediaItemResults': [{
                    'status': {
                        'message': '上传失败'
                    }
                }]
            }
            with patch('builtins.open', mock_open(read_data=b'test_data')) as mock_file:
                result = uploader.upload_screenshot(self.test_file_paths['steam'])
                self.assertFalse(result)
            
            # 测试文件不存在
            mock_size.side_effect = FileNotFoundError()
            result = uploader.upload_screenshot('nonexistent/file.jpg')
            self.assertFalse(result)

if __name__ == '__main__':
    unittest.main(verbosity=2) 