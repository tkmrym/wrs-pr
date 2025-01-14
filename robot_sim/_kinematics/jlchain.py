import math
import os
import copy
import numpy as np
import time
import basis.constant as bc
import basis.utils as bu
import basis.robot_math as rm
import modeling.constant as mc
import modeling.collision_model as mcm
import robot_sim._kinematics.constant as rkc
import robot_sim._kinematics.jl as rkjl
import robot_sim._kinematics.ik_num as rkn
import robot_sim._kinematics.ik_opt as rko
import robot_sim._kinematics.ik_dd as rkd
import robot_sim._kinematics.ik_trac as rkt
import basis.constant as cst


class JLChain(object):
    """
    Joint Link Chain, no branches allowed
    Usage:
    1. Create a JLChain instance with a given n_dof and update its parameters for particular definition
    2. Define multiple instances of this class to compose a complicated structure
    3. Use mimic for underactuated or coupled mechanism
    """

    def __init__(self,
                 name="auto",
                 pos=np.zeros(3),
                 rotmat=np.eye(3),
                 n_dof=6,
                 cdprimitive_type=mc.CDPType.BOX,
                 cdmesh_type=mc.CDMType.DEFAULT):
        """
        conf -- configuration: target joint values
        :param name:
        :param pos:
        :param rotmat:
        :param home: number of joints
        :param cdprimitive_type:
        :param cdmesh_type:
        :param name:
        """
        self.name = name
        self.n_dof = n_dof
        self.home = np.zeros(self.n_dof)  # self.n_dof joints plus one anchor
        # initialize joints and links
        self.anchor = rkjl.Anchor(name, pos=pos, rotmat=rotmat)
        self.jnts = [rkjl.Joint(name=f"j{i}") for i in range(self.n_dof)]
        self._jnt_rngs = self._get_jnt_rngs()
        # default tcp
        self._tcp_jnt_id = self.n_dof - 1
        self.tcp_loc_pos = np.zeros(3)
        self.tcp_loc_rotmat = np.eye(3)
        # initialize
        self.go_home()
        # collision primitives
        # mesh generator
        self.cdprimitive_type = cdprimitive_type
        self.cdmesh_type = cdmesh_type
        # iksolver
        self._ik_solver = None

    @property
    def jnt_rngs(self):
        return self._jnt_rngs

    @property
    def tcp_jnt_id(self):
        return self._tcp_jnt_id

    @tcp_jnt_id.setter
    def tcp_jnt_id(self, value):
        self._tcp_jnt_id = value

    @property
    def tcp_loc_homomat(self):
        return rm.homomat_from_posrot(pos=self.tcp_loc_pos, rotmat=self.tcp_loc_rotmat)

    @property
    def pos(self):
        return self.anchor.pos

    @property
    def rotmat(self):
        return self.anchor.rotmat

    def _get_jnt_rngs(self):
        """
        get jnt ranges
        :return: [[jnt1min, jnt1max], [jnt2min, jnt2max], ...]
        date: 20180602, 20200704osaka
        author: weiwei
        """
        jnt_limits = []
        for i in range(self.n_dof):
            jnt_limits.append(self.jnts[i].motion_rng)
        return np.asarray(jnt_limits)

    def forward_kinematics(self, jnt_vals, toggle_jac=True, update=False):
        """
        This function will update the global parameters
        :param jnt_vals: a 1xn ndarray where each element indicates the value of a joint (in radian or meter)
        :param update if True, update internal values
        :return: True (succ), False (failure)
        author: weiwei
        date: 20161202, 20201009osaka, 20230823
        """
        if not update:
            homomat = self.anchor.homomat
            jnt_pos = np.zeros((self.n_dof, 3))
            jnt_motion_ax = np.zeros((self.n_dof, 3))
            for i in range(self.tcp_jnt_id + 1):
                jnt_motion_ax[i, :] = homomat[:3, :3] @ self.jnts[i].loc_motion_ax
                if self.jnts[i].type == rkc.JntType.REVOLUTE:
                    jnt_pos[i, :] = homomat[:3, 3] + homomat[:3, :3] @ self.jnts[i].loc_pos
                homomat = homomat @ self.jnts[i].get_motion_homomat(motion_val=jnt_vals[i])
            tcp_gl_homomat = homomat @ self.tcp_loc_homomat
            tcp_gl_pos = tcp_gl_homomat[:3, 3]
            tcp_gl_rotmat = tcp_gl_homomat[:3, :3]
            if toggle_jac:
                j_mat = np.zeros((6, self.n_dof))
                for i in range(self.tcp_jnt_id + 1):
                    if self.jnts[i].type == rkc.JntType.REVOLUTE:
                        vec_jnt2tcp = tcp_gl_pos - jnt_pos[i, :]
                        j_mat[:3, i] = np.cross(jnt_motion_ax[i, :], vec_jnt2tcp)
                        j_mat[3:6, i] = jnt_motion_ax[i, :]
                    if self.jnts[i].type == rkc.JntType.PRISMATIC:
                        j_mat[:3, i] = jnt_motion_ax[i, :]
                return tcp_gl_pos, tcp_gl_rotmat, j_mat
            else:
                return tcp_gl_pos, tcp_gl_rotmat
        else:
            pos = self.anchor.pos
            rotmat = self.anchor.rotmat
            for i in range(self.n_dof):
                motion_value = jnt_vals[i]
                self.jnts[i].update_globals(pos=pos, rotmat=rotmat, motion_val=motion_value)
                pos = self.jnts[i].gl_pos_q
                rotmat = self.jnts[i].gl_rotmat_q
            tcp_gl_pos, tcp_gl_rotmat = self.cvt_tcp_loc_to_gl()
            if toggle_jac:
                j_mat = np.zeros((6, self.n_dof))
                for i in range(self.tcp_jnt_id + 1):
                    if self.jnts[i].type == rkc.JntType.REVOLUTE:
                        vec_jnt2tcp = tcp_gl_pos - self.jnts[i].gl_pos_q
                        j_mat[:3, i] = np.cross(self.jnts[i].gl_motion_ax, vec_jnt2tcp)
                        j_mat[3:6, i] = self.jnts[i].gl_motion_ax
                    if self.jnts[i].type == rkc.JntType.PRISMATIC:
                        j_mat[:3, i] = self.jnts[i].gl_motion_ax
                return tcp_gl_pos, tcp_gl_rotmat, j_mat
            else:
                return tcp_gl_pos, tcp_gl_rotmat

    def jacobian(self, joint_values=None):
        """
        compute the jacobian matrix; use internal values if jnt_vals is None
        :param joint_values:
        :param update:
        :return:
        author :weiwei
        date: 20230829
        """
        if joint_values is None:  # use internal, ignore update
            _, _, j_mat = self.forward_kinematics(jnt_vals=self.get_joint_values(),
                                                  toggle_jac=True,
                                                  update=False)
        else:
            _, _, j_mat = self.forward_kinematics(jnt_vals=joint_values,
                                                  toggle_jac=True,
                                                  update=False)
        return j_mat

    def manipulability_val(self, joint_values=None):
        """
        compute the yoshikawa manipulability
        :param tcp_joint_id:
        :param tcp_loc_pos:
        :param tcp_loc_rotmat:
        :return:
        author: weiwei
        date: 20200331
        """
        j_mat = self.jacobian(joint_values=joint_values)
        return np.sqrt(np.linalg.det(j_mat @ j_mat.T))

    def manipulability_mat(self, joint_values=None):
        """
        compute the axes of the manipulability ellipsoid
        :param tcp_joint_id:
        :param tcp_loc_pos:
        :param tcp_loc_rotmat:
        :return: (linear ellipsoid matrix, angular ellipsoid matrix)
        """
        j_mat = self.jacobian(joint_values=joint_values)
        # linear ellipsoid
        linear_j_dot_jt = j_mat[:3, :] @ j_mat[:3, :].T
        eig_values, eig_vecs = np.linalg.eig(linear_j_dot_jt)
        linear_ellipsoid_mat = np.eye(3)
        linear_ellipsoid_mat[:, 0] = np.sqrt(eig_values[0]) * eig_vecs[:, 0]
        linear_ellipsoid_mat[:, 1] = np.sqrt(eig_values[1]) * eig_vecs[:, 1]
        linear_ellipsoid_mat[:, 2] = np.sqrt(eig_values[2]) * eig_vecs[:, 2]
        # angular ellipsoid
        angular_j_dot_jt = j_mat[3:, :] @ j_mat[3:, :].T
        eig_values, eig_vecs = np.linalg.eig(angular_j_dot_jt)
        angular_ellipsoid_mat = np.eye(3)
        angular_ellipsoid_mat[:, 0] = np.sqrt(eig_values[0]) * eig_vecs[:, 0]
        angular_ellipsoid_mat[:, 1] = np.sqrt(eig_values[1]) * eig_vecs[:, 1]
        angular_ellipsoid_mat[:, 2] = np.sqrt(eig_values[2]) * eig_vecs[:, 2]
        return (linear_ellipsoid_mat, angular_ellipsoid_mat)

    def fix_to(self, pos, rotmat):
        self.anchor.update_pose(pos, rotmat)
        return self.go_given_conf(jnt_vals=self.get_joint_values())

    def finalize(self, ik_solver=None, **kwargs):
        """
        ddik is both fast and has high success rate, but it required prebuilding a data file.
        tracik is also fast and reliable, but it is a bit slower and energe-intensive.
        pinv_wc is fast but has low success rate. it is used as a backbone for ddik.
        sqpss has high success rate but is very slow.
        :param ik_solver: 'd' for ddik; 'n' for numik.pinv_wc; 'o' for optik.sqpss; 't' for tracik; default: None
        :**kwargs: path for DDIKSolver
        :return:
        author: weiwei
        date: 20201126, 20231111
        """
        self._jnt_rngs = self._get_jnt_rngs()
        self.go_home()
        if ik_solver == 'd':
            path = kwargs.get('path', os.getcwd())
            self._ik_solver = rkd.DDIKSolver(self, path)

    def set_tcp(self, tcp_joint_id=None, tcp_loc_pos=None, tcp_loc_rotmat=None):
        if tcp_joint_id is not None:
            self.tcp_jnt_id = tcp_joint_id
        if tcp_loc_pos is not None:
            self.tcp_loc_pos = tcp_loc_pos
        if tcp_loc_rotmat is not None:
            self.tcp_loc_rotmat = tcp_loc_rotmat

    def get_gl_tcp(self):
        tcp_gl_pos, tcp_gl_rotmat = self.cvt_tcp_loc_to_gl()
        return tcp_gl_pos, tcp_gl_rotmat

    def cvt_tcp_loc_to_gl(self):
        if self.n_dof >= 1:
            gl_pos = self.jnts[self.tcp_jnt_id].gl_pos_q + self.jnts[self.tcp_jnt_id].gl_rotmat_q @ self.tcp_loc_pos
            gl_rotmat = self.jnts[self.tcp_jnt_id].gl_rotmat_q @ self.tcp_loc_rotmat
        else:
            gl_pos = self.anchor.pos + self.anchor.rotmat @ self.tcp_loc_pos
            gl_rotmat = self.anchor.rotmat @ self.tcp_loc_rotmat
        return (gl_pos, gl_rotmat)

    def cvt_posrot_in_tcp_to_gl(self,
                                pos_in_loc_tcp=np.zeros(3),
                                rotmat_in_loc_tcp=np.eye(3)):
        """
        given a loc pos and rotmat in loc_tcp, convert it to global frame
        if the last three parameters are given, the code will use them as loc_tcp instead of the internal member vars.
        :param pos_in_loc_tcp: nparray 1x3
        :param rotmat_in_loc_tcp: nparray 3x3
        :param
        :return:
        author: weiwei
        date: 20190312, 20210609
        """
        tcp_gl_pos, tcp_gl_rotmat = self.cvt_tcp_loc_to_gl()
        cvted_gl_pos = tcp_gl_pos + tcp_gl_rotmat.dot(pos_in_loc_tcp)
        cvted_gl_rotmat = tcp_gl_rotmat.dot(rotmat_in_loc_tcp)
        return (cvted_gl_pos, cvted_gl_rotmat)

    def cvt_gl_posrot_to_tcp(self, gl_pos, gl_rotmat):
        """
        given a world pos and world rotmat
        get the relative pos and relative rotmat with respective to the ith jntlnk
        :param gl_pos: 1x3 nparray
        :param gl_rotmat: 3x3 nparray
        :return:
        author: weiwei
        date: 20190312
        """
        tcp_gl_pos, tcp_gl_rotmat = self.cvt_tcp_loc_to_gl()
        return rm.rel_pose(tcp_gl_pos, tcp_gl_rotmat, gl_pos, gl_rotmat)

    def are_joint_values_in_ranges(self, joint_values):
        """
        check if the given jnt_vals
        :param joint_values:
        :return:
        author: weiwei
        date: 20220326toyonaka
        """
        if len(joint_values) == self.n_dof:
            raise ValueError('The given joint values do not match n_dof')
        joint_values = np.asarray(joint_values)
        if np.any(joint_values < self.jnt_rngs[:, 0]) or np.any(joint_values > self.jnt_rngs[:, 1]):
            return False
        else:
            return True

    def go_given_conf(self, jnt_vals):
        """
        move the robot_s to the given pose
        :return: null
        author: weiwei
        date: 20230927osaka
        """
        return self.forward_kinematics(jnt_vals=jnt_vals, toggle_jac=False, update=True)

    def go_home(self):
        """
        move the robot_s to initial pose
        :return: null
        author: weiwei
        date: 20161211osaka
        """
        return self.go_given_conf(jnt_vals=self.home)

    def go_zero(self):
        """
        move the robot_s to initial pose
        :return: null
        author: weiwei
        date: 20161211osaka
        """
        return self.go_given_conf(jnt_vals=np.zeros(self.n_dof))

    def get_joint_values(self):
        """
        get the current joint values
        :return: jnt_vals: a 1xn ndarray
        author: weiwei
        date: 20161205tsukuba
        """
        jnt_values = np.zeros(self.n_dof)
        for i in range(self.n_dof):
            jnt_values[i] = self.jnts[i].motion_val
        return jnt_values

    def rand_conf(self):
        """
        generate a random configuration
        author: weiwei
        date: 20200326
        """
        return np.random.rand(self.n_dof) * (self.jnt_rngs[:, 1] - self.jnt_rngs[:, 0]) + self.jnt_rngs[:, 0]

    def ik(self,
           tgt_pos: np.ndarray,
           tgt_rotmat: np.ndarray,
           seed_jnt_vals=None,
           toggle_dbg=False):
        """
        trac ik solver runs num_ik and opt_ik in parallel, and return the faster result
        :param tgt_pos: 1x3 nparray, single value or list
        :param tgt_rotmat: 3x3 nparray, single value or list
        :param seed_jnt_vals: the starting configuration used in the numerical iteration
        :return:
        """
        if self._ik_solver is None:
            raise Exception("IK solver undefined. Use JLChain.finalize to define it.")
        jnt_values = self._ik_solver.ik(tgt_pos=tgt_pos,
                                        tgt_rotmat=tgt_rotmat,
                                        seed_jnt_vals=seed_jnt_vals,
                                        toggle_dbg=toggle_dbg)
        return jnt_values

    def copy(self):
        return copy.deepcopy(self)


