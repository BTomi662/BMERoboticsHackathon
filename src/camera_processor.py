import cv2
import requests
import numpy as np
import math

# Replace with your ESP32-S3 IP address
# Note: The original Arduino code serves the stream directly at the root "/" URL
STREAM_URL = "http://10.84.7.72"


kernal = np.ones((5, 5), "uint8")


RED = cv2.cvtColor(np.uint8([[[0, 0, 230]]]),cv2.COLOR_BGR2HSV)[0][0]
RED[0] = 165
GREEN = cv2.cvtColor(np.uint8([[[0, 255, 0]]]),cv2.COLOR_BGR2HSV)[0][0]
BLUE = cv2.cvtColor(np.uint8([[[255, 0, 0]]]),cv2.COLOR_BGR2HSV)[0][0]
YELLOW = cv2.cvtColor(np.uint8([[[0, 255, 255]]]),cv2.COLOR_BGR2HSV)[0][0]

print("RED: ", RED,type(RED))
print("GREEN", GREEN)
print("BLUE", BLUE)
print("YELLOW", YELLOW)

CALIBRATION_COLOR = YELLOW
PLAYER_COLOR = GREEN
ROBOT_COLOR = YELLOW


def calibrateColor():
    pass



def maskFrame(frame, mask_color,radius:int):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    color_lower = np.array([(mask_color[0]-radius)%180,80,60], np.uint8)
    color_upper = np.array([(mask_color[0]+radius)%180,255,255], np.uint8)

    #color_lower = np.array([136, 87, 111], np.uint8)
    #color_upper = np.array([180, 255, 255], np.uint8)
    color_mask = cv2.inRange(hsv_frame, color_lower, color_upper)

    color_mask = cv2.dilate(color_mask, kernal)
    res_color = cv2.bitwise_and(frame, frame, mask=color_mask)

    return color_mask



