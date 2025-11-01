#!/usr/bin/env python3
"""
ExpressLRS CRSF Protocol Receiver
GPIO14 (TXD) and GPIO15 (RXD) CRSF Communication

This program reads CRSF (Crossfire) protocol frames from ExpressLRS receiver
connected to Raspberry Pi GPIO14/15.
"""

import serial
import struct
import time
import sys
from enum import IntEnum


class CRSFFrameType(IntEnum):
    """CRSF Frame Types"""
    GPS = 0x02
    VARIO = 0x07
    BATTERY_SENSOR = 0x08
    BARO_ALTITUDE = 0x09
    LINK_STATISTICS = 0x14
    RC_CHANNELS_PACKED = 0x16
    ATTITUDE = 0x1E
    FLIGHT_MODE = 0x21
    DEVICE_PING = 0x28
    DEVICE_INFO = 0x29
    PARAMETER_SETTINGS_ENTRY = 0x2B
    PARAMETER_READ = 0x2C
    PARAMETER_WRITE = 0x2D
    COMMAND = 0x32


class CRSFAddress(IntEnum):
    """CRSF Device Addresses"""
    BROADCAST = 0x00
    USB = 0xC8
    TBS_CORE_PNP_PRO = 0x80
    RESERVED1 = 0x8A
    CURRENT_SENSOR = 0xC0
    GPS = 0xC2
    TBS_BLACKBOX = 0xC4
    FLIGHT_CONTROLLER = 0xC8
    RESERVED2 = 0xCA
    RACE_TAG = 0xCC
    RADIO_TRANSMITTER = 0xEA
    CRSF_RECEIVER = 0xEC
    CRSF_TRANSMITTER = 0xEE


