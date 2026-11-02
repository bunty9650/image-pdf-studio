"""
Command-Line Interface (CLI) for Image & PDF Processing Suite
"""

import os
import sys
import argparse

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import converter_core as cc


def main():
    parser = argparse.ArgumentParser(
        description="All-in-One Image & PDF CLI Studio",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. img2pdf
    p_img2pdf = subparsers.add_parser("img2pdf", help="Convert image(s) to a single PDF")
    p_img2pdf.add_argument("images", nargs="+", help="Input image paths (JPG, PNG, WEBP, etc.)")
    p_img2pdf.add_argument("-o", "--output", required=True, help="Output PDF file path")
    p_img2pdf.add_argument("--page-size", default="fit", choices=["fit", "A4", "Letter"], help="Page size (default: fit)")
    p_img2pdf.add_argument("--orientation", default="auto", choices=["auto", "portrait", "landscape"], help="Orientation")
    p_img2pdf.add_argument("--margin", type=float, default=0.0, help="Margin in points (default: 0)")

    # 1B. merge-pdf
    p_merge_pdf = subparsers.add_parser("merge-pdf", help="Merge multiple PDF files into one")
    p_merge_pdf.add_argument("pdfs", nargs="+", help="Input PDF file paths")
    p_merge_pdf.add_argument("-o", "--output", required=True, help="Output PDF file path")

    # 2. pdf2img
    p_pdf2img = subparsers.add_parser("pdf2img", help="Convert PDF pages to images")
    p_pdf2img.add_argument("pdf", help="Input PDF file path")
    p_pdf2img.add_argument("-o", "--output-dir", required=True, help="Destination directory for extracted images")
    p_pdf2img.add_argument("--format", default="png", choices=["png", "jpg", "webp"], help="Image format (default: png)")
    p_pdf2img.add_argument("--dpi", type=int, default=300, choices=[150, 300, 600], help="Resolution DPI (default: 300)")
    p_pdf2img.add_argument("--pages", default="all", help="Pages to extract (e.g., 'all' or '1-3, 5')")

    # 3. compress
    p_comp = subparsers.add_parser("compress", help="Compress Image or PDF")
    p_comp.add_argument("input", help="Input file path (Image or PDF)")
    p_comp.add_argument("-o", "--output", required=True, help="Output file path")
    p_comp.add_argument("--target-kb", type=float, default=None, help="Target file size in KB (e.g. 200)")
    p_comp.add_argument("--quality", type=int, default=75, help="Quality percentage 10-95 (default: 75)")

    # 4. format
    p_fmt = subparsers.add_parser("format", help="Convert image format")
    p_fmt.add_argument("input", help="Input image file")
    p_fmt.add_argument("-o", "--output", required=True, help="Output image file")
    p_fmt.add_argument("--format", default="webp", choices=["webp", "png", "jpg", "bmp", "tiff", "ico"], help="Target format")
    p_fmt.add_argument("--quality", type=int, default=95, help="Quality for lossy formats (default: 95)")

    # 5. merge
    p_merge = subparsers.add_parser("merge", help="Stitch 2 to 5 images horizontally or vertically")
    p_merge.add_argument("images", nargs="+", help="2 to 5 image paths")
    p_merge.add_argument("-o", "--output", required=True, help="Output merged image file")
    p_merge.add_argument("--direction", default="horizontal", choices=["horizontal", "vertical"], help="Merge direction")
    p_merge.add_argument("--gap", type=int, default=10, help="Pixel gap between images (default: 10)")
    p_merge.add_argument("--bg", default="white", choices=["white", "transparent", "black"], help="Background color")
    p_merge.add_argument("--format", default="png", choices=["png", "jpg", "webp"], help="Output format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "img2pdf":
            out = cc.images_to_pdf(
                image_paths=args.images,
                output_pdf_path=args.output,
                page_size=args.page_size,
                orientation=args.orientation,
                margin=args.margin
            )
            size = cc.format_file_size(os.path.getsize(out))
            print(f"✅ Successfully created PDF: {out} ({len(args.images)} pages, {size})")

        elif args.command == "merge-pdf":
            out, pages, size = cc.merge_pdfs(args.pdfs, args.output)
            print(f"✅ Merged {len(args.pdfs)} PDFs into {pages} pages ({cc.format_file_size(size)}): {out}")

        elif args.command == "pdf2img":
            out_files = cc.pdf_to_images(
                pdf_path=args.pdf,
                output_dir=args.output_dir,
                output_format=args.format,
                dpi=args.dpi,
                page_range=args.pages
            )
            print(f"✅ Extracted {len(out_files)} images into: {args.output_dir}")

        elif args.command == "compress":
            ext = os.path.splitext(args.input)[1].lower()
            if ext == ".pdf":
                out, orig, comp = cc.compress_pdf(
                    input_path=args.input,
                    output_path=args.output,
                    target_kb=args.target_kb,
                    quality=args.quality,
                    aggressive=(args.target_kb is not None)
                )
            else:
                out, orig, comp = cc.compress_image(
                    input_path=args.input,
                    output_path=args.output,
                    target_kb=args.target_kb,
                    quality=args.quality
                )
            saved = max(0, orig - comp)
            pct = (saved / max(1, orig)) * 100
            print(f"✅ Compression Complete!")
            print(f"   Original:   {cc.format_file_size(orig)}")
            print(f"   Compressed: {cc.format_file_size(comp)}")
            print(f"   Saved:      {cc.format_file_size(saved)} ({pct:.1f}% reduction)")
            print(f"   Saved at:   {out}")

        elif args.command == "format":
            out = cc.convert_image_format(
                input_path=args.input,
                output_path=args.output,
                target_format=args.format,
                quality=args.quality
            )
            print(f"✅ Image converted to {args.format.upper()}: {out}")

        elif args.command == "merge":
            out, (w, h) = cc.merge_images(
                image_paths=args.images,
                output_path=args.output,
                direction=args.direction,
                gap=args.gap,
                bg_color=args.bg,
                output_format=args.format
            )
            size = cc.format_file_size(os.path.getsize(out))
            print(f"✅ Merged {len(args.images)} images into {w}x{h} px ({size}): {out}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
