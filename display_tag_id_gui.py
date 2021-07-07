from multiprocessing import Process, Queue
import logging
import tkinter as tk
from tkinter import ttk, messagebox

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
    self.queue = queue
    self.main_queue = main_queue
    self.action_to_perform = None
    self.logger = logging.getLogger('display_tag_id_gui')

  def scan(self):
    """
    This method is called when the scan button is pressed
    """
    self.logger.log(logging.DEBUG, "The user pressed scan")
    self.main_queue.put("SCAN")
  
  def upload(self):
    """
    This method is called when the upload button is pressed
    """
    self.logger.log(logging.DEBUG, "The user pressed upload")
    self.main_queue.put("UPLOAD")

  def close_window(self):
    """
    This method is called when the close button is pressed
    """
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
      self.main_queue.put("QUIT")
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
      self.logger.log(logging.ERROR, f"The canvas could not be cleared. {err}")

  def run_loop(self):
    """
    This method is used to run a loop every 900ms and is called
    by TKinter. It listens for user interactions

    Raises
    ------
    Exception
      Raises a base Exception if a button that is neither scan nor upload
      is clicked
    """

    # Check if the queue has any elements in it
    # Do this because queue.get() is a blocking call
    if self.queue.qsize() > 0:
      input_value = self.queue.get()

      # Check if the scan button has been clicked
      if input_value == "SCAN":
        self.logger.log(logging.DEBUG, "Clearing canvas because user pressed scan")
        self.clear_canvas()

      if input_value == "UPLOAD_SUCCESS":
        self.logger.log(logging.DEBUG, "Clearing canvas because the upload was successful")
        self.clear_canvas()
        self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                      font="Helvetica 20 bold", text="UPLOAD SUCCESSFUL", tag="text_to_be_shown")
        self.root.update()
        
      elif input_value == "UPLOAD_FAIL":
        self.logger.log(logging.DEBUG, "Clearing canvas because the upload failed")
        self.clear_canvas()
        self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                      font="Helvetica 20 bold", text="UPLOAD FAILED", tag="text_to_be_shown")
        self.root.update()
      
      # If the value is none of the above, then it must be the list of tags to display
      else:
        self.clear_canvas()
        self.canvas.create_text(100, 100, fill="Black", anchor=tk.NW,
                                      font="Helvetica 40 bold", text=input_value, tag="text_to_be_shown")
        self.root.update()
    self.root.after(300, self.run_loop)

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=800,
                            height=400)
    self.canvas.pack(side=tk.TOP)
    scan_button = tk.Button(self.root, text="Scan", command=self.scan, height=5, width=15)
    upload_button = tk.Button(self.root, text="Upload", command=self.upload, height=5, width=15)
    scan_button.pack(side=tk.RIGHT)
    upload_button.pack(side=tk.LEFT)
    self.root.protocol("WM_DELETE_WINDOW", self.close_window)
    self.root.after(900, self.run_loop)
    tk.mainloop()