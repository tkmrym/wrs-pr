import copy
import numpy as np
import basis.robotmath as rm
import basis.dataadapter as da
import basis.trimeshgenerator as tg
import modeling.geometricmodel as gm
import gimpact as gi

# util functions
def _gen_cdmesh_vvnf(vertices, vertex_normals, faces):
    """
    generate cdmesh given vertices, _, and faces
    :return: gimpact.TriMesh (require gimpact to be installed)
    author: weiwei
    date: 20210118
    """
    return gi.TriMesh(vertices, faces.flatten())

def is_collided(objcm0, objcm1):
    """
    check if two objcm are collided after converting the specified cdmesh_type
    :param objcm0:
    :param objcm1:
    :return:
    author: weiwei
    date: 20210117
    """
    obj_gitrm0 = objcm0.cdmesh
    obj_gitrm1 = objcm1.cdmesh
    contacts = gi.trimesh_trimesh_collision(obj_gitrm0, obj_gitrm1)
    contact_points = [ct.point for ct in contacts]
    return (True, contact_points) if len(contact_points)>0 else (False, contact_points)

def rayhit_triangles_closet(pfrom, pto, objcm):
    """
    :param pfrom:
    :param pto:
    :param objcm:
    :return:
    author: weiwei
    date: 20190805
    """
    tmptrimesh = objcm.objtrm.copy()
    tmptrimesh.apply_transform(objcm.get_homomat())
    geom = da.pandageom_from_vfnf(tmptrimesh.vertices, tmptrimesh.face_normals, tmptrimesh.faces)
    targetobjmesh = BulletTriangleMesh()
    targetobjmesh.addGeom(geom)
    bullettmshape = BulletTriangleMeshShape(targetobjmesh, dynamic=True)
    targetobjmeshnode = BulletRigidBodyNode('facet')
    targetobjmeshnode.addShape(bullettmshape)
    base.physicsworld.attach(targetobjmeshnode)
    result = base.physicsworld.rayTestClosest(da.npv3_to_pdv3(pfrom), da.npv3_to_pdv3(pto))
    base.physicsworld.removeRigidBody(targetobjmeshnode)
    if result.hasHit():
        return [da.pdv3_to_npv3(result.getHitPos()), da.pdv3_to_npv3(result.getHitNormal())]
    else:
        return [None, None]


def rayhit_triangles_all(pfrom, pto, objcm):
    """
    :param pfrom:
    :param pto:
    :param objcm:
    :return:
    author: weiwei
    date: 20190805
    """
    tmptrimesh = objcm.objtrm.copy()
    tmptrimesh.apply_transform(objcm.gethomomat())
    geom = da.pandageom_from_vfnf(tmptrimesh.vertices, tmptrimesh.face_normals, tmptrimesh.faces)
    targetobjmesh = BulletTriangleMesh()
    targetobjmesh.addGeom(geom)
    bullettmshape = BulletTriangleMeshShape(targetobjmesh, dynamic=True)
    targetobjmeshnode = BulletRigidBodyNode('facet')
    targetobjmeshnode.addShape(bullettmshape)
    base.physicsworld.attach(targetobjmeshnode)
    result = base.physicsworld.rayTestAll(da.npv3_to_pdv3(pfrom), da.npv3_to_pdv3(pto))
    base.physicsworld.removeRigidBody(targetobjmeshnode)
    if result.hasHits():
        allhits = []
        for hit in result.getHits():
            allhits.append([da.pdv3_to_npv3(hit.getHitPos()), da.pdv3_to_npv3(-hit.getHitNormal())])
        return allhits
    else:
        return []


def _gen_plane_cdmesh(updirection=np.array([0, 0, 1]), offset=0, name='autogen'):
    """
    generate a plane bulletrigidbody node
    :param updirection: the normal parameter of bulletplaneshape at panda3d
    :param offset: the d parameter of bulletplaneshape at panda3d
    :param name:
    :return: bulletrigidbody
    author: weiwei
    date: 20170202, tsukuba
    """
    bulletplnode = BulletRigidBodyNode(name)
    bulletplshape = BulletPlaneShape(Vec3(updirection[0], updirection[1], updirection[2]), offset)
    bulletplshape.setMargin(0)
    bulletplnode.addShape(bulletplshape)
    return bulletplnode


def _rayhit_geom(pfrom, pto, geom):
    """
    TODO: To be deprecated, 20201119
    NOTE: this function is quite slow
    find the nearest collision point between vec(pto-pfrom) and the mesh of nodepath
    :param pfrom: starting point of the ray, Point3
    :param pto: ending point of the ray, Point3
    :param geom: meshmodel, a panda3d datatype
    :return: None or Point3
    author: weiwei
    date: 20161201
    """
    bulletworld = BulletWorld()
    facetmesh = BulletTriangleMesh()
    facetmesh.addGeom(geom)
    facetmeshnode = BulletRigidBodyNode('facet')
    bullettmshape = BulletTriangleMeshShape(facetmesh, dynamic=True)
    bullettmshape.setMargin(1e-6)
    facetmeshnode.addShape(bullettmshape)
    bulletworld.attach(facetmeshnode)
    result = bulletworld.rayTestClosest(pfrom, pto)
    return result.getHitPos() if result.hasHit() else None


