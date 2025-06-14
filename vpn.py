from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QTextEdit
)

import sys
import subprocess
import time

if sys.platform == "win32":
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

class VPN(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('VPN')
        self.setFixedSize(500, 600)

        layout = QVBoxLayout()

        self.vpn_name_edit = self.create_field("Имя VPN:", layout)
        self.server_edit = self.create_field("Сервер:", layout)
        self.psk_edit = self.create_field("Общий ключ:", layout)
        self.username_edit = self.create_field("Логин:", layout)
        self.password_edit = self.create_field("Пароль:", layout, is_password=True)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        button = QPushButton('Настроить VPN', self)
        button.clicked.connect(self.click)
        layout.addWidget(button)

        self.setLayout(layout)

    def create_field(self, label_text, layout, is_password=False):
        label = QLabel(label_text)
        layout.addWidget(label)

        edit = QLineEdit()
        if is_password:
            edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(edit)

        return edit


    def click(self):
        vpn_name = self.vpn_name_edit.text()
        server = self.server_edit.text()
        psk = self.psk_edit.text()
        username = self.username_edit.text()
        password = self.password_edit.text()
        destination = "YOUR_DESTINATION_PATH" #ввести свой путь

        if not all([vpn_name, server, psk, username, password]):
            QMessageBox.warning(self, 'Ошибка', 'Не все поля заполнены!')
            return
        else:
            try:
                self.log_message("Проверка доступности сервера...")
                ping_result = subprocess.run(['ping', '-n', '1', '-w', '10000', server],
                                             capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                if "TTL=" not in ping_result.stdout:
                    self.log_message("Ошибка: Проверьте интернет")
                    return

                self.log_message(f"Отключение существующего соединения {vpn_name}, если оно активно...")
                subprocess.run(['rasdial', vpn_name, '/disconnect'], stdout=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                time.sleep(3)

                self.log_message(f"Удаление существующего соединения {vpn_name}, если оно есть...")
                ps_script = f"""
                        if (Get-VpnConnection -Name '{vpn_name}' -ErrorAction SilentlyContinue) {{ 
                            Remove-VpnConnection -Name '{vpn_name}' -Force -ErrorAction Stop 
                        }} else {{ 
                            Write-Output 'Соединение не существует, продолжаем...' 
                        }}
                        """

                print(ps_script)
                result = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script], creationflags=CREATE_NO_WINDOW)
                if result.returncode != 0:
                    self.log_message(
                        "Ошибка создания: VPN-соединения. Проверьте параметры или запустите скрипт от имени администратора")
                    return

                self.log_message("Создание нового VPN соединения...")
                ps_script = f"""
                        Add-VpnConnection -Name '{vpn_name}' -ServerAddress '{server}' -TunnelType L2tp `
                        -L2tpPsk '{psk}' -AuthenticationMethod MSChapv2 -RememberCredential -Force -SplitTunneling
                        """
                result = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],creationflags=CREATE_NO_WINDOW)
                if result.returncode != 0:
                    self.log_message("Ошибка: Не удалось создать VPN подключение!")
                    return

                self.log_message(f"Добавление маршрута для {destination}...")
                ps_script = f"""
                        Add-VpnConnectionRoute -ConnectionName '{vpn_name}' -DestinationPrefix '{destination}'
                        """
                result = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],creationflags=CREATE_NO_WINDOW)
                if result.returncode != 0:
                    self.log_message("Ошибка: Не удалось создать маршрут!")
                    return

                self.log_message("Проверка VPN соединения...")
                subprocess.run(['rasdial', vpn_name, username, password],creationflags=CREATE_NO_WINDOW)
                time.sleep(5)
                subprocess.run(['rasdial', vpn_name],creationflags=CREATE_NO_WINDOW)

                self.log_message("VPN успешно подключен!")
                self.log_message("Настройка DNS...")

                #ввести IP1 и IP1 ("8.8.8.8")
                ps_script = f"""
                        Set-DnsClientServerAddress -InterfaceAlias '{vpn_name}' -ServerAddresses ("IP1", "IP2")
                        Write-Output 'DNS успешно настроен'
                        """

                result = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                                        creationflags=CREATE_NO_WINDOW)
                if result.returncode != 0:
                    self.log_message(
                        "Ошибка настройки DNS")
                    return
                QMessageBox.information(self, 'Успешно', 'VPN подключен!')

            except Exception as e:
                self.log_message(f"Error: {str(e)}")
                QMessageBox.critical(self, 'Error', f'An error occurred: {str(e)}')




    def log_message(self, message):
        self.log_area.append(message)
        QApplication.processEvents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VPN()
    window.show()
    sys.exit(app.exec_())
