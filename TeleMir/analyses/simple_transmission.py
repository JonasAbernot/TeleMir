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
    rec_socket.connect('tcp://localhost:5656')
    rec_socket.setsockopt(zmq.SUBSCRIBE,'')
    while stop_rcv.value:
        pack=rec_socket.recv()
        data=msgpack.loads(pack)
        print 'Received data : ',data
        
    print 'End of recepythion'

def test():
    app=QtGui.QApplication([])

    streamhandler = StreamHandler()
    
    # Configure and start
    dev = FakeMultiSignals(streamhandler = streamhandler)
    dev.configure( name = 'Test dev',
                                nb_channel = 14,
                                sampling_rate =1000.,
                                buffer_length = 6.4,
                                packet_size = 64,
                                )
    dev.initialize()
    
    trans=Transmitter(in_stream=dev.streams[0],
                      out_ip='*',
                      out_port=5656,
                      stream_handler=streamhandler,
                      )

    dev.start()

    trans.start()

    stop_rcv = mp.Value('i',1)
    process = mp.Process(target= testRcvLoop, args = (stop_rcv,))
    process.start()
    time.sleep(2.)
    stop_rcv.value = 0
    process.join()


    trans.stop()
    
    dev.stop()
    dev.close()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


if __name__ == '__main__':

    test()
