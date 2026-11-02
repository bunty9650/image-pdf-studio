"""
All-in-One Image & PDF Studio Pro - Premium Desktop Suite
Includes:
1. High-Definition Interactive Preview Dialog (Zoom, Fit, Multi-page PDF flipping)
2. Dedicated Merge PDFs Tool with Sequence Reordering & Previews
3. Animated Canvas Progress Shimmer
4. Visual File Cards with Real Page & Image Thumbnails
5. Interactive Pill Selectors (DPI, Orientation, Direction, Formats)
6. Live Stitch Layout Graphic Canvas
7. Compression Comparison Graphic Cards
"""

import os
import sys
import io
import math
import threading
import subprocess
from typing import List, Optional, Dict, Tuple
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps

import converter_core as cc
from ui_assets import IconManager, IconTheme


# =============================================================================
# 1. HIGH-DEFINITION INTERACTIVE PREVIEW MODAL
# =============================================================================
class FilePreviewDialog(tk.Toplevel):
    """
    Modern HD Viewer Modal:
    - For Images: Displays image with zoom & pan, dimension & size info.
    - For PDFs: Displays pages rendered at high DPI, with Previous/Next page flipping.
    """
    def __init__(self, parent, file_path: str, initial_page: int = 0):
        super().__init__(parent)
        self.file_path = file_path
        self.current_page = initial_page
        self.zoom_level = 1.0

        ext = os.path.splitext(file_path)[1].upper().replace(".", "")
        self.title(f"Preview - {os.path.basename(file_path)} ({ext})")
        self.geometry("860x700")
        self.minsize(680, 500)
        self.configure(bg="#0f172a")

        # Check if PDF
        self.is_pdf = (ext == "PDF")
        self.total_pages = 1
        if self.is_pdf:
            try:
                import pymupdf
                doc = pymupdf.open(file_path)
                self.total_pages = len(doc)
                doc.close()
            except Exception:
                self.total_pages = 1

        self.setup_ui()
        self.load_and_render()

        # Center on parent
        self.transient(parent)
        self.grab_set()

    def setup_ui(self):
        # 1. Top Control Bar
        top_bar = tk.Frame(self, bg="#1e293b", padx=16, pady=10)
        top_bar.pack(fill=tk.X)

        # File name & size
        info_frame = tk.Frame(top_bar, bg="#1e293b")
        info_frame.pack(side=tk.LEFT)

        name = os.path.basename(self.file_path)
        if len(name) > 36:
            name = name[:32] + "..." + os.path.splitext(name)[1]
        sz = cc.format_file_size(os.path.getsize(self.file_path)) if os.path.exists(self.file_path) else ""

        tk.Label(info_frame, text=name, font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#1e293b").pack(anchor="w")
        self.lbl_meta = tk.Label(info_frame, text=f"File Size: {sz}", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b")
        self.lbl_meta.pack(anchor="w")

        # Zoom Controls
        zoom_frame = tk.Frame(top_bar, bg="#1e293b")
        zoom_frame.pack(side=tk.RIGHT)

        icon_zin = IconManager.get("zoom_in", 16, "#38bdf8")
        btn_zin = tk.Button(
            zoom_frame, image=icon_zin, bg="#334155", activebackground="#475569", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.zoom_in
        )
        btn_zin.image = icon_zin
        btn_zin.pack(side=tk.LEFT, padx=3)

        icon_zout = IconManager.get("zoom_out", 16, "#38bdf8")
        btn_zout = tk.Button(
            zoom_frame, image=icon_zout, bg="#334155", activebackground="#475569", bd=0, padx=6, pady=4, cursor="hand2",
            command=self.zoom_out
        )
        btn_zout.image = icon_zout
        btn_zout.pack(side=tk.LEFT, padx=3)

        btn_fit = tk.Button(
            zoom_frame, text="Fit View", font=("Segoe UI", 8, "bold"), bg="#334155", fg="#ffffff", activebackground="#475569", bd=0, padx=8, pady=4, cursor="hand2",
            command=self.zoom_fit
        )
        btn_fit.pack(side=tk.LEFT, padx=5)

        # PDF Page Navigation (if PDF)
        if self.is_pdf:
            nav_frame = tk.Frame(top_bar, bg="#1e293b")
            nav_frame.pack(side=tk.RIGHT, padx=25)

            icon_prev = IconManager.get("chevron_left", 16, "#ffffff")
            self.btn_prev = tk.Button(
                nav_frame, image=icon_prev, bg="#334155", activebackground="#475569", bd=0, padx=8, pady=4, cursor="hand2",
                command=self.prev_page
            )
            self.btn_prev.image = icon_prev
            self.btn_prev.pack(side=tk.LEFT, padx=4)

            self.lbl_page = tk.Label(nav_frame, text=f"Page 1 / {self.total_pages}", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#1e293b")
            self.lbl_page.pack(side=tk.LEFT, padx=8)

            icon_next = IconManager.get("chevron_right", 16, "#ffffff")
            self.btn_next = tk.Button(
                nav_frame, image=icon_next, bg="#334155", activebackground="#475569", bd=0, padx=8, pady=4, cursor="hand2",
                command=self.next_page
            )
            self.btn_next.image = icon_next
            self.btn_next.pack(side=tk.LEFT, padx=4)

        # 2. Main Canvas Viewport with Scrollbars
        view_container = tk.Frame(self, bg="#0f172a")
        view_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(view_container, bg="#0f172a", highlightthickness=0)
        self.hbar = ttk.Scrollbar(view_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(view_container, orient=tk.VERTICAL, command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")

        view_container.rowconfigure(0, weight=1)
        view_container.columnconfigure(0, weight=1)

        self.bind("<Configure>", lambda e: self.on_resize())

    def load_and_render(self):
        try:
            if self.is_pdf:
                self.raw_pil = cc.get_pdf_page_image(self.file_path, self.current_page, dpi=160)
                if hasattr(self, "lbl_page"):
                    self.lbl_page.config(text=f"Page {self.current_page + 1} / {self.total_pages}")
            else:
                im = Image.open(self.file_path)
                self.raw_pil = ImageOps.exif_transpose(im) or im

            w, h = self.raw_pil.size
            sz = cc.format_file_size(os.path.getsize(self.file_path))
            self.lbl_meta.config(text=f"Resolution: {w} x {h} px  |  File Size: {sz}")
            self.update_canvas_image()
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(
                400, 300,
                text=f"Failed to load preview:\n{e}",
                fill="#ef4444",
                font=("Segoe UI", 12, "bold")
            )

    def update_canvas_image(self):
        if not hasattr(self, "raw_pil") or self.raw_pil is None:
            return

        cw = max(200, self.canvas.winfo_width())
        ch = max(200, self.canvas.winfo_height())
        if cw < 300:
            cw, ch = 800, 600

        # Calculate display size with zoom
        orig_w, orig_h = self.raw_pil.size
        ratio = min(cw / orig_w, ch / orig_h)
        target_w = max(50, int(orig_w * ratio * self.zoom_level))
        target_h = max(50, int(orig_h * ratio * self.zoom_level))

        resized = self.raw_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(
            max(cw // 2, target_w // 2),
            max(ch // 2, target_h // 2),
            image=self.photo,
            anchor="center"
        )
        self.canvas.configure(scrollregion=(0, 0, max(cw, target_w), max(ch, target_h)))

    def on_resize(self):
        if hasattr(self, "raw_pil"):
            self.update_canvas_image()

    def zoom_in(self):
        self.zoom_level = min(3.0, self.zoom_level + 0.25)
        self.update_canvas_image()

    def zoom_out(self):
        self.zoom_level = max(0.25, self.zoom_level - 0.25)
        self.update_canvas_image()

    def zoom_fit(self):
        self.zoom_level = 1.0
        self.update_canvas_image()

    def prev_page(self):
        if self.is_pdf and self.current_page > 0:
            self.current_page -= 1
            self.load_and_render()

    def next_page(self):
        if self.is_pdf and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_and_render()


# =============================================================================
# 2. ANIMATED SHIMMER CANVAS PROGRESS BAR
# =============================================================================
class AnimatedProgressBar(tk.Canvas):
    """Modern glowing shimmer progress bar that pulses when active."""
    def __init__(self, parent, height: int = 6, **kwargs):
        super().__init__(parent, height=height, bg="#e2e8f0", highlightthickness=0, bd=0, **kwargs)
        self.is_running = False
        self.pos = 0
        self.anim_id = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.pos = 0
            self._animate()

    def stop(self):
        self.is_running = False
        if self.anim_id:
            self.after_cancel(self.anim_id)
            self.anim_id = None
        self.delete("all")

    def _animate(self):
        if not self.is_running:
            return
        w = max(50, self.winfo_width())
        h = max(4, self.winfo_height())
        bar_w = int(w * 0.3)

        self.delete("all")
        # Draw background track
        self.create_rectangle(0, 0, w, h, fill="#e2e8f0", outline="")

        # Draw glowing shimmer block
        x0 = self.pos
        x1 = self.pos + bar_w
        self.create_rectangle(x0, 0, x1, h, fill="#2563eb", outline="")

        self.pos = (self.pos + 12) % (w + bar_w)
        if self.pos - bar_w > w:
            self.pos = -bar_w

        self.anim_id = self.after(25, self._animate)


# =============================================================================
# 3. INTERACTIVE PILL SELECTOR (REPLACES STANDARD RADIO BUTTONS)
# =============================================================================
class PillSelector(tk.Frame):
    """Modern segmented pill button group with animated selection feedback."""
    def __init__(self, parent, options: List[Tuple[str, str]], default_value: str, on_change=None):
        super().__init__(parent, bg="#ffffff")
        self.options = options  # [(label, value), ...]
        self.value = default_value
        self.on_change = on_change
        self.buttons: Dict[str, tk.Label] = {}

        for lbl, val in options:
            btn = tk.Label(
                self,
                text=lbl,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                padx=12,
                pady=5,
                bd=0
            )
            btn.pack(side=tk.LEFT, padx=3)
            btn.bind("<Button-1>", lambda e, v=val: self.select(v))
            self.buttons[val] = btn

        self.render_state()

    def select(self, val: str):
        self.value = val
        self.render_state()
        if self.on_change:
            self.on_change(val)

    def render_state(self):
        for val, btn in self.buttons.items():
            if val == self.value:
                btn.configure(bg="#2563eb", fg="#ffffff", highlightthickness=0)
            else:
                btn.configure(bg="#f1f5f9", fg="#475569", highlightthickness=1, highlightbackground="#e2e8f0")

    def get(self) -> str:
        return self.value


# =============================================================================
# 4. MODERN VISUAL FILE CARD WITH PREVIEW & SEQUENCE BUTTONS
# =============================================================================
class ModernFileCard(tk.Frame):
    """
    Sleek file card featuring:
    - Real Image or PDF First-Page Thumbnail
    - Sequence Badge & Step indicator
    - Eye / Preview Button (opens HD interactive previewer)
    - Move Up, Move Down, and Trash actions
    """
    def __init__(self, parent, file_path: str, index: int, total_count: int,
                 on_up=None, on_down=None, on_delete=None, on_preview=None):
        super().__init__(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", bd=0)
        self.file_path = file_path
        self.index = index
        self.total_count = total_count
        self.on_up = on_up
        self.on_down = on_down
        self.on_delete = on_delete
        self.on_preview = on_preview

        self.configure(padx=12, pady=8)
        self.pack(fill=tk.X, pady=3, padx=2)

        # 1. Sequence Number Badge
        lbl_seq = tk.Label(
            self,
            text=f"{index + 1}",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            width=2,
            pady=2
        )
        lbl_seq.pack(side=tk.LEFT, padx=(0, 10))

        # 2. Thumbnail Preview
        self.thumb_label = tk.Label(self, bg="#ffffff", cursor="hand2")
        self.thumb_label.pack(side=tk.LEFT, padx=(0, 10))
        self.thumb_label.bind("<Button-1>", lambda e: self.trigger_preview())
        self.load_thumbnail()

        # 3. Middle Metadata
        info_frame = tk.Frame(self, bg="#ffffff")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        name_text = os.path.basename(file_path)
        if len(name_text) > 40:
            name_text = name_text[:36] + "..." + os.path.splitext(name_text)[1]

        lbl_name = tk.Label(
            info_frame,
            text=name_text,
            font=("Segoe UI", 10, "bold"),
            fg="#0f172a",
            bg="#ffffff",
            anchor="w"
        )
        lbl_name.pack(anchor="w")

        # Badges row
        badge_frame = tk.Frame(info_frame, bg="#ffffff")
        badge_frame.pack(anchor="w", pady=(2, 0))

        ext = os.path.splitext(file_path)[1].upper().replace(".", "") or "FILE"
        sz_str = cc.format_file_size(os.path.getsize(file_path)) if os.path.exists(file_path) else "N/A"

        # Format Badge
        bg_col = "#fee2e2" if ext == "PDF" else "#eff6ff"
        fg_col = "#dc2626" if ext == "PDF" else "#2563eb"
        lbl_fmt = tk.Label(badge_frame, text=f" {ext} ", font=("Segoe UI", 8, "bold"), bg=bg_col, fg=fg_col, padx=4, pady=1)
        lbl_fmt.pack(side=tk.LEFT, padx=(0, 6))

        # Page count if PDF
        if ext == "PDF":
            try:
                import pymupdf
                doc = pymupdf.open(file_path)
                p_count = len(doc)
                doc.close()
                lbl_pages = tk.Label(badge_frame, text=f" {p_count} Pages ", font=("Segoe UI", 8, "bold"), bg="#fef3c7", fg="#b45309", padx=4, pady=1)
                lbl_pages.pack(side=tk.LEFT, padx=(0, 6))
            except Exception:
                pass

        # Size Badge
        lbl_size = tk.Label(badge_frame, text=f" {sz_str} ", font=("Segoe UI", 8), bg="#f1f5f9", fg="#475569", padx=4, pady=1)
        lbl_size.pack(side=tk.LEFT)

        # 4. Right Action Buttons
        btn_frame = tk.Frame(self, bg="#ffffff")
        btn_frame.pack(side=tk.RIGHT)

        # EYE / PREVIEW BUTTON
        icon_eye = IconManager.get("eye", 16, "#2563eb")
        btn_eye = tk.Button(
            btn_frame,
            image=icon_eye,
            relief="flat",
            bg="#eff6ff",
            activebackground="#dbeafe",
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=self.trigger_preview
        )
        btn_eye.image = icon_eye
        btn_eye.pack(side=tk.LEFT, padx=3)

        # Move Up
        icon_up = IconManager.get("btn_up", 16, "#2563eb")
        btn_u = tk.Button(
            btn_frame,
            image=icon_up,
            relief="flat",
            bg="#f8fafc",
            activebackground="#e2e8f0",
            bd=0,
            padx=5,
            pady=4,
            cursor="hand2",
            command=lambda: self.on_up(self.index) if self.on_up else None
        )
        btn_u.image = icon_up
        if index > 0:
            btn_u.pack(side=tk.LEFT, padx=2)

        # Move Down
        icon_down = IconManager.get("btn_down", 16, "#2563eb")
        btn_d = tk.Button(
            btn_frame,
            image=icon_down,
            relief="flat",
            bg="#f8fafc",
            activebackground="#e2e8f0",
            bd=0,
            padx=5,
            pady=4,
            cursor="hand2",
            command=lambda: self.on_down(self.index) if self.on_down else None
        )
        btn_d.image = icon_down
        if index < total_count - 1:
            btn_d.pack(side=tk.LEFT, padx=2)

        # Delete
        icon_del = IconManager.get("btn_delete", 16, "#ef4444")
        btn_del = tk.Button(
            btn_frame,
            image=icon_del,
            relief="flat",
            bg="#fef2f2",
            activebackground="#fee2e2",
            bd=0,
            padx=7,
            pady=4,
            cursor="hand2",
            command=lambda: self.on_delete(self.index) if self.on_delete else None
        )
        btn_del.image = icon_del
        btn_del.pack(side=tk.LEFT, padx=(4, 0))

    def trigger_preview(self):
        if self.on_preview:
            self.on_preview(self.file_path)

    def load_thumbnail(self):
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".pdf":
            try:
                # Render real first page of PDF!
                im = cc.get_pdf_page_image(self.file_path, 0, dpi=48)
                im.thumbnail((40, 40), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (40, 40), (254, 226, 226, 255))
                ox = (40 - im.width) // 2
                oy = (40 - im.height) // 2
                canvas.paste(im, (ox, oy))
                photo = ImageTk.PhotoImage(canvas)
                self.thumb_label.config(image=photo)
                self.thumb_label.image = photo
                return
            except Exception:
                ico = IconManager.get("badge_pdf", 38)
                self.thumb_label.config(image=ico)
                self.thumb_label.image = ico
                return

        try:
            with Image.open(self.file_path) as im:
                im = ImageOps.exif_transpose(im) or im
                im.thumbnail((40, 40), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (40, 40), (241, 245, 249, 255))
                ox = (40 - im.width) // 2
                oy = (40 - im.height) // 2
                canvas.paste(im, (ox, oy))
                photo = ImageTk.PhotoImage(canvas)
                self.thumb_label.config(image=photo)
                self.thumb_label.image = photo
        except Exception:
            ico = IconManager.get("badge_image", 38)
            self.thumb_label.config(image=ico)
            self.thumb_label.image = ico


# =============================================================================
# 5. SCROLLABLE CONTAINER WITH GRAPHICAL EMPTY STATE
# =============================================================================
class ScrollableCardContainer(tk.Frame):
    """Custom scrollable canvas container with illustrated empty state graphic."""
    def __init__(self, parent, height: int = 180, **kwargs):
        super().__init__(parent, bg="#f8fafc", highlightthickness=1, highlightbackground="#e2e8f0", **kwargs)
        self.canvas = tk.Canvas(self, bg="#f8fafc", highlightthickness=0, height=height)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="#f8fafc")

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.scroll_frame.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def clear(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

    def show_empty(self, message: str = "No files added yet."):
        self.clear()
        wrap = tk.Frame(self.scroll_frame, bg="#f8fafc", pady=30)
        wrap.pack(fill=tk.BOTH, expand=True)

        hero = IconManager.get("hero_empty", 64)
        lbl_img = tk.Label(wrap, image=hero, bg="#f8fafc")
        lbl_img.image = hero
        lbl_img.pack()

        tk.Label(wrap, text=message, font=("Segoe UI", 10, "bold"), fg="#475569", bg="#f8fafc").pack(pady=(6, 2))
        tk.Label(wrap, text="Click 'Add Files...' above to arrange sequence and preview", font=("Segoe UI", 8), fg="#94a3b8", bg="#f8fafc").pack()


# =============================================================================
# 6. MAIN APPLICATION
# =============================================================================
class ModernStudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("All-in-One Image & PDF Studio Pro")
        self.root.geometry("1060x760")
        self.root.minsize(940, 660)

        if sys.platform == "win32":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self.last_output_dir = os.path.abspath(os.getcwd())
        self.setup_styles()
        self.create_main_layout()

        # Default Active Tab
        self.switch_tab("img2pdf")

    def setup_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.root.configure(bg="#f8fafc")
        self.style.configure(".", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 9))
        self.style.configure("TFrame", background="#f8fafc")
        self.style.configure("TLabel", background="#f8fafc", foreground="#0f172a")

    def create_main_layout(self):
        # 1. Left Dark Sidebar
        self.sidebar = tk.Frame(self.root, bg="#0f172a", width=255)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # 2. Right Workspace
        self.workspace = tk.Frame(self.root, bg="#f8fafc")
        self.workspace.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.build_sidebar()
        self.build_workspace_footer()
        self.build_workspace_content()

    # =========================================================================
    # SIDEBAR
    # =========================================================================
    def build_sidebar(self):
        # Brand Header Box
        brand_box = tk.Frame(self.sidebar, bg="#0f172a", pady=20, padx=16)
        brand_box.pack(fill=tk.X)

        logo_img = IconManager.get("logo", 36)
        lbl_logo = tk.Label(brand_box, image=logo_img, bg="#0f172a")
        lbl_logo.image = logo_img
        lbl_logo.pack(side=tk.LEFT, padx=(0, 10))

        title_frame = tk.Frame(brand_box, bg="#0f172a")
        title_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        lbl_title = tk.Label(title_frame, text="Studio Pro", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(title_frame, text="Image & PDF Engine", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a")
        lbl_sub.pack(anchor="w")

        div = tk.Frame(self.sidebar, bg="#1e293b", height=1)
        div.pack(fill=tk.X, padx=16, pady=(0, 15))

        # Nav Items (Now Includes Merge PDFs!)
        self.nav_buttons: Dict[str, tk.Frame] = {}
        self.nav_items = [
            ("img2pdf", "nav_img2pdf", "Images to PDF"),
            ("merge_pdf", "nav_merge_pdf", "Merge PDFs"),
            ("pdf2img", "nav_pdf2img", "PDF to Images"),
            ("compress", "nav_compress", "Smart Compressor"),
            ("format", "nav_format", "Format Converter"),
            ("merge", "nav_stitch", "Stitch 2-5 Images")
        ]

        menu_container = tk.Frame(self.sidebar, bg="#0f172a")
        menu_container.pack(fill=tk.BOTH, expand=True, padx=12)

        for key, icon_name, label_text in self.nav_items:
            item_frame = self.create_nav_item(menu_container, key, icon_name, label_text)
            self.nav_buttons[key] = item_frame

        # Footer Badge with Canvas Status Dot
        foot = tk.Frame(self.sidebar, bg="#1e293b", padx=12, pady=10)
        foot.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=14)

        status_row = tk.Frame(foot, bg="#1e293b")
        status_row.pack(anchor="w")

        dot_cv = tk.Canvas(status_row, width=8, height=8, bg="#1e293b", highlightthickness=0)
        dot_cv.pack(side=tk.LEFT, padx=(0, 6))
        dot_cv.create_oval(1, 1, 7, 7, fill="#10b981", outline="")

        lbl_offline = tk.Label(status_row, text="Offline and Private", font=("Segoe UI", 8, "bold"), fg="#10b981", bg="#1e293b")
        lbl_offline.pack(side=tk.LEFT)

        lbl_loc = tk.Label(foot, text="All conversions local", font=("Segoe UI", 8), fg="#64748b", bg="#1e293b")
        lbl_loc.pack(anchor="w", pady=(2, 0))

    def create_nav_item(self, parent, key: str, icon_name: str, label_text: str) -> tk.Frame:
        frame = tk.Frame(parent, bg="#0f172a", cursor="hand2")
        frame.pack(fill=tk.X, pady=3)

        bar = tk.Frame(frame, bg="#0f172a", width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        frame.bar = bar

        content = tk.Frame(frame, bg="#0f172a", padx=10, pady=8)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        icon_normal = IconManager.get(icon_name, 20, "#94a3b8")
        icon_active = IconManager.get(icon_name, 20, "#38bdf8")
        frame.icon_normal = icon_normal
        frame.icon_active = icon_active

        lbl_icon = tk.Label(content, image=icon_normal, bg="#0f172a")
        lbl_icon.pack(side=tk.LEFT, padx=(0, 10))
        frame.lbl_icon = lbl_icon

        lbl_text = tk.Label(content, text=label_text, font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#0f172a")
        lbl_text.pack(side=tk.LEFT)
        frame.lbl_text = lbl_text

        for widget in (frame, bar, content, lbl_icon, lbl_text):
            widget.bind("<Button-1>", lambda e, k=key: self.switch_tab(k))
            widget.bind("<Enter>", lambda e, f=frame, k=key: self.on_nav_hover(f, k, True))
            widget.bind("<Leave>", lambda e, f=frame, k=key: self.on_nav_hover(f, k, False))

        return frame

    def on_nav_hover(self, frame, key: str, is_hover: bool):
        if getattr(self, "current_tab", None) == key:
            return
        bg = "#1e293b" if is_hover else "#0f172a"
        fg = "#f8fafc" if is_hover else "#94a3b8"
        frame.configure(bg=bg)
        frame.children[list(frame.children.keys())[1]].configure(bg=bg)
        frame.lbl_icon.configure(bg=bg)
        frame.lbl_text.configure(bg=bg, fg=fg)

    def switch_tab(self, key: str):
        self.current_tab = key
        for k, f in self.nav_buttons.items():
            content = f.children[list(f.children.keys())[1]]
            if k == key:
                f.configure(bg="#1e293b")
                f.bar.configure(bg="#3b82f6")
                content.configure(bg="#1e293b")
                f.lbl_icon.configure(image=f.icon_active, bg="#1e293b")
                f.lbl_text.configure(bg="#1e293b", fg="#ffffff")
            else:
                f.configure(bg="#0f172a")
                f.bar.configure(bg="#0f172a")
                content.configure(bg="#0f172a")
                f.lbl_icon.configure(image=f.icon_normal, bg="#0f172a")
                f.lbl_text.configure(bg="#0f172a", fg="#94a3b8")

        for pane_key, pane in self.tab_panes.items():
            if pane_key == key:
                pane.pack(fill=tk.BOTH, expand=True, padx=22, pady=(15, 6))
            else:
                pane.pack_forget()

    # =========================================================================
    # WORKSPACE FOOTER
    # =========================================================================
    def build_workspace_footer(self):
        self.footer_frame = tk.Frame(self.workspace, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=8)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Animated Shimmer Progress Bar
        self.progress_bar = AnimatedProgressBar(self.footer_frame, height=5)
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        row = tk.Frame(self.footer_frame, bg="#ffffff")
        row.pack(fill=tk.X)

        # Status icon canvas & text
        self.status_dot_canvas = tk.Canvas(row, width=10, height=10, bg="#ffffff", highlightthickness=0)
        self.status_dot_canvas.pack(side=tk.LEFT, padx=(0, 6))
        self.dot_item = self.status_dot_canvas.create_oval(1, 1, 9, 9, fill="#10b981", outline="")

        self.status_label = tk.Label(
            row,
            text="Ready. Select files, adjust sequence, or preview above.",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#ffffff"
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        icon_folder = IconManager.get("open_folder", 18, "#2563eb")
        self.btn_open_folder = tk.Button(
            row,
            text="  Open Output Folder",
            image=icon_folder,
            compound="left",
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            activebackground="#e2e8f0",
            fg="#2563eb",
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.open_output_folder
        )
        self.btn_open_folder.image = icon_folder
        self.btn_open_folder.pack(side=tk.RIGHT)

    def set_status(self, text: str, is_working: bool = False, state: str = "normal"):
        self.status_label.config(text=text)
        if is_working:
            self.status_dot_canvas.itemconfig(self.dot_item, fill="#3b82f6")
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            if state == "success":
                self.status_dot_canvas.itemconfig(self.dot_item, fill="#10b981")
            elif state == "error":
                self.status_dot_canvas.itemconfig(self.dot_item, fill="#ef4444")
            else:
                self.status_dot_canvas.itemconfig(self.dot_item, fill="#64748b")

    def open_output_folder(self):
        if os.path.exists(self.last_output_dir):
            if sys.platform == "win32":
                os.startfile(self.last_output_dir)
            else:
                subprocess.run(["xdg-open", self.last_output_dir])
        else:
            messagebox.showinfo("Folder", f"Folder not found: {self.last_output_dir}")

    def show_preview_dialog(self, file_path: str):
        FilePreviewDialog(self.root, file_path)

    # =========================================================================
    # WORKSPACE CONTENT PAGES
    # =========================================================================
    def build_workspace_content(self):
        self.tab_panes: Dict[str, tk.Frame] = {}

        # 1. Images to PDF
        self.tab_panes["img2pdf"] = tk.Frame(self.workspace, bg="#f8fafc")
        self.build_page_img2pdf(self.tab_panes["img2pdf"])

        # 2. Merge PDFs (NEW!)
        self.tab_panes["merge_pdf"] = tk.Frame(self.workspace, bg="#f8fafc")
        self.build_page_merge_pdfs(self.tab_panes["merge_pdf"])

        # 3. PDF to Images
        self.tab_panes["pdf2img"] = tk.Frame(self.workspace, bg="#f8fafc")
        self.build_page_pdf2img(self.tab_panes["pdf2img"])

        # 4. Smart Compressor
        self.tab_panes["compress"] = tk.Frame(self.workspace, bg="#f8fafc")
        self.build_page_compress(self.tab_panes["compress"])

        # 5. Format Converter
        self.tab_panes["format"] = tk.Frame(self.workspace, bg="#f8fafc")
        self.build_page_format(self.tab_panes["format"])

        # 6. Stitch 2-5 Images
        self.tab_panes["merge"] = tk.Frame(self.workspace, bg="#f8fafc")
        self.build_page_merge(self.tab_panes["merge"])

    # -------------------------------------------------------------------------
    # TAB 1: IMAGES TO PDF (With Sequence Reorder & Previews)
    # -------------------------------------------------------------------------
    def build_page_img2pdf(self, parent):
        h_frame = tk.Frame(parent, bg="#f8fafc")
        h_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(h_frame, text="Images to PDF", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="#f8fafc").pack(anchor="w")
        tk.Label(h_frame, text="Reorder sequence, preview images, and combine into a single PDF", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc").pack(anchor="w")

        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=12)
        card.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        tb = tk.Frame(card, bg="#ffffff")
        tb.pack(fill=tk.X, pady=(0, 8))

        icon_add = IconManager.get("btn_add", 16, "#ffffff")
        btn_add = tk.Button(
            tb, text="  Add Images...", image=icon_add, compound="left", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
            command=self.img2pdf_add_images
        )
        btn_add.image = icon_add
        btn_add.pack(side=tk.LEFT, padx=(0, 6))

        btn_rev = tk.Button(
            tb, text="Reverse Order", font=("Segoe UI", 8, "bold"), bg="#f1f5f9", activebackground="#e2e8f0",
            fg="#334155", relief="flat", bd=0, padx=8, pady=6, cursor="hand2", command=self.img2pdf_reverse
        )
        btn_rev.pack(side=tk.LEFT, padx=(0, 6))

        icon_clear = IconManager.get("btn_clear", 16, "#475569")
        btn_clear = tk.Button(
            tb, text="  Clear", image=icon_clear, compound="left", font=("Segoe UI", 9),
            bg="#f1f5f9", activebackground="#e2e8f0", fg="#475569", relief="flat", bd=0, padx=8, pady=6, cursor="hand2",
            command=self.img2pdf_clear
        )
        btn_clear.image = icon_clear
        btn_clear.pack(side=tk.LEFT)

        self.lbl_img2pdf_count = tk.Label(tb, text="0 images added", font=("Segoe UI", 9), fg="#64748b", bg="#ffffff")
        self.lbl_img2pdf_count.pack(side=tk.RIGHT)

        # Container
        self.img2pdf_container = ScrollableCardContainer(card, height=170)
        self.img2pdf_container.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Pill Selectors for Page Settings
        sbox = tk.LabelFrame(card, text=" Page Layout Settings ", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff", padx=10, pady=6)
        sbox.pack(fill=tk.X, pady=(0, 8))

        r_opts = tk.Frame(sbox, bg="#ffffff")
        r_opts.pack(fill=tk.X)

        tk.Label(r_opts, text="Page Size:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.img2pdf_pagesize_pill = PillSelector(r_opts, [("Fit Original", "fit"), ("A4", "A4"), ("Letter", "Letter")], "fit")
        self.img2pdf_pagesize_pill.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(r_opts, text="Orientation:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.img2pdf_orient_pill = PillSelector(r_opts, [("Auto", "auto"), ("Portrait", "portrait"), ("Landscape", "landscape")], "auto")
        self.img2pdf_orient_pill.pack(side=tk.LEFT)

        # Output Path
        out_f = tk.Frame(card, bg="#ffffff")
        out_f.pack(fill=tk.X, pady=(0, 10))
        tk.Label(out_f, text="Save PDF As:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

        self.img2pdf_out_var = tk.StringVar(value="")
        ttk.Entry(out_f, textvariable=self.img2pdf_out_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        icon_fold = IconManager.get("btn_folder", 16)
        btn_br = tk.Button(out_f, text=" Browse...", image=icon_fold, compound="left", font=("Segoe UI", 9), bg="#f1f5f9", activebackground="#e2e8f0", relief="flat", bd=0, padx=8, pady=4, command=self.img2pdf_browse_output)
        btn_br.image = icon_fold
        btn_br.pack(side=tk.LEFT)

        # Action Convert Button
        icon_play = IconManager.get("btn_play", 18, "#ffffff")
        self.btn_convert_pdf = tk.Button(
            card, text="  Convert Image(s) to PDF", image=icon_play, compound="left", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
            command=self.img2pdf_execute
        )
        self.btn_convert_pdf.image = icon_play
        self.btn_convert_pdf.pack(fill=tk.X)

        self.img2pdf_files: List[str] = []
        self.img2pdf_refresh_list()

    def img2pdf_add_images(self):
        files = filedialog.askopenfilenames(
            title="Select Images to Convert",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff;*.tif;*.gif;*.ico"), ("All Files", "*.*")]
        )
        if files:
            for f in files:
                if f not in self.img2pdf_files:
                    self.img2pdf_files.append(f)
            self.img2pdf_refresh_list()
            if not self.img2pdf_out_var.get() and self.img2pdf_files:
                first = self.img2pdf_files[0]
                base_dir = os.path.dirname(first)
                base_name = os.path.splitext(os.path.basename(first))[0]
                suffix = "_converted.pdf" if len(self.img2pdf_files) == 1 else "_merged_images.pdf"
                self.img2pdf_out_var.set(os.path.join(base_dir, base_name + suffix))

    def img2pdf_refresh_list(self):
        self.img2pdf_container.clear()
        self.lbl_img2pdf_count.config(text=f"{len(self.img2pdf_files)} image(s) in sequence")

        if not self.img2pdf_files:
            self.img2pdf_container.show_empty("No images added yet. Click 'Add Images...' to begin.")
            return

        for idx, f in enumerate(self.img2pdf_files):
            ModernFileCard(
                self.img2pdf_container.scroll_frame,
                file_path=f,
                index=idx,
                total_count=len(self.img2pdf_files),
                on_up=self.img2pdf_move_up,
                on_down=self.img2pdf_move_down,
                on_delete=self.img2pdf_remove_item,
                on_preview=self.show_preview_dialog
            )

    def img2pdf_move_up(self, idx: int):
        if idx > 0:
            self.img2pdf_files[idx - 1], self.img2pdf_files[idx] = self.img2pdf_files[idx], self.img2pdf_files[idx - 1]
            self.img2pdf_refresh_list()

    def img2pdf_move_down(self, idx: int):
        if idx < len(self.img2pdf_files) - 1:
            self.img2pdf_files[idx + 1], self.img2pdf_files[idx] = self.img2pdf_files[idx], self.img2pdf_files[idx + 1]
            self.img2pdf_refresh_list()

    def img2pdf_reverse(self):
        self.img2pdf_files.reverse()
        self.img2pdf_refresh_list()

    def img2pdf_remove_item(self, idx: int):
        if 0 <= idx < len(self.img2pdf_files):
            del self.img2pdf_files[idx]
            self.img2pdf_refresh_list()

    def img2pdf_clear(self):
        self.img2pdf_files.clear()
        self.img2pdf_refresh_list()

    def img2pdf_browse_output(self):
        path = filedialog.asksaveasfilename(title="Save PDF As", defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")])
        if path:
            self.img2pdf_out_var.set(path)

    def img2pdf_execute(self):
        if not self.img2pdf_files:
            messagebox.showwarning("No Images", "Please add at least one image file.")
            return

        out_path = self.img2pdf_out_var.get().strip()
        if not out_path:
            messagebox.showwarning("Missing Output", "Please choose an output PDF destination.")
            return

        page_size = self.img2pdf_pagesize_pill.get()
        orientation = self.img2pdf_orient_pill.get()

        self.set_status("Creating PDF from images in specified sequence...", is_working=True)
        self.btn_convert_pdf.config(state="disabled")

        def worker():
            try:
                res = cc.images_to_pdf(
                    image_paths=self.img2pdf_files,
                    output_pdf_path=out_path,
                    page_size=page_size,
                    orientation=orientation,
                    margin=0.0
                )
                self.last_output_dir = os.path.dirname(os.path.abspath(res))
                size_str = cc.format_file_size(os.path.getsize(res))
                msg = f"PDF Created Successfully! ({len(self.img2pdf_files)} pages, {size_str})"
                self.root.after(0, lambda: self.on_task_complete(msg, res, self.btn_convert_pdf))
            except Exception as e:
                self.root.after(0, lambda: self.on_task_error(str(e), self.btn_convert_pdf))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # TAB 2: MERGE PDFS (NEW FEATURE!)
    # -------------------------------------------------------------------------
    def build_page_merge_pdfs(self, parent):
        h_frame = tk.Frame(parent, bg="#f8fafc")
        h_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(h_frame, text="Merge PDF Documents", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="#f8fafc").pack(anchor="w")
        tk.Label(h_frame, text="Arrange document sequence, flip through pages in preview, and merge into 1 PDF", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc").pack(anchor="w")

        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=12)
        card.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        tb = tk.Frame(card, bg="#ffffff")
        tb.pack(fill=tk.X, pady=(0, 8))

        icon_add = IconManager.get("btn_add", 16, "#ffffff")
        btn_add = tk.Button(
            tb, text="  Add PDF Files...", image=icon_add, compound="left", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
            command=self.merge_pdf_add_files
        )
        btn_add.image = icon_add
        btn_add.pack(side=tk.LEFT, padx=(0, 6))

        btn_rev = tk.Button(
            tb, text="Reverse Order", font=("Segoe UI", 8, "bold"), bg="#f1f5f9", activebackground="#e2e8f0",
            fg="#334155", relief="flat", bd=0, padx=8, pady=6, cursor="hand2", command=self.merge_pdf_reverse
        )
        btn_rev.pack(side=tk.LEFT, padx=(0, 6))

        icon_clear = IconManager.get("btn_clear", 16, "#475569")
        btn_clear = tk.Button(
            tb, text="  Clear", image=icon_clear, compound="left", font=("Segoe UI", 9),
            bg="#f1f5f9", activebackground="#e2e8f0", fg="#475569", relief="flat", bd=0, padx=8, pady=6, cursor="hand2",
            command=self.merge_pdf_clear
        )
        btn_clear.image = icon_clear
        btn_clear.pack(side=tk.LEFT)

        self.lbl_merge_pdf_count = tk.Label(tb, text="0 PDFs selected", font=("Segoe UI", 9, "bold"), fg="#64748b", bg="#ffffff")
        self.lbl_merge_pdf_count.pack(side=tk.RIGHT)

        # Container
        self.merge_pdf_container = ScrollableCardContainer(card, height=190)
        self.merge_pdf_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Output Path
        out_f = tk.Frame(card, bg="#ffffff")
        out_f.pack(fill=tk.X, pady=(0, 10))
        tk.Label(out_f, text="Save Merged PDF As:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

        self.merge_pdf_out_var = tk.StringVar(value="")
        ttk.Entry(out_f, textvariable=self.merge_pdf_out_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        icon_fold = IconManager.get("btn_folder", 16)
        btn_br = tk.Button(out_f, text=" Browse...", image=icon_fold, compound="left", font=("Segoe UI", 9), bg="#f1f5f9", activebackground="#e2e8f0", relief="flat", bd=0, padx=8, pady=4, command=self.merge_pdf_browse_output)
        btn_br.image = icon_fold
        btn_br.pack(side=tk.LEFT)

        # Action Merge Button
        icon_play = IconManager.get("btn_play", 18, "#ffffff")
        self.btn_run_merge_pdf = tk.Button(
            card, text="  Merge PDFs into Single Document", image=icon_play, compound="left", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
            command=self.merge_pdf_execute
        )
        self.btn_run_merge_pdf.image = icon_play
        self.btn_run_merge_pdf.pack(fill=tk.X)

        self.merge_pdf_files: List[str] = []
        self.merge_pdf_refresh_list()

    def merge_pdf_add_files(self):
        files = filedialog.askopenfilenames(
            title="Select PDF Files to Merge",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
        )
        if files:
            for f in files:
                if f not in self.merge_pdf_files:
                    self.merge_pdf_files.append(f)
            self.merge_pdf_refresh_list()
            if not self.merge_pdf_out_var.get() and self.merge_pdf_files:
                base_dir = os.path.dirname(self.merge_pdf_files[0])
                self.merge_pdf_out_var.set(os.path.join(base_dir, "combined_document.pdf"))

    def merge_pdf_refresh_list(self):
        self.merge_pdf_container.clear()
        total_p = 0
        for f in self.merge_pdf_files:
            try:
                import pymupdf
                doc = pymupdf.open(f)
                total_p += len(doc)
                doc.close()
            except Exception:
                pass

        self.lbl_merge_pdf_count.config(text=f"{len(self.merge_pdf_files)} PDFs ({total_p} total pages)")

        if not self.merge_pdf_files:
            self.merge_pdf_container.show_empty("No PDF documents added. Click 'Add PDF Files...' to begin.")
            return

        for idx, f in enumerate(self.merge_pdf_files):
            ModernFileCard(
                self.merge_pdf_container.scroll_frame,
                file_path=f,
                index=idx,
                total_count=len(self.merge_pdf_files),
                on_up=self.merge_pdf_move_up,
                on_down=self.merge_pdf_move_down,
                on_delete=self.merge_pdf_remove_item,
                on_preview=self.show_preview_dialog
            )

    def merge_pdf_move_up(self, idx: int):
        if idx > 0:
            self.merge_pdf_files[idx - 1], self.merge_pdf_files[idx] = self.merge_pdf_files[idx], self.merge_pdf_files[idx - 1]
            self.merge_pdf_refresh_list()

    def merge_pdf_move_down(self, idx: int):
        if idx < len(self.merge_pdf_files) - 1:
            self.merge_pdf_files[idx + 1], self.merge_pdf_files[idx] = self.merge_pdf_files[idx], self.merge_pdf_files[idx + 1]
            self.merge_pdf_refresh_list()

    def merge_pdf_reverse(self):
        self.merge_pdf_files.reverse()
        self.merge_pdf_refresh_list()

    def merge_pdf_remove_item(self, idx: int):
        if 0 <= idx < len(self.merge_pdf_files):
            del self.merge_pdf_files[idx]
            self.merge_pdf_refresh_list()

    def merge_pdf_clear(self):
        self.merge_pdf_files.clear()
        self.merge_pdf_refresh_list()

    def merge_pdf_browse_output(self):
        path = filedialog.asksaveasfilename(title="Save Merged PDF As", defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")])
        if path:
            self.merge_pdf_out_var.set(path)

    def merge_pdf_execute(self):
        if len(self.merge_pdf_files) < 2:
            messagebox.showwarning("At Least 2 PDFs Required", "Please select at least 2 PDF documents to merge.")
            return

        out_path = self.merge_pdf_out_var.get().strip()
        if not out_path:
            messagebox.showwarning("Missing Output", "Please choose an output destination.")
            return

        self.set_status("Merging PDFs into a unified document...", is_working=True)
        self.btn_run_merge_pdf.config(state="disabled")

        def worker():
            try:
                res_path, tot_pages, sz = cc.merge_pdfs(self.merge_pdf_files, out_path)
                self.last_output_dir = os.path.dirname(os.path.abspath(res_path))
                msg = f"Merged {len(self.merge_pdf_files)} PDFs into {tot_pages} pages ({cc.format_file_size(sz)})!"
                self.root.after(0, lambda: self.on_task_complete(msg, res_path, self.btn_run_merge_pdf))
            except Exception as e:
                self.root.after(0, lambda: self.on_task_error(str(e), self.btn_run_merge_pdf))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # TAB 3: PDF TO IMAGES
    # -------------------------------------------------------------------------
    def build_page_pdf2img(self, parent):
        h_frame = tk.Frame(parent, bg="#f8fafc")
        h_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(h_frame, text="PDF to Images", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="#f8fafc").pack(anchor="w")
        tk.Label(h_frame, text="Extract all or specific pages into crisp, high-resolution images", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc").pack(anchor="w")

        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=14)
        card.pack(fill=tk.BOTH, expand=True)

        # Select PDF Row
        row_sel = tk.Frame(card, bg="#ffffff")
        row_sel.pack(fill=tk.X, pady=(0, 10))

        tk.Label(row_sel, text="Select PDF Document:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        self.pdf2img_in_var = tk.StringVar(value="")
        entry_pdf = ttk.Entry(row_sel, textvariable=self.pdf2img_in_var, font=("Segoe UI", 9))
        entry_pdf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        icon_fold = IconManager.get("btn_folder", 16)
        btn_br_pdf = tk.Button(
            row_sel, text=" Select PDF...", image=icon_fold, compound="left", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=self.pdf2img_browse_input
        )
        btn_br_pdf.image = icon_fold
        btn_br_pdf.pack(side=tk.LEFT)

        # Interactive Info Card with Preview Button
        self.card_pdf_info = tk.Frame(card, bg="#f8fafc", highlightthickness=1, highlightbackground="#e2e8f0", padx=12, pady=10)
        self.card_pdf_info.pack(fill=tk.X, pady=(0, 12))

        self.lbl_pdf_info = tk.Label(self.card_pdf_info, text="No PDF selected. Click 'Select PDF...' above.", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc")
        self.lbl_pdf_info.pack(side=tk.LEFT)

        icon_eye = IconManager.get("eye", 16, "#2563eb")
        self.btn_preview_pdf = tk.Button(
            self.card_pdf_info, text=" Preview Pages", image=icon_eye, compound="left", font=("Segoe UI", 8, "bold"),
            bg="#eff6ff", activebackground="#dbeafe", fg="#2563eb", relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
            command=self.pdf2img_preview_current
        )
        self.btn_preview_pdf.image = icon_eye

        # Pill Selectors
        opts = tk.LabelFrame(card, text=" Extraction Quality & Format ", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff", padx=12, pady=8)
        opts.pack(fill=tk.X, pady=(0, 12))

        r1 = tk.Frame(opts, bg="#ffffff")
        r1.pack(fill=tk.X, pady=(0, 6))

        tk.Label(r1, text="Format:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.pdf2img_fmt_pill = PillSelector(r1, [("PNG (Lossless)", "png"), ("JPG (Clean)", "jpg"), ("WEBP", "webp")], "png")
        self.pdf2img_fmt_pill.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(r1, text="Pages to Extract:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.pdf2img_pages_var = tk.StringVar(value="all")
        ttk.Entry(r1, textvariable=self.pdf2img_pages_var, width=12).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(r1, text="('all' or '1-3, 5')", font=("Segoe UI", 8), fg="#94a3b8", bg="#ffffff").pack(side=tk.LEFT)

        r2 = tk.Frame(opts, bg="#ffffff")
        r2.pack(fill=tk.X)

        tk.Label(r2, text="Clarity DPI:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.pdf2img_dpi_pill = PillSelector(r2, [("Standard (150 DPI)", "150"), ("High Crisp (300 DPI)", "300"), ("Ultra Sharp (600 DPI)", "600")], "300")
        self.pdf2img_dpi_pill.pack(side=tk.LEFT)

        # Output Folder
        out_f = tk.Frame(card, bg="#ffffff")
        out_f.pack(fill=tk.X, pady=(0, 14))
        tk.Label(out_f, text="Save Images In:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

        self.pdf2img_outdir_var = tk.StringVar(value="")
        entry_od = ttk.Entry(out_f, textvariable=self.pdf2img_outdir_var, font=("Segoe UI", 9))
        entry_od.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_br_od = tk.Button(out_f, text=" Choose Folder...", image=icon_fold, compound="left", font=("Segoe UI", 9), bg="#f1f5f9", activebackground="#e2e8f0", relief="flat", bd=0, padx=8, pady=4, command=self.pdf2img_browse_outdir)
        btn_br_od.image = icon_fold
        btn_br_od.pack(side=tk.LEFT)

        # Action Button
        icon_play = IconManager.get("btn_play", 18, "#ffffff")
        self.btn_convert_pdf2img = tk.Button(
            card, text="  Extract Images from PDF", image=icon_play, compound="left", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
            command=self.pdf2img_execute
        )
        self.btn_convert_pdf2img.image = icon_play
        self.btn_convert_pdf2img.pack(fill=tk.X)

    def pdf2img_browse_input(self):
        f = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF Documents", "*.pdf")])
        if f:
            self.pdf2img_in_var.set(f)
            try:
                import pymupdf
                doc = pymupdf.open(f)
                num = len(doc)
                doc.close()
                sz = cc.format_file_size(os.path.getsize(f))
                self.lbl_pdf_info.config(text=f"Selected: {os.path.basename(f)}  |  {num} Pages  |  {sz}", fg="#0f172a")
                self.btn_preview_pdf.pack(side=tk.RIGHT)

                base_dir = os.path.dirname(f)
                base_name = os.path.splitext(os.path.basename(f))[0]
                self.pdf2img_outdir_var.set(os.path.join(base_dir, f"{base_name}_images"))
            except Exception as e:
                self.lbl_pdf_info.config(text=f"Error inspecting PDF: {e}", fg="#ef4444")

    def pdf2img_preview_current(self):
        f = self.pdf2img_in_var.get().strip()
        if f and os.path.exists(f):
            self.show_preview_dialog(f)

    def pdf2img_browse_outdir(self):
        d = filedialog.askdirectory(title="Select Folder to Save Images")
        if d:
            self.pdf2img_outdir_var.set(d)

    def pdf2img_execute(self):
        pdf_path = self.pdf2img_in_var.get().strip()
        out_dir = self.pdf2img_outdir_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Invalid PDF", "Please select a valid PDF file.")
            return
        if not out_dir:
            messagebox.showwarning("Missing Folder", "Please choose an output folder.")
            return

        pages_range = self.pdf2img_pages_var.get().strip()
        fmt = self.pdf2img_fmt_pill.get()
        dpi = int(self.pdf2img_dpi_pill.get())

        self.set_status("Extracting PDF pages into images...", is_working=True)
        self.btn_convert_pdf2img.config(state="disabled")

        def worker():
            try:
                out_files = cc.pdf_to_images(
                    pdf_path=pdf_path,
                    output_dir=out_dir,
                    output_format=fmt,
                    dpi=dpi,
                    page_range=pages_range
                )
                self.last_output_dir = os.path.abspath(out_dir)
                msg = f"Extracted {len(out_files)} images into '{os.path.basename(out_dir)}'!"
                self.root.after(0, lambda: self.on_task_complete(msg, out_dir, self.btn_convert_pdf2img))
            except Exception as e:
                self.root.after(0, lambda: self.on_task_error(str(e), self.btn_convert_pdf2img))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # TAB 4: SMART COMPRESSOR (With Before/After Visual Graphics)
    # -------------------------------------------------------------------------
    def build_page_compress(self, parent):
        h_frame = tk.Frame(parent, bg="#f8fafc")
        h_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(h_frame, text="Smart Compressor (Image & PDF)", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="#f8fafc").pack(anchor="w")
        tk.Label(h_frame, text="Hit your exact target size in KB / MB or tune quality with instant comparison", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc").pack(anchor="w")

        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=14)
        card.pack(fill=tk.BOTH, expand=True)

        # Select Row
        r_sel = tk.Frame(card, bg="#ffffff")
        r_sel.pack(fill=tk.X, pady=(0, 8))

        tk.Label(r_sel, text="Select File to Compress:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        self.comp_in_var = tk.StringVar(value="")
        ttk.Entry(r_sel, textvariable=self.comp_in_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        icon_fold = IconManager.get("btn_folder", 16)
        btn_br = tk.Button(r_sel, text=" Choose File...", image=icon_fold, compound="left", font=("Segoe UI", 9, "bold"), bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=10, pady=5, cursor="hand2", command=self.comp_browse_input)
        btn_br.image = icon_fold
        btn_br.pack(side=tk.LEFT)

        # Interactive Info Card with Preview Button
        self.card_comp_info = tk.Frame(card, bg="#f8fafc", highlightthickness=1, highlightbackground="#e2e8f0", padx=12, pady=10)
        self.card_comp_info.pack(fill=tk.X, pady=(0, 12))

        self.lbl_comp_info = tk.Label(self.card_comp_info, text="Supported: JPG, PNG, WEBP, PDF, etc.", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc")
        self.lbl_comp_info.pack(side=tk.LEFT)

        icon_eye = IconManager.get("eye", 16, "#2563eb")
        self.btn_preview_comp = tk.Button(
            self.card_comp_info, text=" Preview File", image=icon_eye, compound="left", font=("Segoe UI", 8, "bold"),
            bg="#eff6ff", activebackground="#dbeafe", fg="#2563eb", relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
            command=self.comp_preview_current
        )
        self.btn_preview_comp.image = icon_eye

        # Mode Box
        mode_box = tk.LabelFrame(card, text=" Compression Mode ", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff", padx=12, pady=10)
        mode_box.pack(fill=tk.X, pady=(0, 10))

        r_mode = tk.Frame(mode_box, bg="#ffffff")
        r_mode.pack(fill=tk.X, pady=(0, 8))

        self.comp_mode_pill = PillSelector(r_mode, [("Target Size (KB / MB)", "target"), ("Quality Slider (%)", "quality")], "target", on_change=self.on_comp_mode_toggle)
        self.comp_mode_pill.pack(side=tk.LEFT)

        # Mode Details Frame
        self.comp_details_frame = tk.Frame(mode_box, bg="#ffffff")
        self.comp_details_frame.pack(fill=tk.X)

        self.comp_target_val_var = tk.StringVar(value="250")
        self.comp_target_unit_var = tk.StringVar(value="KB")
        self.comp_quality_var = tk.IntVar(value=75)

        self.render_comp_mode_details()

        # Output Save Row
        out_f = tk.Frame(card, bg="#ffffff")
        out_f.pack(fill=tk.X, pady=(0, 10))
        tk.Label(out_f, text="Save Compressed File As:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

        self.comp_out_var = tk.StringVar(value="")
        ttk.Entry(out_f, textvariable=self.comp_out_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_br_c = tk.Button(out_f, text=" Browse...", image=icon_fold, compound="left", font=("Segoe UI", 9), bg="#f1f5f9", activebackground="#e2e8f0", relief="flat", bd=0, padx=8, pady=4, command=self.comp_browse_output)
        btn_br_c.image = icon_fold
        btn_br_c.pack(side=tk.LEFT)

        # Action Compress Button
        icon_play = IconManager.get("btn_play", 18, "#ffffff")
        self.btn_run_comp = tk.Button(
            card, text="  Compress File Now", image=icon_play, compound="left", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
            command=self.comp_execute
        )
        self.btn_run_comp.image = icon_play
        self.btn_run_comp.pack(fill=tk.X, pady=(0, 8))

        # Comparison Result Card
        self.res_card = tk.Frame(card, bg="#f8fafc", highlightthickness=1, highlightbackground="#e2e8f0", padx=12, pady=10)
        self.res_card.pack(fill=tk.X)

        self.lbl_comp_stats = tk.Label(self.res_card, text="Select a file and click 'Compress File Now' to see before & after stats.", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc")
        self.lbl_comp_stats.pack(anchor="w")

    def on_comp_mode_toggle(self, val: str):
        self.render_comp_mode_details()

    def render_comp_mode_details(self):
        for w in self.comp_details_frame.winfo_children():
            w.destroy()

        mode = self.comp_mode_pill.get()
        if mode == "target":
            tk.Label(self.comp_details_frame, text="Enter Exact Target Size:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
            ttk.Entry(self.comp_details_frame, textvariable=self.comp_target_val_var, width=8).pack(side=tk.LEFT, padx=(0, 6))
            cb = ttk.Combobox(self.comp_details_frame, textvariable=self.comp_target_unit_var, values=["KB", "MB"], state="readonly", width=5)
            cb.pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(self.comp_details_frame, text="(Smart optimizer calculates highest resolution for this exact size)", font=("Segoe UI", 8), fg="#64748b", bg="#ffffff").pack(side=tk.LEFT)
        else:
            tk.Label(self.comp_details_frame, text="Quality Level:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
            sc = ttk.Scale(self.comp_details_frame, from_=10, to=95, variable=self.comp_quality_var, orient=tk.HORIZONTAL, length=180,
                           command=lambda v: self.lbl_qual_val.config(text=f"{int(float(v))}%"))
            sc.pack(side=tk.LEFT, padx=(0, 8))
            self.lbl_qual_val = tk.Label(self.comp_details_frame, text=f"{self.comp_quality_var.get()}%", font=("Segoe UI", 9, "bold"), fg="#2563eb", bg="#ffffff", width=5)
            self.lbl_qual_val.pack(side=tk.LEFT)

    def comp_browse_input(self):
        f = filedialog.askopenfilename(title="Select File", filetypes=[("Supported", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.pdf"), ("All Files", "*.*")])
        if f:
            self.comp_in_var.set(f)
            sz = cc.format_file_size(os.path.getsize(f))
            ext = os.path.splitext(f)[1].upper().replace(".", "")
            self.lbl_comp_info.config(text=f"Selected: {os.path.basename(f)}  |  Format: {ext}  |  Original Size: {sz}", fg="#0f172a")
            self.btn_preview_comp.pack(side=tk.RIGHT)

            base, ext_orig = os.path.splitext(f)
            self.comp_out_var.set(f"{base}_compressed{ext_orig}")

    def comp_preview_current(self):
        f = self.comp_in_var.get().strip()
        if f and os.path.exists(f):
            self.show_preview_dialog(f)

    def comp_browse_output(self):
        cur = self.comp_out_var.get()
        ext = os.path.splitext(cur)[1] if cur else ".*"
        path = filedialog.asksaveasfilename(title="Save Compressed File As", initialfile=os.path.basename(cur) if cur else "compressed", filetypes=[("Same Type", f"*{ext}"), ("All Files", "*.*")])
        if path:
            self.comp_out_var.set(path)

    def comp_execute(self):
        in_path = self.comp_in_var.get().strip()
        out_path = self.comp_out_var.get().strip()
        if not in_path or not os.path.exists(in_path):
            messagebox.showwarning("Invalid File", "Please select a valid image or PDF to compress.")
            return
        if not out_path:
            messagebox.showwarning("Missing Output", "Please choose an output path.")
            return

        mode = self.comp_mode_pill.get()
        target_kb = None
        quality = int(self.comp_quality_var.get())

        if mode == "target":
            try:
                val = float(self.comp_target_val_var.get().strip())
                unit = self.comp_target_unit_var.get().upper()
                target_kb = val * 1024 if unit == "MB" else val
            except ValueError:
                messagebox.showerror("Invalid Target", "Please enter a valid numeric value for target size.")
                return

        ext = os.path.splitext(in_path)[1].lower()
        is_pdf = (ext == ".pdf")

        self.set_status("Optimizing and compressing file...", is_working=True)
        self.btn_run_comp.config(state="disabled")

        def worker():
            try:
                if is_pdf:
                    res_path, orig, comp = cc.compress_pdf(input_path=in_path, output_path=out_path, target_kb=target_kb, quality=quality, aggressive=(mode == "target"))
                else:
                    res_path, orig, comp = cc.compress_image(input_path=in_path, output_path=out_path, target_kb=target_kb, quality=quality)

                self.last_output_dir = os.path.dirname(os.path.abspath(res_path))
                saved_bytes = max(0, orig - comp)
                saved_pct = (saved_bytes / max(1, orig)) * 100
                orig_str = cc.format_file_size(orig)
                comp_str = cc.format_file_size(comp)

                stat_text = (
                    f"Successfully Compressed!\n"
                    f"- Original Size: {orig_str}  ->  Compressed: {comp_str}\n"
                    f"- Space Saved: {cc.format_file_size(saved_bytes)} ({saved_pct:.1f}% reduction)\n"
                    f"- Saved at: {res_path}"
                )
                self.root.after(0, lambda: self.on_compress_done(stat_text, res_path))
            except Exception as e:
                self.root.after(0, lambda: self.on_task_error(str(e), self.btn_run_comp))

        threading.Thread(target=worker, daemon=True).start()

    def on_compress_done(self, stats: str, out_path: str):
        self.lbl_comp_stats.config(text=stats, fg="#15803d")
        self.set_status("Compression complete!", is_working=False, state="success")
        self.btn_run_comp.config(state="normal")
        messagebox.showinfo("Success", stats)

    # -------------------------------------------------------------------------
    # TAB 5: FORMAT CONVERTER
    # -------------------------------------------------------------------------
    def build_page_format(self, parent):
        h_frame = tk.Frame(parent, bg="#f8fafc")
        h_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(h_frame, text="Image Format Converter", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="#f8fafc").pack(anchor="w")
        tk.Label(h_frame, text="Convert images between JPG, PNG, WEBP, BMP, TIFF, and ICO formats seamlessly", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc").pack(anchor="w")

        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=12)
        card.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        tb = tk.Frame(card, bg="#ffffff")
        tb.pack(fill=tk.X, pady=(0, 8))

        icon_add = IconManager.get("btn_add", 16, "#ffffff")
        btn_add = tk.Button(
            tb, text="  Select Image(s)...", image=icon_add, compound="left", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
            command=self.fmt_add_images
        )
        btn_add.image = icon_add
        btn_add.pack(side=tk.LEFT, padx=(0, 6))

        icon_clear = IconManager.get("btn_clear", 16, "#475569")
        btn_clear = tk.Button(
            tb, text="  Clear", image=icon_clear, compound="left", font=("Segoe UI", 9),
            bg="#f1f5f9", activebackground="#e2e8f0", fg="#475569", relief="flat", bd=0, padx=8, pady=6, cursor="hand2",
            command=self.fmt_clear
        )
        btn_clear.image = icon_clear
        btn_clear.pack(side=tk.LEFT)

        self.lbl_fmt_count = tk.Label(tb, text="0 images added", font=("Segoe UI", 9), fg="#64748b", bg="#ffffff")
        self.lbl_fmt_count.pack(side=tk.RIGHT)

        # Card container
        self.fmt_container = ScrollableCardContainer(card, height=180)
        self.fmt_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Target Options with Pill Selector
        opts = tk.Frame(card, bg="#ffffff")
        opts.pack(fill=tk.X, pady=(0, 10))

        tk.Label(opts, text="Convert To:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        self.fmt_target_pill = PillSelector(opts, [("WEBP", "webp"), ("PNG", "png"), ("JPG", "jpg"), ("BMP", "bmp"), ("TIFF", "tiff"), ("ICO", "ico")], "webp")
        self.fmt_target_pill.pack(side=tk.LEFT)

        # Output Folder
        out_f = tk.Frame(card, bg="#ffffff")
        out_f.pack(fill=tk.X, pady=(0, 10))
        tk.Label(out_f, text="Save Converted Files In:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

        self.fmt_outdir_var = tk.StringVar(value="")
        ttk.Entry(out_f, textvariable=self.fmt_outdir_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        icon_fold = IconManager.get("btn_folder", 16)
        btn_br = tk.Button(out_f, text=" Choose Folder...", image=icon_fold, compound="left", font=("Segoe UI", 9), bg="#f1f5f9", activebackground="#e2e8f0", relief="flat", bd=0, padx=8, pady=4, command=self.fmt_browse_outdir)
        btn_br.image = icon_fold
        btn_br.pack(side=tk.LEFT)

        # Action Convert Button
        icon_play = IconManager.get("btn_play", 18, "#ffffff")
        self.btn_run_fmt = tk.Button(
            card, text="  Convert Image Format(s)", image=icon_play, compound="left", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
            command=self.fmt_execute
        )
        self.btn_run_fmt.image = icon_play
        self.btn_run_fmt.pack(fill=tk.X)

        self.fmt_files: List[str] = []
        self.fmt_refresh_list()

    def fmt_add_images(self):
        files = filedialog.askopenfilenames(
            title="Select Images to Convert",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff;*.tif;*.gif;*.ico"), ("All Files", "*.*")]
        )
        if files:
            for f in files:
                if f not in self.fmt_files:
                    self.fmt_files.append(f)
            self.fmt_refresh_list()
            if not self.fmt_outdir_var.get() and self.fmt_files:
                self.fmt_outdir_var.set(os.path.dirname(self.fmt_files[0]))

    def fmt_refresh_list(self):
        self.fmt_container.clear()
        self.lbl_fmt_count.config(text=f"{len(self.fmt_files)} image(s) added")

        if not self.fmt_files:
            self.fmt_container.show_empty("No images added. Click 'Select Image(s)...' to begin.")
            return

        for idx, f in enumerate(self.fmt_files):
            ModernFileCard(
                self.fmt_container.scroll_frame,
                file_path=f,
                index=idx,
                total_count=len(self.fmt_files),
                on_delete=self.fmt_remove_item,
                on_preview=self.show_preview_dialog
            )

    def fmt_remove_item(self, idx: int):
        if 0 <= idx < len(self.fmt_files):
            del self.fmt_files[idx]
            self.fmt_refresh_list()

    def fmt_clear(self):
        self.fmt_files.clear()
        self.fmt_refresh_list()

    def fmt_browse_outdir(self):
        d = filedialog.askdirectory(title="Select Destination Folder")
        if d:
            self.fmt_outdir_var.set(d)

    def fmt_execute(self):
        if not self.fmt_files:
            messagebox.showwarning("No Images", "Please select at least one image.")
            return

        out_dir = self.fmt_outdir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Missing Folder", "Please choose an output folder.")
            return

        target_fmt = self.fmt_target_pill.get().lower()

        self.set_status("Converting image formats...", is_working=True)
        self.btn_run_fmt.config(state="disabled")

        def worker():
            try:
                converted = []
                for f in self.fmt_files:
                    base = os.path.splitext(os.path.basename(f))[0]
                    out_path = os.path.join(out_dir, f"{base}.{target_fmt}")
                    res = cc.convert_image_format(f, out_path, target_format=target_fmt, quality=95)
                    converted.append(res)

                self.last_output_dir = os.path.abspath(out_dir)
                msg = f"Converted {len(converted)} image(s) to {target_fmt.upper()} successfully!"
                self.root.after(0, lambda: self.on_task_complete(msg, out_dir, self.btn_run_fmt))
            except Exception as e:
                self.root.after(0, lambda: self.on_task_error(str(e), self.btn_run_fmt))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # TAB 6: STITCH / MERGE 2 TO 5 IMAGES (With Live Alignment Graphic Canvas)
    # -------------------------------------------------------------------------
    def build_page_merge(self, parent):
        h_frame = tk.Frame(parent, bg="#f8fafc")
        h_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(h_frame, text="Stitch / Merge 2 to 5 Images", font=("Segoe UI", 16, "bold"), fg="#0f172a", bg="#f8fafc").pack(anchor="w")
        tk.Label(h_frame, text="Reorder sequence, preview alignment, and merge with Lanczos clarity preservation", font=("Segoe UI", 9), fg="#64748b", bg="#f8fafc").pack(anchor="w")

        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0", padx=16, pady=12)
        card.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        tb = tk.Frame(card, bg="#ffffff")
        tb.pack(fill=tk.X, pady=(0, 8))

        icon_add = IconManager.get("btn_add", 16, "#ffffff")
        btn_add = tk.Button(
            tb, text="  Select 2 to 5 Images...", image=icon_add, compound="left", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
            command=self.merge_add_images
        )
        btn_add.image = icon_add
        btn_add.pack(side=tk.LEFT, padx=(0, 6))

        btn_rev = tk.Button(
            tb, text="Reverse Order", font=("Segoe UI", 8, "bold"), bg="#f1f5f9", activebackground="#e2e8f0",
            fg="#334155", relief="flat", bd=0, padx=8, pady=6, cursor="hand2", command=self.merge_reverse
        )
        btn_rev.pack(side=tk.LEFT, padx=(0, 6))

        icon_clear = IconManager.get("btn_clear", 16, "#475569")
        btn_clear = tk.Button(
            tb, text="  Clear", image=icon_clear, compound="left", font=("Segoe UI", 9),
            bg="#f1f5f9", activebackground="#e2e8f0", fg="#475569", relief="flat", bd=0, padx=8, pady=6, cursor="hand2",
            command=self.merge_clear
        )
        btn_clear.image = icon_clear
        btn_clear.pack(side=tk.LEFT)

        self.lbl_merge_count = tk.Label(tb, text="0 / 5 images added", font=("Segoe UI", 9, "bold"), fg="#64748b", bg="#ffffff")
        self.lbl_merge_count.pack(side=tk.RIGHT)

        # Card Container
        self.merge_container = ScrollableCardContainer(card, height=140)
        self.merge_container.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Stitch Options with Pill Selectors
        sbox = tk.LabelFrame(card, text=" Stitching Layout & Gap ", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff", padx=10, pady=6)
        sbox.pack(fill=tk.X, pady=(0, 8))

        r1 = tk.Frame(sbox, bg="#ffffff")
        r1.pack(fill=tk.X, pady=(0, 4))

        tk.Label(r1, text="Direction:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.merge_dir_pill = PillSelector(r1, [("Horizontal (Side-by-Side)", "horizontal"), ("Vertical (Stacked)", "vertical")], "horizontal", on_change=lambda v: self.render_live_stitch_preview())
        self.merge_dir_pill.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(r1, text="Format:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.merge_fmt_pill = PillSelector(r1, [("PNG (Crisp)", "png"), ("JPG", "jpg"), ("WEBP", "webp")], "png")
        self.merge_fmt_pill.pack(side=tk.LEFT)

        r2 = tk.Frame(sbox, bg="#ffffff")
        r2.pack(fill=tk.X)

        tk.Label(r2, text="Gap Spacing:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.merge_gap_pill = PillSelector(r2, [("0 px", "0"), ("10 px", "10"), ("20 px", "20"), ("30 px", "30")], "10", on_change=lambda v: self.render_live_stitch_preview())
        self.merge_gap_pill.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(r2, text="Background:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.merge_bg_pill = PillSelector(r2, [("White", "white"), ("Transparent", "transparent"), ("Black", "black")], "white", on_change=lambda v: self.render_live_stitch_preview())
        self.merge_bg_pill.pack(side=tk.LEFT)

        # Live Layout Canvas Graphic
        self.stitch_preview_canvas = tk.Canvas(card, bg="#f8fafc", height=70, highlightthickness=1, highlightbackground="#e2e8f0")
        self.stitch_preview_canvas.pack(fill=tk.X, pady=(0, 8))

        # Output Save Row
        out_f = tk.Frame(card, bg="#ffffff")
        out_f.pack(fill=tk.X, pady=(0, 8))
        tk.Label(out_f, text="Save Merged Image As:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))

        self.merge_out_var = tk.StringVar(value="")
        ttk.Entry(out_f, textvariable=self.merge_out_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        icon_fold = IconManager.get("btn_folder", 16)
        btn_br = tk.Button(out_f, text=" Browse...", image=icon_fold, compound="left", font=("Segoe UI", 9), bg="#f1f5f9", activebackground="#e2e8f0", relief="flat", bd=0, padx=8, pady=4, command=self.merge_browse_out)
        btn_br.image = icon_fold
        btn_br.pack(side=tk.LEFT)

        # Action Stitch Button
        icon_play = IconManager.get("btn_play", 18, "#ffffff")
        self.btn_run_merge = tk.Button(
            card, text="  Stitch / Merge Images with Maximum Clarity", image=icon_play, compound="left", font=("Segoe UI", 10, "bold"),
            bg="#2563eb", activebackground="#1d4ed8", fg="#ffffff", relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
            command=self.merge_execute
        )
        self.btn_run_merge.image = icon_play
        self.btn_run_merge.pack(fill=tk.X)

        self.merge_files: List[str] = []
        self.merge_refresh_list()

    def merge_add_images(self):
        files = filedialog.askopenfilenames(
            title="Select 2 to 5 Images to Stitch",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff;*.tif"), ("All Files", "*.*")]
        )
        if files:
            for f in files:
                if len(self.merge_files) >= 5:
                    messagebox.showinfo("Limit", "A maximum of 5 images can be stitched at once.")
                    break
                if f not in self.merge_files:
                    self.merge_files.append(f)

            self.merge_refresh_list()
            if not self.merge_out_var.get() and self.merge_files:
                base_dir = os.path.dirname(self.merge_files[0])
                self.merge_out_var.set(os.path.join(base_dir, "stitched_image.png"))

    def merge_refresh_list(self):
        self.merge_container.clear()
        self.lbl_merge_count.config(text=f"{len(self.merge_files)} / 5 images in sequence")

        if not self.merge_files:
            self.merge_container.show_empty("Select between 2 and 5 images to stitch.")
            self.stitch_preview_canvas.delete("all")
            self.stitch_preview_canvas.create_text(200, 35, text="Live alignment graphic will display here when 2+ images are selected.", fill="#94a3b8", font=("Segoe UI", 9))
            return

        for idx, f in enumerate(self.merge_files):
            ModernFileCard(
                self.merge_container.scroll_frame,
                file_path=f,
                index=idx,
                total_count=len(self.merge_files),
                on_up=self.merge_move_up,
                on_down=self.merge_move_down,
                on_delete=self.merge_remove_item,
                on_preview=self.show_preview_dialog
            )

        self.render_live_stitch_preview()

    def render_live_stitch_preview(self):
        self.stitch_preview_canvas.delete("all")
        if len(self.merge_files) < 2:
            self.stitch_preview_canvas.create_text(240, 35, text="Add at least 2 images to see the live layout preview.", fill="#94a3b8", font=("Segoe UI", 9))
            return

        direction = self.merge_dir_pill.get()
        cw = max(200, self.stitch_preview_canvas.winfo_width())
        ch = max(40, self.stitch_preview_canvas.winfo_height())
        if cw < 300:
            cw = 500

        n = len(self.merge_files)
        # Draw mock miniature layout
        if direction == "horizontal":
            block_w = min(80, (cw - 60) // n)
            block_h = 44
            start_x = (cw - (block_w * n + 10 * (n - 1))) // 2
            y = (ch - block_h) // 2

            for i in range(n):
                x = start_x + i * (block_w + 10)
                self.stitch_preview_canvas.create_rectangle(x, y, x + block_w, y + block_h, fill="#eff6ff", outline="#3b82f6", width=2)
                self.stitch_preview_canvas.create_text(x + block_w // 2, y + block_h // 2, text=f"Img {i + 1}", fill="#1d4ed8", font=("Segoe UI", 8, "bold"))
                if i < n - 1:
                    self.stitch_preview_canvas.create_text(x + block_w + 5, y + block_h // 2, text="+", fill="#94a3b8", font=("Segoe UI", 10, "bold"))
        else:
            block_w = 120
            block_h = max(14, (ch - 10) // n)
            start_y = (ch - (block_h * n + 4 * (n - 1))) // 2
            x = (cw - block_w) // 2

            for i in range(n):
                y = start_y + i * (block_h + 4)
                self.stitch_preview_canvas.create_rectangle(x, y, x + block_w, y + block_h, fill="#eff6ff", outline="#3b82f6", width=2)
                self.stitch_preview_canvas.create_text(x + block_w // 2, y + block_h // 2, text=f"Image {i + 1}", fill="#1d4ed8", font=("Segoe UI", 7, "bold"))

    def merge_move_up(self, idx: int):
        if idx > 0:
            self.merge_files[idx - 1], self.merge_files[idx] = self.merge_files[idx], self.merge_files[idx - 1]
            self.merge_refresh_list()

    def merge_move_down(self, idx: int):
        if idx < len(self.merge_files) - 1:
            self.merge_files[idx + 1], self.merge_files[idx] = self.merge_files[idx], self.merge_files[idx + 1]
            self.merge_refresh_list()

    def merge_reverse(self):
        self.merge_files.reverse()
        self.merge_refresh_list()

    def merge_remove_item(self, idx: int):
        if 0 <= idx < len(self.merge_files):
            del self.merge_files[idx]
            self.merge_refresh_list()

    def merge_clear(self):
        self.merge_files.clear()
        self.merge_refresh_list()

    def merge_browse_out(self):
        path = filedialog.asksaveasfilename(title="Save Merged Image As", defaultextension=".png", filetypes=[("PNG (Lossless)", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp")])
        if path:
            self.merge_out_var.set(path)

    def merge_execute(self):
        if len(self.merge_files) < 2:
            messagebox.showwarning("At Least 2 Required", "Please select between 2 and 5 images to merge.")
            return

        out_path = self.merge_out_var.get().strip()
        if not out_path:
            messagebox.showwarning("Missing Output", "Please choose an output path.")
            return

        direction = self.merge_dir_pill.get()
        gap = int(self.merge_gap_pill.get())
        bg = self.merge_bg_pill.get()
        fmt = self.merge_fmt_pill.get()

        self.set_status("Stitching images with pure Lanczos clarity...", is_working=True)
        self.btn_run_merge.config(state="disabled")

        def worker():
            try:
                res_path, (w, h) = cc.merge_images(
                    image_paths=self.merge_files,
                    output_path=out_path,
                    direction=direction,
                    gap=gap,
                    bg_color=bg,
                    output_format=fmt,
                    quality=95
                )
                self.last_output_dir = os.path.dirname(os.path.abspath(res_path))
                size_str = cc.format_file_size(os.path.getsize(res_path))
                msg = f"Merged {len(self.merge_files)} images into {w}x{h} px ({size_str})!"
                self.root.after(0, lambda: self.on_task_complete(msg, res_path, self.btn_run_merge))
            except Exception as e:
                self.root.after(0, lambda: self.on_task_error(str(e), self.btn_run_merge))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    # TASK COMPLETION HANDLERS
    # =========================================================================
    def on_task_complete(self, message: str, output_path: str, button_to_enable=None):
        self.set_status(f"Completed: {message}", is_working=False, state="success")
        if button_to_enable:
            button_to_enable.config(state="normal")
        # Offer immediate preview!
        resp = messagebox.askyesno(
            "Success - View Output",
            f"{message}\n\nSaved at:\n{output_path}\n\nWould you like to open a full HD preview of the output now?"
        )
        if resp:
            self.show_preview_dialog(output_path)

    def on_task_error(self, err_msg: str, button_to_enable=None):
        self.set_status(f"Error: {err_msg}", is_working=False, state="error")
        if button_to_enable:
            button_to_enable.config(state="normal")
        messagebox.showerror("Operation Failed", f"An error occurred:\n{err_msg}")


def main():
    root = tk.Tk()
    app = ModernStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
