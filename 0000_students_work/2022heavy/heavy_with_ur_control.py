import robot_sim.end_effectors.single_contact.suction.mvfln40.mvfln40 as suction
import robot_sim.end_effectors.gripper.robotiq85.robotiq85 as rtq
import robot_sim.robots.ur3_dual.ur3_dual as ur3d
import modeling.geometric_model as gm
import modeling.collision_model as cm
import numpy as np
import visualization.panda.world as wd
import basis.robot_math as rm
import math

base = wd.World(cam_pos=[2, 2, 2], lookat_pos=[0,0,1.5])
ur3d_s = ur3d.UR3Dual()
# ur3d_s.gen_meshmodel().attach_to(base)

ground = gm.gen_box(np.array([2, 2, .001]))
ground.set_rgba([1, 253 / 255, 219 / 255, 1])
ground.attach_to(base)

box_0 = cm.gen_box(np.array([.3, .3, .04]))
box_0.set_rgba([153 / 255, 183 / 255, 1, .3])
box_0.set_pos(np.array([.57, -.17, 1.25]))
box_0.set_rotmat(rm.rotmat_from_axangle([1, 0, 0], math.pi / 2))
box_0.attach_to(base)

# suction_s = suction.MVFLN40()
# loc_pos_box = np.array([.1, 0, .02])
# loc_rotmat_box = rm.rotmat_from_euler(math.pi, 0, 0)
# gl_pos_box = box_0.get_pos() + box_0.get_rotmat().dot(loc_pos_box)
# gl_rotmat_box = box_0.get_rotmat().dot(loc_rotmat_box)
# suction_s.suction_to_with_scpose(gl_pos_box, gl_rotmat_box)
# suction_s.gen_meshmodel(rgba=[.55, .55, .55, .3]).attach_to(base)
# mgm.gen_stick(
#     suction_s.pos,
#     np.array([0,0,1]),rgba=[1,0,0,.3]).attach_to(base)

box = cm.gen_box(np.array([.3, .3, .04]))
box.set_rgba([153 / 255, 183 / 255, 1, 1])
box.set_pos(np.array([.57, -.17, 1.3]))
box.set_rotmat(rm.rotmat_from_axangle([1, 0, 0], math.pi / 2))
# box.set_rotmat(rm.rotmat_from_euler(math.pi / 2, -math.pi/12, 0))

box.set_pos(np.array([.57, -.17, 1.35]))
box.set_rotmat(rm.rotmat_from_euler(math.pi / 2, -math.pi/12, 0))
suction_s = suction.MVFLN40()
loc_pos_box = np.array([.1, .15, .0])
loc_rotmat_box = rm.rotmat_from_euler(math.pi/2, 0, 0)
gl_pos_box = box.get_pos() + box.get_rotmat().dot(loc_pos_box)
gl_rotmat_box = box.get_rotmat().dot(loc_rotmat_box)
suction_s.attach_to_with_cpose(gl_pos_box, gl_rotmat_box)
suction_s.gen_meshmodel().attach_to(base)
# mgm.gen_stick(
#     suction_s.pos,
#     suction_s.pos - suction_s.rotmat[:,2]*10).attach_to(base)
gm.gen_stick(
    suction_s.pos,
    np.array([.5,0,2.4])).attach_to(base)
box.set_pos(np.array([.57, -.17, 1.3]))
box.set_rotmat(rm.rotmat_from_axangle([1, 0, 0], math.pi / 2))


# loc_pos_box = np.array([-.125, .03, .02])
# loc_rotmat_box = rm.rotmat_from_axangle([0,1,0], math.pi*11/12).dot(rm.rotmat_from_axangle([0,0,1], math.pi/2))
# loc_rotmat_box=rm.rotmat_from_axangle([1,0,0], -math.pi/6).dot(loc_rotmat_box)
# # loc_pos_box = np.array([-.12, .03, .02])
# # loc_rotmat_box = rm.rotmat_from_euler(math.pi*5/7, -math.pi / 3, math.pi/3)
# # loc_pos_box = np.array([-.12, .03, -.02])
# # loc_rotmat_box = rm.rotmat_from_euler(0, -math.pi / 3, math.pi/3)
# # loc_pos_box = np.array([0, -.12, -.02])
# # loc_rotmat_box = rm.rotmat_from_euler(0, math.pi / 3, math.pi/3)
# gl_pos_box = box.get_pos() + box.get_rotmat().dot(loc_pos_box)
# gl_rotmat_box = box.get_rotmat().dot(loc_rotmat_box)
# jnt_angles = ur3d_s.ik(component_name='lft_arm', tgt_pos=gl_pos_box, tgt_rotmat=gl_rotmat_box)
# if jnt_angles is not None:
#     ur3d_s.fk(component_name='lft_arm', jnt_vals=jnt_angles)
#     # ur3d_s.gen_meshmodel().attach_to(base)
# print(gl_pos_box)
#
# rtqgel_s = rtqgel.Robotiq85GelsightPusher()
# print(rtqgel_s.jaw_center_pos)
# rtqgel_s.grip_at_with_jcpose(gl_pos_box, gl_rotmat_box, jaw_width=rtqgel_s.jaw_rng[1])
# rtqgel_s.gen_meshmodel(tgl_tcp_frame=False).attach_to(base)

box.set_rotmat(rm.rotmat_from_axangle([1, 0, 0], math.pi / 2))
rtq_s = rtq.Robotiq85()
# loc_pos_box = np.array([-.11, .12, .0])
# loc_rotmat_box = rm.rotmat_from_euler(-math.pi/2,0,-math.pi*4/5)
loc_pos_box = np.array([-.125, .02, .0])
loc_rotmat_box = rm.rotmat_from_euler(math.pi/2,0,math.pi/2)
gl_pos_box = box.get_pos() + box.get_rotmat().dot(loc_pos_box)
gl_rotmat_box = box.get_rotmat().dot(loc_rotmat_box)
rtq_s.grip_at_with_jcpose(gl_pos_box, gl_rotmat_box, jaw_width=.04)
# rtq_s.gen_meshmodel(tgl_tcp_frame=False).attach_to(base)
jnt_angles = ur3d_s.ik(component_name='rgt_arm', tgt_pos=gl_pos_box, tgt_rotmat=gl_rotmat_box)
if jnt_angles is not None:
    ur3d_s.fk(component_name='rgt_arm', jnt_values=jnt_angles)
    ur3d_s.jaw_to(hnd_name='rgt_hnd', jaw_width=.04)
    ur3d_s.gen_meshmodel().attach_to(base)
# box.set_rotmat(rm.rotmat_from_axangle([1, 0, 0], math.pi / 2))
box.set_pos(np.array([.57, -.17, 1.35]))
box.set_rotmat(rm.rotmat_from_euler(math.pi / 2, -math.pi/12, 0))
box.attach_to(base)
base.run()
