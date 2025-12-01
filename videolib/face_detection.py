import cv2
'''Define parameters for face detection object'''
face_model_path = '/opt/vilib/haarcascade_frontalface_default.xml'
face_obj_parameter = {}
face_obj_parameter['x'] = 320  
face_obj_parameter['y'] = 240  
face_obj_parameter['w'] = 0  
face_obj_parameter['h'] = 0  
face_obj_parameter['n'] = 0  
face_cascade = None
def set_face_detection_model(model_path):
    '''
    Set face detection model path
    :param model_path: The path of face haar-cascade XML classifier file
    :type model_path: str
    '''
    global face_cascade, face_model_path
    face_model_path = model_path
    face_cascade = cv2.CascadeClassifier(face_model_path)
def face_detect(img, width, height, rectangle_color=(255, 0, 0)):
    '''
    Face detection with opencv
    :param img: The detected image data
    :type img: list
    :param width: The width of the image data
    :type width: int
    :param height: The height of the image data
    :type height: int
    :param rectangle_color: The color (BGR, tuple) of rectangle. Eg: (255, 0, 0).
    :type color_name: tuple
    :returns: The image returned after detection.
    :rtype: Binary list
    '''
    global face_cascade
    zoom = 2
    width_zoom = int(width / zoom)
    height_zoom = int(height / zoom)
    resize_img = cv2.resize(img, (width_zoom, height_zoom), interpolation=cv2.INTER_LINEAR)
    gray_img = cv2.cvtColor(resize_img, cv2.COLOR_BGR2GRAY) 
    if face_cascade is None:
        face_cascade = cv2.CascadeClassifier(face_model_path)
    faces = face_cascade.detectMultiScale(gray_img, scaleFactor=1.3, minNeighbors=3)
    face_obj_parameter['n'] = len(faces)
    if face_obj_parameter['n'] > 0:
        max_area = 0
        for (x,y,w,h) in faces:
            x = x * zoom
            y = y * zoom
            w = w * zoom
            h = h * zoom
            cv2.rectangle(img, (x, y), (x+w, y+h), rectangle_color, 2)
            object_area = w * h
            if object_area > max_area: 
                max_area = object_area
                face_obj_parameter['x'] = int(x + w/2)
                face_obj_parameter['y'] = int(y + h/2)
                face_obj_parameter['w'] = w
                face_obj_parameter['h'] = h
    else:
        face_obj_parameter['x'] = width/2
        face_obj_parameter['y'] = height/2
        face_obj_parameter['w'] = 0
        face_obj_parameter['h'] = 0
        face_obj_parameter['n'] = 0
    return img
def test():
    print("face detection ...")
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)
    while cap.isOpened():
        success,frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue
        out_img = face_detect(frame, 640, 480)
        cv2.imshow('Face detecting ...', out_img)
        key = cv2.waitKey(10) & 0xff
        print(key)
    cap.release()
    cv2.destroyAllWindows()
if __name__ == "__main__":
    test()
