#/*##########################################################################
# Copyright (C) 2004-2009 European Synchrotron Radiation Facility
#
# This file is part of the PyMCA X-ray Fluorescence Toolkit developed at
# the ESRF by the Beamline Instrumentation Software Support (BLISS) group.
#
# This toolkit is free software; you can redistribute it and/or modify it 
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option) 
# any later version.
#
# PyMCA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# PyMCA; if not, write to the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307, USA.
#
# PyMCA follows the dual licensing model of Trolltech's Qt and Riverbank's PyQt
# and cannot be used as a free plugin for a non-free program. 
#
# Please contact the ESRF industrial unit (industry@esrf.fr) if this license 
# is a problem for you.
#############################################################################*/
import os
import HDF5Widget
qt = HDF5Widget.qt
import HDF5Info
import HDF5CounterTable
import posixpath
import weakref
import gc

class Buttons(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QGridLayout(self)
        self.mainLayout.setMargin(0)
        self.mainLayout.setSpacing(2)
        self.buttonGroup = qt.QButtonGroup(self)
        self.buttonList = []
        i = 0
        optionList = ['SCAN', 'MCA', 'IMAGE']
        optionList = ['SCAN', 'MCA']
        actionList = ['ADD', 'REMOVE', 'REPLACE']
        for option in optionList:
            row = optionList.index(option)
            for action in actionList:
                col = actionList.index(action)
                button = qt.QPushButton(self)
                button.setText(action + " " + option)
                self.mainLayout.addWidget(button, row, col)
                self.buttonGroup.addButton(button)
                self.buttonList.append(button)
        self.connect(self.buttonGroup,
                     qt.SIGNAL('buttonClicked(QAbstractButton *)'),
                     self.emitSignal)

    def emitSignal(self, button):
        ddict={}
        ddict['event'] = 'buttonClicked'
        ddict['action'] = str(button.text())
        self.emit(qt.SIGNAL('ButtonsSignal'), ddict)

class QNexusWidget(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.data = None
        self._dataSourceList = []
        self._oldCntSelection = None
        self._cntList = []
        self._aliasList = []
        self._defaultModel = HDF5Widget.FileModel()
        self.getInfo = HDF5Info.getInfo
        self._modelDict = {}
        self._widgetDict = {}
        self.build()

    def build(self):
        self.mainLayout = qt.QVBoxLayout(self)
        self.splitter = qt.QSplitter(self)
        self.splitter.setOrientation(qt.Qt.Vertical)
        self.hdf5Widget = HDF5Widget.HDF5Widget(self._defaultModel,
                                                self.splitter)
        self.hdf5Widget.setSelectionMode(qt.QAbstractItemView.ExtendedSelection)
        self.cntTable = HDF5CounterTable.HDF5CounterTable(self.splitter)
        self.mainLayout.addWidget(self.splitter)
        self.buttons = Buttons(self)
        self.mainLayout.addWidget(self.buttons)
        self.connect(self.hdf5Widget,
                     qt.SIGNAL('HDF5WidgetSignal'),
                     self.hdf5Slot)
        self.connect(self.buttons,
                     qt.SIGNAL('ButtonsSignal'),
                     self.buttonsSlot)

    def getWidgetConfiguration(self):
        cntSelection = self.cntTable.getCounterSelection()
        ddict = {}
        ddict['counters'] = cntSelection['cntlist']
        ddict['aliases'] = cntSelection['aliaslist']
        return ddict

    def setWidgetConfiguration(self, ddict=None):
        if ddict is None:
            self._cntList = []
            self._aliasList = []
        else:
            self._cntList = ddict['counters']
            self._aliasList = ddict['aliases']
            if type(self._cntList) == type(""):
                self._cntList = [ddict['counters']]
            if type(self._aliasList) == type(""):
                self._aliasList = [ddict['aliases']]
        self.cntTable.build(self._cntList, self._aliasList)

    def setDataSource(self, dataSource):
        self.data = dataSource
        if self.data is None:
            self.hdf5Widget.collapseAll()
            self.hdf5Widget.setModel(self._defaultModel)
            return
        def dataSourceDistroyed(weakrefReference):
            idx = self._dataSourceList.index(weakrefReference)
            del self._dataSourceList[idx]
            del self._modelDict[weakrefReference]
        ref = weakref.ref(dataSource, dataSourceDistroyed)
        if ref not in self._dataSourceList:
            self._dataSourceList.append(ref)
            self._modelDict[ref] = HDF5Widget.FileModel()
        model = self._modelDict[ref]
        self.hdf5Widget.setModel(model)
        for source in self.data._sourceObjectList:
            self.hdf5Widget.model().appendPhynxFile(source, weakreference=True)

    def setFile(self, filename):
        self._data = self.hdf5Widget.model().openFile(filename, weakreference=True)

    def hdf5Slot(self, ddict):
        if ddict['event'] == 'itemClicked':
            if ddict['mouse'] == "right":
                self._checkWidgetDict()
                fileIndex = self.data.sourceName.index(ddict['file'])
                phynxFile  = self.data._sourceObjectList[fileIndex]
                info = self.getInfo(phynxFile, ddict['name'])
                widget = HDF5Info.HDF5GeneralInfoWidget()
                widget.notifyCloseEventToWidget(self)
                widget.setWindowTitle(os.path.basename(ddict['file']))
                wid = id(widget)
                self._widgetDict[wid] = widget
                widget.setInfoDict(info)
                widget.show()
                if ddict['type'] == 'Dataset':
                    if ddict['dtype'].startswith('|S'):
                        #print "string"
                        pass
                    else:
                        #print "dataset"
                        pass                
        if ddict['event'] == "itemDoubleClicked":
            if ddict['type'] == 'Dataset':
                if ddict['dtype'].startswith('|S'):
                    print "string"
                else:
                    root = ddict['name'].split('/')
                    root = "/" + root[1]
                    cnt  = ddict['name'].split(root)[-1]
                    if cnt not in self._cntList:
                        self._cntList.append(cnt)
                        basename = posixpath.basename(cnt)
                        if basename not in self._aliasList:
                            self._aliasList.append(basename)
                        else:
                            self._aliasList.append(cnt)
                        self.cntTable.build(self._cntList, self._aliasList)
            if ddict['type'] == 'Entry':
                print "I should apply latest selection"

    def buttonsSlot(self, ddict):
        if self.data is None:
            return
        action, selectionType = ddict['action'].split()
        entryList = self.getEntryList()
        if not len(entryList):
            return
        cntSelection = self.cntTable.getCounterSelection()
        self._aliasList = cntSelection['aliaslist']
        selectionList = []
        for entry, filename in entryList:
            if not len(cntSelection['cntlist']):
                continue
            if not len(cntSelection['y']):
                #nothing to plot
                continue
            for yCnt in cntSelection['y']:
                sel = {}
                sel['SourceName'] = [filename]
                sel['SourceType'] = "HDF5"
                fileIndex = self.data.sourceName.index(filename)
                phynxFile  = self.data._sourceObjectList[fileIndex]
                entryIndex = phynxFile["/"].listnames().index(entry[1:])
                sel['Key']        = "%d.%d" % (fileIndex+1, entryIndex+1)
                sel['legend']     = os.path.basename(sel['SourceName'][0])+\
                                    " " + sel['Key']
                sel['selection'] = {}
                sel['selection']['sourcename'] = filename
                sel['selection']['entry'] = entry
                sel['selection']['key'] = "%d.%d" % (fileIndex+1, entryIndex+1)
                sel['selection']['x'] = cntSelection['x']
                sel['selection']['y'] = [yCnt]
                sel['selection']['m'] = cntSelection['m']
                sel['selection']['cntlist'] = cntSelection['cntlist']
                sel['selection']['aliaslist'] = cntSelection['aliaslist']
                sel['selection']['selectiontype'] = selectionType
                if selectionType.upper() == "SCAN":
                    sel['scanselection'] = True
                    sel['mcaselection']  = False
                elif selectionType.upper() == "MCA":
                    sel['scanselection'] = False
                    sel['mcaselection']  = True
                else:
                    sel['scanselection'] = False
                    sel['mcaselection']  = False
                selectionList.append(sel)
        if len(selectionList):
            if action.upper() == "ADD":
                self.emit(qt.SIGNAL("addSelection"), selectionList)
            if action.upper() == "REMOVE":
                self.emit(qt.SIGNAL("removeSelection"), selectionList)
            if action.upper() == "REPLACE":
                self.emit(qt.SIGNAL("replaceSelection"), selectionList)

    def getEntryList(self):
        return self.hdf5Widget.getSelectedEntries()

    def closeEvent(self, event):
        keyList = self._widgetDict.keys()
        for key in keyList:
            self._widgetDict[key].close()
            del self._widgetDict[key]
        return qt.QWidget.closeEvent(self, event)

    def _checkWidgetDict(self):
        keyList = self._widgetDict.keys()
        for key in keyList:
            if self._widgetDict[key].isHidden():
                del self._widgetDict[key]

    def customEvent(self, event):
        if hasattr(event, 'dict'):
            ddict = event.dict
            if ddict.has_key('event'):
                if ddict['event'] == "closeEventSignal":
                    if self._widgetDict.has_key(ddict['id']):
                        del self._widgetDict[ddict['id']]
    
if __name__ == "__main__":
    import sys
    app = qt.QApplication(sys.argv)
    w = QNexusWidget()
    if 0:
        w.setFile(sys.argv[1])
    else:
        import NexusDataSource
        dataSource = NexusDataSource.NexusDataSource(sys.argv[1])
        w.setDataSource(dataSource)
    def addSelection(sel):
        print sel
    def removeSelection(sel):
        print sel
    def replaceSelection(sel):
        print sel
    w.show()
    qt.QObject.connect(w, qt.SIGNAL("addSelection"),     addSelection)
    qt.QObject.connect(w, qt.SIGNAL("removeSelection"),  removeSelection)
    qt.QObject.connect(w, qt.SIGNAL("replaceSelection"), replaceSelection)
    sys.exit(app.exec_())
