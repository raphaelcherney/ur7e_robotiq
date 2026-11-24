# UR7e + Robotiq 2F-85 (ROS 2 Lyrical)

ROS 2 packages for our UR7e arm with a Robotiq 2F-85 gripper, including a MoveIt demo.
The layout follows Universal Robots' official
[`my_robot_cell` tutorial](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_tutorials/my_robot_cell/doc/index.html),
so the UR documentation applies directly.

| Package | What it contains |
| --- | --- |
| `ur7e_robotiq_description` | URDF of arm + coupling + gripper (no control) and a model viewer |
| `ur7e_robotiq_control` | Starts the robot with ros2_control: real arm, or mock (simulated) hardware |
| `ur7e_robotiq_moveit_config` | MoveIt config (planning groups, poses, controllers) and launch files |

Everything else (UR driver, UR description, Robotiq description, MoveIt) is installed from apt.

## One-time setup

```bash
mkdir -p ~/ws/ur/src && cd ~/ws/ur/src
# put this folder here (git clone ... ur7e_robotiq)
cd ~/ws/ur
source /opt/ros/lyrical/setup.bash
rosdep install --from-paths src --ignore-src -y   # installs any missing apt packages
colcon build --symlink-install
```

**In every new terminal** (or `Package '...' not found` errors appear):

```bash
source ~/ws/ur/install/setup.bash
```

To do this automatically, add it to your `~/.bashrc` after the `/opt/ros/lyrical/setup.bash` line:

```bash
echo "source ~/ws/ur/install/setup.bash" >> ~/.bashrc
```

## MoveIt demo (no robot needed)

```bash
ros2 launch ur7e_robotiq_moveit_config demo.launch.py
```

In RViz's **MotionPlanning** panel:

- **Planning Group `ur_manipulator`**: drag the interactive marker (it sits at the gripper TCP,
  between the fingers), or pick a goal like `home` / `up` / `test_configuration`, then **Plan & Execute**.
- **Planning Group `gripper`**: pick goal state `open` or `close`, then **Plan & Execute**.

## Real robot

1. On the teach pendant, install and set up the **External Control** URCap (see the
   [UR driver docs](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_robot_driver/ur_robot_driver/doc/installation/robot_setup.html)).
2. Terminal 1 (driver):
   ```bash
   ros2 launch ur7e_robotiq_control start_robot.launch.py robot_ip:=<ROBOT_IP> \
     kinematics_params_file:=<path/to/this_robots_calibration.yaml>
   ```
   Then run the External Control program on the pendant.
3. Terminal 2 (MoveIt):
   ```bash
   ros2 launch ur7e_robotiq_moveit_config moveit.launch.py
   ```

Each arm has its own factory calibration. Extract it once per robot with `ur_calibration`
(see the UR driver docs) and pass it as `kinematics_params_file`.

> **Gripper on the real robot:** this setup does not yet control the real gripper from ROS.
> On hardware the gripper appears in the model but its fingers aren't driven. Use the
> Robotiq URCap on the pendant for now.

## Other useful commands

```bash
# Just look at the model, with joint sliders
ros2 launch ur7e_robotiq_description view_robot.launch.py

# Robot without MoveIt (simulated), e.g. to test your own controller code
ros2 launch ur7e_robotiq_control start_robot.launch.py use_mock_hardware:=true

# Command the gripper directly (0.0 = open, 0.79 = closed)
ros2 action send_goal /robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/ParallelGripperCommand \
  "{command: {name: [robotiq_85_left_knuckle_joint], position: [0.79]}}"
```

## Where things are

- Gripper TCP offset: `ur7e_robotiq_description/urdf/ur7e_robotiq_macro.xacro` (`gripper_tcp_joint`)
- Named poses, planning groups, collision matrix: `ur7e_robotiq_moveit_config/config/ur7e_robotiq.srdf`
- Gripper controller settings: `ur7e_robotiq_control/config/robotiq_controllers.yaml`
- Arm controllers: ur_robot_driver's own `config/ur_controllers.yaml` (used unchanged)
