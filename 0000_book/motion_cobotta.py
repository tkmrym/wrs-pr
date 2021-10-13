if __name__ == '__main__':
    import math
    import numpy as np
    import basis.robot_math as rm
    import robot_sim.robots.cobotta.cobotta as cbt
    import motion.probabilistic.rrt_connect as rrtc
    import visualization.panda.world as wd
    import modeling.geometric_model as gm
    import motion.trajectory.piecewisepoly as trajp

    base = wd.World(cam_pos=[1, 1, .5], lookat_pos=[0, 0, .2])
    gm.gen_frame().attach_to(base)

    robot_s = cbt.Cobotta()
    start_conf = robot_s.get_jnt_values(component_name="arm")
    print("start_radians", start_conf)
    tgt_pos = np.array([0, -.2, .15])
    tgt_rotmat = rm.rotmat_from_axangle([0, 1, 0], math.pi / 3)
    jnt_values = robot_s.ik(tgt_pos=tgt_pos, tgt_rotmat=tgt_rotmat)
    rrtc_planner = rrtc.RRTConnect(robot_s)
    path = rrtc_planner.plan(component_name="arm",
                             start_conf=start_conf,
                             goal_conf=jnt_values,
                             ext_dist=.1,
                             max_time=300)
    for pose in path:
        robot_s.fk("arm", pose)
        robot_meshmodel = robot_s.gen_meshmodel()
        robot_meshmodel.attach_to(base)
    tg = trajp.PiecewisePoly(method="quintic")
    interpolated_confs, interpolated_spds, interpolated_accs, interpolated_x, original_x = \
        tg.interpolate_by_max_spdacc(path, control_frequency=.008, max_jnts_spd=[math.pi / 2] * 6,
                                     max_jnts_acc=[math.pi] * 6, toggle_debug=True)
    # base.run()
