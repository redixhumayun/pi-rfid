def decide_carton_type(product_details_in_carton, carton_type):
  if carton_type == 'perforated':
    # Carton is either solid or mixed
    hash_map_of_unique_sizes = {}
    for dict_item in product_details_in_carton:
      for key in dict_item:
        if key == 'size':
          if dict_item[key] in hash_map_of_unique_sizes:
            hash_map_of_unique_sizes[dict_item[key]] = hash_map_of_unique_sizes[dict_item[key]] + 1
          else:
            hash_map_of_unique_sizes[dict_item[key]] = 1
    print(hash_map_of_unique_sizes)
    if len(hash_map_of_unique_sizes) == 1:
      print('Carton is solid')
    else:
      print('Carton is mixed')
  elif carton_type == 'non-perforated':
    # Carton type is ratio
    print('Carton type is ratio')