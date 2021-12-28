from os import path
from multiprocessing import Process, Queue
import logging
import tkinter as tk
from tkinter import ttk, messagebox

class SelectLocationGUI(Process):
  """
  This class is used to create a GUI that will be used to display the list of possible locations to the user
  and allow the user to select a location
  """

  def __init__(self, queue: Queue, main_queue: Queue):
    Process.__init__(self)
    self.queue = queue
    self.main_queue = main_queue
    self.possible_locations = None
    self.buttons = {}
    self.logger = logging.getLogger('select_location_gui')

  def command(self, location: str):
    """
    This method is used to listen to a click event where the user
    picks the location

    Parameters
    ----------
    location: str, required
      The location selected by the user
    """
    self.logger.log(logging.DEBUG, f"The user has picked the location: {location}")
    dirname = path.dirname(__file__)
    filename = path.join(dirname, 'location.txt')
    with open(filename, 'w+') as f:
      f.write(location)
      self.logger.log(logging.DEBUG, f"Done writing the location to location.txt")
    self.root.destroy()
    self.main_queue.put("LOCATION_PICKED")

  def run(self):
    """
    This method is required to be implemented by any class
    that sub-classes multiprocessing.Process
    """
    print('running select location gui process')
    while self.possible_locations is None:
      self.possible_locations = self.queue.get()

    self.root = tk.Tk()
    self.canvas = tk.Canvas(self.root, bg="white",
                            width=800,
                            height=450)
    self.canvas.pack(side=tk.TOP)
    for location in self.possible_locations:
      key = f"button_{location}"
      self.buttons[key] = ttk.Button(
          self.root, text=location, command=lambda loc=location: self.command(loc))
      self.buttons[key].pack(side=tk.TOP)
    tk.mainloop()
