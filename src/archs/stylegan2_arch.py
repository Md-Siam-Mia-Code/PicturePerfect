# src/archs/stylegan2_arch.py
import math
import random
import torch
from torch import nn
from torch.nn import functional as F
from basicsr.utils.registry import ARCH_REGISTRY
from basicsr.archs.arch_util import default_init_weights
from typing import List, Tuple


class NormStyleCode(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(torch.mean(x**2, dim=1, keepdim=True) + 1e-8)


class ModulatedConv2d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        num_style_feat: int,
        demodulate: bool = True,
        sample_mode: str = None,
        eps: float = 1e-8,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.demodulate = demodulate
        self.sample_mode = sample_mode
        self.eps = eps
        self.modulation = nn.Linear(num_style_feat, in_channels, bias=True)
        self.weight = nn.Parameter(
            torch.randn(1, out_channels, in_channels, kernel_size, kernel_size)
            / math.sqrt(in_channels * kernel_size**2)
        )
        self.padding = kernel_size // 2
        default_init_weights(
            self.modulation,
            scale=1,
            bias_fill=1,
            a=0,
            mode="fan_in",
            nonlinearity="linear",
        )

    def forward(self, x: torch.Tensor, style: torch.Tensor) -> torch.Tensor:
        b, c, h, w = x.shape
        style = self.modulation(style).view(b, 1, c, 1, 1)
        weight = self.weight * style
        if self.demodulate:
            demod = torch.rsqrt(weight.pow(2).sum([2, 3, 4]) + self.eps)
            weight = weight * demod.view(b, self.out_channels, 1, 1, 1)
        weight = weight.view(
            b * self.out_channels, c, self.kernel_size, self.kernel_size
        )

        if self.sample_mode == "upsample":
            x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        elif self.sample_mode == "downsample":
            x = F.interpolate(x, scale_factor=0.5, mode="bilinear", align_corners=False)

        b, c, h, w = x.shape
        out = F.conv2d(x.view(1, b * c, h, w), weight, padding=self.padding, groups=b)
        return out.view(b, self.out_channels, *out.shape[2:4])


class StyleConv(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        num_style_feat: int,
        demodulate: bool = True,
        sample_mode: str = None,
    ):
        super().__init__()
        self.modulated_conv = ModulatedConv2d(
            in_channels,
            out_channels,
            kernel_size,
            num_style_feat,
            demodulate,
            sample_mode,
        )
        self.weight = nn.Parameter(torch.zeros(1))
        self.bias = nn.Parameter(torch.zeros(1, out_channels, 1, 1))
        self.activate = nn.LeakyReLU(0.2, True)

    def forward(
        self, x: torch.Tensor, style: torch.Tensor, noise: torch.Tensor = None
    ) -> torch.Tensor:
        out = self.modulated_conv(x, style)
        if noise is None:
            b, _, h, w = out.shape
            noise = out.new_empty(b, 1, h, w).normal_()
        out = out + self.weight * noise + self.bias
        return self.activate(out)


class ToRGB(nn.Module):
    def __init__(self, in_channels: int, num_style_feat: int, upsample: bool = True):
        super().__init__()
        self.upsample = upsample
        self.modulated_conv = ModulatedConv2d(
            in_channels, 3, 1, num_style_feat, demodulate=False
        )
        self.bias = nn.Parameter(torch.zeros(1, 3, 1, 1))

    def forward(
        self, x: torch.Tensor, style: torch.Tensor, skip: torch.Tensor = None
    ) -> torch.Tensor:
        out = self.modulated_conv(x, style) + self.bias
        if skip is not None:
            if self.upsample:
                skip = F.interpolate(
                    skip, scale_factor=2, mode="bilinear", align_corners=False
                )
            out = out + skip
        return out


class ConstantInput(nn.Module):
    def __init__(self, num_channel: int, size: int):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(1, num_channel, size, size))

    def forward(self, batch: int) -> torch.Tensor:
        return self.weight.repeat(batch, 1, 1, 1)


