
import tensorflow_addons as tfa
import tensorflow as tf

def shear_left_right(images, shear_lambda):
    im_shape = tf.shape(images)
    src_height, src_width = tf.unstack(im_shape)[1:3]
    pad_size = tf.cast(
        tf.cast(tf.maximum(src_height, src_width), tf.float32) * (2.0 - 1.0) / 2 + 0.5, tf.int32)  # larger than usual (sqrt(2))
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')

    images = transformImg(images, [[1.0, shear_lambda, 0], [0, 1.0, 0], [0, 0, 1.0]])
    return tf.slice(images, [0, pad_size*2, pad_size*2, 0], [-1, src_height, src_width, -1])


def skew_left_right(images, l_shear_lambda, r_shear_lambda):
    im_shape = tf.shape(images)
    src_height, src_width = tf.unstack(im_shape)[1:3]
    pad_size = tf.cast(
        tf.cast(tf.maximum(src_height, src_width), tf.float32) * (2.0 - 1.0) / 2 + 0.5,
        tf.int32)  # larger than usual (sqrt(2))
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    images = transformImg(images, [[1.0, r_shear_lambda + l_shear_lambda, 0], [0, 1.0, 0], [0, 0, 1.0]])
    images = tf.slice(images, [0, pad_size * 2, pad_size * 2, 0], [-1, src_height, src_width, -1])

    images = tf.image.flip_left_right(images)
    im_shape = tf.shape(images)
    src_height, src_width = tf.unstack(im_shape)[1:3]
    pad_size = tf.cast(
        tf.cast(tf.maximum(src_height, src_width), tf.float32) * (2.0 - 1.0) / 2 + 0.5,
        tf.int32)  # larger than usual (sqrt(2))
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    images = transformImg(images, [[1.0, r_shear_lambda, 0], [0, 1.0, 0], [0, 0, 1.0]])
    images = tf.slice(images, [0, pad_size * 2, pad_size * 2, 0], [-1, src_height, src_width, -1])
    return tf.image.flip_left_right(images)


def shear_top_down(images, shear_lambda):
    images = tf.image.rot90(images)
    im_shape = tf.shape(images)
    src_height, src_width = tf.unstack(im_shape)[1:3]
    pad_size = tf.cast(
        tf.cast(tf.maximum(src_height, src_width), tf.float32) * (2.0 - 1.0) / 2 + 0.5, tf.int32)  # larger than usual (sqrt(2))
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')
    images = tf.pad(images, [[0, 0], [pad_size] * 2, [pad_size] * 2, [0, 0]], 'REFLECT')

    images = transformImg(images, [[1.0, shear_lambda, 0], [0, 1.0, 0], [0, 0, 1.0]])
    images = tf.slice(images, [0, pad_size*2, pad_size*2, 0], [-1, src_height, src_width, -1])
    return tf.image.rot90(tf.image.rot90(tf.image.rot90(images)))

def transformImg(imgIn,forward_transform):
    t = tfa.image.transform_ops.matrices_to_flat_transforms(tf.linalg.inv(forward_transform))
    return tfa.image.transform(imgIn, t, interpolation="BILINEAR")


