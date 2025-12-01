#!/usr/bin/env python3
import cv2
import mediapipe as mp
from ast import literal_eval
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
class DetectPose():
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5,
                                min_tracking_confidence=0.5)
    def work(self,image):
        joints = []
        if len(image) != 0:
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,)
            joints = str(results.pose_landmarks).replace('\n','').replace(' ','').replace('landmark',',').replace(',','',1)
            joints = '['+joints.replace('{x:','[').replace('y:',',').replace('z:',',').replace('visibilit','').replace('}',']')+']'
            try:
                joints = literal_eval(joints)
            except Exception as e:
                raise(e)           
            return image,joints
