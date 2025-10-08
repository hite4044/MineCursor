<img width="400" height="400" alt="image" src="https://github.com/user-attachments/assets/58f6895c-06f2-42aa-91cf-9aded55af074" />

# _MineCursor_

### 使用 MC _&_ Mod 贴图制作鼠标指针！

---
[编程指导.md](program.md)

## 地道特色

1. 界面简洁
2. 操作没座(简单)！
3. 一键应用
4. 便捷分享

## 如何运行项目

### [下载最新构建版本](https://github.com/hite4044/MineCursor/releases/latest)

### 从源代码运行

1. 下载 [Python 3.10.9](https://www.python.org/ftp/python/3.10.9/python-3.10.9-amd64.exe) 安装程序
2. 在安装程序的首个页面勾选 `Add Python 3.10 to PATH` 然后 `Install Now`, 安装完成后关闭窗口
3. 从项目Github页面下载项目Zip压缩包 (Code绿色按钮->Download ZIP)
4. 解压至某个地方, 打开该文件夹, 并在地址栏输入`cmd`并回车
5. 在命令提示符窗口里运行命令 `python -m pip install -r requirements.txt`
6. 运行命令 `python main.py`
7. 完成！工具启动！

TIP: 如果想要更加方便地打开工具, 可以建立一个快捷方式:

1. 新建快捷方式, 目标里填入 `python "{main.py的绝对路径}"`({}里的内容和花括号本身需要替换)
2. 右键快捷方式>属性, 起始位置里填入项目文件夹的绝对路径
3. 图标换为项目文件夹里 `assets/icon.ico` 的绝对路径

## 项目权限

此项目:

- [MPL2.0 许可证](https://www.mozilla.org/en-US/MPL/2.0/)

项目引用或使用内容:

- 项目图标:
-
    - [Mojang Minecraft](https://www.minecraft.net/)
-
    - 感谢 [YOU-MING-柚明@bilibili](https://space.bilibili.com/1337092956) 制作了项目图标
- 项目自带资源库:
-
    - 部分游戏贴图 (遵循[此条款](https://www.minecraft.net/usage-guidelines))

## Python版本

Python 3.10.9

## 功能

<details>
<summary>有点长, 折起来罢</summary>

| 功能           | 实现状态 | 描述               |
|--------------|------|------------------|
| 支持动图导入       | ⏳    |                  |
| 系统高缩放测试      | ✅    |                  |
| 拖动导出主题       | ✅    |                  |
| 双击主题文件打开适配   | ✅    | 双击打开主题文件时会提示导入主题 |
| 选择元素跳转至对应帧数  | ✅    |                  |
| 素材源随主题发布     | ✅    |                  |
| 测试Zip源导入     | ✅    |                  |
| 首次启动时导入默认主题包 | ✅    |                  |
| 对Jar资源的支持    | ✅    | 存放在默认Data目录下     |

</details>

## 画廊

### 主界面

![主界面](readme_assets/主界面.png)

### 项目编辑器

![项目编辑器](readme_assets/指针编辑器.png)

### 新增元素

![新增元素](readme_assets/新增元素.png)

### 遮罩编辑器

![遮罩编辑器](readme_assets/遮罩编辑器.png)

### 关于

![关于](readme_assets/关于.png)
