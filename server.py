#!/usr/bin/env python3

import socket
import threading
import json
import ssl
import functools

HEADERSIZE = 16
BUFFERSIZE = 64
ENCODING = "utf-8"
SERVERIP = ""
PORT = 5050
ADRS = (SERVERIP,PORT)

SERVERPREF = "/"
CLIENTPREF = "!"
FILEPREF = "%"

ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ctx.load_cert_chain("servercert.pem")
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
#server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server= ctx.wrap_socket(server,server_side = True)
print(server.family,server.type)
server.bind(ADRS)
server.listen(3)
print(f"server live on {server.getsockname()}")
#print(socket.getfqdn(server.getsockname()[0]))


class aliasdict(dict): #will only work with strings as keys and is case insensetive
    def __init__(self,*args,**kwargs):
        dict.__init__(self,*args,**kwargs)
        self.aliases = dict()
    def getkey(self,alias):
        return self.aliases.get(alias,alias)

    def __getitem__(self,key):
        key = key.lower()
        return dict.__getitem__(self ,self.getkey(key))

    def __setitem__(self,key,value):
        key = key.lower()
        return dict.__setitem__(self,self.getkey(key),value)

    def __contains__(self,key):
        key = key.lower()
        return dict.__contains__(self,self.getkey(key))
    
    def pop(self,key,*args,**kwargs):
        key = key.lower()
        return dict.pop(self,self.getkey(key),*args,**kwargs)
    
    def addalias (self,key,alias):
        key = key.lower()
        alias = alias.lower()
        self.aliases[alias] = key
    
    def addaliases(self,key,aliases):
        for alias in aliases:
            self.addalias(key,alias)

    def addaliasesfromdict(self,dic):
        for key in dic:
            self.addaliases(key,dic[key])
    
    def __delitem__(self,key):
        key = key.lower()
        print("deleating",key)
        for i in self.aliases:
            if self.aliases[i] ==key:
                self.aiases.pop(i)
        return dict.__delitem__(self,self.getkey(key))

    def delalias(self,alias):
        alias = alias.lower()
        return self.aliuses.pop(alias)

    def renamekey(self,oldkey, newkey):
        oldkey = oldkey.lower()
        newkey = newkey.lower()
        self.__setitem__(newkey,self.pop(self.getkey(oldkey)))
        for i in self.aliases:
            if self.aliases[i] ==oldkey:
                self.aliases[i] = newkey
                dict.value
    
    def renamealias(self,oldalias,newalias):
        self.alias[newalias] = self.alias.pop(oldalias)

