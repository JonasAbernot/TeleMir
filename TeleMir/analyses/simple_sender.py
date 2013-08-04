from TeleMir.analyses.relays import Transmitter

from pyacq import StreamHandler, FakeMultiSignals
from pyqtgraph.Qt import QtGui, QtCore
import zmq
import msgpack
import time
import sys
import multiprocessing as mp


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

    time.sleep(10.)

    trans.stop()
    
    dev.stop()
    dev.close()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


if __name__ == '__main__':

    test()
