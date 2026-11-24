"""Start the UR7e + Robotiq 2F-85 with ros2_control (real robot or mock hardware).

Simulated (no robot needed):
    ros2 launch ur7e_robotiq_control start_robot.launch.py use_mock_hardware:=true

Real robot, robot in Remote control mode (robot_serial is on the arm's label and selects its
calibration):
    ros2 launch ur7e_robotiq_control start_robot.launch.py robot_serial:=20265702158

Real robot using the ros_control program on the pendant instead (robot in Local mode):
    ros2 launch ur7e_robotiq_control start_robot.launch.py robot_serial:=20265702158 headless_mode:=false

This wraps ur_robot_driver's standard ur_control.launch.py, swapping in our combined
arm + gripper model, and adds the gripper controllers.

On the real robot the gripper is controlled through the UR wrist connector. That needs the
Tool Comm Forwarder URCapX installed and started on the robot (see README). The gripper is
activated once the robot program first runs (scripts/gripper_bringup.py). That first
activation stops the program: in headless mode it is resent automatically, with the pendant
program press play again. Use use_gripper:=false to run the arm alone.
"""

import subprocess

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    Shutdown,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    AndSubstitution,
    LaunchConfiguration,
    NotSubstitution,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def start_if_no_other_gripper_bridge(context, use_tool_communication, actions):
    """Start `actions`, unless a gripper serial bridge from an earlier launch is still running.

    A leftover socat (e.g. from a launch that crashed) also holds a connection to the robot's
    Tool Comm Forwarder and the /tmp/ttyUR link, and the gripper then never answers.
    """
    if context.perform_substitution(use_tool_communication) != "true":
        return actions
    found = subprocess.run(["pgrep", "-f", "socat.*link=/tmp/ttyUR"], capture_output=True)
    if found.returncode != 0:
        return actions
    return [
        LogInfo(
            msg="A gripper serial bridge (socat on /tmp/ttyUR) from an earlier launch is still "
            "running, so the gripper wouldn't answer. Stop all other robot launches, then run: "
            "pkill -f 'link=/tmp/ttyUR'; pkill -f tool_communication.py"
        ),
        Shutdown(reason="another gripper bridge is already running"),
    ]


