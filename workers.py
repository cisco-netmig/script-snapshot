import logging
logger = logging.getLogger(__name__)

import os
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from datetime import datetime

from PyQt5 import QtCore


class RunEvent(QtCore.QThread):
    """
    Threaded class for executing network snapshot tasks in the background.

    Captures command outputs from devices and writes them to text or Excel,
    while updating progress to the UI.
    """

    add_progress = QtCore.pyqtSignal(float)

    def __init__(self, form):
        """
        Initializes the RunEvent thread.

        Args:
            form (QWidget): Reference to the calling form with session and UI context.
        """
        super().__init__()
        self.form = form

    def run(self):
        """
        Entry point for the thread. Prepares the environment, runs snapshot tasks,
        generates reports, and emits progress updates.
        """
        os.makedirs(self.form.output_dir, exist_ok=True)

        self.devices = list(filter(None, self.form.devices_text_edit.toPlainText().splitlines()))
        self.commands = list(filter(None, self.form.commands_text_edit.toPlainText().splitlines()))
        self.output_type = self.form.type_combo_box.currentText()

        logger.info("[MAIN] ScriptExecution >> Starting...")

        self.output_data = {}
        self.thread_executor()
        self.generate_report()

        logger.info("[MAIN] ScriptExecution >> Finished")
        self.add_progress.emit(2)

    def thread_executor(self):
        """
        Executes device snapshots concurrently using ThreadPoolExecutor.
        Emits progress and logs any exceptions.
        """
        self.add_progress.emit(9)
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                device: executor.submit(self.snapshot_task, device)
                for device in self.devices
            }

            sleep(0.5)  # Slight delay before starting shutdown
            executor.shutdown(wait=True)

            for device, future in futures.items():
                exception = future.exception()
                if exception:
                    logger.error("Exception for %s: %s", device, exception)

    def snapshot_task(self, device):
        """
        Connects to a device, sends commands, collects output, and stores results.

        Args:
            device (str): The hostname or IP address of the device.
        """
        from netcore import GenericHandler

        available_progress = 90 / len(self.devices)
        self.output_data[device] = {
            "prompt": "",
            "command_output": {}
        }

        logger.info("Connecting to %s...", device)
        self.add_progress.emit(available_progress * 0.1)

        proxy = None
        if self.form.session.get("JUMPHOST_IP"):
            proxy = {
                "hostname": self.form.session["JUMPHOST_IP"],
                "username": self.form.session["JUMPHOST_USERNAME"],
                "password": self.form.session["JUMPHOST_PASSWORD"],
            }

        handler = GenericHandler(
            hostname=device,
            username=self.form.session["NETWORK_USERNAME"],
            password=self.form.session["NETWORK_PASSWORD"],
            proxy=proxy,
            handler="NETMIKO"
        )

        logger.info("Connection established to %s", device)
        self.output_data[device]["prompt"] = handler.prompt
        self.add_progress.emit(available_progress * 0.2)

        command_progress = (available_progress * 0.7) / len(self.commands)
        for command in self.commands:
            logger.info("Capturing '%s' output for %s", command, device)
            result = handler.sendCommand(command).strip()
            self.output_data[device]["command_output"][command] = result
            self.add_progress.emit(command_progress)
            if hasattr(logger, "savings"):
                logger.savings(10)

        handler.close()

    def generate_report(self):
        """
        Generates and writes the output report based on selected type: Text or Excel.
        """
        from netcore import XLBW

        if self.output_type == "Text":
            logger.info("Writing output to text files...")
            for device, data in self.output_data.items():
                prompt = data["prompt"]
                filename = f"{prompt[:-1]}_{datetime.now().strftime('%Y-%m-%d')}.txt"
                filepath = os.path.join(self.form.output_dir, filename)

                with open(filepath, "w") as file:
                    for command, output in data["command_output"].items():
                        file.write(f"{prompt}{command}\n{output}\n{'-' * 79}\n")

        else:
            logger.info("Writing output to Excel...")
            dump_data = {}
            for idx, (device, data) in enumerate(self.output_data.items(), start=1):
                dump_data[idx] = {"Device": data["prompt"][:-1]}
                dump_data[idx].update(data["command_output"])

            timestamp = datetime.now().strftime("%B %d_%H.%M")
            filename = f"{os.path.basename(os.path.dirname(__file__)).title()}_{timestamp}.xlsx"
            filepath = os.path.join(self.form.output_dir, filename)

            workbook = XLBW(filepath)
            worksheet = workbook.add_worksheet("Snapshot")
            workbook.dump(dump_data, worksheet)
            workbook.close()

            logger.info("Excel report saved: %s", filepath)
