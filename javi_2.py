#!/usr/bin/env python3 #the script is python3
import sqlite3
import os
import serial
from threading import Thread
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import uuid
import datetime
import time

#global variables
isStop = False
root = Tk()

ser0 = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

ser1 = serial.Serial(
    port='/dev/ttyUSB1',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

# Init local database connection
# connect to a database file, if not exist it will create a new one
# create a default path to connect to and create (if necessary) a database
# called 'database.sqlite3' in the same directory as this script
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), 'javi_2.db')

array_a = []
array_b = []

def db_connect(db_path=DEFAULT_PATH):  
    conn = sqlite3.connect(db_path)
    return conn

def createTableIfNotExist():
    conn = db_connect()
    c = conn.cursor()
    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS data
                 (id int NOT NULL, work_id text NOT NULL, USB0 text NOT NULL, USB1 text NOT NULL, date datetime NOT NULL)''')
    # Save (commit) the changes
    conn.commit()
    
def save_to_database():
    conn = db_connect()
    c = conn.cursor()
    date_time = datetime.datetime.now()
    uuidString = str(uuid.uuid4())
    
    records = []
    for i in range(len(array_a)):
        record = (i, uuidString, str(array_a[i][1:]), str(array_b[i][1:]), date_time)
        records.append(record)
        print(record)
        i += 1
        
    c.executemany('INSERT INTO data VALUES (?,?,?,?,?)', records)
    conn.commit()
    array_a.clear()
    array_b.clear()
    
def query_list_database():
    conn = db_connect()
    c = conn.cursor()
    
    c.execute('SELECT work_id, date FROM data GROUP BY work_id ORDER BY date')
    results = c.fetchall()
    conn.close()
    return results
    
def query_item(uuid):
    conn = db_connect()
    c = conn.cursor()
    
    c.execute('SELECT * FROM data WHERE work_id = ?', (uuid,))
    results = c.fetchall()
    conn.close()
    return results

# Read data from serial port
def readSerial(channel):
    print("reading USB: " + str(channel))
    # return data if there is data in serial else return None
    data = None
    while not data:
        if channel == 0:
            #data = input("Please enter USB0: ")
            data = ser0.readline().decode('utf-8')
        else :
            #data = input("Please enter B: ")
            data = ser1.readline().decode('utf-8')
        print("received data: {}".format(data.strip().lstrip().rstrip()))
    return data.strip().lstrip().rstrip()

# Write serial 2 use for sending data mode
def writeSerial2(channel, data, type):
    data = 'A' + str(data) + type + 'B'
    if channel == 0:
        print("send to USB0 with data: {}".format(data))
        ser0.write(data.encode())
    else:
        print("send to USB1 with data: {}".format(data))
        ser1.write(data.encode())


def writeSerial(channel, data):
    if channel == 0:
        print("send to USB0 with data: {}".format(data))
        ser0.write(data.encode())
    else:
        print("send to USB1 with data: {}".format(data))
        ser1.write(data.encode())

# This function only save to memory, the data will be save to database after click done button
def saveDataIfNotNone(channel, data):
    if data.strip():
        #Save
        if channel == 0:
            print("array a saved:{}".format(data[:-1]))
            array_a.append(data[:-1])
        else:
            print("array b saved:{}".format(data[:-1]))
            array_b.append(data[:-1])

def confirmNextData(a, b):
    # 2. Update data and sent to serial
    if a.strip():
        print("writing A...")
        write_a = a[:-1] + 'B'
        writeSerial(0, write_a)
    
    if b.strip():
        print("writing B...")
        write_b = b[:-1] + 'B'
        writeSerial(1, write_b)

# Receive data and save to database
def saveMode(first_usb0, first_usb1):
    global isStop
    print("Starting for SAVE mode:{};{}".format(first_usb0, first_usb1))
    a = first_usb0
    b = first_usb1
    pre_a = ''
    pre_b = ''
    while True:
        if isStop == True:
            break
        # 1. Listen on serial port untill all channels (A&B) was filled
        # If all of usb0 and usb 1 wass filled, the data is store to memory
        if a[-1:] == 'o' and b[-1:] == 'o':
            #save pre_a
            saveDataIfNotNone(0, pre_a)
            #save pre_b
            saveDataIfNotNone(1, pre_b)
            #Prepare next data
            confirmNextData(a, b)
            a = readSerial(0)
            b = readSerial(1)
        elif not a.strip() or not b.strip(): #If one of usb0 and usb1 is empty, send to get the data
            if not a.strip():
                #Resending to get a
                writeSerial(0, 'A00000B')
                a = readSerial(0)
                pre_a = a
            if not b.strip():
                #Reseding to get b
                writeSerial(1, 'A00000B')
                b = readSerial(1)
                pre_b = b
        else: #If receive 'x', the previous data was wrong, have to resend new data to the the 'o' data
            if a[-1:] == 'x': #Have to resend A till get a valid data
                print("A is false, Resending A")
                pre_a = a
                confirmNextData(a, '')
                a = readSerial(0)
            if b[-1:] == 'x':  #Have to resend B till get a valid data 
                print("B is false, Resending B")
                pre_b = b
                confirmNextData('', b)
                b = readSerial(1)
    print("A: {}\nB:{}".format(array_a,array_b))
    
# Query database and send to serial port
def sendMode():
    global isStop
    print("starting for SEND mode")
    arr_a = array_a
    arr_b = array_b
    type_a = 'o'
    type_b = 'o'
    while len(arr_b) > 0:
        if isStop == True:
            break
        #Send a and b
        writeSerial2(0, arr_a[0], type_a)
        writeSerial2(1, arr_b[0], type_b)
        a = None
        b = None
        a = readSerial(0)
        b = readSerial(1)
        if a != None:
            if str(a[1:]) == str(arr_a[0]):
                type_a = 'o'
            else:
                type_a = 'x'
        if b != None:
            if str(b[1:]) == str(arr_b[0]):
                type_b = 'o'
            else:
                type_b = 'x'

        if type_a == 'o' and type_b == 'o':
            arr_a.pop(0)
            arr_b.pop(0)
        else:
            type_a = type_b = 'x'
    #Sent all data, clear memory and turn on buttons
    array_a.clear()
    array_b.clear()
    enable_mode_button()

def select_mode(mode):
    global isStop
    rev_ser0 = ''
    rev_ser1 = ''
    if mode == 0: #save mode
        while 'T' not in rev_ser0 and 'T' not in rev_ser1:
            if 'T' not in rev_ser0:
                writeSerial(0, 'ATB')
                rev_ser0 = readSerial(0)
            if 'T' not in rev_ser1:
                writeSerial(1, 'ATB')
                rev_ser1 = readSerial(1)
        array_a.clear()
        array_b.clear()
        saveMode(rev_ser0[1:], rev_ser1[1:])
        if isStop == True:
            do_atb_save_database()
    else: #send mode
        while rev_ser0 != 'R' and rev_ser1 != 'R':
            if rev_ser0 != 'R':
                writeSerial(0, 'ARB')
                rev_ser0 = readSerial(0)
            if rev_ser1 != 'R':
                writeSerial(1, 'ARB')
                rev_ser1 = readSerial(1)
        sendMode()
    print(">>>:{};{}".format(rev_ser0, rev_ser1))
    
def do_atb_save_database():
    t = Thread(target=save_to_database)
    t.daemon = True
    t.start()

def disable_mode_button():
    atb_button = root.nametowidget("f1").nametowidget("atb_button")
    atb_button.config(state="disabled")
    arb_button = root.nametowidget("f1").nametowidget("arb_button")
    arb_button.config(state="disabled")
    
def enable_mode_button():
    atb_button = root.nametowidget("f1").nametowidget("atb_button")
    atb_button.config(state="normal")
    arb_button = root.nametowidget("f1").nametowidget("arb_button")
    arb_button.config(state="normal")

def do_atb_mode():
    global isStop
    isStop = False
    disable_mode_button()
    t = Thread(target=select_mode, args=(0, ))
    t.daemon = True
    t.start()
    
def selected_item():
    tableView = root.nametowidget("f3").nametowidget("tableView")
    current_item = tableView.focus()
    if current_item:
        return tableView.item(current_item)
    return None

def do_arb_mode():
    global isStop
    isStop = False
    item = selected_item()
    if not item:
        messagebox.showinfo(message="Ban phai chon 1 item trong list truoc khi gui du lieu!")
        return
    
    print(item['values'][0])
    data = query_item(item['values'][0])
    if not data:
        messagebox.showinfo(message="Co loi xay ra, ban vui long nhan nut refresh va thu lai")
        return
    
    for item_data in data:
        array_a.append(item_data[2])
        array_b.append(item_data[3])
    
    disable_mode_button()
    t = Thread(target=select_mode, args=(1, ))
    t.daemon = True
    t.start()
    
def do_stop_action():
    global isStop
    print("stop")
    isStop = True
    enable_mode_button()
    

def main():
    createTableIfNotExist()
    #choose mode
    theUI = JaviGUI(root)
    root.mainloop()

class JaviGUI(Frame):
    def __init__(self, master):
        #self.master = master
        super(JaviGUI, self).__init__()
        master.title("Javi Motor Control")
        
        self.pack(fill=BOTH, expand=True)
        
        frame1 = Frame(master, relief=RAISED, borderwidth=0, name="f1")
        frame1.pack(side=TOP, fill='x', expand=True)
        
        #Button
        select_atb = ttk.Button(frame1, text="ATB", command=do_atb_mode, width=30, name="atb_button")
        #select_atb.grid(row=0, column=1, sticky=E, padx=30, pady=16)
        select_atb.pack(side=LEFT, padx=5, pady = 5)
    
        select_arb = ttk.Button(frame1, text="ARB", command=do_arb_mode, width=30, name="arb_button")
        #select_arb.grid(row=0,column=2, sticky=W, padx=30, pady=16)
        select_arb.pack(side=RIGHT, padx=5, pady = 5)
    
        frame2 = Frame(master, relief=RAISED, borderwidth=0, name="f2")
        frame2.pack(fill='x', expand=True)
        
        stop_button = ttk.Button(frame2, text="Stop", command=do_stop_action, name="stop_button")
        #stop_button.grid(row=1,column=1, columnspan=2, sticky=W+E, padx=30, pady=8)
        stop_button.pack(fill='x', padx=5, pady = 5)
        
        refresh_button = ttk.Button(frame2, text="Refresh", command=self.fill_data_to_table, width=60, name="refresh_button")
        #refresh_button.grid(row=2,column=1, columnspan=2, sticky=W+E, padx=30, pady=8)
        refresh_button.pack(fill='x', padx=5, pady = 5)
        
        self.init_table_view(master)
        self.fill_data_to_table()

    def init_table_view(self, master):
        print("create table view")
        frame = Frame(master, relief=RAISED, borderwidth=1, name="f3")
        frame.pack(fill=BOTH, expand=True)
        tableView = ttk.Treeview(frame, name='tableView')
        tableView.pack(fill=BOTH, expand=True)
        tableView['columns'] = ('ID', 'Date')
        tableView.heading("#0", text='#', anchor='w')
        tableView.column("#0", anchor="w", width=50, stretch=NO)
        tableView.heading('ID', text='ID')
        tableView.column('ID', anchor='center', width=100)
        tableView.heading('Date', text='Created Date')
        tableView.column('Date', anchor='center', width=100)
        #tableView.grid(row=3, column=1, columnspan=2, sticky=W+E)
        self.treeview = tableView
        #self.grid_rowconfigure(0, weight = 1)
        #self.grid_columnconfigure(0, weight = 1)
        
    def fill_data_to_table(self):
        #query and fill data
        data = query_list_database()
        tableView = root.nametowidget("f3").nametowidget("tableView")
        tableView.delete(*tableView.get_children())
        i = 0
        for item in data:
            tableView.insert('', 'end', text=str(i), values=(item[0], item[1]))
            i += 1

if __name__ == "__main__":
    main()