# Form implementation generated from reading ui file 'f:\2. Programming\3. VS Code Project\Python\music_player_qt\ui\add_playlist_ui.ui'
#
# Created by: PyQt6 UI code generator 6.2.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_AddPlaylist(object):
    def setupUi(self, AddPlaylist):
        AddPlaylist.setObjectName("AddPlaylist")
        AddPlaylist.resize(400, 88)
        self.gridLayout = QtWidgets.QGridLayout(AddPlaylist)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(AddPlaylist)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.playlist_name = QtWidgets.QLineEdit(AddPlaylist)
        self.playlist_name.setObjectName("playlist_name")
        self.gridLayout.addWidget(self.playlist_name, 0, 2, 1, 1)
        self.widget = QtWidgets.QWidget(AddPlaylist)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.ok_button = QtWidgets.QPushButton(self.widget)
        self.ok_button.setObjectName("ok_button")
        self.horizontalLayout.addWidget(self.ok_button)
        self.cancel_button = QtWidgets.QPushButton(self.widget)
        self.cancel_button.setObjectName("cancel_button")
        self.horizontalLayout.addWidget(self.cancel_button)
        self.gridLayout.addWidget(self.widget, 1, 0, 1, 3)

        self.retranslateUi(AddPlaylist)
        QtCore.QMetaObject.connectSlotsByName(AddPlaylist)

    def retranslateUi(self, AddPlaylist):
        _translate = QtCore.QCoreApplication.translate
        AddPlaylist.setWindowTitle(_translate("AddPlaylist", "Add Playlist"))
        self.label.setText(_translate("AddPlaylist", "Playlist Name: "))
        self.playlist_name.setPlaceholderText(_translate("AddPlaylist", "Write your new playlist name right here..."))
        self.ok_button.setText(_translate("AddPlaylist", "OK"))
        self.cancel_button.setText(_translate("AddPlaylist", "Cancel"))
