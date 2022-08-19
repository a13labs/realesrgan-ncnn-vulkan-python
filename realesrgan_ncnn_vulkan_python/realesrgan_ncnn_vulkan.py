#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Name: RealESRGAN ncnn Vulkan Python wrapper
Author: alexyz79
Date Created: March 29, 2021
Last Modified: May 21, 2021
"""

# built-in imports
import ctypes
import importlib
import pathlib
import sys
from typing import Tuple

# third-party imports
from PIL import Image

# local imports
if __package__ is None:
    import realesrgan_ncnn_vulkan_wrapper as wrapped
else:
    wrapped = importlib.import_module(
        f"{__package__}.realesrgan_ncnn_vulkan_wrapper")


class RealESRGAN:
    def __init__(
        self,
        gpuid: int = -1,
        model: str = "realesrgan-x4plus-anime",
        scale: int = 4,
        tile_size: int = 200,
        prepadding: int = 0,
        tta_mode: bool = False,
        models_path: str = None
    ) -> None:
        # scale must be a power of 2
        if (scale & (scale - 1)) != 0:
            raise ValueError("scale should be a power of 2")

        # create raw RealESRGAN wrapper object
        self._ersgan_object = wrapped.RealESRGANWrapped(
            gpuid, tta_mode, scale, tile_size, prepadding)

        if models_path is None:
            self.models_path = pathlib.Path(__file__).parent / "models"
        else:
            self.models_path = pathlib.Path(models_path)

        self._scale = scale
        self._prepadding = prepadding
        self._tile_size = tile_size
        self._load(model)

    def _load(self, model: str):

        param_file = self.models_path/f"{model}.param"
        model_file = self.models_path/f"{model}.bin"

        # if the model_dir is specified and exists
        if param_file.exists() and model_file.exists():
            param_str = wrapped.StringType()
            model_str = wrapped.StringType()
            if sys.platform in ("win32", "cygwin"):
                param_str.wstr = wrapped.new_wstr_p()
                wrapped.wstr_p_assign(param_str.wstr, str(param_file))
                model_str.wstr = wrapped.new_wstr_p()
                wrapped.wstr_p_assign(model_str.wstr, str(model_file))
            else:
                param_str.str = wrapped.new_str_p()
                wrapped.str_p_assign(param_str.str, str(param_file))
                model_str.str = wrapped.new_str_p()
                wrapped.str_p_assign(model_str.str, str(model_file))

            self._ersgan_object.load(param_str, model_str)

        # if no model_dir is specified but doesn't exist
        else:
            raise FileNotFoundError(
                f"{model} files not found int {self.models_path}")

    @property
    def scale(self) -> int:
        return self._scale

    @scale.setter
    def set_scale(self, value) -> None:
        self._scale = value
        self._ersgan_object.set_scale(value)

    @property
    def tile_size(self) -> int:
        return self._tile_size

    @tile_size.setter
    def set_tile_size(self, value) -> None:
        self._tile_size = value
        self._ersgan_object.set_tile_size(value)

    @property
    def prepadding(self) -> int:
        return self._prepadding

    @prepadding.setter
    def set_tile_size(self, value) -> None:
        self._prepadding = value
        self._ersgan_object.set_prepadding(value)

    def process(self, src: bytearray, src_size: Tuple[int, int], components: int = 4) -> Tuple[Tuple[int, int], bytearray]:

        out_size = (src_size[0]*self._scale, src_size[1]*self._scale)
        output_bytes = bytearray(out_size[0]*out_size[1]*components)

        # convert image bytes into ncnn::Mat Image
        raw_in_image = wrapped.Image(
            src, src_size[0], src_size[1], components
        )
        raw_out_image = wrapped.Image(
            output_bytes, out_size[0], out_size[1], components
        )

        self._ersgan_object.process(raw_in_image, raw_out_image)
        return out_size, output_bytes
