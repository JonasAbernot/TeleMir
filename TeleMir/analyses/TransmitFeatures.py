# -*- coding: utf-8 -*-
"""

Transmeteur de stream

Ouvre une socket de reception et une socket d'emition
et transmet les données de l'une à l'autre via un Qthread.
La fonction transmit, lancée par le thread est donnée en parametre
et peut réaliser des calculs sur les données avant de les envoyer.

first version by Lx37

"""

from pyacq.core.devices.base import DeviceBase
from pyacq.gui.tools import RecvPosThread
from TeleMir.analyses import GetFeatures

from PyQt4 import QtCore,QtGui
import numpy as np
import multiprocessing as mp
import zmq
import msgpack
import time
import OSC

class TransmitFeatures(DeviceBase):#, QtGui.QWidget):
    def __init__(self,  stream = None, parent = None, **kargs):
        DeviceBase.__init__(self, **kargs)
        #QtGui.QWidget.__init__(self, parent)
    
    def configure( self, name = 'Test dev', 
                                nb_channel = None,
                                nb_pts = None,
                                nb_feature = 8,
                                sampling_rate =1.,
                                digital_port = None,
                                buffer_length= 10.,
                                packet_size = 1,   
                                ):
        self.params = {'name' : name,
                                'nb_channel' : nb_channel,
                                'nb_pts' : nb_pts,
                                'nb_feature' : nb_feature,
                                'digital_port' : digital_port,
                                'buffer_length' : buffer_length,
                                'sampling_rate' : sampling_rate,
                                'packet_size' : packet_size,
                                }
        self.__dict__.update(self.params)
        self.configured = True

    def initialize(self, stream_in):
        ## Feature stuff
        self.feature_names = ['pAlphaO12','pBetaF34','DeltaMean','ThetaMean','AlphaMean','BetaMean','GammaMean','MuMean','meanKurto']
        self.feature_indexes = np.arange(self.nb_feature)
        self.channel_names = [ 'F3', 'F4', 'P7', 'FC6', 'F7', 'F8','T7','P8','FC5','AF4','T8','O2','O1','FC3'] 
        self.channel_indexes = range(self.nb_channel) 
        
        self.extractor = GetFeatures.GetFeatures()
        
        ## OSC socket
        self.oscIP = '194.167.217.90'
        self.oscPort = 9001
        self.oscClient = OSC.OSCClient()
        self.oscMsg = OSC.OSCMessage() 
        self.oscMsg .setAddress("/EEGfeat") 
        
        
        ## Stream In 
        self.stream_in = stream_in
        
        ## Socket In (SUB)
        self.context = zmq.Context()
        self.socket_in = self.context.socket(zmq.SUB)
        self.socket_in.setsockopt(zmq.SUBSCRIBE,'')
        self.socket_in.connect("tcp://localhost:{}".format(self.stream_in['port']))
        
        self.np_arr_in = self.stream_in['shared_array'].to_numpy_array()
        self.half_size_in = self.np_arr_in.shape[1]/2
        self.sr_in = self.stream_in['sampling_rate']
        self.packet_size_in = self.stream_in['packet_size']
        
        self.thread_pos = RecvPosThread(socket = self.socket_in, port = self.stream_in['port'])
        self.thread_pos.start()
        #print np.shape(self.np_arr_in)
        print 'Stream In initialized:', self.stream_in['name'], ', Input port: ', self.stream_in['port'], ', Sampling rate: ', self.sr_in
        
        ## Stream Out
        l = int(self.sampling_rate*self.buffer_length)
        self.buffer_length = (l - l%self.packet_size)/self.sampling_rate
        
        self.stream_out  = self.streamhandler.new_signals_stream(name = self.name+' Digit', sampling_rate = self.sampling_rate,
                                                nb_channel = self.nb_feature, buffer_length = self.buffer_length,
                                                packet_size = self.packet_size, dtype = np.float64,
                                                channel_names = self.feature_names, channel_indexes = self.feature_indexes,            
                                                )
        arr_size = self.stream_out['shared_array'].shape[1]
        assert (arr_size/2)%self.packet_size ==0, 'buffer should be a multilple of pcket_size {}/2 {}'.format(arr_size, self.packet_size)
        
        self.name_stream_out = 'Stream out'
        self.sr_out = float(self.sampling_rate)
        self.np_arr_out = self.stream_out['shared_array'].to_numpy_array()
        
        ## Socket Out
        self.socket_out = self.context.socket(zmq.PUB)
        self.socket_out.bind("tcp://*:{}".format(self.stream_out['port']))
        
        # Could declare other streams if needed
        self.streams = [self.stream_out]
        
        #print np.shape(self.np_arr_out)
        print 'Stream Out initialized:', self.name, ', Output port: ', self.stream_out['port'] , ', Sampling rate: ', self.sr_out
        
        ## Writer counts
        self.pos = 0
        self.abs_pos = self.pos2 = 0
        
        ## Method to be loopely executed by Qthread
        #self.thread_send = SendPosThread(fonction = self.simple_transmit)
        self.thread_copy = SendPosThread(fonction = self.transmit)
                
        self._goOn = True   
        
    def start(self):
        
        self.stop_flag = mp.Value('i', 0) #flag pultiproc  = global 
        
        # Wait for input entries
        time.sleep(0.5)
        self.last_head = (self.thread_pos.pos)%self.half_size_in
        self.last_head2 = self.last_head
        print 'first last head : ', self.last_head 
        
        self.thread_copy.start()
        
        print 'Transmition Started:', self.name
        self.running = True
    
    def stop(self):
        self.stop_flag.value = 1
        self.thread_copy.running = False
        self.thread_copy.exit()
    
    def close(self):
        self._goOn = False

    def simple_transmit(self):
        pos = self.thread_pos.pos
        self.socket_out.send(msgpack.dumps(pos))
        time.sleep(0.007)   # 1/Fe in s
        
    def transmit(self):
        
        t_in = time.time()
        
        ## Read what's comin'
        pos_in = self.thread_pos.pos
        half_size_in = self.half_size_in
        head = pos_in%half_size_in
        
        data = self.np_arr_in[:, head+half_size_in-self.nb_pts : head+half_size_in] 
        #print 'head : ', head
        
        ## Compute features
        features = self.extractor.extract_TCL(data)
        
        ## Write out and send position
        pos2 = self.pos2
        half_size = self.np_arr_out.shape[1]/2
        
        self.np_arr_out[:,pos2:pos2+ self.packet_size] = features.reshape(self.nb_feature,self.packet_size)
        self.np_arr_out[:,pos2+half_size:pos2+self.packet_size+half_size] = features.reshape(self.nb_feature,self.packet_size)
        #print 'pos2 : ', pos2
        
        self.pos += self.packet_size
        self.pos = self.pos%self.np_arr_out.shape[1]
        self.abs_pos += self.packet_size
        self.pos2 = self.abs_pos%half_size
        
        self.socket_out.send(msgpack.dumps(self.abs_pos))
        
        #send OSC
        self.sendOSC(features)
        
        t_out = time.time()
        
        ## Simulate sample rate out
        #t_wait = 1/self.sr_out - (t_out - t_in)
        #print 't wait :', t_wait
        #if t_wait > 0:
        #   time.sleep(t_wait)
        #else:
        #   print 'Output stream sampling rate too fast for calculation'
            #self.stop()
        time.sleep(1/self.sr_out)

    def sendOSC(self,features):
        
        self.oscMsg.append(features)
        self.oscClient.sendto(self.oscMsg, (self.oscIP, self.oscPort))
        self.oscMsg.clearData()
        
        #try:
        #   self.oscClient.sendto(message, (self.oscIP, self.oscPort))
        #except:
        #   print 'Connection refused'
        #pass
        
 

class SendPosThread(QtCore.QThread):
    def __init__(self, parent=None, fonction = None):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.fonction = fonction
    
    def run(self):
        self.running = True
        while self.running:
            self.fonction()

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    