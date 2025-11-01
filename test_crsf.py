#!/usr/bin/env python3
"""
ExpressLRS CRSF Test Program
Simple test script for CRSF receiver functionality
"""

import sys
import time
from crsf_receiver import CRSFReceiver


def test_basic_connection(port='/dev/serial0'):
    """
    Test basic serial connection
    """
    print("=" * 80)
    print("Test 1: Basic Connection")
    print("=" * 80)
    
    crsf = CRSFReceiver(port=port)
    
    if crsf.open():
        print("✓ Serial port opened successfully")
        crsf.close()
        print("✓ Serial port closed successfully")
        return True
    else:
        print("✗ Failed to open serial port")
        return False


def test_frame_reception(port='/dev/serial0', duration=5):
    """
    Test frame reception for specified duration
    """
    print("\n" + "=" * 80)
    print(f"Test 2: Frame Reception ({duration} seconds)")
    print("=" * 80)
    print("Waiting for CRSF frames...")
    
    crsf = CRSFReceiver(port=port)
    
    if not crsf.open():
        print("✗ Failed to open serial port")
        return False
    
    start_time = time.time()
    received_channels = False
    received_link_stats = False
    
    try:
        while (time.time() - start_time) < duration:
            if crsf.read_frame():
                # Check if we received channel data
                channels = crsf.get_channels()
                if any(ch != 0 for ch in channels):
                    if not received_channels:
                        print("✓ Received RC channel data")
                        received_channels = True
                
                # Check if we received link statistics
                stats = crsf.get_link_statistics()
                if stats['link_quality'] > 0:
                    if not received_link_stats:
                        print("✓ Received link statistics")
                        received_link_stats = True
                
                if received_channels and received_link_stats:
                    break
            
            time.sleep(0.001)
    
    finally:
        crsf.close()
    
    frame_stats = crsf.get_statistics()
    print(f"\nFrame Statistics:")
    print(f"  Total frames: {frame_stats['frame_count']}")
    print(f"  Errors: {frame_stats['error_count']}")
    print(f"  Error rate: {frame_stats['error_rate']:.2%}")
    
    if frame_stats['frame_count'] > 0:
        print("✓ Frames received successfully")
        return True
    else:
        print("✗ No frames received")
        return False


def test_channel_values(port='/dev/serial0', duration=3):
    """
    Test channel value reading in different formats
    """
    print("\n" + "=" * 80)
    print(f"Test 3: Channel Value Formats ({duration} seconds)")
    print("=" * 80)
    
    crsf = CRSFReceiver(port=port)
    
    if not crsf.open():
        print("✗ Failed to open serial port")
        return False
    
    start_time = time.time()
    values_checked = False
    
    try:
        while (time.time() - start_time) < duration:
            if crsf.read_frame():
                channels_raw = crsf.get_channels()
                channels_norm = crsf.get_channels_normalized()
                channels_us = crsf.get_channels_microseconds()
                
                if any(ch != 0 for ch in channels_raw) and not values_checked:
                    print("\nChannel value formats:")
                    print(f"  Ch1 (Roll):")
                    print(f"    Raw (11-bit): {channels_raw[0]}")
                    print(f"    Normalized:   {channels_norm[0]:.3f}")
                    print(f"    Microseconds: {channels_us[0]}µs")
                    
                    print(f"  Ch3 (Throttle):")
                    print(f"    Raw (11-bit): {channels_raw[2]}")
                    print(f"    Normalized:   {channels_norm[2]:.3f}")
                    print(f"    Microseconds: {channels_us[2]}µs")
                    
                    # Verify value ranges
                    valid_raw = all(0 <= ch <= 2047 for ch in channels_raw)
                    valid_norm = all(-1.5 <= ch <= 1.5 for ch in channels_norm)
                    valid_us = all(800 <= ch <= 2200 for ch in channels_us)
                    
                    if valid_raw and valid_norm and valid_us:
                        print("\n✓ All channel value formats are valid")
                        values_checked = True
                    else:
                        print("\n✗ Invalid channel values detected")
                        return False
                    
                    break
            
            time.sleep(0.001)
    
    finally:
        crsf.close()
    
    if not values_checked:
        print("✗ Could not verify channel values (no data received)")
        return False
    
    return True


