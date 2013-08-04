from TeleMir.analyses.relays import Transmitter,Receiver
from pyacq.gui import Oscilloscope

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
    app=QtGui.QApplication([])

    streamhandler1 = StreamHandler()
    streamhandler2 = StreamHandler()

    # Configure and start
    dev = FakeMultiSignals(streamhandler = streamhandler1)
    dev.configure( name = 'Test dev',
                                nb_channel = 14,
                                sampling_rate =1000.,
                                buffer_length = 6.4,
                                packet_size = 64,
                                )
    dev.initialize()

    print dev.streams[0]
    
    trans=Transmitter(in_stream=dev.streams[0],
                      out_ip='*',
                      out_port=5656,
                      stream_handler=streamhandler1,
                      )

    receiver=Receiver(in_ip="localhost",
                      in_port=5656,
                      in_nb_channels=14,
                      in_sampling_rate=1000.,
                      in_buffer_length=6.4,
                      in_packet_size=64,
                      stream_handler=streamhandler2,
                      )

    dev.start()

    trans.start()

    receiver.start()
    '''
    stop_rcv = mp.Value('i',1)
    process = mp.Process(target= testRcvLoop, args = (stop_rcv,receiver.out_stream))

    process.start()
    time.sleep(3.)
    stop_rcv.value = 0
    process.join()
    '''
    w1=Oscilloscope(stream = dev.streams[0])
    w1.show()
    w1.auto_gain_and_offset(mode = 0)
    w1.change_param_global(xsize = 2., mode='scroll')

    w2=Oscilloscope(stream = receiver.out_stream)
    w2.show()
    w2.auto_gain_and_offset(mode = 0)
    w2.change_param_global(xsize = 2., mode='scroll')

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()

  
    receiver.stop()

    trans.stop()
      
    dev.stop()
    dev.close()

if __name__ == '__main__':

    test()
