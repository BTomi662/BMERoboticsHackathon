import cv2
import requests
import numpy as np

# Replace with your ESP32-S3 IP address
# Note: The original Arduino code serves the stream directly at the root "/" URL
STREAM_URL = "http://10.84.7.72"


kernal = np.ones((5, 5), "uint8")

# Set range for red color 
red_lower = np.array([136, 87, 111], np.uint8)
red_upper = np.array([180, 255, 255], np.uint8)
#green color
green_lower = np.array([25, 52, 72], np.uint8)
green_upper = np.array([102, 255, 255], np.uint8)
#blue color
blue_lower = np.array([94, 80, 2], np.uint8)
blue_upper = np.array([120, 255, 255], np.uint8)


def calibrateColor():
    pass

def maskFrame(frame, mask_color:list[int,int,int],color_radius:int):
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    #TODO: better way to make colors alike
    color_lower = np.array([x-color_radius if x-color_radius>0 else x-color_radius+255 for x in mask_color], np.uint8)
    color_upper = np.array([mask_color[0]+color_radius,255,255], np.uint8)
    color_lower = np.array([136, 87, 111], np.uint8)
    color_upper = np.array([180, 255, 255], np.uint8)
    color_mask = cv2.inRange(hsv_frame, color_lower, color_upper)

    color_mask = cv2.dilate(color_mask, kernal)
    res_color = cv2.bitwise_and(frame, frame, mask=color_mask)

    return color_mask

def getItemPos(frame, color_mask, label:str="Item"):
    #x=y=w=h = None
    items = []
    contours, hierarchy = cv2.findContours(color_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for pic, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if (area > 300):
            x, y, w, h = cv2.boundingRect(contour)
            frame = cv2.rectangle(frame, (x, y),
                                    (x + w, y + h),
                                    (0, 0, 255), 2)

            cv2.putText(frame, label, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (0, 0, 255))

            items.append([label,x,y,w,h])

    return frame, items



def main():
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
            jpg_data = bytes_accumulator[a:b+2]
            # Keep any remaining bytes belonging to the next frame
            bytes_accumulator = bytes_accumulator[b+2:]
            
            # Decode the JPEG bytes into an OpenCV image array
            frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            items = []
            
            red_mask = maskFrame(frame,[140,30,30],50)
            frame, _items = getItemPos(frame,red_mask,"Red Color")

            items += _items

            red_mask = maskFrame(frame,[100,30,30],50)
            frame, _items = getItemPos(frame,red_mask,"Blue Color")

            items += _items

            items2 = [i[1:] for i in items if i[0]=="Red Color"]
            if _items != []:
                print(items)
                print(items2)

            
            
            
            if frame is not None:
                # Display the live image in a window
                cv2.imshow("ESP32-S3 OV5640 Stream", frame)
            
            # Keep the window responsive. Press 'q' to close it.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()