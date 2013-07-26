# -*- coding: utf-8 -*-

from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import pyqtgraphWorker as pw    
from scipy import fft
import BarGraphItem as bg

class SpectrumGraphics(pw.PyQtGraphicsWorker):
        def __init__(self,stream,interval_length,freqMax=50,colorMode=True,octavMode=False,octavRan=2,channels=None,title=None,**kwargs):
            super(SpectrumGraphics,self).__init__(stream,interval_length,channels,title,**kwargs)

            self.time_length=interval_length
            
            #Shannon
            if freqMax>stream['sampling_rate']/2:
                freqMax=stream['sampling_rate']/2

            #frequence max en entier
            self.freqMax=freqMax
            self.nFreqMax=int(freqMax*interval_length)
            
            #Fourrier
            if self.nFreqMax > self.interval_length/2:
                self.nFreqMax = self.interval_length/2

            #Pile contenant les dernières fft
            self.stackLen=100
            self.lastResults={}
            self.posLastResult=0

            #Modes d'affichage
            self.colorMode=colorMode
            self.octavMode=octavMode
            self.octavRan=octavRan

        def initPlots(self):
               #transformation de l'axe des abscisses
#            ls=np.linspace(1,self.freqMax,self.nFreqMax)
            x0=[np.log(i/self.time_length) for i in range(1,self.nFreqMax)]#ls[:-1]
         #   print len(x0)
            x1=[np.log((i+1)/self.time_length) for i in range(1,self.nFreqMax)]#ls[1:]
         #   print len(x1)

            self.barGraphs={}            
            for i in self.channels:
                #calcul des fft
                spectrum=np.array(abs(fft(self.data[i]))[1:self.nFreqMax])
            
                #affichages par octaves
                if self.octavMode:
                    x0_i,x1_i=self.freqToOctave_freq()
                    spectrum=self.freqToOctave_pow(spectrum)
                else:
                    x0_i,x1_i=x0,x1
                #Création de la pile des fft passees
                self.lastResults[i]=np.zeros(self.stackLen*(len(spectrum))).reshape(self.stackLen,len(spectrum))
                self.lastResults[i][0]=spectrum
                self.posLastResult=1
                


                if self.colorMode:
 #Couleurs en fonction des valeurs de puissances
                #initialisation du gradient
                    self.colMap=pg.ColorMap(pos=np.array([1,0.7]),
                                            color=np.array([[255,0,0],[0,0,255]]),
                                            mode=pg.ColorMap.HSV_POS,
                                            )
                    brushes=self.scaledBrushes(spectrum,i)
                else:
                    brushes=None
                
                print len(spectrum)

                #affichage
                p=self.addPlot(None)
                p.getAxis('bottom').setLogMode(True)
                self.barGraphs[i]=bg.BarGraphItem(x0=x0_i,
                                                  x1=x1_i,
                                                  # width=width,
                                                  height=spectrum,
                                                  brushes=brushes #np.linspace(0.3,1,self.nFreqMax-1),
                                                  )
              
                p.addItem(self.barGraphs[i])
                self.nextRow()
             
        def scaledBrushes(self,spectrum,chan):
            #étalonnage sur du gradient sur les valeurs du spectre
            self.sMax=np.amax(self.lastResults[chan])                
            self.colMap.pos[0]=self.sMax

                #choix des couleurs en fonction des puissances
            return self.colMap.map(spectrum)

        def freqToOctave_freq(self):
             x0_oct=[]
             x1_oct=[]
             #frequences en Hz !
             f0=1
             f1=f0*self.octavRan
             while f1 < self.freqMax:
                 x0_oct.append(np.log2(f0))
                 x1_oct.append(np.log2(f1))
                 f0=self.octavRan*f0
                 f1=self.octavRan*f0
             x0_oct.append(np.log2(f0))
             x1_oct.append(np.log2(self.freqMax))
                 
             return x0_oct,x1_oct

        def freqToOctave_pow(self,spectrum):
             bandes=[spectrum[0]]
             f0=1
             f1=f0*self.octavRan
             while f1 < self.freqMax:
                 nf0=f0*self.time_length
                 nf1=f1*self.time_length
                 
                 if int(nf1)-int(nf0)==0:
                     bandes.append(spectrum[int(nf0)])
                 else :
                     som=(int(nf0)+1-nf0)*spectrum[int(nf0)] + np.sum(spectrum[int(nf0)+1:int(nf1)]) 
                     mean=som/(f1-f0)
                     bandes.append(mean)
                     
                 f0=self.octavRan*f0
                 f1=self.octavRan*f0
                 
             if self.nFreqMax-int(nf0)==0:
                 bandes.append(spectrum[int(nf0)])
             else :
                 som=(int(nf0)+1-nf0)*spectrum[int(nf0)] + np.sum(spectrum[int(nf0)+1:self.nFreqMax]) #FIXME:t'as oublié la fin de l'intégrale
                 mean=som/(f1-f0)
                 bandes.append(mean)

             return bandes

        def updatePlots(self):

            for i in self.channels:
                #calcul des fft
                spectrum=np.array(abs(fft(self.data[i]))[1:self.nFreqMax])
                
                if self.octavMode:
                    spectrum=self.freqToOctave_pow(spectrum)

                #enregistrement dans la pile de sauvegardes
                self.lastResults[i][self.posLastResult]=spectrum
                self.posLastResult=(self.posLastResult+1)%self.stackLen
                
                if self.colorMode:
                #étalonnage du gradient de couleurs sur les valeurs du spectre
                    brushes=self.scaledBrushes(spectrum,i)
                else:
                    brushes=None

                #mise à jour des graphes           
                self.barGraphs[i].updateHeights(spectrum,brushes)
        
        def adaptRange(self):
            for i in self.channels:
                maxS=np.max(self.lastResults[i])
                self.barGraphs[i].parentWidget().setRange(yRange=(0,maxS*1.1))
            
        def keyPressEvent(self,e):
            if e.key()==pg.QtCore.Qt.Key_Escape:
                self.showNormal()
            elif e.key()==pg.QtCore.Qt.Key_Space:
                self.adaptRange()