class servercommand(object):
    cmds = aliasdict()
    def __init__(self,func,*args,**kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.name = self.func.__name__
        if "name" in self.kwargs:
            self.name = self.kwargs["name"]
        self.cmds[self.name]=self
        if "alias" in self.kwargs:
            self.cmds.addalias(self.name, kwargs["alias"])
        if 'aliases' in self.kwargs:
            self.cmds.addaliases(self.name,kwargs['aliases'])
        functools.update_wrapper(self, func)
        
    def __call__(self,*fargs,**fkwargs):
        return(self.func(*fargs,**fkwargs))


        
def servercmd(*args,**kwargs):# this is wrapper classes, just dont think about it too hard
    def wrapper(func):
        class servercommandsp(servercommand):
            @functools.wraps(func)
            def __call__(self,*fargs,**fkwargs):
                return(self.func(*fargs,**fkwargs))
        return servercommandsp(func,*args,**kwargs)
    return wrapper




class user(object):
    userdic = aliasdict()
    def __init__(self,socket,address,username = None):
        self.socket = socket
        self.address = address
        if not username:
            s = servermessager()
            s.send("Server connected, please enter username",self)
            username = self.decode(self.recive())["message"]
        while True:
            if not (username in self.userdic or username=="Server") :
                break
            s.send("Sorry username taken\n Please select a new one",self)
            username = self.decode(self.recive())["message"]
        self.userdic[username] = self
        self.username = username
        s.sendall(f"{username} has joined the server")
    
    def recive(self):
        header = self.recivebytes(HEADERSIZE)
        msg =self.recivebytes(int(header.decode(ENCODING)))
        return msg
    
    def recivebytes(self,msgsize):
            msgsize = int(msgsize)
            fullmsg =  b''
            if msgsize <HEADERSIZE:
                fullmsg = self.socket.recv(msgsize)
            else:
                for i in range(int(msgsize/HEADERSIZE)):
                    fullmsg += self.socket.recv(HEADERSIZE)
                fullmsg += self.socket.recv(msgsize%HEADERSIZE)
            return fullmsg
    
    def send(self,msg,reciver):
        if type(msg) == str:
            msg = {"message":msg, "sender":self.username}
        elif type (msg) == dict:
            msg["sender"] = self.username
        msg = self.encode(json.dumps(msg))
        reciver.socket.send(msg)
    
    def sendall(self,msg):
        if type(msg) == str:
            msg = {"message":msg, "sender":self.username}
        elif type (msg) == dict:
            msg["sender"] = self.username
        msg = self.encode(json.dumps(msg))
        for reciver in self.userdic.values():
            reciver.socket.send(msg)
    
    @classmethod
    def encode(cls,msg):
        msg = bytes(msg,ENCODING)
        while True:
            header = bytes(f"{len(msg):<{HEADERSIZE}}",ENCODING)
            if len(header) > HEADERSIZE:
                header = cls.encode(json.dumps({"largefile":header}),ENCODING)
            return header + msg
    
    def decode(self,msg):
        msg = msg.decode(ENCODING)
        msg = json.loads(msg)
        if "servercommand" in msg:
            stri = msg["servercommand"]
            if stri in servercommand.cmds:
                cmd = servercommand.cmds[stri]
                result = cmd(self,*(msg["sargs"]or []),**(msg["skwargs"]or {}))#sargs will alwasy exist but may be equal to None
            else:
                s = servermessager()
                s.send("command not recognised",self)
                result = ""
            result = result or "/"+stri+" "+" ".join((msg["sargs"]or []))
            return result 
        else:
            if not("message" in msg) or msg["message"] =="":
                msg["message"]=" " 
            return msg
    
    @servercmd (aliases = ("leave"))
    def disconnect(self):
        self.userdic.pop(self.username)
        s = servermessager()
        s.send({"clientcommand":"Disconnect","ccommandargs":(),"ccommandkwargs":{}},self)
        self.socket.close()
        s.sendall(f"{self.username} has left")
        print("Closed conection from",self.address)
        return SERVERPREF+"Disconnect"

    @servercmd()
    def addalias (self,key, alias):
        servercmds.addalias(key, alias)

    @servercmd(alias = "dm")
    def messageuser (self, user, *message):
        user = self.userdic[user]
        message = " ".join(message)
        msg = encode(f"{self.username}(private)>{message}")
        user.socket.send(msg)

    @servercmd(aliases = ["cn","rename"])
    def changeusername (self,newusername):
        if newusername in self.userdic and self.username.lower() != newusername.lower():
            send("userame taken",self.socket)
        else:
            self.userdic.renamekey(self.username,newusername)
            self.username = newusername
    
    @servercmd(alias = "cxn")
    def changexusername (self,otheruser,newusername):
        self.userdic[otheruser].changeusername(newusername)

    @servercmd()
    def kick(self,otheruser,*reason):
        self.userdic[otheruser].disconnect(self.userdic[otheruser])
        sendall(f'{self.username} kicked {otheruser} "{"".join(reason)}"')

class servermessager(user):
    def __init__(self):
        self.username = "Server"

def acceptusers():
    while True:
        clientsocket, address = server.accept()
        print(f"Connection from {address} has been established.")
        clientthread = threading.Thread(target = handleclient,args = (clientsocket,address))
        clientthread.start()    

def handleclient(client,address):
    client = user(client,address)
    try:
        message = ""
        while message!= SERVERPREF+"Disconnect":
            message = client.recive()
            message = client.decode(message)
            client.sendall(message)
    except Exception as e:
        client.disconnect(client)
        raise e



def sendloop():
    while True:
        message = input()
        if message:
            sendall(f"Server>{message}")

acloop = threading.Thread(target = acceptusers)
#sendthread =threading.Thread(target = sendloop)
acloop.start()
#sendthread.start()

