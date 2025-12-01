#!/usr/bin/env python3
import os
import logging
from .version import __version__
if 'VILIB_WELCOME' not in os.environ or os.environ['VILIB_WELCOME'] not in [
        'False', '0'
]:
    from pkg_resources import require
    picamera2_version = require('picamera2')[0].version
    print(f'videolib {__version__} launching ...')
    print(f'picamera2 {picamera2_version}')
os.environ['LIBCAMERA_LOG_LEVELS'] = '*:ERROR'
from picamera2 import Picamera2
import libcamera
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, Response
import time
import datetime
import threading
from multiprocessing import Process, Manager
from .utils import *
user = os.popen("echo ${SUDO_USER:-$(who -m | awk '{ print $1 }')}").readline().strip()
user_home = os.popen(f'getent passwd {user} | cut -d: -f 6').readline().strip()
DEFAULLT_PICTURES_PATH = '%s/Pictures/videolib/'%user_home
DEFAULLT_VIDEOS_PATH = '%s/Videos/videolib/'%user_home
def findContours(img):
    _tuple = cv2.findContours(img, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)      
    if len(_tuple) == 3:
        _, contours, hierarchy = _tuple
    else:
        contours, hierarchy = _tuple
    return contours, hierarchy
os.environ['FLASK_DEBUG'] = 'development'
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')
def get_frame():
    return cv2.imencode('.jpg', videolib.flask_img)[1].tobytes()
def get_qrcode_pictrue():
    return cv2.imencode('.jpg', videolib.flask_img)[1].tobytes()
def get_png_frame():
    return cv2.imencode('.png', videolib.flask_img)[1].tobytes()
def get_qrcode():
    while videolib.qrcode_img_encode is None:
         time.sleep(0.2)
    return videolib.qrcode_img_encode
def gen():
    """Video streaming generator function."""
    while True:  
        frame = get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)
