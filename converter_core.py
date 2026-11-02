"""
Converter Core Engine
Provides modular processing functions for:
1. Converting any image format to PDF (single & multi-image)
2. Converting PDF to images with adjustable DPI/clarity
3. Compressing images & PDFs with quality control or exact target KB/MB
4. Converting image formats (JPG, PNG, WEBP, BMP, TIFF, ICO, etc.)
5. Merging 2 to 5 images horizontally or vertically with maximum clarity
"""

import os
import io
import math
from typing import List, Optional, Tuple, Union
from PIL import Image, ImageOps
import pymupdf


def format_file_size(size_bytes: int) -> str:
    """Format bytes into readable string (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    """
    Parse page range string like '1-3, 5, 8-10' into 0-indexed list of page numbers.
    If range_str is empty or 'all', returns list of all page indices.
    """
    if not range_str or range_str.strip().lower() in ("all", "*", ""):
        return list(range(max_pages))
    
    pages = set()
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2:
                try:
                    start = int(sub[0].strip())
                    end = int(sub[1].strip())
                    for p in range(start, end + 1):
                        if 1 <= p <= max_pages:
                            pages.add(p - 1)
                except ValueError:
                    pass
        else:
            try:
                p = int(part)
                if 1 <= p <= max_pages:
                    pages.add(p - 1)
            except ValueError:
                pass
    return sorted(list(pages))


# ==============================================================================
# 1. IMAGE(S) TO PDF
# ==============================================================================

def images_to_pdf(
    image_paths: List[str],
    output_pdf_path: str,
    page_size: str = "fit",        # 'fit', 'A4', 'Letter'
    orientation: str = "auto",     # 'auto', 'portrait', 'landscape'
    margin: float = 0.0,           # margin in points
    quality: int = 95
) -> str:
    """
    Convert single or multiple images into a single PDF document.
    Preserves aspect ratio, sharpness, and handles any image format.
    """
    if not image_paths:
        raise ValueError("At least one image file is required.")

    doc = pymupdf.open()

    # Standard paper dimensions in points (72 points = 1 inch)
    paper_sizes = {
        "A4": (595.28, 841.89),
        "Letter": (612.0, 792.0),
    }

    for img_path in image_paths:
        if not os.path.exists(img_path):
            continue

        with Image.open(img_path) as pil_img:
            # Auto-orient based on EXIF
            pil_img = ImageOps.exif_transpose(pil_img) or pil_img
            img_w, img_h = pil_img.size

            # Encode image to bytes to support ALL formats (WebP, TIFF, BMP, GIF, etc.) seamlessly
            buf = io.BytesIO()
            if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
                pil_img.save(buf, format="PNG")
            else:
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                pil_img.save(buf, format="JPEG", quality=quality)
            img_stream = buf.getvalue()

        # Determine page dimensions
        if page_size in paper_sizes:
            pw, ph = paper_sizes[page_size]
            if orientation == "landscape":
                pw, ph = max(pw, ph), min(pw, ph)
            elif orientation == "portrait":
                pw, ph = min(pw, ph), max(pw, ph)
            else:  # auto
                if img_w > img_h:
                    pw, ph = max(pw, ph), min(pw, ph)
                else:
                    pw, ph = min(pw, ph), max(pw, ph)
        else:
            # 'fit' - page size matches image dimensions
            pw, ph = float(img_w), float(img_h)

        page = doc.new_page(width=pw, height=ph)

        # Usable page area accounting for margin
        avail_w = max(10.0, pw - 2 * margin)
        avail_h = max(10.0, ph - 2 * margin)

        # Scale image to fit inside usable area while preserving aspect ratio
        ratio = min(avail_w / img_w, avail_h / img_h)
        target_w = img_w * ratio
        target_h = img_h * ratio

        # Center on page
        x0 = margin + (avail_w - target_w) / 2
        y0 = margin + (avail_h - target_h) / 2
        rect = pymupdf.Rect(x0, y0, x0 + target_w, y0 + target_h)

        page.insert_image(rect, stream=img_stream)

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()
    return output_pdf_path


# ==============================================================================
# 2. PDF TO IMAGES & PDF PREVIEW
# ==============================================================================

def merge_pdfs(pdf_paths: List[str], output_pdf_path: str) -> Tuple[str, int, int]:
    """
    Merge multiple PDF files into a single unified PDF document.
    Returns: (output_pdf_path, total_pages, file_size)
    """
    if not pdf_paths or len(pdf_paths) < 2:
        raise ValueError("At least 2 PDF files are required to merge.")

    doc = pymupdf.open()
    total_pages = 0
    for p in pdf_paths:
        if not os.path.exists(p):
            continue
        sub = pymupdf.open(p)
        total_pages += len(sub)
        doc.insert_pdf(sub)
        sub.close()

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()
    return output_pdf_path, total_pages, os.path.getsize(output_pdf_path)


def get_pdf_page_image(pdf_path: str, page_number: int = 0, dpi: int = 150) -> Image.Image:
    """
    Render a specific page of a PDF into a high-clarity PIL Image.
    page_number is 0-indexed.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    doc = pymupdf.open(pdf_path)
    if page_number < 0 or page_number >= len(doc):
        doc.close()
        raise IndexError(f"Page index {page_number} out of range (total {len(doc)} pages).")

    page = doc[page_number]
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img