@ARCH_REGISTRY.register()
class StyleGAN2Generator(nn.Module):
    """Clean StyleGAN2 Generator"""

    def __init__(
        self,
        out_size: int,
        num_style_feat: int = 512,
        num_mlp: int = 8,
        channel_multiplier: int = 2,
        narrow: float = 1.0,
    ):
        super().__init__()
        self.num_style_feat = num_style_feat
        self.style_mlp = nn.Sequential(
            *[NormStyleCode()]
            + [
                l
                for _ in range(num_mlp)
                for l in (
                    nn.Linear(num_style_feat, num_style_feat),
                    nn.LeakyReLU(0.2, True),
                )
            ]
        )
        default_init_weights(
            self.style_mlp,
            scale=1,
            bias_fill=0,
            a=0.2,
            mode="fan_in",
            nonlinearity="leaky_relu",
        )

        channels = {
            "4": int(512 * narrow),
            "8": int(512 * narrow),
            "16": int(512 * narrow),
            "32": int(512 * narrow),
            "64": int(256 * channel_multiplier * narrow),
            "128": int(128 * channel_multiplier * narrow),
            "256": int(64 * channel_multiplier * narrow),
            "512": int(32 * channel_multiplier * narrow),
        }

        self.log_size = int(math.log(out_size, 2))
        self.num_layers = (self.log_size - 2) * 2 + 1
        self.num_latent = self.log_size * 2 - 2

        self.constant_input = ConstantInput(channels["4"], size=4)
        self.style_conv1 = StyleConv(
            channels["4"], channels["4"], 3, num_style_feat, demodulate=True
        )
        self.to_rgb1 = ToRGB(channels["4"], num_style_feat, upsample=False)

        self.style_convs = nn.ModuleList()
        self.to_rgbs = nn.ModuleList()
        self.noises = nn.Module()

        in_channels = channels["4"]
        for layer_idx in range(self.num_layers):
            res = 2 ** ((layer_idx + 5) // 2)
            self.noises.register_buffer(
                f"noise{layer_idx}", torch.randn(1, 1, res, res)
            )

        for i in range(3, self.log_size + 1):
            out_channels = channels[f"{2**i}"]
            self.style_convs.extend(
                [
                    StyleConv(
                        in_channels,
                        out_channels,
                        3,
                        num_style_feat,
                        sample_mode="upsample",
                    ),
                    StyleConv(out_channels, out_channels, 3, num_style_feat),
                ]
            )
            self.to_rgbs.append(ToRGB(out_channels, num_style_feat))
            in_channels = out_channels

    def _styles_to_latents(
        self,
        styles: List[torch.Tensor],
        input_is_latent: bool,
        truncation: float,
        truncation_latent: torch.Tensor,
    ) -> torch.Tensor:
        if not input_is_latent:
            styles = [self.style_mlp(s) for s in styles]
        if truncation < 1:
            styles = [
                truncation_latent + truncation * (s - truncation_latent) for s in styles
            ]

        if len(styles) < 2:
            return styles[0]
        inject_index = random.randint(1, self.num_latent - 1)
        latent1 = styles[0].unsqueeze(1).repeat(1, inject_index, 1)
        latent2 = styles[1].unsqueeze(1).repeat(1, self.num_latent - inject_index, 1)
        return torch.cat([latent1, latent2], 1)

    def forward(
        self,
        styles: List[torch.Tensor],
        input_is_latent: bool = False,
        noise: torch.Tensor = None,
        randomize_noise: bool = True,
        truncation: float = 1,
        truncation_latent: torch.Tensor = None,
        return_latents: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor]:

        latents = self._styles_to_latents(
            styles, input_is_latent, truncation, truncation_latent
        )
        if latents.ndim == 2:
            latents = latents.unsqueeze(1).repeat(1, self.num_latent, 1)

        if noise is None:
            noise = (
                [getattr(self.noises, f"noise{i}") for i in range(self.num_layers)]
                if not randomize_noise
                else [None] * self.num_layers
            )

        out = self.constant_input(latents.shape[0])
        out = self.style_conv1(out, latents[:, 0], noise=noise[0])
        skip = self.to_rgb1(out, latents[:, 1])

        i = 1
        for conv1, conv2, noise1, noise2, to_rgb in zip(
            self.style_convs[::2],
            self.style_convs[1::2],
            noise[1::2],
            noise[2::2],
            self.to_rgbs,
        ):
            out = conv1(out, latents[:, i], noise=noise1)
            out = conv2(out, latents[:, i + 1], noise=noise2)
            skip = to_rgb(out, latents[:, i + 2], skip)
            i += 2

        image = skip
        return (image, latents) if return_latents else (image, None)
