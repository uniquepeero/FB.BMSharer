from sharer import Sharer
from utils import users


if __name__ == '__main__':
    for email, password in users():
        Sharer(email, password).create_share()
