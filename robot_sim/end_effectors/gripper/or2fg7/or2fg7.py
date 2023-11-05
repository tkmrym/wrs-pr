import os
import numpy as np
import modeling.model_collection as mc
import robot_sim.kinematics.jlchain as jl
import basis.robot_math as rm
import robot_sim.end_effectors.gripper.gripper_interface as gp
import modeling.geometric_model as gm
import modeling.collision_model as cm


class OR2FG7(gp.GripperInterface):

    def __init__(self,
                 pos=np.zeros(3),
                 rotmat=np.eye(3),
                 coupling_offset_pos=np.zeros(3),
                 coupling_offset_rotmat=np.eye(3),
                 cdmesh_type='box',
                 name='or2fg7',
                 enable_cc=True):
        super().__init__(pos=pos, rotmat=rotmat, cdmesh_type=cdmesh_type, name=name)
        this_dir, this_filename = os.path.split(__file__)
        self.coupling.joints[-1]['pos_in_loc_tcp'] = coupling_offset_pos
        self.coupling.joints[-1]['gl_rotmat'] = coupling_offset_rotmat
        self.coupling.lnks[0]['rgba'] = np.array([.35, .35, .35, 1])
        self.coupling.lnks[0]['collision_model'] = cm.gen_stick(self.coupling.joints[0]['pos_in_loc_tcp'],
                                                                self.coupling.joints[-1]['pos_in_loc_tcp'],
                                                                radius=0.07,
                                                                # rgba=[.2, .2, .2, 1], rgb will be overwritten
                                                                type='rect',
                                                                n_sec=36)
        self.coupling.reinitialize()
        cpl_end_pos = self.coupling.joints[-1]['gl_posq']
        cpl_end_rotmat = self.coupling.joints[-1]['gl_rotmatq']
        # - lft
        self.lft = jl.JLChain(pos=cpl_end_pos, rotmat=cpl_end_rotmat, home_conf=np.zeros(1), name='base_lft_finger')
        # self.lft.joints[1]['pos_in_loc_tcp'] = np.array([0.032239, -0.029494, 0.12005])
        self.lft.joints[1]['pos_in_loc_tcp'] = np.zeros(3)
        self.lft.joints[1]['end_type'] = 'prismatic'
        self.lft.joints[1]['motion_rng'] = [0, .019]
        self.lft.joints[1]['loc_motionax'] = np.array([-1, 0, 0])
        self.lft.lnks[0]['name'] = "base"
        self.lft.lnks[0]['pos_in_loc_tcp'] = np.zeros(3)
        self.lft.lnks[0]['mesh_file'] = os.path.join(this_dir, "meshes", "base_link.stl")
        self.lft.lnks[0]['rgba'] = [.5, .5, .5, 1]
        self.lft.lnks[1]['name'] = "left_finger"
        self.lft.lnks[1]['mesh_file'] = os.path.join(this_dir, "meshes", "inward_left_finger_link.stl")
        self.lft.lnks[1]['rgba'] = [.7, .7, .7, 1]
        # - rgt
        self.rgt = jl.JLChain(pos=cpl_end_pos, rotmat=cpl_end_rotmat, home_conf=np.zeros(1), name='rgt_finger')
        # self.rgt.joints[1]['pos_in_loc_tcp'] = np.array([-0.054361, -0.029494, 0.12005])
        self.rgt.joints[1]['pos_in_loc_tcp'] = np.zeros(3)
        self.rgt.joints[1]['end_type'] = 'prismatic'
        self.rgt.joints[1]['loc_motionax'] = np.array([1, 0, 0])
        self.rgt.lnks[1]['name'] = "right_finger"
        self.rgt.lnks[1]['mesh_file'] = os.path.join(this_dir, "meshes", "inward_right_finger_link.stl")
        self.rgt.lnks[1]['rgba'] = [.7, .7, .7, 1]
        # jaw center
        self.jaw_center_pos = np.array([0, 0, .15]) + coupling_offset_pos
        # jaw range
        self.jaw_range = [0.0, 0.038]
        # reinitialize
        self.lft.reinitialize()
        self.rgt.reinitialize()
        # collision detection
        self.all_cdelements = []
        self.enable_cc(toggle_cdprimit=enable_cc)

    def enable_cc(self, toggle_cdprimit):
        if toggle_cdprimit:
            super().enable_cc()
            # cdprimit
            self.cc.add_cdlnks(self.lft, [0, 1])
            self.cc.add_cdlnks(self.rgt, [1])
            activelist = [self.lft.lnks[0],
                          self.lft.lnks[1],
                          self.rgt.lnks[1]]
            self.cc.set_active_cdlnks(activelist)
            self.all_cdelements = self.cc.all_cd_elements
        # cdmesh
        for cdelement in self.all_cdelements:
            cdmesh = cdelement['collision_model'].copy()
            self.cdmesh_collection.add_cm(cdmesh)

    def fix_to(self, pos, rotmat, jawwidth=None):
        self.pos = pos
        self.rotmat = rotmat
        if jawwidth is not None:
            side_jawwidth = (self.jaw_range[1] - jawwidth) / 2.0
            if 0 <= side_jawwidth <= self.jaw_range[1]/2.0:
                self.lft.joints[1]['motion_val'] = side_jawwidth;
                self.rgt.joints[1]['motion_val'] = self.lft.joints[1]['motion_val']  # right mimic left
            else:
                raise ValueError("The angle parameter is out of range!")
        self.coupling.fix_to(self.pos, self.rotmat)
        cpl_end_pos = self.coupling.joints[-1]['gl_posq']
        cpl_end_rotmat = self.coupling.joints[-1]['gl_rotmatq']
        self.lft.fix_to(cpl_end_pos, cpl_end_rotmat)
        self.rgt.fix_to(cpl_end_pos, cpl_end_rotmat)

    def fk(self, motion_val):
        """
        lft_outer is the only active joint, all others mimic this one
        :param: angle, radian
        """
        if self.lft.joints[1]['motion_rng'][0] <= motion_val <= self.lft.joints[1]['motion_rng'][1]:
            self.lft.joints[1]['motion_val'] = motion_val
            self.rgt.joints[1]['motion_val'] = self.lft.joints[1]['motion_val']  # right mimic left
            self.lft.fk()
            self.rgt.fk()
        else:
            raise ValueError("The motion_val parameter is out of range!")

    def jaw_to(self, jaw_width):
        if jaw_width > self.jaw_range[1]:
            raise ValueError("The jawwidth parameter is out of range!")
        self.fk(motion_val=(self.jaw_range[1] - jaw_width) / 2.0)

    def gen_stickmodel(self,
                       tcp_jntid=None,
                       tcp_loc_pos=None,
                       tcp_loc_rotmat=None,
                       toggle_tcpcs=False,
                       toggle_jntscs=False,
                       toggle_connjnt=False,
                       name='or2fg7_stick_model'):
        stickmodel = mc.ModelCollection(name=name)
        self.coupling.gen_stickmodel(toggle_tcpcs=False,
                                     toggle_jntscs=toggle_jntscs).attach_to(stickmodel)
        self.lft.gen_stickmodel(toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                toggle_connjnt=toggle_connjnt).attach_to(stickmodel)
        self.rgt.gen_stickmodel(toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                toggle_connjnt=toggle_connjnt).attach_to(stickmodel)
        if toggle_tcpcs:
            jaw_center_gl_pos = self.rotmat.dot(self.jaw_center_pos) + self.pos
            jaw_center_gl_rotmat = self.rotmat.dot(self.jaw_center_rotmat)
            gm.gen_dashed_stick(spos=self.pos,
                                epos=jaw_center_gl_pos,
                                radius=.0062,
                                rgba=[.5, 0, 1, 1],
                                type="round").attach_to(stickmodel)
            gm.gen_myc_frame(pos=jaw_center_gl_pos, rotmat=jaw_center_gl_rotmat).attach_to(stickmodel)
        return stickmodel

    def gen_meshmodel(self,
                      toggle_tcpcs=False,
                      toggle_jntscs=False,
                      rgba=None,
                      name='or2fg7_mesh_model'):
        meshmodel = mc.ModelCollection(name=name)
        self.coupling.gen_mesh_model(toggle_tcpcs=False,
                                     toggle_jntscs=toggle_jntscs,
                                     rgba=rgba).attach_to(meshmodel)
        self.lft.gen_mesh_model(toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                rgba=rgba).attach_to(meshmodel)
        self.rgt.gen_mesh_model(toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                rgba=rgba).attach_to(meshmodel)
        if toggle_tcpcs:
            jaw_center_gl_pos = self.rotmat.dot(self.jaw_center_pos) + self.pos
            jaw_center_gl_rotmat = self.rotmat.dot(self.jaw_center_rotmat)
            gm.gen_dashed_stick(spos=self.pos,
                                epos=jaw_center_gl_pos,
                                radius=.0062,
                                rgba=[.5, 0, 1, 1],
                                type="round").attach_to(meshmodel)
            gm.gen_myc_frame(pos=jaw_center_gl_pos, rotmat=jaw_center_gl_rotmat).attach_to(meshmodel)
        return meshmodel


if __name__ == '__main__':
    import visualization.panda.world as wd
    import math

    base = wd.World(cam_pos=[.5, .5, .5], lookat_pos=[0, 0, 0])
    gm.gen_frame().attach_to(base)
    # for angle in np.linspace(0, .85, 8):
    #     grpr = Robotiq85()
    #     grpr.fk(angle)
    #     grpr.gen_meshmodel().attach_to(base)
    grpr = OR2FG7(coupling_offset_pos=np.array([0, 0, 0.0145]), enable_cc=True)
    if grpr:
        grpr.jaw_to(.0)
        grpr.gen_meshmodel().attach_to(base)
        grpr.gen_stickmodel(toggle_tcpcs=True).attach_to(base)
        grpr.fix_to(pos=np.array([0, .3, .2]), rotmat=rm.rotmat_from_axangle([1, 0, 0], .05))
        grpr.gen_meshmodel().attach_to(base)
        grpr.show_cdmesh()
        grpr.show_cdprimit()
        base.run()