def get_pdf_info(pdf_path: str) -> dict:
    """Get metadata about a PDF file (page count, size, first page thumbnail)."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    doc = pymupdf.open(pdf_path)
    page_count = len(doc)
    doc.close()
    return {
        "page_count": page_count,
        "size": os.path.getsize(pdf_path),
        "size_formatted": format_file_size(os.path.getsize(pdf_path))
    }


def pdf_to_images(
    pdf_path: str,
    output_dir: str,
    output_format: str = "png",   # 'jpg', 'png', 'webp'
    dpi: int = 300,               # 150 (standard), 300 (high), 600 (ultra)
    page_range: Optional[str] = None,
    quality: int = 95
) -> List[str]:
    """
    Convert PDF pages into high-clarity images.
    Returns list of saved image paths.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    os.makedirs(output_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    max_pages = len(doc)
    page_indices = parse_page_ranges(page_range or "all", max_pages)

    if not page_indices:
        doc.close()
        raise ValueError("No valid pages selected.")

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_format = output_format.lower().replace(".", "")
    if out_format in ("jpeg", "jpg"):
        ext = "jpg"
    elif out_format == "webp":
        ext = "webp"
    else:
        ext = "png"

    output_files = []
    for idx in page_indices:
        page = doc[idx]
        pix = page.get_pixmap(dpi=dpi)
        out_filename = f"{base_name}_page_{idx + 1:03d}.{ext}"
        out_filepath = os.path.join(output_dir, out_filename)

        if ext in ("jpg", "jpeg"):
            # RGB conversion without alpha
            img_data = pix.tobytes("jpeg", jpg_quality=quality)
            with open(out_filepath, "wb") as f:
                f.write(img_data)
        elif ext == "webp":
            # Convert through PIL for webp quality control
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img.save(out_filepath, "WEBP", quality=quality, method=6)
        else:
            # PNG lossless
            pix.save(out_filepath)

        output_files.append(out_filepath)

    doc.close()
    return output_files


# ==============================================================================
# 3. COMPRESSION (IMAGE & PDF)
# ==============================================================================

def compress_image(
    input_path: str,
    output_path: str,
    target_kb: Optional[float] = None,
    quality: int = 75,
    output_format: Optional[str] = None
) -> Tuple[str, int, int]:
    """
    Compress image either by quality percentage or to a target size in KB.
    Returns: (output_path, original_size, compressed_size)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    orig_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with Image.open(input_path) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img) or pil_img

        # Determine target format
        if not output_format:
            _, ext = os.path.splitext(output_path)
            fmt = ext.lower().replace(".", "")
            if not fmt:
                _, ext = os.path.splitext(input_path)
                fmt = ext.lower().replace(".", "")
        else:
            fmt = output_format.lower().replace(".", "")

        if fmt in ("jpeg", "jpg"):
            save_format = "JPEG"
        elif fmt == "webp":
            save_format = "WEBP"
        elif fmt == "png":
            save_format = "PNG"
        else:
            save_format = "JPEG"

        # Handle transparency for JPEG
        if save_format == "JPEG":
            if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
                rgb_img = Image.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == "P":
                    pil_img = pil_img.convert("RGBA")
                rgb_img.paste(pil_img, mask=pil_img.split()[-1])
                pil_img = rgb_img
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
        elif save_format in ("PNG", "WEBP"):
            if pil_img.mode not in ("RGB", "RGBA"):
                pil_img = pil_img.convert("RGBA")

        # --- MODE 1: Target KB Compression ---
        if target_kb is not None and target_kb > 0:
            target_bytes = int(target_kb * 1024)

            # If PNG is requested for target size, lossy webp/jpeg or indexed PNG is needed
            current_img = pil_img.copy()
            best_buf = None
            best_diff = float("inf")

            # Try adjusting quality and, if needed, downscale resolution smoothly
            scale = 1.0
            for attempt in range(8):
                low_q = 10
                high_q = 95
                current_attempt_buf = None

                while low_q <= high_q:
                    mid_q = (low_q + high_q) // 2
                    buf = io.BytesIO()
                    if save_format == "PNG":
                        # For PNG target size, try optimizing or quantizing
                        if scale < 1.0:
                            current_img.save(buf, format="PNG", optimize=True)
                        else:
                            current_img.save(buf, format="PNG", optimize=True)
                    else:
                        current_img.save(buf, format=save_format, quality=mid_q, optimize=True)

                    s = buf.tell()
                    if s <= target_bytes:
                        current_attempt_buf = buf
                        low_q = mid_q + 1  # Try higher quality
                    else:
                        high_q = mid_q - 1

                if current_attempt_buf is not None:
                    best_buf = current_attempt_buf
                    break

                # If even quality 10 is > target_bytes, reduce dimensions by 15% and retry
                scale *= 0.85
                new_w = max(10, int(pil_img.width * scale))
                new_h = max(10, int(pil_img.height * scale))
                current_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Fallback if target was ridiculously small
            if best_buf is None:
                best_buf = io.BytesIO()
                current_img.save(best_buf, format=save_format, quality=10, optimize=True)

            with open(output_path, "wb") as f:
                f.write(best_buf.getvalue())

        # --- MODE 2: Quality Percentage Compression ---
        else:
            q = max(5, min(100, int(quality)))
            if save_format == "PNG":
                # PNG lossless compression with optimize
                pil_img.save(output_path, format="PNG", optimize=True)
            elif save_format == "WEBP":
                pil_img.save(output_path, format="WEBP", quality=q, method=6)
            else:
                pil_img.save(output_path, format="JPEG", quality=q, optimize=True)

    compressed_size = os.path.getsize(output_path)
    return output_path, orig_size, compressed_size


def compress_pdf(
    input_path: str,
    output_path: str,
    target_kb: Optional[float] = None,
    quality: int = 75,
    dpi: int = 150,
    aggressive: bool = False
) -> Tuple[str, int, int]:
    """
    Compress PDF using stream deflation, garbage collection, and optional image recompression.
    Supports target file size (KB/MB).
    Returns: (output_path, original_size, compressed_size)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"PDF not found: {input_path}")

    orig_size = os.path.getsize(input_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = pymupdf.open(input_path)

    # First attempt: Clean & deflate lossless optimization
    temp_buf = io.BytesIO()
    doc.save(temp_buf, garbage=4, deflate=True, clean=True)
    first_size = temp_buf.tell()

    target_bytes = int(target_kb * 1024) if (target_kb is not None and target_kb > 0) else None

    # If first attempt meets target or no target specified & not aggressive
    if (target_bytes is None and not aggressive) or (target_bytes is not None and first_size <= target_bytes):
        with open(output_path, "wb") as f:
            f.write(temp_buf.getvalue())
        doc.close()
        return output_path, orig_size, os.path.getsize(output_path)

    # Secondary: Recompress pages (especially for photo/scanned PDFs) to hit target size or aggressive mode
    # Calculate starting DPI and quality
    q = max(30, min(95, quality))
    target_dpi = dpi

    if target_bytes is not None:
        # Scale DPI and quality based on ratio
        ratio = target_bytes / max(1, orig_size)
        if ratio < 0.25:
            target_dpi = min(100, target_dpi)
            q = max(35, min(60, q))
        elif ratio < 0.5:
            target_dpi = min(150, target_dpi)
            q = max(50, min(75, q))

    # Render pages and build compressed PDF
    new_doc = pymupdf.open()
    for page_num in range(len(doc)):
        page = doc[page_num]
        rect = page.rect
        pix = page.get_pixmap(dpi=target_dpi)
        # Convert pixmap to compressed JPEG
        img_data = pix.tobytes("jpeg", jpg_quality=q)

        new_page = new_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, stream=img_data)

    new_doc.save(output_path, garbage=4, deflate=True, clean=True)
    new_doc.close()
    doc.close()

    compressed_size = os.path.getsize(output_path)
    return output_path, orig_size, compressed_size


