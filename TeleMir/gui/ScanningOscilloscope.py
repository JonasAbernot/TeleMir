# -*- coding: utf-8 -*-
'''
Ce fichier contient plusieurs objets oscilloscope, capables d'afficher les signaux bruts, 
de manière autonome (sans intervention de l'utilisateur). Donc non, on peut pas changer la 
couleur des signaux.
'''

from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import pyqtgraphWorker as pw

class Oscilloscope(pw.PyQtGraphicsWorker):
    '''
    Affichage classique du signal, le point le plus récent est à droite. Les signaux sont 
    échellonés sur la fenêtre, l'amplitude relative des signaux est donc perdue. Dans 
    l'optique d'avoir une visualistion sexy du signal, les axes sont cachés.
    Il est possible de modifier à la volée les canaux affichés. En particulier, lors de 
    l'affichage d'un unique signal, la touche espace permet de passer au canal suivant.
    Les paramètres sont : le flux (stream) de positions sur lequel l'oscilloscope est
    branché, la largeur de la fenêtre affichée (interval_length) en seconde 
    (/!\ Des comportements étranges peuvent apparaître si la taille de cette fenêtre 
    s'approche de celle du buffer dans lequel le flux est écrit.)
    L'oscilloscope peut afficher sélectivement certains canaux (channels).
    Toutes les options disponibles pour les GraphicsWidget de pyqtgraph devraient 
    aussi être disponibles ici.

    /!\Classe buguée, elle rame sa mère dès qu'on affiche un peu trop de points
    et je sais pas pourquoi, je vais chercher.
    Lui preférer l'oscilloscope de pyacq.
    '''

    def __init__(self,stream,interval_length,channels=None,title=None,**kwargs):
        super(Oscilloscope,self).__init__(stream,interval_length,channels,title,**kwargs)
        
        #offset et gains
        self.means={}
        self.gains={}
        self.p=None

        #initialisation du timer de rafraichissement de l'échelle
        self.scaleTimer=QtCore.QTimer()
        self.scaleTimer.timeout.connect(self.updateScale)
        self.scaleTimer.setSingleShot(True)
        
    def initPlots(self):
        self.p=self.addPlot(None)

        #remise à 0 des des offsets
        self.means={i:np.mean(self.data[i]) for i in self.channels}

        #Calcul d'un gain pour chaque canal, pour que tous occupent le même espace
        self.gains={i:1.0/(np.max(self.data[i])-np.min(self.data[i])) for i in self.channels}

        #Affichage des courbes
        for i in self.channels:
            self.c[i]=self.p.plot((self.data[i]-self.means[i])*self.gains[i]+self.channels.index(i)*1.1,pen=pg.mkPen('47FF14',width=1.3))
            #Etiquette
            if len(self.channels)==1:
                label=pg.TextItem(html='<div style="text-align: center"><span style="color: #DDD;font-size: 24pt;">Channel %d</span>'%i, anchor=(0.7,2), border='w', fill=(200, 200, 200, 100))
                self.p.addItem(label)
                label.setPos(self.interval_length/2,self.channels.index(i)+0.5)


        #Empêcher la mise à jour automatique des axes
        self.p.enableAutoRange('xy',False)
        
        #Effacer les axes
        self.p.showAxis('bottom',False)
        self.p.showAxis('left',False)
        
        #lancement du timer de rafraichissement de l'échelle
        self.scaleTimer.start(4000)

    def updatePlots(self):
        for i in self.channels:
            self.c[i].clear()
            self.c[i].setData((self.data[i] - self.means[i]) * self.gains[i] + self.channels.index(i)*1.1,antialias=False)
