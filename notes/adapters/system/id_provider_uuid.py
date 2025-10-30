from notes.ports.id_provider import IdProvider
import uuid

class UuidIdProvider(IdProvider):

    def new_id(self):
        return str(uuid.uuid4())