def getItemPos(frame, color_mask, label:str="Item"):
    items = []
    contours, hierarchy = cv2.findContours(color_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for pic, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if (area > 300):
            x, y, w, h = cv2.boundingRect(contour)
            frame = cv2.rectangle(frame, (x, y),
                                    (x + w, y + h),
                                    (0, 0, 255), 2)
            frame = cv2.circle(frame, (x+w//2,y+h//2),5,(0,0,255),-1)

            cv2.putText(frame, label, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (0, 0, 255))

            items.append([label,x+w//2,y+h//2])

    return frame, items



def calibrateLength(frame,calib_color):
    calib_mask = maskFrame(frame,calib_color,15)
    frame, calib_points = getItemPos(frame,calib_mask,"Calibration Points")
    dx = dy = 0
    if len(calib_points) != 4:
        print("Calibration error: Not enough points",len(calib_points))
        return frame, None, None, None
    _x = [p[1] for p in calib_points]
    _y = [p[2] for p in calib_points]
    avg_x = sum(_x)/len(_x)
    avg_y = sum(_y)/len(_y)


    P1=P2=P3=P4 = None
    for p in calib_points:
        if p[1] < avg_x and p[2] < avg_y: P1 = p
        if p[1] < avg_x and p[2] > avg_y: P2 = p
        if p[1] > avg_x and p[2] < avg_y: P3 = p
        if p[1] > avg_x and p[2] > avg_y: P4 = p

    dx1 = math.sqrt(math.pow(abs(P1[1]-P4[1]),2)+math.pow(abs(P1[2]-P4[2]),2))
    dx2 = math.sqrt(math.pow(abs(P2[1]-P3[1]),2)+math.pow(abs(P2[2]-P3[2]),2))
    dx = (dx1+dx2)/2

    dy1 = math.sqrt(math.pow(abs(P1[1]-P2[1]),2)+math.pow(abs(P1[2]-P2[2]),2))
    dy2 = math.sqrt(math.pow(abs(P3[1]-P4[1]),2)+math.pow(abs(P3[2]-P4[2]),2))
    dy = (dy1+dy2)/2

    return frame, dx, dy, P1



def generateGrid(frame,x_div,y_div):
    dx=dy = None
    
    frame, dx, dy, P1 = calibrateLength(frame,CALIBRATION_COLOR)
    print("dx: ",dx, "dy: ",dy)
    if dx is None or dy is None:
        return frame, None, None

    _dx = dx//x_div
    _dy = dy//y_div

    x_scale = [int((P1[1])+i*_dx) for i in range(x_div)]
    y_scale = [int((P1[2])+i*_dy) for i in range(y_div)]

    return frame, x_scale, y_scale



def getCoords(frame, items, x_scale, y_scale):
    coords = [[0,0] for _ in range(len(items))]

    for i in range(len(items)):
        for si in range(2):
            scale = [x_scale, y_scale][si]
            for k in range(len(scale)-1):
                if scale[k] < items[i][si+1] < scale[k+1]:
                    print(scale[k],scale[k+1],items[i][si],"IIIII",i,si)
                    coords[i][si] = k+1
                    break
                   
    return coords

            

             





def main():
    calibrating = False
    calibrated = False
    
    print(f"Connecting to ESP32-S3 stream at: {STREAM_URL}")
    print("Press 'q' in the graphics window to exit.")

    # Open a persistent HTTP connection to stream the data bytes
    stream = requests.get(STREAM_URL, stream=True)
    
    if stream.status_code != 200:
        print(f"Failed to connect to the server. Status code: {stream.status_code}")
        return

    bytes_accumulator = bytes()

    x_scale=y_scale=None

    # Read the stream chunk-by-chunk
    for chunk in stream.iter_content(chunk_size=1024):
        
        bytes_accumulator += chunk
        
        # JPEG images always start with the bytes 0xff 0xd8 and end with 0xff 0xd9
        a = bytes_accumulator.find(b'\xff\xd8')
        b = bytes_accumulator.find(b'\xff\xd9')
        
        # If we have a complete JPEG frame in our buffer
        if a != -1 and b != -1:
            jpg_data = bytes_accumulator[a:b+2]
            # Keep any remaining bytes belonging to the next frame
            bytes_accumulator = bytes_accumulator[b+2:]
            
            # Decode the JPEG bytes into an OpenCV image array
            frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            if calibrating and (x_scale is None or y_scale is None):
                frame,x_scale,y_scale = generateGrid(frame,8,8)
            elif calibrating:
                calibrating = False
                calibrated = True
                
            if calibrated:
                #print("SCALES: ",x_scale,y_scale)
                for x in x_scale:      
                    frame = cv2.line(frame, (x,y_scale[0]),(x,y_scale[-1]),(100,100,100),1)
    
                for y in y_scale:      
                    frame = cv2.line(frame, (x_scale[0],y),(x_scale[-1],y),(100,100,100),1)
                

            items = []
            
            yellow_mask = maskFrame(frame,YELLOW,10)
            frame, _items = getItemPos(frame,yellow_mask,"Yellow")

            items += _items

            blue_mask = maskFrame(frame,BLUE,10)
            frame, _items = getItemPos(frame,blue_mask,"Blue")

            items += _items

            green_mask = maskFrame(frame,GREEN,10)
            frame, _items = getItemPos(frame,green_mask,"Green")

            items += _items

            red_mask = maskFrame(frame,RED,10)
            frame, _items = getItemPos(frame,red_mask,"Red")

            items += _items

            if calibrated:
                filtered_items = [i for i in items if i[0] == "Green"]
                coords = getCoords(frame, filtered_items, x_scale, y_scale)
                print("COORDS: ",coords)
            
            
            if frame is not None:
                # Display the live image in a window
                cv2.imshow("ESP32-S3 OV5640 Stream", frame)
            
            # Keep the window responsive. Press 'q' to close it.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if cv2.waitKey(1) & 0xFF == ord('c'):
                calibrating = True

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()