if __name__ == '__main__':
    import os, math, basis
    import numpy as np
    import visualization.panda.world as wd
    import modeling.geometricmodel as gm
    import modeling.collisionmodel as cm

    # wd.World(campos=[1.0, 1, .0, 1.0], lookatpos=[0, 0, 0])
    # objpath = os.path.join(basis.__path__[0], 'objects', 'bunnysim.stl')
    # objcm1= cm.CollisionModel(objpath)
    # homomat = np.eye(4)
    # homomat[:3, :3] = rm.rotmat_from_axangle([0, 0, 1], math.pi / 2)
    # homomat[:3, 3] = np.array([0.02, 0.02, 0])
    # objcm1.set_homomat(homomat)
    # objcm1.set_rgba([1,1,.3,.2])
    # objcm2 = objcm1.copy()
    # objcm2.set_pos(objcm1.get_pos()+np.array([.05,.02,.0]))
    # objcm1.change_cdmesh_type('convexhull')
    # objcm2.change_cdmesh_type('obb')
    # iscollided, contacts = is_collided(objcm1, objcm2)
    # # objcm1.show_cdmesh(type='box')
    # # show_triangles_cdmesh(objcm1)
    # # show_triangles_cdmesh(objcm2)
    # show_cdmesh(objcm1)
    # show_cdmesh(objcm2)
    # # objcm1.show_cdmesh(type='box')
    # # objcm2.show_cdmesh(type='triangles')
    # objcm1.attach_to(base)
    # objcm2.attach_to(base)
    # print(iscollided)
    # for ct in contacts:
    #     gm.gen_sphere(ct.point, radius=.001).attach_to(base)
    # # pfrom = np.array([0, 0, 0]) + np.array([1.0, 1.0, 1.0])
    # # pto = np.array([0, 0, 0]) + np.array([-1.0, -1.0, -0.9])
    # # hitpos, hitnrml = rayhit_triangles_closet(pfrom=pfrom, pto=pto, objcm=objcm)
    # # objcm.attach_to(base)
    # # objcm.show_cdmesh(type='box')
    # # objcm.show_cdmesh(type='convexhull')
    # # gm.gen_sphere(hitpos, radius=.003, rgba=np.array([0, 1, 1, 1])).attach_to(base)
    # # gm.gen_stick(spos=pfrom, epos=pto, thickness=.002).attach_to(base)
    # # gm.gen_arrow(spos=hitpos, epos=hitpos + hitnrml * .07, thickness=.002, rgba=np.array([0, 1, 0, 1])).attach_to(base)
    # base.run()

    wd.World(campos=[1.0, 1, .0, 1.0], lookatpos=[0, 0, 0])
    objpath = os.path.join(basis.__path__[0], 'objects', 'yumifinger.stl')
    objcm1= cm.CollisionModel(objpath, cdmesh_type='triangles')
    homomat = np.array([[ 5.00000060e-01,  7.00629234e-01,  5.09036899e-01, -3.43725011e-02],
                        [ 8.66025329e-01, -4.04508471e-01, -2.93892622e-01,  5.41121606e-03],
                        [-2.98023224e-08,  5.87785244e-01, -8.09016943e-01,  1.13636881e-01],
                        [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])
    homomat = np.array([[ 1.00000000e+00,  2.38935501e-16,  3.78436685e-17, -7.49999983e-03],
                        [ 2.38935501e-16, -9.51056600e-01, -3.09017003e-01,  2.04893537e-02],
                        [-3.78436685e-17,  3.09017003e-01, -9.51056600e-01,  1.22025304e-01],
                        [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]])
    objcm1.set_homomat(homomat)
    objcm1.set_rgba([1,1,.3,.2])

    objpath = os.path.join(basis.__path__[0], 'objects', 'tubebig.stl')
    objcm2= cm.CollisionModel(objpath, cdmesh_type='triangles')
    iscollided, contact_points = is_collided(objcm1, objcm2)
    # objcm1.show_cdmesh(type='box')
    # show_triangles_cdmesh(objcm1)
    # show_triangles_cdmesh(objcm2)
    objcm1.show_cdmesh()
    objcm2.show_cdmesh()
    # objcm1.show_cdmesh(type='box')
    # objcm2.show_cdmesh(type='triangles')
    objcm1.attach_to(base)
    objcm2.attach_to(base)
    print(iscollided)
    for ctpt in contact_points:
        gm.gen_sphere(ctpt, radius=.001).attach_to(base)
    # pfrom = np.array([0, 0, 0]) + np.array([1.0, 1.0, 1.0])
    # pto = np.array([0, 0, 0]) + np.array([-1.0, -1.0, -0.9])
    # hitpos, hitnrml = rayhit_triangles_closet(pfrom=pfrom, pto=pto, objcm=objcm)
    # objcm.attach_to(base)
    # objcm.show_cdmesh(type='box')
    # objcm.show_cdmesh(type='convexhull')
    # gm.gen_sphere(hitpos, radius=.003, rgba=np.array([0, 1, 1, 1])).attach_to(base)
    # gm.gen_stick(spos=pfrom, epos=pto, thickness=.002).attach_to(base)
    # gm.gen_arrow(spos=hitpos, epos=hitpos + hitnrml * .07, thickness=.002, rgba=np.array([0, 1, 0, 1])).attach_to(base)
    base.run()
