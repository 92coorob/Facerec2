'''
Main program
@Author: David Vu

To execute simply run:
main.py

To input new user:
main.py --mode "input"

'''

import cv2
from align_custom import AlignCustom
from face_feature import FaceFeature
from mtcnn_detect import MTCNNDetect
from tf_graph import FaceRecGraph
from datetime import date
import calendar
import argparse
import sys
import json
import csv
import time
import numpy as np
import datetime
import pyrebase
import datetime
import pyttsx3;
now = datetime.datetime.now()
engine = pyttsx3.init();

config = {
  "apiKey": "Insert your own key",
  "authDomain": "Insert your own domain.firebaseapp.com",
  "databaseURL": "https://Insert your own URL.firebaseio.com",
  "storageBucket": "Insert your own Storage bucket.appspot.com"
}
firebase = pyrebase.initialize_app(config)
# Get a reference to the auth service
auth = firebase.auth()
email = "Insert your own email"
password = "Insert your own password"
DataIn = "facerec_128D.txt"
DataOut = "facerec_128D.txt"
#auth.create_user_with_email_and_password(email, password)
# Log the user in
user = auth.sign_in_with_email_and_password("Insert your own email", "Insert your own password")
db = firebase.database()

#TIMEOUT = 10 #10 seconds
currentDT = datetime.datetime.now()

def main(args):
    mode = args.mode
    if(mode == "camera"):
        camera_recog()
    elif mode == "input":
        create_manual_data();
    elif mode =="delete":
        deleteV3(DataIn, DataOut)
    else:
        raise ValueError("Unimplemented mode")
'''
Description:
Images from Video Capture -> detect faces' regions -> crop those faces and align them
    -> each cropped face is categorized in 3 types: Center, Left, Right
    -> Extract 128D vectors( face features)
    -> Search for matching subjects in the dataset based on the types of face positions.
    -> The preexisitng face 128D vector with the shortest distance to the 128D vector of the face on screen is most likely a match
    (Distance threshold is 0.6, percentage threshold is 70%)

'''
def camera_recog():
    FRGraph = FaceRecGraph();
    MTCNNGraph = FaceRecGraph();
    extract_feature = FaceFeature(FRGraph)
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2); #scale_factor, rescales image for faster detection
    print("[INFO] camera sensor warming up...")
    vs = cv2.VideoCapture(0); #get input from webcam
    detect_time = time.time()
    while True:
        _,frame = vs.read();
        #u can certainly add a roi here but for the sake of a demo i'll just leave it as simple as this
        rects, landmarks = face_detect.detect_face(frame,20);#min face size is set to 80x80
        aligns = []
        positions = []

        for (i, rect) in enumerate(rects):
            aligned_face, face_pos = aligner.align(160,frame,landmarks[:,i])
            if len(aligned_face) == 160 and len(aligned_face[0]) == 160:
                aligns.append(aligned_face)
                positions.append(face_pos)
            else:
                print("Align face failed") #log
        if(len(aligns) > 0):
            features_arr = extract_feature.get_features(aligns)
            recog_data = findPeople(features_arr,positions)


            for (i,rect) in enumerate(rects):
                cv2.rectangle(frame,(rect[0],rect[1]),(rect[2],rect[3]),(255,0,0)) #draw bounding box for the face
                cv2.putText(frame,recog_data[i][0]+" - "+str(recog_data[i][1])+"%",(rect[0],rect[1]),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),1,cv2.LINE_AA)


        cv2.imshow("Frame",frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):


            break

'''
facerec_128D.txt Data Structure:
{
"Person ID": {
    "Center": [[128D vector]],
    "Left": [[128D vector]],
    "Right": [[128D Vector]]
    }
}
This function basically does a simple linear search for
^the 128D vector with the min distance to the 128D vector of the face on screen
'''
def deleteV3(DataIn, DataOut):
    #--- Load Data ---
    file = open(DataIn,"r")
    array = file.read()

    data = json.loads(array)

    file.close()

    #--- Names ---
    NameArray = list(data)
    NameRange = len(NameArray)

    for i in range (0, NameRange):
        print("({}) {}".format(i+1, NameArray[i]))

    #--- Choice ---
    while True:
        try:
            choice = int(input("Choose which data entry to delete (n)\nInput 0 to delete multiple items : "))
        except ValueError:
            print("Please choose an integer")
            continue

        # Check if input are less than zero
        if choice < 0:
            print("Please choose a positive number")
            continue

        break

    #--- Multiple deletes ---
    if choice == 0:
        # Initialise
        ToBeDeleted = []
        Counter = 1
        print("Exit with a 0")

        while True:
            try:
                TempChoice = int(input("Data no {} to be deleted : ".format(Counter)))
            except ValueError:
                print("Please choose an integer")
                continue

            # Check if input are less than zero
            if TempChoice < 0:
                print("Please choose a positive number")
                continue

            ToBeDeleted.append(TempChoice)
            Counter += 1

            if TempChoice == 0:
                break

        # Sort the array
        ToBeDeleted.sort()

    #--- delete ---
    DataNew = {}
    Temp = 0

    # Single Delete
    if not choice == 0:
        for i in NameArray:
            Temp = Temp + 1
            if Temp != choice:
                DataNew[i] = data[i]
    # Multiple delete
    else:
        for i in NameArray:
            Temp = Temp + 1
            if not (Temp in ToBeDeleted):
                DataNew[i] = data[i]



    #--- Store in file ---
    with open(DataOut, 'w') as outfile:
        json.dump(DataNew, outfile)

