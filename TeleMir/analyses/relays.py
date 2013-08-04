# -*- coding: utf-8 -*-

import numpy as np
import msgpack
import multiprocessing as mp
from pyacq.gui.tools import RecvPosThread
import zmq
import time

def transmitterMainLoop(stop_flag,in_stream,out_stream):
#def transmitterMainLoop(stop_flag,in_stream):

    #definition of the memory zone to read
    in_array=in_stream['shared_array'].to_numpy_array()
    half_size=in_array.shape[1]/2

    #definition of the sent interval
    pos=half_size
    last_pos=pos
    data=in_array[:,pos-in_stream['packet_size']:pos]

    #connexion to in_stream
    in_port = in_stream['port']
    context = zmq.Context()
    in_socket = context.socket(zmq.SUB)
    in_socket.connect("tcp://localhost:%d"%in_port)
    in_socket.setsockopt(zmq.SUBSCRIBE,'')
    
    #connexion to out_stream
    out_ip = out_stream['ip']
    out_port = out_stream['port']
    out_socket = context.socket(zmq.PUB)
    phrase="tcp://%s:%d"%(out_ip,out_port)
    print phrase
    out_socket.bind(phrase)
                       
    #initialisation de la pile de réception des positions
    threadPos=RecvPosThread(socket=in_socket, port=in_port)
    threadPos.start()

    #Wait for the first messages
    while threadPos.pos == None :
        pass

    while not stop_flag.value :
        #update in_data
        abs_pos = threadPos.pos
        pos = abs_pos%half_size + half_size
        data = in_array[:,last_pos:pos]
#        print data
        #send the message
        msg=msgpack.dumps(data.tolist())
        out_socket.send(msg)

        #record last position
        last_pos=pos

        time.sleep(in_stream['packet_size']/in_stream['sampling_rate'])

class Transmitter:
    
    def __init__(self,in_stream,out_ip,out_port,stream_handler):
        
        self.in_stream=in_stream
        self.name=self.in_stream['name']+'_data'
        
        #initialization of out_stream
        self.stream_handler=stream_handler
        self.out_ip=out_ip
        self.out_port=out_port
        self.initialize_out_stream()

    def initialize_out_stream(self):
        sampling_rate=self.in_stream['sampling_rate']
        channel_indexes=self.in_stream['channel_indexes']
        channel_names=self.in_stream['channel_names']
        name=self.in_stream['name']+'_data'
        self.out_stream = self.stream_handler.new_data_stream(ip=self.out_ip,
                                                              port=self.out_port,
                                                              name=name,
                                                              sampling_rate=sampling_rate,
                                                              channel_indexes=channel_indexes,
                                                              channel_names=channel_names,
                                                              )
        

    def start(self):
        self.stop_flag = mp.Value('i', 0)
        in_s = self.in_stream
        out_s = self.out_stream

        self.process = mp.Process(target = transmitterMainLoop,  args=(self.stop_flag, in_s, out_s))
        self.process.start()
        
        print 'DataTransmitter started:', self.name

    
    def stop(self):
        self.stop_flag.value = 1
        self.process.join()
        print 'DataTransmitter stoped:', self.name
