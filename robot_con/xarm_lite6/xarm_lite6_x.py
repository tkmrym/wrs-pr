"""
WRS control interface for XArm Lite 6
Author: Chen Hao (chen960216@gmail.com), 20220912, osaka
Reference: XArm Developer Manual (http://download.ufactory.cc/xarm/en/xArm%20Developer%20Manual.pdf?v=1600992000052)
           XArm Python SDK (https://github.com/xArm-Developer/xArm-Python-SDK)
"""

from typing import Optional

import numpy as np

import basis.robot_math as rm
import drivers.xarm.wrapper.xarm_api as arm
import motion.trajectory.piecewisepoly_toppra as pwp

__VERSION__ = '0.0.1'


class XArmLite6X(object):
    def __init__(self, ip: str = "192.168.1.232", reset: bool = False):
        """
        :param ip: The ip address of the robot
        """
        # examine parameters
        # assert isinstance('ip', str) and mode in ['position', 'servo']
        assert isinstance('ip', str)
        # initialization
        self._arm_x = arm.XArmAPI(port=ip)
        driver_v = self._arm_x.version_number
        # ensure the xarm driver is larger than 1.9.0 https://github.com/xArm-Developer/xArm-Python-SDK#1910
        assert driver_v >= (1, 9, 0)
        # reset error
        if self._arm_x.has_err_warn:
            err_code = self._arm_x.get_err_warn_code()[1][0]
            if err_code == 1 or err_code == 2:
                print("The Emergency Button is pushed in to stop!")
                input("Release the emergency button and press any key to continue. Press Enter to continue...")
        self._arm_x.clean_error()
        self._arm_x.motion_enable()
        if reset:
            self._arm_x.reset(wait=True)
        else:
            self._arm_x.set_state(0)
        self.ndof = 6

    @staticmethod
    def pos_unit_xarm2wrs(arr: np.ndarray) -> np.ndarray:
        """
        Convert the position in XArm API to the WRS system
        :param arr: Position array obtained from the XArm API
        :return: Converted position array
        """
        return arr / 1000

    @staticmethod
    def pos_unit_wrs2xarm(arr: np.ndarray) -> np.ndarray:
        """
        Convert the position in WRS system to the XArm API
        :param arr: Position array in the WRS system
        :return: Converted position array
        """
        return arr * 1000

    @property
    def mode(self) -> int:
        """
        xArm mode, only available in socket way and  enable_report is True
        :return:  0: position control mode
                  1: servo motion mode
                  2: joint teaching mode
                  3: cartesian teaching mode (invalid)
                  4: joint velocity control mode
                  5: cartesian velocity control mode

        """
        return self._arm_x.mode

    @property
    def state(self) -> int:
        """
        Get the state of the robot
        :return: tuple((code, state)), only when code is 0, the returned result is correct.
            code: See the [API Code Documentation](./xarm_api_code.md#api-code) for details.
            state:
                1: in motion
                2: sleeping
                3: suspended
                4: stopping
        """
        return self._arm_x.get_state()

    @property
    def cmd_num(self) -> int:
        """
        Get the cmd count in cache
        :return: tuple((code, cmd_num)), only when code is 0, the returned result is correct.
            code: See the [API Code Documentation](./xarm_api_code.md#api-code) for details.
        """
        code, cmd_num = self._arm_x.cmd_num
        self._ex_ret_code(code)
        return cmd_num

    def _ex_ret_code(self, code):
        """
        Examine the return code of the instruction. If the code is not 0 (success), a Exception will be raised.
        :param code:
        :return:
        """
        if code != 0:
            raise Exception(f"The return code {code} is incorrect. Refer API for details")

    def _position_mode(self):
        """
        Enter the position control mode
        """
        if self.mode != 0:
            self._arm_x.arm.set_mode(0)
            self._arm_x.arm.set_state(state=0)

    def _servo_mode(self):
        """
        Enter the servo motion mode
        """
        if self.mode != 1:
            self._arm_x.arm.set_mode(1)
            self._arm_x.arm.set_state(state=0)

    def reset(self):
        self._arm_x.reset()

    def homeconf(self):
        self.move_j(jnt_val=np.array([0., 0.173311, 0.555015, 0., 0.381703, 0.]), )

    def ik(self, tgt_pos: np.ndarray, tgt_rot: np.ndarray) -> np.ndarray:
        """

        :param tgt_pos: The position under WRS system
        :param tgt_rot: The 3x3 Rotation matrix or 1x3 RPY matrix
        :return: inverse kinematics solution
        """
        tgt_pos = self.pos_unit_wrs2xarm(tgt_pos).tolist()
        if tgt_rot is not None:
            if tgt_rot.shape == (3, 3):
                tgt_rpy = rm.rotmat_to_euler(tgt_rot).tolist()
            else:
                tgt_rpy = tgt_rot.flatten()[:3].tolist()
        tgt_pose = tgt_pos + tgt_rpy
        code, ik_s = self._arm_x.get_inverse_kinematics(pose=tgt_pose, input_is_radian=True, return_is_radian=True)
        self._ex_ret_code(code)
        return np.array(ik_s)

    def get_gripper_width(self):
        raise NotImplementedError

    def set_gripper_width(self):
        raise NotImplementedError

    def open_gripper(self):
        raise NotImplementedError

    def close_gripper(self):
        raise NotImplementedError

    def get_jnt_values(self) -> np.ndarray:
        """
        Get the joint values of the arm
        :return: Joint values (Array)
        """
        code, jnt_val = self._arm_x.get_servo_angle(is_radian=True)
        jnt_val = jnt_val[:self.ndof]
        self._ex_ret_code(code)
        return np.array(jnt_val)

    def get_pose(self) -> (np.ndarray, np.ndarray):
        """
        Get the cartesian position
        :return: tuple(Position(Array), Orientation(Array))
        """
        code, pose = self._arm_x.get_position(is_radian=True)
        self._ex_ret_code(code)
        return self.pos_unit_xarm2wrs(np.array(pose[:3])), rm.rotmat_from_euler(*pose[3:])

    def move_j(self, jnt_val: np.ndarray,
               speed: Optional[float] = None,
               is_rel_mov: bool = False,
               wait: bool = True) -> bool:
        """
        Move the robot to a target joint value
        :param jnt_val: Targe joint value (1x6 Array)
        :param speed: Move speed (rad/s)
        :param is_rel_mov: Relative move or not
        :param wait: whether to wait for the arm to complete, default is True
        :return: if the path is moved successfully, it will return 0
        """
        if isinstance(jnt_val, np.ndarray):
            jnt_val = jnt_val.tolist()
        assert isinstance(jnt_val, list) and len(jnt_val) == self.ndof
        self._position_mode()
        suc = self._arm_x.set_servo_angle(angle=jnt_val, speed=speed, is_radian=True,
                                          relative=is_rel_mov, wait=wait)
        if suc == 0:
            return True
        else:
            return False

    def move_p(self,
               pos: Optional[np.ndarray],
               rot: Optional[np.ndarray],
               speed: Optional[float] = None,
               path_rad: Optional[float] = None,
               is_rel_mov: bool = False,
               wait: bool = True) -> bool:
        """
        Move to a pose under the robot base coordinate
        :param pos: Position (Array([x,y,z])) of the pose
        :param rot: Orientation (Array([roll,pitch,yaw]) or Array(3x3)) of the pose
        :param speed: Move speed (mm/s, rad/s)
        :param path_rad: move radius, if radius is larger or equal than 0, will MoveArcLine, else MoveLine
        :param is_rel_mov: Relative move or not
        :return: if the path is moved successfully, it will return 0
        :param wait: whether to wait for the arm to complete, default is True
        """
        assert pos is not None or rot is not None
        assert path_rad is None or path_rad >= 0
        self._position_mode()
        if pos is not None:
            pos = self.pos_unit_wrs2xarm(pos)
        else:
            pos = [None] * 3
        if rot is not None:
            if rot.shape == (3, 3):
                rpy = rm.rotmat_to_euler(rot)
            else:
                rpy = rot.flatten()[:3]
        else:
            rpy = [None] * 3
        suc = self._arm_x.set_position(x=pos[0], y=pos[1], z=pos[2],
                                       roll=rpy[0], pitch=rpy[1], yaw=rpy[2], speed=speed,
                                       is_radian=True,
                                       relative=is_rel_mov,
                                       radius=path_rad,
                                       wait=wait)
        if suc == 0:
            return True
        else:
            return False

    def move_jntspace_path(self, path,
                           max_jntvel=None,
                           max_jntacc=None,
                           start_frame_id=1,
                           toggle_debug=False):
        """
        :param path: [jnt_values0, jnt_values1, ...], results of motion planning
        :param max_jntvel:
        :param max_jntacc:
        :param start_frame_id:
        :return:
        author: weiwei
        """
        # enter servo mode
        self._servo_mode()
        if not path or path is None:
            raise ValueError("The given is incorrect!")
        control_frequency = .005
        tpply = pwp.PiecewisePolyTOPPRA()
        interpolated_path = tpply.interpolate_by_max_spdacc(path=path,
                                                            control_frequency=control_frequency,
                                                            max_vels=max_jntvel,
                                                            max_accs=max_jntacc,
                                                            toggle_debug=toggle_debug)
        interpolated_path = interpolated_path[start_frame_id:]
        for jnt_values in interpolated_path:
            self._arm_x.set_servo_angle_j(jnt_values, is_radian=True)
        return

    def __del__(self):
        self._arm_x.disconnect()