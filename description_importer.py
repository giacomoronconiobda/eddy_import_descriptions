# -*- coding: utf-8 -*-

##########################################################################
#                                                                        #
#  Eddy: a graphical editor for the specification of Graphol ontologies  #
#  Copyright (C) 2015 Daniele Pantaleone <danielepantaleone@me.com>      #
#                                                                        #
#  This program is free software: you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation, either version 3 of the License, or     #
#  (at your option) any later version.                                   #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
#  GNU General Public License for more details.                          #
#                                                                        #
#  You should have received a copy of the GNU General Public License     #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                        #
#  #####################                          #####################  #
#                                                                        #
#  Graphol is developed by members of the DASI-lab group of the          #
#  Dipartimento di Ingegneria Informatica, Automatica e Gestionale       #
#  A.Ruberti at Sapienza University of Rome: http://www.dis.uniroma1.it  #
#                                                                        #
#     - Domenico Lembo <lembo@dis.uniroma1.it>                           #
#     - Valerio Santarelli <santarelli@dis.uniroma1.it>                  #
#     - Domenico Fabio Savo <savo@dis.uniroma1.it>                       #
#     - Daniele Pantaleone <pantaleone@dis.uniroma1.it>                  #
#     - Marco Console <console@dis.uniroma1.it>                          #
#                                                                        #
##########################################################################


import csv
import io
import os
from operator import itemgetter

from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import QtCore

from eddy.core.datatypes.collections import DistinctList
from eddy.core.datatypes.graphol import Item
from eddy.core.datatypes.system import File
from eddy.core.exporters.common import AbstractProjectExporter
from eddy.core.functions.fsystem import fwrite, fexists
from eddy.core.functions.misc import format_exception
from eddy.core.functions.path import openPath, expandPath
from eddy.core.output import getLogger
from eddy.core.owl import AnnotationAssertion, OWL2Datatype
from eddy.core.plugin import AbstractPlugin
from eddy.core.project import K_DESCRIPTION
from eddy.ui.dialogs import DiagramSelectionDialog
from eddy.ui.progress import BusyProgressDialog

LOGGER = getLogger()


class DescriptionImporterPlugin(AbstractPlugin):
    """
    Extends AbstractPlugin consume a Csv file to populate descriptions of entities.
    """
    #############################################
    #   HOOKS
    #################################

    def dispose(self):
        """
        Executed whenever the plugin is going to be destroyed.
        """
        self.debug('Uninstalling description importer')

    def start(self):
        """
        Perform initialization tasks for the plugin.
        """
        self.debug('Installing description importer')
        menu = self.session.menu('file')
        menu.addAction(
            QtWidgets.QAction(
                'Import Descriptions', self, objectName='import_descriptions',
                triggered=self.do_import, shortcut='CTRL+D, I',
                statusTip='Import descriptions in the current project')
        )


    @QtCore.pyqtSlot()
    def do_import(self):
        """
        Import an ontology into the currently active Project.
        """
        self.debug('Open dialog')
        dialog = QtWidgets.QFileDialog(self.session)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setDirectory(expandPath('~'))
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        if dialog.exec_():
            selected = [x for x in dialog.selectedFiles() if fexists(x)]
            if selected:
                try:
                    with BusyProgressDialog(parent=self.session) as progress:
                        for path in selected:
                            progress.setWindowTitle('Importing {0}...'.format(os.path.basename(path)))
                            worker = DescriptionsLoader(path, self.session.project, self.session)
                            worker.run()
                except Exception as e:
                    msgbox = QtWidgets.QMessageBox(self.session)
                    msgbox.setDetailedText(format_exception(e))
                    msgbox.setIconPixmap(QtGui.QIcon(':/icons/48/ic_error_outline_black').pixmap(48))
                    msgbox.setStandardButtons(QtWidgets.QMessageBox.Close)
                    msgbox.setText('Eddy could not import all the selected files!')
                    msgbox.setWindowIcon(QtGui.QIcon(':/icons/128/ic_eddy'))
                    msgbox.setWindowTitle('Import failed!')
                    msgbox.exec_()


class DescriptionsLoader:
    def __init__(self, path, project, session):
        self.path = path
        self.project = project
        self.session = session

    def run_v2(self):
        with open(self.path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter='|', )
            line_count = 0
            for row in csv_reader:
                if not self.project.setMeta(Item.AttributeNode, row[0],
                                            {'description': row[1], 'functional': True}):
                    print(row[0] + ' not found')
                else:
                    line_count += 1
        print('Added ', line_count, ' descriptions')

    def run(self):
        with open(self.path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter='|', )
            line_count = 0
            property_iri = self.find_iri('http://www.w3.org/2000/01/rdf-schema#comment')
            for row in csv_reader:
                iri = self.find_iri(row[0])
                assertion = AnnotationAssertion(iri, property_iri, row[1], OWL2Datatype.PlainLiteral.value, 'it')
                print(row[0])
                print(iri)
                iri.annotationAssertions.append(assertion)

    def find_iri(self, iri_str):
        for iri in self.project.iris:
            if str(iri) == iri_str:
                return iri
