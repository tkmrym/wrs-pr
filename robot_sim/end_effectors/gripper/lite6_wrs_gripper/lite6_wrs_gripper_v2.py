"""
The simulation for the WRS gripper designed by Wan sensei
Author: Chen Hao (chen960216@gmail.com), 20220924, osaka
Reference: The code is implemented referring to the 'robot_sim/end_effectors/yumi_gripper/'
"""
import os
import math
import numpy as np
import modeling.model_collection as mc
import modeling.collision_model as cm
from panda3d.core import CollisionNode, CollisionBox, Point3
import robot_sim._kinematics.jlchain as jl
import basis.robot_math as rm
import robot_sim.end_effectors.gripper.gripper_interface as gp


class Lite6WRSGripper2(gp.GripperInterface):

    def __init__(self, pos=np.zeros(3), rotmat=np.eye(3), cdmesh_type='convex_hull', name='lite6_wrs_gripper2',
                 enable_cc=True):
        super().__init__(pos=pos, rotmat=rotmat, cdmesh_type=cdmesh_type, name=name)
        this_dir, this_filename = os.path.split(__file__)
        cpl_end_pos = self.coupling.jnts[-1]['gl_posq']
        cpl_end_rotmat = self.coupling.jnts[-1]['gl_rotmatq']
        # gripper base
        self.body = jl.JLChain(pos=cpl_end_pos, rotmat=cpl_end_rotmat, home_conf=np.zeros(1), name='base')
        self.body.jnts[1]['pos_in_loc_tcp'] = np.array([0, 0, 0])
        self.body.lnks[0]['name'] = "base"
        self.body.lnks[0]['pos_in_loc_tcp'] = np.zeros(3)
        self.body.lnks[0]['collision_model'] = cm.CollisionModel(os.path.join(this_dir, "meshes", "base_v2.stl"),
                                                                 expand_radius=.001)
        self.body.lnks[0]['rgba'] = [.57, .57, .57, 1]

        self.body.lnks[1]['name'] = "realsense_dual"
        self.body.lnks[1]['pos_in_loc_tcp'] = np.zeros(3)
        self.body.lnks[1]['collision_model'] = cm.CollisionModel(os.path.join(this_dir, "meshes", "dual_realsense.stl"),
                                                                 expand_radius=.001)
        self.body.lnks[1]['rgba'] = [.37, .37, .37, 1]

        # lft finger
        self.lft = jl.JLChain(pos=cpl_end_pos, rotmat=cpl_end_rotmat, home_conf=np.zeros(1), name='lft_finger')
        self.lft.jnts[1]['pos_in_loc_tcp'] = np.array([0.01492498, 0.005, .05])
        self.lft.jnts[1]['gl_rotmat'] = rm.rotmat_from_euler(0, 0, -math.pi)
        self.lft.jnts[1]['end_type'] = 'prismatic'
        self.lft.jnts[1]['motion_rng'] = [.0, .025]
        self.lft.jnts[1]['loc_motionax'] = np.array([0, -1, 0])
        self.lft.lnks[1]['name'] = "finger1"
        self.lft.lnks[1]['mesh_file'] = cm.CollisionModel(
            os.path.join(this_dir, "meshes", "finger_v2.stl"), cdp_type="user_defined",
            userdef_cdp_fn=self._finger_cdnp, expand_radius=.001)
        self.lft.lnks[1]['rgba'] = [.65, .65, .65, 1]
        # rgt finger
        self.rgt = jl.JLChain(pos=cpl_end_pos, rotmat=cpl_end_rotmat, home_conf=np.zeros(1), name='rgt_finger')
        self.rgt.jnts[1]['pos_in_loc_tcp'] = np.array([-0.01492498, -0.005, .05])
        # self.rgt.joints[1]['gl_rotmat'] = rm.rotmat_from_euler(0, 0, math.pi / 2)
        self.rgt.jnts[1]['end_type'] = 'prismatic'
        self.rgt.jnts[1]['loc_motionax'] = np.array([0, -1, 0])
        self.rgt.lnks[1]['name'] = "finger2"
        self.rgt.lnks[1]['mesh_file'] = cm.CollisionModel(
            os.path.join(this_dir, "meshes", "finger_v2.stl"), cdp_type="user_defined",
            userdef_cdp_fn=self._finger_cdnp, expand_radius=.001)
        self.rgt.lnks[1]['rgba'] = [.65, .65, .65, 1]
        # # reinitialize
        self.body.finalize(cdmesh_type=cdmesh_type)
        self.lft.finalize(cdmesh_type=cdmesh_type)
        self.rgt.finalize(cdmesh_type=cdmesh_type)
        # jaw range
        self.jaw_range = [0.0, .04]
        # jaw center
        self.jaw_center_pos = np.array([0, 0, .175])
        # collision detection
        self.all_cdelements = []
        self.enable_cc(toggle_cdprimit=enable_cc)

    @staticmethod
    def _finger_cdnp(name, radius):
        collision_node = CollisionNode(name)
        collision_primitive_c0 = CollisionBox(Point3(.015, .01, .078),
                                              x=.005 + radius, y=.005 + radius, z=.055 + radius)
        collision_node.addSolid(collision_primitive_c0)
        return collision_node

    def enable_cc(self, toggle_cdprimit):
        if toggle_cdprimit:
            super().enable_cc()
            # cdprimit
            self.cc.add_cdlnks(self.body, [0, 1])
            self.cc.add_cdlnks(self.lft, [1])
            self.cc.add_cdlnks(self.rgt, [1])
            activelist = [self.body.lnks[0],
                          self.body.lnks[1],
                          self.lft.lnks[1],
                          self.rgt.lnks[1]]
            self.cc.set_active_cdlnks(activelist)
            self.all_cdelements = self.cc.cce_dict
        else:
            self.all_cdelements = [self.body.lnks[0],
                                   self.body.lnks[1],
                                   self.lft.lnks[1],
                                   self.rgt.lnks[1]]
        # cdmesh
        for cdelement in self.all_cdelements:
            cdmesh = cdelement['collision_model'].copy()
            self.cdmesh_collection.add_cm(cdmesh)

    def fix_to(self, pos, rotmat):
        self.pos = pos
        self.rotmat = rotmat
        self.coupling.fix_to(self.pos, self.rotmat)
        cpl_end_pos = self.coupling.jnts[-1]['gl_posq']
        cpl_end_rotmat = self.coupling.jnts[-1]['gl_rotmatq']
        self.body.fix_to(cpl_end_pos, cpl_end_rotmat)
        self.lft.fix_to(cpl_end_pos, cpl_end_rotmat)
        self.rgt.fix_to(cpl_end_pos, cpl_end_rotmat)

    def fk(self, motion_val):
        """
        lft_outer is the only active joint, all others mimic this one
        :param: motion_val, meter or radian
        """
        if self.lft.jnts[1]['motion_rng'][0] <= -motion_val <= self.lft.jnts[1]['motion_rng'][1]:
            self.lft.jnts[1]['motion_val'] = motion_val
            self.rgt.jnts[1]['motion_val'] = self.lft.jnts[1]['motion_val']
            self.lft.fk()
            self.rgt.fk()
        else:
            raise ValueError("The motion_val parameter is out of range!")

    def change_jaw_width(self, jaw_width):
        if jaw_width > self.jaw_range[1]:
            raise ValueError("The jaw_width parameter is out of range!")
        self.fk(motion_val=-jaw_width / 2.0)

    def get_jaw_width(self):
        return -self.lft.jnts[1]['motion_val'] * 2

    def gen_stickmodel(self,
                       tcp_jnt_id=None,
                       tcp_loc_pos=None,
                       tcp_loc_rotmat=None,
                       toggle_tcpcs=False,
                       toggle_jntscs=False,
                       toggle_connjnt=False,
                       name='lite6wrs_gripper_stickmodel'):
        stickmodel = mc.ModelCollection(name=name)
        self.coupling.gen_stickmodel(tcp_loc_pos=None,
                                     tcp_loc_rotmat=None,
                                     toggle_tcpcs=False,
                                     toggle_jntscs=toggle_jntscs).attach_to(stickmodel)
        self.body.gen_stickmodel(tcp_jnt_id=tcp_jnt_id,
                                 tcp_loc_pos=tcp_loc_pos,
                                 tcp_loc_rotmat=tcp_loc_rotmat,
                                 toggle_tcpcs=False,
                                 toggle_jntscs=toggle_jntscs,
                                 toggle_connjnt=toggle_connjnt).attach_to(stickmodel)
        self.lft.gen_stickmodel(tcp_jnt_id=tcp_jnt_id,
                                tcp_loc_pos=tcp_loc_pos,
                                tcp_loc_rotmat=tcp_loc_rotmat,
                                toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                toggle_connjnt=toggle_connjnt).attach_to(stickmodel)
        self.rgt.gen_stickmodel(tcp_loc_pos=None,
                                tcp_loc_rotmat=None,
                                toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                toggle_connjnt=toggle_connjnt).attach_to(stickmodel)
        if toggle_tcpcs:
            jaw_center_gl_pos = self.rotmat.dot(self.jaw_center_pos) + self.pos
            jaw_center_gl_rotmat = self.rotmat.dot(self.action_center_rotmat)
            gm.gen_dashed_stick(spos=self.pos,
                                epos=jaw_center_gl_pos,
                                radius=.0062,
                                rgba=[.5, 0, 1, 1],
                                type="round").attach_to(stickmodel)
            gm.gen_myc_frame(pos=jaw_center_gl_pos, rotmat=jaw_center_gl_rotmat).attach_to(stickmodel)

        return stickmodel

    def gen_meshmodel(self,
                      tcp_jnt_id=None,
                      tcp_loc_pos=None,
                      tcp_loc_rotmat=None,
                      toggle_tcpcs=False,
                      toggle_jntscs=False,
                      rgba=None,
                      name='lite6wrs_gripper_meshmodel'):
        meshmodel = mc.ModelCollection(name=name)
        self.coupling.gen_mesh_model(tcp_loc_pos=None,
                                     tcp_loc_rotmat=None,
                                     toggle_tcpcs=False,
                                     toggle_jntscs=toggle_jntscs,
                                     rgba=rgba).attach_to(meshmodel)
        self.body.gen_mesh_model(tcp_jnt_id=tcp_jnt_id,
                                 tcp_loc_pos=tcp_loc_pos,
                                 tcp_loc_rotmat=tcp_loc_rotmat,
                                 toggle_tcpcs=False,
                                 toggle_jntscs=toggle_jntscs,
                                 rgba=rgba).attach_to(meshmodel)
        self.lft.gen_mesh_model(tcp_jnt_id=tcp_jnt_id,
                                tcp_loc_pos=tcp_loc_pos,
                                tcp_loc_rotmat=tcp_loc_rotmat,
                                toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                rgba=rgba).attach_to(meshmodel)
        self.rgt.gen_mesh_model(tcp_loc_pos=None,
                                tcp_loc_rotmat=None,
                                toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                rgba=rgba).attach_to(meshmodel)
        if toggle_tcpcs:
            jaw_center_gl_pos = self.rotmat.dot(self.jaw_center_pos) + self.pos
            jaw_center_gl_rotmat = self.rotmat.dot(self.action_center_rotmat)
            gm.gen_dashed_stick(spos=self.pos,
                                epos=jaw_center_gl_pos,
                                radius=.0062,
                                rgba=[.5, 0, 1, 1],
                                type="round").attach_to(meshmodel)
            gm.gen_myc_frame(pos=jaw_center_gl_pos, rotmat=jaw_center_gl_rotmat).attach_to(meshmodel)
        return meshmodel


if __name__ == '__main__':
    import visualization.panda.world as wd
    import modeling.geometric_model as gm
    import robot_sim.end_effectors.gripper.lite6_wrs_gripper as gp1

    base = wd.World(cam_pos=[.5, .5, .5], lookat_pos=[0, 0, 0], auto_cam_rotate=False)
    gm.gen_frame().attach_to(base)
    # mcm.CollisionModel("meshes/dual_realsense.stl", expand_radius=.001).attach_to(base)
    grpr = Lite6WRSGripper2(enable_cc=True)
    grpr.change_jaw_width(.03)
    grpr.gen_meshmodel(toggle_tcpcs=True).attach_to(base)
    # grpr.show_cdprimit()
    base.run()

    gp1_i = gp1.Lite6WRSGripper(pos=np.array([0, .1, 0]))
    gp1_i.change_jaw_width(0.03)
    gp1_i.gen_meshmodel().attach_to(base)

    base.run()
    grpr.change_jaw_width(0.03)

    grpr.show_cdprimit()

    gm.gen_sphere(np.array([.006, 0.049, .062]), radius=.002).attach_to(base)

    base.run()
