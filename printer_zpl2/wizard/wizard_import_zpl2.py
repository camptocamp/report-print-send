# Copyright (C) 2018 Florent de Labarre (<https://github.com/fmdl>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import binascii
import io
import logging
import re
import zlib

from PIL import Image, ImageOps

from odoo import fields, models

from ..models import zpl2

_logger = logging.getLogger(__name__)


def _compute_arg(data, arg):
    vals = {}
    for i, d in enumerate(data.split(",")):
        vals[arg[i]] = d
    return vals


def _field_origin(data):
    if data[:2] == "FO":
        position = data[2:]
        vals = _compute_arg(position, ["origin_x", "origin_y"])
        return vals
    return {}


def _font_format(data):
    if data[:1] == "A":
        data = data.split(",")
        vals = {}
        if len(data[0]) > 1:
            vals[zpl2.ARG_FONT] = data[0][1]
        if len(data[0]) > 2:
            vals[zpl2.ARG_ORIENTATION] = data[0][2]

        if len(data) > 1:
            vals[zpl2.ARG_HEIGHT] = data[1]
        if len(data) > 2:
            vals[zpl2.ARG_WIDTH] = data[2]
        return vals
    return {}


def _default_font_format(data):
    if data[:2] == "CF":
        args = [zpl2.ARG_FONT, zpl2.ARG_HEIGHT, zpl2.ARG_WIDTH]
        vals = _compute_arg(data[2:], args)
        if not vals.get(zpl2.ARG_HEIGHT):
            vals[zpl2.ARG_HEIGHT] = 10
        if not vals.get(zpl2.ARG_WIDTH):
            vals[zpl2.ARG_WIDTH] = vals[zpl2.ARG_HEIGHT]
        return vals
    return {}


