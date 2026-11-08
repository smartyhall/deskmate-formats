"""Conservative DeskMate 3.05 Address Book codecs."""
from .personal import Contact, ContactRecord, AddressBook, parse_bytes, parse_file
from .writer import create_contact, write_new

__all__ = ['Contact', 'ContactRecord', 'AddressBook', 'parse_bytes', 'parse_file',
           'create_contact', 'write_new']
