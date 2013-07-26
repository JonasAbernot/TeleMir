


# -*- coding: utf-8 -*-
"""

Very simple acquisition with a fake multi signal device.

"""
from TeleMir.gui import ScanningOscilloscope,KurtosisGraphics,SpectrumGraphics

from pyacq import StreamHandler, FakeMultiSignals
from pyqtgraph.Qt import QtGui, QtCore
import zmq
import msgpack
import time


def test1():
    import sys
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
    dev.start()
    
    # Read the buffer on ZMQ socket
    port = dev.streams[0]['port']
    np_array = dev.streams[0]['shared_array'].to_numpy_array()
    print np_array.shape # this should be (nb_channel x buffer_length*samplign_rate)

    #initialize plots
    w1=SpectrumGraphics(dev.streams[0],3.,channels=range(14))
    #w1 = ScanningOscilloscope(dev.streams[0],3.,channels=[3],title='Signal Brut')
    #w2 = KurtosisGraphics(dev.streams[0],2.,channels=range(14),title='Kurtosis')

    #start plots
    w1.run()
    #w2.run()
    
    w1.showFullScreen()
    #When you close the window the fake device stop emmiting
    w1.connect(w1,QtCore.SIGNAL("fermeturefenetre()"),dev.stop)
    dev.close()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


if __name__ == '__main__':

    test1()

