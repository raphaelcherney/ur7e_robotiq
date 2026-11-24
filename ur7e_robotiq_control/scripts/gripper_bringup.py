#!/usr/bin/env python3
"""Bring up the real Robotiq gripper whenever the robot program (ros_control) starts.

On the real robot the gripper is reached through the UR wrist connector (Tool Comm Forwarder
URCapX). The robot only powers the tool and enables its RS-485 interface once the External
Control program has been played, so the gripper can't be activated at launch.

- The gripper hardware starts "inactive" (config/controller_manager_real_gripper.yaml): its serial
  port, i.e. the connection to the forwarder, is opened at launch.
- Each time the program starts, this node waits a moment, then activates the gripper hardware
  (first time only, followed by one explicit gripper re-activation) and any gripper controllers
  that aren't active.
- In headless mode, if that first activation stops the robot program, the program is resent
  automatically (with the pendant workflow you press play again instead).
- It never switches anything off: the robot keeps the tool powered when the program stops, and
  ur_robot_driver's controller_stopper pauses the gripper controllers together with the arm's.
"""

import rclpy
from controller_manager_msgs.srv import (
    ListControllers,
    ListHardwareComponents,
    SetHardwareComponentState,
    SwitchController,
)
from std_srvs.srv import Trigger
from lifecycle_msgs.msg import State
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool

HARDWARE = "RobotiqGripperHardwareInterface"
CONTROLLERS = [
    "gripper_joint_state_broadcaster",
    "robotiq_gripper_controller",
    "robotiq_activation_controller",
]


class GripperBringup(Node):
    def __init__(self):
        super().__init__("gripper_bringup")
        self.delay = self.declare_parameter("activation_delay", 2.0).value
        # In headless mode there's no pendant program to press play on: if the gripper's
        # activation stops the robot program, send it again ourselves.
        self.headless = self.declare_parameter("headless_mode", False).value
        cm = "/controller_manager"
        self.list_hw = self.create_client(ListHardwareComponents, f"{cm}/list_hardware_components")
        self.set_hw = self.create_client(
            SetHardwareComponentState, f"{cm}/set_hardware_component_state"
        )
        self.list_ctrl = self.create_client(ListControllers, f"{cm}/list_controllers")
        self.switch = self.create_client(SwitchController, f"{cm}/switch_controller")
        self.reactivate = self.create_client(
            Trigger, "/robotiq_activation_controller/reactivate_gripper"
        )
        self.resend = self.create_client(Trigger, "/io_and_status_controller/resend_robot_program")
        self.resend_timer = None
        self.program_running = False
        self.needs_reactivation = False
        self.timer = None
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.create_subscription(
            Bool, "/io_and_status_controller/robot_program_running", self.on_program, qos
        )
        self.get_logger().info("Waiting for the robot program (ros_control) to start...")

    def on_program(self, msg: Bool):
        self.program_running = msg.data
        if msg.data and self.timer is None:
            self.timer = self.create_timer(self.delay, self.bring_up)

    def bring_up(self):
        self.timer.cancel()
        self.destroy_timer(self.timer)
        self.timer = None
        if not self.program_running:
            return
        self.call(self.list_hw, ListHardwareComponents.Request(), self.after_list_hw)

    def after_list_hw(self, res):
        if res is None:
            return
        state = next((c.state.label for c in res.component if c.name == HARDWARE), None)
        if state == "active":
            self.activate_controllers()
            return
        self.get_logger().info("Robot program running: activating the gripper.")
        req = SetHardwareComponentState.Request()
        req.name = HARDWARE
        req.target_state = State(id=State.PRIMARY_STATE_ACTIVE, label="active")
        self.call(self.set_hw, req, self.after_set_hw)

    def after_set_hw(self, res):
        self.needs_reactivation = res is not None and res.ok
        if self.headless and self.needs_reactivation and self.resend_timer is None:
            # Activating the gripper hardware blocks ros2_control for ~2 s, which makes the
            # robot's control script time out and exit. Restart it if that happened.
            self.resend_timer = self.create_timer(1.0, self.resend_if_stopped)
        if res is None or not res.ok:
            self.get_logger().error(
                "Could not activate the gripper. Check that the Tool Comm Forwarder URCapX is "
                "started and Tool I/O 'Controlled By' is 'User', then restart this launch "
                "(see README, Troubleshooting)."
            )
            return
        self.activate_controllers()

    def activate_controllers(self):
        self.call(self.list_ctrl, ListControllers.Request(), self.after_list_ctrl)

    def after_list_ctrl(self, res):
        if res is None:
            return
        inactive = [c.name for c in res.controller if c.name in CONTROLLERS and c.state != "active"]
        if not inactive:
            self.reactivate_once()
            return
        req = SwitchController.Request()
        req.activate_controllers = inactive
        req.strictness = SwitchController.Request.BEST_EFFORT
        self.call(self.switch, req, self.after_switch)

    def after_switch(self, res):
        if res is not None and res.ok:
            self.reactivate_once()
        else:
            self.get_logger().error("Could not activate the gripper controllers.")

    def resend_if_stopped(self):
        self.resend_timer.cancel()
        self.destroy_timer(self.resend_timer)
        self.resend_timer = None
        if self.program_running:
            return
        self.get_logger().info("Robot program stopped during gripper activation: resending it.")
        self.call(self.resend, Trigger.Request(), self.after_resend)

    def after_resend(self, res):
        if res is None or not res.success:
            self.get_logger().error(
                "Could not resend the robot program. Is the robot in Remote Control mode?"
            )

    def reactivate_once(self):
        # After the gripper has been powered off (e.g. robot reboot), robotiq_driver's own
        # activation can report success without the gripper really being activated; it then
        # ignores commands. One explicit re-activation (fingers open/close) fixes that.
        if not self.needs_reactivation:
            self.get_logger().info("Gripper ready.")
            return
        self.needs_reactivation = False
        self.call(self.reactivate, Trigger.Request(), self.after_reactivate)

    def after_reactivate(self, res):
        if res is not None and res.success:
            self.get_logger().info("Gripper ready.")
        else:
            self.get_logger().error("Gripper re-activation failed.")

    def call(self, client, req, callback):
        if not client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error(f"Service {client.srv_name} not available.")
            callback(None)
            return
        client.call_async(req).add_done_callback(lambda f: callback(f.result()))


def main():
    rclpy.init()
    rclpy.spin(GripperBringup())


if __name__ == "__main__":
    main()
