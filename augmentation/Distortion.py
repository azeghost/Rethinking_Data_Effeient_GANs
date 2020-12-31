import numpy as np
import tensorflow as tf

def distort(images, batch_shape=None, num_anchors=10, perturb_sigma=5.0):
    # Similar results to elastic deformation (a bit complex transformation)
    # However, the transformation is much faster that elastic deformation and have a straightforward arguments
    # TODO: Need to adapt reflect padding and eliminate out-of-frame
    # images is 4D tensor [B,H,W,C]
    # num_anchors : the number of base position to make distortion, total anchors in a image = num_anchors**2
    # perturb_sigma : the displacement sigma of each anchor

    if batch_shape is not None:
        src_shp_list = batch_shape
        batch_size, src_height, src_width, _ = batch_shape
    else:
        src_shp_list = images.get_shape().as_list()
        batch_size, src_height, src_width = tf.unstack(tf.shape(images))[:3]

    pad_size = tf.cast(tf.cast(tf.maximum(src_height, src_width), tf.float32) * (np.sqrt(2) - 1.0) / 2 + 0.5, tf.int32)
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    height, width = tf.unstack(tf.shape(images))[1:3]

    mapx_base = tf.matmul(tf.ones(shape=tf.stack([num_anchors, 1])),
                          tf.transpose(tf.expand_dims(tf.linspace(0., tf.cast(width, tf.float32), num_anchors), 1), [1, 0]))
    mapy_base = tf.matmul(tf.expand_dims(tf.linspace(0., tf.cast(height, tf.float32), num_anchors), 1),
                          tf.ones(shape=tf.stack([1, num_anchors])))

    mapx_base = tf.tile(mapx_base[None, ..., None], [batch_size, 1, 1, 1])  # [batch_size, N, N, 1]
    mapy_base = tf.tile(mapy_base[None, ..., None], [batch_size, 1, 1, 1])
    distortion_x = tf.random.normal((batch_size, num_anchors, num_anchors, 1), stddev=perturb_sigma)
    distortion_y = tf.random.normal((batch_size, num_anchors, num_anchors, 1), stddev=perturb_sigma)
    mapx = mapx_base + distortion_x
    mapy = mapy_base + distortion_y

    interp_mapx = tf.compat.v1.image.resize(mapx, size=(height, width), method=tf.image.ResizeMethod.BILINEAR,
                                         align_corners=True)
    interp_mapy = tf.compat.v1.image.resize(mapy, size=(height, width), method=tf.image.ResizeMethod.BILINEAR,
                                         align_corners=True)
    coord_maps = tf.concat([interp_mapx, interp_mapy], axis=-1)  # [batch_size, height, width, 2]

    warp_images = bilinear_sampling(images, coord_maps)

    warp_images = tf.slice(warp_images, [0, pad_size, pad_size, 0], [-1, src_height, src_width, -1])

    warp_images.set_shape(src_shp_list)

    return warp_images


def bilinear_sampling(photos, coords):
    """Construct a new image by bilinear sampling from the input image.
    Points falling outside the source image boundary have value 0.
    Args:
        photos: source image to be sampled from [batch, height_s, width_s, channels]
        coords: coordinates of source pixels to sample from [batch, height_t,
          width_t, 2]. height_t/width_t correspond to the dimensions of the output
          image (don't need to be the same as height_s/width_s). The two channels
          correspond to x and y coordinates respectively.
    Returns:
        A new sampled image [batch, height_t, width_t, channels]
    """

    # photos: [batch_size, height2, width2, C]
    # coords: [batch_size, height1, width1, C]
    def _repeat(x, n_repeats):
        rep = tf.transpose(
            tf.expand_dims(tf.ones(shape=tf.stack([
                n_repeats,
            ])), 1), [1, 0])
        rep = tf.cast(rep, tf.float32)
        x = tf.matmul(tf.reshape(x, (-1, 1)), rep)
        return tf.reshape(x, [-1])

    coords_x, coords_y = tf.split(coords, [1, 1], axis=3)
    inp_size = tf.shape(photos)
    coord_size = tf.shape(coords)

    out_size = tf.stack([coord_size[0],
                         coord_size[1],
                         coord_size[2],
                         inp_size[3],
                         ])

    coords_x = tf.cast(coords_x, tf.float32)
    coords_y = tf.cast(coords_y, tf.float32)

    x0 = tf.floor(coords_x)
    x1 = x0 + 1
    y0 = tf.floor(coords_y)
    y1 = y0 + 1

    y_max = tf.cast(tf.shape(photos)[1] - 1, tf.float32)
    x_max = tf.cast(tf.shape(photos)[2] - 1, tf.float32)
    zero = tf.zeros([1], dtype=tf.float32)

    x0_safe = tf.clip_by_value(x0, zero, x_max)
    y0_safe = tf.clip_by_value(y0, zero, y_max)
    x1_safe = tf.clip_by_value(x1, zero, x_max)
    y1_safe = tf.clip_by_value(y1, zero, y_max)

    wt_x0 = x1_safe - coords_x
    wt_x1 = coords_x - x0_safe
    wt_y0 = y1_safe - coords_y
    wt_y1 = coords_y - y0_safe

    ## indices in the flat image to sample from
    dim2 = tf.cast(inp_size[2], tf.float32)
    dim1 = tf.cast(inp_size[2] * inp_size[1], tf.float32)
    base = tf.reshape(
        _repeat(
            tf.cast(tf.range(coord_size[0]), tf.float32) * dim1,
            coord_size[1] * coord_size[2]),
        [out_size[0], out_size[1], out_size[2], 1])

    base_y0 = base + y0_safe * dim2
    base_y1 = base + y1_safe * dim2
    idx00 = tf.reshape(x0_safe + base_y0, [-1])
    idx01 = x0_safe + base_y1
    idx10 = x1_safe + base_y0
    idx11 = x1_safe + base_y1

    ## sample from photos
    photos_flat = tf.reshape(photos, tf.stack([-1, inp_size[3]]))
    photos_flat = tf.cast(photos_flat, tf.float32)

    im00 = tf.reshape(tf.gather(photos_flat, tf.cast(idx00, 'int32')), out_size)
    im01 = tf.reshape(tf.gather(photos_flat, tf.cast(idx01, 'int32')), out_size)
    im10 = tf.reshape(tf.gather(photos_flat, tf.cast(idx10, 'int32')), out_size)
    im11 = tf.reshape(tf.gather(photos_flat, tf.cast(idx11, 'int32')), out_size)

    w00 = wt_x0 * wt_y0
    w01 = wt_x0 * wt_y1
    w10 = wt_x1 * wt_y0
    w11 = wt_x1 * wt_y1

    out_photos = tf.add_n([
        w00 * im00, w01 * im01,
        w10 * im10, w11 * im11
    ])

    return out_photos
