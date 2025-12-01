#!/usr/bin/env python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import argparse
import time
import os
import numpy as np
import cv2
from tflite_runtime.interpreter import Interpreter
import threading
from .utils import load_labels
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
default_model = '/opt/vilib/mobilenet_v1_0.25_224_quant.tflite'
default_labels = '/opt/vilib/labels_mobilenet_quant_v1_224.txt'
image_classification_obj_parameter = {}
image_classification_obj_parameter['name'] = ""  
image_classification_obj_parameter['acc'] = 0 
def set_input_tensor(interpreter, image):
  tensor_index = interpreter.get_input_details()[0]['index']
  input_tensor = interpreter.tensor(tensor_index)()[0]
  input_tensor[:, :] = image
def __classify_image(interpreter, image, labels_map):
  """Returns a sorted array of classification results."""
  set_input_tensor(interpreter, image)
  interpreter.invoke()
  output_details = interpreter.get_output_details()[0]
  output = np.squeeze(interpreter.get_tensor(output_details['index']))
  if output_details['dtype'] == np.uint8:
    scale, zero_point = output_details['quantization']
    output = scale * (output - zero_point)
  ordered = np.argpartition(-output, 1)
  return [(i, output[i]) for i in ordered[:1]]
results = []
image = []
elapsed_ms = 0
run_flag = False
def imgshow_fuc(input_height, input_width,labels):
  global results
  global elapsed_ms
  global image
  global run_flag
  run_flag = True
  counter, fps = 0, 0
  start_time = time.time()
  fps_avg_frame_count = 10
  cap = cv2.VideoCapture(0)
  cap.set(3,CAMERA_WIDTH)
  cap.set(4,CAMERA_HEIGHT)
  print('start...')
  while cap.isOpened():    
    success,frame = cap.read()
    if not success:
      print("Ignoring empty camera frame.")
      continue
    image = cv2.resize(frame,(input_width,input_height))
    counter += 1
    if counter % fps_avg_frame_count == 0:
        end_time = time.time()
        fps = fps_avg_frame_count / (end_time - start_time)
        start_time = time.time()
    if len(results) != 0:
      label_id, prob = results[0]
      cv2.putText(frame, 
                  f"{labels[label_id]} {prob:.3f}", 
                  (CAMERA_WIDTH-120, 10), 
                  cv2.FONT_HERSHEY_SIMPLEX,  
                  0.8, 
                  (0,255,255), 
                  1, 
                  cv2.LINE_AA 
                  )
      cv2.putText(frame, '%.1fms' % (elapsed_ms), (CAMERA_WIDTH-120, 40),cv2.FONT_HERSHEY_PLAIN,1, (255, 255, 225), 1)       
      cv2.putText(frame, 'fps %s'%round(fps,1), (CAMERA_WIDTH-120, 20),cv2.FONT_HERSHEY_PLAIN,1,(255, 255, 225),1)  
    cv2.imshow('Detecting...', frame) 
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break
    if cv2.waitKey(1) & 0xff == 27: 
      break
    if cv2.getWindowProperty('Detecting...',1) < 0:
      break
  run_flag = False
  cap.release()
  cv2.destroyAllWindows()
def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--model', 
      help='File path of .tflite file.',
      required=False,
      default=default_model)
  parser.add_argument(
      '--labels', 
      help='File path of labels file.',
      required=False,
      default=default_labels)
  args = parser.parse_args()
  labels = load_labels(args.labels)
  interpreter = Interpreter(args.model)
  interpreter.allocate_tensors()
  _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']
  imgshow_t = threading.Thread(target=imgshow_fuc,args=(input_height, input_width,labels))
  imgshow_t.start()
  global results
  global elapsed_ms
  global run_flag
  while True:
    if len(image) != 0:
      start_time = time.monotonic()
      results = __classify_image(interpreter, image,labels)
      elapsed_ms = (time.monotonic() - start_time) * 1000
      label_id, prob = results[0]
      print(labels[label_id], prob)
      print(' ')
    if run_flag == False:
      print('\nend...')
      break
    time.sleep(0.01)
def classify_image(image, model=None, labels=None):
  if model is None:
    model = default_model
  if labels is None:
    labels = default_labels
  if not os.path.exists(model):
    print('incorrect model path ')
    return image
  if not os.path.exists(labels):
    print('incorrect labels path ')
    return image
  labels = load_labels(labels)
  interpreter = Interpreter(model)
  interpreter.allocate_tensors()
  _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']  
  if len(image) != 0:
    img = cv2.resize(image, (input_width, input_height))
    results = __classify_image(interpreter, img,labels)
    label_id, prob = results[0]
    image_classification_obj_parameter['name'] = labels[label_id]
    image_classification_obj_parameter['acc'] = prob
    cv2.putText(image, 
                f"{labels[label_id]} {prob:.3f}", 
                (10, 25), 
                cv2.FONT_HERSHEY_SIMPLEX,  
                0.8, 
                (0, 255, 255), 
                1, 
                cv2.LINE_AA 
                )
  return image
if __name__ == '__main__':
  main()
