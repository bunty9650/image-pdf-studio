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
import zlib
from typing import List, Optional, Tuple, Union
from PIL import Image, ImageOps
import pymupdf
fitz = pymupdf


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
# 3. COMPRESSION & EXACT SIZE MATCHING (IMAGE & PDF)
# ==============================================================================

def pad_image_to_target_bytes(data: bytes, target_bytes: int, fmt: str) -> bytes:
    """
    Safely pad an image to strictly maintain size within -1 KB to -5 KB of target_bytes
    (specifically target - 2 KB), 100% compliant with standard decoders.
    Supports JPEG (COM markers), PNG (tEXt chunks), and WEBP (skip chunks).
    """
    desired = target_bytes - 2048  # Target is exactly 2 KB below user target
    if len(data) >= desired:
        return data

    needed = desired - len(data)
    fmt = fmt.upper()

    if fmt in ("JPEG", "JPG"):
        if data.endswith(b"\xff\xd9") and needed >= 4:
            body = data[:-2]
            chunks = []
            rem = needed
            while rem > 0:
                cur = min(rem, 65530)
                if cur < 4:
                    break
                payload_len = cur - 4
                marker = b"\xff\xfe" + (payload_len + 2).to_bytes(2, "big") + (b"0" * payload_len)
                chunks.append(marker)
                rem -= cur
            return body + b"".join(chunks) + (b"0" * rem) + b"\xff\xd9"

    elif fmt == "PNG":
        iend = data.rfind(b"IEND")
        if iend != -1:
            before_iend = data[:iend - 4]
            iend_chunk = data[iend - 4:]
            keyword = b"Comment\x00"
            overhead = 12 + len(keyword)
            if needed >= overhead:
                payload = needed - overhead
                payload_data = keyword + (b"0" * payload)
                crc = zlib.crc32(b"tEXt" + payload_data)
                chunk = len(payload_data).to_bytes(4, "big") + b"tEXt" + payload_data + crc.to_bytes(4, "big")
                return before_iend + chunk + iend_chunk

    elif fmt == "WEBP":
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP" and needed >= 8:
            payload_len = needed - 8
            chunk = b"skip" + payload_len.to_bytes(4, "little") + (b"0" * payload_len)
            new_riff_len = len(data) - 8 + len(chunk)
            return data[:4] + new_riff_len.to_bytes(4, "little") + data[8:] + chunk

    return data


def pad_pdf_to_target_bytes(data: bytes, target_bytes: int) -> bytes:
    """
    Safely pad a PDF to strictly maintain size within -1 KB to -5 KB of target_bytes
    (specifically target - 2 KB) by inserting standard comments before %%EOF.
    """
    desired = target_bytes - 2048
    if len(data) >= desired:
        return data

    needed = desired - len(data)
    eof = data.rfind(b"%%EOF")
    if eof != -1 and needed > 5:
        pad_len = needed - 3
        comment = b"% " + (b"0" * pad_len) + b"\n"
        return data[:eof] + comment + data[eof:]

    return data


