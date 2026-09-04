"""Create a Windows icon from the Qizhi Agent vector design."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "qizhi_agent.ico"


def font(size):
    for candidate in (
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
    ):
        if candidate.exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def make_icon(size):
    scale = size / 256
    image = Image.new("RGBA", (size, size), (7, 14, 34, 255))
    draw = ImageDraw.Draw(image)
    s = lambda value: round(value * scale)

    draw.rounded_rectangle((s(6), s(6), s(250), s(250)), radius=s(52), fill=(10, 23, 54, 255))
    draw.ellipse((s(160), s(20), s(238), s(98)), fill=(73, 47, 170, 75))
    draw.ellipse((s(24), s(178), s(116), s(270)), fill=(0, 150, 190, 42))

    line_width = max(2, s(8))
    neon = (101, 219, 255, 255)
    violet = (166, 108, 255, 255)
    for i in range(3):
        x = s(66 + i * 62)
        y = s(58 + i * 62)
        colour = neon if i < 2 else violet
        draw.line((x, s(54), x, s(202)), fill=colour, width=line_width)
        draw.line((s(54), y, s(202), y), fill=colour, width=line_width)

    white = (218, 251, 255, 255)
    draw.arc((s(82), s(82), s(128), s(128)), 35, 325, fill=white, width=max(2, s(5)))
    draw.line((s(119), s(119), s(132), s(132)), fill=white, width=max(2, s(5)))
    draw.arc((s(137), s(82), s(181), s(128)), 215, 500, fill=white, width=max(2, s(5)))
    draw.ellipse((s(188), s(188), s(210), s(210)), fill=(255, 202, 104, 255))
    draw.ellipse((s(195), s(195), s(203), s(203)), fill=(255, 245, 196, 255))
    return image


icons = [make_icon(size) for size in (16, 32, 48, 64, 128, 256)]
icons[-1].save(OUTPUT, format="ICO", sizes=[(image.width, image.height) for image in icons], append_images=icons[:-1])
icons[-1].save(ROOT / "qizhi_agent_logo.png", format="PNG")
print(f"Created {OUTPUT}")
