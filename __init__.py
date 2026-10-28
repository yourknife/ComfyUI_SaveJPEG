# -*- coding: utf-8 -*-
"""ComfyUI 插件入口：注册“保存为 JPEG”节点。"""

from .nodes.save_jpeg import SaveJPEG

NODE_CLASS_MAPPINGS = {
    "SaveJPEG": SaveJPEG,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveJPEG": "Save as JPEG",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
