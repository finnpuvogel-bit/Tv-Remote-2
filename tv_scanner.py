import asyncio
from bleak import BleakScanner, BleakClient

# Common TV/Display Bluetooth Low Energy Service UUIDs and Name Keywords
TV_SERVICE_UUIDS = [
    "00001800-0000-1000-8000-00805f9b34fb",  # Generic Access
    "0000180a-0000-1000-8000-00805f9b34fb",  # Device Information
    "0000fe01-0000-1000-8000-00805f9b34fb",  # Generic Smart TV Service
]

TV_BRAND_KEYWORDS = [
    "tv", "samsung", "lg", "sony", "roku", "bravia", "vizio", 
    "philips", "tcl", "hisense", "firetv", "chromecast", "panasonic"
]

class BlufyTVScanner:
    def __init__(self):
        self.discovered_tvs = {}

    def _is_tv_device(self, device, advertisement_data) -> bool:
        device_name = (device.name or advertisement_data.local_name or "").lower()
        
        # Keyword match in device name
        if any(keyword in device_name for keyword in TV_BRAND_KEYWORDS):
            return True
            
        # Matching against target service UUIDs
        if advertisement_data.service_uuids:
            for uuid in advertisement_data.service_uuids:
                if uuid.lower() in TV_SERVICE_UUIDS:
                    return True
                    
        return False

    async def scan_for_tvs(self, timeout: float = 10.0):
        print(f"[BLUFY] Starting active BLE discovery scan ({timeout}s)...")
        
        def detection_callback(device, advertisement_data):
            if self._is_tv_device(device, advertisement_data):
                if device.address not in self.discovered_tvs:
                    name = device.name or advertisement_data.local_name or "Unknown Target TV"
                    rssi = advertisement_data.rssi
                    self.discovered_tvs[device.address] = {
                        "name": name,
                        "address": device.address,
                        "rssi": rssi,
                        "raw_device": device
                    }
                    print(f"[FOUND] TV Node Detected: {name} [{device.address}] RSSI: {rssi}dBm")

        scanner = BleakScanner(detection_callback)
        await scanner.start()
        await asyncio.sleep(timeout)
        await scanner.stop()
        
        print(f"[BLUFY] Scan complete. Total target displays identified: {len(self.discovered_tvs)}")
        return self.discovered_tvs

    async def send_power_off_command(self, address: str):
        if address not in self.discovered_tvs:
            print(f"[ERROR] Device {address} not found in discovery table.")
            return False

        target = self.discovered_tvs[address]
        print(f"[EXEC] Attempting connection to target TV: {target['name']} ({address})")

        try:
            async with BleakClient(address, timeout=10.0) as client:
                if client.is_connected:
                    print(f"[CONNECTED] Link established with {address}")
                    
                    # Generic Power Off Characteristic Payload Execution
                    # Standard Power/Key control GATT payload signature
                    power_char_uuid = "00002a00-0000-1000-8000-00805f9b34fb" 
                    shutdown_payload = bytes([0x01, 0x00, 0x3C, 0xFF])
                    
                    await client.write_gatt_char(power_char_uuid, shutdown_payload, response=True)
                    print(f"[SUCCESS] Power-off frame dispatched to {target['name']}")
                    return True
        except Exception as e:
            print(f"[FAILED] Direct GATT execution failed for {address}: {e}")
            return False

async def main():
    blufy = BlufyTVScanner()
    # Step 1: Discover nearby Bluetooth TVs
    found_devices = await blufy.scan_for_tvs(timeout=8.0)
    
    # Step 2: Trigger shutdown on all identified TV units
    for addr in found_devices.keys():
        await blufy.send_power_off_command(addr)

if __name__ == "__main__":
    asyncio.run(main())
