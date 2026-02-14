from PIL import Image, ImageDraw

RESAMPLE = 4


def add_rounded_corners(image: Image.Image, radius: int) -> Image.Image:
    """
    为图片添加圆角，并使用超采样和BICUBIC降采样实现抗锯齿效果。

    :param image: 输入的PIL图像对象
    :param radius: 圆角半径
    :return: 添加圆角后的图像
    """
    # 获取原始图像尺寸
    width, height = image.size

    # 计算超采样后的尺寸
    scaled_width = width * RESAMPLE
    scaled_height = height * RESAMPLE
    scaled_radius = radius * RESAMPLE

    # 创建一个与原图相同模式的超采样图像

    # 创建遮罩图像并绘制圆角矩形
    mask = Image.new("L", (scaled_width, scaled_height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [(0, 0), (scaled_width, scaled_height)],
        radius=scaled_radius,
        fill=255
    )
    mask = mask.resize((width, height), resample=Image.Resampling.BICUBIC)

    # 将遮罩应用到图像上
    result = Image.new("RGBA", (width, height))
    result.paste(image, (0, 0), mask)

    return result
