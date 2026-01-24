from os.path import abspath, isfile

IS_PACKAGE_ENV = isfile(abspath("../MineCursor.exe"))

VERSION = "v1.4.2"
PROJ_INFO = """\
https://github.com/hite4044/MineCursor

项目贡献者: hite4044、YOU-MING-柚明
我为这个项目投入了成百小时的时间, 有条件的话请Star吧！
YOU-MING-柚明 为此项目提供了图标设计

hite404 - https://space.bilibili.com/277685481
YOU-MING-柚明 - https://space.bilibili.com/1337092956

项目开源协议: MPL-2.0

项目引用或使用内容条款:
- Mojang Minecraft
https://www.minecraft.net/
- 部分游戏贴图、粒子等内容
https://www.minecraft.net/usage-guidelines

更新日志
v1.0
程序基本完成！
v1.1
更新了主题文件格式, 不兼容以前的压缩格式
v1.1.1
修复无法加载模板项目列表
v1.2
新增多素材源支持
v1.3
支持从文件夹添加素材源
支持在主题文件内嵌入所需素材源
支持通过键盘调整元素位置
支持导入默认主题包
增加新配置项：允许遮罩缩放
v1.4
新增两个主题：鳕鱼、钻石矛
升级所有默认主题的贴图至25w45a版本, 旧的源不受影响
对所有默认成套主题进行署名
v1.4.1
新增渲染缩放, 轻松应对高系统缩放的电脑
v1.4.2
新增两个主题：龙炎骨血剑、铜剑（换皮）
"""