class CRSFReceiver:
    """
    CRSF Protocol Receiver for ExpressLRS
    
    Handles CRSF frame parsing from ExpressLRS receiver
    """
    
    CRSF_BAUDRATE = 420000  # CRSF standard baudrate
    CRSF_SYNC_BYTE = 0xC8   # Frame sync byte
    CRSF_MAX_PACKET_SIZE = 64
    
    def __init__(self, port='/dev/serial0', baudrate=None, timeout=0.1):
        """
        Initialize CRSF receiver
        
        Args:
            port (str): Serial port device path
            baudrate (int): Baudrate (default: 420000 for CRSF)
            timeout (float): Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate or self.CRSF_BAUDRATE
        self.timeout = timeout
        self.serial = None
        self.buffer = bytearray()
        
        # Channel data (16 channels, 11-bit resolution)
        self.channels = [0] * 16
        
        # Link statistics
        self.rssi_1 = 0
        self.rssi_2 = 0
        self.link_quality = 0
        self.snr = 0
        self.active_antenna = 0
        self.rf_mode = 0
        self.tx_power = 0
        
        # Frame statistics
        self.frame_count = 0
        self.error_count = 0
        
    def open(self):
        """Open serial port connection"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            print(f"CRSF receiver opened on {self.port}")
            print(f"Baudrate: {self.baudrate} bps")
            return True
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            return False
    
    def close(self):
        """Close serial port connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Serial port closed")
    
    def _calculate_crc(self, data):
        """
        Calculate CRSF CRC8 (DVB-S2)
        
        Args:
            data (bytes): Data to calculate CRC for
            
        Returns:
            int: CRC8 value
        """
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0xD5
                else:
                    crc = crc << 1
            crc &= 0xFF
        return crc
    
    def _parse_rc_channels(self, payload):
        """
        Parse RC channels from CRSF frame
        
        Args:
            payload (bytes): Frame payload
        """
        if len(payload) < 22:
            return
        
        # CRSF uses 11-bit channel data, packed
        # 16 channels packed into 22 bytes
        bits = int.from_bytes(payload[:22], byteorder='little')
        
        for i in range(16):
            self.channels[i] = (bits >> (i * 11)) & 0x7FF
    
    def _parse_link_statistics(self, payload):
        """
        Parse link statistics from CRSF frame
        
        Args:
            payload (bytes): Frame payload
        """
        if len(payload) < 10:
            return
        
        self.rssi_1 = payload[0]  # Uplink RSSI ant. 1 (dBm)
        self.rssi_2 = payload[1]  # Uplink RSSI ant. 2 (dBm)
        self.link_quality = payload[2]  # Uplink link quality (0-100%)
        self.snr = struct.unpack('b', bytes([payload[3]]))[0]  # Uplink SNR (dB)
        self.active_antenna = payload[4]  # Diversity active antenna
        self.rf_mode = payload[5]  # RF Mode
        self.tx_power = payload[6]  # Uplink TX power
        
    def _parse_frame(self, frame):
        """
        Parse a complete CRSF frame
        
        Args:
            frame (bytes): Complete CRSF frame
        """
        if len(frame) < 4:
            return
        
        # Frame format: [address][length][type][payload...][crc]
        address = frame[0]
        length = frame[1]
        frame_type = frame[2]
        payload = frame[3:-1]
        crc = frame[-1]
        
        # Verify CRC
        calculated_crc = self._calculate_crc(frame[2:-1])
        if crc != calculated_crc:
            self.error_count += 1
            return
        
        self.frame_count += 1
        
        # Parse based on frame type
        if frame_type == CRSFFrameType.RC_CHANNELS_PACKED:
            self._parse_rc_channels(payload)
        elif frame_type == CRSFFrameType.LINK_STATISTICS:
            self._parse_link_statistics(payload)
    
    def read_frame(self):
        """
        Read and parse CRSF frames from serial port
        
        Returns:
            bool: True if frame was parsed successfully
        """
        if not self.serial or not self.serial.is_open:
            return False
        
        # Read available data
        if self.serial.in_waiting > 0:
            data = self.serial.read(self.serial.in_waiting)
            self.buffer.extend(data)
        
        # Look for sync byte
        while len(self.buffer) >= 4:
            # Find sync byte (device address)
            if self.buffer[0] not in [addr.value for addr in CRSFAddress]:
                self.buffer.pop(0)
                continue
            
            # Check if we have enough data for the frame
            frame_length = self.buffer[1]
            if frame_length > self.CRSF_MAX_PACKET_SIZE:
                self.buffer.pop(0)
                continue
            
            # Wait for complete frame (address + length + payload + crc)
            total_length = frame_length + 2
            if len(self.buffer) < total_length:
                break
            
            # Extract frame
            frame = bytes(self.buffer[:total_length])
            self.buffer = self.buffer[total_length:]
            
            # Parse frame
            self._parse_frame(frame)
            return True
        
        return False
    
    def get_channels(self):
        """
        Get current RC channel values
        
        Returns:
            list: List of 16 channel values (0-2047, 11-bit)
        """
        return self.channels.copy()
    
    def get_channels_normalized(self):
        """
        Get normalized RC channel values (-1.0 to 1.0)
        
        Returns:
            list: List of 16 normalized channel values
        """
        # CRSF center is 992, range is 172-1811
        return [(ch - 992) / 819.0 for ch in self.channels]
    
    def get_channels_microseconds(self):
        """
        Get RC channel values in microseconds (1000-2000µs)
        
        Returns:
            list: List of 16 channel values in microseconds
        """
        # Convert 11-bit (172-1811) to microseconds (1000-2000)
        return [int(1000 + (ch - 172) * 1000 / 1639) for ch in self.channels]
    
    def get_link_statistics(self):
        """
        Get link statistics
        
        Returns:
            dict: Link statistics dictionary
        """
        return {
            'rssi_1': self.rssi_1,
            'rssi_2': self.rssi_2,
            'link_quality': self.link_quality,
            'snr': self.snr,
            'active_antenna': self.active_antenna,
            'rf_mode': self.rf_mode,
            'tx_power': self.tx_power
        }
    
    def get_statistics(self):
        """
        Get frame statistics
        
        Returns:
            dict: Statistics dictionary
        """
        return {
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, self.frame_count)
        }


def print_channels(crsf):
    """Print channel values"""
    channels = crsf.get_channels()
    channels_us = crsf.get_channels_microseconds()
    
    print("\n" + "=" * 80)
    print("RC Channels (11-bit / microseconds):")
    print("-" * 80)
    
    for i in range(0, 16, 4):
        line = ""
        for j in range(4):
            ch = i + j
            if ch < 16:
                line += f"Ch{ch+1:2d}: {channels[ch]:4d} ({channels_us[ch]:4d}µs)  "
        print(line)


def print_link_stats(crsf):
    """Print link statistics"""
    stats = crsf.get_link_statistics()
    
    print("\n" + "=" * 80)
    print("Link Statistics:")
    print("-" * 80)
    print(f"RSSI 1:        {stats['rssi_1']:3d} dBm")
    print(f"RSSI 2:        {stats['rssi_2']:3d} dBm")
    print(f"Link Quality:  {stats['link_quality']:3d} %")
    print(f"SNR:           {stats['snr']:3d} dB")
    print(f"Active Ant:    {stats['active_antenna']}")
    print(f"RF Mode:       {stats['rf_mode']}")
    print(f"TX Power:      {stats['tx_power']}")


def continuous_monitor(crsf, duration=None):
    """
    Continuously monitor CRSF data
    
    Args:
        crsf (CRSFReceiver): CRSF receiver instance
        duration (float): Duration in seconds (None for infinite)
    """
    print("\n" + "=" * 80)
    print("CRSF Monitor Mode")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    
    start_time = time.time()
    last_print = 0
    
    try:
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            
            crsf.read_frame()
            
            # Print updates every 0.5 seconds
            if time.time() - last_print > 0.5:
                print_channels(crsf)
                print_link_stats(crsf)
                
                frame_stats = crsf.get_statistics()
                print(f"\nFrames: {frame_stats['frame_count']}, "
                      f"Errors: {frame_stats['error_count']}, "
                      f"Error Rate: {frame_stats['error_rate']:.2%}")
                
                last_print = time.time()
            
            time.sleep(0.001)  # Small delay
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")


def main():
    """Main program"""
    print("ExpressLRS CRSF Protocol Receiver")
    print("GPIO14 (TXD) and GPIO15 (RXD)")
    print("-" * 80)
    
    # Parse command line arguments
    port = '/dev/serial0'
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    # Create CRSF receiver
    crsf = CRSFReceiver(port=port)
    
    # Open serial port
    if not crsf.open():
        print("Failed to open serial port. Exiting.")
        print("\nMake sure:")
        print("1. Serial port is enabled (sudo raspi-config)")
        print("2. User is in dialout group (sudo usermod -a -G dialout $USER)")
        print("3. ExpressLRS receiver is connected to GPIO14/15")
        return 1
    
    try:
        # Start monitoring
        continuous_monitor(crsf)
    
    finally:
        crsf.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