def test_link_statistics(port='/dev/serial0', duration=3):
    """
    Test link statistics reading
    """
    print("\n" + "=" * 80)
    print(f"Test 4: Link Statistics ({duration} seconds)")
    print("=" * 80)
    
    crsf = CRSFReceiver(port=port)
    
    if not crsf.open():
        print("✗ Failed to open serial port")
        return False
    
    start_time = time.time()
    stats_received = False
    
    try:
        while (time.time() - start_time) < duration:
            if crsf.read_frame():
                stats = crsf.get_link_statistics()
                
                if stats['link_quality'] > 0 and not stats_received:
                    print("\nLink Statistics:")
                    print(f"  RSSI 1:       {stats['rssi_1']} dBm")
                    print(f"  RSSI 2:       {stats['rssi_2']} dBm")
                    print(f"  Link Quality: {stats['link_quality']}%")
                    print(f"  SNR:          {stats['snr']} dB")
                    print(f"  RF Mode:      {stats['rf_mode']}")
                    
                    # Verify reasonable values
                    valid_rssi = -120 <= stats['rssi_1'] <= 0
                    valid_lq = 0 <= stats['link_quality'] <= 100
                    
                    if valid_rssi and valid_lq:
                        print("\n✓ Link statistics are valid")
                        stats_received = True
                    else:
                        print("\n✗ Invalid link statistics")
                        return False
                    
                    break
            
            time.sleep(0.001)
    
    finally:
        crsf.close()
    
    if not stats_received:
        print("✗ Could not receive link statistics")
        return False
    
    return True


def test_crc_validation(port='/dev/serial0', duration=5):
    """
    Test CRC error detection
    """
    print("\n" + "=" * 80)
    print(f"Test 5: CRC Validation ({duration} seconds)")
    print("=" * 80)
    
    crsf = CRSFReceiver(port=port)
    
    if not crsf.open():
        print("✗ Failed to open serial port")
        return False
    
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < duration:
            crsf.read_frame()
            time.sleep(0.001)
    
    finally:
        frame_stats = crsf.get_statistics()
        crsf.close()
    
    print(f"\nCRC Statistics:")
    print(f"  Total frames: {frame_stats['frame_count']}")
    print(f"  CRC errors:   {frame_stats['error_count']}")
    print(f"  Error rate:   {frame_stats['error_rate']:.2%}")
    
    if frame_stats['frame_count'] > 0:
        if frame_stats['error_rate'] < 0.05:  # Less than 5% error rate
            print("\n✓ CRC validation working (low error rate)")
            return True
        else:
            print("\n⚠ High CRC error rate (check wiring/interference)")
            return True  # Still pass, but warn user
    else:
        print("\n✗ No frames received for CRC test")
        return False


def run_all_tests(port='/dev/serial0'):
    """
    Run all tests
    """
    print("\n" + "=" * 80)
    print("ExpressLRS CRSF Test Suite")
    print("=" * 80)
    print(f"Testing port: {port}")
    print(f"Expected baudrate: 420000 bps")
    print("\nMake sure:")
    print("1. ExpressLRS receiver is powered on")
    print("2. Receiver is bound to a transmitter")
    print("3. Transmitter is turned on")
    print("4. Receiver is connected to GPIO14/15")
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Frame Reception", test_frame_reception),
        ("Channel Values", test_channel_values),
        ("Link Statistics", test_link_statistics),
        ("CRC Validation", test_crc_validation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func(port)
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
        
        time.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


def main():
    """Main entry point"""
    port = '/dev/serial0'
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python3 test_crsf.py [port]")
            print("\nExamples:")
            print("  python3 test_crsf.py")
            print("  python3 test_crsf.py /dev/ttyAMA0")
            return 0
        else:
            port = sys.argv[1]
    
    return run_all_tests(port)


if __name__ == "__main__":
    sys.exit(main())