def compress_image(
    input_path: str,
    output_path: str,
    target_kb: Optional[float] = None,
    quality: int = 75,
    output_format: Optional[str] = None
) -> Tuple[str, int, int]:
    """
    Compress image or increase file size to exact target size in KB (within -1 to 5 KB range).
    Returns: (output_path, original_size, final_size)
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

        # --- MODE 1: Target KB Compression OR Size Increase ---
        if target_kb is not None and target_kb > 0:
            target_bytes = int(target_kb * 1024)
            desired_bytes = target_bytes - 2048

            current_img = pil_img.copy()

            # First test: if saving at quality 95 is already <= desired_bytes,
            # we can save at crisp 95 quality and pad to exact target!
            test_buf = io.BytesIO()
            current_img.save(test_buf, format=save_format, quality=95, optimize=True)
            if test_buf.tell() <= desired_bytes:
                raw_bytes = test_buf.getvalue()
                final_bytes = pad_image_to_target_bytes(raw_bytes, target_bytes, save_format)
                with open(output_path, "wb") as f:
                    f.write(final_bytes)
                return output_path, orig_size, os.path.getsize(output_path)

            # If original is larger, compress down to fit within desired_bytes
            best_buf = None
            scale = 1.0
            for attempt in range(8):
                low_q = 10
                high_q = 95
                current_attempt_buf = None

                while low_q <= high_q:
                    mid_q = (low_q + high_q) // 2
                    buf = io.BytesIO()
                    if save_format == "PNG":
                        current_img.save(buf, format="PNG", optimize=True)
                    else:
                        current_img.save(buf, format=save_format, quality=mid_q, optimize=True)

                    s = buf.tell()
                    if s <= desired_bytes:
                        current_attempt_buf = buf
                        low_q = mid_q + 1  # Try higher quality
                    else:
                        high_q = mid_q - 1

                if current_attempt_buf is not None:
                    best_buf = current_attempt_buf
                    break

                # If even quality 10 is > desired_bytes, downscale dimensions by 15% and retry
                scale *= 0.85
                new_w = max(10, int(pil_img.width * scale))
                new_h = max(10, int(pil_img.height * scale))
                current_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            if best_buf is None:
                best_buf = io.BytesIO()
                current_img.save(best_buf, format=save_format, quality=10, optimize=True)

            raw_bytes = best_buf.getvalue()
            # Fine-tune to exactly match the target within -1 to 5 KB!
            final_bytes = pad_image_to_target_bytes(raw_bytes, target_bytes, save_format)
            with open(output_path, "wb") as f:
                f.write(final_bytes)

        # --- MODE 2: Quality Percentage Compression ---
        else:
            q = max(5, min(100, int(quality)))
            if save_format == "PNG":
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
    desired_bytes = (target_bytes - 2048) if target_bytes else None

    # If first attempt meets target or no target specified & not aggressive
    if (desired_bytes is None and not aggressive) or (desired_bytes is not None and first_size <= desired_bytes):
        raw_bytes = temp_buf.getvalue()
        if target_bytes:
            raw_bytes = pad_pdf_to_target_bytes(raw_bytes, target_bytes)
        with open(output_path, "wb") as f:
            f.write(raw_bytes)
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

    temp_out = io.BytesIO()
    new_doc.save(temp_out, garbage=4, deflate=True, clean=True)
    new_doc.close()
    doc.close()

    raw_bytes = temp_out.getvalue()
    if target_bytes:
        raw_bytes = pad_pdf_to_target_bytes(raw_bytes, target_bytes)
    with open(output_path, "wb") as f:
        f.write(raw_bytes)

    final_size = os.path.getsize(output_path)
    return output_path, orig_size, final_size


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


# ============================================================================
# NEW PDF ORGANIZER & SECURITY CORE FUNCTIONS
# ============================================================================

def split_pdf(input_pdf: str, output_dir: str, ranges: list = None) -> list:
    """
    Splits a PDF into individual page files or specific page range subsets.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    doc = fitz.open(input_pdf)
    os.makedirs(output_dir, exist_ok=True)
    out_files = []
    base = os.path.splitext(os.path.basename(input_pdf))[0]

    if not ranges:
        for i in range(len(doc)):
            sub = fitz.open()
            sub.insert_pdf(doc, from_page=i, to_page=i)
            p = os.path.join(output_dir, f"{base}_page_{i+1}.pdf")
            sub.save(p)
            sub.close()
            out_files.append(p)
    else:
        for idx, (s, e) in enumerate(ranges, 1):
            sub = fitz.open()
            sub.insert_pdf(doc, from_page=s - 1, to_page=e - 1)
            p = os.path.join(output_dir, f"{base}_part_{idx}.pdf")
            sub.save(p)
            sub.close()
            out_files.append(p)
    doc.close()
    return out_files


def remove_pdf_pages(input_pdf: str, output_pdf: str, pages_to_remove: list) -> str:
    """
    Removes specified 1-based page numbers from a PDF document.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    doc = fitz.open(input_pdf)
    remove_set = {p - 1 for p in pages_to_remove if 1 <= p <= len(doc)}
    keep_pages = [i for i in range(len(doc)) if i not in remove_set]

    if not keep_pages:
        doc.close()
        raise ValueError("Cannot remove all pages from PDF")

    doc.select(keep_pages)
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
    doc.save(output_pdf)
    doc.close()
    return output_pdf


def extract_pdf_pages(input_pdf: str, output_pdf: str, pages_to_extract: list) -> str:
    """
    Extracts specified 1-based page numbers in requested order into a new PDF.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    doc = fitz.open(input_pdf)
    extract_indices = [p - 1 for p in pages_to_extract if 1 <= p <= len(doc)]

    if not extract_indices:
        doc.close()
        raise ValueError("No valid pages to extract")

    doc.select(extract_indices)
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
    doc.save(output_pdf)
    doc.close()
    return output_pdf


