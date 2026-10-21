# -*- coding: utf-8 -*-
"""SaveJPEG 节点核心逻辑自测（无需安装 ComfyUI）。

用法: python tests/test_core.py

覆盖点：
- JPEG 编码与文件落盘；
- RGBA 透明通道合成（white / black 两种底色）；
- 批量输入按序号命名；
- 输出目录正确性。
"""

import os
import sys
import tempfile
import types

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ---- 在无 ComfyUI 的环境下，用最小桩替代 folder_paths ----
OUT_DIR = tempfile.mkdtemp(prefix="savejpeg_test_")

fake_fp = types.ModuleType("folder_paths")
fake_fp.get_output_directory = lambda: OUT_DIR


def fake_get_save_image_path(prefix, output_dir, width, height):
    # 与真实 ComfyUI 一致：full_output_folder 即输出目录，subfolder 为空
    os.makedirs(output_dir, exist_ok=True)
    return output_dir, prefix, 0, "", prefix


fake_fp.get_save_image_path = fake_get_save_image_path
sys.modules["folder_paths"] = fake_fp

from nodes.save_jpeg import SaveJPEG  # noqa: E402


class FakeTensor:
    """仅提供 .cpu().numpy() 的最小张量替身，避免测试依赖 torch。"""

    def __init__(self, arr):
        self._arr = arr

    def cpu(self):
        return self

    def numpy(self):
        return self._arr


class Batch:
    """带 .shape 且可迭代的批量容器。"""

    def __init__(self, arr):
        self._arr = arr

    @property
    def shape(self):
        return self._arr.shape

    def __iter__(self):
        for a in self._arr:
            yield FakeTensor(a)


def make_batch(batch_size=1, alpha="transparent"):
    """2 行 x 3 列的红色 RGBA 图。

    alpha="transparent": 全透明（仅用于验证背景合成）；
    alpha="opaque":      全不透明纯红（用于验证色彩保留）。
    """
    arr = np.zeros((batch_size, 2, 3, 4), dtype=np.float32)
    arr[:, :, :, 0] = 1.0  # R = 255
    if alpha == "opaque":
        arr[:, :, :, 3] = 1.0
    return arr


def run(background, batch_size=1, alpha="transparent", extension="jpg", preview=True):
    node = SaveJPEG()
    batch = Batch(make_batch(batch_size, alpha))
    out = node.save_as_jpeg(
        batch,
        quality=95,
        filename_prefix="test",
        background=background,
        progressive=False,
        extension=extension,
        preview=preview,
    )
    files = out["ui"]["images"]
    assert len(files) == batch_size, f"期望 {batch_size} 个文件，实际 {len(files)}"
    assert out["result"][0] is batch, "应原样透传输入图像"
    paths = []
    for f in files:
        path = os.path.join(OUT_DIR, f["subfolder"], f["filename"])
        assert os.path.isfile(path), f"文件未生成: {path}"
        assert f["filename"].endswith("." + extension), f"扩展名错误: {f['filename']}"
        img = Image.open(path)
        assert img.format == "JPEG", f"不是 JPEG: {img.format}"
        assert img.size == (3, 2), f"尺寸错误: {img.size}"
        paths.append((path, img))
    return paths


def near(a, b, tol=8):
    """JPEG 有损编码允许小幅色差。"""
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def main():
    # 1) 全透明 + 白色底：整图应为白色
    (_, img_white), = run("white", 1, alpha="transparent")
    assert near(img_white.getpixel((0, 0)), (255, 255, 255)), img_white.getpixel((0, 0))

    # 2) 全透明 + 黑色底：整图应为黑色
    (_, img_black), = run("black", 1, alpha="transparent")
    assert near(img_black.getpixel((0, 0)), (0, 0, 0)), img_black.getpixel((0, 0))

    # 3) 全不透明纯红：色彩应被保留
    (_, img_opaque), = run("white", 1, alpha="opaque")
    assert near(img_opaque.getpixel((1, 1)), (255, 0, 0)), img_opaque.getpixel((1, 1))

    # 4) 批量 2 张：应生成 2 个序号不同的文件
    files = run("white", 2, alpha="transparent")
    assert len(files) == 2
    assert files[0][0] != files[1][0], "批量文件应使用不同文件名"

    # 5) extension=jpeg：文件应以 .jpeg 结尾且仍是 JPEG 格式
    files_jpeg = run("white", 1, alpha="transparent", extension="jpeg")
    assert files_jpeg[0][0].endswith(".jpeg"), files_jpeg[0][0]
    assert files_jpeg[0][1].format == "JPEG"

    # 6) 时间戳占位符展开为当前日期时间
    import datetime as _dt

    node = SaveJPEG()
    _now = _dt.datetime.now()
    _exp = node.expand_time_tokens("img_%yyyy-%mm-%dd_%hh%mi%ss")
    assert _exp == (
        f"img_{_now.year:04d}-{_now.month:02d}-{_now.day:02d}"
        f"_{_now.hour:02d}{_now.minute:02d}{_now.second:02d}"
    ), _exp

    # 7) %yyyy 不会被 %yy 误伤；未识别占位符原样保留
    assert node.expand_time_tokens("y=%yyyy yy=%yy") == f"y={_now.year:04d} yy={_now.year % 100:02d}"
    assert node.expand_time_tokens("keep %xx as-is") == "keep %xx as-is"

    # 8) preview=False：文件仍落盘，但 ui 不返回预览
    out_np = node.save_as_jpeg(
        Batch(make_batch(1, alpha="opaque")),
        quality=95,
        filename_prefix="test",
        background="white",
        progressive=False,
        extension="jpg",
        preview=False,
    )
    assert out_np["ui"] == {}, out_np["ui"]
    assert out_np["result"][0] is not None, "preview=False 时仍应透传图像"
    assert any(fn.startswith("test_") and fn.endswith(".jpg") for fn in os.listdir(OUT_DIR)), "文件应仍落盘"

    print("SaveJPEG 核心逻辑测试通过：JPEG 编码 / 透明合成(白底黑底) / 批量命名 / jpg-jpeg 扩展名 / 输出目录 / 时间戳占位符 / 预览开关均正常")
    print("测试输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