@app.route('/mjpg') 
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    if videolib.web_display_flag:
        response = Response(gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame') 
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    else:
        tip = '''
    Please enable web display first:
        videolib.display(web=True)
'''
        html = f"<html><style>p{{white-space: pre-wrap;}}</style><body><p>{tip}</p></body></html>"
        return Response(html, mimetype='text/html')
@app.route('/mjpg.jpg')  
def video_feed_jpg():
    """Video streaming route. Put this in the src attribute of an img tag."""
    response = Response(get_frame(), mimetype="image/jpeg")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response
@app.route('/mjpg.png')  
def video_feed_png():
    """Video streaming route. Put this in the src attribute of an img tag."""
    response = Response(get_png_frame(), mimetype="image/png")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response
@app.route("/qrcode")
def qrcode_feed():
    qrcode_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>QRcode</title>
    <script>
        function refreshQRCode() {
            var imgElement = document.getElementById('qrcode-img');
            imgElement.src = '/qrcode.png?' + new Date().getTime();  // Add timestamp to avoid caching
        }
        var refreshInterval = 500;  // 2s
        window.onload = function() {
            refreshQRCode(); 
            setInterval(refreshQRCode, refreshInterval);
        };
    </script>
</head>
<body>
    <img id="qrcode-img" src="/qrcode.png" alt="QR Code" />
</body>
</html>
'''
    return Response(qrcode_html, mimetype='text/html')
@app.route("/qrcode.png")
def qrcode_feed_png():
    """Video streaming route. Put this in the src attribute of an img tag."""
    if videolib.web_qrcode_flag:
        response = Response(get_qrcode(), mimetype="image/png")
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    else:
        tip = '''
    Please enable web display first:
        videolib.display_qrcode(web=True)
'''
        html = f"<html><style>p{{white-space: pre-wrap;}}</style><body><p>{tip}</p></body></html>"
        return Response(html, mimetype='text/html')
def web_camera_start():
    try:
        videolib.flask_start = True
        app.run(host='0.0.0.0', port=9000, threaded=True, debug=False)
    except Exception as e:
        print(e)
class videolib(object):
    picam2 = Picamera2()
    camera_size = (640, 480)
    camera_width = 640
    camera_height = 480
    camera_vflip = False
    camera_hflip = False
    camera_run = False
    flask_thread = None
    camera_thread = None
    flask_start = False
    qrcode_display_thread = None
    qrcode_making_completed = False
    qrcode_img = Manager().list(range(1))
    qrcode_img_encode = None
    qrcode_win_name = 'qrcode'
    img = Manager().list(range(1))
    flask_img = Manager().list(range(1))
    Windows_Name = "picamera"
    imshow_flag = False
    web_display_flag = False
    imshow_qrcode_flag = False
    web_qrcode_flag = False
    draw_fps = False
    fps_origin = (camera_width-105, 20)
    fps_size = 0.6
    fps_color = (255, 255, 255)
    detect_obj_parameter = {}
    color_detect_color = None
    face_detect_sw = False
    hands_detect_sw = False
    pose_detect_sw = False
    image_classify_sw = False
    image_classification_model = None
    image_classification_labels = None
    objects_detect_sw = False
    objects_detection_model = None
    objects_detection_labels = None
    qrcode_detect_sw = False
    traffic_detect_sw = False
    @staticmethod
    def get_instance():
        return videolib.picam2
    @staticmethod
    def set_controls(controls):
        videolib.picam2.set_controls(controls)
    @staticmethod
    def get_controls():
        return videolib.picam2.capture_metadata()
    @staticmethod
    def camera():
        videolib.camera_width = videolib.camera_size[0]
        videolib.camera_height = videolib.camera_size[1]
        picam2 = videolib.picam2
        preview_config = picam2.preview_configuration
        preview_config.size = videolib.camera_size
        preview_config.format = 'RGB888'  
        preview_config.transform = libcamera.Transform(
                                        hflip=videolib.camera_hflip,
                                        vflip=videolib.camera_vflip
                                    )
        preview_config.colour_space = libcamera.ColorSpace.Sycc()
        preview_config.buffer_count = 4
        preview_config.queue = True
        preview_config.controls = {'FrameRate': 60} 
        try:
            picam2.start()
        except Exception as e:
            print(f"\033[38;5;1mError:\033[0m\n{e}")
            print("\nPlease check whether the camera is connected well" +\
                "You can use the \"libcamea-hello\" command to test the camera"
                )
            exit(1)
        videolib.camera_run = True
        videolib.fps_origin = (videolib.camera_width-105, 20)
        fps = 0
        start_time = 0
        framecount = 0
        try:
            start_time = time.time()
            while True:
                videolib.img = picam2.capture_array()
                videolib.img = videolib.color_detect_func(videolib.img)
                videolib.img = videolib.face_detect_func(videolib.img)
                videolib.img = videolib.traffic_detect_fuc(videolib.img)
                videolib.img = videolib.qrcode_detect_func(videolib.img)
                videolib.img = videolib.image_classify_fuc(videolib.img)
                videolib.img = videolib.object_detect_fuc(videolib.img)
                videolib.img = videolib.hands_detect_fuc(videolib.img)
                videolib.img = videolib.pose_detect_fuc(videolib.img)
                framecount += 1
                elapsed_time = float(time.time() - start_time)
                if (elapsed_time > 1):
                    fps = round(framecount/elapsed_time, 1)
                    framecount = 0
                    start_time = time.time()
                if videolib.draw_fps:
                    cv2.putText(
                            videolib.img,
                            f"FPS: {fps}", 
                            videolib.fps_origin, 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            videolib.fps_size, 
                            videolib.fps_color, 
                            1, 
                            cv2.LINE_AA, 
                        )
                videolib.flask_img = videolib.img
                if videolib.imshow_flag == True:
                    try:
                        try:
                            prop = cv2.getWindowProperty(videolib.Windows_Name, cv2.WND_PROP_VISIBLE)
                            qrcode_prop = cv2.getWindowProperty(videolib.qrcode_win_name, cv2.WND_PROP_VISIBLE)
                            if prop < 1 or qrcode_prop < 1:
                                break
                        except:
                            pass
                        cv2.imshow(videolib.Windows_Name, videolib.img)
                        if videolib.imshow_qrcode_flag and videolib.qrcode_making_completed:
                                videolib.qrcode_making_completed = False
                                cv2.imshow(videolib.qrcode_win_name, videolib.qrcode_img)
                        cv2.waitKey(1)
                    except Exception as e:
                        videolib.imshow_flag = False
                        print(f"imshow failed:\n  {e}")
                        break
                if videolib.camera_run == False:
                    break
        except KeyboardInterrupt as e:
            print(e)
        finally:
            picam2.close()
            cv2.destroyAllWindows()
    @staticmethod
    def camera_start(vflip=False, hflip=False, size=None):
        if size is not None:
            videolib.camera_size = size
        videolib.camera_hflip = hflip
        videolib.camera_vflip = vflip
        videolib.camera_thread = threading.Thread(target=videolib.camera, name="videolib")
        videolib.camera_thread.daemon = False
        videolib.camera_thread.start()
        while not videolib.camera_run:
            time.sleep(0.1)
    @staticmethod
    def camera_close():
        if videolib.camera_thread != None:
            videolib.camera_run = False
            time.sleep(0.1)
    @staticmethod
    def display(local=False, web=True):
        if videolib.camera_thread != None and videolib.camera_thread.is_alive():
            if local == True:
                if 'DISPLAY' in os.environ.keys():
                    videolib.imshow_flag = True  
                    print("Imgshow start ...")
                else:
                    videolib.imshow_flag = False 
                    print("Local display failed, because there is no gui.") 
            if web == True:
                videolib.web_display_flag = True
                print("\nWeb display on:")
                wlan0, eth0 = getIP()
                if wlan0 != None:
                    print(f"      http://{wlan0}:9000/mjpg")
                if eth0 != None:
                    print(f"      http://{eth0}:9000/mjpg")
                print() 
                if videolib.flask_thread == None or videolib.flask_thread.is_alive() == False:
                    print('Starting web streaming ...')
                    videolib.flask_thread = threading.Thread(name='flask_thread',target=web_camera_start)
                    videolib.flask_thread.daemon = True
                    videolib.flask_thread.start()
        else:
            print('Error: Please execute < camera_start() > first.')
    @staticmethod
    def show_fps(color=None, fps_size=None, fps_origin=None):
        if color is not None:
            videolib.fps_color = color
        if fps_size is not None:
            videolib.fps_size = fps_size
        if fps_origin is not None:
            videolib.fps_origin = fps_origin
        videolib.draw_fps = True
    @staticmethod
    def hide_fps():
        videolib.draw_fps = False
    @staticmethod
    def take_photo(photo_name, path=DEFAULLT_PICTURES_PATH):
        if not os.path.exists(path):
            os.makedirs(name=path, mode=0o751, exist_ok=True)
            time.sleep(0.01) 
        status = False
        for _ in range(5):
            if  videolib.img is not None:
                status = cv2.imwrite(path + '/' + photo_name +'.jpg', videolib.img)
                break
            else:
                time.sleep(0.01)
        else:
            status = False
        return status
    rec_video_set = {}
    rec_video_set["fourcc"] = cv2.VideoWriter_fourcc(*'XVID') 
    rec_video_set["fps"] = 30.0
    rec_video_set["framesize"] = (640, 480)
    rec_video_set["isColor"] = True
    rec_video_set["name"] = "default"
    rec_video_set["path"] = DEFAULLT_VIDEOS_PATH
    rec_video_set["start_flag"] = False
    rec_video_set["stop_flag"] =  False
    rec_thread = None
    @staticmethod
    def rec_video_work():
        if not os.path.exists(videolib.rec_video_set["path"]):
            os.makedirs(name=videolib.rec_video_set["path"],
                        mode=0o751,
                        exist_ok=True
            )
            time.sleep(0.01)
        video_out = cv2.VideoWriter(videolib.rec_video_set["path"]+'/'+videolib.rec_video_set["name"]+'.avi',
                                    videolib.rec_video_set["fourcc"], videolib.rec_video_set["fps"], 
                                    videolib.rec_video_set["framesize"], videolib.rec_video_set["isColor"])
        while True:
            if videolib.rec_video_set["start_flag"] == True:
                video_out.write(videolib.img)
            if videolib.rec_video_set["stop_flag"] == True:
                video_out.release() 
                videolib.rec_video_set["start_flag"] == False
                break
    @staticmethod
    def rec_video_run():
        if videolib.rec_thread != None:
            videolib.rec_video_stop()
        videolib.rec_video_set["stop_flag"] = False
        videolib.rec_thread = threading.Thread(name='rec_video', target=videolib.rec_video_work)
        videolib.rec_thread.daemon = True
        videolib.rec_thread.start()
    @staticmethod
    def rec_video_start():
        videolib.rec_video_set["start_flag"] = True 
        videolib.rec_video_set["stop_flag"] = False
    @staticmethod
    def rec_video_pause():
        videolib.rec_video_set["start_flag"] = False
    @staticmethod
    def rec_video_stop():
        videolib.rec_video_set["start_flag"] == False
        videolib.rec_video_set["stop_flag"] = True
        if videolib.rec_thread != None:
            videolib.rec_thread.join(3)
            videolib.rec_thread = None
    @staticmethod 
    def color_detect(color="red"):
        '''
        :param color: could be red, green, blue, yellow , orange, purple
        '''
        videolib.color_detect_color = color
        from .color_detection import color_detect_work, color_obj_parameter
        videolib.color_detect_work = color_detect_work
        videolib.color_obj_parameter = color_obj_parameter
        videolib.detect_obj_parameter['color_x'] = videolib.color_obj_parameter['x']
        videolib.detect_obj_parameter['color_y'] = videolib.color_obj_parameter['y']
        videolib.detect_obj_parameter['color_w'] = videolib.color_obj_parameter['w']
        videolib.detect_obj_parameter['color_h'] = videolib.color_obj_parameter['h']
        videolib.detect_obj_parameter['color_n'] = videolib.color_obj_parameter['n']
    @staticmethod
    def color_detect_func(img):
        if videolib.color_detect_color is not None \
            and videolib.color_detect_color != 'close' \
            and hasattr(videolib, "color_detect_work"):
            img = videolib.color_detect_work(img, videolib.camera_width, videolib.camera_height, videolib.color_detect_color)
            videolib.detect_obj_parameter['color_x'] = videolib.color_obj_parameter['x']
            videolib.detect_obj_parameter['color_y'] = videolib.color_obj_parameter['y']
            videolib.detect_obj_parameter['color_w'] = videolib.color_obj_parameter['w']
            videolib.detect_obj_parameter['color_h'] = videolib.color_obj_parameter['h']
            videolib.detect_obj_parameter['color_n'] = videolib.color_obj_parameter['n']
        return img
    @staticmethod
    def close_color_detection():
        videolib.color_detect_color = None
    @staticmethod   
    def face_detect_switch(flag=False):
        videolib.face_detect_sw = flag
        if videolib.face_detect_sw:
            from .face_detection import face_detect, set_face_detection_model, face_obj_parameter
            videolib.face_detect_work = face_detect
            videolib.set_face_detection_model = set_face_detection_model
            videolib.face_obj_parameter = face_obj_parameter
            videolib.detect_obj_parameter['human_x'] = videolib.face_obj_parameter['x']
            videolib.detect_obj_parameter['human_y'] = videolib.face_obj_parameter['y']
            videolib.detect_obj_parameter['human_w'] = videolib.face_obj_parameter['w']
            videolib.detect_obj_parameter['human_h'] = videolib.face_obj_parameter['h']
            videolib.detect_obj_parameter['human_n'] = videolib.face_obj_parameter['n']
    @staticmethod
    def face_detect_func(img):
        if videolib.face_detect_sw and hasattr(videolib, "face_detect_work"):
            img = videolib.face_detect_work(img, videolib.camera_width, videolib.camera_height)
            videolib.detect_obj_parameter['human_x'] = videolib.face_obj_parameter['x']
            videolib.detect_obj_parameter['human_y'] = videolib.face_obj_parameter['y']
            videolib.detect_obj_parameter['human_w'] = videolib.face_obj_parameter['w']
            videolib.detect_obj_parameter['human_h'] = videolib.face_obj_parameter['h']
            videolib.detect_obj_parameter['human_n'] = videolib.face_obj_parameter['n']
        return img
    @staticmethod
    def traffic_detect_switch(flag=False):
        videolib.traffic_detect_sw  = flag
        if videolib.traffic_detect_sw:
            from .traffic_sign_detection import traffic_sign_detect, traffic_sign_obj_parameter
            videolib.traffic_detect_work = traffic_sign_detect
            videolib.traffic_sign_obj_parameter = traffic_sign_obj_parameter
            videolib.detect_obj_parameter['traffic_sign_x'] = videolib.traffic_sign_obj_parameter['x']
            videolib.detect_obj_parameter['traffic_sign_y'] = videolib.traffic_sign_obj_parameter['y']
            videolib.detect_obj_parameter['traffic_sign_w'] = videolib.traffic_sign_obj_parameter['w']
            videolib.detect_obj_parameter['traffic_sign_h'] = videolib.traffic_sign_obj_parameter['h']
            videolib.detect_obj_parameter['traffic_sign_t'] = videolib.traffic_sign_obj_parameter['t']
            videolib.detect_obj_parameter['traffic_sign_acc'] = videolib.traffic_sign_obj_parameter['acc']
    @staticmethod
    def traffic_detect_fuc(img):
        if videolib.traffic_detect_sw and hasattr(videolib, "traffic_detect_work"):
            img = videolib.traffic_detect_work(img, border_rgb=(255, 0, 0))
            videolib.detect_obj_parameter['traffic_sign_x'] = videolib.traffic_sign_obj_parameter['x']
            videolib.detect_obj_parameter['traffic_sign_y'] = videolib.traffic_sign_obj_parameter['y']
            videolib.detect_obj_parameter['traffic_sign_w'] = videolib.traffic_sign_obj_parameter['w']
            videolib.detect_obj_parameter['traffic_sign_h'] = videolib.traffic_sign_obj_parameter['h']
            videolib.detect_obj_parameter['traffic_sign_t'] = videolib.traffic_sign_obj_parameter['t']
            videolib.detect_obj_parameter['traffic_sign_acc'] = videolib.traffic_sign_obj_parameter['acc']
        return img
    @staticmethod
    def qrcode_detect_switch(flag=False):
        videolib.qrcode_detect_sw  = flag
        if videolib.qrcode_detect_sw:
            from .qrcode_recognition import qrcode_recognize, qrcode_obj_parameter
            videolib.qrcode_recognize = qrcode_recognize
            videolib.qrcode_obj_parameter = qrcode_obj_parameter
            videolib.detect_obj_parameter['qr_x'] = videolib.qrcode_obj_parameter['x']
            videolib.detect_obj_parameter['qr_y'] = videolib.qrcode_obj_parameter['y']
            videolib.detect_obj_parameter['qr_w'] = videolib.qrcode_obj_parameter['w']
            videolib.detect_obj_parameter['qr_h'] = videolib.qrcode_obj_parameter['h']
            videolib.detect_obj_parameter['qr_data'] = videolib.qrcode_obj_parameter['data']
            videolib.detect_obj_parameter['qr_list'] = videolib.qrcode_obj_parameter['list']
    @staticmethod
    def qrcode_detect_func(img):
        if videolib.qrcode_detect_sw and hasattr(videolib, "qrcode_recognize"):
            img = videolib.qrcode_recognize(img, border_rgb=(255, 0, 0))
            videolib.detect_obj_parameter['qr_x'] = videolib.qrcode_obj_parameter['x']
            videolib.detect_obj_parameter['qr_y'] = videolib.qrcode_obj_parameter['y']
            videolib.detect_obj_parameter['qr_w'] = videolib.qrcode_obj_parameter['w']
            videolib.detect_obj_parameter['qr_h'] = videolib.qrcode_obj_parameter['h']
            videolib.detect_obj_parameter['qr_data'] = videolib.qrcode_obj_parameter['data']
        return img
    @staticmethod
    def make_qrcode(data, 
                    path=None,
                    version=1,
                    box_size=10,
                    border=4,
                    fill_color=(132,  112, 255),
                    back_color=(255, 255, 255)
                    ):
        import qrcode 
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr_pil = qr.make_image(fill_color=fill_color,
                            back_color=back_color)
        if path != None:
            qr_pil.save(path)
        videolib.qrcode_img = cv2.cvtColor(np.array(qr_pil), cv2.COLOR_RGB2BGR)
        videolib.qrcode_making_completed = True
        if videolib.web_qrcode_flag:
            videolib.qrcode_img_encode = cv2.imencode('.jpg', videolib.qrcode_img)[1].tobytes()
    @staticmethod
    def display_qrcode_work():
        while True:
            if videolib.imshow_flag:
                time.sleep(0.1)
                continue
            if videolib.imshow_qrcode_flag and videolib.qrcode_making_completed :
                    videolib.qrcode_making_completed = False
                    try:
                        if len(videolib.qrcode_img) > 10:
                            cv2.imshow(videolib.qrcode_win_name, videolib.qrcode_img)
                            cv2.waitKey(1)
                            if cv2.getWindowProperty(videolib.qrcode_win_name, cv2.WND_PROP_VISIBLE) == 0:
                                cv2.destroyWindow(videolib.qrcode_win_name)
                    except Exception as e:
                        videolib.imshow_qrcode_flag = False
                        print(f"imshow qrcode failed:\n  {e}")
                        break
            time.sleep(0.1)
    @staticmethod
    def display_qrcode(local=False, web=True):
        if local == True:
            if 'DISPLAY' in os.environ.keys():
                videolib.imshow_qrcode_flag = True  
                print("Imgshow qrcode start ...")
            else:
                videolib.imshow_qrcode_flag = False 
                print("Local display failed, because there is no gui.") 
        if web == True:
            videolib.web_qrcode_flag = True
            print(f'QRcode display on:')
            wlan0, eth0 = getIP()
            if wlan0 != None:
                print(f"      http://{wlan0}:9000/qrcode")
            if eth0 != None:
                print(f"      http://{eth0}:9000/qrcode")
            print() 
            if videolib.flask_thread == None or videolib.flask_thread.is_alive() == False:
                print('Starting web streaming ...')
                videolib.flask_thread = threading.Thread(name='flask_thread',target=web_camera_start)
                videolib.flask_thread.daemon = True
                videolib.flask_thread.start()
        if videolib.qrcode_display_thread == None or videolib.qrcode_display_thread.is_alive() == False:
            videolib.qrcode_display_thread = threading.Thread(name='qrcode_display',target=videolib.display_qrcode_work)
            videolib.qrcode_display_thread.daemon = True
            videolib.qrcode_display_thread.start()
    @staticmethod
    def image_classify_switch(flag=False):
        from .image_classification import image_classification_obj_parameter
        videolib.image_classify_sw = flag
        videolib.image_classification_obj_parameter = image_classification_obj_parameter
    @staticmethod
    def image_classify_set_model(path):
        if not os.path.exists(path):
            raise ValueError('incorrect model path ')          
        videolib.image_classification_model = path
    @staticmethod
    def image_classify_set_labels(path):
        if not os.path.exists(path):
            raise ValueError('incorrect labels path ')  
        videolib.image_classification_labels = path
    @staticmethod
    def image_classify_fuc(img):
        if videolib.image_classify_sw == True:
            from .image_classification import classify_image
            img = classify_image(image=img,
                                model=videolib.image_classification_model,
                                labels=videolib.image_classification_labels)   
        return img
    @staticmethod
    def object_detect_switch(flag=False):
        videolib.objects_detect_sw = flag
        if videolib.objects_detect_sw == True:
            from .objects_detection import object_detection_list_parameter
            videolib.object_detection_list_parameter = object_detection_list_parameter
    @staticmethod
    def object_detect_set_model(path):
        if not os.path.exists(path):
            raise ValueError('incorrect model path ')    
        videolib.objects_detection_model = path
    @staticmethod
    def object_detect_set_labels(path):
        if not os.path.exists(path):
            raise ValueError('incorrect labels path ')    
        videolib.objects_detection_labels = path
    @staticmethod
    def object_detect_fuc(img):
        if videolib.objects_detect_sw == True:
            from .objects_detection import detect_objects
            img = detect_objects(image=img,
                                model=videolib.objects_detection_model,
                                labels=videolib.objects_detection_labels)   
        return img
    @staticmethod
    def hands_detect_switch(flag=False):
        from .hands_detection import DetectHands
        videolib.detect_hands = DetectHands()
        videolib.hands_detect_sw = flag
    @staticmethod
    def hands_detect_fuc(img):
        if videolib.hands_detect_sw == True:
            img, videolib.detect_obj_parameter['hands_joints'] = videolib.detect_hands.work(image=img)   
        return img
    @staticmethod
    def pose_detect_switch(flag=False):
        from .pose_detection import DetectPose
        videolib.pose_detect = DetectPose()
        videolib.pose_detect_sw = flag
    @staticmethod
    def pose_detect_fuc(img):
        if videolib.pose_detect_sw == True and hasattr(videolib, "pose_detect"):
            img, videolib.detect_obj_parameter['body_joints'] = videolib.pose_detect.work(image=img)   
        return img
