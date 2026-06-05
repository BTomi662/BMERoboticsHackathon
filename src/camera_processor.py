import cv2
import requests
import numpy as np
import math

# Replace with your ESP32-S3 IP address
# Note: The original Arduino code serves the stream directly at the root "/" URL
STREAM_URL = "http://10.84.7.72"


kernal = np.ones((5, 5), "uint8")


mouse_x = 0
mouse_y = 0


class Player:
    def __init__(self, label, color):
        self.label = label
        self.color = color

    def set_color(self,color):
        self.color = color

class Color:
    def __init__(self, name, BGRvalue):
        self.name = name
        self.BRG = BGRvalue
        self.HSV = cv2.cvtColor(np.uint8([[self.BRG]]),cv2.COLOR_BGR2HSV)[0][0]




RED = Color("RED",[0,0,230])
GREEN = Color("GREEN",[0,255,0])
BLUE = Color("BLUE",[255,0,0])
YELLOW = Color("YELLOW",[0,255,255])
COLORS:list[Color] = [RED, GREEN, BLUE, YELLOW]

CALIBRATION_COLOR = YELLOW

HUMAN = Player("human",RED)
ROBOT = Player("robot",BLUE)
PLAYERS = [HUMAN, ROBOT]



def getMousePos(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x,mouse_y = x,y


def calibrateColor(frame):
    color = frame[mouse_x,mouse_y]
    print(color)
    color = cv2.cvtColor(np.uint8([[color]]),cv2.COLOR_BGR2HSV)[0][0]
    return color



def maskFrame(frame, mask_color,radius:int):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    color_lower = np.array([(mask_color.HSV[0]-radius)%180,80,60], np.uint8)
    color_upper = np.array([(mask_color.HSV[0]+radius)%180,255,255], np.uint8)

    color_mask = cv2.inRange(hsv_frame, color_lower, color_upper)

    color_mask = cv2.dilate(color_mask, kernal)
    res_color = cv2.bitwise_and(frame, frame, mask=color_mask)

    return color_mask



def getColorPos(frame, color_mask, label:str="Item"):
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

            items.append([x+w//2,y+h//2])

    return frame, items



def calibrateLength(frame,calib_color):
    calib_mask = maskFrame(frame, calib_color, 15)
    frame, calib_points = getColorPos(frame, calib_mask, "Calibration Points")
    
    if len(calib_points) != 4:
        print("Calibration error: Not exactly 4 points found. Detected:", len(calib_points))
        return frame, None, None, None

    # Convert to a numpy array for easy manipulation
    pts = np.array(calib_points)
    
    # Sort based on x + y sum
    # Top-Left will have the smallest sum, Bottom-Right will have the largest sum
    sum_pts = pts.sum(axis=1)
    P1 = pts[np.argmin(sum_pts)].tolist()  # Top-Left
    P3 = pts[np.argmax(sum_pts)].tolist()  # Bottom-Right
    
    # Sort based on x - y difference
    # Top-Right will have the largest difference, Bottom-Left will have the smallest
    diff_pts = np.diff(pts, axis=1).flatten()
    P2 = pts[np.argmax(diff_pts)].tolist()  # Bottom-Left (Large y, Small x -> y-x is max, x-y is min)
    P4 = pts[np.argmin(diff_pts)].tolist()  # Top-Right (Small y, Large x -> x-y is max, y-x is min)

    # Double check protection to prevent future subscriptable errors
    if not (P1 and P2 and P3 and P4):
        print("Calibration error: Failed to map discrete corners unique positions.")
        return frame, None, None, None

    dx1 = math.sqrt(math.pow(abs(P1[0]-P4[0]),2)+math.pow(abs(P1[1]-P4[1]),2))
    dx2 = math.sqrt(math.pow(abs(P2[0]-P3[0]),2)+math.pow(abs(P2[1]-P3[1]),2))
    dx = (dx1+dx2)/2

    dy1 = math.sqrt(math.pow(abs(P1[0]-P2[0]),2)+math.pow(abs(P1[1]-P2[1]),2))
    dy2 = math.sqrt(math.pow(abs(P3[0]-P4[0]),2)+math.pow(abs(P3[1]-P4[1]),2))
    dy = (dy1+dy2)/2

    return frame, dx, dy, P1



def generateGrid(frame,x_div,y_div, offset):
    dx=dy = None
    
    frame, dx, dy, P1 = calibrateLength(frame,CALIBRATION_COLOR)
    print("dx: ",dx, "dy: ",dy)
    if dx is None or dy is None:
        return frame, None, None

    _dx = dx//x_div
    _dy = dy//y_div

    x_scale = [int((P1[0]+_dx*offset)+i*_dx) for i in range(x_div)]
    y_scale = [int((P1[1]+_dx*offset)+i*_dy) for i in range(y_div)]

    return frame, x_scale, y_scale



def drawGrid(frame, x_scale, y_scale):
    for x in x_scale:      
        frame = cv2.line(frame, (x,y_scale[0]),(x,y_scale[-1]),(100,100,100),1)
    for y in y_scale:      
        frame = cv2.line(frame, (x_scale[0],y),(x_scale[-1],y),(100,100,100),1)
    
    return frame



def getCoords(items, x_scale, y_scale):
    coords = [[0,0] for _ in range(len(items))]

    for i in range(len(items)):
        for si in range(2):
            scale = [x_scale, y_scale][si]
            for k in range(len(scale)-1):
                if scale[k] < items[i][si] < scale[k+1]:
                    coords[i][si] = k+1
                    break                  
    return coords

            

def detectCircles(frame):
    items = []

    # Keep a copy of the original image to draw results on
    output = frame.copy()

    # 2. Pre-processing: Convert to Grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 3. Pre-processing: Apply Gaussian Blur to reduce noise
    # (A 9x9 kernel size works well; adjust based on image noise)
    gray_blurred = cv2.GaussianBlur(gray, (9, 9), 2)

    # 4. Apply Hough Circle Transform
    # Parameters explained below:
    circles = cv2.HoughCircles(
        gray_blurred, 
        cv2.HOUGH_GRADIENT, 
        dp=1,          # Inverse ratio of the accumulator resolution to the image resolution
        minDist=50,    # Minimum distance between the centers of detected circles
        param1=50,     # Higher threshold passed to the Canny edge detector
        param2=30,     # Accumulator threshold for the circle centers (lower = more circles detected)
        minRadius=10,  # Minimum circle radius to detect
        maxRadius=100  # Maximum circle radius to detect
    )

    # 5. Check if any circles were found
    if circles is not None:
        # Convert the circle parameters a, b, and r to integers
        circles = np.uint16(np.around(circles))

        #print(f"Detected {len(circles[0])} circle(s).")

        for i in circles[0, :]:
            center_x, center_y, radius = i[0], i[1], i[2]
            
            cv2.circle(output, (center_x, center_y), radius, (0, 255, 0), 2)
            cv2.circle(output, (center_x, center_y), 5, (0, 0, 255), 1)

            items.append([center_x, center_y])
    else:
        ##print("No circles were detected.")
        pass

    return output, items            



def getPixelColor(img, coord, brightness_threshold=30) -> Color | None:
    """
    Evaluates the average color in a 5-pixel radius around the given coordinate,
    and returns the matching Color object (RED, GREEN, or BLUE) based on 
    the dominant average component.
    """
    x, y = coord
    print(coord,x,y)
    radius = 1
    #img = cv2.cvtColor(img, cv2.COLOR_HSV2BGR)

    # 1. Define the bounding box bounds for the 5-pixel radius area
    y_min = max(0, y - radius)
    y_max = min(img.shape[0], y + radius + 1)
    x_min = max(0, x - radius)
    x_max = min(img.shape[1], x + radius + 1)

    # 2. Extract the sub-matrix (Region of Interest) around the point
    roi = img[y_min:y_max, x_min:x_max]

    # Ensure the region isn't empty (e.g., if clicked completely out of bounds)
    if roi.size == 0:
        return None

    # 3. Calculate the average B, G, R values across the entire region
    # cv2.mean returns a tuple of 4 values: (Mean_B, Mean_G, Mean_R, Mean_Alpha)
    mean_b, mean_g, mean_r, _ = cv2.mean(roi)

    print(mean_b, mean_g, mean_r)

    # 4. Safety Check: If the average brightness is too dark, classify as noise/None
    if (mean_r + mean_g + mean_b) < brightness_threshold:
        return None

    # 5. Determine the dominant channel based on the calculated averages
    if mean_r >= mean_g and mean_r >= mean_b:
        # Red is dominant
        for col in COLORS:
            if col.name == "RED":
                return col
                
    elif mean_g >= mean_r and mean_g >= mean_b:
        # Green is dominant
        for col in COLORS:
            if col.name == "GREEN":
                return col
                
    elif mean_b >= mean_r and mean_b >= mean_g:
        # Blue is dominant
        for col in COLORS:
            if col.name == "BLUE":
                return col

    return None
            
def classifyItem(frame,coordinates):
    labeled_coords = []
    for coor in coordinates:
        color:Color = getPixelColor(frame,coor)
        if color is None: continue
        print(color.name)
        for player in PLAYERS:
            if color.name == player.color.name:
                labeled_coords.append([player, coor])
                print(labeled_coords,color.name)
                break
    return labeled_coords

            
def convertToMisiFormat(coordinates):
    output={}
    for coord in coordinates:
        _id = coord[1][0]*10+coord[1][1]
        player = "player"+str(PLAYERS.index(coord[0])+1)

        output[_id] = player
        print(output[_id],_id)

    return output


LATEST_BOARD_STATE = {}

def main():
    global LATEST_BOARD_STATE
    calibrating = False
    calibrated = False
    x_scale=None
    y_scale=None
    
    print(f"Connecting to ESP32-S3 stream at: {STREAM_URL}")
    print("Press 'q' in the graphics window to exit.")

    # Open a persistent HTTP connection to stream the data bytes
    stream = requests.get(STREAM_URL, stream=True)
    
    if stream.status_code != 200:
        print(f"Failed to connect to the server. Status code: {stream.status_code}")
        return

    bytes_accumulator = bytes()



    # Read the stream chunk-by-chunk
    for chunk in stream.iter_content(chunk_size=1024):
        
        bytes_accumulator += chunk
        
        # JPEG images always start with the bytes 0xff 0xd8 and end with 0xff 0xd9
        a = bytes_accumulator.find(b'\xff\xd8')
        b = bytes_accumulator.find(b'\xff\xd9')
        
        # If we have a complete JPEG frame in our buffer
        if a != -1 and b != -1:
            if b > a:  # Ensure the end marker actually comes after the start marker
                jpg_data = bytes_accumulator[a:b+2]
                # Keep any remaining bytes belonging to the next frame
                bytes_accumulator = bytes_accumulator[b+2:]
                
                # Check that we actually have substantial byte data before giving it to numpy
                if len(jpg_data) > 0:
                    img_buffer = np.frombuffer(jpg_data, dtype=np.uint8)
                    
                    # Safety check: Ensure the buffer isn't empty before calling imdecode
                    if img_buffer.size > 0:
                        frame = cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)
                        
                        # Verify OpenCV successfully turned the bytes into an image
                        if frame is None:
                            print("Warning: Dropped a corrupted frame (OpenCV decode failed).")
                            continue
                    else:
                        continue
            else:
                # If 'b' happened to be before 'a' due to old buffer remnants, 
                # clear out the corrupted section up to 'a' and try again.
                bytes_accumulator = bytes_accumulator[a:]
            
            # Decode the JPEG bytes into an OpenCV image array
            frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            if calibrating:
                frame,x_scale,y_scale = generateGrid(frame,8,8,0.5)
                if x_scale and y_scale:
                    calibrating = False
                    calibrated = True
            elif calibrated:
                drawGrid(frame,x_scale, y_scale)
            
                

            frame, items = detectCircles(frame)

            if calibrated:
                coords = getCoords(items, x_scale, y_scale)
                #print("COORDS: ",coords)
                classified = classifyItem(frame,items)
                players = [[sublist[0], item_b] for sublist, item_b in zip(classified, coords)]
                if players: LATEST_BOARD_STATE = convertToMisiFormat(players)
                


            if frame is not None:
                # Display the live image in a window
                cv2.imshow("ESP32-S3 OV5640 Stream", frame)
            
            # Keep the window responsive. Press 'q' to close it.
            key = cv2.waitKey(1) & 0xFF 
            if key == ord('q'):
                break
            if key == ord('c'):
                calibrating = True
                calibrated = False

    cv2.destroyAllWindows()

    
if __name__ == "__main__":
    main()