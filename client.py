#!/usr/bin/env python3
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog
import json
import ssl
import time

HEADERSIZE = 16
BUFFERSIZE = 64
ENCODING = "utf-8"
SERVERIP = input("please enter servername")
if not SERVERIP:
    SERVERIP= socket.gethostname()
PORT = 5050
ADRS = (SERVERIP,PORT)

SERVERPREF = "/"
CLIENTPREF = "!"
FILEPREF = "%"
FULLLOGGGING= False

class client(object):
    def __init__(self,ADRS):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.load_verify_locations("servercert.pem")
        ctx.check_hostname  = False
        self.ADRS = ADRS
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = ctx.wrap_socket(self.sock,server_hostname=SERVERIP)
        self.sock.connect((ADRS))

    
    def send(self,msg):
        if type(msg) == str:
            msg = self.parsestring(msg)
        if "clientcommand" in msg:
            if not "cargs" in msg:
                msg["cargs"]= []
            if not "ckwargs" in msg:
                msg["ckwargs"]= {}
        if "servercommand" in msg:
            if not "sargs" in msg:
                msg["sargs"]= []
            if not "skwargs" in msg:
                msg["skwargs"]= {}
        msg["time"] = time.time()# used to generate ids
        msg = json.dumps(msg)
        msg = self.encode(msg)
        if FULLLOGGGING: print(msg)
        self.sock.send(msg)

    @classmethod
    def encode(cls,msg):
        msg = bytes(msg,ENCODING)
        while True:
            header = bytes(f"{len(msg):<{HEADERSIZE}}",ENCODING)
            if len(header) > HEADERSIZE:
                header = cls.encode(json.dumps({"largefile":header}),ENCODING)
            return header + msg
    @classmethod
    def parsestring(self,string):
        out = {}
        if string[0] == "/":
            command = string.split()
            out["servercommand"] =command[0][1:]
            if len (command)>1:
                out["sargs"] = command[1:]
            else:
                out["sargs"] = None
        elif string[0] == "!":
            command = string.split(">")
            out["clientcommand"] =command[0][1:]
            if len (command)>1:
                out["cargs"] = command[1:]
            else:
                out["cargs"] = []
        else:
            out["message"]  = string
        return out

    def recivebytes(self,msgsize):
        if msgsize <BUFFERSIZE:
            fullmsg = self.sock.recv(msgsize)
        else:
            fullmsg =  b''
            for i in range(int(msgsize/BUFFERSIZE)):
                fullmsg += self.sock.recv(BUFFERSIZE)
            fullmsg += self.sock.recv(msgsize%BUFFERSIZE)
        return fullmsg
    
    def recive(self):
        header = self.recivebytes(HEADERSIZE)
        msg =self.recivebytes(int(header.decode(ENCODING)))
        return msg
        
    def decode(self,msg):
        if FULLLOGGGING: print(msg)
        msg = msg.decode(ENCODING)
        msg = json.loads(msg)
        if "largefile" in msg:
            msg = decode(recivebytes(int(msg["largefile"])))
        if "clientcommand" in msg:
            cmd = msg["clientcommand"]
            if cmd == "stream":
                streamrcv = streamrecvier(self.master,*msg["cargs"],**msg["ckwargs"])
                msg["message"] = f"connecting to {msg['sender']}"
            elif cmd == "Disconnect":
                msg["message"] ="!Disconnect"
        elif "message" in msg:
            
            ##msg = f'{msg["sender"]}> {msg["message"]}'
            pass # message fomrating is now handeled by the UI
        return msg

    def disconnect(self):
        self.send("/disconnect")








class streamrecvier(client):           
    def __init__(self,master,ip,port):
        self.master = master
        popup = tk.Toplevel(self.master)
        conectionl = tk.Label(popup, text=f"connecting to {ADRS}")
        conectionl.pack()
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.load_verify_locations("clientkey.pem")
        ctx.check_hostname  = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = ctx.wrap_socket(self.sock,server_hostname=ip)
        self.sock.connect((ip,port))
        recivingthread =threading.Thread(target = self.handlestream)
        recivingthread.start()
        popup.destroy()

    def handlestream(self):
        msg = self.recive()
        msg = self.decode(msg)
        if "streamcmd" in msg:
            if msg["streamcmd"] == "writefile":
                streaminfo = tk.Toplevel()
                fileinfo = tk.Label(streaminfo,text= f'Downloading "{msg["filename"]}" ({msg["filesize"]} Bytes)')
                fileinfo.pack()
                self.recivefile(msg["filename"],int(msg["filesize"]))
                streaminfo.destroy()
    
    def recivefile(self,filename, filesize):
        with open("Recived Files/"+filename,"wb") as file:
                for i in range(int(filesize/BUFFERSIZE)):
                    file.write(self.sock.recv(BUFFERSIZE))
                file.write(self.sock.recv(filesize%BUFFERSIZE))






