# Copyright (C) 2018 Florent de Labarre (<https://github.com/fmdl>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import io
import zlib

from PIL import Image

from .common import PrinterZpl2Common


class TestWizardImportZpl2(PrinterZpl2Common):
    def test_open_wizard(self):
        """open wizard from label"""
        res = self.label.import_zpl2()
        self.assertEqual(res.get("context").get("default_label_id"), self.label.id)

    def test_wizard_import_zpl2(self):
        """Import ZPL2 from wizard"""
        zpl_data = (
            "^XA\n"
            "^CI28\n"
            "^LH0,0\n"
            "^CF0\n"
            "^CFA,10\n"
            "^CFB,10,10\n"
            "^FO10,10^A0N,30,30^FDTEXT^FS\n"
            "^BY2,3.0^FO600,60^BCN,30,N,N,N"
            "^FDAJFGJAGJVJVHK^FS\n"
            "^FO10,40^A0N,20,40^FB150,2,1,J,0^FDTEXT BLOCK^FS\n"
            "^FO300,10^GC100,3,B^FS\n"
            "^FO10,200^GB200,200,100,B,0^FS\n"
            "^FO10,60^GFA,16.0,16.0,2.0,"
            "b'FFC0FFC0FFC0FFC0FFC0FFC0FFC0FFC0'^FS\n"
            "^FO10,200^GB300,100,6,W,0^FS\n"
            "^BY2,3.0^FO300,10^B1N,N,30,N,N^FD678987656789^FS\n"
            "^BY2,3.0^FO300,70^B2N,30,Y,Y,N^FD567890987768^FS\n"
            "^BY2,3.0^FO300,120^B3N,N,30,N,N^FD98765456787656^FS\n"
            "^BY2,3.0^FO300,200^BQN,2,5,Q,7"
            "^FDMM,A876567897656787658654645678^FS\n"
            "^BY2,3.0^FO400,250^BER,40,Y,Y^FD9876789987654567^FS\n"
            "^BY2,3.0^FO350,250^B7N,20,0,0,0,N^FD8765678987656789^FS\n"
            "^BY2,3.0^FO700,10^B9N,20,N,N,N^FD87657890987654^FS\n"
            "^BY2,3.0^FO600,200^B4N,50,N^FD7654567898765678^FS\n"
            "^BY2,3.0^FO600,300^BEN,50,Y,Y^FD987654567890876567^FS\n"
            "^FO300,300^AGI,50,50^FR^FDINVERTED^FS\n"
            "^BY2,3.0^FO700,200^B8,50,N,N^FD987609876567^FS\n"
            "^JUR\n"
            "^XZ"
        )

        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        self.assertEqual(18, len(self.label.component_ids))

    def test_wizard_import_zpl2_add(self):
        """Import ZPL2 from wizard ADD"""
        self.env["printing.label.zpl2.component"].create(
            {
                "name": "ZPL II Label",
                "label_id": self.label.id,
                "data": '"data"',
                "sequence": 10,
            }
        )
        zpl_data = "^XA\n^CI28\n^LH0,0\n^FO10,10^A0N,30,30^FDTEXT^FS\n^JUR\n^XZ"

        vals = {"label_id": self.label.id, "delete_component": False, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        self.assertEqual(2, len(self.label.component_ids))

    def test_wizard_import_zpl2_downloaded_graphic(self):
        """Import a label with a downloaded graphic (~DG) recalled by ^XG

        Label designers generate one command per line and store the images
        as compressed graphics, recalled by name in the label.
        """
        # 16x2 bitmap: a black line above a white one
        bitmap = b"\xff\xff\x00\x00"
        z64 = base64.b64encode(zlib.compress(bitmap)).decode()
        zpl_data = (
            "^XA\n"
            f"~DGR:SSGFX000.GRF,4,2,:Z64:{z64}:0000\n"
            "^XZ\n"
            "^XA\n"
            "^FO538,535\n"
            "^BY4\n"
            "^BEN,94,Y,N\n"
            "^FD761050886653\n"
            "^FS\n"
            "^FO12,77\n"
            "^XGR:SSGFX000.GRF,2,3\n"
            "^FS\n"
            "^FO10,10\n"
            "^XGR:MISSING.GRF,1,1\n"
            "^FS\n"
            "^PQ1,0,1,Y\n"
            "^XZ\n"
            "^XA\n"
            "^IDR:SSGFX000.GRF\n"
            "^XZ\n"
        )
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        # The missing graphic is skipped with a warning
        logger = "odoo.addons.printer_zpl2.wizard.wizard_import_zpl2"
        with self.assertLogs(logger, "WARNING") as logs:
            wizard.import_zpl2()
        self.assertEqual(len(logs.output), 1)
        self.assertIn("Recalled graphic not found", logs.output[0])
        barcode, graphic = self.label.component_ids.sorted("sequence")
        self.assertEqual(barcode.component_type, "ean-13")
        self.assertEqual((barcode.origin_x, barcode.origin_y), (538, 535))
        self.assertEqual(barcode.data, '"761050886653"')
        self.assertEqual(barcode.module_width, 4)
        self.assertEqual(barcode.height, 94)
        self.assertEqual(graphic.component_type, "graphic")
        self.assertEqual((graphic.origin_x, graphic.origin_y), (12, 77))
        # Magnified by ^XG
        self.assertEqual((graphic.width, graphic.height), (32, 6))
        image = Image.open(io.BytesIO(base64.b64decode(graphic.graphic_image)))
        self.assertEqual(image.size, (16, 2))
        self.assertEqual(image.getpixel((0, 0)), 0)
        self.assertEqual(image.getpixel((0, 1)), 255)

    def test_wizard_import_zpl2_graphic_field(self):
        """Import inline graphic fields (^GFA), hexadecimal or compressed"""
        # 16x3 bitmap: 10 black pixels then 6 white ones on each row
        bitmap = b"\xff\xc0" * 3
        z64 = base64.b64encode(zlib.compress(bitmap)).decode()
        zpl_data = (
            "^XA\n"
            "^FO10,60^GFA,6,6,2,FFC0FFC0FFC0^FS\n"
            f"^FO20,70^GFA,6,6,2,:Z64:{z64}:0000^FS\n"
            "^XZ"
        )
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        hexadecimal, compressed = self.label.component_ids.sorted("sequence")
        self.assertEqual((hexadecimal.origin_x, hexadecimal.origin_y), (10, 60))
        self.assertEqual((compressed.origin_x, compressed.origin_y), (20, 70))
        for component in (hexadecimal, compressed):
            self.assertEqual(component.component_type, "graphic")
            self.assertEqual((component.width, component.height), (16, 3))
            image = Image.open(io.BytesIO(base64.b64decode(component.graphic_image)))
            self.assertEqual(image.size, (16, 3))
            self.assertEqual(image.getpixel((9, 2)), 0)
            self.assertEqual(image.getpixel((10, 2)), 255)

    def test_wizard_import_zpl2_field_separator(self):
        """A field ends at ^FS, at its SI control code, or at the next field
        origin when the separator is missing"""
        zpl_data = (
            "^XA\n"
            "^FO10,10^A0N,30,30^FDFIRST^FS^FO10,50^A0N,30,30^FDSECOND\x0f\n"
            "^FO10,90^A0N,30,30^FDTHIRD\n"
            "^FO10,130^A0N,30,30^FDFOURTH\n"
            "^XZ"
        )
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        components = self.label.component_ids.sorted("sequence")
        self.assertEqual(
            components.mapped("data"), ['"FIRST"', '"SECOND"', '"THIRD"', '"FOURTH"']
        )
        self.assertEqual(components.mapped("origin_y"), [10, 50, 90, 130])
        self.assertEqual(set(components.mapped("component_type")), {"text"})

    def test_wizard_import_zpl2_diagonal_line(self):
        """Import diagonal lines (^GD)"""
        zpl_data = "^XA\n^FO10,20^GD100,50,3,B,R^FS\n^FO30,40^GD60,60,2^FS\n^XZ"
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        right, left = self.label.component_ids.sorted("sequence")
        self.assertEqual(set((right + left).mapped("component_type")), {"diagonal"})
        self.assertEqual((right.origin_x, right.origin_y), (10, 20))
        self.assertEqual((right.width, right.height, right.thickness), (100, 50, 3))
        self.assertEqual(right.color, "B")
        self.assertEqual(right.diagonal_orientation, "R")
        self.assertEqual((left.width, left.height, left.thickness), (60, 60, 2))
        # Defaults of the omitted arguments
        self.assertEqual(left.color, "B")
        self.assertEqual(left.diagonal_orientation, "L")

    def test_wizard_import_zpl2_defaults(self):
        """The default font (^CF) and barcode (^BY) values apply to the
        fields that do not set them, and do not override the ones that do"""
        zpl_data = (
            "^XA\n"
            "^CF0,20,25\n"
            "^BY2,3.0,50\n"
            "^FO10,10^A0N,30,40^FDEXPLICIT^FS\n"
            "^FO10,50^FDDEFAULT^FS\n"
            "^FO10,100^BCN,30,N,N,N^FDEXPLICIT^FS\n"
            "^FO10,150^BCN^FDDEFAULT^FS\n"
            "^FO10,200^BCN,,N,N,N^FDOMITTED^FS\n"
            "^XZ"
        )
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        text, default_text, barcode, default_barcode, omitted = (
            self.label.component_ids.sorted("sequence")
        )
        self.assertEqual((text.height, text.width), (30, 40))
        self.assertEqual((default_text.height, default_text.width), (20, 25))
        self.assertEqual((barcode.height, barcode.module_width), (30, 2))
        self.assertEqual(
            (default_barcode.height, default_barcode.module_width), (50, 2)
        )
        # An omitted (empty) argument falls back to the default too
        self.assertEqual((omitted.height, omitted.module_width), (50, 2))

    def test_wizard_import_zpl2_field_typeset(self):
        """Fields positioned with ^FT keep their coordinates, and are marked
        as positioned by their bottom left corner"""
        zpl_data = (
            "^XA\n"
            "^FT10,50^A0N,30,30^FDTEXT^FS\n"
            "^FT20,100,1^BCN,40,N,N,N^FDBARCODE^FS\n"
            "^FO30,150^A0N,30,30^FDORIGIN^FS\n"
            "^XZ"
        )
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        components = self.label.component_ids.sorted("sequence")
        self.assertEqual(components.mapped("origin_x"), [10, 20, 30])
        self.assertEqual(components.mapped("origin_y"), [50, 100, 150])
        self.assertEqual(
            components.mapped("position_type"), ["typeset", "typeset", "origin"]
        )

    def test_wizard_import_zpl2_default_orientation(self):
        """The default orientation (^FW) applies to the fields that omit it"""
        zpl_data = (
            "^XA\n"
            "^CF0,20\n"
            "^FWR\n"
            "^FO10,10^A0,30,30^FDDEFAULT^FS\n"
            "^FO10,50^FDDEFAULT FONT^FS\n"
            "^FO10,100^A0N,30,30^FDEXPLICIT^FS\n"
            "^FO10,200^BC,40,N,N,N^FDBARCODE^FS\n"
            "^FO10,300^GB100,50,2^FS\n"
            "^FWN\n"
            "^FO10,400^A0,30,30^FDNORMAL^FS\n"
            "^XZ"
        )
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        components = self.label.component_ids.sorted("sequence")
        self.assertEqual(
            components.mapped("orientation"), ["R", "R", "N", "R", "N", "N"]
        )
        # The font defaults are kept alongside the orientation default
        self.assertEqual(components[1].height, 20)
        self.assertEqual(components[3].height, 40)

    def test_wizard_import_zpl2_label_settings(self):
        """The label home (^LH) and print width (^PW) are set on the label"""
        self.label.write({"origin_x": 10, "origin_y": 10, "width": 480})
        zpl_data = "^XA\n^PW949\n^LH20,30\n^FO10,10^A0N,30,30^FDTEXT^FS\n^XZ"
        vals = {"label_id": self.label.id, "delete_component": True, "data": zpl_data}
        wizard = self.env["wizard.import.zpl2"].create(vals)
        wizard.import_zpl2()
        self.assertEqual((self.label.origin_x, self.label.origin_y), (20, 30))
        self.assertEqual(self.label.width, 949)
        # Kept when the imported data does not set them
        zpl_data = "^XA\n^FO10,10^A0N,30,30^FDTEXT^FS\n^XZ"
        wizard = self.env["wizard.import.zpl2"].create(dict(vals, data=zpl_data))
        wizard.import_zpl2()
        self.assertEqual((self.label.origin_x, self.label.origin_y), (20, 30))
        self.assertEqual(self.label.width, 949)
