"""
Génère les icônes PWA et le favicon depuis static/images/logo.png.
Si logo.png est absent, crée un logo par défaut (cœur sur fond sombre).
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None


class Command(BaseCommand):
    help = "Génère icon-192, icon-512 et favicon.ico depuis static/images/logo.png."

    def handle(self, *args, **options):
        if Image is None:
            self.stderr.write(self.style.ERROR("Pillow requis : pip install Pillow"))
            return

        base = Path(settings.BASE_DIR) / "static" / "images"
        logo_path = base / "logo.png"
        icons_dir = base / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)

        if not logo_path.exists():
            self._create_default_logo(logo_path)
            self.stdout.write(self.style.WARNING(f"Logo par défaut créé : {logo_path}"))

        img = Image.open(logo_path).convert("RGBA")

        for size, name in ((192, "icon-192.png"), (512, "icon-512.png")):
            out = icons_dir / name
            resized = self._fit_square(img, size)
            resized.save(out, format="PNG", optimize=True)
            self.stdout.write(self.style.SUCCESS(f"  {out.relative_to(settings.BASE_DIR)}"))

        favicon_path = base / "favicon.ico"
        fav32 = self._fit_square(img, 32)
        fav48 = self._fit_square(img, 48)
        fav32.save(
            favicon_path,
            format="ICO",
            sizes=[(32, 32), (48, 48)],
            append_images=[fav48],
        )
        self.stdout.write(self.style.SUCCESS(f"  {favicon_path.relative_to(settings.BASE_DIR)}"))
        self.stdout.write(self.style.SUCCESS("Assets PWA générés."))

    @staticmethod
    def _fit_square(img: "Image.Image", size: int) -> "Image.Image":
        """Recadre au centre et redimensionne en carré."""
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        cropped = img.crop((left, top, left + side, top + side))
        return cropped.resize((size, size), Image.Resampling.LANCZOS)

    @staticmethod
    def _create_default_logo(path: Path) -> None:
        """Logo placeholder — remplacer par votre fichier source."""
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 512
        img = Image.new("RGBA", (size, size), (13, 5, 9, 255))
        draw = ImageDraw.Draw(img)
        cx, cy = size // 2, size // 2 + 20
        r = size // 5
        draw.ellipse((cx - r, cy - r - 40, cx, cy + r), fill=(255, 77, 143, 255))
        draw.ellipse((cx, cy - r - 40, cx + r, cy + r), fill=(255, 77, 143, 255))
        draw.polygon(
            [(cx - r - 10, cy), (cx + r + 10, cy), (cx, cy + r + 80)],
            fill=(255, 77, 143, 255),
        )
        img.save(path, format="PNG")