def rotate_pdf_pages(input_pdf: str, output_pdf: str, rotations: dict) -> str:
    """
    Rotates specified 1-based pages by given degrees (e.g. {1: 90, 2: 180}).
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    doc = fitz.open(input_pdf)
    for p_num, angle in rotations.items():
        if 1 <= p_num <= len(doc):
            doc[p_num - 1].set_rotation((doc[p_num - 1].rotation + angle) % 360)

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
    doc.save(output_pdf)
    doc.close()
    return output_pdf


def protect_pdf(input_pdf: str, output_pdf: str, password: str) -> str:
    """
    Encrypts a PDF with standard AES-256 user and owner password protection.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    doc = fitz.open(input_pdf)
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
    doc.save(
        output_pdf,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        owner_pw=password
    )
    doc.close()
    return output_pdf


def unlock_pdf(input_pdf: str, output_pdf: str, password: str = "") -> str:
    """
    Removes password encryption and permissions restrictions from a PDF.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    doc = fitz.open(input_pdf)
    if doc.is_encrypted:
        auth = doc.authenticate(password)
        if not auth:
            doc.close()
            raise ValueError("Incorrect password for locked PDF")

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
    doc.save(output_pdf, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return output_pdf



def word_to_pdf(input_path: str, output_path: str) -> str:
    """
    Converts Microsoft Word (.docx) document to a PDF file.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    import docx
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    d = docx.Document(input_path)
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    for p in d.paragraphs:
        txt = p.text.strip()
        if txt:
            p_style = styles['Normal']
            if p.style and p.style.name and 'Heading 1' in p.style.name:
                p_style = styles['Heading1']
            elif p.style and p.style.name and 'Heading 2' in p.style.name:
                p_style = styles['Heading2']
            story.append(Paragraph(txt, p_style))
            story.append(Spacer(1, 8))

    for t in d.tables:
        t_data = []
        for row in t.rows:
            r_vals = [c.text.strip() for c in row.cells]
            t_data.append(r_vals)
        if t_data:
            t_obj = Table(t_data)
            t_obj.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
            ]))
            story.append(t_obj)
            story.append(Spacer(1, 12))

    if not story:
        story.append(Paragraph("Empty Word Document", styles['Normal']))

    pdf.build(story)
    return output_path


def excel_to_pdf(input_path: str, output_path: str) -> str:
    """
    Converts Excel spreadsheet (.xlsx, .xls) to a landscape PDF document.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    import openpyxl
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb = openpyxl.load_workbook(input_path, data_only=True)
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    for sheet_idx, sheet in enumerate(wb.worksheets):
        if sheet_idx > 0:
            story.append(PageBreak())
        story.append(Paragraph(f"<b>Sheet: {sheet.title}</b>", styles['Heading2']))
        story.append(Spacer(1, 8))

        rows = list(sheet.iter_rows(values_only=True))
        cleaned_rows = []
        for r in rows:
            if any(cell is not None for cell in r):
                cleaned_rows.append([str(c) if c is not None else "" for c in r])

        if cleaned_rows:
            t = Table(cleaned_rows)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a34a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
            ]))
            story.append(t)
            story.append(Spacer(1, 14))

    if not story:
        story.append(Paragraph("Empty Spreadsheet", styles['Normal']))

    pdf.build(story)
    return output_path


def powerpoint_to_pdf(input_path: str, output_path: str) -> str:
    """
    Converts PowerPoint presentation (.pptx) to a landscape PDF presentation.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    import pptx
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    prs = pptx.Presentation(input_path)
    pdf = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    for s_idx, slide in enumerate(prs.slides):
        if s_idx > 0:
            story.append(PageBreak())

        title_text = ""
        if slide.shapes.title and slide.shapes.title.text.strip():
            title_text = slide.shapes.title.text.strip()
        slide_title = title_text if title_text else f"Slide {s_idx + 1}"
        story.append(Paragraph(f"<b>{slide_title}</b>", styles['Heading1']))
        story.append(Spacer(1, 12))

        for shape in slide.shapes:
            if shape != slide.shapes.title and shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    txt = paragraph.text.strip()
                    if txt:
                        story.append(Paragraph(f"• {txt}", styles['Normal']))
                        story.append(Spacer(1, 6))

    if not story:
        story.append(Paragraph("Empty Presentation", styles['Normal']))

    pdf.build(story)
    return output_path


