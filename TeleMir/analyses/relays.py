# -*- coding: utf-8 -*-

import numpy as np
import msgpack
import multiprocessing as mp
from pyacq.gui.tools import RecvPosThread
import zmq
import time


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

        self.process = mp.Process(target = self.transmitterMainLoop,  args=(self.stop_flag, in_s, out_s))
        self.process.start()
        
        print 'DataTransmitter started:', self.name

    
    def stop(self):
        self.stop_flag.value = 1
        self.process.join()
        print 'DataTransmitter stoped:', self.name

        
    def transmitterMainLoop(self,stop_flag,in_stream,out_stream):
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
    #print phrase
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


class Receiver:
    
    def __init__(self,in_ip,
                 in_port,
                 in_sampling_rate,
                 in_nb_channels,
                 in_buffer_length,
                 in_packet_size,
                 stream_handler,
                 ):
        self.stream_handler=stream_handler

        #initialisation of in_stream
        self.in_ip=in_ip
        self.in_port=in_port
        self.in_sampling_rate=in_sampling_rate
        self.in_nb_channels=in_nb_channels
        self.in_buffer_length=in_buffer_length
        self.in_packet_size=in_packet_size
        self.initialize_in_stream()

        #initialisation of out_stream
        self.initialize_out_stream()
    
    def initialize_out_stream(self):
        self.out_stream = self.stream_handler.new_signals_stream(sampling_rate=self.in_sampling_rate,
                                                                 nb_channel=self.in_nb_channels,
                                                                 buffer_length=self.in_buffer_length,
                                                                 packet_size=self.in_packet_size
                                                                 )

    def initialize_in_stream(self):
        self.in_stream = self.stream_handler.new_data_stream(ip=self.in_ip,
                                                             port=self.in_port,
                                                             sampling_rate=self.in_sampling_rate,
                                                             )

    def start(self):
        self.stop_flag = mp.Value('i', 0)
        in_s = self.in_stream
        out_s = self.out_stream

        self.process = mp.Process(target = self.receiverMainLoop,  args=(self.stop_flag, in_s, out_s))
        self.process.start()
        
        print 'DataReceiver started:'
    
    def stop(self):
        self.stop_flag.value = 1
        self.process.join()
        print 'DataReceiver stopped'


    def receiverMainLoop(self,stop_flag,in_stream,out_stream):
    
    #connexion to in_stream
        context = zmq.Context()
        in_socket = context.socket(zmq.SUB)
        in_socket.connect("tcp://%s:%d"%(in_stream['ip'],in_stream['port']))
        in_socket.setsockopt(zmq.SUBSCRIBE,'')
        
    #connexion to out_stream
        out_socket = context.socket(zmq.PUB)
        out_socket.bind("tcp://*:%d"%out_stream['port'])
    
    #initialize position in arrays
        abs_pos=0
        pos=0
        np_arr=out_stream['shared_array'].to_numpy_array()
        half_size=np_arr.shape[1]/2

        while not stop_flag.value:
        #receive data
            in_msg=in_socket.recv()
            new_data=np.array(msgpack.loads(in_msg))
            new_data_len=new_data.shape[1]
            
        #double copy
            np_arr[:,pos:pos+new_data_len] = new_data
            np_arr[:,pos+half_size:pos+half_size+new_data_len] = new_data

        #update positions
            abs_pos += new_data_len
            pos = (pos + new_data_len) % half_size

        #send position
            out_socket.send(msgpack.dumps(abs_pos))
            
            time.sleep(out_stream['packet_size']/out_stream['sampling_rate']/2.)
