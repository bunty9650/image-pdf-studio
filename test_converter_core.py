"""
Test script for converter_core functions
"""

import os
import shutil
import unittest
from PIL import Image, ImageDraw
import converter_core as cc


class TestConverterCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath("test_temp_dir")
        os.makedirs(cls.test_dir, exist_ok=True)

        # Create sample images
        cls.img1_path = os.path.join(cls.test_dir, "sample1.jpg")
        img1 = Image.new("RGB", (600, 400), color=(220, 50, 50))
        d1 = ImageDraw.Draw(img1)
        d1.text((50, 50), "Sample 1 Red", fill=(255, 255, 255))
        img1.save(cls.img1_path, "JPEG")

        cls.img2_path = os.path.join(cls.test_dir, "sample2.png")
        img2 = Image.new("RGBA", (400, 700), color=(50, 180, 50, 200))
        d2 = ImageDraw.Draw(img2)
        d2.text((50, 50), "Sample 2 Green Alpha", fill=(0, 0, 0))
        img2.save(cls.img2_path, "PNG")

        cls.img3_path = os.path.join(cls.test_dir, "sample3.webp")
        img3 = Image.new("RGB", (500, 500), color=(50, 100, 220))
        d3 = ImageDraw.Draw(img3)
        d3.text((50, 50), "Sample 3 Blue", fill=(255, 255, 255))
        img3.save(cls.img3_path, "WEBP")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_images_to_pdf_single_and_multi(self):
        out_pdf = os.path.join(self.test_dir, "multi_images.pdf")
        res = cc.images_to_pdf(
            [self.img1_path, self.img2_path, self.img3_path],
            out_pdf,
            page_size="A4",
            orientation="auto",
            margin=10
        )
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_02_pdf_to_images(self):
        pdf_path = os.path.join(self.test_dir, "multi_images.pdf")
        out_dir = os.path.join(self.test_dir, "pdf_extracted")
        img_paths = cc.pdf_to_images(pdf_path, out_dir, output_format="png", dpi=150)
        self.assertEqual(len(img_paths), 3)
        for p in img_paths:
            self.assertTrue(os.path.exists(p))

    def test_03_compress_image_quality(self):
        out_img = os.path.join(self.test_dir, "comp_qual.jpg")
        path, orig, comp = cc.compress_image(self.img1_path, out_img, quality=30)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(comp, 0)

    def test_04_compress_image_target_kb(self):
        out_img = os.path.join(self.test_dir, "comp_target.jpg")
        target_kb = 15.0
        path, orig, comp = cc.compress_image(self.img1_path, out_img, target_kb=target_kb)
        self.assertTrue(os.path.exists(path))
        self.assertLessEqual(comp, target_kb * 1024 * 1.1)  # within margin

    def test_05_compress_pdf(self):
        pdf_path = os.path.join(self.test_dir, "multi_images.pdf")
        out_pdf = os.path.join(self.test_dir, "comp_pdf.pdf")
        path, orig, comp = cc.compress_pdf(pdf_path, out_pdf, quality=50, aggressive=True)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(comp, 0)

    def test_06_format_conversion(self):
        # Convert PNG with transparency to JPG (should handle alpha cleanly)
        out_jpg = os.path.join(self.test_dir, "converted_sample2.jpg")
        res1 = cc.convert_image_format(self.img2_path, out_jpg, "jpg")
        self.assertTrue(os.path.exists(res1))

        # Convert JPG to WEBP
        out_webp = os.path.join(self.test_dir, "converted_sample1.webp")
        res2 = cc.convert_image_format(self.img1_path, out_webp, "webp")
        self.assertTrue(os.path.exists(res2))

    def test_07_merge_horizontal(self):
        out_merged = os.path.join(self.test_dir, "merged_h.png")
        path, (w, h) = cc.merge_images(
            [self.img1_path, self.img2_path, self.img3_path],
            out_merged,
            direction="horizontal",
            gap=15,
            bg_color="white",
            output_format="png"
        )
        self.assertTrue(os.path.exists(path))
        self.assertEqual(h, 700)  # max height among 400, 700, 500
        self.assertGreater(w, 1000)

    def test_08_merge_vertical(self):
        out_merged = os.path.join(self.test_dir, "merged_v.png")
        path, (w, h) = cc.merge_images(
            [self.img1_path, self.img2_path, self.img3_path],
            out_merged,
            direction="vertical",
            gap=20,
            bg_color="black",
            output_format="png"
        )
        self.assertTrue(os.path.exists(path))
        self.assertEqual(w, 600)  # max width among 600, 400, 500
        self.assertGreater(h, 1500)

    def test_09_merge_pdfs_and_page_preview(self):
        pdf1 = os.path.join(self.test_dir, "test1.pdf")
        pdf2 = os.path.join(self.test_dir, "test2.pdf")
        cc.images_to_pdf([self.img1_path], pdf1)
        cc.images_to_pdf([self.img2_path, self.img3_path], pdf2)

        out_merged_pdf = os.path.join(self.test_dir, "combined.pdf")
        path, tot_pages, sz = cc.merge_pdfs([pdf1, pdf2], out_merged_pdf)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(tot_pages, 3)

        # Test page image preview
        page0 = cc.get_pdf_page_image(out_merged_pdf, 0)
        self.assertIsNotNone(page0)
        self.assertGreater(page0.width, 100)

    def test_10_target_size_matching_increase(self):
        # Test increasing image file size to exact target
        out_boosted_img = os.path.join(self.test_dir, "boosted.jpg")
        target_kb = 250.0  # 250 KB target
        path, orig, final = cc.compress_image(self.img1_path, out_boosted_img, target_kb=target_kb)
        self.assertTrue(os.path.exists(path))
        diff_kb = (target_kb * 1024 - final) / 1024
        # Must be strictly between 1.0 and 5.0 KB below target
        self.assertGreaterEqual(diff_kb, 1.0)
        self.assertLessEqual(diff_kb, 5.0)

        # Test increasing PDF file size to exact target
        dummy_pdf = os.path.join(self.test_dir, "small_doc.pdf")
        cc.images_to_pdf([self.img1_path], dummy_pdf)
        out_boosted_pdf = os.path.join(self.test_dir, "boosted_doc.pdf")
        target_pdf_kb = 400.0  # 400 KB target
        pdf_path, orig_p, final_p = cc.compress_pdf(dummy_pdf, out_boosted_pdf, target_kb=target_pdf_kb)
        self.assertTrue(os.path.exists(pdf_path))
        diff_pdf_kb = (target_pdf_kb * 1024 - final_p) / 1024
        self.assertGreaterEqual(diff_pdf_kb, 1.0)
        self.assertLessEqual(diff_pdf_kb, 5.0)

    def test_11_organize_and_security(self):
        # 1. Create a 3-page PDF
        multi_pdf = os.path.join(self.test_dir, "three_pages.pdf")
        cc.images_to_pdf([self.img1_path, self.img2_path, self.img3_path], multi_pdf)

        # 2. Test Split PDF
        split_dir = os.path.join(self.test_dir, "split_out")
        split_files = cc.split_pdf(multi_pdf, split_dir)
        self.assertEqual(len(split_files), 3)

        # 3. Test Remove Pages (remove page 2)
        cleaned_pdf = os.path.join(self.test_dir, "cleaned.pdf")
        cc.remove_pdf_pages(multi_pdf, cleaned_pdf, [2])
        info = cc.get_pdf_info(cleaned_pdf)
        self.assertEqual(info["page_count"], 2)

        # 4. Test Extract Pages (extract page 1 & 3)
        extracted_pdf = os.path.join(self.test_dir, "extracted.pdf")
        cc.extract_pdf_pages(multi_pdf, extracted_pdf, [1, 3])
        info_ext = cc.get_pdf_info(extracted_pdf)
        self.assertEqual(info_ext["page_count"], 2)

        # 5. Test Rotate Pages (rotate page 1 by 90)
        rotated_pdf = os.path.join(self.test_dir, "rotated.pdf")
        cc.rotate_pdf_pages(multi_pdf, rotated_pdf, {1: 90})
        self.assertTrue(os.path.exists(rotated_pdf))

        # 6. Test Protect & Unlock PDF
        locked_pdf = os.path.join(self.test_dir, "locked.pdf")
        cc.protect_pdf(multi_pdf, locked_pdf, "secret123")
        self.assertTrue(os.path.exists(locked_pdf))

        unlocked_pdf = os.path.join(self.test_dir, "unlocked.pdf")
        cc.unlock_pdf(locked_pdf, unlocked_pdf, "secret123")
        info_unlocked = cc.get_pdf_info(unlocked_pdf)
        self.assertEqual(info_unlocked["page_count"], 3)


if __name__ == "__main__":
    unittest.main()
