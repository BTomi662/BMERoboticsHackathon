import cv2
import requests
import numpy as np

# Replace with your ESP32-S3 IP address
# Note: The original Arduino code serves the stream directly at the root "/" URL
STREAM_URL = "http://10.84.7.72"

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
            
            if frame is not None:
                # Display the live image in a window
                cv2.imshow("ESP32-S3 OV5640 Stream", frame)
            
            # Keep the window responsive. Press 'q' to close it.
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()