def pdf_to_word(input_pdf: str, output_docx: str) -> str:
    """
    Converts a PDF document into a Microsoft Word (.docx) file.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    import fitz
    import docx

    doc = fitz.open(input_pdf)
    d = docx.Document()
    os.makedirs(os.path.dirname(os.path.abspath(output_docx)), exist_ok=True)

    for page_idx, page in enumerate(doc):
        if page_idx > 0:
            d.add_page_break()

        # Check for tables
        tables = []
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                tables = [t.extract() for t in tabs.tables]
        except Exception:
            tables = []

        if tables:
            for t_data in tables:
                if t_data and len(t_data) > 0:
                    rows = len(t_data)
                    cols = len(t_data[0]) if rows > 0 else 0
                    if cols > 0:
                        tbl = d.add_table(rows=rows, cols=cols)
                        tbl.style = 'Table Grid'
                        for r_idx, row in enumerate(t_data):
                            for c_idx, val in enumerate(row):
                                if c_idx < cols:
                                    tbl.cell(r_idx, c_idx).text = str(val or "")
                        d.add_paragraph()

        # Extract text blocks
        blocks = page.get_text("blocks")
        for b in blocks:
            if len(b) >= 7 and b[6] == 0:  # Text block
                txt = b[4].strip()
                if txt:
                    lines = txt.split("\n")
                    for line in lines:
                        l = line.strip()
                        if l:
                            if len(l) < 60 and (l.isupper() or len(lines) == 1 and len(l) < 40):
                                d.add_heading(l, level=2)
                            else:
                                d.add_paragraph(l)

    doc.close()
    d.save(output_docx)
    return output_docx


def pdf_to_excel(input_pdf: str, output_xlsx: str) -> str:
    """
    Extracts tabular data and text from a PDF document into an Excel (.xlsx) spreadsheet.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    import fitz
    import openpyxl

    doc = fitz.open(input_pdf)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    os.makedirs(os.path.dirname(os.path.abspath(output_xlsx)), exist_ok=True)

    for page_idx, page in enumerate(doc):
        ws = wb.create_sheet(title=f"Page {page_idx + 1}")
        table_found = False

        # Try formal table extraction
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                for t in tabs.tables:
                    extracted = t.extract()
                    for r in extracted:
                        ws.append([str(c) if c is not None else "" for c in r])
                    ws.append([])
                    table_found = True
        except Exception:
            pass

        if not table_found:
            words = page.get_text("words")
            lines_dict = {}
            for w in words:
                y_center = round(w[1] / 6) * 6
                if y_center not in lines_dict:
                    lines_dict[y_center] = []
                lines_dict[y_center].append(w)

            sorted_y = sorted(lines_dict.keys())
            for y in sorted_y:
                line_words = sorted(lines_dict[y], key=lambda x: x[0])
                row_cells = []
                last_x = None
                current_cell = []
                for w in line_words:
                    if last_x is not None and (w[0] - last_x) > 25:
                        row_cells.append(" ".join(current_cell))
                        current_cell = [w[4]]
                    else:
                        current_cell.append(w[4])
                    last_x = w[2]
                if current_cell:
                    row_cells.append(" ".join(current_cell))
                if row_cells:
                    ws.append(row_cells)

    if not wb.sheetnames:
        ws = wb.create_sheet(title="Sheet 1")
        ws.append(["Empty Document"])

    doc.close()
    wb.save(output_xlsx)
    return output_xlsx


def pdf_to_powerpoint(input_pdf: str, output_pptx: str) -> str:
    """
    Converts PDF pages into a PowerPoint presentation (.pptx) with 1 slide per page.
    """
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    import fitz
    import pptx
    import shutil

    doc = fitz.open(input_pdf)
    prs = pptx.Presentation()
    prs.slide_width = pptx.util.Inches(10)
    prs.slide_height = pptx.util.Inches(5.625)
    blank_layout = prs.slide_layouts[6]
    os.makedirs(os.path.dirname(os.path.abspath(output_pptx)), exist_ok=True)

    temp_img_dir = os.path.join(os.path.dirname(os.path.abspath(output_pptx)), "_temp_pptx_slides")
    os.makedirs(temp_img_dir, exist_ok=True)

    try:
        for page_idx, page in enumerate(doc):
            slide = prs.slides.add_slide(blank_layout)
            pix = page.get_pixmap(dpi=150)
            img_path = os.path.join(temp_img_dir, f"slide_{page_idx}.png")
            pix.save(img_path)

            img_w, img_h = pix.width, pix.height
            aspect = img_w / img_h
            slide_aspect = prs.slide_width / prs.slide_height

            if aspect > slide_aspect:
                w = prs.slide_width
                h = prs.slide_width / aspect
                left = 0
                top = (prs.slide_height - h) / 2
            else:
                h = prs.slide_height
                w = prs.slide_height * aspect
                top = 0
                left = (prs.slide_width - w) / 2

            slide.shapes.add_picture(img_path, left, top, width=w, height=h)

        prs.save(output_pptx)
    finally:
        if os.path.exists(temp_img_dir):
            shutil.rmtree(temp_img_dir, ignore_errors=True)
    doc.close()
    return output_pptx
