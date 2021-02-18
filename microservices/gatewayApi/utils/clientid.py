import string
import random

def generate_client_id (namespace):
    return "sa-%s-%s" % (namespace, get_random_string(10))

def client_id_valid(ns, client_id):
    cid = "sa-%s-" % ns

    if not client_id.startswith(cid):
        return False
    if len(client_id) != (len(cid) + 10):
        return False
    return True

def get_random_string(length):
    letters = string.ascii_lowercase + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    print("Random string of length", length, "is:", result_str)
    return result_str
