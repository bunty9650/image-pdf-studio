"""
UI Assets and Icon Engine for All-in-One Image & PDF Studio.
Generates razor-sharp, anti-aliased vector-style icons at runtime using Pillow (PIL).
Guarantees 100% offline, zero-dependency, crystal-clear icons across any Windows resolution.
"""

from typing import Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageTk


class IconTheme:
    PRIMARY = "#2563eb"       # Vibrant Blue
    PRIMARY_LIGHT = "#3b82f6" # Accent Blue
    SUCCESS = "#10b981"       # Emerald Green
    DANGER = "#ef4444"        # Crimson Red
    WARNING = "#f59e0b"      # Amber
    DARK = "#0f172a"         # Slate 900
    MUTED = "#64748b"        # Slate 500
    BORDER = "#cbd5e1"       # Slate 300
    WHITE = "#ffffff"


class IconManager:
    """Generates and caches crisp, anti-aliased Tkinter PhotoImage icons."""
    _cache: Dict[str, ImageTk.PhotoImage] = {}
    _pil_cache: Dict[str, Image.Image] = {}

    @classmethod
    def get(cls, name: str, size: int = 24, color: Optional[str] = None) -> ImageTk.PhotoImage:
        cache_key = f"{name}_{size}_{color}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        pil_img = cls.get_pil_icon(name, size, color)
        photo = ImageTk.PhotoImage(pil_img)
        cls._cache[cache_key] = photo
        return photo

    @classmethod
    def get_pil_icon(cls, name: str, size: int = 24, color: Optional[str] = None) -> Image.Image:
        cache_key = f"{name}_{size}_{color}"
        if cache_key in cls._pil_cache:
            return cls._pil_cache[cache_key]

        # 4x supersampling for flawless vector anti-aliasing
        scale = 4
        s = size * scale
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        col = color or IconTheme.PRIMARY

        # 1. STUDIO LOGO
        if name == "logo":
            # Gradient-feel layered squares with a star
            d.rounded_rectangle([s * 0.1, s * 0.1, s * 0.7, s * 0.7], radius=int(s * 0.15), fill="#3b82f6")
            d.rounded_rectangle([s * 0.3, s * 0.3, s * 0.9, s * 0.9], radius=int(s * 0.15), fill="#1d4ed8")
            # Star/Sparkle in center
            cx, cy = int(s * 0.6), int(s * 0.6)
            r1, r2 = int(s * 0.22), int(s * 0.08)
            star = [
                (cx, cy - r1), (cx + r2, cy - r2), (cx + r1, cy), (cx + r2, cy + r2),
                (cx, cy + r1), (cx - r2, cy + r2), (cx - r1, cy), (cx - r2, cy - r2)
            ]
            d.polygon(star, fill="#ffffff")

        # 2. NAV: IMAGES TO PDF
        elif name == "nav_img2pdf":
            # Document outline with image icon inside
            d.rounded_rectangle([s * 0.18, s * 0.1, s * 0.82, s * 0.9], radius=int(s * 0.08), fill=col)
            # Inner white sheet
            d.rounded_rectangle([s * 0.26, s * 0.18, s * 0.74, s * 0.82], radius=int(s * 0.04), fill="#ffffff")
            # Mountain/picture inside
            d.ellipse([s * 0.34, s * 0.28, s * 0.44, s * 0.38], fill="#f59e0b")
            tri = [(s * 0.3, s * 0.72), (s * 0.5, s * 0.46), (s * 0.7, s * 0.72)]
            d.polygon(tri, fill=col)

        # 3. NAV: PDF TO IMAGES
        elif name == "nav_pdf2img":
            # Red PDF document badge with right arrow
            d.rounded_rectangle([s * 0.12, s * 0.12, s * 0.62, s * 0.88], radius=int(s * 0.08), fill="#ef4444")
            # White label on PDF
            d.rectangle([s * 0.22, s * 0.32, s * 0.52, s * 0.42], fill="#ffffff")
            d.rectangle([s * 0.22, s * 0.48, s * 0.52, s * 0.54], fill="#ffffff")
            # Outward image card
            d.rounded_rectangle([s * 0.5, s * 0.35, s * 0.9, s * 0.82], radius=int(s * 0.06), fill="#3b82f6")
            d.ellipse([s * 0.58, s * 0.44, s * 0.68, s * 0.54], fill="#ffffff")

        # 3B. NAV: MERGE PDFS
        elif name == "nav_merge_pdf":
            # Two overlapping PDF sheets merging into one
            d.rounded_rectangle([s * 0.12, s * 0.14, s * 0.62, s * 0.8], radius=int(s * 0.08), fill="#f87171")
            d.rounded_rectangle([s * 0.38, s * 0.24, s * 0.88, s * 0.9], radius=int(s * 0.08), fill="#dc2626")
            # Plus / merge badge in bottom corner
            cx, cy = int(s * 0.63), int(s * 0.57)
            w = int(s * 0.06)
            d.rectangle([cx - w, cy - w * 3, cx + w, cy + w * 3], fill="#ffffff")
            d.rectangle([cx - w * 3, cy - w, cx + w * 3, cy + w], fill="#ffffff")

        # 3C. PREVIEW / EYE ICON
        elif name == "eye" or name == "preview":
            d.arc([s * 0.1, s * 0.22, s * 0.9, s * 0.78], start=25, end=155, fill=col, width=int(s * 0.09))
            d.arc([s * 0.1, s * 0.22, s * 0.9, s * 0.78], start=205, end=335, fill=col, width=int(s * 0.09))
            d.ellipse([s * 0.36, s * 0.36, s * 0.64, s * 0.64], fill=col)
            d.ellipse([s * 0.42, s * 0.42, s * 0.5, s * 0.5], fill="#ffffff")

        # 3D. CHEVRONS LEFT & RIGHT
        elif name == "chevron_left":
            thick = int(s * 0.12)
            d.line([(s * 0.62, s * 0.22), (s * 0.34, s * 0.5), (s * 0.62, s * 0.78)], fill=col, width=thick, joint="curve")

        elif name == "chevron_right":
            thick = int(s * 0.12)
            d.line([(s * 0.38, s * 0.22), (s * 0.66, s * 0.5), (s * 0.38, s * 0.78)], fill=col, width=thick, joint="curve")

        # 3E. ZOOM IN & ZOOM OUT
        elif name == "zoom_in":
            # Glass ring
            d.ellipse([s * 0.18, s * 0.18, s * 0.68, s * 0.68], outline=col, width=int(s * 0.09))
            # Handle
            d.line([(s * 0.56, s * 0.56), (s * 0.82, s * 0.82)], fill=col, width=int(s * 0.12))
            # Plus inside
            d.line([(s * 0.43, s * 0.31), (s * 0.43, s * 0.55)], fill=col, width=int(s * 0.07))
            d.line([(s * 0.31, s * 0.43), (s * 0.55, s * 0.43)], fill=col, width=int(s * 0.07))

        elif name == "zoom_out":
            d.ellipse([s * 0.18, s * 0.18, s * 0.68, s * 0.68], outline=col, width=int(s * 0.09))
            d.line([(s * 0.56, s * 0.56), (s * 0.82, s * 0.82)], fill=col, width=int(s * 0.12))
            d.line([(s * 0.31, s * 0.43), (s * 0.55, s * 0.43)], fill=col, width=int(s * 0.07))

        # 3F. HERO EMPTY STATE ILLUSTRATION
        elif name == "hero_empty":
            # Large illustration with layered sheets and upload arrow
            d.rounded_rectangle([s * 0.18, s * 0.22, s * 0.62, s * 0.82], radius=int(s * 0.08), fill="#e0e7ff")
            d.rounded_rectangle([s * 0.38, s * 0.15, s * 0.82, s * 0.75], radius=int(s * 0.08), fill="#dbeafe")
            # Foreground card with dashed border feel
            d.rounded_rectangle([s * 0.25, s * 0.28, s * 0.75, s * 0.85], radius=int(s * 0.06), fill="#ffffff", outline="#93c5fd", width=int(s * 0.04))
            # Upward upload arrow
            d.polygon([(s * 0.5, s * 0.4), (s * 0.38, s * 0.55), (s * 0.62, s * 0.55)], fill="#2563eb")
            d.rectangle([s * 0.46, s * 0.55, s * 0.54, s * 0.7], fill="#2563eb")

        # 4. NAV: COMPRESS
        elif name == "nav_compress":
            # Inward facing compression arrows
            d.rounded_rectangle([s * 0.12, s * 0.38, s * 0.88, s * 0.62], radius=int(s * 0.06), fill=col)
            # Top arrow pointing down
            d.polygon([(s * 0.5, s * 0.34), (s * 0.34, s * 0.12), (s * 0.66, s * 0.12)], fill="#ef4444")
            # Bottom arrow pointing up
            d.polygon([(s * 0.5, s * 0.66), (s * 0.34, s * 0.88), (s * 0.66, s * 0.88)], fill="#ef4444")

        # 5. NAV: FORMAT CONVERT
        elif name == "nav_format":
            # Two cycling circular arrows
            d.arc([s * 0.18, s * 0.18, s * 0.82, s * 0.82], start=30, end=150, fill=col, width=int(s * 0.1))
            d.polygon([(s * 0.8, s * 0.5), (s * 0.92, s * 0.34), (s * 0.68, s * 0.34)], fill=col)
            d.arc([s * 0.18, s * 0.18, s * 0.82, s * 0.82], start=210, end=330, fill=col, width=int(s * 0.1))
            d.polygon([(s * 0.2, s * 0.5), (s * 0.08, s * 0.66), (s * 0.32, s * 0.66)], fill=col)

        # 6. NAV: STITCH 2-5 IMAGES
        elif name == "nav_stitch":
            # Two adjacent frames joined seamlessly
            d.rounded_rectangle([s * 0.12, s * 0.18, s * 0.46, s * 0.82], radius=int(s * 0.06), fill=col)
            d.rounded_rectangle([s * 0.54, s * 0.18, s * 0.88, s * 0.82], radius=int(s * 0.06), fill="#3b82f6")
            # Small link in center
            d.rectangle([s * 0.44, s * 0.44, s * 0.56, s * 0.56], fill="#ffffff")

        # 7. BUTTON: ADD (PLUS)
        elif name == "btn_add" or name == "plus":
            w = s * 0.12
            d.rounded_rectangle([s * 0.5 - w / 2, s * 0.18, s * 0.5 + w / 2, s * 0.82], radius=w / 2, fill=col)
            d.rounded_rectangle([s * 0.18, s * 0.5 - w / 2, s * 0.82, s * 0.5 + w / 2], radius=w / 2, fill=col)

        # 8. BUTTON: UP (CHEVRON UP)
        elif name == "btn_up" or name == "up":
            thick = int(s * 0.12)
            d.line([(s * 0.22, s * 0.62), (s * 0.5, s * 0.34), (s * 0.78, s * 0.62)], fill=col, width=thick, joint="curve")

        # 9. BUTTON: DOWN (CHEVRON DOWN)
        elif name == "btn_down" or name == "down":
            thick = int(s * 0.12)
            d.line([(s * 0.22, s * 0.38), (s * 0.5, s * 0.66), (s * 0.78, s * 0.38)], fill=col, width=thick, joint="curve")

        # 10. BUTTON: DELETE / TRASH
        elif name == "btn_delete" or name == "trash":
            # Lid
            d.rounded_rectangle([s * 0.2, s * 0.18, s * 0.8, s * 0.28], radius=int(s * 0.04), fill=col)
            d.rounded_rectangle([s * 0.4, s * 0.12, s * 0.6, s * 0.2], radius=int(s * 0.03), fill=col)
            # Bin body
            d.rounded_rectangle([s * 0.26, s * 0.32, s * 0.74, s * 0.88], radius=int(s * 0.06), fill=col)
            # Slats inside
            d.line([(s * 0.4, s * 0.44), (s * 0.4, s * 0.76)], fill="#ffffff", width=int(s * 0.06))
            d.line([(s * 0.5, s * 0.44), (s * 0.5, s * 0.76)], fill="#ffffff", width=int(s * 0.06))
            d.line([(s * 0.6, s * 0.44), (s * 0.6, s * 0.76)], fill="#ffffff", width=int(s * 0.06))

        # 11. BUTTON: CLEAR / SWEEP
        elif name == "btn_clear" or name == "clear":
            # Refresh sweep circle
            d.arc([s * 0.18, s * 0.18, s * 0.82, s * 0.82], start=45, end=315, fill=col, width=int(s * 0.11))
            d.polygon([(s * 0.75, s * 0.2), (s * 0.88, s * 0.42), (s * 0.62, s * 0.42)], fill=col)

        # 12. FOLDER / BROWSE
        elif name == "btn_folder" or name == "folder":
            d.rounded_rectangle([s * 0.12, s * 0.22, s * 0.45, s * 0.38], radius=int(s * 0.05), fill="#2563eb")
            d.rounded_rectangle([s * 0.12, s * 0.32, s * 0.88, s * 0.82], radius=int(s * 0.08), fill="#3b82f6")

        # 13. OPEN FOLDER (WITH ARROW)
        elif name == "open_folder":
            d.rounded_rectangle([s * 0.12, s * 0.22, s * 0.45, s * 0.38], radius=int(s * 0.05), fill="#2563eb")
            d.rounded_rectangle([s * 0.12, s * 0.32, s * 0.88, s * 0.82], radius=int(s * 0.08), fill="#3b82f6")
            # Top-right outward arrow
            d.line([(s * 0.55, s * 0.55), (s * 0.78, s * 0.35)], fill="#ffffff", width=int(s * 0.07))
            d.polygon([(s * 0.78, s * 0.35), (s * 0.65, s * 0.35), (s * 0.78, s * 0.48)], fill="#ffffff")

        # 14. PLAY / CONVERT ACTION
        elif name == "btn_play" or name == "play":
            # Triangle pointing right
            poly = [(s * 0.3, s * 0.2), (s * 0.78, s * 0.5), (s * 0.3, s * 0.8)]
            d.polygon(poly, fill=col)

        # 15. CHECK / SUCCESS
        elif name == "check" or name == "success":
            d.ellipse([s * 0.12, s * 0.12, s * 0.88, s * 0.88], fill=IconTheme.SUCCESS)
            # Checkmark
            pts = [(s * 0.28, s * 0.52), (s * 0.44, s * 0.68), (s * 0.74, s * 0.36)]
            d.line(pts, fill="#ffffff", width=int(s * 0.1), joint="curve")

        # 16. THUMBNAIL BADGE: IMAGE
        elif name == "badge_image":
            d.rounded_rectangle([s * 0.1, s * 0.1, s * 0.9, s * 0.9], radius=int(s * 0.12), fill="#e0e7ff")
            d.ellipse([s * 0.25, s * 0.25, s * 0.45, s * 0.45], fill="#6366f1")
            d.polygon([(s * 0.2, s * 0.8), (s * 0.5, s * 0.5), (s * 0.8, s * 0.8)], fill="#4f46e5")

        # 17. THUMBNAIL BADGE: PDF
        elif name == "badge_pdf":
            d.rounded_rectangle([s * 0.15, s * 0.1, s * 0.85, s * 0.9], radius=int(s * 0.12), fill="#fee2e2")
            d.rounded_rectangle([s * 0.25, s * 0.45, s * 0.75, s * 0.75], radius=int(s * 0.06), fill="#ef4444")
            # PDF text simulation bars
            d.rectangle([s * 0.3, s * 0.25, s * 0.7, s * 0.32], fill="#ef4444")

        # FALLBACK ICON
        else:
            d.ellipse([s * 0.15, s * 0.15, s * 0.85, s * 0.85], fill=col)

        result_img = im.resize((size, size), Image.Resampling.LANCZOS)
        cls._pil_cache[cache_key] = result_img
        return result_img
