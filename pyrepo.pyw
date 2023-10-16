import sys
import os
import json
import requests
import base64
from PySide6.QtCore import Qt, QUrl, QProcess
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QTextBrowser, QLineEdit, QLabel, QDialog, QDialogButtonBox

class TokenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.token_line_edit = QLineEdit()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("OAuth Token:"))
        layout.addWidget(self.token_line_edit)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        self.setWindowTitle("Enter GitHub OAuth Token")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyRepo")
        self.setWindowIcon(QIcon('icon.png'))
        self.username = ""
        self.token = ""
        self.init_ui()
        self.check_token()

    def init_ui(self):
        self.publicTreeWidget = QTreeWidget()
        self.publicTreeWidget.setHeaderLabels(["Public Repositories"])
        self.publicTreeWidget.itemClicked.connect(self.on_item_clicked)
        self.privateTreeWidget = QTreeWidget()
        self.privateTreeWidget.setHeaderLabels(["Private Repositories"])
        self.privateTreeWidget.itemClicked.connect(self.on_item_clicked)
        self.pushButton = QPushButton("Open in GitHub")
        self.pushButton.clicked.connect(self.on_open_in_github_clicked)
        self.pushButton.setEnabled(False)
        self.urlBrowser = QTextBrowser()
        tree_layout = QHBoxLayout()
        tree_layout.addWidget(self.publicTreeWidget)
        tree_layout.addWidget(self.privateTreeWidget)
        layout = QVBoxLayout()
        layout.addLayout(tree_layout)
        layout.addWidget(self.pushButton)
        layout.addWidget(self.urlBrowser)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def check_token(self):
        token_file = 'oauth_token.json'
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token_data = json.load(f)
                self.token = token_data.get('token', '')
                if self.authenticate(self.token):
                    self.load_repos()
                    return
        self.prompt_for_token()

    def authenticate(self, token):
        headers = {'Authorization': f'token {token}'}
        response = requests.get('https://api.github.com/user', headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            self.username = user_data.get('login', '')
            return True
        else:
            return False

    def prompt_for_token(self):
        token_dialog = TokenDialog(self)
        result = token_dialog.exec_()
        if result == QDialog.Accepted:
            self.token = token_dialog.token_line_edit.text()
            if self.authenticate(self.token):
                with open('oauth_token.json', 'w') as f:
                    json.dump({'token': self.token}, f)
                self.load_repos()
            else:
                self.statusBar().showMessage("Invalid OAuth Token. Please try again.")

    def load_repos(self):
        headers = {'Authorization': f'token {self.token}'}
        response = requests.get('https://api.github.com/user/repos?visibility=all', headers=headers)
        if response.status_code == 200:
            repos = response.json()
            for repo in repos:
                item = QTreeWidgetItem(self.privateTreeWidget if repo['private'] else self.publicTreeWidget)
                item.setText(0, repo['name'])


    def on_item_clicked(self, item):
        repo_name = item.text(0)
        headers = {'Authorization': f'token {self.token}'}
        response = requests.get(f'https://api.github.com/repos/{self.username}/{repo_name}', headers=headers)
        if response.status_code == 200:
            repo_info = response.json()
            description = repo_info.get('description', 'No description available.')
            
            readme_response = requests.get(f'https://api.github.com/repos/{self.username}/{repo_name}/readme', headers=headers)
            readme_text = "No README.md found."
            if readme_response.status_code == 200:
                readme_info = readme_response.json()
                readme_content_base64 = readme_info.get('content', '')
                readme_text = base64.b64decode(readme_content_base64).decode('utf-8')
            
            self.urlBrowser.setOpenExternalLinks(True)
            self.urlBrowser.setText(f"<b>About:</b> {description}<br><br><b>README.md:</b><br>{readme_text}<br><br><a href='https://github.com/{self.username}/{repo_name}' target='_blank' style='color: yellow;'>Open on GitHub</a>")

            self.pushButton.setEnabled(True)
        else:
            self.urlBrowser.setText("Could not fetch repository information.")
            self.pushButton.setEnabled(False)

    def on_open_in_github_clicked(self):
        item = self.publicTreeWidget.currentItem() or self.privateTreeWidget.currentItem()
        if item:
            repo_name = item.text(0)
            QProcess.startDetached("xdg-open", [f"https://github.com/{self.username}/{repo_name}"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        * {
            background: #2E2E2E;
            color: #FFFFFF;
        }
        QHeaderView::section {
            background-color: #555555;
            border: none;
            color: white;
            padding: 5px;
        }
        QTreeWidget::item:selected {
            background: #6e6e6e;
        }
        QPushButton {
            background: #555555;
        }
        QPushButton:hover {
            background: #888888;
        }
        """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
