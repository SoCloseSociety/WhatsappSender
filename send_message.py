import csv
import pywhatkit
from datetime import datetime
from pywinauto.keyboard import send_keys
import pyautogui
import time
import numpy as  np
import pandas as  pd
import  random



f = open("message.txt", "r", encoding="utf-8")
message = f.read()



number_filename = input("Enter  the  input filename  with csv which  contains the  numbers : ")
mouse_pos_x = int(input("Enter  the  X value  of  MPos : "))
mouse_pos_y = int(input("Enter  the  Y value  of  MPos : "))
max_count = int(input("Enter  the maximum  limit of  the seneding  message : "))

already_sent_message = []

with open('already_send_message.csv', 'r', encoding="utf-8") as file:
    reader = csv.reader(file)
    for row in reader:
        try:
            if row[0] != "Profile Link":
                already_sent_message.append(row[0])
        except:
            print("Error")
            
count = 0 
            
cleaned_numbers = [number.replace(" ", "").replace("-", "") for number in already_sent_message]



with open(number_filename, newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        try:
            number = row[0].replace(" ", "").replace("-", "")
            if number not in cleaned_numbers:
                print(number)
                now = datetime.now()
                pywhatkit.sendwhatmsg(number, message, now.hour, now.minute+1)
                pyautogui.moveTo(mouse_pos_x, mouse_pos_y)
                pyautogui.click(mouse_pos_x, mouse_pos_y)

                pyautogui.press('enter') 
                time.sleep(2)

                already_sent_message.append(number)
                already_sent_message = list(set(already_sent_message))  # convert to set to remove duplicates
                already_sent_message_np = np.array(already_sent_message)
                already_sent_message_pamdas = pd.DataFrame({"Profile Link" : already_sent_message_np})
                already_sent_message_pamdas.to_csv("already_send_message.csv", index=False)       
                
                count = count + 1
                
                if count == max_count:
                    break           
                

        except Exception as e:
            print(e)