class streamhost(object):
    def __init__(self,master,func,*funcargs,**funckwargs):
        setupwindow = tk.Toplevel()
        tk.Message(setupwindow, text="setting up stream").pack()
        self.master = master
        self.func = func
        self.funcargs = funcargs
        self.funckwargs = funckwargs
        self.ip = socket.gethostname()
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain("clientkey.pem")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server= ctx.wrap_socket(self.server,server_side = True)
        for self.port in range (5100,5200):
            try:
                self.server.bind((self.ip,self.port))
                break
            except:
                pass
        streamthread = threading.Thread(target = self.handle)
        streamthread.start()
        setupwindow.destroy()

    def handle(self):
        streaminfo = tk.Toplevel(self.master)
        streamlog = scrolledtext.ScrolledText(streaminfo)
        streaming = True
        def close():
            streaming = False
            self.server.shutdown(-1)
            self.server.close()
            streaminfo.destroy()
        stopbutton = tk.Button(streaminfo,text = "stop streaming",command = close)
        streamlog.pack()
        stopbutton.pack()
        while streaming:
            self.server.listen(5)
            client,address= self.server.accept()
            clientcon= clientconnection(streamlog,client,address)
            clienthandler = threading.Thread(target = self.func, args = (clientcon,*self.funcargs), kwargs = self.funckwargs)
            clienthandler.start()

class clientconnection:
    def __init__(self,output,client,address):
        self.output = output
        self.client = client
        output.insert(tk.INSERT,f"streaming to {address}\n")
    
    def sendfile(self,path):
        name = path.split("/")[-1]
        import os
        filesize = os.path.getsize(path)
        with open(path,"rb") as file:
            self.client.send(client.encode(json.dumps({"streamcmd":"writefile","filename":name,"filesize":filesize})))
            for i in range(int(filesize/BUFFERSIZE)):
                self.client.send(file.read(BUFFERSIZE))
            self.client.send(file.read(filesize%BUFFERSIZE))
        self.client.close()
        self.output.insert(tk.INSERT,"finnished\n")


class ui(client):
    def __init__(self,master,ADRS):
        client.__init__(self,ADRS)
        self.master = master
        self.window = tk.Frame(master)
        self.window.pack(fill = "both",expand = True)
        self.messages = scrolledtext.ScrolledText(self.window)
        self.inputfield = tk.Entry(self.window)
        self.filebutton = tk.Button(self.window,text = "send file",command = self.sendfile)
        self.inputfield.bind("<Return>", self.sendinput)
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.inputfield.bind("<FocusOut>",self.createfillertext)
        self.inputfield.bind("<FocusIn>",self.removefillertext)
        self.messages.grid(row = 0, column = 0, sticky = "NSEW", rowspan = 4, columnspan = 5)
        self.inputfield.grid(row = 4, column = 0, sticky = "NSEW", columnspan = 3)
        self.filebutton.grid(row = 4, column  = 4)
        self.inputfield.focus_set()
        self.window.grid_columnconfigure(0,weight = 1)
        self.window.grid_rowconfigure(0,weight = 1)
        self.messagedict = {}

    def close(self):
        try:
            self.disconnect()
        except Exception as e:
            print (e)
        self.master.destroy()

    
    def sendinput(self,event):
        if self.inputfield["fg"]!="grey60":
            message = self.inputfield.get()
            self.inputfield.delete(0,tk.END)
        else:
            message = ""
        if message:
            self.send(self.parsestring(message))
    
    def reciveloop(self):
        try:
            while True:
                msg = self.recive()
                msg = self.decode(msg)
                if "message" in msg and len(msg["message"])>0:
                    if msg["message"][0] == CLIENTPREF :
                        if msg["message"][1:]== "Disconnect":
                            break
                    line = f'{msg["sender"]}> {msg["message"]}'
                    if "clientcommand" in msg and msg["clientcommand"] =="edit":
                        indexs = messagedict[msg["sender"]+msg["cargs"]]
                        self.messages.config(state= tk.NORMAL)
                        self.messages.delete(*indexs)
                        self.messages.config(state= tk.DISABLED)
                    else:
                        if "time" in msg:
                            first = self.messages.index(tk.END)
                            last = ".".join((first.split(".")[0],str(int(first.split(".")[1])+len(line))))
                            self.messagedict[msg["sender"]+str(msg["time"])]= (first,last)
                        self.messages.config(state= tk.NORMAL)
                        self.messages.insert(tk.END,line+'\n')
                        self.messages.see(tk.END)
                        self.messages.config(state= tk.DISABLED)
        except Exception as e:
            raise e
            self.close()
            
    
    def createfillertext(self,event):
        if not self.inputfield.get():
            self.inputfield.config(fg = "grey60")
            self.inputfield.insert(0,"message server")
    def removefillertext(self,event):
        if self.inputfield["fg"] == "grey60":
            self.inputfield.delete(0,tk.END)
            self.inputfield.config(fg = "SystemWindowText")
    
    def sendfile(self):
        file = filedialog.askopenfilename()
        if file:
            filestream = streamhost(self.master,clientconnection.sendfile,file)
            self.send({"clientcommand":"stream","ckwargs":{"ip":filestream.ip,"port":filestream.port}})

def main():
    root = tk.Tk()
    global cli
    cli = ui(root,ADRS)
    recivethread = threading.Thread(target = cli.reciveloop)
    recivethread.start()
    root.mainloop()

lemetype = threading.Thread(target = main)
lemetype.start()

