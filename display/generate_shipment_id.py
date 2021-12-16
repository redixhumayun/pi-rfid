from random import randint

def generate_shipment_id():
  range_start = 10**(10-1)
  range_end = (10**10)-1
  return randint(range_start, range_end)