if __name__ == "__main__":
    import time
    import pickle
    from tqdm import tqdm
    import visualization.panda.world as wd
    import robot_sim._kinematics.model_generator as rkmg
    import robot_sim._kinematics.constant as rkc
    import modeling.geometric_model as gm

    base = wd.World(cam_pos=[1.25, .75, .75], lookat_pos=[0, 0, .3])
    gm.gen_frame().attach_to(base)

    jlc = JLChain(n_dof=6)
    jlc.jnts[0].loc_pos = np.array([0, 0, 0])
    jlc.jnts[0].loc_motion_ax = np.array([0, 0, 1])
    jlc.jnts[0].motion_rng = np.array([-np.pi / 2, np.pi / 2])
    # jlc.jnts[1].change_type(rkc.JntType.PRISMATIC)
    jlc.jnts[1].loc_pos = np.array([0, 0, .05])
    jlc.jnts[1].loc_motion_ax = np.array([0, 1, 0])
    jlc.jnts[1].motion_rng = np.array([-np.pi / 2, np.pi / 2])
    jlc.jnts[2].loc_pos = np.array([0, 0, .2])
    jlc.jnts[2].loc_motion_ax = np.array([0, 1, 0])
    jlc.jnts[2].motion_rng = np.array([-np.pi, np.pi])
    jlc.jnts[3].loc_pos = np.array([0, 0, .2])
    jlc.jnts[3].loc_motion_ax = np.array([0, 0, 1])
    jlc.jnts[3].motion_rng = np.array([-np.pi / 2, np.pi / 2])
    jlc.jnts[4].loc_pos = np.array([0, 0, .1])
    jlc.jnts[4].loc_motion_ax = np.array([0, 1, 0])
    jlc.jnts[4].motion_rng = np.array([-np.pi / 2, np.pi / 2])
    jlc.jnts[5].loc_pos = np.array([0, 0, .05])
    jlc.jnts[5].loc_motion_ax = np.array([0, 0, 1])
    jlc.jnts[5].motion_rng = np.array([-np.pi / 2, np.pi / 2])
    jlc.tcp_loc_pos = np.array([0, 0, .01])
    jlc.finalize()
    # rkmg.gen_jlc_stick(jlc, stick_rgba=bc.navy_blue, tgl_tcp_frame=True,
    #                    toggle_joint_frame=True).attach_to(base)
    seed_jnt_vals = jlc.get_joint_values()

    success = 0
    num_win = 0
    opt_win = 0
    time_list = []
    tgt_list = []
    for i in tqdm(range(100), desc="ik"):
        random_jnts = jlc.rand_conf()
        tgt_pos, tgt_rotmat = jlc.forward_kinematics(jnt_vals=random_jnts, update=False, toggle_jac=False)
        tic = time.time()
        joint_values_with_dbg_info = jlc.ik(tgt_pos=tgt_pos,
                                            tgt_rotmat=tgt_rotmat,
                                            toggle_dbg=True)
        toc = time.time()
        time_list.append(toc - tic)
        print(time_list[-1])
        if joint_values_with_dbg_info is not None:
            success += 1
            if joint_values_with_dbg_info[0] == 'o':
                opt_win += 1
            elif joint_values_with_dbg_info[0] == 'n':
                num_win += 1
                # mgm.gen_frame(pos=tgt_pos, rotmat=tgt_rotmat).attach_to(base)
                # jlc.forward_kinematics(jnt_vals=joint_values_with_dbg_info[1], update=True, toggle_jac=False)
                # rkmg.gen_jlc_stick(jlc, stick_rgba=bc.navy_blue, tgl_tcp_frame=True,
                #        toggle_joint_frame=True).attach_to(base)
                # base.run()
        else:
            tgt_list.append((tgt_pos, tgt_rotmat))
    print(success)
    print(f'num_win: {num_win}, opt_win: {opt_win}')
    print('average', np.mean(time_list))
    print('max', np.max(time_list))
    print('min', np.min(time_list))
    base.run()