# ==============================================================================
# 4. IMAGE FORMAT CONVERTER
# ==============================================================================

def convert_image_format(
    input_path: str,
    output_path: str,
    target_format: str = "png",
    quality: int = 95
) -> str:
    """
    Convert image from any format to JPG, PNG, WEBP, BMP, TIFF, ICO.
    Handles alpha channels and color modes properly.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")

    target_fmt = target_format.lower().replace(".", "").strip()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img) or img

        if target_fmt in ("jpg", "jpeg"):
            # JPEG doesn't support alpha channel; composite on white
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                canvas = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                canvas.paste(img, mask=img.split()[-1])
                img = canvas
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.save(output_path, "JPEG", quality=quality, optimize=True)

        elif target_fmt == "png":
            # PNG supports RGBA, RGB, L
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGBA")
            img.save(output_path, "PNG", optimize=True)

        elif target_fmt == "webp":
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            img.save(output_path, "WEBP", quality=quality, method=6)

        elif target_fmt == "bmp":
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(output_path, "BMP")

        elif target_fmt in ("tiff", "tif"):
            img.save(output_path, "TIFF", compression="tiff_lzw")

        elif target_fmt == "ico":
            # Resize icon if needed (standard max is 256x256)
            if img.size[0] > 256 or img.size[1] > 256:
                img.thumbnail((256, 256), Image.Resampling.LANCZOS)
            img.save(output_path, format="ICO")

        else:
            # Fallback format
            img.save(output_path)

    return output_path


# ==============================================================================
# 5. MERGE / STITCH 2 TO 5 IMAGES (VERTICAL & HORIZONTAL)
# ==============================================================================

def merge_images(
    image_paths: List[str],
    output_path: str,
    direction: str = "horizontal",    # 'horizontal' or 'vertical'
    gap: int = 0,                     # gap in pixels between images
    bg_color: Union[str, Tuple[int, ...]] = "white",
    output_format: str = "png",       # 'png' recommended for sharpness
    quality: int = 95
) -> Tuple[str, Tuple[int, int]]:
    """
    Merge 2 to 5 images horizontally or vertically with clarity preservation.
    - Horizontal: Matches height of all images to the maximum height using Lanczos resampling.
    - Vertical: Matches width of all images to the maximum width using Lanczos resampling.
    Returns: (output_path, (total_width, total_height))
    """
    if not image_paths or len(image_paths) < 2:
        raise ValueError("At least 2 images are required to merge.")
    if len(image_paths) > 10:
        raise ValueError("Maximum 10 images supported.")

    loaded_images = []
    for p in image_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Image not found: {p}")
        im = Image.open(p)
        im = ImageOps.exif_transpose(im) or im
        loaded_images.append(im)

    # Determine canvas color
    color_map = {
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "transparent": (0, 0, 0, 0),
    }
    if isinstance(bg_color, str):
        canvas_bg = color_map.get(bg_color.lower(), (255, 255, 255, 255))
    else:
        canvas_bg = bg_color

    mode = "RGBA" if canvas_bg[3] < 255 or any(im.mode == "RGBA" for im in loaded_images) else "RGB"
    gap = max(0, int(gap))

    if direction.lower() == "horizontal":
        # Match all images to the maximum height for ultra-sharp clarity
        max_height = max(im.height for im in loaded_images)
        resized = []
        for im in loaded_images:
            if im.height != max_height:
                scale = max_height / im.height
                new_w = max(1, int(round(im.width * scale)))
                resized.append(im.resize((new_w, max_height), Image.Resampling.LANCZOS))
            else:
                resized.append(im)

        total_width = sum(im.width for im in resized) + gap * (len(resized) - 1)
        total_height = max_height

        canvas = Image.new(mode, (total_width, total_height), canvas_bg if mode == "RGBA" else canvas_bg[:3])
        x_offset = 0
        for im in resized:
            if mode == "RGBA" and im.mode != "RGBA":
                im = im.convert("RGBA")
            elif mode == "RGB" and im.mode != "RGB":
                im = im.convert("RGB")

            mask = im.split()[-1] if im.mode == "RGBA" else None
            canvas.paste(im, (x_offset, 0), mask=mask)
            x_offset += im.width + gap

    else:  # 'vertical'
        # Match all images to the maximum width for ultra-sharp clarity
        max_width = max(im.width for im in loaded_images)
        resized = []
        for im in loaded_images:
            if im.width != max_width:
                scale = max_width / im.width
                new_h = max(1, int(round(im.height * scale)))
                resized.append(im.resize((max_width, new_h), Image.Resampling.LANCZOS))
            else:
                resized.append(im)

        total_width = max_width
        total_height = sum(im.height for im in resized) + gap * (len(resized) - 1)

        canvas = Image.new(mode, (total_width, total_height), canvas_bg if mode == "RGBA" else canvas_bg[:3])
        y_offset = 0
        for im in resized:
            if mode == "RGBA" and im.mode != "RGBA":
                im = im.convert("RGBA")
            elif mode == "RGB" and im.mode != "RGB":
                im = im.convert("RGB")

            mask = im.split()[-1] if im.mode == "RGBA" else None
            canvas.paste(im, (0, y_offset), mask=mask)
            y_offset += im.height + gap

    # Close original opened images
    for im in loaded_images:
        im.close()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    out_fmt = output_format.lower().replace(".", "")

    if out_fmt in ("jpg", "jpeg"):
        if canvas.mode == "RGBA":
            bg = Image.new("RGB", canvas.size, (255, 255, 255))
            bg.paste(canvas, mask=canvas.split()[-1])
            canvas = bg
        elif canvas.mode != "RGB":
            canvas = canvas.convert("RGB")
        canvas.save(output_path, "JPEG", quality=quality, optimize=True)
    elif out_fmt == "webp":
        canvas.save(output_path, "WEBP", quality=quality, method=6)
    else:
        # Default to PNG for pristine sharpness
        canvas.save(output_path, "PNG", optimize=True)

    return output_path, (total_width, total_height)
