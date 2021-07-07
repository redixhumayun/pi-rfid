#!/usr/bin/python3
from os import path
from multiprocessing import Process, Queue
import time
import sys
import argparse
import requests
import logging, logging.handlers
import watchtower
from typing import Union, List

from get_aws_secrets import get_secret, write_secrets_to_env_file
from location_finder import get_latitude_and_longitude, get_location
from make_api_request import MakeApiRequest
from random_number_generator import RandomNumberGenerator
from environment_variable import EnvironmentVariable
from select_location_gui import SelectLocationGUI
from display_tag_id_gui import DisplayTagIdGUI
from tag_reader import TagReader
from upload_tags import upload_tags

# This method is used to configure the watchtower handler which will be used to
# log the events to AWS CloudWatch
def listener_configurer():
  root = logging.getLogger()
  watchtower_handler = watchtower.CloudWatchLogHandler(log_group='ID1-watchtower')
  formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s')
  watchtower_handler.setFormatter(formatter)
  root.addHandler(watchtower_handler)

# This is the listener process which will watch the multiprocessing Queue for all
# records that are sent by the remaining processes
def listener_process(queue, configurer):
  configurer()
  while True:
    try:
      record = queue.get()
      if record is None:
        break
      logger = logging.getLogger(record.name)
      logger.handle(record)
    except Exception:
      import sys, traceback
      traceback.print_exc(file=sys.stderr)

# This is the configurer process which configures the handlers
def worker_configurer(queue):
  root = logging.getLogger()
  root.setLevel(logging.DEBUG)
  if not root.hasHandlers():
    console_handler = logging.StreamHandler()
    queue_handler = logging.handlers.QueueHandler(queue)

    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s')

    console_handler.setFormatter(formatter)

    root.addHandler(queue_handler)
    root.addHandler(console_handler)


if __name__ == "__main__":
  """
  This program is set up to use multi-processing. This is the main process which will spawn
  all of the child processes.
  Communication between processes happens using the multi-processing queue.
  Each process has its own queue, named accordingly. There is also a main process queue
  Each process is passed its own queue and the main queue as parameters.
  Each process queue is used by the main queue to communicate to the child process.
  The main queue is used by the child process to communicate to the main queue.
  """

  # Create the argument parser
  parser = argparse.ArgumentParser(description='Start the RFID process in either dev or prod mode')
  parser.add_argument('--env', action='store', type=str, dest='environment')

  # Parse the environment from command line
  environment = parser.parse_args().environment

  # Get the secrets from AWS and write them to a file
  secrets = get_secret(environment)
  write_secrets_to_env_file(secrets=secrets)

  # This variable will determine whether the location should be checked or not
  should_check_location = False

  # First, check if there is a location file which has been written to
  # If there is no file with location saved, fire up GPS device and fetch latitude & longitude
  # Then allow user to select the correct location
  dirname = path.dirname(__file__)
  filename = path.join(dirname, 'location.txt')
  try:
    with open(filename, 'r') as f:
      location = f.readline()
  except FileNotFoundError:
    print("The location.txt file was not found")
    should_check_location = True

  # Define a list to hold all the process references
  processes: list = []

  # Create the main queue that will be used for parent child communication
  main_queue = Queue()

  # Create a queue and process for logging purposes
  logging_queue = Queue(-1)
  logging_listener = Process(target=listener_process, args=(logging_queue, listener_configurer))
  # NOTE: I have no idea why doing a start here versus adding this process to a list and starting
  # later works, but it does. If you add this process to a list and start it later in a for loop
  # it will cause the same line to log thousands of times
  # processes.append(logging_listener)
  logging_listener.start()

  # Start the worker process that will implement all required handlers
  worker_configurer(logging_queue)

  # Start GPS process and allow user to select location only if
  # location has not already been set
  if should_check_location is True:
    # Create a boolean to check if the location has been picked by the user
    has_location_been_picked = False

    # Create the GUI and associated queue to fetch lat & long using GPS device
    gps_queue = Queue()
    gps_process = Process(
        target=get_latitude_and_longitude, args=(gps_queue, environment))

    # Create the GUI and associated queue to allow the user to select the location
    select_location_gui_queue = Queue()
    select_location_gui_process = SelectLocationGUI(select_location_gui_queue, main_queue)

    processes.append(gps_process)
    processes.append(select_location_gui_process)

    # Start the processes
    for process in processes:
      process.start()

    # Pass data between the various processes
    location_data = gps_queue.get()
    possible_locations = get_location(location_data)
    select_location_gui_queue.put(possible_locations)

    # Keep looping until a location is picked
    while has_location_been_picked is False:
      main_queue_value = main_queue.get()
      if main_queue_value == "LOCATION_PICKED":
        has_location_been_picked = True

    # Allow the processes to stop
    for process in processes:
      process.join()

    # Clear the process list
    processes.clear()

  # Create the GUI and associated queue to allow the user to view the scanned tags
  display_tag_id_gui_queue = Queue()
  display_tag_id_gui_process = DisplayTagIdGUI(display_tag_id_gui_queue, main_queue)
  processes.append(display_tag_id_gui_process)

  # Create the queue and process associated with uploading tags
  upload_tags_queue = Queue()
  upload_tags_process = Process(target=upload_tags, args=(upload_tags_queue, main_queue))
  processes.append(upload_tags_process)

  # Decide based on the environment variable passed in which process to launch
  # Either the tag reader process or the random number generator process
  if environment == EnvironmentVariable.PRODUCTION.value:
    read_tags_queue = Queue()
    read_tags_process = TagReader(read_tags_queue, main_queue)
    processes.append(read_tags_process)
  elif environment == EnvironmentVariable.DEVELOPMENT.value:
    read_tags_queue = Queue()
    read_tags_process = RandomNumberGenerator(read_tags_queue, main_queue)
    processes.append(read_tags_process)
  else:
    raise Exception('Unknown input for --env argument')

  for process in processes:
    process.start()

  list_of_tags_to_upload = []

  while True:
    main_queue_value = main_queue.get(block=True)
    if main_queue_value == "SCAN":
      # Everytime the user hits scan, start a fresh read
      list_of_tags_to_upload.clear()
      read_tags_queue.put("SCAN")

    elif main_queue_value == "UPLOAD":
      read_tags_queue.put("UPLOAD")
      upload_tags_queue.put(list_of_tags_to_upload)

    elif main_queue_value == "UPLOAD_SUCCESS":
      display_tag_id_gui_queue.put("UPLOAD SUCCESSFUL")
    
    elif main_queue_value == "UPLOAD_FAIL":
      display_tag_id_gui_queue.put("UPLOAD_FAIL")

    elif main_queue_value == "QUIT":
      # Pass in a sentinel value for all queues here
      read_tags_queue.put_nowait(None)
      upload_tags_queue.put_nowait(None)
      logging_queue.put_nowait(None)
      break
    
    elif main_queue_value.find("TAGS") != -1:
      print(main_queue_value)
      split_string = main_queue_value.split()
      number_of_tags = split_string[1]
      list_of_tags = split_string[2:]
      display_tag_id_gui_queue.put(number_of_tags)
      list_of_tags_to_upload.extend(list_of_tags)
      # Make the list unique
      list_of_tags_to_upload = list(set(list_of_tags_to_upload))
  
  for process in processes:
    logging_listener.join()
    process.join()
