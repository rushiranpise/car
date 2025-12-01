import cv2
import numpy as np
'''The range of H, S, V in HSV space for colors'''
color_dict = {
        'red':[[0, 8], [80, 255], [0, 255]],
        'orange':[[12, 18], [80, 255], [80, 255]],
        'yellow':[[20, 60], [60, 255], [120, 255]],
        'green':[[45, 85], [120, 255], [80, 255]],
        'blue':[[92,120], [120, 255], [80, 255]],
        'purple':[[115,155], [30, 255], [60, 255]],
        'magenta':[[160,180], [30, 255], [60, 255]],
    }
'''Define parameters for color detection object'''
color_obj_parameter = {}
color_obj_parameter['color'] = 'red'    
color_obj_parameter['x'] = 320    
color_obj_parameter['y'] = 240    
color_obj_parameter['w'] = 0  
color_obj_parameter['h'] = 0  
color_obj_parameter['n'] = 0  
def color_detect_work(img, width, height, color_name, rectangle_color=(0, 0, 255)):
    '''
    Color detection with opencv
    :param img: The detected image data
    :type img: list
    :param width: The width of the image data
    :type width: int
    :param height: The height of the image data
    :type height: int
    :param color_name: The name of the color to be detected. Eg: "red". For supported colors, please see [color_dict].
    :type color_name: str
    :param rectangle_color: The color (BGR, tuple) of rectangle. Eg: (0, 0, 255).
    :type color_name: tuple
    :returns: The image returned after detection.
    :rtype: Binary list
    '''
    color_obj_parameter['color'] = color_name   
    zoom = 4 
    width_zoom = int(width / zoom)
    height_zoom = int(height / zoom)
    resize_img = cv2.resize(img, (width_zoom, height_zoom), interpolation=cv2.INTER_LINEAR)
    hsv = cv2.cvtColor(resize_img, cv2.COLOR_BGR2HSV) 
    color_lower = np.array([min(color_dict[color_name][0]), min(color_dict[color_name][1]), min(color_dict[color_name][2])])
    color_upper = np.array([max(color_dict[color_name][0]), max(color_dict[color_name][1]), max(color_dict[color_name][2])])
    mask = cv2.inRange(hsv, color_lower, color_upper)
    if color_name == 'red':
        mask_2 = cv2.inRange(hsv, (167, 0, 0), (180, 255, 255))
        mask = cv2.bitwise_or(mask, mask_2)
    kernel_5 = np.ones((5,5), np.uint8)
    open_img = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_5, iterations=1)      
    _tuple = cv2.findContours(open_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
    if len(_tuple) == 3:
        _, contours, hierarchy = _tuple
    else:
        contours, hierarchy = _tuple
    color_obj_parameter['n'] = len(contours)
    if color_obj_parameter['n'] < 1:
        color_obj_parameter['x'] = width/2
        color_obj_parameter['y'] = height/2
        color_obj_parameter['w'] = 0
        color_obj_parameter['h'] = 0
        color_obj_parameter['n'] = 0
    else:
        max_area = 0
        for contour in contours:  
            x, y, w, h = cv2.boundingRect(contour)      
            if w >= 8 and h >= 8: 
                x = x * zoom
                y = y * zoom
                w = w * zoom
                h = h * zoom
                cv2.rectangle(img, 
                            (x, y), 
                            (x+w, y+h), 
                            rectangle_color, 
                            2, 
                        )
                cv2.putText(img, 
                            color_name, 
                            (x, y-5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.72, 
                            rectangle_color, 
                            1, 
                            cv2.LINE_AA, 
                        )
            else:
                continue
            object_area = w*h
            if object_area > max_area: 
                max_area = object_area
                color_obj_parameter['x'] = int(x + w/2)
                color_obj_parameter['y'] = int(y + h/2)
                color_obj_parameter['w'] = w
                color_obj_parameter['h'] = h
    return img
def test(color):
    print("color detection: %s"%color)
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)
    while cap.isOpened():
        success,frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue
        out_img = color_detect_work(frame, 640, 480, color)
        cv2.imshow('Color detecting ...', out_img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if cv2.waitKey(1) & 0xff == 27: 
            break
        if cv2.getWindowProperty('Color detecting ...', 1) < 0:
            break
    cap.release()
    cv2.destroyAllWindows()
if __name__ == "__main__":
    test('red')
