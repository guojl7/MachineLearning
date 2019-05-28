#! /usr/bin/env python
"""Run a YOLO_v2 style detection model on test images."""
from __future__ import print_function
import argparse
import colorsys
import imghdr
import os
import random

import numpy as np
from keras import backend as K
from keras.models import load_model
from PIL import Image, ImageDraw, ImageFont

import cv2
from utils.convert_result import convert_result, draw_helper


parser = argparse.ArgumentParser(
    description='Run a YOLO_v2 style detection model on test images..')
parser.add_argument(
    'model_path',
    help='path to h5 model file containing body'
    'of a YOLO_v2 model')
parser.add_argument(
    '-a',
    '--anchors_path',
    help='path to anchors file, defaults to yolo_anchors.txt',
    default='model_data/yolo_anchors.txt')
parser.add_argument(
    '-c',
    '--classes_path',
    help='path to classes file, defaults to coco_classes.txt',
    default='model_data/coco_classes.txt')
parser.add_argument(
    '-t',
    '--test_path',
    help='path to video',
    default='images/video2.mp4')
parser.add_argument(
    '-o',
    '--output_path',
    help='path to output test video',
    default='demo.mp4')
parser.add_argument(
    '-s',
    '--score_threshold',
    type=float,
    help='threshold for bounding box scores, default .4',
    default=.4)
parser.add_argument(
    '-iou',
    '--iou_threshold',
    type=float,
    help='threshold for non max suppression IOU, default .5',
    default=.5)
parser.add_argument(
    '-w',
    '--weight_path',
    help='whether to use different weights other than the default one',
    default=None)

def _main(args):
    model_path = args.model_path
    assert model_path.endswith('.h5'), 'Keras model must be a .h5 file.'
    anchors_path = args.anchors_path
    classes_path = args.classes_path
    test_path = args.test_path
    output_path = args.output_path
    weight_path = args.weight_path

    #if not os.path.exists(output_path):
        #print 'Creating output path {}'.format(output_path)
    #    os.mkdir(output_path)

    sess = K.get_session()  # TODO: Remove dependence on Tensorflow session.

    #classes file should one class one line
    with open(classes_path) as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]

    #anchors should be separated by ,
    with open(anchors_path) as f:
        anchors = f.readline()
        anchors = [float(x) for x in anchors.split(',')]
        anchors = np.array(anchors).reshape(-1, 2)

    yolo_model = load_model(model_path)
    if weight_path!=None:
        yolo_model.load_weights(weight_path)

    # Verify model, anchors, and classes are compatible
    num_classes = len(class_names)
    num_anchors = len(anchors)
    # TODO: Assumes dim ordering is channel last
    model_output_channels = yolo_model.layers[-1].output_shape[-1]
    assert model_output_channels == num_anchors * (num_classes + 5), \
        'Mismatch between model and given anchor and class sizes. ' \
        'Specify matching anchors and classes with --anchors_path and ' \
        '--classes_path flags.'
    print('{} model, anchors, and classes loaded.'.format(model_path))

    # Check if model is fully convolutional, assuming channel last order.
    model_image_size = yolo_model.layers[0].input_shape[1:3]
    is_fixed_size = model_image_size != (None, None)

    # Generate colors for drawing bounding boxes.
    hsv_tuples = [(x / float(len(class_names)), 1., 1.)
                  for x in range(len(class_names))]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(
        map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)),
            colors))
    random.seed(10101)  # Fixed seed for consistent colors across runs.
    random.shuffle(colors)  # Shuffle colors to decorrelate adjacent classes.
    random.seed(None)  # Reset seed to default.

    # Generate output tensor targets for filtered bounding boxes.
    # TODO: Wrap these backend operations with Keras layers.
    yolo_outputs = convert_result(yolo_model.output, anchors, len(class_names))
    input_image_shape = K.placeholder(shape=(2, ))
    boxes, scores, classes = draw_helper(
        yolo_outputs,
        input_image_shape,
        to_threshold=args.score_threshold,
        iou_threshold=args.iou_threshold)

    video_in = cv2.VideoCapture(test_path)
    width, height, FPS = int(video_in.get(3)), int(video_in.get(4)),video_in.get(5)
    video_out = cv2.VideoWriter()
    video_out.open(output_path, # Filename
                    cv2.VideoWriter_fourcc(*'DIVX'), # Negative 1 denotes manual codec selection. You can make this automatic by defining the "fourcc codec" with "cv2.VideoWriter_fourcc"
                    FPS, # 10 frames per second is chosen as a demo, 30FPS and 60FPS is more typical for a YouTube video
                    (width, height), # The width and height come from the stats of image1
                    )
    #begin from here
    while video_in.isOpened():
        ret, data = video_in.read()
        if ret==False:
            break
        array = cv2.cvtColor(data,cv2.COLOR_BGR2RGB)
        image = Image.fromarray(array,mode='RGB')
        if is_fixed_size:  # TODO: When resizing we can use minibatch input.
            resized_image = image.resize(
                tuple(reversed(model_image_size)), Image.BICUBIC)
            image_data = np.array(resized_image, dtype='float32')
        else:
            # Due to skip connection + max pooling in YOLO_v2, inputs must have
            # width and height as multiples of 32.
            new_image_size = (image.width - (image.width % 32),
                              image.height - (image.height % 32))
            resized_image = image.resize(new_image_size, Image.BICUBIC)
            image_data = np.array(resized_image, dtype='float32')
            print(image_data.shape)
            
        image_data /= 255.
        image_data = np.expand_dims(image_data, 0)  # Add batch dimension.

        out_boxes, out_scores, out_classes = sess.run(
            [boxes, scores, classes],
            feed_dict={
                yolo_model.input: image_data,
                input_image_shape: [image.size[1], image.size[0]],
                K.learning_phase(): 0
            })
        #print('Found {} boxes for {}'.format(len(out_boxes), image_file))

        font = ImageFont.truetype(
            font='font/FiraMono-Medium.otf',
            size=np.floor(3e-2 * image.size[1] + 0.5).astype('int32'))
        thickness = (image.size[0] + image.size[1]) // 300

        for i, c in reversed(list(enumerate(out_classes))):
            predicted_class = class_names[c]
            box = out_boxes[i]
            score = out_scores[i]

            label = '{} {:.2f}'.format(predicted_class, score)

            draw = ImageDraw.Draw(image)
            label_size = draw.textsize(label, font)

            top, left, bottom, right = box
            top = max(0, np.floor(top + 0.5).astype('int32'))
            left = max(0, np.floor(left + 0.5).astype('int32'))
            bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
            right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
            #the result's origin is in top left
            print(label, (left, top), (right, bottom))

            if top - label_size[1] >= 0:
                text_origin = np.array([left, top - label_size[1]])
            else:
                text_origin = np.array([left, top + 1])

            # My kingdom for a good redistributable image drawing library.
            for i in range(thickness):
                draw.rectangle(
                    [left + i, top + i, right - i, bottom - i],
                    outline=colors[c])
            draw.rectangle(
                [tuple(text_origin), tuple(text_origin + label_size)],
                fill=colors[c])
            draw.text(text_origin, label, fill=(0, 0, 0), font=font)
            del draw

        #image.save(os.path.join(output_path, image_file), quality=90)
        video_out.write(cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR))
    print("Done")
    sess.close()
    video_in.release()
    video_out.release()


if __name__ == '__main__':
    _main(parser.parse_args())