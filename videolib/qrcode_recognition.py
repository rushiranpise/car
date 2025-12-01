import cv2
from pyzbar import pyzbar
from PIL import Image, ImageDraw, ImageFont
import numpy as np
'''Define parameters for qrcode recognition object'''
qrcode_obj_parameter = {}
qrcode_obj_parameter['x'] = 0   
qrcode_obj_parameter['y'] = 0   
qrcode_obj_parameter['w'] = 0     
qrcode_obj_parameter['h'] = 0     
qrcode_obj_parameter['data'] = "None" 
qrcode_obj_parameter['list'] = []
FONT_PATH = "/opt/vilib/Arial-Unicode-Regular.ttf"
FONT_SIZE = 16
font = None
def qrcode_recognize(img, border_rgb=(255, 0, 0), font_color=(0, 0, 255)):
    global font
    barcodes = pyzbar.decode(img)
    qrcode_obj_parameter['list'].clear()
    if len(barcodes) > 0:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        draw = ImageDraw.Draw(img)
        if font is None:
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE, encoding="utf-8")
        for barcode in barcodes:
            (x, y, w, h) = barcode.rect
            draw.rectangle([x, y, x+w, y+h], outline=border_rgb, width=2)
            barcodeData = barcode.data.decode("utf-8")
            text = f"{barcodeData}"
            qrcode_obj_parameter['list'].append({
                'text': text,
                'x': x,
                'y': y,
                'w': w,
                'h': h,
            })
            if len(text) > 0:
                qrcode_obj_parameter['data'] = text
                qrcode_obj_parameter['h'] = h
                qrcode_obj_parameter['w'] = w
                qrcode_obj_parameter['x'] = x 
                qrcode_obj_parameter['y'] = y
                draw.text((x, y-FONT_SIZE-2), text, font_color, font=font)
            else:
                qrcode_obj_parameter['data'] = "None"
                qrcode_obj_parameter['x'] = 0
                qrcode_obj_parameter['y'] = 0
                qrcode_obj_parameter['w'] = 0
                qrcode_obj_parameter['h'] = 0
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img
    else:
        qrcode_obj_parameter['data'] = "None"
        qrcode_obj_parameter['x'] = 0
        qrcode_obj_parameter['y'] = 0
        qrcode_obj_parameter['w'] = 0
        qrcode_obj_parameter['h'] = 0
        qrcode_obj_parameter['list'] = []
        return img
