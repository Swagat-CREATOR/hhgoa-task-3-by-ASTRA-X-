import hashlib
social_post_data ="this is a sample social media post for hashing"
edata = social_post_data.encode()
magicprint = hashlib.sha256(edata).hexdigest()
print("the hash is :", magicprint)