cmake_minimum_required(VERSION 3.16)
project(ur7e_robotiq_control)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch urdf DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/gripper_bringup.py scripts/check_gripper_comm.py DESTINATION lib/${PROJECT_NAME})

ament_package()
