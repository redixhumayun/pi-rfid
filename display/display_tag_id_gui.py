from multiprocessing import Process, Queue
import logging
import tkinter as tk
from tkinter import *
from tkinter import Button, Canvas, Checkbutton, ttk, messagebox, Frame
from tkinter.constants import DISABLED, LEFT, RIGHT, TOP
from display.display_enums import DisplayEnums


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

        self.barcode_output = None

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
        self.main_queue.put(DisplayEnums.UPLOAD.value)

    def close_window(self):
        """
        This method is called when the close button is pressed
        """
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.main_queue.put(DisplayEnums.QUIT.value)
            self.logger.log(logging.DEBUG, "The user pressed quit")
            self.root.destroy()

    def clear_canvas(self):
        """
        This method is used to clear the canvas
        """
        try:
            self.canvas.delete("text_to_be_shown")
            self.root.update()
        except Exception as err:
            self.logger.log(
                logging.ERROR, f"The canvas could not be cleared. {err}")

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
            if isinstance(input_value, dict):
                if input_value['type'] == DisplayEnums.SHOW_SCANNED_BARCODE.value:
                    self.barcode_output['text'] = input_value['data']['barcode']
                elif input_value['type'] == DisplayEnums.SHOW_WEIGHT.value:
                    self.weight_output['text'] = input_value['data']['weight']
                elif input_value['type'] == DisplayEnums.SHOW_NUMBER_OF_TAGS_AND_CARTON_TYPE.value:
                    self.rfid_output['text'] = input_value['data']['tags']
                    self.carton_type_output['text'] = input_value['data']['carton_type']
                else:
                    raise Exception('This type is not understood')
        self.root.after(300, self.run_loop)
        # if self.queue.qsize() > 0:
        #     input_value = self.queue.get()

        #     # Check if the scan button has been clicked
        #     if input_value == DisplayEnums.SCAN.value:
        #         self.logger.log(
        #             logging.DEBUG, "Clearing canvas because user pressed scan")
        #         self.clear_canvas()

        #     elif input_value == DisplayEnums.UPLOAD_SUCCESS.value:
        #         self.logger.log(
        #             logging.DEBUG, "Clearing canvas because the upload was successful")
        #         self.clear_canvas()
        #         self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
        #                                 font="Helvetica 20 bold", text="UPLOAD SUCCESSFUL", tag="text_to_be_shown")
        #         self.root.update()

        #     elif input_value == DisplayEnums.UPLOAD_FAIL.value:
        #         self.logger.log(
        #             logging.DEBUG, "Clearing canvas because the upload failed")
        #         self.clear_canvas()
        #         self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
        #                                 font="Helvetica 20 bold", text="UPLOAD FAILED", tag="text_to_be_shown")
        #         self.root.update()

        #     # If the value is none of the above, then it must be the list of tags to display
        #     elif isinstance(input_value, dict) and input_value['type'] == DisplayEnums.SHOW_SCAN_DATA.value:
        #         self.clear_canvas()
        #         number_of_tags = input_value['data']['tags']
        #         carton_type = input_value['data']['carton_type']
        #         self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
        #                                 font="Helvetica 40 bold", text=number_of_tags, tag="text_to_be_shown")
        #         self.canvas.create_text(100, 200, fill="Black", anchor=tk.NW,
        #                                 font="Helvetica 40 bold", text=carton_type, tag="text_to_be_shown")
        #         self.root.update()
        # self.root.after(300, self.run_loop)

    def draw_ui(self):
        self.root.maxsize(900, 600)
        left_frame = Frame(self.root, width=200, height=400)
        left_frame.grid(row=0, column=0, padx=50)
        right_frame = Frame(self.root, width=650, height=400)
        right_frame.grid(row=0, column=1)
        
        #   Create the variables for the checkboxes
        carton_barcode_checkbox_variable = BooleanVar(value=False)
        tags_checkbox_variable = BooleanVar(value=False)
        weight_checkbox_variable = BooleanVar(value=False)

        #   Create the checkboxes for the left grid
        self.carton_barcode_checkbox = Checkbutton(left_frame, text="Carton Barcode",
                                        variable=carton_barcode_checkbox_variable,
                                        onvalue=1,
                                        offvalue=0,
                                        state=DISABLED)
        
        self.tags_checkbox = Checkbutton(left_frame, text="RFID Tags",
                                        variable=tags_checkbox_variable,
                                        onvalue=1,
                                        offvalue=0,
                                        state=DISABLED)
        
        self.weight_checkbox = Checkbutton(left_frame, text="Carton Weight",
                                        variable=weight_checkbox_variable,
                                        onvalue=1,
                                        offvalue=0,
                                        state=DISABLED)
        
        self.carton_barcode_checkbox.grid(row=0, column=0, sticky=(E, W))
        self.tags_checkbox.grid(row=1, column=0, sticky=(E, W))
        self.weight_checkbox.grid(row=2, column=0, sticky=(E, W))

        output_data_frame = Frame(right_frame, width=650, height=350)
        output_data_frame.grid(row=0, column=0)
        
        barcode_label = Label(output_data_frame, text="Barcode")
        barcode_label.grid(row=0, column=0, padx=25)
        self.barcode_output = Label(output_data_frame, text="No result")
        self.barcode_output.grid(row=0, column=1)

        weight_label = Label(output_data_frame, text="Weight")
        weight_label.grid(row=1, column=0, padx=25)
        self.weight_output = Label(output_data_frame, text="No result")
        self.weight_output.grid(row=1, column=1)

        rfid_label = Label(output_data_frame, text="RFID Tags")
        rfid_label.grid(row=2, column=0, padx=25)
        self.rfid_output = Label(output_data_frame, text="No result")
        self.rfid_output.grid(row=2, column=1)

        carton_type_label = Label(output_data_frame, text="Carton Type")
        carton_type_label.grid(row=3, column=0, padx=25)
        self.carton_type_output = Label(output_data_frame, text="No result")
        self.carton_type_output.grid(row=3, column=1)
        
        scan_button = Button(right_frame, text="Scan", command=self.scan)
        upload_button = Button(right_frame, text="Upload", command=self.upload)
        scan_button.grid(row=4, column=0, sticky=(N, S, E, W))
        upload_button.grid(row=5, column=0, sticky=(N, S, E, W))

        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.after(900, self.run_loop)
        tk.mainloop()

    def run(self):
        """
        This method is required to be implemented by any class
        that sub-classes multiprocessing.Process
        """
        self.draw_ui()
