#!/usr/bin/env python3
import cv2
import mediapipe as mp
from ast import literal_eval
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
class DetectHands():
    def __init__(self):
        self.hands = mp_hands.Hands(max_num_hands = 1,
                                    min_detection_confidence=0.5,
                                    min_tracking_confidence=0.5)
    def work(self,image):
        joints = []
        if len(image) != 0:
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        image,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,)
            joints = str(results.multi_hand_landmarks).replace('\n','').replace(' ','').replace('landmark',',').replace(',','',1)
            joints = joints.replace('{x:','[').replace('y:',',').replace('z:',',').replace('}',']')
            try:
                joints = literal_eval(joints)
            except Exception as e:
                raise(e)
            return image,joints
