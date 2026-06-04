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


def main():
    print(True)
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
            hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # define mask
            red_mask = cv2.inRange(hsvFrame, red_lower, red_upper)
            green_mask = cv2.inRange(hsvFrame, green_lower, green_upper)
            blue_mask = cv2.inRange(hsvFrame, blue_lower, blue_upper)

            # red color
            red_mask = cv2.dilate(red_mask, kernal)
            res_red = cv2.bitwise_and(frame, frame, mask=red_mask)

            # green color
            green_mask = cv2.dilate(green_mask, kernal)
            res_green = cv2.bitwise_and(frame, frame, mask=green_mask)

            # blue color
            blue_mask = cv2.dilate(blue_mask, kernal)
            res_blue = cv2.bitwise_and(frame, frame, mask=blue_mask)

            contours, hierarchy = cv2.findContours(red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            for pic, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if (area > 300):
                    x, y, w, h = cv2.boundingRect(contour)
                    frame = cv2.rectangle(frame, (x, y),
                                            (x + w, y + h),
                                            (0, 0, 255), 2)

                    cv2.putText(frame, "Red Colour", (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                                (0, 0, 255))

            # Creating contour to track green color
            contours, hierarchy = cv2.findContours(green_mask,
                                                cv2.RETR_TREE,
                                                cv2.CHAIN_APPROX_SIMPLE)

            for pic, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if (area > 300):
                    x, y, w, h = cv2.boundingRect(contour)
                    frame = cv2.rectangle(frame, (x, y),
                                            (x + w, y + h),
                                            (0, 255, 0), 2)

                    cv2.putText(frame, "Green Colour", (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1.0, (0, 255, 0))

            # Creating contour to track blue color
            contours, hierarchy = cv2.findContours(blue_mask,
                                                cv2.RETR_TREE,
                                                cv2.CHAIN_APPROX_SIMPLE)
            for pic, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if (area > 300):
                    x, y, w, h = cv2.boundingRect(contour)
                    frame = cv2.rectangle(frame, (x, y),
                                            (x + w, y + h),
                                            (255, 0, 0), 2)

                    cv2.putText(frame, "Blue Colour", (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1.0, (255, 0, 0))

            
            
            if frame is not None:
                # Display the live image in a window
                cv2.imshow("ESP32-S3 OV5640 Stream", frame)
            
            # Keep the window responsive. Press 'q' to close it.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()