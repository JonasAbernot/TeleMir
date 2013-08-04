from TeleMir.analyses.relays import Transmitter

from pyacq import StreamHandler, FakeMultiSignals
from pyqtgraph.Qt import QtGui, QtCore
import zmq
import msgpack
import time
import sys
import multiprocessing as mp

def testRcvLoop(stop_rcv,stream):
    print 'Begin of reception'
    context=zmq.Context()
    rec_socket=context.socket(zmq.SUB)
    rec_socket.connect('tcp://localhost:%d'%stream['port'])
    rec_socket.setsockopt(zmq.SUBSCRIBE,'')
    while stop_rcv.value:
        pack=rec_socket.recv()
        data=msgpack.loads(pack)
        print 'Received data : ',data
        
    print 'End of recepythion'

def test():
   
    streamhandler=StreamHandler()

    receiver=Receiver(in_ip="192.168.1.43",
                      in_port=5656,
                      in_nb_channels=14,
                      in_sampling_rate=1000.,
                      in_buffer_length=6.4,
                      in_packet_size=64,
                      stream_handler=streamhandler,
                      )

    receiver.start()
    
    stop_rcv = mp.Value('i',1)
    process = mp.Process(target= testRcvLoop, args = (stop_rcv,receiver.out_stream))
    process.start()
    time.sleep(3.)
    stop_rcv.value = 0
    process.join()


    receiver.stop()

if __name__ == '__main__':

    test()