def findPeople(features_arr, positions, thres = 0.6, percent_thres = 90):
    '''
    :param features_arr: a list of 128d Features of all faces on screen
    :param positions: a list of face position types of all faces on screen
    :param thres: distance threshold
    :return: person name and percentage
    '''
    f = open('./facerec_128D.txt','r')
    data_set = json.loads(f.read());
    returnRes = [];


    for (i,features_128D) in enumerate(features_arr):
        result = "Unknown";
        smallest = sys.maxsize
        for person in data_set.keys():
            person_data = data_set[person][positions[i]];
            for data in person_data:
                distance = np.sqrt(np.sum(np.square(data-features_128D)))
                if(distance < smallest):
                    smallest = distance;
                    result = person;

        percentage =  min(100, 100 * thres / smallest)
        if percentage <= percent_thres :
            result = "Unknown"
        returnRes.append((result,percentage))
    #print(result)

    weekNumber = int(date.today().isocalendar()[1])
    my_date = date.today()
    day = calendar.day_name[my_date.weekday()]
    hour = int(now.strftime("%H"))
    test = now.strftime("%Y-%m-%d %H:%M")
    #all these are time slots for our club meetings
    #this should be changed to whatever event you want to take attendance for
    if result != "Unknown":
        if weekNumber == 13 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week1").child(result).update({"Attendance": "True"})
        elif weekNumber == 14 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week2").child(result).update({"Attendance": "True"})
        elif weekNumber == 15 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week3").child(result).update({"Attendance": "True"})
        elif weekNumber == 16 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week4").child(result).update({"Attendance": "True"})
        elif weekNumber == 17 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week5").child(result).update({"Attendance": "True"})
        elif weekNumber == 18 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week6").child(result).update({"Attendance": "True"})
        elif weekNumber == 19 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week7").child(result).update({"Attendance": "True"})
        elif weekNumber == 20 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week8").child(result).update({"Attendance": "True"})
        elif weekNumber == 21 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week9").child(result).update({"Attendance": "True"})
        elif weekNumber == 22 and day == "Wednesday" and hour >= 17 and hour <= 20:
            db.child("classes").child("MVP").child("Week10").child(result).update({"Attendance": "True"})

        db.child("users").child(result).update({"Date": test})
        #hi = "hello "
        #greeting = hi+result
        #engine.say(greeting);
        #ngine.runAndWait() ;

    return returnRes


def register(result):
    ts = time.time()
    Date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    Time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
    row = [result, Date, Time]
    with open('StudentDetails\StudentDetails.csv', 'a+') as csvFile:
        writer = csv.writer(csvFile, delimiter=',')
        writer.writerow(row)
        csvFile.close()


'''
Description:
User input his/her name or ID -> Images from Video Capture -> detect the face -> crop the face and align it
    -> face is then categorized in 3 types: Center, Left, Right
    -> Extract 128D vectors( face features)
    -> Append each newly extracted face 128D vector to its corresponding position type (Center, Left, Right)
    -> Press Q to stop capturing
    -> Find the center ( the mean) of those 128D vectors in each category. ( np.mean(...) )
    -> Save

'''





def create_manual_data():
    FRGraph = FaceRecGraph();
    MTCNNGraph = FaceRecGraph();
    face_detect = MTCNNDetect(MTCNNGraph, scale_factor=2); #scale_factor, rescales image for faster detection
    extract_feature = FaceFeature(FRGraph)
    vs = cv2.VideoCapture(0); #get input from webcam
    print("Please input new user ID:")
    new_name = input().lower(); #ez python input()
    f = open('./facerec_128D.txt','r');
    data_set = json.loads(f.read());
    person_imgs = {"Left" : [], "Right": [], "Center": []};
    person_features = {"Left" : [], "Right": [], "Center": []};
    print("Please start turning slowly. Press 'q' to save and add this new user to the dataset");
    while True:
        _, frame = vs.read();
        rects, landmarks = face_detect.detect_face(frame, 20);  # min face size is set to 80x80
        for (i, rect) in enumerate(rects):
            aligned_frame, pos = aligner.align(160,frame,landmarks[:,i]);
            if len(aligned_frame) == 160 and len(aligned_frame[0]) == 160:
                person_imgs[pos].append(aligned_frame)
                cv2.imshow("Captured face", aligned_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    for pos in person_imgs: #there r some exceptions here, but I'll just leave it as this to keep it simple
        person_features[pos] = [np.mean(extract_feature.get_features(person_imgs[pos]),axis=0).tolist()]
    data_set[new_name] = person_features;
    f = open('./facerec_128D.txt', 'w');
    f.write(json.dumps(data_set))








if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, help="Run camera recognition", default="camera")
    args = parser.parse_args(sys.argv[1:]);
    aligner = AlignCustom();
    main(args);
