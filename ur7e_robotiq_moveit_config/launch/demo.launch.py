"""One-command MoveIt demo: simulated UR7e + Robotiq 2F-85 (mock hardware) with MoveIt and RViz.

    ros2 launch ur7e_robotiq_moveit_config demo.launch.py

No robot needed. This is the same as running, in two terminals:
    ros2 launch ur7e_robotiq_control start_robot.launch.py use_mock_hardware:=true
    ros2 launch ur7e_robotiq_moveit_config moveit.launch.py
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur7e_robotiq_control"), "launch", "start_robot.launch.py"]
            )
        ),
        # The driver's plain RViz is off; MoveIt's RViz below is used instead.
        launch_arguments={"use_mock_hardware": "true", "launch_rviz": "false"}.items(),
    )

    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("ur7e_robotiq_moveit_config"), "launch", "moveit.launch.py"]
            )
        ),
        # Must be set explicitly: launch arguments from the include above carry over.
        launch_arguments={"launch_rviz": "true"}.items(),
    )

    return LaunchDescription([robot, moveit])
