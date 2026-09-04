import hashlib
social_post_data ="this is a sample social media post for hashing"
e_data = social_post_data.encode()
magic_print = hashlib.sha256(e_data).hexdigest()
print("the hash is :", magic_print)