# src/archs/gfpgan_arch.py
import math
import torch
from torch import nn
from torch.nn import functional as F
from basicsr.utils.registry import ARCH_REGISTRY
from typing import List, Tuple

from .stylegan2_arch import StyleGAN2Generator  # Use our renamed and cleaned base


class SFTStyleGAN2Generator(StyleGAN2Generator):
    """StyleGAN2 Generator with Spatial Feature Transform (SFT) modulation."""

    def __init__(
        self,
        out_size: int,
        num_style_feat: int = 512,
        num_mlp: int = 8,
        channel_multiplier: int = 2,
        narrow: float = 1,
        sft_half: bool = False,
    ):
        super().__init__(out_size, num_style_feat, num_mlp, channel_multiplier, narrow)
        self.sft_half = sft_half

    def forward(
        self,
        styles: List[torch.Tensor],
        conditions: List[torch.Tensor],
        input_is_latent: bool = False,
        noise: torch.Tensor = None,
        randomize_noise: bool = True,
        truncation: float = 1,
        truncation_latent: torch.Tensor = None,
        inject_index: int = None,
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

            if i < len(conditions) * 2:
                cond_idx = (i - 1) // 2
                sft_cond = conditions[cond_idx]
                out = (
                    out * sft_cond[:, : out.size(1), :, :]
                    + sft_cond[:, out.size(1) :, :, :]
                )

            out = conv2(out, latents[:, i + 1], noise=noise2)
            skip = to_rgb(out, latents[:, i + 2], skip)
            i += 2

        image = skip
        return (image, latents) if return_latents else (image, None)


class ResBlock(nn.Module):
    """Residual block with bilinear upsampling/downsampling."""

    def __init__(self, in_channels: int, out_channels: int, mode: str = "down"):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, in_channels, 3, 1, 1)
        self.conv2 = nn.Conv2d(in_channels, out_channels, 3, 1, 1)
        self.skip = nn.Conv2d(in_channels, out_channels, 1, bias=False)
        self.scale_factor = 0.5 if mode == "down" else 2

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = F.leaky_relu(self.conv1(x), 0.2, True)
        out = F.interpolate(
            out, scale_factor=self.scale_factor, mode="bilinear", align_corners=False
        )
        out = F.leaky_relu(self.conv2(out), 0.2, True)
        skip_x = F.interpolate(
            x, scale_factor=self.scale_factor, mode="bilinear", align_corners=False
        )
        skip = self.skip(skip_x)
        return out + skip


@ARCH_REGISTRY.register()
class GFPGAN(nn.Module):
    """GFPGAN architecture: U-Net + StyleGAN2 decoder with SFT."""

    def __init__(
        self,
        out_size: int,
        num_style_feat: int = 512,
        channel_multiplier: int = 1,
        decoder_load_path: str = None,
        fix_decoder: bool = True,
        num_mlp: int = 8,
        input_is_latent: bool = False,
        different_w: bool = False,
        narrow: float = 1,
        sft_half: bool = False,
    ):
        super().__init__()
        self.input_is_latent = input_is_latent
        self.different_w = different_w
        self.num_style_feat = num_style_feat

        unet_narrow = narrow * 0.5
        channels = {
            "4": int(512 * unet_narrow),
            "8": int(512 * unet_narrow),
            "16": int(512 * unet_narrow),
            "32": int(512 * unet_narrow),
            "64": int(256 * channel_multiplier * unet_narrow),
            "128": int(128 * channel_multiplier * unet_narrow),
            "256": int(64 * channel_multiplier * unet_narrow),
            "512": int(32 * channel_multiplier * unet_narrow),
        }

        self.log_size = int(math.log(out_size, 2))
        self.conv_body_first = nn.Conv2d(3, channels[f"{out_size}"], 1)

        # Downsample
        in_ch = channels[f"{out_size}"]
        self.conv_body_down = nn.ModuleList()
        for i in range(self.log_size, 2, -1):
            out_ch = channels[f"{2**(i - 1)}"]
            self.conv_body_down.append(ResBlock(in_ch, out_ch, "down"))
            in_ch = out_ch
        self.final_conv = nn.Conv2d(in_ch, channels["4"], 3, 1, 1)

        # Upsample
        in_ch = channels["4"]
        self.conv_body_up = nn.ModuleList()
        for i in range(3, self.log_size + 1):
            out_ch = channels[f"{2**i}"]
            self.conv_body_up.append(ResBlock(in_ch, out_ch, "up"))
            in_ch = out_ch

        # SFT condition generation
        self.condition_convs = nn.ModuleList()
        for i in range(3, self.log_size + 1):
            out_ch = channels[f"{2**i}"]
            sft_out_ch = out_ch * 2  # scale and shift
            self.condition_convs.append(
                nn.Sequential(
                    nn.Conv2d(out_ch, out_ch, 3, 1, 1),
                    nn.LeakyReLU(0.2, True),
                    nn.Conv2d(out_ch, sft_out_ch, 3, 1, 1),
                )
            )

        # Decoder
        linear_out_ch = (
            (self.log_size * 2 - 2) * num_style_feat if different_w else num_style_feat
        )
        self.final_linear = nn.Linear(channels["4"] * 4 * 4, linear_out_ch)

        self.stylegan_decoder = SFTStyleGAN2Generator(
            out_size=out_size,
            num_style_feat=num_style_feat,
            num_mlp=num_mlp,
            channel_multiplier=channel_multiplier,
            narrow=narrow,
            sft_half=sft_half,
        )

        if decoder_load_path:
            self.stylegan_decoder.load_state_dict(
                torch.load(decoder_load_path)["params_ema"]
            )
        if fix_decoder:
            for param in self.stylegan_decoder.parameters():
                param.requires_grad = False

    def forward(
        self, x: torch.Tensor, return_latents: bool = False, **kwargs
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        unet_skips, conditions = [], []

        # Encoder
        feat = F.leaky_relu(self.conv_body_first(x), 0.2, True)
        for down_block in self.conv_body_down:
            feat = down_block(feat)
            unet_skips.insert(0, feat)
        feat = F.leaky_relu(self.final_conv(feat), 0.2, True)

        # Style code
        style_code = self.final_linear(feat.view(feat.size(0), -1))

        # Decoder with SFT
        feat_up = feat
        for i, up_block in enumerate(self.conv_body_up):
            feat_up = feat_up + unet_skips[i]
            feat_up = up_block(feat_up)
            conditions.append(self.condition_convs[i](feat_up))

        image, latents = self.stylegan_decoder(
            [style_code],
            conditions,
            return_latents=return_latents,
            input_is_latent=self.input_is_latent,
            **kwargs,
        )

        return image, latents
