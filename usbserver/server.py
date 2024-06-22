from flask import Flask, request
import usb
import usb.core
import usb.backend.libusb1
import os

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
    bytes_to_write = request.get_data()
    ep.write(bytes_to_write)
    usb.util.dispose_resources(dev)
    return {"result": "success", "reason": "Data sent to the usb device"}

if __name__ == '__main__':
    app.run()