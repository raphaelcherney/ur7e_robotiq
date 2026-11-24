#!/usr/bin/env python3
"""Check that the Robotiq gripper can be reached through the robot's Tool Comm Forwarder.

Read-only: sends one Modbus RTU "read gripper status" request to the forwarder's TCP port and
prints the reply. The gripper does not move. Stop the ROS driver first (only one client should
use the forwarder at a time), and have the ros_control program played at least once since the
robot booted (that is what powers the tool and enables RS-485).

    ros2 run ur7e_robotiq_control check_gripper_comm.py [robot_ip]
"""

import socket
import sys
import time

ROBOT_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.56.101"
PORT = 54321


def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return bytes([crc & 0xFF, crc >> 8])


def main():
    try:
        s = socket.create_connection((ROBOT_IP, PORT), timeout=3)
    except OSError as e:
        print(f"FAIL: cannot connect to {ROBOT_IP}:{PORT} ({e}).")
        print("  -> Is the Tool Comm Forwarder URCapX installed and started? Is port 54321 allowed")
        print("     under Settings > Security > General > Inbound Connections?")
        return 1
    s.settimeout(1.0)
    try:
        if s.recv(64) == b"":
            print("FAIL: the robot closed the connection immediately.")
            print("  -> The forwarder can't open the tool serial port. Uninstall the Robotiq URCapX,")
            print("     set Application > Communication > Tool I/O > 'Controlled By' to User, and")
            print("     restart the robot controller (see README, Troubleshooting).")
            return 1
    except socket.timeout:
        pass  # connection stays open: good
    request = bytes([0x09, 0x04, 0x07, 0xD0, 0x00, 0x03])  # slave 9, read 3 input registers
    s.sendall(request + crc16(request))
    reply, end = b"", time.time() + 2
    while len(reply) < 11 and time.time() < end:
        try:
            chunk = s.recv(64)
        except socket.timeout:
            continue
        if not chunk:
            break
        reply += chunk
    s.close()
    if len(reply) >= 9 and reply[:3] == b"\x09\x04\x06":
        status, fault, position = reply[3], reply[5], reply[7]
        print(f"OK: gripper answered. activated={status & 1}, fault=0x{fault:02x}, "
              f"position={position}/255")
        return 0
    print(f"FAIL: no valid reply from the gripper (got: {reply.hex(' ') or 'nothing'}).")
    print("  -> Play the ros_control program once (it powers the tool and enables RS-485),")
    print("     check the gripper cable, then try again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