def _field_block(data):
    if data[:2] == "FB":
        vals = {zpl2.ARG_IN_BLOCK: True}
        args = [
            zpl2.ARG_BLOCK_WIDTH,
            zpl2.ARG_BLOCK_LINES,
            zpl2.ARG_BLOCK_SPACES,
            zpl2.ARG_BLOCK_JUSTIFY,
            zpl2.ARG_BLOCK_LEFT_MARGIN,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _code11(data):
    if data[:2] == "B1":
        vals = {"component_type": zpl2.BARCODE_CODE_11}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_CHECK_DIGITS,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _interleaved2of5(data):
    if data[:2] == "B2":
        vals = {"component_type": zpl2.BARCODE_INTERLEAVED_2_OF_5}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
            zpl2.ARG_CHECK_DIGITS,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _code39(data):
    if data[:2] == "B3":
        vals = {"component_type": zpl2.BARCODE_CODE_39}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_CHECK_DIGITS,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _code49(data):
    if data[:2] == "B4":
        vals = {"component_type": zpl2.BARCODE_CODE_49}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_STARTING_MODE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _pdf417(data):
    if data[:2] == "B7":
        vals = {"component_type": zpl2.BARCODE_PDF417}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_SECURITY_LEVEL,
            zpl2.ARG_COLUMNS_COUNT,
            zpl2.ARG_ROWS_COUNT,
            zpl2.ARG_TRUNCATE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _ean8(data):
    if data[:2] == "B8":
        vals = {"component_type": zpl2.BARCODE_EAN_8}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _upce(data):
    if data[:2] == "B9":
        vals = {"component_type": zpl2.BARCODE_UPC_E}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
            zpl2.ARG_CHECK_DIGITS,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _code128(data):
    if data[:2] == "BC":
        vals = {"component_type": zpl2.BARCODE_CODE_128}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
            zpl2.ARG_CHECK_DIGITS,
            zpl2.ARG_MODE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _ean13(data):
    if data[:2] == "BE":
        vals = {"component_type": zpl2.BARCODE_EAN_13}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_INTERPRETATION_LINE,
            zpl2.ARG_INTERPRETATION_LINE_ABOVE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _qrcode(data):
    if data[:2] == "BQ":
        vals = {"component_type": zpl2.BARCODE_QR_CODE}
        args = [
            zpl2.ARG_ORIENTATION,
            zpl2.ARG_MODEL,
            zpl2.ARG_MAGNIFICATION_FACTOR,
            zpl2.ARG_ERROR_CORRECTION,
            zpl2.ARG_MASK_VALUE,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _default_barcode_field(data):
    if data[:2] == "BY":
        args = [zpl2.ARG_MODULE_WIDTH, zpl2.ARG_BAR_WIDTH_RATIO, zpl2.ARG_HEIGHT]
        return _compute_arg(data[2:], args)
    return {}


def _field_reverse_print(data):
    if data[:2] == "FR":
        return {zpl2.ARG_REVERSE_PRINT: True}
    return {}


def _graphic_box(data):
    if data[:2] == "GB":
        vals = {"component_type": "rectangle"}
        args = [
            zpl2.ARG_WIDTH,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_THICKNESS,
            zpl2.ARG_COLOR,
            zpl2.ARG_ROUNDING,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _graphic_diagonal_line(data):
    if data[:2] == "GD":
        vals = {"component_type": "diagonal"}
        args = [
            zpl2.ARG_WIDTH,
            zpl2.ARG_HEIGHT,
            zpl2.ARG_THICKNESS,
            zpl2.ARG_COLOR,
            zpl2.ARG_DIAGONAL_ORIENTATION,
        ]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _graphic_circle(data):
    if data[:2] == "GC":
        vals = {"component_type": "circle"}
        args = [zpl2.ARG_WIDTH, zpl2.ARG_THICKNESS, zpl2.ARG_COLOR]
        vals.update(_compute_arg(data[2:], args))
        return vals
    return {}


def _decode_graphic_data(data, total_bytes):
    """Decode the data of a ~DG or ^GF command into raw bitmap bytes

    The data is either hexadecimal ASCII (``^GFA``, ``~DG``), or base64
    with an optional zlib compression (``:B64:`` and ``:Z64:`` prefixes,
    followed by a CRC suffix), as generated by most label designers.
    """
    match = re.match(r":?(B64|Z64):([A-Za-z0-9+/=]+):?", data.strip())
    if match:
        raw = base64.b64decode(match.group(2))
        if match.group(1) == "Z64":
            raw = zlib.decompress(raw)
    else:
        raw = binascii.unhexlify(re.sub("[^A-F0-9]+", "", data))
    # Pad missing bytes with white
    return raw[:total_bytes].ljust(total_bytes, b"\x00")


def _graphic_vals(raw, total_bytes, bytes_per_row):
    """Return the component values of a raw monochrome bitmap"""
    width = bytes_per_row * 8
    height = total_bytes // bytes_per_row

    img = Image.frombytes("1", (width, height), raw, "raw").convert("L")
    img = ImageOps.invert(img)

    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format="PNG")
    image = base64.b64encode(imgByteArr.getvalue())

    return {
        "component_type": "graphic",
        "graphic_image": image,
        zpl2.ARG_WIDTH: width,
        zpl2.ARG_HEIGHT: height,
    }


def _graphic_field(data):
    if data[:3] == "GFA":
        _compression, _binary_bytes, total_bytes, bytes_per_row, ascii_data = data[
            3:
        ].split(",", 4)
        total_bytes = int(float(total_bytes))
        bytes_per_row = int(float(bytes_per_row))
        raw = _decode_graphic_data(ascii_data, total_bytes)
        return _graphic_vals(raw, total_bytes, bytes_per_row)
    return {}


def _graphic_name(name):
    """Normalize a graphic name: the device (R:, E:, ...) is optional"""
    return name.strip().split(":")[-1].upper()


def _download_graphics(data):
    """Extract the ~DG commands and return the graphics, by name, and the
    remaining data"""
    graphics = {}

    def _download(match):
        name, total_bytes, bytes_per_row, ascii_data = match.groups()
        total_bytes = int(total_bytes)
        bytes_per_row = int(bytes_per_row)
        raw = _decode_graphic_data(ascii_data, total_bytes)
        graphics[_graphic_name(name)] = _graphic_vals(raw, total_bytes, bytes_per_row)
        return ""

    data = re.sub(r"~DG([^,]+),(\d+),(\d+),([^~^]*)", _download, data)
    return graphics, data


def _recall_graphic(data):
    if data[:2] == "XG":
        args = data[2:].split(",")
        vals = {"component_type": "graphic", "graphic_name": _graphic_name(args[0])}
        if len(args) > 1 and args[1].strip():
            vals["magnification_x"] = int(args[1])
        if len(args) > 2 and args[2].strip():
            vals["magnification_y"] = int(args[2])
        return vals
    return {}


def _get_data(data):
    if data[:2] == "FD":
        return {"data": f'"{data[2:]}"'}
    return {}


SUPPORTED_CODE = {
    "FO": {"method": _field_origin},
    "FD": {"method": _get_data},
    "A": {"method": _font_format},
    "FB": {"method": _field_block},
    "B1": {"method": _code11},
    "B2": {"method": _interleaved2of5},
    "B3": {"method": _code39},
    "B4": {"method": _code49},
    "B7": {"method": _pdf417},
    "B8": {"method": _ean8},
    "B9": {"method": _upce},
    "BC": {"method": _code128},
    "BE": {"method": _ean13},
    "BQ": {"method": _qrcode},
    "BY": {
        "method": _default_barcode_field,
        "default": [
            zpl2.BARCODE_CODE_11,
            zpl2.BARCODE_INTERLEAVED_2_OF_5,
            zpl2.BARCODE_CODE_39,
            zpl2.BARCODE_CODE_49,
            zpl2.BARCODE_PDF417,
            zpl2.BARCODE_EAN_8,
            zpl2.BARCODE_UPC_E,
            zpl2.BARCODE_CODE_128,
            zpl2.BARCODE_EAN_13,
            zpl2.BARCODE_QR_CODE,
        ],
    },
    "CF": {"method": _default_font_format, "default": ["text"]},
    "FR": {"method": _field_reverse_print},
    "GB": {"method": _graphic_box},
    "GC": {"method": _graphic_circle},
    "GD": {"method": _graphic_diagonal_line},
    "GFA": {"method": _graphic_field},
    "XG": {"method": _recall_graphic},
}


class WizardImportZPl2(models.TransientModel):
    _name = "wizard.import.zpl2"
    _description = "Import ZPL2"

    label_id = fields.Many2one(
        comodel_name="printing.label.zpl2", string="Label", required=True, readonly=True
    )
    data = fields.Text(required=True, help="Printer used to print the labels.")
    delete_component = fields.Boolean(
        string="Delete existing components", default=False
    )

    def _start_sequence(self):
        sequences = self.mapped("label_id.component_ids.sequence")
        if sequences:
            return max(sequences) + 1
        return 0

    def import_zpl2(self):
        self.ensure_one()
        Zpl2Component = self.env["printing.label.zpl2.component"]

        if self.delete_component:
            self.mapped("label_id.component_ids").unlink()

        sequence = self._start_sequence()
        default = {}

        # Graphics are downloaded once (~DG) and recalled by name (^XG)
        graphics, data = _download_graphics(self.data)

        # A component is delimited by the field separator (^FS, or its SI
        # control code), whatever the line breaks in between: label designers
        # usually generate one command per line. As printers do, also start a
        # new field at each field origin (^FO, ^FT) when the separator is
        # missing.
        data = data.replace("\x0f", "^FS")
        for i, field in enumerate(re.split(r"\^FS|(?=\^F[OT])", data)):
            vals = {}

            args = re.split(r"[\^\r\n]", field)
            for arg in args:
                for _key, code in SUPPORTED_CODE.items():
                    component_arg = code["method"](arg)
                    if component_arg:
                        if code.get("default", False):
                            for deft in code.get("default"):
                                default.setdefault(deft, {}).update(component_arg)
                        else:
                            vals.update(component_arg)
                        break

            if "graphic_name" in vals:
                graphic = graphics.get(vals.pop("graphic_name"))
                if not graphic:
                    _logger.warning("Recalled graphic not found in the ZPL data")
                    continue
                vals.update(graphic)
                vals[zpl2.ARG_WIDTH] *= vals.pop("magnification_x", 1)
                vals[zpl2.ARG_HEIGHT] *= vals.pop("magnification_y", 1)

            if vals:
                if "component_type" not in vals.keys():
                    vals.update({"component_type": "text"})

                # The arguments of the field override the defaults, but the
                # omitted ones (empty) do not
                vals = {
                    **default.get(vals["component_type"], {}),
                    **{key: value for key, value in vals.items() if value != ""},
                }

                vals = self._update_vals(vals)

                seq = sequence + i * 10
                vals.update(
                    {
                        "name": self.env._("Import %s", seq),
                        "sequence": seq,
                        "model": str(zpl2.MODEL_ENHANCED),
                        "label_id": self.label_id.id,
                    }
                )
                Zpl2Component.create(vals)

    def _update_vals(self, vals):
        if "orientation" in vals.keys() and vals["orientation"] == "":
            vals["orientation"] = "N"

        # Field
        Zpl2Component = self.env["printing.label.zpl2.component"]
        model_fields = Zpl2Component.fields_get()
        component = {}
        for field, value in vals.items():
            if field in model_fields.keys():
                field_type = model_fields[field].get("type", False)
                if field_type == "boolean":
                    if not value or value == zpl2.BOOL_NO:
                        value = False
                    else:
                        value = True
                if field_type in ("integer", "float"):
                    value = float(value)
                if field == "model":
                    value = int(float(value))
                component.update({field: value})
        return component
