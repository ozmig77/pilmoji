import typing
import asyncio
from gc import collect
from .http import AsyncRequester
from ..classes import BasePilmoji
from ..helpers import get_nodes
from aiohttp import ClientSession
from PIL import ImageFont, Image, ImageDraw


__all__ = [
    'AsyncPilmoji'
]


class AsyncPilmoji(BasePilmoji):
    """
    The synchronous emoji renderer.
    """
    def __init__(self, image: Image.Image, *, session: typing.Optional[ClientSession] = None, loop: typing.Optional[asyncio.AbstractEventLoop] = None):
        if not isinstance(image, Image.Image):
            raise TypeError(f'Image must be of type Image, got {type(image).__name__!r} instead.')

        self.http: AsyncRequester = AsyncRequester(session=session, loop=loop)
        self.image: Image.Image = image
        self.draw = ImageDraw.Draw(image)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """
        Closes the requester and collects garbage.
        """
        await self.http.close()
        collect()
        del self

    async def text(self,
                   xy: typing.Tuple[int, int],
                   text: str,
                   fill=None,
                   font=None,
                   anchor=None,
                   spacing=4,
                   align="left",
                   direction=None,
                   features=None,
                   language=None,
                   stroke_width=0,
                   stroke_fill=None,
                   embedded_color=False,
                   *args, **kwargs) -> None:
        """
        Draws text with emoji rendering.
        Multiline text is supported.

        This function's signature is the exact same as PIL's, with a little bit of type-hinting.
        """
        if not font:
            font = ImageFont.load_default()

        args = (fill, font, anchor, spacing, align, direction,
                features, language, stroke_width, stroke_fill, embedded_color, *args)

        x, y = xy
        original_x = x
        lines = text.split('\n')
        nodes = get_nodes(lines)

        for line in nodes:
            x = original_x
            for node in line:
                content = node['content']
                width, height = font.getsize(content)
                if node['type'] == 'text':
                    self.draw.text((x, y), content, *args, **kwargs)
                else:
                    if node['type'] == 'twemoji':
                        stream = await self.http.get_twemoji(content)
                    else:
                        stream = await self.http.get_discord_emoji(content)

                    with Image.open(stream).convert("RGBA") as asset:
                        asset = asset.resize((width := font.size, font.size), Image.ANTIALIAS)
                        self.image.paste(asset, (x, y), asset)

                x += width
            y += spacing + font.size
