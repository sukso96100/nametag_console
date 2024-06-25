from flask import Flask, request
import usb
import usb.core
import usb.backend.libusb1
import os
from PIL import Image 
import io


app = Flask(__name__)

@app.route('/list', methods=['GET'])
def get_device_list():
    if os.getenv("LIBUSB_PATH", None) is not None:
        backend = usb.backend.libusb1.get_backend(find_library=lambda x: os.getenv("LIBUSB_PATH", ""))
        devices = usb.core.find(find_all=1, backend=backend)
    else:
        devices = usb.core.find(find_all=1)
    device_list_dict = []
    for device in devices:
        device_list_dict.append({
            'vendorId': device.idVendor,
            'productId': device.idProduct,
            'manufacturerName': usb.util.get_string(device, device.iManufacturer),
            'productName': usb.util.get_string(device, device.iProduct),
        })
    return device_list_dict

def build_bitmap_print_tspl_cmd(x, y, img_width_px, img_height_px, canvas_width_mm, canvas_height_mm, image_bitmap):
    width_in_bytes = (img_width_px // 8)
    commands_bytearray = bytearray()
    commands_list = [
        f"SIZE {canvas_width_mm} mm,{canvas_height_mm} mm\r\nCLS\r\n".encode(),
        f"BITMAP {x},{y},{width_in_bytes},{img_height_px},1, ".encode(),
        image_bitmap,
        "\r\nPRINT 1\r\nEND\r\n".encode(),
    ]
    for cmd in commands_list:
        commands_bytearray.append(cmd)
    return commands_bytearray 

@app.route('/write_usb/<int:vendor_id>/<int:product_id>', methods=['POST'])
def write_usb(vendor_id, product_id):
    if os.getenv("LIBUSB_PATH", None) is not None:
        backend = usb.backend.libusb1.get_backend(find_library=lambda x: os.getenv("LIBUSB_PATH", ""))
    # find our device
        dev = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=backend)
    else:
        dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)
    # was it found?
    if dev is None:
        print("Device not found")
        return {"result": "error", "reason": "Device not found"}

    if dev.is_kernel_driver_active(0):
        try:
            dev.detach_kernel_driver(0)
        except usb.core.USBError as e:
            print("Could not detatch kernel driver from interface({0}): {1}".format(0, str(e)))
    # set the active configuration. With no arguments, the first
    # configuration will be the active one
    dev.set_configuration()

    # get an endpoint instance
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]

    ep = usb.util.find_descriptor(
    intf,
    # match the first OUT endpoint
    custom_match = \
    lambda e: \
        usb.util.endpoint_direction(e.bEndpointAddress) == \
        usb.util.ENDPOINT_OUT)
    image = Image.open(io.BytesIO(request.get_data()))
    monochrome_image = image.convert('1')

    monochrome_image_bytes = io.BytesIO()
    monochrome_image.save(monochrome_image_bytes, format=monochrome_image.format)
    monochrome_image_bytes = monochrome_image_bytes.getvalue()
    ep.write(monochrome_image_bytes)
    usb.util.dispose_resources(dev)
    return {"result": "success", "reason": "Data sent to the usb device"}

if __name__ == '__main__':
    app.run()