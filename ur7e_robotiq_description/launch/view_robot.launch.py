"""Show the UR7e + Robotiq 2F-85 model in RViz with joint sliders (no controllers, no MoveIt).

    ros2 launch ur7e_robotiq_description view_robot.launch.py
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Reuse UR's own viewer launch file, just pointing it at our combined model.
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                FrontendLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("ur_description"), "launch", "view_ur.launch.xml"]
                    )
                ),
                launch_arguments={
                    "ur_type": "ur7e",
                    "description_file": PathJoinSubstitution(
                        [
                            FindPackageShare("ur7e_robotiq_description"),
                            "urdf",
                            "ur7e_robotiq.urdf.xacro",
                        ]
                    ),
                }.items(),
            )
        ]
    )
