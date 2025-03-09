"""
游戏截图监控路径配置
"""

# Steam 截图路径
STEAM_SCREENSHOT_PATHS = [
    "E:/Steam/userdata/3350395/760/remote/2246340/screenshots",
    "E:/Steam/userdata/3350395/760/remote/1446780/screenshots",
]

# 其他游戏截图路径可以在这里添加
OTHER_SCREENSHOT_PATHS = [
    # 例如：
    # "D:/Games/Screenshots/*.jpg",
    # "C:/Users/YourName/Pictures/GameScreenshots/*.png"
]

# 合并所有监控路径
MONITORING_PATHS = STEAM_SCREENSHOT_PATHS + OTHER_SCREENSHOT_PATHS 