# -*- coding: utf-8 -*-
"""保存为 JPEG 节点。

原理说明：ComfyUI 工作流内部的所有图像都是张量（IMAGE），本身没有
“PNG / JPEG”的格式概念，格式在【保存】时才最终确定。内置的 Save Image
节点固定输出 PNG，本节点则把输入图像以 JPEG 格式写入 ComfyUI 的
output/ 目录。

注意：输入不限于 PNG，任意图像张量（生成结果、视频帧、处理后的图像）
都可以直接保存为 JPEG。

JPEG 不支持透明通道：带 Alpha 的图像会先合成到所选背景色上（默认白色）。
JPEG 也不支持嵌入 prompt/workflow 元数据，保存的 .jpg 不携带工作流信息。
"""

import datetime
import os

import numpy as np
from PIL import Image

import folder_paths


class SaveJPEG:
    """将输入图像编码为 JPEG 并保存到 ComfyUI 输出目录。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "%yy%mm%dd_%hh%mi%ss"}),
                "background": (["white", "black"], {"default": "white"}),
                "progressive": ("BOOLEAN", {"default": False}),
                "extension": (["jpg", "jpeg"], {"default": "jpg"}),
                "preview": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save_as_jpeg"
    CATEGORY = "image"
    # 声明为输出节点：工作流以本节点为终点时才会被 ComfyUI 视为"有输出"，
    # 否则单独使用 Load Image → SaveJPEG 会报"工作流未包含输出节点"。
    OUTPUT_NODE = True

    @staticmethod
    def tensor_to_pil(tensor):
        """把 ComfyUI 图像张量 (H, W, C) 转成 PIL Image。"""
        arr = 255.0 * tensor.cpu().numpy()
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    @staticmethod
    def flatten_alpha(img, background):
        """JPEG 无透明通道：把 RGBA 合成到纯色背景上后转 RGB。"""
        if img.mode != "RGBA":
            return img.convert("RGB")
        bg_color = (255, 255, 255) if background == "white" else (0, 0, 0)
        bg = Image.new("RGB", img.size, bg_color)
        bg.paste(img, mask=img.split()[-1])
        return bg

    @staticmethod
    def expand_time_tokens(prefix):
        """把文件名前缀中的 %yyyy/%yy/%mm/%dd/%hh/%mi/%ss 替换为当前日期时间。

        注意顺序：先替换 %yyyy（4 位年）再替换 %yy，避免 %yyyy 被 %yy 误伤。
        """
        now = datetime.datetime.now()
        replacements = [
            ("%yyyy", f"{now.year:04d}"),
            ("%yy", f"{now.year % 100:02d}"),
            ("%mm", f"{now.month:02d}"),
            ("%dd", f"{now.day:02d}"),
            ("%hh", f"{now.hour:02d}"),
            ("%mi", f"{now.minute:02d}"),
            ("%ss", f"{now.second:02d}"),
        ]
        for token, value in replacements:
            prefix = prefix.replace(token, value)
        return prefix

    def save_as_jpeg(self, images, quality, filename_prefix, background, progressive, extension, preview):
        filename_prefix = self.expand_time_tokens(filename_prefix)
        output_dir = folder_paths.get_output_directory()
        full_output_folder, filename, counter, subfolder, _ = (
            folder_paths.get_save_image_path(
                filename_prefix, output_dir, images.shape[2], images.shape[1]
            )
        )

        results = []
        for image in images:
            img = self.tensor_to_pil(image)
            img = self.flatten_alpha(img, background)
            file = f"{filename}_{counter:05}_.{extension}"
            img.save(
                os.path.join(full_output_folder, file),
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=progressive,
            )
            results.append({"filename": file, "subfolder": subfolder, "type": "output"})
            counter += 1

        # ui 返回保存结果供前端预览（preview=False 时不返回，文件仍落盘）；
        # result 原样透传输入图像，方便继续接入下游节点
        ui = {"images": results} if preview else {}
        return {"ui": ui, "result": (images,)}