#            self.c[i].setData(self.data[i])

    #mise à jour de l'échelle
    def updateScale(self):
        #remise à 0 des des offsets
        self.means={i:np.mean(self.data[i]) for i in self.channels}

        #Calcul d'un gain pour chaque canal, pour que tous occupent le même espace
        self.gains={i:1.0/(np.max(self.data[i])-np.min(self.data[i])) for i in self.channels}

        self.updatePlots()

        self.p.setRange(yRange=(-1,len(self.channels)))

    #Change les channels affichés
    def changeChannels(self,newChannels):
        self.channels=newChannels
        self.clear()
        self.initPlots()
        self.updateScale()
        
    #Gestion des évènements clavier
    def keyPressEvent(self,e):
        #sortir du plein écran
        if e.key()==pg.QtCore.Qt.Key_Escape:
            self.showNormal()
        #changer de canal affiché (cas d'un canal unique)
        elif e.key()==pg.QtCore.Qt.Key_Space:
            if len(self.channels)==1:
                self.changeChannels([(self.channels[0]+1)%self.data.shape[0]])


class ScanningOscilloscope(pw.PyQtGraphicsWorker):
    '''
    Affichage 'scan' du signal, comme sur les vieux oscillo. Les signaux sont 
    échellonés sur la fenêtre, l'amplitude relative des signaux est donc perdue. Dans 
    l'optique d'avoir une visualistion sexy du signal, les axes sont cachés.
    Chaque courbe est découpée en de nombreuses sous-courbes mises-à-jour indépendemment.
    Par rapport à l'oscilloscope classique, l'éxécution est beaucoup plus légère, donc 
    adaptée à des petits processeurs (raspberry pi). En revanche l'initialisation 
    peut-être un peu longue, en particulier lorsque le nombre de canaux affiché augmente
    Il est possible de modifier à la volée les canaux affichés. Le changement est lent.
    En particulier, lors de l'affichage d'un unique signal, la touche espace permet de 
    passer au canal suivant.
    Les paramètres sont : le flux (stream) de positions sur lequel l'oscilloscope est
    branché, la largeur de la fenêtre affichée (interval_length) en seconde 
    (/!\ Des comportements étranges peuvent apparaître si la taille de cette fenêtre 
    s'approche de celle du buffer dans lequel le flux est écrit.)
    L'oscilloscope peut afficher sélectivement certains canaux (channels).
    Toutes les options disponibles pour les GraphicsWidget de pyqtgraph devraient 
    aussi être disponibles ici.

    Encore à travailler : problème de la dérive lente, piste : filtrage 0,5 Hz
    '''
    
    def __init__(self,stream,interval_length,channels=None,title=None,**kwargs):
        super(ScanningOscilloscope,self).__init__(stream,interval_length,channels,title,**kwargs)
        
        self.interval_length_sec=interval_length

        #Choix du découpage en sous-courbes
        self.nbSegments=int((1000./self.period*2+3)*interval_length)
        self.segmentsLength=self.interval_length/self.nbSegments

        #initialisation du timer de rafraichissement de l'échelle
        self.scaleTimer=QtCore.QTimer()
        self.scaleTimer.timeout.connect(self.updateScale)
        self.scaleTimer.setSingleShot(True)

    def initPlots(self):

        #instanciation du plot widget où les courbes sont affichés
        self.p=self.addPlot(None)

        #remise à 0 des des offsets
        self.means={i:np.mean(self.data[i]) for i in self.channels}

        #Calcul d'un gain pour chaque canal, pour que tous occupent le même espace
        self.gains={i:1.0/(np.max(self.data[i])-np.min(self.data[i])) for i in self.channels}

        #Affichage des courbes
        for i in self.channels:
            self.c[i]=[]

            #Premier segment
            x=np.arange(self.segmentsLength+1)
            y=self.data[i,:self.segmentsLength+1]
            self.c[i].append(self.p.plot(x,y,pen=pg.mkPen('47FF14',width=1.3)))

            #Les autres segments
            for j in range(1,self.nbSegments):

                x=np.arange( j*self.segmentsLength-1 , (j+1)*self.segmentsLength )
                y=(self.data[i,(j*self.segmentsLength)-1 : (j+1)*self.segmentsLength] - self.means[i]) * self.gains[i]+self.channels.index(i)*1.1

                self.c[i].append(self.p.plot( x, y, pen=pg.mkPen('47FF14',width=1.3)))

            #Etiquette
            if len(self.channels)==1:
                label=pg.TextItem(html='<div style="text-align: center"><span style="color: #DDD;font-size: 24pt;">Channel %d</span>'%i,
                                  anchor=(0.7,2),
                                  border='w',
                                  fill=(200, 200, 200, 100),
                                  )
                self.p.addItem(label)
                label.setPos(self.interval_length/2,self.channels.index(i)+0.5)

        #Empêcher la mise-à-jour automatique des axes 
        self.p.enableAutoRange('xy',False)

        #Effacer les axes
        self.p.showAxis('bottom',False)
        self.p.showAxis('left',False)

        #Prochain segment à modifier
        self.currentSegment=0
        #Position des prochaines informations à afficher dans le buffer
        self.pos=self.init

        #lancement du timer de rafraichissement de l'échelle
        self.scaleTimer.start(self.interval_length_sec*1000)

    def updatePlots(self):
               #remise à 0 des des offsets / Tentative d'exclusion de la dérive lente.
