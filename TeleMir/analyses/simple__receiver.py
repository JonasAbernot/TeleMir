from TeleMir.analyses.relays import Transmitter

from pyacq import StreamHandler, FakeMultiSignals
from pyqtgraph.Qt import QtGui, QtCore
import zmq
import msgpack
import time
import sys
import multiprocessing as mp

def testRcvLoop(stop_rcv):
    print 'Begin of reception'
    context=zmq.Context()
    rec_socket=context.socket(zmq.SUB)
    rec_socket.connect('tcp://192.168.1.43:5656')
    rec_socket.setsockopt(zmq.SUBSCRIBE,'')
    while stop_rcv.value:
        pack=rec_socket.recv()
        data=msgpack.loads(pack)
        print 'Received data : ',data
        
    print 'End of recepythion'

def test():


    stop_rcv = mp.Value('i',1)
    process = mp.Process(target= testRcvLoop, args = (stop_rcv,))
    process.start()
    time.sleep(2.)
    stop_rcv.value = 0
    process.join()





if __name__ == '__main__':

    test()
