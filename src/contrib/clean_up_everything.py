import os
import sys
from PySide2 import QtGui, QtCore, QtWidgets
import Metashape

"""
Script for cleaning up Metashape projects by removing chosen assets.
Matjaž Mori, September 2024
https://github.com/matjash

"""

class CleanUpDlg(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clean Up Everything")

        # Layout
        self.layout = QtWidgets.QVBoxLayout(self)

        self.help_label = QtWidgets.QLabel(
            "This script will remove selected assets from one or more selected Metashape project files.\n"
            "You can choose which assets to remove and whether to apply the changes to the current project, "
            "selected projects, or all projects in subfolders."
        )
        self.layout.addWidget(self.help_label)

        # Checkboxes
        self.checkboxes = {
            "Key Points": QtWidgets.QCheckBox("Key Points"),
            "Tie Points": QtWidgets.QCheckBox("Tie Points"),
            "Depth Maps": QtWidgets.QCheckBox("Depth Maps"),
            "Point Clouds": QtWidgets.QCheckBox("Point Clouds"),
            "Models": QtWidgets.QCheckBox("Models"),
            "DEMs": QtWidgets.QCheckBox("DEMs"),
            "Orthophotos": QtWidgets.QCheckBox("Orthophotos"),
            "Orthomosaics": QtWidgets.QCheckBox("Orthomosaics"),
            "Shapes": QtWidgets.QCheckBox("Shapes"),
        }

        # Set default selections
        self.checkboxes["Orthophotos"].setChecked(True)
        self.checkboxes["Orthomosaics"].setChecked(True)
        self.checkboxes["DEMs"].setChecked(True)
        self.checkboxes["Point Clouds"].setChecked(True)

        for checkbox in self.checkboxes.values():
            self.layout.addWidget(checkbox)

        # Buttons
        self.remove_button = QtWidgets.QPushButton("Remove from This Project")
        self.remove_button.clicked.connect(self.remove_from_project)
        self.layout.addWidget(self.remove_button)

        self.select_button = QtWidgets.QPushButton("Select Project")
        self.select_button.clicked.connect(self.select_project)
        self.layout.addWidget(self.select_button)

        self.subfolders_button = QtWidgets.QPushButton("All Projects in Subfolders")
        self.subfolders_button.clicked.connect(self.remove_from_subfolders)
        self.layout.addWidget(self.subfolders_button)

        self.exit_button = QtWidgets.QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        self.layout.addWidget(self.exit_button)

        self.setLayout(self.layout)

    def get_selected_assets(self):
        return [asset for asset, checkbox in self.checkboxes.items() if checkbox.isChecked()]

    def confirm_removal(self, assets, projects):
        assets_message = ', '.join(assets)
        projects_message = '\n'.join(projects)
        
        message = f"Are you sure you want to remove the following assets:\n\n" \
                  f"{assets_message}\n\n" \
                  f"From the following projects:\n\n" \
                  f"{projects_message}"
        reply = QtWidgets.QMessageBox.question(self, 'Confirm Removal of selected assets', message,
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        return reply == QtWidgets.QMessageBox.Yes

    def handle_assets(self, chunk, asset_type):
        try:
            if asset_type == "Key Points":
                if chunk.tie_points:
                    chunk.tie_points.removeKeypoints()
            elif asset_type == "Tie Points":
                chunk.tie_points = None
            elif asset_type == "Depth Maps":
                chunk.remove(chunk.depth_maps_sets)
            elif asset_type == "Point Clouds":
                chunk.remove(chunk.point_clouds)
            elif asset_type == "Models":
                chunk.remove(chunk.models)
            elif asset_type == "Tiled Models":
                chunk.remove(chunk.tiled_models)
            elif asset_type == "DEMs":
                chunk.remove(chunk.elevations)
            elif asset_type == "Orthophotos":
                for ortho in chunk.orthomosaics:
                    ortho.removeOrthophotos()
            elif asset_type == "Orthomosaics":
                chunk.remove(chunk.orthomosaics)
            elif asset_type == "Shapes":
                chunk.shapes = None
            else:
                print("Unknown asset type: " + asset_type)
                return False
            print(asset_type + " removed from " + chunk.label)
            return True
        except Exception as e:
            print(f"Failed to remove {asset_type} from {chunk.label}: {e}")
            return False

    def remove_from_project(self):
        chunk = Metashape.app.document.chunk
        selected_assets = self.get_selected_assets()
        assets = [asset for asset in selected_assets]
        projects = [chunk.label]
        log = []

        if self.confirm_removal(assets, projects):
            for asset in selected_assets:
                success = self.handle_assets(chunk, asset)
                if success:
                    log.append((f"Successfully removed {asset} from {chunk.label}", "black"))
                else:
                    log.append((f"Failed to remove {asset} from {chunk.label}", "red"))
            self.show_log(log)

    def select_project(self):
        file_dialog = QtWidgets.QFileDialog(self, "Select Metashape Project")
        file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Metashape Projects (*.psz *.psx)")
        file_dialog.setViewMode(QtWidgets.QFileDialog.List)
        file_dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            selected_assets = self.get_selected_assets()
            log = []

            if selected_assets:
                if self.confirm_removal(selected_assets, file_paths):
                    for file_path in file_paths:
                        try:
                            doc = Metashape.Document()
                            doc.open(file_path)
                            chunk = doc.chunk
                            for asset in selected_assets:
                                success = self.handle_assets(chunk, asset)
                                if success:
                                    log.append((f"Successfully removed {asset} from {file_path}", "black"))
                                else:
                                    log.append((f"Failed to remove {asset} from {file_path}", "red"))
                            doc.save()
                        except Exception as e:
                            log.append((f"Failed to open or process {file_path}: {e}", "red"))
                    self.show_log(log)

    def remove_from_subfolders(self):
        folder_dialog = QtWidgets.QFileDialog(self, "Select Folder")
        folder_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        folder_dialog.setOptions(QtWidgets.QFileDialog.DontUseNativeDialog)
        folder_dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
        
        if folder_dialog.exec_():
            folder_path = folder_dialog.selectedFiles()[0]
            file_paths = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.psz', '.psx')):
                        file_paths.append(os.path.join(root, file))
            
            if file_paths:
                # Show project selection table
                self.project_selection_table(file_paths)
    
    def project_selection_table(self, file_paths):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Select Projects to Clean")
        layout = QtWidgets.QVBoxLayout(dialog)

        # "Select All" and "Deselect All" buttons
        select_all_button = QtWidgets.QPushButton("Select All", dialog)
        select_all_button.clicked.connect(lambda: self.toggle_select_all(checkboxes, True))
        layout.addWidget(select_all_button)

        deselect_all_button = QtWidgets.QPushButton("Deselect All", dialog)
        deselect_all_button.clicked.connect(lambda: self.toggle_select_all(checkboxes, False))
        layout.addWidget(deselect_all_button)

        table = QtWidgets.QTableWidget(len(file_paths), 2, dialog)
        table.setHorizontalHeaderLabels(["Project Path", "Select"])
        table.setColumnWidth(0, 400)
        table.setColumnWidth(1, 60)
        
        checkboxes = []
        for i, path in enumerate(file_paths):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(path))
            checkbox = QtWidgets.QCheckBox()
            checkbox.setChecked(True)  # Default to selecting all
            table.setCellWidget(i, 1, checkbox)
            checkboxes.append(checkbox)
        
        layout.addWidget(table)

        ok_button = QtWidgets.QPushButton("OK", dialog)
        ok_button.clicked.connect(lambda: self.process_selected_projects(dialog, file_paths, checkboxes))
        layout.addWidget(ok_button)

        dialog.exec_()

    def toggle_select_all(self, checkboxes, state):
        # Toggles all checkboxes based on the "Select All" or "Deselect All" button state
        for checkbox in checkboxes:
            checkbox.setChecked(state)

    def process_selected_projects(self, dialog, file_paths, checkboxes):
        selected_files = [file_paths[i] for i, checkbox in enumerate(checkboxes) if checkbox.isChecked()]
        dialog.close()
        if selected_files:
            selected_assets = self.get_selected_assets()
            log = []

            if selected_assets:
                if self.confirm_removal(selected_assets, selected_files):
                    for file_path in selected_files:
                        try:
                            doc = Metashape.Document()
                            doc.open(file_path)
                            chunk = doc.chunk
                            for asset in selected_assets:
                                success = self.handle_assets(chunk, asset)
                                if success:
                                    log.append((f"Successfully removed {asset} from {file_path}", "black"))
                                else:
                                    log.append((f"Failed to remove {asset} from {file_path}", "red"))
                            doc.save()
                        except Exception as e:
                            log.append((f"Failed to open or process {file_path}: {e}", "red"))
                    self.show_log(log)

    def show_log(self, log):
        log_dialog = QtWidgets.QDialog(self)
        log_dialog.setWindowTitle("Clean Up Log")
        log_dialog.resize(500, 400)
        layout = QtWidgets.QVBoxLayout(log_dialog)

        log_text = QtWidgets.QTextEdit(log_dialog)
        log_text.setReadOnly(True)
        log_text.setStyleSheet("QTextEdit {font-family: Consolas; font-size: 10pt;}")
        log_text.setText("<br>".join(
            [f'<span style="color:{color};">{message}</span>' for message, color in log]
        ))
        log_text.setMinimumHeight(200)

        layout.addWidget(log_text)
        log_dialog.exec_()

def clean_up_dialog():
    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    dlg = CleanUpDlg(parent)
    dlg.exec_()

label = "Scripts/Clean Up Everything"
Metashape.app.addMenuItem(label, clean_up_dialog)
print(f"To execute this script press {label}")

