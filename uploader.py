import os
import pickle
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import re

SCOPES = ['https://www.googleapis.com/auth/photoslibrary',
          'https://www.googleapis.com/auth/photoslibrary.sharing']

class GooglePhotosUploader:
    def __init__(self, credentials_path='credentials.json'):
        """
        初始化 Google Photos 上传器
        
        Args:
            credentials_path (str): Google API credentials.json 文件的路径
        """
        self.credentials_path = credentials_path
        self.credentials = None
        self.service = None
        self.albums = {}
        self.authenticate()

    def authenticate(self):
        """处理Google Photos认证"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.credentials = pickle.load(token)

        # 如果没有认证信息，或认证信息无效，需要进行认证流程
        if not self.credentials or not self.credentials.valid:
            # 如果有认证信息，但已过期，且有刷新令牌，则尝试刷新认证
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            # 如果无法刷新（没有认证信息或无刷新令牌），需要重新进行完整的认证流程
            else:
                # 首先检查 credentials.json 文件是否存在
                # 这个文件包含了 OAuth 2.0 客户端 ID 和密钥，从 Google Cloud Console 下载
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f'Credentials file not found at: {self.credentials_path}')
                
                # 使用 credentials.json 创建认证流程
                # InstalledAppFlow 用于桌面应用的 OAuth 2.0 认证
                # 这会打开浏览器让用户登录 Google 账号并授权
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                self.credentials = flow.run_local_server(port=0)

            # 认证成功后，将认证信息保存到 token.pickle 文件
            # 这样下次运行时可以直接加载，不需要重新认证
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.credentials, token)

        self.service = build('photoslibrary', 'v1', 
                            credentials=self.credentials,
                            static_discovery=False,
                            discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
        self._load_albums()

    def _load_albums(self):
        """加载所有相册信息"""
        try:
            response = self.service.albums().list().execute()
            for album in response.get('albums', []):
                self.albums[album['title']] = album['id']
        except HttpError as error:
            print(f'加载相册时出错: {error}')

    def create_album(self, title):
        """创建新相册"""
        try:
            # 检查相册是否已存在
            if title in self.albums:
                print(f'相册已存在: {title}')
                return self.albums[title]
                
            album = self.service.albums().create(
                body={'album': {'title': title}}
            ).execute()
            self.albums[title] = album['id']
            print(f'成功创建相册: {title}')
            return album['id']
        except HttpError as error:
            print(f'创建相册时出错: {error}')
            return None

    def get_game_name_from_path(self, file_path):
        """
        从文件路径中提取游戏名称或文件夹名称
        - Steam路径格式 (E:/Steam/userdata/3350395/760/remote/2246340/test.jpg): 返回游戏名称（如 "Monster Hunter Wilds"）
        - 普通路径格式 (C:/Users/47122/Desktop/Photos-001/test.jpg): 返回 Photos-001
        """
        try:
            # 将路径分隔符统一为正斜杠
            normalized_path = file_path.replace('\\', '/')
            parts = normalized_path.split('/')
            
            # 如果是Steam路径，查找 'remote' 的位置，游戏ID在它后面
            if 'Steam' in normalized_path and 'remote' in parts:
                remote_index = parts.index('remote')
                if len(parts) > remote_index + 1:
                    game_id = parts[remote_index + 1]
                    # 确保获取到的是数字ID
                    if game_id.isdigit():
                        # 尝试从Steam API获取游戏名称
                        try:
                            response = requests.get(f'https://store.steampowered.com/api/appdetails?appids={game_id}')
                            if response.status_code == 200:
                                data = response.json()
                                if data and data.get(game_id, {}).get('success'):
                                    game_name = data[game_id]['data']['name']
                                    print(f'从Steam API获取到游戏名称: {game_name}')
                                    return game_name
                        except Exception as e:
                            print(f"从Steam API获取游戏名称时出错: {e}")
                        # 如果API调用失败，返回游戏ID
                        return game_id
            
            # 如果不是Steam路径或无法获取游戏ID，返回父文件夹名称
            parent_dir = os.path.basename(os.path.dirname(file_path))
            if parent_dir:
                return parent_dir
            
            return "未分类游戏截图"
        except Exception as e:
            print(f"提取游戏名称时出错: {e}")
            return "未分类游戏截图"

    def upload_screenshot(self, file_path):
        """上传截图到Google Photos"""
        try:
            # 从路径获取游戏名称
            game_name = self.get_game_name_from_path(file_path)
            
            # 确保相册存在
            if game_name not in self.albums:
                album_id = self.create_album(game_name)
                if not album_id:
                    print(f'创建相册失败: {game_name}')
                    return False
            
            # 获取相册ID
            album_id = self.albums[game_name]
            
            # 获取文件名
            file_name = os.path.basename(file_path)
            
            # 上传图片
            upload_token = self._upload_media(file_path)
            if upload_token:
                # 添加到相册
                result = self.service.mediaItems().batchCreate(
                    body={
                        'albumId': album_id,
                        'newMediaItems': [{
                            'description': f'Screenshot from {game_name}',
                            'simpleMediaItem': {
                                'fileName': file_name,
                                'uploadToken': upload_token
                            }
                        }]
                    }
                ).execute()
                
                # 检查上传结果
                if 'newMediaItemResults' in result:
                    item_result = result['newMediaItemResults'][0]
                    if 'mediaItem' in item_result:
                        print(f'成功上传截图到相册: {game_name}')
                        print(f'图片链接: {item_result["mediaItem"]["productUrl"]}')
                        return True
                    else:
                        print(f'上传失败: {item_result.get("status", {}).get("message", "未知错误")}')
                else:
                    print('上传失败: 未收到预期的响应')
            
        except Exception as e:
            print(f'上传截图时出错: {e}')
        return False

    def _upload_media(self, file_path):
        """上传媒体文件并获取上传token"""
        try:
            mime_type = 'image/jpeg'  # 默认 MIME 类型
            if file_path.lower().endswith('.png'):
                mime_type = 'image/png'
            elif file_path.lower().endswith('.gif'):
                mime_type = 'image/gif'

            file_size = os.path.getsize(file_path)
            
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(file_size),
                'X-Goog-Upload-Protocol': 'raw',
                'X-Goog-Upload-Content-Type': mime_type,
                'X-Goog-Upload-Content-Length': str(file_size),
                'Authorization': f'Bearer {self.credentials.token}'
            }
            
            upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
            
            with open(file_path, 'rb') as file:
                response, content = self.service._http.request(
                    upload_url,
                    method='POST',
                    body=file.read(),
                    headers=headers
                )
            
            if response['status'] == '200':
                print(f'成功获取上传token')
                return content.decode('utf-8')
            else:
                print(f'获取上传token失败: {response["status"]} - {content.decode("utf-8")}')
            
        except Exception as e:
            print(f'上传媒体文件时出错: {e}')
        return None