#        self.means={i:np.mean(self.data[i]) for i in self.channels}

        #Calcul d'un gain pour chaque canal, pour que tous occupent le même espace
 #       self.gains={i:1.0/(np.max(self.data[i])-np.min(self.data[i])) for i in self.channels}

        #Choix du nombre de segments à mettre à jour (segments complets)
        for j in range((self.init-self.pos+self.half_size)%self.half_size/self.segmentsLength):
            
            #Mise à jour des segments courants
            for i in self.channels:
                
                x=np.arange(self.currentSegment*self.segmentsLength-1 , (self.currentSegment+1)*self.segmentsLength)
                y=(self.zone_mem[i,self.pos-1 : self.pos+self.segmentsLength]-self.means[i])*self.gains[i]+self.channels.index(i)*1.1

                self.c[i][self.currentSegment].clear()
                self.c[i][self.currentSegment].setData(x=x,y=y)

            #Prochain segment à modifier
            self.currentSegment=(self.currentSegment+1)%self.nbSegments
            self.pos=(self.pos+self.segmentsLength+self.segmentsLength)%(self.half_size) + self.half_size - self.segmentsLength


        #Dessin du reste de la fenêtre, augmentée d'autant de zéros que nécessaire
        for i in self.channels:
           
            x=np.arange(self.currentSegment*self.segmentsLength-1 , (self.currentSegment+1)*self.segmentsLength)
            y=np.concatenate(((self.zone_mem[i,self.pos-1 : self.init]-self.means[i])*self.gains[i],
                              np.zeros(self.segmentsLength-self.init+self.pos))
                             ) + self.channels.index(i)*1.1
            
            self.c[i][self.currentSegment].clear()
            self.c[i][self.currentSegment].setData(x=x,y=y,antialias=False)
            


    #mise à jour de l'échelle
    def updateScale(self):
        #remise à 0 des des offsets
        self.means={i:np.mean(self.data[i]) for i in self.channels}

        #Calcul d'un gain pour chaque canal, pour que tous occupent le même espace
        self.gains={i:1.0/(np.max(self.data[i])-np.min(self.data[i])) for i in self.channels}
        
        self.updatePlots()
                               
        self.p.setRange(yRange=(-1,len(self.channels)))

    #Change les channels affichés, lent (pour 1 ça passe encore quoi)
    def changeChannels(self,newChannels):
        self.channels=newChannels
        self.clear()
        self.initPlots()
        self.updateScale()
        
    #Gestion des évènements clavier
    def keyPressEvent(self,e):
        #sortir du plein écran
        if e.key()==pg.QtCore.Qt.Key_Escape:
            self.showNormal()
        #changer de canal affiché (cas d'un canal unique)
        elif e.key()==pg.QtCore.Qt.Key_Space:
            if len(self.channels)==1:
                self.changeChannels([(self.channels[0]+1)%self.data.shape[0]])


                
