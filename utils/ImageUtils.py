# coding=UTF8

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Tuple
from math import ceil
import jieba
import os
import io

class ImageUtils:
    '''
    基于PIL的基础图片功能实现
    '''
    
    @staticmethod
    def __words2lines(words: List[str], width: int, x_padding: int, y_padding: int,
                    fill: Tuple[int, int, int], font: ImageFont.ImageFont, line_spacing: int,
                    x_offset: int, y_offset: int) -> List[dict]:
        # 可以换行的标点符号
        symbols = ['，', '。', '！', '？', '；', '：', '…', '—', '.', ',', '?', '!', ';', ':', '-', '、', 'ー', "’", "”"]

        # 获取单个词语的宽度
        def get_word_width(word: str) -> int:
            return ceil(font.getlength(word))

        # 获取单行文字的高度
        line_height = ceil(font.getbbox("戸山香澄ToyamaKasumi")[3])

        # 初始化变量
        x, y = x_padding + x_offset, y_padding + y_offset
        is_wraped = False  # 是否需要换行
        lines = []  # 存储行信息的列表

        # 逐个词语进行处理
        for index, word in enumerate(words):
            # 如果当前行可以放下这个词语
            if x + get_word_width(word) <= width - x_padding:
                # 处理换行符
                y += (line_height + 2 * line_spacing) * word.count("\n")
                x += get_word_width(lines[index - 1]["text"]) if is_wraped else 0
                y += line_spacing if is_wraped else 0
                # 记录该词语的信息
                lines.append({
                    "xy": (x, y),
                    "text": word.replace("\n", ""),
                    "fill": fill,
                    "font": font
                })
                x = x + get_word_width(word.replace("\n", "")) if word.count("\n") == 0 else x_padding
                is_wraped = False
            # 如果当前行放不下这个词语
            else:
                # 处理换行符
                y += (line_height + 2 * line_spacing) * (word.count("\n") + 1)
                x = x_padding
                is_wraped = True
                # 记录该词语的信息
                if word not in symbols:
                    lines.append({
                        "xy": (x, y + line_spacing),
                        "text": word.replace("\n", ""),
                        "fill": fill,
                        "font": font
                    })
                else:
                    lines[index - 1]["xy"] = (x, y)
                    x += get_word_width(lines[index - 1]["text"])
                    lines.append({
                        "xy": (x, y),
                        "text": word.replace("\n", ""),
                        "fill": fill,
                        "font": font
                    })

        return lines

    @staticmethod
    def Image2bytes(img: Image.Image) -> bytes:
        '''
        - 把PIL.Image.Image转换为bytes

        :param img: 用于转换的图片

        :return: 转换后的bytes
        '''
        imgByteArr = io.BytesIO()
        img.save(imgByteArr, format="PNG")
        return imgByteArr.getvalue()

    @staticmethod
    def border_text(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, font: ImageFont.ImageFont, 
                    shadowcolor: Tuple[int, int, int], fillcolor: Tuple[int, int, int], border_width: int = 1) -> None:        
        '''
        - 绘制描边的文字

        :param draw: ImageDraw对象
        :param xy: 文字的左下角坐标
        :param text: 要绘制的文本
        :param font: 字体
        :param shadowcolor: 描边颜色
        :param fillcolor: 填充颜色
        :param border_width: 描边的宽度

        :return: None
        '''

        x, y = xy
        
        # 绘制描边
        for i in range(1, border_width+1):
            draw.text((x-i, y), text, font=font, fill=shadowcolor)
            draw.text((x+i, y), text, font=font, fill=shadowcolor)
            draw.text((x, y-i), text, font=font, fill=shadowcolor)
            draw.text((x, y+i), text, font=font, fill=shadowcolor)

            draw.text((x-i, y-i), text, font=font, fill=shadowcolor)
            draw.text((x+i, y-i), text, font=font, fill=shadowcolor)
            draw.text((x-i, y+i), text, font=font, fill=shadowcolor)
            draw.text((x+i, y+i), text, font=font, fill=shadowcolor)

        # 绘制填充文字
        draw.text((x, y), text, font=font, fill=fillcolor)

    @staticmethod
    def merge_images(images: List[Image.Image], direction: str = 'v', spacing: int = 0, 
                     x_padding: int = 0, y_padding: int = 0, bg_fill: Tuple[int] = (255, 255, 255)) -> Image.Image:
        '''
        - 将多张图片纵向或横向合并
        
        :param images: 一个`PIL.Image.Image`的列表
        :param direction: `v` (纵向) 或 `h` (横向)，表示合并的方向，默认为 `v`
        :param spacing: 图片间的间隔，默认为 `0`
        :param x_padding: 图片横向留空
        :param y_padding: 图片纵向留空
        :param bg_fill: 留空区域颜色

        :return: 合并后的图片
        '''
        if not images:
            raise ValueError("The images list is empty.")
        
        # 确定合并方向和所需的新图像大小
        if direction == 'v':
            width = max(image.width for image in images)
            height = sum(image.height for image in images) + spacing * (len(images) - 1)
        elif direction == 'h':
            width = sum(image.width for image in images) + spacing * (len(images) - 1)
            height = max(image.height for image in images)
        else:
            raise ValueError(f"Invalid direction '{direction}' specified, direction must be 'v' or 'h'.")

        # 创建新图像
        merged_image = Image.new('RGBA', (width + 2 * x_padding, height + 2 * y_padding), bg_fill)
            
        # 将图像粘贴到新图像中
        x_offset = 0
        y_offset = 0
        for image in images:
            if direction == 'v':
                merged_image = ImageUtils.paste(merged_image.convert("RGBA"), image.convert("RGBA"), (x_padding, y_offset + y_padding))
                y_offset += image.height + spacing
            elif direction == 'h':
                merged_image = ImageUtils.paste(merged_image.convert("RGBA"), image.convert("RGBA"), (x_offset + x_padding, y_padding))
                x_offset += image.width + spacing

        return merged_image
    
    @staticmethod
    def make_bg(img: Image.Image, size: Tuple[int, int], color: Tuple[int, int, int, int] = (255, 237, 237, 255)):
        '''
        使用连续图片生成背景图
        '''
        width, height = size
        width_p, height_p = img.size
        width_num = ceil(width / width_p)
        height_num = ceil(height / height_p)
        result_width = width_p * width_num
        result_height = height_p * height_num
        bg = Image.new('RGBA', (result_width, result_height), color)
        for i in range(width_num):
            for j in range(height_num):
                ImageUtils.paste(bg, img, (i * width_p, j * height_p))

        return bg.crop((0, 0, width, height))
    
    @staticmethod
    def add_circle_corn(img: Image.Image, radius: int = 8, color: Tuple[int, int, int, int] = (255, 255, 255, 255), frame_color: Tuple[int, int, int, int] = (200, 200, 200, 255), background_color: Tuple[int, int, int, int] = (0, 0, 0, 0), frame_width: int = 4):
        circle = Image.new('RGBA', (radius * 2, radius * 2), background_color)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, radius * 2, radius * 2), fill=color)

        result = Image.new("RGBA", (img.width + 2 * radius, img.height + 2 * radius), background_color)
        w, h = result.size

        result.paste(circle.crop((0, 0, radius, radius)), (0, 0))  # 左上角
        result.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))  # 右上角
        result.paste(circle.crop((radius, radius, radius * 2, radius * 2)), (w - radius, h - radius))  # 右下角
        result.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))  # 左下角

        draw = ImageDraw.Draw(result)
        draw.rectangle((radius, 0, w - radius, radius), color)
        draw.rectangle((0, radius, radius, h - radius), color)
        draw.rectangle((w - radius, radius, w, h - radius), color)
        draw.rectangle((radius, h - radius, w - radius, h), color)

        draw.rounded_rectangle(result.getbbox(), outline=frame_color, width=frame_width, radius=radius)

        result = ImageUtils.paste(result, img.convert("RGBA"), (radius, radius))

        return result

    @staticmethod
    def paste(background: Image.Image, overlay: Image.Image, box: Tuple[int, int]) -> Image.Image:
        """
        - 将 `overlay` 以 `alpha` 相加的方式粘贴到 `background` 的指定位置上

        :param background: 背景图片
        :param overlay: 需要粘贴的图片
        :param box: 粘贴图片在背景图片的左上角位置

        :return: 返回合并后的图片
        """
        if background.mode != "RGBA" or overlay.mode != "RGBA":
            raise TypeError("The input image must be in RGBA mode.")
        
        paste_x, paste_y = box

        # 创建一个和 background 大小相同的透明图像作为遮罩
        mask = Image.new("L", background.size, 0)
        mask_draw = ImageDraw.Draw(mask)

        # 在遮罩上画一个矩形，矩形的左上角为 (paste_x, paste_y)
        # 矩形的右下角为 (paste_x + overlay.width, paste_y + overlay.height)
        mask_draw.rectangle((paste_x, paste_y, paste_x + overlay.width, paste_y + overlay.height), fill=255)

        # 将 overlay 粘贴到 background 上，只在矩形区域内合并 alpha 值
        background.alpha_composite(overlay, dest=(paste_x, paste_y))

        # 返回合并后的图片
        return background
    
    @staticmethod
    def text(img: Image.Image, xy: Tuple[int, int], text: str, fill: Tuple[int, int, int], font: ImageFont.ImageFont, fallback_font: ImageFont.ImageFont = None, fallback_x_offset: int = 0, fallback_y_offset: int = 0):
        '''
        - `draw.text()` 的功能拓展，主要用于处理文本中含有字体无法正常绘制的字符的情况

        :param img: 背景图片
        :param xy: 文本绘制坐标
        :param text: 文本
        :param fill: 文本颜色
        :param font: 主字体
        :param fallback_font: 备用字体
        :param fallback_x_offset: 备用字体左右偏移量
        :param fallback_y_offset: 备用字体上下偏移量

        :return: 返回合并后的图片
        '''
        return ImageUtils.paste(
            img,
            ImageUtils.text2img(text, 
                                {"width": ceil(font.getlength(text)) * 2, 
                                 "x_padding": 0,
                                 "y_padding": 0,
                                 "fill": fill,
                                 "bg_fill": (0, 0, 0, 0),
                                 "font": font,
                                 "fallback_font": fallback_font,
                                 "fallback_x_offset": fallback_x_offset,
                                 "fallback_y_offset": fallback_y_offset
                                 }
                ),
            xy
        )

    @staticmethod
    def text2img(text: str,
                 cfg: dict = {
                    "width": 640,
                    "x_padding": 24,
                    "y_padding": 24,
                    "fill": (80, 80, 80),
                    "bg_fill": (255, 255, 255),
                    "font": ImageFont.truetype(font=os.path.abspath("data/fonts/GB18030.ttf"), size=36),
                    "fallback_font": None,
                    "line_spacing": 0,
                    "x_offset": 0,
                    "y_offset": 0,
                    "fallback_x_offset": 0,
                    "fallback_y_offset": 0
                }
        ):
        '''
        - 把文段绘制成图片

        :param text: 文段
        :param cfg: (可选) 包含以下信息的字典{"width","x_padding","y_padding","fill","font","x_offset","y_offset"}

        | 参数 | 描述 | 默认值 |
        | --- | --- | --- |
        | `width` | 图片宽度 | `640` |
        | `x_padding` | x方向的边距 | `24` |
        | `y_padding` | y方向的边距 | `24` |
        | `fill` | 文字颜色 | `(80, 80, 80)` |
        | `bg_fill` | 背景颜色 | `(255, 255, 255)` |
        | `font` | 字体 | `ImageFont.truetype(font=os.path.abspath("data/fonts/GB18030.ttf"), size=36)` |
        | `fallback_font` | 备用字体 | `None` |
        | `line_spacing` | 行间距 | `0` |
        | `x_offset` | 左右偏移量，正为右，负为左 | `0` |
        | `y_offset` | 上下偏移量，正为下，负为上 | `0` |
        | `fallback_x_offset` | 备用字体左右偏移量，正为右，负为左 | `0` |
        | `fallback_y_offset` | 备用字体上下偏移量，正为下，负为上 | `0` |

        :return: 图片
        '''
        width: int = cfg.get("width", 640)
        x_padding: int = cfg.get("x_padding", 24) 
        y_padding: int = cfg.get("y_padding", 24) 
        fill: tuple = cfg.get("fill", (80, 80, 80)) 
        bg_fill: tuple = cfg.get("bg_fill", (255, 255, 255))
        font: ImageFont.ImageFont = cfg.get("font", ImageFont.truetype(font=os.path.abspath("data/fonts/GB18030.ttf"), size=36))
        fallback_font: ImageFont.ImageFont = cfg.get("fallback_font")
        line_spacing: int = cfg.get("line_spacing", 0)
        x_offset: int = cfg.get("x_offset", 0)
        y_offset: int = cfg.get("y_offset", 0)
        fallback_x_offset = cfg.get("fallback_x_offset", 0)
        fallback_y_offset = cfg.get("fallback_y_offset", 0)

        words = jieba.lcut(text, cut_all=False)
        new_words = []
        for word in words:
            if font.getlength(word) > width - x_padding:
                word_list = list(word)
                new_words.extend(word_list)
            else:
                new_words.append(word)
        words = new_words

        data = ImageUtils.__words2lines(words, width, x_padding, y_padding, fill, font, line_spacing, x_offset, y_offset)
        height = max(i["xy"][1] for i in data or [{"xy": (0, 0)}]) + y_padding + ceil(font.getbbox("戸山香澄ToyamaKasumi")[3])
        result = Image.new("RGBA", (width, height), bg_fill)
        draw = ImageDraw.Draw(result)
        for i in data:
            if font.getmask(i["text"]).getbbox() == font.getmask(chr(1234)).getbbox() and fallback_font:
                i["font"] = fallback_font
                draw.text((i["xy"][0] + fallback_x_offset, i["xy"][1] + fallback_y_offset), i["text"], i["fill"], i["font"])
            else:
                draw.text(i["xy"], i["text"], i["fill"], i["font"])
        return result
