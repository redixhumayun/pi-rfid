from multiprocessing import Process, Queue
import logging
import tkinter as tk
from tkinter import *
from tkinter import Button, Canvas, Checkbutton, ttk, messagebox, Frame
from tkinter.constants import DISABLED, LEFT, RIGHT, TOP
from display.display_enums import DisplayEnums
from display.generate_shipment_id import generate_shipment_id

class DisplayTagIdGUI(Process):
    """
    This class is used to create a GUI that will be used to display the list of tags that
    are being read from the USB device
    """

    def __init__(self, queue: Queue, main_queue: Queue):
        """
        Parameters
        ----------
        queue: list
          The list into which the main process will input data
        main_queue: list
          The list into which this process will transfer data back to the
          main process
        """
        Process.__init__(self)
        self.root = tk.Tk()
        self.queue = queue
        self.main_queue = main_queue
        self.logger = logging.getLogger('display_tag_id_gui')
        self.shipment_id = generate_shipment_id()
        self.scan_button = None
        self.upload_button = None

        #   Define the variables for storing the checkbox value
        self.carton_barcode_checkbox_variable = BooleanVar(False)
        self.tags_checkbox_variable = BooleanVar(False)
        self.weight_checkbox_variable = BooleanVar(False)

        #   Define the variables for storing the output values
        self.barcode_output = None
        self.weight_output = None
        self.carton_type_output = None
        self.rfid_output = None

    def show_error(self, title: str, body: str) -> None:
        """This method will show an error message"""
        messagebox.showerror(f"{title}", f"{body}")

    def show_message(self, title: str, body: str) -> None:
        """This method will show an info message"""
        messagebox.showinfo(f"{title}", f"{body}")

    def scan(self):
        """
        This method is called when the scan button is pressed
        """
        self.logger.log(logging.DEBUG, "The user pressed scan")
        self.main_queue.put(DisplayEnums.SCAN.value)

    def upload(self):
        """
        This method is called when the upload button is pressed
        """
        self.logger.log(logging.DEBUG, "The user pressed upload")
        #   Check if the relevant data is present before passing message to the main queue
        if self.carton_barcode_checkbox_variable is False or self.weight_checkbox_variable is False or self.tags_checkbox_variable is False:
            self.logger.log(logging.DEBUG, "The user tried to upload without all the relevant data")
            self.show_error(title="Upload Error", body="All the data is not entered. View checkboxes on the side for more information.")
        # self.main_queue.put(DisplayEnums.UPLOAD.value)
        self.main_queue.put({
            'type': DisplayEnums.UPLOAD.value,
            'data': {
                'shipment_id': self.shipment_id
            }
        })

    def close_window(self):
        """
        This method is called when the close button is pressed
        """
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.main_queue.put(DisplayEnums.QUIT.value)
            self.logger.log(logging.DEBUG, "The user pressed quit")
            # self.root.destroy()

    def generate_new_shipment_id(self):
        """This method generates a new shipment id"""
        self.shipment_id = generate_shipment_id()
        self.set_new_shipment_id()

    def check_if_scan_button_should_be_activated(self):
        """This method will check if the scan button should be activated based on whether
        there is a carton barcode value provided"""
        carton_barcode_checkbox_variable_value = self.carton_barcode_checkbox_variable.get()
        
        if carton_barcode_checkbox_variable_value is True:
            self.scan_button['state'] = NORMAL

    def check_if_upload_button_should_be_activated(self):
        """This method checks to see if the requisite data is present to activate the upload button"""
        carton_barcode_checkbox_variable_value = self.carton_barcode_checkbox_variable.get()
        weight_checkbox_variable_value = self.weight_checkbox_variable.get()
        tags_checkbox_variable_value = self.tags_checkbox_variable.get()

        if carton_barcode_checkbox_variable_value is True and weight_checkbox_variable_value is True and tags_checkbox_variable_value is True:
            self.upload_button['state'] = NORMAL

    def reset_data(self):
        """This method will reset all data from the UI after an upload is successful"""
        self.carton_barcode_checkbox_variable.set(False)
        self.tags_checkbox_variable.set(False)
        self.weight_checkbox_variable.set(False)

        self.barcode_output['text'] = "No result"
        self.weight_output['text'] = "No result"
        self.rfid_output['text'] = "No result"
        self.carton_type_output['text'] = "No result"

        self.scan_button['state'] = DISABLED
        self.upload_button['state'] = DISABLED

    def set_new_shipment_id(self):
        """This method will set the new shipment id"""
        self.shipment_id_label['text'] = f"Shipment ID: {self.shipment_id}"

    def run_loop(self):
        """
        This method is used to run a loop every 900ms and is called
        by TKinter. It listens for user interactions

        Raises
        ------
        Exception
          Raises a base Exception if it receives an enum type it does not understand
        """

        # Check if the queue has any elements in it
        # Do this because queue.get() is a blocking call
        if self.queue.qsize() > 0:
            input_value = self.queue.get()
            if input_value is None:
                self.logger.log(
                    logging.DEBUG, "Exiting the display tag process")
                self.root.destroy()
                return
            if input_value == DisplayEnums.UPLOAD_SUCCESS.value:
                self.show_message("Upload Successful", "Your data was uploaded successfully")
                self.reset_data()
            if input_value == DisplayEnums.UPLOAD_FAIL.value:
                self.show_error("Upload Error", "There was an error while uploading the carton details")
            if isinstance(input_value, dict):
                if input_value['type'] == DisplayEnums.SHOW_SCANNED_BARCODE.value:
                    self.barcode_output['text'] = input_value['data']['barcode']
                    self.carton_barcode_checkbox_variable.set(True)
                elif input_value['type'] == DisplayEnums.SHOW_WEIGHT.value:
                    self.weight_output['text'] = input_value['data']['weight']
                    self.weight_checkbox_variable.set(True)
                elif input_value['type'] == DisplayEnums.SHOW_NUMBER_OF_TAGS_AND_CARTON_TYPE.value:
                    self.rfid_output['text'] = input_value['data']['tags']
                    self.tags_checkbox_variable.set(True)

                    self.carton_type_output['text'] = input_value['data']['carton_type']
                else:
                    raise Exception('This type is not understood')

        self.check_if_scan_button_should_be_activated()
        self.check_if_upload_button_should_be_activated()
        self.root.after(300, self.run_loop)

    def draw_ui(self):
        # self.root.maxsize(1500, 900)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        self.shipment_id_label = Label(self.root, text=f"Shipment ID: {self.shipment_id}")
        self.shipment_id_label.grid(row = 0, column = 0, pady=50)
        self.shipment_id_label.config(font=("TkDefaultFont", 15))

        new_shipment_id_button = Button(self.root, text="Generate New Shipment ID", command=self.generate_new_shipment_id)
        new_shipment_id_button.grid(row = 0, column = 1, pady=50)

        #   Create the frame on the left
        left_frame = Frame(self.root, width=400, height=800)
        left_frame.grid(row=1, column=0, padx=50)

        #   Create the variables for the checkboxes
        self.carton_barcode_checkbox_variable = BooleanVar(value=False)
        self.tags_checkbox_variable = BooleanVar(value=False)
        self.weight_checkbox_variable = BooleanVar(value=False)

        #   Create the checkboxes for the left frame
        carton_barcode_checkbox = Checkbutton(left_frame, text="Carton Barcode",
                                        variable=self.carton_barcode_checkbox_variable,
                                        onvalue=1,
                                        offvalue=0,
                                        state=DISABLED)
        
        tags_checkbox = Checkbutton(left_frame, text="RFID Tags",
                                        variable=self.tags_checkbox_variable,
                                        onvalue=1,
                                        offvalue=0,
                                        state=DISABLED)
        
        weight_checkbox = Checkbutton(left_frame, text="Carton Weight",
                                        variable=self.weight_checkbox_variable,
                                        onvalue=1,
                                        offvalue=0,
                                        state=DISABLED)
        
        carton_barcode_checkbox.grid(row=0, column=0, sticky=(E, W))
        carton_barcode_checkbox.config(font=("TkDefaultFont", 15))
        
        tags_checkbox.grid(row=1, column=0, sticky=(E, W))
        tags_checkbox.config(font=("TkDefaultFont", 15))
        
        weight_checkbox.grid(row=2, column=0, sticky=(E, W))
        weight_checkbox.config(font=("TkDefaultFont", 15))

        #   Create the frame on the right
        right_frame = Frame(self.root, width=650, height=800)
        right_frame.grid(row=1, column=1)

        #   Create the frame where the output data will be shown
        output_data_frame = Frame(right_frame, width=650, height=350)
        output_data_frame.grid(row=0, column=0)
        output_data_frame.columnconfigure(0, weight=1)
        output_data_frame.rowconfigure(0, weight=1)
        
        barcode_label = Label(output_data_frame, text="Barcode")
        barcode_label.grid(row=0, column=0, padx=25)
        barcode_label.config(font=("TkDefaultFont", 15))
        self.barcode_output = Label(output_data_frame, text="No result")
        self.barcode_output.grid(row=0, column=1)
        self.barcode_output.config(font=("TkDefaultFont", 15))

        weight_label = Label(output_data_frame, text="Weight")
        weight_label.grid(row=1, column=0, padx=25)
        weight_label.config(font=("TkDefaultFont", 15))
        self.weight_output = Label(output_data_frame, text="No result")
        self.weight_output.grid(row=1, column=1)
        self.weight_output.config(font=("TkDefaultFont", 15))

        rfid_label = Label(output_data_frame, text="RFID Tags")
        rfid_label.grid(row=2, column=0, padx=25)
        rfid_label.config(font=("TkDefaultFont", 15))
        self.rfid_output = Label(output_data_frame, text="No result")
        self.rfid_output.grid(row=2, column=1)
        self.rfid_output.config(font=("TkDefaultFont", 15))

        carton_type_label = Label(output_data_frame, text="Carton Type")
        carton_type_label.grid(row=3, column=0, padx=25)
        carton_type_label.config(font=("TkDefaultFont", 15))
        self.carton_type_output = Label(output_data_frame, text="No result")
        self.carton_type_output.grid(row=3, column=1)
        self.carton_type_output.config(font=("TkDefaultFont", 15))

        #   Create the buttons for scanning & uploading the data
        self.scan_button = Button(right_frame, text="Scan", command=self.scan, state=DISABLED)
        self.scan_button.grid(row=4, column=0, sticky=(N, S, E, W))
        self.scan_button.config(font=("TkDefaultFont", 15))

        self.upload_button = Button(right_frame, text="Upload", command=self.upload, state=DISABLED)
        self.upload_button.grid(row=5, column=0, sticky=(N, S, E, W))
        self.upload_button.config(font=("TkDefaultFont", 15))

        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.after(900, self.run_loop)
        tk.mainloop()

    def run(self):
        """
        This method is required to be implemented by any class
        that sub-classes multiprocessing.Process
        """
        self.draw_ui()
        print('display run exit')
