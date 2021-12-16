from carton.carton_type import CartonType
from carton.carton_perforation import CartonPerforation


def decide_carton_type(product_details_in_carton, carton_type):
    """
    This method will decide what type of carton it is based on the sizes
    of products found inside the carton
    1. Perforated Carton
      a. Solid cartons have only one size
      b. Mixed cartons have more than one size
    2. Non-perforated carton
      a. Is only a ratio pack
    """
    if carton_type == CartonPerforation.PERFORATED.value:
        # Carton is either solid or mixed
        hash_map_of_unique_sizes = {}
        for dict_item in product_details_in_carton:
            for key in dict_item:
                if key == 'size':
                    if dict_item[key] in hash_map_of_unique_sizes:
                        hash_map_of_unique_sizes[dict_item[key]
                                                 ] = hash_map_of_unique_sizes[dict_item[key]] + 1
                    else:
                        hash_map_of_unique_sizes[dict_item[key]] = 1
        if len(hash_map_of_unique_sizes) == 1:
            return CartonType.SOLID.value
        return CartonType.MIXED.value
        
    if carton_type == CartonPerforation.NONPERFORATED.value:
        # Carton type is ratio
        return CartonType.ASSORTED.value