def generate_launch_description():
    robot_ip = LaunchConfiguration("robot_ip")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    use_gripper = LaunchConfiguration("use_gripper")
    headless_mode = LaunchConfiguration("headless_mode")
    kinematics_params_file = LaunchConfiguration("kinematics_params_file")
    launch_rviz = LaunchConfiguration("launch_rviz")

    declared_arguments = [
        DeclareLaunchArgument(
            "robot_ip",
            default_value="192.168.56.101",
            description="IP address of the robot (UR's standard direct-cable address). "
            "Ignored with use_mock_hardware:=true.",
        ),
        DeclareLaunchArgument(
            "use_mock_hardware",
            default_value="false",
            description="Simulate the arm and gripper instead of connecting to a robot.",
        ),
        DeclareLaunchArgument(
            "robot_serial",
            default_value="nominal",
            description="Serial number of the arm (on its label), used to pick "
            "config/calibration/ur7e_<robot_serial>.yaml. 'nominal' = uncalibrated UR model.",
        ),
        DeclareLaunchArgument(
            "kinematics_params_file",
            default_value=PathJoinSubstitution(
                [
                    FindPackageShare("ur7e_robotiq_control"),
                    "config",
                    "calibration",
                    ["ur7e_", LaunchConfiguration("robot_serial"), ".yaml"],
                ]
            ),
            description="Robot calibration file (normally chosen via robot_serial).",
        ),
        DeclareLaunchArgument(
            "use_gripper",
            default_value="true",
            description="Control the real gripper through the wrist connector "
            "(needs the Tool Comm Forwarder URCapX). Always on in simulation.",
        ),
        DeclareLaunchArgument(
            "headless_mode",
            default_value="true",
            description="Send the control program from ROS (robot in Remote control mode). "
            "Set to false to use the ros_control program on the pendant instead (Local mode).",
        ),
        DeclareLaunchArgument(
            "launch_rviz",
            default_value="false",
            description="Launch the driver's plain RViz view (MoveIt has its own).",
        ),
    ]

    # Real robot + gripper: forward the wrist connector's RS-485 to a virtual serial port
    # (/tmp/ttyUR) that robotiq_driver opens. Settings are the Robotiq 2F-85 defaults.
    use_tool_communication = AndSubstitution(use_gripper, NotSubstitution(use_mock_hardware))
    real_gripper = IfCondition(use_tool_communication)

    # Real robot + gripper: the gripper hardware starts "unconfigured" and gripper_bringup.py
    # activates it once the robot program runs (the tool is only powered/enabled then).
    controller_manager_config = PythonExpression(
        [
            "'",
            PathJoinSubstitution(
                [FindPackageShare("ur7e_robotiq_control"), "config", "controller_manager_real_gripper.yaml"]
            ),
            "' if '",
            use_tool_communication,
            "' == 'true' else '",
            PathJoinSubstitution(
                [FindPackageShare("ur_robot_driver"), "config", "ur7e_update_rate.yaml"]
            ),
            "'",
        ]
    )

    ur_control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur_robot_driver"), "launch", "ur_control.launch.py"]
            )
        ),
        launch_arguments={
            "ur_type": "ur7e",
            "robot_ip": robot_ip,
            "use_mock_hardware": use_mock_hardware,
            "kinematics_params_file": kinematics_params_file,
            "launch_rviz": launch_rviz,
            # Our combined arm + gripper model, read by ur_robot_driver's ur_rsp.launch.py
            "description_file": PathJoinSubstitution(
                [
                    FindPackageShare("ur7e_robotiq_control"),
                    "urdf",
                    "ur7e_robotiq_controlled.urdf.xacro",
                ]
            ),
            "use_tool_communication": use_tool_communication,
            "tool_voltage": "24",
            "tool_parity": "0",
            "tool_baud_rate": "115200",
            "tool_stop_bits": "1",
            "tool_rx_idle_chars": "1.5",
            "tool_tx_idle_chars": "3.5",
            "tool_device_name": "/tmp/ttyUR",
            "update_rate_config_file": controller_manager_config,
            "headless_mode": headless_mode,
        }.items(),
    )

    gripper_controllers_file = PathJoinSubstitution(
        [FindPackageShare("ur7e_robotiq_control"), "config", "robotiq_controllers.yaml"]
    )
    gripper_controllers = ["robotiq_gripper_controller", "robotiq_activation_controller"]

    # Simulation: start the gripper controllers right away.
    mock_gripper_spawner = Node(
        package="controller_manager",
        executable="spawner",
        condition=IfCondition(use_mock_hardware),
        arguments=gripper_controllers
        + ["--controller-manager", "/controller_manager", "--param-file", gripper_controllers_file],
    )

    # Real robot: load them inactive; gripper_bringup activates them when the program runs.
    real_gripper_spawner = Node(
        package="controller_manager",
        executable="spawner",
        condition=real_gripper,
        arguments=["gripper_joint_state_broadcaster"]
        + gripper_controllers
        + [
            "--inactive",
            "--controller-manager",
            "/controller_manager",
            "--param-file",
            gripper_controllers_file,
        ],
    )
    gripper_bringup = Node(
        package="ur7e_robotiq_control",
        executable="gripper_bringup.py",
        condition=real_gripper,
        parameters=[{"headless_mode": headless_mode}],
        output="screen",
    )

    start = OpaqueFunction(
        function=start_if_no_other_gripper_bridge,
        args=[
            use_tool_communication,
            [ur_control, mock_gripper_spawner, real_gripper_spawner, gripper_bringup],
        ],
    )

    return LaunchDescription(declared_arguments + [start])
