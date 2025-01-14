import os
import numpy as np
import modeling.model_collection as mc
import robot_sim._kinematics.jlchain as jl
import basis.robot_math as rm
import robot_sim.end_effectors.single_contact.single_contact_interface as si


class MVFLN40(si.SCInterface):

    def __init__(self, pos=np.zeros(3), rotmat=np.eye(3), cdmesh_type='box', name='mvfln40', enable_cc=True):
        super().__init__(pos=pos, rotmat=rotmat, cdmesh_type=cdmesh_type, name=name)
        this_dir, this_filename = os.path.split(__file__)
        cpl_end_pos = self.coupling.jnts[-1]['gl_posq']
        cpl_end_rotmat = self.coupling.jnts[-1]['gl_rotmatq']
        self.jlc = jl.JLChain(pos=cpl_end_pos, rotmat=cpl_end_rotmat, home_conf=np.zeros(0), name='mvfln40_jlc')
        self.jlc.jnts[1]['pos_in_loc_tcp'] = np.array([0, .0, .068])
        self.jlc.lnks[0]['name'] = "mvfln40"
        self.jlc.lnks[0]['pos_in_loc_tcp'] = np.zeros(3)
        self.jlc.lnks[0]['mesh_file'] = os.path.join(this_dir, "meshes", "mvfln40.stl")
        self.jlc.lnks[0]['rgba'] = [.55, .55, .55, 1]
        # reinitialize
        self.jlc.finalize()
        # suction center
        self.suction_center_pos = np.array([0, 0, .068])
        # collision detection
        self.all_cdelements = []
        self.enable_cc(toggle_cdprimit=enable_cc)

    def enable_cc(self, toggle_cdprimit):
        if toggle_cdprimit:
            super().enable_cc()
            # cdprimit
            self.cc.add_cdlnks(self.jlc, [0])
            activelist = [self.jlc.lnks[0]]
            self.cc.set_active_cdlnks(activelist)
            self.all_cdelements = self.cc.cce_dict
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
        self.jlc.fix_to(cpl_end_pos, cpl_end_rotmat)

    def gen_stickmodel(self,
                       toggle_tcpcs=False,
                       toggle_jntscs=False,
                       toggle_connjnt=False,
                       name='suction_stickmodel'):
        mm_collection = mc.ModelCollection(name=name)
        self.coupling.gen_stickmodel(toggle_tcpcs=False,
                                     toggle_jntscs=toggle_jntscs).attach_to(mm_collection)
        self.jlc.gen_stickmodel(toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                toggle_connjnt=toggle_connjnt).attach_to(mm_collection)
        if toggle_tcpcs:
            suction_center_gl_pos = self.rotmat.dot(self.suction_center_pos) + self.pos
            suction_center_gl_rotmat = self.rotmat.dot(self.contact_center_rotmat)
            gm.gen_dashed_stick(spos=self.pos,
                                epos=suction_center_gl_pos,
                                radius=.0062,
                                rgba=[.5, 0, 1, 1],
                                type="round").attach_to(mm_collection)
            gm.gen_myc_frame(pos=suction_center_gl_pos, rotmat=suction_center_gl_rotmat).attach_to(mm_collection)
        return mm_collection

    def gen_meshmodel(self,
                      toggle_tcpcs=False,
                      toggle_jntscs=False,
                      rgba=None,
                      name='xarm_gripper_meshmodel'):
        mm_collection = mc.ModelCollection(name=name)
        self.coupling.gen_mesh_model(toggle_tcpcs=False,
                                     toggle_jntscs=toggle_jntscs,
                                     rgba=rgba).attach_to(mm_collection)
        self.jlc.gen_mesh_model(toggle_tcpcs=False,
                                toggle_jntscs=toggle_jntscs,
                                rgba=rgba).attach_to(mm_collection)
        if toggle_tcpcs:
            suction_center_gl_pos = self.rotmat.dot(self.suction_center_pos) + self.pos
            suction_center_gl_rotmat = self.rotmat.dot(self.contact_center_rotmat)
            gm.gen_dashed_stick(spos=self.pos,
                                epos=suction_center_gl_pos,
                                radius=.0062,
                                rgba=[.5, 0, 1, 1],
                                type="round").attach_to(mm_collection)
            gm.gen_myc_frame(pos=suction_center_gl_pos, rotmat=suction_center_gl_rotmat).attach_to(mm_collection)
        return mm_collection


if __name__ == '__main__':
    import visualization.panda.world as wd
    import modeling.geometric_model as gm

    base = wd.World(cam_pos=[.5, .5, .5], lookat_pos=[0, 0, 0])
    gm.gen_frame().attach_to(base)
    # for angle in np.linspace(0, .85, 8):
    #     grpr = Robotiq85()
    #     grpr.fk(angle)
    #     grpr.gen_meshmodel().attach_to(base)
    grpr = MVFLN40(enable_cc=True)
    grpr.gen_meshmodel(toggle_tcpcs=True).attach_to(base)
    # grpr.gen_stickmodel(toggle_joint_frame=False).attach_to(base)
    grpr.fix_to(pos=np.array([0, .3, .2]), rotmat=rm.rotmat_from_axangle([1, 0, 0], .05))
    grpr.gen_meshmodel().attach_to(base)
    grpr.show_cdmesh()
    grpr.show_cdprimit()
    base.run()
