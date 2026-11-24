"""Start the UR7e + Robotiq 2F-85 with ros2_control (real robot or mock hardware).

Simulated (no robot needed):
    ros2 launch ur7e_robotiq_control start_robot.launch.py use_mock_hardware:=true

Real robot:
    ros2 launch ur7e_robotiq_control start_robot.launch.py robot_ip:=<ROBOT_IP>

This wraps ur_robot_driver's standard ur_control.launch.py, swapping in our combined
arm + gripper model, and adds the gripper controller when simulating.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_ip = LaunchConfiguration("robot_ip")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    kinematics_params_file = LaunchConfiguration("kinematics_params_file")
    launch_rviz = LaunchConfiguration("launch_rviz")

    declared_arguments = [
        DeclareLaunchArgument(
            "robot_ip",
            default_value="0.0.0.0",
            description="IP address of the robot (ignored with use_mock_hardware:=true).",
        ),
        DeclareLaunchArgument(
            "use_mock_hardware",
            default_value="false",
            description="Simulate the arm and gripper instead of connecting to a robot.",
        ),
        DeclareLaunchArgument(
            "kinematics_params_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("ur_description"), "config", "ur7e", "default_kinematics.yaml"]
            ),
            description="Robot calibration file. Use your robot's own calibration on hardware "
            "(see ur_calibration).",
        ),
        DeclareLaunchArgument(
            "launch_rviz",
            default_value="false",
            description="Launch the driver's plain RViz view (MoveIt has its own).",
        ),
    ]

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
        }.items(),
    )

    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        condition=IfCondition(use_mock_hardware),
        arguments=[
            "robotiq_gripper_controller",
            "--controller-manager",
            "/controller_manager",
            "--param-file",
            PathJoinSubstitution(
                [FindPackageShare("ur7e_robotiq_control"), "config", "robotiq_controllers.yaml"]
            ),
        ],
    )

    return LaunchDescription(declared_arguments + [ur_control, gripper_controller_spawner])
