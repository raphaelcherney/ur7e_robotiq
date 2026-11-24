"""Start MoveIt (move_group + RViz) for the UR7e + Robotiq 2F-85.

Run this after ur7e_robotiq_control/start_robot.launch.py is up (real or mock hardware):
    ros2 launch ur7e_robotiq_moveit_config moveit.launch.py

Modeled on ur_moveit_config/launch/ur_moveit.launch.py. Like that file, the robot model is
read from the /robot_description topic published by the driver, so MoveIt always uses the
same (calibrated) model as the robot.
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    launch_rviz = LaunchConfiguration("launch_rviz")
    use_sim_time = LaunchConfiguration("use_sim_time")
    warehouse_sqlite_path = LaunchConfiguration("warehouse_sqlite_path")

    declared_arguments = [
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz?"),
        DeclareLaunchArgument(
            "use_sim_time", default_value="false", description="Use simulation (Gazebo) clock?"
        ),
        DeclareLaunchArgument(
            "warehouse_sqlite_path",
            default_value=os.path.expanduser("~/.ros/warehouse_ros.sqlite"),
            description="Where RViz stores saved poses / scenes.",
        ),
    ]

    # Loads config/ur7e_robotiq.srdf, kinematics.yaml, joint_limits.yaml,
    # moveit_controllers.yaml and the *_planning.yaml pipelines from this package.
    moveit_config = MoveItConfigsBuilder(
        "ur7e_robotiq", package_name="ur7e_robotiq_moveit_config"
    ).to_moveit_configs()

    warehouse_ros_config = {
        "warehouse_plugin": "warehouse_ros_sqlite::DatabaseConnection",
        "warehouse_host": warehouse_sqlite_path,
    }

    # Wait until the driver has published /robot_description before starting MoveIt.
    wait_robot_description = Node(
        package="ur_robot_driver",
        executable="wait_for_robot_description",
        output="screen",
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            warehouse_ros_config,
            {"use_sim_time": use_sim_time, "publish_robot_description_semantic": True},
        ],
    )

    rviz_node = Node(
        package="rviz2",
        condition=IfCondition(launch_rviz),
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        arguments=[
            "-d",
            PathJoinSubstitution(
                [FindPackageShare("ur7e_robotiq_moveit_config"), "config", "moveit.rviz"]
            ),
        ],
        parameters=[
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            warehouse_ros_config,
            {"use_sim_time": use_sim_time},
        ],
    )

    return LaunchDescription(
        declared_arguments
        + [
            wait_robot_description,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=wait_robot_description,
                    on_exit=[move_group_node, rviz_node],
                )
            ),
        ]
    )
